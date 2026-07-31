# Raw Daily Bars Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-007` by implementing a deterministic raw daily bars Dataset for unadjusted OHLCV/amount records.

**Architecture:** Add a narrow `datasets.raw_daily_bars` module that consumes already-normalized Provider `DataBatch` daily-bar records and publishes immutable Dataset JSON artifacts. Records are keyed by `InstrumentId + trade_date + provider_id`, validated against Instrument Master and Trading Calendar snapshots, carry Provider source timestamp plus Bronze lineage, and expose offline query helpers without creating Dataset Catalog/latest aliases, Arrow Schema Registry, quality gates, PIT/fallback policy, or real Provider calls.

**Tech Stack:** Python 3.11+, dataclasses, existing `InstrumentId`, `Market`, `DataBatch`, `Provenance`, `ArtifactStore`, `InstrumentMasterDataset`, `TradingCalendarDataset`, `TraceContext` scalar IDs, pytest.

---

## Files

- Create: `src/serenity_alpha_lab/datasets/raw_daily_bars.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`
- Create: `tests/datasets/test_raw_daily_bars.py`
- Create: `docs/raw-daily-bars-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

## Task 1: Raw Daily Bars Contract Tests

**Files:**
- Create: `tests/datasets/test_raw_daily_bars.py`
- Read: `src/serenity_alpha_lab/datasets/instrument_master.py`
- Read: `src/serenity_alpha_lab/datasets/trading_calendar.py`
- Read: `src/serenity_alpha_lab/domain/providers.py`
- Read: `src/serenity_alpha_lab/repositories/local_artifact_store.py`

- [ ] **Step 1: Write failing tests**

Cover:

- `RawDailyBarsDataset.from_provider_batch()` maps Provider `DataBatch` records into immutable unadjusted bar records.
- Primary key is `(instrument_id, trade_date, provider_id)` and duplicate keys are rejected.
- OHLC rule `low <= open/close <= high` and non-negative `volume` / `amount` are enforced.
- `trade_date` must be a trading day in `TradingCalendarDataset`.
- `instrument_id` must exist in `InstrumentMasterDataset` as of `trade_date`.
- Provider/source metadata includes `provider_id`, provider row `source`, Provider `source_timestamp`, Provider raw-response SHA-256, field lineage, trace/run/stage IDs, and `source_bronze_artifact_id`.
- Query helpers return bars by instrument, market/date range, and provider.
- Artifact publishing is deterministic JSON through `ArtifactStore`.
- Validation errors map through existing `ProblemDetails` as `validation_error`.

- [ ] **Step 2: Run Red test**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q`

Expected: FAIL during collection because `serenity_alpha_lab.datasets.raw_daily_bars` does not exist yet.

## Task 2: Minimal Dataset Implementation

**Files:**
- Create: `src/serenity_alpha_lab/datasets/raw_daily_bars.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [ ] **Step 1: Implement immutable records**

Implement:

- `RAW_DAILY_BARS_SCHEMA_NAME = "dataset.bars_1d_raw"`
- `RAW_DAILY_BARS_SCHEMA_VERSION = "1.0.0"`
- `RAW_DAILY_BARS_CONTENT_TYPE = "application/vnd.serenity.dataset.raw-daily-bars+json"`
- `RawDailyBarsDatasetError(ValueError)`
- `RawDailyBar` with canonical `InstrumentId`, `trade_date`, unadjusted OHLCV/amount, `provider_id`, provider row source, source timestamp, raw-response hash, field lineage, Bronze lineage, and optional `currency`.

- [ ] **Step 2: Implement Provider batch conversion**

Create `RawDailyBarsDataset.from_provider_batch(batch, instrument_master=..., trading_calendar=..., source_bronze_artifact_id=..., created_at=..., trace_id=..., run_id=..., stage_id=...)`.

Validate records offline using the supplied Instrument Master and Trading Calendar snapshots. Do not construct or call a real Provider.

- [ ] **Step 3: Implement indexes, query, and publish APIs**

Expose:

- `RawDailyBarsDataset.get(instrument_id, trade_date, provider_id)`
- `bars_for_instrument(instrument_id, start, end, provider_id=None)`
- `bars_for_market(market, trade_date, provider_id=None)`
- `bars_for_provider(provider_id, start, end)`
- `to_json_bytes()`
- `publish(artifact_store, produced_by_run_id=..., produced_by_stage_id=...)`

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q`

Expected: PASS.

## Task 3: Evidence, Ledger, And Verification

**Files:**
- Create: `docs/raw-daily-bars-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Record acceptance evidence**

Document schema, key policy, validation rules, Instrument Master and Trading Calendar checks, Provider/Bronze lineage, deterministic publishing, and explicit exclusions: no adjusted bars, corporate actions, PIT/fallback policy, real Provider calls, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime migration.

- [ ] **Step 2: Update progress/status ledgers**

Mark `SAL-P2-007` done, set P2 to `7/20`, total to `36/129`, promote `SAL-P2-008` to READY, and refresh the next-session prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q
uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

- [ ] **Step 4: Commit**

Stage only `SAL-P2-007` files and create a Chinese checkpoint commit with the project template.
