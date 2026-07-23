from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "src" / "serenity_alpha_lab"

DOMAIN_FORBIDDEN_IMPORT_ROOTS = {
    "akshare",
    "fastapi",
    "litellm",
    "pandas",
    "qlib",
    "sqlalchemy",
}

DOMAIN_FORBIDDEN_INTERNAL_PREFIXES = (
    "serenity_alpha_lab.integrations",
    "serenity_alpha_lab.repositories",
    "serenity_alpha_lab.services",
)

DATASETS_FORBIDDEN_IMPORT_ROOTS = {
    "akshare",
    "fastapi",
    "litellm",
    "pandas",
    "qlib",
    "sqlalchemy",
}

DATASETS_FORBIDDEN_INTERNAL_PREFIXES = (
    "serenity_alpha_lab.integrations",
    "serenity_alpha_lab.repositories",
    "serenity_alpha_lab.services",
)

QUANT_FORBIDDEN_INTERNAL_PREFIXES = (
    "serenity_alpha_lab.agents",
    "serenity_alpha_lab.notifications",
    "serenity_alpha_lab.integrations.dsa.agent",
    "serenity_alpha_lab.integrations.dsa.notification",
)

INTEGRATION_FORBIDDEN_INTERNAL_PREFIXES = (
    "serenity_alpha_lab.repositories",
)


