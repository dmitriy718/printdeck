---
name: luxury-ecommerce-cro
description: Luxury Editorial Gallery & Modern Lifestyle E-Commerce Conversion Rate Optimization (CRO) design system for PrintDeck (printdeck.net). Enforces warm architectural gallery aesthetics, zero developer/internal jargon exposure, real high-resolution product and room photography, tactile variant selectors, and Authentik SSO integration.
---

# Luxury E-Commerce & Editorial Gallery Storefront Skill (`luxury-ecommerce-cro`)

This skill governs all customer-facing frontend surfaces (`index.html`, `/studio`, `/collections/*`, `/sign-in.html`, `/sign-up.html`, and interactive components) for **PrintDeck (`printdeck.net`)**.

## 1. Non-Negotiable Storefront Rules

1. **NO Terminal or Developer Debug Aesthetics**:
   - **NEVER** use terminal/monospace aesthetics as primary body copy, dashed developer boxes, or pitch-black hacker themes (`#070809` / `#0b0c0e` voids) on customer-facing e-commerce pages.
   - Customer pages must feel like a sunlit architectural art gallery and luxury lifestyle flagship store.

2. **ZERO Internal Infrastructure, SKU, or Agent Jargon on Public Pages**:
   - **NEVER** expose internal server/cluster hostnames (`omnibook-spark`, `aidev`, `macmini-ops`, `homeserv`, `geekom-gt1`, `mbp-m5pro`, `para-paygate`, `para-intake`), internal database SKU codes (`PD-BUNDLE-QUANT-DESK-SETUP`, `PD-CANVAS-24X36`), or internal AI agent names (`Agent Aria`, `Agent Lucas`, `Agent Maya`, `Agent Damon`, `Agent Jennifer`, `Answered-Forge`) on the public storefront.
   - All internal telemetry, node statuses, and agent orchestration belong strictly inside `/admin`.

3. **Real, High-Resolution Visual Imagery (`naturalWidth > 0`) Everywhere**:
   - **EVERY** product card, bundle showcase, hero banner, and live room visualizer MUST render real, high-resolution visual imagery (`<img>` and `<canvas>` backed by verified `.webp` / `.jpg` photography assets on disk with `naturalWidth > 0`).
   - Every visual asset must include realistic multi-layered gallery drop shadows, physical frame moldings (Museum Oak, Walnut Float, Matte Black Aluminum, Gallery Stretched Canvas), tactile fabric textures, star ratings (`4.9★`), verified collector review counts, and interactive color/size/frame selectors.

4. **Editorial Gallery & Modern Lifestyle Design System**:
   - **Inspirations**: Framebridge, Saatchi Art, Aimé Leon Dore, and Kith.
   - **Color Palette**:
     - Primary Background: Gallery Alabaster (`#FAF8F5`)
     - Secondary / Card Surface: Soft Stone (`#F2EFE9`) & Warm Linen (`#EBE5DA`)
     - Primary Ink / Typography: Deep Charcoal Espresso (`#141413`)
     - Secondary Muted Ink: Warm Graphite (`#57534E`)
     - High-Converting Primary CTA: Warm Terracotta / Burnt Sienna (`#C85A32`, hover `#B04822`)
     - Luxury Accents & Badges: Champagne Gold (`#C5A059`) & Botanical Sage (`#2E6F40`)
   - **Typography**:
     - Display / Headlines: `Instrument Serif` or `Playfair Display` (editorial, authoritative, gallery-grade).
     - UI / Body / Navigation: `Plus Jakarta Sans` or `Inter` (clean geometric legibility).

5. **Conversion-Obsessed Merchandising & Authentik Customer Identity**:
   - Announcement bar with clear customer value propositions (*Free Express Shipping Over $120 • 2-Hour Easy Order Edit Guarantee*).
   - Interactive Split Hero with a working **Live Room Visualizer** (swapping real room photography for *Modern Loft*, *Executive Study*, *Coastal Living*, and *Gallery Spot*, plus real-time frame molding and size scaling).
   - Filterable Best-Sellers Catalog across Fine Art Prints, Heavyweight Apparel (280 GSM Tees & 450 GSM Hoodies), and Studio Desk & Lifestyle Goods.
   - Interactive Custom Studio Drawer/Modal allowing customers to upload or preview artwork, choose frame/apparel color, see real-time pricing, and check out in 1 click.
   - Unified **Authentik OIDC / SSO** authentication (`/auth/login`, `/auth/callback`, `/api/auth/session`, `/sign-in.html`, and account drawer) for customer order tracking, saved room mockups, and protected `/admin` access.
