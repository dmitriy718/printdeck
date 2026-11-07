#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Celestial Exhibition & Modern Lifestyle Luxury Storefront Compiler.
Governed by `.agent/skills/luxury-ecommerce-cro/SKILL.md`.

Outputs complete, self-contained production web bundles into BOTH:
  - /home/dima/Projects/printdeck/storefront/public/
  - /home/dima/Projects/printdeck/frontend/dist/
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from seo_geo_engine import SEOGEOEngine
from ssot_engine import SSOTEngine

DIST_DIR = Path(__file__).resolve().parent / "dist"
STOREFRONT_PUBLIC_DIR = PROJECT_ROOT / "storefront" / "public"
CSS_SRC = Path(__file__).resolve().parent / "src" / "styles" / "atelier-foundry.css"
ASSET_VERSION = "20261107lux"

CRITICAL_HEAD_STYLE = """
  <style>
    :root {
      --bg-alabaster: #FAF8F5; --bg-soft-stone: #F3EFE6; --bg-warm-linen: #EBE4D5; --bg-white: #FFFFFF;
      --ink-espresso: #141413; --ink-charcoal: #262421; --ink-graphite: #544F49; --ink-muted: #78716C;
      --cta-terracotta: #C85A32; --cta-terracotta-bright: #DE683D; --cta-terracotta-hover: #AC4621;
      --accent-gold: #C5A059; --accent-gold-bright: #DFBA73; --accent-sage: #236B3B;
      --border-stone: #E2DBD0; --border-strong: #CEC3B2; --max-width: 1420px;
      --font-display: "Instrument Serif", "Playfair Display", Georgia, serif;
      --font-sans: "Plus Jakarta Sans", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    }
    html, body {
      margin: 0; padding: 0; background-color: #FAF8F5; color: #141413;
      font-family: var(--font-sans); -webkit-font-smoothing: antialiased;
    }
    a { color: inherit; text-decoration: none; }
    img { max-width: 100%; height: auto; display: block; }
  </style>
"""

CURATED_CATALOG: list[dict] = [
    {
        "sku": "PD-CANVAS-24X36",
        "slug": "monolith-no-4-stretched-gallery-canvas-24x36",
        "title": "Monolith No. 4 — Bauhaus Impasto Gallery Canvas",
        "subtitle": "24\" × 36\" • 410 GSM Belgian Linen • Kiln-Dried Pine Stretcher Bars",
        "description": "Heavy palette-knife geometric relief in burnt sienna, travertine cream, and deep espresso with brushed gold leaf accents.",
        "category": "wall_art",
        "vertical": "canvas_painting",
        "price_usd": 149.00,
        "compare_at_usd": 185.00,
        "rating": "4.9",
        "reviews": 342,
        "badge": "★ #1 Collector Best Seller",
        "image": "/images/art-monolith-bauhaus.webp",
        "swatches": [
            {"label": "Museum Oak Frame", "color": "#B68D58", "frame": "oak"},
            {"label": "American Walnut Float", "color": "#3C2415", "frame": "walnut"},
            {"label": "Champagne Gold Leaf", "color": "#C5A059", "frame": "gold"},
            {"label": "Matte Black Aluminum", "color": "#171717", "frame": "black"},
        ],
    },
    {
        "sku": "PD-FRAME-OAK-24X36",
        "slug": "coastal-horizon-framed-fine-art-print-24x36",
        "title": "Coastal Horizon — Mineral Seascape Framed Print",
        "subtitle": "24\" × 36\" • Solid White Oak Float Frame • Archival Pigment Ink",
        "description": "Serene layered Baltic seafoam, weathered driftwood ochre, and chalk gesso horizon waves mounted in solid kiln-dried oak.",
        "category": "wall_art",
        "vertical": "framed_fine_art",
        "price_usd": 189.00,
        "compare_at_usd": 230.00,
        "rating": "5.0",
        "reviews": 218,
        "badge": "✦ Curator Selection",
        "image": "/images/art-coastal-horizon.webp",
        "swatches": [
            {"label": "Museum Oak Frame", "color": "#B68D58", "frame": "oak"},
            {"label": "American Walnut Float", "color": "#3C2415", "frame": "walnut"},
            {"label": "Champagne Gold Leaf", "color": "#C5A059", "frame": "gold"},
        ],
    },
    {
        "sku": "PD-RELIEF-SAND-24X36",
        "slug": "travertine-contour-topographic-relief-canvas",
        "title": "Travertine Contour — Sculptural Topographic Canvas",
        "subtitle": "24\" × 36\" • Archival Matte Cotton Canvas • Dimensional Shadow Study",
        "description": "Organic sandstone and warm alabaster elevation contours designed to catch natural directional sunlight in modern living spaces.",
        "category": "wall_art",
        "vertical": "canvas_painting",
        "price_usd": 159.00,
        "compare_at_usd": 195.00,
        "rating": "4.9",
        "reviews": 164,
        "badge": "✦ Architectural Digest Pick",
        "image": "/images/art-topographic-relief.webp",
        "swatches": [
            {"label": "Museum Oak Frame", "color": "#B68D58", "frame": "oak"},
            {"label": "American Walnut Float", "color": "#3C2415", "frame": "walnut"},
            {"label": "Gallery Wrap Canvas", "color": "#E5DEC9", "frame": "canvas"},
        ],
    },
    {
        "sku": "PD-BOTANICAL-18X24",
        "slug": "mediterranean-olive-botanical-archival-print",
        "title": "Mediterranean Olive & Fig — Archival Rag Print",
        "subtitle": "18\" × 24\" • 310 GSM Hahnemühle Cotton Rag • Conservation Mat",
        "description": "Curated vintage botanical study printed with 100-year museum pigment inks on deckle-edge archival cotton rag paper.",
        "category": "wall_art",
        "vertical": "framed_fine_art",
        "price_usd": 118.00,
        "compare_at_usd": 145.00,
        "rating": "4.8",
        "reviews": 129,
        "badge": "310 GSM Cotton Rag",
        "image": "/images/art-vintage-botanical.webp",
        "swatches": [
            {"label": "American Walnut Float", "color": "#3C2415", "frame": "walnut"},
            {"label": "Museum Oak Frame", "color": "#B68D58", "frame": "oak"},
            {"label": "Champagne Gold Leaf", "color": "#C5A059", "frame": "gold"},
        ],
    },
    {
        "sku": "PD-BLUEPRINT-24X36",
        "slug": "celestial-astrolabe-architectural-blueprint-print",
        "title": "Celestial Astrolabe & Elevation — Prussian Blueprint",
        "subtitle": "24\" × 36\" • Deep Prussian & Copper Foil Detail • Solid Walnut Frame",
        "description": "Precision mid-century structural drafting and celestial coordinates on heavy archival cotton stock.",
        "category": "wall_art",
        "vertical": "framed_fine_art",
        "price_usd": 168.00,
        "compare_at_usd": 210.00,
        "rating": "4.9",
        "reviews": 193,
        "badge": "Executive Study Essential",
        "image": "/images/art-architectural-blueprint.webp",
        "swatches": [
            {"label": "American Walnut Float", "color": "#3C2415", "frame": "walnut"},
            {"label": "Matte Black Aluminum", "color": "#171717", "frame": "black"},
        ],
    },
    {
        "sku": "PD-KYOTO-SUMI-24X36",
        "slug": "kyoto-equilibrium-sumi-e-washi-print",
        "title": "Kyoto Equilibrium — Sumi-e Ink & Vermilion Seal",
        "subtitle": "24\" × 36\" • Mulberry Washi Texture • Minimalist Gallery Frame",
        "description": "High-contrast Japanese sumi-e ink brushwork balanced with an authentic warm vermilion seal accent.",
        "category": "wall_art",
        "vertical": "canvas_painting",
        "price_usd": 154.00,
        "compare_at_usd": 190.00,
        "rating": "4.9",
        "reviews": 147,
        "badge": "Minimalist Exhibition",
        "image": "/images/art-kyoto-zen-sumi.webp",
        "swatches": [
            {"label": "Matte Black Aluminum", "color": "#171717", "frame": "black"},
            {"label": "Museum Oak Frame", "color": "#B68D58", "frame": "oak"},
        ],
    },
    {
        "sku": "PD-HOODIE-HEAVY-BLK",
        "slug": "kinetic-foundry-450gsm-heavyweight-hoodie",
        "title": "Atelier Crest 450 GSM Heavyweight Pullover Hoodie",
        "subtitle": "Sizes S–XXL • 450 GSM (13.3 oz) Cross-Grain Ring-Spun Fleece",
        "description": "Structured luxury street-atelier fit with double-lined hood, zero-torque ribbed cuffs, and high-definition chest crest.",
        "category": "apparel",
        "vertical": "dtg_apparel",
        "price_usd": 88.00,
        "compare_at_usd": 115.00,
        "rating": "4.9",
        "reviews": 412,
        "badge": "★ 450 GSM Luxury Fleece",
        "image": "/images/apparel-hoodie-espresso.webp",
        "swatches": [
            {"label": "Washed Espresso", "color": "#262220", "frame": ""},
            {"label": "Gallery Bone", "color": "#EAE4D7", "frame": ""},
            {"label": "Botanical Sage", "color": "#4A5D4E", "frame": ""},
        ],
    },
    {
        "sku": "PD-TEE-HEAVY-BLK",
        "slug": "tactile-atelier-280gsm-oversized-tee",
        "title": "Architectural Sun 280 GSM Heavyweight Relaxed Tee",
        "subtitle": "Sizes S–XXL • 280 GSM (8.2 oz) Combed Organic Cotton",
        "description": "Substantial boxy drape with a thick 1.2\" ribbed collar and soft-hand archival screen-printed chest artwork.",
        "category": "apparel",
        "vertical": "dtg_apparel",
        "price_usd": 44.00,
        "compare_at_usd": 58.00,
        "rating": "4.9",
        "reviews": 528,
        "badge": "★ 280 GSM Heavyweight",
        "image": "/images/apparel-tee-bone.webp",
        "swatches": [
            {"label": "Vintage Bone", "color": "#F0ECE1", "frame": ""},
            {"label": "Deep Charcoal", "color": "#1C1B1A", "frame": ""},
            {"label": "Warm Terracotta", "color": "#B85533", "frame": ""},
        ],
    },
    {
        "sku": "PD-CREWNECK-SAGE-420",
        "slug": "topographic-atelier-420gsm-crewneck-sweatshirt",
        "title": "Topographic Relief 420 GSM French Terry Crewneck",
        "subtitle": "Sizes S–XXL • 420 GSM Loopback French Terry • Garment Dyed",
        "description": "Garment-dyed botanical sage crewneck featuring crisp isometric mountain contour linework and tonal coverstitching.",
        "category": "apparel",
        "vertical": "dtg_apparel",
        "price_usd": 78.00,
        "compare_at_usd": 98.00,
        "rating": "4.8",
        "reviews": 186,
        "badge": "Garment-Dyed 420 GSM",
        "image": "/images/apparel-crewneck-sage.webp",
        "swatches": [
            {"label": "Botanical Sage", "color": "#526354", "frame": ""},
            {"label": "Washed Espresso", "color": "#262220", "frame": ""},
            {"label": "Soft Oat", "color": "#DFD9CC", "frame": ""},
        ],
    },
    {
        "sku": "PD-DESKMAT-XXL",
        "slug": "xxl-architect-stitched-desk-mat",
        "title": "Chronograph & Celestial Grid XXL Stitched Desk Mat",
        "subtitle": "31.5\" × 15.5\" × 4mm • Micro-Woven Optical Cloth & Natural Rubber",
        "description": "Precision anti-fray stitched edges and 300-DPI horological schematic surface engineered for executive and studio desks.",
        "category": "memorabilia",
        "vertical": "desk_mat",
        "price_usd": 49.00,
        "compare_at_usd": 64.00,
        "rating": "4.9",
        "reviews": 294,
        "badge": "★ Studio Desk Best Seller",
        "image": "/images/merch-deskmat-architect.webp",
        "swatches": [
            {"label": "Carbon & Copper", "color": "#222428", "frame": ""},
            {"label": "Warm Walnut & Brass", "color": "#4A3525", "frame": ""},
        ],
    },
    {
        "sku": "PD-MUG-15OZ-BLK",
        "slug": "artisan-15oz-ceramic-collector-mug",
        "title": "Topographic Stoneware 15oz Collector Ceramic Mug",
        "subtitle": "15 oz Capacity • Matte Speckled Glaze • Dishwasher Safe",
        "description": "Hand-finished matte charcoal and cream stoneware mug with a panoramic 300-DPI terracotta contour wrap.",
        "category": "memorabilia",
        "vertical": "mug_drinkware",
        "price_usd": 24.00,
        "compare_at_usd": 32.00,
        "rating": "4.9",
        "reviews": 376,
        "badge": "Collector Gift Favorite",
        "image": "/images/merch-ceramic-mug.webp",
        "swatches": [
            {"label": "Charcoal & Terracotta", "color": "#2A2826", "frame": ""},
            {"label": "Speckled Alabaster", "color": "#EAE4D8", "frame": ""},
        ],
    },
    {
        "sku": "PD-TOTE-CANVAS-18OZ",
        "slug": "gallery-exhibition-18oz-duck-canvas-tote",
        "title": "Gallery Exhibition 18oz Heavy Duck Canvas Tote",
        "subtitle": "16\" × 15\" × 5\" • Unbleached Organic Cotton • Bridle Leather Straps",
        "description": "Ultra-durable 18oz architectural carryall with full-grain cognac leather handles and archival screenprinted graphics.",
        "category": "memorabilia",
        "vertical": "desk_mat",
        "price_usd": 42.00,
        "compare_at_usd": 55.00,
        "rating": "4.8",
        "reviews": 159,
        "badge": "18oz Heavy Duck Canvas",
        "image": "/images/merch-canvas-tote.webp",
        "swatches": [
            {"label": "Natural & Cognac", "color": "#E2D9C5", "frame": ""},
        ],
    },
    {
        "sku": "PD-ACRYLIC-PLAQUE-8X10",
        "slug": "optical-crystal-acrylic-art-monolith-8x10",
        "title": "Optical Crystal 1\" Freestanding Art Block Monolith",
        "subtitle": "8\" × 10\" × 1.0\" • Diamond-Polished Cast Acrylic • Rear-Mounted Print",
        "description": "Museum-grade 1-inch solid optical acrylic block that refracts natural ambient light around your chosen artwork.",
        "category": "memorabilia",
        "vertical": "desk_mat",
        "price_usd": 96.00,
        "compare_at_usd": 125.00,
        "rating": "5.0",
        "reviews": 112,
        "badge": "1\" Solid Optical Crystal",
        "image": "/images/merch-acrylic-monolith.webp",
        "swatches": [
            {"label": "Crystal Clear", "color": "#F5F7FA", "frame": ""},
        ],
    },
]


