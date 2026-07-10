from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ReleaseCheck = dict[str, Any]
ReleaseCheckRunner = Callable[[ReleaseCheck], Mapping[str, Any]]

_OFFLINE_ENVIRONMENT = {
    "SERENITY_EXTERNAL_INTEGRATIONS_ENABLED": "false",
    "SERENITY_RESEARCH_AGENTS_ENABLED": "false",
    "SERENITY_RESEARCH_BOT_ENABLED": "false",
    "SERENITY_RESEARCH_MONITORS_ENABLED": "false",
    "SERENITY_RESEARCH_MONITOR_NOTIFICATIONS_ENABLED": "false",
    "SERENITY_MARKET_DATA_API_KEY": "",
    "SERENITY_NOTIFICATION_CHANNELS": "",
}
_OUTPUT_TAIL_LIMIT = 4000


def build_release_check_plan() -> dict[str, Any]:
    return {
        "offline_application_semantics": True,
        "requires_secrets": False,
        "requires_external_providers": False,
        "research_only": True,
        "protected_paths": ["output/ui"],
        "environment": dict(_OFFLINE_ENVIRONMENT),
        "checks": [
            _command_check(
                "python_tests",
                ["python3", "-m", "pytest", "tests", "-q"],
            ),
            _command_check(
                "doctor",
                ["python3", "-m", "serenity_alpha_lab.cli", "doctor"],
            ),
            _command_check(
                "agent_bot_desktop",
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/test_research_agents.py",
                    "tests/test_research_bot.py",
                    "tests/test_desktop_runtime.py",
                    "tests/test_app_api.py",
                    "-q",
                ],
            ),
            _command_check(
                "report_safety",
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/test_analysis_report.py",
                    "-q",
                ],
            ),
            _command_check(
                "dsa_boundary",
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/test_dsa_migration_boundaries.py",
                    "-q",
                ],
            ),
            _command_check(
                "frontend_unit",
                ["npm", "test", "--", "--run"],
                cwd="apps/serenity-web",
            ),
            _command_check(
                "frontend_build",
                ["npm", "run", "build"],
                cwd="apps/serenity-web",
            ),
            _command_check(
                "frontend_smoke",
                ["npm", "run", "test:smoke", "--", "--reporter=line"],
                cwd="apps/serenity-web",
                required=False,
            ),
            {
                "id": "docker_static",
                "kind": "internal",
                "required": True,
            },
            {
                "id": "docker_smoke",
                "kind": "internal",
                "required": False,
            },
        ],
    }


def run_release_check(
    *,
    command_runner: ReleaseCheckRunner | None = None,
    include_browser_smoke: bool = True,
    include_docker_smoke: bool = True,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    plan = build_release_check_plan()
    root = Path(repo_root) if repo_root is not None else _repository_root()
    runner = command_runner or (
        lambda check: _run_check(
            check,
            repo_root=root,
            environment=plan["environment"],
        )
    )
    results: list[dict[str, Any]] = []

    for check in plan["checks"]:
        check_id = str(check["id"])
        if check_id == "frontend_smoke" and not include_browser_smoke:
            results.append(_explicit_skip(check_id))
            continue
        if check_id == "docker_smoke" and not include_docker_smoke:
            results.append(_explicit_skip(check_id))
            continue

        outcome = dict(runner(dict(check)))
        status = str(outcome.get("status") or "blocked")
        if status not in {"passed", "blocked", "skipped"}:
            status = "blocked"
            outcome = {"reason": "invalid_check_status"}
        if status == "skipped":
            status = "blocked"
            outcome = {"reason": "skip_requires_explicit_caller_choice"}

        result = {
            "id": check_id,
            "status": status,
            "reason": str(outcome.get("reason") or f"check_{status}"),
        }
        for key in ("return_code", "stdout_tail", "stderr_tail"):
            if key not in outcome:
                continue
            value = outcome[key]
            if key in {"stdout_tail", "stderr_tail"}:
                value = _sanitize_output(str(value), root)
            result[key] = value
        results.append(result)

    blocked = [check for check in results if check["status"] == "blocked"]
    skipped = [check for check in results if check["status"] == "skipped"]
    return {
        "status": "blocked" if blocked else "passed",
        "research_only": True,
        "offline_application_semantics": True,
        "error_count": len(blocked),
        "skipped_count": len(skipped),
        "checks": results,
    }


def _command_check(
    check_id: str,
    command: list[str],
    *,
    cwd: str = ".",
    required: bool = True,
) -> ReleaseCheck:
    return {
        "id": check_id,
        "kind": "command",
        "required": required,
        "command": command,
        "cwd": cwd,
    }


def _explicit_skip(check_id: str) -> dict[str, str]:
    return {
        "id": check_id,
        "status": "skipped",
        "reason": "explicitly_disabled_by_caller",
    }


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_check(
    check: ReleaseCheck,
    *,
    repo_root: Path,
    environment: Mapping[str, str],
) -> Mapping[str, Any]:
    check_id = str(check["id"])
    if check_id == "docker_static":
        return _run_docker_static_check(repo_root)
    if check_id == "docker_smoke":
        return _run_docker_smoke(repo_root, environment)
    return _run_command_check(check, repo_root=repo_root, environment=environment)


def _run_command_check(
    check: ReleaseCheck,
    *,
    repo_root: Path,
    environment: Mapping[str, str],
) -> Mapping[str, Any]:
    command = check.get("command")
    if not isinstance(command, list) or not all(
        isinstance(item, str) and item
        for item in command
    ):
        return {"status": "blocked", "reason": "invalid_command"}

    cwd = repo_root / str(check.get("cwd") or ".")
    env = os.environ.copy()
    env.update(environment)
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else src_path
    )

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except FileNotFoundError:
        return {"status": "blocked", "reason": "command_not_found"}
    except subprocess.TimeoutExpired:
        return {"status": "blocked", "reason": "command_timeout"}

    return {
        "status": "passed" if completed.returncode == 0 else "blocked",
        "reason": "command_passed" if completed.returncode == 0 else "command_failed",
        "return_code": completed.returncode,
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }


