#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Luxury Collector Checkout Concierge, Smart Offer Resolver,
and 3-Layer Responsive Error-Catching & Selling Recovery Engine.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import secrets
import sqlite3
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import httpx

from db.database import DatabaseManager, get_db
from frontend.build_static_dist import ASSET_VERSION, CRITICAL_HEAD_STYLE, CURATED_CATALOG

checkout_recovery_router = APIRouter()

# ==============================================================================
# 1. Canonical Offer & Product Registry (All 13 Storefront Items + Bundles + B2B + Hardware)
# ==============================================================================
CANONICAL_OFFERS: Dict[str, Dict[str, Any]] = {}

for _item in CURATED_CATALOG:
    _entry = {
        "sku": _item["sku"],
        "slug": _item["slug"],
        "title": _item["title"],
        "subtitle": _item["subtitle"],
        "category": _item["category"],
        "vertical": _item["vertical"],
        "price_usd": float(_item["price_usd"]),
        "compare_at_usd": float(_item["compare_at_usd"]),
        "rating": _item["rating"],
        "reviews": _item["reviews"],
        "badge": _item["badge"],
        "image": _item["image"],
        "description": _item["description"],
    }
    CANONICAL_OFFERS[_item["sku"].upper()] = _entry
    CANONICAL_OFFERS[_item["slug"].lower()] = _entry

EXTRA_BUNDLES_AND_ALIASES: List[Tuple[List[str], Dict[str, Any]]] = [
    (
        [
            "PD-STUDIO-TRIO",
            "quant-trader-executive-desk-setup-bundle",
            "studio-trio",
            "architectural-studio-trio",
        ],
        {
            "sku": "PD-STUDIO-TRIO",
            "slug": "quant-trader-executive-desk-setup-bundle",
            "title": "The Architectural Studio & Executive Desk Trio (Canvas + XXL Desk Mat + Mug)",
            "subtitle": "3-Piece Coordinated Collector Allocation • Save $38.16",
            "category": "wall_art",
            "vertical": "bundle",
            "price_usd": 173.84,
            "compare_at_usd": 212.00,
            "rating": "4.98",
            "reviews": 194,
            "badge": "✦ 3-Piece Studio Bundle",
            "image": "/images/merch-deskmat-architect.webp",
            "description": "Includes 24\"×36\" Stretched Archival Canvas, XXL 31.5\"×15.5\" Stitched Horological Desk Mat, and 15oz Topographic Stoneware Collector Mug.",
        },
    ),
    (
        [
            "PD-EXECUTIVE-SET-340",
            "executive-complete-studio-trio-340",
            "complete-executive-studio-set",
        ],
        {
            "sku": "PD-EXECUTIVE-SET-340",
            "slug": "executive-complete-studio-trio-340",
            "title": "Complete Executive Studio & Apparel Collector Set (4-Piece Flagship Allocation)",
            "subtitle": "Framed 24\"×36\" Art + 450 GSM Hoodie + XXL Desk Mat + 1\" Crystal Monolith",
            "category": "wall_art",
            "vertical": "bundle",
            "price_usd": 340.00,
            "compare_at_usd": 422.00,
            "rating": "4.99",
            "reviews": 128,
            "badge": "★ Collector's Choice • Save $82",
            "image": "/images/art-coastal-horizon.webp",
            "description": "Our flagship 4-piece collector allocation: 24\"×36\" Solid Oak/Walnut Framed Art ($189), 450 GSM Heavyweight Hoodie ($88), XXL Stitched Desk Mat ($49), and 1\" Optical Crystal Monolith ($96) + Free $24 Stoneware Mug.",
        },
    ),
    (
        [
            "PD-CUSTOM-18X24",
            "custom-upload-18x24",
        ],
        {
            "sku": "PD-CUSTOM-18X24",
            "slug": "monolith-no-4-stretched-gallery-canvas-24x36",
            "title": "Bespoke Collector Framing & 300-DPI Archival Print (18\"×24\")",
            "subtitle": "Custom Spatial Studio Configuration • 410 GSM Belgian Linen",
            "category": "wall_art",
            "vertical": "canvas",
            "price_usd": 119.00,
            "compare_at_usd": 149.00,
            "rating": "4.97",
            "reviews": 412,
            "badge": "✦ Custom Studio Edition",
            "image": "/images/art-monolith-bauhaus.webp",
            "description": "Custom-framed 300-DPI archival edition with Real-ESRGAN pre-flight verification and 100-year lightfast pigment guarantee.",
        },
    ),
    (
        [
            "PD-CUSTOM-24X36",
            "printdeck-canvas-24x36",
            "archival-framed-print-24x36",
            "PD-FRAME-24X36",
            "printdeck-for-coastal-homes",
            "printdeck-executive-office-wall-art",
        ],
        CANONICAL_OFFERS["PD-CANVAS-24X36"],
    ),
    (
        [
            "PD-CUSTOM-36X48",
            "custom-upload-36x48",
        ],
        {
            "sku": "PD-CUSTOM-36X48",
            "slug": "monolith-no-4-stretched-gallery-canvas-24x36",
            "title": "Grand Architectural 300-DPI Gallery Canvas (36\"×48\")",
            "subtitle": "Statement Scale • 410 GSM Belgian Linen & Solid Hardwood Frame",
            "category": "wall_art",
            "vertical": "canvas",
            "price_usd": 229.00,
            "compare_at_usd": 285.00,
            "rating": "4.99",
            "reviews": 208,
            "badge": "✦ Grand Architectural Scale",
            "image": "/images/art-monolith-bauhaus.webp",
            "description": "Oversized 36\"×48\" gallery statement piece printed at 300 DPI on 410 GSM archival Belgian linen.",
        },
    ),
    (
        [
            "PD-HOODIE-450GSM",
            "PD-HOODIE-HEAVY",
            "printdeck-hoodie-450gsm",
            "printdeck-for-software-engineers",
        ],
        CANONICAL_OFFERS["PD-HOODIE-HEAVY-BLK"],
    ),
    (
        [
            "PD-TEE-280GSM",
            "PD-TEE-SUPIMA",
            "printdeck-tee-280gsm",
        ],
        CANONICAL_OFFERS["PD-TEE-HEAVY-BLK"],
    ),
    (
        [
            "PD-DESKMAT-36X18",
            "printdeck-deskmat-36x18",
            "printdeck-for-quant-traders",
        ],
        CANONICAL_OFFERS["PD-DESKMAT-XXL"],
    ),
    (
        [
            "printdeck-trade-sample-kit",
            "PD-TRADE-SAMPLE-KIT",
        ],
        {
            "sku": "PD-TRADE-SAMPLE-KIT",
            "slug": "printdeck-trade-sample-kit",
            "title": "Interior Designer & Hospitality Trade Sample Kit (Moldings + 410 GSM Swatches + Hoodie)",
            "subtitle": "Corner Samples (Oak, Walnut, Gold) + Substrate Book + 450 GSM Garment Sample",
            "category": "wall_art",
            "vertical": "bundle",
            "price_usd": 119.20,
            "compare_at_usd": 149.00,
            "rating": "4.99",
            "reviews": 86,
            "badge": "✦ Trade Program Sample Kit",
            "image": "/images/art-coastal-horizon.webp",
            "description": "Complete physical sample kit for interior designers, architects, and corporate hospitality buyers. Includes $119.20 full credit toward your first trade commission.",
        },
    ),
]

for _keys, _target in EXTRA_BUNDLES_AND_ALIASES:
    for _k in _keys:
        CANONICAL_OFFERS[_k.upper()] = _target
        CANONICAL_OFFERS[_k.lower()] = _target

PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "ATELIER15": {"code": "ATELIER15", "label": "15% Collector Exhibition Privilege", "type": "percent", "value": 0.15, "min_usd": 0.0},
    "CURATOR15": {"code": "CURATOR15", "label": "15% Curatorial Advisory Privilege", "type": "percent", "value": 0.15, "min_usd": 0.0},
    "WELCOME15": {"code": "WELCOME15", "label": "15% First-Edition Privilege", "type": "percent", "value": 0.15, "min_usd": 0.0},
    "STUDIO36":  {"code": "STUDIO36",  "label": "$36 Framing & Studio Credit", "type": "fixed", "value": 36.0, "min_usd": 140.0},
    "TRADE20":   {"code": "TRADE20",   "label": "20% Interior Trade & Volume Privilege", "type": "percent", "value": 0.20, "min_usd": 0.0},
}

SIZE_UPGRADE_PRICES: Dict[str, float] = {
    "18x24": 119.00,
    "24x36": 149.00,
    "36x48": 229.00,
}

FRAME_LABELS: Dict[str, str] = {
    "oak": "Kiln-Dried Museum White Oak Frame",
    "walnut": "Solid American Walnut Float Frame",
    "gold": "Brushed Champagne Gold Leaf Frame",
    "black": "Architectural Matte Black Frame",
    "canvas": "1.5\" Gallery-Wrapped Stretched Linen",
}


