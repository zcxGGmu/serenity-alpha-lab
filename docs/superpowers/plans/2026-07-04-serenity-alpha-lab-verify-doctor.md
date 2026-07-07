# Verify Doctor Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the release verification command include the read-only `doctor` health check before generating product outputs.

**Architecture:** The Makefile already provides `test`, `run-cpo-pack`, `verify`, and `clean-pack`. Add a dedicated `doctor` target that runs the CLI health check, then make `verify` depend on `test doctor run-cpo-pack` so users get tests, environment/input validation, and product generation in one command.

**Tech Stack:** Make, Python CLI, pytest release-hardening tests.

---

## Files

- Modify: `tests/test_release_hardening.py`
  - Assert `doctor:` exists and `verify` depends on `test doctor run-cpo-pack`.
- Modify: `Makefile`
  - Add `doctor` to `.PHONY`.
  - Add `doctor` target.
  - Update `verify` dependency order.
- Modify: `docs/OPERATIONS.md`
  - Include `make doctor` in the make target list.
- Modify: `tasks/todo.md`
  - Track red/green/product verification for this phase.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append:

```markdown
# Serenity Alpha Lab Verify Doctor Phase

- [ ] Create verify doctor implementation plan.
- [ ] Add failing release hardening test for Makefile doctor target.
- [ ] Add Makefile doctor target and verify dependency.
- [ ] Update operations docs.
- [ ] Run release verification.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Verify Doctor Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing Release Test

**Files:**
- Modify: `tests/test_release_hardening.py`

- [ ] **Step 1: Add assertions**

Update `test_release_makefile_exposes_standard_targets()` to assert:

```python
assert "doctor:" in makefile
assert "verify: test doctor run-cpo-pack" in makefile
assert "serenity_alpha_lab.cli doctor" in makefile
```

- [ ] **Step 2: Run test to verify failure**

Run: `python3 -m pytest tests/test_release_hardening.py::test_release_makefile_exposes_standard_targets -q`

Expected: FAIL because Makefile does not expose `doctor` yet.

### Task 3: Implement Makefile Integration

**Files:**
- Modify: `Makefile`
- Modify: `docs/OPERATIONS.md`

- [ ] **Step 1: Update Makefile**

Change:

```make
.PHONY: test run-cpo-pack verify clean-pack
```

to:

```make
.PHONY: test doctor run-cpo-pack verify clean-pack
```

Add:

```make
doctor:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
```

Change:

```make
verify: test run-cpo-pack
```

to:

```make
verify: test doctor run-cpo-pack
```

- [ ] **Step 2: Update operations guide**

Add `make doctor` to the Make Targets block.

- [ ] **Step 3: Run target test**

Run: `python3 -m pytest tests/test_release_hardening.py::test_release_makefile_exposes_standard_targets -q`

Expected: PASS.

### Task 4: Verify Release Path

**Files:**
- Generated: `output/reports/cpo-readiness-guarded.md`
- Generated: `output/packs/cpo-guarded/*.md`

- [ ] **Step 1: Run release command**

Run: `make verify`

Expected: tests pass, doctor reports required inputs ok, product run reports `combined 182 evidence items; ready memos 6; skipped 0`.

- [ ] **Step 2: Run full suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update every phase checklist item to `[x]`.

- [ ] **Step 2: Append review notes**

Record red test result, target green result, `make verify` result, and full suite result.
