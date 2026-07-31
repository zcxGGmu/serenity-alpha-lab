from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.candidate_batch import (
    CANDIDATE_BATCH_SCHEMA_NAME,
    Candidate,
    CandidateBatch,
    CandidateBatchError,
    CandidateLayerScore,
    CandidateReason,
    CandidateScoreLayer,
    CandidateSource,
    CandidateSourceType,
    candidate_batch_from_screening_result,
)
from serenity_alpha_lab.application.screening_provider import ScreeningResult
from serenity_alpha_lab.domain.instruments import InstrumentId


REQUESTED = datetime(2026, 7, 23, 9, 25, tzinfo=UTC)
SNAPSHOT = datetime(2026, 7, 23, 9, 30, tzinfo=UTC)
DISCOVERED = datetime(2026, 7, 23, 9, 31, tzinfo=UTC)
RECEIVED = datetime(2026, 7, 23, 9, 31, 2, tzinfo=UTC)
DATASET_VERSIONS = {
    "raw_daily_bars": "dsv_" + "a" * 32,
    "adjusted_daily_bars": "dsv_" + "b" * 32,
    "instrument_master": "dsv_" + "c" * 32,
}


def test_candidate_batch_records_scores_reasons_sources_and_rank_independently() -> None:
    candidate = _candidate_with_scores(include_llm=True)
    batch = CandidateBatch(
        batch_id="cb_quality_momentum_20260723",
        provider_id="alphasift",
        provider_version="0.2.0+9f522747",
        strategy_id="quality_momentum",
        strategy_version="1.0.0",
        market="cn",
        dataset_versions=DATASET_VERSIONS,
        source_snapshot_at=SNAPSHOT,
        discovered_at=DISCOVERED,
        requested_at=REQUESTED,
        received_at=RECEIVED,
        provider_run_id="alphasift-run-001",
        snapshot_count=5000,
        after_filter_count=128,
        candidates=(candidate,),
        sources=_sources(),
        llm_overlay_enabled=True,
        llm_coverage=1.0,
        trace_id="trace-candidate",
        platform_run_id="run-candidate",
        stage_id="stage-l1",
    )

    assert batch.schema_name == CANDIDATE_BATCH_SCHEMA_NAME
    assert batch.candidate_count == 1
    assert batch.dataset_versions == DATASET_VERSIONS
    assert batch.candidates[0].instrument.canonical == "600519.XSHG"
    assert batch.candidates[0].rank == 1
    assert batch.candidates[0].score(CandidateScoreLayer.L1_PROVIDER).score == 88.5
    assert batch.candidates[0].score(CandidateScoreLayer.L2_DETERMINISTIC).score == 90.0
    assert batch.candidates[0].score(CandidateScoreLayer.L3_LLM_OVERLAY).score == 93.0
    assert batch.candidates[0].score(CandidateScoreLayer.L2_DETERMINISTIC).score != batch.candidates[0].score(
        CandidateScoreLayer.L3_LLM_OVERLAY
    ).score
    assert batch.candidates[0].reasons[0].code == "price_volume_breakout"
    assert batch.candidates[0].source_ids == ("provider:alphasift", "dataset:raw_daily_bars", "llm:ranker")

    record = batch.to_record()
    assert record["schema_name"] == "screening.candidate_batch"
    assert record["strategy_version"] == "1.0.0"
    assert record["source_snapshot_at"] == SNAPSHOT.isoformat()
    assert record["discovered_at"] == DISCOVERED.isoformat()
    assert record["candidates"][0]["rank"] == 1
    assert record["candidates"][0]["scores"]["l2_deterministic"]["score"] == 90.0
    assert record["candidates"][0]["scores"]["l3_llm_overlay"]["score"] == 93.0
    assert record["sources"][1]["dataset_version"] == DATASET_VERSIONS["raw_daily_bars"]
    json.dumps(record, sort_keys=True)

    with pytest.raises(TypeError):
        batch.dataset_versions["raw_daily_bars"] = "dsv_" + "d" * 32  # type: ignore[index]
    with pytest.raises(TypeError):
        batch.candidates[0].raw_payload["score"] = 0  # type: ignore[index]
    with pytest.raises(TypeError):
        batch.candidates[0].scores[CandidateScoreLayer.L2_DETERMINISTIC] = CandidateLayerScore(  # type: ignore[index]
            layer=CandidateScoreLayer.L2_DETERMINISTIC,
            score=1,
        )


