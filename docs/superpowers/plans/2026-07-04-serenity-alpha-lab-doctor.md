# Doctor Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `doctor` command that checks whether the local product inputs are present and usable before a user runs the memo-pack pipeline.

**Architecture:** Reuse the same default input paths as `run-cpo-pack`, but keep the command read-only. `doctor` validates required base/SEC/official files, reports optional manual intake status, and exits non-zero with a clear stderr message when required files are missing.

**Tech Stack:** Python 3, argparse-style CLI dispatch, pytest, existing CLI preflight helpers.

---

## Files

- Modify: `tests/test_cli.py`
  - Add tests for successful and failing `doctor` runs.
- Modify: `src/serenity_alpha_lab/cli.py`
  - Add `build_doctor_parser()`.
  - Add `doctor` dispatch branch.
  - Add `_print_doctor_status()` helper.
- Modify: `README.md`
  - Document the health-check command in Quick Start.
- Modify: `docs/OPERATIONS.md`
  - Add operational guidance for `doctor`.
- Modify: `tasks/todo.md`
  - Track red/green/product verification and review notes.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append:

```markdown
# Serenity Alpha Lab Doctor Command Phase

- [ ] Create doctor command implementation plan.
- [ ] Add failing doctor CLI tests.
- [ ] Implement doctor command.
- [ ] Update user-facing docs.
- [ ] Run product verification.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Doctor Command Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing CLI Tests

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write successful doctor test**

Add a test that runs:

```python
exit_code = main([
    "doctor",
    "--base-data", str(FIXTURE),
    "--sec-sources", str(SEC_COMPANYFACTS_SOURCES),
    "--official-sources", str(OFFICIAL_REPORT_SOURCES),
    "--manual-data", str(tmp_path / "missing-optional-manual.jsonl"),
])
```

Assert:

- exit code is `0`
- stdout contains `Serenity Alpha Lab doctor`
- stdout contains `required inputs: ok`
- stdout contains `optional manual intake: missing`

- [ ] **Step 2: Write failing doctor test**

Add a test that passes missing base, SEC, and official paths.

Assert:

- exit code is `2`
- stderr contains `Missing required input file`
- stderr lists all missing paths

- [ ] **Step 3: Run tests to verify failure**

Run: `python3 -m pytest tests/test_cli.py::test_cli_doctor_reports_ok_when_required_inputs_exist tests/test_cli.py::test_cli_doctor_reports_missing_required_inputs -q`

Expected: FAIL because `doctor` is not recognized yet.

### Task 3: Implement Doctor Command

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add parser**

Add `build_doctor_parser()` with:

- positional `doctor`
- `--base-data`, same default as `run-cpo-pack`
- `--sec-sources`, same default as `run-cpo-pack`
- `--official-sources`, same default as `run-cpo-pack`
- `--manual-data`, optional list defaulting to guarded manual intake

- [ ] **Step 2: Add status helper**

Implement:

```python
def _print_doctor_status(required_paths: Sequence[str | Path], optional_paths: Sequence[str | Path]) -> None:
    optional_missing = _missing_paths(optional_paths)
    print("Serenity Alpha Lab doctor")
    print("required inputs: ok")
    if optional_missing:
        print("optional manual intake: missing")
        for path in optional_missing:
            print(f"- {path}")
    else:
        print("optional manual intake: ok")
```

- [ ] **Step 3: Add dispatch branch**

Before `run-cpo-pack`:

```python
if args_list and args_list[0] == "doctor":
    args = build_doctor_parser().parse_args(args_list)
    required_paths = [*args.base_data, args.sec_sources, args.official_sources]
    preflight_exit = _preflight_required_paths(required_paths)
    if preflight_exit:
        return preflight_exit
    _print_doctor_status(required_paths, args.manual_data)
    return 0
```

- [ ] **Step 4: Run target tests**

Run: `python3 -m pytest tests/test_cli.py::test_cli_doctor_reports_ok_when_required_inputs_exist tests/test_cli.py::test_cli_doctor_reports_missing_required_inputs -q`

Expected: both pass.

### Task 4: Document And Verify

**Files:**
- Modify: `README.md`
- Modify: `docs/OPERATIONS.md`

- [ ] **Step 1: Update docs**

Add `doctor` before `run-cpo-pack` in Quick Start and Operations.

- [ ] **Step 2: Run product command**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor && PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack`

Expected: doctor reports required inputs ok; product run reports `combined 182 evidence items; ready memos 6; skipped 0`.

- [ ] **Step 3: Run full suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update all phase checklist items to `[x]`.

- [ ] **Step 2: Append review notes**

Record red test result, target green result, product doctor/run result, and full suite result.
