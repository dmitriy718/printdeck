#!/usr/bin/env python3
"""
PrintDeck Phase 8 — A9 ProactiveHunter Synthetic Canary Order Guard.
Intercepts synthetic checkout probes from A1 CheckoutProber and pi-edge
(para-oob-watchdog.timer) during the 120-minute hold window and purges them
so Printify/Printful are never billed for synthetic test orders.
"""
from __future__ import annotations
import sqlite3
from typing import Any, Dict, List
from ssot_engine import require_punch_in


class A9ProactiveHunterGuard:
    CANARY_EMAIL_PATTERNS = (
        "canary@novahorizon.net",
        "prober@printdeck.net",
        "a1-checkoutprober@novahorizon.net",
        "oob-watchdog@pi-edge.local",
    )

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @require_punch_in(
        agent_name="A9-ProactiveHunter",
        scope="orders:canary-purge",
        task_description="purging A1 CheckoutProber and pi-edge synthetic canary orders before POD production submission",
    )
    def purge_synthetic_canary_orders(self) -> Dict[str, Any]:
        rows = self.conn.execute(
            "SELECT id, customer_email, stripe_session_id FROM orders WHERE status = 'PAID_GRACE_HOLD'"
        ).fetchall()
        purged_ids: List[str] = []
        with self.conn:
            for r in rows:
                email = r["customer_email"].lower()
                sess = r["stripe_session_id"].lower()
                if email in self.CANARY_EMAIL_PATTERNS or "canary" in email or sess.startswith("cs_canary_"):
                    oid = r["id"]
                    self.conn.execute("DELETE FROM fulfillment_holds WHERE order_id = ?", (oid,))
                    self.conn.execute("DELETE FROM order_items WHERE order_id = ?", (oid,))
                    self.conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
                    purged_ids.append(oid)
        return {
            "purged_count": len(purged_ids),
            "purged_order_ids": purged_ids,
            "wasted_pod_spend_cents": 0,
        }
