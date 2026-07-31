from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class InstrumentIdError(ValueError):
    """Base error for invalid instrument identifiers."""


class AmbiguousInstrumentSymbol(InstrumentIdError):
    """Raised when a symbol cannot be mapped without explicit context."""


class InvalidInstrumentSymbol(InstrumentIdError):
    """Raised when a symbol is malformed or unsupported."""


class UnsupportedProvider(InstrumentIdError):
    """Raised when provider symbol formatting is not supported."""


class Market(StrEnum):
    CN = "cn"
    HK = "hk"
    US = "us"
    JP = "jp"
    KR = "kr"
    TW = "tw"


class AssetType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    UNKNOWN = "unknown"


class Exchange(StrEnum):
    XSHG = "XSHG"
    XSHE = "XSHE"
    XBSE = "XBSE"
    XHKG = "XHKG"
    XNAS = "XNAS"
    XNYS = "XNYS"
    XTKS = "XTKS"
    XKRX = "XKRX"
    XKOS = "XKOS"
    XTAI = "XTAI"
    ROCO = "ROCO"


_EXCHANGE_MARKETS: dict[Exchange, Market] = {
    Exchange.XSHG: Market.CN,
    Exchange.XSHE: Market.CN,
    Exchange.XBSE: Market.CN,
    Exchange.XHKG: Market.HK,
    Exchange.XNAS: Market.US,
    Exchange.XNYS: Market.US,
    Exchange.XTKS: Market.JP,
    Exchange.XKRX: Market.KR,
    Exchange.XKOS: Market.KR,
    Exchange.XTAI: Market.TW,
    Exchange.ROCO: Market.TW,
}

_US_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}(?:\.[A-Z]{1,2})?$")
_CN_PREFIX_EXCHANGES = {
    "SH": Exchange.XSHG,
    "SS": Exchange.XSHG,
    "SZ": Exchange.XSHE,
    "BJ": Exchange.XBSE,
}
_CN_SUFFIX_EXCHANGES = {
    "SH": Exchange.XSHG,
    "SS": Exchange.XSHG,
    "SZ": Exchange.XSHE,
    "BJ": Exchange.XBSE,
}
_YAHOO_SUFFIX_EXCHANGES = {
    "T": Exchange.XTKS,
    "KS": Exchange.XKRX,
    "KQ": Exchange.XKOS,
    "TW": Exchange.XTAI,
    "TWO": Exchange.ROCO,
}
_YAHOO_SUFFIX_LENGTHS = {
    "T": (4, 5),
    "KS": (6,),
    "KQ": (6,),
    "TW": (4, 5, 6),
    "TWO": (4, 5, 6),
}


