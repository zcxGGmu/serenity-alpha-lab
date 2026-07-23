# AlphaSift Wheel Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-002` by building a reproducible offline AlphaSift wheel intake and committing auditable manifest, SBOM, license inventory, and internal artifact reference evidence.

**Architecture:** Keep the wheel binary out of Git and place it under `.cache/alphasift-wheel-intake/wheelhouse`. Commit only the deterministic intake script and evidence files under `docs/baselines/alphasift-wheel-intake/`, plus a human review doc. Use the locked codeload source archive, fixed `SOURCE_DATE_EPOCH`, and no production `git+https` dependency.

**Tech Stack:** Bash, `uv build`, Python stdlib `zipfile` / `importlib.metadata`, CycloneDX JSON, pytest architecture tests.

---

### Task 1: Evidence Contract

**Files:**
- Create: `tests/architecture/test_alphasift_wheel_intake.py`
- Modify: `tasks/todo.md`

- [x] **Step 1: Write the failing test**

Add tests that require `scripts/build-alphasift-wheel-intake.sh`, `docs/alphasift-wheel-intake.md`, `docs/baselines/alphasift-wheel-intake/intake-manifest.json`, `sbom-cyclonedx.json`, `license-inventory.csv`, `license-summary.md`, and `alphasift-wheel.sha256`.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_wheel_intake.py -q`
Expected: FAIL because the intake script and evidence files do not exist yet.

### Task 2: Intake Script

**Files:**
- Create: `scripts/build-alphasift-wheel-intake.sh`

- [x] **Step 1: Implement reproducible build script**

Build from `https://codeload.github.com/ZhuLinsen/alphasift/tar.gz/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, verify source SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, set `SOURCE_DATE_EPOCH=1783081838`, and run `uv build --wheel`.

- [x] **Step 2: Generate committed evidence**

Generate `intake-manifest.json`, `sbom-cyclonedx.json`, `license-inventory.csv`, `license-summary.md`, and `alphasift-wheel.sha256` from wheel metadata.

- [x] **Step 3: Verify offline install shape**

Run `uv pip install --no-index --find-links <wheelhouse> --no-deps --target <cache-target> alphasift==0.2.0` and record the result in the manifest.

### Task 3: Human Evidence And Status

**Files:**
- Create: `docs/alphasift-wheel-intake.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document wheel intake evidence**

Record the locked source commit, source archive hash, reproducible wheel hash, internal artifact URI, SBOM/license paths, offline install command, and explicit non-goals.

- [x] **Step 2: Update task and recovery status**

Mark only `SAL-P3-002` done, advance P3 to `2/17`, total to `51/129`, set `SAL-P3-003` as next READY, keep G3 not passed, and preserve all P3/G2 guardrails.

### Task 4: Verification And Commit

**Files:**
- Verify all modified files only

- [x] **Step 1: Run target and related tests**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_wheel_intake.py tests/architecture/test_alphasift_source_review.py tests/architecture/test_dependency_locking.py -q
```

- [x] **Step 2: Run final checks**

Run full pytest, compileall, dependency lock guard, `git diff --check`, immutable tag check, and Git status review.

- [x] **Step 3: Commit**

Stage only `SAL-P3-002` files and commit with a Chinese checkpoint message.
