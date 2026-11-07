#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 7 Specialist Agent 2:
Publicist, Social Media & Cross-Portfolio Backlink Agent (`Agent Julian` — `agent_publicist_julian.py`).

Supervised by: Tier 1 Business Manager `Agent Elena`.
Coordinates with: `A3 SEO/Content`, `Answered-Scribe`, and `Portfolio Steward` (`:8085`).

Mandatory Operating Law:
  1. Punches into `SOURCE_OF_TRUTH.md` before updating any local or cross-domain content
     directory (`/var/www/*`) or generating social/PR syndication payloads.
  2. Verifies active Redis (`pi-core:6379`) / SSOT lock via `verify_active_lock_and_board_token`.
  3. Verifies all outbound `printdeck.net` links return HTTP 200 via `Portfolio Steward`.
  4. Punches out immediately upon completion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from cross_portfolio_publisher import (
    PORTFOLIO_CLUSTERS,
    CrossPortfolioPublisher,
    SyndicatedArticleRecord,
)
from db.database import DatabaseManager, get_db
from playwright_verifier import verify_active_lock_and_board_token
from ssot_engine import SSOTEngine, format_punch_timestamp


class PublicistAgentJulian:
    """
    `Agent Julian` — Publicist, Social Media & Cross-Portfolio Backlink Specialist Agent.
    Orchestrates semantic cross-portfolio editorial syndication across Clusters A, B, and C
    on `novahorizon` (`100.66.219.67`), and generates daily Pinterest Rich Pins, X/Twitter
    threads, Reddit community guides, and Digital PR press releases with UTM attribution.
    """

    AGENT_NAME = "Agent Julian"
    DEFAULT_SCOPE = "growth:publicist-social-specialist"

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[DatabaseManager] = None,
        publisher: Optional[CrossPortfolioPublisher] = None,
        webroot_base_dir: Optional[Path] = None,
    ) -> None:
        self.ssot = ssot or SSOTEngine()
        self.db = db or get_db()
        self.publisher = publisher or CrossPortfolioPublisher(
            ssot=self.ssot,
            db=self.db,
            webroot_base_dir=webroot_base_dir,
        )

    async def syndicate_across_all_portfolio_clusters(
        self,
        selected_domains_per_cluster: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes semantic cross-portfolio syndication across:
          - Cluster C (`coastalserenity.co`): Interior design lookbooks & framing guides
          - Cluster B (`tradeflows.net`, `tradeflows.co`, `mirrortape.net`): Quant trading desk ergonomics
          - Cluster A (`novahorizon.net`, `tradeloom.net`, `gighound.net`, `horizonsvc.com`): B2B company swag
        Each domain write acquires its own scoped punch-in lock in `SOURCE_OF_TRUTH.md`,
        verifies HTTP 200 link integrity via `Portfolio Steward`, and regenerates `sitemap.xml`.
        """
        published: List[Dict[str, Any]] = []
        for cluster_id, cfg in PORTFOLIO_CLUSTERS.items():
            domains = (
                selected_domains_per_cluster.get(cluster_id, cfg["domains"])
                if selected_domains_per_cluster
                else cfg["domains"]
            )
            for domain in domains:
                rec: SyndicatedArticleRecord = self.publisher.publish_cluster_article(
                    agent_name=self.AGENT_NAME,
                    cluster_id=cluster_id,
                    source_domain=domain,
                )
                published.append(rec.to_dict())

        return {
            "agent": self.AGENT_NAME,
            "clusters_syndicated": list(PORTFOLIO_CLUSTERS.keys()),
            "articles_published_count": len(published),
            "all_http_200_verified": all(p["http_200_verified"] for p in published),
            "articles": published,
            "completed_at": format_punch_timestamp(),
        }

    async def generate_social_and_pr_syndication_pack(
        self,
        featured_sku: str = "PD-CANVAS-24X36",
        campaign_tag: str = "q4_atelier_drop",
    ) -> Dict[str, Any]:
        """
        Generates daily ready-to-publish external social and PR payloads with full UTM tracking:
          1. Pinterest Rich Pin (high-res lifestyle room mockup + Schema.org Product metadata)
          2. X/Twitter 4-part thread showcasing the 300-DPI Spatial Mockup Studio
          3. Reddit / community value post (Gallery Wall 57-Inch Golden Ratio hanging guide)
          4. Digital PR press release
        """
        scope = f"{self.DEFAULT_SCOPE}:social-pr-pack-{featured_sku.lower()}"
        lock = self.ssot.punch_in(
            agent_name=self.AGENT_NAME,
            scope=scope,
            task_description=(
                f"generating Pinterest Rich Pin, X thread, Reddit guide, and PR payload for {featured_sku}"
            ),
        )
        try:
            lock_verification = verify_active_lock_and_board_token(
                ssot=self.ssot,
                agent_name=self.AGENT_NAME,
                scope=scope,
                lock_token=lock["token"],
                requires_board_resolution=False,
            )

            http_200_ok = self.publisher.verify_printdeck_target_http_200("/studio")
            if not http_200_ok:
                raise RuntimeError("Target /studio route failed HTTP 200 verification.")

            base_url = "https://printdeck.net/studio"
            pinterest_pin = {
                "platform": "pinterest",
                "pin_type": "Rich_Product_Pin",
                "title": "24×36\" Archival Belgian Linen Stretched Canvas — Live 3D Room Visualizer",
                "description": (
                    "Preview museum-grade 300-DPI impasto canvases in Modern Loft, Executive Office, "
                    "and Coastal Living lighting before printing to order."
                ),
                "image_mockup_url": f"https://printdeck.net/assets/mockups/{featured_sku.lower()}-modern-loft-300dpi.avif",
                "destination_url": (
                    f"{base_url}?utm_source=pinterest&utm_medium=rich_pin"
                    f"&utm_campaign={campaign_tag}&sku={featured_sku}"
                ),
                "product_schema": {
                    "@type": "Product",
                    "sku": featured_sku,
                    "brand": "PrintDeck Tactile Atelier",
                    "priceCurrency": "USD",
                    "price": "149.00",
                    "availability": "https://schema.org/InStock",
                },
            }

            x_thread = [
                (
                    "1/4 Flat 2D print-on-demand mockups are dead. We built the PrintDeck Spatial "
                    "Mockup Studio so you can test directional 2700K–5600K gallery lighting and "
                    "true-to-scale furniture ratios in real time."
                ),
                (
                    "2/4 Every piece runs through our automated 300-DPI Pre-Flight Pipeline "
                    "(7200×10800 px for 24×36\" canvases) + ICC sRGB soft-proofing before touching "
                    "a stretcher bar."
                ),
                (
                    "3/4 Plus, every order enters a 120-minute editable grace window after checkout "
                    "— swap frame finishes, adjust sizing, or update your shipping address with 1 click."
                ),
                (
                    f"4/4 Try the live Spatial Studio & Gallery Wall Golden-Ratio Calculator here: "
                    f"{base_url}?utm_source=x_twitter&utm_medium=thread&utm_campaign={campaign_tag}"
                ),
            ]

            reddit_post = {
                "subreddit_targets": ["r/InteriorDesign", "r/battlestations", "r/malelivingspace"],
                "title": "[Guide] The 57-Inch Museum Centerline Rule & 0.618 Sofa-to-Canvas Golden Ratio Formula",
                "body_markdown": (
                    "When hanging large-format art (like a 24×36\" or triptych canvas) above a sofa or "
                    "desk setup, two measurements eliminate guesswork:\n\n"
                    "1. **57\" Museum Centerline**: Keep the vertical center of the frame at 57 inches from the floor.\n"
                    "2. **0.618 Golden Ratio Width**: Total artwork span should cover ~61.8% of the furniture width below it.\n\n"
                    f"We built a free interactive calculator in our [PrintDeck Spatial Studio]({base_url}"
                    f"?utm_source=reddit&utm_medium=community_guide&utm_campaign={campaign_tag}) if you want to test your wall dimensions."
                ),
            }

            press_release = {
                "headline": "PrintDeck Launches Interactive WebGL Spatial Mockup Studio & 300-DPI Dual-Provider Print Foundry",
                "dateline": "NEW YORK — Para Investments LLC",
                "media_contact": "press@printdeck.net",
                "canonical_url": f"https://printdeck.net/?utm_source=digital_pr&utm_medium=press_release&utm_campaign={campaign_tag}",
            }

            self.ssot.punch_out(
                agent_name=self.AGENT_NAME,
                scope=scope,
                resolution_summary=(
                    f"generated Pinterest Rich Pin, 4-part X thread, Reddit value guide, and PR payload "
                    f"for {featured_sku} (campaign={campaign_tag}; HTTP 200 verified)"
                ),
                token=lock["token"],
            )

            return {
                "agent": self.AGENT_NAME,
                "featured_sku": featured_sku,
                "campaign_tag": campaign_tag,
                "http_200_verified": http_200_ok,
                "pinterest_rich_pin": pinterest_pin,
                "x_twitter_thread": x_thread,
                "reddit_value_post": reddit_post,
                "press_release": press_release,
                "lock_verification": lock_verification,
            }
        except Exception as exc:
            state = self.ssot.get_state()
            if scope in state.get("active_locks", {}):
                self.ssot.punch_out(
                    agent_name=self.AGENT_NAME,
                    scope=scope,
                    resolution_summary=f"social/PR pack generation failed: {exc}",
                    token=lock["token"],
                )
            raise


# --- Canonical Phase 7 PublicistAgentJulian Bridge ---

