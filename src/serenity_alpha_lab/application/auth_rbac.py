from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


AUTH_RBAC_CONTRACT_VERSION = "security.auth_rbac@1.0.0"
AUTH_RBAC_SCHEMA_NAME = "security.auth_rbac_policy"
AUTH_RBAC_SCHEMA_VERSION = "1.0.0"


class AuthRbacError(ValueError):
    """Raised when the authentication/RBAC contract is structurally invalid."""


class AuthMode(StrEnum):
    DESKTOP = "desktop"
    STANDALONE = "standalone"
    TEAM = "team"


class AuthRole(StrEnum):
    LOCAL_OWNER = "local_owner"
    ADMIN = "admin"
    CONFIG_ADMIN = "config_admin"
    DATA_STEWARD = "data_steward"
    RUN_OPERATOR = "run_operator"
    RESEARCHER = "researcher"
    VIEWER = "viewer"
    AUDITOR = "auditor"
    SERVICE_WORKER = "service_worker"


class AuthPermission(StrEnum):
    DATASET_READ = "dataset:read"
    DATASET_WRITE = "dataset:write"
    DEFINITION_READ = "definition:read"
    DEFINITION_WRITE = "definition:write"
    RUN_READ = "run:read"
    RUN_CREATE = "run:create"
    RUN_CANCEL = "run:cancel"
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_WRITE = "evidence:write"
    REPORT_READ = "report:read"
    REPORT_WRITE = "report:write"
    ARTIFACT_DOWNLOAD = "artifact:download"
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    USER_ADMIN = "user:admin"
    AUDIT_READ = "audit:read"
    SERVICE_EXECUTE = "service:execute"
    NOTIFICATION_OUTBOX_READ = "notification_outbox:read"
    NOTIFICATION_OUTBOX_ADMIN = "notification_outbox:admin"


class AuthorizationStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class AuthorizationIssueCode(StrEnum):
    MODE_NOT_ALLOWED = "mode_not_allowed"
    TENANT_SCOPE_MISMATCH = "tenant_scope_mismatch"
    TEAM_SCOPE_MISMATCH = "team_scope_mismatch"
    PERMISSION_NOT_GRANTED = "permission_not_granted"


@dataclass(frozen=True, slots=True)
class ResourceScope:
    tenant_id: str
    resource_kind: str
    team_id: str | None = None
    owner_user_id: str | None = None
    resource_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "resource_kind", _required_string("resource_kind", self.resource_kind))
        object.__setattr__(self, "team_id", _optional_safe_id("team_id", self.team_id))
        object.__setattr__(self, "owner_user_id", _optional_safe_id("owner_user_id", self.owner_user_id))
        object.__setattr__(self, "resource_id", _optional_safe_id("resource_id", self.resource_id))

    def to_record(self) -> dict[str, str | None]:
        return {
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "owner_user_id": self.owner_user_id,
            "resource_kind": self.resource_kind,
            "resource_id": self.resource_id,
        }


