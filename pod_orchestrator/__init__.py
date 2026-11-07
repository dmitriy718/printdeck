"""
PrintDeck (printdeck.net) — Phase 2 Dual-Provider POD Orchestrator Package.
Unifies Printify API v1 and Printful API v2 behind a real-time Smart Arbitrage Router.
"""

from .arbitrage_router import ArbitrageNoStockError, SmartArbitrageRouter
from .catalog_mapper import UnifiedCatalogMapper
from .models import (
    ArbitrageDecision,
    OrderLineRequest,
    ProviderOrderResult,
    ProviderQuote,
    ShippingAddress,
)
from .printful_client import PrintfulQueueError, PrintfulV2Client
from .printify_client import PrintifyClient, PrintifyQueueError
from .rate_limiter import AdaptiveRateLimiter, RateLimitExhaustedError

__all__ = [
    "AdaptiveRateLimiter",
    "ArbitrageDecision",
    "ArbitrageNoStockError",
    "OrderLineRequest",
    "PrintfulQueueError",
    "PrintfulV2Client",
    "PrintifyClient",
    "PrintifyQueueError",
    "ProviderOrderResult",
    "ProviderQuote",
    "RateLimitExhaustedError",
    "ShippingAddress",
    "SmartArbitrageRouter",
    "UnifiedCatalogMapper",
]
