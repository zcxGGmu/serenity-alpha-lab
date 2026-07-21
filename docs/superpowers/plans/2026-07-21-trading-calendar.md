# Trading Calendar Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-006` by implementing a deterministic trading calendar Dataset for market time zones, trading dates, sessions, half days, and ad-hoc closures.

**Architecture:** Add a narrow `datasets.trading_calendar` module that stays independent of Provider SDKs, DSA runtime source, PIT data, daily bars, fallback policy, Quant Core, and formal backtesting. Calendar records are keyed by `Market + trade_date`, reuse P1/P2 `Market` identities, carry Bronze lineage and Run/Stage/Trace scalar attribution, build in-memory query caches, and publish deterministic JSON through the existing `ArtifactStore`.

**Tech Stack:** Python 3.11+, `dataclasses`, `zoneinfo`, existing `Market`, `ArtifactStore`, `LocalArtifactStore`, pytest.

---

## Files

- Create: `src/serenity_alpha_lab/datasets/trading_calendar.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`
- Create: `tests/datasets/test_trading_calendar.py`
- Modify: `tests/architecture/test_architecture_boundaries.py` only if boundary coverage needs an explicit calendar guard
- Create: `docs/trading-calendar-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

## Task 1: Trading Calendar Contract Tests

**Files:**
- Create: `tests/datasets/test_trading_calendar.py`
- Read: `src/serenity_alpha_lab/domain/instruments.py`
- Read: `src/serenity_alpha_lab/repositories/local_artifact_store.py`

- [ ] **Step 1: Write failing tests**

Create tests covering:

- `TradingCalendarDataset` publishes deterministic JSON artifacts with schema/content type, Run/Stage attribution, Trace ID, and Bronze source artifact IDs.
- `Market.CN` sessions use `Asia/Shanghai`, with regular open/close, lunch break, closed holiday, and explicit half-day/ad-hoc closure records.
- UTC-to-`Asia/Shanghai` conversion goldens for pre-open, open, lunch break, afternoon open, and post-close timestamps.
- Query cache behavior for `get()`, `sessions_for_market()`, `trading_days()`, `next_trading_day()`, `previous_trading_day()`, `is_trading_day()`, and `is_open_at()`.
- Validation rejects duplicate `(market, trade_date)` keys, naive datetimes, inconsistent time zones, missing open/close times on trading sessions, open/close times on closed sessions, invalid lunch breaks, and empty Bronze lineage.

- [ ] **Step 2: Run Red test**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q`

Expected: FAIL during collection because `serenity_alpha_lab.datasets.trading_calendar` does not exist yet.

## Task 2: Minimal Dataset Implementation

**Files:**
- Create: `src/serenity_alpha_lab/datasets/trading_calendar.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [ ] **Step 1: Implement immutable calendar records**

Implement:

- `TRADING_CALENDAR_SCHEMA_NAME = "dataset.trading_calendar"`
- `TRADING_CALENDAR_SCHEMA_VERSION = "1.0.0"`
- `TRADING_CALENDAR_CONTENT_TYPE = "application/vnd.serenity.dataset.trading-calendar+json"`
- `TradingCalendarDatasetError(ValueError)`
- `TradingSessionStatus` with `OPEN`, `HALF_DAY`, `CLOSED`, `AD_HOC_CLOSED`, and `SUSPENDED`
- `MarketSession` with `market`, `trade_date`, `timezone`, `status`, `open_at`, `close_at`, optional lunch break, `source_bronze_artifact_id`, and optional note

- [ ] **Step 2: Implement validation and indexes**

Validate:

- timezone matches the configured market timezone
- trading sessions have aware open/close datetimes in the market timezone
- closed/ad-hoc/suspended sessions do not carry open/close times
- lunch break has both endpoints and is strictly within the session
- session local date equals `trade_date`
- duplicate `(market, trade_date)` keys are rejected

Build immutable in-memory indexes by key and market for fast query APIs.

- [ ] **Step 3: Implement query and publish APIs**

Expose:

- `market_timezone(market)`
- `TradingCalendarDataset.get(market, trade_date)`
- `sessions_for_market(market, start, end, include_closed=True)`
- `trading_days(market, start, end)`
- `is_trading_day(market, trade_date)`
- `next_trading_day(market, after, inclusive=False)`
- `previous_trading_day(market, before, inclusive=False)`
- `is_open_at(market, at)`
- `to_json_bytes()`
- `publish(artifact_store, produced_by_run_id=..., produced_by_stage_id=...)`

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q`

Expected: PASS.

## Task 3: Evidence, Ledger, And Verification

**Files:**
- Create: `docs/trading-calendar-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Record acceptance evidence**

Document schema, query semantics, timezone policy, A-share holiday/half-day/ad-hoc closure policy, Bronze lineage, artifact publishing, and explicit exclusions: no raw daily bars, PIT/fallback policy, real Provider calls, Dataset Catalog/latest alias, Quant Core, formal backtest, Evidence Agent, Worker runtime, or broad DSA runtime migration.

- [ ] **Step 2: Update progress/status ledgers**

Mark `SAL-P2-006` done, set P2 to `6/20`, total to `35/129`, promote `SAL-P2-007` to READY, and refresh the next-session prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q
uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

- [ ] **Step 4: Commit**

Stage only `SAL-P2-006` files and create a Chinese checkpoint commit with the project template.
