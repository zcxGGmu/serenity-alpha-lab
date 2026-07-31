# Qlib Version Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock Qlib/pyqlib for SAL-P4-005 and freeze the process/resource isolation policy before any Qlib runtime or formal portfolio backtest implementation.

**Architecture:** Keep Qlib optional behind the `quant` extra and a new `integrations.qlib` policy module that imports no Qlib runtime. The FastAPI/API/application/domain path stays Qlib-free; later adapter tasks may initialize Qlib only inside a dedicated Quant Worker process with persisted run/stage context and resource limits.

**Tech Stack:** Python 3.11/3.12 metadata, `uv.lock`, architecture tests, Markdown ADR/evidence docs, existing `PersistentTaskBackend` and `Run/Stage/Event` boundaries.

---

### Task 1: Red Architecture Tests

**Files:**
- Create: `tests/architecture/test_qlib_version_isolation.py`
- Read: `pyproject.toml`
- Read: `uv.lock`
- Read: `requirements.txt`

- [ ] **Step 1: Write the failing test**

```python
def test_quant_extra_pins_pyqlib_exactly_and_keeps_production_surface_clean() -> None:
    project = load_pyproject()["project"]
    quant_deps = project["optional-dependencies"]["quant"]
    assert "pyqlib==0.9.7" in quant_deps
    assert "pyqlib==" not in REQUIREMENTS.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/architecture/test_qlib_version_isolation.py -q`

Expected: FAIL because the test file, Qlib docs, policy module, and exact pin do not exist yet.

### Task 2: Dependency Lock Surface

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Preserve: `requirements.txt`

- [ ] **Step 1: Pin pyqlib exactly**

Change the quant extra from range/marker form to:

```toml
"pyqlib==0.9.7",
```

- [ ] **Step 2: Refresh the lock**

Run: `uv lock`

Expected: lock resolves successfully and `uv.lock` keeps `pyqlib` at `0.9.7`.

- [ ] **Step 3: Verify production export remains clean**

Run: `scripts/verify-python-dependency-lock.sh`

Expected: PASS and `requirements.txt` still excludes `pyqlib`.

### Task 3: Qlib Runtime Policy

**Files:**
- Create: `src/serenity_alpha_lab/integrations/qlib/__init__.py`
- Create: `src/serenity_alpha_lab/integrations/qlib/runtime_policy.py`

- [ ] **Step 1: Add policy constants and DTO**

Implement a frozen `QlibRuntimeIsolationPolicy` with:

```python
package_name = "pyqlib"
package_version = "0.9.7"
scope = "quant_worker_only"
queue_name = "worker-quant"
process_isolation = "dedicated_process"
forbid_fastapi_initialization = True
forbid_runtime_import_at_module_import = True
requires_run_stage_context = True
allow_arbitrary_module_path = False
```

- [ ] **Step 2: Add default resource limits**

Include conservative defaults:

```python
max_cpu_cores = 2
max_memory_mb = 4096
wall_clock_timeout_seconds = 3600
heartbeat_interval_seconds = 15
checkpoint_interval_seconds = 300
```

- [ ] **Step 3: Ensure no runtime import**

Do not import `qlib`, `pyqlib`, FastAPI, SQLAlchemy, application services, repositories, or Worker loops in this module.

### Task 4: Evidence Docs And ADR

**Files:**
- Create: `docs/qlib-version-isolation.md`
- Create: `docs/adr/ADR-009-qlib-adapter-boundary-and-version-upgrade-strategy.md`

- [ ] **Step 1: Document version and license evidence**

Record:

```yaml
task: SAL-P4-005
package_name: pyqlib
locked_version: 0.9.7
license_spdx: MIT
requires_python: ">=3.8.0"
approved_python: ">=3.11,<3.13"
production_requirements_contains_pyqlib: false
```

- [ ] **Step 2: Document platform and dependency evidence**

List supported local/worker targets from wheel metadata: macOS universal2, manylinux2014 x86_64, Windows amd64 for CPython 3.11/3.12. Record the direct runtime dependencies from PyPI metadata and note that production Qlib Worker images are Linux x86_64 only until later platform validation expands support.

- [ ] **Step 3: Document worker isolation**

State that Qlib cannot initialize in FastAPI, domain, application, dataset, provider, or report paths. Later `SAL-P4-006`/`SAL-P4-007` may consume the policy but may not accept arbitrary module paths.

- [ ] **Step 4: Document upgrade and stop-use conditions**

Require lock refresh, license review, SCA/SBOM, fixed-data golden comparison, artifact hash review, and worker resource regression checks before any Qlib upgrade.

### Task 5: Status And Verification

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Update task state**

Mark `SAL-P4-005` as `DONE`, set P4 progress to `5/22`, total progress to `71/129`, register `DEC-069` and `AEV-071`, and make `SAL-P4-006` `READY`.

- [ ] **Step 2: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/architecture/test_qlib_version_isolation.py -q
uv run --extra core --extra dev python -m pytest tests/architecture/test_qlib_version_isolation.py tests/architecture/test_dependency_locking.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all pass, immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, and no Qlib runtime is started.

- [ ] **Step 3: Commit**

Stage only SAL-P4-005 files and commit:

```bash
git commit -m "feat(P4): 锁定 Qlib 版本与隔离方案"
```
