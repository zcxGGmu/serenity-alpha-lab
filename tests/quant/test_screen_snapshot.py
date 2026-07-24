from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.application.candidate_batch import (
    Candidate,
    CandidateBatch,
    CandidateLayerScore,
    CandidateReason,
    CandidateScoreLayer,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.quant.factors.post_processing import (
    CrossSectionPostProcessingResult,
    CrossSectionPostProcessingSpec,
    ProcessedCrossSectionFactorValue,
)
from serenity_alpha_lab.quant.screening.pipeline import (
    ScreenDefinition,
    ScreenDefinitionStatus,
    ScreenFactorSpec,
    ScreenFactorStageSpec,
    ScreenLlmOverlayStageSpec,
    ScreenProviderStageSpec,
    ScreenRiskGateSpec,
    run_screen_pipeline,
)
from serenity_alpha_lab.quant.screening.snapshot import (
    SCREEN_SNAPSHOT_CONTENT_TYPE,
    SCREEN_SNAPSHOT_SCHEMA_NAME,
    SCREEN_SNAPSHOT_SCHEMA_VERSION,
    ScreenSnapshotStatus,
    build_screen_snapshot,
    compare_screen_snapshots,
    publish_screen_snapshot,
)
from serenity_alpha_lab.quant.screening.universe import (
    UniverseDataEvidence,
    UniverseDefinition,
    UniverseExclusion,
    UniverseMember,
    UniverseSnapshot,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 24, 10, 30, tzinfo=UTC)
AS_OF = date(2026, 7, 24)
DATASET_VERSIONS = {
    "universe": "dsv_" + "1" * 32,
    "raw_daily_bars": "dsv_" + "2" * 32,
    "factor_values": "dsv_" + "3" * 32,
    "instrument_master": "dsv_" + "4" * 32,
}
FACTOR_QUALITY_VERSION = "fdv_" + "a" * 32
FACTOR_MOMENTUM_VERSION = "fdv_" + "b" * 32


def test_screen_snapshot_records_passed_failed_rows_and_replayable_explanations() -> None:
    pipeline_snapshot = _pipeline_snapshot()

    snapshot = build_screen_snapshot(pipeline_snapshot, created_at=NOW)

    assert snapshot.schema_name == SCREEN_SNAPSHOT_SCHEMA_NAME
    assert snapshot.schema_version == SCREEN_SNAPSHOT_SCHEMA_VERSION
    assert snapshot.screen_snapshot_id.startswith("ssn_")
    assert len(snapshot.screen_snapshot_id) == len("ssn_") + 32
    assert snapshot.pipeline_snapshot_id == pipeline_snapshot.pipeline_snapshot_id
    assert snapshot.definition_version_id == pipeline_snapshot.definition_version_id
    assert snapshot.dataset_versions == pipeline_snapshot.dataset_versions
    assert snapshot.as_of == AS_OF
    assert snapshot.passed_count == 2
    assert snapshot.failed_count == 2

    passed = snapshot.result_for("600519.XSHG")
    assert passed.status is ScreenSnapshotStatus.PASSED
    assert passed.rank == 1
    assert passed.failed_stage is None
    assert passed.scores["l4_final"] == pytest.approx(passed.final_score)
    assert set(passed.factor_contributions) == {"quality_factor", "momentum_factor"}
    assert [step.stage.value for step in passed.explanation_steps] == [
        "l0_universe",
        "l1_provider",
        "l2_factor",
        "l3_llm_overlay",
        "l4_final",
    ]
    assert passed.explanation_steps[-1].rule_id == "l4_final_passed"
    assert all(step.authoritative for step in passed.explanation_steps)

    failed = snapshot.result_for("600090.XSHG")
    assert failed.status is ScreenSnapshotStatus.FAILED
    assert failed.rank is None
    assert failed.failed_stage.value == "l0_universe"
    assert failed.explanation_steps[0].rule_id == "l0_universe_member"
    assert failed.explanation_steps[0].reason == "raw daily bar missing for decision date"
    assert failed.explanation_steps[0].authoritative is True
    assert failed.scores["l3_llm_overlay"] == 100.0

    record = snapshot.to_record()
    assert record["schema_name"] == SCREEN_SNAPSHOT_SCHEMA_NAME
    assert record["results"][0]["status"] == "passed"
    assert record["results"][0]["explanation_steps"][-1]["authoritative"] is True
    assert record["results_by_instrument"]["600090.XSHG"]["failed_stage"] == "l0_universe"
    json.dumps(record, sort_keys=True)


def test_screen_snapshot_comparison_uses_passed_set_and_rank_score_deltas() -> None:
    previous = build_screen_snapshot(_pipeline_snapshot(), created_at=NOW)
    current = build_screen_snapshot(
        _pipeline_snapshot(risk_gate=ScreenRiskGateSpec(top_n=3, max_per_industry=2)),
        created_at=NOW,
    )

    comparison = compare_screen_snapshots(previous, current)

    assert comparison.previous_screen_snapshot_id == previous.screen_snapshot_id
    assert comparison.current_screen_snapshot_id == current.screen_snapshot_id
    assert comparison.added == ("600091.XSHG",)
    assert comparison.removed == ()
    assert comparison.retained == ("000001.XSHE", "600519.XSHG")
    assert comparison.status_changes[0].instrument_id == "600091.XSHG"
    assert comparison.status_changes[0].previous_status is ScreenSnapshotStatus.FAILED
    assert comparison.status_changes[0].current_status is ScreenSnapshotStatus.PASSED
    assert comparison.rank_changes == ()
    assert comparison.score_delta_for("600519.XSHG").delta == pytest.approx(0.0)
    json.dumps(comparison.to_record(), sort_keys=True)


def test_screen_snapshot_publishes_deterministic_artifact(tmp_path: Path) -> None:
    snapshot = build_screen_snapshot(
        _pipeline_snapshot(),
        created_at=NOW,
        run_id="run-screen-snapshot",
        stage_id="stage-screen-snapshot",
    )
    store = LocalArtifactStore(tmp_path / "artifacts")

    artifact = publish_screen_snapshot(snapshot, store)
    repeated = publish_screen_snapshot(snapshot, store)
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert repeated.artifact_id == artifact.artifact_id
    assert artifact.schema_name == SCREEN_SNAPSHOT_SCHEMA_NAME
    assert artifact.schema_version == SCREEN_SNAPSHOT_SCHEMA_VERSION
    assert artifact.content_type == SCREEN_SNAPSHOT_CONTENT_TYPE
    assert artifact.produced_by_run_id == "run-screen-snapshot"
    assert artifact.produced_by_stage_id == "stage-screen-snapshot"
    assert payload["screen_snapshot_id"] == snapshot.screen_snapshot_id
    assert payload["passed_count"] == 2
    assert payload["failed_count"] == 2


def _pipeline_snapshot(*, risk_gate: ScreenRiskGateSpec | None = None):
    return run_screen_pipeline(
        _screen_definition(**({"risk_gate": risk_gate} if risk_gate is not None else {})),
        as_of=AS_OF,
        universe_snapshot=_universe_snapshot(),
        candidate_batch=_candidate_batch(include_llm=True),
        factor_results=_factor_results(),
        created_at=NOW,
        trace_id="trace-screen-pipeline",
        run_id="run-screen-pipeline",
        stage_id="stage-screen-pipeline",
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
        "created_by_run_id": "run-screen-definition",
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
        created_by_run_id="run-universe",
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
        run_id="run-universe",
        stage_id="stage-universe",
        universe_version_id=DATASET_VERSIONS["universe"],
    )


def _candidate_batch(*, include_llm: bool) -> CandidateBatch:
    return CandidateBatch(
        batch_id="cb_quality_momentum",
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
        provider_run_id="alphasift-run-001",
        snapshot_count=4,
        after_filter_count=4,
        candidates=(
            _candidate("600090.XSHG", rank=1, l1=100.0, l3=100.0 if include_llm else None, industry="energy"),
            _candidate("000001.XSHE", rank=2, l1=95.0, l3=60.0 if include_llm else None, industry="bank"),
            _candidate("600091.XSHG", rank=3, l1=85.0, l3=40.0 if include_llm else None, industry="bank"),
            _candidate("600519.XSHG", rank=4, l1=70.0, l3=20.0 if include_llm else None, industry="beverage"),
        ),
        llm_overlay_enabled=include_llm,
        llm_coverage=1.0 if include_llm else None,
        trace_id="trace-candidate-batch",
        platform_run_id="run-candidate-batch",
        stage_id="stage-l1",
    )


def _candidate(instrument_id: str, *, rank: int, l1: float, l3: float | None, industry: str) -> Candidate:
    scores = [
        CandidateLayerScore(layer=CandidateScoreLayer.L1_PROVIDER, score=l1, source_id="provider:alphasift"),
        CandidateLayerScore(layer=CandidateScoreLayer.L2_DETERMINISTIC, score=50.0, source_id="factor:placeholder"),
    ]
    if l3 is not None:
        scores.append(CandidateLayerScore(layer=CandidateScoreLayer.L3_LLM_OVERLAY, score=l3, source_id="llm:stub"))
    return Candidate(
        instrument=InstrumentId.parse(instrument_id),
        rank=rank,
        final_score=l1,
        scores=tuple(scores),
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
    processed = tuple(
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
    )
    return CrossSectionPostProcessingResult(spec=spec, processed_values=processed, dropped_values=(), warnings=())


def _member(instrument_id: str, *, industry: str) -> UniverseMember:
    return UniverseMember(
        instrument_id=instrument_id,
        market=Market.CN,
        exchange=InstrumentId.parse(instrument_id).exchange.value,
        listed_on=date(2001, 1, 1),
        listing_trading_days=5000,
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
