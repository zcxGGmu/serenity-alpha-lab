# AlphaSift Source Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-001` by locking the AlphaSift source commit, license attribution, dependency surface, vulnerability review, known limitations, and replacement/stop-use conditions.

**Architecture:** This is a security and provenance checkpoint only. It creates auditable documentation and a lightweight regression test that prevents future P3 work from losing the locked source decision or accidentally treating AlphaSift as Quant Core/backtesting/evidence infrastructure.

**Tech Stack:** Markdown evidence, pytest doc assertions, GitHub API/codeload source metadata, `uvx pip-audit`, existing P0/P1/P2 dependency and Gate records.

---

### Task 1: Review Evidence Contract

**Files:**
- Create: `tests/architecture/test_alphasift_source_review.py`
- Create: `docs/alphasift-source-review.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Record task plan in `tasks/todo.md`**

Add a new top-level `SAL-P3-001 AlphaSift Source Review Plan` section with guardrails, evidence sources, verification commands, and a review block.

- [x] **Step 2: Write the failing doc test**

Create `tests/architecture/test_alphasift_source_review.py` that requires:

```python
LOCKED_COMMIT = "9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf"
SOURCE_ARCHIVE_SHA256 = "4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a"
```

The test must assert the review document includes the locked commit, source archive hash, Apache-2.0 SPDX attribution, runtime dependency list, pip-audit result, known limitations, replacement conditions, stop-use conditions, and explicit P3 non-goals.

- [x] **Step 3: Run target test to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_source_review.py -q`

Expected: FAIL because `docs/alphasift-source-review.md` does not exist yet.

### Task 2: AlphaSift Review Document

**Files:**
- Create: `docs/alphasift-source-review.md`
- Modify: `tests/architecture/test_alphasift_source_review.py` only if the evidence contract needs clearer labels

- [x] **Step 1: Lock upstream source decision**

Document the selected source as `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, default branch `main`, latest commit date `2026-07-03T12:30:38Z`, source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, and note that `v0.2.0` tag points to older commit `f2c2ca22ae3fcb18b0273b8494a9e055d82c01e0`.

- [x] **Step 2: Document license and dependency surface**

Record Apache-2.0 license attribution, `LICENSE` file inclusion, `pyproject.toml` version `0.2.0`, Python `>=3.10`, runtime dependencies, and dev dependencies.

- [x] **Step 3: Document security and maintenance review**

Record `uvx --python 3.11 --from pip-audit pip-audit --requirement <requirements> --format json` result `0 known vulnerabilities` for the current resolved dependency surface, plus limitations: AlphaSift itself is not on PyPI, range dependencies are not release locks, and the result is not a release SBOM.

- [x] **Step 4: Document platform limitations and boundaries**

Record that AlphaSift is accepted only as an L1 snapshot/candidate screening plugin; it may not replace Dataset Catalog, PIT Dataset, Provider Policy, Quant Core, formal backtesting, Evidence Agent, or real Provider/LLM guarded execution.

- [x] **Step 5: Run target test to verify Green**

Run: `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_source_review.py -q`

Expected: PASS.

### Task 3: Status, Evidence, and Checkpoint

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Update progress checklist**

Mark `SAL-P3-001` DONE, set P3 progress to `1/17`, total progress to `50/129`, set `SAL-P3-002` READY, and add `DEC-048` plus `AEV-050`.

- [x] **Step 2: Update development status and next prompt**

Set current executable task to `SAL-P3-002`, summarize AlphaSift review evidence, keep Gate G3 pending, and update the copyable next-start prompt.

- [x] **Step 3: Complete review block**

Record evidence, verification outputs, scope retained, and remaining accepted risks in `tasks/todo.md`.

- [x] **Step 4: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_source_review.py tests/architecture/test_dependency_locking.py -q
uv run --extra core --extra dev python -m compileall src tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

- [x] **Step 5: Commit**

Stage only `SAL-P3-001` files and commit with a Chinese message. Checkpoint: 本文件所在提交，标题为 `docs(P3): 完成 AlphaSift 源码审查与锁定`。