def _run_docker_static_check(repo_root: Path) -> Mapping[str, Any]:
    dockerfile = repo_root / "docker" / "Dockerfile"
    compose = repo_root / "docker" / "docker-compose.yml"
    dockerignore = repo_root / ".dockerignore"
    if not all(path.is_file() for path in (dockerfile, compose, dockerignore)):
        return {"status": "blocked", "reason": "docker_files_missing"}

    dockerfile_text = dockerfile.read_text(encoding="utf-8")
    compose_text = compose.read_text(encoding="utf-8")
    dockerignore_text = dockerignore.read_text(encoding="utf-8")
    required_fragments = (
        (dockerfile_text, "USER serenity"),
        (dockerfile_text, "/health"),
        (dockerignore_text, "output/ui"),
        (dockerignore_text, ".env"),
        (dockerignore_text, "daily_stock_analysis"),
        (compose_text, "SERENITY_RESEARCH_AGENTS_ENABLED=false"),
        (compose_text, "SERENITY_RESEARCH_BOT_ENABLED=false"),
    )
    if not all(fragment in text for text, fragment in required_fragments):
        return {"status": "blocked", "reason": "docker_static_rule_failed"}
    return {"status": "passed", "reason": "docker_static_rules_passed"}


def _run_docker_smoke(
    repo_root: Path,
    environment: Mapping[str, str],
) -> Mapping[str, Any]:
    if shutil.which("docker") is None:
        return {"status": "blocked", "reason": "docker_command_not_found"}

    info = _run_process(
        ["docker", "info"],
        cwd=repo_root,
        environment=environment,
        timeout=60,
    )
    if info["status"] != "passed":
        return {"status": "blocked", "reason": "docker_daemon_unavailable"}

    image = "serenity-alpha-lab:offline-release"
    container = "serenity-alpha-lab-offline-release"
    build = _run_process(
        ["docker", "build", "-f", "docker/Dockerfile", "-t", image, "."],
        cwd=repo_root,
        environment=environment,
        timeout=1200,
    )
    if build["status"] != "passed":
        return build

    _run_process(
        ["docker", "rm", "-f", container],
        cwd=repo_root,
        environment=environment,
        timeout=30,
    )
    started = _run_process(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            container,
            "-p",
            "18010:8010",
            image,
        ],
        cwd=repo_root,
        environment=environment,
        timeout=60,
    )
    if started["status"] != "passed":
        return started

    try:
        if not _wait_for_health("http://127.0.0.1:18010/health"):
            return {"status": "blocked", "reason": "docker_health_failed"}
        return {"status": "passed", "reason": "docker_health_passed"}
    finally:
        _run_process(
            ["docker", "stop", container],
            cwd=repo_root,
            environment=environment,
            timeout=60,
        )


def _run_process(
    command: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(environment)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "blocked",
            "reason": type(exc).__name__,
        }
    return {
        "status": "passed" if completed.returncode == 0 else "blocked",
        "reason": "command_passed" if completed.returncode == 0 else "command_failed",
        "return_code": completed.returncode,
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }


def _wait_for_health(url: str) -> bool:
    for _ in range(30):
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200 and b'"research_only": true' in response.read():
                    return True
        except (URLError, TimeoutError):
            time.sleep(1)
    return False


def _tail(value: str) -> str:
    return value[-_OUTPUT_TAIL_LIMIT:]


def _sanitize_output(value: str, repo_root: Path) -> str:
    root = str(repo_root.resolve())
    return value.replace(root, "<repo>")