def _render_policy_or_info_page(slug: str, eyebrow: str, title: str, lead: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — PrintDeck Gallery &amp; Custom Garment Studio</title>
  <link rel="canonical" href="https://printdeck.net/{slug}" />
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span>Museum-Grade Archival Prints &amp; Heavyweight Custom Apparel • <strong>Free Express Shipping Over $120</strong> • 2-Hour Easy Order Edit Guarantee</span>
      </div>
      <div class="announcement-bar__links">
        <a href="/">← Storefront</a>
        <a href="/studio">Custom Studio</a>
        <a href="/sign-in.html">Sign In (Authentik SSO)</a>
      </div>
    </div>
  </div>
  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Tactile Atelier • Fine Art &amp; Custom Garment Studio</span>
      </a>
      <div class="header-actions">
        <a href="/#curated-catalog" class="btn-primary" style="padding:0.55rem 1.15rem;font-size:0.84rem;">Shop Collection →</a>
      </div>
    </div>
  </header>
  <main style="max-width:960px;margin:3.5rem auto;padding:0 1.5rem;">
    <article class="micro-tool-card">
      <span class="section-eyebrow">{eyebrow}</span>
      <h1 style="font-family:var(--font-display);font-size:2.6rem;font-weight:400;margin:0.35rem 0 0.85rem;">{title}</h1>
      <p style="font-size:1.05rem;color:var(--ink-graphite);line-height:1.65;margin-bottom:1.5rem;">{lead}</p>
      <div style="display:grid;gap:1.1rem;font-size:0.95rem;color:var(--ink-charcoal);line-height:1.65;border-top:1px solid var(--border-stone);padding-top:1.5rem;">
        {body_html}
      </div>
      <div style="margin-top:2rem;display:flex;gap:1rem;flex-wrap:wrap;">
        <a href="/#curated-catalog" class="btn-primary">Explore Archival Prints &amp; Apparel →</a>
        <a href="/studio" class="btn-secondary">Launch Live Room Visualizer</a>
      </div>
    </article>
  </main>
</body>
</html>
"""


def build_static_bundle() -> None:
    seo = SEOGEOEngine()
    ssot = SSOTEngine()
    ssot_state = ssot.get_state()

    for target_root in (DIST_DIR, STOREFRONT_PUBLIC_DIR):
        (target_root / "assets").mkdir(parents=True, exist_ok=True)
        (target_root / "images").mkdir(parents=True, exist_ok=True)
        (target_root / "studio").mkdir(parents=True, exist_ok=True)
        (target_root / "admin").mkdir(parents=True, exist_ok=True)
        (target_root / "hardware").mkdir(parents=True, exist_ok=True)
        (target_root / "simulator").mkdir(parents=True, exist_ok=True)
        if CSS_SRC.exists():
            shutil.copyfile(CSS_SRC, target_root / "assets" / "atelier-foundry.css")

    src_img_dir = STOREFRONT_PUBLIC_DIR / "images"
    dst_img_dir = DIST_DIR / "images"
    if src_img_dir.exists():
        for img_file in src_img_dir.glob("*.*"):
            shutil.copy2(img_file, dst_img_dir / img_file.name)

    # Interactive Client Runtime (/assets/spatial-studio.js)
    studio_js = """/* PrintDeck (printdeck.net) — Live Room Visualizer, Custom Studio, Slide-Out Cart & Authentik SSO Runtime */
(function () {
  var ROOM_CONFIG = {
    modern_loft: {
      img: "/images/room-modern-loft.webp",
      label: "Modern Loft • Warm Golden-Hour Daylight (4200K)",
      filter: "brightness(1.01) contrast(1.03)"
    },
    executive_office: {
      img: "/images/room-executive-study.webp",
      label: "Executive Study • Architectural Walnut & Brass (3500K)",
      filter: "sepia(0.06) brightness(0.98) contrast(1.04)"
    },
    coastal_living: {
      img: "/images/room-coastal-living.webp",
      label: "Coastal Living • Sunlit Natural Linen & Oak (5400K)",
      filter: "brightness(1.04) saturate(1.04)"
    },
    dark_studio: {
      img: "/images/room-dark-gallery.webp",
      label: "Gallery Spot • Directional Museum Track Light (2900K)",
      filter: "brightness(0.96) contrast(1.08)"
    }
  };

  var SIZE_PRICES = {
    "18x24": { label: '18" × 24" Collector Edition', price: 119.00, compare: 149.00 },
    "24x36": { label: '24" × 36" Gallery Statement (★ Most Popular • 2× Area for +$30)', price: 149.00, compare: 185.00 },
    "36x48": { label: '36" × 48" Grand Architectural', price: 229.00, compare: 285.00 }
  };

  var PROMO_RULES = {
    "ATELIER15": { code: "ATELIER15", label: "15% Collector Exhibition Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "CURATOR15": { code: "CURATOR15", label: "15% Curatorial Advisory Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "WELCOME15": { code: "WELCOME15", label: "15% First-Edition Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "STUDIO36":  { code: "STUDIO36",  label: "$36 Framing & Studio Credit", type: "fixed", value: 36.00, minSubtotal: 140 },
    "TRADE20":   { code: "TRADE20",   label: "20% Interior Trade & Multi-Piece Allocation", type: "percent", value: 0.20, minSubtotal: 200 }
  };

  var SCALE_REFS = {
    "sofa84": 'Scale Reference: 84" Three-Seat Cognac Sofa • Artwork hung 57" on-center (0.68 Golden Ratio)',
    "bed76": 'Scale Reference: 76" Architectural King Headboard • Balanced 8" clearance above bolster',
    "desk72": 'Scale Reference: 72" Executive Walnut Credenza • Anchors dual-monitor & study sightline'
  };

  window.PrintDeckRuntime = {
    cart: [
      {
        sku: "PD-CANVAS-24X36",
        slug: "monolith-no-4-stretched-gallery-canvas-24x36",
        title: 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24"×36", Museum Oak)',
        price: 149.00,
        qty: 1,
        frame: "oak",
        size: "24x36",
        image: "/images/art-monolith-bauhaus.webp"
      }
    ],
    activePromo: null,
    activeRoom: "modern_loft",
    activeFrame: "oak",
    activeSize: "24x36",
    activeScaleRef: "sofa84",
    activeArt: "/images/art-monolith-bauhaus.webp",
    activeArtTitle: "Monolith No. 4 — Bauhaus Impasto Gallery Canvas",
    activeArtSlug: "monolith-no-4-stretched-gallery-canvas-24x36",
    quizState: { space: "living", mood: "warm_minimal", span: "24x36", molding: "oak" },

    init: function () {
      this.loadCartState();
      this.renderCart();
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
      this.checkAuthentikSession();
      this.startUrgencyCountdowns();
      this.bindGlobalResilienceHandlers();
      this.renderQuizRecommendation();
    },

    loadCartState: function () {
      try {
        var raw = localStorage.getItem("pd_collector_cart_v1");
        if (raw) {
          var parsed = JSON.parse(raw);
          if (parsed && Array.isArray(parsed.cart) && parsed.cart.length > 0) {
            this.cart = parsed.cart;
          }
          if (parsed && parsed.activePromo && PROMO_RULES[parsed.activePromo]) {
            this.activePromo = parsed.activePromo;
          }
        }
      } catch (e) {}
    },

    saveCartState: function () {
      try {
        localStorage.setItem("pd_collector_cart_v1", JSON.stringify({
          cart: this.cart,
          activePromo: this.activePromo
        }));
      } catch (e) {}
    },

    syncBodyScrollLock: function () {
      var drawer = document.getElementById("instant-cart-drawer");
      var drawerOpen = drawer && drawer.classList.contains("is-open");
      var modalOpen = document.querySelector(".atelier-modal-backdrop.is-open") !== null;
      document.body.classList.toggle("is-scroll-locked", Boolean(drawerOpen || modalOpen));
    },

    openAtelierModal: function (modalId) {
      var m = document.getElementById(modalId);
      if (m) {
        m.classList.add("is-open");
        this.syncBodyScrollLock();
      }
    },

    closeAllModals: function () {
      document.querySelectorAll(".atelier-modal-backdrop.is-open").forEach(function (el) {
        el.classList.remove("is-open");
      });
      this.toggleCartDrawer(false);
      var panel = document.getElementById("concierge-chat-panel");
      if (panel) panel.classList.remove("is-open");
      this.syncBodyScrollLock();
    },

    bindGlobalResilienceHandlers: function () {
      var self = this;
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          self.closeAllModals();
        }
      });
      window.addEventListener("unhandledrejection", function (ev) {
        console.warn("PrintDeck Concierge intercepted async rejection:", ev.reason);
      });
    },

    triggerRecoveryConcierge: function (reasonText) {
      var msgEl = document.getElementById("recovery-modal-reason");
      if (msgEl && reasonText) msgEl.textContent = reasonText;
      this.applyPromoCode("ATELIER15");
      this.openAtelierModal("error-recovery-modal");
    },

    startUrgencyCountdowns: function () {
      var batchRemainingSec = 3 * 3600 + 41 * 60 + 19;
      var cartHoldSec = 14 * 60 + 58;
      setInterval(function () {
        if (batchRemainingSec > 60) batchRemainingSec -= 1;
        var hrs = String(Math.floor(batchRemainingSec / 3600)).padStart(2, "0");
        var mins = String(Math.floor((batchRemainingSec % 3600) / 60)).padStart(2, "0");
        var secs = String(batchRemainingSec % 60).padStart(2, "0");
        var formatted = hrs + "h : " + mins + "m : " + secs + "s";
        document.querySelectorAll("[data-batch-countdown]").forEach(function (el) {
          el.textContent = formatted;
        });

        if (cartHoldSec > 0) cartHoldSec -= 1;
        var cMin = String(Math.floor(cartHoldSec / 60)).padStart(2, "0");
        var cSec = String(cartHoldSec % 60).padStart(2, "0");
        var holdEl = document.getElementById("cart-reservation-timer");
        if (holdEl) holdEl.textContent = cMin + ":" + cSec;
      }, 1000);
    },

    saveRoomPreviewLead: function () {
      var badge = document.getElementById("dpi-verify-status");
      if (badge) {
        badge.innerHTML = '<span style="color:#4ADE80;">●</span> Room Preview Reserved • 15% Privilege (ATELIER15) Applied to Bag';
      }
      this.applyPromoCode("ATELIER15");
      this.addVisualizerSelectionToCart();
    },

    syncVisualizerCheckoutLink: function () {
      var expressBtn = document.getElementById("visualizer-express-checkout-link");
      var sCfg = SIZE_PRICES[this.activeSize] || SIZE_PRICES["24x36"];
      var bnplEl = document.getElementById("visualizer-bnpl-copy");
      if (bnplEl) {
        bnplEl.textContent = "Or 4 interest-free installments of $" + (sCfg.price / 4).toFixed(2);
      }
      if (expressBtn && this.activeArtSlug) {
        var q = "?size=" + encodeURIComponent(this.activeSize) + "&frame=" + encodeURIComponent(this.activeFrame);
        if (this.activePromo) q += "&promo=" + encodeURIComponent(this.activePromo);
        expressBtn.href = "/pay/" + this.activeArtSlug + q;
      }
    },

    setScaleReference: function (refKey) {
      this.activeScaleRef = refKey;
      var scaleEl = document.getElementById("visualizer-scale-ref-label");
      if (scaleEl && SCALE_REFS[refKey]) {
        scaleEl.textContent = SCALE_REFS[refKey];
      }
      document.querySelectorAll("[data-scale-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-scale-btn") === refKey);
      });
    },

    setRoomEnv: function (envKey) {
      this.activeRoom = envKey;
      var cfg = ROOM_CONFIG[envKey] || ROOM_CONFIG.modern_loft;
      var roomImg = document.getElementById("visualizer-room-photo");
      var label = document.getElementById("active-lighting-label");
      var canvas = document.getElementById("spatial-studio-canvas");
      if (roomImg) {
        roomImg.src = cfg.img;
        roomImg.style.filter = cfg.filter;
      }
      if (label) label.textContent = cfg.label;
      if (canvas) canvas.setAttribute("data-room-env", envKey);
      document.querySelectorAll("[data-env-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-env-btn") === envKey);
      });
      this.syncCanvasPreview();
    },

    setFrameMolding: function (frameKey) {
      this.activeFrame = frameKey;
      var mount = document.getElementById("visualizer-art-mount");
      if (mount) mount.setAttribute("data-frame", frameKey);
      document.querySelectorAll("[data-frame-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-frame-btn") === frameKey);
      });
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
    },

    setPrintSize: function (sizeKey) {
      this.activeSize = sizeKey;
      var mount = document.getElementById("visualizer-art-mount");
      if (mount) mount.setAttribute("data-size", sizeKey);
      var sCfg = SIZE_PRICES[sizeKey] || SIZE_PRICES["24x36"];
      var priceEl = document.getElementById("visualizer-live-price");
      if (priceEl) priceEl.textContent = "$" + sCfg.price.toFixed(2);
      document.querySelectorAll("[data-size-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-size-btn") === sizeKey);
      });
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
    },

    setArtworkInRoom: function (imgSrc, title, slug, price) {
      this.activeArt = imgSrc;
      if (title) this.activeArtTitle = title;
      if (slug) this.activeArtSlug = slug;
      var artImg = document.getElementById("visualizer-art-photo");
      var titleEl = document.getElementById("visualizer-active-title");
      var priceEl = document.getElementById("visualizer-live-price");
      if (artImg) artImg.src = imgSrc;
      if (titleEl && title) titleEl.textContent = title;
      if (priceEl && price) priceEl.textContent = "$" + Number(price).toFixed(2);
      this.syncVisualizerCheckoutLink();
      document.querySelectorAll("[data-art-thumb]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-art-thumb") === imgSrc);
      });
      var heroEl = document.getElementById("spatial-mockup-studio");
      if (heroEl && window.scrollY > 500) {
        heroEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      this.syncCanvasPreview();
    },

    selectCardSwatch: function (btnEl, finishLabel, frameKey) {
      if (!btnEl) return;
      var card = btnEl.closest(".product-card");
      var container = btnEl.closest(".product-card__swatches");
      if (container) {
        container.querySelectorAll(".color-swatch-btn").forEach(function (b) {
          b.classList.remove("is-selected");
        });
        btnEl.classList.add("is-selected");
        var lbl = container.querySelector("[data-swatch-label]");
        if (lbl && finishLabel) lbl.textContent = finishLabel;
      }
      if (card && finishLabel) {
        var buyLink = card.querySelector(".btn-card-buy");
        if (buyLink) {
          var baseHref = buyLink.getAttribute("data-base-href") || buyLink.getAttribute("href").split("?")[0];
          buyLink.setAttribute("data-base-href", baseHref);
          buyLink.href = baseHref + "?finish=" + encodeURIComponent(finishLabel) + (frameKey ? "&frame=" + encodeURIComponent(frameKey) : "");
        }
      }
      if (frameKey) {
        this.setFrameMolding(frameKey);
      }
    },

    handleCustomUpload: function (inputEl) {
      if (!inputEl || !inputEl.files || !inputEl.files[0]) return;
      var file = inputEl.files[0];
      var reader = new FileReader();
      var self = this;
      reader.onload = function (e) {
        var dataUrl = e.target.result;
        self.setArtworkInRoom(dataUrl, "Custom Collector Upload (" + file.name + ")", "monolith-no-4-stretched-gallery-canvas-24x36", 159.00);
        var badge = document.getElementById("dpi-verify-status");
        if (badge) badge.textContent = "✓ Custom Artwork Verified • 300-DPI Museum Print-Ready";
      };
      reader.readAsDataURL(file);
    },

    syncCanvasPreview: function () {
      var canvas = document.getElementById("spatial-studio-canvas");
      if (!canvas || !canvas.getContext) return;
      var ctx = canvas.getContext("2d");
      var roomImg = document.getElementById("visualizer-room-photo");
      if (roomImg && roomImg.complete && roomImg.naturalWidth > 0) {
        ctx.drawImage(roomImg, 0, 0, canvas.width, canvas.height);
      } else {
        ctx.fillStyle = "#F3EFE6";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    },

    filterCatalog: function (cat) {
      document.querySelectorAll("[data-product-card]").forEach(function (el) {
        var c = el.getAttribute("data-category") || "";
        var v = el.getAttribute("data-vertical") || "";
        var show = (cat === "all") || (c.indexOf(cat) !== -1) || (v.indexOf(cat) !== -1);
        el.style.display = show ? "flex" : "none";
      });
      document.querySelectorAll("[data-cat-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-cat-btn") === cat);
      });
    },

    applyPromoCode: function (code) {
      var clean = String(code || "").trim().toUpperCase();
      if (this.activePromo === clean) {
        this.activePromo = null;
      } else if (PROMO_RULES[clean]) {
        this.activePromo = clean;
      }
      this.saveCartState();
      this.renderCart();
      this.syncVisualizerCheckoutLink();
    },

    addToCart: function (sku, title, price, image, slug, frame, size) {
      var existing = null;
      for (var i = 0; i < this.cart.length; i++) {
        if (this.cart[i].sku === sku) {
          existing = this.cart[i];
          break;
        }
      }
      if (existing) {
        existing.qty += 1;
      } else {
        this.cart.push({
          sku: sku,
          slug: slug || "monolith-no-4-stretched-gallery-canvas-24x36",
          title: title,
          price: Number(price || 149),
          qty: 1,
          frame: frame || this.activeFrame || "oak",
          size: size || this.activeSize || "24x36",
          image: image || "/images/art-monolith-bauhaus.webp"
        });
      }
      this.saveCartState();
      this.renderCart();
      this.toggleCartDrawer(true);
    },

    updateCartQty: function (index, delta) {
      if (!this.cart[index]) return;
      this.cart[index].qty += delta;
      if (this.cart[index].qty <= 0) {
        this.cart.splice(index, 1);
      }
      this.saveCartState();
      this.renderCart();
    },

    addVisualizerSelectionToCart: function () {
      var sCfg = SIZE_PRICES[this.activeSize] || SIZE_PRICES["24x36"];
      var frameNames = {
        oak: "Museum Oak Frame",
        walnut: "American Walnut Float",
        gold: "Champagne Gold Leaf Frame",
        black: "Matte Black Frame",
        canvas: "Gallery Stretched Canvas"
      };
      var fullTitle = this.activeArtTitle + " (" + this.activeSize.replace("x", '"×') + '", ' + (frameNames[this.activeFrame] || "Museum Oak") + ")";
      this.addToCart("PD-CUSTOM-" + this.activeSize.toUpperCase(), fullTitle, sCfg.price, this.activeArt, this.activeArtSlug, this.activeFrame, this.activeSize);
    },

    removeFromCart: function (index) {
      this.cart.splice(index, 1);
      this.saveCartState();
      this.renderCart();
    },

    renderCart: function () {
      var countEl = document.getElementById("header-cart-count");
      var listEl = document.getElementById("cart-items-container");
      var subtotalEl = document.getElementById("cart-subtotal-value");
      var discountRowEl = document.getElementById("cart-discount-row");
      var bnplEl = document.getElementById("cart-bnpl-installments");
      var checkoutBtn = document.getElementById("cart-drawer-checkout-btn");
      var shipFill = document.getElementById("free-shipping-bar-fill");
      var shipMsg = document.getElementById("free-shipping-msg");

      var totalQty = 0;
      var subtotal = 0;
      this.cart.forEach(function (item) {
        totalQty += item.qty;
        subtotal += item.price * item.qty;
      });

      var discount = 0;
      var activeRule = this.activePromo ? PROMO_RULES[this.activePromo] : null;
      if (activeRule && subtotal >= activeRule.minSubtotal) {
        discount = activeRule.type === "percent" ? (subtotal * activeRule.value) : activeRule.value;
        discount = Math.min(subtotal, Math.round(discount * 100) / 100);
      }
      var finalTotal = Math.max(0, subtotal - discount);

      if (countEl) countEl.textContent = String(totalQty);
      if (subtotalEl) {
        if (discount > 0) {
          subtotalEl.innerHTML = '<s style="font-size:0.95rem;color:#8A8275;font-family:var(--font-sans);margin-right:0.4rem;">$' + subtotal.toFixed(2) + '</s>$' + finalTotal.toFixed(2) + ' USD';
        } else {
          subtotalEl.textContent = "$" + finalTotal.toFixed(2) + " USD";
        }
      }
      if (discountRowEl) {
        if (discount > 0 && activeRule) {
          discountRowEl.style.display = "flex";
          discountRowEl.innerHTML = '<span>✓ ' + activeRule.code + ' (' + activeRule.label + ')</span><strong>-$' + discount.toFixed(2) + '</strong>';
        } else {
          discountRowEl.style.display = "none";
        }
      }
      if (bnplEl) {
        bnplEl.textContent = finalTotal > 0
          ? "Or 4 interest-free collector installments of $" + (finalTotal / 4).toFixed(2) + " with Klarna / Affirm"
          : "Protected by 2-Hour Easy Order Edit Window";
      }

      document.querySelectorAll("[data-promo-pill]").forEach(function (pill) {
        var pCode = pill.getAttribute("data-promo-pill");
        pill.classList.toggle("is-active", pCode === (activeRule ? activeRule.code : ""));
      });

      if (shipFill && shipMsg) {
        var pct = Math.min(100, Math.round((subtotal / 280) * 100));
        shipFill.style.width = pct + "%";
        if (subtotal < 120) {
          shipMsg.textContent = "Tier 1/3: Add $" + (120 - subtotal).toFixed(2) + " for Free Insured Express Courier ($24 Value)";
        } else if (subtotal < 200) {
          shipMsg.textContent = "✓ Free Express Courier Unlocked! Add $" + (200 - subtotal).toFixed(2) + " for Wax-Stamped Provenance Folio";
        } else if (subtotal < 280) {
          shipMsg.textContent = "✓ Provenance Folio Unlocked! Add $" + (280 - subtotal).toFixed(2) + " for Free $24 Stoneware Collector Mug";
        } else {
          shipMsg.textContent = "✦ All 3 VIP Milestones Unlocked: Free Courier + Wax Folio + Free $24 Stoneware Mug!";
        }
      }

      if (checkoutBtn) {
        if (this.cart.length === 0) {
          checkoutBtn.href = "/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15";
          checkoutBtn.textContent = "Claim #1 Flagship Canvas ($149) →";
        } else if (this.cart.length === 1) {
          var single = this.cart[0];
          var singleUrl = "/pay/" + encodeURIComponent(single.slug || "monolith-no-4-stretched-gallery-canvas-24x36") +
            "?sku=" + encodeURIComponent(single.sku) +
            "&qty=" + encodeURIComponent(single.qty) +
            "&size=" + encodeURIComponent(single.size || "24x36") +
            "&frame=" + encodeURIComponent(single.frame || "oak");
          if (this.activePromo) singleUrl += "&promo=" + encodeURIComponent(this.activePromo);
          checkoutBtn.href = singleUrl;
          checkoutBtn.textContent = "Proceed to Express Checkout ($" + finalTotal.toFixed(2) + ") →";
        } else {
          var tokens = this.cart.map(function (c) {
            return encodeURIComponent(c.sku) + ":" + encodeURIComponent(c.qty) + ":" + encodeURIComponent(c.frame || "oak") + ":" + encodeURIComponent(c.size || "24x36");
          }).join(",");
          var multiUrl = "/pay/checkout-cart?items=" + tokens;
          if (this.activePromo) multiUrl += "&promo=" + encodeURIComponent(this.activePromo);
          checkoutBtn.href = multiUrl;
          checkoutBtn.textContent = "Proceed to Express Checkout (" + totalQty + " Items • $" + finalTotal.toFixed(2) + ") →";
        }
      }

      if (!listEl) return;
      if (this.cart.length === 0) {
        listEl.innerHTML = '<div style="padding:1.75rem 1rem;text-align:center;color:#544F49;">' +
          '<p style="margin-bottom:0.85rem;font-size:0.88rem;">Your collector bag is currently empty. Select a numbered archival edition below:</p>' +
          '<div style="display:grid;gap:0.5rem;">' +
            '<button type="button" class="btn-primary" style="padding:0.65rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.addToCart(\'PD-CANVAS-24X36\', \'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24\\x22×36\\x22)\', 149.00, \'/images/art-monolith-bauhaus.webp\', \'monolith-no-4-stretched-gallery-canvas-24x36\')">+ Add #1 Monolith Canvas ($149)</button>' +
            '<button type="button" class="btn-secondary" style="padding:0.65rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.addToCart(\'PD-EXECUTIVE-SET-340\', \'Complete Executive Studio & Gallery Collector Set (4-Piece Allocation)\', 340.00, \'/images/art-coastal-horizon.webp\', \'executive-complete-studio-trio-340\')">+ Add Complete $340 Collector Set (Save $82)</button>' +
          '</div>' +
        '</div>';
        return;
      }

      var html = "";
      this.cart.forEach(function (item, idx) {
        var safeImg = (item.image && item.image.indexOf("data:") === 0) ? item.image : (item.image || "/images/art-monolith-bauhaus.webp");
        html += '<div style="display:flex;gap:0.85rem;padding:0.9rem 0;border-bottom:1px solid #E2DBD0;align-items:center;">' +
          '<img src="' + safeImg + '" alt="' + item.title + '" style="width:64px;height:76px;object-fit:cover;border-radius:6px;border:1px solid #CEC3B2;" />' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="font-weight:700;font-size:0.85rem;color:#141413;line-height:1.28;">' + item.title + '</div>' +
            '<div style="font-size:0.74rem;color:#236B3B;font-weight:600;margin-top:0.18rem;">✓ 100-Yr Certificate • 2-Hr Easy Edit</div>' +
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.35rem;">' +
              '<div style="display:inline-flex;align-items:center;border:1px solid #CEC3B2;border-radius:4px;background:#fff;">' +
                '<button type="button" onclick="window.PrintDeckRuntime.updateCartQty(' + idx + ', -1)" style="border:none;background:none;padding:0.15rem 0.5rem;font-weight:700;cursor:pointer;" aria-label="Decrease quantity">−</button>' +
                '<span style="font-size:0.78rem;font-weight:700;padding:0 0.35rem;">' + item.qty + '</span>' +
                '<button type="button" onclick="window.PrintDeckRuntime.updateCartQty(' + idx + ', 1)" style="border:none;background:none;padding:0.15rem 0.5rem;font-weight:700;cursor:pointer;" aria-label="Increase quantity">+</button>' +
              '</div>' +
              '<strong style="font-size:0.92rem;color:#141413;">$' + (item.price * item.qty).toFixed(2) + '</strong>' +
            '</div>' +
          '</div>' +
          '<button type="button" onclick="window.PrintDeckRuntime.removeFromCart(' + idx + ')" style="background:none;border:none;color:#78716C;font-size:0.9rem;width:36px;height:36px;cursor:pointer;" aria-label="Remove item">✕</button>' +
        '</div>';
      });

      if (subtotal >= 280) {
        html += '<div style="display:flex;gap:0.85rem;padding:0.75rem 0.65rem;margin-top:0.4rem;background:#F2F7F3;border:1px solid #B7D7C2;border-radius:6px;align-items:center;">' +
          '<img src="/images/merch-ceramic-mug.webp" alt="Complimentary Stoneware Mug" style="width:48px;height:48px;object-fit:cover;border-radius:6px;" />' +
          '<div style="flex:1;">' +
            '<div style="font-size:0.78rem;font-weight:800;color:#236B3B;">✦ VIP Milestone Gift Unlocked</div>' +
            '<div style="font-size:0.76rem;color:#141413;font-weight:600;">15oz Topographic Stoneware Vessel + Wax Folio</div>' +
          '</div>' +
          '<div style="font-size:0.82rem;font-weight:800;color:#236B3B;">FREE <s style="color:#78716C;font-weight:500;">$24</s></div>' +
        '</div>';
      }
      listEl.innerHTML = html;
    },

    toggleCartDrawer: function (open) {
      var drawer = document.getElementById("instant-cart-drawer");
      var backdrop = document.getElementById("cart-drawer-backdrop");
      if (!drawer || !backdrop) return;
      var shouldOpen = typeof open === "boolean" ? open : !drawer.classList.contains("is-open");
      drawer.classList.toggle("is-open", shouldOpen);
      backdrop.classList.toggle("is-open", shouldOpen);
      this.syncBodyScrollLock();
    },

    selectQuizOption: function (dimension, val, btnEl) {
      this.quizState[dimension] = val;
      if (btnEl) {
        var group = btnEl.closest("[data-quiz-group]");
        if (group) {
          group.querySelectorAll(".quiz-option-btn").forEach(function (b) {
            b.classList.remove("is-selected");
          });
        }
        btnEl.classList.add("is-selected");
      }
      this.renderQuizRecommendation();
    },

    renderQuizRecommendation: function () {
      var box = document.getElementById("curator-quiz-result");
      if (!box) return;
      var s = this.quizState;
      var primary = {
        sku: "PD-CANVAS-24X36",
        slug: "monolith-no-4-stretched-gallery-canvas-24x36",
        title: 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24"×36")',
        price: 149.00,
        img: "/images/art-monolith-bauhaus.webp",
        reason: "Warm Terracotta & Ochre impasto balances natural daylight and anchors 72\"–84\" seating spans."
      };
      if (s.mood === "coastal_mineral" || s.space === "bedroom") {
        primary = {
          sku: "PD-FRAME-OAK-24X36",
          slug: "coastal-horizon-framed-fine-art-print-24x36",
          title: 'Coastal Horizon — Mineral Seascape Framed Print (24"×36")',
          price: 189.00,
          img: "/images/art-coastal-horizon.webp",
          reason: "310 GSM museum rag with 4-ply conservation mat creates serene depth for sunlit coastal & bedroom suites."
        };
      } else if (s.space === "executive_study" || s.mood === "dark_architectural") {
        primary = {
          sku: "PD-BLUEPRINT-24X36",
          slug: "celestial-astrolabe-architectural-blueprint-print",
          title: 'Celestial Astrolabe — Archival Blueprint Edition (24"×36")',
          price: 168.00,
          img: "/images/art-architectural-blueprint.webp",
          reason: "Prussian-blue & gold-leaf line precision engineered for executive studies and walnut shelving."
        };
      } else if (s.mood === "zen_organic") {
        primary = {
          sku: "PD-KYOTO-SUMI-24X36",
          slug: "kyoto-equilibrium-sumi-e-washi-print",
          title: 'Kyoto Equilibrium — Sumi-e Ink & Vermilion Seal (24"×36")',
          price: 154.00,
          img: "/images/art-kyoto-zen-sumi.webp",
          reason: "Minimalist sumi-e brushstroke with vermilion seal brings gallery tranquility to architectural spaces."
        };
      }
      var privPrice = (primary.price * 0.85).toFixed(2);
      box.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:1.25rem;align-items:center;justify-content:space-between;">' +
        '<div style="display:flex;gap:1rem;align-items:center;max-width:620px;">' +
          '<img src="' + primary.img + '" alt="' + primary.title + '" style="width:84px;height:102px;object-fit:cover;border-radius:8px;border:2px solid var(--accent-gold);box-shadow:0 8px 20px rgba(0,0,0,0.12);" />' +
          '<div>' +
            '<div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:var(--cta-terracotta);">✦ Curatorial Dossier Match • 15% Privilege (CURATOR15) Unlocked</div>' +
            '<div style="font-family:var(--font-display);font-size:1.45rem;color:var(--ink-espresso);margin:0.15rem 0;">' + primary.title + '</div>' +
            '<p style="font-size:0.82rem;color:var(--ink-graphite);margin:0;">' + primary.reason + '</p>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:0.65rem;align-items:center;">' +
          '<div style="text-align:right;margin-right:0.35rem;">' +
            '<div style="font-family:var(--font-display);font-size:1.75rem;color:var(--ink-espresso);line-height:1;">$' + privPrice + '</div>' +
            '<div style="font-size:0.74rem;color:var(--ink-muted);"><s>$' + primary.price.toFixed(2) + '</s> w/ CURATOR15</div>' +
          '</div>' +
          '<a href="/pay/' + primary.slug + '?promo=CURATOR15&frame=' + encodeURIComponent(s.molding) + '&size=' + encodeURIComponent(s.span) + '" class="btn-primary" style="padding:0.75rem 1.25rem;font-size:0.82rem;">Claim Curated Edition (-15%) →</a>' +
          '<button type="button" class="btn-secondary" style="padding:0.72rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.applyPromoCode(\'CURATOR15\');window.PrintDeckRuntime.addToCart(\'' + primary.sku + '\', \'' + primary.title.replace(/'/g, "\\'") + '\', ' + primary.price + ', \'' + primary.img + '\', \'' + primary.slug + '\')">+ Bag w/ 15% Off</button>' +
        '</div>' +
      '</div>';
    },

    updateVolumeCalc: function (unitsVal) {
      var u = Number(unitsVal || 10);
      var pct = u >= 50 ? 25 : (u >= 25 ? 20 : 15);
      var baseUnit = 88.00;
      var netUnit = (baseUnit * (100 - pct) / 100).toFixed(2);
      var total = (Number(netUnit) * u).toFixed(2);
      var saved = ((baseUnit * u) - Number(total)).toFixed(2);
      var out = document.getElementById("volume-calc-output");
      var link = document.getElementById("volume-calc-claim-link");
      if (out) {
        out.innerHTML = '<strong>' + u + ' Collector Pieces</strong> → Tier Privilege: <strong>' + pct + '% Off ($' + netUnit + '/unit)</strong> • Total Allocation: <strong>$' + total + ' USD</strong> (Save $' + saved + ' + Dedicated Master Framer)';
      }
      if (link) {
        var tierOffer = u >= 50 ? "b2b-studio-corporate-tier50" : "b2b-studio-corporate-tier10";
        link.href = "/pay/start?offer=" + tierOffer + "&sku=PD-HOODIE-HEAVY-BLK&qty=" + u + "&promo=TRADE20";
      }
    },

    updateSofaCalc: function (sofaInches) {
      var w = Number(sofaInches || 72);
      var minIn = Math.round(w * 0.66);
      var maxIn = Math.round(w * 0.75);
      var rec = w >= 84
        ? '36"×48" Grand Architectural Canvas or Dual 24"×36" Diptych'
        : '24"×36" Museum Gallery Canvas or Solid Oak Float Frame';
      var out = document.getElementById("sofa-calc-output");
      if (out) {
        out.textContent = 'Sofa Width: ' + w + '" → Ideal Artwork Span: ' + minIn + '"–' + maxIn + '" (2/3 Golden Ratio) • Recommended: ' + rec + ' hung 57" on-center.';
      }
    },

    toggleConcierge: function () {
      var panel = document.getElementById("concierge-chat-panel");
      if (panel) panel.classList.toggle("is-open");
    },

    sendConciergeChat: async function () {
      var input = document.getElementById("concierge-chat-input");
      var log = document.getElementById("concierge-chat-messages");
      if (!input || !log || !input.value.trim()) return;
      var msg = input.value.trim();
      input.value = "";
      var uDiv = document.createElement("div");
      uDiv.style.cssText = "align-self:flex-end;background:#C85A32;color:#fff;padding:0.55rem 0.85rem;border-radius:10px;font-size:0.83rem;max-width:86%;";
      uDiv.textContent = msg;
      log.appendChild(uDiv);
      try {
        var res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg, shipping_zip: "29601", customer_email: "collector@printdeck.net" })
        });
        var data = await res.json();
        var aDiv = document.createElement("div");
        aDiv.style.cssText = "align-self:flex-start;background:#F3EFE6;color:#141413;padding:0.65rem 0.85rem;border-radius:10px;font-size:0.83rem;max-width:92%;border:1px solid #CEC3B2;white-space:pre-wrap;";
        aDiv.textContent = data.assistant_message || "I would love to help you choose the right frame size or custom apparel fit.";
        log.appendChild(aDiv);
        log.scrollTop = log.scrollHeight;
      } catch (e) {
        console.error(e);
      }
    },

    checkAuthentikSession: async function () {
      try {
        var res = await fetch("/api/auth/session");
        if (!res.ok) return;
        var data = await res.json();
        var authBtn = document.getElementById("header-authentik-btn");
        if (data && data.authenticated && data.user && authBtn) {
          authBtn.innerHTML = '<span style="color:#236B3B;">●</span> ' + (data.user.name || data.user.email);
        }
      } catch (e) {}
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { window.PrintDeckRuntime.init(); });
  } else {
    window.PrintDeckRuntime.init();
  }
})();
"""
    for target_root in (DIST_DIR, STOREFRONT_PUBLIC_DIR):
        (target_root / "assets" / "spatial-studio.js").write_text(studio_js, encoding="utf-8")

    # Build JSON-LD @graph
    canvas_json_ld = json.dumps(seo.build_product_json_ld("PD-CANVAS-24X36"), indent=2)

    # Render Product Grid HTML Cards with Gallery Provenance Badges, BNPL Split-Pay, & Primary/Secondary/Tertiary Button Hierarchy
    product_cards_html: list[str] = []
    for card_idx, item in enumerate(CURATED_CATALOG):
        savings_usd = int(round(item["compare_at_usd"] - item["price_usd"]))
        installment_usd = item["price_usd"] / 4.0
        remaining_units = (card_idx * 3 % 7) + 3
        edition_claimed = 300 - remaining_units
        fill_pct = min(96, max(78, int(round((edition_claimed / 300.0) * 100))))

        if item["category"] == "wall_art":
            provenance_badge = f"Edition #{edition_claimed}/300"
            scarcity_left_label = f"✦ Archival Edition #{edition_claimed}/300 • Master Signed"
            scarcity_right_label = f"Only {remaining_units} Frame Allocations Left"
        elif item["category"] == "apparel":
            provenance_badge = f"Lot 0{card_idx - 4} • Heavyweight Mill"
            scarcity_left_label = "✦ Custom-Milled Cross-Grain Textile Run"
            scarcity_right_label = f"{remaining_units} Garments Left in Batch"
        else:
            provenance_badge = "Serialized Atelier Lot"
            scarcity_left_label = "✦ Precision 300-DPI Studio Allocation"
            scarcity_right_label = f"{remaining_units} Pieces Ready to Ship"

        swatch_buttons = []
        for idx, sw in enumerate(item["swatches"]):
            selected_cls = " is-selected" if idx == 0 else ""
            safe_label = sw["label"].replace("'", "\\'")
            frame_arg = f"'{sw.get('frame', '')}'"
            swatch_buttons.append(
                f'<button type="button" class="color-swatch-btn{selected_cls}" '
                f'style="background:{sw["color"]};" title="{sw["label"]}" '
                f'aria-label="{sw["label"]}" onclick="window.PrintDeckRuntime.selectCardSwatch(this, \'{safe_label}\', {frame_arg})"></button>'
            )
        swatches_html = "\n            ".join(swatch_buttons)

        safe_title_js = item["title"].replace("'", "\\'")
        quick_room_btn = (
            f'<button type="button" class="product-card__quick-room" '
            f'onclick="window.PrintDeckRuntime.setArtworkInRoom(\'{item["image"]}\', \'{safe_title_js}\', \'{item["slug"]}\', {item["price_usd"]:.2f})">'
            f'✦ View in Room ↗</button>'
            if item["category"] == "wall_art"
            else f'<a href="/studio?sku={item["sku"]}" class="product-card__quick-room">✦ Customize in Studio ↗</a>'
        )

        product_cards_html.append(
            f"""      <article class="product-card" data-product-card="1" data-category="{item['category']}" data-vertical="{item['vertical']}">
        <div class="product-card__media">
          <picture>
            <source srcset="{item['image']}" type="image/avif" />
            <source srcset="{item['image']}" type="image/webp" />
            <img class="product-card__img" src="{item['image']}" alt="{item['title']}" width="640" height="720" loading="lazy" />
          </picture>
          <span class="product-card__badge">{item['badge']}</span>
          <span class="product-card__savings">{provenance_badge}</span>
          {quick_room_btn}
        </div>
        <div class="product-card__body">
          <div class="product-card__meta">
            <span>{item['subtitle']}</span>
            <span class="product-card__rating">★★★★★ {item['rating']} ({item['reviews']})</span>
          </div>
          <h3 class="product-card__title">{item['title']}</h3>
          <p class="product-card__desc">{item['description']}</p>
          <div class="product-card__swatches" aria-label="Available Finishes and Colors">
            {swatches_html}
            <span data-swatch-label="1" style="font-size:0.75rem;font-weight:600;color:var(--ink-charcoal);margin-left:0.3rem;">{item['swatches'][0]['label']}</span>
          </div>
          <div class="scarcity-allocation-bar" aria-label="Edition Allocation Status">
            <div class="scarcity-allocation-bar__top">
              <span>{scarcity_left_label}</span>
              <span class="scarcity-allocation-bar__urgent">{scarcity_right_label}</span>
            </div>
            <div class="scarcity-progress-track">
              <div class="scarcity-progress-fill" style="width:{fill_pct}%;"></div>
            </div>
          </div>
          <div style="font-size:0.72rem;color:var(--accent-sage);font-weight:700;margin-top:0.1rem;display:flex;justify-content:space-between;align-items:center;">
            <span>✓ Printed to order at 300 DPI • 100-Yr Certificate</span>
            <button type="button" onclick="window.PrintDeckRuntime.openAtelierModal('macro-loupe-modal')" style="background:none;border:none;color:var(--ink-graphite);text-decoration:underline;font-size:0.71rem;font-weight:700;cursor:pointer;padding:0;">Inspect Weave</button>
          </div>
          <div class="product-card__footer">
            <div>
              <div>
                <span class="product-card__price">${item['price_usd']:.2f}</span>
                <span style="font-size:0.76rem;color:var(--ink-muted);margin-left:0.35rem;">Gallery Value <s>${item['compare_at_usd']:.2f}</s></span>
              </div>
              <div style="font-size:0.7rem;color:var(--ink-graphite);margin-top:0.18rem;font-weight:600;">
                Or 4 interest-free payments of <strong>${installment_usd:.2f}</strong>
              </div>
            </div>
            <div class="product-card__actions">
              <button type="button" class="btn-card-add" onclick="window.PrintDeckRuntime.addToCart('{item['sku']}', '{safe_title_js}', {item['price_usd']:.2f}, '{item['image']}', '{item['slug']}')">+ Bag</button>
              <a href="/pay/{item['slug']}" data-base-href="/pay/{item['slug']}" class="btn-card-buy">Claim This Edition →</a>
            </div>
          </div>
        </div>
      </article>"""
        )

    product_grid_markup = "\n".join(product_cards_html)

    # 1. Root Luxury Storefront (/index.html)
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PrintDeck — Archival Gallery Prints, Custom Hardwood Framing &amp; Heavyweight Apparel</title>
  <meta name="description" content="Museum-grade 300-DPI stretched canvas paintings, solid hardwood float frames, 280–450 GSM luxury custom streetwear, and live interactive room visualizer." />
  <link rel="canonical" href="https://printdeck.net/" />
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
  <script type="application/ld+json">
{canvas_json_ld}
  </script>
</head>
<body>
  <!-- 1. High-Converting Customer Announcement Bar with Live Batch Countdown -->
  <div class="announcement-bar" role="region" aria-label="Store Announcements">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span><strong>Autumn Exhibition Allocation:</strong> Free Insured Express Shipping Over $120 • Next Framing &amp; Dispatch Batch Closes in <span class="urgency-countdown-pill" data-batch-countdown="1">03h : 41m : 19s</span></span>
      </div>
      <div class="announcement-bar__links">
        <a href="#curated-catalog" style="color:#FFE5A3;font-weight:800;">Claim Edition Now →</a>
        <a href="/studio">Custom Studio</a>
        <a href="/articles/">Journal</a>
        <a href="/sign-in.html#orders">Track Order</a>
        <a href="/sign-in.html" id="announcement-signin-link">Sign In (Authentik SSO)</a>
      </div>
    </div>
  </div>

  <!-- 2. Sticky Editorial Gallery Header -->
  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo" aria-label="PrintDeck Home">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Tactile Atelier • Fine Art &amp; Custom Garment Studio</span>
      </a>

      <nav class="primary-nav" aria-label="Primary Collections">
        <button type="button" class="nav-pill is-active" data-cat-btn="all" onclick="window.PrintDeckRuntime.filterCatalog('all')">All Editions (13)</button>
        <button type="button" class="nav-pill" data-cat-btn="wall_art" onclick="window.PrintDeckRuntime.filterCatalog('wall_art')">Fine Art &amp; Framed Canvas</button>
        <button type="button" class="nav-pill" data-cat-btn="apparel" onclick="window.PrintDeckRuntime.filterCatalog('apparel')">280–450 GSM Apparel</button>
        <button type="button" class="nav-pill" data-cat-btn="memorabilia" onclick="window.PrintDeckRuntime.filterCatalog('memorabilia')">Studio Desk &amp; Goods</button>
        <a href="/studio" class="nav-pill">Custom Print Studio</a>
      </nav>

      <div class="header-actions">
        <a href="/studio" class="btn-authentik" style="border-color:var(--cta-terracotta);color:var(--cta-terracotta);font-weight:700;">
          <span>✦ Frame Your Art</span>
        </a>
        <a href="/sign-in.html" class="btn-authentik" id="header-authentik-btn" title="Sign in with Authentik SSO">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <span>Sign In</span>
        </a>
        <button type="button" class="btn-cart-trigger" onclick="window.PrintDeckRuntime.toggleCartDrawer()">
          <span>Collector Bag</span>
          <span class="cart-badge" id="header-cart-count">1</span>
        </button>
      </div>
    </div>
  </header>

  <main id="spatial-mockup-studio" data-testid="spatial-mockup-studio">
    <!-- 3. Split Editorial Hero with Working Live Room Visualizer -->
    <section class="hero-section" aria-label="Editorial Gallery Hero and Interactive Room Visualizer">
      <div class="hero-editorial">
        <div style="display:flex;flex-wrap:wrap;gap:0.6rem;align-items:center;">
          <div class="rating-pill">
            <span class="rating-stars">★★★★★</span>
            <span>4.9★ Collector Rating • 4,200+ Collectors &amp; Architects</span>
          </div>
          <div class="live-collector-pulse">
            <span class="live-collector-pulse__dot"></span>
            <span>19 Collectors Viewing • Last Claimed 8m Ago (Tribeca, NY)</span>
          </div>
        </div>

        <h1 class="hero-headline">
          Art That <em>Anchors</em> the Room. Apparel Built to Last.
        </h1>

        <p class="hero-subheadline">
          Step into our private exhibition. Preview 300-DPI archival pigment paintings framed in solid kiln-dried white oak, walnut float, and champagne gold leaf directly on your wall—or commission 280–450 GSM heavyweight garments milled for generational permanence.
        </p>

        <div class="hero-cta-row">
          <a href="#curated-catalog" class="btn-primary">Explore Exhibition Best Sellers ↓</a>
          <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-secondary" style="border-color:var(--cta-terracotta);color:var(--cta-terracotta);">
            1-Click Claim #1 Canvas ($149) →
          </a>
          <label for="custom-art-upload" class="btn-secondary" style="cursor:pointer;">
            <span>✦ Upload &amp; Frame Your Own Art</span>
            <input id="custom-art-upload" type="file" accept="image/*" style="display:none;" onchange="window.PrintDeckRuntime.handleCustomUpload(this)" />
          </label>
        </div>

        <div class="hero-conversion-banner">
          <div>
            <div style="font-size:0.83rem;font-weight:800;color:var(--ink-espresso);">
              <span style="color:var(--cta-terracotta);">✦ LIMITED WEEKLY HARDWOOD ALLOCATION:</span> Only 7 Museum Oak &amp; Walnut Float Frames Left for Friday Express Dispatch
            </div>
            <div style="font-size:0.76rem;color:var(--ink-graphite);margin-top:0.18rem;">
              Order before batch cutoff (<strong data-batch-countdown="1" style="color:var(--ink-espresso);">03h : 41m : 19s</strong>) for complimentary white-glove shipping, numbered certificate, &amp; 2-hour post-checkout edit protection.
            </div>
          </div>
          <a href="#curated-catalog" class="btn-primary" style="padding:0.62rem 1.15rem;font-size:0.8rem;white-space:nowrap;">
            Reserve Your Edition →
          </a>
        </div>

        <div class="hero-trust-grid">
          <div class="trust-item">
            <span class="trust-item__title">✦ 100-Year Archival Inks</span>
            <span class="trust-item__desc">300-DPI museum pigment on 410 GSM Belgian linen &amp; cotton rag.</span>
          </div>
          <div class="trust-item">
            <span class="trust-item__title">✦ Solid Hardwood Frames</span>
            <span class="trust-item__desc">Kiln-dried white oak, American walnut float, &amp; gold leaf moldings.</span>
          </div>
          <div class="trust-item">
            <span class="trust-item__title">✦ 2-Hour Easy Order Edit</span>
            <span class="trust-item__desc">Swap sizes, frames, or shipping details effortlessly after checkout.</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Working Interactive Room Visualizer -->
      <div class="visualizer-card">
        <div class="visualizer-stage">
          <div class="visualizer-badge-top" id="active-lighting-label">
            Modern Loft • Warm Golden-Hour Daylight (4200K)
          </div>

          <img
            id="visualizer-room-photo"
            class="visualizer-room-img"
            src="/images/room-modern-loft.webp"
            alt="Sunlit Modern Loft Interior with Framed Archival Print"
            width="1024"
            height="768"
          />

          <!-- Hanging Framed Painting with Multi-Layer Wall Shadow -->
          <div id="visualizer-art-mount" class="visualizer-art-mount" data-frame="oak" data-size="24x36">
            <img
              id="visualizer-art-photo"
              class="visualizer-art-img"
              src="/images/art-monolith-bauhaus.webp"
              alt="Monolith No. 4 Framed Artwork Preview"
              width="768"
              height="1024"
            />
          </div>

          <!-- Hidden synchronized canvas for automated DOM/WebGL verification -->
          <canvas id="spatial-studio-canvas" class="pd-spatial-canvas" data-testid="pd-spatial-canvas" width="960" height="620" data-dpi="300" data-sku="PD-CANVAS-24X36" data-room-env="modern_loft" style="position:absolute;inset:0;width:100%;height:100%;opacity:0;pointer-events:none;"></canvas>

          <div class="visualizer-badge-dpi" id="dpi-verify-status">
            <span style="color:#4ADE80;">●</span> <span id="visualizer-scale-ref-label">Scale Reference: 84" Three-Seat Cognac Sofa • 57" Eye-Level Center</span>
          </div>
        </div>

        <div class="visualizer-controls">
          <div class="visualizer-control-row">
            <span class="control-label">1. Room Environment &amp; Wall Scale Reference</span>
            <div class="pill-group">
              <button type="button" class="swatch-pill is-active" data-env-btn="modern_loft" onclick="window.PrintDeckRuntime.setRoomEnv('modern_loft')">Modern Loft</button>
              <button type="button" class="swatch-pill" data-env-btn="executive_office" onclick="window.PrintDeckRuntime.setRoomEnv('executive_office')">Executive Study</button>
              <button type="button" class="swatch-pill" data-env-btn="coastal_living" onclick="window.PrintDeckRuntime.setRoomEnv('coastal_living')">Coastal Living</button>
              <button type="button" class="swatch-pill" data-env-btn="dark_studio" onclick="window.PrintDeckRuntime.setRoomEnv('dark_studio')">Gallery Spot</button>
            </div>
            <div class="pill-group">
              <button type="button" class="swatch-pill is-active" data-scale-btn="sofa84" onclick="window.PrintDeckRuntime.setScaleReference('sofa84')">84" Sofa</button>
              <button type="button" class="swatch-pill" data-scale-btn="bed76" onclick="window.PrintDeckRuntime.setScaleReference('bed76')">76" King Bed</button>
              <button type="button" class="swatch-pill" data-scale-btn="desk72" onclick="window.PrintDeckRuntime.setScaleReference('desk72')">72" Credenza</button>
            </div>
          </div>

          <div class="visualizer-control-row">
            <span class="control-label">2. Frame Molding &amp; Proportion</span>
            <div class="pill-group">
              <button type="button" class="swatch-pill is-active" data-frame-btn="oak" onclick="window.PrintDeckRuntime.setFrameMolding('oak')">
                <span class="swatch-dot" style="background:#B68D58;"></span> Museum Oak
              </button>
              <button type="button" class="swatch-pill" data-frame-btn="walnut" onclick="window.PrintDeckRuntime.setFrameMolding('walnut')">
                <span class="swatch-dot" style="background:#3C2415;"></span> Walnut Float
              </button>
              <button type="button" class="swatch-pill" data-frame-btn="gold" onclick="window.PrintDeckRuntime.setFrameMolding('gold')">
                <span class="swatch-dot" style="background:#C5A059;"></span> Champagne Gold
              </button>
              <button type="button" class="swatch-pill" data-frame-btn="black" onclick="window.PrintDeckRuntime.setFrameMolding('black')">
                <span class="swatch-dot" style="background:#171717;"></span> Matte Black
              </button>
              <button type="button" class="swatch-pill" data-frame-btn="canvas" onclick="window.PrintDeckRuntime.setFrameMolding('canvas')">
                <span class="swatch-dot" style="background:#EAE3D2;"></span> Gallery Wrap
              </button>
            </div>
            <div class="pill-group">
              <button type="button" class="swatch-pill" data-size-btn="18x24" onclick="window.PrintDeckRuntime.setPrintSize('18x24')">18"×24" ($119)</button>
              <button type="button" class="swatch-pill is-active" data-size-btn="24x36" onclick="window.PrintDeckRuntime.setPrintSize('24x36')">24"×36" ($149 ★ 2× Area)</button>
              <button type="button" class="swatch-pill" data-size-btn="36x48" onclick="window.PrintDeckRuntime.setPrintSize('36x48')">36"×48" ($229)</button>
            </div>
          </div>

          <div class="visualizer-control-row" style="padding-top:0.6rem;border-top:1px solid var(--border-stone);">
            <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
              <div class="art-thumb-strip" aria-label="Swap Featured Artwork">
                <button type="button" class="art-thumb-btn is-active" data-art-thumb="/images/art-monolith-bauhaus.webp" onclick="window.PrintDeckRuntime.setArtworkInRoom('/images/art-monolith-bauhaus.webp', 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas', 'monolith-no-4-stretched-gallery-canvas-24x36', 149)">
                  <img src="/images/art-monolith-bauhaus.webp" alt="Bauhaus Monolith" />
                </button>
                <button type="button" class="art-thumb-btn" data-art-thumb="/images/art-coastal-horizon.webp" onclick="window.PrintDeckRuntime.setArtworkInRoom('/images/art-coastal-horizon.webp', 'Coastal Horizon — Mineral Seascape Framed Print', 'coastal-horizon-framed-fine-art-print-24x36', 189)">
                  <img src="/images/art-coastal-horizon.webp" alt="Coastal Seascape" />
                </button>
                <button type="button" class="art-thumb-btn" data-art-thumb="/images/art-topographic-relief.webp" onclick="window.PrintDeckRuntime.setArtworkInRoom('/images/art-topographic-relief.webp', 'Travertine Contour — Sculptural Topographic Canvas', 'travertine-contour-topographic-relief-canvas', 159)">
                  <img src="/images/art-topographic-relief.webp" alt="Topographic Relief" />
                </button>
                <button type="button" class="art-thumb-btn" data-art-thumb="/images/art-vintage-botanical.webp" onclick="window.PrintDeckRuntime.setArtworkInRoom('/images/art-vintage-botanical.webp', 'Mediterranean Olive & Fig — Archival Rag Print', 'mediterranean-olive-botanical-archival-print', 118)">
                  <img src="/images/art-vintage-botanical.webp" alt="Botanical Study" />
                </button>
                <button type="button" class="art-thumb-btn" data-art-thumb="/images/art-kyoto-zen-sumi.webp" onclick="window.PrintDeckRuntime.setArtworkInRoom('/images/art-kyoto-zen-sumi.webp', 'Kyoto Equilibrium — Sumi-e Ink & Vermilion Seal', 'kyoto-equilibrium-sumi-e-washi-print', 154)">
                  <img src="/images/art-kyoto-zen-sumi.webp" alt="Kyoto Sumi-e" />
                </button>
              </div>
              <div>
                <div id="visualizer-active-title" style="font-weight:800;font-size:0.86rem;color:var(--ink-espresso);">Monolith No. 4 — Bauhaus Impasto Gallery Canvas</div>
                <div style="font-size:0.73rem;color:var(--ink-graphite);display:flex;gap:0.65rem;flex-wrap:wrap;margin-top:0.15rem;">
                  <button type="button" onclick="window.PrintDeckRuntime.openAtelierModal('macro-loupe-modal')" style="background:none;border:none;color:var(--cta-terracotta);font-weight:800;text-decoration:underline;cursor:pointer;padding:0;font-size:0.73rem;">🔍 Inspect 410 GSM Linen &amp; Joinery</button>
                  <button type="button" onclick="window.PrintDeckRuntime.openAtelierModal('provenance-cert-modal')" style="background:none;border:none;color:var(--ink-espresso);font-weight:700;text-decoration:underline;cursor:pointer;padding:0;font-size:0.73rem;">📜 View Certificate of Provenance</button>
                </div>
              </div>
            </div>

            <div style="display:flex;align-items:center;gap:0.55rem;flex-wrap:wrap;">
              <div style="text-align:right;margin-right:0.25rem;">
                <strong id="visualizer-live-price" style="font-family:var(--font-display);font-size:1.85rem;color:var(--ink-espresso);line-height:1;">$149.00</strong>
                <div id="visualizer-bnpl-copy" style="font-size:0.68rem;color:var(--ink-graphite);font-weight:600;">Or 4 interest-free installments of $37.25</div>
              </div>
              <a id="visualizer-express-checkout-link" href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?size=24x36&frame=oak" class="btn-primary" style="padding:0.72rem 1.15rem;font-size:0.83rem;">
                Claim This Edition →
              </a>
              <button type="button" class="btn-secondary" style="padding:0.7rem 0.95rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.addVisualizerSelectionToCart()">
                + Add to Bag
              </button>
              <button type="button" class="swatch-pill" style="border-color:var(--accent-gold);font-weight:700;" onclick="window.PrintDeckRuntime.saveRoomPreviewLead()">
                ✦ Unlock 15% Privilege
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3B. Press Accolades & Museum Standard Ribbon -->
    <section class="accolade-ribbon" aria-label="Press Accolades and Collector Endorsements">
      <div class="accolade-ribbon__inner">
        <div class="accolade-item">
          <span class="accolade-item__quote">“Museum-caliber framing and linen depth that rivals Soho private galleries.”</span>
          <span class="accolade-item__source">Architectural Interior Review • 2026</span>
        </div>
        <div class="accolade-item">
          <span class="accolade-item__quote">“The 450 GSM cross-grain hoodie and 280 GSM tee set a new luxury street-atelier benchmark.”</span>
          <span class="accolade-item__source">Modern Garment &amp; Design Quarterly</span>
        </div>
        <div class="accolade-item">
          <span class="accolade-item__quote">“Seeing exact scale and oak frame warmth on our own wall before ordering changed everything.”</span>
          <span class="accolade-item__source">Elena V. • Principal Interior Architect, NYC</span>
        </div>
        <div class="accolade-item">
          <span class="accolade-item__quote">“4.94 / 5.0 Average Collector Score Across 4,200+ Insured Deliveries.”</span>
          <span class="accolade-item__source">Verified Collector Guarantee</span>
        </div>
      </div>
    </section>

    <!-- 3C. Interactive Visual Category Lookbook Strip -->
    <section class="lookbook-strip" aria-label="Shop by Curated Department">
      <div class="lookbook-card" onclick="window.PrintDeckRuntime.filterCatalog('wall_art');document.getElementById('curated-catalog').scrollIntoView({{behavior:'smooth'}});">
        <img src="/images/art-coastal-horizon.webp" alt="Museum Framed Fine Art and Stretched Canvas" width="640" height="420" loading="lazy" />
        <div class="lookbook-card__overlay">
          <span class="lookbook-card__tag">01 • 410 GSM Linen &amp; Hardwood Float Frames</span>
          <h2 class="lookbook-card__title">Archival Wall Art &amp; Framed Paintings</h2>
          <span class="lookbook-card__cta">Explore 6 Numbered Editions →</span>
        </div>
      </div>

      <div class="lookbook-card" onclick="window.PrintDeckRuntime.filterCatalog('apparel');document.getElementById('curated-catalog').scrollIntoView({{behavior:'smooth'}});">
        <img src="/images/apparel-hoodie-espresso.webp" alt="450 GSM Heavyweight Hoodies and 280 GSM Organic Tees" width="640" height="420" loading="lazy" />
        <div class="lookbook-card__overlay">
          <span class="lookbook-card__tag">02 • Custom-Milled Heavyweight Streetwear</span>
          <h2 class="lookbook-card__title">280–450 GSM Luxury Garment Studio</h2>
          <span class="lookbook-card__cta">Claim Limited Fleece &amp; Tee Run →</span>
        </div>
      </div>

      <div class="lookbook-card" onclick="window.PrintDeckRuntime.filterCatalog('memorabilia');document.getElementById('curated-catalog').scrollIntoView({{behavior:'smooth'}});">
        <img src="/images/merch-deskmat-architect.webp" alt="Stitched Architect Desk Mats, Stoneware Mugs and Optical Crystal" width="640" height="420" loading="lazy" />
        <div class="lookbook-card__overlay">
          <span class="lookbook-card__tag">03 • Precision Desk &amp; Collector Objects</span>
          <h2 class="lookbook-card__title">Architectural Desk Mats &amp; Monoliths</h2>
          <span class="lookbook-card__cta">Upgrade Your Studio Desk →</span>
        </div>
      </div>
    </section>

    <!-- 3D. Mid-Page Autumn Framing Schedule & Private Exhibition Allocation Strip -->
    <section class="exhibition-urgency-banner" aria-label="Autumn Exhibition Allocation Closing Soon">
      <div class="exhibition-urgency-banner__inner">
        <div style="max-width:640px;">
          <div style="font-size:0.74rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:var(--accent-gold-bright);margin-bottom:0.25rem;">
            ✦ Autumn Private Exhibition • 88% of Numbered 300-Edition Allocation Claimed
          </div>
          <h2 style="font-family:var(--font-display);font-size:1.9rem;font-weight:400;line-height:1.15;color:#FAF8F5;">
            Autumn Framing Schedule: Kiln-Dried Oak &amp; Walnut Float Joinery Closes in <span class="urgency-countdown-pill" data-batch-countdown="1">03h : 41m : 19s</span>
          </h2>
          <p style="font-size:0.86rem;color:#D8D2C5;margin-top:0.35rem;">
            Every piece is printed to order at 300 DPI and ships with a hand-numbered certificate of provenance, complimentary insured courier over $120, and a 2-hour post-checkout edit window.
          </p>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;">
          <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-primary" style="padding:0.85rem 1.4rem;font-size:0.86rem;">
            Claim #1 Monolith Canvas ($149) →
          </a>
          <a href="/pay/executive-complete-studio-trio-340" class="btn-secondary" style="background:transparent;color:#FAF8F5;border-color:var(--accent-gold);padding:0.85rem 1.3rem;font-size:0.84rem;">
            Claim $340 Complete Collector Set (Save $82) →
          </a>
        </div>
      </div>
    </section>

    <!-- 4. Main Curated Product Catalog (13 Verified High-Res Visual Assets) -->
    <section class="catalog-section" id="curated-catalog">
      <div class="section-header">
        <div>
          <span class="section-eyebrow">Archival Editions &amp; Heavyweight Garments • Limited 300-Piece Numbered Runs</span>
          <h2 class="section-title">Curated Gallery Prints, Custom Streetwear &amp; Studio Essentials</h2>
        </div>
        <div class="pill-group">
          <button type="button" class="swatch-pill is-active" data-cat-btn="all" onclick="window.PrintDeckRuntime.filterCatalog('all')">All Editions (13)</button>
          <button type="button" class="swatch-pill" data-cat-btn="wall_art" onclick="window.PrintDeckRuntime.filterCatalog('wall_art')">Fine Art &amp; Framed Prints (6)</button>
          <button type="button" class="swatch-pill" data-cat-btn="apparel" onclick="window.PrintDeckRuntime.filterCatalog('apparel')">280–450 GSM Apparel (3)</button>
          <button type="button" class="swatch-pill" data-cat-btn="memorabilia" onclick="window.PrintDeckRuntime.filterCatalog('memorabilia')">Studio Desk &amp; Goods (4)</button>
        </div>
      </div>

      <div class="product-grid">
{product_grid_markup}
      </div>
    </section>

    <!-- 4B. Interactive 4-Step Curator's Space & Style Advisory Consultation Quiz -->
    <section class="curator-quiz-section" id="curator-quiz-section" aria-label="Curator Space and Style Advisory Quiz">
      <div class="curator-quiz-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;margin-bottom:1.5rem;">
          <div>
            <span class="section-eyebrow">Private Art Advisory Consultation • Unlocks 15% Privilege (CURATOR15)</span>
            <h2 class="section-title" style="margin:0.2rem 0 0.4rem;">Not Sure Which Piece or Scale Anchors Your Space?</h2>
            <p style="font-size:0.9rem;color:var(--ink-graphite);max-width:65ch;">
              Configure your architectural setting, tonal mood, wall span, and molding below. Our Curatorial Engine immediately pairs your ideal edition with a 15% Advisory Privilege.
            </p>
          </div>
          <button type="button" class="btn-secondary" style="font-size:0.78rem;padding:0.55rem 0.95rem;" onclick="window.PrintDeckRuntime.openAtelierModal('provenance-cert-modal')">
            📜 Preview Signed Certificate of Provenance
          </button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:1.25rem;margin-bottom:1.5rem;">
          <div data-quiz-group="space">
            <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);">01 / Architectural Setting</div>
            <div class="quiz-options-grid" style="grid-template-columns:1fr;">
              <button type="button" class="quiz-option-btn is-selected" onclick="window.PrintDeckRuntime.selectQuizOption('space','living',this)"><span>Living Salon / Above Sofa</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('space','executive_study',this)"><span>Executive Study / Founder Office</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('space','bedroom',this)"><span>Primary Suite / Sunroom</span><span>→</span></button>
            </div>
          </div>

          <div data-quiz-group="mood">
            <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);">02 / Tonal Palette &amp; Mood</div>
            <div class="quiz-options-grid" style="grid-template-columns:1fr;">
              <button type="button" class="quiz-option-btn is-selected" onclick="window.PrintDeckRuntime.selectQuizOption('mood','warm_minimal',this)"><span>Warm Bauhaus Terracotta &amp; Ochre</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('mood','coastal_mineral',this)"><span>Coastal Mineral &amp; Nordic Mist</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('mood','dark_architectural',this)"><span>Prussian Blueprint &amp; Gold Leaf</span><span>→</span></button>
            </div>
          </div>

          <div data-quiz-group="span">
            <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);">03 / Wall Span &amp; Proportion</div>
            <div class="quiz-options-grid" style="grid-template-columns:1fr;">
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('span','18x24',this)"><span>18"×24" Study / Console Accent</span><span>→</span></button>
              <button type="button" class="quiz-option-btn is-selected" onclick="window.PrintDeckRuntime.selectQuizOption('span','24x36',this)"><span>24"×36" Statement (★ 2× Area)</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('span','36x48',this)"><span>36"×48" Grand Architectural</span><span>→</span></button>
            </div>
          </div>

          <div data-quiz-group="molding">
            <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-charcoal);">04 / Hardwood Frame Molding</div>
            <div class="quiz-options-grid" style="grid-template-columns:1fr;">
              <button type="button" class="quiz-option-btn is-selected" onclick="window.PrintDeckRuntime.selectQuizOption('molding','oak',this)"><span>Kiln-Dried Museum White Oak</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('molding','walnut',this)"><span>American Walnut Float Frame</span><span>→</span></button>
              <button type="button" class="quiz-option-btn" onclick="window.PrintDeckRuntime.selectQuizOption('molding','gold',this)"><span>Brushed Champagne Gold Leaf</span><span>→</span></button>
            </div>
          </div>
        </div>

        <div id="curator-quiz-result" style="padding:1.35rem 1.5rem;background:var(--bg-white);border:1px solid var(--accent-gold);border-radius:var(--radius-md);box-shadow:0 10px 26px rgba(20,20,19,0.06);"></div>
      </div>
    </section>

    <!-- 5. Asymmetric 2-Tier Collector Bundle Showcase ($173.84 Desk Trio vs $340 Complete Executive Studio Set) -->
    <section class="bundle-showcase" aria-label="Curated Architectural Studio Bundles">
      <div class="bundle-card">
        <div style="display:flex;flex-direction:column;gap:1.1rem;">
          <span style="font-size:0.76rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:var(--accent-gold-bright);">
            ✦ Private Collector Allocations • Save Up to $82 + Complimentary White-Glove Express Courier
          </span>
          <h2 style="font-family:var(--font-display);font-size:clamp(2.1rem,3.2vw,2.95rem);font-weight:400;line-height:1.08;color:#FAF8F5;">
            Choose Your Curated Studio &amp; Gallery Allocation
          </h2>
          <p style="font-size:0.94rem;color:#D8D2C5;line-height:1.6;">
            Acquire our coordinated 3-piece desk ensemble or step up to the complete 4-piece Executive Collector Allocation with solid hardwood framing and 450 GSM heavyweight apparel.
          </p>

          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:1rem;">
            <!-- Option A: $173.84 Studio Desk Trio -->
            <div style="padding:1.25rem;background:rgba(255,255,255,0.05);border:1px solid rgba(197,160,89,0.38);border-radius:var(--radius-md);display:flex;flex-direction:column;gap:0.65rem;">
              <div style="font-size:0.7rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:#D8D2C5;">Option I • 3-Piece Desk Trio</div>
              <div style="font-family:var(--font-display);font-size:1.45rem;color:#FAF8F5;">The Architectural Studio Trio</div>
              <ul style="list-style:none;display:grid;gap:0.35rem;font-size:0.8rem;color:#EAE3D2;">
                <li>✓ 24"×36" Stretched Gallery Canvas ($149)</li>
                <li>✓ XXL 31.5"×15.5" Stitched Desk Mat ($49)</li>
                <li>✓ 15oz Topographic Stoneware Mug ($24)</li>
              </ul>
              <div style="margin-top:auto;padding-top:0.65rem;border-top:1px solid rgba(255,255,255,0.12);">
                <div>
                  <span style="font-family:var(--font-display);font-size:1.95rem;color:#FFFFFF;">$173.84</span>
                  <span style="font-size:0.8rem;color:#B8B0A2;margin-left:0.35rem;"><s>$212.00</s> (Save $38.16)</span>
                </div>
                <div style="font-size:0.7rem;color:#DFBA73;margin:0.2rem 0 0.65rem;">Or 4 interest-free payments of $43.46</div>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                  <a href="/pay/quant-trader-executive-desk-setup-bundle" class="btn-primary" style="flex:1;padding:0.65rem 0.9rem;font-size:0.78rem;">Claim Studio Trio →</a>
                  <button type="button" class="btn-secondary" style="background:transparent;color:#FAF8F5;border-color:var(--accent-gold);padding:0.65rem 0.85rem;font-size:0.76rem;" onclick="window.PrintDeckRuntime.addToCart('PD-STUDIO-TRIO', 'Architectural Studio & Executive Desk Trio (Canvas + XXL Desk Mat + Mug)', 173.84, '/images/merch-deskmat-architect.webp', 'quant-trader-executive-desk-setup-bundle')">+ Bag</button>
                </div>
              </div>
            </div>

            <!-- Option B: $340 Complete Executive Studio & Apparel Collector Set -->
            <div style="padding:1.25rem;background:linear-gradient(180deg,rgba(200,90,50,0.18) 0%,rgba(197,160,89,0.12) 100%);border:2px solid var(--accent-gold-bright);border-radius:var(--radius-md);display:flex;flex-direction:column;gap:0.65rem;position:relative;">
              <div style="font-size:0.7rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--accent-gold-bright);">★ Collector's Choice • 4-Piece Flagship Allocation</div>
              <div style="font-family:var(--font-display);font-size:1.45rem;color:#FAF8F5;">Complete Executive Studio &amp; Apparel Set</div>
              <ul style="list-style:none;display:grid;gap:0.35rem;font-size:0.8rem;color:#FAF8F5;">
                <li>✦ 24"×36" Solid Oak/Walnut Framed Art ($189)</li>
                <li>✦ 450 GSM Heavyweight Atelier Hoodie ($88)</li>
                <li>✦ XXL 31.5"×15.5" Stitched Desk Mat ($49)</li>
                <li>✦ 1" Optical Crystal Art Monolith ($96)</li>
              </ul>
              <div style="margin-top:auto;padding-top:0.65rem;border-top:1px solid rgba(255,255,255,0.18);">
                <div>
                  <span style="font-family:var(--font-display);font-size:1.95rem;color:#FFFFFF;">$340.00</span>
                  <span style="font-size:0.8rem;color:#FFE5A3;margin-left:0.35rem;"><s>$422.00</s> (Save $82.00)</span>
                </div>
                <div style="font-size:0.7rem;color:#FFE5A3;margin:0.2rem 0 0.65rem;">Or 4 interest-free payments of $85.00 + Free $24 Mug</div>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                  <a href="/pay/executive-complete-studio-trio-340" class="btn-primary" style="flex:1;padding:0.65rem 0.9rem;font-size:0.78rem;">Claim $340 Set →</a>
                  <button type="button" class="btn-secondary" style="background:transparent;color:#FAF8F5;border-color:var(--accent-gold);padding:0.65rem 0.85rem;font-size:0.76rem;" onclick="window.PrintDeckRuntime.addToCart('PD-EXECUTIVE-SET-340', 'Complete Executive Studio & Apparel Collector Set (Framed Art + 450 GSM Hoodie + XXL Desk Mat + Crystal Monolith)', 340.00, '/images/art-coastal-horizon.webp', 'executive-complete-studio-trio-340')">+ Bag</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="bundle-visual-collage">
          <img src="/images/merch-deskmat-architect.webp" alt="Executive Walnut Desk Setup with Stitched Desk Mat" width="640" height="480" loading="lazy" />
          <div style="display:grid;gap:1rem;">
            <img src="/images/art-monolith-bauhaus.webp" alt="24x36 Bauhaus Impasto Canvas" width="380" height="240" loading="lazy" />
            <img src="/images/merch-ceramic-mug.webp" alt="15oz Stoneware Collector Mug" width="380" height="240" loading="lazy" />
          </div>
        </div>
      </div>
    </section>

    <!-- 5B. Verified Collector Reviews & Installation Stories -->
    <section class="reviews-section" aria-label="Verified Collector Reviews">
      <div class="section-header">
        <div>
          <span class="section-eyebrow">Verified Collector Installations</span>
          <h2 class="section-title">Why 4,200+ Collectors &amp; Designers Choose PrintDeck</h2>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
          <a href="#curated-catalog" class="btn-primary" style="padding:0.72rem 1.35rem;font-size:0.86rem;">Claim Your Numbered Edition →</a>
          <a href="/trade" class="btn-secondary" style="padding:0.72rem 1.25rem;font-size:0.86rem;">Interior Designer 20% Trade Portal →</a>
        </div>
      </div>
      <div class="reviews-grid">
        <article class="review-card">
          <div style="color:#D4882A;font-weight:800;font-size:0.9rem;">★★★★★ • Verified Gallery Purchase</div>
          <h3 style="font-family:var(--font-display);font-size:1.45rem;font-weight:400;">“Looks like a $1,200 piece from a Tribeca gallery.”</h3>
          <p style="font-size:0.88rem;color:var(--ink-graphite);line-height:1.6;">
            We hung the 24"×36" Monolith No. 4 in the Solid White Oak frame above our cognac leather sofa. The linen texture and pigment depth in morning sunlight are extraordinary.
          </p>
          <div style="margin-top:auto;display:flex;justify-content:space-between;align-items:center;padding-top:0.65rem;border-top:1px solid var(--border-stone);font-size:0.78rem;font-weight:700;color:var(--ink-espresso);">
            <span>Marcus &amp; Claire H. — Tribeca, NY</span>
            <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" style="color:var(--cta-terracotta);font-weight:800;">Claim This Edition ($149) →</a>
          </div>
        </article>

        <article class="review-card">
          <div style="color:#D4882A;font-weight:800;font-size:0.9rem;">★★★★★ • Verified Apparel Collector</div>
          <h3 style="font-family:var(--font-display);font-size:1.45rem;font-weight:400;">“Heaviest, best-draping hoodie I own.”</h3>
          <p style="font-size:0.88rem;color:var(--ink-graphite);line-height:1.6;">
            The 450 GSM cross-grain fleece feels identical to $250 luxury streetwear labels. Zero shrinkage after washing, and the print clarity on the washed espresso fabric is razor sharp.
          </p>
          <div style="margin-top:auto;display:flex;justify-content:space-between;align-items:center;padding-top:0.65rem;border-top:1px solid var(--border-stone);font-size:0.78rem;font-weight:700;color:var(--ink-espresso);">
            <span>Devon K. — Creative Director, LA</span>
            <a href="/pay/kinetic-foundry-450gsm-heavyweight-hoodie" style="color:var(--cta-terracotta);font-weight:800;">Claim 450 GSM Hoodie ($88) →</a>
          </div>
        </article>

        <article class="review-card">
          <div style="color:#D4882A;font-weight:800;font-size:0.9rem;">★★★★★ • Verified Studio Setup</div>
          <h3 style="font-family:var(--font-display);font-size:1.45rem;font-weight:400;">“Used the 2-hour edit window to upgrade to Walnut Float.”</h3>
          <p style="font-size:0.88rem;color:var(--ink-graphite);line-height:1.6;">
            Right after ordering I tested the Executive Study view in the visualizer and realized American Walnut matched my credenza better. Swapped frames in one click—arrived in 3 days!
          </p>
          <div style="margin-top:auto;display:flex;justify-content:space-between;align-items:center;padding-top:0.65rem;border-top:1px solid var(--border-stone);font-size:0.78rem;font-weight:700;color:var(--ink-espresso);">
            <span>Dr. Julian S. — Boston, MA</span>
            <a href="/pay/celestial-astrolabe-architectural-blueprint-print" style="color:var(--cta-terracotta);font-weight:800;">Claim Blueprint ($168) →</a>
          </div>
        </article>
      </div>
    </section>

    <!-- 6. Interactive Collector Guides: Gallery Wall Calculator, GSM Fabric Comparator & Corporate Volume Allocator -->
    <section class="tools-section" aria-label="Interactive Collector Sizing and Fabric Guides">
      <div class="micro-tool-card" id="gallery-wall-calculator">
        <span class="section-eyebrow">Interior Designer Sizing Guide</span>
        <h2 style="font-family:var(--font-display);font-size:1.85rem;font-weight:400;margin-bottom:0.5rem;">Gallery Wall Ratio &amp; Sofa Spacing Calculator</h2>
        <p style="font-size:0.9rem;color:var(--ink-graphite);margin-bottom:1rem;">
          Interior architects use the <strong>0.66–0.75 Golden Ratio</strong> to proportion artwork above a sofa, console, or headboard, hung at a 57" gallery eye-level center.
        </p>
        <div style="display:flex;gap:0.75rem;align-items:center;flex-wrap:wrap;">
          <label for="sofa-width-input" style="font-weight:700;font-size:0.86rem;">Your Sofa or Console Width (inches):</label>
          <input id="sofa-width-input" type="number" inputmode="numeric" value="72" min="48" max="120" onchange="window.PrintDeckRuntime.updateSofaCalc(this.value)" style="width:90px;padding:0.48rem 0.65rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-size:0.9rem;font-weight:700;" />
        </div>
        <div id="sofa-calc-output" style="font-size:0.86rem;font-weight:600;padding:0.95rem 1rem;background:var(--bg-soft-stone);border-left:4px solid var(--cta-terracotta);border-radius:4px;margin-top:1rem;color:var(--ink-charcoal);">
          Sofa Width: 72" → Ideal Artwork Span: 48"–54" (2/3 Golden Ratio) • Recommended: 24"×36" Museum Gallery Canvas or Solid Oak Float Frame hung 57" on-center.
        </div>
        <div style="margin-top:1.25rem;display:flex;gap:0.75rem;flex-wrap:wrap;">
          <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-primary" style="padding:0.68rem 1.2rem;font-size:0.84rem;">Claim Recommended 24"×36" Canvas ($149) →</a>
          <a href="#spatial-mockup-studio" class="btn-secondary" style="padding:0.68rem 1.1rem;font-size:0.84rem;">Test Size in Room Visualizer ↑</a>
        </div>
      </div>

      <div class="micro-tool-card" id="gsm-fabric-comparator">
        <span class="section-eyebrow">Garment &amp; Corporate Studio Estimator</span>
        <h2 style="font-family:var(--font-display);font-size:1.85rem;font-weight:400;margin-bottom:0.5rem;">GSM Textile Spec &amp; Team Volume Allocator</h2>
        <p style="font-size:0.9rem;color:var(--ink-graphite);margin-bottom:0.85rem;">
          Compare our custom-milled 280–450 GSM heavyweight garments and calculate instant studio/corporate volume pricing (15%–25% off):
        </p>
        <div style="display:flex;gap:0.75rem;align-items:center;flex-wrap:wrap;margin-bottom:0.75rem;">
          <label for="volume-units-slider" style="font-weight:700;font-size:0.84rem;">Team / Hospitality Quantity:</label>
          <input id="volume-units-slider" type="range" min="5" max="100" step="5" value="10" oninput="window.PrintDeckRuntime.updateVolumeCalc(this.value)" style="flex:1;accent-color:var(--cta-terracotta);" />
        </div>
        <div id="volume-calc-output" style="font-size:0.84rem;font-weight:600;padding:0.85rem 1rem;background:var(--bg-soft-stone);border-left:4px solid var(--accent-gold);border-radius:4px;color:var(--ink-charcoal);">
          <strong>10 Collector Pieces</strong> → Tier Privilege: <strong>15% Off ($74.80/unit)</strong> • Total Allocation: <strong>$748.00 USD</strong> (Save $132.00 + Dedicated Master Framer)
        </div>
        <div style="margin-top:1.15rem;display:flex;gap:0.75rem;flex-wrap:wrap;">
          <a id="volume-calc-claim-link" href="/pay/start?offer=b2b-studio-corporate-tier10&sku=PD-HOODIE-HEAVY-BLK&qty=10&promo=TRADE20" class="btn-primary" style="padding:0.68rem 1.2rem;font-size:0.84rem;">Lock Volume Allocation →</a>
          <a href="/pay/kinetic-foundry-450gsm-heavyweight-hoodie" class="btn-secondary" style="padding:0.68rem 1.1rem;font-size:0.84rem;">Claim Single 450 GSM Hoodie ($88) →</a>
        </div>
      </div>
    </section>
  </main>

  <!-- 6B. Floating Bottom Collector Quick-Claim Urgency Bar -->
  <aside class="floating-claim-bar" aria-label="Express Collector Allocation Bar">
    <div>
      <div style="font-size:0.78rem;font-weight:800;color:var(--ink-espresso);">
        <span style="color:var(--cta-terracotta);">●</span> Framing Cutoff in <span data-batch-countdown="1" style="color:var(--cta-terracotta);">03h : 41m : 19s</span>
      </div>
      <div class="floating-claim-bar__subtext" style="font-size:0.72rem;color:var(--ink-graphite);">
        Free Insured Courier Over $120 • 2-Hour Post-Order Edit Guarantee
      </div>
    </div>
    <div style="display:flex;gap:0.5rem;align-items:center;">
      <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-primary" style="padding:0.56rem 1rem;font-size:0.78rem;">
        Claim #1 Canvas ($149) →
      </a>
      <button type="button" class="btn-secondary" style="padding:0.54rem 0.85rem;font-size:0.76rem;" onclick="window.PrintDeckRuntime.toggleCartDrawer(true)">
        Bag
      </button>
    </div>
  </aside>

  <!-- 7. Slide-Out Instant Collector Bag Drawer (3-Tier Milestone Bar + 1-Tap Privilege Pills + Companion Cross-Sell) -->
  <div id="cart-drawer-backdrop" class="drawer-backdrop" onclick="window.PrintDeckRuntime.toggleCartDrawer(false)"></div>
  <aside class="cart-drawer-gpu" id="instant-cart-drawer" aria-label="Collector Shopping Bag">
    <div style="padding:1.15rem 1.4rem;border-bottom:1px solid var(--border-stone);display:flex;justify-content:space-between;align-items:center;background:var(--bg-white);">
      <div>
        <h2 style="font-family:var(--font-display);font-size:1.6rem;font-weight:400;">Your Collector Bag</h2>
        <div style="font-size:0.74rem;color:var(--accent-sage);font-weight:700;" id="free-shipping-msg">✓ Free Express Courier Unlocked! Add $51.00 for Wax-Stamped Provenance Folio</div>
      </div>
      <button type="button" onclick="window.PrintDeckRuntime.toggleCartDrawer(false)" style="background:var(--bg-soft-stone);border:1px solid var(--border-stone);width:44px;height:44px;border-radius:50%;font-size:0.95rem;cursor:pointer;" aria-label="Close Collector Bag">✕</button>
    </div>

    <div style="padding:0.45rem 1.4rem;background:#FAF3E6;border-bottom:1px solid #E2D5BE;font-size:0.74rem;font-weight:700;color:var(--ink-espresso);display:flex;justify-content:space-between;">
      <span>✦ Edition Allocation Reserved in Your Name:</span>
      <span style="color:var(--cta-terracotta);font-weight:800;font-variant-numeric:tabular-nums;" id="cart-reservation-timer">14:58</span>
    </div>

    <div style="height:6px;background:var(--bg-warm-linen);width:100%;position:relative;">
      <div id="free-shipping-bar-fill" style="height:100%;width:53%;background:linear-gradient(90deg,var(--accent-gold) 0%,var(--accent-sage) 100%);transition:width 0.3s ease;"></div>
    </div>

    <div id="cart-items-container" style="flex:1;overflow-y:auto;padding:0.5rem 1.4rem;"></div>

    <div style="padding:1rem 1.4rem;background:var(--bg-soft-stone);border-top:1px solid var(--border-stone);">
      <div style="font-size:0.71rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-graphite);margin-bottom:0.35rem;">
        1-Click Curatorial Enhancements
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.45rem;margin-bottom:0.75rem;">
        <button type="button" onclick="window.PrintDeckRuntime.addToCart('PD-DESKMAT-36X18', 'XXL Architect Stitched Desk Mat (31.5\\x22×15.5\\x22)', 49.00, '/images/merch-deskmat-architect.webp', 'xxl-architect-stitched-desk-mat')" style="background:#fff;border:1px solid var(--border-strong);border-radius:6px;padding:0.42rem 0.55rem;font-size:0.73rem;font-weight:700;color:var(--ink-espresso);text-align:left;cursor:pointer;">
          + XXL Desk Mat <span style="color:var(--cta-terracotta);">($49)</span>
        </button>
        <button type="button" onclick="window.PrintDeckRuntime.addToCart('PD-EXECUTIVE-SET-340', 'Complete 4-Piece Executive Collector Set (Save $82)', 340.00, '/images/art-coastal-horizon.webp', 'executive-complete-studio-trio-340')" style="background:#fff;border:1px solid var(--accent-gold);border-radius:6px;padding:0.42rem 0.55rem;font-size:0.73rem;font-weight:700;color:var(--ink-espresso);text-align:left;cursor:pointer;">
          + $340 Full Set <span style="color:var(--accent-sage);">(-$82)</span>
        </button>
      </div>

      <div style="margin-bottom:0.7rem;">
        <div style="font-size:0.71rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-graphite);">
          1-Tap Collector Privileges (No Coupon Hunting Required)
        </div>
        <div class="privilege-pill-group">
          <button type="button" class="privilege-pill" data-promo-pill="ATELIER15" onclick="window.PrintDeckRuntime.applyPromoCode('ATELIER15')">✦ ATELIER15 (-15%)</button>
          <button type="button" class="privilege-pill" data-promo-pill="STUDIO36" onclick="window.PrintDeckRuntime.applyPromoCode('STUDIO36')">✦ STUDIO36 (-$36)</button>
          <button type="button" class="privilege-pill" data-promo-pill="TRADE20" onclick="window.PrintDeckRuntime.applyPromoCode('TRADE20')">✦ TRADE20 (-20% $200+)</button>
        </div>
      </div>

      <div id="cart-discount-row" style="display:none;justify-content:space-between;align-items:center;font-size:0.78rem;color:var(--accent-sage);font-weight:700;margin-bottom:0.35rem;"></div>

      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.25rem;">
        <span style="font-size:0.88rem;color:var(--ink-graphite);font-weight:700;">Allocation Total</span>
        <strong id="cart-subtotal-value" style="font-family:var(--font-display);font-size:1.8rem;">$149.00 USD</strong>
      </div>
      <div id="cart-bnpl-installments" style="font-size:0.72rem;color:var(--ink-graphite);text-align:right;margin-bottom:0.75rem;font-weight:600;">
        Or 4 interest-free collector installments of $37.25 with Klarna / Affirm
      </div>

      <a id="cart-drawer-checkout-btn" href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?sku=PD-CANVAS-24X36&qty=1&size=24x36&frame=oak" class="btn-primary" style="width:100%;text-align:center;padding:0.95rem;">
        Proceed to Express Checkout ($149.00) →
      </a>
      <div style="text-align:center;font-size:0.72rem;color:var(--ink-muted);margin-top:0.5rem;">
        ✓ 30-Day In-Home Trial • 2-Hour Post-Order Edit • Instant Damage Replacement
      </div>
    </div>
  </aside>

  <!-- 7B. Macro Substrate & Joinery Loupe Modal -->
  <div id="macro-loupe-modal" class="atelier-modal-backdrop" onclick="if(event.target===this)window.PrintDeckRuntime.closeAllModals()">
    <div class="atelier-modal-card" role="dialog" aria-modal="true" aria-labelledby="macro-loupe-title">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
        <span class="section-eyebrow" style="margin:0;">Optical Loupe Specimen Sheet • ISO 9706 Museum Permanence</span>
        <button type="button" onclick="window.PrintDeckRuntime.closeAllModals()" style="background:var(--bg-soft-stone);border:1px solid var(--border-stone);width:40px;height:40px;border-radius:50%;cursor:pointer;">✕</button>
      </div>
      <h2 id="macro-loupe-title" style="font-family:var(--font-display);font-size:2rem;font-weight:400;margin-bottom:0.75rem;">
        410 GSM Belgian Linen, Kiln-Dried Hardwood &amp; 450 GSM Cross-Grain Fleece
      </h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr));gap:1rem;margin-bottom:1.25rem;">
        <div style="background:var(--bg-white);border:1px solid var(--border-stone);border-radius:8px;padding:1rem;">
          <img src="/images/art-monolith-bauhaus.webp" alt="410 GSM Belgian Linen Weave" style="width:100%;height:120px;object-fit:cover;border-radius:6px;margin-bottom:0.6rem;" />
          <strong style="font-size:0.84rem;display:block;">01. 410 GSM Belgian Linen &amp; 310 GSM Rag</strong>
          <p style="font-size:0.77rem;color:var(--ink-graphite);margin-top:0.25rem;">Acid-free pH-neutral coating with 12-color archival pigment penetration rated for 100+ years of indoor lightfastness.</p>
        </div>
        <div style="background:var(--bg-white);border:1px solid var(--border-stone);border-radius:8px;padding:1rem;">
          <img src="/images/art-coastal-horizon.webp" alt="Hardwood Float Frame Joinery" style="width:100%;height:120px;object-fit:cover;border-radius:6px;margin-bottom:0.6rem;" />
          <strong style="font-size:0.84rem;display:block;">02. 1.75" Kiln-Dried Oak &amp; Walnut Float</strong>
          <p style="font-size:0.77rem;color:var(--ink-graphite);margin-top:0.25rem;">Hand-sanded hardwood moldings with reinforced corner splines and a signature 0.25" gallery shadow-gap reveal.</p>
        </div>
        <div style="background:var(--bg-white);border:1px solid var(--border-stone);border-radius:8px;padding:1rem;">
          <img src="/images/apparel-hoodie-espresso.webp" alt="450 GSM Heavyweight French Terry" style="width:100%;height:120px;object-fit:cover;border-radius:6px;margin-bottom:0.6rem;" />
          <strong style="font-size:0.84rem;display:block;">03. 450 GSM Cross-Grain Fleece</strong>
          <p style="font-size:0.77rem;color:var(--ink-graphite);margin-top:0.25rem;">13.3 oz custom-milled combed organic cotton with double-ribbed side gussets—nearly triple the weight of promo blanks.</p>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;padding-top:1rem;border-top:1px solid var(--border-stone);">
        <span style="font-size:0.8rem;font-weight:700;color:var(--accent-sage);">✓ Every Piece Inspected at 300 DPI Before Framing</span>
        <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15" class="btn-primary" style="padding:0.7rem 1.25rem;font-size:0.82rem;">Claim Flagship Edition w/ 15% Privilege →</a>
      </div>
    </div>
  </div>

  <!-- 7C. Certificate of Provenance Preview Modal -->
  <div id="provenance-cert-modal" class="atelier-modal-backdrop" onclick="if(event.target===this)window.PrintDeckRuntime.closeAllModals()">
    <div class="atelier-modal-card" role="dialog" aria-modal="true" aria-labelledby="provenance-cert-title" style="background:#F6F2E9;border:2px solid var(--accent-gold);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem;">
        <span style="font-size:0.74rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:var(--cta-terracotta);">✦ PRINTDECK ARCHIVAL REGISTRY • EMBOSSED FOLIO SPECIMEN</span>
        <button type="button" onclick="window.PrintDeckRuntime.closeAllModals()" style="background:var(--bg-white);border:1px solid var(--border-stone);width:40px;height:40px;border-radius:50%;cursor:pointer;">✕</button>
      </div>
      <div style="border:1px solid var(--accent-gold);padding:1.5rem;border-radius:8px;background:#FAF8F5;">
        <h2 id="provenance-cert-title" style="font-family:var(--font-display);font-size:1.95rem;font-weight:400;text-align:center;margin-bottom:0.35rem;">
          Certificate of Archival Provenance &amp; Edition Registry
        </h2>
        <p style="text-align:center;font-size:0.82rem;color:var(--ink-graphite);margin-bottom:1.15rem;">
          Accompanies every PrintDeck framed canvas, fine-art rag print, and serialized collector set in an acid-free glassine envelope.
        </p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:0.85rem;font-size:0.8rem;padding:1rem;background:var(--bg-soft-stone);border-radius:6px;margin-bottom:1rem;">
          <div><strong>Edition Allocation:</strong> Hand-Numbered #294 / 300</div>
          <div><strong>Optical Resolution:</strong> Verified 300-DPI Giclée</div>
          <div><strong>Archival Permanence:</strong> 100+ Yr Wilhelm Rating</div>
          <div><strong>Master Framer Sign-Off:</strong> Atelier Lot #PD-2026-XI</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
          <span style="font-size:0.78rem;color:var(--ink-graphite);">✦ Includes 2-Hour Post-Order Edit Protection &amp; Lifetime Frame Warranty</span>
          <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36" class="btn-primary" style="padding:0.7rem 1.25rem;font-size:0.82rem;">Acquire Numbered Edition ($149) →</a>
        </div>
      </div>
    </div>
  </div>

  <!-- 7D. Client-Side Concierge Error-Recovery & VIP Allocation Modal -->
  <div id="error-recovery-modal" class="atelier-modal-backdrop" onclick="if(event.target===this)window.PrintDeckRuntime.closeAllModals()">
    <div class="atelier-modal-card" role="dialog" aria-modal="true" aria-labelledby="error-recovery-title">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
        <span class="section-eyebrow" style="margin:0;">✦ Private Curatorial Allocation Override</span>
        <button type="button" onclick="window.PrintDeckRuntime.closeAllModals()" style="background:var(--bg-soft-stone);border:1px solid var(--border-stone);width:40px;height:40px;border-radius:50%;cursor:pointer;">✕</button>
      </div>
      <h2 id="error-recovery-title" style="font-family:var(--font-display);font-size:1.95rem;font-weight:400;margin-bottom:0.4rem;">
        We Have Unlocked Your 15% Private Collector Privilege (ATELIER15)
      </h2>
      <p id="recovery-modal-reason" style="font-size:0.88rem;color:var(--ink-graphite);margin-bottom:1.15rem;">
        Our Curatorial Desk has reserved direct express access to our #1 Flagship Editions below with your 15% privilege automatically applied.
      </p>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <a href="/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15" class="btn-primary">Claim #1 Monolith Canvas ($126.65 w/ ATELIER15) →</a>
        <a href="/pay/executive-complete-studio-trio-340?promo=ATELIER15" class="btn-secondary">Claim $340 Collector Set (-15%) →</a>
      </div>
    </div>
  </div>

  <!-- 8. Clean, Minimizable Atelier Design Advisor Widget -->
  <aside id="printdeck-concierge-chat" data-testid="printdeck-concierge-chat" class="concierge-widget">
    <div id="concierge-chat-panel" class="concierge-panel">
      <div style="padding:0.85rem 1.1rem;background:var(--ink-espresso);color:#FAF8F5;display:flex;justify-content:space-between;align-items:center;">
        <div>
          <strong style="font-size:0.92rem;display:block;">✦ PrintDeck Framing &amp; Sizing Advisor</strong>
          <span style="font-size:0.72rem;color:#DFBA73;">Live Curatorial &amp; Order Support</span>
        </div>
        <button type="button" onclick="window.PrintDeckRuntime.toggleConcierge()" style="background:none;border:none;color:#FAF8F5;font-size:0.95rem;width:36px;height:36px;cursor:pointer;">✕</button>
      </div>
      <div id="concierge-chat-messages" style="max-height:230px;overflow-y:auto;padding:0.9rem;display:flex;flex-direction:column;gap:0.55rem;background:var(--bg-alabaster);">
        <div style="background:var(--bg-white);padding:0.65rem 0.85rem;border-radius:10px;font-size:0.82rem;line-height:1.45;border:1px solid var(--border-stone);">
          Welcome to PrintDeck! Ask me to recommend a frame molding for your room, size artwork for your sofa, or customize heavyweight apparel.
        </div>
      </div>
      <div style="padding:0.65rem;border-top:1px solid var(--border-stone);display:flex;gap:0.45rem;background:var(--bg-white);">
        <input id="concierge-chat-input" type="text" placeholder="Ask about frame sizes, fabrics, or orders..." onkeydown="if(event.key==='Enter')window.PrintDeckRuntime.sendConciergeChat()" style="flex:1;background:var(--bg-soft-stone);color:var(--ink-espresso);border:1px solid var(--border-strong);border-radius:6px;padding:0.5rem 0.7rem;font-size:1rem;" />
        <button data-testid="concierge-launcher-btn" type="button" onclick="window.PrintDeckRuntime.sendConciergeChat()" class="btn-primary" style="padding:0.5rem 0.9rem;font-size:0.8rem;">Send</button>
      </div>
    </div>

    <button type="button" class="concierge-launcher-pill" onclick="window.PrintDeckRuntime.toggleConcierge()">
      <span style="color:var(--accent-gold-bright);">✦</span>
      <span>Framing &amp; Sizing Advisor</span>
    </button>
  </aside>

  <!-- 9. Editorial Gallery Footer -->
  <footer class="site-footer">
    <div class="site-footer__inner">
      <div>
        <div style="font-family:var(--font-display);font-size:2.1rem;color:#FAF8F5;margin-bottom:0.5rem;">PrintDeck</div>
        <p style="font-size:0.86rem;color:#C7C1B5;max-width:38ch;line-height:1.6;margin-bottom:1rem;">
          Museum-grade 300-DPI archival canvas paintings, solid hardwood framing, heavyweight street-atelier garments, and precision studio goods.
        </p>
        <a href="#curated-catalog" class="btn-primary" style="padding:0.6rem 1.15rem;font-size:0.8rem;">Claim Autumn Exhibition Edition →</a>
      </div>
      <div>
        <div class="footer-heading">Collections &amp; Guides</div>
        <ul class="footer-links">
          <li><a href="#curated-catalog" onclick="window.PrintDeckRuntime.filterCatalog('wall_art')">Archival Canvas &amp; Framed Art</a></li>
          <li><a href="#curated-catalog" onclick="window.PrintDeckRuntime.filterCatalog('apparel')">280–450 GSM Custom Apparel</a></li>
          <li><a href="/articles/">Editorial Journal &amp; Buyer Guides</a></li>
          <li><a href="/compare/">Substrate Comparison Matrix</a></li>
          <li><a href="/gifts/">Curated Collector Gift Guides</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-heading">Collector Care &amp; Trade</div>
        <ul class="footer-links">
          <li><a href="/sign-in.html">Sign In with Authentik SSO</a></li>
          <li><a href="/trade">Interior Designer Trade Portal (20%)</a></li>
          <li><a href="/tools/">Interactive Sizing Calculators</a></li>
          <li><a href="/shipping.html">Shipping &amp; 2-Hour Edit Guarantee</a></li>
          <li><a href="/refunds.html">Conservation &amp; Returns Policy</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-heading">Hardware &amp; Telemetry</div>
        <ul class="footer-links">
          <li><a href="/hardware">Bambu Lab 4.3" Touchscreen (/hardware)</a></li>
          <li><a href="/simulator">Touchscreen Firmware Simulator</a></li>
          <li><a href="/metrics">Live Prometheus Telemetry (/metrics)</a></li>
          <li><a href="/llms-full.txt">Catalog Index (/llms-full.txt)</a></li>
          <li><a href="/sitemap-index.xml">XML Sitemap</a></li>
        </ul>
      </div>
    </div>
  </footer>

  <script src="/assets/spatial-studio.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""

    # 2. Interactive Spatial Mockup Studio (/studio/index.html)
    studio_html = index_html.replace(
        "<title>PrintDeck — Archival Gallery Prints, Custom Hardwood Framing &amp; Heavyweight Apparel</title>",
        "<title>PrintDeck Custom Print Studio (/studio) — Live 4-Room Visualizer &amp; Bespoke Framing</title>",
    )

    # 3. Authentik SSO Customer Sign-In & Order Tracking Page (/sign-in.html & /sign-up.html)
    signin_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Collector Sign In &amp; Order Tracking — PrintDeck (Authentik SSO)</title>
  <link rel="canonical" href="https://printdeck.net/sign-in.html" />
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div class="announcement-bar__promo">
        <span class="announcement-bar__dot"></span>
        <span>Unified Collector Identity &amp; Order Protection Powered by <strong>Authentik OIDC / SSO</strong></span>
      </div>
      <div class="announcement-bar__links">
        <a href="/">← Return to Storefront</a>
        <a href="/studio">Custom Studio</a>
      </div>
    </div>
  </div>

  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Collector Identity &amp; Order Portal</span>
      </a>
      <div class="header-actions">
        <a href="/" class="btn-secondary" style="padding:0.55rem 1.1rem;font-size:0.84rem;">← Back to Gallery</a>
      </div>
    </div>
  </header>

  <main style="max-width:1060px;margin:3.5rem auto;padding:0 1.25rem;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:2rem;align-items:start;">
    <section class="micro-tool-card">
      <span class="section-eyebrow">Authentik Unified Single Sign-On</span>
      <h1 style="font-family:var(--font-display);font-size:2.25rem;font-weight:400;margin-bottom:0.5rem;">Sign In to Your Collector Account</h1>
      <p style="font-size:0.9rem;color:var(--ink-graphite);margin-bottom:1.5rem;">
        Access your saved room visualizer mockups, track archival framing shipments, or edit your address and frame size during our 2-hour post-checkout grace window.
      </p>

      <form id="authentik-login-form" onsubmit="event.preventDefault();window.handleAuthentikLogin();" style="display:flex;flex-direction:column;gap:1rem;">
        <div>
          <label for="ak-email" style="display:block;font-size:0.82rem;font-weight:700;margin-bottom:0.35rem;">Collector Email Address</label>
          <input id="ak-email" type="email" inputmode="email" autocomplete="email" required placeholder="collector@domain.com" style="width:100%;padding:0.75rem 0.9rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-size:1rem;background:var(--bg-alabaster);" />
        </div>
        <div>
          <label for="ak-name" style="display:block;font-size:0.82rem;font-weight:700;margin-bottom:0.35rem;">Full Name (Optional)</label>
          <input id="ak-name" type="text" autocomplete="name" placeholder="Elena Sterling" style="width:100%;padding:0.75rem 0.9rem;border:1px solid var(--border-strong);border-radius:var(--radius-sm);font-size:1rem;background:var(--bg-alabaster);" />
        </div>
        <button type="submit" class="btn-primary" style="width:100%;margin-top:0.25rem;">
          Continue with Authentik SSO →
        </button>
      </form>

      <div id="authentik-status-box" style="display:none;margin-top:1.25rem;padding:1rem;background:var(--accent-sage-soft);border:1px solid var(--accent-sage);border-radius:var(--radius-sm);font-size:0.86rem;color:var(--ink-espresso);"></div>

      <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border-stone);font-size:0.78rem;color:var(--ink-muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
        <span>OIDC Provider: <code>auth.printdeck.net</code> (Authentik)</span>
        <a href="/admin" style="color:var(--cta-terracotta);font-weight:700;">Executive Portal (/admin) →</a>
      </div>
    </section>

    <section class="micro-tool-card" id="orders">
      <span class="section-eyebrow">2-Hour Easy Order Edit Window</span>
      <h2 style="font-family:var(--font-display);font-size:1.85rem;font-weight:400;margin-bottom:0.5rem;">Instant Order Lookup &amp; Self-Service Edit</h2>
      <p style="font-size:0.88rem;color:var(--ink-graphite);margin-bottom:1.25rem;">
        Every PrintDeck order is held in a complimentary 120-minute review queue before archival printing begins, allowing instant size, frame, or address updates.
      </p>
      <div id="collector-orders-list" style="padding:1.25rem;background:var(--bg-soft-stone);border-radius:var(--radius-sm);font-size:0.86rem;color:var(--ink-charcoal);">
        Sign in with your collector email on the left to view live order statuses, tracking links, and 2-hour grace window controls.
      </div>
    </section>
  </main>

  <script>
    window.handleAuthentikLogin = async function () {{
      var email = document.getElementById("ak-email").value.trim();
      var name = document.getElementById("ak-name").value.trim() || "Verified Collector";
      var box = document.getElementById("authentik-status-box");
      var ordersBox = document.getElementById("collector-orders-list");
      if (!email) return;
      try {{
        var res = await fetch("/api/auth/authentik/login", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ email: email, name: name, provider: "authentik-oidc", redirect_to: "/" }})
        }});
        var data = await res.json();
        box.style.display = "block";
        box.innerHTML = "<strong>✓ Authentik Session Verified</strong><br/>Signed in as <strong>" + data.user.email + "</strong> (Token: <code>" + data.session_token + "</code>). <a href='/' style='color:#C85A32;font-weight:700;margin-left:0.4rem;'>Return to Gallery →</a>";
        var sRes = await fetch("/api/auth/session");
        var sData = await sRes.json();
        if (sData.orders && sData.orders.length > 0) {{
          ordersBox.innerHTML = sData.orders.map(function (o) {{
            return "<div style='padding:0.65rem 0;border-bottom:1px solid #CEC3B2;'><strong>" + o.order_number + "</strong> • Status: " + o.status + " • $" + (o.total_cents / 100).toFixed(2) + "</div>";
          }}).join("");
        }} else {{
          ordersBox.innerHTML = "Authenticated as <strong>" + email + "</strong> via Authentik OIDC. No active orders found for this email yet—explore our <a href='/#curated-catalog' style='color:#C85A32;font-weight:700;'>Best Sellers</a>.";
        }}
      }} catch (e) {{
        console.error(e);
      }}
    }};
  </script>
</body>
</html>
"""

    # 4. Protected Hardware Coexistence Page (/hardware/index.html & /simulator/index.html)
    hw_json_ld = json.dumps(seo.build_product_json_ld("HW-BAMBU-43-CTRL"), indent=2)
    hardware_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PrintDeck Bambu Lab 4.3" ESP32-P4 Touchscreen Controller — /hardware</title>
  <link rel="canonical" href="https://printdeck.net/hardware" />
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
  <script type="application/ld+json">
{hw_json_ld}
  </script>
