#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 Database Manager.
Integrates cleanly with CodexStore PostgreSQL (:5432) and SQLite (printdeck.sqlite,
paygate.sqlite, intake.sqlite) while preserving all legacy Bambu Lab 4.3" touchscreen
hardware offers (/hardware, /simulator, /pay/*).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB_PATH = PROJECT_ROOT / ".ssot" / "printdeck_phase2.sqlite"
DEFAULT_PAYGATE_DB_PATH = PROJECT_ROOT / ".ssot" / "paygate.sqlite"
DEFAULT_INTAKE_DB_PATH = PROJECT_ROOT / ".ssot" / "intake.sqlite"


class DatabaseManager:
    """
    Unified relational store for PrintDeck Phase 2.
    Operates against SQLite out-of-the-box and mirrors transactions to local
    paygate.sqlite / intake.sqlite tables when para-paygate / para-intake run locally.
    """

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        paygate_db_path: Optional[Path | str] = None,
        intake_db_path: Optional[Path | str] = None,
    ) -> None:
        self.db_path = Path(db_path or os.getenv("PRINTDECK_SQLITE_PATH", str(DEFAULT_DB_PATH)))
        self.paygate_db_path = Path(
            paygate_db_path or os.getenv("PAYGATE_SQLITE_PATH", str(DEFAULT_PAYGATE_DB_PATH))
        )
        self.intake_db_path = Path(
            intake_db_path or os.getenv("INTAKE_SQLITE_PATH", str(DEFAULT_INTAKE_DB_PATH))
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()
        self.init_auxiliary_sidecar_databases()
        self.seed_reference_catalog()

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema_sql)

    def init_auxiliary_sidecar_databases(self) -> None:
        """
        Ensures local paygate.sqlite and intake.sqlite schemas exist so local/offline
        integrations with para-paygate.service (:8790) and para-intake.service (:8787)
        persist identically to novahorizon production.
        """
        self.paygate_db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.paygate_db_path), timeout=10.0) as pg_conn:
            pg_conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS paygate_sessions (
                    session_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    offer_sku TEXT NOT NULL,
                    customer_email TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    payment_methods_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'CREATED',
                    unsubscribe_token TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS paygate_optouts (
                    email TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    rfc8058_compliant INTEGER NOT NULL DEFAULT 1,
                    opted_out_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

        self.intake_db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.intake_db_path), timeout=10.0) as in_conn:
            in_conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS intake_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    order_id TEXT,
                    customer_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'NORMAL',
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def seed_reference_catalog(self) -> None:
        """
        Idempotently seeds PrintDeck's Master SKUs (PD-*) across all 9 POD verticals
        plus the 3 protected Bambu Lab 4.3" touchscreen hardware SKUs (HW-*),
        along with dual-provider Printify + Printful mappings.
        """
        products_seed = [
            # 1. Canvas Painting (24"x36" = 7200x10800 px @ 300 DPI)
            {
                "product_id": "prod_canvas_24x36",
                "master_sku": "PD-CANVAS-24X36",
                "slug": "museum-gallery-wrap-canvas-24x36",
                "title": "24\"×36\" Museum Gallery-Wrap Fine Art Canvas Painting",
                "description": "Archival poly-cotton artist canvas stretched over 1.5\" kiln-dried pine stretcher bars with mirrored gallery-wrap bleed.",
                "vertical": "canvas_painting",
                "print_area_width_in": 24.0,
                "print_area_height_in": 36.0,
                "required_dpi": 300,
                "bleed_margin_in": 1.5,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 1,
                "base_retail_price_cents": 14900,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 2. Framed Fine Art (18"x24" = 5400x7200 px @ 300 DPI)
            {
                "product_id": "prod_framed_18x24",
                "master_sku": "PD-FRAMED-18X24",
                "slug": "archival-framed-fine-art-18x24",
                "title": "18\"×24\" Museum Framed Giclée Fine Art Print",
                "description": "10.3 mil museum-grade matte paper in solid alder wood black frame with acrylite front protector.",
                "vertical": "framed_fine_art",
                "print_area_width_in": 18.0,
                "print_area_height_in": 24.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.25,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 11900,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 3. DTG Apparel — Heavyweight Hoodie (12"x16" = 3600x4800 px @ 300 DPI)
            {
                "product_id": "prod_hoodie_heavy",
                "master_sku": "PD-HOODIE-HEAVY",
                "slug": "heavyweight-atelier-art-hoodie",
                "title": "PrintDeck Heavyweight 400GSM Atelier Graphic Hoodie",
                "description": "Ring-spun combed cotton fleece hoodie with 300-DPI zero-halo DTG center chest & back fine art print.",
                "vertical": "dtg_apparel",
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.25,
                "requires_transparent_alpha": 1,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 6800,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 4. DTG Apparel — Supima Graphic Tee (12"x16" = 3600x4800 px @ 300 DPI)
            {
                "product_id": "prod_tee_supima",
                "master_sku": "PD-TEE-SUPIMA",
                "slug": "luxury-garment-dyed-studio-tee",
                "title": "PrintDeck Garment-Dyed Heavyweight Studio Tee",
                "description": "100% ring-spun cotton heavyweight tee with pre-flight alpha-sanitized DTG artwork.",
                "vertical": "dtg_apparel",
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.25,
                "requires_transparent_alpha": 1,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 3800,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 5. All-Over-Print Apparel (30"x36" = 9000x10800 px @ 300 DPI)
            {
                "product_id": "prod_aop_crewneck",
                "master_sku": "PD-AOP-CREWNECK",
                "slug": "all-over-print-cut-and-sew-crewneck",
                "title": "Full-Bleed Cut & Sew All-Over-Print Art Sweatshirt",
                "description": "Precision sublimation printed panels hand-sewn with brushed fleece lining.",
                "vertical": "aop_apparel",
                "print_area_width_in": 30.0,
                "print_area_height_in": 36.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.5,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 6400,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 6. Headwear (4.0"x2.25" = 1200x675 px @ 300 DPI)
            {
                "product_id": "prod_cap_snapback",
                "master_sku": "PD-CAP-SNAPBACK",
                "slug": "structured-atelier-snapback-cap",
                "title": "PrintDeck Structured 6-Panel Atelier Snapback",
                "description": "High-profile wool-blend snapback with high-density front graphic patch.",
                "vertical": "headwear",
                "print_area_width_in": 4.0,
                "print_area_height_in": 2.25,
                "required_dpi": 300,
                "bleed_margin_in": 0.125,
                "requires_transparent_alpha": 1,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 3200,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 7. Mugs & Drinkware (8.5"x3.5" = 2550x1050 px @ 300 DPI)
            {
                "product_id": "prod_mug_15oz",
                "master_sku": "PD-MUG-15OZ-BLK",
                "slug": "artisan-15oz-ceramic-collector-mug",
                "title": "15oz Matte Black Ceramic Collector Art Mug",
                "description": "Panoramic wrap-around 300-DPI dye-sublimation ceramic mug, dishwasher and microwave safe.",
                "vertical": "mug_drinkware",
                "print_area_width_in": 8.5,
                "print_area_height_in": 3.5,
                "required_dpi": 300,
                "bleed_margin_in": 0.125,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 2400,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 8. Desk Mat (31.5"x15.5" = 9450x4650 px @ 300 DPI)
            {
                "product_id": "prod_deskmat_xxl",
                "master_sku": "PD-DESKMAT-XXL",
                "slug": "xxl-architect-stitched-desk-mat",
                "title": "XXL 31.5\"×15.5\" Stitched-Edge Studio Desk Mat",
                "description": "4mm thick non-slip rubber base with micro-woven 300-DPI high-definition optical surface.",
                "vertical": "desk_mat",
                "print_area_width_in": 31.5,
                "print_area_height_in": 15.5,
                "required_dpi": 300,
                "bleed_margin_in": 0.25,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 3900,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 9. Decal / Sticker (6"x6" = 1800x1800 px @ 300 DPI)
            {
                "product_id": "prod_decal_6x6",
                "master_sku": "PD-DECAL-KISS-6X6",
                "slug": "kiss-cut-weatherproof-art-decal-6x6",
                "title": "6\"×6\" Weatherproof UV-Laminated Fine Art Vinyl Decal",
                "description": "Precision kiss-cut vinyl decal with clean zero-halo alpha border and 5-year UV rating.",
                "vertical": "decal_sticker",
                "print_area_width_in": 6.0,
                "print_area_height_in": 6.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.125,
                "requires_transparent_alpha": 1,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 1200,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 10. Custom Memorabilia (8"x10" = 2400x3000 px @ 300 DPI)
            {
                "product_id": "prod_acrylic_8x10",
                "master_sku": "PD-ACRYLIC-PLAQUE-8X10",
                "slug": "museum-optical-acrylic-art-block-8x10",
                "title": "8\"×10\" Optical Crystal Acrylic Collector Memorabilia Plaque",
                "description": "1-inch thick hand-polished crystal acrylic block with back-mounted 300-DPI HD print.",
                "vertical": "custom_memorabilia",
                "print_area_width_in": 8.0,
                "print_area_height_in": 10.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.25,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 8900,
                "is_legacy_hardware": 0,
                "protected_route": None,
            },
            # 11. Protected Legacy Hardware Coexistence (/hardware & /simulator)
            {
                "product_id": "prod_hw_bambu_ctrl",
                "master_sku": "HW-BAMBU-43-CTRL",
                "slug": "bambu-lab-43-esp32-p4-touchscreen-controller",
                "title": "PrintDeck Bambu Lab 4.3\" ESP32-P4 Touchscreen Controller",
                "description": "Complete plug-and-play 4.3\" IPS capacitive touchscreen controller for Bambu Lab P1P/P1S/X1/A1 printers.",
                "vertical": "legacy_hardware",
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.0,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 12900,
                "is_legacy_hardware": 1,
                "protected_route": "/hardware",
            },
            {
                "product_id": "prod_hw_maker_pack_19",
                "master_sku": "HW-MAKER-PACK-19",
                "slug": "printdeck-bambu-maker-pack-license",
                "title": "PrintDeck $19 Maker Pack (STL Enclosures + Firmware License)",
                "description": "Digital download: CNC/3D-printable bezel STLs, wiring harness BOM, and flashed ESP32-P4 firmware license.",
                "vertical": "legacy_hardware",
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.0,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 1900,
                "is_legacy_hardware": 1,
                "protected_route": "/hardware",
            },
            {
                "product_id": "prod_hw_beta_deposit_50",
                "master_sku": "HW-BETA-DEPOSIT-50",
                "slug": "printdeck-beta-hardware-batch-deposit",
                "title": "PrintDeck $50 Beta Hardware Reservation Deposit",
                "description": "Priority Batch #1 reservation deposit for the assembled Bambu Lab 4.3\" Touchscreen Controller.",
                "vertical": "legacy_hardware",
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
                "required_dpi": 300,
                "bleed_margin_in": 0.0,
                "requires_transparent_alpha": 0,
                "gallery_wrap_bleed": 0,
                "base_retail_price_cents": 5000,
                "is_legacy_hardware": 1,
                "protected_route": "/hardware",
            },
        ]

        variants_seed = [
            # Canvas 24x36
            {
                "variant_id": "var_canvas_24x36_wrap",
                "product_id": "prod_canvas_24x36",
                "variant_sku": "PD-CANVAS-24X36-WRAP",
                "title": "24\"×36\" — 1.5\" Gallery Wrap",
                "size_code": "24x36",
                "color_name": "Archival White",
                "color_hex": "#FFFFFF",
                "garment_is_dark": 0,
                "retail_price_cents": 14900,
                "weight_grams": 1850,
                "print_area_width_in": 24.0,
                "print_area_height_in": 36.0,
            },
            # Framed Fine Art 18x24
            {
                "variant_id": "var_framed_18x24_blk",
                "product_id": "prod_framed_18x24",
                "variant_sku": "PD-FRAMED-18X24-BLK",
                "title": "18\"×24\" — Obsidian Wood Frame",
                "size_code": "18x24",
                "color_name": "Obsidian Black",
                "color_hex": "#111111",
                "garment_is_dark": 0,
                "retail_price_cents": 11900,
                "weight_grams": 1600,
                "print_area_width_in": 18.0,
                "print_area_height_in": 24.0,
            },
            # Hoodie Heavyweight — Black M, L, XL
            {
                "variant_id": "var_hoodie_blk_m",
                "product_id": "prod_hoodie_heavy",
                "variant_sku": "PD-HOODIE-HEAVY-BLK-M",
                "title": "Heavyweight Hoodie — Obsidian Black / M",
                "size_code": "M",
                "color_name": "Obsidian Black",
                "color_hex": "#0B0B0B",
                "garment_is_dark": 1,
                "retail_price_cents": 6800,
                "weight_grams": 620,
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
            },
            {
                "variant_id": "var_hoodie_blk_l",
                "product_id": "prod_hoodie_heavy",
                "variant_sku": "PD-HOODIE-HEAVY-BLK-L",
                "title": "Heavyweight Hoodie — Obsidian Black / L",
                "size_code": "L",
                "color_name": "Obsidian Black",
                "color_hex": "#0B0B0B",
                "garment_is_dark": 1,
                "retail_price_cents": 6800,
                "weight_grams": 660,
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
            },
            {
                "variant_id": "var_hoodie_blk_xl",
                "product_id": "prod_hoodie_heavy",
                "variant_sku": "PD-HOODIE-HEAVY-BLK-XL",
                "title": "Heavyweight Hoodie — Obsidian Black / XL",
                "size_code": "XL",
                "color_name": "Obsidian Black",
                "color_hex": "#0B0B0B",
                "garment_is_dark": 1,
                "retail_price_cents": 7000,
                "weight_grams": 710,
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
            },
            # Tee Supima — Black L
            {
                "variant_id": "var_tee_blk_l",
                "product_id": "prod_tee_supima",
                "variant_sku": "PD-TEE-SUPIMA-BLK-L",
                "title": "Studio Heavyweight Tee — Vintage Black / L",
                "size_code": "L",
                "color_name": "Vintage Black",
                "color_hex": "#161616",
                "garment_is_dark": 1,
                "retail_price_cents": 3800,
                "weight_grams": 260,
                "print_area_width_in": 12.0,
                "print_area_height_in": 16.0,
            },
            # AOP Crewneck — L
            {
                "variant_id": "var_aop_crew_l",
                "product_id": "prod_aop_crewneck",
                "variant_sku": "PD-AOP-CREWNECK-L",
                "title": "All-Over-Print Crewneck — L",
                "size_code": "L",
                "color_name": "Full Bleed Sublimation",
                "color_hex": "#FFFFFF",
                "garment_is_dark": 0,
                "retail_price_cents": 6400,
                "weight_grams": 450,
                "print_area_width_in": 30.0,
                "print_area_height_in": 36.0,
            },
            # Snapback Cap
            {
                "variant_id": "var_cap_snapback_blk",
                "product_id": "prod_cap_snapback",
                "variant_sku": "PD-CAP-SNAPBACK-BLK-OS",
                "title": "Structured 6-Panel Snapback — Black / One Size",
                "size_code": "OS",
                "color_name": "Black",
                "color_hex": "#101010",
                "garment_is_dark": 1,
                "retail_price_cents": 3200,
                "weight_grams": 140,
                "print_area_width_in": 4.0,
                "print_area_height_in": 2.25,
            },
            # 15oz Mug
            {
                "variant_id": "var_mug_15oz_blk",
                "product_id": "prod_mug_15oz",
                "variant_sku": "PD-MUG-15OZ-BLK-STD",
                "title": "15oz Collector Mug — Matte Black",
                "size_code": "15oz",
                "color_name": "Matte Black",
                "color_hex": "#121212",
                "garment_is_dark": 1,
                "retail_price_cents": 2400,
                "weight_grams": 480,
                "print_area_width_in": 8.5,
                "print_area_height_in": 3.5,
            },
            # XXL Desk Mat
            {
                "variant_id": "var_deskmat_xxl_std",
                "product_id": "prod_deskmat_xxl",
                "variant_sku": "PD-DESKMAT-XXL-31X15",
                "title": "31.5\"×15.5\" Studio Desk Mat",
                "size_code": "31.5x15.5",
                "color_name": "Obsidian Trim",
                "color_hex": "#0F0F0F",
                "garment_is_dark": 0,
                "retail_price_cents": 3900,
                "weight_grams": 780,
                "print_area_width_in": 31.5,
                "print_area_height_in": 15.5,
            },
            # 6x6 Decal
            {
                "variant_id": "var_decal_6x6_std",
                "product_id": "prod_decal_6x6",
                "variant_sku": "PD-DECAL-KISS-6X6-STD",
                "title": "6\"×6\" Kiss-Cut Weatherproof Decal",
                "size_code": "6x6",
                "color_name": "Transparent Gloss",
                "color_hex": "#FFFFFF",
                "garment_is_dark": 0,
                "retail_price_cents": 1200,
                "weight_grams": 30,
                "print_area_width_in": 6.0,
                "print_area_height_in": 6.0,
            },
            # 8x10 Acrylic Memorabilia Block
            {
                "variant_id": "var_acrylic_8x10_std",
                "product_id": "prod_acrylic_8x10",
                "variant_sku": "PD-ACRYLIC-PLAQUE-8X10-STD",
                "title": "8\"×10\" Crystal Acrylic Collector Block",
                "size_code": "8x10",
                "color_name": "Optical Clear",
                "color_hex": "#FFFFFF",
                "garment_is_dark": 0,
                "retail_price_cents": 8900,
                "weight_grams": 1150,
                "print_area_width_in": 8.0,
                "print_area_height_in": 10.0,
            },
            # Legacy Hardware Variants
            {
                "variant_id": "var_hw_bambu_ctrl",
                "product_id": "prod_hw_bambu_ctrl",
                "variant_sku": "HW-BAMBU-43-CTRL-STD",
                "title": "Bambu Lab 4.3\" ESP32-P4 Touchscreen Controller (Assembled)",
                "size_code": "4.3in",
                "color_name": "Carbon Grey",
                "color_hex": "#2B2B2B",
                "garment_is_dark": 1,
                "retail_price_cents": 12900,
                "weight_grams": 320,
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
            },
            {
                "variant_id": "var_hw_maker_pack_19",
                "product_id": "prod_hw_maker_pack_19",
                "variant_sku": "HW-MAKER-PACK-19-DIG",
                "title": "$19 Maker Pack Digital License",
                "size_code": "DIGITAL",
                "color_name": "N/A",
                "color_hex": "#000000",
                "garment_is_dark": 0,
                "retail_price_cents": 1900,
                "weight_grams": 0,
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
            },
            {
                "variant_id": "var_hw_beta_deposit_50",
                "product_id": "prod_hw_beta_deposit_50",
                "variant_sku": "HW-BETA-DEPOSIT-50-RES",
                "title": "$50 Beta Hardware Reservation Deposit",
                "size_code": "DEPOSIT",
                "color_name": "N/A",
                "color_hex": "#000000",
                "garment_is_dark": 0,
                "retail_price_cents": 5000,
                "weight_grams": 0,
                "print_area_width_in": 0.0,
                "print_area_height_in": 0.0,
            },
        ]

        # Dual-Provider Mappings (Printify + Printful v2) for all POD variants
        mappings_seed = [
            # 1. Canvas 24x36: Printify (Sensaria) vs Printful (NC/TX Fine Art Hub)
            {
                "mapping_id": "map_canvas_24x36_printify",
                "variant_id": "var_canvas_24x36_wrap",
                "master_sku": "PD-CANVAS-24X36",
                "provider": "printify",
                "external_blueprint_id": "bp_50",
                "external_print_provider_id": "pp_2",
                "external_variant_id": "pfy_var_55024",
                "provider_name_label": "Printify — Sensaria Fine Art (Janesville, WI)",
                "base_blank_cost_cents": 4280,
                "base_shipping_cents": 1199,
                "additional_item_shipping_cents": 450,
                "volume_tier_discount_bps": 2000,  # 20% Printify Premium discount
                "facility_region": "US-MIDWEST",
                "facility_zip_prefix": "535",
                "avg_production_hours": 32.0,
                "quality_rating": 4.9,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_canvas_24x36_printful",
                "variant_id": "var_canvas_24x36_wrap",
                "master_sku": "PD-CANVAS-24X36",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_3",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_825",
                "provider_name_label": "Printful — Charlotte Fine Art Hub (NC)",
                "base_blank_cost_cents": 4650,
                "base_shipping_cents": 1299,
                "additional_item_shipping_cents": 500,
                "volume_tier_discount_bps": 1200,  # 12% Printful Pro volume tier
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 28.0,
                "quality_rating": 4.95,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 2. Framed Fine Art 18x24
            {
                "mapping_id": "map_framed_18x24_printify",
                "variant_id": "var_framed_18x24_blk",
                "master_sku": "PD-FRAMED-18X24",
                "provider": "printify",
                "external_blueprint_id": "bp_492",
                "external_print_provider_id": "pp_2",
                "external_variant_id": "pfy_var_66210",
                "provider_name_label": "Printify — Sensaria Framed Gallery",
                "base_blank_cost_cents": 3890,
                "base_shipping_cents": 1099,
                "additional_item_shipping_cents": 400,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-MIDWEST",
                "facility_zip_prefix": "535",
                "avg_production_hours": 36.0,
                "quality_rating": 4.85,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_framed_18x24_printful",
                "variant_id": "var_framed_18x24_blk",
                "master_sku": "PD-FRAMED-18X24",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_4",
                "external_print_provider_id": "pf_hub_dfw",
                "external_variant_id": "pf_var_1350",
                "provider_name_label": "Printful — Dallas Framing Hub (TX)",
                "base_blank_cost_cents": 4100,
                "base_shipping_cents": 999,
                "additional_item_shipping_cents": 350,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-SOUTH",
                "facility_zip_prefix": "752",
                "avg_production_hours": 26.0,
                "quality_rating": 4.92,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 3. Heavyweight Hoodie M, L, XL (Monster Digital vs Printful Charlotte)
            {
                "mapping_id": "map_hoodie_blk_m_printify",
                "variant_id": "var_hoodie_blk_m",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printify",
                "external_blueprint_id": "bp_77",
                "external_print_provider_id": "pp_29",
                "external_variant_id": "pfy_var_32918",
                "provider_name_label": "Printify — Monster Digital (Miami, FL / Juarez)",
                "base_blank_cost_cents": 2150,
                "base_shipping_cents": 849,
                "additional_item_shipping_cents": 250,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "331",
                "avg_production_hours": 24.0,
                "quality_rating": 4.9,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_hoodie_blk_m_printful",
                "variant_id": "var_hoodie_blk_m",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_380",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_10779",
                "provider_name_label": "Printful — Charlotte Apparel DTG (NC)",
                "base_blank_cost_cents": 2495,
                "base_shipping_cents": 799,
                "additional_item_shipping_cents": 220,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 22.0,
                "quality_rating": 4.92,
                "in_stock": 1,
                "priority_rank": 2,
            },
            {
                "mapping_id": "map_hoodie_blk_l_printify",
                "variant_id": "var_hoodie_blk_l",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printify",
                "external_blueprint_id": "bp_77",
                "external_print_provider_id": "pp_29",
                "external_variant_id": "pfy_var_32919",
                "provider_name_label": "Printify — Monster Digital (Miami, FL)",
                "base_blank_cost_cents": 2150,
                "base_shipping_cents": 849,
                "additional_item_shipping_cents": 250,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "331",
                "avg_production_hours": 24.0,
                "quality_rating": 4.9,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_hoodie_blk_l_printful",
                "variant_id": "var_hoodie_blk_l",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_380",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_10780",
                "provider_name_label": "Printful — Charlotte Apparel DTG (NC)",
                "base_blank_cost_cents": 2495,
                "base_shipping_cents": 799,
                "additional_item_shipping_cents": 220,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 22.0,
                "quality_rating": 4.92,
                "in_stock": 1,
                "priority_rank": 2,
            },
            {
                "mapping_id": "map_hoodie_blk_xl_printify",
                "variant_id": "var_hoodie_blk_xl",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printify",
                "external_blueprint_id": "bp_77",
                "external_print_provider_id": "pp_29",
                "external_variant_id": "pfy_var_32920",
                "provider_name_label": "Printify — Monster Digital (Miami, FL)",
                "base_blank_cost_cents": 2250,
                "base_shipping_cents": 849,
                "additional_item_shipping_cents": 250,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "331",
                "avg_production_hours": 24.0,
                "quality_rating": 4.9,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_hoodie_blk_xl_printful",
                "variant_id": "var_hoodie_blk_xl",
                "master_sku": "PD-HOODIE-HEAVY",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_380",
                "external_print_provider_id": "pf_hub_lax",
                "external_variant_id": "pf_var_10781",
                "provider_name_label": "Printful — West Coast DTG Hub (CA)",
                "base_blank_cost_cents": 2595,
                "base_shipping_cents": 749,
                "additional_item_shipping_cents": 220,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-WEST",
                "facility_zip_prefix": "900",
                "avg_production_hours": 20.0,
                "quality_rating": 4.94,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 4. Studio Heavyweight Tee L
            {
                "mapping_id": "map_tee_blk_l_printify",
                "variant_id": "var_tee_blk_l",
                "master_sku": "PD-TEE-SUPIMA",
                "provider": "printify",
                "external_blueprint_id": "bp_706",
                "external_print_provider_id": "pp_39",
                "external_variant_id": "pfy_var_73199",
                "provider_name_label": "Printify — SwiftPOD (San Jose, CA)",
                "base_blank_cost_cents": 1180,
                "base_shipping_cents": 475,
                "additional_item_shipping_cents": 240,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-WEST",
                "facility_zip_prefix": "951",
                "avg_production_hours": 26.0,
                "quality_rating": 4.82,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_tee_blk_l_printful",
                "variant_id": "var_tee_blk_l",
                "master_sku": "PD-TEE-SUPIMA",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_586",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_15116",
                "provider_name_label": "Printful — Comfort Colors 1717 Hub (NC)",
                "base_blank_cost_cents": 1350,
                "base_shipping_cents": 469,
                "additional_item_shipping_cents": 220,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 20.0,
                "quality_rating": 4.95,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 5. AOP Crewneck L
            {
                "mapping_id": "map_aop_crew_l_printify",
                "variant_id": "var_aop_crew_l",
                "master_sku": "PD-AOP-CREWNECK",
                "provider": "printify",
                "external_blueprint_id": "bp_288",
                "external_print_provider_id": "pp_10",
                "external_variant_id": "pfy_var_45102",
                "provider_name_label": "Printify — MWW On Demand (NC)",
                "base_blank_cost_cents": 2340,
                "base_shipping_cents": 699,
                "additional_item_shipping_cents": 250,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "287",
                "avg_production_hours": 42.0,
                "quality_rating": 4.85,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_aop_crew_l_printful",
                "variant_id": "var_aop_crew_l",
                "master_sku": "PD-AOP-CREWNECK",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_257",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_8854",
                "provider_name_label": "Printful — Cut & Sew Sublimation Hub (NC)",
                "base_blank_cost_cents": 2595,
                "base_shipping_cents": 649,
                "additional_item_shipping_cents": 200,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 36.0,
                "quality_rating": 4.93,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 6. Structured Snapback Cap
            {
                "mapping_id": "map_cap_snapback_printify",
                "variant_id": "var_cap_snapback_blk",
                "master_sku": "PD-CAP-SNAPBACK",
                "provider": "printify",
                "external_blueprint_id": "bp_1140",
                "external_print_provider_id": "pp_61",
                "external_variant_id": "pfy_var_85100",
                "provider_name_label": "Printify — OTTO Cap Specialist (TX)",
                "base_blank_cost_cents": 1250,
                "base_shipping_cents": 499,
                "additional_item_shipping_cents": 199,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-SOUTH",
                "facility_zip_prefix": "750",
                "avg_production_hours": 30.0,
                "quality_rating": 4.8,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_cap_snapback_printful",
                "variant_id": "var_cap_snapback_blk",
                "master_sku": "PD-CAP-SNAPBACK",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_99",
                "external_print_provider_id": "pf_hub_dfw",
                "external_variant_id": "pf_var_4790",
                "provider_name_label": "Printful — Yupoong 6089M Headwear Hub (TX)",
                "base_blank_cost_cents": 1395,
                "base_shipping_cents": 449,
                "additional_item_shipping_cents": 150,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-SOUTH",
                "facility_zip_prefix": "752",
                "avg_production_hours": 24.0,
                "quality_rating": 4.95,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 7. 15oz Mug
            {
                "mapping_id": "map_mug_15oz_printify",
                "variant_id": "var_mug_15oz_blk",
                "master_sku": "PD-MUG-15OZ-BLK",
                "provider": "printify",
                "external_blueprint_id": "bp_425",
                "external_print_provider_id": "pp_28",
                "external_variant_id": "pfy_var_61099",
                "provider_name_label": "Printify — District Photo Drinkware (MD)",
                "base_blank_cost_cents": 590,
                "base_shipping_cents": 659,
                "additional_item_shipping_cents": 280,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "207",
                "avg_production_hours": 20.0,
                "quality_rating": 4.88,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_mug_15oz_printful",
                "variant_id": "var_mug_15oz_blk",
                "master_sku": "PD-MUG-15OZ-BLK",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_300",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_9322",
                "provider_name_label": "Printful — Ceramic Sublimation Hub (NC)",
                "base_blank_cost_cents": 795,
                "base_shipping_cents": 699,
                "additional_item_shipping_cents": 300,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 24.0,
                "quality_rating": 4.91,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 8. XXL Desk Mat
            {
                "mapping_id": "map_deskmat_xxl_printify",
                "variant_id": "var_deskmat_xxl_std",
                "master_sku": "PD-DESKMAT-XXL",
                "provider": "printify",
                "external_blueprint_id": "bp_943",
                "external_print_provider_id": "pp_10",
                "external_variant_id": "pfy_var_78901",
                "provider_name_label": "Printify — MWW Studio Desk Mats (NC)",
                "base_blank_cost_cents": 1280,
                "base_shipping_cents": 639,
                "additional_item_shipping_cents": 220,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "287",
                "avg_production_hours": 28.0,
                "quality_rating": 4.9,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_deskmat_xxl_printful",
                "variant_id": "var_deskmat_xxl_std",
                "master_sku": "PD-DESKMAT-XXL",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_614",
                "external_print_provider_id": "pf_hub_lax",
                "external_variant_id": "pf_var_15921",
                "provider_name_label": "Printful — Gaming & Studio Desk Mats (CA)",
                "base_blank_cost_cents": 1450,
                "base_shipping_cents": 599,
                "additional_item_shipping_cents": 200,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-WEST",
                "facility_zip_prefix": "900",
                "avg_production_hours": 24.0,
                "quality_rating": 4.92,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 9. 6x6 Kiss-Cut Decal
            {
                "mapping_id": "map_decal_6x6_printify",
                "variant_id": "var_decal_6x6_std",
                "master_sku": "PD-DECAL-KISS-6X6",
                "provider": "printify",
                "external_blueprint_id": "bp_400",
                "external_print_provider_id": "pp_72",
                "external_variant_id": "pfy_var_60125",
                "provider_name_label": "Printify — SPOKE Custom Decals (GA)",
                "base_blank_cost_cents": 265,
                "base_shipping_cents": 399,
                "additional_item_shipping_cents": 50,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-SOUTH",
                "facility_zip_prefix": "300",
                "avg_production_hours": 18.0,
                "quality_rating": 4.86,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_decal_6x6_printful",
                "variant_id": "var_decal_6x6_std",
                "master_sku": "PD-DECAL-KISS-6X6",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_358",
                "external_print_provider_id": "pf_hub_clt",
                "external_variant_id": "pf_var_10165",
                "provider_name_label": "Printful — Kiss-Cut Vinyl Hub (NC)",
                "base_blank_cost_cents": 295,
                "base_shipping_cents": 399,
                "additional_item_shipping_cents": 40,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-EAST",
                "facility_zip_prefix": "282",
                "avg_production_hours": 16.0,
                "quality_rating": 4.93,
                "in_stock": 1,
                "priority_rank": 2,
            },
            # 10. 8x10 Acrylic Collector Memorabilia Block
            {
                "mapping_id": "map_acrylic_8x10_printify",
                "variant_id": "var_acrylic_8x10_std",
                "master_sku": "PD-ACRYLIC-PLAQUE-8X10",
                "provider": "printify",
                "external_blueprint_id": "bp_832",
                "external_print_provider_id": "pp_2",
                "external_variant_id": "pfy_var_75440",
                "provider_name_label": "Printify — Sensaria Acrylic Fine Art (WI)",
                "base_blank_cost_cents": 2790,
                "base_shipping_cents": 949,
                "additional_item_shipping_cents": 350,
                "volume_tier_discount_bps": 2000,
                "facility_region": "US-MIDWEST",
                "facility_zip_prefix": "535",
                "avg_production_hours": 36.0,
                "quality_rating": 4.91,
                "in_stock": 1,
                "priority_rank": 1,
            },
            {
                "mapping_id": "map_acrylic_8x10_printful",
                "variant_id": "var_acrylic_8x10_std",
                "master_sku": "PD-ACRYLIC-PLAQUE-8X10",
                "provider": "printful",
                "external_blueprint_id": "pf_cat_712",
                "external_print_provider_id": "pf_hub_dfw",
                "external_variant_id": "pf_var_18200",
                "provider_name_label": "Printful — Acrylic Memorabilia Hub (TX)",
                "base_blank_cost_cents": 3150,
                "base_shipping_cents": 899,
                "additional_item_shipping_cents": 300,
                "volume_tier_discount_bps": 1200,
                "facility_region": "US-SOUTH",
                "facility_zip_prefix": "752",
                "avg_production_hours": 30.0,
                "quality_rating": 4.94,
                "in_stock": 1,
                "priority_rank": 2,
            },
        ]

        with self.connect() as conn:
            for p in products_seed:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO products (
                        product_id, master_sku, slug, title, description, vertical,
                        print_area_width_in, print_area_height_in, required_dpi,
                        bleed_margin_in, requires_transparent_alpha, gallery_wrap_bleed,
                        base_retail_price_cents, is_legacy_hardware, protected_route
                    ) VALUES (
                        :product_id, :master_sku, :slug, :title, :description, :vertical,
                        :print_area_width_in, :print_area_height_in, :required_dpi,
                        :bleed_margin_in, :requires_transparent_alpha, :gallery_wrap_bleed,
                        :base_retail_price_cents, :is_legacy_hardware, :protected_route
                    )
                    """,
                    p,
                )

            for v in variants_seed:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO product_variants (
                        variant_id, product_id, variant_sku, title, size_code,
                        color_name, color_hex, garment_is_dark, retail_price_cents,
                        weight_grams, print_area_width_in, print_area_height_in
                    ) VALUES (
                        :variant_id, :product_id, :variant_sku, :title, :size_code,
                        :color_name, :color_hex, :garment_is_dark, :retail_price_cents,
                        :weight_grams, :print_area_width_in, :print_area_height_in
                    )
                    """,
                    v,
                )

            for m in mappings_seed:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pod_provider_mappings (
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
                    """,
                    m,
                )

    # --------------------------------------------------------------------------
    # Query & Mutation Helpers
    # --------------------------------------------------------------------------
    def list_products(self, include_hardware: bool = True) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            if include_hardware:
                rows = conn.execute(
                    "SELECT * FROM products WHERE active = 1 ORDER BY is_legacy_hardware ASC, master_sku ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM products WHERE active = 1 AND is_legacy_hardware = 0 ORDER BY master_sku ASC"
                ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                variants = conn.execute(
                    "SELECT * FROM product_variants WHERE product_id = ? AND active = 1",
                    (d["product_id"],),
                ).fetchall()
                d["variants"] = [dict(v) for v in variants]
                result.append(d)
            return result

    def get_variant_with_mappings(self, variant_id_or_sku: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.master_sku, p.vertical, p.required_dpi, p.bleed_margin_in,
                       p.requires_transparent_alpha, p.gallery_wrap_bleed, p.is_legacy_hardware,
                       p.title AS product_title
                FROM product_variants v
                JOIN products p ON p.product_id = v.product_id
                WHERE v.variant_id = ? OR v.variant_sku = ?
                """,
                (variant_id_or_sku, variant_id_or_sku),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            mappings = conn.execute(
                """
                SELECT * FROM pod_provider_mappings
                WHERE variant_id = ?
                ORDER BY priority_rank ASC
                """,
                (data["variant_id"],),
            ).fetchall()
            data["provider_mappings"] = [dict(m) for m in mappings]
            return data

    def save_print_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        asset_id = asset.get("asset_id") or f"ast_{uuid.uuid4().hex[:12]}"
        payload = {
            "asset_id": asset_id,
            "product_id": asset.get("product_id"),
            "title": asset.get("title", "Untitled Print Asset"),
            "source_filename": asset.get("source_filename", "upload.png"),
            "sha256_hash": asset.get("sha256_hash", hashlib.sha256(asset_id.encode()).hexdigest()),
            "storage_uri": asset.get("storage_uri", f"file:///var/www/printdeck/assets/{asset_id}.png"),
            "original_width_px": int(asset["original_width_px"]),
            "original_height_px": int(asset["original_height_px"]),
            "target_width_in": float(asset["target_width_in"]),
            "target_height_in": float(asset["target_height_in"]),
            "required_width_px": int(asset["required_width_px"]),
            "required_height_px": int(asset["required_height_px"]),
            "final_width_px": int(asset["final_width_px"]),
            "final_height_px": int(asset["final_height_px"]),
            "effective_dpi_x": float(asset["effective_dpi_x"]),
            "effective_dpi_y": float(asset["effective_dpi_y"]),
            "upscaled": int(bool(asset.get("upscaled", False))),
            "upscale_node": asset.get("upscale_node", "native"),
            "upscale_scale_factor": float(asset.get("upscale_scale_factor", 1.0)),
            "icc_profile_name": asset.get("icc_profile_name", "sRGB IEC61966-2.1"),
            "icc_gamut_verified": int(bool(asset.get("icc_gamut_verified", True))),
            "out_of_gamut_pixel_ratio": float(asset.get("out_of_gamut_pixel_ratio", 0.0)),
            "alpha_channel_sanitized": int(bool(asset.get("alpha_channel_sanitized", False))),
            "semi_transparent_pixels_removed": int(asset.get("semi_transparent_pixels_removed", 0)),
            "bleed_verified": int(bool(asset.get("bleed_verified", True))),
            "bleed_margin_px": int(asset.get("bleed_margin_px", 0)),
            "trademark_passed": int(bool(asset.get("trademark_passed", True))),
            "trademark_report_json": json.dumps(asset.get("trademark_report", {})),
            "preflight_status": asset.get("preflight_status", "PASSED_300DPI"),
            "printify_upload_id": asset.get("printify_upload_id"),
            "printful_file_id": asset.get("printful_file_id"),
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO print_assets (
                    asset_id, product_id, title, source_filename, sha256_hash, storage_uri,
                    original_width_px, original_height_px, target_width_in, target_height_in,
                    required_width_px, required_height_px, final_width_px, final_height_px,
                    effective_dpi_x, effective_dpi_y, upscaled, upscale_node, upscale_scale_factor,
                    icc_profile_name, icc_gamut_verified, out_of_gamut_pixel_ratio,
                    alpha_channel_sanitized, semi_transparent_pixels_removed,
                    bleed_verified, bleed_margin_px, trademark_Passed, trademark_report_json,
                    preflight_status, printify_upload_id, printful_file_id
                ) VALUES (
                    :asset_id, :product_id, :title, :source_filename, :sha256_hash, :storage_uri,
                    :original_width_px, :original_height_px, :target_width_in, :target_height_in,
                    :required_width_px, :required_height_px, :final_width_px, :final_height_px,
                    :effective_dpi_x, :effective_dpi_y, :upscaled, :upscale_node, :upscale_scale_factor,
                    :icc_profile_name, :icc_gamut_verified, :out_of_gamut_pixel_ratio,
                    :alpha_channel_sanitized, :semi_transparent_pixels_removed,
                    :bleed_verified, :bleed_margin_px, :trademark_passed, :trademark_report_json,
                    :preflight_status, :printify_upload_id, :printful_file_id
                )
                """,
                payload,
            )
        return payload

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE order_id = ? OR order_number = ?",
                (order_id, order_id),
            ).fetchone()
            if not row:
                return None
            order = dict(row)
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY created_at ASC",
                (order["order_id"],),
            ).fetchall()
            holds = conn.execute(
                "SELECT * FROM fulfillment_holds WHERE order_id = ? ORDER BY created_at DESC",
                (order["order_id"],),
            ).fetchall()
            order["items"] = [dict(i) for i in items]
            order["holds"] = [dict(h) for h in holds]
            return order


_DEFAULT_DB_INSTANCE: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    global _DEFAULT_DB_INSTANCE
    if _DEFAULT_DB_INSTANCE is None:
        _DEFAULT_DB_INSTANCE = DatabaseManager()
    return _DEFAULT_DB_INSTANCE


PrintDeckDB = DatabaseManager

