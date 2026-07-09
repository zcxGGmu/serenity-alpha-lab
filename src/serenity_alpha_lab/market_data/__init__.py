"""Serenity-owned market data provider contracts and normalization."""

from .contracts import (
    DailyBar,
    MarketDataProvider,
    MarketDataProviderConfig,
    MarketSymbol,
    ProviderAttemptDiagnostic,
    ProviderDiagnostics,
    ProviderFetchResult,
    RealtimeQuote,
)
from .manager import MarketDataManager
from .normalization import normalize_daily_bars, normalize_realtime_quote
from .symbols import normalize_market_symbol

__all__ = [
    "DailyBar",
    "MarketDataManager",
    "MarketDataProvider",
    "MarketDataProviderConfig",
    "MarketSymbol",
    "ProviderAttemptDiagnostic",
    "ProviderDiagnostics",
    "ProviderFetchResult",
    "RealtimeQuote",
    "normalize_daily_bars",
    "normalize_market_symbol",
    "normalize_realtime_quote",
]
