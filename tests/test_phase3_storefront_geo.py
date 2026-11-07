#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 3 Storefront, Spatial Studio & SEO/GEO Verification Suite.
Verifies:
  1. Tactile Atelier & Precision Print Foundry storefront (/ and /studio), SpatialMockupStudio,
     Answered-Forge Micro-Tools, AVIF/WebP responsive srcsets, and GPU-composited Cart Drawer
  2. Coexistence of /hardware and /simulator for Bambu Lab 4.3" ESP32-P4 Touchscreen Controller
  3. Complete Schema.org JSON-LD @graph (Product, AggregateOffer, Brand, BreadcrumbList,
     MerchantReturnPolicy, OfferShippingDetails, FAQPage)
  4. Real-time /llms.txt and /llms-full.txt AI Shopping Agent endpoints
  5. Auto-split XML Sitemaps (sitemap-index.xml, sitemap-products.xml,
     sitemap-collections.xml, sitemap-guides.xml) & IndexNow batch submission
  6. novahorizon Caddyfile configuration & strict HTTP 404 Portfolio Steward compliance.
"""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from fastapi.testclient import TestClient

from app import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_storefront_spatial_studio_and_micro_tools() -> None:
    for route in ("/", "/studio"):
        resp = client.get(route)
        assert resp.status_code == 200
        html = resp.text
        assert "spatial-mockup-studio" in html
        assert "pd-spatial-canvas" in html
        assert "gallery-wall-calculator" in html
        assert "gsm-fabric-comparator" in html
        assert "image/avif" in html
        assert "image/webp" in html
        assert "Printed to order at 300 DPI" in html
        assert "application/ld+json" in html

    # Verify TypeScript components & CSS exist and include iOS GPU translate3d fix (ISS-0003)
    css_text = (PROJECT_ROOT / "frontend/src/styles/atelier-foundry.css").read_text(encoding="utf-8")
    assert "translate3d(" in css_text
    assert "backface-visibility: hidden" in css_text
    assert (PROJECT_ROOT / "frontend/src/components/SpatialMockupStudio.tsx").exists()
    assert (PROJECT_ROOT / "frontend/src/components/AnsweredForgeMicroTools.tsx").exists()
    assert (PROJECT_ROOT / "frontend/src/components/InstantCartDrawer.tsx").exists()


def test_hardware_and_simulator_coexistence() -> None:
    hw_resp = client.get("/hardware")
    assert hw_resp.status_code == 200
    hw_data = hw_resp.json()
    assert hw_data["protected_coexistence"] is True
    skus = {o["master_sku"] for o in hw_data["offers"]}
    assert {"HW-BAMBU-43-CTRL", "HW-MAKER-PACK-19", "HW-BETA-DEPOSIT-50"}.issubset(skus)

    sim_resp = client.get("/simulator")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["route"] == "/simulator"
    assert sim_data["protected_coexistence"] is True

    sim_html_resp = client.get("/simulator", headers={"Accept": "text/html"})
    assert sim_html_resp.status_code == 200
    assert "ESP32-P4" in sim_html_resp.text


def test_dynamic_json_ld_complete_schema_graph() -> None:
    resp = client.get("/api/v2/seo/json-ld/PD-CANVAS-24X36")
    assert resp.status_code == 200
    data = resp.json()
    assert data["@context"] == "https://schema.org"
    graph_types = {node["@type"] for node in data["@graph"]}
    required_types = {
        "Brand",
        "MerchantReturnPolicy",
        "OfferShippingDetails",
        "BreadcrumbList",
        "Product",
        "FAQPage",
    }
    assert required_types.issubset(graph_types)

    product_node = next(n for n in data["@graph"] if n["@type"] == "Product")
    assert product_node["sku"] == "PD-CANVAS-24X36"
    assert product_node["offers"]["@type"] == "AggregateOffer"


def test_llms_txt_and_llms_full_txt_ai_catalog_endpoints() -> None:
    r_short = client.get("/llms.txt")
    assert r_short.status_code == 200
    assert "PrintDeck (printdeck.net)" in r_short.text
    assert "PD-CANVAS-24X36" in r_short.text
    assert "PD-HOODIE-HEAVY" in r_short.text
    assert "HW-BAMBU-43-CTRL" in r_short.text

    r_full = client.get("/llms-full.txt")
    assert r_full.status_code == 200
    assert "7200×10800 px @ 300 DPI" in r_full.text
    assert "3600×4800 px @ 300 DPI" in r_full.text
    assert "POST /pay/checkout" in r_full.text
    assert "Gallery Wall Golden-Ratio" in r_full.text


def test_split_xml_sitemaps_and_indexnow_ping() -> None:
    for path in (
        "/sitemap-index.xml",
        "/sitemap-products.xml",
        "/sitemap-collections.xml",
        "/sitemap-guides.xml",
    ):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        # Validate well-formed XML
        root = ET.fromstring(resp.text)
        assert root is not None

    ping_resp = client.post("/api/v2/seo/indexnow-ping")
    assert ping_resp.status_code == 200
    ping_data = ping_resp.json()
    assert ping_data["submitted_urls_count"] >= 10
    assert "https://printdeck.net/sitemap-index.xml" in ping_data["sitemaps_pinged"]


def test_caddyfile_novahorizon_and_strict_404() -> None:
    caddyfile = (PROJECT_ROOT / "deploy/Caddyfile.novahorizon").read_text(encoding="utf-8")
    assert "encode zstd br gzip" in caddyfile
    assert "handle /hardware*" in caddyfile
    assert "handle /simulator*" in caddyfile
    assert "127.0.0.1:8790" in caddyfile
    assert "127.0.0.1:8787" in caddyfile
    assert "handle_errors" in caddyfile
    assert "/404.html" in caddyfile

    # Verify non-existent route returns strict HTTP 404 (never soft-200)
    missing = client.get("/non-existent-route-for-portfolio-steward")
    assert missing.status_code == 404
