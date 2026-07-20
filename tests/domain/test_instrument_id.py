from __future__ import annotations

import pytest

from serenity_alpha_lab.domain.instruments import (
    AmbiguousInstrumentSymbol,
    AssetType,
    Exchange,
    InstrumentId,
    InvalidInstrumentSymbol,
    Market,
    ProviderSymbolMapping,
)


@pytest.mark.parametrize(
    ("canonical", "market", "exchange", "symbol"),
    [
        ("600519.XSHG", Market.CN, Exchange.XSHG, "600519"),
        ("000001.XSHE", Market.CN, Exchange.XSHE, "000001"),
        ("00700.XHKG", Market.HK, Exchange.XHKG, "00700"),
        ("AAPL.XNAS", Market.US, Exchange.XNAS, "AAPL"),
        ("7203.XTKS", Market.JP, Exchange.XTKS, "7203"),
        ("005930.XKRX", Market.KR, Exchange.XKRX, "005930"),
        ("035720.XKOS", Market.KR, Exchange.XKOS, "035720"),
        ("2330.XTAI", Market.TW, Exchange.XTAI, "2330"),
        ("6505.ROCO", Market.TW, Exchange.ROCO, "6505"),
    ],
)
def test_canonical_instrument_id_round_trips(
    canonical: str,
    market: Market,
    exchange: Exchange,
    symbol: str,
) -> None:
    instrument = InstrumentId.parse(canonical)

    assert instrument.market is market
    assert instrument.exchange is exchange
    assert instrument.symbol == symbol
    assert instrument.asset_type is AssetType.EQUITY
    assert instrument.canonical == canonical
    assert str(instrument) == canonical


@pytest.mark.parametrize(
    ("legacy", "market", "expected"),
    [
        ("600519", Market.CN, "600519.XSHG"),
        ("000001", Market.CN, "000001.XSHE"),
        ("SH600519", None, "600519.XSHG"),
        ("600519.SH", None, "600519.XSHG"),
        ("SZ000001", None, "000001.XSHE"),
        ("HK00700", None, "00700.XHKG"),
        ("0700.HK", None, "00700.XHKG"),
        ("AAPL", Market.US, "AAPL.XNAS"),
        ("7203.T", None, "7203.XTKS"),
        ("005930.KS", None, "005930.XKRX"),
        ("035720.KQ", None, "035720.XKOS"),
        ("2330.TW", None, "2330.XTAI"),
        ("6505.TWO", None, "6505.ROCO"),
    ],
)
def test_legacy_symbols_map_to_canonical_instrument_id(
    legacy: str,
    market: Market | None,
    expected: str,
) -> None:
    assert InstrumentId.from_legacy(legacy, market=market).canonical == expected


def test_bare_six_digit_symbol_requires_market_context() -> None:
    with pytest.raises(AmbiguousInstrumentSymbol):
        InstrumentId.parse("600519")

    with pytest.raises(AmbiguousInstrumentSymbol):
        InstrumentId.from_legacy("600519")

    assert InstrumentId.from_legacy("600519", market=Market.CN).canonical == "600519.XSHG"


@pytest.mark.parametrize("legacy", ["005930", "2330", "1234567.TW", "7203.KS", "123.T"])
def test_ambiguous_or_invalid_suffix_market_symbols_are_rejected(legacy: str) -> None:
    with pytest.raises(InvalidInstrumentSymbol):
        InstrumentId.from_legacy(legacy, market=Market.KR if legacy == "005930" else None)


@pytest.mark.parametrize(
    ("canonical", "provider", "provider_symbol", "dsa_symbol"),
    [
        ("600519.XSHG", "yahoo", "600519.SS", "SH600519"),
        ("000001.XSHE", "yahoo", "000001.SZ", "SZ000001"),
        ("00700.XHKG", "yahoo", "00700.HK", "HK00700"),
        ("AAPL.XNAS", "yahoo", "AAPL", "AAPL"),
        ("7203.XTKS", "yahoo", "7203.T", "7203.T"),
        ("005930.XKRX", "yahoo", "005930.KS", "005930.KS"),
        ("035720.XKOS", "yahoo", "035720.KQ", "035720.KQ"),
        ("2330.XTAI", "yahoo", "2330.TW", "2330.TW"),
        ("6505.ROCO", "yahoo", "6505.TWO", "6505.TWO"),
    ],
)
def test_provider_symbol_mapping_round_trips(
    canonical: str,
    provider: str,
    provider_symbol: str,
    dsa_symbol: str,
) -> None:
    instrument = InstrumentId.parse(canonical)

    mapping = instrument.to_provider_symbol(provider)

    assert mapping == ProviderSymbolMapping(
        provider=provider,
        symbol=provider_symbol,
        instrument_id=instrument,
    )
    assert instrument.to_dsa_symbol() == dsa_symbol
    assert ProviderSymbolMapping.from_provider_symbol(provider, provider_symbol).instrument_id == instrument