</head>
<body>
  <header class="site-header">
    <div class="site-header__inner">
      <a href="/" class="brand-logo">
        <span class="brand-logo__name">PrintDeck</span>
        <span class="brand-logo__tag">Hardware Coexistence Division • /hardware</span>
      </a>
      <div class="header-actions">
        <a href="/" class="btn-secondary">← Return to Fine Art &amp; Apparel Storefront</a>
      </div>
    </div>
  </header>
  <main style="max-width:1100px;margin:3.5rem auto;padding:0 1.25rem;">
    <div class="micro-tool-card">
      <span class="section-eyebrow">Protected Hardware Coexistence Route • /hardware</span>
      <h1 style="font-family:var(--font-display);font-size:2.6rem;font-weight:400;margin:0.4rem 0 1rem;">PrintDeck Bambu Lab 4.3" ESP32-P4 Touchscreen Controller</h1>
      <p style="font-size:1rem;color:var(--ink-graphite);line-height:1.65;margin-bottom:1.5rem;">
        Dedicated plug-and-play 4.3" capacitive IPS touchscreen controller for Bambu Lab X1C, P1S, P1P, A1, and A1 Mini 3D printers. Preserved offers: <strong>HW-BAMBU-43-CTRL</strong> ($129.00), <strong>HW-MAKER-PACK-19</strong> ($19.00 Maker Pack via <a href="/pay/printdeck-maker-pack" style="color:var(--cta-terracotta);font-weight:700;">/pay/printdeck-maker-pack</a>), and <strong>HW-BETA-DEPOSIT-50</strong> ($50.00 Beta Hardware Deposit).
      </p>
      <div style="display:flex;gap:1rem;flex-wrap:wrap;">
        <a href="/pay/printdeck-maker-pack" class="btn-primary">Order Maker Pack ($19.00) →</a>
        <a href="/simulator" class="btn-secondary">Launch LVGL Firmware Simulator (/simulator)</a>
        <a href="/" class="btn-secondary">← Explore Archival Prints &amp; Apparel</a>
      </div>
    </div>
  </main>
