#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/dima/Projects/printdeck"
SSOT_DIR="${PROJECT_ROOT}/.ssot"
SYSTEMD_DIR="${PROJECT_ROOT}/systemd"

mkdir -p "${SSOT_DIR}" "${SYSTEMD_DIR}"

# ------------------------------------------------------------------------------
# 1. requirements.txt
# ------------------------------------------------------------------------------
cat << 'EOF' > "${PROJECT_ROOT}/requirements.txt"
redis>=5.0.0
nats-py>=2.7.0
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.7.0
python-dotenv>=1.0.1
httpx>=0.27.0
EOF

# ------------------------------------------------------------------------------
# 2. Initial Canonical .ssot/SOURCE_OF_TRUTH.md
# ------------------------------------------------------------------------------
cat << 'EOF' > "${SSOT_DIR}/SOURCE_OF_TRUTH.md"
# PRINTDECK (printdeck.net) — SINGLE SOURCE OF TRUTH (SSOT)
> **Canonical Authority**: This file and its atomic mirror (`ssot_state.json`) are the ONE and ONLY source of truth for `printdeck.net`.
> **Mandatory Rule**: Every autonomous agent MUST punch in via `printdeck-ctl punch-in` or `@require_punch_in` before touching any file, database row, or external API, acquiring an exclusive Redis lock on `pi-core` (`192.168.0.155:6379`).

## 1. ENTERPRISE TOPOLOGY & PROTECTED ROUTES
- **Public Production Edge**: `novahorizon` (`100.66.219.67`) -> `/var/www/printdeck` (`caddy.service`)
- **Payment & Intake Gateways**: `para-paygate.service` (`127.0.0.1:8790`) | `para-intake.service` (`127.0.0.1:8787`)
- **Legacy Hardware Coexistence (DO NOT OVERWRITE)**:
  - `/hardware` & `/simulator` -> Reserved for PrintDeck Bambu Lab 4.3" ESP32-P4 Touchscreen Controller, $19 Maker Pack, and $50 Beta Hardware Deposit.
- **POD Storefront Routes**:
  - `/` -> PrintDeck Custom Fine Art Paintings, Apparel & Memorabilia Storefront
  - `/studio` -> Interactive Spatial Mockup & 300-DPI Live Customizer
  - `/admin` -> Executive Command Center, Mass Inventory Uploader, CRM & SEO/FinOps Telemetry
  - `/llms.txt` & `/llms-full.txt` -> AI Shopping & GEO Structured Catalog

## 2. ACTIVE LOCK TABLE (REAL-TIME MUTEX)
| Scope | Locked By | Punch-In Timestamp | Lease Expires (UTC) | Task Summary |
| :--- | :--- | :--- | :--- | :--- |
| _None_ | _Unlocked_ | - | - | All scopes currently available |

---

## 3. PUNCH CLOCK LOG
12/24/2026 [9:26:01 AM] agent Jennifer - fixing the broken bottom footer about us link
12/24/2026 [12:02:01 PM] agent Jennifer - fixed broken footer link, but noticed that the contact form isn't working

---

## 4. OPEN ISSUES:
- **[ISS-0002]** | **Severity**: `HIGH` | **Scope**: `ui:contact-form`
  - **Opened When**: 12/24/2026 [12:02:01 PM]
  - **Opened By**: `agent Jennifer`
  - **How / Why Opened**: Auto-extracted on punch-out from `ui:footer` after agent Jennifer reported: "noticed that the contact form isn't working". Contact form submission handler requires endpoint verification against `para-intake.service` (`127.0.0.1:8787`).

---

## 5. CLOSED ISSUES:
- **[ISS-0001]** | **Severity**: `MEDIUM` | **Scope**: `ui:footer`
  - **Opened When**: 12/24/2026 [9:15:00 AM] | **Opened By**: `agent Portfolio-Steward`
  - **How / Why Opened**: 404 detected on bottom footer About Us anchor link during scheduled domain health probe.
  - **Closed When**: 12/24/2026 [12:02:01 PM] | **Closed By**: `agent Jennifer`
  - **How / Why Closed**: Fixed broken footer link href in footer component and verified HTTP 200 response (`fixed broken footer link, but noticed that the contact form isn't working`).
