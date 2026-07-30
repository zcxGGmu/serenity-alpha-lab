from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

from serenity_alpha_lab.application.auth_rbac import (
    AuthPermission,
    AuthRole,
    AuthSubject,
    AuthorizationIssueCode,
    RbacPolicy,
    ResourceScope,
)


RESOURCE_AUTHORIZATION_CONTRACT_VERSION = "security.resource_artifact_authorization@1.0.0"
RESOURCE_AUTHORIZATION_SCHEMA_NAME = "security.resource_authorization"
RESOURCE_AUTHORIZATION_SCHEMA_VERSION = "1.0.0"


class ResourceAuthorizationError(ValueError):
    """Raised when object-level resource authorization contracts are invalid."""


class ResourceKind(StrEnum):
    RUN = "run"
    DEFINITION = "definition"
    EVIDENCE = "evidence"
    REPORT = "report"
    ARTIFACT = "artifact"


class ResourceVisibility(StrEnum):
    PRIVATE = "private"
    TEAM = "team"
    TENANT = "tenant"


class ResourceAuthorizationStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class ResourceAuthorizationIssueCode(StrEnum):
    TENANT_SCOPE_MISMATCH = "tenant_scope_mismatch"
    TEAM_SCOPE_MISMATCH = "team_scope_mismatch"
    OWNER_SCOPE_MISMATCH = "owner_scope_mismatch"
    PERMISSION_NOT_GRANTED = "permission_not_granted"
    RESOURCE_KIND_PERMISSION_MISMATCH = "resource_kind_permission_mismatch"
    ARTIFACT_PARENT_SCOPE_MISMATCH = "artifact_parent_scope_mismatch"
    ARTIFACT_HASH_REQUIRED = "artifact_hash_required"
    SIGNED_URL_EXPIRED = "signed_url_expired"
    SIGNED_URL_SCOPE_MISMATCH = "signed_url_scope_mismatch"
    WORKER_GRANT_EXPIRED = "worker_grant_expired"
    WORKER_GRANT_PERMISSION_MISMATCH = "worker_grant_permission_mismatch"
    WORKER_GRANT_SCOPE_MISMATCH = "worker_grant_scope_mismatch"


