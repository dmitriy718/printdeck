#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 7 Cross-Portfolio Content Syndication Router
(`cross_portfolio_publisher.py`).

Safely writes static SEO editorial articles, buyer guides, and contextual showcases
across the 10-domain Para Investments portfolio network on `novahorizon` (`100.66.219.67`)
with mandatory SSOT Punch-In lock protection, HTTP 200 link verification via
`Portfolio Steward` (`:8085`), and automatic XML sitemap regeneration.

Cluster Taxonomy:
  - Cluster C Synergy (`coastalserenity.co`): Interior design lookbooks, framing guides,
    and acoustic/canvas comparisons linking directly to `printdeck.net` fine art canvases.
  - Cluster B Synergy (`tradeflows.net`, `tradeflows.co`, `mirrortape.net`): "Ultimate Trading
    Desk Ergonomics & Workspace Setup" reviews featuring PrintDeck custom chart-pattern desk
    mats, framed market art, and trader apparel.
  - Cluster A Synergy (`novahorizon.net`, `tradeloom.net`, `gighound.net`, `horizonsvc.com`,
    `corporate.novahorizon.net`): Case studies on "Turnkey Custom Company Swag & Client Gift
    Boxes for Remote Agencies & Freelancers," driving B2B bulk orders to `printdeck.net`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import html
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi.testclient import TestClient
import httpx

from db.database import DatabaseManager, get_db
from playwright_verifier import verify_active_lock_and_board_token
from seo_geo_engine import SEOGEOEngine
from ssot_engine import PROJECT_ROOT, SSOTEngine, format_punch_timestamp

PORTFOLIO_STEWARD_URL = os.getenv("PORTFOLIO_STEWARD_URL", "http://192.168.0.148:8085")
DEFAULT_WEBROOT_BASE = Path(
    os.getenv("PARA_PORTFOLIO_WEBROOT", str(PROJECT_ROOT / ".ssot" / "var_www_portfolio"))
)


PORTFOLIO_CLUSTERS: Dict[str, Dict[str, Any]] = {
    "CLUSTER_C_INTERIOR_DESIGN": {
        "domains": ["coastalserenity.co"],
        "audience": "Interior designers, coastal homeowners, and gallery wall collectors",
        "primary_printdeck_vertical": "canvas_painting",
        "target_printdeck_route": "/studio",
        "target_printdeck_sku": "PD-CANVAS-24X36",
        "editorial_template": {
            "slug": "archival-linen-canvas-vs-framed-giclee-coastal-lighting-guide",
            "title": "Archival Belgian Linen Canvas vs. Museum Framed Giclée: A Coastal Interior Lighting Guide",
            "anchor_text": "PrintDeck 300-DPI Archival Stretched Canvas & Spatial Room Studio",
            "utm_campaign": "cluster_c_coastal_lookbook",
        },
    },
    "CLUSTER_B_QUANT_TRADING_DESK": {
        "domains": ["tradeflows.net", "tradeflows.co", "mirrortape.net"],
        "audience": "Algorithmic traders, quantitative researchers, and multi-monitor desk architects",
        "primary_printdeck_vertical": "desk_mat",
        "target_printdeck_route": "/",
        "target_printdeck_sku": "PD-DESKMAT-XXL",
        "editorial_template": {
            "slug": "ultimate-quant-trading-desk-ergonomics-and-300dpi-chart-mat-review",
            "title": "Ultimate Trading Desk Ergonomics & Workspace Setup: 31.5×15.5\" Stitched Desk Mats & Framed Market Art",
            "anchor_text": "PrintDeck Precision 300-DPI XXL Architect & Quant Trader Desk Mat",
            "utm_campaign": "cluster_b_trading_desk_setup",
        },
    },
    "CLUSTER_A_B2B_CORPORATE_SWAG": {
        "domains": [
            "novahorizon.net",
            "tradeloom.net",
            "gighound.net",
            "horizonsvc.com",
            "corporate.novahorizon.net",
        ],
        "audience": "Remote engineering agencies, SaaS founders, and independent consultants",
        "primary_printdeck_vertical": "dtg_apparel",
        "target_printdeck_route": "/studio",
        "target_printdeck_sku": "PD-HOODIE-HEAVY",
        "editorial_template": {
            "slug": "turnkey-custom-company-swag-and-client-gift-boxes-for-remote-agencies",
            "title": "Turnkey Custom Company Swag & Client Gift Boxes for Remote Agencies & Freelancers (Zero Minimums)",
            "anchor_text": "PrintDeck 400GSM Heavyweight Corporate Apparel & VIP Client Gift Foundry",
            "utm_campaign": "cluster_a_b2b_agency_swag",
        },
    },
}


