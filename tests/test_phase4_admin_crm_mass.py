#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 4 Executive Administration Portal, Mass Uploader,
360° CRM, SEO/FinOps Dashboard, Live SSOT WebSocket & Prometheus/ntfy Verification Suite.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from fastapi.testclient import TestClient

from admin_portal import ADMIN_API_KEY
from app import app
from mass_uploader_worker import MassUploaderWorker
from ssot_engine import SSOTEngine

client = TestClient(app)

AUTH_HEADERS_API_KEY = {"X-PrintDeck-Admin-Key": ADMIN_API_KEY}
AUTH_HEADERS_AUTHELIA = {
    "Remote-User": "dima",
    "Remote-Groups": "admins,lldap_admin",
    "Remote-Email": "dima@printdeck.net",
}


def test_admin_auth_authelia_lldap_and_operator_override_preemption() -> None:
    # 1. Unauthenticated request must be rejected with 401
    unauth = client.get("/api/v2/admin/ssot/live")
    assert unauth.status_code == 401

    # 2. Authelia user without admin group must be rejected with 403
    bad_group = client.get(
        "/api/v2/admin/ssot/live",
        headers={"Remote-User": "guest", "Remote-Groups": "viewers"},
    )
    assert bad_group.status_code == 403

    # 3. Valid Authelia + LLDAP headers succeed on /admin UI
    ui_resp = client.get("/admin", headers=AUTH_HEADERS_AUTHELIA)
    assert ui_resp.status_code == 200
    assert "PrintDeck Executive Command Center" in ui_resp.text

    # 4. Verify OPERATOR_OVERRIDE preempts an active autonomous agent lock
    engine = SSOTEngine()
    engine.punch_in(
        agent_name="Autonomous-Catalog-Bot",
        scope="admin:test-preempt-scope",
        task_description="running background catalog optimization",
    )
    preempt_resp = client.post(
        "/api/v2/admin/ssot/preempt",
        headers=AUTH_HEADERS_API_KEY,
        json={
            "scope": "admin:test-preempt-scope",
            "task_description": "Operator dima manual override in /admin",
        },
    )
    assert preempt_resp.status_code == 200
    lock_info = preempt_resp.json()["lock"]
    assert lock_info["priority"] == "OPERATOR_OVERRIDE"
    assert lock_info["preempted_agent"] == "agent Autonomous-Catalog-Bot"

    # Release the test operator lock cleanly
    engine.punch_out(
        agent_name="agent OPERATOR_OVERRIDE(dima)",
        scope="admin:test-preempt-scope",
        resolution_summary="Finished manual operator override verification",
        token=lock_info["token"],
    )


