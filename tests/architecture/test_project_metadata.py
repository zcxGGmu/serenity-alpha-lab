from __future__ import annotations

import importlib
import os
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def load_pyproject() -> dict:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)


def test_pyproject_declares_standard_project_metadata() -> None:
    data = load_pyproject()

    assert data["build-system"]["build-backend"] == "setuptools.build_meta"

    project = data["project"]
    assert project["name"] == "serenity-alpha-lab"
    assert project["version"] == "0.1.0a0"
    assert project["requires-python"] == ">=3.11,<3.13"

    scripts = project["scripts"]
    assert scripts["serenity-alpha-lab"] == "serenity_alpha_lab.cli:main"
    assert scripts["serenity-dsa-cli"] == "serenity_alpha_lab.integrations.dsa.entrypoints:run_cli"
    assert scripts["serenity-dsa-api"] == "serenity_alpha_lab.integrations.dsa.entrypoints:run_api"
    assert scripts["serenity-dsa-worker"] == "serenity_alpha_lab.integrations.dsa.entrypoints:run_worker"
    assert scripts["serenity-dsa-tests"] == "serenity_alpha_lab.integrations.dsa.entrypoints:run_tests"


def test_pyproject_migrates_current_dsa_runtime_dependencies() -> None:
    dependencies = set(load_pyproject()["project"]["dependencies"])

    assert "python-dotenv>=1.0.0" in dependencies
    assert "sqlalchemy>=2.0.0" in dependencies
    assert "exchange-calendars>=4.13.0" in dependencies
    assert "fastapi>=0.109.0" in dependencies
    assert "uvicorn[standard]>=0.27.0" in dependencies
    assert "litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0" in dependencies
    assert (
        "alphasift @ git+https://github.com/ZhuLinsen/alphasift.git"
        "@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
    ) in dependencies


def test_package_and_dsa_entrypoints_are_importable() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    try:
        package = importlib.import_module("serenity_alpha_lab")
        cli = importlib.import_module("serenity_alpha_lab.cli")
        entrypoints = importlib.import_module("serenity_alpha_lab.integrations.dsa.entrypoints")
    finally:
        sys.path.remove(str(ROOT / "src"))

    assert package.__version__ == "0.1.0a0"
    assert cli.main(["--version"]) == 0

    dsa_root = ROOT / ".worktrees" / "dsa-v3.26.1"
    assert entrypoints.resolve_dsa_root(dsa_root) == dsa_root
    assert entrypoints.build_dsa_command("cli", ["--help"], root=dsa_root)[1:] == [
        str(dsa_root / "main.py"),
        "--help",
    ]
    assert "--serve-only" in entrypoints.build_dsa_command("api", root=dsa_root)
    assert "--schedule" in entrypoints.build_dsa_command("worker", root=dsa_root)
    assert entrypoints.build_dsa_command("tests", ["tests/test_local_cli_backend.py"], root=dsa_root)[1:] == [
        "-m",
        "pytest",
        "tests/test_local_cli_backend.py",
    ]

    os.environ["SERENITY_DSA_DRY_RUN"] = "1"
    try:
        assert entrypoints.run_cli(["--help"]) == 0
        assert entrypoints.run_api(["--host", "127.0.0.1"]) == 0
        assert entrypoints.run_worker(["--no-run-immediately"]) == 0
        assert entrypoints.run_tests(["tests/test_local_cli_backend.py", "-q"]) == 0
        with patch.object(sys, "argv", ["serenity-dsa-cli", "--check-notify"]):
            assert entrypoints.run_cli() == 0
    finally:
        os.environ.pop("SERENITY_DSA_DRY_RUN", None)
