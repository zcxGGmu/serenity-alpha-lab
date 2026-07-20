from __future__ import annotations

import json

import pytest

from serenity_alpha_lab.application.config_profiles import (
    ConfigProfileError,
    RuntimeProfile,
    load_runtime_settings,
    preview_runtime_config_update,
    profile_policy,
    redacted_config_diagnostics,
)


def test_ci_profile_defaults_to_offline_stub_policy() -> None:
    settings = load_runtime_settings({"SERENITY_PROFILE": "ci"})

    assert settings.profile is RuntimeProfile.CI
    policy = profile_policy(settings)
    assert policy.network_allowed is False
    assert policy.model_calls_allowed is False
    assert policy.provider_calls_allowed is False
    assert policy.env_file_mutation_allowed is False


@pytest.mark.parametrize("secret_name", ["OPENAI_API_KEY", "TUSHARE_TOKEN"])
def test_ci_profile_rejects_real_model_or_provider_keys(secret_name: str) -> None:
    with pytest.raises(ConfigProfileError, match="real model/provider key"):
        load_runtime_settings(
            {
                "SERENITY_PROFILE": "ci",
                secret_name: "sk-real-secret-value",
            }
        )


@pytest.mark.parametrize(
    ("flag_name", "message"),
    [
        ("SERENITY_ALLOW_NETWORK", "network calls"),
        ("SERENITY_ALLOW_MODEL_CALLS", "model calls"),
        ("SERENITY_ALLOW_PROVIDER_CALLS", "provider calls"),
    ],
)
def test_ci_profile_rejects_runtime_call_overrides(flag_name: str, message: str) -> None:
    with pytest.raises(ConfigProfileError, match=message):
        load_runtime_settings(
            {
                "SERENITY_PROFILE": "ci",
                flag_name: "true",
            }
        )


def test_redacted_diagnostics_track_sources_without_leaking_secret_values() -> None:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "standalone",
            "SERENITY_DATABASE_URL": "postgresql://serenity.example/db",
            "OPENAI_API_KEY": "sk-live-should-not-leak",
            "TUSHARE_TOKEN": "provider-token-should-not-leak",
        }
    )

    diagnostics = redacted_config_diagnostics(settings)
    serialized = json.dumps(diagnostics, sort_keys=True)

    assert diagnostics["profile"]["value"] == "standalone"
    assert diagnostics["profile"]["source"] == "env:SERENITY_PROFILE"
    assert diagnostics["database_url"]["value"] == "postgresql://serenity.example/db"
    assert diagnostics["database_url"]["source"] == "env:SERENITY_DATABASE_URL"
    assert diagnostics["openai_api_key"]["value"] == "[REDACTED]"
    assert diagnostics["openai_api_key"]["source"] == "env:OPENAI_API_KEY"
    assert diagnostics["tushare_token"]["value"] == "[REDACTED]"
    assert "sk-live-should-not-leak" not in serialized
    assert "provider-token-should-not-leak" not in serialized


def test_service_profile_update_preview_never_rewrites_deployment_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=keep-this-value\n", encoding="utf-8")

    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "standalone",
            "SERENITY_DATABASE_URL": "postgresql://serenity.example/original",
        }
    )
    preview = preview_runtime_config_update(
        settings,
        {"database_url": "postgresql://serenity.example/preview"},
        target_env_file=env_file,
    )

    assert preview.settings.database_url == "postgresql://serenity.example/preview"
    assert preview.would_rewrite_env_file is False
    assert preview.env_file_mutation_allowed is False
    assert "standalone profile" in preview.blocked_reason
    assert env_file.read_text(encoding="utf-8") == "OPENAI_API_KEY=keep-this-value\n"


def test_desktop_profile_can_plan_env_file_update_without_writing_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SERENITY_PROFILE=desktop\n", encoding="utf-8")

    settings = load_runtime_settings({"SERENITY_PROFILE": "desktop"})
    preview = preview_runtime_config_update(
        settings,
        {"database_url": "sqlite:///local.db"},
        target_env_file=env_file,
    )

    assert preview.settings.database_url == "sqlite:///local.db"
    assert preview.env_file_mutation_allowed is True
    assert preview.would_rewrite_env_file is True
    assert env_file.read_text(encoding="utf-8") == "SERENITY_PROFILE=desktop\n"