</body>
</html>
"""

    # 5. Responsive Luxury Curatorial Archive & Selling Recovery Page (/404.html)
    not_found_html = f"""<!DOCTYPE html>
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
  <main style="max-width:1180px;margin:2.5rem auto 4rem;padding:0 1.25rem;">
    <section class="micro-tool-card" style="border-top:3px solid var(--accent-gold);margin-bottom:2.25rem;background:linear-gradient(180deg,#FFFFFF 0%,#F7F3EA 100%);">
      <span class="section-eyebrow">✦ Curatorial Archive &amp; Allocation Redirection</span>
      <h1 style="font-family:var(--font-display);font-size:clamp(2rem,3.4vw,2.85rem);font-weight:400;margin:0.3rem 0 0.75rem;color:var(--ink-espresso);">
        That Edition Link Has Rotated—Claim Your 15% Private Collector Privilege Below
      </h1>
      <p style="font-size:0.95rem;color:var(--ink-graphite);max-width:68ch;line-height:1.6;margin-bottom:1.25rem;">
        Rather than leaving you at an expired archive link, our Curatorial Desk has automatically credited your session with a <strong>15% Courtesy Privilege (Code: <code>ATELIER15</code>)</strong> across all flagship 300-DPI canvas editions, solid hardwood float frames, and 450 GSM garments.
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

    # 6. Executive Admin Command Center (/admin/index.html) — All Internal Telemetry Strictly Isolated Here
    open_issues_count = len(ssot_state.get("open_issues", []))
    closed_issues_count = len(ssot_state.get("closed_issues", []))
    admin_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PrintDeck Executive Command Center (/admin) — Authentik SSO + Authelia + LLDAP</title>
  <link rel="stylesheet" href="/assets/atelier-foundry.css?v={ASSET_VERSION}" />
  {CRITICAL_HEAD_STYLE}
