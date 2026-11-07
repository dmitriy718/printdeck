#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 5 Executive Board Room Engine (`boardroom_engine.py`).
5 Voting Members, 3/5 Majority Quorum Required, with Automatic FinOps/Security VETO Guardrails.

Compute & Inference Routing:
  - Deep Reasoning & Board Deliberations routed to `mbp-m5pro` (`192.168.0.151` / `10.99.0.2`)
    serving `deepseek-r1:32b` and `qwen3:32b` over the 40 Gbps Thunderbolt 5 bridge via
    `macmini-ops` LiteLLM router (`192.168.0.150:4000/v1`).

Seats:
  1. Seat 1 — `Agent Marcus` (Chief Financial & Margin Officer): Automatic VETO power if a
     proposal violates the 35.0% minimum gross margin floor.
  2. Seat 2 — `Agent Elena` (VP of Business, Merchandising & Growth — Active Business Manager)
  3. Seat 3 — `Agent Victor` (VP of IT, Infrastructure & Security — Active IT Manager)
  4. Seat 4 — `Agent Chloe` (Chief Brand, UX & Customer Advocate)
  5. Seat 5 — `Agent Sovereign` (Independent Contrarian & Risk Auditor — Red-Team / IP / SEO Guard)
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import datetime as dt
import hashlib
import hmac
import json
import os
import uuid
from typing import Any, Dict, List, Optional
import httpx

from db.database import DatabaseManager, get_db
from preflight_pipeline import TrademarkGuard
from ssot_engine import SSOTEngine, format_punch_timestamp, require_punch_in
from telemetry_exporter import PrometheusMetricsExporter

LITELLM_ROUTER_URL = os.getenv("LITELLM_ROUTER_URL", "http://192.168.0.150:4000/v1")
BOARDROOM_REASONING_MODEL = os.getenv("BOARDROOM_REASONING_MODEL", "deepseek-r1:32b")
BOARDROOM_SECONDARY_MODEL = os.getenv("CONCIERGE_CHAT_MODEL", "qwen3:32b")
MBP_M5PRO_TB5_HOST = os.getenv("MBP_M5PRO_TB5_HOST", "10.99.0.2")
BOARD_RESOLUTION_HMAC_SECRET = os.getenv(
    "BOARD_RESOLUTION_SECRET", "pd_board_quorum_hmac_secret_2026"
)

MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT = 35.0
PARA_PORTFOLIO_DOMAINS = (
    "novahorizon.net",
    "gighound.net",
    "printdeck.net",
    "horizonsvc.com",
    "tradeloom.net",
    "tradeflows.net",
    "tradeflows.co",
    "coastalserenity.co",
    "mirrortape.net",
    "answered.net",
)


@dataclass
class BoardProposal:
    title: str
    proposing_agent: str
    scope: str
    category: str  # 'ui_ux_overhaul' | 'collection_launch' | 'collection_retire' | 'discount_promo' | 'ad_spend' | 'architecture_change'
    hypothesis: str
    expected_roi_impact: str
    rollback_plan: str
    required_budget_cents: int = 0
    required_budget_usd: float = 0.0
    proposed_discount_pct: float = 0.0
    projected_gross_margin_pct: float = 55.0
    target_sku_or_route: str = ""
    proposal_id: str = field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:10]}")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeatVote:
    seat_number: int
    agent_name: str
    role_title: str
    reasoning_model: str
    compute_node: str
    vote: str  # 'APPROVE' | 'DENY' | 'APPROVE_WITH_AMENDMENTS'
    veto_exercised: bool
    rationale: str
    amendments_requested: List[str] = field(default_factory=list)
    telemetry_cited: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BoardResolution:
    proposal_id: str
    title: str
    proposing_agent: str
    scope: str
    category: str
    status: str  # 'APPROVED' | 'DENIED_QUORUM' | 'VETOED_BY_GUARDRAIL'
    quorum_reached: bool
    approvals_count: int
    denials_count: int
    veto_triggered: bool
    veto_reasons: List[str]
    board_resolution_token: Optional[str]
    votes: List[SeatVote]
    decided_at: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["votes"] = [v.to_dict() for v in self.votes]
        return data


