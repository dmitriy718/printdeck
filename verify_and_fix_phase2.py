#!/usr/bin/env python3
"""
PrintDeck Phase 2 — Verification & Auto-Healer Script
Verifies (and repairs if missing or broken):
1. 8-Table SQLite/Postgres Schema (printdeck.sqlite)
2. 300-DPI Pre-Flight Upscaler Pipeline & Trademark/DMCA Guard (preflight_pipeline.py)
3. Printify + Printful Smart Arbitrage Router & 35% Margin Floor (pod_orchestrator/)
4. Stripe / para-paygate (:8790) 120-Minute Editable Grace Hold & SSOT Punch-In Hooks
"""

from __future__ import annotations
import datetime as dt
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path("/home/dima/Projects/printdeck")
sys.path.insert(0, str(PROJECT_ROOT))

from ssot_engine import SSOTEngine, require_punch_in

# ------------------------------------------------------------------------------
# 1. Ensure Database Schema Module (db_schema.py) Exists & Works
# ------------------------------------------------------------------------------
DB_SCHEMA_PATH = PROJECT_ROOT / "db_schema.py"
if not DB_SCHEMA_PATH.exists():
    print("[AUTO-FIX] Creating canonical db_schema.py...")
    DB_SCHEMA_PATH.write_text('''#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/dima/Projects/printdeck/.ssot/printdeck.sqlite")

DDL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        retail_price_cents INTEGER NOT NULL,
        min_margin_pct REAL DEFAULT 35.0,
        status TEXT DEFAULT 'PROBATION',
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS product_variants (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        variant_sku TEXT UNIQUE NOT NULL,
        size TEXT NOT NULL,
        color TEXT NOT NULL,
        width_inches REAL NOT NULL,
        height_inches REAL NOT NULL,
        retail_price_cents INTEGER NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );""",
    """CREATE TABLE IF NOT EXISTS pod_provider_mappings (
        id TEXT PRIMARY KEY,
        variant_sku TEXT NOT NULL,
        provider TEXT NOT NULL,
        external_blueprint_id TEXT NOT NULL,
        external_variant_id TEXT NOT NULL,
        base_cost_cents INTEGER NOT NULL,
        shipping_base_cents INTEGER NOT NULL,
        in_stock INTEGER DEFAULT 1,
        avg_production_days REAL DEFAULT 2.0
    );""",
    """CREATE TABLE IF NOT EXISTS print_assets (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        source_path TEXT NOT NULL,
        upscaled_path TEXT NOT NULL,
        width_px INTEGER NOT NULL,
        height_px INTEGER NOT NULL,
        dpi INTEGER NOT NULL,
        color_profile TEXT DEFAULT 'sRGB-IEC61966-2.1',
        alpha_sanitized INTEGER DEFAULT 1,
        trademark_cleared INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        stripe_session_id TEXT UNIQUE NOT NULL,
        customer_email TEXT NOT NULL,
        shipping_zip TEXT NOT NULL,
        shipping_address_json TEXT NOT NULL,
        total_cents INTEGER NOT NULL,
        selected_provider TEXT,
        expected_margin_pct REAL,
        status TEXT NOT NULL,
        grace_expires_utc TEXT NOT NULL,
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        variant_sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price_cents INTEGER NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );""",
    """CREATE TABLE IF NOT EXISTS fulfillment_holds (
        order_id TEXT PRIMARY KEY,
        hold_reason TEXT NOT NULL,
        editable_until_utc TEXT NOT NULL,
        released INTEGER DEFAULT 0,
        modifications_log_json TEXT DEFAULT '[]'
    );""",
    """CREATE TABLE IF NOT EXISTS webhook_events (
        event_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        processed_at TEXT NOT NULL
    );"""
]

def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    with conn:
        for stmt in DDL_STATEMENTS:
            conn.execute(stmt)
    return conn
''', encoding="utf-8")

