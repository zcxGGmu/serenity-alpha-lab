from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.candidate_batch import (
    Candidate,
    CandidateBatch,
    CandidateLayerScore,
    CandidateReason,
    CandidateScoreLayer,
)
from serenity_alpha_lab.application.quant_screening_api import (
    InMemoryQuantScreeningRepository,
    QuantScreeningApiService,
    QuantScreeningRunMode,
    QuantScreeningRunRequest,
)
from serenity_alpha_lab.application.task_backend import InMemoryTaskBackend, TaskStatus
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.datasets.catalog import DatasetVersionRef
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.run_lifecycle import EventKind, Run, RunStatus
from serenity_alpha_lab.quant.factors import FactorDirection
from serenity_alpha_lab.quant.factors.base_factors import base_factor_catalog, compile_base_factor_plans
from serenity_alpha_lab.quant.factors.evaluation import (
    FactorEvaluationObservation,
    FactorEvaluationSpec,
    FutureReturnWindow,
    evaluate_factor,
    publish_factor_evaluation_report,
)
from serenity_alpha_lab.quant.factors.post_processing import (
    CrossSectionPostProcessingResult,
    CrossSectionPostProcessingSpec,
    ProcessedCrossSectionFactorValue,
)
from serenity_alpha_lab.quant.screening.performance import (
    ScreenIncrementalBaseline,
    ScreenStagePerformanceSample,
    build_screen_performance_report,
    default_a_share_screening_budget,
    publish_screen_performance_report,
)
from serenity_alpha_lab.quant.screening.pipeline import (
    ScreenDefinition,
    ScreenDefinitionStatus,
    ScreenFactorSpec,
    ScreenFactorStageSpec,
    ScreenLlmOverlayStageSpec,
    ScreenPipelineStage,
    ScreenProviderStageSpec,
    ScreenRiskGateSpec,
    run_screen_pipeline,
)
from serenity_alpha_lab.quant.screening.snapshot import build_screen_snapshot, publish_screen_snapshot
from serenity_alpha_lab.quant.screening.universe import (
    UniverseDataEvidence,
    UniverseDefinition,
    UniverseExclusion,
    UniverseMember,
    UniverseSnapshot,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 25, 11, 0, tzinfo=UTC)
AS_OF = date(2026, 7, 24)
DATASET_VERSIONS = {
    "universe": "dsv_" + "1" * 32,
    "raw_daily_bars": "dsv_" + "2" * 32,
    "factor_values": "dsv_" + "3" * 32,
    "instrument_master": "dsv_" + "4" * 32,
}
FACTOR_QUALITY_VERSION = "fdv_" + "a" * 32
FACTOR_MOMENTUM_VERSION = "fdv_" + "b" * 32


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


def test_gate_g3_review_document_approves_screen_factor_inputs_without_expanding_scope() -> None:
    review_path = Path("docs/gate-g3-screen-factor-review.md")
    text = review_path.read_text(encoding="utf-8")

    required_phrases = [
        "GO with accepted risks",
        "APPROVED FOR P4",
        "SAL-P3-001",
        "SAL-P3-016",
        "Screen Lab",
        "Quant Screening API",
        "ScreenSnapshot",
        "ScreenDefinition",
        "CandidateBatch",
        "FactorDefinition",
        "Factor Evaluation",
        "Dataset Catalog",
        "ProblemDetails",
        "Trace",
        "Artifact",
        "Run/Stage/Event",
        "docs/screen-performance-reproducibility.md",
        "不启动 Quant Core",
        "不执行正式回测",
        "不启动 Evidence Agent",
        "不调用真实 Provider/LLM",
        "不启动 Worker execution loop",
        "不迁移 DSA runtime source",
    ]

    assert all(phrase in text for phrase in required_phrases)
    assert "未通过数据/偏差检查的 Screen 不得进入 P4 正式回测" in text


