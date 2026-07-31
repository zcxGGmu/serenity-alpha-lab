from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigProfileError(ValueError):
    """Raised when runtime profile boundaries are violated."""


class RuntimeProfile(str, Enum):
    DESKTOP = "desktop"
    STANDALONE = "standalone"
    CI = "ci"


class SecretStorageBackend(str, Enum):
    ENVIRONMENT = "environment"
    OS_KEYCHAIN = "os_keychain"
    SECRET_MANAGER = "secret_manager"


class ConfigAuditAction(str, Enum):
    CONFIG_DIAGNOSTICS_VIEWED = "config_diagnostics_viewed"
    CONFIG_UPDATE_PREVIEWED = "config_update_previewed"
    SECRET_REFERENCE_UPDATED = "secret_reference_updated"
    SECRET_ROTATION_PLANNED = "secret_rotation_planned"


class ConfigAuditStatus(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    PREVIEW = "preview"


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    profile: RuntimeProfile
    network_allowed: bool
    model_calls_allowed: bool
    provider_calls_allowed: bool
    env_file_mutation_allowed: bool


@dataclass(frozen=True, slots=True)
class ConfigValueSource:
    field_name: str
    source: str
    sensitive: bool = False


@dataclass(frozen=True, slots=True)
class SecretReference:
    field_name: str
    backend: SecretStorageBackend | str
    reference_uri: str
    version: str | None = None
    last_four: str | None = None
    configured: bool = True

    def __post_init__(self) -> None:
        backend = SecretStorageBackend(self.backend)
        object.__setattr__(self, "backend", backend)
        object.__setattr__(self, "field_name", _normalize_field_name(self.field_name, sensitive=True))
        object.__setattr__(self, "reference_uri", _secret_reference_uri(backend, self.reference_uri))
        object.__setattr__(self, "version", _optional_string("version", self.version))
        object.__setattr__(self, "last_four", _optional_last_four(self.last_four))
        if type(self.configured) is not bool:
            raise ConfigProfileError("configured must be boolean")

    @property
    def reference_hash(self) -> str:
        return _hash_record(
            {
                "backend": self.backend.value,
                "field_name": self.field_name,
                "reference_uri": self.reference_uri,
                "version": self.version,
            }
        )

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "field_name": self.field_name,
                "backend": self.backend.value,
                "configured": self.configured,
                "last_four": self.last_four,
                "version": self.version,
                "reference_hash": self.reference_hash,
            }
        )

    def to_storage_record(self) -> dict[str, Any]:
        record = self.to_record()
        record["reference_uri"] = self.reference_uri
        return record


