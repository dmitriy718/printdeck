import React from "react";

/**
 * Protected Legacy Hardware Simulator Route (`/simulator`).
 * Preserves interactive Bambu Lab 4.3" ESP32-P4 UI preview alongside the Phase 3 POD storefront.
 */
export default function HardwareSimulatorPage() {
  return (
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "3rem 2rem" }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--foundry-brass)" }}>
        PROTECTED ROUTE • /SIMULATOR • ESP32-P4 FIRMWARE UI
      </div>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "2.3rem", fontWeight: 400, margin: "0.5rem 0 1rem" }}>
        PrintDeck 4.3&quot; IPS Touchscreen Firmware Simulator
      </h1>
      <p style={{ color: "var(--atelier-parchment)", marginBottom: "1.5rem" }}>
        Interactive 800×480 LVGL touchscreen telemetry simulator for Bambu Lab X1C / P1S / A1 series.
      </p>
      <div
        style={{
          width: "800px",
          maxWidth: "100%",
          aspectRatio: "5 / 3",
          background: "#090b0f",
          border: "2px solid var(--foundry-brass)",
          padding: "1.5rem",
          fontFamily: "var(--font-mono)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--foundry-emerald)" }}>
          <span>● BAMBU P1S-01 ONLINE (LAN MQTT)</span>
          <span>NOZZLE: 220°C / BED: 60°C • CHAMBER: 38°C</span>
        </div>
        <div style={{ marginTop: "2rem", fontSize: "1.2rem" }}>
          ACTIVE JOB: PrintDeck_Bezel_Rev4.3mf — 78.4% Complete (00:34 remaining)
        </div>
        <div style={{ marginTop: "2rem" }}>
          <a href="/hardware" className="foundry-pill is-active" style={{ textDecoration: "none" }}>
            ← RETURN TO /HARDWARE OFFERS ($19 MAKER PACK / $50 DEPOSIT)
          </a>
        </div>
      </div>
    </main>
  );
}