@dataclass(frozen=True, slots=True)
class InstrumentId:
    market: Market
    exchange: Exchange
    symbol: str
    asset_type: AssetType = AssetType.EQUITY

    def __post_init__(self) -> None:
        market = Market(self.market)
        exchange = Exchange(self.exchange)
        asset_type = AssetType(self.asset_type)
        if _EXCHANGE_MARKETS[exchange] is not market:
            raise InvalidInstrumentSymbol(f"Exchange {exchange.value} is not in market {market.value}")

        normalized_symbol = _normalize_symbol_for_exchange(str(self.symbol), exchange)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "exchange", exchange)
        object.__setattr__(self, "asset_type", asset_type)
        object.__setattr__(self, "symbol", normalized_symbol)

    @property
    def canonical(self) -> str:
        return f"{self.symbol}.{self.exchange.value}"

    def __str__(self) -> str:
        return self.canonical

    @classmethod
    def parse(cls, value: str) -> InstrumentId:
        text = _clean(value)
        if not text:
            raise InvalidInstrumentSymbol("instrument id is required")
        if text.isdigit() and len(text) == 6:
            raise AmbiguousInstrumentSymbol("bare 6-digit symbols require explicit market context")

        if "." not in text:
            raise InvalidInstrumentSymbol(f"Invalid canonical instrument id: {value!r}")

        symbol, exchange_text = text.rsplit(".", 1)
        try:
            exchange = Exchange(exchange_text)
        except ValueError as exc:
            raise InvalidInstrumentSymbol(f"Unsupported exchange: {exchange_text}") from exc

        return cls(
            market=_EXCHANGE_MARKETS[exchange],
            exchange=exchange,
            symbol=symbol,
        )

    @classmethod
    def from_legacy(cls, value: str, *, market: Market | str | None = None) -> InstrumentId:
        text = _clean(value)
        if not text:
            raise InvalidInstrumentSymbol("instrument symbol is required")

        market_context = Market(market) if market is not None else None

        if "." in text:
            suffix = text.rsplit(".", 1)[1]
            if suffix in {exchange.value for exchange in Exchange}:
                instrument = cls.parse(text)
                return _ensure_market_context(instrument, market_context)

        cn_prefixed = _parse_cn_prefixed_symbol(text)
        if cn_prefixed is not None:
            return _ensure_market_context(cn_prefixed, market_context)

        dotted = _parse_dotted_legacy_symbol(text)
        if dotted is not None:
            return _ensure_market_context(dotted, market_context)

        if text.startswith("HK") and text[2:].isdigit():
            instrument = cls(market=Market.HK, exchange=Exchange.XHKG, symbol=text[2:])
            return _ensure_market_context(instrument, market_context)
        if text.startswith("HK.") and text[3:].isdigit():
            instrument = cls(market=Market.HK, exchange=Exchange.XHKG, symbol=text[3:])
            return _ensure_market_context(instrument, market_context)

        if text.isdigit():
            return _from_bare_numeric_symbol(text, market_context)

        if _US_SYMBOL_RE.fullmatch(text):
            instrument = cls(market=Market.US, exchange=Exchange.XNAS, symbol=text)
            return _ensure_market_context(instrument, market_context)

        raise InvalidInstrumentSymbol(f"Unsupported instrument symbol: {value!r}")

    def to_provider_symbol(self, provider: str) -> ProviderSymbolMapping:
        provider_id = _normalize_provider(provider)
        if provider_id == "yahoo":
            symbol = _format_yahoo_symbol(self)
        elif provider_id in {"dsa", "legacy"}:
            symbol = self.to_dsa_symbol()
        else:
            raise UnsupportedProvider(f"Unsupported provider: {provider}")
        return ProviderSymbolMapping(provider=provider_id, symbol=symbol, instrument_id=self)

    def to_dsa_symbol(self) -> str:
        if self.exchange is Exchange.XSHG:
            return f"SH{self.symbol}"
        if self.exchange is Exchange.XSHE:
            return f"SZ{self.symbol}"
        if self.exchange is Exchange.XBSE:
            return f"BJ{self.symbol}"
        if self.exchange is Exchange.XHKG:
            return f"HK{self.symbol}"
        if self.market is Market.US:
            return self.symbol
        return _format_yahoo_symbol(self)


@dataclass(frozen=True, slots=True)
class ProviderSymbolMapping:
    provider: str
    symbol: str
    instrument_id: InstrumentId

    @classmethod
    def from_provider_symbol(
        cls,
        provider: str,
        symbol: str,
        *,
        market: Market | str | None = None,
    ) -> ProviderSymbolMapping:
        provider_id = _normalize_provider(provider)
        if provider_id not in {"yahoo", "dsa", "legacy"}:
            raise UnsupportedProvider(f"Unsupported provider: {provider}")
        instrument = InstrumentId.from_legacy(symbol, market=market)
        return cls(provider=provider_id, symbol=_clean(symbol), instrument_id=instrument)


def _clean(value: str) -> str:
    return str(value or "").strip().upper()


def _normalize_provider(provider: str) -> str:
    provider_id = str(provider or "").strip().lower()
    if not provider_id:
        raise UnsupportedProvider("provider is required")
    return provider_id


def _normalize_symbol_for_exchange(symbol: str, exchange: Exchange) -> str:
    text = _clean(symbol)
    if exchange in {Exchange.XSHG, Exchange.XSHE, Exchange.XBSE}:
        if not (text.isdigit() and len(text) == 6):
            raise InvalidInstrumentSymbol(f"{exchange.value} symbols must be 6 digits")
        expected = _infer_cn_exchange(text)
        if expected is not exchange:
            raise InvalidInstrumentSymbol(f"{text} does not belong to {exchange.value}")
        return text
    if exchange is Exchange.XHKG:
        if not (text.isdigit() and 1 <= len(text) <= 5):
            raise InvalidInstrumentSymbol("Hong Kong symbols must be 1-5 digits")
        return text.zfill(5)
    if exchange in {Exchange.XNAS, Exchange.XNYS}:
        if not _US_SYMBOL_RE.fullmatch(text):
            raise InvalidInstrumentSymbol("US symbols must be 1-5 letters with optional class suffix")
        return text
    if exchange is Exchange.XTKS:
        if not (text.isdigit() and len(text) in (4, 5)):
            raise InvalidInstrumentSymbol("Japan symbols must be 4-5 digits")
        return text
    if exchange in {Exchange.XKRX, Exchange.XKOS}:
        if not (text.isdigit() and len(text) == 6):
            raise InvalidInstrumentSymbol("Korea symbols must be 6 digits")
        return text
    if exchange in {Exchange.XTAI, Exchange.ROCO}:
        if not (text.isdigit() and len(text) in (4, 5, 6)):
            raise InvalidInstrumentSymbol("Taiwan symbols must be 4-6 digits")
        return text
    raise InvalidInstrumentSymbol(f"Unsupported exchange: {exchange.value}")