@dataclass(frozen=True, slots=True)
class ResourceDescriptor:
    resource_kind: ResourceKind | str
    resource_id: str
    tenant_id: str
    visibility: ResourceVisibility | str
    team_id: str | None = None
    owner_user_id: str | None = None
    artifact_sha256: str | None = None
    parent_resource_kind: ResourceKind | str | None = None
    parent_resource_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = ResourceKind(self.resource_kind)
        visibility = ResourceVisibility(self.visibility)
        object.__setattr__(self, "resource_kind", kind)
        object.__setattr__(self, "resource_id", _safe_id("resource_id", self.resource_id))
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "visibility", visibility)
        object.__setattr__(self, "team_id", _optional_safe_id("team_id", self.team_id))
        object.__setattr__(self, "owner_user_id", _optional_safe_id("owner_user_id", self.owner_user_id))
        object.__setattr__(self, "artifact_sha256", _optional_sha256("artifact_sha256", self.artifact_sha256))
        parent_kind = ResourceKind(self.parent_resource_kind) if self.parent_resource_kind is not None else None
        object.__setattr__(self, "parent_resource_kind", parent_kind)
        object.__setattr__(self, "parent_resource_id", _optional_safe_id("parent_resource_id", self.parent_resource_id))
        object.__setattr__(self, "metadata", {str(key): str(value) for key, value in sorted(dict(self.metadata).items())})
        if visibility is ResourceVisibility.PRIVATE and self.owner_user_id is None:
            raise ResourceAuthorizationError("private resources require owner_user_id")
        if visibility is ResourceVisibility.TEAM and self.team_id is None:
            raise ResourceAuthorizationError("team resources require team_id")
        if kind is ResourceKind.ARTIFACT and self.parent_resource_kind is None:
            raise ResourceAuthorizationError("artifact resources require parent_resource_kind")
        if kind is ResourceKind.ARTIFACT and self.parent_resource_id is None:
            raise ResourceAuthorizationError("artifact resources require parent_resource_id")
        if kind is ResourceKind.ARTIFACT and self.parent_resource_kind is ResourceKind.ARTIFACT:
            raise ResourceAuthorizationError("artifact parent_resource_kind must be run, definition, evidence or report")

    def to_scope(self) -> ResourceScope:
        return ResourceScope(
            tenant_id=self.tenant_id,
            team_id=self.team_id,
            owner_user_id=self.owner_user_id,
            resource_kind=self.resource_kind.value,
            resource_id=self.resource_id,
        )

    def to_record(self) -> dict[str, object]:
        return _drop_none(
            {
                "resource_kind": self.resource_kind.value,
                "resource_id": self.resource_id,
                "tenant_id": self.tenant_id,
                "team_id": self.team_id,
                "owner_user_id": self.owner_user_id,
                "visibility": self.visibility.value,
                "artifact_sha256": self.artifact_sha256,
                "parent_resource_kind": self.parent_resource_kind.value if self.parent_resource_kind else None,
                "parent_resource_id": self.parent_resource_id,
                "metadata": dict(self.metadata) if self.metadata else None,
                "scope_hash": self.scope_hash,
            }
        )

    @property
    def scope_hash(self) -> str:
        payload = {
            "artifact_sha256": self.artifact_sha256,
            "parent_resource_id": self.parent_resource_id,
            "parent_resource_kind": self.parent_resource_kind.value if self.parent_resource_kind else None,
            "resource_id": self.resource_id,
            "resource_kind": self.resource_kind.value,
            "team_id": self.team_id,
            "tenant_id": self.tenant_id,
            "visibility": self.visibility.value,
        }
        return _hash_record(payload)


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationAuditRecord:
    subject_id: str
    permission: AuthPermission
    resource: Mapping[str, object]
    status: ResourceAuthorizationStatus
    created_at: datetime
    issue_code: ResourceAuthorizationIssueCode | None = None
    detail: str | None = None
    matched_roles: Sequence[AuthRole] = ()
    contract_version: str = RESOURCE_AUTHORIZATION_CONTRACT_VERSION

    @classmethod
    def create(
        cls,
        *,
        subject: AuthSubject,
        permission: AuthPermission,
        resource: ResourceDescriptor,
        status: ResourceAuthorizationStatus,
        created_at: datetime,
        issue_code: ResourceAuthorizationIssueCode | None = None,
        detail: str | None = None,
        matched_roles: Sequence[AuthRole] = (),
    ) -> ResourceAuthorizationAuditRecord:
        _require_aware_datetime("created_at", created_at)
        return cls(
            subject_id=subject.subject_id,
            permission=permission,
            resource=resource.to_record(),
            status=status,
            issue_code=issue_code,
            detail=detail,
            matched_roles=tuple(matched_roles),
            created_at=created_at,
        )

    @property
    def decision_hash(self) -> str:
        return _hash_record(self._record(include_hash=False))

    @property
    def decision_id(self) -> str:
        return f"rad_{self.decision_hash.removeprefix('sha256:')[:32]}"

    def to_record(self) -> dict[str, object]:
        return self._record(include_hash=True)

    def _record(self, *, include_hash: bool) -> dict[str, object]:
        record = _drop_none(
            {
                "contract_version": self.contract_version,
                "decision_id": self.decision_id if include_hash else None,
                "decision_hash": self.decision_hash if include_hash else None,
                "status": self.status.value,
                "subject_id": self.subject_id,
                "permission": self.permission.value,
                "resource": dict(self.resource),
                "matched_roles": [role.value for role in self.matched_roles],
                "issue_code": self.issue_code.value if self.issue_code is not None else None,
                "detail": self.detail,
                "created_at": self.created_at.isoformat(),
            }
        )
        return record


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationDecision:
    status: ResourceAuthorizationStatus
    subject_id: str
    permission: AuthPermission
    resource: ResourceDescriptor
    audit_record: ResourceAuthorizationAuditRecord
    issue_code: ResourceAuthorizationIssueCode | None = None
    detail: str | None = None
    matched_roles: Sequence[AuthRole] = ()
    contract_version: str = RESOURCE_AUTHORIZATION_CONTRACT_VERSION

    @property
    def allowed(self) -> bool:
        return self.status is ResourceAuthorizationStatus.ALLOWED

    def to_record(self) -> dict[str, object]:
        return _drop_none(
            {
                "contract_version": self.contract_version,
                "status": self.status.value,
                "subject_id": self.subject_id,
                "permission": self.permission.value,
                "resource": self.resource.to_record(),
                "matched_roles": [role.value for role in self.matched_roles],
                "issue_code": self.issue_code.value if self.issue_code is not None else None,
                "detail": self.detail,
                "audit": self.audit_record.to_record(),
            }
        )


