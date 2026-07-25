from __future__ import annotations

import ast
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
LOCKFILE = ROOT / "uv.lock"
REQUIREMENTS = ROOT / "requirements.txt"
REVIEW_DOC = ROOT / "docs" / "qlib-version-isolation.md"
ADR = ROOT / "docs" / "adr" / "ADR-009-qlib-adapter-boundary-and-version-upgrade-strategy.md"
POLICY_MODULE = ROOT / "src" / "serenity_alpha_lab" / "integrations" / "qlib" / "runtime_policy.py"


def load_pyproject() -> dict:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_quant_extra_pins_pyqlib_exactly_and_keeps_production_surface_clean() -> None:
    project = load_pyproject()["project"]
    quant_dependencies = project["optional-dependencies"]["quant"]

    assert "pyqlib==0.9.7" in quant_dependencies
    assert all(not dependency.startswith("pyqlib>=") for dependency in quant_dependencies)

    requirements_text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "pyqlib==" not in requirements_text
    assert "qlib" not in requirements_text.lower()


def test_uv_lock_captures_pyqlib_version_and_supported_worker_wheels() -> None:
    lock_text = LOCKFILE.read_text(encoding="utf-8")

    required_terms = [
        'name = "pyqlib"',
        'version = "0.9.7"',
        "pyqlib-0.9.7-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "sha256:f74d6344984dce6e774a90dc0b8ef7ff78d85036aba81b4bdc7bfa9e9184ecae",
        "pyqlib-0.9.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "sha256:b50e70d127976d973c447af667b51aa2bb088d79bc0c344e295e9aadc753b86e",
        "pyqlib-0.9.7-cp311-cp311-macosx_10_9_universal2.whl",
        "pyqlib-0.9.7-cp312-cp312-macosx_10_13_universal2.whl",
        "pyqlib-0.9.7-cp311-cp311-win_amd64.whl",
        "pyqlib-0.9.7-cp312-cp312-win_amd64.whl",
    ]

    missing = [term for term in required_terms if term not in lock_text]
    assert missing == []


def test_qlib_review_doc_records_license_dependencies_platforms_and_non_goals() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    required_terms = [
        "SAL-P4-005",
        "package_name: pyqlib",
        "locked_version: 0.9.7",
        "license_spdx: MIT",
        'requires_python: ">=3.8.0"',
        'approved_python: ">=3.11,<3.13"',
        "production_requirements_contains_pyqlib: false",
        "pyyaml",
        "numpy",
        "pandas>=0.24",
        "mlflow",
        "filelock>=3.16.0",
        "redis",
        "lightgbm",
        "cvxpy",
        "macOS universal2",
        "manylinux2014 x86_64",
        "Windows amd64",
        "worker-quant",
        "dedicated Quant Worker process",
        "qlib.init",
        "must not start formal portfolio backtest runs",
        "must not initialize Qlib in FastAPI",
        "must not call real Provider",
        "must not call real LLM",
        "legacy_signal_evaluation",
    ]

    missing = [term for term in required_terms if term not in text]
    assert missing == []


def test_qlib_adr_freezes_worker_boundary_and_upgrade_strategy() -> None:
    text = ADR.read_text(encoding="utf-8")

    required_terms = [
        "ADR-009",
        "Status: Approved",
        "SAL-P4-005",
        "pyqlib==0.9.7",
        "MIT",
        "Quant Worker",
        "FastAPI",
        "arbitrary Python module path",
        "Run/Stage/Event",
        "resource limits",
        "upgrade",
        "golden",
        "stop-use",
        "formal portfolio backtest",
    ]

    missing = [term for term in required_terms if term not in text]
    assert missing == []


def test_qlib_runtime_policy_is_worker_only_and_does_not_import_runtime() -> None:
    from serenity_alpha_lab.integrations.qlib.runtime_policy import (
        QLIB_PACKAGE_NAME,
        QLIB_PACKAGE_VERSION,
        QLIB_RUNTIME_SCOPE,
        default_qlib_runtime_policy,
    )

    policy = default_qlib_runtime_policy()

    assert QLIB_PACKAGE_NAME == "pyqlib"
    assert QLIB_PACKAGE_VERSION == "0.9.7"
    assert QLIB_RUNTIME_SCOPE == "quant_worker_only"
    assert policy.queue_name == "worker-quant"
    assert policy.process_isolation == "dedicated_process"
    assert policy.forbid_fastapi_initialization is True
    assert policy.forbid_runtime_import_at_module_import is True
    assert policy.requires_run_stage_context is True
    assert policy.allow_arbitrary_module_path is False
    assert policy.max_cpu_cores == 2
    assert policy.max_memory_mb == 4096
    assert policy.wall_clock_timeout_seconds == 3600
    assert policy.heartbeat_interval_seconds == 15
    assert policy.checkpoint_interval_seconds == 300
    assert policy.to_record()["package"] == {"name": "pyqlib", "version": "0.9.7"}

    forbidden_roots = {"qlib", "pyqlib", "fastapi", "sqlalchemy"}
    imports = imported_modules(POLICY_MODULE)
    assert {module.split(".", maxsplit=1)[0] for module in imports}.isdisjoint(forbidden_roots)

