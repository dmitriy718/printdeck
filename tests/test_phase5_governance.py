#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 5 Governance, 5-Agent Executive Board Room,
Two-Tier Management Hierarchy (`ITManagerVictor` + `BusinessManagerElena`), and
`para-commander.timer` / `Herdr Control Tower` Integration Test Suite.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app import app
from boardroom_engine import (
    BOARD_SEAT_PERSONAS,
    MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT,
    BoardProposal,
    BoardRoomEngine,
)
from db.database import DatabaseManager
from herdr_commander_bridge import ParaCommanderHerdrBridge
from manager_biz_elena import BIZ_SPECIALIST_ROSTER, BusinessManagerElena
from manager_it_victor import IT_SPECIALIST_ROSTER, ITManagerVictor
from ssot_engine import SSOTEngine


def _make_isolated_env(tmp_path: Path) -> tuple[SSOTEngine, DatabaseManager, Path]:
    ssot_md = tmp_path / "SOURCE_OF_TRUTH.md"
    state_dir = tmp_path / ".ssot"
    growth_dir = tmp_path / "growth"
    growth_dir.mkdir(parents=True, exist_ok=True)

    # Seed realistic existing Herdr Control Tower files to verify non-destructive sync
    (growth_dir / "state.json").write_text(
        json.dumps(
            {
                "sprint_day": 1,
                "spend_usd": 0.0,
                "existing_herdr_key": "MUST_BE_PRESERVED",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (growth_dir / "growth_log.md").write_text(
        "# Para Growth System — Autonomous COMMANDER Log (`growth_log.md`)\n",
        encoding="utf-8",
    )

    ssot = SSOTEngine(
        ssot_md_path=ssot_md,
        state_dir=state_dir,
        herdr_growth_dir=growth_dir,
    )
    db = DatabaseManager(
        db_path=state_dir / "test_phase5.sqlite",
        paygate_db_path=state_dir / "test_paygate.sqlite",
        intake_db_path=state_dir / "test_intake.sqlite",
    )
    return ssot, db, growth_dir


@pytest.mark.asyncio
async def test_boardroom_5_seat_quorum_and_marcus_35pct_margin_veto(tmp_path: Path) -> None:
    ssot, db, _ = _make_isolated_env(tmp_path)
    board = BoardRoomEngine(ssot=ssot, db=db)

    assert len(BOARD_SEAT_PERSONAS) == 5
    assert MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT == 35.0

    # 1. Valid high-margin proposal -> Approved by >= 3/5 quorum, signs board_resolution_token
    valid_proposal = BoardProposal(
        proposal_id="PROP-TEST-001",
        title="Launch Bauhaus Archival 24x36 Stretched Canvas Capsule",
        proposing_agent="Agent Elena (Business Manager)",
        scope="merchandising:launch:bauhaus-24x36",
        category="COLLECTION_LAUNCH",
        hypothesis="Adding 300-DPI Bauhaus geometric canvas works increases gallery wall bundle AOV by 22%.",
        expected_roi_impact="+$1,450/mo net margin at 61.5% gross margin",
        rollback_plan="Pause SKU in `products` table and revert homepage collection carousel.",
        projected_gross_margin_pct=61.5,
        proposed_discount_pct=10.0,
        required_budget_usd=0.0,
        target_sku_or_route="PD-CANVAS-24X36",
    )

    resolution = await board.deliberate_proposal(valid_proposal)
    assert resolution.status == "APPROVED"
    assert resolution.quorum_reached is True
    assert resolution.approvals_count >= 3
    assert resolution.veto_triggered is False
    assert BoardRoomEngine.verify_resolution_token(resolution.board_resolution_token)
    assert len(resolution.votes) == 5

    # Verify resolution was persisted to SOURCE_OF_TRUTH.md
    md_text = ssot.ssot_md_path.read_text(encoding="utf-8")
    assert "EXECUTIVE BOARD ROOM RESOLUTIONS" in md_text
    assert "PROP-TEST-001" in md_text
    assert resolution.board_resolution_token in md_text

    # 2. Proposal violating the 35% minimum gross margin floor -> Automatic VETO by Seat 1 (`Agent Marcus`)
    low_margin_proposal = BoardProposal(
        proposal_id="PROP-TEST-VETO-MARCUS",
        title="Run 45% Flash Discount on Heavyweight Hoodies",
        proposing_agent="Marketing-Agent",
        scope="pricing:flash-sale:hoodies",
        category="DISCOUNT_OVER_15PCT",
        hypothesis="Deep 45% discount drives high unit volume.",
        expected_roi_impact="+300 units sold",
        rollback_plan="Restore retail_price_cents=6800 in `product_variants`.",
        projected_gross_margin_pct=28.4,  # Violates 35.0% floor!
        proposed_discount_pct=45.0,
        required_budget_usd=0.0,
        target_sku_or_route="PD-HOODIE-HEAVY",
    )

    veto_res = await board.deliberate_proposal(low_margin_proposal)
    assert veto_res.status == "VETOED_BY_GUARDRAIL"
    assert veto_res.quorum_reached is False
    assert veto_res.veto_triggered is True
    assert veto_res.board_resolution_token is None
    marcus_vote = next(v for v in veto_res.votes if v.seat_number == 1)
    assert marcus_vote.agent_name == "Agent Marcus"
    assert marcus_vote.veto_exercised is True
    assert "AUTOMATIC FINOPS VETO" in marcus_vote.rationale


@pytest.mark.asyncio
async def test_boardroom_victor_and_sovereign_redteam_vetoes(tmp_path: Path) -> None:
    ssot, db, _ = _make_isolated_env(tmp_path)
    board = BoardRoomEngine(ssot=ssot, db=db)

    # Seat 3 (`Agent Victor`) VETO on proposal threatening `/hardware` coexistence route
    hw_threat_proposal = BoardProposal(
        proposal_id="PROP-TEST-VETO-VICTOR",
        title="Delete /hardware route and replace with apparel landing page",
        proposing_agent="Website-Maintenance-UI-Agent",
        scope="route:overwrite:/hardware",
        category="UI_UX_OVERHAUL",
        hypothesis="Reusing /hardware URL for apparel.",
        expected_roi_impact="+5% apparel clicks",
        rollback_plan="Restore Caddyfile route.",
        projected_gross_margin_pct=58.0,
        target_sku_or_route="/hardware",
    )
    res_victor = await board.deliberate_proposal(hw_threat_proposal)
    assert res_victor.quorum_reached is False
    assert res_victor.veto_triggered is True
    victor_vote = next(v for v in res_victor.votes if v.seat_number == 3)
    assert victor_vote.veto_exercised is True
    assert "/hardware" in victor_vote.rationale

    # Seat 5 (`Agent Sovereign`) VETO on Trademark/DMCA infringement
    tm_proposal = BoardProposal(
        proposal_id="PROP-TEST-VETO-SOVEREIGN",
        title="Launch Unlicensed Marvel Spiderman & Disney Star Wars Canvas Collection",
        proposing_agent="Inventory-Agent",
        scope="merchandising:launch:fan-art",
        category="COLLECTION_LAUNCH",
        hypothesis="Pop culture characters have high search volume.",
        expected_roi_impact="+$2,000 GMV",
        rollback_plan="Unpublish SKUs from Printify and Printful.",
        projected_gross_margin_pct=60.0,
    )
    res_sov = await board.deliberate_proposal(tm_proposal)
    assert res_sov.quorum_reached is False
    assert res_sov.veto_triggered is True
    sov_vote = next(v for v in res_sov.votes if v.seat_number == 5)
    assert sov_vote.veto_exercised is True
    assert "RED-TEAM IP/DMCA VETO" in sov_vote.rationale


@pytest.mark.asyncio
async def test_it_manager_victor_supervision_and_playwright_gate(tmp_path: Path) -> None:
    ssot, db, _ = _make_isolated_env(tmp_path)
    board = BoardRoomEngine(ssot=ssot, db=db)
    victor = ITManagerVictor(ssot=ssot, db=db, boardroom=board)

    assert len(IT_SPECIALIST_ROSTER) == 4

    # Open two technical issues in SSOT for Victor to triage and resolve
    iss1 = ssot.open_issue(
        agent_name="QA-Probe",
        scope="frontend:spatial-studio",
        how_why="Optimize WebGL Spatial Studio shader warmup on mobile Safari (High-DPI texture spike)",
        severity="HIGH",
    )
    iss2 = ssot.open_issue(
        agent_name="FinOps-Monitor",
        scope="backend:pod-webhooks",
        how_why="Verify Printful API v2 webhook retry backoff jitter under 429 burst",
        severity="MEDIUM",
    )

    cycle_report = await victor.run_supervision_cycle(auto_resolve_triaged=True)
    assert cycle_report["manager"] == "Agent Victor"
    assert cycle_report["open_issues_triaged_count"] == 2
    assert cycle_report["playwright_gate"]["playwright_gate_passed"] is True
    assert cycle_report["playwright_gate"]["hardware_coexistence_preserved"] is True
    assert len(cycle_report["auto_resolved_results"]) == 2

    # Both issues should now be moved from OPEN ISSUES to CLOSED ISSUES in SSOT
    updated_state = ssot.get_state()
    open_ids = [i["id"] for i in updated_state["open_issues"]]
    assert iss1["id"] not in open_ids
    assert iss2["id"] not in open_ids
    closed_ids = [c["id"] for c in updated_state["closed_issues"]]
    assert iss1["id"] in closed_ids
    assert iss2["id"] in closed_ids


@pytest.mark.asyncio
async def test_biz_manager_elena_standup_and_cull_candidate_board_escalation(
    tmp_path: Path,
) -> None:
    ssot, db, _ = _make_isolated_env(tmp_path)
    board = BoardRoomEngine(ssot=ssot, db=db)
    elena = BusinessManagerElena(ssot=ssot, db=db, boardroom=board)

    assert len(BIZ_SPECIALIST_ROSTER) == 5

    standup = await elena.run_merchandising_standup(escalate_cull_candidates=True)
    assert standup["manager"] == "Agent Elena"
    assert standup["cohort_counts"]["STAR"] >= 1
    assert standup["cohort_counts"]["HIDDEN GEM"] >= 1
    assert standup["cohort_counts"]["CULL CANDIDATE"] >= 1
    assert standup["dispatched_tasks_count"] >= 4
    assert len(standup["boardroom_escalations"]) >= 1

    first_escalation = standup["boardroom_escalations"][0]
    assert first_escalation["executed"] is True
    assert BoardRoomEngine.verify_resolution_token(first_escalation["board_resolution_token"])


@pytest.mark.asyncio
async def test_para_commander_bridge_and_fastapi_governance_routes(tmp_path: Path) -> None:
    ssot, db, growth_dir = _make_isolated_env(tmp_path)
    bridge = ParaCommanderHerdrBridge(ssot=ssot, db=db, growth_dir=growth_dir)

    tick = await bridge.run_commander_tick(
        escalate_cull_candidates=True,
        append_growth_log=True,
    )
    assert tick["herdr_control_tower_sync"]["synced"] is True
    assert tick["board_resolutions_total"] >= 1

    # Verify state.json preserved existing keys and added printdeck_governance
    state_json = json.loads((growth_dir / "state.json").read_text(encoding="utf-8"))
    assert state_json["existing_herdr_key"] == "MUST_BE_PRESERVED"
    assert "printdeck_governance" in state_json
    assert (
        state_json["printdeck_governance"]["it_manager_victor"]["hardware_coexistence_preserved"]
        is True
    )

    # Verify growth_log.md had the governance block appended non-destructively
    growth_log_text = (growth_dir / "growth_log.md").read_text(encoding="utf-8")
    assert "PrintDeck Phase 5 Governance Tick (`para-commander`)" in growth_log_text

    # Verify FastAPI Phase 5 endpoints behind X-PrintDeck-Admin-Key
    client = TestClient(app)
    headers = {"X-PrintDeck-Admin-Key": "pd_admin_geekom_gt1_key"}

    r_hier = client.get("/api/v2/governance/hierarchy", headers=headers)
    assert r_hier.status_code == 200
    hier = r_hier.json()
    assert hier["executive_boardroom"]["voting_members"] == 5
    assert hier["executive_boardroom"]["majority_quorum_required"] == 3

    r_delib = client.post(
        "/api/v2/governance/boardroom/deliberate",
        headers=headers,
        json={
            "proposal_id": "PROP-API-501",
            "title": "Add 20% Post-Purchase Matching Mug Bundle in Grace Window",
            "proposing_agent": "Agent Elena (Business Manager)",
            "scope": "cro:upsell:ceramic-mug",
            "category": "CRO_EXPERIMENT",
            "hypothesis": "Offering a 20%-off matching mug during the 120m grace window lifts AOV by $14.",
            "expected_roi_impact=" : "+14% post-purchase attach rate",
            "expected_roi_impact": "+14% post-purchase attach rate",
            "rollback_plan": "Disable mug upsell offer in InstantCartDrawer config.",
            "projected_gross_margin_pct": 54.0,
            "proposed_discount_pct": 20.0,
            "required_budget_usd": 0.0,
            "target_sku_or_route": "PD-MUG-15OZ",
        },
    )
    assert r_delib.status_code == 200
    delib_data = r_delib.json()
    assert delib_data["quorum_reached"] is True
    assert delib_data["board_resolution_token"].startswith("br_tok_")