@dataclass(frozen=True, slots=True)
class ArtifactDownloadGrant:
    decision: ResourceAuthorizationDecision
    artifact: ResourceDescriptor
    parent_resource_kind: ResourceKind
    parent_resource_id: str

    @property
    def allowed(self) -> bool:
        return self.decision.allowed

    @property
    def status(self) -> ResourceAuthorizationStatus:
        return self.decision.status

    @property
    def issue_code(self) -> ResourceAuthorizationIssueCode | None:
        return self.decision.issue_code

    @property
    def audit_record(self) -> ResourceAuthorizationAuditRecord:
        return self.decision.audit_record

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": RESOURCE_AUTHORIZATION_CONTRACT_VERSION,
            "decision": self.decision.to_record(),
            "artifact": self.artifact.to_record(),
            "parent_resource_kind": self.parent_resource_kind.value,
            "parent_resource_id": self.parent_resource_id,
        }


@dataclass(frozen=True, slots=True)
class SignedArtifactUrl:
    url: str
    artifact_id: str
    artifact_sha256: str
    subject_id: str
    tenant_id: str
    expires_at: datetime
    scope_hash: str
    signature: str = field(repr=False)
    contract_version: str = RESOURCE_AUTHORIZATION_CONTRACT_VERSION

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "subject_id": self.subject_id,
            "tenant_id": self.tenant_id,
            "expires_at": self.expires_at.isoformat(),
            "scope_hash": self.scope_hash,
            "signature_hash": _hash_text(self.signature),
        }


