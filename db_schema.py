#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/dima/Projects/printdeck/.ssot/printdeck.sqlite")

DDL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        retail_price_cents INTEGER NOT NULL,
        min_margin_pct REAL DEFAULT 35.0,
        status TEXT DEFAULT 'PROBATION',
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS product_variants (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        variant_sku TEXT UNIQUE NOT NULL,
        size TEXT NOT NULL,
        color TEXT NOT NULL,
        width_inches REAL NOT NULL,
        height_inches REAL NOT NULL,
        retail_price_cents INTEGER NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );""",
    """CREATE TABLE IF NOT EXISTS pod_provider_mappings (
        id TEXT PRIMARY KEY,
        variant_sku TEXT NOT NULL,
        provider TEXT NOT NULL,
        external_blueprint_id TEXT NOT NULL,
        external_variant_id TEXT NOT NULL,
        base_cost_cents INTEGER NOT NULL,
        shipping_base_cents INTEGER NOT NULL,
        in_stock INTEGER DEFAULT 1,
        avg_production_days REAL DEFAULT 2.0
    );""",
    """CREATE TABLE IF NOT EXISTS print_assets (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        source_path TEXT NOT NULL,
        upscaled_path TEXT NOT NULL,
        width_px INTEGER NOT NULL,
        height_px INTEGER NOT NULL,
        dpi INTEGER NOT NULL,
        color_profile TEXT DEFAULT 'sRGB-IEC61966-2.1',
        alpha_sanitized INTEGER DEFAULT 1,
        trademark_cleared INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        stripe_session_id TEXT UNIQUE NOT NULL,
        customer_email TEXT NOT NULL,
        shipping_zip TEXT NOT NULL,
        shipping_address_json TEXT NOT NULL,
        total_cents INTEGER NOT NULL,
        selected_provider TEXT,
        expected_margin_pct REAL,
        status TEXT NOT NULL,
        grace_expires_utc TEXT NOT NULL,
        created_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        variant_sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price_cents INTEGER NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );""",
    """CREATE TABLE IF NOT EXISTS fulfillment_holds (
        order_id TEXT PRIMARY KEY,
        hold_reason TEXT NOT NULL,
        editable_until_utc TEXT NOT NULL,
        released INTEGER DEFAULT 0,
        modifications_log_json TEXT DEFAULT '[]'
    );""",
    """CREATE TABLE IF NOT EXISTS webhook_events (
        event_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        processed_at TEXT NOT NULL
    );"""
]

def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    with conn:
        for stmt in DDL_STATEMENTS:
            conn.execute(stmt)
    return conn
