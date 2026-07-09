from __future__ import annotations

from datetime import datetime, timezone

from serenity_alpha_lab.market_data import (
    MarketDataManager,
    MarketDataProvider,
    MarketDataProviderConfig,
    ProviderFetchResult,
    normalize_daily_bars,
    normalize_market_symbol,
    normalize_realtime_quote,
)


class StubProvider(MarketDataProvider):
    def __init__(
        self,
        *,
        name: str,
        priority: int = 10,
        supported_markets: tuple[str, ...] = ("cn",),
        quote_result: object = None,
        error: Exception | None = None,
        config: MarketDataProviderConfig | None = None,
    ) -> None:
        super().__init__(
            MarketDataProviderConfig(
                name=name,
                priority=config.priority if config else priority,
                supported_markets=config.supported_markets if config else supported_markets,
                requires_credentials=config.requires_credentials if config else False,
                credential_env=config.credential_env if config else None,
            )
        )
        self.quote_result = quote_result
        self.error = error
        self.calls: list[str] = []

    def fetch_realtime_quote(self, symbol, *, timeout_seconds: float | None = None):
        self.calls.append(symbol.provider_code)
        if self.error is not None:
            raise self.error
        return self.quote_result


def test_normalize_market_symbol_routes_dsa_stock_code_formats():
    cases = {
        "600519.SH": ("600519", "cn", "SH", "CNY"),
        "SZ000001": ("000001", "cn", "SZ", "CNY"),
        "BJ920748": ("920748", "cn", "BJ", "CNY"),
        "1810.HK": ("HK01810", "hk", "HK", "HKD"),
        "hk700": ("HK00700", "hk", "HK", "HKD"),
        "7203.t": ("7203.T", "jp", "T", "JPY"),
        "005930.ks": ("005930.KS", "kr", "KS", "KRW"),
        "2330.tw": ("2330.TW", "tw", "TW", "TWD"),
        "aapl": ("AAPL", "us", "US", "USD"),
    }

    for raw, expected in cases.items():
        symbol = normalize_market_symbol(raw)
        assert (symbol.canonical_code, symbol.market, symbol.exchange, symbol.currency) == expected


def test_normalize_realtime_quote_coerces_provider_payload_without_network():
    symbol = normalize_market_symbol("600519.SH")
    fetched_at = datetime(2026, 7, 9, 4, 30, tzinfo=timezone.utc)

    quote = normalize_realtime_quote(
        {
            "code": "SH600519",
            "name": "贵州茅台",
            "price": "1800.50",
            "change_pct": "-1.25",
            "volume": "1234.0",
            "provider_timestamp": "2026-07-09T04:25:00+00:00",
        },
        symbol=symbol,
        source="stub",
        fetched_at=fetched_at,
        realtime_cache_ttl=600,
    )

    assert quote.code == "600519"
    assert quote.name == "贵州茅台"
    assert quote.source == "stub"
    assert quote.market == "cn"
    assert quote.currency == "CNY"
    assert quote.price == 1800.5
    assert quote.change_pct == -1.25
    assert quote.volume == 1234
    assert quote.data_quality == "ok"
    assert quote.missing_fields == []
    assert quote.is_stale is False
    assert quote.stale_seconds == 300


def test_normalize_realtime_quote_rejects_non_finite_price():
    quote = normalize_realtime_quote(
        {"code": "AAPL", "name": "Apple", "price": "inf"},
        symbol=normalize_market_symbol("AAPL"),
        source="stub",
    )

    assert quote.price is None
    assert quote.data_quality == "unavailable"
    assert quote.missing_fields == ["price"]
    assert quote.has_basic_data() is False


def test_normalize_daily_bars_preserves_standard_dsa_columns():
    rows = normalize_daily_bars(
        [
            {
                "date": "2026-07-08",
                "open": "10.1",
                "high": "10.8",
                "low": "9.9",
                "close": "10.4",
                "volume": "1200",
                "amount": "48000.5",
                "pct_chg": "1.2",
            }
        ],
        symbol=normalize_market_symbol("000001.SZ"),
        source="stub",
    )

    assert len(rows) == 1
    assert rows[0].code == "000001"
    assert rows[0].source == "stub"
    assert rows[0].open == 10.1
    assert rows[0].close == 10.4
    assert rows[0].volume == 1200
    assert rows[0].amount == 48000.5
    assert rows[0].pct_chg == 1.2


def test_market_data_manager_falls_back_with_safe_diagnostics():
    primary = StubProvider(
        name="primary",
        priority=1,
        error=RuntimeError("token SECRET at /Users/zq/private/provider.log"),
    )
    secondary = StubProvider(
        name="secondary",
        priority=2,
        quote_result={"code": "600519", "name": "贵州茅台", "price": "1800.50"},
    )
    manager = MarketDataManager([secondary, primary])

    result = manager.get_realtime_quote("SH600519")

    assert result.quote is not None
    assert result.quote.source == "secondary"
    assert result.quote.fallback_from == "primary"
    assert [attempt.provider for attempt in result.diagnostics.attempts] == ["primary", "secondary"]
    assert result.diagnostics.attempts[0].status == "failed"
    assert result.diagnostics.attempts[0].error_type == "RuntimeError"
    assert result.diagnostics.attempts[0].fallback_to == "secondary"
    diagnostics_text = str(result.diagnostics.to_dict())
    assert "SECRET" not in diagnostics_text
    assert "/Users/zq" not in diagnostics_text


def test_market_data_manager_skips_credentialed_provider_by_default(monkeypatch):
    monkeypatch.delenv("SERENITY_FAKE_PROVIDER_KEY", raising=False)
    provider = StubProvider(
        name="credentialed",
        quote_result={"price": 1},
        config=MarketDataProviderConfig(
            name="credentialed",
            priority=1,
            supported_markets=("us",),
            requires_credentials=True,
            credential_env="SERENITY_FAKE_PROVIDER_KEY",
        ),
    )
    manager = MarketDataManager([provider])

    result: ProviderFetchResult = manager.get_realtime_quote("AAPL")

    assert result.quote is None
    assert provider.calls == []
    assert result.diagnostics.status == "unavailable"
    assert result.diagnostics.attempts[0].provider == "credentialed"
    assert result.diagnostics.attempts[0].status == "skipped"
    assert result.diagnostics.attempts[0].error_type == "credentials_unavailable"


def test_market_data_manager_calls_credentialed_provider_when_env_is_present(monkeypatch):
    monkeypatch.setenv("SERENITY_FAKE_PROVIDER_KEY", "fake-key")
    provider = StubProvider(
        name="credentialed",
        quote_result={"price": "190.25"},
        config=MarketDataProviderConfig(
            name="credentialed",
            priority=1,
            supported_markets=("us",),
            requires_credentials=True,
            credential_env="SERENITY_FAKE_PROVIDER_KEY",
        ),
    )
    manager = MarketDataManager([provider])

    result = manager.get_realtime_quote("AAPL")

    assert result.quote is not None
    assert result.quote.price == 190.25
    assert provider.calls == ["AAPL"]
    assert result.diagnostics.status == "ok"
