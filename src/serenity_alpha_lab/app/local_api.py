from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from serenity_alpha_lab import __version__
from serenity_alpha_lab.desktop_runtime import build_desktop_runtime_plan

from .config import AppRuntimeConfig
from .stock_analysis_artifacts import (
    ArtifactRepositoryError,
    StockAnalysisArtifactRepository,
)

_ALLOWED_ARTIFACT_API_PATHS = {
    "/api/artifacts/stock-analysis/latest/manifest",
    "/api/artifacts/stock-analysis/latest/report",
}
_TRUSTED_URL_PATTERN = re.compile(
    r"""(?ix)
    \b
    (?:https?|serenity)://
    [^\s<>(){}"'`]+
    """
)
_HTML_CLOSING_TAG_PATTERN = re.compile(
    r"</[A-Za-z][A-Za-z0-9:-]*\s*>",
    re.IGNORECASE,
)
_ALLOWED_MARKET_SYMBOLS = {
    "/6A",
    "/6B",
    "/6C",
    "/6E",
    "/6J",
    "/6S",
    "/CL",
    "/ES",
    "/GC",
    "/HG",
    "/NG",
    "/NQ",
    "/RTY",
    "/SI",
    "/YM",
    "/ZB",
    "/ZF",
    "/ZN",
    "/ZT",
}
_MARKET_SYMBOL_BOUNDARY = frozenset(",.;:!?)]}")
_WINDOWS_DRIVE_PATH_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/](?=[^\r\n])"
)
_WINDOWS_UNC_PATH_PATTERN = re.compile(
    r"(?<!\\)\\\\[^\\\r\n]+\\[^\\\r\n]+"
)
_FILE_URI_PATTERN = re.compile(r"(?i)\bfile:(?=[\\/])")


def create_api_handler(config: AppRuntimeConfig):
    config.validate_startup()
    repository = StockAnalysisArtifactRepository(
        config.stock_analysis_artifact_dir,
    )

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
            try:
                if parsed.path == "/api/artifacts/stock-analysis/latest":
                    payload = repository.load_latest_summary()
                    _reject_local_path_leakage(payload)
                    self._send_json(payload)
                    return
                if parsed.path == "/api/artifacts/stock-analysis/latest/manifest":
                    payload = repository.load_latest_manifest()
                    _reject_local_path_leakage(payload)
                    self._send_json(payload)
                    return
                if parsed.path == "/api/artifacts/stock-analysis/latest/report":
                    report = repository.load_latest_report()
                    _reject_local_path_leakage(report)
                    self._send_text(
                        report,
                        content_type="text/markdown; charset=utf-8",
                    )
                    return
            except ArtifactRepositoryError as exc:
                self._send_json(exc.to_payload(), status=exc.status_code)
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

        def _send_text(
            self,
            text: str,
            *,
            content_type: str,
            status: int = 200,
        ) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return SerenityAppRequestHandler


def _reject_local_path_leakage(value: object) -> None:
    if isinstance(value, str):
        if _contains_local_path(value):
            raise ArtifactRepositoryError(
                422,
                "artifact_invalid",
                "local_path_detected",
            )
        return
    if isinstance(value, dict):
        for item in value.values():
            _reject_local_path_leakage(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _reject_local_path_leakage(item)


def _contains_local_path(value: str) -> bool:
    masked = value
    for allowed_path in _ALLOWED_ARTIFACT_API_PATHS:
        masked = masked.replace(allowed_path, "")
    masked = _mask_trusted_urls(masked)

    return any(
        pattern.search(masked) is not None
        for pattern in (
            _WINDOWS_DRIVE_PATH_PATTERN,
            _WINDOWS_UNC_PATH_PATTERN,
            _FILE_URI_PATTERN,
        )
    ) or _contains_posix_absolute_path(masked)


def _mask_trusted_urls(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        try:
            parsed = urlparse(candidate)
            hostname = parsed.hostname
        except ValueError:
            return "/invalid-url"
        if (
            parsed.scheme.lower() in {"http", "https", "serenity"}
            and parsed.netloc
            and hostname
        ):
            return ""
        return candidate.partition("://")[2]

    return _TRUSTED_URL_PATTERN.sub(replace, value)


def _contains_posix_absolute_path(value: str) -> bool:
    value = _HTML_CLOSING_TAG_PATTERN.sub("", value)
    for index, character in enumerate(value):
        if character != "/":
            continue
        if index > 0 and (
            value[index - 1].isalnum()
            or value[index - 1] in {"_", "/"}
        ):
            continue
        if index + 1 >= len(value):
            continue
        if value[index + 1].isspace() or value[index + 1] == "/":
            continue
        if _is_allowed_market_symbol(value, index):
            continue
        return True
    return False


def _is_allowed_market_symbol(value: str, index: int) -> bool:
    for market_symbol in _ALLOWED_MARKET_SYMBOLS:
        if not value.startswith(market_symbol, index):
            continue
        end = index + len(market_symbol)
        return (
            end == len(value)
            or value[end].isspace()
            or value[end] in _MARKET_SYMBOL_BOUNDARY
        )
    return False


def serve_app(config: AppRuntimeConfig) -> None:
    config.validate_startup()
    handler = create_api_handler(config)
    with ThreadingHTTPServer((config.host, config.port), handler) as server:
        print(f"Serving Serenity Alpha Lab API at http://{config.host}:{config.port}")
        server.serve_forever()


def _health_payload(config: AppRuntimeConfig) -> dict[str, Any]:
    desktop = build_desktop_runtime_plan(
        packaging_status=config.desktop_packaging_status,
    )
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
        "research_agents": {
            "enabled": config.research_agents_enabled,
            "execution": "explicit_context_only",
        },
        "research_bot": {
            "enabled": config.research_bot_enabled,
            "platform_delivery": "disabled",
        },
        "desktop": {
            "runtime_mode": desktop.runtime_mode,
            "packaging_status": desktop.packaging_status,
            "automatic_updates_enabled": desktop.automatic_updates_enabled,
            "credentials_bundled": desktop.credentials_bundled,
            "public_bind_enabled": desktop.public_bind_enabled,
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
