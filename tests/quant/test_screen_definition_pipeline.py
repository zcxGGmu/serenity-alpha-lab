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
    SCREEN_PIPELINE_CONTENT_TYPE,
    SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME,
    SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION,
    SCREEN_DEFINITION_SCHEMA_NAME,
    ScreenDefinition,
    ScreenDefinitionStatus,
    ScreenFactorSpec,
    ScreenFactorStageSpec,
    ScreenLlmOverlayStageSpec,
    ScreenPipelineError,
    ScreenPipelineStage,
    ScreenProviderStageSpec,
    ScreenRiskGateSpec,
    publish_screen_pipeline_snapshot,
    run_screen_pipeline,
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


def test_screen_definition_requires_concrete_versions_published_runs_and_version_changes() -> None:
    definition = _screen_definition()

    assert definition.schema_name == SCREEN_DEFINITION_SCHEMA_NAME
    assert definition.status is ScreenDefinitionStatus.PUBLISHED
    assert definition.definition_version_id.startswith("sdv_")
    assert definition.dataset_versions == DATASET_VERSIONS

    changed_weight = _screen_definition(
        factor_stage=ScreenFactorStageSpec(
            factors=(
                ScreenFactorSpec("quality_factor", FACTOR_QUALITY_VERSION, weight=0.90),
                ScreenFactorSpec("momentum_factor", FACTOR_MOMENTUM_VERSION, weight=0.10),
            ),
            score_weight=0.80,
        )
    )
    changed_gate = _screen_definition(risk_gate=ScreenRiskGateSpec(top_n=3, max_per_industry=1))

    assert changed_weight.definition_version_id != definition.definition_version_id
    assert changed_gate.definition_version_id != definition.definition_version_id

    with pytest.raises(ScreenPipelineError, match="concrete Dataset Version"):
        _screen_definition(dataset_versions={"universe": "latest"})

    with pytest.raises(ScreenPipelineError, match="published ScreenDefinition"):
        run_screen_pipeline(
            _screen_definition(status=ScreenDefinitionStatus.DRAFT),
            as_of=AS_OF,
            universe_snapshot=_universe_snapshot(),
            candidate_batch=_candidate_batch(include_llm=True),
            factor_results=_factor_results(),
            created_at=NOW,
        )

    with pytest.raises(ScreenPipelineError, match="candidate batch dataset version mismatch"):
        run_screen_pipeline(
            _screen_definition(),
            as_of=AS_OF,
            universe_snapshot=_universe_snapshot(),
            candidate_batch=_candidate_batch(
                include_llm=True,
                dataset_versions={
                    "raw_daily_bars": "dsv_" + "9" * 32,
                    "instrument_master": DATASET_VERSIONS["instrument_master"],
                },
            ),
            factor_results=_factor_results(),
            created_at=NOW,
        )


def test_pipeline_applies_l0_to_l4_and_llm_cannot_bypass_hard_filters() -> None:
    snapshot = run_screen_pipeline(
        _screen_definition(),
        as_of=AS_OF,
        universe_snapshot=_universe_snapshot(),
        candidate_batch=_candidate_batch(include_llm=True),
        factor_results=_factor_results(),
        created_at=NOW,
        trace_id="trace-screen-pipeline",
        run_id="run-screen-pipeline",
        stage_id="stage-screen-pipeline",
    )

    assert snapshot.pipeline_snapshot_id.startswith("sps_")
    assert snapshot.definition_version_id == _screen_definition().definition_version_id
    assert [trace.stage for trace in snapshot.stage_traces] == [
        ScreenPipelineStage.L0_UNIVERSE,
        ScreenPipelineStage.L1_PROVIDER,
        ScreenPipelineStage.L2_FACTOR,
        ScreenPipelineStage.L3_LLM_OVERLAY,
        ScreenPipelineStage.L4_FINAL,
    ]
    assert [candidate.instrument_id for candidate in snapshot.passed_candidates] == [
        "600519.XSHG",
        "000001.XSHE",
    ]
    assert snapshot.passed_candidates[0].rank == 1
    assert snapshot.passed_candidates[0].scores["l2_factor"] > snapshot.passed_candidates[1].scores["l2_factor"]

    exclusions = {exclusion.instrument_id: exclusion for exclusion in snapshot.exclusions}
    assert exclusions["600090.XSHG"].failed_stage is ScreenPipelineStage.L0_UNIVERSE
    assert exclusions["600090.XSHG"].rule_id == "l0_universe_member"
    assert exclusions["600090.XSHG"].scores["l3_llm_overlay"] == 100.0
    assert exclusions["600091.XSHG"].failed_stage is ScreenPipelineStage.L4_FINAL
    assert exclusions["600091.XSHG"].rule_id == "max_per_industry"

    record = snapshot.to_record()
    assert record["schema_name"] == SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME
    assert record["schema_version"] == SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION
    assert record["definition"]["definition_version_id"] == snapshot.definition_version_id
    assert record["stage_traces"][0]["stage"] == "l0_universe"
    json.dumps(record, sort_keys=True)


def test_pipeline_snapshot_publishes_deterministic_artifact(tmp_path: Path) -> None:
    snapshot = run_screen_pipeline(
        _screen_definition(),
        as_of=AS_OF,
        universe_snapshot=_universe_snapshot(),
        candidate_batch=_candidate_batch(include_llm=True),
        factor_results=_factor_results(),
        created_at=NOW,
        run_id="run-screen-pipeline",
        stage_id="stage-screen-pipeline",
    )
    store = LocalArtifactStore(tmp_path / "artifacts")

    artifact = publish_screen_pipeline_snapshot(snapshot, store)
    repeated = publish_screen_pipeline_snapshot(snapshot, store)
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert repeated.artifact_id == artifact.artifact_id
    assert artifact.schema_name == SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME
    assert artifact.schema_version == SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION
    assert artifact.content_type == SCREEN_PIPELINE_CONTENT_TYPE
    assert artifact.produced_by_run_id == "run-screen-pipeline"
    assert artifact.produced_by_stage_id == "stage-screen-pipeline"
    assert payload["pipeline_snapshot_id"] == snapshot.pipeline_snapshot_id
    assert payload["passed_count"] == 2
    assert payload["exclusion_count"] == 2


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


def _candidate_batch(
    *,
    include_llm: bool,
    dataset_versions: dict[str, str] | None = None,
) -> CandidateBatch:
    return CandidateBatch(
        batch_id="cb_quality_momentum",
        provider_id="alphasift",
        provider_version="0.2.0+9f522747",
        strategy_id="quality_momentum",
        strategy_version="1.0.0",
        market="cn",
        dataset_versions=dataset_versions
        or {
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
