#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 7 Growth, Cross-Portfolio Publicist &
Autonomous Mailer / `para-intake` (:8787) Verification Suite
(`tests/test_phase7_growth_mailer_syndication.py`).

Tests:
  1. `Agent Aria` (`agent_marketing_aria.py`): High-AOV Bundle Architect (with `Agent Lucas`
     35% margin clearance + Board quorum on >15% discounts), B2B Landing Pages, and UCB1 Bandit CRO.
  2. `Agent Julian` (`agent_publicist_julian.py`) & `CrossPortfolioPublisher` (`cross_portfolio_publisher.py`):
     Cluster A, B, and C editorial syndication across all Para Investments domains with SSOT
     Punch-In protection, HTTP 200 verification, XML sitemap regeneration, and Social/PR packs.
  3. `Agent Clara` (`agent_mailer_clara.py`) & `email_templates.py`: Pre-send `RCPT TO` &
     RFC 8058 `/pay/optout` compliance, 3-Stage Abandoned Cart Recovery (`T30M`, `T6H`, `T24H`),
     Post-Purchase Lifecycle flows, and `para-intake.service` (`:8787`) autonomous support &
     photo-verified damage replacement orders.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest

from agent_mailer_clara import MailerAgentClara
from agent_marketing_aria import MarketingAgentAria
from agent_publicist_julian import PublicistAgentJulian
from boardroom_engine import BoardProposal, BoardRoomEngine
from db.database import DatabaseManager
from playwright_verifier import BoardResolutionRequiredError
from ssot_engine import SSOTEngine


def _make_phase7_env(tmp_path: Path) -> tuple[SSOTEngine, DatabaseManager]:
    ssot_md = tmp_path / "SOURCE_OF_TRUTH.md"
    state_dir = tmp_path / ".ssot"
    growth_dir = tmp_path / "growth"
    growth_dir.mkdir(parents=True, exist_ok=True)

    ssot = SSOTEngine(
        ssot_md_path=ssot_md,
        state_dir=state_dir,
        herdr_growth_dir=growth_dir,
    )
    db = DatabaseManager(
        db_path=state_dir / "test_phase7.sqlite",
        paygate_db_path=state_dir / "test_paygate.sqlite",
        intake_db_path=state_dir / "test_intake.sqlite",
    )
    return ssot, db