@dataclass(frozen=True, slots=True)
class SecretRotationPlan:
    field_name: str
    old_reference: SecretReference
    new_reference: SecretReference
    requested_by: str
    tenant_id: str
    profile: RuntimeProfile | str
    requested_at: datetime
    effective_after: datetime | None = None
    dry_run: bool = False

    @classmethod
    def create(
        cls,
        *,
        field_name: str,
        old_reference: SecretReference,
        new_reference: SecretReference,
        requested_by: str,
        tenant_id: str,
        profile: RuntimeProfile | str,
        requested_at: datetime,
        effective_after: datetime | None = None,
        dry_run: bool = False,
    ) -> SecretRotationPlan:
        return cls(
            field_name=field_name,
            old_reference=old_reference,
            new_reference=new_reference,
            requested_by=requested_by,
            tenant_id=tenant_id,
            profile=profile,
            requested_at=requested_at,
            effective_after=effective_after,
            dry_run=dry_run,
        )

    def __post_init__(self) -> None:
        field_name = _normalize_field_name(self.field_name, sensitive=True)
        if type(self.old_reference) is not SecretReference or type(self.new_reference) is not SecretReference:
            raise ConfigProfileError("rotation references must be SecretReference values")
        if self.old_reference.field_name != field_name or self.new_reference.field_name != field_name:
            raise ConfigProfileError("rotation references must match field_name")
        if self.old_reference.reference_hash == self.new_reference.reference_hash:
            raise ConfigProfileError("new_reference must differ from old_reference")
        object.__setattr__(self, "field_name", field_name)
        object.__setattr__(self, "requested_by", _safe_id("requested_by", self.requested_by))
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "profile", RuntimeProfile(self.profile))
        _require_aware_datetime("requested_at", self.requested_at)
        if self.effective_after is not None:
            _require_aware_datetime("effective_after", self.effective_after)
            if self.effective_after <= self.requested_at:
                raise ConfigProfileError("effective_after must be after requested_at")
        if type(self.dry_run) is not bool:
            raise ConfigProfileError("dry_run must be boolean")

    @property
    def rotation_hash(self) -> str:
        return _hash_record(self._record(include_hash=False))

    @property
    def rotation_id(self) -> str:
        return f"scr_{self.rotation_hash.removeprefix('sha256:')[:32]}"

    def to_record(self) -> dict[str, Any]:
        return self._record(include_hash=True)

    def _record(self, *, include_hash: bool) -> dict[str, Any]:
        return _drop_none(
            {
                "rotation_id": self.rotation_id if include_hash else None,
                "rotation_hash": self.rotation_hash if include_hash else None,
                "field_name": self.field_name,
                "old_reference": self.old_reference.to_record(),
                "new_reference": self.new_reference.to_record(),
                "requested_by": self.requested_by,
                "tenant_id": self.tenant_id,
                "profile": self.profile.value,
                "requested_at": self.requested_at.isoformat(),
                "effective_after": self.effective_after.isoformat() if self.effective_after is not None else None,
                "dry_run": self.dry_run,
            }
        )


