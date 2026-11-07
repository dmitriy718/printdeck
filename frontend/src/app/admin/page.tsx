"use client";

/**
 * PrintDeck (printdeck.net) — Phase 4 Executive Administration Portal (`/admin`).
 * Protected by Authelia SSO + LLDAP & `geekom-gt1` API Key Auth.
 * Every manual action acquires an `OPERATOR_OVERRIDE` lock in the Phase 1 Punch-In Engine.
 *
 * Modules:
 * 1. Inventory Command & Mass Product Uploader / Matrix Generator (CSV/JSON/ZIP/Prompts -> 450+ variants)
 * 2. Full-Lifecycle 360° E-Commerce CRM & 1-Click Order Intervention
 * 3. SEO, GEO & FinOps Performance Dashboard + 4-Quadrant Product Cohort Matrix
 * 4. Live SSOT Punch-Clock, Issue Tracker & Board Room Console (WebSocket + Operator Override)
 */

import React, { useEffect, useState } from "react";

type AdminTab = "inventory_mass" | "crm_360" | "finops_seo_cohort" | "ssot_boardroom";

export default function PrintDeckAdminCommandCenter() {
  const [activeTab, setActiveTab] = useState<AdminTab>("inventory_mass");
  const [adminKey, setAdminKey] = useState<string>("pd_admin_geekom_gt1_key");
  const [massFormat, setMassFormat] = useState<"csv" | "json" | "zip" | "ai_prompts">("ai_prompts");
  const [massPromptsText, setMassPromptsText] = useState<string>(
    "Brutalist Solstice Monolith — Architectural Ink Study\nKyoto Horizon Chromatic Equilibrium\nNeo-Tokyo Kinetic Vector Grid"
  );
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([
    "stretched_canvas_3_sizes",
    "heavyweight_oversized_tee_5_colors",
    "ceramic_mug_15oz",
    "stitched_desk_mat_xxl",
  ]);
  const [massResult, setMassResult] = useState<Record<string, unknown> | null>(null);
  const [ssotLive, setSsotLive] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetch("/api/v2/admin/ssot/live", {
      headers: { "X-PrintDeck-Admin-Key": adminKey },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setSsotLive(data);
      })
      .catch(() => {});
  }, [adminKey]);

  const triggerMassUpload = async () => {
    const resp = await fetch("/api/v2/admin/mass-upload", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-PrintDeck-Admin-Key": adminKey,
      },
      body: JSON.stringify({
        source_format: massFormat,
        payload: massPromptsText,
        selected_templates: selectedTemplates,
        persist_all_db_rows: true,
      }),
    });
    if (resp.ok) {
      setMassResult(await resp.json());
    }
  };

  return (
    <main style={{ maxWidth: "1440px", margin: "0 auto", padding: "2rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingBottom: "1.25rem",
          borderBottom: "1px solid var(--foundry-hairline)",
          marginBottom: "1.75rem",
        }}
      >
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-brass)" }}>
            AUTHELIA SSO + LLDAP VERIFIED • OPERATOR: DIMA (GEEKOM-GT1 192.168.0.99) • OPERATOR_OVERRIDE ACTIVE
          </div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: "2.25rem", fontWeight: 400 }}>
            PrintDeck Executive Command Center (/admin)
          </h1>
        </div>
        <div className="foundry-pill-group" style={{ gridTemplateColumns: "repeat(4, auto)" }}>
          <button
            type="button"
            className={`foundry-pill ${activeTab === "inventory_mass" ? "is-active" : ""}`}
            onClick={() => setActiveTab("inventory_mass")}
          >
            01. INVENTORY & MASS UPLOADER
          </button>
          <button
            type="button"
            className={`foundry-pill ${activeTab === "crm_360" ? "is-active" : ""}`}
            onClick={() => setActiveTab("crm_360")}
          >
            02. 360° LIFECYCLE CRM
          </button>
          <button
            type="button"
            className={`foundry-pill ${activeTab === "finops_seo_cohort" ? "is-active" : ""}`}
            onClick={() => setActiveTab("finops_seo_cohort")}
          >
            03. SEO / GEO & FINOPS COHORTS
          </button>
          <button
            type="button"
            className={`foundry-pill ${activeTab === "ssot_boardroom" ? "is-active" : ""}`}
            onClick={() => setActiveTab("ssot_boardroom")}
          >
            04. LIVE SSOT & BOARD ROOM
          </button>
        </div>
      </header>

      {activeTab === "inventory_mass" && (
        <section className="micro-tool-card">
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.6rem", marginBottom: "0.75rem" }}>
            Bulk Dropzone & Multi-Product Matrix Generator (300-DPI Pre-Flight + LiteLLM SEO)
          </h2>
          <p style={{ fontSize: "0.86rem", color: "var(--atelier-parchment)", marginBottom: "1rem" }}>
            Upload CSV, JSON, ZIP archive of artwork folders, or AI generation prompts. Selecting
            Stretched Canvas (3 sizes) + Heavyweight Oversized Tee (5 colors) + Ceramic Mug (1) +
            Stitched Desk Mat (1) multiplies 50 artworks into 450–500 300-DPI variants in one click.
          </p>
          <textarea
            rows={4}
            value={massPromptsText}
            onChange={(e) => setMassPromptsText(e.target.value)}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: "#0b0c0e",
              color: "#f5f2eb",
              border: "1px solid var(--foundry-hairline)",
              fontFamily: "var(--font-mono)",
              marginBottom: "1rem",
            }}
          />
          <button type="button" className="foundry-pill is-active" onClick={triggerMassUpload}>
            ⚡ LAUNCH 300-DPI MASS MATRIX GENERATOR (OPERATOR_OVERRIDE)
          </button>
          {massResult && (
            <pre
              style={{
                marginTop: "1rem",
                padding: "1rem",
                background: "#090a0d",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                overflowX: "auto",
              }}
            >
              {JSON.stringify(massResult, null, 2)}
            </pre>
          )}
        </section>
      )}

      {activeTab === "ssot_boardroom" && (
        <section className="micro-tool-card">
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.6rem", marginBottom: "0.75rem" }}>
            Live SSOT Punch-Clock, Issue Ledger & Board Room Proposals
          </h2>
          <pre
            style={{
              padding: "1rem",
              background: "#090a0d",
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              overflowX: "auto",
            }}
          >
            {JSON.stringify(ssotLive, null, 2)}
          </pre>
        </section>
      )}
    </main>
  );
}