@dataclass(frozen=True, slots=True)
class AuthSubject:
    subject_id: str
    tenant_id: str
    roles: Sequence[AuthRole | str]
    mode: AuthMode | str
    team_ids: Sequence[str] = ()
    identity_provider: str | None = None
    external_subject_id: str | None = None
    email: str | None = None
    display_name: str | None = None

    @classmethod
    def local_desktop_owner(cls) -> AuthSubject:
        return cls(
            subject_id="local-owner",
            tenant_id="local",
            roles=(AuthRole.LOCAL_OWNER,),
            mode=AuthMode.DESKTOP,
            display_name="Local Owner",
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _safe_id("subject_id", self.subject_id))
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "roles", _role_tuple(self.roles))
        object.__setattr__(self, "mode", AuthMode(self.mode))
        object.__setattr__(self, "team_ids", _string_tuple("team_id", self.team_ids))
        object.__setattr__(self, "identity_provider", _optional_safe_id("identity_provider", self.identity_provider))
        object.__setattr__(self, "external_subject_id", _optional_string(self.external_subject_id))
        object.__setattr__(self, "email", _optional_string(self.email))
        object.__setattr__(self, "display_name", _optional_string(self.display_name))

    def to_record(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "tenant_id": self.tenant_id,
            "team_ids": list(self.team_ids),
            "roles": [role.value for role in self.roles],
            "mode": self.mode.value,
            "identity_provider": self.identity_provider,
            "external_subject_id": self.external_subject_id,
            "email": self.email,
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    status: AuthorizationStatus | str
    subject_id: str
    permission: AuthPermission | str
    resource: ResourceScope
    matched_roles: Sequence[AuthRole | str] = ()
    issue_code: AuthorizationIssueCode | str | None = None
    detail: str | None = None
    contract_version: str = AUTH_RBAC_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", AuthorizationStatus(self.status))
        object.__setattr__(self, "subject_id", _safe_id("subject_id", self.subject_id))
        object.__setattr__(self, "permission", AuthPermission(self.permission))
        if type(self.resource) is not ResourceScope:
            raise AuthRbacError("resource must be a ResourceScope")
        object.__setattr__(self, "matched_roles", _role_tuple(self.matched_roles))
        object.__setattr__(
            self,
            "issue_code",
            AuthorizationIssueCode(self.issue_code) if self.issue_code is not None else None,
        )
        object.__setattr__(self, "detail", _optional_string(self.detail))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    @property
    def allowed(self) -> bool:
        return self.status is AuthorizationStatus.ALLOWED

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "status": self.status.value,
            "subject_id": self.subject_id,
            "permission": self.permission.value,
            "resource": self.resource.to_record(),
            "matched_roles": [role.value for role in self.matched_roles],
            "issue_code": self.issue_code.value if self.issue_code is not None else None,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class OidcProviderConfig:
    provider_id: str
    issuer: str
    client_id: str
    audience: str
    enabled: bool = False
    client_secret_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _safe_id("provider_id", self.provider_id))
        object.__setattr__(self, "issuer", _https_url("issuer", self.issuer))
        object.__setattr__(self, "client_id", _required_string("client_id", self.client_id))
        object.__setattr__(self, "audience", _required_string("audience", self.audience))
        if type(self.enabled) is not bool:
            raise AuthRbacError("enabled must be boolean")
        object.__setattr__(self, "client_secret_ref", _optional_string(self.client_secret_ref))

    def to_record(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "issuer": self.issuer,
            "client_id": self.client_id,
            "audience": self.audience,
            "enabled": self.enabled,
            "client_secret_configured": self.client_secret_ref is not None,
        }


@dataclass(frozen=True, slots=True)
class OidcClaimMapping:
    tenant_id: str
    subject_claim: str = "sub"
    roles_claim: str = "roles"
    teams_claim: str = "teams"
    email_claim: str | None = "email"
    display_name_claim: str | None = "name"
    role_aliases: Mapping[str, AuthRole | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "subject_claim", _required_string("subject_claim", self.subject_claim))
        object.__setattr__(self, "roles_claim", _required_string("roles_claim", self.roles_claim))
        object.__setattr__(self, "teams_claim", _required_string("teams_claim", self.teams_claim))
        object.__setattr__(self, "email_claim", _optional_string(self.email_claim))
        object.__setattr__(self, "display_name_claim", _optional_string(self.display_name_claim))
        object.__setattr__(
            self,
            "role_aliases",
            {str(alias): AuthRole(role) for alias, role in sorted(dict(self.role_aliases).items())},
        )

    def map_claims(self, claims: Mapping[str, Any], *, provider_id: str) -> AuthSubject:
        if not isinstance(claims, Mapping):
            raise AuthRbacError("claims must be a mapping")
        normalized_provider = _safe_id("provider_id", provider_id)
        external_subject_id = _required_string(self.subject_claim, claims.get(self.subject_claim))
        mapped_roles = []
        for alias in _claim_values(claims.get(self.roles_claim)):
            role = self.role_aliases.get(alias)
            if role is not None:
                mapped_roles.append(role)
        return AuthSubject(
            subject_id=f"oidc:{normalized_provider}:{external_subject_id}",
            tenant_id=self.tenant_id,
            team_ids=tuple(_claim_values(claims.get(self.teams_claim))),
            roles=tuple(dict.fromkeys(mapped_roles)),
            mode=AuthMode.TEAM,
            identity_provider=normalized_provider,
            external_subject_id=external_subject_id,
            email=_claim_scalar(claims.get(self.email_claim)) if self.email_claim is not None else None,
            display_name=_claim_scalar(claims.get(self.display_name_claim)) if self.display_name_claim is not None else None,
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "subject_claim": self.subject_claim,
            "roles_claim": self.roles_claim,
            "teams_claim": self.teams_claim,
            "email_claim": self.email_claim,
            "display_name_claim": self.display_name_claim,
            "role_aliases": {alias: role.value for alias, role in self.role_aliases.items()},
        }


