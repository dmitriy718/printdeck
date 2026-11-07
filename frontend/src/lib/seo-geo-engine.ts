/**
 * PrintDeck (printdeck.net) — Phase 3 TypeScript SEO & Generative Engine Optimization (GEO)
 * Metadata & Schema.org JSON-LD Builder for Next.js App Router pages.
 */

import type { PrintDeckProduct } from "../types/catalog";

export const SITE_ORIGIN = "https://printdeck.net";

export function generateProductJsonLd(product: PrintDeckProduct): Record<string, unknown> {
  const prices =
    product.variants.length > 0
      ? product.variants.map((v) => v.retail_price_cents / 100)
      : [product.base_retail_price_cents / 100];
  const lowPrice = Math.min(...prices).toFixed(2);
  const highPrice = Math.max(...prices).toFixed(2);
  const isHardware = product.is_legacy_hardware;
  const canonicalUrl = isHardware
    ? `${SITE_ORIGIN}/hardware#${product.master_sku}`
    : `${SITE_ORIGIN}/products/${product.slug}`;

  const reqWidthPx = Math.round(product.print_area_width_in * product.required_dpi);
  const reqHeightPx = Math.round(product.print_area_height_in * product.required_dpi);

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Brand",
        "@id": `${SITE_ORIGIN}/#brand`,
        name: "PrintDeck",
        url: SITE_ORIGIN,
        slogan: "Tactile Atelier & 300-DPI Precision Print Foundry",
      },
      {
        "@type": "MerchantReturnPolicy",
        "@id": `${SITE_ORIGIN}/#return-policy`,
        applicableCountry: "US",
        returnPolicyCategory: "https://schema.org/MerchantReturnFiniteReturnWindow",
        merchantReturnDays: 30,
        returnMethod: "https://schema.org/ReturnByMail",
        returnFees: "https://schema.org/FreeReturn",
      },
      {
        "@type": "OfferShippingDetails",
        "@id": `${SITE_ORIGIN}/#shipping-details`,
        shippingRate: {
          "@type": "MonetaryAmount",
          value: parseFloat(lowPrice) >= 120 ? "0.00" : "6.99",
          currency: "USD",
        },
        shippingDestination: {
          "@type": "DefinedRegion",
          addressCountry: "US",
        },
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${canonicalUrl}#breadcrumbs`,
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "PrintDeck Atelier", item: SITE_ORIGIN },
          {
            "@type": "ListItem",
            position: 2,
            name: product.vertical.replace(/_/g, " "),
            item: `${SITE_ORIGIN}/collections/${product.vertical}`,
          },
          { "@type": "ListItem", position: 3, name: product.title, item: canonicalUrl },
        ],
      },
      {
        "@type": "Product",
        "@id": `${canonicalUrl}#product`,
        name: product.title,
        sku: product.master_sku,
        mpn: product.master_sku,
        description: product.description,
        url: canonicalUrl,
        brand: { "@id": `${SITE_ORIGIN}/#brand` },
        additionalProperty: [
          {
            "@type": "PropertyValue",
            name: "300-DPI Master Geometry",
            value: reqWidthPx > 0 ? `${reqWidthPx}x${reqHeightPx} px` : "ESP32-P4 Hardware",
          },
          {
            "@type": "PropertyValue",
            name: "Editable Grace Hold Window",
            value: "120 Minutes Post-Checkout (PAID_GRACE_HOLD)",
          },
        ],
        offers: {
          "@type": "AggregateOffer",
          lowPrice,
          highPrice,
          priceCurrency: "USD",
          offerCount: Math.max(1, product.variants.length),
          availability: "https://schema.org/InStock",
          offers: product.variants.map((v) => ({
            "@type": "Offer",
            sku: v.variant_sku,
            price: (v.retail_price_cents / 100).toFixed(2),
            priceCurrency: "USD",
            availability: "https://schema.org/InStock",
            hasMerchantReturnPolicy: { "@id": `${SITE_ORIGIN}/#return-policy` },
            shippingDetails: { "@id": `${SITE_ORIGIN}/#shipping-details` },
          })),
        },
      },
      {
        "@type": "FAQPage",
        "@id": `${canonicalUrl}#faq`,
        mainEntity: [
          {
            "@type": "Question",
            name: `How does PrintDeck verify 300-DPI print quality for ${product.title}?`,
            acceptedAnswer: {
              "@type": "Answer",
              text: `Every ${product.master_sku} artwork file is inspected by PrintDeck's automated 300-DPI Pre-Flight Pipeline (${reqWidthPx}x${reqHeightPx} px), soft-proofed to print-safe sRGB IEC61966-2.1, and upscaled via Real-ESRGAN / ComfyUI Flux when needed.`,
            },
          },
        ],
      },
    ],
  };
}
