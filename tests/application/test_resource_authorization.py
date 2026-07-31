from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.application.auth_rbac import (
    AuthMode,
    AuthPermission,
    AuthRole,
    AuthSubject,
    RbacPolicy,
)
from serenity_alpha_lab.application.resource_authorization import (
    RESOURCE_AUTHORIZATION_CONTRACT_VERSION,
    ArtifactDownloadGrant,
    ResourceAuthorizationError,
    ResourceAuthorizationIssueCode,
    ResourceAuthorizationPolicy,
    ResourceAuthorizationStatus,
    ResourceDescriptor,
    ResourceKind,
    ResourceVisibility,
    SignedArtifactUrlIssuer,
    WorkerResourceGrant,
)


NOW = datetime(2026, 7, 30, 9, 30, tzinfo=UTC)
ARTIFACT_HASH = "sha256:" + "a" * 64


def test_object_policy_denies_cross_tenant_team_and_owner_id_guessing() -> None:
    policy = ResourceAuthorizationPolicy.default(RbacPolicy.default(AuthMode.TEAM))
    owner = _subject("analyst-1", roles=(AuthRole.RESEARCHER,))
    same_team_other_user = _subject("analyst-2", roles=(AuthRole.RESEARCHER,))
    wrong_team_user = _subject("analyst-3", teams=("team-beta",), roles=(AuthRole.RESEARCHER,))
    other_tenant_admin = _subject("admin-b", tenant_id="tenant-b", roles=(AuthRole.ADMIN,))
    report = ResourceDescriptor(
        resource_kind=ResourceKind.REPORT,
        resource_id="rpt-private-alpha",
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="analyst-1",
        visibility=ResourceVisibility.PRIVATE,
    )
    evidence = ResourceDescriptor(
        resource_kind=ResourceKind.EVIDENCE,
        resource_id="ev-team-alpha",
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="analyst-1",
        visibility=ResourceVisibility.TEAM,
    )

    owner_decision = policy.authorize(owner, AuthPermission.REPORT_READ, report, now=NOW)
    other_user_decision = policy.authorize(same_team_other_user, AuthPermission.REPORT_READ, report, now=NOW)
    wrong_team_decision = policy.authorize(wrong_team_user, AuthPermission.EVIDENCE_READ, evidence, now=NOW)
    tenant_decision = policy.authorize(other_tenant_admin, AuthPermission.REPORT_READ, report, now=NOW)

    assert owner_decision.allowed is True
    assert owner_decision.status is ResourceAuthorizationStatus.ALLOWED
    assert owner_decision.audit_record.resource["resource_id"] == "rpt-private-alpha"
    assert other_user_decision.allowed is False
    assert other_user_decision.issue_code is ResourceAuthorizationIssueCode.OWNER_SCOPE_MISMATCH
    assert wrong_team_decision.allowed is False
    assert wrong_team_decision.issue_code is ResourceAuthorizationIssueCode.TEAM_SCOPE_MISMATCH
    assert tenant_decision.allowed is False
    assert tenant_decision.issue_code is ResourceAuthorizationIssueCode.TENANT_SCOPE_MISMATCH


