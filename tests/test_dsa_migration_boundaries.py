from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "src" / "serenity_alpha_lab"
EXTERNAL_DSA_CHECKOUT = Path("/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis")
EXTERNAL_DSA_PATH = str(EXTERNAL_DSA_CHECKOUT)


def _python_files() -> list[Path]:
    return sorted(RUNTIME_DIR.rglob("*.py"))


def _literal_strings(node: ast.AST) -> list[str]:
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)
    return values


def test_serenity_runtime_does_not_reference_external_dsa_checkout_path():
    offenders: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for literal in _literal_strings(tree):
            if EXTERNAL_DSA_PATH in literal:
                offenders.append(f"{path.relative_to(ROOT)}: {literal}")

    assert offenders == []


def test_serenity_runtime_does_not_import_dsa_source_packages():
    forbidden_roots = {"api", "bot", "data_provider", "main", "server", "webui"}
    offenders: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots = {alias.name.split(".", 1)[0] for alias in node.names}
                forbidden = sorted(imported_roots & forbidden_roots)
                if forbidden:
                    offenders.append(f"{path.relative_to(ROOT)} imports {', '.join(forbidden)}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_root = node.module.split(".", 1)[0]
                if imported_root in forbidden_roots:
                    offenders.append(f"{path.relative_to(ROOT)} imports from {node.module}")

    assert offenders == []


def test_serenity_package_name_remains_owned_by_serenity():
    assert RUNTIME_DIR.exists()
    assert (RUNTIME_DIR / "__init__.py").exists()
    assert not (ROOT / "src" / "daily_stock_analysis").exists()