def test_inline_product_editor_and_450_variant_mass_matrix_uploader() -> None:
    # 1. Inline Product Editor (override provider routing & price)
    patch_resp = client.patch(
        "/api/v2/admin/products/PD-CANVAS-24X36",
        headers=AUTH_HEADERS_AUTHELIA,
        json={
            "base_retail_price_cents": 15500,
            "preferred_provider_override": "printful",
            "margin_floor_pct": 42.0,
        },
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "UPDATED_WITH_OPERATOR_OVERRIDE"
    assert patch_data["base_retail_price_cents"] == 15500
    assert patch_data["metadata"]["preferred_provider_override"] == "printful"

    # Restore base price to 14900
    client.patch(
        "/api/v2/admin/products/PD-CANVAS-24X36",
        headers=AUTH_HEADERS_API_KEY,
        json={"base_retail_price_cents": 14900, "preferred_provider_override": "printify"},
    )

    # 2. Verify 50-Artwork Matrix Projection = 450 variants (3 canvas + 5 tees + 1 mug = 9 * 50)
    proj = MassUploaderWorker.calculate_matrix_projection(
        artworks_count=50,
        selected_templates=[
            "stretched_canvas_3_sizes",
            "heavyweight_oversized_tee_5_colors",
            "ceramic_mug_15oz",
        ],
    )
    assert proj["variants_per_artwork"] == 9
    assert proj["total_variants_to_create"] == 450

    # 3. Execute Mass Upload Batch with 50 AI prompts -> 450 variants created
    fifty_prompts = [f"Atelier Brutalist Monolith Series #{i:02d}" for i in range(1, 51)]
    mass_resp = client.post(
        "/api/v2/admin/mass-upload",
        headers=AUTH_HEADERS_API_KEY,
        json={
            "source_format": "ai_prompts",
            "payload": fifty_prompts,
            "selected_templates": [
                "stretched_canvas_3_sizes",
                "heavyweight_oversized_tee_5_colors",
                "ceramic_mug_15oz",
            ],
            "persist_all_db_rows": False,
        },
    )
    assert mass_resp.status_code == 200
    mass_data = mass_resp.json()
    assert mass_data["artworks_ingested"] == 50
    assert mass_data["variants_per_artwork"] == 9
    assert mass_data["total_variants_created"] == 450
    assert mass_data["status"] == "COMPLETED"
    assert mass_data["progress_pct"] == 100.0

    # 4. Also verify ZIP archive ingestion format
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("collection_a/obsidian_solstice.png", b"fake_png_header")
        zf.writestr("collection_b/kinetic_horizon.png", b"fake_png_header")
    b64_zip = base64.b64encode(zip_buf.getvalue()).decode("ascii")
    parsed_zip = MassUploaderWorker.parse_bulk_source("zip", b64_zip)
    assert len(parsed_zip) == 2
    assert parsed_zip[0]["title"] == "Obsidian Solstice"


def test_crm_360_profiles_and_1_click_order_interventions() -> None:
    # Create an order to intervene on
    ck_resp = client.post(
        "/pay/checkout",
        json={
            "customer_address": {
                "recipient_name": "Victoria Sterling",
                "email": "marcus@sterling.io",
                "line1": "888 Brickell Ave",
                "city": "Miami",
                "state": "FL",
                "postal_code": "33131",
                "country": "US",
            },
            "items": [
                {"variant_id": "var_canvas_24x36_wrap", "quantity": 2},
            ],
            "payment_gateway": "stripe",
            "preferred_payment_method": "card",
        },
    )
    assert ck_resp.status_code == 200
    order_id = ck_resp.json()["order_id"]

    # 1. Fetch 360° Customer CRM profiles
    crm_resp = client.get("/api/v2/admin/crm/customers", headers=AUTH_HEADERS_API_KEY)
    assert crm_resp.status_code == 200
    crm_data = crm_resp.json()
    assert crm_data["customers_count"] >= 1
    marcus = next(c for c in crm_data["customers"] if c["email"] == "marcus@sterling.io")
    assert marcus["lifetime_value_cents"] >= 29800
    assert len(marcus["ai_concierge_transcripts"]) >= 1

    # 2. Test 1-Click Intervention: HOLD_GRACE_WINDOW
    r_hold = client.post(
        f"/api/v2/admin/orders/{order_id}/intervene",
        headers=AUTH_HEADERS_API_KEY,
        json={"action": "HOLD_GRACE_WINDOW"},
    )
    assert r_hold.status_code == 200
    assert r_hold.json()["new_status"] == "PAID_GRACE_HOLD"

    # 3. Test 1-Click Intervention: REROUTE_PROVIDER
    r_reroute = client.post(
        f"/api/v2/admin/orders/{order_id}/intervene",
        headers=AUTH_HEADERS_API_KEY,
        json={"action": "REROUTE_PROVIDER", "target_provider": "printful"},
    )
    assert r_reroute.status_code == 200
    assert r_reroute.json()["new_provider"] == "printful"

    # 4. Test 1-Click Intervention: REPLACEMENT_REPRINT
    r_repl = client.post(
        f"/api/v2/admin/orders/{order_id}/intervene",
        headers=AUTH_HEADERS_API_KEY,
        json={"action": "REPLACEMENT_REPRINT", "reason": "Damaged frame corner in UPS transit"},
    )
    assert r_repl.status_code == 200
    assert r_repl.json()["customer_charge_cents"] == 0
    assert r_repl.json()["replacement_order_number"].startswith("PD-REPL-")

    # 5. Test 1-Click Intervention: STRIPE_REFUND
    r_ref = client.post(
        f"/api/v2/admin/orders/{order_id}/intervene",
        headers=AUTH_HEADERS_API_KEY,
        json={"action": "STRIPE_REFUND"},
    )
    assert r_ref.status_code == 200
    assert r_ref.json()["new_status"] == "REFUNDED"


def test_finops_seo_cohort_matrix_ssot_websocket_and_prometheus_ntfy() -> None:
    # 1. FinOps Telemetry
    fin_resp = client.get("/api/v2/admin/telemetry/finops", headers=AUTH_HEADERS_API_KEY)
    assert fin_resp.status_code == 200
    fin = fin_resp.json()["finops"]
    assert "gmv_cents" in fin
    assert "arbitrage_savings_cents" in fin

    # 2. SEO / GEO & AI Crawler Hits Telemetry
    seo_resp = client.get("/api/v2/admin/telemetry/seo-geo", headers=AUTH_HEADERS_API_KEY)
    assert seo_resp.status_code == 200
    seo_data = seo_resp.json()
    assert seo_data["core_web_vitals"]["cls_score"] == 0.0
    bots = {h["bot_name"] for h in seo_data["ai_crawler_recent_hits"]}
    assert {"GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"}.issubset(bots)

    # 3. 4-Quadrant Product Cohort Matrix
    cohort_resp = client.get("/api/v2/admin/telemetry/cohort-matrix", headers=AUTH_HEADERS_API_KEY)
    assert cohort_resp.status_code == 200
    matrix = cohort_resp.json()["matrix"]
    assert set(matrix.keys()) == {"STAR", "HIDDEN GEM", "FIXABLE", "CULL CANDIDATE"}
    assert len(matrix["STAR"]) >= 1
    assert len(matrix["HIDDEN GEM"]) >= 1

    # 4. Live SSOT WebSocket & Board Room Proposal Override
    with client.websocket_connect("/api/v2/admin/ws/ssot") as ws:
        snap = ws.receive_json()
        assert snap["event"] == "SSOT_LIVE_SNAPSHOT"
        assert "ssot_state" in snap
        assert len(snap["boardroom_proposals"]) >= 2
        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["event"] == "SSOT_PONG"

    br_resp = client.post(
        "/api/v2/admin/boardroom/proposals/prop_br_001/decide",
        headers=AUTH_HEADERS_AUTHELIA,
        json={"decision": "OPERATOR_APPROVED", "notes": "Approved for Q4 West Coast Canvas SLA"},
    )
    assert br_resp.status_code == 200
    assert br_resp.json()["status"] == "OPERATOR_APPROVED"

    # 5. Prometheus `/metrics` Exporter & `ntfy` (:2586) High-Value Order Alert
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert "printdeck_gmv_cents_total" in metrics_resp.text
    assert "printdeck_arbitrage_savings_cents_total" in metrics_resp.text
    assert 'printdeck_ai_crawler_hits_total{bot="GPTBot"}' in metrics_resp.text

    # Trigger ntfy alert on a high-value order ($298.00+)
    hv_ck = client.post(
        "/pay/checkout",
        json={
            "customer_address": {
                "recipient_name": "High Value Collector",
                "email": "vip@printdeck.net",
                "line1": "100 Park Ave",
                "city": "New York",
                "state": "NY",
                "postal_code": "10017",
                "country": "US",
            },
            "items": [{"variant_id": "var_canvas_24x36_wrap", "quantity": 2}],
        },
    ).json()
    ntfy_resp = client.post(
        f"/api/v2/admin/alerts/evaluate-order/{hv_ck['order_id']}",
        headers=AUTH_HEADERS_API_KEY,
    )
    assert ntfy_resp.status_code == 200
    ntfy_data = ntfy_resp.json()
    assert ntfy_data["alerts_triggered_count"] >= 1
    assert ntfy_data["alerts"][0]["metadata"]["alert_type"] == "HIGH_VALUE_ORDER"
