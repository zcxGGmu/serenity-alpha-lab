from __future__ import annotations

from serenity_alpha_lab.desktop_runtime import build_desktop_runtime_plan


def test_desktop_runtime_plan_is_loopback_only_and_packaging_is_deferred() -> None:
    payload = build_desktop_runtime_plan().to_dict()

    assert payload["runtime_mode"] == "local_web_api"
    assert payload["loopback_host"] == "127.0.0.1"
    assert payload["backend_command"] == ["serenity-alpha-lab", "serve-app"]
    assert payload["web_asset_directory"] == "apps/serenity-web/dist"
    assert payload["packaging_status"] == "deferred_until_runtime_parity"
    assert payload["automatic_updates_enabled"] is False
    assert payload["credentials_bundled"] is False
    assert payload["external_network_enabled"] is False
    assert payload["public_bind_enabled"] is False
    assert payload["research_only"] is True


def test_desktop_runtime_plan_records_explicit_parity_requirements() -> None:
    payload = build_desktop_runtime_plan().to_dict()

    assert payload["parity_requirements"] == [
        "canonical_backend_artifact_or_api",
        "stable_desktop_api_routes",
        "offline_no_secret_release_gate",
        "updater_threat_model_and_rollback_plan",
    ]
