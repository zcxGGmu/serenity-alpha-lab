from __future__ import annotations

from datetime import date

from serenity_alpha_lab.analysis import (
    AnalysisReadinessGate,
    StockAnalysisPipeline,
    build_analysis_context,
)
from serenity_alpha_lab.market_data import (
    DailyBar,
    ProviderAttemptDiagnostic,
    ProviderDiagnostics,
    ProviderFetchResult,
    RealtimeQuote,
)


class StubMarketDataManager:
    def __init__(self, result: ProviderFetchResult, bars: list[DailyBar]) -> None:
        self.result = result
        self.bars = bars
        self.quote_calls: list[str] = []
        self.bar_calls: list[tuple[str, int]] = []

    def get_realtime_quote(self, stock_code: str) -> ProviderFetchResult:
        self.quote_calls.append(stock_code)
        return self.result

    def get_daily_bars(self, stock_code: str, *, days: int = 30) -> list[DailyBar]:
        self.bar_calls.append((stock_code, days))
        return list(self.bars)


def quote_result(
    *,
    price: float | None = 42.5,
    provider_status: str = "ok",
    attempts: list[ProviderAttemptDiagnostic] | None = None,
) -> ProviderFetchResult:
    quote = (
        RealtimeQuote(
            code="AAPL",
            name="Apple Inc.",
            source="stub",
            fetched_at="2026-07-09T09:30:00+00:00",
            provider_timestamp="2026-07-09T09:29:55+00:00",
            market="us",
            currency="USD",
            price=price,
            change_pct=2.4,
            volume=1_250_000,
            pe_ratio=28.1,
            data_quality="ok" if price else "unavailable",
        )
        if price is not None
        else None
    )
    return ProviderFetchResult(
        quote=quote,
        diagnostics=ProviderDiagnostics(
            symbol="AAPL",
            market="us",
            status=provider_status,
            attempts=attempts or [ProviderAttemptDiagnostic(provider="stub", status="ok", duration_ms=3)],
        ),
    )


def daily_bars(*, include_risk_bar: bool = True) -> list[DailyBar]:
    rows = [
        DailyBar(
            code="AAPL",
            date="2026-07-08",
            source="stub",
            market="us",
            currency="USD",
            open=41.0,
            high=43.0,
            low=40.8,
            close=42.5,
            volume=1_400_000,
            pct_chg=2.4,
        ),
        DailyBar(
            code="AAPL",
            date="2026-07-07",
            source="stub",
            market="us",
            currency="USD",
            open=40.8,
            high=41.8,
            low=40.1,
            close=41.5,
            volume=1_100_000,
            pct_chg=1.0,
        ),
    ]
    if include_risk_bar:
        rows.append(
            DailyBar(
                code="AAPL",
                date="2026-07-06",
                source="stub",
                market="us",
                currency="USD",
                open=43.2,
                high=43.4,
                low=40.4,
                close=41.1,
                volume=1_700_000,
                pct_chg=-4.2,
            )
        )
    return rows


def test_context_builder_converts_market_data_to_evidence_with_provenance_metadata() -> None:
    context = build_analysis_context(
        stock_code="AAPL",
        stock_name="Apple Inc.",
        quote=quote_result().quote,
        daily_bars=daily_bars(),
        diagnostics=quote_result().diagnostics,
        query="AAPL market data research",
    )

    assert context.subject.code == "AAPL"
    assert context.subject.market == "us"
    assert context.query == "AAPL market data research"
    assert context.source_coverage.focus_ticker == "AAPL"
    assert context.source_coverage.evidence_count >= 3
    assert context.source_coverage.primary_count >= 1
    assert context.source_coverage.risk_count >= 1
    assert context.readiness_status == "ready"
    assert context.metadata["provider_status"] == "ok"
    assert context.metadata["source_coverage"]["focus_evidence_count"] == context.source_coverage.focus_evidence_count

    evidence_ids = {item.id for item in context.evidence}
    assert "serenity:market-data:AAPL:quote:2026-07-09" in evidence_ids
    assert "serenity:market-data:AAPL:bar:2026-07-08" in evidence_ids
    assert "serenity:market-data:AAPL:risk:2026-07-06" in evidence_ids

    quote_item = next(item for item in context.evidence if item.id.endswith(":quote:2026-07-09"))
    assert quote_item.source_title == "Market data quote for AAPL"
    assert quote_item.source_url == "serenity://market-data/AAPL/quote/2026-07-09"
    assert quote_item.published_at == date(2026, 7, 9)
    assert quote_item.claim_type == "fact"
    assert quote_item.strength == "primary"
    assert quote_item.tickers == ["AAPL"]
    assert "market-data" in quote_item.themes
    assert quote_item.factor_impacts["evidence_quality"] > 0
    assert quote_item.source_excerpt


def test_pipeline_produces_research_only_signals_and_blocks_report_when_readiness_fails() -> None:
    manager = StubMarketDataManager(
        quote_result(price=42.5),
        daily_bars(include_risk_bar=False),
    )
    pipeline = StockAnalysisPipeline(market_data=manager, readiness_gate=AnalysisReadinessGate())

    result = pipeline.analyze("AAPL", stock_name="Apple Inc.", query="AAPL market data research")

    assert manager.quote_calls == ["AAPL"]
    assert manager.bar_calls == [("AAPL", 30)]
    assert result.research_only is True
    assert result.symbol == "AAPL"
    assert result.market == "us"
    assert result.readiness.status == "needs_work"
    assert result.report_gate.status == "blocked"
    assert result.report_gate.reason == "readiness_not_ready"
    assert "missing_risk_coverage" in result.readiness.flag_codes
    assert result.signals.rating in {"Review Candidate", "Watchlist Candidate"}
    assert result.signals.confidence in {"low", "medium"}
    assert result.signals.score >= 0
    assert result.diagnostics["provider_status"] == "ok"

    dumped = result.to_dict()
    text = str(dumped).lower()
    assert dumped["research_only"] is True
    assert dumped["report_gate"]["research_only"] is True
    assert "operation_advice" not in text
    assert "target_price" not in text
    assert "position_sizing" not in text
    assert "stop_loss" not in text
    assert "take_profit" not in text


def test_pipeline_keeps_provider_failures_fail_open_and_default_off() -> None:
    manager = StubMarketDataManager(
        quote_result(price=None, provider_status="unavailable", attempts=[
            ProviderAttemptDiagnostic(
                provider="credentialed",
                status="skipped",
                error_type="credentials_unavailable",
                error_message="provider credentials are not configured",
            )
        ]),
        [],
    )
    pipeline = StockAnalysisPipeline(market_data=manager)

    result = pipeline.analyze("AAPL", stock_name="Apple Inc.")

    assert result.research_only is True
    assert result.status == "blocked"
    assert result.readiness.status == "blocked"
    assert result.report_gate.status == "blocked"
    assert result.evidence == []
    assert result.diagnostics["provider_status"] == "unavailable"
    assert result.diagnostics["attempts"][0]["error_type"] == "credentials_unavailable"
