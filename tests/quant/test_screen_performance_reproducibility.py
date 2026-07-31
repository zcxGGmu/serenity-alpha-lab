from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from serenity_alpha_lab.quant.screening.performance import (
    SCREEN_PERFORMANCE_REPORT_CONTENT_TYPE,
    SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME,
    SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION,
    ScreenIncrementalBaseline,
    ScreenPerformanceBudget,
    ScreenPerformanceError,
    ScreenStagePerformanceSample,
    build_screen_performance_report,
    default_a_share_screening_budget,
    screen_result_hash,
    publish_screen_performance_report,
)
from serenity_alpha_lab.quant.screening.pipeline import ScreenPipelineStage, ScreenPipelineStageTrace
from serenity_alpha_lab.quant.screening.snapshot import (
    ScreenExplanationStep,
    ScreenSnapshot,
    ScreenSnapshotResult,
    ScreenSnapshotStatus,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 25, 10, 30, tzinfo=UTC)
AS_OF = date(2026, 7, 24)
DATASET_VERSIONS = {
    "universe": "dsv_" + "1" * 32,
    "raw_daily_bars": "dsv_" + "2" * 32,
    "factor_values": "dsv_" + "3" * 32,
    "instrument_master": "dsv_" + "4" * 32,
}
SCREEN_DEFINITION_VERSION_ID = "sdv_" + "a" * 32
CODE_VERSION = "git:eb476ff0"
ENGINE_VERSION = "screen_pipeline@1.0.0"


def test_screen_performance_report_records_budget_reproducibility_bundle_and_artifact(tmp_path: Path) -> None:
    baseline_snapshot = _snapshot(run_id="run-screen-a", trace_id="trace-a", stage_id="stage-a")
    repeated_snapshot = _snapshot(
        run_id="run-screen-b",
        trace_id="trace-b",
        stage_id="stage-b",
        created_at=NOW + timedelta(minutes=5),
    )
    stage_samples = _stage_samples()
    incremental = ScreenIncrementalBaseline(
        changed_dataset_versions={"factor_values": "dsv_" + "9" * 32},
        total_candidate_count=6_000,
        recomputed_candidate_count=240,
        changed_factor_versions=("fdv_" + "b" * 32,),
    )

    report = build_screen_performance_report(
        snapshot=baseline_snapshot,
        repeated_snapshot=repeated_snapshot,
        code_version=CODE_VERSION,
        engine_version=ENGINE_VERSION,
        stage_samples=stage_samples,
        incremental_baseline=incremental,
        budget=default_a_share_screening_budget(),
        cached_query_duration_ms=180.0,
        created_at=NOW,
        trace_id="trace-performance",
        run_id="run-performance",
        stage_id="stage-performance",
    )

    assert report.schema_name == SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME
    assert report.schema_version == SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION
    assert report.acceptance_status == "passed"
    assert report.failure_codes == ()
    assert report.total_duration_ms == pytest.approx(900.0)
    assert report.peak_memory_mb == pytest.approx(188.0)
    assert report.reproducibility.reproducible is True
    assert report.reproducibility.baseline_result_hash == report.reproducibility.repeated_result_hash
    assert report.run_bundle.code_version == CODE_VERSION
    assert report.run_bundle.engine_version == ENGINE_VERSION
    assert report.run_bundle.result_hash == screen_result_hash(
        baseline_snapshot,
        code_version=CODE_VERSION,
        engine_version=ENGINE_VERSION,
    )
    assert report.run_bundle.screen_snapshot_id == baseline_snapshot.screen_snapshot_id
    assert report.run_bundle.pipeline_snapshot_id == baseline_snapshot.pipeline_snapshot_id
    assert report.run_bundle.dataset_versions == DATASET_VERSIONS
    assert report.incremental_baseline.recompute_ratio == pytest.approx(0.04)

    store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = publish_screen_performance_report(report, store)
    repeated_artifact = publish_screen_performance_report(report, store)
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert repeated_artifact.artifact_id == artifact.artifact_id
    assert artifact.schema_name == SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME
    assert artifact.schema_version == SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION
    assert artifact.content_type == SCREEN_PERFORMANCE_REPORT_CONTENT_TYPE
    assert payload["report_id"] == report.report_id
    assert payload["run_bundle"]["result_hash"] == report.run_bundle.result_hash
    assert payload["observed"]["result_row_count"] == len(baseline_snapshot.results)
    assert payload["reproducibility"]["reproducible"] is True


def test_report_fails_when_budget_or_reproducibility_breaks() -> None:
    baseline_snapshot = _snapshot(run_id="run-screen-a")
    drifted_snapshot = _snapshot(
        run_id="run-screen-b",
        result_score_overrides={"600519.XSHG": 98.0},
    )
    slow_samples = (
        ScreenStagePerformanceSample.from_stage_trace(
            ScreenPipelineStageTrace(
                stage=ScreenPipelineStage.L0_UNIVERSE,
                input_count=6_000,
                output_count=5_800,
                excluded_count=200,
            ),
            duration_ms=3_200.0,
            peak_memory_mb=700.0,
        ),
    )
    incremental = ScreenIncrementalBaseline(
        changed_dataset_versions={"factor_values": "dsv_" + "9" * 32},
        total_candidate_count=1_000,
        recomputed_candidate_count=500,
    )

    report = build_screen_performance_report(
        snapshot=baseline_snapshot,
        repeated_snapshot=drifted_snapshot,
        code_version=CODE_VERSION,
        engine_version=ENGINE_VERSION,
        stage_samples=slow_samples,
        incremental_baseline=incremental,
        budget=ScreenPerformanceBudget(
            common_screen_slo_ms=3_000.0,
            cached_query_slo_ms=500.0,
            max_peak_memory_mb=512.0,
            max_result_rows=6_000,
            max_incremental_recompute_ratio=0.15,
        ),
        cached_query_duration_ms=900.0,
        created_at=NOW,
    )

    assert report.acceptance_status == "failed"
    assert set(report.failure_codes) >= {
        "common_screen_slo_exceeded",
        "cached_query_slo_exceeded",
        "peak_memory_budget_exceeded",
        "incremental_recompute_ratio_exceeded",
        "result_reproducibility_failed",
    }
    assert report.reproducibility.reproducible is False
    assert "result_hash_mismatch" in report.reproducibility.mismatch_reasons