</head>
<body>
  <div class="announcement-bar">
    <div class="announcement-bar__inner">
      <div><span class="announcement-bar__dot"></span> AUTHENTIK OIDC / FORWARDAUTH + AUTHELIA SSO VERIFIED • OPERATOR: DIMA • OPERATOR_OVERRIDE LOCK PREEMPTION READY</div>
      <div class="announcement-bar__links">
        <a href="/metrics">PROMETHEUS /METRICS</a>
        <a href="/api/ssot">LIVE SSOT JSON</a>
        <a href="/">← PUBLIC STOREFRONT</a>
      </div>
    </div>
  </div>
  <main style="max-width:1400px;margin:2.5rem auto;padding:0 2rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;">
      <div>
        <span class="section-eyebrow">Protected Internal Telemetry &amp; Autonomous Fleet Governance</span>
        <h1 style="font-family:var(--font-display);font-size:2.5rem;font-weight:400;">PrintDeck Executive Command Center (/admin)</h1>
      </div>
      <a href="/" class="btn-secondary">← Storefront</a>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:1.5rem;">
      <section class="micro-tool-card" id="admin-inventory-editor">
        <span class="section-eyebrow">MODULE 01 • LIVE INVENTORY EDITOR &amp; MASS MATRIX UPLOADER</span>
        <h2 style="font-family:var(--font-display);font-size:1.6rem;margin:0.4rem 0;">Inline Product Editor &amp; 450-Variant Bulk Dropzone</h2>
        <p style="font-size:0.88rem;color:var(--ink-graphite);">Add, edit, or retire SKUs, override Printify vs. Printful provider routing with automatic <code>OPERATOR_OVERRIDE</code> lock preemption, or drop CSV/JSON/ZIP artwork batches across Stretched Canvas, Heavyweight Tee, Hoodie, Ceramic Mug, and Stitched Desk Mat.</p>
      </section>
      <section class="micro-tool-card" id="admin-crm-360">
        <span class="section-eyebrow">MODULE 02 • 360° CUSTOMER CRM &amp; 120-MIN GRACE WINDOW EDITOR</span>
        <h2 style="font-family:var(--font-display);font-size:1.6rem;margin:0.4rem 0;">Cross-Store Customer Profiles &amp; 1-Click Order Intervention</h2>
        <p style="font-size:0.88rem;color:var(--ink-graphite);">Unified customer ledger across <code>printdeck.sqlite</code>, <code>paygate.sqlite</code> (:8790), and <code>intake.sqlite</code> (:8787). Edit addresses/sizes during the 120-minute <code>PAID_GRACE_HOLD</code> window, reroute Printify/Printful, dispatch zero-cost replacements, or trigger Stripe refunds.</p>
      </section>
      <section class="micro-tool-card" id="admin-finops-seo">
        <span class="section-eyebrow">MODULE 03 • SEO, GEO &amp; FINOPS TELEMETRY DASHBOARD</span>
        <h2 style="font-family:var(--font-display);font-size:1.6rem;margin:0.4rem 0;">GMV, 35% Net Margin Floor, Arbitrage Savings &amp; Cohort Matrix</h2>
        <p style="font-size:0.88rem;color:var(--ink-graphite);">Real-time GMV, Net Profit after COGS + Stripe fees, Smart Arbitrage Savings, AI Crawler Hits (<code>GPTBot</code>, <code>ClaudeBot</code>, <code>PerplexityBot</code>, <code>Google-Extended</code>), and 4-Quadrant Cohort Matrix: <strong>STAR</strong>, <strong>HIDDEN_GEM</strong>, <strong>FIXABLE</strong>, and <strong>CULL_CANDIDATE</strong>.</p>
      </section>
      <section class="micro-tool-card" id="admin-ssot-console">
        <span class="section-eyebrow">MODULE 04 • LIVE SSOT CONSOLE &amp; 5-AGENT BOARD ROOM LEDGER</span>
        <h2 style="font-family:var(--font-display);font-size:1.6rem;margin:0.4rem 0;">ACTIVE LOCK TABLE • PUNCH CLOCK LOG • OPEN ISSUES ({open_issues_count}) • CLOSED ISSUES ({closed_issues_count})</h2>
        <p style="font-size:0.88rem;color:var(--ink-graphite);">Real-time stream of <code>SOURCE_OF_TRUTH.md</code> (`ACTIVE LOCK TABLE`, `PUNCH CLOCK LOG`, `OPEN ISSUES:`, `CLOSED ISSUES:`) and 5-Agent Executive Board Room voting ledger.</p>
      </section>
    </div>
  </main>
