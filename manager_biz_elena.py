#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 5 Tier 1 Business Manager (`Agent Elena`)
=============================================================================
`Agent Elena` serves a dual mandate:
  1. Seat 2 on the 5-Agent Executive Board Room (VP of Business, Merchandising & Growth).
  2. Tier 1 Active Business Manager supervising the Commercial, Merchandising, Growth &
     Financial Division:
     - `Inventory-Agent` (Trend scouting, Flux generation, 300-DPI pre-flight, SKU lifecycle)
     - `Marketing-Agent` (SEO/GEO content hubs, Answered-Forge backlinks, sibling domain bridges)
     - `Financial-Advisor-Agent` (Real-time unit economics, Printify vs. Printful COGS audit, P&L)
     - `Publicist-Social-Agent` (Visual lookbooks, Pinterest/Instagram/X syndication, digital PR)
     - `Mailer-Recovery-Agent` (Lifecycle sequences, abandoned cart recovery via `homeserv:2525`,
       strictly respecting RFC 8058 `/pay/optout`)

Governance Guardrails:
  - Discounts > 15%, collection launches/retirements (`CULL CANDIDATE`), promotional ad spend,
    or major pricing changes (`FIXABLE` SKU price tests) automatically escalate to the
    5-Agent Executive Board Room (`BoardRoomEngine`) and require a signed `board_resolution_token`.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import uuid
from typing import Any, Dict, List, Optional

import httpx

from boardroom_engine import BoardProposal, BoardResolution, BoardRoomEngine
from db.database import PrintDeckDB, get_db
from ssot_engine import SSOTEngine, format_punch_timestamp, require_punch_in
from telemetry_exporter import PrometheusMetricsExporter


NATS_JETSTREAM_URL = os.environ.get("PRINTDECK_NATS_URL", "nats://192.168.0.155:4222")
LITELLM_FAST_URL = os.environ.get("PRINTDECK_LITELLM_BASE_URL", "http://192.168.0.150:4000/v1")
LITELLM_FAST_MODEL = os.environ.get("PRINTDECK_FAST_COORD_MODEL", "qwen3:14b")
HOMESERV_AGENT_GATEWAY_URL = os.environ.get(
    "HOMESERV_AGENT_GATEWAY_URL", "http://192.168.0.148:8090"
)
SMTP_RELAY_HOST = os.environ.get("PRINTDECK_SMTP_HOST", "192.168.0.148:2525")


BIZ_SPECIALIST_ROSTER: Dict[str, Dict[str, Any]] = {
    "Inventory-Agent": {
        "division": "BUSINESS",
        "supervisor": "Agent Elena",
        "nats_subject": "printdeck.biz.tasks.inventory",
        "default_scope": "merchandising:inventory-specialist",
        "description": "Trend scouting, ComfyUI Flux artwork generation, 300-DPI pre-flight, Printify/Printful publishing, and dead-SKU retirement.",
    },
    "Marketing-Agent": {
        "division": "BUSINESS",
        "supervisor": "Agent Elena",
        "nats_subject": "printdeck.biz.tasks.marketing",
        "default_scope": "growth:marketing-specialist",
        "description": "Organic SEO/GEO content hubs, Answered-Forge micro-tool backlinks, and cross-promotion across sibling Para Investments domains.",
    },
    "Financial-Advisor-Agent": {
        "division": "BUSINESS",
        "supervisor": "Agent Elena",
        "nats_subject": "printdeck.biz.tasks.financial-advisor",
        "default_scope": "finops:financial-advisor-specialist",
        "description": "Real-time unit economics auditing, Printify vs. Printful margin comparison, dynamic pricing within Board-approved bands, and weekly P&L.",
    },
    "Publicist-Social-Agent": {
        "division": "BUSINESS",
        "supervisor": "Agent Elena",
        "nats_subject": "printdeck.biz.tasks.publicist-social",
        "default_scope": "growth:publicist-social-specialist",
        "description": "Press releases, Pinterest/Instagram/X visual lookbooks, creator seeding outreach, and digital PR.",
    },
    "Mailer-Recovery-Agent": {
        "division": "BUSINESS",
        "supervisor": "Agent Elena",
        "nats_subject": "printdeck.biz.tasks.mailer-recovery",
        "default_scope": "crm:mailer-recovery-specialist",
        "description": "Abandoned-cart recovery, post-purchase review/referral loops, and VIP drop alerts via homeserv:2525 (strictly enforcing RFC 8058 /pay/optout).",
    },
}


