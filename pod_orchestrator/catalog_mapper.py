#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 Unified Catalog & Dual-Provider Blueprint Mapper.
Maps PrintDeck Master SKUs (PD-*) across all verticals to Printify Blueprints/Print
Providers and Printful v2 Catalog Variants while protecting legacy Bambu Lab hardware (HW-*).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Optional

from db.database import DatabaseManager, get_db
from ssot_engine import require_punch_in
from .printful_client import PrintfulV2Client
from .printify_client import PrintifyClient


class UnifiedCatalogMapper:
    """
    Maintains the canonical mapping between PrintDeck Master SKUs (PD-*) and
    Printify + Printful v2 catalog entities.
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        printify_client: Optional[PrintifyClient] = None,
        printful_client: Optional[PrintfulV2Client] = None,
    ) -> None:
        self.db = db or get_db()
        self.printify = printify_client or PrintifyClient()
        self.printful = printful_client or PrintfulV2Client()

    def get_blueprint_matrix(self) -> List[Dict[str, Any]]:
        """
        Returns all POD Master SKUs with their Printify Blueprint/Provider and
        Printful v2 Catalog Variant mappings.
        """
        products = self.db.list_products(include_hardware=False)
        matrix: List[Dict[str, Any]] = []
        for prod in products:
            variant_entries = []
            for var in prod.get("variants", []):
                full_var = self.db.get_variant_with_mappings(var["variant_id"])
                if full_var:
                    variant_entries.append(
                        {
                            "variant_id": full_var["variant_id"],
                            "variant_sku": full_var["variant_sku"],
                            "size_code": full_var["size_code"],
                            "color_name": full_var["color_name"],
                            "retail_price_cents": full_var["retail_price_cents"],
                            "providers": full_var.get("provider_mappings", []),
                        }
                    )
            matrix.append(
                {
                    "product_id": prod["product_id"],
                    "master_sku": prod["master_sku"],
                    "title": prod["title"],
                    "vertical": prod["vertical"],
                    "print_dimensions_in": f"{prod['print_area_width_in']}x{prod['print_area_height_in']}",
                    "required_300dpi_px": (
                        f"{int(round(prod['print_area_width_in'] * 300))}x"
                        f"{int(round(prod['print_area_height_in'] * 300))}"
                    ),
                    "requires_transparent_alpha": bool(prod["requires_transparent_alpha"]),
                    "gallery_wrap_bleed": bool(prod["gallery_wrap_bleed"]),
                    "variants": variant_entries,
                }
            )
        return matrix

    @require_punch_in(
        agent_name="Catalog-Sync-Steward",
        scope="api:pod-catalog-sync",
        task_description="synchronizing live Printify and Printful v2 blank stock and pricing across PD-* Master SKUs",
    )
    async def sync_live_catalog_availability(self) -> Dict[str, Any]:
        """
        Polls both Printify and Printful v2 for all mapped variants and updates
        in_stock and last_stock_sync_at in pod_provider_mappings.
        """
        updated_count = 0
        out_of_stock_count = 0
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

        with self.db.connect() as conn:
            mappings = [
                dict(r)
                for r in conn.execute("SELECT * FROM pod_provider_mappings").fetchall()
            ]

        for m in mappings:
            if m["provider"] == "printify":
                status = await self.printify.check_variant_availability(
                    blueprint_id=m["external_blueprint_id"],
                    print_provider_id=m["external_print_provider_id"],
                    external_variant_id=m["external_variant_id"],
                    db_in_stock_default=bool(m["in_stock"]),
                )
            else:
                status = await self.printful.check_variant_availability(
                    external_variant_id=m["external_variant_id"],
                    db_in_stock_default=bool(m["in_stock"]),
                )

            in_stock_int = 1 if status["in_stock"] else 0
            if not status["in_stock"]:
                out_of_stock_count += 1

            with self.db.connect() as conn:
                conn.execute(
                    """
                    UPDATE pod_provider_mappings
                    SET in_stock = ?, last_stock_sync_at = ?
                    WHERE mapping_id = ?
                    """,
                    (in_stock_int, now_iso, m["mapping_id"]),
                )
            updated_count += 1

        return {
            "synced_mappings": updated_count,
            "out_of_stock_detected": out_of_stock_count,
            "synced_at_utc": now_iso,
        }

    @require_punch_in(
        agent_name="Catalog-Sync-Steward",
        scope="api:pod-catalog-mutation",
        task_description="upserting dual-provider POD mapping for PrintDeck variant",
    )
    def upsert_provider_mapping(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds or updates a Printify or Printful mapping for a PrintDeck variant.
        Refuses to attach POD fulfillment to protected legacy hardware SKUs (HW-*).
        """
        master_sku = str(mapping_data.get("master_sku", "")).upper()
        if master_sku.startswith("HW-"):
            raise ValueError(
                f"Protected Hardware SKU '{master_sku}' cannot be mapped to POD providers."
            )

        mapping_id = mapping_data.get("mapping_id") or f"map_{uuid.uuid4().hex[:12]}"
        record = {
            "mapping_id": mapping_id,
            "variant_id": mapping_data["variant_id"],
            "master_sku": master_sku,
            "provider": mapping_data["provider"].lower(),
            "external_blueprint_id": mapping_data["external_blueprint_id"],
            "external_print_provider_id": mapping_data["external_print_provider_id"],
            "external_variant_id": mapping_data["external_variant_id"],
            "provider_name_label": mapping_data.get(
                "provider_name_label", f"{mapping_data['provider'].title()} Provider"
            ),
            "base_blank_cost_cents": int(mapping_data["base_blank_cost_cents"]),
            "base_shipping_cents": int(mapping_data["base_shipping_cents"]),
            "additional_item_shipping_cents": int(
                mapping_data.get("additional_item_shipping_cents", 200)
            ),
            "volume_tier_discount_bps": int(mapping_data.get("volume_tier_discount_bps", 0)),
            "facility_region": mapping_data.get("facility_region", "US-EAST"),
            "facility_zip_prefix": str(mapping_data.get("facility_zip_prefix", "282")),
            "avg_production_hours": float(mapping_data.get("avg_production_hours", 30.0)),
            "quality_rating": float(mapping_data.get("quality_rating", 4.85)),
            "in_stock": int(bool(mapping_data.get("in_stock", True))),
            "priority_rank": int(mapping_data.get("priority_rank", 1)),
        }

        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO pod_provider_mappings (
                    mapping_id, variant_id, master_sku, provider,
                    external_blueprint_id, external_print_provider_id,
                    external_variant_id, provider_name_label,
                    base_blank_cost_cents, base_shipping_cents,
                    additional_item_shipping_cents, volume_tier_discount_bps,
                    facility_region, facility_zip_prefix, avg_production_hours,
                    quality_rating, in_stock, priority_rank
                ) VALUES (
                    :mapping_id, :variant_id, :master_sku, :provider,
                    :external_blueprint_id, :external_print_provider_id,
                    :external_variant_id, :provider_name_label,
                    :base_blank_cost_cents, :base_shipping_cents,
                    :additional_item_shipping_cents, :volume_tier_discount_bps,
                    :facility_region, :facility_zip_prefix, :avg_production_hours,
                    :quality_rating, :in_stock, :priority_rank
                )
                ON CONFLICT(variant_id, provider, external_print_provider_id) DO UPDATE SET
                    base_blank_cost_cents = excluded.base_blank_cost_cents,
                    base_shipping_cents = excluded.base_shipping_cents,
                    volume_tier_discount_bps = excluded.volume_tier_discount_bps,
                    in_stock = excluded.in_stock,
                    last_stock_sync_at = CURRENT_TIMESTAMP
                """,
                record,
            )
        return record
