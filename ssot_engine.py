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

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None):
        import os
        if dotenv_path and Path(dotenv_path).exists():
            for line in Path(dotenv_path).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

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
DEFAULT_HERDR_GROWTH_DIR = HERDR_GROWTH_DIR


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

    def __init__(
        self,
        ssot_md_path: Optional[Path] = None,
        state_dir: Optional[Path] = None,
        herdr_growth_dir: Optional[Path] = None,
    ) -> None:
        self.state_dir = Path(state_dir) if state_dir else SSOT_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ssot_md_path = Path(ssot_md_path) if ssot_md_path else SSOT_MD_PATH
        self.ssot_json_path = (
            (self.state_dir / "ssot_state.json") if state_dir else SSOT_JSON_PATH
        )
        self.file_mutex_path = (
            (self.state_dir / ".local_ssot.lock") if state_dir else FILE_MUTEX_PATH
        )
        self.herdr_growth_dir = Path(herdr_growth_dir) if herdr_growth_dir else HERDR_GROWTH_DIR
        self._is_default_ssot = (ssot_md_path is None and state_dir is None)
        self._redis = self._connect_redis()

    @staticmethod
    def _tcp_reachable(url: str, default_port: int, timeout: float = 0.15) -> bool:
        import socket
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or default_port
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _connect_redis(self) -> Optional[Any]:
        if redis is None or not self._tcp_reachable(REDIS_LOCK_URL, 6379):
            return None
        try:
            client = redis.Redis.from_url(
                REDIS_LOCK_URL,
                decode_responses=True,
                socket_connect_timeout=0.3,
                socket_timeout=0.3,
            )
            client.ping()
            return client
        except Exception:
            return None

    def _emit_nats_event(self, subject: str, payload: Dict[str, Any]) -> None:
        if nats is None or not self._tcp_reachable(NATS_JETSTREAM_URL, 4222):
            return

        async def _pub() -> None:
            try:
                async def _silent_err(e: Exception) -> None:
                    pass
                nc = await nats.connect(
                    NATS_JETSTREAM_URL,
                    connect_timeout=0.3,
                    allow_reconnect=False,
                    max_reconnect_attempts=0,
                    error_cb=_silent_err,
                )
                await nc.publish(subject, json.dumps(payload).encode("utf-8"))
                await nc.flush(timeout=0.3)
                await nc.close()
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_pub())
        except RuntimeError:
            asyncio.run(_pub())

    def _with_state_lock(self, mutator: Callable[[Dict[str, Any]], Any]) -> Any:
        self.file_mutex_path.touch(exist_ok=True)
        with open(self.file_mutex_path, "r+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                if self.ssot_json_path.exists():
                    state = json.loads(self.ssot_json_path.read_text(encoding="utf-8"))
                else:
                    state = {
                        "site": "printdeck.net",
                        "ssot_version": "1.0.0",
                        "last_updated": format_punch_timestamp(),
                        "active_locks": {},
                        "punch_log": [],
                        "open_issues": [],
                        "closed_issues": [],
                        "board_resolutions": [],
                        "issue_counter": 0,
                    }
                result = mutator(state)
                state["last_updated"] = format_punch_timestamp()
                self.ssot_json_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
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
        if self.ssot_json_path.exists():
            return json.loads(self.ssot_json_path.read_text(encoding="utf-8"))
        return {
            "site": "printdeck.net",
            "ssot_version": "1.0.0",
            "active_locks": {},
            "punch_log": [],
            "open_issues": [],
            "closed_issues": [],
            "board_resolutions": [],
            "issue_counter": 0,
        }

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

        board_resolutions = state.get("board_resolutions", [])
        if board_resolutions:
            res_md = "\n".join(
                f"- **[{r['proposal_id']}]** | **Status**: `{r['status']}` | **Quorum**: `{r['approvals_count']}/5` | **Scope**: `{r['scope']}`\n"
                f"  - **Title**: {r['title']}\n"
                f"  - **Resolution Token**: `{r.get('board_resolution_token', 'NONE')}`\n"
                f"  - **Timestamp**: {r['decided_at']}"
                for r in board_resolutions[:25]
            )
        else:
            res_md = "- _No Board Room resolutions recorded yet._"

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

---

## 6. EXECUTIVE BOARD ROOM RESOLUTIONS:
{res_md}
"""
        self.ssot_md_path.write_text(md_content, encoding="utf-8")
        if self._is_default_ssot:
            root_md = PROJECT_ROOT / "SOURCE_OF_TRUTH.md"
            root_md.write_text(md_content, encoding="utf-8")

    def record_board_resolution(self, resolution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a signed 5-Agent Executive Board Room resolution into ssot_state.json
        and renders it into SOURCE_OF_TRUTH.md.
        """
        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            res_list: List[Dict[str, Any]] = state.setdefault("board_resolutions", [])
            res_list.insert(0, resolution)
            return resolution

        rec = self._with_state_lock(_mutate)
        self._emit_nats_event("printdeck.boardroom.resolution", rec)
        return rec

    def _sync_herdr_control_tower(self, state: Dict[str, Any]) -> None:
        """
        Non-destructively syncs PrintDeck lock & issue telemetry to Herdr Control Tower
        on geekom-gt1 (/home/dima/Projects/growth) if that directory exists.
        """
        try:
            if self.herdr_growth_dir.exists() and self.herdr_growth_dir.is_dir():
                snapshot_file = self.herdr_growth_dir / "printdeck_ssot_status.json"
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
                engine = (
                    getattr(args[0], "ssot", None)
                    if args and isinstance(getattr(args[0], "ssot", None), SSOTEngine)
                    else SSOTEngine()
                )
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
            engine = (
                getattr(args[0], "ssot", None)
                if args and isinstance(getattr(args[0], "ssot", None), SSOTEngine)
                else SSOTEngine()
            )
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


def operator_override_punch_in(
    engine: SSOTEngine,
    operator_name: str,
    scope: str,
    task_description: str,
    ttl_seconds: int = 1800,
) -> Dict[str, Any]:
    """
    Acquires a high-priority OPERATOR_OVERRIDE lock for human operator `dima` in `/admin`.
    If an autonomous agent currently holds `scope`, preempts and evicts that agent's lock
    immediately so autonomous agents yield to manual operator edits.
    """
    agent_label = f"agent OPERATOR_OVERRIDE({operator_name.strip()})"
    scope_key = scope.strip()
    redis_key = f"printdeck:lock:{scope_key}"
    token = str(uuid.uuid4())
    now_utc = dt.datetime.now(dt.timezone.utc)
    expires_utc = (now_utc + dt.timedelta(seconds=ttl_seconds)).isoformat()
    ts_str = format_punch_timestamp()
    punch_line = f"{ts_str} {agent_label} - [OPERATOR_OVERRIDE] {task_description.strip()}"

    preempted_agent: Optional[str] = None

    if engine._redis is not None:
        try:
            existing_raw = engine._redis.get(redis_key)
            if existing_raw:
                existing_data = json.loads(existing_raw)
                preempted_agent = existing_data.get("agent")
            lock_payload = json.dumps(
                {
                    "token": token,
                    "agent": agent_label,
                    "priority": "OPERATOR_OVERRIDE",
                    "operator": operator_name.strip(),
                    "scope": scope_key,
                    "punched_in_at": ts_str,
                    "expires_utc": expires_utc,
                    "task": task_description.strip(),
                }
            )
            # Force overwrite (`nx=False`) to preempt any autonomous agent lock
            engine._redis.set(redis_key, lock_payload, ex=ttl_seconds)
        except Exception:
            pass

    def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal preempted_agent
        active_locks = state.setdefault("active_locks", {})
        if scope_key in active_locks:
            prev = active_locks[scope_key]
            preempted_agent = prev.get("agent")
            evict_line = (
                f"{ts_str} {prev.get('agent', 'agent unknown')} - "
                f"[YIELDED TO OPERATOR_OVERRIDE by {operator_name.strip()} on {scope_key}]"
            )
            state.setdefault("punch_log", []).append(
                {
                    "timestamp": ts_str,
                    "agent": prev.get("agent", "agent unknown"),
                    "event": "OPERATOR_PREEMPTED",
                    "scope": scope_key,
                    "message": f"Yielded scope to OPERATOR_OVERRIDE ({operator_name.strip()})",
                    "raw_line": evict_line,
                }
            )

        lock_record = {
            "token": token,
            "agent": agent_label,
            "priority": "OPERATOR_OVERRIDE",
            "operator": operator_name.strip(),
            "preempted_agent": preempted_agent,
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
                "agent": agent_label,
                "event": "OPERATOR_OVERRIDE_PUNCH_IN",
                "scope": scope_key,
                "message": task_description.strip(),
                "raw_line": punch_line,
            }
        )
        return lock_record

    record = engine._with_state_lock(_mutate)
    engine._emit_nats_event("printdeck.punch.operator_override", record)
    return record


