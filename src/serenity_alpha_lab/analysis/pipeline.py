from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from serenity_alpha_lab.market_data import DailyBar, MarketDataManager, ProviderFetchResult
from serenity_alpha_lab.scoring import score_research_question, summarize_scorecard

from .context import StockAnalysisContext, build_analysis_context


class MarketDataRuntime(Protocol):
    def get_realtime_quote(self, stock_code: str) -> ProviderFetchResult:
        ...

    def get_daily_bars(self, stock_code: str, *, days: int = 30) -> list[DailyBar]:
        ...


@dataclass(frozen=True)
class AnalysisReadiness:
    status: str
    flag_codes: list[str]
    source_coverage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "flag_codes": list(self.flag_codes),
            "source_coverage": dict(self.source_coverage),
        }


@dataclass(frozen=True)
class AnalysisReportGate:
    status: str
    reason: str
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "research_only": self.research_only,
        }


@dataclass(frozen=True)
class ResearchSignals:
    score: int
    rating: str
    confidence: str
    gaps: list[str]
    factor_scores: dict[str, int]
    evidence_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "rating": self.rating,
            "confidence": self.confidence,
            "gaps": list(self.gaps),
            "factor_scores": dict(self.factor_scores),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class StockAnalysisResult:
    symbol: str
    stock_name: str
    market: str
    status: str
    research_only: bool
    context: StockAnalysisContext
    readiness: AnalysisReadiness
    report_gate: AnalysisReportGate
    signals: ResearchSignals
    evidence: list[dict[str, Any]]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "stock_name": self.stock_name,
            "market": self.market,
            "status": self.status,
            "research_only": self.research_only,
            "readiness": self.readiness.to_dict(),
            "report_gate": self.report_gate.to_dict(),
            "signals": self.signals.to_dict(),
            "evidence": list(self.evidence),
            "diagnostics": dict(self.diagnostics),
        }


class AnalysisReadinessGate:
    def evaluate(self, context: StockAnalysisContext) -> AnalysisReadiness:
        coverage = context.source_coverage
        return AnalysisReadiness(
            status=context.readiness_status,
            flag_codes=[flag.code for flag in coverage.flags],
            source_coverage=dict(context.metadata.get("source_coverage", {})),
        )

    def report_gate(self, readiness: AnalysisReadiness) -> AnalysisReportGate:
        if readiness.status == "ready":
            return AnalysisReportGate(status="available", reason="readiness_ready")
        return AnalysisReportGate(status="blocked", reason="readiness_not_ready")


class StockAnalysisPipeline:
    def __init__(
        self,
        *,
        market_data: MarketDataRuntime | None = None,
        readiness_gate: AnalysisReadinessGate | None = None,
    ) -> None:
        self.market_data = market_data or MarketDataManager()
        self.readiness_gate = readiness_gate or AnalysisReadinessGate()

    def analyze(
        self,
        stock_code: str,
        *,
        stock_name: str = "",
        query: str = "",
        days: int = 30,
    ) -> StockAnalysisResult:
        fetch_result = self.market_data.get_realtime_quote(stock_code)
        bars = self.market_data.get_daily_bars(stock_code, days=days)
        context = build_analysis_context(
            stock_code=stock_code,
            stock_name=stock_name,
            quote=fetch_result.quote,
            daily_bars=bars,
            diagnostics=fetch_result.diagnostics,
            query=query,
        )
        readiness = self.readiness_gate.evaluate(context)
        report_gate = self.readiness_gate.report_gate(readiness)
        score = score_research_question(context.evidence)
        summary = summarize_scorecard(score)
        signals = ResearchSignals(
            score=score.total,
            rating=summary.rating,
            confidence=summary.confidence,
            gaps=list(summary.gaps),
            factor_scores={name: factor.value for name, factor in score.factors.items()},
            evidence_ids=[item.id for item in context.evidence],
        )
        status = "completed" if readiness.status in {"ready", "needs_work"} else "blocked"
        return StockAnalysisResult(
            symbol=context.subject.code,
            stock_name=context.subject.stock_name,
            market=context.subject.market,
            status=status,
            research_only=True,
            context=context,
            readiness=readiness,
            report_gate=report_gate,
            signals=signals,
            evidence=[_evidence_to_dict(item) for item in context.evidence],
            diagnostics={
                "provider_status": fetch_result.diagnostics.status,
                "attempts": [attempt.to_dict() for attempt in fetch_result.diagnostics.attempts],
            },
        )


def _evidence_to_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_title": item.source_title,
        "source_url": item.source_url,
        "published_at": item.published_at.isoformat(),
        "claim": item.claim,
        "summary": item.summary,
        "tickers": list(item.tickers),
        "themes": list(item.themes),
        "supply_chain_layer": item.supply_chain_layer,
        "direction": item.direction,
        "strength": item.strength,
        "confidence": item.confidence,
        "factor_impacts": dict(item.factor_impacts),
        "claim_type": item.claim_type,
        "source_excerpt": item.source_excerpt,
    }
