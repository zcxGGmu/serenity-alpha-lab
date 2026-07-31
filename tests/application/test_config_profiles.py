from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.application.config_profiles import (
    ConfigAuditAction,
    ConfigAuditRecord,
    ConfigAuditStatus,
    ConfigProfileError,
    RuntimeProfile,
    SecretReference,
    SecretRotationPlan,
    SecretStorageBackend,
    config_api_diagnostics,
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


def test_secret_references_use_keychain_or_secret_manager_without_plaintext_leakage() -> None:
    keychain_ref = SecretReference(
        field_name="openai_api_key",
        backend=SecretStorageBackend.OS_KEYCHAIN,
        reference_uri="keychain://serenity/openai-api-key",
        last_four="9abc",
    )
    secret_manager_ref = SecretReference(
        field_name="tushare_token",
        backend=SecretStorageBackend.SECRET_MANAGER,
        reference_uri="secretmanager://production/tushare-token",
        version="v2",
        last_four="1234",
    )

    keychain_record = keychain_ref.to_record()
    storage_record = secret_manager_ref.to_storage_record()
    serialized = json.dumps([keychain_record, storage_record], sort_keys=True)

    assert keychain_record["backend"] == "os_keychain"
    assert keychain_record["configured"] is True
    assert keychain_record["last_four"] == "9abc"
    assert keychain_record["reference_hash"].startswith("sha256:")
    assert storage_record["reference_uri"] == "secretmanager://production/tushare-token"
    assert storage_record["reference_hash"].startswith("sha256:")
    assert "sk-live-should-not-leak" not in serialized

    with pytest.raises(ConfigProfileError, match="secret reference URI"):
        SecretReference(
            field_name="openai_api_key",
            backend=SecretStorageBackend.SECRET_MANAGER,
            reference_uri="sk-live-should-not-be-a-reference",
        )
    with pytest.raises(ConfigProfileError, match="query or fragment"):
        SecretReference(
            field_name="openai_api_key",
            backend=SecretStorageBackend.SECRET_MANAGER,
            reference_uri="secretmanager://production/openai?token=leak",
        )


def test_config_api_diagnostics_show_only_presence_backend_and_last_four() -> None:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "standalone",
            "SERENITY_DATABASE_URL": "postgresql://serenity.example/db",
            "OPENAI_API_KEY": "sk-live-should-not-leak",
        }
    )
    diagnostics = config_api_diagnostics(
        settings,
        secret_references=(
            SecretReference(
                field_name="tushare_token",
                backend=SecretStorageBackend.SECRET_MANAGER,
                reference_uri="secretmanager://production/tushare-token",
                version="v7",
                last_four="7890",
            ),
        ),
    )
    serialized = json.dumps(diagnostics, sort_keys=True)

    assert diagnostics["database_url"]["value"] == "postgresql://serenity.example/db"
    assert diagnostics["openai_api_key"]["configured"] is True
    assert diagnostics["openai_api_key"]["backend"] == "environment"
    assert diagnostics["openai_api_key"]["last_four"] == "leak"
    assert "value" not in diagnostics["openai_api_key"]
    assert diagnostics["tushare_token"]["configured"] is True
    assert diagnostics["tushare_token"]["backend"] == "secret_manager"
    assert diagnostics["tushare_token"]["last_four"] == "7890"
    assert "sk-live-should-not-leak" not in serialized
    assert "[REDACTED]" not in serialized


def test_secret_rotation_plan_records_old_and_new_reference_hashes_only() -> None:
    requested_at = datetime(2026, 7, 31, 9, 30, tzinfo=UTC)
    old_ref = SecretReference(
        field_name="openai_api_key",
        backend=SecretStorageBackend.SECRET_MANAGER,
        reference_uri="secretmanager://production/openai-v1",
        version="v1",
        last_four="old1",
    )
    new_ref = SecretReference(
        field_name="openai_api_key",
        backend=SecretStorageBackend.SECRET_MANAGER,
        reference_uri="secretmanager://production/openai-v2",
        version="v2",
        last_four="new2",
    )

    plan = SecretRotationPlan.create(
        field_name="openai_api_key",
        old_reference=old_ref,
        new_reference=new_ref,
        requested_by="user-1",
        tenant_id="tenant-a",
        profile=RuntimeProfile.STANDALONE,
        requested_at=requested_at,
        effective_after=requested_at + timedelta(minutes=30),
        dry_run=True,
    )
    record = plan.to_record()
    serialized = json.dumps(record, sort_keys=True)

    assert plan.rotation_id.startswith("scr_")
    assert record["dry_run"] is True
    assert record["old_reference"]["last_four"] == "old1"
    assert record["new_reference"]["last_four"] == "new2"
    assert record["old_reference"]["reference_hash"] != record["new_reference"]["reference_hash"]
    assert "secretmanager://production/openai-v1" not in serialized
    assert "secretmanager://production/openai-v2" not in serialized

    with pytest.raises(ConfigProfileError, match="new_reference must differ"):
        SecretRotationPlan.create(
            field_name="openai_api_key",
            old_reference=old_ref,
            new_reference=old_ref,
            requested_by="user-1",
            tenant_id="tenant-a",
            profile=RuntimeProfile.STANDALONE,
            requested_at=requested_at,
            effective_after=requested_at + timedelta(minutes=30),
        )


def test_config_audit_record_is_deterministic_and_redacts_sensitive_payloads() -> None:
    created_at = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    old_ref = SecretReference(
        field_name="openai_api_key",
        backend=SecretStorageBackend.SECRET_MANAGER,
        reference_uri="secretmanager://production/openai-v1",
        version="v1",
        last_four="old1",
    )
    new_ref = SecretReference(
        field_name="openai_api_key",
        backend=SecretStorageBackend.SECRET_MANAGER,
        reference_uri="secretmanager://production/openai-v2",
        version="v2",
        last_four="new2",
    )

    audit = ConfigAuditRecord.create(
        action=ConfigAuditAction.SECRET_ROTATION_PLANNED,
        status=ConfigAuditStatus.ALLOWED,
        actor_subject_id="user-1",
        tenant_id="tenant-a",
        profile=RuntimeProfile.STANDALONE,
        field_name="openai_api_key",
        created_at=created_at,
        before=old_ref,
        after=new_ref,
        metadata={"ticket": "SEC-123", "raw_token": "sk-live-should-not-leak"},
    )
    repeat = ConfigAuditRecord.create(
        action=ConfigAuditAction.SECRET_ROTATION_PLANNED,
        status=ConfigAuditStatus.ALLOWED,
        actor_subject_id="user-1",
        tenant_id="tenant-a",
        profile=RuntimeProfile.STANDALONE,
        field_name="openai_api_key",
        created_at=created_at,
        before=old_ref,
        after=new_ref,
        metadata={"ticket": "SEC-123", "raw_token": "sk-live-should-not-leak"},
    )
    record = audit.to_record()
    serialized = json.dumps(record, sort_keys=True)

    assert record["audit_hash"] == repeat.to_record()["audit_hash"]
    assert record["audit_id"].startswith("cad_")
    assert record["metadata"]["ticket"] == "SEC-123"
    assert record["metadata"]["raw_token"] == "[REDACTED]"
    assert "sk-live-should-not-leak" not in serialized
    assert "secretmanager://production/openai-v2" not in serialized
