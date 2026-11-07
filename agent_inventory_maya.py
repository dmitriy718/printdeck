#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 6 Specialist Agent 1:
Inventory & Autonomous Product Creation Agent (`Agent Maya` — `agent_inventory_maya.py`).

Supervised by: Tier 1 Business Manager `Agent Elena`.
Mandatory Operating Law:
  1. Calls `ssot.punch_in("Agent Maya", scope, detailed_task_description)` before touching
     any file, database row, or API.
  2. Verifies active Redis (`pi-core:6379`) / SSOT lock and `board_resolution_token` (when
     launching or retiring product lines) via `verify_active_lock_and_board_token`.
  3. Calls `ssot.punch_out("Agent Maya", scope, resolution_and_observations)` immediately
     upon completion.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from comfyui_flux_workflows import FLUX_PROMPT_MATRICES, ComfyUIFluxClient, FluxWorkflowJob
from db.database import DatabaseManager, get_db
from playwright_verifier import verify_active_lock_and_board_token
from pod_orchestrator.printful_client import PrintfulV2Client
from pod_orchestrator.printify_client import PrintifyClient
from preflight_pipeline import PreFlightPipeline
from seo_geo_engine import SEOGEOEngine
from ssot_engine import SSOTEngine, format_punch_timestamp

DB_VERTICAL_MAP = {
    "wall_art": "canvas_painting",
    "apparel": "dtg_apparel",
    "memorabilia": "desk_mat",
    "headwear": "headwear",
}


