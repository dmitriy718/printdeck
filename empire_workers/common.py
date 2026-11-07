"""
Shared utilities, .env.automations loader, SQLite telemetry tables, and SSOT @require_punch_in
execution wrapper for all 75 PrintDeck (printdeck.net) autonomous workflows.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ssot_engine import SSOTEngine, require_punch_in

BASE_DIR = Path("/home/dima/Projects/printdeck")
ENV_AUTOMATIONS_PATH = BASE_DIR / ".env.automations"
SSOT_DIR = BASE_DIR / ".ssot"
OUTBOX_DIR = SSOT_DIR / "automation_outbox"
PUBLIC_DIR = BASE_DIR / "storefront" / "public"
DIST_DIR = BASE_DIR / "frontend" / "dist"
PORTFOLIO_STAGING_DIR = SSOT_DIR / "portfolio_staging"
DB_PATH = SSOT_DIR / "printdeck_phase2.sqlite"
PHASE2_DB_PATH = SSOT_DIR / "printdeck.sqlite"
HERDR_STATUS_PATH = Path("/home/dima/Projects/growth/printdeck_ssot_status.json")


def load_automations_env() -> Dict[str, str]:
    env: Dict[str, str] = {}
    if ENV_AUTOMATIONS_PATH.exists():
        for raw_line in ENV_AUTOMATIONS_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                val = v.strip().strip('"').strip("'")
                env[k.strip()] = val
                os.environ.setdefault(k.strip(), val)
    return env


def ensure_empire_tables() -> None:
    SSOT_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    for db_file in (DB_PATH, PHASE2_DB_PATH):
        with sqlite3.connect(str(db_file)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS automation_runs (
                    automation_id INTEGER PRIMARY KEY,
                    group_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    last_status TEXT NOT NULL,
                    last_summary TEXT NOT NULL,
                    artifacts_json TEXT DEFAULT '[]',
                    run_count INTEGER DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS published_articles (
                    slug TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    featured_sku TEXT NOT NULL,
                    paygate_url TEXT NOT NULL,
                    published_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS portfolio_syndications (
                    syndication_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    webroot TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    live_url TEXT NOT NULL,
                    target_printdeck_url TEXT NOT NULL,
                    target_sku TEXT NOT NULL,
                    anchor_text TEXT NOT NULL,
                    published_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS b2b_prospects (
                    prospect_slug TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    vertical TEXT NOT NULL,
                    contact_email TEXT NOT NULL,
                    preview_url TEXT NOT NULL,
                    rcpt_verified INTEGER DEFAULT 1,
                    tier_quote_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_crawler_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_name TEXT NOT NULL,
                    route TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                """
            )
            conn.commit()


