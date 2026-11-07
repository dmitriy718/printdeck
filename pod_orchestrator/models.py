#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 POD Orchestrator Data Models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ShippingAddress:
    recipient_name: str
    email: str
    line1: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    line2: str = ""
    phone: str = ""

    @property
    def zip_prefix3(self) -> str:
        digits = "".join(ch for ch in self.postal_code if ch.isdigit())
        return (digits[:3] if len(digits) >= 3 else "100").zfill(3)

    @property
    def inferred_us_region(self) -> str:
        first_digit = self.zip_prefix3[0]
        if first_digit in {"0", "1", "2", "3"}:
            return "US-EAST"
        if first_digit in {"4", "5", "6"}:
            return "US-MIDWEST"
        if first_digit in {"7"}:
            return "US-SOUTH"
        return "US-WEST"


@dataclass
class OrderLineRequest:
    variant_id: str
    quantity: int
    unit_retail_price_cents: int
    print_asset_id: Optional[str] = None
    print_asset_uri: Optional[str] = None
    customization: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderQuote:
    provider: str  # 'printify' | 'printful'
    provider_label: str
    variant_id: str
    master_sku: str
    external_blueprint_id: str
    external_print_provider_id: str
    external_variant_id: str
    quantity: int
    in_stock: bool
    gross_blank_cost_cents: int
    shipping_to_zip_cents: int
    volume_tier_discount_bps: int
    volume_tier_discount_cents: int
    total_fulfillment_cost_cents: int
    gross_retail_revenue_cents: int
    net_margin_cents: int
    net_margin_pct: float
    facility_region: str
    facility_zip_prefix: str
    customer_zip_prefix: str
    regional_proximity_km_est: float
    avg_production_hours: float
    estimated_transit_hours: float
    total_delivery_hours_est: float
    quality_rating: float
    arbitrage_utility_score: float
    disqualified_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArbitrageDecision:
    order_id: str
    customer_zip: str
    customer_region: str
    selected_provider: str
    failover_provider: Optional[str]
    selected_total_fulfillment_cost_cents: int
    selected_net_margin_cents: int
    selected_delivery_hours_est: float
    margin_advantage_cents: int
    speed_advantage_hours: float
    quotes_evaluated: List[ProviderQuote]
    line_allocations: List[Dict[str, Any]]
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["quotes_evaluated"] = [q.to_dict() for q in self.quotes_evaluated]
        return data


@dataclass
class ProviderOrderResult:
    success: bool
    provider: str
    external_order_id: str
    status: str
    failover_triggered: bool = False
    primary_failure_reason: Optional[str] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
