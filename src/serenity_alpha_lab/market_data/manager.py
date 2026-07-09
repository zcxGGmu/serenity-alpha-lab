"""Provider fallback manager with safe diagnostics."""

from __future__ import annotations

import time
from typing import Iterable, Optional

from .contracts import (
    MarketDataProvider,
    ProviderAttemptDiagnostic,
    ProviderDiagnostics,
    ProviderFetchResult,
)
from .normalization import normalize_realtime_quote
from .symbols import normalize_market_symbol


def _safe_error_message(error_type: str) -> str:
    return f"{error_type}: provider attempt failed"


class MarketDataManager:
    """Coordinate provider routing, fallback, and normalized diagnostics."""

    def __init__(self, providers: Iterable[MarketDataProvider] = ()) -> None:
        self.providers = sorted(list(providers), key=lambda provider: provider.priority)

    def _providers_for_market(self, market: str) -> list[MarketDataProvider]:
        return [provider for provider in self.providers if provider.supports_market(market)]

    @staticmethod
    def _next_provider_name(providers: list[MarketDataProvider], index: int) -> Optional[str]:
        if index + 1 >= len(providers):
            return None
        return providers[index + 1].name

    def get_realtime_quote(
        self,
        stock_code: str,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> ProviderFetchResult:
        symbol = normalize_market_symbol(stock_code)
        candidates = self._providers_for_market(symbol.market)
        attempts: list[ProviderAttemptDiagnostic] = []
        failed_providers: list[str] = []

        if not candidates:
            diagnostics = ProviderDiagnostics(
                symbol=symbol.canonical_code,
                market=symbol.market,
                status="unavailable",
                attempts=[
                    ProviderAttemptDiagnostic(
                        provider="provider_registry",
                        status="skipped",
                        error_type="no_provider_for_market",
                        error_message="no provider available for requested market",
                    )
                ],
            )
            return ProviderFetchResult(quote=None, diagnostics=diagnostics)

        for index, provider in enumerate(candidates):
            fallback_to = self._next_provider_name(candidates, index)
            if not provider.credentials_available():
                attempts.append(
                    ProviderAttemptDiagnostic(
                        provider=provider.name,
                        status="skipped",
                        error_type="credentials_unavailable",
                        error_message="provider credentials are not configured",
                        fallback_to=fallback_to,
                    )
                )
                failed_providers.append(provider.name)
                continue

            start = time.monotonic()
            try:
                raw_quote = provider.fetch_realtime_quote(
                    symbol,
                    timeout_seconds=timeout_seconds or provider.config.timeout_seconds,
                )
            except Exception as exc:
                error_type = type(exc).__name__
                attempts.append(
                    ProviderAttemptDiagnostic(
                        provider=provider.name,
                        status="failed",
                        duration_ms=int((time.monotonic() - start) * 1000),
                        error_type=error_type,
                        error_message=_safe_error_message(error_type),
                        fallback_to=fallback_to,
                    )
                )
                failed_providers.append(provider.name)
                continue

            quote = normalize_realtime_quote(
                raw_quote or {},
                symbol=symbol,
                source=provider.name,
                fallback_from=failed_providers[0] if failed_providers else None,
            )
            if quote.has_basic_data():
                attempts.append(
                    ProviderAttemptDiagnostic(
                        provider=provider.name,
                        status="ok",
                        duration_ms=int((time.monotonic() - start) * 1000),
                    )
                )
                diagnostics = ProviderDiagnostics(
                    symbol=symbol.canonical_code,
                    market=symbol.market,
                    status="ok",
                    attempts=attempts,
                )
                return ProviderFetchResult(quote=quote, diagnostics=diagnostics)

            attempts.append(
                ProviderAttemptDiagnostic(
                    provider=provider.name,
                    status="empty",
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error_type="empty",
                    error_message="provider returned no usable price",
                    fallback_to=fallback_to,
                )
            )
            failed_providers.append(provider.name)

        diagnostics = ProviderDiagnostics(
            symbol=symbol.canonical_code,
            market=symbol.market,
            status="unavailable",
            attempts=attempts,
        )
        return ProviderFetchResult(quote=None, diagnostics=diagnostics)
