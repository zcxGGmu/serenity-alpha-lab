from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.costs import CostBreakdown, CostLineItem, CostLineItemName
from serenity_alpha_lab.quant.backtest.metrics import (
    BACKTEST_PERFORMANCE_METRIC_CONTRACT_VERSION,
    BACKTEST_PERFORMANCE_METRIC_SET_VERSION,
    BacktestEquityPoint,
    BacktestIndustryExposurePoint,
    BacktestMetricFrequency,
    BacktestPerformanceMetricCalculator,
    BacktestPerformanceMetricError,
    BacktestPerformanceMetricPolicy,
    BacktestTradeOutcome,
    BacktestTurnoverObservation,
)
from serenity_alpha_lab.quant.backtest.orders import OrderSide
from serenity_alpha_lab.quant.backtest.spec import (
    BacktestCostSpec,
    BacktestDatasetSpec,
    BacktestExecutionSpec,
    BacktestRiskSpec,
    BacktestSpec,
    BacktestStrategySpec,
    BacktestUniverseSpec,
)


NOW = datetime(2026, 7, 26, 9, 30, tzinfo=UTC)
SPEC_HASH_CODE = "sha256:" + "8" * 64
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
FACTOR_QUALITY_VERSION = "fdv_" + "3" * 32
INSTRUMENT_KWEICHOW = InstrumentId.parse("600519.XSHG")
INSTRUMENT_PINGAN = InstrumentId.parse("000001.XSHE")


def test_performance_metrics_calculate_returns_risk_drawdown_and_sample_metadata() -> None:
    report = BacktestPerformanceMetricCalculator(spec=_formal_backtest_spec(), policy=_metric_policy()).calculate(
        run_id="run-metrics",
        stage_id="stage-metrics",
        equity_curve=_equity_curve(),
        turnover_observations=_turnover_observations(),
        trade_outcomes=_trade_outcomes(),
        cost_breakdowns=_cost_breakdowns(),
        industry_exposures=_industry_exposures(),
    )

    assert report.contract_version == BACKTEST_PERFORMANCE_METRIC_CONTRACT_VERSION
    assert report.metric_set_version == BACKTEST_PERFORMANCE_METRIC_SET_VERSION
    assert report.sample_start == date(2026, 1, 2)
    assert report.sample_end == date(2026, 1, 8)
    assert report.frequency is BacktestMetricFrequency.DAILY
    assert report.annualization_days == 252
    assert report.risk_free_rate == Decimal("0.0300")
    assert report.period_count == 4

    assert report.returns["cumulative_return"] == Decimal("0.320000")
    assert report.returns["annualized_return"] == Decimal("39460052.157899")
    assert report.risk["annualized_volatility"] == Decimal("1.307832")
    assert report.risk["sharpe_ratio"] == Decimal("30172106.573197")
    assert report.risk["sortino_ratio"] == Decimal("109087279.142505")
    assert report.drawdown["max_drawdown"] == Decimal("0.045455")
    assert report.drawdown["max_drawdown_duration_periods"] == 1
    assert report.drawdown["max_drawdown_peak_date"] == "2026-01-05"
    assert report.drawdown["max_drawdown_trough_date"] == "2026-01-06"
    assert report.drawdown["calmar_ratio"] == Decimal("868121147.473772")
    assert report.formula_version("sharpe_ratio") == "sharpe_ratio@1.0.0"

    record = report.to_record()
    assert record["frequency"] == "daily"
    assert record["returns"]["cumulative_return"] == "0.320000"
    assert record["metric_formula_versions"]["tracking_error"] == "tracking_error@1.0.0"
    json.dumps(record, sort_keys=True)