def test_candidate_batch_rejects_non_versioned_or_inconsistent_contract_data() -> None:
    base_candidate = _candidate_with_scores(include_llm=False)

    with pytest.raises(CandidateBatchError, match="concrete Dataset Version"):
        CandidateBatch(
            **_batch_kwargs(candidates=(base_candidate,), dataset_versions={"raw_daily_bars": "latest"}),
        )

    with pytest.raises(CandidateBatchError, match="duplicate candidate ranks"):
        CandidateBatch(
            **_batch_kwargs(
                candidates=(
                    base_candidate,
                    Candidate(
                        instrument=InstrumentId.from_legacy("000001", market="cn"),
                        name="Ping An Bank",
                        rank=1,
                        final_score=77.0,
                        scores=(
                            CandidateLayerScore(layer=CandidateScoreLayer.L1_PROVIDER, score=77.0),
                            CandidateLayerScore(layer=CandidateScoreLayer.L2_DETERMINISTIC, score=77.0),
                        ),
                        reasons=(CandidateReason(code="fixture", layer=CandidateScoreLayer.L2_DETERMINISTIC),),
                        source_ids=("provider:alphasift",),
                    ),
                )
            ),
        )

    with pytest.raises(CandidateBatchError, match="L1_PROVIDER"):
        CandidateBatch(
            **_batch_kwargs(
                candidates=(
                    Candidate(
                        instrument=InstrumentId.from_legacy("600519", market="cn"),
                        rank=1,
                        final_score=90.0,
                        scores=(CandidateLayerScore(layer=CandidateScoreLayer.L2_DETERMINISTIC, score=90.0),),
                    ),
                )
            ),
        )

    with pytest.raises(CandidateBatchError, match="llm_overlay_enabled"):
        CandidateBatch(
            **_batch_kwargs(candidates=(_candidate_with_scores(include_llm=True),), llm_overlay_enabled=False)
        )

    with pytest.raises(CandidateBatchError, match="concrete Dataset Version"):
        CandidateSource(
            source_id="dataset:latest",
            source_type=CandidateSourceType.DATASET,
            dataset_name="raw_daily_bars",
            dataset_version="latest",
        )

    with pytest.raises(CandidateBatchError, match="discovered_at cannot be before source_snapshot_at"):
        CandidateBatch(
            **_batch_kwargs(
                candidates=(base_candidate,),
                source_snapshot_at=DISCOVERED,
                discovered_at=SNAPSHOT,
            )
        )


def test_candidate_batch_bridge_copies_screening_result_metadata_without_parsing_raw_candidates() -> None:
    screening_result = ScreeningResult(
        provider_id="alphasift",
        provider_version="0.2.0+9f522747",
        strategy_id="quality_momentum",
        strategy_version="1.0.0",
        market="cn",
        dataset_versions=DATASET_VERSIONS,
        candidates=({"code": "600519", "score": 88.5},),
        candidate_count=1,
        snapshot_count=5000,
        after_filter_count=128,
        provider_run_id="alphasift-run-001",
        requested_at=REQUESTED,
        received_at=RECEIVED,
        warnings=("fallback provider unavailable",),
        source_errors=("efinance timeout",),
        llm_overlay_enabled=False,
        trace_id="trace-screening",
        platform_run_id="run-screening",
        stage_id="stage-screening",
    )

    batch = candidate_batch_from_screening_result(
        screening_result,
        candidates=(_candidate_with_scores(include_llm=False),),
        source_snapshot_at=SNAPSHOT,
        sources=_sources()[:2],
        batch_id="cb_from_screening_result",
        metadata={"fixture": "bridge"},
    )

    assert batch.batch_id == "cb_from_screening_result"
    assert batch.provider_id == "alphasift"
    assert batch.provider_version == "0.2.0+9f522747"
    assert batch.strategy_id == "quality_momentum"
    assert batch.strategy_version == "1.0.0"
    assert batch.market == "cn"
    assert batch.dataset_versions == DATASET_VERSIONS
    assert batch.snapshot_count == 5000
    assert batch.after_filter_count == 128
    assert batch.provider_run_id == "alphasift-run-001"
    assert batch.requested_at == REQUESTED
    assert batch.received_at == RECEIVED
    assert batch.discovered_at == RECEIVED
    assert batch.source_snapshot_at == SNAPSHOT
    assert batch.trace_id == "trace-screening"
    assert batch.platform_run_id == "run-screening"
    assert batch.stage_id == "stage-screening"
    assert batch.warnings == ("fallback provider unavailable",)
    assert batch.source_errors == ("efinance timeout",)
    assert batch.metadata["fixture"] == "bridge"

    with pytest.raises(CandidateBatchError, match="ScreeningResult"):
        candidate_batch_from_screening_result(  # type: ignore[arg-type]
            object(),
            candidates=(_candidate_with_scores(include_llm=False),),
            source_snapshot_at=SNAPSHOT,
        )


