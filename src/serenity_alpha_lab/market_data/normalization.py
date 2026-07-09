"""Normalization helpers for provider payloads."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from .contracts import DailyBar, MarketSymbol, RealtimeQuote
from .symbols import normalize_market_symbol


_QUOTE_FLOAT_FIELDS = {
    "price",
    "change_pct",
    "change_amount",
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
}


def _payload_get(payload: Any, key: str, default: Any = None) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(key, default)
    return getattr(payload, key, default)


def _payload_to_mapping(payload: Any) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if is_dataclass(payload):
        return asdict(payload)
    return {}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value in {"", "-", "--"}:
                return None
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return numeric
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_realtime_quote(
    payload: Any,
    *,
    symbol: MarketSymbol,
    source: str,
    fetched_at: Optional[datetime] = None,
    realtime_cache_ttl: int = 600,
    fallback_from: Optional[str] = None,
) -> RealtimeQuote:
    """Convert heterogeneous provider quote payloads into a stable quote."""

    data = _payload_to_mapping(payload)
    payload_code = _payload_get(payload, "code", symbol.canonical_code)
    try:
        code = normalize_market_symbol(str(payload_code)).canonical_code
    except ValueError:
        code = symbol.canonical_code

    quote = RealtimeQuote(
        code=code,
        name=str(_payload_get(payload, "name", "") or ""),
        source=str(source),
        market=symbol.market,
        currency=symbol.currency,
        fallback_from=fallback_from,
    )

    for field_name in _QUOTE_FLOAT_FIELDS:
        setattr(quote, field_name, _safe_float(data.get(field_name, _payload_get(payload, field_name))))
    quote.volume = _safe_int(data.get("volume", _payload_get(payload, "volume")))

    fetched_dt = fetched_at or datetime.now(timezone.utc)
    if fetched_dt.tzinfo is None:
        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
    fetched_dt = fetched_dt.astimezone(timezone.utc)
    quote.fetched_at = fetched_dt.isoformat()

    provider_dt = _parse_datetime(_payload_get(payload, "provider_timestamp"))
    if provider_dt is not None:
        quote.provider_timestamp = provider_dt.isoformat()
        quote.stale_seconds = max(0, int((fetched_dt - provider_dt).total_seconds()))
        quote.is_stale = quote.stale_seconds > int(realtime_cache_ttl)

    quote.missing_fields = []
    if quote.price is None or quote.price <= 0:
        quote.missing_fields.append("price")
    quote.data_quality = "ok" if not quote.missing_fields else "unavailable"
    return quote


def normalize_daily_bars(
    rows: Iterable[Any],
    *,
    symbol: MarketSymbol,
    source: str,
) -> list[DailyBar]:
    """Normalize provider daily-bar rows to DSA-compatible standard fields."""

    normalized: list[DailyBar] = []
    for row in rows:
        data = _payload_to_mapping(row)
        normalized.append(
            DailyBar(
                code=symbol.canonical_code,
                date=str(data.get("date", _payload_get(row, "date", ""))),
                source=source,
                market=symbol.market,
                currency=symbol.currency,
                open=_safe_float(data.get("open", _payload_get(row, "open"))),
                high=_safe_float(data.get("high", _payload_get(row, "high"))),
                low=_safe_float(data.get("low", _payload_get(row, "low"))),
                close=_safe_float(data.get("close", _payload_get(row, "close"))),
                volume=_safe_int(data.get("volume", _payload_get(row, "volume"))),
                amount=_safe_float(data.get("amount", _payload_get(row, "amount"))),
                pct_chg=_safe_float(data.get("pct_chg", _payload_get(row, "pct_chg"))),
            )
        )
    return normalized
