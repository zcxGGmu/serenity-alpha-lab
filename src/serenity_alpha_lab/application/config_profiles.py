from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigProfileError(ValueError):
    """Raised when runtime profile boundaries are violated."""


class RuntimeProfile(str, Enum):
    DESKTOP = "desktop"
    STANDALONE = "standalone"
    CI = "ci"


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
    "ConfigProfileError",
    "ConfigValueSource",
    "ProfilePolicy",
    "RuntimeConfigUpdatePreview",
    "RuntimeProfile",
    "RuntimeSettings",
    "load_runtime_settings",
    "preview_runtime_config_update",
    "profile_policy",
    "redacted_config_diagnostics",
]
