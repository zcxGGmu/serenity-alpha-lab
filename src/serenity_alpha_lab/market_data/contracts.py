"""Provider-neutral market data contracts.

These contracts intentionally avoid importing live provider SDKs. Provider
adapters can implement the small methods here while Serenity keeps normalized
outputs, fallback diagnostics, and research-only boundaries under its own
package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence


@dataclass(frozen=True)
class MarketSymbol:
    raw_code: str
    canonical_code: str
    provider_code: str
    market: str
    exchange: str
    currency: str


@dataclass(frozen=True)
class MarketDataProviderConfig:
    name: str
    priority: int = 99
    supported_markets: tuple[str, ...] = ("cn",)
    requires_credentials: bool = False
    credential_env: Optional[str] = None
    timeout_seconds: Optional[float] = None


@dataclass
class RealtimeQuote:
    code: str
    name: str = ""
    source: str = "unknown"
    fetched_at: Optional[str] = None
    provider_timestamp: Optional[str] = None
    is_stale: Optional[bool] = None
    stale_seconds: Optional[int] = None
    fallback_from: Optional[str] = None
    market: Optional[str] = None
    currency: Optional[str] = None
    data_quality: Optional[str] = None
    missing_fields: list[str] = field(default_factory=list)
    price: Optional[float] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None
    volume: Optional[int] = None
    amount: Optional[float] = None
    volume_ratio: Optional[float] = None
    turnover_rate: Optional[float] = None
    amplitude: Optional[float] = None
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None
    change_60d: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None

    def has_basic_data(self) -> bool:
        return self.price is not None and self.price > 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "name": self.name,
            "source": self.source,
            "missing_fields": list(self.missing_fields),
        }
        for field_name in (
            "fetched_at",
            "provider_timestamp",
            "is_stale",
            "stale_seconds",
            "fallback_from",
            "market",
            "currency",
            "data_quality",
            "price",
            "change_pct",
            "change_amount",
            "volume",
            "amount",
            "volume_ratio",
            "turnover_rate",
            "amplitude",
            "open_price",
            "high",
            "low",
            "pre_close",
            "pe_ratio",
            "pb_ratio",
            "total_mv",
            "circ_mv",
            "change_60d",
            "high_52w",
            "low_52w",
        ):
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result


@dataclass(frozen=True)
class DailyBar:
    code: str
    date: str
    source: str
    market: str
    currency: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    amount: Optional[float] = None
    pct_chg: Optional[float] = None


@dataclass(frozen=True)
class ProviderAttemptDiagnostic:
    provider: str
    status: str
    duration_ms: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    fallback_to: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "status": self.status,
            "duration_ms": self.duration_ms,
        }
        if self.error_type:
            payload["error_type"] = self.error_type
        if self.error_message:
            payload["error_message"] = self.error_message
        if self.fallback_to:
            payload["fallback_to"] = self.fallback_to
        return payload


@dataclass(frozen=True)
class ProviderDiagnostics:
    symbol: str
    market: str
    status: str
    attempts: list[ProviderAttemptDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market": self.market,
            "status": self.status,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


@dataclass(frozen=True)
class ProviderFetchResult:
    quote: Optional[RealtimeQuote]
    diagnostics: ProviderDiagnostics


class MarketDataProvider:
    """Base contract for Serenity market data providers."""

    def __init__(self, config: MarketDataProviderConfig) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def priority(self) -> int:
        return self.config.priority

    def supports_market(self, market: str) -> bool:
        supported = {item.lower() for item in self.config.supported_markets}
        return "*" in supported or market.lower() in supported

    def credentials_available(self, environ: Mapping[str, str] | None = None) -> bool:
        if not self.config.requires_credentials:
            return True
        if not self.config.credential_env:
            return False
        source = os.environ if environ is None else environ
        return bool(source.get(self.config.credential_env))

    def fetch_realtime_quote(
        self,
        symbol: MarketSymbol,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> Any:
        raise NotImplementedError

    def fetch_daily_bars(
        self,
        symbol: MarketSymbol,
        *,
        days: int = 30,
        timeout_seconds: Optional[float] = None,
    ) -> Sequence[Any]:
        raise NotImplementedError