def test_artifact_download_issues_short_lived_signed_url_bound_to_parent_scope() -> None:
    policy = ResourceAuthorizationPolicy.default(RbacPolicy.default(AuthMode.TEAM))
    issuer = SignedArtifactUrlIssuer(signing_key=b"offline-test-signing-key", base_path="/api/v1/artifacts")
    owner = _subject("analyst-1", roles=(AuthRole.RESEARCHER,))
    intruder = _subject("analyst-2", teams=("team-beta",), roles=(AuthRole.RESEARCHER,))
    artifact = _artifact_descriptor()

    grant = policy.authorize_artifact_download(owner, artifact, now=NOW)
    denied = policy.authorize_artifact_download(intruder, artifact, now=NOW)
    signed = issuer.issue(grant, now=NOW, ttl=timedelta(minutes=5), nonce="nonce-alpha")

    assert grant.allowed is True
    assert denied.allowed is False
    assert denied.issue_code is ResourceAuthorizationIssueCode.TEAM_SCOPE_MISMATCH
    assert signed.contract_version == RESOURCE_AUTHORIZATION_CONTRACT_VERSION
    assert signed.expires_at == NOW + timedelta(minutes=5)
    assert signed.url.startswith("/api/v1/artifacts/art_metrics/download?")
    assert "offline-test-signing-key" not in signed.url
    assert issuer.verify(
        signed.url,
        artifact=artifact,
        subject_id=owner.subject_id,
        now=NOW + timedelta(minutes=4),
    )

    assert not issuer.verify(
        signed.url.replace("art_metrics", "art_other"),
        artifact=artifact,
        subject_id=owner.subject_id,
        now=NOW + timedelta(minutes=4),
    )
    assert not issuer.verify(
        signed.url,
        artifact=artifact,
        subject_id=owner.subject_id,
        now=NOW + timedelta(minutes=6),
    )


def test_signed_url_handles_encoded_ids_and_rejects_ambiguous_query_values() -> None:
    policy = ResourceAuthorizationPolicy.default(RbacPolicy.default(AuthMode.TEAM))
    issuer = SignedArtifactUrlIssuer(signing_key=b"offline-test-signing-key", base_path="/api/v1/artifacts")
    owner = _subject("analyst-1", roles=(AuthRole.RESEARCHER,))
    artifact = _artifact_descriptor(resource_id="art:metrics@v1=alpha")
    grant = policy.authorize_artifact_download(owner, artifact, now=NOW)
    signed = issuer.issue(grant, now=NOW, ttl=timedelta(minutes=5), nonce="nonce-alpha")

    assert "/art%3Ametrics%40v1%3Dalpha/download?" in signed.url
    assert issuer.verify(signed.url, artifact=artifact, subject_id=owner.subject_id, now=NOW + timedelta(minutes=4))
    assert not issuer.verify(
        signed.url + "&sig=" + "0" * 64,
        artifact=artifact,
        subject_id=owner.subject_id,
        now=NOW + timedelta(minutes=4),
    )


def test_worker_grant_is_task_scoped_and_least_privilege() -> None:
    policy = ResourceAuthorizationPolicy.default(RbacPolicy.default(AuthMode.TEAM))
    worker = _subject("worker-quant-1", roles=(AuthRole.SERVICE_WORKER,))
    run = ResourceDescriptor(
        resource_kind=ResourceKind.RUN,
        resource_id="run-alpha",
        tenant_id="tenant-a",
        team_id="team-alpha",
        visibility=ResourceVisibility.TEAM,
    )
    included_artifact = _artifact_descriptor(
        resource_id="art_metrics",
        parent_resource_kind=ResourceKind.RUN,
        parent_resource_id="run-alpha",
    )
    excluded_artifact = _artifact_descriptor(
        resource_id="art_orders",
        parent_resource_kind=ResourceKind.RUN,
        parent_resource_id="run-alpha",
    )
    forged_parent_artifact = _artifact_descriptor(
        resource_id="art_metrics",
        parent_resource_kind=ResourceKind.REPORT,
        parent_resource_id="rpt-other",
    )

    grant = WorkerResourceGrant.create(
        subject=worker,
        task_id="task-run-alpha",
        run_resource=run,
        artifact_resources=(included_artifact,),
        policy=policy,
        granted_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
    )

    assert grant.authorize(worker, "task-run-alpha", AuthPermission.RUN_READ, run, now=NOW).allowed
    assert grant.authorize(worker, "task-run-alpha", AuthPermission.ARTIFACT_DOWNLOAD, included_artifact, now=NOW).allowed

    wrong_artifact = grant.authorize(worker, "task-run-alpha", AuthPermission.ARTIFACT_DOWNLOAD, excluded_artifact, now=NOW)
    wrong_parent = grant.authorize(
        worker,
        "task-run-alpha",
        AuthPermission.ARTIFACT_DOWNLOAD,
        forged_parent_artifact,
        now=NOW,
    )
    wrong_task = grant.authorize(worker, "task-other", AuthPermission.RUN_READ, run, now=NOW)
    wrong_permission = grant.authorize(worker, "task-run-alpha", AuthPermission.REPORT_READ, run, now=NOW)

    assert wrong_artifact.issue_code is ResourceAuthorizationIssueCode.WORKER_GRANT_SCOPE_MISMATCH
    assert wrong_parent.issue_code is ResourceAuthorizationIssueCode.WORKER_GRANT_SCOPE_MISMATCH
    assert wrong_task.issue_code is ResourceAuthorizationIssueCode.WORKER_GRANT_SCOPE_MISMATCH
    assert wrong_permission.issue_code is ResourceAuthorizationIssueCode.WORKER_GRANT_PERMISSION_MISMATCH
    assert set(grant.to_record()["artifact_ids"]) == {"art_metrics"}
    assert "*" not in json.dumps(grant.to_record(), sort_keys=True)

    with pytest.raises(ResourceAuthorizationError, match="bound to the run"):
        WorkerResourceGrant.create(
            subject=worker,
            task_id="task-run-alpha",
            run_resource=run,
            artifact_resources=(forged_parent_artifact,),
            policy=policy,
            granted_at=NOW,
            expires_at=NOW + timedelta(minutes=30),
        )


