from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.costs import CostBreakdown
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec


BACKTEST_PERFORMANCE_METRIC_CONTRACT_VERSION = "quant.backtest_performance_metrics@1.0.0"
BACKTEST_PERFORMANCE_METRIC_SCHEMA_NAME = "quant.backtest.performance_metrics"
BACKTEST_PERFORMANCE_METRIC_SCHEMA_VERSION = "1.0.0"
BACKTEST_PERFORMANCE_METRIC_ENGINE_VERSION = "cn_a_share_performance_metric_calculator@1.0.0"
BACKTEST_PERFORMANCE_METRIC_SET_VERSION = "backtest_performance_metrics@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_METRIC_QUANT = Decimal("0.000001")


class BacktestPerformanceMetricError(ValueError):
    """Raised when performance metric inputs violate the contract."""


class BacktestMetricFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class BacktestMetricDefinition:
    metric_id: str
    category: str
    formula_version: str
    formula: str
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required_string("metric_id", self.metric_id))
        object.__setattr__(self, "category", _required_string("category", self.category))
        object.__setattr__(self, "formula_version", _required_string("formula_version", self.formula_version))
        object.__setattr__(self, "formula", _required_string("formula", self.formula))
        object.__setattr__(self, "description", _required_string("description", self.description))

    def to_record(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "category": self.category,
            "formula_version": self.formula_version,
            "formula": self.formula,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class BacktestMetricRegistry:
    registry_version: str
    definitions: Sequence[BacktestMetricDefinition]

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_version", _required_string("registry_version", self.registry_version))
        definitions = tuple(self.definitions)
        for definition in definitions:
            if type(definition) is not BacktestMetricDefinition:
                raise BacktestPerformanceMetricError("definitions must contain BacktestMetricDefinition values")
        if len({definition.metric_id for definition in definitions}) != len(definitions):
            raise BacktestPerformanceMetricError("duplicate metric definitions are not allowed")
        object.__setattr__(self, "definitions", definitions)

    @classmethod
    def default(cls) -> BacktestMetricRegistry:
        return cls(
            registry_version=BACKTEST_PERFORMANCE_METRIC_SET_VERSION,
            definitions=(
                BacktestMetricDefinition(
                    "cumulative_return",
                    "returns",
                    "cumulative_return@1.0.0",
                    "ending_equity / starting_equity - 1",
                    "Total portfolio return over the sample period.",
                ),
                BacktestMetricDefinition(
                    "annualized_return",
                    "returns",
                    "annualized_return@1.0.0",
                    "(1 + cumulative_return) ** (annualization_days / period_count) - 1",
                    "Annualized geometric return using the policy annualization day count.",
                ),
                BacktestMetricDefinition(
                    "annualized_volatility",
                    "risk",
                    "annualized_volatility@1.0.0",
                    "sample_stdev(period_returns) * sqrt(annualization_days)",
                    "Annualized sample volatility of portfolio period returns.",
                ),
                BacktestMetricDefinition(
                    "sharpe_ratio",
                    "risk",
                    "sharpe_ratio@1.0.0",
                    "(annualized_return - risk_free_rate) / annualized_volatility",
                    "Annualized excess return per unit of annualized volatility.",
                ),
                BacktestMetricDefinition(
                    "sortino_ratio",
                    "risk",
                    "sortino_ratio@1.0.0",
                    "(annualized_return - risk_free_rate) / annualized_downside_deviation",
                    "Annualized excess return per unit of annualized downside deviation.",
                ),
                BacktestMetricDefinition(
                    "max_drawdown",
                    "drawdown",
                    "max_drawdown@1.0.0",
                    "max((running_peak - equity) / running_peak)",
                    "Maximum peak-to-trough portfolio equity loss.",
                ),
                BacktestMetricDefinition(
                    "max_drawdown_duration_periods",
                    "drawdown",
                    "max_drawdown_duration_periods@1.0.0",
                    "maximum consecutive periods below previous equity peak",
                    "Longest underwater duration measured in return periods.",
                ),
                BacktestMetricDefinition(
                    "calmar_ratio",
                    "drawdown",
                    "calmar_ratio@1.0.0",
                    "annualized_return / max_drawdown",
                    "Annualized return per unit of maximum drawdown.",
                ),
                BacktestMetricDefinition(
                    "win_rate",
                    "trading",
                    "win_rate@1.0.0",
                    "profitable_closed_trades / closed_trade_count",
                    "Share of closed trade outcomes with positive realized P&L.",
                ),
                BacktestMetricDefinition(
                    "profit_loss_ratio",
                    "trading",
                    "profit_loss_ratio@1.0.0",
                    "average_winning_trade / abs(average_losing_trade)",
                    "Average realized gain divided by average realized loss magnitude.",
                ),
                BacktestMetricDefinition(
                    "turnover_rate",
                    "trading",
                    "turnover_rate@1.0.0",
                    "mean((buy_notional + sell_notional) / equity)",
                    "Average rebalance turnover over supplied turnover observations.",
                ),
                BacktestMetricDefinition(
                    "cost_ratio",
                    "cost",
                    "cost_ratio@1.0.0",
                    "sum(transaction_cost) / sum(gross_traded_amount)",
                    "Trading costs as a share of gross traded amount.",
                ),
                BacktestMetricDefinition(
                    "tracking_error",
                    "benchmark",
                    "tracking_error@1.0.0",
                    "sample_stdev(portfolio_returns - benchmark_returns) * sqrt(annualization_days)",
                    "Annualized sample standard deviation of active returns.",
                ),
                BacktestMetricDefinition(
                    "information_ratio",
                    "benchmark",
                    "information_ratio@1.0.0",
                    "(portfolio_annualized_return - benchmark_annualized_return) / tracking_error",
                    "Annualized active return per unit of tracking error.",
                ),
                BacktestMetricDefinition(
                    "industry_exposure",
                    "exposure",
                    "industry_exposure@1.0.0",
                    "average and maximum industry weights over supplied exposure observations",
                    "Sample-period average and max industry exposure weights.",
                ),
            ),
        )

    def definition(self, metric_id: str) -> BacktestMetricDefinition:
        metric_id = _required_string("metric_id", metric_id)
        for definition in self.definitions:
            if definition.metric_id == metric_id:
                return definition
        raise BacktestPerformanceMetricError(f"unknown metric_id: {metric_id}")

    @property
    def formula_versions(self) -> Mapping[str, str]:
        return MappingProxyType({definition.metric_id: definition.formula_version for definition in self.definitions})

    def to_record(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "definitions": [definition.to_record() for definition in self.definitions],
        }


@dataclass(frozen=True, slots=True)
class BacktestPerformanceMetricPolicy:
    policy_id: str
    policy_version: str
    frequency: BacktestMetricFrequency | str
    annualization_days: int
    risk_free_rate: Decimal | int | str
    metric_set_version: str = BACKTEST_PERFORMANCE_METRIC_SET_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "policy_version", _required_string("policy_version", self.policy_version))
        object.__setattr__(self, "frequency", _enum_value(BacktestMetricFrequency, "frequency", self.frequency))
        if type(self.annualization_days) is not int or self.annualization_days <= 0:
            raise BacktestPerformanceMetricError("annualization_days must be a positive integer")
        object.__setattr__(self, "risk_free_rate", _decimal_value("risk_free_rate", self.risk_free_rate))
        object.__setattr__(self, "metric_set_version", _required_string("metric_set_version", self.metric_set_version))

    def to_record(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "frequency": self.frequency.value,
            "annualization_days": self.annualization_days,
            "risk_free_rate": _decimal_to_string(self.risk_free_rate),
            "metric_set_version": self.metric_set_version,
        }