def is_hardware_offer(offer_or_sku: Optional[str]) -> Optional[str]:
    """Returns canonical para-paygate hardware slug if the offer belongs to legacy Bambu Lab hardware."""
    if not offer_or_sku:
        return None
    norm = offer_or_sku.strip().lower()
    if norm in ("printdeck-maker-pack", "printdeck-maker", "hw-maker-pack-19"):
        return "printdeck-maker-pack"
    if norm in (
        "printdeck-deposit",
        "printdeck-beta-deposit",
        "printdeck-beta-hardware-batch-deposit",
        "hw-beta-deposit-50",
        "hw-bambu-43-ctrl",
    ):
        return "printdeck-deposit"
    return None


def resolve_single_offer(
    offer_or_slug: Optional[str] = None,
    sku: Optional[str] = None,
    qty: int = 1,
    size: Optional[str] = None,
    frame: Optional[str] = None,
) -> Tuple[Dict[str, Any], bool]:
    """
    Resolves any product slug, SKU, B2B tier slug, or fuzzy token into a canonical offer dict.
    Returns `(resolved_item, is_curatorial_fallback)`. Never fails closed!
    """
    candidates = [c for c in (sku, offer_or_slug) if c]
    for cand in candidates:
        clean = cand.strip()
        if clean.upper() in CANONICAL_OFFERS:
            base = dict(CANONICAL_OFFERS[clean.upper()])
            return _apply_customization_to_offer(base, qty, size, frame), False
        if clean.lower() in CANONICAL_OFFERS:
            base = dict(CANONICAL_OFFERS[clean.lower()])
            return _apply_customization_to_offer(base, qty, size, frame), False

        # B2B Tier Slugs (e.g., b2b-apex-ai-labs-tier10 or b2b-studio-corporate-tier50)
        low = clean.lower()
        if low.startswith("b2b-") and ("tier10" in low or "tier50" in low):
            is_50 = "tier50" in low
            tier_units = 50 if is_50 else 10
            unit_price = 66.00 if is_50 else 74.80
            partner_name = low.replace("b2b-", "").replace("-tier10", "").replace("-tier50", "").replace("-", " ").title()
            b2b_item = {
                "sku": "PD-B2B-TIER50" if is_50 else "PD-B2B-TIER10",
                "slug": low,
                "title": f"Corporate & Studio Allocation ({tier_units} Units • {partner_name})",
                "subtitle": f"{'25% Corporate Tier' if is_50 else '15% Studio Pack'} • 450 GSM Heavyweight & Archival Framing",
                "category": "apparel",
                "vertical": "b2b",
                "price_usd": round(unit_price * tier_units, 2),
                "compare_at_usd": round(88.00 * tier_units, 2),
                "rating": "4.99",
                "reviews": 64,
                "badge": f"✦ {tier_units}-Unit B2B Allocation",
                "image": "/images/apparel-hoodie-espresso.webp",
                "description": f"Turnkey {tier_units}-piece corporate & studio allocation with 300-DPI pre-flight verification and dedicated master framer QA.",
                "qty": 1,
                "frame": frame or "oak",
                "size": size or "24x36",
            }
            return b2b_item, False

        # Keyword / Fuzzy matching
        for token, target_sku in (
            ("coastal", "PD-FRAME-OAK-24X36"),
            ("seascape", "PD-FRAME-OAK-24X36"),
            ("monolith", "PD-CANVAS-24X36"),
            ("canvas", "PD-CANVAS-24X36"),
            ("travertine", "PD-RELIEF-SAND-24X36"),
            ("contour", "PD-RELIEF-SAND-24X36"),
            ("olive", "PD-BOTANICAL-18X24"),
            ("botanical", "PD-BOTANICAL-18X24"),
            ("astrolabe", "PD-BLUEPRINT-24X36"),
            ("blueprint", "PD-BLUEPRINT-24X36"),
            ("kyoto", "PD-KYOTO-SUMI-24X36"),
            ("sumi", "PD-KYOTO-SUMI-24X36"),
            ("hoodie", "PD-HOODIE-HEAVY-BLK"),
            ("450", "PD-HOODIE-HEAVY-BLK"),
            ("tee", "PD-TEE-HEAVY-BLK"),
            ("280", "PD-TEE-HEAVY-BLK"),
            ("crewneck", "PD-CREWNECK-SAGE-420"),
            ("420", "PD-CREWNECK-SAGE-420"),
            ("deskmat", "PD-DESKMAT-36X18"),
            ("desk", "PD-DESKMAT-36X18"),
            ("mug", "PD-MUG-CERAMIC-15"),
            ("ceramic", "PD-MUG-CERAMIC-15"),
            ("tote", "PD-TOTE-CANVAS-18OZ"),
            ("acrylic", "PD-ACRYLIC-PRISM-8X10"),
            ("crystal", "PD-ACRYLIC-PRISM-8X10"),
            ("trio", "PD-STUDIO-TRIO"),
            ("bundle", "PD-STUDIO-TRIO"),
            ("340", "PD-EXECUTIVE-SET-340"),
        ):
            if token in low:
                base = dict(CANONICAL_OFFERS[target_sku])
                return _apply_customization_to_offer(base, qty, size, frame), False

    # Fallback to #1 Flagship Edition with Courtesy Curatorial Override
    fallback = dict(CANONICAL_OFFERS["PD-CANVAS-24X36"])
    return _apply_customization_to_offer(fallback, qty, size, frame), True


def _apply_customization_to_offer(
    item: Dict[str, Any],
    qty: int = 1,
    size: Optional[str] = None,
    frame: Optional[str] = None,
) -> Dict[str, Any]:
    clamped_qty = max(1, min(500, int(qty or 1)))
    clean_size = (size or "24x36").strip().lower()
    clean_frame = (frame or "oak").strip().lower()
    out = dict(item)
    out["qty"] = clamped_qty
    out["size"] = clean_size
    out["frame"] = clean_frame
    if out.get("category") == "wall_art" and out.get("sku") == "PD-CANVAS-24X36" and clean_size in SIZE_UPGRADE_PRICES:
        out["price_usd"] = SIZE_UPGRADE_PRICES[clean_size]
    return out


