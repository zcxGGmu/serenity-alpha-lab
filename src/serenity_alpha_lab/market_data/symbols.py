"""Stock code normalization and market routing."""

from __future__ import annotations

import re

from .contracts import MarketSymbol


_CURRENCY_BY_MARKET = {
    "cn": "CNY",
    "hk": "HKD",
    "us": "USD",
    "jp": "JPY",
    "kr": "KRW",
    "tw": "TWD",
}


def _is_bse_code(code: str) -> bool:
    base = (code or "").strip().upper().split(".", 1)[0]
    return len(base) == 6 and base.isdigit() and base.startswith(("92", "43", "83", "87", "88"))


def _infer_cn_exchange(base: str) -> str:
    if _is_bse_code(base):
        return "BJ"
    if base.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def _valid_cn_exchange(exchange: str, base: str) -> bool:
    if not (base.isdigit() and len(base) == 6):
        return False
    inferred = _infer_cn_exchange(base)
    if exchange == "SS":
        exchange = "SH"
    return exchange == inferred


def _market_symbol(
    *,
    raw_code: str,
    canonical_code: str,
    provider_code: str | None = None,
    market: str,
    exchange: str,
) -> MarketSymbol:
    return MarketSymbol(
        raw_code=raw_code,
        canonical_code=canonical_code,
        provider_code=provider_code or canonical_code,
        market=market,
        exchange=exchange,
        currency=_CURRENCY_BY_MARKET[market],
    )


def _normalize_hk_digits(raw_code: str, digits: str) -> MarketSymbol:
    canonical = f"HK{digits.zfill(5)}"
    return _market_symbol(
        raw_code=raw_code,
        canonical_code=canonical,
        market="hk",
        exchange="HK",
    )


def normalize_market_symbol(raw_code: str) -> MarketSymbol:
    """Normalize common DSA stock-code formats and infer market routing."""

    raw = (raw_code or "").strip()
    text = raw.upper()
    if not text:
        raise ValueError("stock code is required")

    if "." in text:
        base, suffix = text.rsplit(".", 1)
        if suffix in {"SH", "SS", "SZ", "BJ"} and _valid_cn_exchange(suffix, base):
            exchange = "SH" if suffix == "SS" else suffix
            return _market_symbol(raw_code=raw, canonical_code=base, market="cn", exchange=exchange)
        if suffix == "HK" and base.isdigit() and 1 <= len(base) <= 5:
            return _normalize_hk_digits(raw, base)
        if suffix == "T" and base.isdigit() and len(base) in (4, 5):
            return _market_symbol(
                raw_code=raw,
                canonical_code=f"{base}.T",
                market="jp",
                exchange="T",
            )
        if suffix in {"KS", "KQ"} and base.isdigit() and len(base) == 6:
            return _market_symbol(
                raw_code=raw,
                canonical_code=f"{base}.{suffix}",
                market="kr",
                exchange=suffix,
            )
        if suffix in {"TW", "TWO"} and base.isdigit() and 4 <= len(base) <= 6:
            return _market_symbol(
                raw_code=raw,
                canonical_code=f"{base}.{suffix}",
                market="tw",
                exchange=suffix,
            )

    for prefix in ("SH", "SS", "SZ", "BJ"):
        dotted = f"{prefix}."
        if text.startswith(dotted):
            base = text[len(dotted):]
        elif text.startswith(prefix):
            base = text[len(prefix):]
        else:
            continue
        if _valid_cn_exchange(prefix, base):
            exchange = "SH" if prefix == "SS" else prefix
            return _market_symbol(raw_code=raw, canonical_code=base, market="cn", exchange=exchange)

    if text.startswith("HK.") and text[3:].isdigit() and 1 <= len(text[3:]) <= 5:
        return _normalize_hk_digits(raw, text[3:])
    if text.startswith("HK") and text[2:].isdigit() and 1 <= len(text[2:]) <= 5:
        return _normalize_hk_digits(raw, text[2:])

    if text.isdigit() and len(text) == 6:
        exchange = _infer_cn_exchange(text)
        return _market_symbol(raw_code=raw, canonical_code=text, market="cn", exchange=exchange)
    if text.isdigit() and len(text) == 5:
        return _normalize_hk_digits(raw, text)

    if re.match(r"^[A-Z]{1,5}(?:\.(?:US|[A-Z]))?$", text):
        return _market_symbol(raw_code=raw, canonical_code=text, market="us", exchange="US")

    raise ValueError(f"unsupported stock code format: {raw_code!r}")