@dataclass(frozen=True, slots=True)
class BacktestEquityPoint:
    valuation_date: date
    equity: Decimal | int | str
    benchmark_value: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        _require_date("valuation_date", self.valuation_date)
        object.__setattr__(self, "equity", _decimal_min("equity", self.equity, Decimal("0"), exclusive=True))
        object.__setattr__(
            self,
            "benchmark_value",
            _optional_decimal_min("benchmark_value", self.benchmark_value, Decimal("0"), exclusive=True),
        )

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "valuation_date": self.valuation_date.isoformat(),
            "equity": _decimal_to_string(self.equity),
        }
        _set_if_present(record, "benchmark_value", _optional_decimal_to_string(self.benchmark_value))
        return record


@dataclass(frozen=True, slots=True)
class BacktestTurnoverObservation:
    valuation_date: date
    buy_notional: Decimal | int | str
    sell_notional: Decimal | int | str
    equity: Decimal | int | str

    def __post_init__(self) -> None:
        _require_date("valuation_date", self.valuation_date)
        object.__setattr__(self, "buy_notional", _decimal_min("buy_notional", self.buy_notional, Decimal("0")))
        object.__setattr__(self, "sell_notional", _decimal_min("sell_notional", self.sell_notional, Decimal("0")))
        object.__setattr__(self, "equity", _decimal_min("equity", self.equity, Decimal("0"), exclusive=True))

    @property
    def turnover_rate(self) -> Decimal:
        return (self.buy_notional + self.sell_notional) / self.equity

    def to_record(self) -> dict[str, object]:
        return {
            "valuation_date": self.valuation_date.isoformat(),
            "buy_notional": _decimal_to_string(self.buy_notional),
            "sell_notional": _decimal_to_string(self.sell_notional),
            "equity": _decimal_to_string(self.equity),
            "turnover_rate": _decimal_to_string(_quantize_metric(self.turnover_rate)),
        }