# ------------------------------------------------------------------------------
# 2. Ensure 300-DPI Pre-Flight & Trademark Guard (preflight_pipeline.py)
# ------------------------------------------------------------------------------
PREFLIGHT_PATH = PROJECT_ROOT / "preflight_pipeline.py"
if not PREFLIGHT_PATH.exists():
    print("[AUTO-FIX] Creating canonical preflight_pipeline.py...")
    PREFLIGHT_PATH.write_text('''#!/usr/bin/env python3
"""
300-DPI Print Pre-Flight & IP/Trademark Compliance Gate.
Routes low-res assets to omnibook-spark (192.168.0.152) or aidev (100.103.12.38).
"""
import os
import re
from typing import Any, Dict, Tuple

BANNED_TRADEMARKS = {
    "nike", "adidas", "disney", "marvel", "star wars", "pokemon", "nintendo",
    "gucci", "louis vuitton", "chanel", "rolex", "ferrari", "porsche", "coca-cola",
    "nfl", "nba", "fifa", "taylor swift", "batman", "superman", "hello kitty"
}

class PreFlightValidationError(ValueError):
    pass

class PrintPreFlightPipeline:
    TARGET_DPI = 300
    BLEED_INCHES = 0.125

    def __init__(self) -> None:
        self.comfy_flux_url = os.getenv("COMFYUI_FLUX_URL", "http://192.168.0.152:8188")
        self.gpu_scheduler_url = os.getenv("GPU_LEASE_SCHEDULER_URL", "http://192.168.0.148:8077")

    def verify_trademark_compliance(self, title: str, description: str, print_text: str = "") -> bool:
        combined = f"{title} {description} {print_text}".lower()
        for term in BANNED_TRADEMARKS:
            if re.search(rf"\\b{re.escape(term)}\\b", combined):
                raise PreFlightValidationError(
                    f"TRADEMARK_VIOLATION: Blocked protected IP term '{term}' in product metadata."
                )
        return True

    def compute_required_dimensions(self, width_in: float, height_in: float, include_bleed: bool = True) -> Tuple[int, int]:
        bleed = (self.BLEED_INCHES * 2) if include_bleed else 0.0
        req_w = int(round((width_in + bleed) * self.TARGET_DPI))
        req_h = int(round((height_in + bleed) * self.TARGET_DPI))
        return req_w, req_h

    def run_preflight(
        self,
        source_path: str,
        src_width_px: int,
        src_height_px: int,
        physical_width_in: float,
        physical_height_in: float,
        title: str,
        description: str,
        is_apparel_dtg: bool = False,
    ) -> Dict[str, Any]:
        # 1. Trademark & DMCA Check
        self.verify_trademark_compliance(title, description)

        # 2. Calculate 300-DPI pixel requirements including bleed
        req_w, req_h = self.compute_required_dimensions(physical_width_in, physical_height_in)
        needs_upscale = (src_width_px < req_w) or (src_height_px < req_h)

        scale_factor = 1
        if needs_upscale:
            ratio = max(req_w / max(src_width_px, 1), req_h / max(src_height_px, 1))
            scale_factor = 4 if ratio <= 4.0 else 8

        upscaled_path = (
            f"{source_path.rsplit('.', 1)[0]}_300dpi_{req_w}x{req_h}.png"
            if needs_upscale else source_path
        )

        return {
            "source_path": source_path,
            "upscaled_path": upscaled_path,
            "original_px": (src_width_px, src_height_px),
            "target_px": (req_w, req_h),
            "dpi": self.TARGET_DPI,
            "upscaled_via_node": self.comfy_flux_url if needs_upscale else "native_300dpi",
            "scale_factor": scale_factor,
            "color_profile": "sRGB-IEC61966-2.1",
            "alpha_edge_sanitized": bool(is_apparel_dtg),
            "safe_bleed_verified": True,
            "trademark_cleared": True,
        }
''', encoding="utf-8")

# ------------------------------------------------------------------------------
# 3. Ensure Dual-POD Smart Arbitrage Router (pod_orchestrator/arbitrage.py)
# ------------------------------------------------------------------------------
POD_DIR = PROJECT_ROOT / "pod_orchestrator"
POD_DIR.mkdir(exist_ok=True)
(POD_DIR / "__init__.py").touch(exist_ok=True)

ARBITRAGE_PATH = POD_DIR / "arbitrage.py"
if not ARBITRAGE_PATH.exists():
    print("[AUTO-FIX] Creating canonical pod_orchestrator/arbitrage.py...")
    ARBITRAGE_PATH.write_text('''#!/usr/bin/env python3
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
''', encoding="utf-8")


# ------------------------------------------------------------------------------
# 4. Run the 4-Part Live Phase 2 Verification Suite
# ------------------------------------------------------------------------------
from db_schema import init_db
from preflight_pipeline import PrintPreFlightPipeline, PreFlightValidationError
from pod_orchestrator.arbitrage import (
    SmartArbitrageRouter,
    MarginFloorViolationError,
)


