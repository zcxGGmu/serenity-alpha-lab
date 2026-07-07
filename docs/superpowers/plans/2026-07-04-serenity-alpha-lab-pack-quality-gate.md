# Pack Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make product runs fail when requested ticker candidates are skipped, so a generated pack cannot look successful while missing expected memos.

**Architecture:** `run-cpo-pack` already builds readiness and memo pack artifacts. Keep writing diagnostic outputs, then return a non-zero exit code when `pack.skipped` is non-empty unless the caller explicitly allows skipped candidates. This preserves useful reports for debugging while making CI/release verification enforce complete product output.

**Tech Stack:** Python 3, existing CLI dispatcher, pytest, memo-pack readiness model.

---

## Files

- Modify: `tests/test_cli.py`
  - Add a failing `run-cpo-pack` regression test for skipped memo candidates.
  - Update the existing fixture-based product-output test to opt into skipped candidates because it intentionally uses a small fixture set.
- Modify: `src/serenity_alpha_lab/cli.py`
  - Add `--allow-skipped` to `run-cpo-pack`.
  - Return `3` and write skipped ticker details to stderr when skipped candidates exist and are not allowed.
- Modify: `tasks/todo.md`
  - Track red/green/release verification and review notes.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append:

```markdown
# Serenity Alpha Lab Pack Quality Gate Phase

- [ ] Create pack quality gate implementation plan.
- [ ] Add failing skipped-memo quality gate test.
- [ ] Implement run-cpo-pack skipped candidate gate.
- [ ] Run release verification.
- [ ] Record review.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Pack Quality Gate Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing CLI Test

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add skipped-candidate regression test**

Add a test that runs `run-cpo-pack` with the small fixture data, `SIVE` and `AAOI`, and no `--allow-skipped`.

Assert:

- exit code is `3`
- stderr contains `Skipped memo candidate(s)`
- stderr includes `AAOI`
- combined output, readiness report, and pack index are still written for debugging

- [ ] **Step 2: Update existing product-output fixture test**

Add `--allow-skipped` to `test_cli_run_cpo_pack_regenerates_product_outputs` because that test uses a deliberately small fixture and verifies output regeneration rather than release completeness.

- [ ] **Step 3: Run red test**

Run: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_when_candidates_are_skipped_without_override -q`

Expected: FAIL because `run-cpo-pack` currently returns `0` even with skipped candidates.

### Task 3: Implement Quality Gate

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add parser flag**

Add to `build_run_cpo_pack_parser()`:

```python
parser.add_argument(
    "--allow-skipped",
    action="store_true",
    help="Return success even when one or more ticker candidates are skipped.",
)
```

- [ ] **Step 2: Add quality gate after pack generation**

After the success summary print:

```python
if pack.skipped and not args.allow_skipped:
    print("Skipped memo candidate(s):", file=sys.stderr)
    for candidate in pack.skipped:
        flags = ", ".join(flag.code for flag in candidate.report.flags) or "none"
        print(f"- {candidate.ticker}: {candidate.status} ({flags})", file=sys.stderr)
    return 3
```

Keep the existing success path returning `0` when there are no skipped candidates.

- [ ] **Step 3: Run target tests**

Run: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_when_candidates_are_skipped_without_override tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q`

Expected: both pass.

### Task 4: Verify Release Path

**Files:**
- Generated: `data/enriched/github_plus_primary.jsonl`
- Generated: `output/reports/cpo-readiness-guarded.md`
- Generated: `output/packs/cpo-guarded/*.md`

- [ ] **Step 1: Run release verification**

Run: `make verify`

Expected: tests pass, `doctor` passes, and default product run returns `0` because all six default tickers are ready.

- [ ] **Step 2: Run full suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update all phase checklist items to `[x]`.

- [ ] **Step 2: Append review notes**

Record red test result, target green result, `make verify` result, and final full suite result.