def _candidate_with_scores(*, include_llm: bool) -> Candidate:
    scores = [
        CandidateLayerScore(
            layer=CandidateScoreLayer.L1_PROVIDER,
            score=88.5,
            raw_score=0.885,
            weight=1.0,
            source_id="provider:alphasift",
            reason_codes=("price_volume_breakout",),
        ),
        CandidateLayerScore(
            layer=CandidateScoreLayer.L2_DETERMINISTIC,
            score=90.0,
            raw_score=90.0,
            weight=0.7,
            source_id="dataset:raw_daily_bars",
            reason_codes=("price_volume_breakout", "quality_filter"),
        ),
    ]
    if include_llm:
        scores.append(
            CandidateLayerScore(
                layer=CandidateScoreLayer.L3_LLM_OVERLAY,
                score=93.0,
                raw_score=9.3,
                weight=0.2,
                source_id="llm:ranker",
                reason_codes=("llm_quality_summary",),
            )
        )

    return Candidate(
        instrument=InstrumentId.from_legacy("600519", market="cn"),
        name="Kweichow Moutai",
        rank=1,
        final_score=91.2 if include_llm else 90.0,
        scores=tuple(scores),
        reasons=(
            CandidateReason(
                code="price_volume_breakout",
                layer=CandidateScoreLayer.L1_PROVIDER,
                message="Provider score flags price and volume strength",
                direction="positive",
                weight=0.6,
                source_ids=("provider:alphasift",),
                details={"threshold": "top_decile"},
            ),
            CandidateReason(
                code="quality_filter",
                layer=CandidateScoreLayer.L2_DETERMINISTIC,
                message="Deterministic quality filter passed",
                direction="positive",
                source_ids=("dataset:raw_daily_bars",),
            ),
        ),
        source_ids=("provider:alphasift", "dataset:raw_daily_bars", "llm:ranker") if include_llm else (
            "provider:alphasift",
            "dataset:raw_daily_bars",
        ),
        raw_payload={"code": "600519", "score": 88.5},
    )


def _sources() -> tuple[CandidateSource, ...]:
    return (
        CandidateSource(
            source_id="provider:alphasift",
            source_type=CandidateSourceType.SCREENING_PROVIDER,
            provider_id="alphasift",
            observed_at=DISCOVERED,
            metadata={"strategy_catalog_version": "fixture"},
        ),
        CandidateSource(
            source_id="dataset:raw_daily_bars",
            source_type=CandidateSourceType.DATASET,
            dataset_name="raw_daily_bars",
            dataset_version=DATASET_VERSIONS["raw_daily_bars"],
            artifact_uri="artifact://raw-daily-bars",
            observed_at=SNAPSHOT,
        ),
        CandidateSource(
            source_id="llm:ranker",
            source_type=CandidateSourceType.LLM_OVERLAY,
            provider_id="stubbed-llm",
            observed_at=DISCOVERED,
        ),
    )


def _batch_kwargs(**overrides):
    values = {
        "batch_id": "cb_quality_momentum_20260723",
        "provider_id": "alphasift",
        "provider_version": "0.2.0+9f522747",
        "strategy_id": "quality_momentum",
        "strategy_version": "1.0.0",
        "market": "cn",
        "dataset_versions": DATASET_VERSIONS,
        "source_snapshot_at": SNAPSHOT,
        "discovered_at": DISCOVERED,
        "requested_at": REQUESTED,
        "received_at": RECEIVED,
        "provider_run_id": "alphasift-run-001",
        "snapshot_count": 5000,
        "after_filter_count": 128,
        "candidates": (_candidate_with_scores(include_llm=False),),
        "sources": _sources()[:2],
        "llm_overlay_enabled": False,
    }
    values.update(overrides)
    return values