class SignedArtifactUrlIssuer:
    """Issues and verifies offline, short-lived artifact download URL contracts."""

    def __init__(
        self,
        *,
        signing_key: bytes,
        base_path: str,
        max_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        if type(signing_key) is not bytes or not signing_key:
            raise ResourceAuthorizationError("signing_key must be non-empty bytes")
        self._signing_key = signing_key
        self._base_path = "/" + _required_string("base_path", base_path).strip("/")
        if type(max_ttl) is not timedelta or max_ttl.total_seconds() <= 0:
            raise ResourceAuthorizationError("max_ttl must be positive")
        self._max_ttl = max_ttl

    def issue(
        self,
        grant: ArtifactDownloadGrant,
        *,
        now: datetime,
        ttl: timedelta,
        nonce: str | None = None,
    ) -> SignedArtifactUrl:
        if type(grant) is not ArtifactDownloadGrant:
            raise ResourceAuthorizationError("grant must be an ArtifactDownloadGrant")
        if not grant.allowed:
            raise ResourceAuthorizationError("cannot issue signed URL for denied artifact grant")
        _require_aware_datetime("now", now)
        if type(ttl) is not timedelta or ttl.total_seconds() <= 0 or ttl > self._max_ttl:
            raise ResourceAuthorizationError("ttl must be positive and no greater than max_ttl")
        artifact = grant.artifact
        if artifact.artifact_sha256 is None:
            raise ResourceAuthorizationError("artifact_sha256 is required")
        expires_at = now + ttl
        nonce_value = _safe_id("nonce", nonce or _default_nonce(grant, expires_at))
        payload = _signed_url_payload(
            artifact=artifact,
            subject_id=grant.decision.subject_id,
            expires_at=expires_at,
            nonce=nonce_value,
        )
        signature = _hmac_signature(self._signing_key, payload)
        query = urlencode(
            {
                "expires_at": expires_at.isoformat(),
                "nonce": nonce_value,
                "scope_hash": artifact.scope_hash,
                "sig": signature,
                "subject_id": grant.decision.subject_id,
                "tenant_id": artifact.tenant_id,
            }
        )
        artifact_id = quote(artifact.resource_id, safe="")
        url = f"{self._base_path}/{artifact_id}/download?{query}"
        return SignedArtifactUrl(
            url=url,
            artifact_id=artifact.resource_id,
            artifact_sha256=artifact.artifact_sha256,
            subject_id=grant.decision.subject_id,
            tenant_id=artifact.tenant_id,
            expires_at=expires_at,
            scope_hash=artifact.scope_hash,
            signature=signature,
        )

    def verify(
        self,
        url: str,
        *,
        artifact: ResourceDescriptor,
        subject_id: str,
        now: datetime,
    ) -> bool:
        if type(artifact) is not ResourceDescriptor:
            raise ResourceAuthorizationError("artifact must be a ResourceDescriptor")
        if artifact.resource_kind is not ResourceKind.ARTIFACT or artifact.artifact_sha256 is None:
            return False
        _require_aware_datetime("now", now)
        parsed = urlparse(_required_string("url", url))
        parts = [part for part in parsed.path.split("/") if part]
        base_parts = [part for part in self._base_path.split("/") if part]
        if len(parts) != len(base_parts) + 2 or parts[: len(base_parts)] != base_parts:
            return False
        artifact_id = unquote(parts[-2])
        action = parts[-1]
        if action != "download" or artifact_id != artifact.resource_id:
            return False
        required_keys = {"expires_at", "nonce", "scope_hash", "sig", "subject_id", "tenant_id"}
        parsed_query = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(parsed_query.get(key, ())) != 1 for key in required_keys):
            return False
        query = {key: parsed_query[key][0] for key in required_keys}
        if not required_keys.issubset(query):
            return False
        if query["subject_id"] != subject_id or query["tenant_id"] != artifact.tenant_id or query["scope_hash"] != artifact.scope_hash:
            return False
        try:
            expires_at = datetime.fromisoformat(query["expires_at"])
        except ValueError:
            return False
        if expires_at.tzinfo is None or expires_at.utcoffset() is None or now >= expires_at:
            return False
        payload = _signed_url_payload(
            artifact=artifact,
            subject_id=query["subject_id"],
            expires_at=expires_at,
            nonce=query["nonce"],
        )
        expected = _hmac_signature(self._signing_key, payload)
        return hmac.compare_digest(expected, query["sig"])