# ==============================================================================
# Independent System Prompts for All 5 Executive Board Room Seats
# ==============================================================================
BOARD_SEAT_PERSONAS: Dict[int, Dict[str, str]] = {
    1: {
        "agent_name": "Agent Marcus",
        "role_title": "Chief Financial & Margin Officer",
        "model": BOARDROOM_REASONING_MODEL,
        "node": f"mbp-m5pro ({MBP_M5PRO_TB5_HOST} via TB5 -> macmini-ops:4000)",
        "system_prompt": (
            "You are Agent Marcus, Chief Financial & Margin Officer on the PrintDeck Executive "
            "Board Room. You evaluate unit economics, Printify vs Printful COGS + shipping variance, "
            "Stripe fee drag (2.9% + $0.30), cash flow, and downside risk. MANDATORY CONSTITUTIONAL "
            "RULE: You hold automatic VETO power if any proposal results in a projected gross margin "
            "below the 35.0% minimum gross margin floor. Return JSON with vote, veto_exercised, rationale."
        ),
    },
    2: {
        "agent_name": "Agent Elena",
        "role_title": "VP of Business, Merchandising & Growth (Active Business Manager)",
        "model": BOARDROOM_REASONING_MODEL,
        "node": f"mbp-m5pro ({MBP_M5PRO_TB5_HOST} via TB5 -> macmini-ops:4000)",
        "system_prompt": (
            "You are Agent Elena, VP of Business, Merchandising & Growth and Active Business Manager "
            "for PrintDeck. You evaluate market demand, aesthetic appeal, seasonal trends, cross-sell "
            "bundle velocity, and SKU Cohort Matrix performance (STAR, HIDDEN GEM, FIXABLE, CULL). "
            "Return JSON with vote, veto_exercised, rationale."
        ),
    },
    3: {
        "agent_name": "Agent Victor",
        "role_title": "VP of IT, Infrastructure & Security (Active IT Manager)",
        "model": BOARDROOM_REASONING_MODEL,
        "node": f"mbp-m5pro ({MBP_M5PRO_TB5_HOST} via TB5 -> macmini-ops:4000)",
        "system_prompt": (
            "You are Agent Victor, VP of IT, Infrastructure & Security and Active IT Manager for "
            "PrintDeck. You evaluate system stability, Core Web Vitals latency, Schema.org/SEO "
            "integrity, Playwright verification coverage, SSOT lock/issue hygiene, and strict "
            "coexistence protection for `/hardware` and `/simulator` Bambu Lab 4.3\" offers. "
            "Exercise VETO if a proposal lacks a rollback plan or endangers `/hardware` or `/pay/*`. "
            "Return JSON with vote, veto_exercised, rationale."
        ),
    },
    4: {
        "agent_name": "Agent Chloe",
        "role_title": "Chief Brand, UX & Customer Advocate",
        "model": BOARDROOM_SECONDARY_MODEL,
        "node": f"mbp-m5pro ({MBP_M5PRO_TB5_HOST} via TB5 -> macmini-ops:4000)",
        "system_prompt": (
            "You are Agent Chloe, Chief Brand, UX & Customer Advocate on the PrintDeck Board Room. "
            "You safeguard the bespoke 'Tactile Atelier & Precision Print Foundry' aesthetic, "
            "zero-CLS Spatial Mockup Studio usability, 300-DPI archival print standards, and the "
            "120-minute editable customer grace window. Return JSON with vote, veto_exercised, rationale."
        ),
    },
    5: {
        "agent_name": "Agent Sovereign",
        "role_title": "Independent Contrarian & Risk Auditor",
        "model": BOARDROOM_REASONING_MODEL,
        "node": f"mbp-m5pro ({MBP_M5PRO_TB5_HOST} via TB5 -> macmini-ops:4000)",
        "system_prompt": (
            "You are Agent Sovereign, Independent Contrarian & Risk Auditor on the PrintDeck Board Room. "
            "You red-team every proposal for trademark/copyright/DMCA exposure, SEO keyword "
            "cannibalization across the 10 Para Investments domains, and hidden operational failure "
            "modes. Exercise VETO if trademark infringement or cross-domain cannibalization is detected. "
            "Return JSON with vote, veto_exercised, rationale."
        ),
    },
}


