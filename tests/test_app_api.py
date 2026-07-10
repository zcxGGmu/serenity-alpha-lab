import json
from pathlib import Path
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from serenity_alpha_lab import __version__
from serenity_alpha_lab.app import AppRuntimeConfig, create_api_handler
from serenity_alpha_lab.app.local_api import _health_payload, _load_run_records


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def _get_response(url: str) -> tuple[int, dict[str, str], bytes]:
    try:
        response = urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, dict(exc.headers.items()), exc.read()
    with response:
        return response.status, dict(response.headers.items()), response.read()


def _write_canonical_artifact(root: Path, *, mutate=None) -> None:
    manifest = {
        "schema_version": 1,
        "artifact_type": "stock_analysis_report",
        "symbol": "MSFT",
        "stock_name": "Microsoft Corporation",
        "query": "MSFT market data research",
        "generated_at": "2026-07-10T00:00:00+00:00",
        "research_only": True,
        "readiness": {
            "status": "ready",
            "reason": "readiness_ready",
            "flags": [],
        },
        "report_gate": {
            "status": "available",
            "reason": "readiness_ready",
            "research_only": True,
        },
        "source_coverage": {
            "status": "ready",
            "focus_ticker": "MSFT",
            "evidence_count": 4,
            "focus_evidence_count": 4,
            "primary_count": 3,
            "risk_count": 1,
            "methodology_share": 0.0,
            "placeholder_share": 0.0,
            "external_non_serenity_count": 0,
            "flags": [],
        },
        "skeptical_review": {
            "summary": "Risk coverage uses 1 risk or invalidation evidence item.",
            "counter_thesis": ["MSFT closed lower on 2026-07-08."],
        },
        "reports": {
            "stock_analysis": "reports/stock-analysis-report.md",
            "ui": "index.html",
        },
        "safety": {
            "passed": True,
            "boundary": "research only; not investment advice",
            "findings": [],
        },
        "key_claims": [
            {
                "claim_id": "claim:MSFT:readiness",
                "claim": "Readiness is ready.",
                "provenance_refs": [
                    {
                        "evidence_id": "serenity:market-data:MSFT:quote:2026-07-10",
                        "source_url": "serenity://market-data/MSFT/quote/2026-07-10",
                        "source_title": "MSFT quote",
                        "excerpt": "Normalized quote evidence.",
                    }
                ],
                "diagnostics": [],
            }
        ],
    }
    if mutate is not None:
        mutate(manifest)
    (root / "reports").mkdir(parents=True)
    (root / "analysis-report-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (root / "reports" / "stock-analysis-report.md").write_text(
        "# MSFT Research Report\n",
        encoding="utf-8",
    )


def _artifact_config(artifact_dir: Path, runs_path: Path) -> AppRuntimeConfig:
    return AppRuntimeConfig(
        runs_path=runs_path,
        stock_analysis_artifact_dir=artifact_dir,
    )


