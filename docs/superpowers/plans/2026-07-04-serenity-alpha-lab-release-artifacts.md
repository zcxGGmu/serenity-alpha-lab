# Release Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add release-facing artifacts that make the project easier for another user or CI runner to validate and operate.

**Architecture:** Keep the product local-first and dependency-light. Add documentation-only release artifacts plus a GitHub Actions workflow that runs the existing `make verify` release gate. Test those files directly so future edits cannot silently remove the release path.

**Tech Stack:** Markdown release docs, GitHub Actions YAML, Makefile release gate, pytest release-hardening tests.

---

## Files

- Create: `CHANGELOG.md`
  - Record the first productized release state and major hardening improvements.
- Create: `docs/RELEASE_CHECKLIST.md`
  - Define the manual release checklist around `make verify`, output inspection, and research-only safety.
- Create: `.github/workflows/verify.yml`
  - Run the release gate on pushes and pull requests.
- Modify: `tests/test_release_hardening.py`
  - Assert release artifacts exist and point to `make verify`.
- Modify: `README.md`
  - Link to the release checklist and changelog from the stable run section.
- Modify: `tasks/todo.md`
  - Track red/green/release verification and review notes.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append:

```markdown
# Serenity Alpha Lab Release Artifacts Phase

- [ ] Create release artifacts implementation plan.
- [ ] Add failing release artifact tests.
- [ ] Create changelog, release checklist, and CI workflow.
- [ ] Update README release links.
- [ ] Run release verification.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Release Artifacts Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing Release Tests

**Files:**
- Modify: `tests/test_release_hardening.py`

- [ ] **Step 1: Add changelog test**

Add a test that reads `CHANGELOG.md` and asserts it contains:

- `# Changelog`
- `## 0.1.0`
- `run-cpo-pack`
- `doctor`
- `make verify`

- [ ] **Step 2: Add release checklist test**

Add a test that reads `docs/RELEASE_CHECKLIST.md` and asserts it contains:

- `# Release Checklist`
- `make verify`
- `output/packs/cpo-guarded/index.md`
- `output/packs/cpo-guarded/sources.md`
- `research only`

- [ ] **Step 3: Add CI workflow test**

Add a test that reads `.github/workflows/verify.yml` and asserts it contains:

- `name: Verify`
- `python-version: "3.9"`
- `make verify`

- [ ] **Step 4: Run red tests**

Run: `python3 -m pytest tests/test_release_hardening.py -q`

Expected: FAIL because the release artifact files do not exist yet.

### Task 3: Create Release Artifacts

**Files:**
- Create: `CHANGELOG.md`
- Create: `docs/RELEASE_CHECKLIST.md`
- Create: `.github/workflows/verify.yml`
- Modify: `README.md`

- [ ] **Step 1: Write changelog**

Create `CHANGELOG.md` with a `0.1.0` section covering:

- local-first CPO memo pack
- `doctor`
- `run-cpo-pack`
- `make verify`
- provenance and source excerpt rendering
- skipped memo quality gate

- [ ] **Step 2: Write release checklist**

Create `docs/RELEASE_CHECKLIST.md` with these checks:

- run `make verify`
- confirm six default memos are generated
- inspect `index.md`
- inspect `sources.md`
- keep research-only disclaimer

- [ ] **Step 3: Write CI workflow**

Create `.github/workflows/verify.yml` with Python 3.9 and `make verify`.

- [ ] **Step 4: Update README links**

Add links to `CHANGELOG.md` and `docs/RELEASE_CHECKLIST.md` near the Stable Product Run section.

- [ ] **Step 5: Run target tests**

Run: `python3 -m pytest tests/test_release_hardening.py -q`

Expected: all release hardening tests pass.

### Task 4: Verify Release Path

**Files:**
- Generated: `data/enriched/github_plus_primary.jsonl`
- Generated: `output/reports/cpo-readiness-guarded.md`
- Generated: `output/packs/cpo-guarded/*.md`

- [ ] **Step 1: Run release gate**

Run: `make verify`

Expected: tests pass, `doctor` reports required inputs ok, and `run-cpo-pack` reports `combined 182 evidence items; ready memos 6; skipped 0`.

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
