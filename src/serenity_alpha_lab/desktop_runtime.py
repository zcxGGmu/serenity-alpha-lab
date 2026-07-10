from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DesktopRuntimePlan:
    runtime_mode: str = "local_web_api"
    loopback_host: str = "127.0.0.1"
    backend_command: tuple[str, ...] = ("serenity-alpha-lab", "serve-app")
    web_asset_directory: str = "apps/serenity-web/dist"
    packaging_status: str = "deferred_until_runtime_parity"
    automatic_updates_enabled: bool = False
    credentials_bundled: bool = False
    external_network_enabled: bool = False
    public_bind_enabled: bool = False
    research_only: bool = True
    parity_requirements: tuple[str, ...] = (
        "canonical_backend_artifact_or_api",
        "stable_desktop_api_routes",
        "offline_no_secret_release_gate",
        "updater_threat_model_and_rollback_plan",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_mode": self.runtime_mode,
            "loopback_host": self.loopback_host,
            "backend_command": list(self.backend_command),
            "web_asset_directory": self.web_asset_directory,
            "packaging_status": self.packaging_status,
            "automatic_updates_enabled": self.automatic_updates_enabled,
            "credentials_bundled": self.credentials_bundled,
            "external_network_enabled": self.external_network_enabled,
            "public_bind_enabled": self.public_bind_enabled,
            "research_only": self.research_only,
            "parity_requirements": list(self.parity_requirements),
        }


def build_desktop_runtime_plan(
    *,
    packaging_status: str = "deferred_until_runtime_parity",
) -> DesktopRuntimePlan:
    return DesktopRuntimePlan(packaging_status=packaging_status)
