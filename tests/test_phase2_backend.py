#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 End-to-End Verification Suite.
Tests:
  1. PostgreSQL/SQLite Schema & Legacy Hardware Coexistence (/hardware)
  2. Dual-Provider Printify + Printful v2 Arbitrage & Automatic Failover
  3. 300-DPI Pre-Flight Pipeline (7200x10800 canvas, 3600x4800 hoodie, GPU Lease routing,
     DTG alpha halo sanitization, ICC gamut check, bleed verification, Trademark Guard)
  4. Stripe / para-paygate (:8790) Checkout, 120-Minute Editable Grace Queue,
     1-Click Post-Purchase Upsells, RFC 8058 /pay/optout, and Idempotent Webhooks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import (
    PRINTFUL_WEBHOOK_SECRET,
    PRINTIFY_WEBHOOK_SECRET,
    STRIPE_WEBHOOK_SECRET,
    app,
)
from db.database import get_db
from pod_orchestrator import OrderLineRequest, ShippingAddress, SmartArbitrageRouter
from preflight_pipeline import PreFlightPipeline, PreFlightRejectedError
from ssot_engine import SSOTEngine


client = TestClient(app)


def _sign_stripe_payload(raw_bytes: bytes, secret: str = STRIPE_WEBHOOK_SECRET) -> str:
    ts = int(time.time())
    signed = f"{ts}.".encode("utf-8") + raw_bytes
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _sign_hmac_payload(raw_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def test_health_and_legacy_hardware_coexistence() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["pod_products_count"] >= 10
    assert data["protected_hardware_offers_count"] == 3

    hw_resp = client.get("/hardware")
    assert hw_resp.status_code == 200
    hw_data = hw_resp.json()
    assert hw_data["protected_coexistence"] is True
    skus = {o["master_sku"] for o in hw_data["offers"]}
    assert {"HW-BAMBU-43-CTRL", "HW-MAKER-PACK-19", "HW-BETA-DEPOSIT-50"}.issubset(skus)


def test_300dpi_exact_dimensions_and_gpu_node_routing() -> None:
    pipeline = PreFlightPipeline()
    # 24"x36" canvas = 7200x10800 px @ 300 DPI (77.76 MP -> routed to aidev RTX 5090)
    canvas_spec = pipeline.calculate_required_pixels(24.0, 36.0, target_dpi=300, bleed_margin_in=1.5)
    assert canvas_spec.required_width_px == 7200
    assert canvas_spec.required_height_px == 10800
    assert canvas_spec.bleed_margin_px == 450
    node_canvas = pipeline.upscaler.select_compute_node(7200, 10800)
    assert node_canvas["node_name"] == "aidev"
    assert node_canvas["host"] == "100.103.12.38"

    # 12"x16" hoodie center chest = 3600x4800 px @ 300 DPI (17.28 MP -> routed to omnibook-spark)
    hoodie_spec = pipeline.calculate_required_pixels(12.0, 16.0, target_dpi=300, bleed_margin_in=0.25)
    assert hoodie_spec.required_width_px == 3600
    assert hoodie_spec.required_height_px == 4800
    node_hoodie = pipeline.upscaler.select_compute_node(3600, 4800)
    assert node_hoodie["node_name"] == "omnibook-spark"
    assert node_hoodie["host"] == "192.168.0.152"


def test_preflight_pipeline_alpha_halo_sanitizer_and_trademark_guard() -> None:
    # 1. Test DTG Hoodie Pre-Flight via FastAPI endpoint (upscaling + alpha halo removal)
    resp = client.post(
        "/api/v2/preflight/inspect",
        json={
            "title": "Cyberpunk Geometric Samurai — Original Atelier Edition",
            "description": "Original hand-drawn vector composition for heavyweight streetwear.",
            "printed_text": "PRINTDECK ATELIER MMXXVI",
            "width_in": 12.0,
            "height_in": 16.0,
            "product_id": "prod_hoodie_heavy",
            "requires_transparent_alpha": True,
            "gallery_wrap_bleed": False,
            "bleed_margin_in": 0.25,
            "image_width_px": 900,
            "image_height_px": 1200,
            "simulate_halo_noise": True,
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["asset"]["required_width_px"] == 3600
    assert result["asset"]["required_height_px"] == 4800
    assert result["asset"]["final_width_px"] == 3600
    assert result["asset"]["final_height_px"] == 4800
    assert result["asset"]["effective_dpi_x"] == 300.0
    assert result["asset"]["effective_dpi_y"] == 300.0
    assert result["asset"]["upscaled"] == 1
    assert result["asset"]["upscale_node"] == "omnibook-spark"
    assert result["alpha_telemetry"]["alpha_channel_sanitized"] is True
    assert result["alpha_telemetry"]["semi_transparent_pixels_removed"] > 0
    assert result["trademark_telemetry"]["passed"] is True

    # 2. Test Trademark/Copyright/DMCA Guard rejection
    bad_resp = client.post(
        "/api/v2/preflight/inspect",
        json={
            "title": "Official Licensed Marvel Spider-Man & Nike Air Jordan Hoodie",
            "description": "1:1 replica superhero graphic",
            "printed_text": "Marvel Studios",
            "width_in": 12.0,
            "height_in": 16.0,
            "requires_transparent_alpha": True,
        },
    )
    assert bad_resp.status_code == 422
    err = bad_resp.json()
    assert err["error"] == "PREFLIGHT_QUALITY_OR_TRADEMARK_GATE_REJECTED"
    assert "marvel" in err["detail"].lower()


@pytest.mark.asyncio
async def test_smart_arbitrage_router_and_automatic_failover() -> None:
    db = get_db()
    router = SmartArbitrageRouter(db=db)
    address = ShippingAddress(
        recipient_name="Elena Vance",
        email="elena@example.com",
        line1="400 S Tryon St",
        city="Charlotte",
        state="NC",
        postal_code="28202",
        country="US",
    )
    lines = [
        OrderLineRequest(
            variant_id="var_hoodie_blk_l",
            quantity=2,
            unit_retail_price_cents=6800,
        )
    ]

    # 1. Normal arbitrage quote evaluation
    decision = await router.compute_order_arbitrage("ord_test_arb1", lines, address)
    assert decision.selected_provider in ("printify", "printful")
    assert decision.failover_provider in ("printify", "printful")
    assert decision.selected_provider != decision.failover_provider
    assert len(decision.quotes_evaluated) == 2

    # 2. Simulate primary provider queue error -> verify automatic failover to secondary provider
    primary = decision.selected_provider
    if primary == "printify":
        router.printify.simulate_print_queue_error = True
    else:
        router.printful.simulate_print_queue_error = True

    try:
        dispatch = await router.dispatch_order_with_failover("ord_test_failover", lines, address)
        exec_res = dispatch["execution"]
        assert exec_res["success"] is True
        assert exec_res["failover_triggered"] is True
        assert exec_res["provider"] != primary
        assert len(exec_res["attempts"]) == 2
        assert exec_res["attempts"][0]["status"] == "FAILED"
        assert exec_res["attempts"][1]["status"] == "SUCCESS"
    finally:
        router.printify.simulate_print_queue_error = False
        router.printful.simulate_print_queue_error = False


def test_checkout_120m_grace_hold_edits_upsell_webhooks_and_optout() -> None:
    # 1. Create Checkout Session (/pay/checkout)
    checkout_resp = client.post(
        "/pay/checkout",
        json={
            "customer_address": {
                "recipient_name": "Marcus Sterling",
                "email": "marcus@sterling.io",
                "line1": "742 Evergreen Ter",
                "city": "Miami",
                "state": "FL",
                "postal_code": "33101",
                "country": "US",
            },
            "items": [
                {"variant_id": "var_hoodie_blk_m", "quantity": 1},
                {"variant_id": "var_canvas_24x36_wrap", "quantity": 1},
            ],
            "payment_gateway": "stripe",
            "preferred_payment_method": "apple_pay",
        },
    )
    assert checkout_resp.status_code == 200
    assert "List-Unsubscribe" in checkout_resp.headers
    assert checkout_resp.headers.get("List-Unsubscribe-Post") == "List-Unsubscribe=One-Click"

    ck_data = checkout_resp.json()
    order_id = ck_data["order_id"]
    assert ck_data["status"] == "PENDING_PAYMENT"

    # 2. Deliver signed Stripe `checkout.session.completed` webhook -> activates 120-Minute Grace Hold
    stripe_event = {
        "id": f"evt_stripe_{order_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": ck_data["stripe_checkout_session_id"],
                "client_reference_id": order_id,
                "metadata": {"order_id": order_id},
            }
        },
    }
    raw_stripe = json.dumps(stripe_event).encode("utf-8")
    sig_stripe = _sign_stripe_payload(raw_stripe)

    wh_resp = client.post(
        "/api/v2/webhooks/stripe",
        content=raw_stripe,
        headers={"Stripe-Signature": sig_stripe, "Content-Type": "application/json"},
    )
    assert wh_resp.status_code == 200
    wh_json = wh_resp.json()
    assert wh_json["processing_status"] == "PROCESSED"
    assert wh_json["grace_hold"]["status"] == "PAID_GRACE_HOLD"
    assert wh_json["grace_hold"]["grace_window_minutes"] == 120

    # 3. Verify Webhook Idempotency (replay identical Stripe event)
    wh_dup = client.post(
        "/api/v2/webhooks/stripe",
        content=raw_stripe,
        headers={"Stripe-Signature": sig_stripe, "Content-Type": "application/json"},
    )
    assert wh_dup.status_code == 200
    assert wh_dup.json()["processing_status"] == "DUPLICATE_IGNORED"

    # 4. Edit order during 120-minute grace window (fix address typo + swap Hoodie M -> L)
    order_details = client.get(f"/api/v2/orders/{order_id}").json()
    hoodie_item = next(
        i for i in order_details["items"] if i["variant_id"] == "var_hoodie_blk_m"
    )
    edit_resp = client.patch(
        f"/api/v2/orders/{order_id}/grace-edit",
        json={
            "agent_name": "AI-Concierge",
            "updated_address": {
                "recipient_name": "Marcus Sterling",
                "email": "marcus@sterling.io",
                "line1": "888 Brickell Ave Suite 1200",
                "city": "Miami",
                "state": "FL",
                "postal_code": "33131",
                "country": "US",
            },
            "variant_swaps": [
                {
                    "order_item_id": hoodie_item["order_item_id"],
                    "new_variant_id": "var_hoodie_blk_l",
                }
            ],
        },
    )
    assert edit_resp.status_code == 200
    edit_data = edit_resp.json()
    assert len(edit_data["edits_applied"]) == 2

    # 5. Accept 1-Click Post-Purchase Bundle Upsell during grace window
    upsell_resp = client.post(
        f"/api/v2/orders/{order_id}/upsell",
        json={
            "variant_id": "var_decal_6x6_std",
            "quantity": 1,
            "upsell_discount_bps": 2000,
        },
    )
    assert upsell_resp.status_code == 200
    assert upsell_resp.json()["discounted_unit_price_cents"] == 960  # 20% off $12.00

    # 6. Release 120-Minute Grace Hold -> Dispatch to Printify / Printful
    rel_resp = client.post(f"/api/v2/orders/{order_id}/release-hold?fast_track=true")
    assert rel_resp.status_code == 200
    rel_data = rel_resp.json()
    assert rel_data["status"] == "SENT_TO_PRODUCTION"
    ext_pod_id = rel_data["external_pod_order_id"]
    selected_provider = rel_data["selected_provider"]

    # 7. Deliver signed Printify/Printful lifecycle webhooks (shipment created + delivered + on-hold)
    pod_secret = (
        PRINTIFY_WEBHOOK_SECRET if selected_provider == "printify" else PRINTFUL_WEBHOOK_SECRET
    )
    pod_header_name = (
        "X-Printify-Signature" if selected_provider == "printify" else "X-PF-Webhook-Signature"
    )
    ship_payload = json.dumps(
        {
            "id": f"evt_ship_{order_id}",
            "type": "order:shipment:created",
            "resource": {
                "id": ext_pod_id,
                "order_id": order_id,
                "tracking_number": "1Z999AA10123456784",
                "tracking_url": "https://ups.com/track?num=1Z999AA10123456784",
                "carrier": "UPS Ground",
            },
        }
    ).encode("utf-8")
    ship_sig = _sign_hmac_payload(ship_payload, pod_secret)
    ship_wh = client.post(
        f"/api/v2/webhooks/{selected_provider}",
        content=ship_payload,
        headers={pod_header_name: ship_sig, "Content-Type": "application/json"},
    )
    assert ship_wh.status_code == 200
    assert ship_wh.json()["new_order_status"] == "SHIPPED"

    # Test order:on-hold -> auto-creates para-intake ticket
    hold_payload = json.dumps(
        {
            "id": f"evt_hold_{order_id}",
            "type": "order:on-hold",
            "resource": {
                "id": ext_pod_id,
                "order_id": order_id,
                "reason": "Carrier address apartment number confirmation requested",
            },
        }
    ).encode("utf-8")
    hold_sig = _sign_hmac_payload(hold_payload, pod_secret)
    hold_wh = client.post(
        f"/api/v2/webhooks/{selected_provider}",
        content=hold_payload,
        headers={pod_header_name: hold_sig, "Content-Type": "application/json"},
    )
    assert hold_wh.status_code == 200
    assert hold_wh.json()["new_order_status"] == "ON_HOLD"
    assert hold_wh.json()["intake_ticket_id"].startswith("tkt_")

    # 8. Test RFC 8058 1-Click Unsubscribe (/pay/optout)
    opt_resp = client.post("/pay/optout?email=marcus@sterling.io&token=tok_test_rfc8058")
    assert opt_resp.status_code == 200
    assert opt_resp.json()["rfc8058_one_click_verified"] is True

    final_order = client.get(f"/api/v2/orders/{order_id}").json()
    assert final_order["marketing_opt_out"] == 1
    assert final_order["tracking_number"] == "1Z999AA10123456784"
    assert final_order["intake_ticket_id"].startswith("tkt_")
