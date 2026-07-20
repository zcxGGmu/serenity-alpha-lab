# Python Project Metadata Review

> Task: `SAL-P1-002` Standardize Python project metadata<br>
> Date: 2026-07-20<br>
> Baseline: DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Scope: Root packaging metadata only; dependency extras and lock generation are covered by `SAL-P1-003`.

## Summary

The root project now has standard PEP 621 metadata in `pyproject.toml`. This makes Serenity Alpha Lab installable as a Python package while keeping the DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.

The metadata intentionally does not copy DSA runtime modules into the working tree. Console scripts expose compatibility entry points that resolve the isolated DSA worktree at runtime and can be validated in dry-run mode.

## Migrated From DSA Baseline

| Source | Treatment |
|---|---|
| `.worktrees/dsa-v3.26.1/requirements.txt` | Runtime dependency declarations moved into `core` / `providers` / `desktop` optional dependency surfaces with comments removed and PEP 508 markers normalized. |
| `.worktrees/dsa-v3.26.1/pyproject.toml` | Black, isort, and Bandit tool settings carried forward and adapted to exclude Serenity cache/worktree directories. |
| `.worktrees/dsa-v3.26.1/setup.cfg` | Pytest discovery, markers, and line-length conventions carried into root tool configuration. |
| DSA `main.py`, `server.py`, `src/services/alert_worker.py`, and `tests/` | Referenced by compatibility entry-point wrappers only; files remain in the isolated worktree. |

## Intentional Differences

- Project name is `serenity-alpha-lab`; DSA source remains an upstream baseline, not the root package name.
- Python support is declared as `>=3.11,<3.13`, matching the P0 validated Python 3.11 environment and DSA 3.12 target range.
- Build backend is `setuptools.build_meta` because the existing P0 virtualenv already includes modern setuptools with editable-install support.
- `SAL-P1-003` removed the AlphaSift dynamic Git dependency from Serenity production dependency declarations. DSA's isolated upstream worktree remains unchanged; reviewed AlphaSift wheel/package intake is deferred to the later AlphaSift adapter task.
- `core/providers/desktop/quant/dev` extras, `uv.lock`, and exported `requirements.txt` are now tracked by `SAL-P1-003`; see [Python 依赖 Extras 与锁文件记录](./python-dependency-lock.md).

## Entry Points

| Script | Target |
|---|---|
| `serenity-alpha-lab` | Serenity CLI metadata and future local commands. |
| `serenity-dsa-cli` | DSA `main.py` command wrapper. |
| `serenity-dsa-api` | DSA `main.py --serve-only` API wrapper. |
| `serenity-dsa-worker` | DSA scheduled worker wrapper using `main.py --schedule --no-run-immediately`. |
| `serenity-dsa-tests` | DSA pytest wrapper for isolated worktree validation. |

Set `SERENITY_DSA_DRY_RUN=1` to validate command construction without launching DSA runtime processes.

## Verification

- `tests/architecture/test_project_metadata.py` parses `pyproject.toml`, checks migrated dependency anchors, and verifies entry-point command construction.
- Editable install verification should use the P0 Python 3.11 virtualenv with `--no-deps` so this metadata task does not resolve dynamic dependencies before `SAL-P1-003`.