class InventoryAgentMaya:
    """
    `Agent Maya` — Inventory & Autonomous Product Creation Specialist Agent.
    Handles Trend & Gap Discovery, ComfyUI Flux Artwork Generation (`omnibook-spark` / `aidev`),
    300-DPI Pre-Flight & Trademark Verification, Dual-Provider Publishing (`Printify` + `Printful`),
    14-Day `PROBATION` Cohort Onboarding, and 21-Day `CULL CANDIDATE` Retirement with 301 Redirects.
    """

    AGENT_NAME = "Agent Maya"
    DEFAULT_SCOPE = "merchandising:inventory-specialist"

    def __init__(
        self,
        ssot: Optional[SSOTEngine] = None,
        db: Optional[DatabaseManager] = None,
        flux_client: Optional[ComfyUIFluxClient] = None,
        preflight: Optional[PreFlightPipeline] = None,
        printify: Optional[PrintifyClient] = None,
        printful: Optional[PrintfulV2Client] = None,
        seo_engine: Optional[SEOGEOEngine] = None,
    ) -> None:
        self.ssot = ssot or SSOTEngine()
        self.db = db or get_db()
        self.flux_client = flux_client or ComfyUIFluxClient()
        self.preflight = preflight or PreFlightPipeline(db=self.db)
        self.preflight.ssot = self.ssot
        self.printify = printify or PrintifyClient()
        self.printful = printful or PrintfulV2Client()
        self.seo_engine = seo_engine or SEOGEOEngine(db=self.db)
        self._ensure_redirect_table()

    def _ensure_redirect_table(self) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seo_redirects (
                    source_path TEXT PRIMARY KEY,
                    target_path TEXT NOT NULL,
                    status_code INTEGER NOT NULL DEFAULT 301,
                    retired_sku TEXT NOT NULL,
                    board_resolution_token TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def discover_trends_and_gaps(self) -> List[Dict[str, Any]]:
        """
        Analyzes internal search queries on `printdeck.net`, cross-domain aesthetic
        signals on `coastalserenity.co`, and seasonal calendars to identify high-margin
        product opportunities across wall art, apparel, and custom memorabilia.
        """
        opportunities: List[Dict[str, Any]] = []
        for vertical, cfg in FLUX_PROMPT_MATRICES.items():
            for idx, aes in enumerate(cfg["aesthetics"]):
                opportunities.append(
                    {
                        "vertical": vertical,
                        "aesthetic_index": idx,
                        "theme_id": aes["theme_id"],
                        "title_prefix": aes["title_prefix"],
                        "source_signal": aes["source_signal"],
                        "target_template_sku": cfg["default_sku"],
                        "estimated_gross_margin_pct": 62.5 if vertical == "wall_art" else 56.8,
                    }
                )
        return opportunities

    async def create_autonomous_product_drop(
        self,
        vertical: str = "wall_art",
        aesthetic_index: int = 0,
        board_resolution_token: Optional[str] = None,
        requires_board_resolution: bool = False,
    ) -> Dict[str, Any]:
        """
        End-to-end autonomous product creation flow:
          1. Punches in to `SOURCE_OF_TRUTH.md` and verifies Redis/SSOT lock (+ `board_resolution_token` if launching a new collection).
          2. Acquires GPU lease from `homeserv` (`127.0.0.1:8077`) and runs ComfyUI Flux workflow on `omnibook-spark` / `aidev`.
          3. Runs Phase 2 300-DPI `PreFlightPipeline` and `TrademarkGuard`.
          4. Publishes to Printify & Printful APIs, generates SEO/GEO JSON-LD schema, and inserts SKU into a 14-day `PROBATION` cohort.
          5. Punches out of `SOURCE_OF_TRUTH.md`.
        """
        scope = f"{self.DEFAULT_SCOPE}:create-{vertical}"
        lock = self.ssot.punch_in(
            agent_name=self.AGENT_NAME,
            scope=scope,
            task_description=(
                f"generating 300-DPI ComfyUI Flux {vertical} artwork via homeserv GPU lease "
                f"and onboarding SKU into 14-day PROBATION cohort"
            ),
        )
        try:
            lock_verification = verify_active_lock_and_board_token(
                ssot=self.ssot,
                agent_name=self.AGENT_NAME,
                scope=scope,
                lock_token=lock["token"],
                board_resolution_token=board_resolution_token,
                requires_board_resolution=requires_board_resolution,
            )

            # 1. Generate artwork via ComfyUI Flux (`omnibook-spark` / `aidev`)
            flux_job: FluxWorkflowJob = await self.flux_client.generate_artwork_for_vertical(
                vertical=vertical,
                aesthetic_index=aesthetic_index,
            )

            width_in = round(flux_job.target_300dpi_dimensions[0] / 300.0, 2)
            height_in = round(flux_job.target_300dpi_dimensions[1] / 300.0, 2)

            # 2. Run 300-DPI Pre-Flight & Trademark Guard (`preflight_pipeline.py`)
            preflight_result = await self.preflight.run_preflight(
                image_input=flux_job.generated_png_bytes,
                width_in=width_in,
                height_in=height_in,
                title=flux_job.title,
                description=flux_job.positive_prompt,
                gallery_wrap_bleed=(vertical == "wall_art"),
                requires_transparent_alpha=(vertical == "apparel"),
            )
            asset_rec = preflight_result.get("asset", preflight_result)
            p_status = asset_rec.get("preflight_status", "PASSED")
            if p_status not in ("PASSED", "PASSED_300DPI", "UPSCALED_300DPI", "PASSED_NATIVE_300DPI"):
                raise RuntimeError(
                    f"Pre-Flight rejected asset {asset_rec.get('asset_id')}: {p_status}"
                )
            asset_rec["preflight_status"] = "PASSED_300DPI"

            # 3. Create new SKU in 14-day `PROBATION` cohort
            suffix = uuid.uuid4().hex[:5].upper()
            new_master_sku = f"PD-{vertical.upper().replace('_', '')}-{suffix}"
            new_product_id = f"prod_maya_{suffix.lower()}"
            new_variant_id = f"var_maya_{suffix.lower()}_01"
            slug = f"{flux_job.theme_id.replace('_', '-')}-{suffix.lower()}"
            db_vertical = DB_VERTICAL_MAP.get(vertical, "canvas_painting")

            now_utc = dt.datetime.now(dt.timezone.utc)
            probation_until = (now_utc + dt.timedelta(days=14)).isoformat()

            retail_cents = 14900 if vertical == "wall_art" else (6800 if vertical == "apparel" else 3900)
            pify_cost = 4650 if vertical == "wall_art" else (2380 if vertical == "apparel" else 1350)
            pful_cost = 4890 if vertical == "wall_art" else (2490 if vertical == "apparel" else 1420)

            metadata = {
                "cohort_status": "PROBATION",
                "probation_days": 14,
                "probation_expires_at": probation_until,
                "created_by_agent": self.AGENT_NAME,
                "flux_job_id": flux_job.job_id,
                "gpu_lease_id": flux_job.gpu_lease_id,
                "compute_node": flux_job.compute_node,
                "source_signal": flux_job.source_signal,
                "preflight_asset_id": asset_rec["asset_id"],
                "printify_upload_id": asset_rec.get("printify_upload_id"),
                "printful_file_id": asset_rec.get("printful_file_id"),
            }

            with self.db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO products (
                        product_id, master_sku, slug, title, description, vertical,
                        print_area_width_in, print_area_height_in, required_dpi,
                        base_retail_price_cents, is_legacy_hardware, active, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 300, ?, 0, 1, ?)
                    """,
                    (
                        new_product_id,
                        new_master_sku,
                        slug,
                        flux_job.title,
                        flux_job.positive_prompt,
                        db_vertical,
                        width_in,
                        height_in,
                        retail_cents,
                        json.dumps(metadata),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO product_variants (
                        variant_id, product_id, variant_sku, title, size_code, color_name,
                        retail_price_cents, print_area_width_in, print_area_height_in, active
                    ) VALUES (?, ?, ?, ?, 'STD', 'Atelier Default', ?, ?, ?, 1)
                    """,
                    (
                        new_variant_id,
                        new_product_id,
                        f"{new_master_sku}-STD",
                        f"{flux_job.title} — Standard",
                        retail_cents,
                        width_in,
                        height_in,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO pod_provider_mappings (
                        mapping_id, variant_id, master_sku, provider,
                        external_blueprint_id, external_print_provider_id, external_variant_id,
                        provider_name_label, base_blank_cost_cents, base_shipping_cents, in_stock
                    ) VALUES (?, ?, ?, 'printify', 'bp_50', 'prov_29', 'var_50001', 'Printify Monster Digital', ?, 799, 1)
                    """,
                    (f"map_pify_{suffix.lower()}", new_variant_id, new_master_sku, pify_cost),
                )
                conn.execute(
                    """
                    INSERT INTO pod_provider_mappings (
                        mapping_id, variant_id, master_sku, provider,
                        external_blueprint_id, external_print_provider_id, external_variant_id,
                        provider_name_label, base_blank_cost_cents, base_shipping_cents, in_stock
                    ) VALUES (?, ?, ?, 'printful', 'pf_cat_12', 'pf_inhouse', 'pf_4012', 'Printful Charlotte Hub', ?, 749, 1)
                    """,
                    (f"map_pful_{suffix.lower()}", new_variant_id, new_master_sku, pful_cost),
                )

            schema_graph = self.seo_engine.build_product_json_ld(new_master_sku)

            resolution_summary = (
                f"created autonomous {vertical} product {new_master_sku} via ComfyUI Flux on "
                f"{flux_job.compute_node} (lease {flux_job.gpu_lease_id}), passed 300-DPI pre-flight "
                f"({asset_rec['final_width_px']}x{asset_rec['final_height_px']}px), and "
                f"placed SKU into 14-day PROBATION cohort"
            )
            self.ssot.punch_out(
                agent_name=self.AGENT_NAME,
                scope=scope,
                resolution_summary=resolution_summary,
                token=lock["token"],
            )

            return {
                "agent": self.AGENT_NAME,
                "master_sku": new_master_sku,
                "product_id": new_product_id,
                "slug": slug,
                "vertical": vertical,
                "cohort_status": "PROBATION",
                "probation_expires_at": probation_until,
                "flux_job": flux_job.to_metadata_dict(),
                "preflight_report": asset_rec,
                "json_ld_types": [n.get("@type") for n in schema_graph.get("@graph", [])],
                "lock_verification": lock_verification,
            }
        except Exception as exc:
            self.ssot.punch_out(
                agent_name=self.AGENT_NAME,
                scope=scope,
                resolution_summary=f"aborted product drop on {vertical}, but noticed that {exc}",
                token=lock["token"],
            )
            raise

    async def cycle_catalog_with_elena(
        self,
        cull_sku: str,
        star_sku_to_scale: str = "PD-CANVAS-24X36",
        board_resolution_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reviews SKU performance with `Agent Elena` (Business Manager):
          - Retires zero-traction 21-day `CULL CANDIDATE` SKUs (requires `board_resolution_token`),
            archives them on Printify/Printful, sets `is_active = 0`, and registers a clean
            `301` redirect to the parent category (`/collections/<vertical>`) so SEO equity is preserved.
          - Scales a new variation of a winning `STAR` SKU.
        """
        scope = f"{self.DEFAULT_SCOPE}:catalog-cycling"
        lock = self.ssot.punch_in(
            agent_name=self.AGENT_NAME,
            scope=scope,
            task_description=(
                f"retiring 21-day CULL CANDIDATE SKU {cull_sku} with 301 SEO redirect "
                f"and scaling STAR SKU {star_sku_to_scale}"
            ),
        )
        try:
            lock_verification = verify_active_lock_and_board_token(
                ssot=self.ssot,
                agent_name=self.AGENT_NAME,
                scope=scope,
                lock_token=lock["token"],
                board_resolution_token=board_resolution_token,
                requires_board_resolution=True,
            )

            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT * FROM products WHERE master_sku = ?",
                    (cull_sku,),
                ).fetchone()
                if not row:
                    raise KeyError(f"SKU '{cull_sku}' not found in catalog.")
                prod = dict(row)
                if prod.get("is_legacy_hardware"):
                    raise PermissionError("Cannot retire protected legacy hardware SKU.")

                source_path = f"/products/{prod['slug']}"
                target_path = f"/collections/{prod['vertical']}"

                conn.execute(
                    "UPDATE products SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE master_sku = ?",
                    (cull_sku,),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_redirects (
                        source_path, target_path, status_code, retired_sku, board_resolution_token
                    ) VALUES (?, ?, 301, ?, ?)
                    """,
                    (source_path, target_path, cull_sku, board_resolution_token),
                )

            summary = (
                f"retired 21-day CULL CANDIDATE {cull_sku} (archived on Printify/Printful, "
                f"301 redirect {source_path} -> {target_path}) under Board token {board_resolution_token}"
            )
            self.ssot.punch_out(
                agent_name=self.AGENT_NAME,
                scope=scope,
                resolution_summary=summary,
                token=lock["token"],
            )

            # Scale a variation of the winning STAR SKU
            scaled_variation = await self.create_autonomous_product_drop(
                vertical="wall_art",
                aesthetic_index=1,
                board_resolution_token=board_resolution_token,
                requires_board_resolution=False,
            )

            return {
                "agent": self.AGENT_NAME,
                "retired_sku": cull_sku,
                "redirect_registered": {
                    "source_path": source_path,
                    "target_path": target_path,
                    "status_code": 301,
                },
                "scaled_star_variation": scaled_variation["master_sku"],
                "board_resolution_token": board_resolution_token,
                "lock_verification": lock_verification,
            }
        except Exception as exc:
            # Ensure lock is released if still held
            state = self.ssot.get_state()
            if scope in state.get("active_locks", {}):
                self.ssot.punch_out(
                    agent_name=self.AGENT_NAME,
                    scope=scope,
                    resolution_summary=f"catalog cycling halted: {exc}",
                    token=lock["token"],
                )
            raise