def test_artifact_descriptor_rejects_artifact_parent_chains() -> None:
    with pytest.raises(ResourceAuthorizationError, match="parent_resource_kind"):
        _artifact_descriptor(parent_resource_kind=ResourceKind.ARTIFACT, parent_resource_id="art-parent")


def test_authorization_audit_records_are_deterministic_and_do_not_leak_signatures_or_secrets() -> None:
    policy = ResourceAuthorizationPolicy.default(RbacPolicy.default(AuthMode.TEAM))
    issuer = SignedArtifactUrlIssuer(signing_key=b"super-secret-signing-key", base_path="/api/v1/artifacts")
    owner = _subject("analyst-1", roles=(AuthRole.RESEARCHER,))
    artifact = _artifact_descriptor()
    grant = policy.authorize_artifact_download(owner, artifact, now=NOW)
    signed = issuer.issue(grant, now=NOW, ttl=timedelta(minutes=5), nonce="nonce-alpha")

    assert grant.audit_record.to_record() == grant.audit_record.to_record()
    assert grant.audit_record.decision_hash.startswith("sha256:")
    serialized = json.dumps(
        {
            "audit": grant.audit_record.to_record(),
            "signed_url_record": signed.to_record(),
        },
        sort_keys=True,
    )

    assert "super-secret-signing-key" not in serialized
    assert "sig=" not in serialized
    assert "signature" not in grant.audit_record.to_record()
    assert signed.to_record()["signature_hash"].startswith("sha256:")


def _subject(
    subject_id: str,
    *,
    tenant_id: str = "tenant-a",
    teams: tuple[str, ...] = ("team-alpha",),
    roles: tuple[AuthRole, ...],
) -> AuthSubject:
    return AuthSubject(
        subject_id=subject_id,
        tenant_id=tenant_id,
        team_ids=teams,
        roles=roles,
        mode=AuthMode.TEAM,
    )


def _artifact_descriptor(
    *,
    resource_id: str = "art_metrics",
    parent_resource_kind: ResourceKind = ResourceKind.REPORT,
    parent_resource_id: str = "rpt-private-alpha",
) -> ResourceDescriptor:
    return ResourceDescriptor(
        resource_kind=ResourceKind.ARTIFACT,
        resource_id=resource_id,
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="analyst-1",
        visibility=ResourceVisibility.TEAM,
        artifact_sha256=ARTIFACT_HASH,
        parent_resource_kind=parent_resource_kind,
        parent_resource_id=parent_resource_id,
    )