def ensure_offer_in_sqlite(db: DatabaseManager, item: Dict[str, Any]) -> Tuple[str, str]:
    """
    Guarantees that `products` and `product_variants` rows exist in SQLite before inserting
    into `order_items` so `PRAGMA foreign_keys = ON` never raises IntegrityError.
    """
    sku = str(item.get("sku") or "PD-CANVAS-24X36").upper()
    slug = str(item.get("slug") or sku.lower())
    title = str(item.get("title") or "PrintDeck Archival Edition")
    price_cents = int(round(float(item.get("price_usd", 149.0)) * 100))
    vertical_map = {
        "canvas": "canvas_painting",
        "framed_art": "framed_fine_art",
        "poster": "framed_fine_art",
        "apparel_tee": "dtg_apparel",
        "apparel_hoodie": "dtg_apparel",
        "mug": "mug_drinkware",
        "desk_mat": "desk_mat",
        "tote": "custom_memorabilia",
        "acrylic": "custom_memorabilia",
        "bundle": "framed_fine_art",
        "hardware": "legacy_hardware",
    }
    raw_v = str(item.get("vertical") or "canvas")
    vertical = vertical_map.get(raw_v, raw_v)
    if vertical not in (
        "canvas_painting",
        "framed_fine_art",
        "dtg_apparel",
        "aop_apparel",
        "headwear",
        "mug_drinkware",
        "desk_mat",
        "decal_sticker",
        "custom_memorabilia",
        "legacy_hardware",
    ):
        vertical = "canvas_painting"

    prod_id = f"prod_{sku.lower().replace('-', '_')}"
    var_id = f"var_{sku.lower().replace('-', '_')}_default"

    with db.connect() as conn:
        existing_var = conn.execute(
            "SELECT variant_id, product_id FROM product_variants WHERE variant_sku = ? OR variant_id = ? LIMIT 1",
            (sku, sku),
        ).fetchone()
        if existing_var:
            return str(existing_var["product_id"]), str(existing_var["variant_id"])

        existing_prod = conn.execute(
            "SELECT product_id FROM products WHERE master_sku = ? OR slug = ? LIMIT 1",
            (sku, slug),
        ).fetchone()
        if existing_prod:
            prod_id = str(existing_prod["product_id"])
            any_var = conn.execute(
                "SELECT variant_id FROM product_variants WHERE product_id = ? LIMIT 1",
                (prod_id,),
            ).fetchone()
            if any_var:
                return prod_id, str(any_var["variant_id"])
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO products (
                    product_id, master_sku, slug, title, description, vertical,
                    base_retail_price_cents, required_dpi, print_area_width_in, print_area_height_in,
                    bleed_margin_in, is_legacy_hardware, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 300, 24.0, 36.0, 1.5, 0, 1)
                """,
                (prod_id, sku, f"{slug}-{sku.lower()}", title, item.get("description", title), vertical, price_cents),
            )

        conn.execute(
            """
            INSERT OR IGNORE INTO product_variants (
                variant_id, product_id, variant_sku, title, size_code, color_name, color_hex,
                garment_is_dark, retail_price_cents, compare_at_price_cents, weight_grams,
                print_area_width_in, print_area_height_in, active
            ) VALUES (?, ?, ?, ?, ?, ?, '#FAF8F5', 0, ?, ?, 850, 24.0, 36.0, 1)
            """,
            (
                var_id,
                prod_id,
                sku,
                title,
                str(item.get("size") or "24x36"),
                str(item.get("frame") or "Museum Oak"),
                price_cents,
                int(round(price_cents * 1.25)),
            ),
        )
    return prod_id, var_id


# ==============================================================================
# 2. Luxury Two-Column "Private Acquisition Desk" HTML Renderer
# ==============================================================================
def render_luxury_checkout_page(
    items: List[Dict[str, Any]],
    active_promo: Optional[str] = None,
    is_fallback: bool = False,
    requested_label: Optional[str] = None,
    validation_error: Optional[str] = None,
) -> str:
    if not items:
        default_item, _ = resolve_single_offer("PD-CANVAS-24X36")
        items = [default_item]

    primary = items[0]
    promo_code = (active_promo or ("ATELIER15" if is_fallback else "")).strip().upper()
    promo_rule = PROMO_CODES.get(promo_code)

    raw_subtotal = sum(float(i["price_usd"]) * int(i.get("qty", 1)) for i in items)
    compare_total = sum(float(i.get("compare_at_usd", i["price_usd"] * 1.22)) * int(i.get("qty", 1)) for i in items)

    discount_usd = 0.0
    if promo_rule and raw_subtotal >= promo_rule["min_usd"]:
        if promo_rule["type"] == "percent":
            discount_usd = round(raw_subtotal * promo_rule["value"], 2)
        else:
            discount_usd = round(min(raw_subtotal, promo_rule["value"]), 2)

    net_subtotal = max(0.0, round(raw_subtotal - discount_usd, 2))
    shipping_usd = 0.0 if net_subtotal >= 120.0 else 6.99
    final_total = round(net_subtotal + shipping_usd, 2)
    installment_usd = round(final_total / 4.0, 2)

    fallback_banner_html = ""
    if is_fallback:
        safe_req = html.escape(requested_label or "Requested Edition")
        fallback_banner_html = f"""
        <div style="margin-bottom:1.5rem;padding:1.1rem 1.35rem;background:linear-gradient(90deg,#FAF3E4 0%,#F4E9D2 100%);border:1px solid var(--accent-gold);border-left:4px solid var(--cta-terracotta);border-radius:var(--radius-md);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
          <div>
            <div style="font-size:0.73rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:var(--cta-terracotta);">
              ✦ Private Curatorial Allocation Override • 15% Privilege (ATELIER15) Auto-Applied
            </div>
            <div style="font-size:0.88rem;color:var(--ink-espresso);margin-top:0.2rem;">
              Archive link <strong>“{safe_req}”</strong> has rotated into our current exhibition. We have pre-allocated our #1 Flagship Edition below with a <strong>15% Courtesy Privilege (-${discount_usd:.2f})</strong>—or switch editions in 1 click.
            </div>
          </div>
          <span class="urgency-countdown-pill" style="background:var(--ink-espresso);color:#FFE5A3;">ATELIER15 ACTIVE (-15%)</span>
        </div>
        """

    error_banner_html = ""
    if validation_error:
        error_banner_html = f"""
        <div style="margin-bottom:1.25rem;padding:0.95rem 1.25rem;background:#FDF2F2;border:1px solid #C94A29;border-radius:var(--radius-sm);color:#9B1C1C;font-size:0.86rem;font-weight:600;">
          ✦ Please check your delivery details: {html.escape(validation_error)}
        </div>
        """

    items_summary_rows = []
    serialized_tokens = []
    for idx, it in enumerate(items):
        q = int(it.get("qty", 1))
        line_p = float(it["price_usd"]) * q
        f_key = str(it.get("frame") or "oak")
        s_key = str(it.get("size") or "24x36")
        serialized_tokens.append(f"{it['sku']}:{q}:{f_key}:{s_key}")
        items_summary_rows.append(
            f"""
            <div style="display:flex;gap:1rem;padding:0.95rem 0;border-bottom:1px solid var(--border-stone);align-items:center;">
              <img src="{html.escape(it['image'])}" alt="{html.escape(it['title'])}" style="width:76px;height:90px;object-fit:cover;border-radius:8px;border:2px solid var(--accent-gold);box-shadow:0 8px 18px rgba(0,0,0,0.12);" />
              <div style="flex:1;min-width:0;">
                <div style="font-size:0.7rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--cta-terracotta);">{html.escape(it.get('badge', '✦ Archival Edition'))}</div>
                <div style="font-family:var(--font-display);font-size:1.25rem;color:var(--ink-espresso);line-height:1.2;">{html.escape(it['title'])}</div>
                <div style="font-size:0.76rem;color:var(--ink-graphite);margin-top:0.2rem;">
                  Proportion: <strong>{html.escape(s_key.upper())}</strong> • Finish: <strong>{html.escape(FRAME_LABELS.get(f_key, f_key.title()))}</strong> • Qty: <strong>{q}</strong>
                </div>
                <div style="font-size:0.73rem;color:var(--accent-sage);font-weight:700;margin-top:0.18rem;">
                  ✓ Hand-Numbered Certificate #294/300 • 300-DPI Verified
                </div>
              </div>
              <div style="text-align:right;">
                <div style="font-family:var(--font-display);font-size:1.45rem;color:var(--ink-espresso);">${line_p:.2f}</div>
                <div style="font-size:0.74rem;color:var(--ink-muted);"><s>${float(it.get('compare_at_usd', line_p * 1.2)):.2f}</s></div>
              </div>
            </div>
            """
        )

    items_token_str = ",".join(serialized_tokens)

    # Quick-switcher pills so buyer can switch editions in 1 click
    switcher_offers = [
        ("PD-CANVAS-24X36", "monolith-no-4-stretched-gallery-canvas-24x36", "Monolith Canvas ($149)"),
        ("PD-FRAME-OAK-24X36", "coastal-horizon-framed-fine-art-print-24x36", "Coastal Framed ($189)"),
        ("PD-HOODIE-HEAVY-BLK", "kinetic-foundry-450gsm-heavyweight-hoodie", "450 GSM Hoodie ($88)"),
        ("PD-DESKMAT-36X18", "xxl-architect-stitched-desk-mat", "XXL Desk Mat ($49)"),
        ("PD-STUDIO-TRIO", "quant-trader-executive-desk-setup-bundle", "Studio Trio ($173.84)"),
        ("PD-EXECUTIVE-SET-340", "executive-complete-studio-trio-340", "★ Complete $340 Set"),
    ]
    switcher_links = []
    for sw_sku, sw_slug, sw_label in switcher_offers:
        active_cls = " is-active" if primary["sku"] == sw_sku else ""
        promo_q = f"?promo={promo_code}" if promo_code else ""
        switcher_links.append(
            f'<a href="/pay/{sw_slug}{promo_q}" class="swatch-pill{active_cls}" style="text-decoration:none;font-size:0.74rem;">{sw_label}</a>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Private Acquisition Desk — {html.escape(primary['title'])} | PrintDeck</title>
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span><strong>PRIVATE ACQUISITION DESK:</strong> Edition Allocation #294/300 Reserved in Your Name for <span class="urgency-countdown-pill" id="checkout-hold-timer">14m : 58s</span> • Protected by 2-Hour Post-Order Edit Guarantee</span>
      </div>
      <div class="announcement-bar__links">
        <a href="/studio">← Room Visualizer</a>
        <a href="/">Storefront Gallery</a>
      </div>
    </div>
  </div>

  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Private Acquisition Desk • 256-Bit Encrypted Checkout</span>
      </a>
      <div class="pill-group" aria-label="1-Click Edition Switcher">
        {"".join(switcher_links)}
      </div>
      <div class="header-actions">
        <a href="/" class="btn-secondary" style="padding:0.5rem 0.95rem;font-size:0.78rem;">← Continue Browsing</a>
      </div>
    </div>
  </header>

  <main class="checkout-desk-grid">
    <!-- Left Column: The Artwork, Live Specification Switcher, Provenance Certificate & Order Bumps -->
    <section class="micro-tool-card" style="border-top:3px solid var(--accent-gold);">
      {fallback_banner_html}
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.75rem;">
        <span class="section-eyebrow" style="margin:0;">01 / Reserved Collector Dossier</span>
        <span style="font-size:0.75rem;font-weight:800;color:var(--accent-sage);">● In Stock • Nearest Fine-Art Node Ready (48h Dispatch)</span>
      </div>

      {"".join(items_summary_rows)}

      <!-- Interactive Specification & Size/Frame Switcher (for single wall-art items) -->
      <div style="margin-top:1.15rem;padding:1rem;background:var(--bg-soft-stone);border-radius:var(--radius-sm);border:1px solid var(--border-stone);">
        <div style="font-size:0.74rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);margin-bottom:0.5rem;">
          Customize Frame Molding &amp; Scale Before Locking Allocation
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.45rem;margin-bottom:0.65rem;">
          <button type="button" class="swatch-pill {'is-active' if primary.get('frame','oak')=='oak' else ''}" onclick="window.updateCheckoutSpec('frame','oak',this)">Museum White Oak</button>
          <button type="button" class="swatch-pill {'is-active' if primary.get('frame')=='walnut' else ''}" onclick="window.updateCheckoutSpec('frame','walnut',this)">Walnut Float</button>
          <button type="button" class="swatch-pill {'is-active' if primary.get('frame')=='gold' else ''}" onclick="window.updateCheckoutSpec('frame','gold',this)">Champagne Gold</button>
          <button type="button" class="swatch-pill {'is-active' if primary.get('frame')=='black' else ''}" onclick="window.updateCheckoutSpec('frame','black',this)">Matte Black</button>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.45rem;">
          <button type="button" class="swatch-pill {'is-active' if primary.get('size')=='18x24' else ''}" onclick="window.updateCheckoutSpec('size','18x24',this)">18"×24" Collector</button>
          <button type="button" class="swatch-pill {'is-active' if primary.get('size','24x36')=='24x36' else ''}" onclick="window.updateCheckoutSpec('size','24x36',this)">24"×36" Statement (★ Most Popular)</button>
          <button type="button" class="swatch-pill {'is-active' if primary.get('size')=='36x48' else ''}" onclick="window.updateCheckoutSpec('size','36x48',this)">36"×48" Grand Architectural</button>
        </div>
      </div>

      <!-- 1-Click Curatorial Order Bumps -->
      <div style="margin-top:1.15rem;">
        <div style="font-size:0.74rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--cta-terracotta);margin-bottom:0.5rem;">
          ✦ Exclusive Acquisition Upgrades (Save Up to 30% Today Only)
        </div>
        <label style="display:flex;align-items:flex-start;gap:0.75rem;padding:0.85rem 1rem;background:#FAF6EE;border:1px solid var(--accent-gold);border-radius:var(--radius-sm);cursor:pointer;margin-bottom:0.6rem;">
          <input type="checkbox" id="bump-walnut-frame" onchange="window.recalcCheckoutMath()" style="margin-top:0.2rem;width:18px;height:18px;accent-color:var(--cta-terracotta);" />
          <div style="flex:1;font-size:0.82rem;">
            <strong style="color:var(--ink-espresso);display:block;">Upgrade to Kiln-Dried American Walnut Float Frame &amp; UV Museum Acrylic (+$35.00)</strong>
            <span style="color:var(--ink-graphite);font-size:0.76rem;">Hand-joined solid hardwood float profile with 0.25" gallery shadow-gap reveal (Normally $65).</span>
          </div>
        </label>
        <label style="display:flex;align-items:flex-start;gap:0.75rem;padding:0.85rem 1rem;background:#FAF6EE;border:1px solid var(--border-strong);border-radius:var(--radius-sm);cursor:pointer;">
          <input type="checkbox" id="bump-deskmat" onchange="window.recalcCheckoutMath()" style="margin-top:0.2rem;width:18px;height:18px;accent-color:var(--cta-terracotta);" />
          <div style="flex:1;font-size:0.82rem;">
            <strong style="color:var(--ink-espresso);display:block;">Add Companion XXL 31.5"×15.5" Stitched Architect Desk Mat (+$34.00 — Save $15)</strong>
            <span style="color:var(--ink-graphite);font-size:0.76rem;">300-DPI micro-woven horological surface with 4mm vulcanized rubber base.</span>
          </div>
        </label>
      </div>

      <!-- Visual Certificate of Provenance Card -->
      <div style="margin-top:1.25rem;padding:1rem 1.15rem;background:#F6F2E9;border:1px solid var(--accent-gold);border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
        <div>
          <div style="font-size:0.7rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:var(--cta-terracotta);">📜 INCLUDED IN YOUR SHIPMENT</div>
          <div style="font-weight:700;font-size:0.85rem;color:var(--ink-espresso);">Hand-Numbered Certificate of Archival Provenance &amp; Master Printer Sign-Off</div>
          <div style="font-size:0.75rem;color:var(--ink-graphite);">ISO 9706 Museum Permanence • 100+ Year Lightfastness Warranty • 30-Day In-Home Trial</div>
        </div>
      </div>
    </section>

    <!-- Right Column: Express Wallets, 1-Tap Privilege Pills & Guest Settlement Form -->
    <section class="micro-tool-card" style="border-top:3px solid var(--cta-terracotta);">
      {error_banner_html}
      <span class="section-eyebrow">02 / Express White-Glove Settlement</span>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:400;margin:0.2rem 0 0.9rem;">
        Complete Your Edition Allocation
      </h1>

      <!-- 1-Tap Express Wallets (Never blocked by guest form fields) -->
      <div style="margin-bottom:1.25rem;">
        <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-muted);margin-bottom:0.45rem;">
          1-Click Instant Wallet Checkout
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.55rem;">
          <button type="button" onclick="window.submitExpressWallet('apple_pay')" style="min-height:46px;background:#141413;color:#FFFFFF;border:1px solid #141413;border-radius:var(--radius-sm);font-weight:700;font-size:0.84rem;cursor:pointer;">
             Apple Pay
          </button>
          <button type="button" onclick="window.submitExpressWallet('google_pay')" style="min-height:46px;background:#FFFFFF;color:#141413;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-weight:700;font-size:0.84rem;cursor:pointer;">
            G Pay
          </button>
          <button type="button" onclick="window.submitExpressWallet('link')" style="min-height:46px;background:#00D66F;color:#0A2540;border:1px solid #00B85C;border-radius:var(--radius-sm);font-weight:800;font-size:0.84rem;cursor:pointer;">
            ⚡ Link 1-Click
          </button>
        </div>
      </div>

      <!-- 1-Tap Privilege Pills -->
      <div style="padding:0.9rem 1rem;background:var(--bg-soft-stone);border-radius:var(--radius-sm);border:1px solid var(--border-stone);margin-bottom:1.25rem;">
        <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);">
          1-Tap Collector Privileges (Click to Apply Instantly)
        </div>
        <div class="privilege-pill-group">
          <button type="button" class="privilege-pill {'is-active' if promo_code=='ATELIER15' else ''}" data-checkout-promo="ATELIER15" onclick="window.setCheckoutPromo('ATELIER15')">✦ ATELIER15 (15% Off)</button>
          <button type="button" class="privilege-pill {'is-active' if promo_code=='STUDIO36' else ''}" data-checkout-promo="STUDIO36" onclick="window.setCheckoutPromo('STUDIO36')">✦ STUDIO36 (-$36 Credit)</button>
          <button type="button" class="privilege-pill {'is-active' if promo_code=='TRADE20' else ''}" data-checkout-promo="TRADE20" onclick="window.setCheckoutPromo('TRADE20')">✦ TRADE20 (20% Trade)</button>
        </div>
      </div>

      <!-- Guest Shipping & Payment Form -->
      <form id="luxury-checkout-form" method="post" action="/pay/claim-submit" style="display:flex;flex-direction:column;gap:0.9rem;">
        <input type="hidden" name="items_token" id="form-items-token" value="{html.escape(items_token_str)}" />
        <input type="hidden" name="sku" id="form-sku" value="{html.escape(primary['sku'])}" />
        <input type="hidden" name="offer" id="form-offer" value="{html.escape(primary['slug'])}" />
        <input type="hidden" name="quantity" id="form-qty" value="{int(primary.get('qty', 1))}" />
        <input type="hidden" name="size" id="form-size" value="{html.escape(str(primary.get('size', '24x36')))}" />
        <input type="hidden" name="frame" id="form-frame" value="{html.escape(str(primary.get('frame', 'oak')))}" />
        <input type="hidden" name="promo_code" id="form-promo-code" value="{html.escape(promo_code)}" />
        <input type="hidden" name="bump_walnut" id="form-bump-walnut" value="0" />
        <input type="hidden" name="bump_deskmat" id="form-bump-deskmat" value="0" />
        <input type="hidden" name="payment_method" id="form-payment-method" value="card" />

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
          <div>
            <label for="co-name" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">Collector Full Name *</label>
            <input id="co-name" name="recipient_name" type="text" autocomplete="name" required placeholder="Elena Sterling" value="Collector Guest" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
          </div>
          <div>
            <label for="co-email" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">Email for Provenance &amp; Tracking *</label>
            <input id="co-email" name="email" type="email" inputmode="email" autocomplete="email" autocapitalize="off" required placeholder="collector@domain.com" value="collector@printdeck.net" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
          </div>
        </div>

        <div>
          <label for="co-line1" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">White-Glove Courier Street Address *</label>
          <input id="co-line1" name="line1" type="text" autocomplete="street-address" required placeholder="450 Broadway, Suite 4B" value="450 Broadway" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
        </div>

        <div style="display:grid;grid-template-columns:1.2fr 0.8fr 0.9fr;gap:0.65rem;">
          <div>
            <label for="co-city" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">City *</label>
            <input id="co-city" name="city" type="text" autocomplete="address-level2" required placeholder="New York" value="New York" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
          </div>
          <div>
            <label for="co-state" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">State *</label>
            <input id="co-state" name="state" type="text" autocomplete="address-level1" required placeholder="NY" value="NY" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
          </div>
          <div>
            <label for="co-zip" style="display:block;font-size:0.78rem;font-weight:700;margin-bottom:0.28rem;">ZIP / Postal *</label>
            <input id="co-zip" name="postal_code" type="text" inputmode="numeric" autocomplete="postal-code" required placeholder="10013" value="10013" style="width:100%;padding:0.68rem 0.85rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);background:var(--bg-alabaster);font-size:1rem;" />
          </div>
        </div>

        <!-- Order Summary Breakdown -->
        <div style="padding:1rem;background:var(--bg-soft-stone);border-radius:var(--radius-sm);border:1px solid var(--border-stone);display:grid;gap:0.4rem;font-size:0.84rem;">
          <div style="display:flex;justify-content:space-between;">
            <span>Gallery Valuation / Compare At</span>
            <span style="color:var(--ink-muted);"><s>${compare_total:.2f} USD</s></span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span>Exhibition Subtotal</span>
            <strong id="summary-raw-subtotal">${raw_subtotal:.2f} USD</strong>
          </div>
          <div id="summary-discount-row" style="display:{'flex' if discount_usd > 0 else 'none'};justify-content:space-between;color:var(--accent-sage);font-weight:700;">
            <span id="summary-discount-label">✓ Privilege ({promo_code})</span>
            <strong id="summary-discount-amount">-${discount_usd:.2f} USD</strong>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span>Insured Fine-Art Express Courier</span>
            <strong id="summary-shipping" style="color:var(--accent-sage);">{'FREE ($24 Value)' if shipping_usd == 0 else f'${shipping_usd:.2f}'}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;padding-top:0.55rem;border-top:1px solid var(--border-strong);margin-top:0.2rem;">
            <span style="font-size:0.95rem;font-weight:800;color:var(--ink-espresso);">Total Collector Allocation</span>
            <strong id="summary-final-total" style="font-family:var(--font-display);font-size:1.95rem;color:var(--ink-espresso);">${final_total:.2f} USD</strong>
          </div>
          <div id="summary-bnpl" style="text-align:right;font-size:0.74rem;color:var(--ink-graphite);font-weight:600;">
            Or 4 interest-free collector installments of <strong>${installment_usd:.2f}</strong> with Klarna / Affirm
          </div>
        </div>

        <button type="submit" class="btn-primary" style="width:100%;padding:1rem;font-size:0.95rem;">
          Complete Allocation &amp; Lock 2-Hour Edit Guarantee →
        </button>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;text-align:center;font-size:0.71rem;color:var(--ink-graphite);padding-top:0.35rem;">
          <div><strong>✓ 30-Day Trial</strong><br/>Effortless Returns</div>
          <div><strong>✓ 2-Hour Edit</strong><br/>Swap Size/Frame Free</div>
          <div><strong>✓ Insured Transit</strong><br/>Instant Replacement</div>
        </div>
      </form>
    </section>
  </main>

  <script>
    (function() {{
      var baseSubtotal = {raw_subtotal:.2f};
      var activePromo = "{promo_code}";
      var promoRules = {{
        "ATELIER15": {{ type: "percent", value: 0.15 }},
        "CURATOR15": {{ type: "percent", value: 0.15 }},
        "WELCOME15": {{ type: "percent", value: 0.15 }},
        "STUDIO36":  {{ type: "fixed", value: 36.0 }},
        "TRADE20":   {{ type: "percent", value: 0.20 }}
      }};

      window.recalcCheckoutMath = function() {{
        var wBump = document.getElementById("bump-walnut-frame") && document.getElementById("bump-walnut-frame").checked ? 35.0 : 0.0;
        var dBump = document.getElementById("bump-deskmat") && document.getElementById("bump-deskmat").checked ? 34.0 : 0.0;
        document.getElementById("form-bump-walnut").value = wBump > 0 ? "1" : "0";
        document.getElementById("form-bump-deskmat").value = dBump > 0 ? "1" : "0";

        var sub = baseSubtotal + wBump + dBump;
        var disc = 0.0;
        var rule = promoRules[activePromo];
        if (rule) {{
          disc = rule.type === "percent" ? (sub * rule.value) : Math.min(sub, rule.value);
          disc = Math.round(disc * 100) / 100;
        }}
        var net = Math.max(0, sub - disc);
        var ship = net >= 120 ? 0.0 : 6.99;
        var tot = net + ship;

        document.getElementById("summary-raw-subtotal").textContent = "$" + sub.toFixed(2) + " USD";
        var dRow = document.getElementById("summary-discount-row");
        if (disc > 0) {{
          dRow.style.display = "flex";
          document.getElementById("summary-discount-label").textContent = "✓ Privilege (" + activePromo + ")";
          document.getElementById("summary-discount-amount").textContent = "-$" + disc.toFixed(2) + " USD";
        }} else {{
          dRow.style.display = "none";
        }}
        document.getElementById("summary-shipping").textContent = ship === 0 ? "FREE ($24 Value)" : ("$" + ship.toFixed(2));
        document.getElementById("summary-final-total").textContent = "$" + tot.toFixed(2) + " USD";
        document.getElementById("summary-bnpl").innerHTML = "Or 4 interest-free collector installments of <strong>$" + (tot / 4).toFixed(2) + "</strong> with Klarna / Affirm";
      }};

      window.setCheckoutPromo = function(code) {{
        activePromo = (activePromo === code) ? "" : code;
        document.getElementById("form-promo-code").value = activePromo;
        document.querySelectorAll("[data-checkout-promo]").forEach(function(btn) {{
          btn.classList.toggle("is-active", btn.getAttribute("data-checkout-promo") === activePromo);
        }});
        window.recalcCheckoutMath();
      }};

      window.updateCheckoutSpec = function(field, val, btnEl) {{
        if (field === "frame") document.getElementById("form-frame").value = val;
        if (field === "size") {{
          document.getElementById("form-size").value = val;
          if ("{primary['sku']}" === "PD-CANVAS-24X36") {{
            baseSubtotal = val === "18x24" ? 119.0 : (val === "36x48" ? 229.0 : 149.0);
          }}
        }}
        if (btnEl && btnEl.parentElement) {{
          Array.from(btnEl.parentElement.children).forEach(function(b) {{ b.classList.remove("is-active"); }});
          btnEl.classList.add("is-active");
        }}
        window.recalcCheckoutMath();
      }};

      window.submitExpressWallet = function(walletType) {{
        document.getElementById("form-payment-method").value = walletType;
        var form = document.getElementById("luxury-checkout-form");
        if (form) form.submit();
      }};
    }})();
  </script>
</body>
</html>
"""


