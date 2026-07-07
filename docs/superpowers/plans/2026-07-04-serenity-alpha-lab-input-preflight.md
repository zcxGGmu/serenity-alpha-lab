# Input Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `run-cpo-pack` fail fast with a clear product-grade error when required local input files are missing.

**Architecture:** The default product run depends on base evidence, SEC source manifest, and official report source manifest. Add a small CLI preflight helper that validates those required paths before any output is written. Keep guarded manual intake optional because a new installation may not have manual rows yet.

**Tech Stack:** Python 3, argparse-style CLI function, pytest, existing `main()` command dispatch.

---

## Files

- Modify: `tests/test_cli.py`
  - Add a regression test for missing required `run-cpo-pack` input files.
- Modify: `src/serenity_alpha_lab/cli.py`
  - Add `_missing_paths()` and `_preflight_required_paths()` helpers.
  - Call preflight at the start of `run-cpo-pack`.
- Modify: `tasks/todo.md`
  - Track red/green/product verification and review notes for this phase.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append this section:

```markdown
# Serenity Alpha Lab Input Preflight Phase

- [ ] Create input preflight implementation plan.
- [ ] Add failing run-cpo-pack missing input test.
- [ ] Implement required input preflight.
- [ ] Regenerate product outputs.
- [ ] Run full verification.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Input Preflight Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing CLI Test

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add a test that calls:

```python
exit_code = main([
    "run-cpo-pack",
    "--base-data", str(tmp_path / "missing-base.jsonl"),
    "--sec-sources", str(tmp_path / "missing-sec.json"),
    "--official-sources", str(tmp_path / "missing-official.json"),
    "--combined-out", str(tmp_path / "combined.jsonl"),
    "--readiness-out", str(tmp_path / "readiness.md"),
    "--pack-out-dir", str(tmp_path / "pack"),
])
```

Assert:

- exit code is `2`
- stderr contains `Missing required input file`
- stderr lists all three missing paths
- no combined output, readiness output, or pack directory was created

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_fast_when_required_inputs_are_missing -q`

Expected: FAIL because current `run-cpo-pack` raises from lower-level file loading instead of returning a controlled product error.

### Task 3: Implement Required Input Preflight

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add helpers near parser builders**

Implement:

```python
def _missing_paths(paths: Sequence[str | Path]) -> list[Path]:
    return [Path(path) for path in paths if not Path(path).exists()]

def _preflight_required_paths(paths: Sequence[str | Path]) -> int:
    missing = _missing_paths(paths)
    if not missing:
        return 0
    print("Missing required input file(s):", file=sys.stderr)
    for path in missing:
        print(f"- {path}", file=sys.stderr)
    return 2
```

- [ ] **Step 2: Call preflight before loading data**

At the top of the `run-cpo-pack` branch, after parsing args:

```python
preflight_exit = _preflight_required_paths([*args.base_data, args.sec_sources, args.official_sources])
if preflight_exit:
    return preflight_exit
```

Do not include `manual_data` because it is optional and already loaded only when present.

- [ ] **Step 3: Run targeted CLI tests**

Run: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_fast_when_required_inputs_are_missing tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q`

Expected: both tests pass.

### Task 4: Regenerate And Verify

**Files:**
- Generated: `data/enriched/github_plus_primary.jsonl`
- Generated: `output/reports/cpo-readiness-guarded.md`
- Generated: `output/packs/cpo-guarded/*.md`

- [ ] **Step 1: Run product pipeline**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack`

Expected: `combined 182 evidence items; ready memos 6; skipped 0`.

- [ ] **Step 2: Run full suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update every checklist item to `[x]`.

- [ ] **Step 2: Append review notes**

Record:

- Red test command and failure reason.
- Target green test command.
- Product run result.
- Full suite result.