@dataclass(frozen=True, slots=True)
class BacktestTradeOutcome:
    trade_id: str
    instrument_id: InstrumentId
    realized_pnl: Decimal | int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "trade_id", _required_string("trade_id", self.trade_id))
        if type(self.instrument_id) is not InstrumentId:
            raise BacktestPerformanceMetricError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "realized_pnl", _decimal_value("realized_pnl", self.realized_pnl))

    def to_record(self) -> dict[str, object]:
        return {
            "trade_id": self.trade_id,
            "instrument_id": self.instrument_id.canonical,
            "realized_pnl": _decimal_to_string(self.realized_pnl),
        }


@dataclass(frozen=True, slots=True)
class BacktestIndustryExposurePoint:
    valuation_date: date
    weights: Mapping[str, Decimal | int | str]

    def __post_init__(self) -> None:
        _require_date("valuation_date", self.valuation_date)
        if not isinstance(self.weights, Mapping) or not self.weights:
            raise BacktestPerformanceMetricError("industry exposure weights must be a non-empty mapping")
        weights: dict[str, Decimal] = {}
        for industry, weight in self.weights.items():
            weights[_required_string("industry", industry)] = _decimal_ratio("industry weight", weight)
        object.__setattr__(self, "weights", MappingProxyType(dict(sorted(weights.items()))))

    def to_record(self) -> dict[str, object]:
        return {
            "valuation_date": self.valuation_date.isoformat(),
            "weights": {industry: _decimal_to_string(weight) for industry, weight in self.weights.items()},
        }


@dataclass(frozen=True, slots=True)
class BacktestPerformanceMetricReport:
    report_id: str
    spec_id: str
    spec_hash: str
    run_id: str
    stage_id: str
    sample_start: date
    sample_end: date
    frequency: BacktestMetricFrequency | str
    annualization_days: int
    risk_free_rate: Decimal | int | str
    period_count: int
    metric_registry: BacktestMetricRegistry
    returns: Mapping[str, object]
    risk: Mapping[str, object]
    drawdown: Mapping[str, object]
    trading: Mapping[str, object]
    costs: Mapping[str, object]
    benchmark: Mapping[str, object]
    industry_exposure: Mapping[str, object]
    warnings: Sequence[str] = ()
    contract_version: str = BACKTEST_PERFORMANCE_METRIC_CONTRACT_VERSION
    schema_name: str = BACKTEST_PERFORMANCE_METRIC_SCHEMA_NAME
    schema_version: str = BACKTEST_PERFORMANCE_METRIC_SCHEMA_VERSION
    engine_version: str = BACKTEST_PERFORMANCE_METRIC_ENGINE_VERSION
    metric_set_version: str = BACKTEST_PERFORMANCE_METRIC_SET_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _required_string("report_id", self.report_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        _require_date("sample_start", self.sample_start)
        _require_date("sample_end", self.sample_end)
        if self.sample_end < self.sample_start:
            raise BacktestPerformanceMetricError("sample_end cannot be before sample_start")
        object.__setattr__(self, "frequency", _enum_value(BacktestMetricFrequency, "frequency", self.frequency))
        if type(self.annualization_days) is not int or self.annualization_days <= 0:
            raise BacktestPerformanceMetricError("annualization_days must be a positive integer")
        object.__setattr__(self, "risk_free_rate", _decimal_value("risk_free_rate", self.risk_free_rate))
        if type(self.period_count) is not int or self.period_count <= 0:
            raise BacktestPerformanceMetricError("period_count must be a positive integer")
        if type(self.metric_registry) is not BacktestMetricRegistry:
            raise BacktestPerformanceMetricError("metric_registry must be a BacktestMetricRegistry")
        for name in ("returns", "risk", "drawdown", "trading", "costs", "benchmark", "industry_exposure"):
            object.__setattr__(self, name, _freeze_value(getattr(self, name)))
        object.__setattr__(self, "warnings", tuple(_required_string("warning", warning) for warning in self.warnings))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "metric_set_version", _required_string("metric_set_version", self.metric_set_version))

    @property
    def metric_formula_versions(self) -> Mapping[str, str]:
        return self.metric_registry.formula_versions

    def formula_version(self, metric_id: str) -> str:
        return self.metric_registry.definition(metric_id).formula_version

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "metric_set_version": self.metric_set_version,
            "report_id": self.report_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "sample_start": self.sample_start.isoformat(),
            "sample_end": self.sample_end.isoformat(),
            "frequency": self.frequency.value,
            "annualization_days": self.annualization_days,
            "risk_free_rate": _decimal_to_string(self.risk_free_rate),
            "period_count": self.period_count,
            "metric_formula_versions": dict(self.metric_formula_versions),
            "returns": _thaw_value(self.returns),
            "risk": _thaw_value(self.risk),
            "drawdown": _thaw_value(self.drawdown),
            "trading": _thaw_value(self.trading),
            "costs": _thaw_value(self.costs),
            "benchmark": _thaw_value(self.benchmark),
            "industry_exposure": _thaw_value(self.industry_exposure),
            "warnings": list(self.warnings),
        }


