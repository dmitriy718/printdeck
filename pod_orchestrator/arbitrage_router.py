#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 Smart Order Arbitrage Router.
Evaluates Printify and Printful v2 in real time on:
  1. Exact size/color blank in-stock availability
  2. Total fulfillment cost = Base Blank Cost + Shipping to Customer ZIP - Volume Tier Discounts
  3. Regional proximity & historical production + transit speed to customer's shipping address
  4. Automatic failover to the secondary provider if the primary returns OOS or print-queue error.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.database import DatabaseManager, get_db
from ssot_engine import require_punch_in
from .models import (
    ArbitrageDecision,
    OrderLineRequest,
    ProviderOrderResult,
    ProviderQuote,
    ShippingAddress,
)
from .printful_client import PrintfulQueueError, PrintfulV2Client
from .printify_client import PrintifyClient, PrintifyQueueError


class ArbitrageNoStockError(RuntimeError):
    """Raised when both Printify and Printful are out of stock for a requested blank."""


class SmartArbitrageRouter:
    """
    Real-time dual-provider arbitrage engine and automatic failover dispatcher.
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        printify_client: Optional[PrintifyClient] = None,
        printful_client: Optional[PrintfulV2Client] = None,
        margin_weight: float = 0.65,
        speed_weight: float = 0.35,
    ) -> None:
        self.db = db or get_db()
        self.printify = printify_client or PrintifyClient()
        self.printful = printful_client or PrintfulV2Client()
        self.margin_weight = margin_weight
        self.speed_weight = speed_weight

    async def evaluate_variant_quotes(
        self,
        line: OrderLineRequest,
        address: ShippingAddress,
    ) -> List[ProviderQuote]:
        """
        Computes real-time ProviderQuote objects across both Printify and Printful
        for a single line item.
        """
        variant_info = self.db.get_variant_with_mappings(line.variant_id)
        if not variant_info:
            raise ValueError(f"Unknown PrintDeck variant: {line.variant_id}")

        quotes: List[ProviderQuote] = []
        gross_retail = line.unit_retail_price_cents * line.quantity

        for m in variant_info.get("provider_mappings", []):
            provider = m["provider"]
            if provider == "printify":
                avail = await self.printify.check_variant_availability(
                    blueprint_id=m["external_blueprint_id"],
                    print_provider_id=m["external_print_provider_id"],
                    external_variant_id=m["external_variant_id"],
                    db_in_stock_default=bool(m["in_stock"]),
                )
                ship_info = await self.printify.calculate_shipping_to_zip(
                    mapping=m, quantity=line.quantity, address=address
                )
            else:
                avail = await self.printful.check_variant_availability(
                    external_variant_id=m["external_variant_id"],
                    db_in_stock_default=bool(m["in_stock"]),
                )
                ship_info = await self.printful.calculate_shipping_to_zip(
                    mapping=m, quantity=line.quantity, address=address
                )

            in_stock = bool(avail["in_stock"])
            gross_blank_cents = int(m["base_blank_cost_cents"]) * line.quantity
            discount_bps = int(m.get("volume_tier_discount_bps", 0))
            # Volume Tier Discounts (e.g. Printify Premium 2000 bps = 20% off blank cost;
            # plus extra 300 bps multi-unit volume bonus when quantity >= 3)
            effective_discount_bps = discount_bps + (300 if line.quantity >= 3 else 0)
            volume_discount_cents = int(round(gross_blank_cents * (effective_discount_bps / 10000.0)))
            shipping_cents = int(ship_info["shipping_cents"])

            # Core Formula:
            # Total Fulfillment Cost = Base Blank Cost + Shipping to Customer ZIP - Volume Tier Discounts
            total_fulfillment_cost_cents = max(
                0, gross_blank_cents + shipping_cents - volume_discount_cents
            )
            net_margin_cents = gross_retail - total_fulfillment_cost_cents
            net_margin_pct = (
                round((net_margin_cents / gross_retail) * 100.0, 2) if gross_retail > 0 else 0.0
            )

            avg_prod_hours = float(m.get("avg_production_hours", 30.0))
            transit_hours = float(ship_info["estimated_transit_hours"])
            total_delivery_hours = round(avg_prod_hours + transit_hours, 1)
            proximity_km = float(ship_info["proximity_km_est"])
            quality = float(m.get("quality_rating", 4.85))

            if not in_stock:
                utility_score = -9999.0
                disqualified = "OUT_OF_STOCK_AT_PROVIDER"
            else:
                # Normalize margin contribution ($0.01 = 0.05 pts) and delivery speed (faster = higher)
                margin_score = (net_margin_cents / 100.0) * 2.5
                speed_score = max(0.0, (168.0 - total_delivery_hours) * 0.45)
                regional_bonus = 6.0 if m.get("facility_region") == address.inferred_us_region else 0.0
                quality_bonus = (quality - 4.5) * 10.0
                utility_score = round(
                    (self.margin_weight * margin_score)
                    + (self.speed_weight * speed_score)
                    + regional_bonus
                    + quality_bonus,
                    3,
                )
                disqualified = None

            quotes.append(
                ProviderQuote(
                    provider=provider,
                    provider_label=m["provider_name_label"],
                    variant_id=variant_info["variant_id"],
                    master_sku=variant_info["master_sku"],
                    external_blueprint_id=m["external_blueprint_id"],
                    external_print_provider_id=m["external_print_provider_id"],
                    external_variant_id=m["external_variant_id"],
                    quantity=line.quantity,
                    in_stock=in_stock,
                    gross_blank_cost_cents=gross_blank_cents,
                    shipping_to_zip_cents=shipping_cents,
                    volume_tier_discount_bps=effective_discount_bps,
                    volume_tier_discount_cents=volume_discount_cents,
                    total_fulfillment_cost_cents=total_fulfillment_cost_cents,
                    gross_retail_revenue_cents=gross_retail,
                    net_margin_cents=net_margin_cents,
                    net_margin_pct=net_margin_pct,
                    facility_region=m.get("facility_region", "US-EAST"),
                    facility_zip_prefix=m.get("facility_zip_prefix", "282"),
                    customer_zip_prefix=address.zip_prefix3,
                    regional_proximity_km_est=proximity_km,
                    avg_production_hours=avg_prod_hours,
                    estimated_transit_hours=transit_hours,
                    total_delivery_hours_est=total_delivery_hours,
                    quality_rating=quality,
                    arbitrage_utility_score=utility_score,
                    disqualified_reason=disqualified,
                )
            )

        quotes.sort(key=lambda q: q.arbitrage_utility_score, reverse=True)
        return quotes

    async def compute_order_arbitrage(
        self,
        order_id: str,
        lines: List[OrderLineRequest],
        address: ShippingAddress,
    ) -> ArbitrageDecision:
        """
        Evaluates all items in an order and determines the optimal POD fulfillment routing
        (Printify vs Printful v2) with complete margin and delivery speed telemetry.
        """
        all_quotes: List[ProviderQuote] = []
        line_allocations: List[Dict[str, Any]] = []

        provider_totals: Dict[str, Dict[str, float]] = {
            "printify": {"cost": 0, "margin": 0, "hours": 0.0, "in_stock_all": 1, "score": 0.0},
            "printful": {"cost": 0, "margin": 0, "hours": 0.0, "in_stock_all": 1, "score": 0.0},
        }

        for line in lines:
            variant_info = self.db.get_variant_with_mappings(line.variant_id)
            if variant_info and variant_info.get("is_legacy_hardware"):
                line_allocations.append(
                    {
                        "variant_id": line.variant_id,
                        "master_sku": variant_info["master_sku"],
                        "selected_provider": "hardware_direct",
                        "failover_provider": None,
                        "total_fulfillment_cost_cents": 0,
                        "net_margin_cents": line.unit_retail_price_cents * line.quantity,
                    }
                )
                continue

            item_quotes = await self.evaluate_variant_quotes(line, address)
            all_quotes.extend(item_quotes)

            in_stock_quotes = [q for q in item_quotes if q.in_stock]
            if not in_stock_quotes:
                raise ArbitrageNoStockError(
                    f"Both Printify and Printful are out of stock for variant {line.variant_id}."
                )

            primary_q = in_stock_quotes[0]
            secondary_q = in_stock_quotes[1] if len(in_stock_quotes) > 1 else None

            line_allocations.append(
                {
                    "variant_id": primary_q.variant_id,
                    "master_sku": primary_q.master_sku,
                    "quantity": line.quantity,
                    "selected_provider": primary_q.provider,
                    "selected_provider_label": primary_q.provider_label,
                    "external_variant_id": primary_q.external_variant_id,
                    "external_print_provider_id": primary_q.external_print_provider_id,
                    "failover_provider": secondary_q.provider if secondary_q else None,
                    "failover_external_variant_id": (
                        secondary_q.external_variant_id if secondary_q else None
                    ),
                    "gross_blank_cost_cents": primary_q.gross_blank_cost_cents,
                    "shipping_to_zip_cents": primary_q.shipping_to_zip_cents,
                    "volume_tier_discount_cents": primary_q.volume_tier_discount_cents,
                    "total_fulfillment_cost_cents": primary_q.total_fulfillment_cost_cents,
                    "net_margin_cents": primary_q.net_margin_cents,
                    "total_delivery_hours_est": primary_q.total_delivery_hours_est,
                }
            )

            by_prov = {q.provider: q for q in item_quotes}
            for prov_name in ("printify", "printful"):
                pq = by_prov.get(prov_name)
                if pq and pq.in_stock:
                    provider_totals[prov_name]["cost"] += pq.total_fulfillment_cost_cents
                    provider_totals[prov_name]["margin"] += pq.net_margin_cents
                    provider_totals[prov_name]["hours"] = max(
                        provider_totals[prov_name]["hours"], pq.total_delivery_hours_est
                    )
                    provider_totals[prov_name]["score"] += pq.arbitrage_utility_score
                else:
                    provider_totals[prov_name]["in_stock_all"] = 0

        # Determine order-level winner if all items are hardware vs POD
        pod_allocs = [a for a in line_allocations if a["selected_provider"] != "hardware_direct"]
        if not pod_allocs:
            return ArbitrageDecision(
                order_id=order_id,
                customer_zip=address.postal_code,
                customer_region=address.inferred_us_region,
                selected_provider="hardware_direct",
                failover_provider=None,
                selected_total_fulfillment_cost_cents=0,
                selected_net_margin_cents=sum(a["net_margin_cents"] for a in line_allocations),
                selected_delivery_hours_est=48.0,
                margin_advantage_cents=0,
                speed_advantage_hours=0.0,
                quotes_evaluated=[],
                line_allocations=line_allocations,
                rationale="Protected Bambu Lab 4.3\" Hardware SKU routed to direct hardware fulfillment.",
            )

        valid_providers = [
            p for p, stats in provider_totals.items() if stats["in_stock_all"] == 1
        ]
        if valid_providers:
            valid_providers.sort(key=lambda p: provider_totals[p]["score"], reverse=True)
            winner = valid_providers[0]
            runner_up = valid_providers[1] if len(valid_providers) > 1 else None
        else:
            # Split-order fallback if one item is only in stock at Printify and another at Printful
            winner = pod_allocs[0]["selected_provider"]
            runner_up = "printful" if winner == "printify" else "printify"

        total_cost = sum(int(a["total_fulfillment_cost_cents"]) for a in pod_allocs)
        total_margin = sum(int(a["net_margin_cents"]) for a in pod_allocs)
        est_hours = max(float(a["total_delivery_hours_est"]) for a in pod_allocs)

        if runner_up and provider_totals[runner_up]["in_stock_all"] == 1:
            margin_adv = int(provider_totals[winner]["margin"] - provider_totals[runner_up]["margin"])
            speed_adv = round(
                float(provider_totals[runner_up]["hours"] - provider_totals[winner]["hours"]), 1
            )
        else:
            margin_adv = total_margin
            speed_adv = 0.0

        rationale = (
            f"Selected {winner.upper()} for ZIP {address.postal_code} ({address.inferred_us_region}): "
            f"Fulfillment Cost=${total_cost / 100:.2f}, Net Margin=${total_margin / 100:.2f} "
            f"(+${margin_adv / 100:.2f} vs alternative), Est. Delivery={est_hours:.1f}h."
        )

        return ArbitrageDecision(
            order_id=order_id,
            customer_zip=address.postal_code,
            customer_region=address.inferred_us_region,
            selected_provider=winner,
            failover_provider=runner_up,
            selected_total_fulfillment_cost_cents=total_cost,
            selected_net_margin_cents=total_margin,
            selected_delivery_hours_est=est_hours,
            margin_advantage_cents=margin_adv,
            speed_advantage_hours=speed_adv,
            quotes_evaluated=all_quotes,
            line_allocations=line_allocations,
            rationale=rationale,
        )

    @require_punch_in(
        agent_name="Arbitrage-Fulfillment-Router",
        scope="api:pod-fulfillment",
        task_description="routing verified order to highest-margin POD provider with automatic secondary failover",
    )
    async def dispatch_order_with_failover(
        self,
        order_id: str,
        lines: List[OrderLineRequest],
        address: ShippingAddress,
    ) -> Dict[str, Any]:
        """
        Computes real-time arbitrage and submits the order to the winning provider.
        If the primary provider raises an out-of-stock or print-queue error at
        submission time, automatically fails over to the secondary provider.
        """
        decision = await self.compute_order_arbitrage(order_id, lines, address)

        if decision.selected_provider == "hardware_direct":
            result = ProviderOrderResult(
                success=True,
                provider="hardware_direct",
                external_order_id=f"hw_direct_{order_id}",
                status="SENT_TO_PRODUCTION",
                failover_triggered=False,
                attempts=[{"provider": "hardware_direct", "status": "RESERVED"}],
            )
            return {"decision": decision.to_dict(), "execution": result.to_dict()}

        primary = decision.selected_provider
        secondary = decision.failover_provider or ("printful" if primary == "printify" else "printify")
        attempts: List[Dict[str, Any]] = []

        def _build_provider_lines(target_provider: str) -> List[Dict[str, Any]]:
            payload_lines = []
            for q in decision.quotes_evaluated:
                if q.provider == target_provider:
                    payload_lines.append(
                        {
                            "variant_id": q.variant_id,
                            "external_variant_id": q.external_variant_id,
                            "external_print_provider_id": q.external_print_provider_id,
                            "quantity": q.quantity,
                        }
                    )
            return payload_lines

        # 1. Try Primary Winning Provider
        try:
            primary_lines = _build_provider_lines(primary)
            if primary == "printify":
                resp = await self.printify.submit_order(order_id, address, primary_lines)
            else:
                resp = await self.printful.submit_order(order_id, address, primary_lines)

            attempts.append(
                {
                    "provider": primary,
                    "role": "PRIMARY",
                    "status": "SUCCESS",
                    "external_order_id": resp["external_order_id"],
                }
            )
            result = ProviderOrderResult(
                success=True,
                provider=primary,
                external_order_id=resp["external_order_id"],
                status=resp["status"],
                failover_triggered=False,
                attempts=attempts,
                raw_response=resp,
            )
            return {"decision": decision.to_dict(), "execution": result.to_dict()}

        except (PrintifyQueueError, PrintfulQueueError, RuntimeError) as primary_err:
            attempts.append(
                {
                    "provider": primary,
                    "role": "PRIMARY",
                    "status": "FAILED",
                    "error": str(primary_err),
                }
            )

            # 2. Automatic Failover to Secondary Provider
            secondary_lines = _build_provider_lines(secondary)
            if not secondary_lines:
                raise ArbitrageNoStockError(
                    f"Primary provider {primary} failed ({primary_err}) and no secondary mapping exists."
                ) from primary_err

            if secondary == "printify":
                failover_resp = await self.printify.submit_order(order_id, address, secondary_lines)
            else:
                failover_resp = await self.printful.submit_order(order_id, address, secondary_lines)

            attempts.append(
                {
                    "provider": secondary,
                    "role": "SECONDARY_FAILOVER",
                    "status": "SUCCESS",
                    "external_order_id": failover_resp["external_order_id"],
                }
            )
            decision.selected_provider = secondary
            decision.rationale += (
                f" [FAILOVER EXECUTED: Primary {primary.upper()} returned '{primary_err}'; "
                f"automatically rerouted to {secondary.upper()} ({failover_resp['external_order_id']})]"
            )
            result = ProviderOrderResult(
                success=True,
                provider=secondary,
                external_order_id=failover_resp["external_order_id"],
                status=failover_resp["status"],
                failover_triggered=True,
                primary_failure_reason=str(primary_err),
                attempts=attempts,
                raw_response=failover_resp,
            )
            return {"decision": decision.to_dict(), "execution": result.to_dict()}
