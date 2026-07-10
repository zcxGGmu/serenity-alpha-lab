from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from serenity_alpha_lab.analysis import StockAnalysisPipeline
from serenity_alpha_lab.analysis.report import (
    ReportSafetyViolation,
    render_stock_analysis_report_markdown,
    write_stock_analysis_report_artifacts,
)
from serenity_alpha_lab.market_data import (
    DailyBar,
    ProviderAttemptDiagnostic,
    ProviderDiagnostics,
    ProviderFetchResult,
    RealtimeQuote,
)


FIXED_GENERATED_AT = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)


class StubMarketDataManager:
    def __init__(self, result: ProviderFetchResult, bars: list[DailyBar]) -> None:
        self.result = result
        self.bars = bars

    def get_realtime_quote(self, stock_code: str) -> ProviderFetchResult:
        return self.result

    def get_daily_bars(self, stock_code: str, *, days: int = 30) -> list[DailyBar]:
        return list(self.bars)


def quote_result(*, price: float | None = 42.5) -> ProviderFetchResult:
    quote = RealtimeQuote(
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
        data_quality="ok",
    )
    return ProviderFetchResult(
        quote=quote,
        diagnostics=ProviderDiagnostics(
            symbol="AAPL",
            market="us",
            status="ok",
            attempts=[ProviderAttemptDiagnostic(provider="stub", status="ok", duration_ms=3)],
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


def _ready_analysis():
    manager = StubMarketDataManager(quote_result(price=42.5), daily_bars(include_risk_bar=True))
    return StockAnalysisPipeline(market_data=manager).analyze(
        "AAPL",
        stock_name="Apple Inc.",
        query="AAPL market data research",
    )


def test_render_stock_analysis_report_uses_dsa_sections_with_research_only_language() -> None:
    result = _ready_analysis()

    markdown = render_stock_analysis_report_markdown(result)

    assert "# Serenity Stock Analysis Report" in markdown
    assert "## Intelligence Brief" in markdown
    assert "## Data View" in markdown
    assert "## Research Readiness Guardrails" in markdown
    assert "## Signal Attribution" in markdown
    assert "## Historical Comparison" in markdown
    assert "research only" in markdown.lower()
    forbidden = [
        "you should buy",
        "you should sell",
        "target price",
        "position sizing",
        "stop loss",
        "take profit",
        "operation_advice",
        "sentiment_score",
    ]
    assert not any(phrase in markdown.lower() for phrase in forbidden)


def test_render_stock_analysis_report_attaches_provenance_to_every_key_claim() -> None:
    result = _ready_analysis()

    markdown = render_stock_analysis_report_markdown(result)

    assert "## Key Claims And Provenance" in markdown
    assert "| Claim ID | Claim | Provenance refs |" in markdown
    assert "claim:AAPL:latest-normalized-quote" in markdown
    assert "claim:AAPL:readiness" in markdown
    assert "claim:AAPL:research-score" in markdown
    assert "serenity:market-data:AAPL:quote:2026-07-09" in markdown
    assert "serenity://market-data/AAPL/quote/2026-07-09" in markdown
    key_claim_rows = [
        line
        for line in markdown.splitlines()
        if line.startswith("| claim:")
    ]
    assert key_claim_rows
    assert all("missing-provenance" not in row for row in key_claim_rows)
    assert all("serenity:" in row for row in key_claim_rows)


def test_render_stock_analysis_report_blocks_unsupported_recommendation_language() -> None:
    result = _ready_analysis()

    try:
        render_stock_analysis_report_markdown(
            result,
            additional_generated_sections={"Unsafe": "You should buy AAPL now with a target price of 100."},
        )
    except ReportSafetyViolation as exc:
        assert exc.findings
        phrases = {finding.phrase for finding in exc.findings}
        assert "you should buy" in phrases
        assert "target price" in phrases
    else:
        raise AssertionError("unsupported recommendation language should be blocked")


def test_write_stock_analysis_report_artifacts_creates_markdown_and_manifest(tmp_path) -> None:
    result = _ready_analysis()

    artifact = write_stock_analysis_report_artifacts(result, tmp_path)

    report_text = artifact.markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    html = artifact.ui_path.read_text(encoding="utf-8")

    assert artifact.markdown_path == tmp_path / "reports" / "stock-analysis-report.md"
    assert artifact.manifest_path == tmp_path / "analysis-report-manifest.json"
    assert artifact.ui_path == tmp_path / "index.html"
    assert "## Key Claims And Provenance" in report_text
    assert 'data-report-href="reports/stock-analysis-report.md"' in html
    assert "Serenity Stock Analysis Report" in html
    assert manifest["symbol"] == "AAPL"
    assert manifest["reports"]["stock_analysis"] == "reports/stock-analysis-report.md"
    assert manifest["reports"]["ui"] == "index.html"
    assert manifest["research_only"] is True
    assert manifest["safety"]["passed"] is True
    assert manifest["key_claims"]
    assert all(claim["provenance_refs"] for claim in manifest["key_claims"])


def test_write_stock_analysis_manifest_includes_runtime_parity_semantics(tmp_path) -> None:
    result = _ready_analysis()

    artifact = write_stock_analysis_report_artifacts(
        result,
        tmp_path,
        generated_at=FIXED_GENERATED_AT,
    )

    report_text = artifact.markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))

    assert "**Generated:** 2026-07-10 00:00 UTC" in report_text
    assert manifest["schema_version"] == 1
    assert manifest["artifact_type"] == "stock_analysis_report"
    assert set(manifest) == {
        "schema_version",
        "artifact_type",
        "symbol",
        "stock_name",
        "query",
        "generated_at",
        "research_only",
        "readiness",
        "report_gate",
        "source_coverage",
        "skeptical_review",
        "reports",
        "safety",
        "key_claims",
    }
    assert manifest["query"] == "AAPL market data research"
    assert manifest["generated_at"] == "2026-07-10T00:00:00+00:00"
    assert manifest["research_only"] is True
    assert manifest["readiness"] == {
        "status": result.readiness.status,
        "reason": result.report_gate.reason,
        "flags": result.readiness.flag_codes,
    }
    assert manifest["report_gate"] == result.report_gate.to_dict()
    assert manifest["source_coverage"]["status"] == result.readiness.status
    assert manifest["source_coverage"]["focus_ticker"] == "AAPL"
    assert manifest["source_coverage"]["evidence_count"] == len(result.evidence)
    assert manifest["source_coverage"]["primary_count"] == 3
    assert manifest["source_coverage"]["risk_count"] == 1
    assert manifest["source_coverage"]["flags"] == []
    assert manifest["skeptical_review"]["summary"] == (
        "Risk coverage uses 1 risk or invalidation evidence item."
    )
    assert manifest["skeptical_review"]["counter_thesis"] == [
        "AAPL closed at 41.1 on 2026-07-06"
    ]
    assert manifest["safety"]["boundary"] == "research only; not investment advice"
    assert all(claim["provenance_refs"] for claim in manifest["key_claims"])