@dataclasses.dataclass
class SyndicatedArticleRecord:
    article_id: str
    cluster_id: str
    source_domain: str
    slug: str
    title: str
    published_file_path: str
    sitemap_path: str
    backlink_url: str
    target_sku: str
    http_200_verified: bool
    published_at: str = dataclasses.field(default_factory=format_punch_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class CrossPortfolioPublisher:
    """
    Safely publishes static HTML editorial articles across `/var/www/<domain>/guides/`
    with mandatory SSOT Punch-In lock protection, HTTP 200 backlink verification,
    and automatic XML sitemap regeneration.
    """

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[DatabaseManager] = None,
        seo_engine: Optional[SEOGEOEngine] = None,
        webroot_base_dir: Optional[Path] = None,
    ) -> None:
        self.ssot = ssot or SSOTEngine()
        self.db = db or get_db()
        self.seo_engine = seo_engine or SEOGEOEngine(db=self.db)
        self.webroot_base_dir = Path(webroot_base_dir or DEFAULT_WEBROOT_BASE)
        self._ensure_syndication_table()

    def _ensure_syndication_table(self) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_syndications (
                    article_id TEXT PRIMARY KEY,
                    cluster_id TEXT NOT NULL,
                    source_domain TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_file_path TEXT NOT NULL,
                    backlink_url TEXT NOT NULL,
                    target_sku TEXT NOT NULL,
                    http_200_verified BOOLEAN NOT NULL DEFAULT 1,
                    published_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def verify_printdeck_target_http_200(self, target_url_or_path: str) -> bool:
        """
        Verifies via `Portfolio Steward` (`:8085`) and PrintDeck's FastAPI `TestClient`
        that the linked `printdeck.net` destination route returns a strict HTTP 200.
        """
        parsed = urlparse(target_url_or_path)
        path = parsed.path or "/"

        if SSOTEngine._tcp_reachable(PORTFOLIO_STEWARD_URL, 8085):
            try:
                with httpx.Client(timeout=0.8) as http_client:
                    resp = http_client.get(
                        f"{PORTFOLIO_STEWARD_URL}/api/v1/check-url",
                        params={"url": f"https://printdeck.net{path}"},
                    )
                    if resp.status_code == 200:
                        return True
            except Exception:
                pass

        from app import app

        client = TestClient(app)
        resp = client.get(path)
        return resp.status_code == 200

    @staticmethod
    def _render_editorial_html(
        source_domain: str,
        title: str,
        slug: str,
        audience: str,
        backlink_url: str,
        anchor_text: str,
        target_sku: str,
    ) -> str:
        now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        canonical = f"https://{source_domain}/guides/{slug}.html"
        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "author": {"@type": "Organization", "name": f"{source_domain} Editorial Desk"},
            "datePublished": now_iso,
            "mainEntityOfPage": canonical,
            "about": {
                "@type": "Product",
                "sku": target_sku,
                "url": backlink_url,
            },
        }
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} | {html.escape(source_domain)}</title>
  <link rel="canonical" href="{canonical}" />
  <script type="application/ld+json">{json.dumps(article_schema)}</script>
</head>
<body class="editorial-guide">
  <article>
    <header>
      <p class="eyebrow">Curated for {html.escape(audience)}</p>
      <h1>{html.escape(title)}</h1>
      <time datetime="{now_iso}">{now_iso}</time>
    </header>
    <section class="editorial-body">
      <p>When specifying archival-grade visual pieces and tactile desk surfaces, resolution integrity (300 DPI minimum at physical print dimensions) and ICC sRGB color calibration determine longevity.</p>
      <p>Explore the interactive live visualizer and configure custom pieces directly via <a href="{html.escape(backlink_url)}" rel="noopener">{html.escape(anchor_text)}</a> (Master SKU: <code>{html.escape(target_sku)}</code>).</p>
    </section>
  </article>
