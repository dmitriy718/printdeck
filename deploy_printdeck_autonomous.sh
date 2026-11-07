#!/usr/bin/env bash
set -euo pipefail
# PrintDeck (printdeck.net) — Master Staging-to-Production Cutover Script
# Preserves /hardware and /simulator on novahorizon (100.66.219.67) while deploying
# the POD Storefront, Spatial Studio, GEO /llms.txt, and Autonomous Agent Fleet.

echo "[1/4] Running Playwright DOM & Route Verification Gate..."
/home/dima/Projects/printdeck/.venv/bin/python -c "from playwright_verifier import PlaywrightDOMVerifier; res = PlaywrightDOMVerifier().verify_storefront_dom_and_routes(['spatial-mockup-studio', '/pay/printdeck-maker-pack']); assert res['passed']; print('  -> Playwright Gate PASSED:', res)"

echo "[2/4] Running A9 ProactiveHunter Synthetic Order Canary Sweep..."
/home/dima/Projects/printdeck/.venv/bin/python -c "from db_schema import init_db; from a9_canary_guard import A9ProactiveHunterGuard; print('  -> Canary Guard:', A9ProactiveHunterGuard(init_db()).purge_synthetic_canary_orders())"

echo "[3/4] Verifying SSOT Lock & Issue Hygiene..."
/home/dima/Projects/printdeck/.venv/bin/python /home/dima/Projects/printdeck/printdeck-ctl status

echo "[4/4] Ready for novahorizon (100.66.219.67:/var/www/printdeck) rsync cutover."
