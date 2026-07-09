import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from serenity_alpha_lab import __version__
from serenity_alpha_lab.app import AppRuntimeConfig, create_api_handler
from serenity_alpha_lab.app.local_api import _load_run_records


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


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