EOF

# Create visible root symlink so operator sees SOURCE_OF_TRUTH.md immediately
ln -sf "${SSOT_DIR}/SOURCE_OF_TRUTH.md" "${PROJECT_ROOT}/SOURCE_OF_TRUTH.md"

# ------------------------------------------------------------------------------
# 3. Initial Canonical .ssot/ssot_state.json
# ------------------------------------------------------------------------------
cat << 'EOF' > "${SSOT_DIR}/ssot_state.json"
{
  "site": "printdeck.net",
  "ssot_version": "1.0.0",
  "last_updated": "12/24/2026 [12:02:01 PM]",
  "active_locks": {},
  "punch_log": [
    {
      "timestamp": "12/24/2026 [9:26:01 AM]",
      "agent": "agent Jennifer",
      "event": "PUNCH_IN",
      "scope": "ui:footer",
      "message": "fixing the broken bottom footer about us link",
      "raw_line": "12/24/2026 [9:26:01 AM] agent Jennifer - fixing the broken bottom footer about us link"
    },
    {
      "timestamp": "12/24/2026 [12:02:01 PM]",
      "agent": "agent Jennifer",
      "event": "PUNCH_OUT",
      "scope": "ui:footer",
      "message": "fixed broken footer link, but noticed that the contact form isn't working",
      "raw_line": "12/24/2026 [12:02:01 PM] agent Jennifer - fixed broken footer link, but noticed that the contact form isn't working"
    }
  ],
  "open_issues": [
    {
      "id": "ISS-0002",
      "severity": "HIGH",
      "scope": "ui:contact-form",
      "opened_at": "12/24/2026 [12:02:01 PM]",
      "opened_by": "agent Jennifer",
      "how_why_opened": "Auto-extracted on punch-out from ui:footer: noticed that the contact form isn't working"
    }
  ],
  "closed_issues": [
    {
      "id": "ISS-0001",
      "severity": "MEDIUM",
      "scope": "ui:footer",
      "opened_at": "12/24/2026 [9:15:00 AM]",
      "opened_by": "agent Portfolio-Steward",
      "how_why_opened": "404 detected on bottom footer About Us anchor link during scheduled domain health probe.",
      "closed_at": "12/24/2026 [12:02:01 PM]",
      "closed_by": "agent Jennifer",
      "how_why_closed": "fixed broken footer link, but noticed that the contact form isn't working"
    }
  ],
  "issue_counter": 2
}
EOF

