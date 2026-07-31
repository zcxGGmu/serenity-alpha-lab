from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
)
from serenity_alpha_lab.repositories.evidence_store import (
    EvidenceAccessScope,
    EvidenceRevisionReason,
    EvidenceStoreAccessDenied,
    EvidenceStoreConflict,
    LocalEvidenceStore,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 26, 16, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def _store(tmp_path):
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    return LocalEvidenceStore(tmp_path / "evidence", artifact_store=artifact_store), artifact_store


def _evidence(evidence_id: str = "ev_metric_001") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Backtest metric report",
        summary="Metric report summary",
        source=EvidenceSource(
            source_id="btm_001",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "1" * 32},
        run_id="run-001",
        stage_id="stage-metrics",
    )


def test_store_publishes_sanitized_body_and_queryable_evidence_metadata(tmp_path) -> None:
    store, artifact_store = _store(tmp_path)
    body = {"metric": "cumulative_return", "value": "0.024660", "api_key": "secret"}

    persisted = store.put_evidence(
        _evidence(),
        body,
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        access_scope=EvidenceAccessScope.TEAM,
        created_at=NOW,
        retention_tier=ArtifactRetentionTier.ARCHIVE,
    )

    assert persisted.evidence.evidence_id == "ev_metric_001"
    assert persisted.evidence.artifact_id is not None
    assert persisted.evidence.artifact_hash == persisted.evidence.content_hash
    assert persisted.body_sha256 == persisted.evidence.content_hash
    assert persisted.access_scope is EvidenceAccessScope.TEAM
    assert artifact_store.get_bytes(persisted.body_artifact_id) == (
        b'{"api_key":"[REDACTED]","metric":"cumulative_return","value":"0.024660"}'
    )
    assert store.get_evidence("ev_metric_001", tenant_id="tenant-a", team_id="team-alpha").evidence == persisted.evidence
    assert [item.evidence.evidence_id for item in store.find_evidence(tenant_id="tenant-a", team_id="team-alpha")] == [
        "ev_metric_001"
    ]


def test_store_deduplicates_same_scope_metadata_and_rejects_conflicting_id(tmp_path) -> None:
    store, _ = _store(tmp_path)
    evidence = _evidence()

    first = store.put_evidence(
        evidence,
        {"value": "0.024660"},
        tenant_id="tenant-a",
        team_id="team-alpha",
        created_at=NOW,
    )
    second = store.put_evidence(
        evidence,
        {"value": "0.024660"},
        tenant_id="tenant-a",
        team_id="team-alpha",
        created_at=NOW,
    )

    assert second == first
    conflicting = evidence.model_copy(update={"summary": "different metadata"})
    with pytest.raises(EvidenceStoreConflict, match="already exists"):
        store.put_evidence(
            conflicting,
            {"value": "0.024660"},
            tenant_id="tenant-a",
            team_id="team-alpha",
            created_at=NOW,
        )


def test_revision_creates_new_evidence_and_preserves_previous_record(tmp_path) -> None:
    store, _ = _store(tmp_path)
    original = store.put_evidence(_evidence("ev_metric_001"), {"value": "0.024660"}, tenant_id="tenant-a", created_at=NOW)
    replacement = _evidence("ev_metric_002").model_copy(update={"summary": "Corrected metric summary"})

    revision = store.revise_evidence(
        previous_evidence_id=original.evidence.evidence_id,
        replacement_evidence=replacement,
        body={"value": "0.024661"},
        tenant_id="tenant-a",
        created_at=NOW,
        reason=EvidenceRevisionReason.CORRECTION,
        note="corrected rounding",
    )

    assert revision.previous_evidence_id == "ev_metric_001"
    assert revision.replacement_evidence_id == "ev_metric_002"
    assert store.get_evidence("ev_metric_001", tenant_id="tenant-a").evidence.summary == "Metric report summary"
    assert store.get_evidence("ev_metric_002", tenant_id="tenant-a").evidence.summary == "Corrected metric summary"
    assert [item.replacement_evidence_id for item in store.list_revisions(tenant_id="tenant-a")] == ["ev_metric_002"]


def test_private_and_team_scopes_are_isolated(tmp_path) -> None:
    store, _ = _store(tmp_path)
    store.put_evidence(
        _evidence("ev_private"),
        {"value": 1},
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        access_scope=EvidenceAccessScope.PRIVATE,
        created_at=NOW,
    )

    with pytest.raises(EvidenceStoreAccessDenied):
        store.get_evidence("ev_private", tenant_id="tenant-a", team_id="team-alpha", owner_user_id="user-2")
    with pytest.raises(EvidenceStoreAccessDenied):
        store.get_evidence("ev_private", tenant_id="tenant-a", team_id="team-beta", owner_user_id="user-1")
