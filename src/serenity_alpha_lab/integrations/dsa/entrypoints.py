from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


DSA_ROOT_ENV = "SERENITY_DSA_ROOT"
DSA_DRY_RUN_ENV = "SERENITY_DSA_DRY_RUN"


@dataclass(frozen=True)
class DsaCommand:
    """Resolved DSA command metadata."""

    kind: str
    root: Path
    argv: tuple[str, ...]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _candidate_repo_roots() -> list[Path]:
    roots = [Path.cwd()]
    roots.extend(Path(__file__).resolve().parents)
    return roots


def _default_dsa_root() -> Path:
    for root in _candidate_repo_roots():
        candidate = root / ".worktrees" / "dsa-v3.26.1"
        if candidate.exists():
            return candidate
    return Path.cwd() / ".worktrees" / "dsa-v3.26.1"


def resolve_dsa_root(root: str | Path | None = None) -> Path:
    dsa_root = Path(root or os.environ.get(DSA_ROOT_ENV) or _default_dsa_root()).expanduser().resolve()
    required_paths = [
        dsa_root / "main.py",
        dsa_root / "server.py",
        dsa_root / "src" / "services" / "alert_worker.py",
        dsa_root / "tests",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"DSA runtime root is incomplete: {dsa_root}. Missing: {', '.join(missing)}"
        )
    return dsa_root


def build_dsa_command(
    kind: str,
    argv: Sequence[str] | None = None,
    *,
    root: str | Path | None = None,
    python: str | None = None,
) -> list[str]:
    dsa_root = resolve_dsa_root(root)
    args = list(argv or [])
    executable = python or sys.executable

    if kind == "cli":
        return [executable, str(dsa_root / "main.py"), *args]
    if kind == "api":
        return [executable, str(dsa_root / "main.py"), "--serve-only", *args]
    if kind == "worker":
        return [executable, str(dsa_root / "main.py"), "--schedule", "--no-run-immediately", *args]
    if kind == "tests":
        return [executable, "-m", "pytest", *args]
    raise ValueError(f"Unsupported DSA entrypoint kind: {kind}")


def _run(kind: str, argv: Sequence[str] | None = None) -> int:
    dsa_root = resolve_dsa_root()
    forwarded_argv = sys.argv[1:] if argv is None else argv
    command = build_dsa_command(kind, forwarded_argv, root=dsa_root)
    if _truthy(os.environ.get(DSA_DRY_RUN_ENV)):
        print(" ".join(command))
        return 0
    return subprocess.call(command, cwd=dsa_root)


def run_cli(argv: Sequence[str] | None = None) -> int:
    return _run("cli", argv)


def run_api(argv: Sequence[str] | None = None) -> int:
    return _run("api", argv)


def run_worker(argv: Sequence[str] | None = None) -> int:
    return _run("worker", argv)


def run_tests(argv: Sequence[str] | None = None) -> int:
    return _run("tests", argv)
