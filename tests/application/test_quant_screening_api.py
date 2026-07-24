from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.quant_screening_api import (
    QUANT_SCREENING_API_ROUTES,
    InMemoryQuantScreeningRepository,
    QuantScreeningApiService,
    QuantScreeningRunMode,
    QuantScreeningRunRequest,
)
from serenity_alpha_lab.application.task_backend import InMemoryTaskBackend
from serenity_alpha_lab.quant.factors.definitions import (
    FactorDefinition,
    FactorDirection,
    FactorFormula,
    FactorInput,
    FactorInputKind,
    FactorWindow,
    MissingValuePolicy,
    MissingValueStrategy,
)
from serenity_alpha_lab.quant.screening.pipeline import (
    ScreenDefinition,
    ScreenDefinitionStatus,
    ScreenFactorSpec,
    ScreenFactorStageSpec,
    ScreenLlmOverlayStageSpec,
    ScreenProviderStageSpec,
    ScreenRiskGateSpec,
)
from serenity_alpha_lab.quant.screening.snapshot import (
    SCREEN_SNAPSHOT_SCHEMA_NAME,
    SCREEN_SNAPSHOT_SCHEMA_VERSION,
    ScreenExplanationStep,
    ScreenSnapshot,
    ScreenSnapshotResult,
    ScreenSnapshotStatus,
)
from serenity_alpha_lab.quant.screening.pipeline import ScreenPipelineStage


NOW = datetime(2026, 7, 24, 10, 30, tzinfo=UTC)
AS_OF = date(2026, 7, 24)
DATASET_VERSIONS = {
    "universe": "dsv_" + "1" * 32,
    "raw_daily_bars": "dsv_" + "2" * 32,
    "factor_values": "dsv_" + "3" * 32,
    "instrument_master": "dsv_" + "4" * 32,
}
FACTOR_VERSION_ID = "fdv_" + "a" * 32


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


def test_quant_screening_api_declares_expected_v1_routes() -> None:
    paths = {(route.method, route.path, route.response_status) for route in QUANT_SCREENING_API_ROUTES}

    assert ("POST", "/api/v1/quant/factor-definitions", 201) in paths
    assert ("POST", "/api/v1/quant/screen-definitions", 201) in paths
    assert ("POST", "/api/v1/quant/screen-runs", 202) in paths
    assert ("GET", "/api/v1/quant/screen-runs/{run_id}/results", 200) in paths
    assert ("GET", "/api/v1/quant/screen-runs/{run_id}/results/{instrument_id}", 200) in paths
    assert ("GET", "/api/v1/quant/screen-runs/{run_id}/comparison", 200) in paths

    operation_ids = [route.operation_id for route in QUANT_SCREENING_API_ROUTES]
    assert len(operation_ids) == len(set(operation_ids))
    assert json.dumps([route.to_record() for route in QUANT_SCREENING_API_ROUTES], sort_keys=True)


def test_definition_endpoints_return_versioned_records_without_running_quant_work() -> None:
    service = _service()
    factor = _factor_definition()
    screen_definition = _screen_definition()

    factor_response = service.create_factor_definition(factor)
    screen_response = service.create_screen_definition(screen_definition)

    assert factor_response.status_code == 201
    assert factor_response.headers["Location"] == "/api/v1/quant/factor-definitions/quality_factor@1.0.0"
    assert factor_response.body["schema"]["name"] == "quant.factor_definition"
    assert factor_response.body["factor_definition"]["definition_id"] == "quality_factor"
    assert factor_response.body["factor_definition"]["dataset_versions"]["factor_values"] == DATASET_VERSIONS["factor_values"]
    assert factor_response.body["trace"]["trace_id"] == "trace-api"

    assert screen_response.status_code == 201
    assert screen_response.headers["Location"] == (
        f"/api/v1/quant/screen-definitions/{screen_definition.definition_version_id}"
    )
    assert screen_response.body["schema"]["name"] == "quant.screen_definition"
    assert screen_response.body["screen_definition"]["definition_version_id"] == screen_definition.definition_version_id
    assert screen_response.body["screen_definition"]["dataset_versions"] == DATASET_VERSIONS