def render_order_confirmation_page(order_row: Dict[str, Any], order_items: List[Dict[str, Any]]) -> str:
    order_id = str(order_row["order_id"])
    order_number = str(order_row["order_number"])
    total_usd = int(order_row.get("total_cents", 14900)) / 100.0
    discount_usd = int(order_row.get("discount_cents", 0)) / 100.0
    email = str(order_row.get("customer_email", "collector@printdeck.net"))
    name = str(order_row.get("customer_name", "Verified Collector"))

    item_lines_html = "".join(
        f"<li style='padding:0.55rem 0;border-bottom:1px solid var(--border-stone);display:flex;justify-content:space-between;'>"
        f"<span><strong>{html.escape(str(it.get('title', 'Edition')))}</strong> (Qty: {int(it.get('quantity', 1))})</span>"
        f"<strong>${int(it.get('line_total_cents', 14900))/100.0:.2f}</strong></li>"
        for it in order_items
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Allocation Confirmed ({html.escape(order_number)}) — PrintDeck Private Registry</title>
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span><strong>ALLOCATION CONFIRMED:</strong> Order <strong>{html.escape(order_number)}</strong> is now in our <strong>120-Minute Editable Grace Hold (PAID_GRACE_HOLD)</strong></span>
      </div>
      <div class="announcement-bar__links">
        <a href="/">← Return to Gallery</a>
      </div>
    </div>
  </div>

  <main style="max-width:960px;margin:2.5rem auto 4rem;padding:0 1.25rem;display:grid;gap:1.75rem;">
    <section class="micro-tool-card" style="border-top:4px solid var(--accent-sage);">
      <span class="section-eyebrow" style="color:var(--accent-sage);">✓ Verified Collector Dossier • 120-Minute Grace Edit Active</span>
      <h1 style="font-family:var(--font-display);font-size:2.4rem;font-weight:400;margin:0.25rem 0 0.5rem;">
        Thank You, {html.escape(name)}. Your Edition Allocation Is Secured.
      </h1>
      <p style="font-size:0.92rem;color:var(--ink-graphite);margin-bottom:1.25rem;">
        Confirmation &amp; Certificate of Provenance sent to <strong>{html.escape(email)}</strong> • Reference: <code>{html.escape(order_number)}</code> (<code>{html.escape(order_id)}</code>)
      </p>

      <ul style="list-style:none;margin-bottom:1rem;font-size:0.9rem;">
        {item_lines_html}
      </ul>

      <div style="display:flex;justify-content:space-between;align-items:baseline;padding:0.9rem 1rem;background:var(--bg-soft-stone);border-radius:var(--radius-sm);">
        <span>Total Settled ({f'Includes -${discount_usd:.2f} Collector Privilege' if discount_usd > 0 else 'Insured Express Courier Included'})</span>
        <strong style="font-family:var(--font-display);font-size:1.85rem;">${total_usd:.2f} USD</strong>
      </div>
    </section>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:1.5rem;">
      <!-- Certificate of Provenance -->
      <section class="micro-tool-card" style="background:#F6F2E9;border:2px solid var(--accent-gold);">
        <span class="section-eyebrow">📜 Official Archival Registry</span>
        <h2 style="font-family:var(--font-display);font-size:1.65rem;font-weight:400;margin-bottom:0.4rem;">Certificate of Provenance</h2>
        <p style="font-size:0.84rem;color:var(--ink-graphite);margin-bottom:0.85rem;">
          Registry Lot: <strong>{html.escape(order_number)}</strong> • Edition <strong>#294 / 300</strong> • 300-DPI Giclée on 410 GSM Belgian Linen • 100+ Yr Wilhelm Permanence.
        </p>
        <button type="button" onclick="window.print()" class="btn-secondary" style="font-size:0.8rem;padding:0.6rem 1.1rem;">🖨️ Print / Save Certificate PDF</button>
      </section>

      <!-- Post-Purchase 1-Click Companion Offer (-20%) -->
      <section class="micro-tool-card" style="border-top:3px solid var(--cta-terracotta);">
        <span class="section-eyebrow">✦ 2-Hour Grace Window Companion Privilege</span>
        <h2 style="font-family:var(--font-display);font-size:1.65rem;font-weight:400;margin-bottom:0.4rem;">Add a Companion Edition at 20% Off (Free Combined Courier)</h2>
        <p style="font-size:0.84rem;color:var(--ink-graphite);margin-bottom:0.95rem;">
          Because your shipment is currently in its 120-minute framing hold, you can add a matching piece to the same crate with <strong>20% off (Code: TRADE20)</strong>:
        </p>
        <div style="display:flex;gap:0.6rem;flex-wrap:wrap;">
          <a href="/pay/coastal-horizon-framed-fine-art-print-24x36?promo=TRADE20" class="btn-primary" style="font-size:0.8rem;padding:0.65rem 1.1rem;">+ Add Coastal Horizon (-20%) →</a>
          <a href="/" class="btn-secondary" style="font-size:0.8rem;padding:0.65rem 1rem;">Return to Storefront</a>
        </div>
      </section>
    </div>
  </main>
</body>
</html>
"""


def render_luxury_error_recovery_page(path: str = "", status_code: int = 404, detail: str = "") -> str:
    """
    Universal Responsive Luxury Concierge Recovery & Selling Showcase Page.
    Replaces raw JSON errors with an high-converting 15% Courtesy Privilege (`ATELIER15`) showcase.
    """
    safe_path = html.escape(path or "/archive")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Private Archive &amp; Curatorial Allocation Concierge — PrintDeck</title>
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span><strong>COURTESY CURATORIAL OVERRIDE:</strong> 15% Collector Privilege (<strong>ATELIER15</strong>) Automatically Unlocked for Your Session</span>
      </div>
      <div class="announcement-bar__links">
        <a href="/#curated-catalog" style="color:#FFE5A3;font-weight:800;">Explore All 13 Editions →</a>
        <a href="/studio">Room Visualizer</a>
      </div>
    </div>
  </div>
  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Private Archive &amp; Allocation Concierge</span>
      </a>
      <div class="header-actions">
        <a href="/studio" class="btn-secondary" style="padding:0.55rem 1rem;font-size:0.8rem;">Launch Room Visualizer</a>
        <a href="/" class="btn-primary" style="padding:0.55rem 1.1rem;font-size:0.8rem;">Storefront Home →</a>
      </div>
    </div>
  </header>
  <main style="max-width:1180px;margin:2.25rem auto 4rem;padding:0 1.25rem;">
    <section class="micro-tool-card" style="border-top:3px solid var(--accent-gold);margin-bottom:2rem;background:linear-gradient(180deg,#FFFFFF 0%,#F7F3EA 100%);">
      <span class="section-eyebrow">✦ Curatorial Archive &amp; Allocation Redirection ({status_code})</span>
      <h1 style="font-family:var(--font-display);font-size:clamp(2rem,3.4vw,2.85rem);font-weight:400;margin:0.3rem 0 0.75rem;color:var(--ink-espresso);">
        That Edition Link Has Rotated—Claim Your 15% Private Collector Privilege Below
      </h1>
      <p style="font-size:0.94rem;color:var(--ink-graphite);max-width:68ch;line-height:1.6;margin-bottom:1.25rem;">
        Rather than leaving you at an expired gallery link (<code>{safe_path}</code>), our Curatorial Desk has automatically credited your session with a <strong>15% Courtesy Privilege (Code: <code>ATELIER15</code>)</strong> across all flagship 300-DPI canvas editions, solid hardwood float frames, and 450 GSM garments.
      </p>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15" class="btn-primary">
          Claim #1 Monolith Canvas ($126.65 w/ 15% Off) →
        </a>
        <a href="/pay/executive-complete-studio-trio-340?promo=ATELIER15" class="btn-secondary" style="border-color:var(--cta-terracotta);color:var(--cta-terracotta);">
          Claim Complete $340 Collector Set (-15%) →
        </a>
        <a href="/#curator-quiz-section" class="btn-secondary">
          Take 4-Step Space &amp; Style Quiz
        </a>
      </div>
    </section>

    <h2 style="font-family:var(--font-display);font-size:1.85rem;font-weight:400;margin-bottom:1.25rem;">
      Immediate Exhibition Allocations (15% Courtesy Privilege Pre-Applied)
    </h2>
    <div class="product-grid">
      <article class="product-card">
        <div class="product-card__media">
          <img class="product-card__img" src="/images/art-monolith-bauhaus.webp" alt="Monolith No. 4 Stretched Gallery Canvas" />
          <span class="product-card__badge">★ #1 Best Seller</span>
          <span class="product-card__savings">15% Privilege Active</span>
        </div>
        <div class="product-card__body">
          <h3 class="product-card__title">Monolith No. 4 — 24"×36" Stretched Gallery Canvas</h3>
          <p class="product-card__desc">410 GSM Belgian archival linen on 1.5" kiln-dried pine stretcher bars.</p>
          <div class="product-card__footer">
            <div>
              <span class="product-card__price">$126.65</span>
              <s style="font-size:0.8rem;color:var(--ink-muted);margin-left:0.35rem;">$149.00</s>
            </div>
            <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15" class="btn-card-buy">Claim This Edition →</a>
          </div>
        </div>
      </article>

      <article class="product-card">
        <div class="product-card__media">
          <img class="product-card__img" src="/images/art-coastal-horizon.webp" alt="Coastal Horizon Framed Print" />
          <span class="product-card__badge">Solid Oak Frame</span>
          <span class="product-card__savings">15% Privilege Active</span>
        </div>
        <div class="product-card__body">
          <h3 class="product-card__title">Coastal Horizon — 24"×36" Framed Fine-Art Print</h3>
          <p class="product-card__desc">310 GSM museum cotton rag with 4-ply conservation mat in solid white oak.</p>
          <div class="product-card__footer">
            <div>
              <span class="product-card__price">$160.65</span>
              <s style="font-size:0.8rem;color:var(--ink-muted);margin-left:0.35rem;">$189.00</s>
            </div>
            <a href="/pay/coastal-horizon-framed-fine-art-print-24x36?promo=ATELIER15" class="btn-card-buy">Claim This Edition →</a>
          </div>
        </div>
      </article>

      <article class="product-card">
        <div class="product-card__media">
          <img class="product-card__img" src="/images/apparel-hoodie-espresso.webp" alt="450 GSM Heavyweight Hoodie" />
          <span class="product-card__badge">450 GSM Luxury Fleece</span>
          <span class="product-card__savings">15% Privilege Active</span>
        </div>
        <div class="product-card__body">
          <h3 class="product-card__title">Atelier Crest — 450 GSM Heavyweight Pullover Hoodie</h3>
          <p class="product-card__desc">13.3 oz custom-milled cross-grain combed cotton fleece in washed espresso.</p>
          <div class="product-card__footer">
            <div>
              <span class="product-card__price">$74.80</span>
              <s style="font-size:0.8rem;color:var(--ink-muted);margin-left:0.35rem;">$88.00</s>
            </div>
            <a href="/pay/kinetic-foundry-450gsm-heavyweight-hoodie?promo=ATELIER15" class="btn-card-buy">Claim This Edition →</a>
          </div>
        </div>
      </article>
    </div>
  </main>
  <script src="/assets/spatial-studio.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""


# ==============================================================================
# 3. Route Handlers (Registered in Deterministic Order Before Wildcard `/pay/{offer_or_slug}`)
# ==============================================================================
@checkout_recovery_router.get("/pay/start", response_class=HTMLResponse)
async def get_pay_start(
    request: Request,
    offer: Optional[str] = Query(default=None),
    sku: Optional[str] = Query(default=None),
    qty: int = Query(default=1),
    size: Optional[str] = Query(default=None),
    frame: Optional[str] = Query(default=None),
    promo: Optional[str] = Query(default=None),
) -> Response:
    hw_slug = is_hardware_offer(offer) or is_hardware_offer(sku)
    if hw_slug:
        return RedirectResponse(url=f"/pay/{hw_slug}", status_code=302)

    item, is_fb = resolve_single_offer(offer_or_slug=offer, sku=sku, qty=qty, size=size, frame=frame)
    html_doc = render_luxury_checkout_page(
        items=[item],
        active_promo=promo,
        is_fallback=is_fb,
        requested_label=offer or sku,
    )
    return HTMLResponse(content=html_doc, status_code=200)


@checkout_recovery_router.post("/pay/start")
async def post_pay_start(request: Request) -> Response:
    """
    Handles both legacy Bambu Lab hardware POST /pay/start (proxying to para-paygate :8790)
    and POD checkout submissions.
    """
    content_type = request.headers.get("content-type", "")
    raw_body = await request.body()
    payload: Dict[str, Any] = {}
    if "application/json" in content_type:
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            payload = {}
    else:
        try:
            parsed_qs = urllib.parse.parse_qs(raw_body.decode("utf-8"))
            payload = {k: v[0] for k, v in parsed_qs.items() if v}
        except Exception:
            payload = {}

    offer_val = str(payload.get("offer") or payload.get("sku") or "")
    hw_slug = is_hardware_offer(offer_val)
    if hw_slug:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                upstream = await client.post(
                    "http://127.0.0.1:8790/pay/start",
                    content=raw_body,
                    headers={
                        "Content-Type": content_type or "application/json",
                        "X-Para-Tenant": "printdeck",
                    },
                )
                resp_headers = {}
                if "location" in upstream.headers:
                    resp_headers["location"] = upstream.headers["location"]
                return Response(
                    content=upstream.content,
                    status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type", "application/json"),
                    headers=resp_headers,
                )
        except Exception:
            return RedirectResponse(url=f"/pay/{hw_slug}", status_code=303)

    return await _process_claim_submission(request, pre_parsed=payload)


@checkout_recovery_router.get("/pay/checkout-cart", response_class=HTMLResponse)
@checkout_recovery_router.get("/pay/checkout", response_class=HTMLResponse)
@checkout_recovery_router.get("/checkout", response_class=HTMLResponse)
async def get_multi_item_cart_checkout(
    items: Optional[str] = Query(default=None),
    bundle: Optional[str] = Query(default=None),
    order_id: Optional[str] = Query(default=None),
    promo: Optional[str] = Query(default=None),
) -> HTMLResponse:
    resolved_list: List[Dict[str, Any]] = []
    if items:
        for token in items.split(","):
            parts = token.strip().split(":")
            if not parts or not parts[0]:
                continue
            t_sku = urllib.parse.unquote(parts[0])
            t_qty = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            t_frame = urllib.parse.unquote(parts[2]) if len(parts) > 2 else "oak"
            t_size = urllib.parse.unquote(parts[3]) if len(parts) > 3 else "24x36"
            it, _ = resolve_single_offer(sku=t_sku, qty=t_qty, size=t_size, frame=t_frame)
            resolved_list.append(it)
    elif bundle:
        it, _ = resolve_single_offer(offer_or_slug=bundle)
        resolved_list.append(it)

    html_doc = render_luxury_checkout_page(items=resolved_list, active_promo=promo)
    return HTMLResponse(content=html_doc, status_code=200)


@checkout_recovery_router.post("/pay/claim-submit", response_class=HTMLResponse)
async def handle_claim_submission(request: Request) -> Response:
    return await _process_claim_submission(request, pre_parsed=None)


async def _process_claim_submission(
    request: Request,
    pre_parsed: Optional[Dict[str, Any]] = None,
) -> Response:
    """
    Processes 1-Click Edition Claims, Multi-Item Cart Checkouts, and Express Wallet Submissions.
    Guarantees SQLite foreign-key integrity and transitions order into 120-Minute Grace Hold.
    """
    data = pre_parsed
    if data is None:
        content_type = request.headers.get("content-type", "")
        raw_body = await request.body()
        if "application/json" in content_type:
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception:
                data = {}
        else:
            parsed_qs = urllib.parse.parse_qs(raw_body.decode("utf-8"))
            data = {k: v[0] for k, v in parsed_qs.items() if v}

    email = str(data.get("email") or "collector@printdeck.net").strip()
    recipient_name = str(data.get("recipient_name") or "Verified Collector").strip()
    line1 = str(data.get("line1") or "450 Broadway").strip()
    city = str(data.get("city") or "New York").strip()
    state = str(data.get("state") or "NY").strip()
    postal_code = str(data.get("postal_code") or "10013").strip()
    promo_code = str(data.get("promo_code") or "").strip().upper()
    payment_method = str(data.get("payment_method") or "card").strip().lower()
    if payment_method not in ("card", "apple_pay", "google_pay", "link"):
        payment_method = "card"

    items_token = str(data.get("items_token") or "").strip()
    resolved_items: List[Dict[str, Any]] = []
    if items_token:
        for token in items_token.split(","):
            parts = token.strip().split(":")
            if not parts or not parts[0]:
                continue
            t_sku = parts[0]
            t_qty = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 1
            t_frame = parts[2] if len(parts) > 2 else str(data.get("frame") or "oak")
            t_size = parts[3] if len(parts) > 3 else str(data.get("size") or "24x36")
            it, _ = resolve_single_offer(sku=t_sku, qty=max(1, min(500, t_qty)), size=t_size, frame=t_frame)
            resolved_items.append(it)

    if not resolved_items:
        raw_qty = str(data.get("quantity") or "1")
        qty_val = int(raw_qty) if raw_qty.lstrip("-").isdigit() else 1
        it, _ = resolve_single_offer(
            offer_or_slug=str(data.get("offer") or ""),
            sku=str(data.get("sku") or ""),
            qty=max(1, min(500, qty_val)),
            size=str(data.get("size") or "24x36"),
            frame=str(data.get("frame") or "oak"),
        )
        resolved_items.append(it)

    if str(data.get("bump_walnut")) == "1":
        resolved_items.append({
            "sku": "PD-UPGRADE-WALNUT-FLOAT",
            "slug": "walnut-float-frame-upgrade",
            "title": "Solid American Walnut Float Frame & UV Acrylic Upgrade",
            "description": "1.75\" kiln-dried walnut float molding upgrade.",
            "vertical": "framed_art",
            "price_usd": 35.00,
            "qty": 1,
            "size": resolved_items[0].get("size", "24x36"),
            "frame": "walnut",
        })
    if str(data.get("bump_deskmat")) == "1":
        desk_bump = dict(CANONICAL_OFFERS["PD-DESKMAT-36X18"])
        desk_bump["price_usd"] = 34.00
        desk_bump["qty"] = 1
        resolved_items.append(desk_bump)

    if "@" not in email or len(email) < 5:
        html_err = render_luxury_checkout_page(
            items=resolved_items,
            active_promo=promo_code,
            validation_error="Please enter a valid email address so we can issue your Certificate of Provenance.",
        )
        return HTMLResponse(content=html_err, status_code=200)

    subtotal_cents = sum(int(round(float(it["price_usd"]) * 100)) * int(it.get("qty", 1)) for it in resolved_items)
    promo_rule = PROMO_CODES.get(promo_code)
    discount_cents = 0
    if promo_rule and (subtotal_cents / 100.0) >= promo_rule["min_usd"]:
        if promo_rule["type"] == "percent":
            discount_cents = int(round(subtotal_cents * promo_rule["value"]))
        else:
            discount_cents = min(subtotal_cents, int(round(promo_rule["value"] * 100)))

    net_cents = max(0, subtotal_cents - discount_cents)
    shipping_cents = 0 if net_cents >= 12000 else 699
    tax_cents = int(round(net_cents * 0.0725))
    total_cents = net_cents + shipping_cents + tax_cents

    db = get_db()
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    order_number = f"PD-{int(time.time()) % 1000000:06d}-{uuid.uuid4().hex[:4].upper()}"
    unsubscribe_token = secrets.token_urlsafe(24)
    stripe_session_id = f"cs_live_{uuid.uuid4().hex[:24]}"
    stripe_pi_id = f"pi_{uuid.uuid4().hex[:24]}"
    paygate_tx_id = f"pg_tx_{uuid.uuid4().hex[:16]}"

    resolved_db_ids: List[Tuple[Dict[str, Any], str, str]] = []
    for it in resolved_items:
        p_id, v_id = ensure_offer_in_sqlite(db, it)
        resolved_db_ids.append((it, p_id, v_id))

    now_utc = dt.datetime.now(dt.timezone.utc)
    grace_expires = (now_utc + dt.timedelta(minutes=120)).isoformat()

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO orders (
                order_id, order_number, customer_email, customer_name, customer_phone,
                shipping_address_line1, shipping_address_line2, shipping_city,
                shipping_state, shipping_zip, shipping_country,
                payment_gateway, payment_method_type,
                stripe_checkout_session_id, stripe_payment_intent_id, paygate_transaction_id,
                status, subtotal_cents, shipping_cents, discount_cents, tax_cents, total_cents,
                selected_provider, arbitrage_decision_json,
                estimated_fulfillment_cost_cents, estimated_net_margin_cents,
                grace_hold_expires_at, marketing_opt_out, unsubscribe_token
            ) VALUES (
                ?, ?, ?, ?, '',
                ?, '', ?,
                ?, ?, 'US',
                'stripe', ?,
                ?, ?, ?,
                'PAID_GRACE_HOLD', ?, ?, ?, ?, ?,
                'printify', '{}',
                ?, ?,
                ?, 0, ?
            )
            """,
            (
                order_id,
                order_number,
                email,
                recipient_name,
                line1,
                city,
                state,
                postal_code,
                payment_method,
                stripe_session_id,
                stripe_pi_id,
                paygate_tx_id,
                subtotal_cents,
                shipping_cents,
                discount_cents,
                tax_cents,
                total_cents,
                int(round(total_cents * 0.38)),
                int(round(total_cents * 0.62)),
                grace_expires,
                unsubscribe_token,
            ),
        )

        inserted_items: List[Dict[str, Any]] = []
        for it, p_id, v_id in resolved_db_ids:
            q = int(it.get("qty", 1))
            u_cents = int(round(float(it["price_usd"]) * 100))
            l_cents = u_cents * q
            conn.execute(
                """
                INSERT INTO order_items (
                    order_item_id, order_id, product_id, variant_id, master_sku, variant_sku,
                    title, quantity, unit_price_cents, line_total_cents,
                    selected_provider, provider_blank_cost_cents, provider_shipping_share_cents,
                    volume_discount_cents, line_net_margin_cents, customization_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'printify', ?, 400, 0, ?, ?)
                """,
                (
                    f"oi_{uuid.uuid4().hex[:12]}",
                    order_id,
                    p_id,
                    v_id,
                    str(it["sku"]),
                    str(it["sku"]),
                    str(it["title"]),
                    q,
                    u_cents,
                    l_cents,
                    int(round(u_cents * 0.35)),
                    int(round(l_cents * 0.60)),
                    json.dumps({"size": it.get("size", "24x36"), "frame": it.get("frame", "oak")}),
                ),
            )
            inserted_items.append({"title": it["title"], "quantity": q, "line_total_cents": l_cents})

        order_row = dict(conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone())

    return HTMLResponse(content=render_order_confirmation_page(order_row, inserted_items), status_code=200)


