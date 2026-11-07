#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 6 Core Operational Specialist Agents Test Suite
(`tests/test_phase6_specialist_agents.py`).

Tests:
  1. `Agent Maya` (`agent_inventory_maya.py`) + `comfyui_flux_workflows.py`
  2. `Agent Lucas` (`agent_finops_lucas.py`)
  3. `Agent Nadia` / `Agent Viktor-Eng` (`agent_engineering_nadia.py`)
  4. `Agent Jennifer` (`agent_dev_jennifer.py`) + `playwright_verifier.py` (`omnibook-spark:8900`)
  5. `Agent Damon` (`agent_maintenance_damon.py`)
"""

from __future__ import annotations

from pathlib import Path
import pytest

from agent_dev_jennifer import DevelopmentAgentJennifer
from agent_engineering_nadia import EngineeringAgentNadia, EngineeringAgentViktorEng
from agent_finops_lucas import MINIMUM_NET_MARGIN_PCT, FinancialAdvisorAgentLucas
from agent_inventory_maya import InventoryAgentMaya
from agent_maintenance_damon import WebsiteMaintenanceAgentDamon
from boardroom_engine import BoardProposal, BoardRoomEngine
from comfyui_flux_workflows import FLUX_PROMPT_MATRICES, build_comfyui_flux_api_graph
from db.database import DatabaseManager
from playwright_verifier import (
    BoardResolutionRequiredError,
    PlaywrightVerificationError,
    PlaywrightVerifier,
)
from ssot_engine import SSOTEngine


def _make_phase6_env(tmp_path: Path) -> tuple[SSOTEngine, DatabaseManager]:
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
        db_path=state_dir / "test_phase6.sqlite",
        paygate_db_path=state_dir / "test_paygate.sqlite",
        intake_db_path=state_dir / "test_intake.sqlite",
    )
    return ssot, db


@pytest.mark.asyncio
async def test_agent_maya_comfyui_flux_probation_drop_and_catalog_cycling(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase6_env(tmp_path)
    maya = InventoryAgentMaya(ssot=ssot, db=db)

    # 1. Verify ComfyUI Flux prompt matrices & node graph across all 3 verticals
    assert set(FLUX_PROMPT_MATRICES.keys()) == {"wall_art", "apparel", "memorabilia"}
    graph = build_comfyui_flux_api_graph("Bauhaus monolith painting", width=1024, height=1536)
    assert graph["1"]["inputs"]["unet_name"] == "flux1-dev.safetensors"
    assert graph["8"]["inputs"]["model_name"] == "4x-UltraSharp.pth"

    gaps = maya.discover_trends_and_gaps()
    assert len(gaps) >= 6

    # 2. Autonomous product creation -> GPU lease, Flux generation, 300-DPI preflight, 14-day PROBATION cohort
    drop = await maya.create_autonomous_product_drop(vertical="wall_art", aesthetic_index=0)
    assert drop["agent"] == "Agent Maya"
    assert drop["cohort_status"] == "PROBATION"
    assert drop["preflight_report"]["preflight_status"] == "PASSED_300DPI"
    assert "Product" in drop["json_ld_types"]

    # 3. Catalog cycling without Board Resolution Token must be blocked
    with pytest.raises(BoardResolutionRequiredError):
        await maya.cycle_catalog_with_elena(
            cull_sku="PD-CAP-SNAPBACK",
            board_resolution_token=None,
        )

    # 4. Obtain formal 3/5 Board Room Resolution Token and execute catalog cycling (301 redirect + scale STAR)
    board = BoardRoomEngine(ssot=ssot, db=db)
    res = await board.deliberate_proposal(
        BoardProposal(
            proposal_id="PROP-P6-CULL-CAP",
            title="Retire zero-traction PD-CAP-SNAPBACK after 21 days and 301 redirect to /collections/apparel",
            proposing_agent="Agent Elena",
            scope="merchandising:catalog-cycling",
            category="collection_retire",
            hypothesis="Reallocating catalog slot to high-margin canvas increases store RPM.",
            expected_roi_impact="+320 bps margin",
            rollback_plan="Restore is_active=1 on PD-CAP-SNAPBACK.",
            projected_gross_margin_pct=61.0,
        )
    )
    assert res.quorum_reached is True

    cycle_res = await maya.cycle_catalog_with_elena(
        cull_sku="PD-CAP-SNAPBACK",
        star_sku_to_scale="PD-CANVAS-24X36",
        board_resolution_token=res.board_resolution_token,
    )
    assert cycle_res["retired_sku"] == "PD-CAP-SNAPBACK"
    assert cycle_res["redirect_registered"]["status_code"] == 301
    assert cycle_res["redirect_registered"]["target_path"] == "/collections/headwear"

    # Verify punch log in SOURCE_OF_TRUTH.md contains agent Maya entries
    md_text = ssot.ssot_md_path.read_text(encoding="utf-8")
    assert "agent Maya" in md_text


@pytest.mark.asyncio
async def test_agent_lucas_dynamic_35pct_net_margin_floor_and_pnl_ledger(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase6_env(tmp_path)
    lucas = FinancialAdvisorAgentLucas(ssot=ssot, db=db)

    # Simulate a +$28.00 blank/shipping cost spike on a variant so its net margin drops < 35.0%
    with db.connect() as conn:
        sample_var = dict(
            conn.execute(
                "SELECT pv.variant_sku, pv.retail_price_cents FROM product_variants pv "
                "JOIN products p ON pv.product_id = p.product_id WHERE p.is_legacy_hardware = 0 LIMIT 1"
            ).fetchone()
        )
    target_vsku = sample_var["variant_sku"]
    hike_cents = int(sample_var["retail_price_cents"] * 0.65)

    audit = await lucas.run_daily_margin_and_ledger_audit(
        simulated_provider_cost_hikes={target_vsku: hike_cents}
    )
    pnl = audit["pnl_brief"]
    assert pnl["variants_repriced_count"] >= 1
    repriced = next(r for r in pnl["repriced_variants"] if r["variant_sku"] == target_vsku)
    assert repriced["old_net_margin_pct"] < MINIMUM_NET_MARGIN_PCT
    assert repriced["new_net_margin_pct"] >= MINIMUM_NET_MARGIN_PCT

    # Anomalous surcharge (>= $4.00) must also auto-open an issue in OPEN ISSUES on punch-out
    assert audit["auto_opened_issue"] is not None
    assert target_vsku in audit["auto_opened_issue"]["how_why_opened"]


@pytest.mark.asyncio
async def test_agent_nadia_backend_remediation_and_issue_closure(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase6_env(tmp_path)
    nadia = EngineeringAgentNadia(ssot=ssot, db=db)
    assert EngineeringAgentViktorEng is EngineeringAgentNadia

    # Seed a stalled/FAILED Printify webhook and open an SSOT issue
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO webhook_events (
                event_id, source, external_event_id, event_type,
                signature_header, signature_verified, payload_sha256,
                payload_json, processing_status, processing_notes
            ) VALUES (
                'wh_fail_p6_01', 'printify', 'evt_ext_991', 'order:shipment:created',
                'sha256=valid', 1, 'deadbeef', '{}', 'FAILED', 'Simulated transient DB lock timeout'
            )
            """
        )

    issue = ssot.open_issue(
        agent_name="Agent Victor",
        scope="backend:engineering-specialist",
        how_why="Webhook wh_fail_p6_01 stalled and DB query latency spiked to 142ms",
        severity="HIGH",
    )

    rem = await nadia.remediate_backend_incident(
        issue_id=issue["id"],
        simulated_query_latency_ms=142.0,
    )
    assert rem["integration_test_passed"] is True
    assert "wh_fail_p6_01" in rem["replayed_webhooks"]
    assert rem["closed_issue_record"] is not None
    assert rem["closed_issue_record"]["id"] == issue["id"]