def require_operator_override(
    scope: str,
    task_description: str,
    operator_name: str = "dima",
    ttl_seconds: int = 1800,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for `/admin` manual operator actions that acquires an OPERATOR_OVERRIDE
    lock (preempting any autonomous agent on `scope`) and punches out on completion.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        agent_label = f"agent OPERATOR_OVERRIDE({operator_name.strip()})"
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                engine = SSOTEngine()
                lock = operator_override_punch_in(
                    engine, operator_name, scope, task_description, ttl_seconds=ttl_seconds
                )
                try:
                    result = await func(*args, **kwargs)
                    engine.punch_out(
                        agent_label,
                        scope,
                        f"[OPERATOR_OVERRIDE COMPLETED] {task_description}",
                        token=lock["token"],
                    )
                    return result
                except Exception as exc:
                    engine.punch_out(
                        agent_label,
                        scope,
                        f"[OPERATOR_OVERRIDE ABORTED] {task_description} ({exc})",
                        token=lock["token"],
                    )
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            engine = SSOTEngine()
            lock = operator_override_punch_in(
                engine, operator_name, scope, task_description, ttl_seconds=ttl_seconds
            )
            try:
                result = func(*args, **kwargs)
                engine.punch_out(
                    agent_label,
                    scope,
                    f"[OPERATOR_OVERRIDE COMPLETED] {task_description}",
                    token=lock["token"],
                )
                return result
            except Exception as exc:
                engine.punch_out(
                    agent_label,
                    scope,
                    f"[OPERATOR_OVERRIDE ABORTED] {task_description} ({exc})",
                    token=lock["token"],
                )
                raise

        return sync_wrapper

    return decorator

