from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Sequence

from serenity_alpha_lab.evidence import EvidenceItem, dedupe_evidence
from serenity_alpha_lab.market_data import DailyBar, ProviderDiagnostics, RealtimeQuote, normalize_market_symbol
from serenity_alpha_lab.source_coverage import SourceCoverageReport, assess_source_coverage


@dataclass(frozen=True)
class AnalysisSubject:
    code: str
    stock_name: str
    market: str
    currency: str


@dataclass(frozen=True)
class StockAnalysisContext:
    subject: AnalysisSubject
    query: str
    evidence: list[EvidenceItem]
    source_coverage: SourceCoverageReport
    readiness_status: str
    metadata: dict[str, Any]


def build_analysis_context(
    *,
    stock_code: str,
    stock_name: str = "",
    quote: RealtimeQuote | None,
    daily_bars: Sequence[DailyBar],
    diagnostics: ProviderDiagnostics,
    query: str = "",
) -> StockAnalysisContext:
    symbol = normalize_market_symbol(stock_code)
    subject = AnalysisSubject(
        code=symbol.canonical_code,
        stock_name=stock_name or (quote.name if quote else ""),
        market=symbol.market,
        currency=symbol.currency,
    )
    evidence = dedupe_evidence(
        [
            *(_quote_evidence(subject, quote) if quote else []),
            *_daily_bar_evidence(subject, daily_bars),
        ]
    )
    source_coverage = assess_source_coverage(evidence, focus_ticker=subject.code)
    readiness_status = _readiness_status(source_coverage)
    metadata = {
        "provider_status": diagnostics.status,
        "attempts": [attempt.to_dict() for attempt in diagnostics.attempts],
        "source_coverage": _source_coverage_dict(source_coverage),
    }
    return StockAnalysisContext(
        subject=subject,
        query=query or f"{subject.code} stock analysis",
        evidence=evidence,
        source_coverage=source_coverage,
        readiness_status=readiness_status,
        metadata=metadata,
    )


def _quote_evidence(subject: AnalysisSubject, quote: RealtimeQuote) -> list[EvidenceItem]:
    if quote.price is None or quote.price <= 0:
        return []
    published_at = _date_from_iso(quote.provider_timestamp or quote.fetched_at)
    price = _format_number(quote.price)
    change = _format_number(quote.change_pct)
    claim = f"{subject.code} latest normalized quote was {price} {subject.currency}"
    if quote.change_pct is not None:
        claim += f" with {change}% session change"
    summary = (
        f"Provider {quote.source} returned a normalized quote for {subject.code}; "
        f"price={price}, change_pct={change if quote.change_pct is not None else 'n/a'}, "
        f"volume={quote.volume if quote.volume is not None else 'n/a'}."
    )
    return [
        EvidenceItem(
            id=f"serenity:market-data:{subject.code}:quote:{published_at.isoformat()}",
            source_title=f"Market data quote for {subject.code}",
            source_url=f"serenity://market-data/{subject.code}/quote/{published_at.isoformat()}",
            published_at=published_at,
            claim=claim,
            summary=summary,
            tickers=[subject.code],
            themes=["market-data", "primary-source", subject.market],
            supply_chain_layer="market data",
            direction=_direction_from_change(quote.change_pct),
            strength="primary",
            confidence=0.88,
            factor_impacts={
                "demand_certainty": 10 if (quote.change_pct or 0) > 0 else 4,
                "evidence_quality": 24,
                "invalidation_clarity": 4,
            },
            claim_type="fact",
            source_excerpt=summary,
        )
    ]


def _daily_bar_evidence(subject: AnalysisSubject, daily_bars: Sequence[DailyBar]) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for bar in daily_bars:
        if bar.close is None or not bar.date:
            continue
        published_at = _date_from_iso(bar.date)
        pct_chg = bar.pct_chg
        direction = _direction_from_change(pct_chg)
        claim_type = "risk" if direction == "negative" else "fact"
        suffix = "risk" if direction == "negative" else "bar"
        summary = (
            f"{subject.code} daily bar on {published_at.isoformat()} from {bar.source}: "
            f"close={_format_number(bar.close)}, pct_chg={_format_number(pct_chg) if pct_chg is not None else 'n/a'}, "
            f"volume={bar.volume if bar.volume is not None else 'n/a'}."
        )
        evidence.append(
            EvidenceItem(
                id=f"serenity:market-data:{subject.code}:{suffix}:{published_at.isoformat()}",
                source_title=f"Market data daily bar for {subject.code}",
                source_url=f"serenity://market-data/{subject.code}/daily/{published_at.isoformat()}",
                published_at=published_at,
                claim=f"{subject.code} closed at {_format_number(bar.close)} on {published_at.isoformat()}",
                summary=summary,
                tickers=[subject.code],
                themes=["market-data", "price-history", subject.market],
                supply_chain_layer="market data",
                direction=direction,
                strength="derived",
                confidence=0.74,
                factor_impacts=_bar_factor_impacts(direction, pct_chg),
                claim_type=claim_type,
                source_excerpt=summary,
            )
        )
    return evidence


def _bar_factor_impacts(direction: str, pct_chg: float | None) -> dict[str, int]:
    magnitude = abs(pct_chg or 0.0)
    if direction == "negative":
        return {
            "crowding_risk": min(30, 10 + round(magnitude * 3)),
            "evidence_quality": 12,
            "invalidation_clarity": 10,
        }
    return {
        "demand_certainty": min(24, 8 + round(magnitude * 2)),
        "evidence_quality": 12,
        "invalidation_clarity": 4,
    }


def _readiness_status(report: SourceCoverageReport) -> str:
    if any(flag.severity == "critical" for flag in report.flags):
        return "blocked"
    if report.flags:
        return "needs_work"
    return "ready"


def _source_coverage_dict(report: SourceCoverageReport) -> dict[str, Any]:
    return {
        "focus_ticker": report.focus_ticker,
        "evidence_count": report.evidence_count,
        "focus_evidence_count": report.focus_evidence_count,
        "primary_count": report.primary_count,
        "risk_count": report.risk_count,
        "methodology_share": report.methodology_share,
        "placeholder_share": report.placeholder_share,
        "external_non_serenity_count": report.external_non_serenity_count,
        "flags": [flag.__dict__ for flag in report.flags],
    }


def _date_from_iso(value: str | None) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def _direction_from_change(change: float | None) -> str:
    if change is None:
        return "neutral"
    if change < 0:
        return "negative"
    if change > 0:
        return "positive"
    return "neutral"


def _format_number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
