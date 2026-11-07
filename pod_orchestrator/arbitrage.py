#!/usr/bin/env python3
"""
PrintDeck Dual-POD Smart Arbitrage Router & 120-Minute Grace Queue Manager.
Compares Printify vs. Printful landed cost, stock status, SLA, and enforces
the strict >= 35.0% net margin floor after Stripe fees (2.9% + $0.30).
"""
from __future__ import annotations
import datetime as dt
import json
import uuid
from typing import Any, Dict, List, Optional
import sqlite3

from ssot_engine import require_punch_in


class MarginFloorViolationError(ValueError):
    """Raised when a product or order violates the mandatory 35% net margin floor."""


class OutOfStockEverywhereError(RuntimeError):
    """Raised when neither Printify nor Printful has the requested blank in stock."""


class SmartArbitrageRouter:
    MIN_MARGIN_PCT = 35.0
    STRIPE_PCT_FEE = 0.029
    STRIPE_FIXED_CENTS = 30
    GRACE_HOLD_MINUTES = 120

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def calculate_net_margin_pct(
        retail_cents: int,
        blank_cost_cents: int,
        shipping_cents: int,
    ) -> Tuple[int, float]:
        stripe_fee = int(round(retail_cents * SmartArbitrageRouter.STRIPE_PCT_FEE)) + SmartArbitrageRouter.STRIPE_FIXED_CENTS
        total_cost = blank_cost_cents + shipping_cents + stripe_fee
        net_profit_cents = retail_cents - total_cost
        margin_pct = (net_profit_cents / max(retail_cents, 1)) * 100.0
        return net_profit_cents, round(margin_pct, 2)

    def select_optimal_provider(self, variant_sku: str, customer_zip: str, retail_cents: int) -> Dict[str, Any]:
        rows = self.conn.execute(
            "SELECT * FROM pod_provider_mappings WHERE variant_sku = ? AND in_stock = 1",
            (variant_sku,),
        ).fetchall()

        if not rows:
            raise OutOfStockEverywhereError(f"Variant {variant_sku} is out of stock on both Printify and Printful.")

        candidates: List[Dict[str, Any]] = []
        for r in rows:
            net_profit_cents, margin_pct = self.calculate_net_margin_pct(
                retail_cents=retail_cents,
                blank_cost_cents=r["base_cost_cents"],
                shipping_cents=r["shipping_base_cents"],
            )
            candidates.append({
                "provider": r["provider"],
                "external_blueprint_id": r["external_blueprint_id"],
                "external_variant_id": r["external_variant_id"],
                "landed_cost_cents": r["base_cost_cents"] + r["shipping_base_cents"],
                "net_profit_cents": net_profit_cents,
                "margin_pct": margin_pct,
                "avg_production_days": r["avg_production_days"],
            })

        # Sort by highest net margin first, then fastest production SLA
        candidates.sort(key=lambda c: (-c["margin_pct"], c["avg_production_days"]))
        winner = candidates[0]

        if winner["margin_pct"] < self.MIN_MARGIN_PCT:
            raise MarginFloorViolationError(
                f"FINOPS BLOCK: Best provider ({winner['provider']}) yields {winner['margin_pct']}% margin "
                f"on {variant_sku}, which is below the mandatory {self.MIN_MARGIN_PCT}% floor."
            )

        runner_up = candidates[1] if len(candidates) > 1 else None
        arbitrage_savings_cents = (
            (runner_up["landed_cost_cents"] - winner["landed_cost_cents"])
            if runner_up else 0
        )

        return {
            "selected_provider": winner["provider"],
            "external_variant_id": winner["external_variant_id"],
            "margin_pct": winner["margin_pct"],
            "net_profit_cents": winner["net_profit_cents"],
            "arbitrage_savings_cents": arbitrage_savings_cents,
            "failover_available": runner_up is not None,
            "failover_provider": runner_up["provider"] if runner_up else None,
        }

    def create_order_with_grace_hold(
        self,
        stripe_session_id: str,
        customer_email: str,
        shipping_zip: str,
        shipping_address: Dict[str, str],
        variant_sku: str,
        quantity: int,
        retail_cents: int,
    ) -> Dict[str, Any]:
        route = self.select_optimal_provider(variant_sku, shipping_zip, retail_cents)
        now_utc = dt.datetime.now(dt.timezone.utc)
        grace_expires = (now_utc + dt.timedelta(minutes=self.GRACE_HOLD_MINUTES)).isoformat()
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        with self.conn:
            self.conn.execute(
                """INSERT INTO orders
                   (id, stripe_session_id, customer_email, shipping_zip, shipping_address_json,
                    total_cents, selected_provider, expected_margin_pct, status, grace_expires_utc, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PAID_GRACE_HOLD', ?, ?)""",
                (
                    order_id,
                    stripe_session_id,
                    customer_email,
                    shipping_zip,
                    json.dumps(shipping_address),
                    retail_cents * quantity,
                    route["selected_provider"],
                    route["margin_pct"],
                    grace_expires,
                    now_utc.isoformat(),
                ),
            )
            self.conn.execute(
                """INSERT INTO order_items (id, order_id, variant_sku, quantity, unit_price_cents)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), order_id, variant_sku, quantity, retail_cents),
            )
            self.conn.execute(
                """INSERT INTO fulfillment_holds (order_id, hold_reason, editable_until_utc, released, modifications_log_json)
                   VALUES (?, '120_MIN_EDITABLE_GRACE_WINDOW', ?, 0, '[]')""",
                (order_id, grace_expires),
            )

        return {
            "order_id": order_id,
            "status": "PAID_GRACE_HOLD",
            "selected_provider": route["selected_provider"],
            "expected_margin_pct": route["margin_pct"],
            "arbitrage_savings_cents": route["arbitrage_savings_cents"],
            "grace_expires_utc": grace_expires,
        }

    def modify_order_in_grace_window(
        self,
        order_id: str,
        new_shipping_address: Optional[Dict[str, str]] = None,
        new_variant_sku: Optional[str] = None,
    ) -> Dict[str, Any]:
        row = self.conn.execute(
            "SELECT o.*, h.editable_until_utc, h.released, h.modifications_log_json "
            "FROM orders o JOIN fulfillment_holds h ON o.id = h.order_id WHERE o.id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Order {order_id} not found.")
        if row["released"] == 1 or row["status"] != "PAID_GRACE_HOLD":
            raise RuntimeError(f"Order {order_id} has already exited the 120-minute grace window.")

        now_utc = dt.datetime.now(dt.timezone.utc)
        if dt.datetime.fromisoformat(row["editable_until_utc"]) <= now_utc:
            raise RuntimeError(f"120-minute grace window expired for {order_id}.")

        mods = json.loads(row["modifications_log_json"])
        with self.conn:
            if new_shipping_address:
                self.conn.execute(
                    "UPDATE orders SET shipping_address_json = ?, shipping_zip = ? WHERE id = ?",
                    (json.dumps(new_shipping_address), new_shipping_address.get("zip", row["shipping_zip"]), order_id),
                )
                mods.append({"ts": now_utc.isoformat(), "action": "ADDRESS_UPDATED"})
            if new_variant_sku:
                self.conn.execute(
                    "UPDATE order_items SET variant_sku = ? WHERE order_id = ?",
                    (new_variant_sku, order_id),
                )
                mods.append({"ts": now_utc.isoformat(), "action": f"VARIANT_SWAPPED_TO_{new_variant_sku}"})
            self.conn.execute(
                "UPDATE fulfillment_holds SET modifications_log_json = ? WHERE order_id = ?",
                (json.dumps(mods), order_id),
            )
        return {"order_id": order_id, "status": "PAID_GRACE_HOLD", "modifications": mods}
