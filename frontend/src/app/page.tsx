"use client";

import React, { useState } from "react";
import { AnsweredForgeMicroTools } from "../components/AnsweredForgeMicroTools";
import { InstantCartDrawer } from "../components/InstantCartDrawer";
import { SpatialMockupStudio } from "../components/SpatialMockupStudio";
import { generateProductJsonLd } from "../lib/seo-geo-engine";
import type { CartLineItem, PrintDeckProduct } from "../types/catalog";

const INITIAL_ATELIER_CATALOG: PrintDeckProduct[] = [
  {
    product_id: "prod_canvas_24x36",
    master_sku: "PD-CANVAS-24X36",
    slug: "museum-gallery-wrap-canvas-24x36",
    title: "24\"×36\" Museum Gallery-Wrap Fine Art Canvas Painting",
    description:
      "Archival poly-cotton artist canvas stretched over 1.5\" kiln-dried pine stretcher bars with mirrored gallery-wrap bleed.",
    vertical: "canvas_painting",
    print_area_width_in: 24,
    print_area_height_in: 36,
    required_dpi: 300,
    bleed_margin_in: 1.5,
    requires_transparent_alpha: false,
    gallery_wrap_bleed: true,
    base_retail_price_cents: 14900,
    is_legacy_hardware: false,
    variants: [
      {
        variant_id: "var_canvas_24x36_wrap",
        variant_sku: "PD-CANVAS-24X36-WRAP",
        size_code: "24x36",
        color_name: "Archival White",
        color_hex: "#FFFFFF",
        retail_price_cents: 14900,
      },
    ],
  },
  {
    product_id: "prod_hoodie_heavy",
    master_sku: "PD-HOODIE-HEAVY",
    slug: "heavyweight-atelier-art-hoodie",
    title: "PrintDeck Heavyweight 400GSM Atelier Graphic Hoodie",
    description:
      "Ring-spun combed cotton fleece hoodie with 300-DPI zero-halo DTG center chest & back fine art print.",
    vertical: "dtg_apparel",
    print_area_width_in: 12,
    print_area_height_in: 16,
    required_dpi: 300,
    bleed_margin_in: 0.25,
    requires_transparent_alpha: true,
    gallery_wrap_bleed: false,
    base_retail_price_cents: 6800,
    is_legacy_hardware: false,
    variants: [
      {
        variant_id: "var_hoodie_blk_l",
        variant_sku: "PD-HOODIE-HEAVY-BLK-L",
        size_code: "L",
        color_name: "Obsidian Black",
        color_hex: "#0B0B0B",
        retail_price_cents: 6800,
      },
    ],
  },
  {
    product_id: "prod_deskmat_xxl",
    master_sku: "PD-DESKMAT-XXL",
    slug: "xxl-architect-stitched-desk-mat",
    title: "XXL 31.5\"×15.5\" Stitched-Edge Studio Desk Mat",
    description:
      "4mm thick non-slip rubber base with micro-woven 300-DPI high-definition optical surface.",
    vertical: "desk_mat",
    print_area_width_in: 31.5,
    print_area_height_in: 15.5,
    required_dpi: 300,
    bleed_margin_in: 0.25,
    requires_transparent_alpha: false,
    gallery_wrap_bleed: false,
    base_retail_price_cents: 3900,
    is_legacy_hardware: false,
    variants: [
      {
        variant_id: "var_deskmat_xxl_std",
        variant_sku: "PD-DESKMAT-XXL-31X15",
        size_code: "31.5x15.5",
        color_name: "Obsidian Trim",
        color_hex: "#0F0F0F",
        retail_price_cents: 3900,
      },
    ],
  },
];

export default function PrintDeckStorefrontPage() {
  const [cartItems, setCartItems] = useState<CartLineItem[]>([
    {
      variant_id: "var_canvas_24x36_wrap",
      variant_sku: "PD-CANVAS-24X36-WRAP",
      master_sku: "PD-CANVAS-24X36",
      title: "24\"×36\" Museum Gallery-Wrap Fine Art Canvas Painting",
      unit_price_cents: 14900,
      quantity: 1,
      customSummary: "Modern Concrete Loft • 1.5\" Mirrored Gallery Bleed",
    },
  ]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);

  const handleAddToCart = (item: CartLineItem) => {
    setCartItems((prev) => {
      const existing = prev.find((p) => p.variant_id === item.variant_id);
      if (existing) {
        return prev.map((p) =>
          p.variant_id === item.variant_id ? { ...p, quantity: p.quantity + item.quantity } : p
        );
      }
      return [...prev, item];
    });
    setIsCartOpen(true);
  };

  const jsonLdPayload = generateProductJsonLd(INITIAL_ATELIER_CATALOG[0]);

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdPayload) }}
      />

      <header className="atelier-header">
        <a href="/" className="brand-mark">
          <span className="brand-mark__title">PrintDeck</span>
          <span className="brand-mark__badge">ATELIER & 300-DPI FOUNDRY</span>
        </a>
        <nav style={{ display: "flex", gap: "1.5rem", alignItems: "center", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
          <a href="#spatial-mockup-studio" style={{ color: "var(--atelier-alabaster)", textDecoration: "none" }}>
            SPATIAL STUDIO
          </a>
          <a href="#answered-forge-micro-tools" style={{ color: "var(--atelier-alabaster)", textDecoration: "none" }}>
            CALCULATORS
          </a>
          <a href="/hardware" style={{ color: "var(--foundry-brass)", textDecoration: "none" }}>
            BAMBU 4.3&quot; HARDWARE
          </a>
          <a href="/llms.txt" style={{ color: "#9ca3af", textDecoration: "none" }}>
            /LLMS.TXT
          </a>
          <button
            type="button"
            className="foundry-pill is-active"
            onClick={() => setIsCartOpen(true)}
          >
            CART ({cartItems.reduce((s, i) => s + i.quantity, 0)})
          </button>
        </nav>
      </header>

      <SpatialMockupStudio
        products={INITIAL_ATELIER_CATALOG}
        initialProductSku="PD-CANVAS-24X36"
        onAddToCart={handleAddToCart}
      />

      <AnsweredForgeMicroTools />

      <InstantCartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        items={cartItems}
        onAddCrossSell={handleAddToCart}
        onRemoveItem={(vid) => setCartItems((prev) => prev.filter((i) => i.variant_id !== vid))}
      />
    </main>
  );
}
