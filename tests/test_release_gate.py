from __future__ import annotations

from pathlib import Path

from serenity_alpha_lab.release_gate import (
    build_release_check_plan,
    run_release_check,
)


def test_release_plan_is_no_secret_research_only_and_covers_all_surfaces() -> None:
    plan = build_release_check_plan()

    assert plan["offline_application_semantics"] is True
    assert plan["requires_secrets"] is False
    assert plan["requires_external_providers"] is False
    assert plan["protected_paths"] == ["output/ui"]
    ids = {check["id"] for check in plan["checks"]}
    assert {
        "python_tests",
        "doctor",
        "agent_bot_desktop",
        "report_safety",
        "dsa_boundary",
        "frontend_unit",
        "frontend_build",
        "frontend_smoke",
        "docker_static",
        "docker_smoke",
    } <= ids
    for check in plan["checks"]:
        assert check["required"] in {True, False}
        if check["kind"] == "command":
            assert isinstance(check["command"], list)
            assert check["command"]


def test_release_gate_never_treats_required_failure_as_passed() -> None:
    result = run_release_check(
        command_runner=lambda check: {
            "status": "blocked",
            "reason": f"{check['id']}_failed",
        },
        include_browser_smoke=False,
        include_docker_smoke=False,
    )

    assert result["status"] == "blocked"
    assert result["error_count"] >= 1
    assert any(
        check["id"] == "python_tests" and check["status"] == "blocked"
        for check in result["checks"]
    )


def test_release_gate_records_explicit_environment_dependent_skips() -> None:
    result = run_release_check(
        command_runner=lambda check: {"status": "passed"},
        include_browser_smoke=False,
        include_docker_smoke=False,
    )
    by_id = {check["id"]: check for check in result["checks"]}

    assert result["status"] == "passed"
    assert by_id["frontend_smoke"] == {
        "id": "frontend_smoke",
        "status": "skipped",
        "reason": "explicitly_disabled_by_caller",
    }
    assert by_id["docker_smoke"] == {
        "id": "docker_smoke",
        "status": "skipped",
        "reason": "explicitly_disabled_by_caller",
    }
    assert result["skipped_count"] == 2
    assert all("reason" in check for check in result["checks"])


def test_release_plan_does_not_use_protected_generated_ui_as_input() -> None:
    rendered = str(build_release_check_plan()).lower()

    assert "output/ui/analyses/manifest.json" not in rendered
    assert "output/ui/reports/deliverable-research-report.md" not in rendered
    assert "output/ui/runs.json" not in rendered
    assert "topic-2bde5fabbc" not in rendered


def test_release_plan_sets_integrations_default_off() -> None:
    plan = build_release_check_plan()

    assert plan["environment"] == {
        "SERENITY_EXTERNAL_INTEGRATIONS_ENABLED": "false",
        "SERENITY_RESEARCH_AGENTS_ENABLED": "false",
        "SERENITY_RESEARCH_BOT_ENABLED": "false",
        "SERENITY_RESEARCH_MONITORS_ENABLED": "false",
        "SERENITY_RESEARCH_MONITOR_NOTIFICATIONS_ENABLED": "false",
        "SERENITY_MARKET_DATA_API_KEY": "",
        "SERENITY_NOTIFICATION_CHANNELS": "",
    }


def test_release_gate_sanitizes_repo_paths_from_command_output() -> None:
    result = run_release_check(
        command_runner=lambda check: {
            "status": "passed",
            "stdout_tail": "/Users/example/private-repo/output",
            "stderr_tail": "/Users/example/private-repo/error",
        },
        include_browser_smoke=False,
        include_docker_smoke=False,
        repo_root="/Users/example/private-repo",
    )

    rendered = str(result)
    assert "/Users/example/private-repo" not in rendered
    assert "<repo>/output" in rendered


def test_docker_runtime_is_non_root_no_secret_and_excludes_protected_outputs() -> None:
    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")
    compose = Path("docker/docker-compose.yml").read_text(encoding="utf-8")

    assert "FROM node:20" in dockerfile
    assert "FROM python:3.11-slim" in dockerfile
    assert "USER serenity" in dockerfile
    assert "/health" in dockerfile
    assert (
        'CMD ["serenity-alpha-lab", "serve-app", "--host", "0.0.0.0", '
        '"--port", "8010"]'
    ) in dockerfile
    assert "output/ui" in dockerignore
    assert ".env" in dockerignore
    assert "daily_stock_analysis" in dockerignore
    assert "node_modules" in dockerignore
    assert "__pycache__" in dockerignore
    assert "SERENITY_RESEARCH_AGENTS_ENABLED=false" in compose
    assert "SERENITY_RESEARCH_BOT_ENABLED=false" in compose
    assert "SERENITY_RESEARCH_MONITOR_NOTIFICATIONS_ENABLED=false" in compose
    assert "8010:8010" in compose
    assert "4175:4175" in compose


def test_verify_workflow_runs_one_release_gate_for_pr_branch_and_tags() -> None:
    workflow = Path(".github/workflows/verify.yml").read_text(encoding="utf-8")
    playwright = Path("apps/serenity-web/playwright.config.ts").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "branches:" in workflow
    assert "tags:" in workflow
    assert "actions/setup-python@" in workflow
    assert 'python-version: "3.11"' in workflow
    assert "actions/setup-node@" in workflow
    assert 'node-version: "20"' in workflow
    assert "npm ci" in workflow
    assert "playwright install --with-deps chromium" in workflow
    assert "scripts/verify_offline_release.py" in workflow
    assert 'SERENITY_RESEARCH_AGENTS_ENABLED: "false"' in workflow
    assert 'SERENITY_RESEARCH_BOT_ENABLED: "false"' in workflow
    assert (
        'SERENITY_RESEARCH_MONITOR_NOTIFICATIONS_ENABLED: "false"'
        in workflow
    )
    assert "process.env.CI" in playwright
    assert "channel: 'msedge'" in playwright
