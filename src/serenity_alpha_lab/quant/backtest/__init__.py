"""Formal portfolio backtest contracts.

SAL-P4-003 defines the immutable BacktestSpec. SAL-P4-004 adds the compact
BacktestArtifact output contract. Execution, order generation, ledger replay,
risk evaluation and APIs are introduced by later P4 tasks.
"""

from serenity_alpha_lab.quant.backtest.artifacts import (
    BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE,
    BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME,
    BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION,
    BACKTEST_ARTIFACT_CONTRACT_VERSION,
    BACKTEST_ARTIFACT_ENGINE_SCOPE,
    BACKTEST_ARTIFACT_ENGINE_VERSION,
    BacktestArtifactBundle,
    BacktestArtifactError,
    BacktestArtifactKind,
    BacktestArtifactState,
    BacktestOutputArtifact,
    publish_backtest_artifact_bundle,
)
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
    "BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE",
    "BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME",
    "BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION",
    "BACKTEST_ARTIFACT_CONTRACT_VERSION",
    "BACKTEST_ARTIFACT_ENGINE_SCOPE",
    "BACKTEST_ARTIFACT_ENGINE_VERSION",
    "BACKTEST_SPEC_CONTRACT_VERSION",
    "BACKTEST_SPEC_ENGINE_VERSION",
    "BACKTEST_SPEC_SCHEMA_NAME",
    "BACKTEST_SPEC_SCHEMA_VERSION",
    "BacktestArtifactBundle",
    "BacktestArtifactError",
    "BacktestArtifactKind",
    "BacktestArtifactState",
    "BacktestCostSpec",
    "BacktestDatasetSpec",
    "BacktestExecutionSpec",
    "BacktestOutputArtifact",
    "BacktestRiskSpec",
    "BacktestSpec",
    "BacktestSpecError",
    "BacktestStrategySpec",
    "BacktestUniverseSpec",
    "publish_backtest_artifact_bundle",
]
