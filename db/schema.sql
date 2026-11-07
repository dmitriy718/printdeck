-- ============================================================================
-- PrintDeck (printdeck.net) — Phase 2 Production E-Commerce & POD Arbitrage Schema
-- Compatible with PostgreSQL 15+ (CodexStore :5432 on novahorizon) & SQLite 3.35+
-- Coexists non-destructively with para-paygate (paygate.sqlite) & para-intake (intake.sqlite)
-- ============================================================================

-- 1. PRODUCTS: Master SKUs (PD-*) across all POD verticals + Protected Legacy Hardware (HW-*)
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    master_sku TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    vertical TEXT NOT NULL CHECK (
        vertical IN (
            'canvas_painting',
            'framed_fine_art',
            'dtg_apparel',
            'aop_apparel',
            'headwear',
            'mug_drinkware',
            'desk_mat',
            'decal_sticker',
            'custom_memorabilia',
            'legacy_hardware'
        )
    ),
    print_area_width_in REAL NOT NULL DEFAULT 0.0,
    print_area_height_in REAL NOT NULL DEFAULT 0.0,
    required_dpi INTEGER NOT NULL DEFAULT 300,
    bleed_margin_in REAL NOT NULL DEFAULT 0.125,
    requires_transparent_alpha BOOLEAN NOT NULL DEFAULT 0,
    gallery_wrap_bleed BOOLEAN NOT NULL DEFAULT 0,
    base_retail_price_cents INTEGER NOT NULL CHECK (base_retail_price_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    is_legacy_hardware BOOLEAN NOT NULL DEFAULT 0,
    protected_route TEXT,
    trademark_verified BOOLEAN NOT NULL DEFAULT 1,
    active BOOLEAN NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_vertical ON products(vertical);
CREATE INDEX IF NOT EXISTS idx_products_master_sku ON products(master_sku);

-- 2. PRODUCT_VARIANTS: Exact Size / Color / Blank Combinations
CREATE TABLE IF NOT EXISTS product_variants (
    variant_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    variant_sku TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    size_code TEXT NOT NULL,
    color_name TEXT NOT NULL,
    color_hex TEXT NOT NULL DEFAULT '#000000',
    garment_is_dark BOOLEAN NOT NULL DEFAULT 1,
    retail_price_cents INTEGER NOT NULL CHECK (retail_price_cents >= 0),
    compare_at_price_cents INTEGER,
    weight_grams INTEGER NOT NULL DEFAULT 250,
    print_area_width_in REAL NOT NULL,
    print_area_height_in REAL NOT NULL,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON product_variants(variant_sku);

-- 3. POD_PROVIDER_MAPPINGS: Dual-Provider Blueprint & Variant Arbitrage Table (Printify + Printful v2)
CREATE TABLE IF NOT EXISTS pod_provider_mappings (
    mapping_id TEXT PRIMARY KEY,
    variant_id TEXT NOT NULL REFERENCES product_variants(variant_id) ON DELETE CASCADE,
    master_sku TEXT NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('printify', 'printful')),
    external_blueprint_id TEXT NOT NULL,
    external_print_provider_id TEXT NOT NULL,
    external_variant_id TEXT NOT NULL,
    provider_name_label TEXT NOT NULL,
    base_blank_cost_cents INTEGER NOT NULL CHECK (base_blank_cost_cents >= 0),
    base_shipping_cents INTEGER NOT NULL CHECK (base_shipping_cents >= 0),
    additional_item_shipping_cents INTEGER NOT NULL DEFAULT 200,
    volume_tier_discount_bps INTEGER NOT NULL DEFAULT 0 CHECK (volume_tier_discount_bps BETWEEN 0 AND 5000),
    facility_region TEXT NOT NULL DEFAULT 'US-EAST',
    facility_zip_prefix TEXT NOT NULL DEFAULT '282',
    facility_country TEXT NOT NULL DEFAULT 'US',
    avg_production_hours REAL NOT NULL DEFAULT 36.0,
    quality_rating REAL NOT NULL DEFAULT 4.8,
    in_stock BOOLEAN NOT NULL DEFAULT 1,
    last_stock_sync_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    priority_rank INTEGER NOT NULL DEFAULT 1,
    raw_provider_meta_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(variant_id, provider, external_print_provider_id)
);

CREATE INDEX IF NOT EXISTS idx_pod_mappings_variant ON pod_provider_mappings(variant_id);
CREATE INDEX IF NOT EXISTS idx_pod_mappings_provider ON pod_provider_mappings(provider, in_stock);

-- 4. PRINT_ASSETS: 300-DPI Pre-Flight Validated Artwork & Upscaled Masters
CREATE TABLE IF NOT EXISTS print_assets (
    asset_id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES products(product_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    original_width_px INTEGER NOT NULL,
    original_height_px INTEGER NOT NULL,
    target_width_in REAL NOT NULL,
    target_height_in REAL NOT NULL,
    required_width_px INTEGER NOT NULL,
    required_height_px INTEGER NOT NULL,
    final_width_px INTEGER NOT NULL,
    final_height_px INTEGER NOT NULL,
    effective_dpi_x REAL NOT NULL,
    effective_dpi_y REAL NOT NULL,
    upscaled BOOLEAN NOT NULL DEFAULT 0,
    upscale_node TEXT NOT NULL DEFAULT 'native',
    upscale_scale_factor REAL NOT NULL DEFAULT 1.0,
    icc_profile_name TEXT NOT NULL DEFAULT 'sRGB IEC61966-2.1',
    icc_gamut_verified BOOLEAN NOT NULL DEFAULT 1,
    out_of_gamut_pixel_ratio REAL NOT NULL DEFAULT 0.0,
    alpha_channel_sanitized BOOLEAN NOT NULL DEFAULT 0,
    semi_transparent_pixels_removed INTEGER NOT NULL DEFAULT 0,
    bleed_verified BOOLEAN NOT NULL DEFAULT 0,
    bleed_margin_px INTEGER NOT NULL DEFAULT 0,
    trademark_Passed BOOLEAN NOT NULL DEFAULT 1,
    trademark_report_json TEXT NOT NULL DEFAULT '{}',
    preflight_status TEXT NOT NULL CHECK (
        preflight_status IN ('PENDING', 'PASSED_300DPI', 'UPSCALED_300DPI', 'REJECTED_QUALITY', 'REJECTED_TRADEMARK')
    ),
    printify_upload_id TEXT,
    printful_file_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_print_assets_sha256 ON print_assets(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_print_assets_status ON print_assets(preflight_status);

-- 5. ORDERS: Customer Checkout, Stripe / para-paygate (:8790) & 120-Minute Grace Queue State
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_number TEXT NOT NULL UNIQUE,
    customer_email TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT,
    shipping_address_line1 TEXT NOT NULL,
    shipping_address_line2 TEXT DEFAULT '',
    shipping_city TEXT NOT NULL,
    shipping_state TEXT NOT NULL,
    shipping_zip TEXT NOT NULL,
    shipping_country TEXT NOT NULL DEFAULT 'US',
    payment_gateway TEXT NOT NULL CHECK (payment_gateway IN ('stripe', 'para-paygate')),
    payment_method_type TEXT NOT NULL DEFAULT 'card',
    stripe_checkout_session_id TEXT UNIQUE,
    stripe_payment_intent_id TEXT UNIQUE,
    paygate_transaction_id TEXT UNIQUE,
    status TEXT NOT NULL CHECK (
        status IN (
            'PENDING_PAYMENT',
            'PAID_GRACE_HOLD',
            'ROUTING_ARBITRAGE',
            'SENT_TO_PRODUCTION',
            'IN_PRODUCTION',
            'SHIPPED',
            'DELIVERED',
            'ON_HOLD',
            'CANCELLED',
            'REFUNDED'
        )
    ),
    subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
    shipping_cents INTEGER NOT NULL DEFAULT 0,
    discount_cents INTEGER NOT NULL DEFAULT 0,
    tax_cents INTEGER NOT NULL DEFAULT 0,
    upsell_added_cents INTEGER NOT NULL DEFAULT 0,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    selected_provider TEXT CHECK (selected_provider IN ('printify', 'printful', 'split', 'hardware_direct')),
    external_pod_order_id TEXT,
    arbitrage_decision_json TEXT NOT NULL DEFAULT '{}',
    estimated_fulfillment_cost_cents INTEGER NOT NULL DEFAULT 0,
    estimated_net_margin_cents INTEGER NOT NULL DEFAULT 0,
    tracking_number TEXT,
    tracking_url TEXT,
    carrier TEXT,
    grace_hold_expires_at TIMESTAMP,
    sent_to_production_at TIMESTAMP,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    marketing_opt_out BOOLEAN NOT NULL DEFAULT 0,
    unsubscribe_token TEXT NOT NULL,
    intake_ticket_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_status_grace ON orders(status, grace_hold_expires_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders(customer_email);
CREATE INDEX IF NOT EXISTS idx_orders_external_pod ON orders(external_pod_order_id);

-- 6. ORDER_ITEMS: Line Items, Linked Print Assets & Item-Level Arbitrage Breakdown
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    variant_id TEXT NOT NULL REFERENCES product_variants(variant_id),
    master_sku TEXT NOT NULL,
    variant_sku TEXT NOT NULL,
    title TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
    print_asset_id TEXT REFERENCES print_assets(asset_id),
    selected_provider TEXT CHECK (selected_provider IN ('printify', 'printful', 'hardware_direct')),
    external_variant_id TEXT,
    external_print_provider_id TEXT,
    provider_blank_cost_cents INTEGER NOT NULL DEFAULT 0,
    provider_shipping_share_cents INTEGER NOT NULL DEFAULT 0,
    volume_discount_cents INTEGER NOT NULL DEFAULT 0,
    line_net_margin_cents INTEGER NOT NULL DEFAULT 0,
    is_post_purchase_upsell BOOLEAN NOT NULL DEFAULT 0,
    customization_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- 7. FULFILLMENT_HOLDS: 120-Minute Editable Grace Queue & Pre-Flight / Exception Holds
CREATE TABLE IF NOT EXISTS fulfillment_holds (
    hold_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    hold_type TEXT NOT NULL CHECK (
        hold_type IN (
            'GRACE_WINDOW_120M',
            'PREFLIGHT_300DPI_WAIT',
            'ADDRESS_VERIFICATION',
            'PROVIDER_QUEUE_HOLD',
            'MANUAL_ADMIN_HOLD'
        )
    ),
    status TEXT NOT NULL CHECK (
        status IN ('ACTIVE', 'RELEASED_TO_PRODUCTION', 'FAST_TRACKED', 'CANCELLED')
    ),
    hold_reason TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    released_at TIMESTAMP,
    released_by TEXT,
    customer_edits_count INTEGER NOT NULL DEFAULT 0,
    customer_edits_log_json TEXT NOT NULL DEFAULT '[]',
    upsells_accepted_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fulfillment_holds_active ON fulfillment_holds(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_fulfillment_holds_order ON fulfillment_holds(order_id);

-- 8. WEBHOOK_EVENTS: Cryptographically Verified Idempotency Ledger (Stripe, Printify, Printful, Paygate)
CREATE TABLE IF NOT EXISTS webhook_events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('stripe', 'printify', 'printful', 'para-paygate')),
    external_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    signature_header TEXT NOT NULL,
    signature_verified BOOLEAN NOT NULL DEFAULT 0,
    payload_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    order_id TEXT REFERENCES orders(order_id) ON DELETE SET NULL,
    processing_status TEXT NOT NULL CHECK (
        processing_status IN ('PROCESSED', 'DUPLICATE_IGNORED', 'FAILED', 'REJECTED_SIGNATURE')
    ),
    processing_notes TEXT DEFAULT '',
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, external_event_id)
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_source_ext ON webhook_events(source, external_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_order ON webhook_events(order_id);

-- 9. MARKETING_OPTOUTS: RFC 8058 1-Click Unsubscribe Compliance (/pay/optout)
CREATE TABLE IF NOT EXISTS marketing_optouts (
    optout_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    unsubscribe_token TEXT NOT NULL,
    rfc8058_one_click BOOLEAN NOT NULL DEFAULT 1,
    source_order_id TEXT,
    user_agent TEXT DEFAULT '',
    opted_out_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_marketing_optouts_email ON marketing_optouts(email);

-- 10. MASS_UPLOAD_JOBS: Phase 4 Asynchronous Bulk Ingestion & Multi-Product Matrix Queue
CREATE TABLE IF NOT EXISTS mass_upload_jobs (
    job_id TEXT PRIMARY KEY,
    operator TEXT NOT NULL DEFAULT 'dima',
    source_format TEXT NOT NULL CHECK (source_format IN ('csv', 'json', 'zip', 'ai_prompts')),
    selected_templates_json TEXT NOT NULL DEFAULT '[]',
    artworks_count INTEGER NOT NULL DEFAULT 0,
    variants_per_artwork INTEGER NOT NULL DEFAULT 1,
    variants_target_count INTEGER NOT NULL DEFAULT 0,
    variants_created_count INTEGER NOT NULL DEFAULT 0,
    progress_pct REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL CHECK (status IN ('QUEUED', 'RUNNING_PREFLIGHT', 'PUBLISHING_POD', 'COMPLETED', 'FAILED')),
    litellm_model TEXT NOT NULL DEFAULT 'qwen3:14b',
    results_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. AI_CRAWLER_HITS: Phase 4 GEO / AI Search Bot Telemetry (GPTBot, ClaudeBot, PerplexityBot, Google-Extended)
CREATE TABLE IF NOT EXISTS ai_crawler_hits (
    hit_id TEXT PRIMARY KEY,
    bot_name TEXT NOT NULL,
    user_agent TEXT NOT NULL,
    request_path TEXT NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 200,
    response_ms REAL NOT NULL DEFAULT 4.2,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_crawler_hits_bot ON ai_crawler_hits(bot_name, created_at);

-- 12. BOARDROOM_PROPOSALS: Phase 4 Autonomous Strategy Proposals & Operator Override Console
CREATE TABLE IF NOT EXISTS boardroom_proposals (
    proposal_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    proposing_agent TEXT NOT NULL,
    reasoning_model TEXT NOT NULL DEFAULT 'deepseek-r1:32b',
    target_scope TEXT NOT NULL,
    rationale TEXT NOT NULL,
    expected_margin_impact_bps INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('PENDING_REVIEW', 'OPERATOR_APPROVED', 'OPERATOR_VETOED')),
    decided_by TEXT,
    decided_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 13. CUSTOMER_TRANSCRIPTS: Phase 4 360° CRM AI Concierge & Mailer Agent Conversations
CREATE TABLE IF NOT EXISTS customer_transcripts (
    transcript_id TEXT PRIMARY KEY,
    customer_email TEXT NOT NULL,
    order_id TEXT,
    channel TEXT NOT NULL CHECK (channel IN ('ai_chat_concierge', 'lifecycle_mailer', 'support_intake')),
    agent_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    messages_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_transcripts_email ON customer_transcripts(customer_email);

