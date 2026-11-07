import React from "react";
import "../styles/atelier-foundry.css";

export const metadata = {
  title: "PrintDeck (printdeck.net) — Tactile Atelier & 300-DPI Precision Print Foundry",
  description:
    "Museum-grade 300-DPI custom fine art canvas paintings, 400GSM zero-halo DTG streetwear, XXL architect desk mats, and interactive Spatial Mockup Studio.",
  alternates: {
    canonical: "https://printdeck.net",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="alternate" type="text/markdown" href="/llms.txt" title="AI Shopping Catalog" />
        <link
          rel="alternate"
          type="text/markdown"
          href="/llms-full.txt"
          title="Full AI Shopping Specification"
        />
      </head>
      <body>
        <div className="provenance-ribbon">
          <div>
            <span className="provenance-pulse" />
            PRINTED TO ORDER AT 300 DPI • ARCHIVAL PIGMENT INKS • AUTOMATIC REGIONAL FULFILLMENT NEAR YOUR ZIP
          </div>
          <div>120-MINUTE EDITABLE GRACE HOLD • STRIPE / PARA-PAYGATE (:8790)</div>
        </div>
        {children}
      </body>
    </html>
  );
}
