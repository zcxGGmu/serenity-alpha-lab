# Symbol Compatibility Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-003` by wrapping legacy DSA `normalize_stock_code` semantics with Serenity `InstrumentId` and explicit provider symbol mappings.

**Architecture:** Add a narrow `integrations/dsa` symbol compatibility module that converts legacy stock strings into immutable `InstrumentId`-backed mapping records with validity windows, DSA-normalized legacy codes, DSA provider symbols, and Yahoo provider symbols. Wire the P2 DSA Provider adapter and stock-history compatibility facade through this mapper so provider provenance stores canonical `instrument_id` values instead of naked symbols, while legacy API payloads keep their existing `stock_code` strings. Do not modify the isolated DSA worktree and do not start Bronze, Dataset, PIT, fallback policy, real Provider calls, or broad DSA source migration.

**Tech Stack:** Python 3.11, stdlib dataclasses/protocols, existing `InstrumentId`, `ProviderSymbolMapping`, DSA adapter facade, pytest, Pandas only in adapter tests.

---

### Task 1: Red Tests for Symbol Compatibility

**Files:**
- Create: `tests/integrations/test_dsa_symbol_compatibility.py`
- Modify: `tests/integrations/test_dsa_provider_adapter.py`

- [ ] **Step 1: Add failing symbol mapping tests**

Add tests for P0-compatible conversions: `SH.600519`, `SS600519`, `600519.SS`, `BJ.920748`, `1810.HK`, `hk700`, `7203.t`, `005930.ks`, `035720.kq`, `2330.tw`, `6505.two`, and `AAPL`.

- [ ] **Step 2: Add ambiguity and validity tests**

Add tests asserting bare six-digit legacy symbols require explicit `Market.CN`, invalid explicit exchange hints such as `SZ600519` fail, validity windows are retained, and `valid_to < valid_from` is rejected.

- [ ] **Step 3: Add adapter wrapper test**

Extend the DSA adapter test with an injected stock-code mapper/normalizer and assert daily-bar calls and provenance pass through the wrapper, while records continue to use canonical `instrument_id`.

- [ ] **Step 4: Run tests and confirm Red**

Run: `.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py -q`
Expected: FAIL because `serenity_alpha_lab.integrations.dsa.symbol_compatibility` and adapter wiring do not exist yet.

### Task 2: Symbol Compatibility Implementation

**Files:**
- Create: `src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py`
- Modify: `src/serenity_alpha_lab/integrations/dsa/provider_adapter.py`
- Modify: `src/serenity_alpha_lab/integrations/dsa/__init__.py`

- [ ] **Step 1: Implement mapping value object**

Implement frozen `DsaStockCodeMapping` with `raw_symbol`, `instrument_id`, `legacy_stock_code`, `dsa_symbol`, `provider_mappings`, `valid_from`, and `valid_to`; validate mapping ownership and validity order.

- [ ] **Step 2: Implement compatibility mapper**

Implement `DsaStockCodeCompatibilityMapper` with injectable `normalize_stock_code` callable, `from_legacy()`, and `from_instrument()`; default behavior mirrors DSA P0 `normalize_stock_code` conversion cases without importing DSA runtime source.

- [ ] **Step 3: Wire adapter and facade**

Use the mapper inside `DsaProviderCompatibilityAdapter.get_daily_bars()` and `DsaStockHistoryCompatibilityFacade._get_history_data_via_provider()` so request provenance includes canonical `instrument_ids`, legacy-normalized `legacy_stock_codes`, and provider `dsa_symbols`.

- [ ] **Step 4: Export symbols**

Export `DsaStockCodeCompatibilityMapper`, `DsaStockCodeMapping`, and `normalize_stock_code_compatible` from `integrations/dsa/__init__.py`.

- [ ] **Step 5: Run target tests**

Run: `.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py -q`
Expected: PASS.

### Task 3: Evidence and Guardrails

**Files:**
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/dsa-symbol-compatibility-migration.md`

- [ ] **Step 1: Add architecture guard**

Add or extend a boundary test confirming the symbol compatibility module stays in the DSA integration layer, imports only stdlib plus domain objects, and does not import concrete `data_provider.*` or DSA `src.*` modules.

- [ ] **Step 2: Document evidence**

Document P0 conversion coverage, ambiguity behavior, provider symbol mapping table, validity-window handling, adapter provenance changes, non-goals, and verification commands.

- [ ] **Step 3: Run related verification**

Run:
`.cache/dsa-p0/venv/bin/python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py tests/domain/test_instrument_id.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

### Task 4: Status Sync and Checkpoint

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Update task ledger**

Mark only `SAL-P2-003` as done, move P2 progress to `3/20`, total to `32/129`, add decision/evidence rows, and keep `SAL-P2-004` ready without marking it complete.

- [ ] **Step 2: Update recovery state**

Refresh current Phase/Gate, completed/unfinished scope, latest delivery checkpoint placeholder, next task, constraints, and copyable next-session prompt.

- [ ] **Step 3: Add task review**

Append a `SAL-P2-003` review to `tasks/todo.md` with Red/Green evidence, verification, exclusions, and checkpoint scope.

- [ ] **Step 4: Run final verification**

Run target/related/full pytest, py_compile for changed Python files, dependency lock guard, `git diff --check`, immutable tag check, and `git status --short --branch`.

- [ ] **Step 5: Commit checkpoint**

Stage only relevant `SAL-P2-003` code, tests, docs, and task files, then create a Chinese checkpoint commit.