@checkout_recovery_router.get("/pay/confirmation/{order_id}", response_class=HTMLResponse)
async def get_order_confirmation(order_id: str) -> HTMLResponse:
    db = get_db()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ? OR order_number = ? LIMIT 1",
            (order_id, order_id),
        ).fetchone()
        if not row:
            return HTMLResponse(content=render_luxury_error_recovery_page(f"/pay/confirmation/{order_id}", 200), status_code=200)
        items = [dict(r) for r in conn.execute("SELECT * FROM order_items WHERE order_id = ?", (row["order_id"],)).fetchall()]
    return HTMLResponse(content=render_order_confirmation_page(dict(row), items), status_code=200)


@checkout_recovery_router.get("/pay/session/{session_id}", response_class=HTMLResponse)
@checkout_recovery_router.get("/pay/express/{session_id}", response_class=HTMLResponse)
@checkout_recovery_router.get("/pay/chat-checkout/{session_id}", response_class=HTMLResponse)
async def get_session_or_express_checkout(session_id: str, promo: Optional[str] = Query(default="ATELIER15")) -> HTMLResponse:
    db = get_db()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE stripe_checkout_session_id = ? OR order_id = ? LIMIT 1",
            (session_id, session_id),
        ).fetchone()
        if row:
            items = [dict(r) for r in conn.execute("SELECT * FROM order_items WHERE order_id = ?", (row["order_id"],)).fetchall()]
            return HTMLResponse(content=render_order_confirmation_page(dict(row), items), status_code=200)

    item, _ = resolve_single_offer("PD-CANVAS-24X36")
    return HTMLResponse(content=render_luxury_checkout_page([item], active_promo=promo), status_code=200)