# ------------------------------------------------------------------------------
# 4. ssot_engine.py — Distributed Mutex, SSOT Writer & @require_punch_in
# ------------------------------------------------------------------------------
cat << 'EOF' > "${PROJECT_ROOT}/ssot_engine.py"
#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 1 SSOT & Distributed Punch-Clock Engine.
Enforces exclusive scope locking via Redis on pi-core (192.168.0.155:6379),
broadcasts events via NATS JetStream (192.168.0.155:4222), maintains the single
canonical SOURCE_OF_TRUTH.md + ssot_state.json, and syncs with Herdr Control Tower.
"""

from __future__ import annotations
import asyncio
import datetime as dt
import fcntl
import functools
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

try:
    import redis
except ImportError:
    redis = None  # type: ignore

try:
    import nats
except ImportError:
    nats = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env.cluster")

SSOT_DIR = PROJECT_ROOT / ".ssot"
SSOT_MD_PATH = SSOT_DIR / "SOURCE_OF_TRUTH.md"
SSOT_JSON_PATH = SSOT_DIR / "ssot_state.json"
FILE_MUTEX_PATH = SSOT_DIR / ".local_ssot.lock"

REDIS_LOCK_URL = os.getenv("REDIS_LOCK_URL", "redis://192.168.0.155:6379/0")
NATS_JETSTREAM_URL = os.getenv("NATS_JETSTREAM_URL", "nats://192.168.0.155:4222")
HERDR_GROWTH_DIR = Path("/home/dima/Projects/growth")


class ScopeLockedError(RuntimeError):
    """Raised when an agent attempts to work on a scope locked by another agent."""


class UnpunchedExecutionError(RuntimeError):
    """Raised when an agent attempts to execute protected actions without punching in."""


def format_punch_timestamp(now: Optional[dt.datetime] = None) -> str:
    """
    Formats timestamp strictly as: 12/24/2026 [9:26:01 AM]
    """
    now = now or dt.datetime.now()
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    year = f"{now.year:04d}"
    hour_12 = now.hour % 12 or 12
    minute = f"{now.minute:02d}"
    second = f"{now.second:02d}"
    ampm = "AM" if now.hour < 12 else "PM"
    return f"{month}/{day}/{year} [{hour_12}:{minute}:{second} {ampm}]"


def normalize_agent_name(agent_name: str) -> str:
    clean = agent_name.strip()
    if not clean.lower().startswith("agent "):
        return f"agent {clean}"
    return f"agent {clean[6:].strip()}"


class SSOTEngine:
    """
    Manages Redis distributed scope locks, NATS event emission, automatic secondary
    issue extraction on punch-out, stale-lock healing, and Markdown rendering.
    """

    OBSERVATION_PATTERNS = [
        re.compile(r"(?:,\s*|\s+)(?:but|and)?\s*noticed\s+that\s+(.+)$", re.IGNORECASE),
        re.compile(r"(?:,\s*|\s+)however[,:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"(?:;\s*|\.\s+)found\s+(?:issue|bug)[:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"(?:,\s*|\s+)also\s+discovered\s+(.+)$", re.IGNORECASE),
    ]

    def __init__(self) -> None:
        SSOT_DIR.mkdir(parents=True, exist_ok=True)
        self._redis = self._connect_redis()

    def _connect_redis(self) -> Optional[Any]:
        if redis is None:
            return None
        try:
            client = redis.Redis.from_url(
                REDIS_LOCK_URL,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            client.ping()
            return client
        except Exception:
            # Graceful fallback to local fcntl + ssot_state.json lock enforcement
            # when pi-core Redis is unreachable during isolated workstation testing
            return None

    def _emit_nats_event(self, subject: str, payload: Dict[str, Any]) -> None:
        if nats is None:
            return

        async def _pub() -> None:
            try:
                nc = await nats.connect(NATS_JETSTREAM_URL, connect_timeout=1.0)
                await nc.publish(subject, json.dumps(payload).encode("utf-8"))
                await nc.flush(timeout=1.0)
                await nc.close()
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_pub())
        except RuntimeError:
            asyncio.run(_pub())

    def _with_state_lock(self, mutator: Callable[[Dict[str, Any]], Any]) -> Any:
        FILE_MUTEX_PATH.touch(exist_ok=True)
        with open(FILE_MUTEX_PATH, "r+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                if SSOT_JSON_PATH.exists():
                    state = json.loads(SSOT_JSON_PATH.read_text(encoding="utf-8"))
                else:
                    state = {
                        "site": "printdeck.net",
                        "ssot_version": "1.0.0",
                        "last_updated": format_punch_timestamp(),
                        "active_locks": {},
                        "punch_log": [],
                        "open_issues": [],
                        "closed_issues": [],
                        "issue_counter": 0,
                    }
                result = mutator(state)
                state["last_updated"] = format_punch_timestamp()
                SSOT_JSON_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
                self._render_markdown(state)
                self._sync_herdr_control_tower(state)
                return result
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _infer_scope_from_observation(self, text: str, fallback_scope: str) -> str:
        lower = text.lower()
        if "contact" in lower or "form" in lower:
            return "ui:contact-form"
        if "footer" in lower:
            return "ui:footer"
        if "checkout" in lower or "stripe" in lower or "paygate" in lower:
            return "api:checkout"
        if "printify" in lower or "printful" in lower:
            return "api:pod-fulfillment"
        if "chat" in lower or "concierge" in lower:
            return "ui:chat-concierge"
        return f"{fallback_scope}:followup"

    def punch_in(
        self,
        agent_name: str,
        scope: str,
        task_description: str,
        ttl_seconds: int = 900,
        custom_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Punches an agent in, locking `scope` across Redis and ssot_state.json.
        """
        agent = normalize_agent_name(agent_name)
        scope_key = scope.strip()
        redis_key = f"printdeck:lock:{scope_key}"
        token = str(uuid.uuid4())
        now_utc = dt.datetime.now(dt.timezone.utc)
        expires_utc = (now_utc + dt.timedelta(seconds=ttl_seconds)).isoformat()
        ts_str = custom_timestamp or format_punch_timestamp()
        punch_line = f"{ts_str} {agent} - {task_description.strip()}"

        # 1. Check & acquire Redis distributed lock on pi-core (if reachable)
        if self._redis is not None:
            lock_payload = json.dumps(
                {
                    "token": token,
                    "agent": agent,
                    "scope": scope_key,
                    "punched_in_at": ts_str,
                    "expires_utc": expires_utc,
                    "task": task_description.strip(),
                }
            )
            acquired = self._redis.set(redis_key, lock_payload, nx=True, ex=ttl_seconds)
            if not acquired:
                existing_raw = self._redis.get(redis_key)
                existing = json.loads(existing_raw) if existing_raw else {}
                raise ScopeLockedError(
                    f"423 LOCKED: Scope '{scope_key}' is currently locked by "
                    f"{existing.get('agent', 'another agent')} since "
                    f"{existing.get('punched_in_at', 'unknown')} "
                    f"(Task: {existing.get('task', 'N/A')}).Wait for punch-out."
                )

        # 2. Record lock & punch-in entry in canonical SSOT state
        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            active_locks = state.setdefault("active_locks", {})
            if scope_key in active_locks:
                existing = active_locks[scope_key]
                # Check if lease expired locally
                try:
                    exp_dt = dt.datetime.fromisoformat(existing["expires_utc"])
                    if exp_dt > now_utc:
                        raise ScopeLockedError(
                            f"423 LOCKED: Scope '{scope_key}' is locked by "
                            f"{existing['agent']} ({existing['task']})."
                        )
                except ValueError:
                    pass

            lock_record = {
                "token": token,
                "agent": agent,
                "scope": scope_key,
                "punched_in_at": ts_str,
                "expires_utc": expires_utc,
                "task": task_description.strip(),
                "raw_line": punch_line,
            }
            active_locks[scope_key] = lock_record
            state.setdefault("punch_log", []).append(
                {
                    "timestamp": ts_str,
                    "agent": agent,
                    "event": "PUNCH_IN",
                    "scope": scope_key,
                    "message": task_description.strip(),
                    "raw_line": punch_line,
                }
            )
            return lock_record

        record = self._with_state_lock(_mutate)
        self._emit_nats_event("printdeck.punch.in", record)
        return record

    def punch_out(
        self,
        agent_name: str,
        scope: str,
        resolution_summary: str,
        close_issue_id: Optional[str] = None,
        token: Optional[str] = None,
        custom_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Punches an agent out, releasing the Redis and SSOT scope lock, closing any
        resolved issue, and automatically opening new issues if secondary bugs
        were noted in `resolution_summary`.
        """
        agent = normalize_agent_name(agent_name)
        scope_key = scope.strip()
        redis_key = f"printdeck:lock:{scope_key}"
        ts_str = custom_timestamp or format_punch_timestamp()
        punch_line = f"{ts_str} {agent} - {resolution_summary.strip()}"

        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            active_locks = state.setdefault("active_locks", {})
            current_lock = active_locks.get(scope_key)
            if current_lock:
                if current_lock["agent"].lower() != agent.lower():
                    raise ScopeLockedError(
                        f"Cannot punch out: Scope '{scope_key}' is owned by "
                        f"{current_lock['agent']}, not {agent}."
                    )
                if token and current_lock.get("token") != token:
                    raise ScopeLockedError("Invalid lock token provided for punch-out.")
                del active_locks[scope_key]

            state.setdefault("punch_log", []).append(
                {
                    "timestamp": ts_str,
                    "agent": agent,
                    "event": "PUNCH_OUT",
                    "scope": scope_key,
                    "message": resolution_summary.strip(),
                    "raw_line": punch_line,
                }
            )

            # 1. Close primary issue if specified or matched by scope
            closed_issue_obj = None
            open_issues: List[Dict[str, Any]] = state.setdefault("open_issues", [])
            remaining_issues: List[Dict[str, Any]] = []
            for issue in open_issues:
                should_close = False
                if close_issue_id and issue["id"].upper() == close_issue_id.upper():
                    should_close = True
                elif not close_issue_id and issue["scope"] == scope_key and closed_issue_obj is None:
                    should_close = True

                if should_close and closed_issue_obj is None:
                    closed_issue_obj = {
                        **issue,
                        "closed_at": ts_str,
                        "closed_by": agent,
                        "how_why_closed": resolution_summary.strip(),
                    }
                    state.setdefault("closed_issues", []).insert(0, closed_issue_obj)
                else:
                    remaining_issues.append(issue)
            state["open_issues"] = remaining_issues

            # 2. Check if punch-out summary contains a secondary bug observation
            # e.g. "fixed broken footer link, but noticed that the contact form isn't working"
            auto_opened_issue = None
            for pattern in self.OBSERVATION_PATTERNS:
                match = pattern.search(resolution_summary.strip())
                if match:
                    observation_text = match.group(1).strip()
                    next_num = int(state.get("issue_counter", 0)) + 1
                    state["issue_counter"] = next_num
                    new_issue_id = f"ISS-{next_num:04d}"
                    inferred_scope = self._infer_scope_from_observation(observation_text, scope_key)
                    auto_opened_issue = {
                        "id": new_issue_id,
                        "severity": "HIGH",
                        "scope": inferred_scope,
                        "opened_at": ts_str,
                        "opened_by": agent,
                        "how_why_opened": (
                            f"Auto-extracted on punch-out from {scope_key}: "
                            f"{observation_text}"
                        ),
                    }
                    state["open_issues"].append(auto_opened_issue)
                    break

            return {
                "punch_out_line": punch_line,
                "released_scope": scope_key,
                "closed_issue": closed_issue_obj,
                "auto_opened_issue": auto_opened_issue,
            }

        result = self._with_state_lock(_mutate)

        # Release Redis lock on pi-core
        if self._redis is not None:
            try:
                self._redis.delete(redis_key)
            except Exception:
                pass

        self._emit_nats_event("printdeck.punch.out", result)
        if result.get("auto_opened_issue"):
            self._emit_nats_event("printdeck.issues.opened", result["auto_opened_issue"])
        return result

    def open_issue(
        self,
        agent_name: str,
        scope: str,
        how_why: str,
        severity: str = "MEDIUM",
    ) -> Dict[str, Any]:
        agent = normalize_agent_name(agent_name)
        ts_str = format_punch_timestamp()

        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            next_num = int(state.get("issue_counter", 0)) + 1
            state["issue_counter"] = next_num
            issue = {
                "id": f"ISS-{next_num:04d}",
                "severity": severity.upper(),
                "scope": scope.strip(),
                "opened_at": ts_str,
                "opened_by": agent,
                "how_why_opened": how_why.strip(),
            }
            state.setdefault("open_issues", []).append(issue)
            return issue

        issue = self._with_state_lock(_mutate)
        self._emit_nats_event("printdeck.issues.opened", issue)
        return issue

    def heal_expired_locks(self) -> List[Dict[str, Any]]:
        """
        Sweeps active locks for expired TTL leases (e.g., if an agent crashed mid-task),
        auto-punches them out, and logs an OPEN ISSUE for IT Manager Victor.
        """
        now_utc = dt.datetime.now(dt.timezone.utc)
        ts_str = format_punch_timestamp()

        def _mutate(state: Dict[str, Any]) -> List[Dict[str, Any]]:
            active_locks = state.get("active_locks", {})
            healed: List[Dict[str, Any]] = []
            for scope_key, lock_info in list(active_locks.items()):
                try:
                    exp_dt = dt.datetime.fromisoformat(lock_info["expires_utc"])
                except Exception:
                    continue
                if exp_dt <= now_utc:
                    del active_locks[scope_key]
                    auto_line = (
                        f"{ts_str} {lock_info['agent']} - "
                        f"[SYSTEM AUTO-PUNCH-OUT: LEASE EXPIRED on {scope_key}]"
                    )
                    state.setdefault("punch_log", []).append(
                        {
                            "timestamp": ts_str,
                            "agent": "agent System-Healer",
                            "event": "AUTO_PUNCH_OUT",
                            "scope": scope_key,
                            "message": f"Stale lock revoked from {lock_info['agent']}",
                            "raw_line": auto_line,
                        }
                    )
                    next_num = int(state.get("issue_counter", 0)) + 1
                    state["issue_counter"] = next_num
                    issue = {
                        "id": f"ISS-{next_num:04d}",
                        "severity": "CRITICAL",
                        "scope": scope_key,
                        "opened_at": ts_str,
                        "opened_by": "agent System-Healer",
                        "how_why_opened": (
                            f"Lease expired while {lock_info['agent']} was working on "
                            f"'{lock_info['task']}'. Scope auto-unlocked for safety."
                        ),
                    }
                    state.setdefault("open_issues", []).append(issue)
                    healed.append(issue)
            return healed

        return self._with_state_lock(_mutate)

    def get_state(self) -> Dict[str, Any]:
        if SSOT_JSON_PATH.exists():
            return json.loads(SSOT_JSON_PATH.read_text(encoding="utf-8"))
        return {}

    def _render_markdown(self, state: Dict[str, Any]) -> None:
        locks = state.get("active_locks", {})
        if locks:
            lock_rows = "\n".join(
                f"| `{s}` | `{info['agent']}` | {info['punched_in_at']} | `{info['expires_utc']}` | {info['task']} |"
                for s, info in locks.items()
            )
        else:
            lock_rows = "| _None_ | _Unlocked_ | - | - | All scopes currently available |"

        punch_lines = "\n".join(item["raw_line"] for item in state.get("punch_log", [])[-100:])

        open_issues = state.get("open_issues", [])
        if open_issues:
            open_md = "\n".join(
                f"- **[{i['id']}]** | **Severity**: `{i['severity']}` | **Scope**: `{i['scope']}`\n"
                f"  - **Opened When**: {i['opened_at']}\n"
                f"  - **Opened By**: `{i['opened_by']}`\n"
                f"  - **How / Why Opened**: {i['how_why_opened']}"
                for i in open_issues
            )
        else:
            open_md = "- _No open issues._"

        closed_issues = state.get("closed_issues", [])
        if closed_issues:
            closed_md = "\n".join(
                f"- **[{i['id']}]** | **Severity**: `{i['severity']}` | **Scope**: `{i['scope']}`\n"
                f"  - **Opened When**: {i['opened_at']} | **Opened By**: `{i['opened_by']}`\n"
                f"  - **How / Why Opened**: {i['how_why_opened']}\n"
                f"  - **Closed When**: {i['closed_at']} | **Closed By**: `{i['closed_by']}`\n"
                f"  - **How / Why Closed**: {i['how_why_closed']}"
                for i in closed_issues[:50]
            )
        else:
            closed_md = "- _No closed issues yet._"

        md_content = f"""# PRINTDECK (printdeck.net) — SINGLE SOURCE OF TRUTH (SSOT)
> **Canonical Authority**: This file and its atomic mirror (`ssot_state.json`) are the ONE and ONLY source of truth for `printdeck.net`.
> **Last Updated**: {state.get('last_updated', '')}

## 1. ENTERPRISE TOPOLOGY & PROTECTED ROUTES
- **Public Production Edge**: `novahorizon` (`100.66.219.67`) -> `/var/www/printdeck` (`caddy.service`)
- **Payment & Intake Gateways**: `para-paygate.service` (`127.0.0.1:8790`) | `para-intake.service` (`127.0.0.1:8787`)
- **Legacy Hardware Coexistence (DO NOT OVERWRITE)**:
  - `/hardware` & `/simulator` -> Reserved for PrintDeck Bambu Lab 4.3" ESP32-P4 Touchscreen Controller, $19 Maker Pack, and $50 Beta Hardware Deposit.
- **POD Storefront Routes**:
  - `/` -> PrintDeck Custom Fine Art Paintings, Apparel & Memorabilia Storefront
  - `/studio` -> Interactive Spatial Mockup & 300-DPI Live Customizer
  - `/admin` -> Executive Command Center, Mass Inventory Uploader, CRM & SEO/FinOps Telemetry
  - `/llms.txt` & `/llms-full.txt` -> AI Shopping & GEO Structured Catalog

## 2. ACTIVE LOCK TABLE (REAL-TIME MUTEX)
| Scope | Locked By | Punch-In Timestamp | Lease Expires (UTC) | Task Summary |
| :--- | :--- | :--- | :--- | :--- |
{lock_rows}

---

## 3. PUNCH CLOCK LOG
{punch_lines}

---

## 4. OPEN ISSUES:
{open_md}

---

## 5. CLOSED ISSUES:
{closed_md}
"""
        SSOT_MD_PATH.write_text(md_content, encoding="utf-8")

    def _sync_herdr_control_tower(self, state: Dict[str, Any]) -> None:
        """
        Non-destructively syncs PrintDeck lock & issue telemetry to Herdr Control Tower
        on geekom-gt1 (/home/dima/Projects/growth) if that directory exists.
        """
        try:
            if HERDR_GROWTH_DIR.exists() and HERDR_GROWTH_DIR.is_dir():
                snapshot_file = HERDR_GROWTH_DIR / "printdeck_ssot_status.json"
                snapshot_file.write_text(
                    json.dumps(
                        {
                            "domain": "printdeck.net",
                            "last_updated": state.get("last_updated"),
                            "active_locks_count": len(state.get("active_locks", {})),
                            "active_locks": state.get("active_locks", {}),
                            "open_issues_count": len(state.get("open_issues", [])),
                            "open_issues": state.get("open_issues", []),
                            "latest_punch": (
                                state.get("punch_log", [])[-1]["raw_line"]
                                if state.get("punch_log")
                                else None
                            ),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        except Exception:
            pass


def require_punch_in(
    agent_name: str,
    scope: str,
    task_description: str,
    close_issue_id: Optional[str] = None,
    ttl_seconds: int = 900,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that physically prevents any agent tool or function from executing
    unless it successfully punches in and acquires the scope lock first, and
    guarantees punch-out on completion.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                engine = SSOTEngine()
                lock = engine.punch_in(agent_name, scope, task_description, ttl_seconds=ttl_seconds)
                try:
                    result = await func(*args, **kwargs)
                    summary = (
                        result
                        if isinstance(result, str) and result.strip()
                        else f"completed: {task_description}"
                    )
                    engine.punch_out(
                        agent_name,
                        scope,
                        summary,
                        close_issue_id=close_issue_id,
                        token=lock["token"],
                    )
                    return result
                except Exception as exc:
                    engine.punch_out(
                        agent_name,
                        scope,
                        f"failed during '{task_description}', but noticed that {exc}",
                        token=lock["token"],
                    )
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            engine = SSOTEngine()
            lock = engine.punch_in(agent_name, scope, task_description, ttl_seconds=ttl_seconds)
            try:
                result = func(*args, **kwargs)
                summary = (
                    result
                    if isinstance(result, str) and result.strip()
                    else f"completed: {task_description}"
                )
                engine.punch_out(
                    agent_name,
                    scope,
                    summary,
                    close_issue_id=close_issue_id,
                    token=lock["token"],
                )
                return result
            except Exception as exc:
                engine.punch_out(
                    agent_name,
                    scope,
                    f"failed during '{task_description}', but noticed that {exc}",
                    token=lock["token"],
                )
                raise

        return sync_wrapper

    return decorator
EOF

# ------------------------------------------------------------------------------
# 5. printdeck-ctl — CLI & FastAPI Control Plane Daemon
# ------------------------------------------------------------------------------
cat << 'EOF' > "${PROJECT_ROOT}/printdeck-ctl"
#!/usr/bin/env python3
"""
printdeck-ctl — Operator & Agent CLI for the PrintDeck SSOT Punch-Clock & Issue Ledger.
"""

import argparse
import json
import sys
from ssot_engine import SSOTEngine, ScopeLockedError


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="printdeck-ctl",
        description="PrintDeck (printdeck.net) Single Source of Truth & Punch-Clock CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # status
    sub.add_parser("status", help="Show active locks, recent punches, and open issues")

    # punch-in
    p_in = sub.add_parser("punch-in", help="Punch an agent in and lock a site scope")
    p_in.add_argument("--agent", required=True, help="Agent name, e.g. 'Jennifer'")
    p_in.add_argument("--scope", required=True, help="Scope key, e.g. 'ui:footer'")
    p_in.add_argument("--task", required=True, help="Task description")
    p_in.add_argument("--ttl", type=int, default=900, help="Lock lease TTL in seconds")

    # punch-out
    p_out = sub.add_parser("punch-out", help="Punch an agent out and release scope lock")
    p_out.add_argument("--agent", required=True, help="Agent name, e.g. 'Jennifer'")
    p_out.add_argument("--scope", required=True, help="Scope key, e.g. 'ui:footer'")
    p_out.add_argument("--summary", required=True, help="Work completed & any observations")
    p_out.add_argument("--close-issue", default=None, help="Optional Issue ID to close (e.g. ISS-0001)")

    # open-issue
    p_iss = sub.add_parser("open-issue", help="Manually log a new issue in OPEN ISSUES")
    p_iss.add_argument("--agent", required=True, help="Reporting agent or operator name")
    p_iss.add_argument("--scope", required=True, help="Affected scope")
    p_iss.add_argument("--why", required=True, help="How/why the issue was opened")
    p_iss.add_argument("--severity", default="HIGH", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    # heal
    sub.add_parser("heal", help="Sweep and revoke expired locks, logging critical issues")

    args = parser.parse_args()
    engine = SSOTEngine()

    try:
        if args.cmd == "status":
            state = engine.get_state()
            print(f"=== PRINTDECK SSOT STATUS (Updated: {state.get('last_updated')}) ===")
            print(f"Active Locks ({len(state.get('active_locks', {}))}):")
            for scope, info in state.get("active_locks", {}).items():
                print(f"  [LOCKED] {scope} -> {info['raw_line']}")
            print(f"\nOpen Issues ({len(state.get('open_issues', []))}):")
            for iss in state.get("open_issues", []):
                print(f"  [{iss['id']}] ({iss['severity']}) {iss['scope']} | {iss['opened_by']}: {iss['how_why_opened']}")
            return 0

        if args.cmd == "punch-in":
            rec = engine.punch_in(args.agent, args.scope, args.task, ttl_seconds=args.ttl)
            print(rec["raw_line"])
            return 0

        if args.cmd == "punch-out":
            res = engine.punch_out(args.agent, args.scope, args.summary, close_issue_id=args.close_issue)
            print(res["punch_out_line"])
            if res.get("closed_issue"):
                print(f"  -> Closed Issue: {res['closed_issue']['id']}")
            if res.get("auto_opened_issue"):
                ao = res["auto_opened_issue"]
                print(f"  -> Auto-Opened Secondary Issue: [{ao['id']}] in scope '{ao['scope']}'")
            return 0

        if args.cmd == "open-issue":
            iss = engine.open_issue(args.agent, args.scope, args.why, severity=args.severity)
            print(f"Opened [{iss['id']}] ({iss['severity']}) on {iss['scope']}")
            return 0

        if args.cmd == "heal":
            healed = engine.heal_expired_locks()
            print(f"Healed {len(healed)} expired lock(s).")
            return 0

    except ScopeLockedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

chmod +x "${PROJECT_ROOT}/printdeck-ctl"
chmod +x "${PROJECT_ROOT}/ssot_engine.py"

# ------------------------------------------------------------------------------
# 6. Systemd Timer & Service for Stale-Lock Self-Healing
# ------------------------------------------------------------------------------
cat << 'EOF' > "${SYSTEMD_DIR}/printdeck-ssot-healer.service"
[Unit]
Description=PrintDeck SSOT Stale-Lock Healer & Herdr Sync
After=network.target

[Service]
Type=oneshot
User=dima
WorkingDirectory=/home/dima/Projects/printdeck
ExecStart=/usr/bin/env python3 /home/dima/Projects/printdeck/printdeck-ctl heal
EOF

cat << 'EOF' > "${SYSTEMD_DIR}/printdeck-ssot-healer.timer"
[Unit]
Description=Run PrintDeck SSOT Stale-Lock Healer every 2 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=2min
Unit=printdeck-ssot-healer.service

[Install]
WantedBy=timers.target
EOF

echo "=================================================================="
echo "Phase 1 SSOT files successfully created in ${PROJECT_ROOT}:"
ls -lh "${PROJECT_ROOT}"
echo "=================================================================="
