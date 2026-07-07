# Install Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the post-install user path explicit and verifiable with a smoke command.

**Architecture:** Keep installation local and editable for now. Add `INSTALL.md` for a clean setup path, add a `smoke` Makefile target that exercises the installed console script (`serenity-alpha-lab doctor` and `serenity-alpha-lab run-cpo-pack`), and test those release-facing artifacts so future changes cannot silently break the handoff path.

**Tech Stack:** Markdown install docs, Makefile, pytest release-hardening tests, existing console script entrypoint.

---

## Files

- Create: `INSTALL.md`
  - Document Python version, editable install, smoke test, and fallback `PYTHONPATH=src` commands.
- Modify: `Makefile`
  - Add `smoke` target using installed `serenity-alpha-lab` console command.
- Modify: `.github/workflows/verify.yml`
  - Run `make smoke` before `make verify`.
- Modify: `tests/test_release_hardening.py`
  - Assert install docs and smoke target exist.
- Modify: `README.md`
  - Link `INSTALL.md` from Quick Start / stable run area.
- Modify: `tasks/todo.md`
  - Track red/green/release verification and review notes.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append:

```markdown
# Serenity Alpha Lab Install Smoke Phase

- [ ] Create install smoke implementation plan.
- [ ] Add failing install and smoke tests.
- [ ] Create install docs and smoke target.
- [ ] Run smoke and release verification.
- [ ] Record review.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Install Smoke Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing Release Tests

**Files:**
- Modify: `tests/test_release_hardening.py`

- [ ] **Step 1: Add install doc test**

Assert `INSTALL.md` contains:

- `# Install`
- `python3 -m pip install -e .`
- `serenity-alpha-lab doctor`
- `serenity-alpha-lab run-cpo-pack`
- `make smoke`

- [ ] **Step 2: Add smoke target assertions**

Update Makefile test to assert:

- `smoke:` exists
- `.PHONY` includes `smoke`
- `serenity-alpha-lab doctor` appears
- `serenity-alpha-lab run-cpo-pack` appears

- [ ] **Step 3: Add CI smoke assertion**

Update CI workflow test to assert `make smoke` appears.

- [ ] **Step 4: Run red tests**

Run: `python3 -m pytest tests/test_release_hardening.py -q`

Expected: FAIL because `INSTALL.md`, `make smoke`, and CI smoke are not present yet.

### Task 3: Implement Install Smoke Path

**Files:**
- Create: `INSTALL.md`
- Modify: `Makefile`
- Modify: `.github/workflows/verify.yml`
- Modify: `README.md`

- [ ] **Step 1: Create install docs**

Document editable install:

```bash
python3 -m pip install -e .
make smoke
make verify
```

Also include fallback non-installed commands:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack
```

- [ ] **Step 2: Add smoke target**

Add:

```make
smoke:
	serenity-alpha-lab doctor
	serenity-alpha-lab run-cpo-pack
```

- [ ] **Step 3: Add CI smoke step**

Add a workflow step before `make verify`:

```yaml
- name: Install package
  run: python -m pip install -e .

- name: Run installed smoke test
  run: make smoke
```

- [ ] **Step 4: Run target tests**

Run: `python3 -m pytest tests/test_release_hardening.py -q`

Expected: all release hardening tests pass.

### Task 4: Verify Smoke And Release

**Files:**
- Generated: `data/enriched/github_plus_primary.jsonl`
- Generated: `output/reports/cpo-readiness-guarded.md`
- Generated: `output/packs/cpo-guarded/*.md`

- [ ] **Step 1: Install editable package**

Run: `python3 -m pip install -e .`

Expected: install succeeds.

- [ ] **Step 2: Run smoke**

Run: `make smoke`

Expected: installed console script reports `required inputs: ok` and `ready memos 6; skipped 0`.

- [ ] **Step 3: Run release gate**

Run: `make verify`

Expected: tests pass, doctor passes, product run passes.

- [ ] **Step 4: Run full suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update all phase checklist items to `[x]`.

- [ ] **Step 2: Append review notes**

Record red test result, target green result, install result, smoke result, `make verify` result, and final full suite result.