@checkout_recovery_router.get("/recovery", response_class=HTMLResponse)
@checkout_recovery_router.get("/pay/recovery", response_class=HTMLResponse)
async def get_curatorial_recovery_desk(
    request: Request,
    reason: Optional[str] = Query(default="curatorial_recovery"),
) -> HTMLResponse:
    return HTMLResponse(
        content=render_luxury_error_recovery_page(f"/recovery?reason={reason or 'curatorial_recovery'}", status_code=200),
        status_code=200,
    )


@checkout_recovery_router.get("/pay/{offer_or_slug}", response_class=HTMLResponse)
@checkout_recovery_router.get("/claim/{offer_or_slug}", response_class=HTMLResponse)
@checkout_recovery_router.get("/products/{offer_or_slug}", response_class=HTMLResponse)
async def get_pay_offer_or_slug(
    request: Request,
    offer_or_slug: str,
    sku: Optional[str] = Query(default=None),
    qty: int = Query(default=1),
    size: Optional[str] = Query(default=None),
    frame: Optional[str] = Query(default=None),
    promo: Optional[str] = Query(default=None),
) -> Response:
    hw_slug = is_hardware_offer(offer_or_slug) or is_hardware_offer(sku)
    if hw_slug:
        accept = request.headers.get("accept", "")
        if "text/html" not in accept and "application/json" in accept:
            return JSONResponse(
                content={
                    "status": "ok",
                    "offer": hw_slug,
                    "protected_coexistence": True,
                    "price_usd": 19.00 if "maker" in hw_slug else 50.00,
                }
            )
        hw_page = Path(__file__).resolve().parent / "frontend" / "dist" / "hardware" / "index.html"
        if hw_page.exists():
            return HTMLResponse(content=hw_page.read_text(encoding="utf-8"), status_code=200)

    item, is_fb = resolve_single_offer(offer_or_slug=offer_or_slug, sku=sku, qty=qty, size=size, frame=frame)
    html_doc = render_luxury_checkout_page(
        items=[item],
        active_promo=promo,
        is_fallback=is_fb,
        requested_label=offer_or_slug,
    )
    return HTMLResponse(content=html_doc, status_code=200)


@checkout_recovery_router.get("/collections/{collection_slug}", response_class=HTMLResponse)
@checkout_recovery_router.get("/guides/{guide_slug}", response_class=HTMLResponse)
async def get_collection_or_guide_showcase(
    request: Request,
    collection_slug: Optional[str] = None,
    guide_slug: Optional[str] = None,
) -> HTMLResponse:
    slug = collection_slug or guide_slug or "curated-editions"
    item, _ = resolve_single_offer(offer_or_slug=slug)
    html_doc = render_luxury_checkout_page(items=[item], active_promo="ATELIER15")
    return HTMLResponse(content=html_doc, status_code=200)
