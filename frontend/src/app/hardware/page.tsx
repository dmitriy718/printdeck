import React from "react";

/**
 * Protected Legacy Hardware Coexistence Route (`/hardware`).
 * Preserves all existing PrintDeck Bambu Lab 4.3" ESP32-P4 Touchscreen Controller,
 * $19 Maker Pack, and $50 Beta Hardware Deposit offers for A1 CheckoutProber.
 */
export default function LegacyHardwarePage() {
  return (
    <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "3rem 2rem" }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--foundry-brass)" }}>
        PROTECTED HARDWARE COEXISTENCE ROUTE • /HARDWARE
      </div>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "2.6rem", fontWeight: 400, margin: "0.5rem 0 1rem" }}>
        PrintDeck Bambu Lab 4.3&quot; ESP32-P4 Touchscreen Controller
      </h1>
      <p style={{ color: "var(--atelier-parchment)", maxWidth: "740px", marginBottom: "2rem" }}>
        Direct LAN MQTT + Bambu Cloud telemetry controller with 4.3-inch IPS capacitive touch,
        multi-printer fleet switching, and AMS filament spool management.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        <article className="micro-tool-card" id="HW-BAMBU-43-CTRL">
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-emerald)" }}>
            SKU: HW-BAMBU-43-CTRL
          </div>
          <h2 style={{ fontSize: "1.25rem", margin: "0.4rem 0" }}>
            Assembled 4.3&quot; ESP32-P4 Touchscreen Controller
          </h2>
          <p style={{ fontSize: "0.86rem", color: "#9ca3af", marginBottom: "1rem" }}>
            Complete plug-and-play CNC/injection bezel + flashed ESP32-P4 IPS controller.
          </p>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.35rem", fontWeight: 700 }}>$129.00 USD</div>
        </article>

        <article className="micro-tool-card" id="HW-MAKER-PACK-19">
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-brass)" }}>
            SKU: HW-MAKER-PACK-19
          </div>
          <h2 style={{ fontSize: "1.25rem", margin: "0.4rem 0" }}>
            $19 Maker Pack (STL Enclosures + Firmware License)
          </h2>
          <p style={{ fontSize: "0.86rem", color: "#9ca3af", marginBottom: "1rem" }}>
            Printable 3MF/STL enclosure pack, BOM, and personal ESP32-P4 firmware license key.
          </p>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.35rem", fontWeight: 700 }}>$19.00 USD</div>
        </article>

        <article className="micro-tool-card" id="HW-BETA-DEPOSIT-50">
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-vermilion)" }}>
            SKU: HW-BETA-DEPOSIT-50
          </div>
          <h2 style={{ fontSize: "1.25rem", margin: "0.4rem 0" }}>
            $50 Beta Hardware Batch Reservation Deposit
          </h2>
          <p style={{ fontSize: "0.86rem", color: "#9ca3af", marginBottom: "1rem" }}>
            Fully refundable priority Batch #1 reservation via para-paygate.service (:8790).
          </p>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.35rem", fontWeight: 700 }}>$50.00 USD</div>
        </article>
      </div>
    </main>
  );
}