@dataclass(frozen=True, slots=True)
class WorkerResourceGrant:
    subject_id: str
    task_id: str
    tenant_id: str
    team_id: str | None
    run_id: str
    artifact_ids: Sequence[str]
    permissions: Sequence[AuthPermission]
    granted_at: datetime
    expires_at: datetime
    contract_version: str = RESOURCE_AUTHORIZATION_CONTRACT_VERSION

    @classmethod
    def create(
        cls,
        *,
        subject: AuthSubject,
        task_id: str,
        run_resource: ResourceDescriptor,
        artifact_resources: Sequence[ResourceDescriptor],
        policy: ResourceAuthorizationPolicy,
        granted_at: datetime,
        expires_at: datetime,
    ) -> WorkerResourceGrant:
        if type(policy) is not ResourceAuthorizationPolicy:
            raise ResourceAuthorizationError("policy must be a ResourceAuthorizationPolicy")
        _require_aware_datetime("granted_at", granted_at)
        _require_aware_datetime("expires_at", expires_at)
        service_decision = policy.authorize(subject, AuthPermission.SERVICE_EXECUTE, run_resource, now=granted_at)
        run_read_decision = policy.authorize(subject, AuthPermission.RUN_READ, run_resource, now=granted_at)
        if not service_decision.allowed or not run_read_decision.allowed:
            raise ResourceAuthorizationError("service worker is not authorized for this run")
        if expires_at <= granted_at:
            raise ResourceAuthorizationError("expires_at must be after granted_at")
        artifact_ids = []
        for artifact in artifact_resources:
            if type(artifact) is not ResourceDescriptor or artifact.resource_kind is not ResourceKind.ARTIFACT:
                raise ResourceAuthorizationError("artifact_resources must contain artifact descriptors")
            if artifact.tenant_id != run_resource.tenant_id or artifact.team_id != run_resource.team_id:
                raise ResourceAuthorizationError("worker artifact grant scope must match run scope")
            if artifact.parent_resource_kind is not ResourceKind.RUN or artifact.parent_resource_id != run_resource.resource_id:
                raise ResourceAuthorizationError("worker artifact grant must be bound to the run")
            artifact_ids.append(artifact.resource_id)
        return cls(
            subject_id=subject.subject_id,
            task_id=_safe_id("task_id", task_id),
            tenant_id=run_resource.tenant_id,
            team_id=run_resource.team_id,
            run_id=run_resource.resource_id,
            artifact_ids=tuple(dict.fromkeys(artifact_ids)),
            permissions=(AuthPermission.RUN_READ, AuthPermission.ARTIFACT_DOWNLOAD),
            granted_at=granted_at,
            expires_at=expires_at,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _safe_id("subject_id", self.subject_id))
        object.__setattr__(self, "task_id", _safe_id("task_id", self.task_id))
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "team_id", _optional_safe_id("team_id", self.team_id))
        object.__setattr__(self, "run_id", _safe_id("run_id", self.run_id))
        object.__setattr__(self, "artifact_ids", _string_tuple("artifact_id", self.artifact_ids))
        object.__setattr__(self, "permissions", tuple(AuthPermission(permission) for permission in self.permissions))
        _require_aware_datetime("granted_at", self.granted_at)
        _require_aware_datetime("expires_at", self.expires_at)

    def authorize(
        self,
        subject: AuthSubject,
        task_id: str,
        permission: AuthPermission | str,
        resource: ResourceDescriptor,
        *,
        now: datetime,
    ) -> ResourceAuthorizationDecision:
        _require_aware_datetime("now", now)
        requested = AuthPermission(permission)
        if requested not in self.permissions:
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.WORKER_GRANT_PERMISSION_MISMATCH,
                detail="permission is not included in worker grant",
            )
        if now >= self.expires_at:
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.WORKER_GRANT_EXPIRED,
                detail="worker grant has expired",
            )
        if subject.subject_id != self.subject_id or task_id != self.task_id or resource.tenant_id != self.tenant_id or resource.team_id != self.team_id:
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.WORKER_GRANT_SCOPE_MISMATCH,
                detail="resource is outside this worker task grant",
            )
        allowed_resource = (
            requested is AuthPermission.RUN_READ
            and resource.resource_kind is ResourceKind.RUN
            and resource.resource_id == self.run_id
        ) or (
            requested is AuthPermission.ARTIFACT_DOWNLOAD
            and resource.resource_kind is ResourceKind.ARTIFACT
            and resource.resource_id in self.artifact_ids
            and resource.parent_resource_kind is ResourceKind.RUN
            and resource.parent_resource_id == self.run_id
        )
        if not allowed_resource:
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.WORKER_GRANT_SCOPE_MISMATCH,
                detail="resource id is not included in worker grant",
            )
        return _decision(
            subject=subject,
            permission=requested,
            resource=resource,
            status=ResourceAuthorizationStatus.ALLOWED,
            now=now,
            matched_roles=(AuthRole.SERVICE_WORKER,),
        )

    def to_record(self) -> dict[str, object]:
        content = {
            "contract_version": self.contract_version,
            "subject_id": self.subject_id,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "run_id": self.run_id,
            "artifact_ids": list(self.artifact_ids),
            "permissions": [permission.value for permission in self.permissions],
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        content["grant_hash"] = _hash_record(content)
        return _drop_none(content)


class ResourceAuthorizationPolicy:
    """Object-level authorization facade layered on top of SAL-P6-001 RBAC."""

    def __init__(self, rbac_policy: RbacPolicy) -> None:
        if type(rbac_policy) is not RbacPolicy:
            raise ResourceAuthorizationError("rbac_policy must be an RbacPolicy")
        self._rbac_policy = rbac_policy

    @classmethod
    def default(cls, rbac_policy: RbacPolicy) -> ResourceAuthorizationPolicy:
        return cls(rbac_policy)

    def authorize(
        self,
        subject: AuthSubject,
        permission: AuthPermission | str,
        resource: ResourceDescriptor,
        *,
        now: datetime,
    ) -> ResourceAuthorizationDecision:
        if type(subject) is not AuthSubject:
            raise ResourceAuthorizationError("subject must be an AuthSubject")
        if type(resource) is not ResourceDescriptor:
            raise ResourceAuthorizationError("resource must be a ResourceDescriptor")
        _require_aware_datetime("now", now)
        requested = AuthPermission(permission)
        if requested not in _permissions_for(resource.resource_kind):
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.RESOURCE_KIND_PERMISSION_MISMATCH,
                detail="permission does not apply to resource kind",
            )
        coarse = self._rbac_policy.authorize(subject, requested, resource.to_scope())
        if not coarse.allowed:
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=_from_rbac_issue(coarse.issue_code),
                detail=coarse.detail or "RBAC policy denied access",
            )
        if (
            resource.visibility is ResourceVisibility.PRIVATE
            and not _has_object_admin_role(subject)
            and resource.owner_user_id != subject.subject_id
        ):
            return _decision(
                subject=subject,
                permission=requested,
                resource=resource,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.OWNER_SCOPE_MISMATCH,
                detail="subject does not own this private resource",
            )
        return _decision(
            subject=subject,
            permission=requested,
            resource=resource,
            status=ResourceAuthorizationStatus.ALLOWED,
            now=now,
            matched_roles=coarse.matched_roles,
        )

    def authorize_artifact_download(
        self,
        subject: AuthSubject,
        artifact: ResourceDescriptor,
        *,
        now: datetime,
    ) -> ArtifactDownloadGrant:
        if type(artifact) is not ResourceDescriptor or artifact.resource_kind is not ResourceKind.ARTIFACT:
            raise ResourceAuthorizationError("artifact must be an artifact ResourceDescriptor")
        if artifact.artifact_sha256 is None:
            denied = _decision(
                subject=subject,
                permission=AuthPermission.ARTIFACT_DOWNLOAD,
                resource=artifact,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.ARTIFACT_HASH_REQUIRED,
                detail="artifact_sha256 is required before issuing download access",
            )
            return ArtifactDownloadGrant(
                decision=denied,
                artifact=artifact,
                parent_resource_kind=artifact.parent_resource_kind or ResourceKind.ARTIFACT,
                parent_resource_id=artifact.parent_resource_id or artifact.resource_id,
            )
        artifact_decision = self.authorize(subject, AuthPermission.ARTIFACT_DOWNLOAD, artifact, now=now)
        if not artifact_decision.allowed:
            return ArtifactDownloadGrant(
                decision=artifact_decision,
                artifact=artifact,
                parent_resource_kind=artifact.parent_resource_kind or ResourceKind.ARTIFACT,
                parent_resource_id=artifact.parent_resource_id or artifact.resource_id,
            )
        parent_kind = artifact.parent_resource_kind
        parent_id = artifact.parent_resource_id
        if parent_kind is None or parent_id is None:
            denied = _decision(
                subject=subject,
                permission=AuthPermission.ARTIFACT_DOWNLOAD,
                resource=artifact,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=ResourceAuthorizationIssueCode.ARTIFACT_PARENT_SCOPE_MISMATCH,
                detail="artifact must be bound to a parent resource",
            )
            return ArtifactDownloadGrant(decision=denied, artifact=artifact, parent_resource_kind=ResourceKind.ARTIFACT, parent_resource_id=artifact.resource_id)
        parent_resource = ResourceDescriptor(
            resource_kind=parent_kind,
            resource_id=parent_id,
            tenant_id=artifact.tenant_id,
            team_id=artifact.team_id,
            owner_user_id=artifact.owner_user_id,
            visibility=artifact.visibility,
        )
        parent_permission = _read_permission_for(parent_kind)
        parent_decision = self.authorize(subject, parent_permission, parent_resource, now=now)
        if not parent_decision.allowed:
            denied = _decision(
                subject=subject,
                permission=AuthPermission.ARTIFACT_DOWNLOAD,
                resource=artifact,
                status=ResourceAuthorizationStatus.DENIED,
                now=now,
                issue_code=parent_decision.issue_code or ResourceAuthorizationIssueCode.ARTIFACT_PARENT_SCOPE_MISMATCH,
                detail=parent_decision.detail or "parent resource does not grant download access",
            )
            return ArtifactDownloadGrant(decision=denied, artifact=artifact, parent_resource_kind=parent_kind, parent_resource_id=parent_id)
        return ArtifactDownloadGrant(
            decision=artifact_decision,
            artifact=artifact,
            parent_resource_kind=parent_kind,
            parent_resource_id=parent_id,
        )


