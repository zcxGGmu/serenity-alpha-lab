"""Formal portfolio backtest input contracts.

SAL-P4-003 defines the immutable BacktestSpec only. Execution, artifacts,
orders, ledger, risk evaluation and APIs are introduced by later P4 tasks.
"""

from serenity_alpha_lab.quant.backtest.spec import (
    BACKTEST_SPEC_CONTRACT_VERSION,
    BACKTEST_SPEC_ENGINE_VERSION,
    BACKTEST_SPEC_SCHEMA_NAME,
    BACKTEST_SPEC_SCHEMA_VERSION,
    BacktestCostSpec,
    BacktestDatasetSpec,
    BacktestExecutionSpec,
    BacktestRiskSpec,
    BacktestSpec,
    BacktestSpecError,
    BacktestStrategySpec,
    BacktestUniverseSpec,
)

__all__ = [
    "BACKTEST_SPEC_CONTRACT_VERSION",
    "BACKTEST_SPEC_ENGINE_VERSION",
    "BACKTEST_SPEC_SCHEMA_NAME",
    "BACKTEST_SPEC_SCHEMA_VERSION",
    "BacktestCostSpec",
    "BacktestDatasetSpec",
    "BacktestExecutionSpec",
    "BacktestRiskSpec",
    "BacktestSpec",
    "BacktestSpecError",
    "BacktestStrategySpec",
    "BacktestUniverseSpec",
]
