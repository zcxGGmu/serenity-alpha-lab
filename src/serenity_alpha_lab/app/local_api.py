from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from serenity_alpha_lab import __version__

from .config import AppRuntimeConfig


def create_api_handler(config: AppRuntimeConfig):
    config.validate_startup()

    class SerenityAppRequestHandler(BaseHTTPRequestHandler):
        server_version = "SerenityAlphaLabAPI/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json(_health_payload(config))
                return
            if parsed.path == "/version":
                self._send_json(_version_payload())
                return
            if parsed.path == "/run-state":
                self._send_json(_run_state_payload(config.runs_path))
                return
            self._send_json({"error": "not_found", "path": parsed.path}, status=404)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return SerenityAppRequestHandler


def serve_app(config: AppRuntimeConfig) -> None:
    config.validate_startup()
    handler = create_api_handler(config)
    with ThreadingHTTPServer((config.host, config.port), handler) as server:
        print(f"Serving Serenity Alpha Lab API at http://{config.host}:{config.port}")
        server.serve_forever()


def _health_payload(config: AppRuntimeConfig) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "serenity-alpha-lab-api",
        "research_only": config.research_only,
        "external_integrations": {
            "enabled": config.external_integrations_enabled,
        },
        "research_monitors": {
            "enabled": config.research_monitors_enabled,
            "notifications_enabled": config.research_monitor_notifications_enabled,
            "delivery_status": "enabled" if config.research_monitor_notifications_enabled else "disabled",
            "configured_channel_count": len(config.configured_notification_channels),
        },
        "market_data": {
            "enabled": config.market_data_enabled,
            "credentials_required": config.require_market_data_credentials,
            "env_var": config.market_data_env_var,
        },
    }


def _version_payload() -> dict[str, Any]:
    return {
        "service": "serenity-alpha-lab",
        "version": __version__,
        "api": "local",
    }


def _run_state_payload(path: Path) -> dict[str, Any]:
    runs = _load_run_records(path)
    latest_run = runs[0] if runs else None
    active_statuses = {"queued", "running"}
    status = "running" if any(str(run.get("status") or "") in active_statuses for run in runs) else "idle"
    return {
        "status": status,
        "run_count": len(runs),
        "latest_run": latest_run,
        "runs_path": str(path),
    }


def _load_run_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("runs", [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]