def iter_python_files(package: str) -> list[Path]:
    package_path = PACKAGE_ROOT / package
    return sorted(path for path in package_path.rglob("*.py") if "__pycache__" not in path.parts)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def imported_names(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.update((node.module, alias.name) for alias in node.names)
    return names


def assert_no_forbidden_imports(
    package: str,
    *,
    forbidden_roots: set[str] | None = None,
    forbidden_prefixes: tuple[str, ...] = (),
) -> None:
    failures: list[str] = []
    for path in iter_python_files(package):
        for module in imported_modules(path):
            root = module.split(".", maxsplit=1)[0]
            if forbidden_roots and root in forbidden_roots:
                failures.append(f"{path.relative_to(ROOT)} imports {module}")
            if module.startswith(forbidden_prefixes):
                failures.append(f"{path.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_target_package_skeleton_exists() -> None:
    expected_packages = [
        "domain",
        "application",
        "quant",
        "quant/factors",
        "quant/screening",
        "quant/backtest",
        "quant/portfolio",
        "quant/risk",
        "datasets",
        "evidence",
        "integrations",
        "integrations/dsa",
        "integrations/data",
        "repositories",
        "services",
    ]

    missing = [
        package for package in expected_packages if not (PACKAGE_ROOT / package / "__init__.py").exists()
    ]
    assert missing == []


def test_domain_stays_free_of_frameworks_and_infrastructure() -> None:
    assert_no_forbidden_imports(
        "domain",
        forbidden_roots=DOMAIN_FORBIDDEN_IMPORT_ROOTS,
        forbidden_prefixes=DOMAIN_FORBIDDEN_INTERNAL_PREFIXES,
    )


def test_provider_domain_contract_does_not_import_application_or_integrations() -> None:
    target = PACKAGE_ROOT / "domain" / "providers.py"
    failures: list[str] = []
    allowed_modules = {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "enum",
        "math",
        "serenity_alpha_lab.domain.artifacts",
        "serenity_alpha_lab.domain.instruments",
        "types",
        "typing",
    }

    if not target.exists():
        failures.append(f"{target.relative_to(ROOT)} does not exist")
    else:
        for module in imported_modules(target):
            if module not in allowed_modules:
                failures.append(f"{target.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_datasets_stay_free_of_provider_runtime_and_infrastructure() -> None:
    assert_no_forbidden_imports(
        "datasets",
        forbidden_roots=DATASETS_FORBIDDEN_IMPORT_ROOTS,
        forbidden_prefixes=DATASETS_FORBIDDEN_INTERNAL_PREFIXES,
    )


def test_quant_does_not_depend_on_agent_or_notifications() -> None:
    assert_no_forbidden_imports(
        "quant",
        forbidden_prefixes=QUANT_FORBIDDEN_INTERNAL_PREFIXES,
    )


def test_integrations_do_not_reach_into_repositories() -> None:
    assert_no_forbidden_imports(
        "integrations",
        forbidden_prefixes=INTEGRATION_FORBIDDEN_INTERNAL_PREFIXES,
    )


def test_application_and_dsa_task_facade_do_not_import_thread_pool_executor() -> None:
    failures: list[str] = []
    for package in ("application", "integrations/dsa"):
        for path in iter_python_files(package):
            if ("concurrent.futures", "ThreadPoolExecutor") in imported_names(path):
                failures.append(f"{path.relative_to(ROOT)} imports ThreadPoolExecutor")

    assert failures == []


def test_research_orchestrator_contracts_do_not_import_concrete_dsa_agent_runtime() -> None:
    failures: list[str] = []
    forbidden_prefixes = (
        "src.agent",
        "src.core.pipeline",
        "api.v1.endpoints.agent",
        "bot.commands",
    )
    target_files = [
        PACKAGE_ROOT / "application" / "research_orchestrator.py",
        PACKAGE_ROOT / "integrations" / "dsa" / "research_orchestrator.py",
    ]

    for path in target_files:
        if not path.exists():
            failures.append(f"{path.relative_to(ROOT)} does not exist")
            continue
        for module in imported_modules(path):
            if module.startswith(forbidden_prefixes):
                failures.append(f"{path.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_screening_provider_contracts_do_not_import_alphasift_runtime() -> None:
    failures: list[str] = []
    target_files = [
        PACKAGE_ROOT / "application" / "screening_provider.py",
        PACKAGE_ROOT / "domain" / "__init__.py",
    ]

    for path in target_files:
        if not path.exists():
            failures.append(f"{path.relative_to(ROOT)} does not exist")
            continue
        for module in imported_modules(path):
            if module == "alphasift" or module.startswith("alphasift."):
                failures.append(f"{path.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_alphasift_adapter_keeps_alphasift_import_lazy_and_integration_scoped() -> None:
    failures: list[str] = []
    target = PACKAGE_ROOT / "integrations" / "alphasift" / "provider_adapter.py"
    if not target.exists():
        failures.append(f"{target.relative_to(ROOT)} does not exist")
    else:
        for module in imported_modules(target):
            if module == "alphasift" or module.startswith("alphasift."):
                failures.append(f"{target.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_dsa_provider_adapter_keeps_concrete_dsa_imports_lazy() -> None:
    failures: list[str] = []
    target = PACKAGE_ROOT / "integrations" / "dsa" / "provider_adapter.py"
    forbidden_modules = ("data_provider", "src")
    forbidden_prefixes = tuple(f"{prefix}." for prefix in forbidden_modules)
    if not target.exists():
        failures.append(f"{target.relative_to(ROOT)} does not exist")
    else:
        for module in imported_modules(target):
            if module in forbidden_modules or module.startswith(forbidden_prefixes):
                failures.append(f"{target.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_dsa_symbol_compatibility_stays_integration_only_and_dsa_runtime_free() -> None:
    failures: list[str] = []
    target = PACKAGE_ROOT / "integrations" / "dsa" / "symbol_compatibility.py"
    allowed_modules = {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "serenity_alpha_lab.domain.instruments",
    }
    if not target.exists():
        failures.append(f"{target.relative_to(ROOT)} does not exist")
    else:
        for module in imported_modules(target):
            if module not in allowed_modules:
                failures.append(f"{target.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_repositories_do_not_import_concrete_dsa_provider_runtime() -> None:
    failures: list[str] = []
    forbidden_modules = ("data_provider", "src")
    forbidden_prefixes = tuple(f"{prefix}." for prefix in forbidden_modules)
    for path in iter_python_files("repositories"):
        for module in imported_modules(path):
            if module in forbidden_modules or module.startswith(forbidden_prefixes):
                failures.append(f"{path.relative_to(ROOT)} imports {module}")

    assert failures == []


def test_api_error_protocol_stays_framework_neutral() -> None:
    failures: list[str] = []
    target = PACKAGE_ROOT / "application" / "api_errors.py"
    if not target.exists():
        failures.append(f"{target.relative_to(ROOT)} does not exist")
    else:
        for module in imported_modules(target):
            root = module.split(".", maxsplit=1)[0]
            if root in {"fastapi", "starlette"}:
                failures.append(f"{target.relative_to(ROOT)} imports {module}")

    assert failures == []
