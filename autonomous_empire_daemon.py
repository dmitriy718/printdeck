#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Master 75-Automation Autonomous Empire Daemon.
Orchestrates all 8 Daemon Groups (Automations 1–75) across geekom-gt1, homeserv,
macmini-ops, mbp-m5pro, omnibook-spark, and public edge novahorizon (100.66.219.67).
Every automation obeys Phase 1 SSOT punch-in/punch-out law via ssot_engine.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from ssot_engine import SSOTEngine
from empire_workers.common import (
    BASE_DIR,
    DB_PATH,
    HERDR_STATUS_PATH,
    PUBLIC_DIR,
    SSOT_DIR,
    ensure_empire_tables,
    load_automations_env,
)
from empire_workers.group_a_omnichannel import run_group_a
from empire_workers.group_b_geo_seo import run_group_b
from empire_workers.group_c_b2b_outbound import run_group_c
from empire_workers.group_d_inventory_flux import run_group_d
from empire_workers.group_e_cro_lifecycle import run_group_e
from empire_workers.group_f_finops_arbitrage import run_group_f
from empire_workers.group_g_concierge_support import run_group_g
from empire_workers.group_h_governance_ops import run_group_h


def sync_storefront_and_ssot_to_novahorizon() -> Dict[str, Any]:
    """Rsyncs storefront/public (excluding /hardware) and .ssot state to novahorizon (100.66.219.67)."""
    cmds = [
        [
            "rsync",
            "-avz",
            "--exclude=hardware",
            f"{PUBLIC_DIR}/",
            "100.66.219.67:/var/www/printdeck/",
        ],
        [
            "rsync",
            "-avz",
            f"{SSOT_DIR}/",
            "100.66.219.67:/home/dima/Projects/printdeck/.ssot/",
        ],
    ]
    statuses = []
    for cmd in cmds:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        statuses.append({"cmd": " ".join(cmd[:4]), "returncode": proc.returncode})
    return {"synced": all(s["returncode"] == 0 for s in statuses), "details": statuses}


def run_all_75_automations(sync_remote: bool = True) -> Dict[str, Any]:
    load_automations_env()
    ensure_empire_tables()
    engine = SSOTEngine()

    all_results: List[Dict[str, Any]] = []
    all_results.extend(run_group_a(engine, sync_remote=sync_remote))
    all_results.extend(run_group_b(engine))
    all_results.extend(run_group_c(engine))
    all_results.extend(run_group_d(engine))
    all_results.extend(run_group_e(engine))
    all_results.extend(run_group_f(engine))
    all_results.extend(run_group_g(engine))
    all_results.extend(run_group_h(engine))

    sync_info = {}
    if sync_remote:
        sync_info = sync_storefront_and_ssot_to_novahorizon()

    summary = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_automations_executed": len(all_results),
        "ok_count": sum(1 for r in all_results if r.get("status") == "OK"),
        "remote_sync": sync_info,
    }
    return {"summary": summary, "results": all_results}


def run_3x_daily_publisher(sync_remote: bool = True) -> Dict[str, Any]:
    load_automations_env()
    ensure_empire_tables()
    engine = SSOTEngine()
    res_a = run_group_a(engine, sync_remote=sync_remote)
    res_b = run_group_b(engine)
    sync_info = sync_storefront_and_ssot_to_novahorizon() if sync_remote else {}
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "executed_count": len(res_a) + len(res_b),
        "remote_sync": sync_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PrintDeck 75-Automation Autonomous Empire Daemon")
    parser.add_argument("--wave1-blitz", action="store_true", help="Run all 75 automations + Wave #1 omnichannel blitz and sync to novahorizon")
    parser.add_argument("--3x-publisher", action="store_true", help="Run Group A + Group B 3x-daily omnichannel & GEO publisher")
    parser.add_argument("--boardroom", action="store_true", help="Run 30-minute Board Room + Manager standup cycle")
    parser.add_argument("--ssot-healer", action="store_true", help="Run 2-minute SSOT stale-lock healer")
    parser.add_argument("--canary-purge", action="store_true", help="Run 5-minute A9 canary purger + external HTTP 200 canary")
    parser.add_argument("--daemon", action="store_true", help="Run continuous 24/7 master orchestration loop")
    parser.add_argument("--no-remote-sync", action="store_true", help="Skip SSH/rsync to novahorizon")
    args = parser.parse_args()

    sync_remote = not args.no_remote_sync
    load_automations_env()
    ensure_empire_tables()
    engine = SSOTEngine()

    if args.wave1_blitz:
        out = run_all_75_automations(sync_remote=sync_remote)
        print(json.dumps(out["summary"], indent=2))
        return 0

    if args.__dict__.get("3x_publisher"):
        out = run_3x_daily_publisher(sync_remote=sync_remote)
        print(json.dumps(out, indent=2))
        return 0

    if args.boardroom:
        res = run_group_h(engine)
        print(json.dumps({"boardroom_cycle": len(res)}, indent=2))
        return 0

    if args.ssot_healer:
        revoked = engine.heal_expired_locks()
        print(json.dumps({"reclaimed_locks": [str(r) for r in revoked]}, indent=2))
        return 0

    if args.canary_purge:
        res_f = run_group_f(engine)
        print(json.dumps({"finops_canary_cycle": len(res_f)}, indent=2))
        return 0

    if args.daemon:
        # Execute immediate startup pass across all 75 automations, then loop every 15 minutes
        run_all_75_automations(sync_remote=sync_remote)
        while True:
            time.sleep(900)
            try:
                run_all_75_automations(sync_remote=sync_remote)
            except Exception as exc:
                sys.stderr.write(f"[empire-daemon] cycle error: {exc}\n")

    out = run_all_75_automations(sync_remote=sync_remote)
    print(json.dumps(out["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