def _decision(
    *,
    subject: AuthSubject,
    permission: AuthPermission,
    resource: ResourceDescriptor,
    status: ResourceAuthorizationStatus,
    now: datetime,
    issue_code: ResourceAuthorizationIssueCode | None = None,
    detail: str | None = None,
    matched_roles: Sequence[AuthRole] = (),
) -> ResourceAuthorizationDecision:
    audit = ResourceAuthorizationAuditRecord.create(
        subject=subject,
        permission=permission,
        resource=resource,
        status=status,
        issue_code=issue_code,
        detail=detail,
        matched_roles=matched_roles,
        created_at=now,
    )
    return ResourceAuthorizationDecision(
        status=status,
        subject_id=subject.subject_id,
        permission=permission,
        resource=resource,
        audit_record=audit,
        issue_code=issue_code,
        detail=detail,
        matched_roles=tuple(matched_roles),
    )


def _permissions_for(kind: ResourceKind) -> tuple[AuthPermission, ...]:
    return {
        ResourceKind.RUN: (
            AuthPermission.RUN_READ,
            AuthPermission.RUN_CREATE,
            AuthPermission.RUN_CANCEL,
            AuthPermission.SERVICE_EXECUTE,
        ),
        ResourceKind.DEFINITION: (AuthPermission.DEFINITION_READ, AuthPermission.DEFINITION_WRITE),
        ResourceKind.EVIDENCE: (AuthPermission.EVIDENCE_READ, AuthPermission.EVIDENCE_WRITE),
        ResourceKind.REPORT: (AuthPermission.REPORT_READ, AuthPermission.REPORT_WRITE),
        ResourceKind.ARTIFACT: (AuthPermission.ARTIFACT_DOWNLOAD,),
    }[kind]


