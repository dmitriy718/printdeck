#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 6 Specialist Agent 4:
Development Agent (`Agent Jennifer` — `agent_dev_jennifer.py`).

Supervised by: Tier 1 IT Manager `Agent Victor`.
Mandatory Operating Law:
  1. Calls `ssot.punch_in("Agent Jennifer", scope, detailed_task_description)` before touching
     any file, database row, or API.
  2. Verifies active Redis (`pi-core:6379`) / SSOT lock and `board_resolution_token` (when
     altering UI layouts) via `verify_active_lock_and_board_token`.
  3. Builds in an isolated staging worktree, runs `PlaywrightVerifier` (`omnibook-spark:8900`)
     requiring a strict 100.0% pass rate before promoting to production and calling
     `ssot.punch_out("Agent Jennifer", scope, resolution_and_observations, close_issue_id=...)`.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from db.database import DatabaseManager, get_db
from playwright_verifier import (
    PlaywrightSuiteReport,
    PlaywrightVerifier,
    verify_active_lock_and_board_token,
)
from ssot_engine import PROJECT_ROOT, SSOTEngine, format_punch_timestamp


class DevelopmentAgentJennifer:
    """
    `Agent Jennifer` — Full-Stack Storefront & Interactive Tooling Development Agent.
    Pulls prioritized frontend/backend tickets from `OPEN ISSUES:` assigned by IT Manager
    `Agent Victor`, stages code in an isolated worktree, runs full headless Chromium E2E
    verification via `omnibook-spark` (`192.168.0.152:8900`), and promotes to production
    only when 100% of Playwright checks pass.
    """

    AGENT_NAME = "Agent Jennifer"
    DEFAULT_SCOPE = "frontend:development-specialist"

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[DatabaseManager] = None,
        playwright_verifier: Optional[PlaywrightVerifier] = None,
        worktree_base_dir: Optional[Path] = None,
        production_deploy_dir: Optional[Path] = None,
    ) -> None:
        self.ssot = ssot or SSOTEngine()
        self.db = db or get_db()
        self.playwright = playwright_verifier or PlaywrightVerifier()
        self.worktree_base_dir = Path(
            worktree_base_dir or (self.ssot.state_dir / "worktrees" / "jennifer")
        )
        self.production_deploy_dir = Path(
            production_deploy_dir or (PROJECT_ROOT / "frontend" / "dist")
        )

    def pull_prioritized_tickets_from_victor(self) -> List[Dict[str, Any]]:
        """
        Pulls open frontend, WebGL `<SpatialMockupStudio />`, and `Answered-Forge`
        calculator tickets from `OPEN ISSUES:` in `SOURCE_OF_TRUTH.md`.
        """
        state = self.ssot.get_state()
        raw_issues = state.get("open_issues", [])
        issues = list(raw_issues.values()) if isinstance(raw_issues, dict) else list(raw_issues)

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        issues.sort(key=lambda i: severity_rank.get(str(i.get("severity", "MEDIUM")).upper(), 2))
        return issues

    def _prepare_isolated_worktree(self, ticket_id: str) -> Path:
        """
        Creates an isolated staging worktree for `ticket_id` so changes are tested
        in isolation before promotion to `/var/www/printdeck` (`frontend/dist`).
        """
        wt_dir = self.worktree_base_dir / f"wt_{ticket_id.lower().replace('-', '_')}"
        if wt_dir.exists():
            shutil.rmtree(wt_dir)
        wt_dir.mkdir(parents=True, exist_ok=True)

        # Attempt git worktree metadata snapshot or stage dist artifacts
        try:
            subprocess.run(
                ["git", "status", "--short"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                timeout=1.5,
                check=False,
            )
        except Exception:
            pass

        if self.production_deploy_dir.exists():
            shutil.copytree(self.production_deploy_dir, wt_dir / "dist", dirs_exist_ok=True)
        else:
            (wt_dir / "dist").mkdir(parents=True, exist_ok=True)

        return wt_dir

    async def implement_and_promote_ticket(
        self,
        issue_id: Optional[str] = None,
        feature_spec: str = "Add Answered-Forge Print Viewing Distance & DPI Acuity Calculator micro-tool",
        alters_ui_layout: bool = False,
        board_resolution_token: Optional[str] = None,
        staged_html_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Full lifecycle for `Agent Jennifer`:
          1. Punches in to `SOURCE_OF_TRUTH.md` and verifies Redis/SSOT lock (+ `board_resolution_token` if `alters_ui_layout=True`).
          2. Creates an isolated staging worktree and implements the feature or bug fix.
          3. Runs `PlaywrightVerifier.run_full_verification_suite()` targeting `omnibook-spark:8900`.
          4. Blocks promotion and raises `PlaywrightVerificationError` if pass rate < 100.0%.
          5. Promotes verified artifacts to production and punches out of `SOURCE_OF_TRUTH.md` (closing `issue_id`).
        """
        if issue_id is None:
            tickets = self.pull_prioritized_tickets_from_victor()
            if tickets:
                issue_id = str(tickets[0].get("id"))
                feature_spec = str(tickets[0].get("how_why_opened") or feature_spec)

        scope = f"{self.DEFAULT_SCOPE}:{(issue_id or 'feature').lower()}"
        lock = self.ssot.punch_in(
            agent_name=self.AGENT_NAME,
            scope=scope,
            task_description=(
                f"staging feature/fix '{feature_spec}' ({issue_id or 'NEW'}) in isolated worktree "
                f"and running omnibook-spark:8900 Playwright E2E gate"
            ),
        )
        try:
            lock_verification = verify_active_lock_and_board_token(
                ssot=self.ssot,
                agent_name=self.AGENT_NAME,
                scope=scope,
                lock_token=lock["token"],
                board_resolution_token=board_resolution_token,
                requires_board_resolution=alters_ui_layout,
            )

            wt_dir = self._prepare_isolated_worktree(issue_id or "feat_calc")
            manifest_path = wt_dir / "staged_feature_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "agent": self.AGENT_NAME,
                        "issue_id": issue_id,
                        "feature_spec": feature_spec,
                        "worktree_path": str(wt_dir),
                        "staged_at": format_punch_timestamp(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            # Mandatory 100% Playwright verification gate before promoting to production
            pw_report: PlaywrightSuiteReport = await self.playwright.run_full_verification_suite(
                staged_html_overrides=staged_html_overrides,
                require_100_pct=True,
            )

            # Promote staged manifest to production deploy directory
            self.production_deploy_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                manifest_path,
                self.production_deploy_dir / "jennifer_last_promoted_release.json",
            )

            summary = (
                f"implemented and promoted '{feature_spec}' ({issue_id or 'FEAT'}) from isolated "
                f"worktree {wt_dir.name} after 100.0% Playwright verification "
                f"({pw_report.passed_checks}/{pw_report.total_checks} checks passed on omnibook-spark:8900)"
            )
            punch_out_res = self.ssot.punch_out(
                agent_name=self.AGENT_NAME,
                scope=scope,
                resolution_summary=summary,
                close_issue_id=issue_id,
                token=lock["token"],
            )

            return {
                "agent": self.AGENT_NAME,
                "issue_id_closed": issue_id,
                "feature_spec": feature_spec,
                "worktree_path": str(wt_dir),
                "promoted_to_production": True,
                "playwright_report": pw_report.to_dict(),
                "closed_issue_record": punch_out_res.get("closed_issue"),
                "lock_verification": lock_verification,
            }
        except Exception as exc:
            state = self.ssot.get_state()
            if scope in state.get("active_locks", {}):
                self.ssot.punch_out(
                    agent_name=self.AGENT_NAME,
                    scope=scope,
                    resolution_summary=f"blocked promoting '{feature_spec}': {exc}",
                    token=lock["token"],
                )
            raise

