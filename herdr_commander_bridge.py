#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 5 `para-commander.timer` (30m) & `Herdr Control Tower` Bridge
=================================================================================================
Synchronizes PrintDeck's 5-Agent Executive Board Room (`BoardRoomEngine`), Tier 1 IT Manager
(`ITManagerVictor`), and Tier 1 Business Manager (`BusinessManagerElena`) with:
  1. `para-commander.timer` (30-minute autonomous governance cadence).
  2. `Herdr Control Tower` (`/home/dima/Projects/growth/state.json`,
     `/home/dima/Projects/growth/printdeck_ssot_status.json`, and
     `/home/dima/Projects/growth/growth_log.md`) using non-destructive `fcntl.flock`
     mutex locking on `/home/dima/Projects/growth/state.lock`.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import fcntl
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from boardroom_engine import BoardProposal, BoardRoomEngine
from db.database import PrintDeckDB, get_db
from manager_biz_elena import BusinessManagerElena
from manager_it_victor import ITManagerVictor
from ssot_engine import DEFAULT_HERDR_GROWTH_DIR, SSOTEngine, format_punch_timestamp


class ParaCommanderHerdrBridge:
    """
    Executes the 30-minute `para-commander` governance tick across PrintDeck's
    Two-Tier Management Hierarchy + 5-Agent Executive Board Room, and publishes
    telemetry non-destructively into `Herdr Control Tower` (`/home/dima/Projects/growth`).
    """

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[PrintDeckDB] = None,
        growth_dir: Path = DEFAULT_HERDR_GROWTH_DIR,
    ) -> None:
        self.ssot = ssot or SSOTEngine(herdr_growth_dir=growth_dir)
        self.db = db or get_db()
        self.growth_dir = Path(growth_dir)
        self.boardroom = BoardRoomEngine(ssot=self.ssot, db=self.db)
        self.victor = ITManagerVictor(ssot=self.ssot, db=self.db, boardroom=self.boardroom)
        self.elena = BusinessManagerElena(ssot=self.ssot, db=self.db, boardroom=self.boardroom)

    async def process_pending_db_proposals(self) -> List[Dict[str, Any]]:
        """
        Finds any `PENDING_REVIEW` rows in `boardroom_proposals` and runs them through
        the 5-Agent Executive Board Room (`BoardRoomEngine.deliberate_proposal`).
        """
        with self.db.connect() as conn:
            rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM boardroom_proposals WHERE status = 'PENDING_REVIEW'"
                ).fetchall()
            ]

        resolutions: List[Dict[str, Any]] = []
        for row in rows:
            bps = int(row.get("expected_margin_impact_bps") or 0)
            projected_margin = max(38.0, 55.0 + (bps / 100.0))
            proposal = BoardProposal(
                proposal_id=row["proposal_id"],
                title=row["title"],
                proposing_agent=row["proposing_agent"],
                scope=row["target_scope"],
                category="STRATEGIC_GOVERNANCE",
                hypothesis=row["rationale"],
                expected_roi_impact=f"{bps:+d} bps margin impact",
                rollback_plan=f"Revert scope {row['target_scope']} to previous SSOT snapshot.",
                projected_gross_margin_pct=projected_margin,
                proposed_discount_pct=0.0,
                required_budget_usd=0.0,
                target_sku_or_route=row["target_scope"],
            )
            res = await self.boardroom.deliberate_proposal(proposal)
            resolutions.append(res.to_dict())

        return resolutions

    def sync_to_herdr_control_tower(
        self,
        tick_summary: Dict[str, Any],
        append_growth_log: bool = True,
    ) -> Dict[str, Any]:
        """
        Non-destructively updates `/home/dima/Projects/growth/state.json` (under `state.lock`),
        writes `/home/dima/Projects/growth/printdeck_ssot_status.json`, and appends a
        governance cycle entry to `/home/dima/Projects/growth/growth_log.md`.
        """
        if not self.growth_dir.exists():
            return {"synced": False, "reason": f"Growth dir {self.growth_dir} does not exist"}

        lock_path = self.growth_dir / "state.lock"
        state_json_path = self.growth_dir / "state.json"
        ssot_status_path = self.growth_dir / "printdeck_ssot_status.json"
        growth_log_path = self.growth_dir / "growth_log.md"

        lock_path.touch(exist_ok=True)
        with open(lock_path, "r+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                # 1. Non-destructive update of state.json
                if state_json_path.exists():
                    raw_state = json.loads(state_json_path.read_text(encoding="utf-8"))
                else:
                    raw_state = {}

                raw_state["printdeck_governance"] = {
                    "last_commander_tick_utc": tick_summary["tick_timestamp_utc"],
                    "boardroom_quorum_model": "5-Seat Majority (3/5 Required, Seat 1 Marcus 35% Margin Veto)",
                    "board_resolutions_logged": tick_summary["board_resolutions_total"],
                    "it_manager_victor": {
                        "playwright_gate_passed": tick_summary["victor_cycle"]["playwright_gate"][
                            "playwright_gate_passed"
                        ],
                        "hardware_coexistence_preserved": tick_summary["victor_cycle"][
                            "playwright_gate"
                        ]["hardware_coexistence_preserved"],
                        "open_issues_triaged": tick_summary["victor_cycle"][
                            "open_issues_triaged_count"
                        ],
                        "dispatched_tasks_count": len(
                            tick_summary["victor_cycle"]["dispatched_tasks"]
                        ),
                    },
                    "biz_manager_elena": {
                        "cohort_counts": tick_summary["elena_standup"]["cohort_counts"],
                        "realized_gross_margin_pct": tick_summary["elena_standup"][
                            "finops_snapshot"
                        ]["realized_gross_margin_pct"],
                        "dispatched_tasks_count": tick_summary["elena_standup"][
                            "dispatched_tasks_count"
                        ],
                    },
                }

                tmp_state = state_json_path.with_suffix(".json.tmp")
                tmp_state.write_text(json.dumps(raw_state, indent=2), encoding="utf-8")
                tmp_state.replace(state_json_path)

                # 2. Update printdeck_ssot_status.json
                ssot_state = self.ssot.get_state()
                raw_open = ssot_state.get("open_issues", [])
                open_list = list(raw_open.values()) if isinstance(raw_open, dict) else list(raw_open)
                status_payload = {
                    "project": "printdeck.net",
                    "updated_at": ssot_state.get("last_updated"),
                    "active_locks_count": len(ssot_state.get("active_locks", {})),
                    "active_locks": list(ssot_state.get("active_locks", {}).values()),
                    "open_issues_count": len(open_list),
                    "open_issues": open_list,
                    "board_resolutions_count": len(ssot_state.get("board_resolutions", [])),
                    "latest_board_resolutions": ssot_state.get("board_resolutions", [])[:5],
                    "phase5_commander_tick": raw_state["printdeck_governance"],
                }
                tmp_status = ssot_status_path.with_suffix(".json.tmp")
                tmp_status.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")
                tmp_status.replace(ssot_status_path)

                # 3. Append non-destructively to growth_log.md
                if append_growth_log and growth_log_path.exists():
                    finops = tick_summary["elena_standup"]["finops_snapshot"]
                    log_entry = (
                        f"\n### PrintDeck Phase 5 Governance Tick (`para-commander`) — {tick_summary['tick_timestamp_utc']}\n"
                        f"- **Executive Board Room (5-Seat Quorum):** `{tick_summary['board_resolutions_total']}` total resolutions logged | "
                        f"`{len(tick_summary['pending_proposals_deliberated'])}` pending proposals deliberated this tick\n"
                        f"- **IT Manager (`Agent Victor`):** Playwright Gate=`{tick_summary['victor_cycle']['playwright_gate']['playwright_gate_passed']}` "
                        f"(`/hardware` & `/simulator` preserved=`{tick_summary['victor_cycle']['playwright_gate']['hardware_coexistence_preserved']}`) | "
                        f"`{tick_summary['victor_cycle']['open_issues_triaged_count']}` open issues triaged via NATS\n"
                        f"- **Business Manager (`Agent Elena`):** Realized Gross Margin=`{finops['realized_gross_margin_pct']:.2f}%` "
                        f"(Floor `35.0%`) | Cohorts={json.dumps(tick_summary['elena_standup']['cohort_counts'])} | "
                        f"`{tick_summary['elena_standup']['dispatched_tasks_count']}` specialist tasks dispatched\n"
                    )
                    with open(growth_log_path, "a", encoding="utf-8") as log_fh:
                        log_fh.write(log_entry)
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

        return {
            "synced": True,
            "state_json_path": str(state_json_path),
            "ssot_status_path": str(ssot_status_path),
            "growth_log_path": str(growth_log_path),
        }

    async def run_commander_tick(
        self,
        escalate_cull_candidates: bool = True,
        append_growth_log: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the full 30-minute `para-commander.timer` governance cycle:
          1. Runs `ITManagerVictor.run_supervision_cycle()`.
          2. Runs `BusinessManagerElena.run_merchandising_standup()`.
          3. Deliberates any `PENDING_QUORUM` proposals in `boardroom_proposals`.
          4. Syncs telemetry into `Herdr Control Tower` (`/home/dima/Projects/growth`).
        """
        victor_cycle = await self.victor.run_supervision_cycle()
        elena_standup = await self.elena.run_merchandising_standup(
            escalate_cull_candidates=escalate_cull_candidates
        )
        pending_deliberated = await self.process_pending_db_proposals()

        ssot_state = self.ssot.get_state()
        now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        tick_summary: Dict[str, Any] = {
            "tick_timestamp_utc": now_utc,
            "cadence": "para-commander.timer (30m)",
            "victor_cycle": victor_cycle,
            "elena_standup": elena_standup,
            "pending_proposals_deliberated": pending_deliberated,
            "board_resolutions_total": len(ssot_state.get("board_resolutions", [])),
        }
        herdr_sync = self.sync_to_herdr_control_tower(
            tick_summary=tick_summary,
            append_growth_log=append_growth_log,
        )
        tick_summary["herdr_control_tower_sync"] = herdr_sync
        return tick_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PrintDeck Phase 5 para-commander 30m Governance & Herdr Control Tower Bridge"
    )
    parser.add_argument(
        "--no-growth-log-append",
        action="store_true",
        help="Skip appending markdown block to growth_log.md",
    )
    args = parser.parse_args()

    bridge = ParaCommanderHerdrBridge()
    result = asyncio.run(
        bridge.run_commander_tick(append_growth_log=not args.no_growth_log_append)
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
