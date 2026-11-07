"use client";

/**
 * PrintDeck (printdeck.net) — Phase 3 Answered-Forge Embedded Interactive Micro-Tools.
 * 1. Gallery Wall Golden-Ratio & Spacing Calculator (57" museum eye-level & triptych stud math)
 * 2. Instant Fit & GSM Fabric Weight Comparator (180 vs 280 vs 400 GSM DTG weave & drape calculator)
 */

import React, { useState } from "react";

export const AnsweredForgeMicroTools: React.FC = () => {
  // Micro-Tool 1: Gallery Wall Ratio & Spacing Calculator State
  const [wallWidthIn, setWallWidthIn] = useState<number>(108);
  const [sofaWidthIn, setSofaWidthIn] = useState<number>(84);
  const [panelCount, setPanelCount] = useState<number>(3);
  const [panelWidthIn, setPanelWidthIn] = useState<number>(24);
  const [panelHeightIn, setPanelHeightIn] = useState<number>(36);

  // Golden Ratio (0.618) target span over furniture
  const idealSpanIn = Math.round(sofaWidthIn * 0.618 * 10) / 10;
  const recommendedGapIn = panelCount > 1 ? 3.0 : 0;
  const totalArtworkSpanIn = panelCount * panelWidthIn + Math.max(0, panelCount - 1) * recommendedGapIn;
  const spanToSofaRatio = Math.round((totalArtworkSpanIn / Math.max(1, sofaWidthIn)) * 100);
  const eyeLevelCenterIn = 57;
  const topNailHeightIn = Math.round((eyeLevelCenterIn + panelHeightIn / 2 - 1.5) * 10) / 10;
  const leftMarginFromWallEdgeIn = Math.max(0, Math.round(((wallWidthIn - totalArtworkSpanIn) / 2) * 10) / 10);

  // Micro-Tool 2: Instant Fit & GSM Fabric Weight Comparator State
  const [selectedGsmTier, setSelectedGsmTier] = useState<180 | 280 | 400>(400);
  const [chestIn, setChestIn] = useState<number>(42);
  const [fitPreference, setFitPreference] = useState<"tailored" | "atelier_relaxed" | "boxy_drop">(
    "atelier_relaxed"
  );

  const GSM_SPECS: Record<
    180 | 280 | 400,
    {
      name: string;
      ozPerYd: string;
      weave: string;
      dtgUnderbaseRating: string;
      drapeIndex: string;
      bestFor: string;
    }
  > = {
    180: {
      name: "180 GSM Standard Combed Jersey",
      ozPerYd: "5.3 oz/yd²",
      weave: "30-Singles Fine Ring-Spun",
      dtgUnderbaseRating: "91% Opacity • Featherweight Breathable",
      drapeIndex: "Fluid / High-Drape",
      bestFor: "Layered summer studio tees",
    },
    280: {
      name: "280 GSM Heavyweight Atelier Studio Tee",
      ozPerYd: "8.2 oz/yd²",
      weave: "16-Singles Tightly Knit Supima/Combed",
      dtgUnderbaseRating: "98% Opacity • Ultra-Crisp 300-DPI Halftones",
      drapeIndex: "Architectural Boxy Structure",
      bestFor: "Gallery-grade graphic tees (PD-TEE-SUPIMA)",
    },
    400: {
      name: "400 GSM Luxury Brushed 3-End Fleece",
      ozPerYd: "11.8 oz/yd²",
      weave: "Cross-Grain Ring-Spun Face + Zero-Torque Fleece",
      dtgUnderbaseRating: "99.4% Opacity • Zero White-Underbase Halo",
      drapeIndex: "Heavy Sculptural Silhouette",
      bestFor: "Atelier Heavyweight Hoodie (PD-HOODIE-HEAVY)",
    },
  };

  const computeRecommendedSize = (): string => {
    const ease = fitPreference === "boxy_drop" ? 6 : fitPreference === "atelier_relaxed" ? 3 : 0;
    const targetChest = chestIn + ease;
    if (targetChest <= 39) return "S (20.5\" Pit-to-Pit)";
    if (targetChest <= 43) return "M (22.5\" Pit-to-Pit)";
    if (targetChest <= 47) return "L (24.0\" Pit-to-Pit)";
    return "XL (26.0\" Pit-to-Pit)";
  };

  const activeGsm = GSM_SPECS[selectedGsmTier];

  return (
    <section
      id="answered-forge-micro-tools"
      className="micro-tools-section"
      aria-label="Answered-Forge Interactive Print & Sizing Calculators"
    >
      {/* Tool 1: Gallery Wall Ratio & Spacing Calculator */}
      <article className="micro-tool-card" id="gallery-wall-calculator">
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--foundry-brass)",
            letterSpacing: "0.08em",
          }}
        >
          ANSWERED-FORGE MICRO-TOOL 01 • ARCHITECTURAL HANGING GEOMETRY
        </div>
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.55rem",
            fontWeight: 400,
            margin: "0.35rem 0 0.75rem",
          }}
        >
          Gallery Wall Golden-Ratio & 57&quot; Centerline Calculator
        </h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "0.75rem",
            marginBottom: "1rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
          }}
        >
          <label>
            Wall Width (in): <strong>{wallWidthIn}&quot;</strong>
            <input
              type="range"
              min={60}
              max={180}
              value={wallWidthIn}
              onChange={(e) => setWallWidthIn(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </label>
          <label>
            Sofa / Credenza Width (in): <strong>{sofaWidthIn}&quot;</strong>
            <input
              type="range"
              min={48}
              max={120}
              value={sofaWidthIn}
              onChange={(e) => setSofaWidthIn(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </label>
          <label>
            Canvas Panels: <strong>{panelCount}</strong>
            <input
              type="range"
              min={1}
              max={4}
              value={panelCount}
              onChange={(e) => setPanelCount(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </label>
          <label>
            Panel Size: <strong>{panelWidthIn}&quot;×{panelHeightIn}&quot;</strong>
            <select
              value={`${panelWidthIn}x${panelHeightIn}`}
              onChange={(e) => {
                const [pw, ph] = e.target.value.split("x").map(Number);
                setPanelWidthIn(pw);
                setPanelHeightIn(ph);
              }}
              style={{
                width: "100%",
                padding: "0.35rem",
                background: "#0b0c0e",
                color: "#f5f2eb",
                border: "1px solid var(--foundry-hairline)",
              }}
            >
              <option value="24x36">24&quot;×36&quot; Museum Canvas (7200×10800 px)</option>
              <option value="18x24">18&quot;×24&quot; Framed Giclée (5400×7200 px)</option>
            </select>
          </label>
        </div>

        <div
          style={{
            padding: "1rem",
            background: "#0b0c0e",
            border: "1px solid var(--foundry-hairline)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.76rem",
            lineHeight: 1.65,
          }}
        >
          <div>
            • <strong>Total Gallery Span:</strong> {totalArtworkSpanIn}&quot; ({spanToSofaRatio}% of{" "}
            {sofaWidthIn}&quot; furniture; Golden Ratio 61.8% target = {idealSpanIn}&quot;)
          </div>
          <div>
            • <strong>57&quot; Museum Anchor Height:</strong> Place top D-ring hook at{" "}
            <span style={{ color: "var(--foundry-brass)" }}>{topNailHeightIn}&quot; from floor</span>
          </div>
          <div>
            • <strong>Left / Right Wall Margin:</strong> {leftMarginFromWallEdgeIn}&quot; from corner
            • <strong>Inter-Panel Gap:</strong> {recommendedGapIn}&quot;
          </div>
        </div>
      </article>

      {/* Tool 2: Instant Fit & GSM Fabric Weight Comparator */}
      <article className="micro-tool-card" id="gsm-fabric-comparator">
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--foundry-brass)",
            letterSpacing: "0.08em",
          }}
        >
          ANSWERED-FORGE MICRO-TOOL 02 • TEXTILE METALLURGY & FIT
        </div>
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.55rem",
            fontWeight: 400,
            margin: "0.35rem 0 0.75rem",
          }}
        >
          Instant Fit & GSM Fabric Weight Comparator
        </h3>

        <div className="foundry-pill-group" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          {([180, 280, 400] as const).map((gsm) => (
            <button
              key={gsm}
              type="button"
              className={`foundry-pill ${selectedGsmTier === gsm ? "is-active" : ""}`}
              onClick={() => setSelectedGsmTier(gsm)}
            >
              {gsm} GSM ({GSM_SPECS[gsm].ozPerYd})
            </button>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "0.75rem",
            margin: "0.9rem 0",
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
          }}
        >
          <label>
            Chest Measure: <strong>{chestIn}&quot;</strong>
            <input
              type="range"
              min={34}
              max={52}
              value={chestIn}
              onChange={(e) => setChestIn(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </label>
          <label>
            Drape Cut:
            <select
              value={fitPreference}
              onChange={(e) =>
                setFitPreference(e.target.value as "tailored" | "atelier_relaxed" | "boxy_drop")
              }
              style={{
                width: "100%",
                padding: "0.35rem",
                background: "#0b0c0e",
                color: "#f5f2eb",
                border: "1px solid var(--foundry-hairline)",
              }}
            >
              <option value="tailored">Tailored Studio Fit</option>
              <option value="atelier_relaxed">Atelier Relaxed (+3&quot; ease)</option>
              <option value="boxy_drop">Boxy Drop-Shoulder (+6&quot; ease)</option>
            </select>
          </label>
        </div>

        <div
          style={{
            padding: "1rem",
            background: "#0b0c0e",
            border: "1px solid var(--foundry-hairline)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.76rem",
            lineHeight: 1.65,
          }}
        >
          <div>
            • <strong>Spec:</strong> {activeGsm.name} — {activeGsm.weave}
          </div>
          <div>
            • <strong>300-DPI DTG Ink Adhesion:</strong> {activeGsm.dtgUnderbaseRating}
          </div>
          <div>
            • <strong>Recommended PrintDeck Size:</strong>{" "}
            <span style={{ color: "var(--foundry-emerald)" }}>{computeRecommendedSize()}</span>
          </div>
        </div>
      </article>
    </section>
  );
};