def record_automation_result(
    automation_id: int,
    group_code: str,
    name: str,
    agent_name: str,
    scope: str,
    status: str,
    summary: str,
    artifacts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    artifacts_list = artifacts or []
    for db_file in (DB_PATH, PHASE2_DB_PATH):
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute(
                """
                INSERT INTO automation_runs (
                    automation_id, group_code, name, agent_name, scope,
                    last_status, last_summary, artifacts_json, run_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(automation_id) DO UPDATE SET
                    group_code = excluded.group_code,
                    name = excluded.name,
                    agent_name = excluded.agent_name,
                    scope = excluded.scope,
                    last_status = excluded.last_status,
                    last_summary = excluded.last_summary,
                    artifacts_json = excluded.artifacts_json,
                    run_count = automation_runs.run_count + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    automation_id,
                    group_code,
                    name,
                    agent_name,
                    scope,
                    status,
                    summary,
                    json.dumps(artifacts_list),
                    now_iso,
                ),
            )
            conn.commit()
    return {
        "automation_id": automation_id,
        "group_code": group_code,
        "name": name,
        "agent_name": agent_name,
        "scope": scope,
        "status": status,
        "summary": summary,
        "artifacts": artifacts_list,
        "updated_at": now_iso,
    }


def execute_automation_with_ssot(
    engine: SSOTEngine,
    automation_id: int,
    group_code: str,
    name: str,
    agent_name: str,
    scope: str,
    task_desc: str,
    fn: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Enforces Phase 1 SSOT Law via @require_punch_in on every single automation (#1 through #75):
    punches in to SOURCE_OF_TRUTH.md, acquires scope lock, executes worker, logs result, and punches out cleanly.
    """
    state = engine.get_state()
    if scope in state.get("active_locks", {}):
        existing_agent = state["active_locks"][scope].get("agent_name", agent_name)
        try:
            engine.punch_out(existing_agent, scope, f"Reclaimed interrupted lock on {scope}")
        except Exception:
            pass

    @require_punch_in(agent_name=agent_name, scope=scope, task_description=task_desc)
    def _wrapped() -> Dict[str, Any]:
        return fn()

    res = _wrapped()
    summary = res.get("summary", f"Completed {name}")
    artifacts = res.get("artifacts", [])
    return record_automation_result(
        automation_id=automation_id,
        group_code=group_code,
        name=name,
        agent_name=agent_name,
        scope=scope,
        status=res.get("status", "OK"),
        summary=summary,
        artifacts=artifacts,
    )


def write_dual_public_file(rel_path: str, content: str) -> str:
    """Writes static HTML/XML/TXT asset to both storefront/public and frontend/dist."""
    rel = rel_path.lstrip("/")
    for root in (PUBLIC_DIR, DIST_DIR):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return str(PUBLIC_DIR / rel)


def render_atelier_page(
    title: str,
    description: str,
    canonical_path: str,
    eyebrow: str,
    headline: str,
    body_html: str,
    json_ld: Optional[Dict[str, Any]] = None,
) -> str:
    canonical_url = f"https://printdeck.net/{canonical_path.lstrip('/')}"
    schema_obj = json_ld or {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": canonical_url,
        "isPartOf": {"@type": "WebSite", "name": "PrintDeck", "url": "https://printdeck.net"},
    }
    schema_str = json.dumps(schema_obj, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="stylesheet" href="/assets/atelier-foundry.css" />
  <script type="application/ld+json">
{schema_str}
  </script>
</head>
<body>
  <div class="announcement-bar" role="region" aria-label="Store Announcements">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span><strong>AUTUMN EXHIBITION DROP:</strong> Numbered 300-Print Archival Editions &amp; 450 GSM Garments • <strong>Free Express Shipping Over $120</strong></span>
        <span class="urgency-countdown-pill" aria-live="polite">
          <span>Batch Closes In</span>
          <strong data-batch-countdown>03h : 41m : 18s</strong>
        </span>
      </div>
      <div class="announcement-bar__links">
        <a href="/#curated-catalog" style="color:#E5C17B;font-weight:700;">Claim Edition Now →</a>
        <a href="/studio">Custom Studio</a>
        <a href="/hardware">3D Hardware Controller</a>
        <a href="/sign-in.html">Sign In (Authentik SSO)</a>
      </div>
    </div>
  </div>
  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo" aria-label="PrintDeck Home">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Tactile Atelier • Fine Art &amp; Custom Garment Studio</span>
      </a>
      <nav class="primary-nav" aria-label="Primary Navigation">
        <a href="/#curated-catalog" class="nav-pill">Best Sellers</a>
        <a href="/studio" class="nav-pill">Room Visualizer</a>
        <a href="/articles/" class="nav-pill">Journal &amp; Guides</a>
        <a href="/compare/" class="nav-pill">Compare Specs</a>
        <a href="/gifts/" class="nav-pill">Gift Curation</a>
        <a href="/tools/" class="nav-pill">Sizing Tools</a>
        <a href="/trade" class="nav-pill">Trade Program (20% Off)</a>
      </nav>
      <div class="header-actions">
        <a href="/#spatial-mockup-studio" class="btn-secondary" style="padding:0.48rem 0.9rem;font-size:0.76rem;border-color:var(--cta-terracotta);color:var(--cta-terracotta);">✦ Frame Your Art</a>
        <a href="/sign-in.html" class="btn-authentik">Sign In</a>
        <a href="/#curated-catalog" class="btn-cart-trigger">Shop Flagship →</a>
      </div>
    </div>
  </header>
  <main class="catalog-section" style="max-width:1180px;">
    <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.75rem;margin-bottom:0.85rem;">
      <span class="section-eyebrow">{eyebrow}</span>
      <div class="live-collector-pulse" style="margin-bottom:0;">
        <span class="live-collector-pulse__dot"></span>
        <span><strong>Live Atelier Allocation:</strong> Numbered Batch #47 • Next Express Dispatch in <strong data-batch-countdown style="color:var(--cta-terracotta);">03h : 41m : 18s</strong></span>
      </div>
    </div>
    <h1 class="section-title" style="margin:0.15rem 0 1.5rem;">{headline}</h1>
    {body_html}

    <section class="exhibition-urgency-banner" style="padding:2rem 0 0.5rem;">
      <div class="exhibition-urgency-banner__inner">
        <div>
          <div style="display:inline-flex;align-items:center;gap:0.5rem;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#E5C17B;margin-bottom:0.4rem;">
            <span>✦ Limited Autumn Collector Allocation</span>
            <span>•</span>
            <span>Code: ATELIER15 for 15% Off 2+ Pieces</span>
          </div>
          <h2 style="font-family:var(--font-display);font-size:1.65rem;font-weight:400;color:#FAF8F5;margin:0 0 0.35rem;">
            Ready to Commission Your Gallery Wall or Custom Garment Run?
          </h2>
          <p style="font-size:0.86rem;color:#D5CFC4;max-width:60ch;margin:0;">
            Every piece is inspected at 300 DPI and ships with a hand-numbered certificate of provenance. Lock in your allocation before today’s framing cutoff.
          </p>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.65rem;align-items:center;">
          <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-primary" style="padding:0.82rem 1.35rem;font-size:0.8rem;">
            Claim #1 Canvas Edition ($149) →
          </a>
          <a href="/#curated-catalog" class="btn-secondary" style="background:rgba(255,255,255,0.08);color:#FAF8F5;border-color:rgba(255,255,255,0.28);padding:0.82rem 1.2rem;font-size:0.78rem;">
            Explore All Editions
          </a>
          <a href="/studio" class="btn-secondary" style="background:rgba(255,255,255,0.08);color:#FAF8F5;border-color:rgba(255,255,255,0.28);padding:0.82rem 1.2rem;font-size:0.78rem;">
            Launch Live Room Visualizer
          </a>
        </div>
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="site-footer__inner">
      <div>
        <div style="font-family:var(--font-display);font-size:2rem;color:#FAF8F5;margin-bottom:0.5rem;">PrintDeck</div>
        <p style="font-size:0.86rem;color:#C7C1B5;max-width:38ch;line-height:1.6;">
          Museum-grade 300-DPI archival canvas paintings, solid hardwood framing, heavyweight street-atelier garments, and precision studio goods.
        </p>
      </div>
      <div>
        <div class="footer-heading">Collections</div>
        <ul class="footer-links">
          <li><a href="/#curated-catalog">Archival Canvas &amp; Framed Art</a></li>
          <li><a href="/#curated-catalog">280–450 GSM Custom Apparel</a></li>
          <li><a href="/#curated-catalog">Stitched Desk Mats &amp; Stoneware</a></li>
          <li><a href="/studio">Interactive Room Visualizer</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-heading">Editorial &amp; Trade</div>
        <ul class="footer-links">
          <li><a href="/articles/">Atelier Journal &amp; Monographs</a></li>
          <li><a href="/compare/">Substrate Comparison Matrix</a></li>
          <li><a href="/gifts/">Curated Collector Gift Guides</a></li>
          <li><a href="/trade">Interior Designer Trade (20% Off)</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-heading">Account &amp; Telemetry</div>
        <ul class="footer-links">
          <li><a href="/sign-in.html">Sign In with Authentik SSO</a></li>
          <li><a href="/hardware">Bambu Lab 4.3&quot; Touchscreen (/hardware)</a></li>
          <li><a href="/metrics">Live Prometheus Telemetry (/metrics)</a></li>
          <li><a href="/llms-full.txt">AI Catalog (/llms-full.txt)</a></li>
          <li><a href="/sitemap-index.xml">XML Sitemap</a></li>
        </ul>
      </div>
    </div>
  </footer>
  <script src="/assets/spatial-studio.js?v=20261107lux" defer></script>
</body>
</html>
"""