@pytest.mark.asyncio
async def test_agent_aria_bundles_lucas_clearance_and_bandit_landing_pages(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase7_env(tmp_path)
    aria = MarketingAgentAria(
        ssot=ssot,
        db=db,
        landing_pages_dir=tmp_path / "dist_landing",
    )

    # 1. 14% discount bundle (<= 15%) executes directly with Agent Lucas >=35% net margin clearance
    b_coastal = await aria.create_margin_cleared_bundle(
        blueprint_key="coastal_atelier_sanctuary_trio"
    )
    assert b_coastal["discount_pct"] == 14.0
    assert b_coastal["lucas_finops_cleared"] is True
    assert b_coastal["net_margin_pct"] >= 35.0

    # 2. 18% discount bundle ("The Quant Trader Desk Setup ... Save 18%") requires Board Resolution Token
    with pytest.raises(BoardResolutionRequiredError):
        await aria.create_margin_cleared_bundle(
            blueprint_key="quant_trader_desk_setup",
            board_resolution_token=None,
        )

    board = BoardRoomEngine(ssot=ssot, db=db)
    res = await board.deliberate_proposal(
        BoardProposal(
            proposal_id="PROP-P7-QUANT-BUNDLE",
            title="Launch Quant Trader Desk Setup Bundle at 18% Discount",
            proposing_agent="Agent Aria",
            scope="growth:marketing-specialist:bundle-bnd_quant_trader_desk",
            category="discount_promo",
            hypothesis="Bundling Framed Canvas + XXL Desk Mat + 15oz Mug lifts AOV above $210 while preserving >52% net margin.",
            expected_roi_impact="+$42 AOV lift",
            rollback_plan="Revert bundle_price_cents to regular sum in product_bundles.",
            projected_gross_margin_pct=54.5,
            proposed_discount_pct=18.0,
        )
    )
    assert res.quorum_reached is True

    b_quant = await aria.create_margin_cleared_bundle(
        blueprint_key="quant_trader_desk_setup",
        board_resolution_token=res.board_resolution_token,
    )
    assert b_quant["discount_pct"] == 18.0
    assert b_quant["lucas_finops_cleared"] is True
    assert b_quant["net_margin_pct"] >= 35.0

    # 3. Deploy B2B Swag Landing Page & run Multi-Armed Bandit CRO optimization
    lp = await aria.deploy_campaign_landing_page_and_bandit(
        route_prefix="custom-corporate-swag",
        slug="remote-engineering-agency-gift-boxes",
    )
    assert lp["route_path"] == "/custom-corporate-swag/remote-engineering-agency-gift-boxes"
    assert Path(lp["html_path"]).exists()
    assert lp["bandit_winner"]["arm_id"] == "arm_a_precision_atelier"


@pytest.mark.asyncio
async def test_agent_julian_cross_portfolio_syndication_and_social_pr_pack(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase7_env(tmp_path)
    webroot = tmp_path / "var_www"
    julian = PublicistAgentJulian(
        ssot=ssot,
        db=db,
        webroot_base_dir=webroot,
    )

    # 1. Syndicate across Clusters C, B, and A
    synd = await julian.syndicate_across_all_portfolio_clusters()
    assert synd["articles_published_count"] == 9  # 1 (Cluster C) + 3 (Cluster B) + 5 (Cluster A)
    assert synd["all_http_200_verified"] is True

    for art in synd["articles"]:
        html_path = Path(art["published_file_path"])
        smap_path = Path(art["sitemap_path"])
        assert html_path.exists()
        assert smap_path.exists()
        assert "https://printdeck.net" in html_path.read_text(encoding="utf-8")
        assert art["slug"] in smap_path.read_text(encoding="utf-8")

    # 2. Generate Pinterest Rich Pin, X thread, Reddit guide, and PR pack
    pack = await julian.generate_social_and_pr_syndication_pack(
        featured_sku="PD-CANVAS-24X36",
        campaign_tag="q4_atelier_showcase",
    )
    assert pack["http_200_verified"] is True
    assert pack["pinterest_rich_pin"]["product_schema"]["sku"] == "PD-CANVAS-24X36"
    assert len(pack["x_twitter_thread"]) == 4
    assert "utm_source=reddit" in pack["reddit_value_post"]["body_markdown"]


@pytest.mark.asyncio
async def test_agent_clara_3stage_cart_recovery_optout_and_para_intake_support(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase7_env(tmp_path)
    clara = MailerAgentClara(ssot=ssot, db=db)

    # 1. Seed two PENDING_PAYMENT carts (one active, one opted-out via RFC 8058) and one paid order
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO orders (
                order_id, order_number, customer_email, customer_name,
                shipping_address_line1, shipping_city, shipping_state, shipping_zip, shipping_country,
                payment_gateway, status, subtotal_cents, total_cents,
                estimated_fulfillment_cost_cents, selected_provider, unsubscribe_token
            ) VALUES
            ('ord_cart_active', 'PD-CART-101', 'elena.vance@architects.io', 'Elena Vance',
             '400 W Broadway', 'New York', 'NY', '10012', 'US',
             'para-paygate', 'PENDING_PAYMENT', 14900, 14900, 5200, 'printify', 'tok_elena_101'),
            ('ord_cart_optedout', 'PD-CART-102', 'optedout@collector.org', 'Opted Out User',
             '100 Main St', 'Austin', 'TX', '78701', 'US',
             'para-paygate', 'PENDING_PAYMENT', 6800, 6800, 2400, 'printful', 'tok_opt_102'),
            ('ord_paid_shipped', 'PD-ORD-909', 'marcus.cole@quantfund.io', 'Marcus Cole',
             '1 Market St', 'San Francisco', 'CA', '94105', 'US',
             'stripe', 'SHIPPED', 14900, 14900, 5100, 'printful', 'tok_marcus_909')
            """
        )
        conn.execute(
            """
            INSERT INTO marketing_optouts (optout_id, email, unsubscribe_token, rfc8058_one_click)
            VALUES ('opt_01', 'optedout@collector.org', 'tok_opt_102', 1)
            """
        )

    # Verify pre-send RCPT TO / syntax / disposable / opt-out checks
    assert clara.verify_recipient_pre_send("bounce@example.invalid")["allowed"] is False
    assert clara.verify_recipient_pre_send("optedout@collector.org")["allowed"] is False
    assert clara.verify_recipient_pre_send("elena.vance@architects.io")["allowed"] is True

    # 2. Run 3-Stage Abandoned Cart Recovery (T30M, T6H, T24H)
    rec = await clara.run_3stage_abandoned_cart_recovery()
    assert rec["dispatched_count"] == 3  # 3 stages for ord_cart_active
    assert rec["suppressed_count"] == 1  # ord_cart_optedout suppressed via RFC 8058
    t24_mail = next(m for m in rec["dispatched_emails"] if m["stage"] == "T24H")
    assert t24_mail["promo_code"].startswith("ATELIER10-")
    assert "List-Unsubscribe-Post" in t24_mail["headers"]
    assert "/pay/optout" in t24_mail["headers"]["List-Unsubscribe"]

    # 3. Post-purchase lifecycle emails (Order Confirmation -> 2h Grace Window, Tracking, Day-14 Winback)
    conf_mail = await clara.send_post_purchase_lifecycle_email(
        order_id="ord_paid_shipped",
        event_type="ORDER_CONFIRMATION",
    )
    assert conf_mail["sent"] is True
    assert "120-Minute" in conf_mail["subject"]

    # 4. Seed 3 inbound tickets in intake.sqlite (`para-intake.service` :8787)
    with sqlite3.connect(str(db.intake_db_path)) as ik_conn:
        ik_conn.executemany(
            """
            INSERT INTO intake_tickets (
                ticket_id, customer_email, customer_name, order_id,
                category, subject, message, photo_attachment_url, status
            ) VALUES (?, ?, ?, ?, 'support', ?, ?, ?, 'OPEN')
            """,
            [
                (
                    "ik_001_tracking",
                    "marcus.cole@quantfund.io",
                    "Marcus Cole",
                    "ord_paid_shipped",
                    "Where is my canvas order?",
                    "Hi, checking on the carrier status for PD-ORD-909.",
                    "",
                ),
                (
                    "ik_002_damaged_photo",
                    "marcus.cole@quantfund.io",
                    "Marcus Cole",
                    "ord_paid_shipped",
                    "Canvas frame corner arrived cracked in transit",
                    "The courier dented the box and the frame corner is cracked. Photo attached.",
                    "https://printdeck.net/uploads/intake/damage_photo_909.jpg",
                ),
                (
                    "ik_003_damaged_no_photo",
                    "elena.vance@architects.io",
                    "Elena Vance",
                    "ord_cart_active",
                    "Box looks torn",
                    "My item arrived damaged but I have not taken a photo yet.",
                    "",
                ),
            ],
        )

    intake_res = await clara.process_inbound_intake_tickets()
    assert intake_res["tickets_processed_count"] == 3
    assert len(intake_res["replacement_orders_created"]) == 1
    assert intake_res["escalated_to_elena"] == ["ik_003_damaged_no_photo"]

    by_id = {t["ticket_id"]: t for t in intake_res["tickets"]}
    assert by_id["ik_001_tracking"]["status"] == "RESOLVED_AUTONOMOUSLY"
    assert by_id["ik_002_damaged_photo"]["status"] == "RESOLVED_AUTO_REPLACEMENT"
    assert by_id["ik_002_damaged_photo"]["replacement_order_id"] is not None
    assert by_id["ik_003_damaged_no_photo"]["status"] == "ESCALATED_TO_ELENA"
