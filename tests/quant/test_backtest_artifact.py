from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.quant.backtest.artifacts import (
    BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE,
    BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME,
    BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION,
    BacktestArtifactBundle,
    BacktestArtifactError,
    BacktestArtifactKind,
    BacktestArtifactState,
    BacktestOutputArtifact,
    publish_backtest_artifact_bundle,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
SPEC_HASH = "sha256:" + "1" * 64
DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "a" * 32,
    "raw_daily_bars": "dsv_" + "b" * 32,
    "trading_calendar": "dsv_" + "c" * 32,
    "corporate_actions": "dsv_" + "d" * 32,
    "instrument_master": "dsv_" + "e" * 32,
}


def test_backtest_artifact_bundle_records_uri_only_required_outputs(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    outputs = _required_outputs(store)

    bundle = BacktestArtifactBundle(
        run_id="run-backtest-artifact",
        stage_id="stage-artifacts",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        dataset_versions=DATASET_VERSIONS,
        state=BacktestArtifactState.FORMAL,
        outputs=outputs,
        created_at=NOW,
        engine_version="portfolio_backtest_artifacts@1.0.0",
        trace_id="trace-artifacts",
    )

    assert bundle.schema_name == BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME
    assert bundle.schema_version == BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION
    assert bundle.state is BacktestArtifactState.FORMAL
    assert bundle.spec_hash == SPEC_HASH
    assert set(bundle.outputs) == {kind for kind in BacktestArtifactKind}
    assert bundle.outputs[BacktestArtifactKind.ORDERS].row_count == 3
    assert bundle.outputs[BacktestArtifactKind.METRICS].schema_name == "quant.backtest.metrics"

    record = bundle.to_record()
    assert record["spec_hash"] == SPEC_HASH
    assert record["dataset_versions"] == DATASET_VERSIONS
    assert record["state"] == "formal"
    assert record["trace"] == {
        "trace_id": "trace-artifacts",
        "run_id": "run-backtest-artifact",
        "stage_id": "stage-artifacts",
    }
    assert record["outputs"]["orders"]["artifact_uri"].startswith("artifact://sha256/")
    assert record["outputs"]["orders"]["content_hash"].startswith("sha256:")
    assert record["outputs"]["orders"]["row_count"] == 3
    assert "rows" not in json.dumps(record, sort_keys=True)
    json.dumps(record, sort_keys=True)


def test_backtest_artifact_bundle_publishes_compact_summary_artifact(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    bundle = BacktestArtifactBundle(
        run_id="run-backtest-artifact",
        stage_id="stage-artifacts",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        dataset_versions=DATASET_VERSIONS,
        state="preview",
        outputs=_required_outputs(store),
        created_at=NOW,
        warnings=("preview uses a shortened date range",),
    )

    artifact = publish_backtest_artifact_bundle(bundle, store)
    repeated_artifact = publish_backtest_artifact_bundle(bundle, store)
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert repeated_artifact.artifact_id == artifact.artifact_id
    assert artifact.schema_name == BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME
    assert artifact.schema_version == BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION
    assert artifact.content_type == BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE
    assert payload["bundle_id"] == bundle.bundle_id
    assert payload["state"] == "preview"
    assert payload["outputs"]["metrics"]["artifact_id"] == bundle.outputs[BacktestArtifactKind.METRICS].artifact_id
    assert "records" not in payload["outputs"]["orders"]
    assert "dataframe" not in json.dumps(payload, sort_keys=True).lower()


def test_backtest_artifact_contract_rejects_invalid_states_versions_and_manifests(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    outputs = _required_outputs(store)

    with pytest.raises(BacktestArtifactError, match="required output kinds"):
        BacktestArtifactBundle(
            run_id="run-backtest-artifact",
            spec_id="formal_cn_quality_momentum_v1",
            spec_hash=SPEC_HASH,
            dataset_versions=DATASET_VERSIONS,
            state=BacktestArtifactState.FORMAL,
            outputs=tuple(output for output in outputs if output.kind is not BacktestArtifactKind.AUDIT),
            created_at=NOW,
        )

    with pytest.raises(BacktestArtifactError, match="concrete Dataset Version"):
        BacktestArtifactBundle(
            run_id="run-backtest-artifact",
            spec_id="formal_cn_quality_momentum_v1",
            spec_hash=SPEC_HASH,
            dataset_versions={**DATASET_VERSIONS, "raw_daily_bars": "latest"},
            state=BacktestArtifactState.FORMAL,
            outputs=outputs,
            created_at=NOW,
        )

    with pytest.raises(BacktestArtifactError, match="partial bundles require warnings or errors"):
        BacktestArtifactBundle(
            run_id="run-backtest-artifact",
            spec_id="formal_cn_quality_momentum_v1",
            spec_hash=SPEC_HASH,
            dataset_versions=DATASET_VERSIONS,
            state=BacktestArtifactState.PARTIAL,
            outputs=outputs,
            created_at=NOW,
        )

    with pytest.raises(BacktestArtifactError, match="legacy Signal Evaluation"):
        BacktestArtifactBundle(
            run_id="run-backtest-artifact",
            spec_id="formal_cn_quality_momentum_v1",
            spec_hash=SPEC_HASH,
            dataset_versions=DATASET_VERSIONS,
            state=BacktestArtifactState.FORMAL,
            outputs=outputs,
            created_at=NOW,
            engine_scope="legacy_signal_evaluation",
        )

    manifest = _artifact_manifest(store, "bad-manifest")
    with pytest.raises(BacktestArtifactError, match="content_hash must match artifact manifest"):
        BacktestOutputArtifact(
            kind=BacktestArtifactKind.ORDERS,
            schema_name="quant.backtest.orders",
            schema_version="1.0.0",
            artifact_manifest=manifest,
            content_hash="sha256:" + "9" * 64,
            row_count=1,
        )

    with pytest.raises(BacktestArtifactError, match="row_count"):
        BacktestOutputArtifact(
            kind=BacktestArtifactKind.ORDERS,
            schema_name="quant.backtest.orders",
            schema_version="1.0.0",
            artifact_manifest=manifest,
            content_hash="sha256:" + manifest.sha256,
            row_count=-1,
        )


def _required_outputs(store: LocalArtifactStore) -> tuple[BacktestOutputArtifact, ...]:
    specs = (
        (BacktestArtifactKind.ORDERS, "quant.backtest.orders", 3),
        (BacktestArtifactKind.EXECUTIONS, "quant.backtest.executions", 2),
        (BacktestArtifactKind.POSITIONS, "quant.backtest.positions", 4),
        (BacktestArtifactKind.CASH, "quant.backtest.cash", 6),
        (BacktestArtifactKind.EQUITY_CURVE, "quant.backtest.equity_curve", 6),
        (BacktestArtifactKind.METRICS, "quant.backtest.metrics", 12),
        (BacktestArtifactKind.AUDIT, "quant.backtest.audit", 5),
    )
    outputs: list[BacktestOutputArtifact] = []
    for kind, schema_name, row_count in specs:
        manifest = _artifact_manifest(store, kind.value)
        outputs.append(
            BacktestOutputArtifact(
                kind=kind,
                schema_name=schema_name,
                schema_version="1.0.0",
                artifact_manifest=manifest,
                content_hash="sha256:" + manifest.sha256,
                row_count=row_count,
                partition_keys=("trade_date",)
                if kind in {BacktestArtifactKind.ORDERS, BacktestArtifactKind.EXECUTIONS}
                else (),
            )
        )
    return tuple(outputs)


def _artifact_manifest(store: LocalArtifactStore, name: str) -> ArtifactManifest:
    return store.put_bytes(
        json.dumps({"name": name}, sort_keys=True).encode("utf-8"),
        schema_name=f"quant.backtest.{name}",
        schema_version="1.0.0",
        content_type="application/vnd.serenity.quant.backtest-table+json",
        produced_by_run_id="run-backtest-artifact",
        produced_by_stage_id="stage-artifacts",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
