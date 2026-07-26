from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
)
from serenity_alpha_lab.application.evidence_bundle_builder import (
    EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS,
    EvidenceBundleBudget,
    EvidenceBundleBuilder,
    EvidenceBundleError,
    EvidenceBundleRequest,
    EvidenceBundleRole,
    EvidenceBundleStatus,
    estimate_text_tokens,
)
from serenity_alpha_lab.repositories.evidence_store import EvidenceAccessScope, LocalEvidenceStore
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 26, 17, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64
INSTRUMENT = "600519.XSHG"


def test_builder_filters_decision_time_instrument_and_dedupes_by_content_hash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _put(store, _evidence("ev_metric", EvidenceKind.BACKTEST_PERFORMANCE_METRICS), {"metric": "return", "value": "0.024660"})
    _put(
        store,
        _evidence("ev_metric_duplicate", EvidenceKind.BACKTEST_PERFORMANCE_METRICS),
        {"metric": "return", "value": "0.024660"},
    )
    _put(store, _evidence("ev_risk", EvidenceKind.RISK_POLICY_RESULT, summary="Risk policy passed."), {"risk": "pass"})
    _put(
        store,
        _evidence("ev_future", EvidenceKind.BACKTEST_BIAS_AUDIT, available_at=NOW + timedelta(minutes=1)),
        {"audit": "future"},
    )
    _put(
        store,
        _evidence("ev_other_instrument", EvidenceKind.FACTOR_EVALUATION, instrument_id="000001.XSHE"),
        {"factor": "other"},
    )
    _put(store, _evidence("ev_global", EvidenceKind.FORMAL_BACKTEST_API_RECORD, instrument_id=None), {"api": "lineage"})

    bundle = EvidenceBundleBuilder(store).build(
        EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id=INSTRUMENT,
            decision_time=NOW,
            role=EvidenceBundleRole.RISK_PORTFOLIO,
            budget=EvidenceBundleBudget(max_prompt_tokens=2_000),
        )
    )

    assert bundle.status is EvidenceBundleStatus.COMPLETE
    assert [item.evidence.evidence_id for item in bundle.items][:2] == ["ev_risk", "ev_metric"]
    assert {item.evidence.evidence_id for item in bundle.items} == {"ev_risk", "ev_metric", "ev_global"}
    assert {item.evidence_id: item.reason for item in bundle.excluded_items} == {
        "ev_metric_duplicate": "duplicate_content_hash",
        "ev_future": "future_available_at",
        "ev_other_instrument": "instrument_mismatch",
    }
    payload = bundle.to_prompt_payload()
    assert payload["schema_instructions"] == EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS
    assert payload["evidence_records"][0]["evidence_id"] == "ev_risk"
    assert "body" not in payload["evidence_records"][0]


def test_builder_trims_evidence_by_priority_without_truncating_schema_instructions(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _put(store, _evidence("ev_risk", EvidenceKind.RISK_POLICY_RESULT, summary="Risk policy passed."), {"risk": "pass"})
    _put(
        store,
        _evidence("ev_metric", EvidenceKind.BACKTEST_PERFORMANCE_METRICS, summary="A longer metric summary " * 6),
        {"metric": "return", "value": "0.024660"},
    )

    large_bundle = EvidenceBundleBuilder(store).build(
        EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id=INSTRUMENT,
            decision_time=NOW,
            role=EvidenceBundleRole.RISK_PORTFOLIO,
            budget=EvidenceBundleBudget(max_prompt_tokens=2_000),
        )
    )
    schema_tokens = estimate_text_tokens(EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS)
    first_item_tokens = large_bundle.items[0].estimated_tokens

    trimmed = EvidenceBundleBuilder(store).build(
        EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id=INSTRUMENT,
            decision_time=NOW,
            role=EvidenceBundleRole.RISK_PORTFOLIO,
            budget=EvidenceBundleBudget(max_prompt_tokens=schema_tokens + first_item_tokens),
        )
    )

    assert trimmed.status is EvidenceBundleStatus.TRIMMED
    assert [item.evidence.evidence_id for item in trimmed.items] == ["ev_risk"]
    assert {item.reason for item in trimmed.excluded_items} == {"budget_trimmed"}
    assert trimmed.to_prompt_payload()["schema_instructions"] == EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS


def test_builder_rejects_budget_that_cannot_fit_schema_instructions(tmp_path: Path) -> None:
    store = _store(tmp_path)
    schema_tokens = estimate_text_tokens(EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS)

    with pytest.raises(EvidenceBundleError, match="schema instructions"):
        EvidenceBundleBuilder(store).build(
            EvidenceBundleRequest(
                tenant_id="tenant-a",
                team_id="team-alpha",
                owner_user_id="user-1",
                instrument_id=INSTRUMENT,
                decision_time=NOW,
                role=EvidenceBundleRole.TECHNICAL,
                budget=EvidenceBundleBudget(max_prompt_tokens=schema_tokens - 1),
            )
        )


def _store(tmp_path: Path) -> LocalEvidenceStore:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    return LocalEvidenceStore(tmp_path / "evidence", artifact_store=artifact_store)


def _put(store: LocalEvidenceStore, evidence: EvidenceRecord, body: object) -> None:
    store.put_evidence(
        evidence,
        body,
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        access_scope=EvidenceAccessScope.TEAM,
        created_at=NOW,
    )


def _evidence(
    evidence_id: str,
    kind: EvidenceKind,
    *,
    summary: str = "Evidence summary.",
    available_at: datetime = NOW,
    instrument_id: str | None = INSTRUMENT,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=kind,
        evaluation_scope=_scope_for(kind),
        title=f"{kind.value} evidence",
        summary=summary,
        source=EvidenceSource(
            source_id=f"src_{evidence_id}",
            source_type="artifact",
            schema_name=_schema_for(kind),
            schema_version="1.0.0",
        ),
        available_at=available_at,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "1" * 32},
        instrument_id=instrument_id,
        run_id="run-001",
        stage_id=f"stage-{kind.value}",
    )


def _scope_for(kind: EvidenceKind) -> EvidenceEvaluationScope:
    if kind is EvidenceKind.FACTOR_EVALUATION:
        return EvidenceEvaluationScope.FACTOR_EVALUATION
    if kind is EvidenceKind.FORMAL_BACKTEST_API_RECORD:
        return EvidenceEvaluationScope.API_LINEAGE
    return EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST


def _schema_for(kind: EvidenceKind) -> str:
    return {
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: "quant.backtest.performance_metrics",
        EvidenceKind.RISK_POLICY_RESULT: "quant.backtest.risk_policy",
        EvidenceKind.BACKTEST_BIAS_AUDIT: "quant.backtest.bias_audit",
        EvidenceKind.FACTOR_EVALUATION: "quant.factor_evaluation",
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: "application.formal_backtest_api",
    }[kind]