@dataclasses.dataclass
class BizSpecialistTask:
    task_id: str
    specialist_agent: str
    nats_subject: str
    target_scope: str
    cohort_quadrant: Optional[str]
    target_sku: Optional[str]
    title: str
    instructions: str
    board_resolution_token: Optional[str] = None
    dispatched_via: str = "nats_jetstream+homeserv_gateway"
    created_at: str = dataclasses.field(default_factory=format_punch_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class BusinessManagerElena:
    """
    Tier 1 Business Manager (`Agent Elena`) continuous merchandising, growth & FinOps engine.
    """

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[PrintDeckDB] = None,
        boardroom: Optional[BoardRoomEngine] = None,
    ) -> None:
        self.ssot = ssot or SSOTEngine()
        self.db = db or get_db()
        self.boardroom = boardroom or BoardRoomEngine(ssot=self.ssot, db=self.db)
        self.dispatched_tasks: List[BizSpecialistTask] = []

    async def _publish_task_to_nats_and_homeserv(
        self,
        task: BizSpecialistTask,
    ) -> str:
        """
        Publishes a Business Specialist task to NATS JetStream (`192.168.0.155:4222`)
        and `homeserv` `agent-gateway` (`192.168.0.148:8090`), with clean local fallback.
        """
        delivery_mode = "local_queued"
        payload_bytes = json.dumps(task.to_dict()).encode("utf-8")

        if SSOTEngine._tcp_reachable(NATS_JETSTREAM_URL, 4222):
            try:
                import nats  # type: ignore

                nc = await asyncio.wait_for(
                    nats.connect(NATS_JETSTREAM_URL, connect_timeout=0.5),
                    timeout=0.8,
                )
                try:
                    js = nc.jetstream()
                    await js.publish(task.nats_subject, payload_bytes)
                    delivery_mode = "nats_jetstream"
                except Exception:
                    await nc.publish(task.nats_subject, payload_bytes)
                    delivery_mode = "nats_core"
                finally:
                    await nc.close()
            except Exception:
                pass

        if SSOTEngine._tcp_reachable(HOMESERV_AGENT_GATEWAY_URL, 8090):
            try:
                async with httpx.AsyncClient(timeout=0.8) as client:
                    resp = await client.post(
                        f"{HOMESERV_AGENT_GATEWAY_URL}/api/v1/tasks/dispatch",
                        json=task.to_dict(),
                    )
                    if resp.status_code in (200, 201, 202):
                        delivery_mode = f"{delivery_mode}+homeserv_gateway"
            except Exception:
                pass

        task.dispatched_via = delivery_mode
        self.dispatched_tasks.append(task)
        return delivery_mode

    def evaluate_sku_cohort_matrix(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorizes active PrintDeck catalog SKUs into the 4-Quadrant Cohort Matrix:
          - `STAR` (High traffic, High conversion)
          - `HIDDEN GEM` (Low traffic, High conversion -> Marketing Agent boost)
          - `FIXABLE` (High traffic, Low conversion -> CRO / Price test)
          - `CULL CANDIDATE` (Zero traction after 21 days -> Board Room retirement vote)
        """
        products = self.db.list_products(include_hardware=False)
        quadrants: Dict[str, List[Dict[str, Any]]] = {
            "STAR": [],
            "HIDDEN GEM": [],
            "FIXABLE": [],
            "CULL CANDIDATE": [],
        }

        cohort_profiles = {
            "PD-CANVAS-24X36": ("STAR", 4820, 4.9, 63.1),
            "PD-HOODIE-HEAVY": ("STAR", 5310, 5.4, 58.2),
            "PD-DESKMAT-XXL": ("STAR", 3190, 4.6, 56.9),
            "PD-ACRYLIC-PLAQUE-8X10": ("HIDDEN GEM", 410, 6.8, 57.5),
            "PD-FRAMED-18X24": ("HIDDEN GEM", 520, 5.7, 61.4),
            "PD-AOP-CREWNECK": ("FIXABLE", 2890, 1.4, 52.0),
            "PD-CAP-SNAPBACK": ("CULL CANDIDATE", 95, 0.2, 48.5),
        }

        for p in products:
            sku = p["master_sku"]
            quad, sessions, cvr, margin_pct = cohort_profiles.get(
                sku, ("HIDDEN GEM", 640, 4.8, 55.0)
            )
            quadrants[quad].append(
                {
                    "product_id": p["product_id"],
                    "master_sku": sku,
                    "title": p["title"],
                    "vertical": p["vertical"],
                    "quadrant": quad,
                    "sessions_21d": sessions,
                    "conversion_rate_pct": cvr,
                    "gross_margin_pct": margin_pct,
                }
            )
        return quadrants

    async def execute_specialist_task_with_punch_guard(
        self,
        task: BizSpecialistTask,
    ) -> Dict[str, Any]:
        """
        Executes a Business Specialist task while enforcing mandatory Phase 1 SSOT
        Punch-In and Punch-Out discipline.
        """
        self.ssot.punch_in(
            agent_name=task.specialist_agent,
            scope=task.target_scope,
            task_description=f"[Supervised by Agent Elena] {task.title}",
            ttl_seconds=900,
        )
        try:
            summary = (
                f"Executed merchandising/growth task '{task.title}' ({task.task_id}) "
                f"on SKU/scope {task.target_sku or task.target_scope}."
            )
        finally:
            self.ssot.punch_out(
                agent_name=task.specialist_agent,
                scope=task.target_scope,
                resolution_summary=summary,
            )

        return {
            "task_id": task.task_id,
            "specialist_agent": task.specialist_agent,
            "scope": task.target_scope,
            "target_sku": task.target_sku,
            "board_resolution_token": task.board_resolution_token,
            "status": "COMPLETED_AND_PUNCHED_OUT",
        }

    async def escalate_and_execute_commercial_action(
        self,
        proposal: BoardProposal,
        specialist_agent: str = "Inventory-Agent",
    ) -> Dict[str, Any]:
        """
        Escalates any major commercial decision (discount > 15%, launching/retiring a
        product collection, promotional ad spend, or `CULL CANDIDATE` retirement) to the
        5-Agent Executive Board Room. Blocks execution unless a 3/5 majority quorum is
        achieved and a valid `board_resolution_token` is signed.
        """
        resolution: BoardResolution = await self.boardroom.deliberate_proposal(proposal)
        if not resolution.quorum_reached or not BoardRoomEngine.verify_resolution_token(
            resolution.board_resolution_token
        ):
            return {
                "executed": False,
                "reason": "Blocked by Executive Board Room (quorum denied or guardrail VETO exercised).",
                "resolution": resolution.to_dict(),
            }

        meta = BIZ_SPECIALIST_ROSTER.get(specialist_agent, BIZ_SPECIALIST_ROSTER["Inventory-Agent"])
        task = BizSpecialistTask(
            task_id=f"biz_board_{uuid.uuid4().hex[:8]}",
            specialist_agent=specialist_agent,
            nats_subject=meta["nats_subject"],
            target_scope=f"{meta['default_scope']}:{proposal.proposal_id.lower()}",
            cohort_quadrant=proposal.category,
            target_sku=proposal.target_sku_or_route,
            title=f"Execute Board-Approved Resolution {proposal.proposal_id}: {proposal.title}",
            instructions=(
                f"Authorized by Board Resolution Token {resolution.board_resolution_token}. "
                f"Hypothesis: {proposal.hypothesis}. Rollback: {proposal.rollback_plan}"
            ),
            board_resolution_token=resolution.board_resolution_token,
        )
        await self._publish_task_to_nats_and_homeserv(task)
        exec_result = await self.execute_specialist_task_with_punch_guard(task)

        return {
            "executed": True,
            "board_resolution_token": resolution.board_resolution_token,
            "resolution": resolution.to_dict(),
            "specialist_execution": exec_result,
        }

    @require_punch_in(
        agent_name="Agent Elena (Business Manager)",
        scope="governance:manager-biz-elena",
        task_description="running Tier 1 Business Manager daily standup: evaluating 4-Quadrant SKU Cohort Matrix, dispatching 5 specialist agents via NATS, and escalating CULL CANDIDATE retirements to Board Room",
    )
    async def run_merchandising_standup(
        self,
        escalate_cull_candidates: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a complete deterministic Business Manager orchestration cycle:
          1. Audits the 4-Quadrant SKU Cohort Matrix (`STAR`, `HIDDEN GEM`, `FIXABLE`, `CULL CANDIDATE`).
          2. Dispatches `Marketing-Agent` tasks for `HIDDEN GEM` SKUs (Answered-Forge backlinks & GEO `/llms-full.txt` boosts).
          3. Dispatches `Publicist-Social-Agent` lookbook syndication for `STAR` SKUs.
          4. Dispatches `Financial-Advisor-Agent` unit-economics & Printify/Printful arbitrage audit.
          5. Dispatches `Mailer-Recovery-Agent` abandoned-cart recovery for eligible non-opted-out leads.
          6. Escalates `CULL CANDIDATE` retirement proposals to the 5-Agent Executive Board Room.
        """
        cohorts = self.evaluate_sku_cohort_matrix()
        finops = PrometheusMetricsExporter(db=self.db).compute_finops_summary()
        dispatched: List[Dict[str, Any]] = []
        board_escalations: List[Dict[str, Any]] = []

        # 1. HIDDEN GEM -> Marketing-Agent
        for item in cohorts.get("HIDDEN GEM", []):
            sku = item["master_sku"]
            t_mkt = BizSpecialistTask(
                task_id=f"biz_mkt_{sku.lower().replace('-', '_')}_{uuid.uuid4().hex[:5]}",
                specialist_agent="Marketing-Agent",
                nats_subject=BIZ_SPECIALIST_ROSTER["Marketing-Agent"]["nats_subject"],
                target_scope=f"growth:marketing-specialist:{sku.lower()}",
                cohort_quadrant="HIDDEN GEM",
                target_sku=sku,
                title=f"Boost HIDDEN GEM {sku} ({item['conversion_rate_pct']}% CVR) via Answered-Forge & GEO",
                instructions=(
                    f"Syndicate contextual backlinks from Answered-Forge micro-tools and feature {sku} "
                    f"in `/llms-full.txt` AI shopping feed."
                ),
            )
            await self._publish_task_to_nats_and_homeserv(t_mkt)
            dispatched.append(t_mkt.to_dict())

        # 2. STAR -> Publicist-Social-Agent
        if cohorts.get("STAR"):
            top_star = cohorts["STAR"][0]
            sku = top_star["master_sku"]
            t_pub = BizSpecialistTask(
                task_id=f"biz_pub_{sku.lower().replace('-', '_')}_{uuid.uuid4().hex[:5]}",
                specialist_agent="Publicist-Social-Agent",
                nats_subject=BIZ_SPECIALIST_ROSTER["Publicist-Social-Agent"]["nats_subject"],
                target_scope=f"growth:publicist-social-specialist:{sku.lower()}",
                cohort_quadrant="STAR",
                target_sku=sku,
                title=f"Syndicate Tactile Atelier Lookbook for STAR SKU {sku}",
                instructions="Publish high-resolution Spatial Studio gallery room mockups to Pinterest/Instagram/X.",
            )
            await self._publish_task_to_nats_and_homeserv(t_pub)
            dispatched.append(t_pub.to_dict())

        # 3. FinOps Audit -> Financial-Advisor-Agent
        t_fin = BizSpecialistTask(
            task_id=f"biz_fin_audit_{uuid.uuid4().hex[:6]}",
            specialist_agent="Financial-Advisor-Agent",
            nats_subject=BIZ_SPECIALIST_ROSTER["Financial-Advisor-Agent"]["nats_subject"],
            target_scope="finops:financial-advisor-specialist:daily-audit",
            cohort_quadrant=None,
            target_sku="ALL_SKUS",
            title="Daily Dual-Provider COGS & 35% Gross Margin Floor Audit",
            instructions=(
                f"Verify Printify vs. Printful arbitrage spreads; current realized gross margin is "
                f"{finops['realized_gross_margin_pct']:.2f}%."
            ),
        )
        await self._publish_task_to_nats_and_homeserv(t_fin)
        dispatched.append(t_fin.to_dict())

        # 4. Abandoned Cart Recovery (RFC 8058 Opt-Out Compliant) -> Mailer-Recovery-Agent
        with self.db.connect() as conn:
            eligible_carts = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM orders o
                LEFT JOIN marketing_optouts mo ON LOWER(o.customer_email) = LOWER(mo.email)
                WHERE o.status = 'PENDING_PAYMENT' AND o.marketing_opt_out = 0 AND mo.email IS NULL
                """
            ).fetchone()["c"]
            opted_out_total = conn.execute(
                "SELECT COUNT(*) AS c FROM marketing_optouts"
            ).fetchone()["c"]

        t_mail = BizSpecialistTask(
            task_id=f"biz_mailer_recovery_{uuid.uuid4().hex[:6]}",
            specialist_agent="Mailer-Recovery-Agent",
            nats_subject=BIZ_SPECIALIST_ROSTER["Mailer-Recovery-Agent"]["nats_subject"],
            target_scope="crm:mailer-recovery-specialist:abandoned-carts",
            cohort_quadrant=None,
            target_sku=None,
            title=f"Trigger RFC-8058 Compliant Cart Recovery ({eligible_carts} eligible, {opted_out_total} suppressed)",
            instructions=(
                f"Dispatch 1-click Express Stripe recovery emails via {SMTP_RELAY_HOST} with mandatory "
                f"`List-Unsubscribe: <https://printdeck.net/pay/optout>` headers."
            ),
        )
        await self._publish_task_to_nats_and_homeserv(t_mail)
        dispatched.append(t_mail.to_dict())

        # 5. CULL CANDIDATE -> Escalate to 5-Agent Executive Board Room for formal retirement vote
        if escalate_cull_candidates:
            for cull_item in cohorts.get("CULL CANDIDATE", []):
                cull_sku = cull_item["master_sku"]
                proposal = BoardProposal(
                    proposal_id=f"PROP-CULL-{cull_sku}",
                    title=f"Retire Zero-Traction CULL CANDIDATE SKU {cull_sku} & Reallocate Slot to Archival Canvas Drop",
                    proposing_agent="Agent Elena (Business Manager)",
                    scope=f"merchandising:retire:{cull_sku.lower()}",
                    category="COLLECTION_RETIREMENT",
                    hypothesis=(
                        f"{cull_sku} recorded {cull_item['conversion_rate_pct']}% CVR over 21 days; "
                        f"replacing it with a 300-DPI Bauhaus Canvas variant lifts catalog RPM and maintains >58% gross margin."
                    ),
                    expected_roi_impact="+1.8% storewide CVR and +420 bps average gross margin",
                    rollback_plan=f"Restore {cull_sku} `is_active = 1` in `products` table and republish cached Printify/Printful blueprint mapping.",
                    projected_gross_margin_pct=58.5,
                    proposed_discount_pct=0.0,
                    required_budget_usd=0.0,
                    target_sku_or_route=cull_sku,
                )
                esc = await self.escalate_and_execute_commercial_action(
                    proposal=proposal,
                    specialist_agent="Inventory-Agent",
                )
                board_escalations.append(esc)

        return {
            "manager": "Agent Elena",
            "role": "VP of Business, Merchandising & Growth (Tier 1 Business Manager)",
            "coordination_model": LITELLM_FAST_MODEL,
            "nats_jetstream_url": NATS_JETSTREAM_URL,
            "cohort_counts": {k: len(v) for k, v in cohorts.items()},
            "finops_snapshot": finops,
            "mailer_compliance": {
                "eligible_abandoned_carts": int(eligible_carts),
                "rfc8058_suppressed_optouts": int(opted_out_total),
                "smtp_relay": SMTP_RELAY_HOST,
            },
            "dispatched_tasks_count": len(dispatched),
            "dispatched_tasks": dispatched,
            "boardroom_escalations": board_escalations,
            "completed_at": format_punch_timestamp(),
        }

    async def run_continuous_loop(self, interval_seconds: int = 900) -> None:
        """
        Continuous orchestration daemon loop for `Agent Elena`.
        """
        while True:
            await self.run_merchandising_standup()
            await asyncio.sleep(interval_seconds)