@dataclass(frozen=True, slots=True)
class ConfigAuditRecord:
    action: ConfigAuditAction | str
    status: ConfigAuditStatus | str
    actor_subject_id: str
    tenant_id: str
    profile: RuntimeProfile | str
    field_name: str
    created_at: datetime
    before: Any = None
    after: Any = None
    metadata: Mapping[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        action: ConfigAuditAction | str,
        status: ConfigAuditStatus | str,
        actor_subject_id: str,
        tenant_id: str,
        profile: RuntimeProfile | str,
        field_name: str,
        created_at: datetime,
        before: Any = None,
        after: Any = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ConfigAuditRecord:
        return cls(
            action=action,
            status=status,
            actor_subject_id=actor_subject_id,
            tenant_id=tenant_id,
            profile=profile,
            field_name=field_name,
            created_at=created_at,
            before=before,
            after=after,
            metadata=metadata,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", ConfigAuditAction(self.action))
        object.__setattr__(self, "status", ConfigAuditStatus(self.status))
        object.__setattr__(self, "actor_subject_id", _safe_id("actor_subject_id", self.actor_subject_id))
        object.__setattr__(self, "tenant_id", _safe_id("tenant_id", self.tenant_id))
        object.__setattr__(self, "profile", RuntimeProfile(self.profile))
        object.__setattr__(self, "field_name", _normalize_field_name(self.field_name, sensitive=False))
        _require_aware_datetime("created_at", self.created_at)
        if self.metadata is not None and not isinstance(self.metadata, Mapping):
            raise ConfigProfileError("metadata must be a mapping")

    @property
    def audit_hash(self) -> str:
        return _hash_record(self._record(include_hash=False))

    @property
    def audit_id(self) -> str:
        return f"cad_{self.audit_hash.removeprefix('sha256:')[:32]}"

    def to_record(self) -> dict[str, Any]:
        return self._record(include_hash=True)

    def _record(self, *, include_hash: bool) -> dict[str, Any]:
        return _drop_none(
            {
                "audit_id": self.audit_id if include_hash else None,
                "audit_hash": self.audit_hash if include_hash else None,
                "action": self.action.value,
                "status": self.status.value,
                "actor_subject_id": self.actor_subject_id,
                "tenant_id": self.tenant_id,
                "profile": self.profile.value,
                "field_name": self.field_name,
                "created_at": self.created_at.isoformat(),
                "before": _audit_safe_value("before", self.before),
                "after": _audit_safe_value("after", self.after),
                "metadata": _audit_safe_value("metadata", self.metadata or {}),
            }
        )


@dataclass(frozen=True, slots=True)
class RuntimeConfigUpdatePreview:
    settings: RuntimeSettings
    diagnostics: dict[str, dict[str, Any]]
    env_file_mutation_allowed: bool
    would_rewrite_env_file: bool
    blocked_reason: str | None = None


class RuntimeSettings(BaseSettings):
    """Pydantic settings model for Serenity runtime profile resolution."""

    model_config = SettingsConfigDict(extra="ignore", validate_assignment=True)

    profile: RuntimeProfile = RuntimeProfile.DESKTOP
    database_url: str | None = None
    allow_network: bool | None = None
    allow_model_calls: bool | None = None
    allow_provider_calls: bool | None = None
    config_version: str | None = None
    openai_api_key: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    tushare_token: SecretStr | None = None
    tavily_api_key: SecretStr | None = None
    serpapi_api_key: SecretStr | None = None
    sources: tuple[ConfigValueSource, ...] = Field(default_factory=tuple, exclude=True)
    warnings: tuple[str, ...] = Field(default_factory=tuple, exclude=True)


_DEFAULT_POLICIES = {
    RuntimeProfile.DESKTOP: ProfilePolicy(
        profile=RuntimeProfile.DESKTOP,
        network_allowed=True,
        model_calls_allowed=True,
        provider_calls_allowed=True,
        env_file_mutation_allowed=True,
    ),
    RuntimeProfile.STANDALONE: ProfilePolicy(
        profile=RuntimeProfile.STANDALONE,
        network_allowed=True,
        model_calls_allowed=True,
        provider_calls_allowed=True,
        env_file_mutation_allowed=False,
    ),
    RuntimeProfile.CI: ProfilePolicy(
        profile=RuntimeProfile.CI,
        network_allowed=False,
        model_calls_allowed=False,
        provider_calls_allowed=False,
        env_file_mutation_allowed=False,
    ),
}

_FIELD_ENV_NAMES: dict[str, tuple[str, ...]] = {
    "profile": ("SERENITY_PROFILE", "RUNTIME_PROFILE"),
    "database_url": ("SERENITY_DATABASE_URL", "DATABASE_URL"),
    "allow_network": ("SERENITY_ALLOW_NETWORK",),
    "allow_model_calls": ("SERENITY_ALLOW_MODEL_CALLS",),
    "allow_provider_calls": ("SERENITY_ALLOW_PROVIDER_CALLS",),
    "config_version": ("SERENITY_CONFIG_VERSION",),
    "openai_api_key": ("OPENAI_API_KEY", "SERENITY_OPENAI_API_KEY"),
    "deepseek_api_key": ("DEEPSEEK_API_KEY", "SERENITY_DEEPSEEK_API_KEY"),
    "tushare_token": ("TUSHARE_TOKEN", "SERENITY_TUSHARE_TOKEN"),
    "tavily_api_key": ("TAVILY_API_KEY", "SERENITY_TAVILY_API_KEY"),
    "serpapi_api_key": ("SERPAPI_API_KEY", "SERENITY_SERPAPI_API_KEY"),
}

_SENSITIVE_FIELDS = {
    "openai_api_key",
    "deepseek_api_key",
    "tushare_token",
    "tavily_api_key",
    "serpapi_api_key",
}

_CI_SECRET_STUB_PREFIXES = (
    "ci-",
    "dummy",
    "fake",
    "local-",
    "stub",
    "test",
)


def load_runtime_settings(
    env: Mapping[str, str] | None = None,
    *,
    explicit_profile: RuntimeProfile | str | None = None,
) -> RuntimeSettings:
    """Resolve settings from a mapping and enforce runtime profile boundaries."""

    environ = os.environ if env is None else env
    data, sources, warnings = _settings_data_from_env(environ)
    if explicit_profile is not None:
        data["profile"] = explicit_profile
        sources = _without_field_source(sources, "profile") + (
            ConfigValueSource("profile", "explicit:profile"),
        )

    settings = RuntimeSettings(**data, sources=sources, warnings=warnings)
    _enforce_profile_boundaries(settings)
    return settings


def profile_policy(settings: RuntimeSettings) -> ProfilePolicy:
    default = _DEFAULT_POLICIES[settings.profile]
    return ProfilePolicy(
        profile=settings.profile,
        network_allowed=_override_bool(settings.allow_network, default.network_allowed),
        model_calls_allowed=_override_bool(settings.allow_model_calls, default.model_calls_allowed),
        provider_calls_allowed=_override_bool(settings.allow_provider_calls, default.provider_calls_allowed),
        env_file_mutation_allowed=default.env_file_mutation_allowed,
    )


def redacted_config_diagnostics(settings: RuntimeSettings) -> dict[str, dict[str, Any]]:
    source_by_field = {source.field_name: source.source for source in settings.sources}
    diagnostics: dict[str, dict[str, Any]] = {}
    for field_name in _FIELD_ENV_NAMES:
        value = getattr(settings, field_name)
        diagnostics[field_name] = {
            "value": _redacted_value(field_name, value),
            "source": source_by_field.get(field_name, "default"),
            "sensitive": field_name in _SENSITIVE_FIELDS,
        }
    if settings.warnings:
        diagnostics["_warnings"] = {
            "value": list(settings.warnings),
            "source": "resolver",
            "sensitive": False,
        }
    return diagnostics


def config_api_diagnostics(
    settings: RuntimeSettings,
    *,
    secret_references: tuple[SecretReference, ...] = (),
) -> dict[str, dict[str, Any]]:
    """Return API-safe config diagnostics without plaintext secret values."""

    source_by_field = {source.field_name: source.source for source in settings.sources}
    ref_by_field = _secret_references_by_field(secret_references)
    diagnostics: dict[str, dict[str, Any]] = {}
    for field_name in _FIELD_ENV_NAMES:
        value = getattr(settings, field_name)
        if field_name not in _SENSITIVE_FIELDS:
            diagnostics[field_name] = {
                "value": _redacted_value(field_name, value),
                "source": source_by_field.get(field_name, "default"),
                "sensitive": False,
            }
            continue

        reference = ref_by_field.get(field_name)
        if reference is not None:
            diagnostics[field_name] = {
                "configured": reference.configured,
                "backend": reference.backend.value,
                "last_four": reference.last_four,
                "source": f"secret_reference:{reference.backend.value}",
                "sensitive": True,
            }
            continue

        secret_value = value.get_secret_value() if value is not None else ""
        diagnostics[field_name] = {
            "configured": bool(secret_value),
            "backend": SecretStorageBackend.ENVIRONMENT.value if secret_value else None,
            "last_four": _last_four(secret_value) if secret_value else None,
            "source": source_by_field.get(field_name, "default"),
            "sensitive": True,
        }
    if settings.warnings:
        diagnostics["_warnings"] = {
            "value": list(settings.warnings),
            "source": "resolver",
            "sensitive": False,
        }
    return diagnostics


def preview_runtime_config_update(
    settings: RuntimeSettings,
    updates: Mapping[str, Any],
    *,
    target_env_file: str | Path | None = None,
) -> RuntimeConfigUpdatePreview:
    """Validate updates and describe whether an env-file write would be allowed.

    This function is intentionally side-effect free: it never writes the target
    env file. Desktop callers may use the preview to drive an explicit save
    workflow later; standalone/service callers get an immutable deployment
    boundary by default.
    """

    existing = settings.model_dump(exclude={"sources", "warnings"}, mode="python")
    existing.update(dict(updates))
    updated_settings = RuntimeSettings(
        **existing,
        sources=_merge_update_sources(settings.sources, updates),
        warnings=settings.warnings,
    )
    _enforce_profile_boundaries(updated_settings)

    policy = profile_policy(updated_settings)
    has_target = target_env_file is not None
    would_rewrite = has_target and policy.env_file_mutation_allowed
    blocked_reason = None
    if has_target and not policy.env_file_mutation_allowed:
        blocked_reason = f"{updated_settings.profile.value} profile does not rewrite deployment .env"

    return RuntimeConfigUpdatePreview(
        settings=updated_settings,
        diagnostics=redacted_config_diagnostics(updated_settings),
        env_file_mutation_allowed=policy.env_file_mutation_allowed,
        would_rewrite_env_file=would_rewrite,
        blocked_reason=blocked_reason,
    )


def _settings_data_from_env(env: Mapping[str, str]) -> tuple[dict[str, str], tuple[ConfigValueSource, ...], tuple[str, ...]]:
    data: dict[str, str] = {}
    sources: list[ConfigValueSource] = []
    recognized = {name for names in _FIELD_ENV_NAMES.values() for name in names}

    for field_name, names in _FIELD_ENV_NAMES.items():
        for env_name in names:
            raw_value = env.get(env_name)
            if raw_value is None or raw_value == "":
                continue
            data[field_name] = raw_value
            sources.append(
                ConfigValueSource(
                    field_name=field_name,
                    source=f"env:{env_name}",
                    sensitive=field_name in _SENSITIVE_FIELDS,
                )
            )
            break

    warnings = tuple(
        f"unknown SERENITY config field ignored: {key}"
        for key in sorted(env)
        if key.startswith("SERENITY_") and key not in recognized
    )
    return data, tuple(sources), warnings


def _enforce_profile_boundaries(settings: RuntimeSettings) -> None:
    policy = profile_policy(settings)
    if settings.profile is not RuntimeProfile.CI:
        return

    if policy.network_allowed:
        raise ConfigProfileError("CI profile forbids real network calls")
    if policy.model_calls_allowed:
        raise ConfigProfileError("CI profile forbids real model calls")
    if policy.provider_calls_allowed:
        raise ConfigProfileError("CI profile forbids real provider calls")

    for field_name in _SENSITIVE_FIELDS:
        value = getattr(settings, field_name)
        if value is not None and _looks_like_real_secret(value.get_secret_value()):
            raise ConfigProfileError(f"CI profile rejects real model/provider key: {field_name}")


def _override_bool(value: bool | None, default: bool) -> bool:
    return default if value is None else value


def _redacted_value(field_name: str, value: Any) -> Any:
    if isinstance(value, RuntimeProfile):
        return value.value
    if field_name in _SENSITIVE_FIELDS:
        if value is None or value.get_secret_value() == "":
            return None
        return "[REDACTED]"
    return value


def _looks_like_real_secret(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"", "none", "null", "changeme"}:
        return False
    return not normalized.startswith(_CI_SECRET_STUB_PREFIXES)


def _looks_like_plaintext_secret_value(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith(
        (
            "sk-",
            "provider-token",
            "xoxb-",
            "xoxp-",
            "ghp_",
            "gho_",
            "glpat-",
        )
    )


def _secret_references_by_field(secret_references: tuple[SecretReference, ...]) -> dict[str, SecretReference]:
    by_field: dict[str, SecretReference] = {}
    for reference in secret_references:
        if type(reference) is not SecretReference:
            raise ConfigProfileError("secret_references must contain SecretReference values")
        by_field[reference.field_name] = reference
    return by_field


def _secret_reference_uri(backend: SecretStorageBackend, value: str) -> str:
    text = _required_string("secret reference URI", value)
    if _looks_like_real_secret(text) and "://" not in text:
        raise ConfigProfileError("secret reference URI must be a backend reference, not plaintext secret material")
    parsed = urlparse(text)
    expected_scheme = {
        SecretStorageBackend.ENVIRONMENT: "env",
        SecretStorageBackend.OS_KEYCHAIN: "keychain",
        SecretStorageBackend.SECRET_MANAGER: "secretmanager",
    }[backend]
    if parsed.scheme != expected_scheme or not parsed.netloc:
        raise ConfigProfileError(f"secret reference URI must use {expected_scheme}:// for {backend.value}")
    if parsed.query or parsed.fragment:
        raise ConfigProfileError("secret reference URI must not include query or fragment")
    if any(marker in text.lower() for marker in ("password=", "token=", "secret=", "api_key=")):
        raise ConfigProfileError("secret reference URI must not contain inline secret material")
    return text


def _normalize_field_name(field_name: str, *, sensitive: bool) -> str:
    normalized = _required_string("field_name", field_name)
    known_fields = set(_FIELD_ENV_NAMES)
    if normalized not in known_fields:
        raise ConfigProfileError(f"unknown config field: {normalized}")
    if sensitive and normalized not in _SENSITIVE_FIELDS:
        raise ConfigProfileError(f"config field is not sensitive: {normalized}")
    return normalized


def _safe_id(name: str, value: str) -> str:
    text = _required_string(name, value)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:@=-")
    if len(text) > 160 or text[0] not in allowed or any(char not in allowed for char in text):
        raise ConfigProfileError(f"{name} contains unsupported characters")
    return text


def _required_string(name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise ConfigProfileError(f"{name} is required")
    return value.strip()


def _optional_string(name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _required_string(name, value)


def _optional_last_four(value: str | None) -> str | None:
    if value is None:
        return None
    text = _required_string("last_four", value)
    if len(text) != 4:
        raise ConfigProfileError("last_four must contain exactly four characters")
    return text


def _last_four(value: str) -> str:
    return value[-4:] if len(value) >= 4 else value


def _require_aware_datetime(name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ConfigProfileError(f"{name} must be timezone-aware")


def _hash_record(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(record)).hexdigest()


def _canonical_json_bytes(record: Mapping[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


def _audit_safe_value(name: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, SecretReference):
        return value.to_record()
    if isinstance(value, RuntimeProfile):
        return value.value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, SecretStr):
        secret_value = value.get_secret_value()
        return {"configured": bool(secret_value), "last_four": _last_four(secret_value) if secret_value else None}
    if isinstance(value, Mapping):
        return {
            str(key): _audit_safe_value(str(key), item)
            for key, item in sorted(dict(value).items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_audit_safe_value(name, item) for item in value]
    if isinstance(value, str):
        lowered_name = name.lower()
        if any(marker in lowered_name for marker in ("secret", "token", "password", "api_key", "key")):
            return "[REDACTED]"
        if _looks_like_plaintext_secret_value(value):
            return "[REDACTED]"
        return value
    return value


def _without_field_source(
    sources: tuple[ConfigValueSource, ...],
    field_name: str,
) -> tuple[ConfigValueSource, ...]:
    return tuple(source for source in sources if source.field_name != field_name)


def _merge_update_sources(
    sources: tuple[ConfigValueSource, ...],
    updates: Mapping[str, Any],
) -> tuple[ConfigValueSource, ...]:
    merged = tuple(source for source in sources if source.field_name not in updates)
    merged += tuple(
        ConfigValueSource(field_name=str(field_name), source="preview:update", sensitive=str(field_name) in _SENSITIVE_FIELDS)
        for field_name in updates
    )
    return merged


__all__ = [
    "ConfigAuditAction",
    "ConfigAuditRecord",
    "ConfigAuditStatus",
    "ConfigProfileError",
    "ConfigValueSource",
    "ProfilePolicy",
    "RuntimeConfigUpdatePreview",
    "RuntimeProfile",
    "RuntimeSettings",
    "SecretReference",
    "SecretRotationPlan",
    "SecretStorageBackend",
    "config_api_diagnostics",
    "load_runtime_settings",
    "preview_runtime_config_update",
    "profile_policy",
    "redacted_config_diagnostics",
]