@dataclass(frozen=True, slots=True)
class ApiAuthorizationRequirement:
    method: str
    path: str
    operation_id: str
    resource_kind: str
    required_permissions: Sequence[AuthPermission | str]
    contract_version: str = AUTH_RBAC_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _required_string("method", self.method).upper())
        object.__setattr__(self, "path", _required_string("path", self.path))
        object.__setattr__(self, "operation_id", _required_string("operation_id", self.operation_id))
        object.__setattr__(self, "resource_kind", _required_string("resource_kind", self.resource_kind))
        permissions = tuple(AuthPermission(permission) for permission in self.required_permissions)
        if not permissions:
            raise AuthRbacError("required_permissions cannot be empty")
        object.__setattr__(self, "required_permissions", permissions)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "method": self.method,
            "path": self.path,
            "operation_id": self.operation_id,
            "resource_kind": self.resource_kind,
            "required_permissions": [permission.value for permission in self.required_permissions],
        }


@dataclass(frozen=True, slots=True)
class RbacPolicy:
    mode: AuthMode | str
    role_permissions: Mapping[AuthRole | str, Sequence[AuthPermission | str]]
    oidc_required: bool = False
    contract_version: str = AUTH_RBAC_CONTRACT_VERSION
    schema_name: str = AUTH_RBAC_SCHEMA_NAME
    schema_version: str = AUTH_RBAC_SCHEMA_VERSION

    @classmethod
    def default(cls, mode: AuthMode | str) -> RbacPolicy:
        auth_mode = AuthMode(mode)
        if auth_mode is AuthMode.DESKTOP:
            return cls(
                mode=auth_mode,
                oidc_required=False,
                role_permissions={AuthRole.LOCAL_OWNER: tuple(AuthPermission)},
            )
        if auth_mode is AuthMode.STANDALONE:
            return cls(
                mode=auth_mode,
                oidc_required=False,
                role_permissions={
                    AuthRole.ADMIN: tuple(AuthPermission),
                    AuthRole.RESEARCHER: _researcher_permissions(),
                    AuthRole.VIEWER: _viewer_permissions(),
                    AuthRole.AUDITOR: _auditor_permissions(),
                    AuthRole.SERVICE_WORKER: _service_worker_permissions(),
                },
            )
        return cls(
            mode=auth_mode,
            oidc_required=True,
            role_permissions={
                AuthRole.ADMIN: tuple(AuthPermission),
                AuthRole.CONFIG_ADMIN: (
                    AuthPermission.CONFIG_READ,
                    AuthPermission.CONFIG_WRITE,
                    AuthPermission.AUDIT_READ,
                ),
                AuthRole.DATA_STEWARD: (
                    AuthPermission.DATASET_READ,
                    AuthPermission.DATASET_WRITE,
                    AuthPermission.DEFINITION_READ,
                    AuthPermission.EVIDENCE_READ,
                    AuthPermission.EVIDENCE_WRITE,
                ),
                AuthRole.RUN_OPERATOR: (
                    AuthPermission.DATASET_READ,
                    AuthPermission.DEFINITION_READ,
                    AuthPermission.RUN_READ,
                    AuthPermission.RUN_CREATE,
                    AuthPermission.RUN_CANCEL,
                    AuthPermission.EVIDENCE_READ,
                    AuthPermission.REPORT_READ,
                ),
                AuthRole.RESEARCHER: _researcher_permissions(),
                AuthRole.VIEWER: _viewer_permissions(),
                AuthRole.AUDITOR: _auditor_permissions(),
                AuthRole.SERVICE_WORKER: _service_worker_permissions(),
            },
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", AuthMode(self.mode))
        if type(self.oidc_required) is not bool:
            raise AuthRbacError("oidc_required must be boolean")
        normalized: dict[AuthRole, tuple[AuthPermission, ...]] = {}
        for role, permissions in self.role_permissions.items():
            normalized[AuthRole(role)] = tuple(AuthPermission(permission) for permission in permissions)
        object.__setattr__(self, "role_permissions", normalized)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def authorize(
        self,
        subject: AuthSubject,
        permission: AuthPermission | str,
        resource: ResourceScope,
    ) -> AuthorizationDecision:
        if type(subject) is not AuthSubject:
            raise AuthRbacError("subject must be an AuthSubject")
        if type(resource) is not ResourceScope:
            raise AuthRbacError("resource must be a ResourceScope")
        requested = AuthPermission(permission)
        if subject.mode is not self.mode:
            return _deny(subject, requested, resource, AuthorizationIssueCode.MODE_NOT_ALLOWED, "subject mode is not accepted by policy")
        if subject.tenant_id != resource.tenant_id:
            return _deny(subject, requested, resource, AuthorizationIssueCode.TENANT_SCOPE_MISMATCH, "subject tenant does not match resource tenant")
        if resource.team_id is not None and not _has_cross_team_role(subject) and resource.team_id not in subject.team_ids:
            return _deny(subject, requested, resource, AuthorizationIssueCode.TEAM_SCOPE_MISMATCH, "subject team does not match resource team")

        matched_roles = tuple(
            role
            for role in subject.roles
            if requested in self.role_permissions.get(role, ())
        )
        if not matched_roles:
            return _deny(subject, requested, resource, AuthorizationIssueCode.PERMISSION_NOT_GRANTED, "permission is not granted by subject roles")
        return AuthorizationDecision(
            status=AuthorizationStatus.ALLOWED,
            subject_id=subject.subject_id,
            permission=requested,
            resource=resource,
            matched_roles=matched_roles,
        )

    def to_record(self) -> dict[str, Any]:
        role_records = {
            role.value: [permission.value for permission in permissions]
            for role, permissions in sorted(self.role_permissions.items(), key=lambda item: item[0].value)
        }
        content = {
            "contract_version": self.contract_version,
            "schema": {"name": self.schema_name, "version": self.schema_version},
            "mode": self.mode.value,
            "oidc_required": self.oidc_required,
            "role_permissions": role_records,
        }
        content["policy_hash"] = _hash_record(content)
        return content


def default_api_authorization_catalog() -> tuple[ApiAuthorizationRequirement, ...]:
    routes = (
        _route("GET", "/api/v1/auth/status", "getAuthStatus", "auth", AuthPermission.CONFIG_READ),
        _route("POST", "/api/v1/auth/settings", "updateAuthSettings", "auth", AuthPermission.USER_ADMIN),
        _route("POST", "/api/v1/auth/change-password", "changePassword", "auth", AuthPermission.USER_ADMIN),
        _route("GET", "/api/v1/admin/users", "listUsers", "user", AuthPermission.USER_ADMIN),
        _route("POST", "/api/v1/admin/users", "createUser", "user", AuthPermission.USER_ADMIN),
        _route("GET", "/api/v1/config", "getRuntimeConfig", "config", AuthPermission.CONFIG_READ),
        _route("POST", "/api/v1/config", "updateRuntimeConfig", "config", AuthPermission.CONFIG_WRITE),
        _route("POST", "/api/v1/quant/factor-definitions", "createQuantFactorDefinition", "definition", AuthPermission.DEFINITION_WRITE),
        _route("POST", "/api/v1/quant/screen-definitions", "createQuantScreenDefinition", "definition", AuthPermission.DEFINITION_WRITE),
        _route("POST", "/api/v1/quant/screen-runs", "createQuantScreenRun", "screen_run", AuthPermission.RUN_CREATE),
        _route("GET", "/api/v1/quant/screen-runs/{run_id}", "getQuantScreenRun", "screen_run", AuthPermission.RUN_READ),
        _route("GET", "/api/v1/quant/screen-runs/{run_id}/results", "listQuantScreenRunResults", "screen_run", AuthPermission.RUN_READ),
        _route("GET", "/api/v1/quant/screen-runs/{run_id}/results/{instrument_id}", "getQuantScreenRunResult", "screen_run", AuthPermission.RUN_READ),
        _route("POST", "/api/v1/quant/backtest-runs", "createFormalBacktestRun", "backtest_run", AuthPermission.RUN_CREATE),
        _route("GET", "/api/v1/quant/backtest-runs/{run_id}", "getFormalBacktestRun", "backtest_run", AuthPermission.RUN_READ),
        _route("POST", "/api/v1/quant/backtest-runs/{run_id}/cancel", "cancelFormalBacktestRun", "backtest_run", AuthPermission.RUN_CANCEL),
        _route("GET", "/api/v1/quant/backtest-runs/{run_id}/metrics", "getFormalBacktestMetrics", "backtest_run", AuthPermission.RUN_READ),
        _route("GET", "/api/v1/quant/backtest-runs/{run_id}/audit", "getFormalBacktestAudit", "backtest_run", AuthPermission.AUDIT_READ),
        _route("GET", "/api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}", "downloadFormalBacktestArtifact", "artifact", AuthPermission.ARTIFACT_DOWNLOAD),
        _route("POST", "/api/v1/research/evidence", "createEvidence", "evidence", AuthPermission.EVIDENCE_WRITE),
        _route("GET", "/api/v1/research/evidence/{evidence_id}", "getEvidence", "evidence", AuthPermission.EVIDENCE_READ),
        _route("GET", "/api/v1/research/reports/{report_id}", "getResearchReport", "research_report", AuthPermission.REPORT_READ),
        _route("POST", "/api/v1/research/reports", "createResearchReport", "research_report", AuthPermission.REPORT_WRITE),
        _route("GET", "/api/v1/research/reports/{report_id}/notifications", "listResearchReportNotifications", "notification_outbox", AuthPermission.NOTIFICATION_OUTBOX_READ),
        _route("GET", "/api/v1/admin/audit", "listAuditEvents", "audit", AuthPermission.AUDIT_READ),
        _route("GET", "/api/v1/admin/notification-outbox", "listNotificationOutbox", "notification_outbox", AuthPermission.NOTIFICATION_OUTBOX_ADMIN),
    )
    return tuple(sorted(routes, key=lambda item: (item.path, item.method)))


def _route(
    method: str,
    path: str,
    operation_id: str,
    resource_kind: str,
    *permissions: AuthPermission,
) -> ApiAuthorizationRequirement:
    return ApiAuthorizationRequirement(
        method=method,
        path=path,
        operation_id=operation_id,
        resource_kind=resource_kind,
        required_permissions=permissions,
    )


def _researcher_permissions() -> tuple[AuthPermission, ...]:
    return (
        AuthPermission.DATASET_READ,
        AuthPermission.DEFINITION_READ,
        AuthPermission.DEFINITION_WRITE,
        AuthPermission.RUN_READ,
        AuthPermission.RUN_CREATE,
        AuthPermission.RUN_CANCEL,
        AuthPermission.EVIDENCE_READ,
        AuthPermission.EVIDENCE_WRITE,
        AuthPermission.REPORT_READ,
        AuthPermission.REPORT_WRITE,
        AuthPermission.ARTIFACT_DOWNLOAD,
        AuthPermission.NOTIFICATION_OUTBOX_READ,
    )


def _viewer_permissions() -> tuple[AuthPermission, ...]:
    return (
        AuthPermission.DATASET_READ,
        AuthPermission.DEFINITION_READ,
        AuthPermission.RUN_READ,
        AuthPermission.EVIDENCE_READ,
        AuthPermission.REPORT_READ,
        AuthPermission.NOTIFICATION_OUTBOX_READ,
    )


def _auditor_permissions() -> tuple[AuthPermission, ...]:
    return (
        AuthPermission.DATASET_READ,
        AuthPermission.DEFINITION_READ,
        AuthPermission.RUN_READ,
        AuthPermission.EVIDENCE_READ,
        AuthPermission.REPORT_READ,
        AuthPermission.AUDIT_READ,
        AuthPermission.NOTIFICATION_OUTBOX_READ,
    )


def _service_worker_permissions() -> tuple[AuthPermission, ...]:
    return (
        AuthPermission.SERVICE_EXECUTE,
        AuthPermission.RUN_READ,
    )


def _deny(
    subject: AuthSubject,
    permission: AuthPermission,
    resource: ResourceScope,
    issue_code: AuthorizationIssueCode,
    detail: str,
) -> AuthorizationDecision:
    return AuthorizationDecision(
        status=AuthorizationStatus.DENIED,
        subject_id=subject.subject_id,
        permission=permission,
        resource=resource,
        matched_roles=(),
        issue_code=issue_code,
        detail=detail,
    )


def _has_cross_team_role(subject: AuthSubject) -> bool:
    return AuthRole.ADMIN in subject.roles or AuthRole.LOCAL_OWNER in subject.roles


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _role_tuple(values: Sequence[AuthRole | str]) -> tuple[AuthRole, ...]:
    if isinstance(values, (str, bytes)):
        raise AuthRbacError("roles must be a sequence of AuthRole values")
    roles = tuple(AuthRole(value) for value in values)
    return tuple(dict.fromkeys(roles))


def _string_tuple(name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AuthRbacError(f"{name} values must be a sequence")
    return tuple(dict.fromkeys(_safe_id(name, value) for value in values))


def _claim_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(str(item) for item in value if str(item).strip())
    return (str(value),)


def _claim_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        first = next(iter(value), None)
        return _optional_string(first)
    return _optional_string(value)


def _https_url(name: str, value: Any) -> str:
    text = _required_string(name, value)
    if not text.startswith("https://"):
        raise AuthRbacError(f"{name} must be an https URL")
    return text


def _safe_id(name: str, value: Any) -> str:
    text = _required_string(name, value)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:@=-")
    if len(text) > 160 or text[0] not in allowed or any(char not in allowed for char in text):
        raise AuthRbacError(f"{name} contains unsupported characters")
    return text


def _optional_safe_id(name: str, value: Any) -> str | None:
    text = _optional_string(value)
    return _safe_id(name, text) if text is not None else None


def _required_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthRbacError(f"{name} is required")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AuthRbacError("optional string values must be non-empty strings when provided")
    return value.strip()


__all__ = [
    "AUTH_RBAC_CONTRACT_VERSION",
    "AUTH_RBAC_SCHEMA_NAME",
    "AUTH_RBAC_SCHEMA_VERSION",
    "ApiAuthorizationRequirement",
    "AuthMode",
    "AuthPermission",
    "AuthRbacError",
    "AuthRole",
    "AuthSubject",
    "AuthorizationDecision",
    "AuthorizationIssueCode",
    "AuthorizationStatus",
    "OidcClaimMapping",
    "OidcProviderConfig",
    "RbacPolicy",
    "ResourceScope",
    "default_api_authorization_catalog",
]