def _request_latest_artifact(
    artifact_dir: Path,
    runs_path: Path,
    *,
    suffix: str = "",
) -> tuple[int, dict[str, str], bytes]:
    config = _artifact_config(artifact_dir, runs_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return _get_response(
            f"http://127.0.0.1:{server.server_port}"
            f"/api/artifacts/stock-analysis/latest{suffix}"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_app_runtime_config_defaults_to_local_research_only_without_market_data_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("SERENITY_MARKET_DATA_API_KEY", raising=False)
    monkeypatch.delenv("DSA_MARKET_DATA_API_KEY", raising=False)

    config = AppRuntimeConfig(runs_path=tmp_path / "runs.json")

    assert config.host == "127.0.0.1"
    assert config.port == 8010
    assert config.require_market_data_credentials is False
    assert config.market_data_enabled is False
    assert config.external_integrations_enabled is False
    assert config.research_only is True
    assert config.stock_analysis_artifact_dir == Path("output/stock-analysis")


def test_health_payload_reports_research_monitors_default_off_without_secrets(monkeypatch):
    monkeypatch.delenv("SERENITY_NOTIFICATION_CHANNELS", raising=False)

    payload = _health_payload(AppRuntimeConfig())

    assert payload["research_only"] is True
    assert payload["research_monitors"]["enabled"] is False
    assert payload["research_monitors"]["notifications_enabled"] is False
    assert payload["research_monitors"]["delivery_status"] == "disabled"
    assert payload["research_monitors"]["configured_channel_count"] == 0
    rendered = str(payload).lower()
    assert "token" not in rendered
    assert "secret" not in rendered
    assert "password" not in rendered


def test_health_reports_agent_bot_and_desktop_capabilities_default_off():
    payload = _health_payload(AppRuntimeConfig())

    assert payload["research_agents"] == {
        "enabled": False,
        "execution": "explicit_context_only",
    }
    assert payload["research_bot"]["enabled"] is False
    assert payload["research_bot"]["platform_delivery"] == "disabled"
    assert payload["desktop"]["runtime_mode"] == "local_web_api"
    assert payload["desktop"]["packaging_status"] == "deferred_until_runtime_parity"
    assert payload["desktop"]["automatic_updates_enabled"] is False
    assert payload["desktop"]["credentials_bundled"] is False
    assert payload["desktop"]["public_bind_enabled"] is False
    rendered = str(payload).lower()
    assert "token" not in rendered
    assert "secret" not in rendered
    assert "password" not in rendered
    assert "/users/" not in rendered


def test_local_api_serves_health_version_and_run_state_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("SERENITY_MARKET_DATA_API_KEY", raising=False)
    monkeypatch.delenv("DSA_MARKET_DATA_API_KEY", raising=False)
    runs_path = tmp_path / "runs.json"
    runs_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "job_id": "job-1",
                        "status": "completed",
                        "query": "CPO laser bottleneck",
                        "href": "analyses/cpo/index.html",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config = AppRuntimeConfig(runs_path=runs_path, dashboard_path=tmp_path / "index.html")

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        health = _get_json(f"{base_url}/health")
        version = _get_json(f"{base_url}/version")
        run_state = _get_json(f"{base_url}/run-state")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health["status"] == "ok"
    assert health["service"] == "serenity-alpha-lab-api"
    assert health["research_only"] is True
    assert health["market_data"]["credentials_required"] is False
    assert health["market_data"]["enabled"] is False
    assert version["version"] == __version__
    assert version["api"] == "local"
    assert run_state["status"] == "idle"
    assert run_state["run_count"] == 1
    assert run_state["latest_run"]["job_id"] == "job-1"
    assert run_state["latest_run"]["status"] == "completed"


def test_local_api_run_state_marks_active_jobs_running(tmp_path):
    runs_path = tmp_path / "runs.json"
    runs_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "job_id": "job-2",
                        "status": "running",
                        "query": "HBM",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config = AppRuntimeConfig(runs_path=runs_path, dashboard_path=tmp_path / "index.html")

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        run_state = _get_json(f"{base_url}/run-state")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert run_state["status"] == "running"
    assert run_state["run_count"] == 1
    assert run_state["latest_run"]["job_id"] == "job-2"


def test_local_api_serves_validated_latest_stock_analysis_artifacts(tmp_path) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(artifact_dir)
    config = _artifact_config(artifact_dir, tmp_path / "runs.json")

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        summary_status, summary_headers, summary_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest"
        )
        manifest_status, manifest_headers, manifest_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest/manifest"
        )
        report_status, report_headers, report_body = _get_response(
            f"{base_url}/api/artifacts/stock-analysis/latest/report"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    summary = json.loads(summary_body)
    manifest = json.loads(manifest_body)
    assert summary_status == 200
    assert summary_headers["Cache-Control"] == "no-store"
    assert summary_headers["Content-Type"].startswith("application/json")
    assert summary["symbol"] == "MSFT"
    assert summary["research_only"] is True
    assert summary["reports"] == {
        "stock_analysis": "/api/artifacts/stock-analysis/latest/report",
        "manifest": "/api/artifacts/stock-analysis/latest/manifest",
    }
    assert manifest_status == 200
    assert manifest_headers["Cache-Control"] == "no-store"
    assert manifest_headers["Content-Type"].startswith("application/json")
    assert manifest["schema_version"] == 1
    assert manifest["reports"] == {
        "stock_analysis": "reports/stock-analysis-report.md",
        "ui": "index.html",
    }
    assert manifest["safety"]["passed"] is True
    assert manifest["key_claims"][0]["provenance_refs"]
    assert report_status == 200
    assert report_headers["Cache-Control"] == "no-store"
    assert report_headers["Content-Type"] == "text/markdown; charset=utf-8"
    assert report_body.decode("utf-8") == "# MSFT Research Report\n"
    rendered = "\n".join(
        [
            summary_body.decode(),
            manifest_body.decode(),
            report_body.decode(),
        ]
    ).lower()
    assert str(tmp_path).lower() not in rendered
    assert "/users/" not in rendered


@pytest.mark.parametrize(
    ("prepare", "expected_status", "expected_code", "expected_reason"),
    [
        (
            lambda root: None,
            404,
            "artifact_not_found",
            "stock_analysis_artifact_missing",
        ),
        (
            lambda root: _write_canonical_artifact(
                root,
                mutate=lambda payload: payload.update(research_only=False),
            ),
            409,
            "artifact_blocked",
            "research_only_required",
        ),
        (
            lambda root: _write_canonical_artifact(
                root,
                mutate=lambda payload: payload["key_claims"][0].update(
                    provenance_refs=[]
                ),
            ),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda root: _write_canonical_artifact(
                root,
                mutate=lambda payload: payload["reports"].update(
                    stock_analysis="../secret.md"
                ),
            ),
            422,
            "artifact_invalid",
            "report_path_invalid",
        ),
    ],
)
def test_local_api_returns_sanitized_artifact_errors(
    tmp_path,
    prepare,
    expected_status,
    expected_code,
    expected_reason,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    prepare(artifact_dir)
    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
    )
    payload = json.loads(body)

    assert status == expected_status
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Type"].startswith("application/json")
    assert payload == {
        "error": {
            "code": expected_code,
            "reason": expected_reason,
        }
    }
    assert str(tmp_path) not in body.decode("utf-8")
    assert "/users/" not in body.decode("utf-8").lower()


@pytest.mark.parametrize("suffix", ["", "/manifest", "/report"])
def test_local_api_maps_repository_errors_for_every_artifact_route(
    tmp_path,
    suffix,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(
        artifact_dir,
        mutate=lambda payload: payload.update(research_only=False),
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix=suffix,
    )

    assert status == 409
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {
        "error": {
            "code": "artifact_blocked",
            "reason": "research_only_required",
        }
    }
    assert str(tmp_path) not in body.decode("utf-8")


def test_local_api_reports_missing_markdown_without_path_leakage(tmp_path) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(artifact_dir)
    (artifact_dir / "reports" / "stock-analysis-report.md").unlink()

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix="/report",
    )

    assert status == 404
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {
        "error": {
            "code": "artifact_not_found",
            "reason": "stock_analysis_report_missing",
        }
    }
    assert str(tmp_path) not in body.decode("utf-8")


@pytest.mark.parametrize(
    ("suffix", "local_path"),
    [
        ("", "Review,/Users/alice/private/secret.txt"),
        ("/manifest", "Review /workspace/project/secret.txt"),
        ("", "Review /etc/passwd"),
        ("/manifest", r"Review D:\work\secret.txt"),
        ("", r"Review \\server\share\secret.txt"),
        ("", "Source:/Users/alice/private/secret.txt"),
        ("/manifest", "/secret.txt"),
        ("", "file:/Users/alice/private/secret.txt"),
        ("/manifest", "/数据/秘密.txt"),
        ("", r"C:\secret.txt"),
        ("/manifest", r"C:\Program Files\secret.txt"),
        ("", "https:///Users/alice/private/secret.txt"),
        ("/manifest", "serenity:///Users/alice/private/secret.txt"),
        ("", "https://[bad/Users/alice/private/secret.txt"),
        ("/manifest", "/USERS"),
        ("", "/TMP"),
        ("/manifest", "/SECRET"),
    ],
)
def test_local_api_rejects_local_paths_in_json_artifact_responses(
    tmp_path,
    suffix,
    local_path,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(
        artifact_dir,
        mutate=lambda payload: payload.update(query=local_path),
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix=suffix,
    )

    assert status == 422
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {
        "error": {
            "code": "artifact_invalid",
            "reason": "local_path_detected",
        }
    }
    assert local_path not in body.decode("utf-8")


@pytest.mark.parametrize(
    "safe_url",
    [
        "https://example.com/view?path=/docs/report.pdf",
        "serenity://market-data/MSFT/quote?path=/docs/report.pdf",
        "https://[2001:db8::1]/reports/2026",
    ],
)
def test_local_api_allows_trusted_urls_with_root_relative_components(
    tmp_path,
    safe_url,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(
        artifact_dir,
        mutate=lambda payload: payload["key_claims"][0][
            "provenance_refs"
        ][0].update(source_url=safe_url),
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix="/manifest",
    )

    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert safe_url in body.decode("utf-8")


def test_local_api_allows_trusted_url_in_markdown_report(tmp_path) -> None:
    safe_url = "https://example.com/view?path=/docs/report.pdf"
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(artifact_dir)
    report = f"# MSFT Research Report\n\n[source]({safe_url})\n"
    (artifact_dir / "reports" / "stock-analysis-report.md").write_text(
        report,
        encoding="utf-8",
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix="/report",
    )

    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert body.decode("utf-8") == report


def test_local_api_allows_html_closing_tags_and_market_symbols(tmp_path) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(artifact_dir)
    report = (
        "# MSFT Research Report\n\n"
        "</div>\n\n"
        "Market contracts: /ES, (/NQ)\n"
    )
    (artifact_dir / "reports" / "stock-analysis-report.md").write_text(
        report,
        encoding="utf-8",
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix="/report",
    )

    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert body.decode("utf-8") == report


@pytest.mark.parametrize(
    "local_path",
    [
        "/workspace/project/secret.txt",
        r"D:\work\secret.txt",
        r"\\server\share\secret.txt",
    ],
)
def test_local_api_rejects_local_paths_in_markdown_report(
    tmp_path,
    local_path,
) -> None:
    artifact_dir = tmp_path / "stock-analysis"
    _write_canonical_artifact(artifact_dir)
    (artifact_dir / "reports" / "stock-analysis-report.md").write_text(
        f"# MSFT Research Report\n\nSource: {local_path}\n",
        encoding="utf-8",
    )

    status, headers, body = _request_latest_artifact(
        artifact_dir,
        tmp_path / "runs.json",
        suffix="/report",
    )

    assert status == 422
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {
        "error": {
            "code": "artifact_invalid",
            "reason": "local_path_detected",
        }
    }
    assert local_path not in body.decode("utf-8")


def test_local_api_preserves_generic_not_found_behavior(tmp_path) -> None:
    config = AppRuntimeConfig(
        runs_path=tmp_path / "runs.json",
        stock_analysis_artifact_dir=tmp_path / "stock-analysis",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_api_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, body = _get_response(
            f"http://127.0.0.1:{server.server_port}/unknown"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status == 404
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {
        "error": "not_found",
        "path": "/unknown",
    }


def test_run_records_loader_accepts_legacy_top_level_list(tmp_path):
    runs_path = tmp_path / "runs.json"
    runs_path.write_text(
        json.dumps(
            [
                {
                    "job_id": "job-legacy",
                    "status": "completed",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert _load_run_records(runs_path)[0]["job_id"] == "job-legacy"