@pytest.mark.asyncio
async def test_agent_jennifer_and_damon_with_100pct_playwright_gate(
    tmp_path: Path,
) -> None:
    ssot, db = _make_phase6_env(tmp_path)
    verifier = PlaywrightVerifier()

    jennifer = DevelopmentAgentJennifer(
        ssot=ssot,
        db=db,
        playwright_verifier=verifier,
        worktree_base_dir=tmp_path / "worktrees",
        production_deploy_dir=tmp_path / "prod_dist",
    )

    iss = ssot.open_issue(
        agent_name="Agent Victor",
        scope="frontend:development-specialist",
        how_why="Add Answered-Forge Print Viewing Distance & DPI Acuity Calculator to /studio",
        severity="MEDIUM",
    )

    # 1. If staged HTML breaks legacy /hardware coexistence, PlaywrightVerifier (<100%) blocks promotion!
    with pytest.raises(PlaywrightVerificationError):
        await jennifer.implement_and_promote_ticket(
            issue_id=iss["id"],
            feature_spec="Broken hardware regression test",
            staged_html_overrides={"/hardware": "<html><body>Broken page without controller</body></html>"},
        )

    # Issue should still be open because promotion was blocked
    open_ids = [i["id"] for i in ssot.get_state()["open_issues"]]
    assert iss["id"] in open_ids

    # 2. Valid implementation passes 100.0% (6/6) Playwright checks, promotes, and closes issue
    promo = await jennifer.implement_and_promote_ticket(
        issue_id=iss["id"],
        feature_spec="Add Answered-Forge Print Viewing Distance & DPI Acuity Calculator",
    )
    assert promo["promoted_to_production"] is True
    assert promo["playwright_report"]["passed_100_pct"] is True
    assert promo["playwright_report"]["pass_rate_pct"] == 100.0
    assert promo["closed_issue_record"]["id"] == iss["id"]

    # 3. Test Agent Damon (Website Maintenance & Autonomous UI Evolution Agent)
    board = BoardRoomEngine(ssot=ssot, db=db)
    damon = WebsiteMaintenanceAgentDamon(
        ssot=ssot,
        db=db,
        boardroom=board,
        playwright_verifier=verifier,
        production_deploy_dir=tmp_path / "prod_dist",
    )

    # Structural UI layout overhaul without Board Resolution Token must raise BoardResolutionRequiredError
    with pytest.raises(BoardResolutionRequiredError):
        await damon.deploy_ui_evolution(
            evolution_title="Major Structural Split-Screen Hero Overhaul",
            is_structural_layout_overhaul=True,
            board_resolution_token=None,
        )

    # Obtain Board approval and deploy with rage-click observation auto-logging to OPEN ISSUES
    ui_res = await board.deliberate_proposal(
        BoardProposal(
            proposal_id="PROP-P6-UI-EVO",
            title="Deploy Milanese Travertine Penthouse Room & Split-Screen Atelier Hero",
            proposing_agent="Agent Damon",
            scope="frontend:ui-maintenance-specialist",
            category="ui_ux_overhaul",
            hypothesis="Adding warm 3200K travertine room preset increases canvas add-to-cart rate by 9%.",
            expected_roi_impact="+9% canvas CVR",
            rollback_plan="Revert SpatialMockupStudio room preset list to previous snapshot.",
            projected_gross_margin_pct=62.0,
        )
    )
    assert ui_res.quorum_reached is True

    evo = await damon.deploy_ui_evolution(
        evolution_title="Deploy Milanese Travertine Penthouse Room & Split-Screen Atelier Hero",
        is_structural_layout_overhaul=True,
        board_resolution_token=ui_res.board_resolution_token,
        simulated_rage_click_selector="#mobile-frame-swatch-carousel",
    )
    assert evo["promoted_to_production"] is True
    assert evo["playwright_report"]["passed_100_pct"] is True
    assert evo["auto_opened_issue"] is not None
    assert "#mobile-frame-swatch-carousel" in evo["auto_opened_issue"]["how_why_opened"]