def test_gate_g3_executable_contract_links_factors_screen_api_artifacts_and_run_lifecycle(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    for version in DATASET_VERSIONS.values():
        assert DatasetVersionRef.version(version).version_id == version

    catalog = base_factor_catalog(dataset_versions={"fundamentals_pit": DATASET_VERSIONS["factor_values"]})
    plans = compile_base_factor_plans(catalog.definitions)
    assert len(catalog.definitions) >= 15
    assert {"quality", "valuation", "growth", "momentum", "volatility", "liquidity"} == set(
        catalog.category_counts
    )
    assert "momentum_20d" in plans

    factor_report = evaluate_factor(_factor_observations(), _factor_evaluation_spec())
    factor_artifact = publish_factor_evaluation_report(factor_report, artifact_store, created_at=NOW)
    assert factor_report.coverage.sample_overlap_ratio > 0.80
    assert factor_report.ic_summary.mean_ic > 0.80
    assert factor_artifact.schema_name == "quant.factor_evaluation"

    pipeline_snapshot = run_screen_pipeline(
        _screen_definition(),
        as_of=AS_OF,
        universe_snapshot=_universe_snapshot(),
        candidate_batch=_candidate_batch(),
        factor_results=_factor_results(),
        created_at=NOW,
        trace_id="trace-g3-screen",
        run_id="run-g3-screen",
        stage_id="stage-g3-screen",
    )
    screen_snapshot = build_screen_snapshot(
        pipeline_snapshot,
        created_at=NOW,
        trace_id="trace-g3-snapshot",
        run_id="run-g3-snapshot",
        stage_id="stage-g3-snapshot",
    )
    snapshot_artifact = publish_screen_snapshot(screen_snapshot, artifact_store)
    assert screen_snapshot.passed_count == 2
    assert [trace.stage for trace in pipeline_snapshot.stage_traces] == [
        ScreenPipelineStage.L0_UNIVERSE,
        ScreenPipelineStage.L1_PROVIDER,
        ScreenPipelineStage.L2_FACTOR,
        ScreenPipelineStage.L3_LLM_OVERLAY,
        ScreenPipelineStage.L4_FINAL,
    ]

    performance_report = build_screen_performance_report(
        snapshot=screen_snapshot,
        repeated_snapshot=screen_snapshot,
        code_version="git:sal-p3-017",
        stage_samples=tuple(
            ScreenStagePerformanceSample.from_stage_trace(
                trace,
                duration_ms=100.0,
                peak_memory_mb=180.0,
            )
            for trace in pipeline_snapshot.stage_traces
        ),
        incremental_baseline=ScreenIncrementalBaseline(
            changed_dataset_versions={"factor_values": "dsv_" + "9" * 32},
            changed_factor_versions=(FACTOR_MOMENTUM_VERSION,),
            changed_trade_dates=(AS_OF,),
            total_candidate_count=6_000,
            recomputed_candidate_count=240,
        ),
        budget=default_a_share_screening_budget(),
        cached_query_duration_ms=120.0,
        created_at=NOW,
        artifact_manifest=snapshot_artifact,
        trace_id="trace-g3-performance",
        run_id="run-g3-performance",
        stage_id="stage-g3-performance",
    )
    performance_artifact = publish_screen_performance_report(performance_report, artifact_store)
    assert performance_report.acceptance_status == "passed"
    assert performance_report.reproducibility.reproducible is True
    assert performance_artifact.schema_name == "quant.screen_performance_reproducibility"
    assert performance_report.run_bundle.artifact_manifest == snapshot_artifact

    service = QuantScreeningApiService(
        repository=InMemoryQuantScreeningRepository(),
        task_backend=InMemoryTaskBackend(clock=DeterministicClock()),
        clock=DeterministicClock(),
        trace_id="trace-g3-api",
    )
    service.create_screen_definition(_screen_definition())
    request = QuantScreeningRunRequest.from_snapshot(
        screen_definition_id="quality_momentum_cn",
        screen_definition_version_id=screen_snapshot.definition_version_id,
        snapshot=screen_snapshot,
        run_mode=QuantScreeningRunMode.FORMAL,
        submitted_by="gate-g3-reviewer",
        artifact_manifest=snapshot_artifact,
    )
    accepted = service.create_screen_run(request, idempotency_key="gate-g3:screen:2026-07-24")
    replay = service.create_screen_run(request, idempotency_key="gate-g3:screen:2026-07-24")
    first_page = service.get_screen_run_results(accepted.body["run_id"], page_size=2)
    problem = problem_from_exception(
        ValueError("latest Dataset Version is not allowed for Gate G3"),
        trace_context=TraceContext(trace_id="trace-g3-api", run_id=accepted.body["run_id"], stage_id="stage-g3-api"),
    )

    assert accepted.status_code == 202
    assert replay.body == accepted.body
    assert accepted.body["status"] == TaskStatus.QUEUED.value
    assert accepted.body["artifact"]["artifact_id"] == snapshot_artifact.artifact_id
    assert first_page.body["trace"]["trace_id"] == "trace-g3-snapshot"
    assert first_page.body["dataset_versions"] == DATASET_VERSIONS
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-g3-api"

    run = Run.start(
        run_id=accepted.body["run_id"],
        run_type="quant.screen.run",
        idempotency_key="gate-g3:screen:2026-07-24",
        started_at=NOW,
    )
    run.start_stage(stage_id="stage-g3-api", name="Quant Screening API handoff", started_at=NOW)
    run.complete_stage("stage-g3-api", completed_at=NOW + timedelta(seconds=1))
    run.complete(completed_at=NOW + timedelta(seconds=2))

    assert run.status is RunStatus.COMPLETED
    assert [event.kind for event in run.events] == [
        EventKind.RUN_STARTED,
        EventKind.STAGE_STARTED,
        EventKind.STAGE_COMPLETED,
        EventKind.RUN_COMPLETED,
    ]
    json.dumps(
        {
            "factor": factor_report.to_record(),
            "snapshot": screen_snapshot.to_record(),
            "performance": performance_report.to_record(),
            "api": first_page.body,
        },
        sort_keys=True,
    )


def _screen_definition(**overrides) -> ScreenDefinition:
    values = {
        "definition_id": "quality_momentum_cn",
        "semantic_version": "1.0.0",
        "status": ScreenDefinitionStatus.PUBLISHED,
        "markets": (Market.CN,),
        "dataset_versions": DATASET_VERSIONS,
        "provider_stage": ScreenProviderStageSpec(
            provider_id="alphasift",
            strategy_id="quality_momentum",
            strategy_version="1.0.0",
            score_weight=0.20,
            max_candidates=100,
        ),
        "factor_stage": ScreenFactorStageSpec(
            factors=(
                ScreenFactorSpec("quality_factor", FACTOR_QUALITY_VERSION, weight=0.70),
                ScreenFactorSpec("momentum_factor", FACTOR_MOMENTUM_VERSION, weight=0.30),
            ),
            score_weight=0.80,
        ),
        "llm_overlay_stage": ScreenLlmOverlayStageSpec(enabled=True, score_weight=0.10),
        "risk_gate": ScreenRiskGateSpec(top_n=2, max_per_industry=1),
        "created_at": NOW,
        "created_by_run_id": "run-g3-screen-definition",
    }
    values.update(overrides)
    return ScreenDefinition(**values)


def _universe_snapshot() -> UniverseSnapshot:
    universe_definition = UniverseDefinition(
        definition_id="cn_l0_historical_universe",
        semantic_version="1.0.0",
        markets=(Market.CN,),
        dataset_versions={
            "instrument_master": DATASET_VERSIONS["instrument_master"],
            "trading_calendar": "dsv_" + "5" * 32,
            "raw_daily_bars": "dsv_" + "6" * 32,
            "instrument_trade_status": "dsv_" + "7" * 32,
        },
        created_at=NOW,
        created_by_run_id="run-g3-universe",
    )
    return UniverseSnapshot(
        definition=universe_definition,
        as_of=AS_OF,
        members=(
            _member("600519.XSHG", industry="beverage"),
            _member("000001.XSHE", industry="bank"),
            _member("600091.XSHG", industry="bank"),
        ),
        exclusions=(
            UniverseExclusion(
                instrument_id="600090.XSHG",
                rule_id="daily_bar_available",
                reason="raw daily bar missing for decision date",
                evidence=(_evidence("raw_daily_bars", "instrument_id", "600090.XSHG missing"),),
            ),
        ),
        created_at=NOW,
        run_id="run-g3-universe",
        stage_id="stage-g3-universe",
        universe_version_id=DATASET_VERSIONS["universe"],
    )


def _candidate_batch() -> CandidateBatch:
    return CandidateBatch(
        batch_id="cb_gate_g3_quality_momentum",
        provider_id="alphasift",
        provider_version="0.2.0+9f522747",
        strategy_id="quality_momentum",
        strategy_version="1.0.0",
        market="cn",
        dataset_versions={
            "raw_daily_bars": DATASET_VERSIONS["raw_daily_bars"],
            "instrument_master": DATASET_VERSIONS["instrument_master"],
        },
        source_snapshot_at=NOW,
        discovered_at=NOW,
        requested_at=NOW,
        received_at=NOW,
        provider_run_id="alphasift-run-g3",
        snapshot_count=4,
        after_filter_count=4,
        candidates=(
            _candidate("600090.XSHG", rank=1, l1=100.0, l3=100.0, industry="energy"),
            _candidate("000001.XSHE", rank=2, l1=95.0, l3=60.0, industry="bank"),
            _candidate("600091.XSHG", rank=3, l1=85.0, l3=40.0, industry="bank"),
            _candidate("600519.XSHG", rank=4, l1=70.0, l3=20.0, industry="beverage"),
        ),
        llm_overlay_enabled=True,
        llm_coverage=1.0,
        trace_id="trace-g3-candidate-batch",
        platform_run_id="run-g3-candidate-batch",
        stage_id="stage-g3-l1",
    )


def _candidate(instrument_id: str, *, rank: int, l1: float, l3: float, industry: str) -> Candidate:
    return Candidate(
        instrument=InstrumentId.parse(instrument_id),
        rank=rank,
        final_score=l1,
        scores=(
            CandidateLayerScore(layer=CandidateScoreLayer.L1_PROVIDER, score=l1, source_id="provider:alphasift"),
            CandidateLayerScore(layer=CandidateScoreLayer.L2_DETERMINISTIC, score=50.0, source_id="factor:gate-g3"),
            CandidateLayerScore(layer=CandidateScoreLayer.L3_LLM_OVERLAY, score=l3, source_id="llm:disabled-stub"),
        ),
        reasons=(CandidateReason(code="provider_fixture", layer=CandidateScoreLayer.L1_PROVIDER),),
        source_ids=("provider:alphasift",),
        raw_payload={"industry": industry},
    )


def _factor_results() -> dict[str, CrossSectionPostProcessingResult]:
    return {
        "quality_factor": _factor_result(
            {
                "600519.XSHG": (2.0, "beverage"),
                "000001.XSHE": (0.7, "bank"),
                "600091.XSHG": (0.6, "bank"),
                "600090.XSHG": (9.9, "energy"),
            }
        ),
        "momentum_factor": _factor_result(
            {
                "600519.XSHG": (1.0, "beverage"),
                "000001.XSHE": (0.2, "bank"),
                "600091.XSHG": (0.1, "bank"),
                "600090.XSHG": (9.9, "energy"),
            }
        ),
    }


def _factor_result(values: dict[str, tuple[float, str]]) -> CrossSectionPostProcessingResult:
    spec = CrossSectionPostProcessingSpec(
        dataset_versions={
            "factor_values": DATASET_VERSIONS["factor_values"],
            "instrument_master": DATASET_VERSIONS["instrument_master"],
        }
    )
    return CrossSectionPostProcessingResult(
        spec=spec,
        processed_values=tuple(
            ProcessedCrossSectionFactorValue(
                instrument_id=instrument_id,
                trade_date=AS_OF,
                raw_value=value,
                filled_value=value,
                processed_value=value,
                step_values={"standardized": value},
                exposures={"industry": industry},
            )
            for instrument_id, (value, industry) in values.items()
        ),
        dropped_values=(),
        warnings=(),
    )


def _factor_evaluation_spec() -> FactorEvaluationSpec:
    return FactorEvaluationSpec(
        run_id="run-g3-factor-eval",
        stage_id="stage-g3-factor-eval",
        factor_definition_id="momentum_20d",
        factor_version_id=FACTOR_MOMENTUM_VERSION,
        dataset_versions={
            "factor_values": DATASET_VERSIONS["factor_values"],
            "forward_returns": "dsv_" + "f" * 32,
            "instrument_master": DATASET_VERSIONS["instrument_master"],
        },
        future_return_window=FutureReturnWindow(
            horizon=5,
            return_field="forward_return_5d",
            version="forward_return_5d_v1",
        ),
        factor_direction=FactorDirection.HIGHER_IS_BETTER,
        quantile_count=3,
        minimum_ic_observations=3,
        exposure_fields=("beta",),
        formal=True,
    )


def _factor_observations() -> tuple[FactorEvaluationObservation, ...]:
    rows: list[FactorEvaluationObservation] = []
    decision_time = datetime(2026, 1, 2, 15, 30, tzinfo=UTC)
    available_at = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
    forward_available_at = datetime(2026, 1, 8, 18, 0, tzinfo=UTC)
    for offset, trade_date in enumerate((date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6))):
        factor_values = (
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            [1.0, 2.0, 3.0, 5.0, 4.0, 6.0],
            [1.0, 2.0, 3.0, 4.0, 6.0, 5.0],
        )[offset]
        returns_by_date = (
            [0.01, 0.02, 0.04, 0.05, 0.08, 0.10],
            [0.02, 0.01, 0.05, 0.11, 0.09, 0.12],
            [0.01, 0.03, 0.02, 0.06, 0.10, 0.09],
        )[offset]
        for index, factor_value in enumerate(factor_values):
            rows.append(
                FactorEvaluationObservation(
                    instrument_id=f"60000{index}.XSHG",
                    trade_date=trade_date,
                    decision_time=decision_time,
                    factor_available_at=available_at,
                    forward_return_available_at=forward_available_at,
                    factor_value=factor_value,
                    forward_return=returns_by_date[index],
                    exposures={"beta": 0.8 + index * 0.1},
                )
            )
    return tuple(rows)


def _member(instrument_id: str, *, industry: str) -> UniverseMember:
    return UniverseMember(
        instrument_id=instrument_id,
        market=Market.CN,
        exchange=InstrumentId.parse(instrument_id).exchange.value,
        listed_on=date(2001, 1, 1),
        listing_trading_days=5_000,
        evidence=(
            _evidence("instrument_master", "listing_status", "active"),
            _evidence("instrument_master", "industry", industry),
        ),
    )


def _evidence(dataset_name: str, field_name: str, value: object) -> UniverseDataEvidence:
    return UniverseDataEvidence(
        dataset_name=dataset_name,
        dataset_version=DATASET_VERSIONS.get(dataset_name, DATASET_VERSIONS["instrument_master"]),
        source_bronze_artifact_id=f"art_bronze_{dataset_name}",
        field_name=field_name,
        observed_value=value,
    )
