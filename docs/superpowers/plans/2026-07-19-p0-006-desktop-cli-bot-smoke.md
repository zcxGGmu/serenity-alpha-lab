# SAL-P0-006 Desktop CLI Bot Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the P0 Desktop, CLI, and Bot smoke baseline for the locked DSA `v3.26.1` baseline without starting P1 or Quant Core work.

**Architecture:** This task is a baseline evidence task. It uses the existing DSA isolated worktree and bootstrap scripts, inspects upstream entrypoints, runs safe smoke commands where possible, and records pass/fail/blocked evidence in project documentation. It does not modify DSA upstream source.

**Tech Stack:** Git worktree, Bash/PowerShell bootstrap scripts, Node/npm for Desktop, Python for CLI/Bot entrypoints, Markdown evidence docs.

---

### Task 1: Baseline Materialization

**Files:**
- Modify: `tasks/todo.md`
- Read: `scripts/bootstrap-dsa-baseline.sh`
- Read: `scripts/bootstrap-dsa-baseline.ps1`
- Output: terminal verification evidence

- [x] **Step 1: Confirm current branch and untracked generated files**

Run: `git status --short --branch`

Expected: current branch is `codex/p0-baseline-status`; generated untracked directories may exist but must not be committed.

- [x] **Step 2: Confirm DSA baseline ref availability**

Run: `git rev-parse upstream/dsa-v3.26.1`

Expected: resolves to `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`. If missing, add/fetch `upstream` remote and recreate the local immutable baseline tag.

- [x] **Step 3: Materialize locked DSA worktree**

Run: `bash scripts/bootstrap-dsa-baseline.sh --validate-only`

Expected: validates the baseline tag. If the worktree does not exist, run `bash scripts/bootstrap-dsa-baseline.sh`.

### Task 2: Entrypoint Discovery

**Files:**
- Read: `.worktrees/dsa-v3.26.1/pyproject.toml`
- Read: `.worktrees/dsa-v3.26.1/package.json` if present
- Read: `.worktrees/dsa-v3.26.1/apps/dsa-desktop/package.json`
- Read: DSA CLI and bot source files discovered by `rg`

- [x] **Step 1: Inspect Desktop scripts**

Run: `cat .worktrees/dsa-v3.26.1/apps/dsa-desktop/package.json`

Expected: identify install/build/dev/smoke-capable commands and required environment.

- [x] **Step 2: Inspect CLI entrypoints**

Run: `rg -n "argparse|click|typer|if __name__ == .__main__.|console_scripts|entry_points" .worktrees/dsa-v3.26.1`

Expected: identify an offline-safe CLI command or classify dependency blockers.

- [x] **Step 3: Inspect Bot command entrypoints**

Run: `rg -n "bot|telegram|discord|command|slash|webhook" .worktrees/dsa-v3.26.1/src .worktrees/dsa-v3.26.1/bot .worktrees/dsa-v3.26.1/api 2>/dev/null`

Expected: identify at least one offline/stub-safe bot command path or classify blockers.

### Task 3: Smoke Execution and Classification

**Files:**
- Create: `docs/desktop-cli-bot-smoke-baseline.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Run Desktop dependency/bootstrap smoke if feasible**

Run: `bash scripts/bootstrap-dsa-baseline.sh --install-desktop`

Expected: `npm ci` succeeds for `apps/dsa-desktop`, or failure is recorded with exact blocker.

- [x] **Step 2: Run Desktop non-GUI validation if available**

Run the safest script discovered in Task 2, such as `npm run lint`, `npm run build`, or `npm run test`.

Expected: command succeeds, or missing script/GUI/runtime constraint is recorded.

- [x] **Step 3: Run CLI offline smoke if feasible**

Run the safest command discovered in Task 2, preferring help/version/stub commands that do not call real providers.

Expected: command succeeds without real secrets or network, or dependency blocker is recorded.

- [x] **Step 4: Run Bot offline smoke if feasible**

Run the safest bot command dispatch/help/stub path discovered in Task 2.

Expected: command succeeds without real secrets or network, or blocker is recorded.

### Task 4: Documentation and Status Update

**Files:**
- Create: `docs/desktop-cli-bot-smoke-baseline.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Write evidence document**

Record environment, DSA SHA, commands, outputs summary, pass/fail/blocked status, and non-goals.

- [x] **Step 2: Update progress checklist**

Set `SAL-P0-006` to `DONE` only if all acceptance criteria passed; otherwise set `BLOCKED` with concrete blocker and unblock conditions.

- [x] **Step 3: Update development status**

Update current task, completed/blocked sections, next steps, risks if needed, and recovery prompt.

- [x] **Step 4: Mark `tasks/todo.md` checklist truthfully**

Mark only completed checklist items as checked.

### Task 5: Verification and Checkpoint

**Files:**
- Read/verify all modified documentation
- Commit only reviewable project files

- [x] **Step 1: Verify docs and status**

Run: `git diff --check && git diff -- docs/development-status.md docs/development-progress-checklist.md docs/desktop-cli-bot-smoke-baseline.md tasks/todo.md`

Expected: no whitespace errors and changes match evidence.

- [x] **Step 2: Confirm generated files are not staged**

Run: `git status --short`

Expected: only intentional docs/task files are staged before commit.

- [x] **Step 3: Create checkpoint commit**

Run: `git add tasks/todo.md docs/desktop-cli-bot-smoke-baseline.md docs/development-progress-checklist.md docs/development-status.md docs/superpowers/plans/2026-07-19-p0-006-desktop-cli-bot-smoke.md && git commit -m "docs(P0): 记录 Desktop CLI Bot smoke 基线"`

Expected: commit succeeds with a Chinese message and generated files remain untracked/ignored.