def test_performance_metrics_calculate_trading_cost_benchmark_and_exposure_metrics() -> None:
    report = BacktestPerformanceMetricCalculator(spec=_formal_backtest_spec(), policy=_metric_policy()).calculate(
        run_id="run-metrics",
        stage_id="stage-metrics",
        equity_curve=_equity_curve(),
        turnover_observations=_turnover_observations(),
        trade_outcomes=_trade_outcomes(),
        cost_breakdowns=_cost_breakdowns(),
        industry_exposures=_industry_exposures(),
    )

    assert report.trading["win_rate"] == Decimal("0.666667")
    assert report.trading["profit_loss_ratio"] == Decimal("2.500000")
    assert report.trading["closed_trade_count"] == 3
    assert report.trading["turnover_rate"] == Decimal("0.250000")
    assert report.costs["total_cost"] == Decimal("18.000000")
    assert report.costs["cost_ratio"] == Decimal("0.004500")
    assert report.costs["cost_to_average_equity"] == Decimal("0.000016")
    assert report.benchmark["benchmark_cumulative_return"] == Decimal("0.150000")
    assert report.benchmark["active_cumulative_return"] == Decimal("0.170000")
    assert report.benchmark["tracking_error"] == Decimal("0.666171")
    assert report.benchmark["information_ratio"] == Decimal("59224085.772864")
    assert report.industry_exposure["average_weights"] == {
        "consumer": Decimal("0.550000"),
        "financials": Decimal("0.450000"),
    }
    assert report.industry_exposure["max_weights"] == {
        "consumer": Decimal("0.600000"),
        "financials": Decimal("0.500000"),
    }