def _read_permission_for(kind: ResourceKind) -> AuthPermission:
    return {
        ResourceKind.RUN: AuthPermission.RUN_READ,
        ResourceKind.DEFINITION: AuthPermission.DEFINITION_READ,
        ResourceKind.EVIDENCE: AuthPermission.EVIDENCE_READ,
        ResourceKind.REPORT: AuthPermission.REPORT_READ,
        ResourceKind.ARTIFACT: AuthPermission.ARTIFACT_DOWNLOAD,
    }[kind]


def _from_rbac_issue(issue: AuthorizationIssueCode | None) -> ResourceAuthorizationIssueCode:
    if issue is AuthorizationIssueCode.TENANT_SCOPE_MISMATCH:
        return ResourceAuthorizationIssueCode.TENANT_SCOPE_MISMATCH
    if issue is AuthorizationIssueCode.TEAM_SCOPE_MISMATCH:
        return ResourceAuthorizationIssueCode.TEAM_SCOPE_MISMATCH
    return ResourceAuthorizationIssueCode.PERMISSION_NOT_GRANTED


def _has_object_admin_role(subject: AuthSubject) -> bool:
    return AuthRole.ADMIN in subject.roles or AuthRole.LOCAL_OWNER in subject.roles


def _signed_url_payload(
    *,
    artifact: ResourceDescriptor,
    subject_id: str,
    expires_at: datetime,
    nonce: str,
) -> Mapping[str, object]:
    return {
        "artifact_id": artifact.resource_id,
        "artifact_sha256": artifact.artifact_sha256,
        "contract_version": RESOURCE_AUTHORIZATION_CONTRACT_VERSION,
        "expires_at": expires_at.isoformat(),
        "nonce": nonce,
        "scope_hash": artifact.scope_hash,
        "subject_id": subject_id,
        "tenant_id": artifact.tenant_id,
    }