def test_write_stock_analysis_manifest_emits_missing_risk_counter_thesis(tmp_path) -> None:
    manager = StubMarketDataManager(
        quote_result(price=42.5),
        daily_bars(include_risk_bar=False),
    )
    result = StockAnalysisPipeline(market_data=manager).analyze(
        "AAPL",
        stock_name="Apple Inc.",
        query="AAPL market data research",
    )

    artifact = write_stock_analysis_report_artifacts(
        result,
        tmp_path,
        generated_at=FIXED_GENERATED_AT,
    )
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))

    assert manifest["source_coverage"]["risk_count"] == 0
    assert manifest["skeptical_review"]["summary"] == (
        "Risk coverage is incomplete because no risk or invalidation evidence item is available."
    )
    assert manifest["skeptical_review"]["counter_thesis"] == [
        "missing_risk_coverage: No negative, risk, or invalidation evidence was retrieved for AAPL."
    ]


def test_write_stock_analysis_manifest_normalizes_generated_at_to_utc(tmp_path) -> None:
    result = _ready_analysis()
    generated_at = datetime(
        2026,
        7,
        10,
        8,
        0,
        tzinfo=timezone(timedelta(hours=8)),
    )

    artifact = write_stock_analysis_report_artifacts(
        result,
        tmp_path,
        generated_at=generated_at,
    )

    report_text = artifact.markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))

    assert "**Generated:** 2026-07-10 00:00 UTC" in report_text
    assert manifest["generated_at"] == "2026-07-10T00:00:00+00:00"


def test_write_stock_analysis_manifest_rejects_naive_generated_at(tmp_path) -> None:
    result = _ready_analysis()

    with pytest.raises(ValueError, match="generated_at must be timezone-aware"):
        write_stock_analysis_report_artifacts(
            result,
            tmp_path,
            generated_at=datetime(2026, 7, 10, 0, 0),
        )