def _infer_cn_exchange(symbol: str) -> Exchange:
    if symbol.startswith(("43", "83", "87", "88", "92")):
        return Exchange.XBSE
    if symbol.startswith(("5", "6", "9")):
        return Exchange.XSHG
    return Exchange.XSHE


def _parse_cn_prefixed_symbol(text: str) -> InstrumentId | None:
    for prefix, exchange in _CN_PREFIX_EXCHANGES.items():
        dotted_prefix = f"{prefix}."
        if text.startswith(dotted_prefix):
            base = text[len(dotted_prefix):]
            if base.isdigit() and len(base) == 6:
                return InstrumentId(market=Market.CN, exchange=exchange, symbol=base)
            raise InvalidInstrumentSymbol(f"Invalid {prefix} symbol: {text}")
        if text.startswith(prefix):
            base = text[len(prefix):]
            if base.isdigit() and len(base) == 6:
                return InstrumentId(market=Market.CN, exchange=exchange, symbol=base)
            if base and base[0].isdigit():
                raise InvalidInstrumentSymbol(f"Invalid {prefix} symbol: {text}")
    return None


def _parse_dotted_legacy_symbol(text: str) -> InstrumentId | None:
    if "." not in text:
        return None
    base, suffix = text.rsplit(".", 1)
    if suffix in _CN_SUFFIX_EXCHANGES:
        if base.isdigit() and len(base) == 6:
            return InstrumentId(
                market=Market.CN,
                exchange=_CN_SUFFIX_EXCHANGES[suffix],
                symbol=base,
            )
        raise InvalidInstrumentSymbol(f"Invalid CN symbol: {text}")
    if suffix == "HK":
        if base.isdigit() and 1 <= len(base) <= 5:
            return InstrumentId(market=Market.HK, exchange=Exchange.XHKG, symbol=base)
        raise InvalidInstrumentSymbol(f"Invalid HK symbol: {text}")
    if suffix in _YAHOO_SUFFIX_EXCHANGES:
        if base.isdigit() and len(base) in _YAHOO_SUFFIX_LENGTHS[suffix]:
            exchange = _YAHOO_SUFFIX_EXCHANGES[suffix]
            return InstrumentId(market=_EXCHANGE_MARKETS[exchange], exchange=exchange, symbol=base)
        raise InvalidInstrumentSymbol(f"Invalid Yahoo suffix-market symbol: {text}")
    return None


def _from_bare_numeric_symbol(text: str, market_context: Market | None) -> InstrumentId:
    if len(text) == 6:
        if market_context is None:
            raise AmbiguousInstrumentSymbol("bare 6-digit symbols require explicit market context")
        if market_context is Market.CN:
            exchange = _infer_cn_exchange(text)
            return InstrumentId(market=Market.CN, exchange=exchange, symbol=text)
        raise InvalidInstrumentSymbol(f"Market {market_context.value} requires an exchange-qualified symbol")
    if 1 <= len(text) <= 5 and market_context is Market.HK:
        return InstrumentId(market=Market.HK, exchange=Exchange.XHKG, symbol=text)
    raise InvalidInstrumentSymbol(f"Unsupported bare numeric symbol: {text}")


def _ensure_market_context(
    instrument: InstrumentId,
    market_context: Market | None,
) -> InstrumentId:
    if market_context is not None and instrument.market is not market_context:
        raise InvalidInstrumentSymbol(
            f"Symbol {instrument.canonical} belongs to {instrument.market.value}, not {market_context.value}"
        )
    return instrument


def _format_yahoo_symbol(instrument: InstrumentId) -> str:
    if instrument.exchange is Exchange.XSHG:
        return f"{instrument.symbol}.SS"
    if instrument.exchange is Exchange.XSHE:
        return f"{instrument.symbol}.SZ"
    if instrument.exchange is Exchange.XBSE:
        return f"{instrument.symbol}.BJ"
    if instrument.exchange is Exchange.XHKG:
        return f"{instrument.symbol}.HK"
    if instrument.market is Market.US:
        return instrument.symbol
    suffix_by_exchange = {
        Exchange.XTKS: "T",
        Exchange.XKRX: "KS",
        Exchange.XKOS: "KQ",
        Exchange.XTAI: "TW",
        Exchange.ROCO: "TWO",
    }
    suffix = suffix_by_exchange.get(instrument.exchange)
    if suffix is None:
        raise UnsupportedProvider(f"Yahoo mapping is unsupported for {instrument.exchange.value}")
    return f"{instrument.symbol}.{suffix}"