def test_screen_run_creation_requires_idempotency_key_and_replays_accepted_response() -> None:
    service = _service()
    screen_definition = _screen_definition()
    snapshot = _screen_snapshot(definition_version_id=screen_definition.definition_version_id)
    service.create_screen_definition(screen_definition)
    request = QuantScreeningRunRequest.from_snapshot(
        screen_definition_id=screen_definition.definition_id,
        screen_definition_version_id=screen_definition.definition_version_id,
        snapshot=snapshot,
        run_mode=QuantScreeningRunMode.PREVIEW,
        submitted_by="researcher@example.com",
    )

    response = service.create_screen_run(request, idempotency_key="screen:quality:2026-07-24")
    replay = service.create_screen_run(request, idempotency_key="screen:quality:2026-07-24")

    assert response.status_code == 202
    assert replay.body == response.body
    assert response.headers["Location"] == f"/api/v1/quant/screen-runs/{response.body['run_id']}"
    assert response.headers["Idempotency-Key"] == "screen:quality:2026-07-24"
    assert response.body["status"] == "queued"
    assert response.body["run_type"] == "quant.screen.run"
    assert response.body["screen_definition_version_id"] == screen_definition.definition_version_id
    assert response.body["screen_snapshot_id"] == snapshot.screen_snapshot_id
    assert response.body["as_of"] == AS_OF.isoformat()
    assert response.body["dataset_versions"] == DATASET_VERSIONS
    assert response.body["schema"]["name"] == SCREEN_SNAPSHOT_SCHEMA_NAME
    assert response.body["trace"] == {"trace_id": "trace-snapshot", "run_id": response.body["run_id"], "stage_id": "stage-snapshot"}

    with pytest.raises(ValueError, match="Idempotency-Key"):
        service.create_screen_run(request, idempotency_key="")


def test_screen_results_are_stably_paginated_with_schema_dataset_and_trace_metadata() -> None:
    service = _service()
    screen_definition = _screen_definition()
    snapshot = _screen_snapshot(definition_version_id=screen_definition.definition_version_id)
    service.create_screen_definition(screen_definition)
    run_response = service.create_screen_run(
        QuantScreeningRunRequest.from_snapshot(
            screen_definition_id=screen_definition.definition_id,
            screen_definition_version_id=screen_definition.definition_version_id,
            snapshot=snapshot,
        ),
        idempotency_key="screen:page:2026-07-24",
    )

    first_page = service.get_screen_run_results(run_response.body["run_id"], page_size=2)
    second_page = service.get_screen_run_results(
        run_response.body["run_id"],
        page_size=2,
        cursor=first_page.body["pagination"]["next_cursor"],
    )
    row = service.get_screen_run_result(run_response.body["run_id"], "600091.XSHG")

    assert first_page.status_code == 200
    assert first_page.body["schema"] == {"name": SCREEN_SNAPSHOT_SCHEMA_NAME, "version": SCREEN_SNAPSHOT_SCHEMA_VERSION}
    assert first_page.body["as_of"] == AS_OF.isoformat()
    assert first_page.body["dataset_versions"] == DATASET_VERSIONS
    assert first_page.body["trace"]["trace_id"] == "trace-snapshot"
    assert first_page.body["pagination"] == {
        "page_size": 2,
        "cursor": None,
        "next_cursor": "2",
        "total_count": 3,
    }
    assert [item["instrument_id"] for item in first_page.body["results"]] == ["600519.XSHG", "000001.XSHE"]
    assert [item["instrument_id"] for item in second_page.body["results"]] == ["600091.XSHG"]
    assert second_page.body["pagination"]["next_cursor"] is None
    assert row.body["result"]["instrument_id"] == "600091.XSHG"
    assert row.body["result"]["failed_stage"] == "l2_factor"
    assert row.body["result"]["rank"] is None
    assert json.dumps(first_page.body, sort_keys=True)


def test_screen_run_comparison_uses_snapshot_comparison_and_problem_details_boundary() -> None:
    service = _service()
    screen_definition = _screen_definition()
    service.create_screen_definition(screen_definition)
    previous = service.create_screen_run(
        QuantScreeningRunRequest.from_snapshot(
            screen_definition_id=screen_definition.definition_id,
            screen_definition_version_id=screen_definition.definition_version_id,
            snapshot=_screen_snapshot(
                definition_version_id=screen_definition.definition_version_id,
                score_offset=0.0,
                include_third_passed=False,
            ),
        ),
        idempotency_key="screen:comparison:previous",
    )
    current = service.create_screen_run(
        QuantScreeningRunRequest.from_snapshot(
            screen_definition_id=screen_definition.definition_id,
            screen_definition_version_id=screen_definition.definition_version_id,
            snapshot=_screen_snapshot(
                definition_version_id=screen_definition.definition_version_id,
                score_offset=1.5,
                include_third_passed=True,
            ),
        ),
        idempotency_key="screen:comparison:current",
    )

    response = service.compare_screen_runs(previous.body["run_id"], current.body["run_id"])
    problem = problem_from_exception(
        ValueError("screen run not found: run-missing"),
        instance="/api/v1/quant/screen-runs/run-missing/results",
    )

    assert response.status_code == 200
    assert response.body["schema"] == {"name": "quant.screen_snapshot_comparison", "version": "1.0.0"}
    assert response.body["previous_run_id"] == previous.body["run_id"]
    assert response.body["current_run_id"] == current.body["run_id"]
    assert response.body["comparison"]["added"] == ["600091.XSHG"]
    assert response.body["comparison"]["removed"] == []
    assert response.body["comparison"]["score_deltas"][0]["delta"] == pytest.approx(1.5)
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR


def _service() -> QuantScreeningApiService:
    return QuantScreeningApiService(
        repository=InMemoryQuantScreeningRepository(),
        task_backend=InMemoryTaskBackend(clock=DeterministicClock()),
        clock=DeterministicClock(),
        trace_id="trace-api",
    )


def _factor_definition() -> FactorDefinition:
    return FactorDefinition.draft(
        definition_id="quality_factor",
        semantic_version="1.0.0",
        name="Quality Factor",
        description="Fixture factor for API contract testing.",
        category="quality",
        direction=FactorDirection.HIGHER_IS_BETTER,
        formula=FactorFormula(expression="rank(quality_score)", language="serenity_factor_dsl"),
        inputs=(
            FactorInput(
                input_id="quality_score",
                dataset_name="factor_values",
                dataset_version=DATASET_VERSIONS["factor_values"],
                field_name="quality_score",
                kind=FactorInputKind.DATASET_FIELD,
                data_type="float64",
            ),
        ),
        windows=(FactorWindow(name="point_in_time", length=1, unit="trading_day"),),
        missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.DROP),
        post_process=(),
        implementation_hash="sha256:" + "f" * 64,
        created_at=NOW,
        created_by_run_id="run-factor-definition",
        source_commit="10d97975",
    )


def _screen_definition() -> ScreenDefinition:
    return ScreenDefinition(
        definition_id="quality_momentum_cn",
        semantic_version="1.0.0",
        status=ScreenDefinitionStatus.PUBLISHED,
        markets=("cn",),
        dataset_versions=DATASET_VERSIONS,
        provider_stage=ScreenProviderStageSpec(
            provider_id="alphasift",
            strategy_id="quality_momentum",
            strategy_version="1.0.0",
            score_weight=0.20,
            max_candidates=100,
        ),
        factor_stage=ScreenFactorStageSpec(
            factors=(ScreenFactorSpec("quality_factor", FACTOR_VERSION_ID, weight=1.0),),
            score_weight=0.80,
        ),
        llm_overlay_stage=ScreenLlmOverlayStageSpec(enabled=False, score_weight=0.0),
        risk_gate=ScreenRiskGateSpec(top_n=20, max_per_industry=5),
        created_at=NOW,
        created_by_run_id="run-screen-definition",
    )


def _screen_snapshot(
    *,
    definition_version_id: str,
    score_offset: float = 0.0,
    include_third_passed: bool = False,
) -> ScreenSnapshot:
    results: list[ScreenSnapshotResult] = [
        _passed_result("600519.XSHG", rank=1, score=91.0 + score_offset),
        _passed_result("000001.XSHE", rank=2, score=87.0 + score_offset),
    ]
    if include_third_passed:
        results.append(_passed_result("600091.XSHG", rank=3, score=74.0 + score_offset))
    else:
        results.append(_failed_result("600091.XSHG"))
    return ScreenSnapshot(
        pipeline_snapshot_id="sps_" + "9" * 32,
        definition_version_id=definition_version_id,
        as_of=AS_OF,
        dataset_versions=DATASET_VERSIONS,
        results=tuple(results),
        created_at=NOW,
        trace_id="trace-snapshot",
        run_id="run-snapshot-source",
        stage_id="stage-snapshot",
    )


def _passed_result(instrument_id: str, *, rank: int, score: float) -> ScreenSnapshotResult:
    return ScreenSnapshotResult(
        instrument_id=instrument_id,
        status=ScreenSnapshotStatus.PASSED,
        rank=rank,
        final_score=score,
        scores={"l4_final": score, "l2_factor": score - 5.0},
        factor_contributions={"quality_factor": score - 5.0},
        reason_codes=("l4_final_passed",),
        summary="instrument passed all screen stages",
        explanation_steps=(
            ScreenExplanationStep(
                stage=ScreenPipelineStage.L4_FINAL,
                rule_id="l4_final_passed",
                reason="instrument passed deterministic final screen gates",
                scores={"l4_final": score},
                factor_contributions={"quality_factor": score - 5.0},
            ),
        ),
    )


def _failed_result(instrument_id: str) -> ScreenSnapshotResult:
    return ScreenSnapshotResult(
        instrument_id=instrument_id,
        status=ScreenSnapshotStatus.FAILED,
        failed_stage=ScreenPipelineStage.L2_FACTOR,
        scores={"l1_provider": 72.0},
        factor_contributions={},
        reason_codes=("l2_factor_value_missing",),
        summary="missing factor values",
        explanation_steps=(
            ScreenExplanationStep(
                stage=ScreenPipelineStage.L2_FACTOR,
                rule_id="l2_factor_value_missing",
                reason="missing factor values",
                scores={"l1_provider": 72.0},
            ),
        ),
    )
