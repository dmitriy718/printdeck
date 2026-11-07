# PrintDeck Phase 4 Admin Command Center


# --- Canonical Phase 4 AdminCommandCenter Bridge ---
import datetime as _dt
import json as _json
import sqlite3 as _sqlite3
import uuid as _uuid
from typing import Any as _Any, Dict as _Dict, List as _List
from ssot_engine import SSOTEngine as _SSOTEngine
from pod_orchestrator.arbitrage import SmartArbitrageRouter as _ArbitrageRouter


class AdminCommandCenter:
    def __init__(self, conn: _sqlite3.Connection) -> None:
        self.conn = conn
        self.ssot = _SSOTEngine()
        self.router = _ArbitrageRouter(conn)

    def acquire_operator_override_lock(self, scope: str, action: str) -> _Dict[str, _Any]:
        """
        Gives human operator (dima) immediate OPERATOR_OVERRIDE lock in SSOT,
        preempting autonomous agents on the target scope.
        """
        state = self.ssot.get_state()
        if scope in state.get("active_locks", {}):
            # Preempt autonomous lock for operator override
            self.ssot.punch_out(
                state["active_locks"][scope]["agent"],
                scope,
                f"yielded lock immediately to OPERATOR_OVERRIDE (dima) for: {action}",
            )
        return self.ssot.punch_in("OPERATOR_OVERRIDE (dima)", scope, action, ttl_seconds=1800)

    def release_operator_override_lock(self, scope: str, summary: str, token: str) -> _Dict[str, _Any]:
        return self.ssot.punch_out("OPERATOR_OVERRIDE (dima)", scope, summary, token=token)

    def sync_crm_360_profile(self, customer_email: str, full_name: str = "VIP Collector", utm: str = "coastalserenity_referral") -> _Dict[str, _Any]:
        orders = self.conn.execute(
            "SELECT * FROM orders WHERE customer_email = ? ORDER BY created_at DESC",
            (customer_email,),
        ).fetchall()
        ltv_cents = sum(r["total_cents"] for r in orders)
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO crm_customers
                   (email, full_name, acquisition_utm, lifetime_value_cents, orders_count, abandoned_carts_count, last_seen_utc)
                   VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (customer_email, full_name, utm, ltv_cents, len(orders), now_iso),
            )
        return {
            "email": customer_email,
            "full_name": full_name,
            "acquisition_utm": utm,
            "lifetime_value_cents": ltv_cents,
            "orders_count": len(orders),
            "order_ids": [r["id"] for r in orders],
        }

    def admin_reroute_order_provider(self, order_id: str, target_provider: str) -> _Dict[str, _Any]:
        assert target_provider in ("printify", "printful"), "Invalid POD provider"
        with self.conn:
            self.conn.execute(
                "UPDATE orders SET selected_provider = ? WHERE id = ?",
                (target_provider, order_id),
            )
        return {"order_id": order_id, "rerouted_to": target_provider, "status": "PROVIDER_OVERRIDDEN"}

    def classify_product_cohorts(self) -> _Dict[str, _List[str]]:
        """
        Categorizes all SKUs into the 4-Quadrant Cohort Matrix:
        - STAR: High traffic (>= 500 impressions) & High conversion (>= 3.0% order/click CR)
        - HIDDEN_GEM: Low traffic (< 500 impressions) & High conversion (>= 4.0% CR) -> Marketing boost
        - FIXABLE: High traffic (>= 500 impressions) & Low conversion (< 2.0% CR) -> CRO/Price test
        - CULL_CANDIDATE: >= 21 days live & 0 orders -> Queued for 301 retirement
        """
        rows = self.conn.execute("SELECT * FROM sku_telemetry").fetchall()
        matrix: _Dict[str, _List[str]] = {
            "STAR": [],
            "HIDDEN_GEM": [],
            "FIXABLE": [],
            "CULL_CANDIDATE": [],
        }
        with self.conn:
            for r in rows:
                sku = r["sku"]
                impr = r["impressions"]
                clicks = max(r["clicks"], 1)
                orders = r["orders_count"]
                days = r["days_live"]
                cr_pct = (orders / clicks) * 100.0

                if days >= 21 and orders == 0:
                    cohort = "CULL_CANDIDATE"
                elif impr >= 500 and cr_pct >= 3.0:
                    cohort = "STAR"
                elif impr < 500 and cr_pct >= 4.0 and orders > 0:
                    cohort = "HIDDEN_GEM"
                else:
                    cohort = "FIXABLE"

                matrix[cohort].append(sku)
                self.conn.execute("UPDATE sku_telemetry SET cohort = ? WHERE sku = ?", (cohort, sku))
        return matrix

    def export_prometheus_metrics(self) -> str:
        prod_count = self.conn.execute("SELECT COUNT(*) FROM products WHERE status != 'RETIRED'").fetchone()[0]
        order_row = self.conn.execute("SELECT COUNT(*), COALESCE(SUM(total_cents), 0), COALESCE(AVG(expected_margin_pct), 0) FROM orders").fetchone()
        ai_hits = self.conn.execute("SELECT bot_name, COUNT(*) as cnt FROM ai_crawler_hits GROUP BY bot_name").fetchall()
        state = self.ssot.get_state()

        lines = [
            "# HELP printdeck_active_products_total Total active non-retired SKUs on printdeck.net",
            "# TYPE printdeck_active_products_total gauge",
            f"printdeck_active_products_total {prod_count}",
            "# HELP printdeck_gmv_cents_total Gross Merchandise Value in USD cents",
            "# TYPE printdeck_gmv_cents_total counter",
            f"printdeck_gmv_cents_total {order_row[1]}",
            "# HELP printdeck_avg_margin_percent Average net margin percentage across orders",
            "# TYPE printdeck_avg_margin_percent gauge",
            f"printdeck_avg_margin_percent {order_row[2]:.2f}",
            "# HELP printdeck_ssot_active_locks Current active Redis/SSOT agent locks",
            "# TYPE printdeck_ssot_active_locks gauge",
            f"printdeck_ssot_active_locks {len(state.get('active_locks', {}))}",
        ]
        for row in ai_hits:
            lines.append(f'printdeck_ai_crawler_hits_total{{bot="{row["bot_name"]}"}} {row["cnt"]}')
        return "\n".join(lines) + "\n"
