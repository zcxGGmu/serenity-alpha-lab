from __future__ import annotations

from datetime import date

import pytest

from serenity_alpha_lab.domain.instruments import (
    AmbiguousInstrumentSymbol,
    InstrumentId,
    InvalidInstrumentSymbol,
    Market,
    ProviderSymbolMapping,
)
from serenity_alpha_lab.integrations.dsa.symbol_compatibility import (
    DsaStockCodeCompatibilityMapper,
    DsaStockCodeMapping,
    normalize_stock_code_compatible,
)


@pytest.mark.parametrize(
    ("raw", "market", "legacy_stock_code", "canonical", "dsa_symbol", "yahoo_symbol"),
    [
        ("SH.600519", None, "600519", "600519.XSHG", "SH600519", "600519.SS"),
        ("SS600519", None, "600519", "600519.XSHG", "SH600519", "600519.SS"),
        ("600519.SS", None, "600519", "600519.XSHG", "SH600519", "600519.SS"),
        ("BJ.920748", None, "920748", "920748.XBSE", "BJ920748", "920748.BJ"),
        ("1810.HK", None, "HK01810", "01810.XHKG", "HK01810", "01810.HK"),
        ("hk700", None, "HK00700", "00700.XHKG", "HK00700", "00700.HK"),
        ("7203.t", None, "7203.T", "7203.XTKS", "7203.T", "7203.T"),
        ("005930.ks", None, "005930.KS", "005930.XKRX", "005930.KS", "005930.KS"),
        ("035720.kq", None, "035720.KQ", "035720.XKOS", "035720.KQ", "035720.KQ"),
        ("2330.tw", None, "2330.TW", "2330.XTAI", "2330.TW", "2330.TW"),
        ("6505.two", None, "6505.TWO", "6505.ROCO", "6505.TWO", "6505.TWO"),
        ("AAPL", None, "AAPL", "AAPL.XNAS", "AAPL", "AAPL"),
        ("600519", Market.CN, "600519", "600519.XSHG", "SH600519", "600519.SS"),
    ],
)
def test_mapper_preserves_p0_normalize_stock_code_cases(
    raw: str,
    market: Market | None,
    legacy_stock_code: str,
    canonical: str,
    dsa_symbol: str,
    yahoo_symbol: str,
) -> None:
    mapper = DsaStockCodeCompatibilityMapper()

    mapping = mapper.from_legacy(raw, market=market)

    assert isinstance(mapping, DsaStockCodeMapping)
    assert mapping.raw_symbol == raw
    assert mapping.instrument_id.canonical == canonical
    assert mapping.legacy_stock_code == legacy_stock_code
    assert mapping.dsa_symbol == dsa_symbol
    assert mapping.provider_symbol("dsa") == dsa_symbol
    assert mapping.provider_symbol("yahoo") == yahoo_symbol
    assert mapping.provider_mappings == (
        ProviderSymbolMapping(provider="dsa", symbol=dsa_symbol, instrument_id=InstrumentId.parse(canonical)),
        ProviderSymbolMapping(provider="yahoo", symbol=yahoo_symbol, instrument_id=InstrumentId.parse(canonical)),
    )


def test_mapper_keeps_bare_six_digit_symbols_ambiguous_without_market_context() -> None:
    mapper = DsaStockCodeCompatibilityMapper()

    with pytest.raises(AmbiguousInstrumentSymbol):
        mapper.from_legacy("600519")

    mapping = mapper.from_legacy("600519", market=Market.CN)

    assert mapping.instrument_id.canonical == "600519.XSHG"
    assert mapping.legacy_stock_code == "600519"


def test_mapper_rejects_conflicting_explicit_exchange_hints() -> None:
    mapper = DsaStockCodeCompatibilityMapper()

    with pytest.raises(InvalidInstrumentSymbol):
        mapper.from_legacy("SZ600519")


def test_mapping_validity_window_is_retained_and_validated() -> None:
    mapper = DsaStockCodeCompatibilityMapper()
    valid_from = date(2026, 1, 1)
    valid_to = date(2026, 12, 31)

    mapping = mapper.from_legacy(
        "600519",
        market=Market.CN,
        valid_from=valid_from,
        valid_to=valid_to,
    )

    assert mapping.valid_from == valid_from
    assert mapping.valid_to == valid_to

    with pytest.raises(ValueError, match="valid_to cannot be before valid_from"):
        mapper.from_legacy(
            "600519",
            market=Market.CN,
            valid_from=valid_to,
            valid_to=valid_from,
        )


def test_mapper_wraps_injected_normalize_stock_code_callable() -> None:
    calls: list[str] = []

    def spy_normalizer(stock_code: str) -> str:
        calls.append(stock_code)
        return normalize_stock_code_compatible(stock_code)

    mapper = DsaStockCodeCompatibilityMapper(normalize_stock_code=spy_normalizer)

    mapping = mapper.from_instrument(InstrumentId.parse("600519.XSHG"), raw_symbol="600519.XSHG")

    assert calls == ["SH600519"]
    assert mapping.instrument_id.canonical == "600519.XSHG"
    assert mapping.legacy_stock_code == "600519"
    assert mapping.dsa_symbol == "SH600519"