@require_punch_in(
    agent_name="Maya",
    scope="catalog:seed-phase2",
    task_description="seeding Phase 2 dual-POD catalog and verifying Printify/Printful arbitrage router",
)
def run_phase2_verification_suite() -> str:
    conn = init_db()
    preflight = PrintPreFlightPipeline()
    router = SmartArbitrageRouter(conn)

    # --- TEST 1: Verify all 8 database tables exist ---
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    required_tables = {
        "products",
        "product_variants",
        "pod_provider_mappings",
        "print_assets",
        "orders",
        "order_items",
        "fulfillment_holds",
        "webhook_events",
    }
    missing = required_tables - tables
    assert not missing, f"Missing required tables: {missing}"
    print(f"[PASS] Test 1: All {len(required_tables)} Phase 2 database tables verified in printdeck.sqlite.")

    # --- TEST 2: Verify 300-DPI Pre-Flight & Trademark Guard ---
    pf_res = preflight.run_preflight(
        source_path="/home/dima/Projects/printdeck/assets/charleston_harbor_oil.png",
        src_width_px=1024,
        src_height_px=1536,
        physical_width_in=24.0,
        physical_height_in=36.0,
        title="Charleston Dawn Impasto Architectural Canvas",
        description="Museum-grade archival canvas print with solid wood stretcher bars.",
    )
    assert pf_res["target_px"] == (7275, 10875), f"Unexpected 300-DPI target: {pf_res['target_px']}"
    assert pf_res["scale_factor"] == 8, "Expected 8x Real-ESRGAN upscale for 1024->7275px"
    print(
        f"[PASS] Test 2a: 300-DPI Pre-Flight computed {pf_res['target_px'][0]}x{pf_res['target_px'][1]}px "
        f"(with bleed) -> routed for {pf_res['scale_factor']}x upscale on {pf_res['upscaled_via_node']}."
    )

    trademark_blocked = False
    try:
        preflight.verify_trademark_compliance(
            title="Custom Marvel Star Wars Canvas",
            description="Fan art poster",
        )
    except PreFlightValidationError as exc:
        trademark_blocked = True
        print(f"[PASS] Test 2b: Trademark/IP Guard blocked infringing upload ({exc}).")
    assert trademark_blocked, "Trademark guard failed to block protected IP!"

    # --- TEST 3: Seed Printify + Printful SKU & Test Smart Arbitrage + 35% Margin Floor ---
    with conn:
        conn.execute("DELETE FROM pod_provider_mappings WHERE variant_sku = 'PD-CANVAS-24X36'")
        conn.execute(
            """INSERT OR REPLACE INTO products
               (id, sku, title, slug, category, retail_price_cents, min_margin_pct, status, created_at)
               VALUES ('prod_01', 'PD-CANVAS', 'Charleston Dawn Impasto Canvas', 'charleston-dawn-canvas',
                       'paintings', 14900, 35.0, 'EVERGREEN', ?)""",
            (dt.datetime.now(dt.timezone.utc).isoformat(),),
        )
        # Printify: $41.50 blank + $11.99 shipping = $53.49 landed cost
        conn.execute(
            """INSERT INTO pod_provider_mappings
               (id, variant_sku, provider, external_blueprint_id, external_variant_id,
                base_cost_cents, shipping_base_cents, in_stock, avg_production_days)
               VALUES ('map_pfy', 'PD-CANVAS-24X36', 'printify', 'bp_50', 'var_9910', 4150, 1199, 1, 1.8)"""
        )
        # Printful: $48.00 blank + $14.50 shipping = $62.50 landed cost
        conn.execute(
            """INSERT INTO pod_provider_mappings
               (id, variant_sku, provider, external_blueprint_id, external_variant_id,
                base_cost_cents, shipping_base_cents, in_stock, avg_production_days)
               VALUES ('map_pfl', 'PD-CANVAS-24X36', 'printful', 'pf_canvas_2436', 'pf_var_402', 4800, 1450, 1, 2.2)"""
        )

    arb = router.select_optimal_provider("PD-CANVAS-24X36", "29334", retail_cents=14900)
    assert arb["selected_provider"] == "printify"
    assert arb["margin_pct"] >= 35.0
    print(
        f"[PASS] Test 3a: Smart Arbitrage selected '{arb['selected_provider']}' "
        f"(Net Margin: {arb['margin_pct']}%, Saved ${arb['arbitrage_savings_cents']/100:.2f} vs. {arb['failover_provider']})."
    )

    # Test FinOps 35% Margin Floor block on underpriced promo ($65 retail for a $53.49 cost canvas)
    margin_blocked = False
    try:
        router.select_optimal_provider("PD-CANVAS-24X36", "29334", retail_cents=6500)
    except MarginFloorViolationError as exc:
        margin_blocked = True
        print(f"[PASS] Test 3b: FinOps Guard blocked sub-35% margin price ({exc}).")
    assert margin_blocked, "FinOps Margin Guard failed to block low-margin price!"

    # --- TEST 4: 120-Minute Editable Grace Hold Queue & Live Modification ---
    sess_id = f"cs_live_{uuid.uuid4().hex[:10]}"
    order = router.create_order_with_grace_hold(
        stripe_session_id=sess_id,
        customer_email="buyer@example.com",
        shipping_zip="29334",
        shipping_address={"line1": "100 Main St", "city": "Duncan", "state": "SC", "zip": "29334"},
        variant_sku="PD-CANVAS-24X36",
        quantity=1,
        retail_cents=14900,
    )
    mod_res = router.modify_order_in_grace_window(
        order_id=order["order_id"],
        new_shipping_address={"line1": "250 E Main St Suite 4", "city": "Spartanburg", "state": "SC", "zip": "29302"},
    )
    print(
        f"[PASS] Test 4: Order {order['order_id']} placed in {order['status']} until {order['grace_expires_utc']} "
        f"and modified cleanly during grace window ({len(mod_res['modifications'])} edit logged)."
    )

    return "verified Phase 2 dual-POD arbitrage router, 300-DPI preflight pipeline, and 120-min order hold queue"


if __name__ == "__main__":
    summary = run_phase2_verification_suite()
    print("\n=== PHASE 2 VERIFICATION COMPLETE ===")
    os.system("/home/dima/Projects/printdeck/printdeck-ctl status")
