from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean
from typing import Any, Sequence


@dataclass(frozen=True)
class PortfolioObservation:
    symbol: str
    research_weight: float
    evidence_ids: list[str] = field(default_factory=list)
    thesis: str = ""
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol.strip().upper(),
            "research_weight": float(self.research_weight),
            "evidence_ids": list(self.evidence_ids),
            "thesis": self.thesis,
            "risk_flags": list(self.risk_flags),
        }


@dataclass(frozen=True)
class PortfolioResearchSnapshot:
    portfolio_id: str
    as_of: date
    items: list[PortfolioObservation]
    diagnostics: dict[str, Any]
    research_only: bool = True
    validation_scope: str = "portfolio_research_snapshot"

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "as_of": self.as_of.isoformat(),
            "research_only": self.research_only,
            "validation_scope": self.validation_scope,
            "items": [item.to_dict() for item in self.items],
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class BacktestObservation:
    symbol: str
    analysis_date: date
    evaluation_window_days: int
    start_value: float
    end_value: float
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def return_pct(self) -> float:
        if self.start_value <= 0:
            return 0.0
        return (self.end_value - self.start_value) / self.start_value * 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol.strip().upper(),
            "analysis_date": self.analysis_date.isoformat(),
            "evaluation_window_days": int(self.evaluation_window_days),
            "start_value": float(self.start_value),
            "end_value": float(self.end_value),
            "return_pct": self.return_pct,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class BacktestValidationSummary:
    hypothesis_id: str
    observations: list[BacktestObservation]
    diagnostics: dict[str, Any]
    research_only: bool = True
    validation_scope: str = "historical_research_validation"

    def to_dict(self) -> dict[str, Any]:
        returns = [item.return_pct for item in self.observations]
        return {
            "hypothesis_id": self.hypothesis_id,
            "research_only": self.research_only,
            "validation_scope": self.validation_scope,
            "completed_count": len(self.observations),
            "positive_count": sum(1 for value in returns if value > 0),
            "negative_count": sum(1 for value in returns if value < 0),
            "average_return_pct": mean(returns) if returns else None,
            "observations": [item.to_dict() for item in self.observations],
            "diagnostics": dict(self.diagnostics),
        }


def build_portfolio_research_snapshot(
    *,
    portfolio_id: str,
    as_of: date,
    observations: Sequence[PortfolioObservation],
) -> PortfolioResearchSnapshot:
    items = list(observations)
    missing_evidence = [item.symbol for item in items if not item.evidence_ids]
    return PortfolioResearchSnapshot(
        portfolio_id=portfolio_id,
        as_of=as_of,
        items=items,
        diagnostics={
            "automation_enabled": False,
            "execution_integration": "disabled",
            "missing_evidence_symbols": missing_evidence,
        },
    )


def summarize_backtest_validation(
    *,
    hypothesis_id: str,
    observations: Sequence[BacktestObservation],
) -> BacktestValidationSummary:
    items = list(observations)
    return BacktestValidationSummary(
        hypothesis_id=hypothesis_id,
        observations=items,
        diagnostics={
            "future_performance_disclaimer": "historical_validation_only",
            "automation_enabled": False,
            "evaluation_count": len(items),
        },
    )