def test_performance_metrics_reject_bad_inputs_and_stays_inside_pure_boundary() -> None:
    calculator = BacktestPerformanceMetricCalculator(spec=_formal_backtest_spec(), policy=_metric_policy())

    with pytest.raises(BacktestPerformanceMetricError, match="at least two equity points"):
        calculator.calculate(
            run_id="run-metrics",
            stage_id="stage-metrics",
            equity_curve=(_equity_curve()[0],),
        )

    with pytest.raises(BacktestPerformanceMetricError, match="benchmark_value"):
        calculator.calculate(
            run_id="run-metrics",
            stage_id="stage-metrics",
            equity_curve=(
                BacktestEquityPoint(date(2026, 1, 2), Decimal("100"), Decimal("100")),
                BacktestEquityPoint(date(2026, 1, 5), Decimal("101"), None),
            ),
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/metrics.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _metric_policy() -> BacktestPerformanceMetricPolicy:
    return BacktestPerformanceMetricPolicy(
        policy_id="cn_a_share_daily_metrics",
        policy_version="1.0.0",
        frequency=BacktestMetricFrequency.DAILY,
        annualization_days=252,
        risk_free_rate=Decimal("0.0300"),
    )


def _equity_curve() -> tuple[BacktestEquityPoint, ...]:
    return (
        BacktestEquityPoint(date(2026, 1, 2), Decimal("1000000"), Decimal("1000")),
        BacktestEquityPoint(date(2026, 1, 5), Decimal("1100000"), Decimal("1050")),
        BacktestEquityPoint(date(2026, 1, 6), Decimal("1050000"), Decimal("1020")),
        BacktestEquityPoint(date(2026, 1, 7), Decimal("1200000"), Decimal("1080")),
        BacktestEquityPoint(date(2026, 1, 8), Decimal("1320000"), Decimal("1150")),
    )


def _turnover_observations() -> tuple[BacktestTurnoverObservation, ...]:
    return (
        BacktestTurnoverObservation(
            valuation_date=date(2026, 1, 5),
            buy_notional=Decimal("100000"),
            sell_notional=Decimal("120000"),
            equity=Decimal("1100000"),
        ),
        BacktestTurnoverObservation(
            valuation_date=date(2026, 1, 7),
            buy_notional=Decimal("180000"),
            sell_notional=Decimal("180000"),
            equity=Decimal("1200000"),
        ),
    )


def _trade_outcomes() -> tuple[BacktestTradeOutcome, ...]:
    return (
        BacktestTradeOutcome("trade-win-1", INSTRUMENT_KWEICHOW, Decimal("100")),
        BacktestTradeOutcome("trade-loss-1", INSTRUMENT_PINGAN, Decimal("-50")),
        BacktestTradeOutcome("trade-win-2", INSTRUMENT_KWEICHOW, Decimal("150")),
    )


def _cost_breakdowns() -> tuple[CostBreakdown, ...]:
    return (
        _cost_breakdown("exe-cost-1", Decimal("2000"), Decimal("8")),
        _cost_breakdown("exe-cost-2", Decimal("2000"), Decimal("10")),
    )


def _cost_breakdown(execution_id: str, gross_amount: Decimal, total_cost: Decimal) -> CostBreakdown:
    return CostBreakdown(
        spec_hash=_formal_backtest_spec().spec_hash,
        order_id=f"ord-{execution_id}",
        execution_id=execution_id,
        instrument_id=INSTRUMENT_KWEICHOW.canonical,
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        fill_price=gross_amount / Decimal("100"),
        effective_price=gross_amount / Decimal("100"),
        gross_amount=gross_amount,
        total_cost=total_cost,
        participation_rate=Decimal("0.0500"),
        max_participation_rate=Decimal("0.1000"),
        line_items=(
            CostLineItem(
                name=CostLineItemName.COMMISSION,
                amount=total_cost,
                rate_bps=Decimal("0"),
                basis_amount=gross_amount,
            ),
        ),
        filled_at=NOW,
        pre_cost_cash_amount=gross_amount,
        post_cost_cash_amount=gross_amount + total_cost,
    )


def _industry_exposures() -> tuple[BacktestIndustryExposurePoint, ...]:
    return (
        BacktestIndustryExposurePoint(
            valuation_date=date(2026, 1, 5),
            weights={"consumer": Decimal("0.60"), "financials": Decimal("0.40")},
        ),
        BacktestIndustryExposurePoint(
            valuation_date=date(2026, 1, 7),
            weights={"consumer": Decimal("0.50"), "financials": Decimal("0.50")},
        ),
    )


def _formal_backtest_spec() -> BacktestSpec:
    dataset_versions = {
        "adjusted_daily_bars": "dsv_" + "a" * 32,
        "raw_daily_bars": "dsv_" + "b" * 32,
        "trading_calendar": "dsv_" + "c" * 32,
        "corporate_actions": "dsv_" + "d" * 32,
        "instrument_master": "dsv_" + "e" * 32,
    }
    dataset_hashes = {name: f"sha256:{index:064x}" for index, name in enumerate(sorted(dataset_versions), start=1)}
    return BacktestSpec(
        spec_id="formal_cn_quality_momentum_v1",
        created_at=NOW,
        created_by_run_id="run-metrics",
        dataset=BacktestDatasetSpec(dataset_versions=dataset_versions, dataset_hashes=dataset_hashes),
        universe=BacktestUniverseSpec(
            universe_version_id="dsv_" + "f" * 32,
            universe_name="cn_a_share_l0",
            as_of=date(2026, 1, 5),
            membership_policy="pit_membership_as_of_decision_time",
        ),
        strategy=BacktestStrategySpec(
            strategy_id="quality_momentum_weekly",
            strategy_version="1.0.0",
            strategy_kind="screen_snapshot_rebalance",
            source_commit="abcdef1234567890",
            code_hash=SPEC_HASH_CODE,
            screen_definition_version_id=SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=SCREEN_SNAPSHOT_ID,
            factor_version_ids=(FACTOR_QUALITY_VERSION,),
        ),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        benchmark="000300.XSHG",
        currency="CNY",
        initial_capital=Decimal("100000.00"),
        cash_rate_bps=Decimal("150.0"),
        execution=BacktestExecutionSpec(
            signal_timing="after_close",
            execution_timing="next_open",
            signal_price_field="close",
            execution_price_field="open",
            rebalance_calendar="cn_a_share_trading_calendar",
            valuation_calendar="cn_a_share_trading_calendar",
            rebalance_frequency="weekly",
            settlement_lag_days=1,
            lot_size=100,
            random_seed=20260725,
        ),
        costs=BacktestCostSpec(
            commission_bps=Decimal("3.0"),
            min_commission=Decimal("5.00"),
            stamp_tax_bps=Decimal("10.0"),
            transfer_fee_bps=Decimal("0.2"),
            slippage_bps=Decimal("5.0"),
            impact_bps=Decimal("2.0"),
            max_participation_rate=Decimal("0.1000"),
        ),
        risk=BacktestRiskSpec(
            risk_policy_version="risk_policy.cn_a_share@1.0.0",
            max_weight_per_instrument=Decimal("0.1000"),
            max_weight_per_industry=Decimal("0.3000"),
            max_turnover_per_rebalance=Decimal("0.4000"),
            cash_buffer_pct=Decimal("0.0200"),
            liquidity_floor_amount=Decimal("1000000.00"),
        ),
        artifact_output_level="full_audit",
    )