</body>
</html>
"""

    def _regenerate_domain_sitemap(self, domain_dir: Path, source_domain: str) -> Path:
        guides_dir = domain_dir / "guides"
        urls: List[str] = [f"https://{source_domain}/"]
        if guides_dir.exists():
            for html_file in sorted(guides_dir.glob("*.html")):
                urls.append(f"https://{source_domain}/guides/{html_file.name}")

        now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url_nodes = "\n".join(
            f"  <url><loc>{u}</loc><lastmod>{now_iso}</lastmod><changefreq>weekly</changefreq></url>"
            for u in urls
        )
        sitemap_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{url_nodes}\n"
            "</urlset>\n"
        )
        sitemap_path = domain_dir / "sitemap.xml"
        sitemap_path.write_text(sitemap_xml, encoding="utf-8")
        return sitemap_path

    def publish_cluster_article(
        self,
        agent_name: str,
        cluster_id: str,
        source_domain: str,
        custom_slug: Optional[str] = None,
        custom_title: Optional[str] = None,
    ) -> SyndicatedArticleRecord:
        """
        Punches in to `SOURCE_OF_TRUTH.md`, verifies the target `printdeck.net` link
        returns HTTP 200, writes the static HTML guide to `/var/www/<source_domain>/guides/`,
        regenerates the domain's `sitemap.xml` and PrintDeck's sitemaps, and punches out.
        """
        cluster = PORTFOLIO_CLUSTERS[cluster_id]
        tpl = cluster["editorial_template"]
        slug = custom_slug or tpl["slug"]
        title = custom_title or tpl["title"]
        target_route = cluster["target_printdeck_route"]
        target_sku = cluster["target_printdeck_sku"]
        utm = (
            f"?utm_source={source_domain}&utm_medium=editorial_syndication"
            f"&utm_campaign={tpl['utm_campaign']}&sku={target_sku}"
        )
        backlink_url = f"https://printdeck.net{target_route}{utm}"

        scope = f"syndication:cross-portfolio:{source_domain}"
        lock = self.ssot.punch_in(
            agent_name=agent_name,
            scope=scope,
            task_description=(
                f"publishing contextual {cluster_id} editorial guide '{slug}' to "
                f"/var/www/{source_domain}/guides/ and regenerating XML sitemaps"
            ),
        )
        try:
            verify_active_lock_and_board_token(
                ssot=self.ssot,
                agent_name=agent_name,
                scope=scope,
                lock_token=lock["token"],
                requires_board_resolution=False,
            )

            http_200_ok = self.verify_printdeck_target_http_200(target_route)
            if not http_200_ok:
                raise RuntimeError(
                    f"Portfolio Steward link check failed: target route '{target_route}' did not return HTTP 200."
                )

            domain_dir = self.webroot_base_dir / source_domain
            guides_dir = domain_dir / "guides"
            guides_dir.mkdir(parents=True, exist_ok=True)

            article_path = guides_dir / f"{slug}.html"
            html_content = self._render_editorial_html(
                source_domain=source_domain,
                title=title,
                slug=slug,
                audience=cluster["audience"],
                backlink_url=backlink_url,
                anchor_text=tpl["anchor_text"],
                target_sku=target_sku,
            )
            article_path.write_text(html_content, encoding="utf-8")

            sitemap_path = self._regenerate_domain_sitemap(domain_dir, source_domain)
            # Also refresh PrintDeck split XML sitemaps
            self.seo_engine.generate_sitemap_index_xml()

            article_id = f"synd_{source_domain.replace('.', '_')}_{slug[:24]}"
            record = SyndicatedArticleRecord(
                article_id=article_id,
                cluster_id=cluster_id,
                source_domain=source_domain,
                slug=slug,
                title=title,
                published_file_path=str(article_path),
                sitemap_path=str(sitemap_path),
                backlink_url=backlink_url,
                target_sku=target_sku,
                http_200_verified=http_200_ok,
            )

            with self.db.connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO portfolio_syndications (
                        article_id, cluster_id, source_domain, slug, title,
                        published_file_path, backlink_url, target_sku, http_200_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.article_id,
                        record.cluster_id,
                        record.source_domain,
                        record.slug,
                        record.title,
                        record.published_file_path,
                        record.backlink_url,
                        record.target_sku,
                        1 if record.http_200_verified else 0,
                    ),
                )

            self.ssot.punch_out(
                agent_name=agent_name,
                scope=scope,
                resolution_summary=(
                    f"published {cluster_id} showcase '{slug}.html' on {source_domain} "
                    f"(verified HTTP 200 link to {backlink_url}) and updated {sitemap_path.name}"
                ),
                token=lock["token"],
            )
            return record
        except Exception as exc:
            state = self.ssot.get_state()
            if scope in state.get("active_locks", {}):
                self.ssot.punch_out(
                    agent_name=agent_name,
                    scope=scope,
                    resolution_summary=f"cross-portfolio publish failed on {source_domain}: {exc}",
                    token=lock["token"],
                )
            raise


# --- Canonical Phase 7 CrossPortfolioPublisher Bridge ---