def _hmac_signature(signing_key: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(signing_key, _canonical_json_bytes(payload), hashlib.sha256).hexdigest()


def _default_nonce(grant: ArtifactDownloadGrant, expires_at: datetime) -> str:
    return hashlib.sha256(
        "\0".join(
            [
                grant.decision.subject_id,
                grant.artifact.resource_id,
                grant.artifact.scope_hash,
                expires_at.isoformat(),
            ]
        ).encode("utf-8")
    ).hexdigest()[:24]


def _hash_record(record: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(record)).hexdigest()


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json_bytes(record: Mapping[str, object]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _drop_none(record: Mapping[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in record.items() if value is not None}


def _string_tuple(name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ResourceAuthorizationError(f"{name} values must be a sequence")
    return tuple(dict.fromkeys(_safe_id(name, value) for value in values))


def _safe_id(name: str, value: object) -> str:
    text = _required_string(name, value)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:@=-")
    if len(text) > 160 or text[0] not in allowed or any(char not in allowed for char in text):
        raise ResourceAuthorizationError(f"{name} contains unsupported characters")
    return text


def _optional_safe_id(name: str, value: object | None) -> str | None:
    if value is None:
        return None
    return _safe_id(name, value)


def _required_string(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ResourceAuthorizationError(f"{name} is required")
    return value.strip()


def _optional_sha256(name: str, value: object | None) -> str | None:
    if value is None:
        return None
    text = _required_string(name, value)
    if not (len(text) == 71 and text.startswith("sha256:") and all(char in "0123456789abcdef" for char in text.removeprefix("sha256:"))):
        raise ResourceAuthorizationError(f"{name} must match sha256:<64 lowercase hex chars>")
    return text


def _require_aware_datetime(name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ResourceAuthorizationError(f"{name} must be timezone-aware")


__all__ = [
    "RESOURCE_AUTHORIZATION_CONTRACT_VERSION",
    "RESOURCE_AUTHORIZATION_SCHEMA_NAME",
    "RESOURCE_AUTHORIZATION_SCHEMA_VERSION",
    "ArtifactDownloadGrant",
    "ResourceAuthorizationAuditRecord",
    "ResourceAuthorizationDecision",
    "ResourceAuthorizationError",
    "ResourceAuthorizationIssueCode",
    "ResourceAuthorizationPolicy",
    "ResourceAuthorizationStatus",
    "ResourceDescriptor",
    "ResourceKind",
    "ResourceVisibility",
    "SignedArtifactUrl",
    "SignedArtifactUrlIssuer",
    "WorkerResourceGrant",
]
