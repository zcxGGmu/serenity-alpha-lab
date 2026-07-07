# Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Serenity Alpha Lab easier and safer for another user to install, run, verify, and operate repeatedly.

**Architecture:** Add release-facing command surfaces (`project.scripts`, `Makefile`, `docs/OPERATIONS.md`) and make memo-pack output writes clean stale generated files before writing fresh outputs.

**Tech Stack:** Python packaging metadata, Makefile, markdown operations docs, pytest.

---

### Task 1: Add Release Hardening Tests

**Files:**
- Create: `tests/test_release_hardening.py`
- Modify: `tests/test_memo_pack.py`

- [ ] **Step 1: Write failing release metadata test**

Assert `pyproject.toml` contains:

```toml
[project.scripts]
serenity-alpha-lab = "serenity_alpha_lab.cli:main"
```

- [ ] **Step 2: Write failing Makefile/docs test**

Assert `Makefile` contains `run-cpo-pack` and `test`, and `docs/OPERATIONS.md` contains `run-cpo-pack`, `output/packs/cpo-guarded`, and `python3 -m pytest tests -q`.

- [ ] **Step 3: Write failing stale-output test**

Create `tmp_path / "stale-memo.md"`, call `write_memo_pack(pack, tmp_path)`, and assert the stale memo is removed while `index.md` and `sources.md` are written.

- [ ] **Step 4: Run red check**

Run:

```bash
python3 -m pytest tests/test_release_hardening.py tests/test_memo_pack.py::test_write_memo_pack_removes_stale_generated_memos -q
```

Expected: FAIL because release metadata/docs do not exist and stale memo cleanup is not implemented.

### Task 2: Implement Release Surface

**Files:**
- Modify: `pyproject.toml`
- Create: `Makefile`
- Create: `docs/OPERATIONS.md`
- Modify: `src/serenity_alpha_lab/memo_pack.py`

- [ ] **Step 1: Add console script**

Add:

```toml
[project.scripts]
serenity-alpha-lab = "serenity_alpha_lab.cli:main"
```

- [ ] **Step 2: Add Makefile**

Create targets:
- `test`
- `run-cpo-pack`
- `verify`
- `clean-pack`

- [ ] **Step 3: Add operations guide**

Document prerequisites, one-command run, expected outputs, verification, evidence refresh inputs, and troubleshooting.

- [ ] **Step 4: Clean stale generated pack files**

Before writing a pack, remove `*-memo.md`, `index.md`, and `sources.md` in the output directory.

- [ ] **Step 5: Run target tests**

Run:

```bash
python3 -m pytest tests/test_release_hardening.py tests/test_memo_pack.py::test_write_memo_pack_removes_stale_generated_memos -q
```

Expected: PASS.

### Task 3: Verify Product Run

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run default product command**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack
```

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.