def test_performance_contract_rejects_latest_versions_and_invalid_metrics() -> None:
    with pytest.raises(ScreenPerformanceError, match="concrete Dataset Version"):
        ScreenIncrementalBaseline(
            changed_dataset_versions={"factor_values": "latest"},
            total_candidate_count=100,
            recomputed_candidate_count=10,
        )

    with pytest.raises(ScreenPerformanceError, match="duration_ms"):
        ScreenStagePerformanceSample(
            stage=ScreenPipelineStage.L0_UNIVERSE,
            duration_ms=-1.0,
            peak_memory_mb=10.0,
            input_count=100,
            output_count=80,
            excluded_count=20,
        )

    with pytest.raises(ScreenPerformanceError, match="recomputed_candidate_count"):
        ScreenIncrementalBaseline(
            changed_dataset_versions={"factor_values": "dsv_" + "9" * 32},
            total_candidate_count=10,
            recomputed_candidate_count=11,
        )


def _stage_samples() -> tuple[ScreenStagePerformanceSample, ...]:
    traces = (
        (ScreenPipelineStage.L0_UNIVERSE, 6_000, 5_800, 200, 120.0, 160.0),
        (ScreenPipelineStage.L1_PROVIDER, 5_800, 4_200, 1_600, 210.0, 175.0),
        (ScreenPipelineStage.L2_FACTOR, 4_200, 4_000, 200, 330.0, 188.0),
        (ScreenPipelineStage.L3_LLM_OVERLAY, 4_000, 4_000, 0, 40.0, 188.0),
        (ScreenPipelineStage.L4_FINAL, 4_000, 100, 3_900, 200.0, 180.0),
    )
    return tuple(
        ScreenStagePerformanceSample.from_stage_trace(
            ScreenPipelineStageTrace(
                stage=stage,
                input_count=input_count,
                output_count=output_count,
                excluded_count=excluded_count,
            ),
            duration_ms=duration_ms,
            peak_memory_mb=peak_memory_mb,
        )
        for stage, input_count, output_count, excluded_count, duration_ms, peak_memory_mb in traces
    )


def _snapshot(
    *,
    run_id: str,
    trace_id: str = "trace-screen",
    stage_id: str = "stage-screen",
    created_at: datetime = NOW,
    result_score_overrides: dict[str, float] | None = None,
) -> ScreenSnapshot:
    score_overrides = result_score_overrides or {}
    return ScreenSnapshot(
        pipeline_snapshot_id=f"sps_{run_id.replace('-', '_')}",
        definition_version_id=SCREEN_DEFINITION_VERSION_ID,
        as_of=AS_OF,
        dataset_versions=DATASET_VERSIONS,
        created_at=created_at,
        trace_id=trace_id,
        run_id=run_id,
        stage_id=stage_id,
        results=(
            _passed_result(
                "600519.XSHG",
                rank=1,
                score=score_overrides.get("600519.XSHG", 96.0),
                industry="beverage",
            ),
            _passed_result(
                "000001.XSHE",
                rank=2,
                score=score_overrides.get("000001.XSHE", 82.0),
                industry="bank",
            ),
            _failed_result("600091.XSHG"),
        ),
    )


def _passed_result(instrument_id: str, *, rank: int, score: float, industry: str) -> ScreenSnapshotResult:
    scores = {"l1_provider": 85.0, "l2_factor": score, "l4_final": score}
    return ScreenSnapshotResult(
        instrument_id=instrument_id,
        status=ScreenSnapshotStatus.PASSED,
        rank=rank,
        final_score=score,
        scores=scores,
        factor_contributions={"quality_factor": score * 0.7, "momentum_factor": score * 0.3},
        industry=industry,
        reason_codes=("provider_fixture",),
        explanation_steps=(
            ScreenExplanationStep(
                stage=ScreenPipelineStage.L4_FINAL,
                rule_id="l4_final_passed",
                reason="instrument passed deterministic final screen gates",
                scores=scores,
                factor_contributions={"quality_factor": score * 0.7, "momentum_factor": score * 0.3},
            ),
        ),
    )


def _failed_result(instrument_id: str) -> ScreenSnapshotResult:
    return ScreenSnapshotResult(
        instrument_id=instrument_id,
        status=ScreenSnapshotStatus.FAILED,
        failed_stage=ScreenPipelineStage.L4_FINAL,
        final_score=70.0,
        scores={"l1_provider": 80.0, "l2_factor": 70.0, "l4_final": 70.0},
        reason_codes=("top_n",),
        explanation_steps=(
            ScreenExplanationStep(
                stage=ScreenPipelineStage.L4_FINAL,
                rule_id="top_n",
                reason="candidate rank exceeds top_n=2",
                scores={"l1_provider": 80.0, "l2_factor": 70.0, "l4_final": 70.0},
            ),
        ),
    )
