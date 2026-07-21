# DSA Provider Compatibility Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P2-002` by wrapping DSA `DataFetcherManager` daily-bar Pandas output behind the frozen Serenity `MarketDataProvider` contract.

**Architecture:** Add a narrow adapter under `integrations/dsa` that accepts an injected DSA-like manager for tests and optionally constructs the real DSA manager through the existing isolated worktree resolver. The adapter maps `InstrumentId` to DSA symbols, turns DataFrame rows into immutable `DataBatch` records with provenance, field lineage, trace context, stable hashes, and provider error categories. A small stock-history facade provides the feature-flag switch between the legacy direct manager path and the new provider-contract path without modifying DSA runtime source.

**Tech Stack:** Python 3.11, stdlib dataclasses/protocols, existing `RuntimeSettings`, `TraceContext`, `ProviderError`, `DataBatch`, `InstrumentId`, pytest, Pandas only in tests/fake DSA outputs.

---

### Task 1: Red Tests for DSA Provider Adapter

**Files:**
- Create: `tests/integrations/test_dsa_provider_adapter.py`

- [ ] **Step 1: Add failing tests**

Write tests covering: capabilities, daily-bar mapping, trace/provenance/hash, immutable records, schema drift, empty results, exception classification/redaction, CI profile real-manager guard, unsupported methods, and feature-flag history facade switching.

- [ ] **Step 2: Run tests and confirm Red**

Run: `.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_provider_adapter.py -q`
Expected: FAIL because `serenity_alpha_lab.integrations.dsa.provider_adapter` does not exist.

### Task 2: Adapter Implementation

**Files:**
- Create: `src/serenity_alpha_lab/integrations/dsa/provider_adapter.py`
- Modify: `src/serenity_alpha_lab/integrations/dsa/__init__.py`

- [ ] **Step 1: Implement minimal adapter**

Implement `DsaProviderCompatibilityAdapter` with injected manager/factory support, `MarketDataProvider` methods, daily-bar DataFrame normalization, request/provenance construction, raw-response SHA-256 hashing, field lineage, trace propagation, and ProviderError classification.

- [ ] **Step 2: Implement feature-flag facade**

Implement `DsaStockHistoryCompatibilityFacade` so callers can request legacy direct output or provider-contract output via `use_provider_contract`.

- [ ] **Step 3: Export public adapter symbols**

Export the adapter, facade, factory helper, and constants from `integrations/dsa/__init__.py`.

- [ ] **Step 4: Run target tests**

Run: `.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_provider_adapter.py -q`
Expected: PASS.

### Task 3: Architecture and Evidence

**Files:**
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/dsa-provider-compatibility-adapter.md`

- [ ] **Step 1: Add architecture guard**

Add a test ensuring the DSA provider adapter keeps concrete DSA imports lazy and does not import `data_provider.*` or `src.*` at module import time.

- [ ] **Step 2: Document evidence**

Document scope, field mapping, feature-flag behavior, Provider/Profile/Trace/ProblemDetails reuse, non-goals, and verification commands.

- [ ] **Step 3: Run related verification**

Run:
`.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_provider_adapter.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

### Task 4: Project Status and Checkpoint

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Update task ledger**

Mark only `SAL-P2-002` as done, move P2 progress to `2/20`, total to `31/129`, add decision/evidence rows, and promote the next valid task without marking it complete.

- [ ] **Step 2: Update recovery state**

Refresh current Phase/Gate, completed/unfinished scope, latest delivery checkpoint placeholder, next task, constraints, and copyable next-session prompt.

- [ ] **Step 3: Add task review**

Append a `SAL-P2-002` review to `tasks/todo.md` with Red/Green evidence, verification, exclusions, and checkpoint scope.

- [ ] **Step 4: Run final verification**

Run full relevant checks: target/related pytest, full pytest, py_compile for changed Python files, dependency lock guard, `git diff --check`, immutable tag check, and `git status --short`.

- [ ] **Step 5: Commit checkpoint**

Stage only relevant `SAL-P2-002` files and create a Chinese checkpoint commit.