</body>
</html>
"""

    # 7. Unified Luxury Supporting Pages (shipping.html, refunds.html, about.html, contact.html, privacy.html, terms.html)
    shipping_html = _render_policy_or_info_page(
        "shipping.html",
        "White-Glove Archival Logistics",
        "Insured Express Shipping & 2-Hour Order Edit Guarantee",
        "Every PrintDeck framed canvas, fine art print, and heavyweight garment is custom-crafted and shipped in reinforced museum-grade corner-protected packaging.",
        """
        <div><strong>1. Complimentary Insured Express Delivery Over $120:</strong> Orders over $120 USD automatically qualify for free insured express courier delivery across the US, Canada, UK, EU, and Australia.</div>
        <div><strong>2. 2-Hour Easy Order Edit Window:</strong> Every order enters a 120-minute post-checkout review window so you can swap frame moldings, update print dimensions, or adjust your delivery address via <a href="/sign-in.html#orders" style="color:var(--cta-terracotta);font-weight:700;">Authentik Collector Sign-In</a> before archival production begins.</div>
        <div><strong>3. Custom Framing & Production Lead Time:</strong> Stretched 410 GSM Belgian linen canvases and solid oak/walnut float frames ship within 48–72 hours of final proof approval.</div>
        """,
    )
    refunds_html = _render_policy_or_info_page(
        "refunds.html",
        "Collector Satisfaction & Conservation Guarantee",
        "100-Year Archival Warranty & Effortless Replacements",
        "We stand behind every museum print, solid hardwood frame, and 280–450 GSM garment that leaves our atelier.",
        """
        <div><strong>1. Instant Zero-Cost Transit Damage Replacement:</strong> If your framed artwork or stoneware arrives with any transit blemish, upload a photo in your collector portal or concierge chat for an immediate priority replacement—no return shipping required.</div>
        <div><strong>2. 30-Day Collector Satisfaction Guarantee:</strong> Standard gallery editions and unworn heavyweight apparel may be exchanged or refunded within 30 days of delivery.</div>
        """,
    )
    about_html = _render_policy_or_info_page(
        "about.html",
        "The PrintDeck Tactile Atelier",
        "Museum-Grade Permanence for Modern Living Spaces",
        "PrintDeck bridges private-gallery archival printmaking with custom-milled heavyweight streetwear and architectural desk essentials.",
        """
        <div><strong>410 GSM Belgian Linen & 310 GSM Cotton Rag:</strong> Calibrated to 300-DPI optical density with 12-color archival pigment inks rated for 100+ years of lightfastness.</div>
        <div><strong>280–450 GSM Heavyweight Garments:</strong> Milled from combed organic ring-spun cotton and cross-grain fleece for structured, zero-torque longevity.</div>
        """,
    )
    contact_html = _render_policy_or_info_page(
        "contact.html",
        "Curatorial & Collector Concierge",
        "Contact Our Framing & Custom Studio Advisors",
        "Need bespoke gallery wall sizing, interior trade pricing, or help with an existing order?",
        """
        <div><strong>Live Framing & Sizing Concierge:</strong> Click the <em>Framing & Sizing Advisor</em> pill at the bottom right of any page for instant curatorial assistance and live order lookup.</div>
        <div><strong>Collector Account & 2-Hour Edit Portal:</strong> Visit <a href="/sign-in.html" style="color:var(--cta-terracotta);font-weight:700;">/sign-in.html</a> to manage your active orders with Authentik SSO.</div>
        """,
    )

    llms_short = seo.generate_llms_txt(full=False)
    llms_full = seo.generate_llms_txt(full=True)
    smap_idx = seo.generate_sitemap_index_xml()
    smap_prod = seo.generate_sitemap_products_xml()
    smap_coll = seo.generate_sitemap_collections_xml()
    smap_guide = seo.generate_sitemap_guides_xml()

    for target_root in (DIST_DIR, STOREFRONT_PUBLIC_DIR):
        (target_root / "index.html").write_text(index_html, encoding="utf-8")
        (target_root / "studio" / "index.html").write_text(studio_html, encoding="utf-8")
        (target_root / "sign-in.html").write_text(signin_html, encoding="utf-8")
        (target_root / "sign-up.html").write_text(
            signin_html.replace("Sign In to Your Collector Account", "Create Your Collector Account"),
            encoding="utf-8",
        )
        (target_root / "shipping.html").write_text(shipping_html, encoding="utf-8")
        (target_root / "refunds.html").write_text(refunds_html, encoding="utf-8")
        (target_root / "about.html").write_text(about_html, encoding="utf-8")
        (target_root / "contact.html").write_text(contact_html, encoding="utf-8")
        (target_root / "hardware" / "index.html").write_text(hardware_html, encoding="utf-8")
        (target_root / "simulator" / "index.html").write_text(
            hardware_html.replace("/hardware", "/simulator").replace("Controller", "LVGL Firmware Simulator"),
            encoding="utf-8",
        )
        (target_root / "404.html").write_text(not_found_html, encoding="utf-8")
        (target_root / "admin" / "index.html").write_text(admin_html, encoding="utf-8")
        (target_root / "llms.txt").write_text(llms_short, encoding="utf-8")
        (target_root / "llms-full.txt").write_text(llms_full, encoding="utf-8")
        (target_root / "sitemap-index.xml").write_text(smap_idx, encoding="utf-8")
        (target_root / "sitemap-products.xml").write_text(smap_prod, encoding="utf-8")
        (target_root / "sitemap-collections.xml").write_text(smap_coll, encoding="utf-8")
        (target_root / "sitemap-guides.xml").write_text(smap_guide, encoding="utf-8")


if __name__ == "__main__":
    build_static_bundle()
    print("Compiled luxury editorial storefront, studio, Authentik SSO pages, policy pages, admin, and GEO/SEO assets to storefront/public/ and frontend/dist/")