class BacktestPerformanceMetricCalculator:
    def __init__(
        self,
        *,
        spec: BacktestSpec,
        policy: BacktestPerformanceMetricPolicy,
        metric_registry: BacktestMetricRegistry | None = None,
    ) -> None:
        if type(spec) is not BacktestSpec:
            raise BacktestPerformanceMetricError("spec must be a BacktestSpec")
        if type(policy) is not BacktestPerformanceMetricPolicy:
            raise BacktestPerformanceMetricError("policy must be a BacktestPerformanceMetricPolicy")
        if metric_registry is None:
            metric_registry = BacktestMetricRegistry.default()
        if type(metric_registry) is not BacktestMetricRegistry:
            raise BacktestPerformanceMetricError("metric_registry must be a BacktestMetricRegistry")
        if policy.metric_set_version != metric_registry.registry_version:
            raise BacktestPerformanceMetricError("policy metric_set_version must match registry version")
        self.spec = spec
        self.policy = policy
        self.metric_registry = metric_registry

    def calculate(
        self,
        *,
        run_id: str,
        stage_id: str,
        equity_curve: Sequence[BacktestEquityPoint],
        turnover_observations: Sequence[BacktestTurnoverObservation] = (),
        trade_outcomes: Sequence[BacktestTradeOutcome] = (),
        cost_breakdowns: Sequence[CostBreakdown] = (),
        industry_exposures: Sequence[BacktestIndustryExposurePoint] = (),
    ) -> BacktestPerformanceMetricReport:
        run_id = _required_string("run_id", run_id)
        stage_id = _required_string("stage_id", stage_id)
        points = _normalize_equity_curve(equity_curve)
        period_returns = _period_returns(point.equity for point in points)
        benchmark_returns = self._benchmark_returns(points)
        warnings: list[str] = []
        if benchmark_returns is None:
            warnings.append("benchmark metrics are not evaluable because benchmark_value is absent")

        returns = self._returns(points=points, period_count=len(period_returns))
        cumulative_return = points[-1].equity / points[0].equity - Decimal("1")
        annualized_return_raw = _annualize_return_raw(
            cumulative_return,
            len(period_returns),
            self.policy.annualization_days,
        )
        risk = self._risk(
            period_returns=period_returns,
            annualized_return_raw=annualized_return_raw,
            warnings=warnings,
        )
        drawdown = self._drawdown(points=points, annualized_return_raw=annualized_return_raw)
        trading = self._trading(
            trade_outcomes=_normalize_trade_outcomes(trade_outcomes),
            turnover_observations=_normalize_turnover_observations(turnover_observations),
        )
        costs = self._costs(cost_breakdowns=_normalize_cost_breakdowns(cost_breakdowns), points=points)
        benchmark = self._benchmark(
            period_returns=period_returns,
            benchmark_returns=benchmark_returns,
            portfolio_annualized_return_raw=annualized_return_raw,
            points=points,
        )
        industry_exposure = self._industry_exposure(_normalize_industry_exposures(industry_exposures))
        payload = {
            "spec_id": self.spec.spec_id,
            "spec_hash": self.spec.spec_hash,
            "run_id": run_id,
            "stage_id": stage_id,
            "sample_start": points[0].valuation_date.isoformat(),
            "sample_end": points[-1].valuation_date.isoformat(),
            "frequency": self.policy.frequency.value,
            "annualization_days": self.policy.annualization_days,
            "risk_free_rate": _decimal_to_string(self.policy.risk_free_rate),
            "period_count": len(period_returns),
            "returns": _thaw_value(returns),
            "risk": _thaw_value(risk),
            "drawdown": _thaw_value(drawdown),
            "trading": _thaw_value(trading),
            "costs": _thaw_value(costs),
            "benchmark": _thaw_value(benchmark),
            "industry_exposure": _thaw_value(industry_exposure),
            "warnings": warnings,
        }
        return BacktestPerformanceMetricReport(
            report_id=_stable_id("metrics", payload),
            spec_id=self.spec.spec_id,
            spec_hash=self.spec.spec_hash,
            run_id=run_id,
            stage_id=stage_id,
            sample_start=points[0].valuation_date,
            sample_end=points[-1].valuation_date,
            frequency=self.policy.frequency,
            annualization_days=self.policy.annualization_days,
            risk_free_rate=self.policy.risk_free_rate,
            period_count=len(period_returns),
            metric_registry=self.metric_registry,
            returns=returns,
            risk=risk,
            drawdown=drawdown,
            trading=trading,
            costs=costs,
            benchmark=benchmark,
            industry_exposure=industry_exposure,
            warnings=tuple(warnings),
        )

    def _returns(self, *, points: Sequence[BacktestEquityPoint], period_count: int) -> Mapping[str, object]:
        starting_equity = points[0].equity
        ending_equity = points[-1].equity
        cumulative_return = ending_equity / starting_equity - Decimal("1")
        annualized_return = _annualize_return(cumulative_return, period_count, self.policy.annualization_days)
        return MappingProxyType(
            {
                "starting_equity": _quantize_metric(starting_equity),
                "ending_equity": _quantize_metric(ending_equity),
                "cumulative_return": _quantize_metric(cumulative_return),
                "annualized_return": annualized_return,
            }
        )

    def _risk(
        self,
        *,
        period_returns: Sequence[Decimal],
        annualized_return_raw: float,
        warnings: list[str],
    ) -> Mapping[str, object]:
        annualized_volatility = _annualized_sample_stdev(period_returns, self.policy.annualization_days)
        annualized_volatility_raw = _annualized_sample_stdev_raw(period_returns, self.policy.annualization_days)
        annualized_excess_raw = annualized_return_raw - float(self.policy.risk_free_rate)
        annualized_excess = _quantize_float(annualized_excess_raw)
        sharpe = None if annualized_volatility_raw in (None, 0.0) else _quantize_float(annualized_excess_raw / annualized_volatility_raw)
        downside_deviation = _annualized_downside_deviation(
            period_returns=period_returns,
            risk_free_rate=self.policy.risk_free_rate,
            annualization_days=self.policy.annualization_days,
        )
        downside_deviation_raw = _annualized_downside_deviation_raw(
            period_returns=period_returns,
            risk_free_rate=self.policy.risk_free_rate,
            annualization_days=self.policy.annualization_days,
        )
        sortino = None if downside_deviation_raw in (None, 0.0) else _quantize_float(annualized_excess_raw / downside_deviation_raw)
        if annualized_volatility is None:
            warnings.append("annualized volatility is not evaluable with fewer than two return periods")
        if downside_deviation is None:
            warnings.append("sortino ratio is not evaluable because downside deviation is zero")
        return MappingProxyType(
            {
                "annualized_volatility": annualized_volatility,
                "annualized_excess_return": annualized_excess,
                "sharpe_ratio": sharpe,
                "annualized_downside_deviation": downside_deviation,
                "sortino_ratio": sortino,
            }
        )

    def _drawdown(self, *, points: Sequence[BacktestEquityPoint], annualized_return_raw: float) -> Mapping[str, object]:
        peak = points[0].equity
        max_drawdown = Decimal("0")
        current_duration = 0
        max_duration = 0
        trough_date = points[0].valuation_date
        peak_date = points[0].valuation_date
        max_drawdown_peak_date = points[0].valuation_date
        for point in points:
            if point.equity >= peak:
                peak = point.equity
                peak_date = point.valuation_date
                current_duration = 0
                continue
            current_duration += 1
            drawdown = (peak - point.equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_peak_date = peak_date
                trough_date = point.valuation_date
            max_duration = max(max_duration, current_duration)
        calmar = None if max_drawdown == 0 else _quantize_float(annualized_return_raw / float(max_drawdown))
        return MappingProxyType(
            {
                "max_drawdown": _quantize_metric(max_drawdown),
                "max_drawdown_duration_periods": max_duration,
                "max_drawdown_peak_date": max_drawdown_peak_date.isoformat(),
                "max_drawdown_trough_date": trough_date.isoformat(),
                "calmar_ratio": calmar,
            }
        )

    def _trading(
        self,
        *,
        trade_outcomes: Sequence[BacktestTradeOutcome],
        turnover_observations: Sequence[BacktestTurnoverObservation],
    ) -> Mapping[str, object]:
        winning = [trade.realized_pnl for trade in trade_outcomes if trade.realized_pnl > 0]
        losing = [trade.realized_pnl for trade in trade_outcomes if trade.realized_pnl < 0]
        closed_count = len(trade_outcomes)
        win_rate = None if closed_count == 0 else _quantize_metric(Decimal(len(winning)) / Decimal(closed_count))
        avg_win = None if not winning else sum(winning, Decimal("0")) / Decimal(len(winning))
        avg_loss = None if not losing else sum(losing, Decimal("0")) / Decimal(len(losing))
        profit_loss_ratio = None if avg_win is None or avg_loss in (None, Decimal("0")) else _safe_divide(avg_win, abs(avg_loss))
        turnover_values = [observation.turnover_rate for observation in turnover_observations]
        turnover_rate = None if not turnover_values else _quantize_metric(_mean_decimal(turnover_values))
        total_turnover_notional = sum(
            (observation.buy_notional + observation.sell_notional for observation in turnover_observations),
            Decimal("0"),
        )
        return MappingProxyType(
            {
                "closed_trade_count": closed_count,
                "winning_trade_count": len(winning),
                "losing_trade_count": len(losing),
                "win_rate": win_rate,
                "average_win": None if avg_win is None else _quantize_metric(avg_win),
                "average_loss": None if avg_loss is None else _quantize_metric(avg_loss),
                "profit_loss_ratio": profit_loss_ratio,
                "turnover_observation_count": len(turnover_observations),
                "turnover_rate": turnover_rate,
                "total_turnover_notional": _quantize_metric(total_turnover_notional),
            }
        )

    def _costs(self, *, cost_breakdowns: Sequence[CostBreakdown], points: Sequence[BacktestEquityPoint]) -> Mapping[str, object]:
        for cost in cost_breakdowns:
            if cost.spec_hash != self.spec.spec_hash:
                raise BacktestPerformanceMetricError("cost_breakdown spec_hash must match BacktestSpec")
        total_cost = sum((cost.total_cost for cost in cost_breakdowns), Decimal("0"))
        gross_traded_amount = sum((cost.gross_amount for cost in cost_breakdowns), Decimal("0"))
        average_equity = _mean_decimal([point.equity for point in points])
        return MappingProxyType(
            {
                "cost_observation_count": len(cost_breakdowns),
                "total_cost": _quantize_metric(total_cost),
                "gross_traded_amount": _quantize_metric(gross_traded_amount),
                "cost_ratio": _safe_divide(total_cost, gross_traded_amount),
                "cost_to_average_equity": _safe_divide(total_cost, average_equity),
            }
        )

    def _benchmark(
        self,
        *,
        period_returns: Sequence[Decimal],
        benchmark_returns: Sequence[Decimal] | None,
        portfolio_annualized_return_raw: float,
        points: Sequence[BacktestEquityPoint],
    ) -> Mapping[str, object]:
        if benchmark_returns is None:
            return MappingProxyType(
                {
                    "benchmark_cumulative_return": None,
                    "benchmark_annualized_return": None,
                    "active_cumulative_return": None,
                    "tracking_error": None,
                    "information_ratio": None,
                }
            )
        assert points[0].benchmark_value is not None
        assert points[-1].benchmark_value is not None
        benchmark_cumulative = points[-1].benchmark_value / points[0].benchmark_value - Decimal("1")
        benchmark_annualized = _annualize_return(benchmark_cumulative, len(benchmark_returns), self.policy.annualization_days)
        benchmark_annualized_raw = _annualize_return_raw(
            benchmark_cumulative,
            len(benchmark_returns),
            self.policy.annualization_days,
        )
        active_returns = tuple(portfolio - benchmark for portfolio, benchmark in zip(period_returns, benchmark_returns, strict=True))
        tracking_error = _annualized_sample_stdev(active_returns, self.policy.annualization_days)
        tracking_error_raw = _annualized_sample_stdev_raw(active_returns, self.policy.annualization_days)
        information_ratio = (
            None
            if tracking_error_raw in (None, 0.0)
            else _quantize_float((portfolio_annualized_return_raw - benchmark_annualized_raw) / tracking_error_raw)
        )
        return MappingProxyType(
            {
                "benchmark_cumulative_return": _quantize_metric(benchmark_cumulative),
                "benchmark_annualized_return": benchmark_annualized,
                "active_cumulative_return": _quantize_metric(
                    (points[-1].equity / points[0].equity - Decimal("1")) - benchmark_cumulative
                ),
                "tracking_error": tracking_error,
                "information_ratio": information_ratio,
            }
        )

    def _benchmark_returns(self, points: Sequence[BacktestEquityPoint]) -> tuple[Decimal, ...] | None:
        has_benchmark = [point.benchmark_value is not None for point in points]
        if all(has_benchmark):
            return _period_returns(point.benchmark_value for point in points)  # type: ignore[arg-type]
        if any(has_benchmark):
            raise BacktestPerformanceMetricError("benchmark_value must be present for every equity point or none")
        return None

    def _industry_exposure(self, exposures: Sequence[BacktestIndustryExposurePoint]) -> Mapping[str, object]:
        if not exposures:
            return MappingProxyType({"observation_count": 0, "average_weights": MappingProxyType({}), "max_weights": MappingProxyType({})})
        industries = sorted({industry for exposure in exposures for industry in exposure.weights})
        average_weights: dict[str, Decimal] = {}
        max_weights: dict[str, Decimal] = {}
        for industry in industries:
            values = [exposure.weights.get(industry, Decimal("0")) for exposure in exposures]
            average_weights[industry] = _quantize_metric(_mean_decimal(values))
            max_weights[industry] = _quantize_metric(max(values))
        return MappingProxyType(
            {
                "observation_count": len(exposures),
                "average_weights": MappingProxyType(average_weights),
                "max_weights": MappingProxyType(max_weights),
            }
        )


def _normalize_equity_curve(equity_curve: Sequence[BacktestEquityPoint]) -> tuple[BacktestEquityPoint, ...]:
    points = tuple(equity_curve)
    if len(points) < 2:
        raise BacktestPerformanceMetricError("at least two equity points are required")
    for point in points:
        if type(point) is not BacktestEquityPoint:
            raise BacktestPerformanceMetricError("equity_curve must contain BacktestEquityPoint values")
    sorted_points = tuple(sorted(points, key=lambda point: point.valuation_date))
    if len({point.valuation_date for point in sorted_points}) != len(sorted_points):
        raise BacktestPerformanceMetricError("equity_curve cannot contain duplicate valuation_date values")
    return sorted_points


def _normalize_turnover_observations(
    observations: Sequence[BacktestTurnoverObservation],
) -> tuple[BacktestTurnoverObservation, ...]:
    normalized = tuple(observations)
    for observation in normalized:
        if type(observation) is not BacktestTurnoverObservation:
            raise BacktestPerformanceMetricError("turnover_observations must contain BacktestTurnoverObservation values")
    return tuple(sorted(normalized, key=lambda observation: observation.valuation_date))


def _normalize_trade_outcomes(trade_outcomes: Sequence[BacktestTradeOutcome]) -> tuple[BacktestTradeOutcome, ...]:
    normalized = tuple(trade_outcomes)
    for trade in normalized:
        if type(trade) is not BacktestTradeOutcome:
            raise BacktestPerformanceMetricError("trade_outcomes must contain BacktestTradeOutcome values")
    if len({trade.trade_id for trade in normalized}) != len(normalized):
        raise BacktestPerformanceMetricError("trade_outcomes cannot contain duplicate trade_id values")
    return tuple(sorted(normalized, key=lambda trade: trade.trade_id))


def _normalize_cost_breakdowns(cost_breakdowns: Sequence[CostBreakdown]) -> tuple[CostBreakdown, ...]:
    normalized = tuple(cost_breakdowns)
    for cost in normalized:
        if type(cost) is not CostBreakdown:
            raise BacktestPerformanceMetricError("cost_breakdowns must contain CostBreakdown values")
    if len({cost.execution_id for cost in normalized}) != len(normalized):
        raise BacktestPerformanceMetricError("cost_breakdowns cannot contain duplicate execution_id values")
    return tuple(sorted(normalized, key=lambda cost: cost.execution_id))


def _normalize_industry_exposures(
    industry_exposures: Sequence[BacktestIndustryExposurePoint],
) -> tuple[BacktestIndustryExposurePoint, ...]:
    normalized = tuple(industry_exposures)
    for exposure in normalized:
        if type(exposure) is not BacktestIndustryExposurePoint:
            raise BacktestPerformanceMetricError("industry_exposures must contain BacktestIndustryExposurePoint values")
    if len({exposure.valuation_date for exposure in normalized}) != len(normalized):
        raise BacktestPerformanceMetricError("industry_exposures cannot contain duplicate valuation_date values")
    return tuple(sorted(normalized, key=lambda exposure: exposure.valuation_date))


def _period_returns(values: Sequence[Decimal] | Any) -> tuple[Decimal, ...]:
    series = tuple(values)
    if len(series) < 2:
        raise BacktestPerformanceMetricError("at least two values are required to compute returns")
    returns: list[Decimal] = []
    for previous, current in zip(series, series[1:], strict=False):
        if previous <= 0:
            raise BacktestPerformanceMetricError("return base values must be positive")
        returns.append(current / previous - Decimal("1"))
    return tuple(returns)


def _annualize_return(cumulative_return: Decimal, period_count: int, annualization_days: int) -> Decimal:
    return _quantize_float(_annualize_return_raw(cumulative_return, period_count, annualization_days))


def _annualize_return_raw(cumulative_return: Decimal, period_count: int, annualization_days: int) -> float:
    if period_count <= 0:
        raise BacktestPerformanceMetricError("period_count must be positive")
    factor = float(Decimal("1") + cumulative_return)
    if factor <= 0:
        return -1.0
    return factor ** (annualization_days / period_count) - 1.0


def _annualized_sample_stdev(values: Sequence[Decimal], annualization_days: int) -> Decimal | None:
    raw = _annualized_sample_stdev_raw(values, annualization_days)
    return None if raw is None else _quantize_float(raw)


def _annualized_sample_stdev_raw(values: Sequence[Decimal], annualization_days: int) -> float | None:
    if len(values) < 2:
        return None
    stdev = statistics.stdev(float(value) for value in values)
    return stdev * math.sqrt(annualization_days)


def _annualized_downside_deviation(
    *,
    period_returns: Sequence[Decimal],
    risk_free_rate: Decimal,
    annualization_days: int,
) -> Decimal | None:
    raw = _annualized_downside_deviation_raw(
        period_returns=period_returns,
        risk_free_rate=risk_free_rate,
        annualization_days=annualization_days,
    )
    return None if raw is None else _quantize_float(raw)


def _annualized_downside_deviation_raw(
    *,
    period_returns: Sequence[Decimal],
    risk_free_rate: Decimal,
    annualization_days: int,
) -> float | None:
    if not period_returns:
        return None
    period_risk_free = risk_free_rate / Decimal(annualization_days)
    downside = [min(Decimal("0"), period_return - period_risk_free) for period_return in period_returns]
    mean_square = sum((value * value for value in downside), Decimal("0")) / Decimal(len(downside))
    if mean_square == 0:
        return None
    return math.sqrt(float(mean_square)) * math.sqrt(annualization_days)


def _safe_divide(numerator: object, denominator: object) -> Decimal | None:
    if numerator is None or denominator is None:
        return None
    numerator_decimal = _decimal_value("numerator", numerator)
    denominator_decimal = _decimal_value("denominator", denominator)
    if denominator_decimal == 0:
        return None
    return _quantize_metric(numerator_decimal / denominator_decimal)


def _mean_decimal(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise BacktestPerformanceMetricError("cannot compute mean of empty sequence")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(nested) for key, nested in sorted(value.items(), key=lambda item: str(item[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_to_string(value)
    if isinstance(value, Mapping):
        return {key: _thaw_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise BacktestPerformanceMetricError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise BacktestPerformanceMetricError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BacktestPerformanceMetricError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise BacktestPerformanceMetricError(f"{field_name} must be finite")
    return decimal


def _decimal_min(
    field_name: str,
    value: object,
    minimum: Decimal,
    *,
    exclusive: bool = False,
) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if exclusive:
        if decimal <= minimum:
            raise BacktestPerformanceMetricError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise BacktestPerformanceMetricError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_ratio(field_name: str, value: object) -> Decimal:
    decimal = _decimal_min(field_name, value, Decimal("0"))
    if decimal > Decimal("1"):
        raise BacktestPerformanceMetricError(f"{field_name} cannot exceed 1")
    return decimal


def _optional_decimal_min(
    field_name: str,
    value: object,
    minimum: Decimal,
    *,
    exclusive: bool = False,
) -> Decimal | None:
    if value is None:
        return None
    return _decimal_min(field_name, value, minimum, exclusive=exclusive)


def _quantize_float(value: float) -> Decimal:
    if not math.isfinite(value):
        raise BacktestPerformanceMetricError("metric value must be finite")
    return _quantize_metric(Decimal(f"{value:.12f}"))


def _quantize_metric(value: object) -> Decimal:
    return _decimal_value("metric", value).quantize(_METRIC_QUANT)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    return None if value is None else _decimal_to_string(value)


def _required_string(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BacktestPerformanceMetricError(f"{field_name} is required")
    return value


def _validate_sha256(field_name: str, value: object) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(value):
        raise BacktestPerformanceMetricError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise BacktestPerformanceMetricError(f"{field_name} must be a date")


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value