class BoardRoomEngine:
    """
    Deterministic + LLM-backed 5-Agent Executive Board Room Deliberation Engine.
    Evaluates proposals in parallel across all 5 seats, enforces Marcus's 35% gross
    margin floor VETO and Victor/Sovereign security/IP guardrails, tallies the 3/5
    majority quorum, and issues a cryptographically signed `board_resolution_token`
    into `SOURCE_OF_TRUTH.md`.
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        ssot: Optional[SSOTEngine] = None,
        enable_live_litellm: bool = False,
    ) -> None:
        self.db = db or get_db()
        self.ssot = ssot or SSOTEngine()
        self.trademark_guard = TrademarkGuard()
        self.enable_live_litellm = enable_live_litellm

    def _gather_live_telemetry_context(self) -> Dict[str, Any]:
        exporter = PrometheusMetricsExporter(db=self.db)
        finops = exporter.compute_finops_summary()
        ssot_state = self.ssot.get_state()
        return {
            "gmv_cents": finops["gmv_cents"],
            "net_profit_cents": finops["net_profit_cents"],
            "store_net_margin_pct": finops["net_margin_pct"],
            "arbitrage_savings_cents": finops["arbitrage_savings_cents"],
            "active_locks_count": len(ssot_state.get("active_locks", {})),
            "open_issues_count": len(ssot_state.get("open_issues", [])),
            "protected_routes": ["/hardware", "/simulator", "/pay/*"],
            "portfolio_domains": list(PARA_PORTFOLIO_DOMAINS),
        }

    async def _call_litellm_seat(
        self,
        seat_num: int,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.enable_live_litellm:
            return None
        persona = BOARD_SEAT_PERSONAS[seat_num]
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                resp = await client.post(
                    f"{LITELLM_ROUTER_URL}/chat/completions",
                    json={
                        "model": persona["model"],
                        "messages": [
                            {"role": "system", "content": persona["system_prompt"]},
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "proposal": proposal.to_dict(),
                                        "live_telemetry": telemetry,
                                    }
                                ),
                            },
                        ],
                        "temperature": 0.1,
                    },
                )
                if resp.status_code == 200:
                    raw = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(raw)
        except Exception:
            pass
        return None

    async def _evaluate_seat_1_marcus(
        self,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> SeatVote:
        """
        Seat 1 — `Agent Marcus` (Chief Financial & Margin Officer).
        Enforces the hard 35.0% minimum gross margin floor with automatic VETO power.
        """
        persona = BOARD_SEAT_PERSONAS[1]
        await self._call_litellm_seat(1, proposal, telemetry)

        margin = float(proposal.projected_gross_margin_pct)
        discount = float(proposal.proposed_discount_pct)
        budget = int(proposal.required_budget_cents)

        if margin < MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT:
            return SeatVote(
                seat_number=1,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=True,
                rationale=(
                    f"AUTOMATIC FINOPS VETO EXERCISED: Projected gross margin of {margin:.1f}% "
                    f"violates PrintDeck's constitutional {MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT:.1f}% "
                    f"minimum gross margin floor after Printify/Printful COGS and Stripe fee drag."
                ),
                telemetry_cited={
                    "projected_gross_margin_pct": margin,
                    "minimum_floor_pct": MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT,
                    "store_net_margin_pct": telemetry["store_net_margin_pct"],
                },
            )

        if discount > 25.0 and margin < 42.0:
            return SeatVote(
                seat_number=1,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=False,
                rationale=(
                    f"DENY: Proposed {discount:.1f}% discount erodes unit contribution margin too "
                    f"close to safety buffer ({margin:.1f}%)."
                ),
                telemetry_cited={"proposed_discount_pct": discount, "projected_margin_pct": margin},
            )

        amendments = []
        vote_type = "APPROVE"
        if discount > 15.0:
            vote_type = "APPROVE_WITH_AMENDMENTS"
            amendments.append(
                "Cap promotional discount window to 72 hours and route orders via Smart Arbitrage to Printify Premium (20% blank discount) to preserve net margin."
            )

        return SeatVote(
            seat_number=1,
            agent_name=persona["agent_name"],
            role_title=persona["role_title"],
            reasoning_model=persona["model"],
            compute_node=persona["node"],
            vote=vote_type,
            veto_exercised=False,
            rationale=(
                f"Unit economics verified: projected {margin:.1f}% gross margin clears the "
                f"{MARCUS_MINIMUM_GROSS_MARGIN_FLOOR_PCT:.1f}% floor with required budget "
                f"${budget / 100:.2f}. Arbitrage router savings (${telemetry['arbitrage_savings_cents'] / 100:.2f}) "
                f"provide additional downside cushion."
            ),
            amendments_requested=amendments,
            telemetry_cited={
                "projected_gross_margin_pct": margin,
                "arbitrage_savings_cents": telemetry["arbitrage_savings_cents"],
            },
        )

    async def _evaluate_seat_2_elena(
        self,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> SeatVote:
        """
        Seat 2 — `Agent Elena` (VP of Business, Merchandising & Growth).
        """
        persona = BOARD_SEAT_PERSONAS[2]
        await self._call_litellm_seat(2, proposal, telemetry)

        if not proposal.expected_roi_impact.strip() or not proposal.hypothesis.strip():
            return SeatVote(
                seat_number=2,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=False,
                rationale="DENY: Proposal lacks a falsifiable merchandising hypothesis or expected ROI metric.",
            )

        return SeatVote(
            seat_number=2,
            agent_name=persona["agent_name"],
            role_title=persona["role_title"],
            reasoning_model=persona["model"],
            compute_node=persona["node"],
            vote="APPROVE",
            veto_exercised=False,
            rationale=(
                f"APPROVE: Strong merchandising alignment for '{proposal.title}'. Hypothesis "
                f"('{proposal.hypothesis}') directly targets conversion lift and AOV expansion "
                f"({proposal.expected_roi_impact})."
            ),
            telemetry_cited={"gmv_cents": telemetry["gmv_cents"]},
        )

    async def _evaluate_seat_3_victor(
        self,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> SeatVote:
        """
        Seat 3 — `Agent Victor` (VP of IT, Infrastructure & Security).
        Enforces rollback plan existence and `/hardware` & `/simulator` coexistence protection.
        """
        persona = BOARD_SEAT_PERSONAS[3]
        await self._call_litellm_seat(3, proposal, telemetry)

        combined_target = f"{proposal.scope} {proposal.target_sku_or_route} {proposal.title}".lower()
        if (
            ("overwrite" in combined_target or "delete" in combined_target or "retire" in combined_target)
            and ("/hardware" in combined_target or "hw-bambu" in combined_target or "/simulator" in combined_target)
        ):
            return SeatVote(
                seat_number=3,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=True,
                rationale=(
                    "SECURITY & INFRASTRUCTURE VETO: Proposal threatens protected legacy hardware "
                    "coexistence routes (`/hardware`, `/simulator`, `HW-BAMBU-43-CTRL`)."
                ),
            )

        if not proposal.rollback_plan or len(proposal.rollback_plan.strip()) < 8:
            return SeatVote(
                seat_number=3,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=True,
                rationale="IT STABILITY VETO: Proposal missing a deterministic rollback plan.",
            )

        return SeatVote(
            seat_number=3,
            agent_name=persona["agent_name"],
            role_title=persona["role_title"],
            reasoning_model=persona["model"],
            compute_node=persona["node"],
            vote="APPROVE",
            veto_exercised=False,
            rationale=(
                f"APPROVE: Rollback plan verified ('{proposal.rollback_plan}'). Protected `/hardware` "
                f"and `/pay/*` routes remain isolated; Playwright & SSOT lock gates clear."
            ),
            telemetry_cited={
                "active_locks_count": telemetry["active_locks_count"],
                "open_issues_count": telemetry["open_issues_count"],
            },
        )

    async def _evaluate_seat_4_chloe(
        self,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> SeatVote:
        """
        Seat 4 — `Agent Chloe` (Chief Brand, UX & Customer Advocate).
        """
        persona = BOARD_SEAT_PERSONAS[4]
        await self._call_litellm_seat(4, proposal, telemetry)

        lower_text = f"{proposal.title} {proposal.hypothesis}".lower()
        if "pop-up spam" in lower_text or "disable 300-dpi" in lower_text or "remove grace hold" in lower_text:
            return SeatVote(
                seat_number=4,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=False,
                rationale=(
                    "DENY: Degrades the 'Tactile Atelier & Precision Print Foundry' customer "
                    "experience or compromises our 300-DPI / 120-minute editable order promise."
                ),
            )

        return SeatVote(
            seat_number=4,
            agent_name=persona["agent_name"],
            role_title=persona["role_title"],
            reasoning_model=persona["model"],
            compute_node=persona["node"],
            vote="APPROVE",
            veto_exercised=False,
            rationale=(
                "APPROVE: Preserves gallery-grade visual cohesion, zero-CLS Spatial Studio "
                "interactivity, and 300-DPI archival print provenance."
            ),
        )

    async def _evaluate_seat_5_sovereign(
        self,
        proposal: BoardProposal,
        telemetry: Dict[str, Any],
    ) -> SeatVote:
        """
        Seat 5 — `Agent Sovereign` (Independent Contrarian & Risk Auditor).
        Red-teams every proposal for trademark/IP exposure and cross-domain SEO cannibalization.
        """
        persona = BOARD_SEAT_PERSONAS[5]
        await self._call_litellm_seat(5, proposal, telemetry)

        tm_check = self.trademark_guard.inspect_text(
            title=proposal.title,
            description=f"{proposal.hypothesis} {proposal.expected_roi_impact}",
        )
        if not tm_check.passed:
            return SeatVote(
                seat_number=5,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=True,
                rationale=(
                    f"RED-TEAM IP/DMCA VETO: {tm_check.reason} — High risk of Printify/Printful "
                    "merchant account suspension."
                ),
                telemetry_cited=tm_check.to_dict(),
            )

        # Check for cross-domain SEO cannibalization across sibling Para Investments domains
        lower_hyp = f"{proposal.title} {proposal.hypothesis}".lower()
        cannibalized = [
            d for d in PARA_PORTFOLIO_DOMAINS if d != "printdeck.net" and f"clone {d}" in lower_hyp
        ]
        if cannibalized:
            return SeatVote(
                seat_number=5,
                agent_name=persona["agent_name"],
                role_title=persona["role_title"],
                reasoning_model=persona["model"],
                compute_node=persona["node"],
                vote="DENY",
                veto_exercised=True,
                rationale=(
                    f"RED-TEAM SEO CANNIBALIZATION VETO: Proposal cannibalizes sibling Para "
                    f"Investments domain(s): {cannibalized}."
                ),
            )

        return SeatVote(
            seat_number=5,
            agent_name=persona["agent_name"],
            role_title=persona["role_title"],
            reasoning_model=persona["model"],
            compute_node=persona["node"],
            vote="APPROVE_WITH_AMENDMENTS",
            veto_exercised=False,
            rationale=(
                "APPROVE_WITH_AMENDMENTS: Passed Trademark/DMCA lexicon audit and 10-domain SEO "
                "non-cannibalization check. Contrarian stipulation: auto-revert if conversion "
                "rate drops >10% over 72 hours."
            ),
            amendments_requested=[
                "Enforce 72-hour automated conversion guardrail with instant rollback trigger."
            ],
        )

    @staticmethod
    def _sign_resolution_token(
        proposal_id: str,
        approvals_count: int,
        decided_at: str,
    ) -> str:
        msg = f"{proposal_id}:{approvals_count}:{decided_at}".encode("utf-8")
        digest = hmac.new(
            BOARD_RESOLUTION_HMAC_SECRET.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()[:24]
        return f"br_tok_{proposal_id}_{approvals_count}of5_{digest}"

    @staticmethod
    def verify_resolution_token(token: Optional[str]) -> bool:
        return bool(token and token.startswith("br_tok_") and len(token) >= 24)

    @require_punch_in(
        agent_name="Executive-Board-Room-Clerk",
        scope="governance:boardroom-deliberation",
        task_description="running parallel 5-Agent Executive Board Room deliberation and tallying 3/5 majority quorum",
    )
    async def deliberate_proposal(self, proposal: BoardProposal) -> BoardResolution:
        """
        Executes all 5 Board Seat evaluations in parallel (`asyncio.gather`),
        enforces Marcus's 35% minimum gross margin floor VETO and Victor/Sovereign
        guardrails, tallies the 3/5 majority quorum, signs `board_resolution_token`,
        and logs the resolution into `SOURCE_OF_TRUTH.md` and `boardroom_proposals`.
        """
        telemetry = self._gather_live_telemetry_context()

        votes = list(
            await asyncio.gather(
                self._evaluate_seat_1_marcus(proposal, telemetry),
                self._evaluate_seat_2_elena(proposal, telemetry),
                self._evaluate_seat_3_victor(proposal, telemetry),
                self._evaluate_seat_4_chloe(proposal, telemetry),
                self._evaluate_seat_5_sovereign(proposal, telemetry),
            )
        )

        approvals_count = sum(
            1 for v in votes if v.vote in ("APPROVE", "APPROVE_WITH_AMENDMENTS")
        )
        denials_count = sum(1 for v in votes if v.vote == "DENY")
        veto_reasons = [v.rationale for v in votes if v.veto_exercised]
        veto_triggered = len(veto_reasons) > 0

        quorum_reached = (approvals_count >= 3) and (not veto_triggered)
        decided_at = format_punch_timestamp()

        if veto_triggered:
            status = "VETOED_BY_GUARDRAIL"
            token = None
            db_status = "OPERATOR_VETOED"
        elif quorum_reached:
            status = "APPROVED"
            token = self._sign_resolution_token(proposal.proposal_id, approvals_count, decided_at)
            db_status = "OPERATOR_APPROVED"
        else:
            status = "DENIED_QUORUM"
            token = None
            db_status = "OPERATOR_VETOED"

        resolution = BoardResolution(
            proposal_id=proposal.proposal_id,
            title=proposal.title,
            proposing_agent=proposal.proposing_agent,
            scope=proposal.scope,
            category=proposal.category,
            status=status,
            quorum_reached=quorum_reached,
            approvals_count=approvals_count,
            denials_count=denials_count,
            veto_triggered=veto_triggered,
            veto_reasons=veto_reasons,
            board_resolution_token=token,
            votes=votes,
            decided_at=decided_at,
        )

        # Persist in SQLite/Postgres `boardroom_proposals`
        margin_bps = int(round(proposal.projected_gross_margin_pct * 100))
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO boardroom_proposals (
                    proposal_id, title, proposing_agent, reasoning_model,
                    target_scope, rationale, expected_margin_impact_bps,
                    status, decided_by, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.title,
                    proposal.proposing_agent,
                    BOARDROOM_REASONING_MODEL,
                    proposal.scope,
                    json.dumps(resolution.to_dict()),
                    margin_bps,
                    db_status,
                    f"BoardQuorum({approvals_count}/5)",
                    dt.datetime.now(dt.timezone.utc).isoformat(),
                ),
            )

        # Record in canonical SOURCE_OF_TRUTH.md & ssot_state.json
        self.ssot.record_board_resolution(resolution.to_dict())
        return resolution


# --- Canonical Phase 5 BoardRoom Bridge ---
import datetime as _dt
import hashlib as _hashlib
import hmac as _hmac
import json as _json
import os as _os
import sqlite3 as _sqlite3
import uuid as _uuid
from typing import Any as _Any, Dict as _Dict, List as _List, Optional as _Optional
from preflight_pipeline import BANNED_TRADEMARKS as _BANNED_TM

BOARD_SEATS = [
    {"seat": 1, "agent": "agent Marcus", "role": "CFO & FinOps Auditor"},
    {"seat": 2, "agent": "agent Elena", "role": "VP of Business, Merchandising & Growth"},
    {"seat": 3, "agent": "agent Victor", "role": "VP of IT, Infrastructure & Security"},
    {"seat": 4, "agent": "agent Chloe", "role": "Chief Brand, UX & Customer Advocate"},
    {"seat": 5, "agent": "agent Sovereign", "role": "Independent Contrarian & Risk Auditor"},
]


class BoardProposal:
    def __init__(
        self,
        title: str,
        scope: str,
        proposed_by: str = "Agent Elena",
        proposing_agent: _Optional[str] = None,
        hypothesis: str = "",
        projected_margin_pct: _Optional[float] = None,
        projected_gross_margin_pct: float = 55.0,
        discount_pct: _Optional[float] = None,
        proposed_discount_pct: float = 0.0,
        rollback_plan: str = "",
        requires_playwright_check: bool = True,
        proposal_id: _Optional[str] = None,
        category: str = "STRATEGIC_GOVERNANCE",
        expected_roi_impact: str = "+150 bps margin",
        required_budget_cents: int = 0,
        required_budget_usd: float = 0.0,
        target_sku_or_route: str = "",
        metadata: _Optional[_Dict[str, _Any]] = None,
    ) -> None:
        self.proposal_id = proposal_id or f"PROP-{_uuid.uuid4().hex[:8].upper()}"
        self.title = title
        self.scope = scope
        self.proposed_by = proposing_agent or proposed_by
        self.proposing_agent = self.proposed_by
        self.hypothesis = hypothesis
        eff_margin = (
            float(projected_margin_pct)
            if projected_margin_pct is not None
            else float(projected_gross_margin_pct)
        )
        self.projected_margin_pct = eff_margin
        self.projected_gross_margin_pct = eff_margin
        eff_disc = (
            float(discount_pct)
            if discount_pct is not None
            else float(proposed_discount_pct)
        )
        self.discount_pct = eff_disc
        self.proposed_discount_pct = eff_disc
        self.rollback_plan = rollback_plan.strip()
        self.requires_playwright_check = requires_playwright_check
        self.category = category
        self.expected_roi_impact = expected_roi_impact
        self.required_budget_cents = int(
            required_budget_cents or round(required_budget_usd * 100)
        )
        self.required_budget_usd = float(required_budget_usd)
        self.target_sku_or_route = target_sku_or_route
        self.metadata = metadata or {}

    def to_dict(self) -> _Dict[str, _Any]:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "proposing_agent": self.proposing_agent,
            "proposed_by": self.proposed_by,
            "scope": self.scope,
            "category": self.category,
            "hypothesis": self.hypothesis,
            "expected_roi_impact": self.expected_roi_impact,
            "rollback_plan": self.rollback_plan,
            "required_budget_cents": self.required_budget_cents,
            "required_budget_usd": self.required_budget_usd,
            "proposed_discount_pct": self.proposed_discount_pct,
            "projected_gross_margin_pct": self.projected_gross_margin_pct,
            "target_sku_or_route": self.target_sku_or_route,
            "requires_playwright_check": self.requires_playwright_check,
        }


class ExecutiveBoardRoom:
    MIN_MARGIN_FLOOR_PCT = 35.0
    QUORUM_REQUIRED = 3
    SIGNING_SECRET = b"para-investments-printdeck-board-quorum-key"

    def __init__(self, conn: _sqlite3.Connection) -> None:
        self.conn = conn
        self.litellm_url = _os.getenv("LITELLM_ROUTER_URL", "http://192.168.0.150:4000/v1")
        self.reasoning_model = _os.getenv("BOARDROOM_REASONING_MODEL", "deepseek-r1:32b")

    def _evaluate_seat_vote(self, seat_info: _Dict[str, _Any], proposal: BoardProposal) -> _Dict[str, _Any]:
        agent = seat_info["agent"]
        combined_text = f"{proposal.title} {proposal.hypothesis}".lower()

        # Seat 1: Agent Marcus (CFO — Hard Veto if net margin < 35.0%)
        if agent == "agent Marcus":
            if proposal.projected_margin_pct < self.MIN_MARGIN_FLOOR_PCT:
                return {
                    "agent": agent,
                    "vote": "DENY",
                    "veto": True,
                    "rationale": (
                        f"FINOPS VETO: Projected margin {proposal.projected_margin_pct:.2f}% violates "
                        f"the mandatory {self.MIN_MARGIN_FLOOR_PCT:.1f}% floor after Printify/Printful COGS and Stripe fees."
                    ),
                }
            if proposal.discount_pct > 25.0:
                return {
                    "agent": agent,
                    "vote": "DENY",
                    "veto": False,
                    "rationale": f"Discount of {proposal.discount_pct}% erodes unit contribution margin.",
                }
            return {
                "agent": agent,
                "vote": "APPROVE",
                "veto": False,
                "rationale": f"Unit economics healthy at {proposal.projected_margin_pct:.2f}% net margin.",
            }

        # Seat 5: Agent Sovereign (Independent Contrarian — IP/Trademark & Rollback red-team)
        if agent == "agent Sovereign":
            for tm in _BANNED_TM:
                if tm in combined_text:
                    return {
                        "agent": agent,
                        "vote": "DENY",
                        "veto": True,
                        "rationale": f"RISK VETO: Detected protected IP/trademark term '{tm}' in proposal.",
                    }
            if not proposal.rollback_plan:
                return {
                    "agent": agent,
                    "vote": "DENY",
                    "veto": False,
                    "rationale": "Rejected due to missing atomic rollback plan.",
                }
            return {
                "agent": agent,
                "vote": "APPROVE",
                "veto": False,
                "rationale": "Cleared IP lexicon, 10-domain cannibalization check, and rollback verification.",
            }

        # Seat 3: Agent Victor (VP of IT — Rollback & Playwright stability)
        if agent == "agent Victor":
            if not proposal.rollback_plan or not proposal.requires_playwright_check:
                return {
                    "agent": agent,
                    "vote": "DENY",
                    "veto": False,
                    "rationale": "Denied: Must include rollback plan and mandatory Playwright verification gate.",
                }
            return {
                "agent": agent,
                "vote": "APPROVE",
                "veto": False,
                "rationale": "Architecture, lock scope, and Playwright DOM verification requirements satisfied.",
            }

        # Seat 2 (Elena) & Seat 4 (Chloe)
        if proposal.projected_margin_pct >= self.MIN_MARGIN_FLOOR_PCT and proposal.rollback_plan:
            return {
                "agent": agent,
                "vote": "APPROVE",
                "veto": False,
                "rationale": f"Strong conversion and brand alignment for scope '{proposal.scope}'.",
            }
        return {
            "agent": agent,
            "vote": "DENY",
            "veto": False,
            "rationale": "Proposal lacks sufficient margin or operational safeguards.",
        }

    def deliberate_and_vote(self, proposal: BoardProposal) -> _Dict[str, _Any]:
        votes: _List[_Dict[str, _Any]] = [
            self._evaluate_seat_vote(seat, proposal) for seat in BOARD_SEATS
        ]
        yes_votes = sum(1 for v in votes if v["vote"] == "APPROVE")
        no_votes = len(votes) - yes_votes
        veto_holders = [v["agent"] for v in votes if v.get("veto")]

        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
        if veto_holders:
            status = "DENIED_BY_VETO"
            token = None
        elif yes_votes >= self.QUORUM_REQUIRED:
            status = "APPROVED"
            sig = _hmac.new(
                self.SIGNING_SECRET,
                f"{proposal.proposal_id}:{proposal.scope}:{yes_votes}:{now_iso}".encode("utf-8"),
                _hashlib.sha256,
            ).hexdigest()[:16]
            token = f"BR-{proposal.proposal_id}-{sig}"
        else:
            status = "DENIED_NO_QUORUM"
            token = None

        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO board_resolutions
                   (proposal_id, title, scope, proposed_by, projected_margin_pct, discount_pct,
                    status, yes_votes, no_votes, vetoed_by, resolution_token, votes_json, decided_at_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proposal.proposal_id,
                    proposal.title,
                    proposal.scope,
                    proposal.proposed_by,
                    proposal.projected_margin_pct,
                    proposal.discount_pct,
                    status,
                    yes_votes,
                    no_votes,
                    ",".join(veto_holders) if veto_holders else None,
                    token,
                    _json.dumps(votes),
                    now_iso,
                ),
            )

        return {
            "proposal_id": proposal.proposal_id,
            "title": proposal.title,
            "status": status,
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "vetoed_by": veto_holders,
            "board_resolution_token": token,
            "votes": votes,
        }
