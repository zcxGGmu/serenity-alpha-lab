# PIT Fundamental Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-009` by adding an offline point-in-time fundamental Dataset that distinguishes period, announced, available, ingested, and revision timestamps.

**Architecture:** Add a new `serenity_alpha_lab.datasets.fundamentals` module that mirrors the existing P2 Dataset pattern: frozen records, validation-first constructors, deterministic JSON publishing through `ArtifactStore`, Bronze lineage, trace/run/stage scalar attribution, and in-memory query indexes. PIT query methods must only return records with `available_at <= decision_time`, choose the latest usable revision per item, and exclude unknown temporal-confidence records from formal backtest queries.

**Tech Stack:** Python dataclasses, standard-library datetime/date/json, existing `InstrumentId`, `InstrumentMasterDataset`, `DataBatch`/`Provenance`, `ProviderCapability.FUNDAMENTALS`, `ArtifactStore`, pytest.

---

### Task 1: Define RED Dataset Tests

**Files:**
- Create: `tests/datasets/test_fundamentals_dataset.py`
- Later modify: `src/serenity_alpha_lab/datasets/fundamentals.py`

- [x] **Step 1: Add fixtures for instrument master, Provider fundamentals batch, and PIT rows**

```python
def make_provider_batch(records: list[dict[str, object]] | None = None) -> DataBatch[dict[str, object]]:
    provenance = Provenance(
        provider_id="dsa:FundamentalFixture",
        provider_version="fixture-1.0",
        operation=ProviderCapability.FUNDAMENTALS,
        request_parameters={"instrument_ids": ["600519.XSHG"], "as_of": DECISION_TIME.isoformat()},
        requested_at=NOW,
        fetched_at=FETCHED_AT,
        raw_response_sha256=RAW_SHA256,
        field_lineage={"value": "fixture.value", "available_at": "fixture.available_at"},
        source_timestamp=SOURCE_TIMESTAMP,
        trace_id="trace-provider-fundamentals",
        run_id="run-provider-fundamentals",
        stage_id="stage-provider-fundamentals",
    )
    return DataBatch(...)
```

- [x] **Step 2: Test artifact publishing and PIT query behavior**

Expected assertions:
- field schema includes `period_end`, `announced_at`, `available_at`, `ingested_at`, `revision`, `temporal_confidence`
- published payload is deterministic and includes schema metadata, partition keys, provider ids, Bronze artifact ids, trace/run/stage, and records
- `latest_as_of(..., decision_time=2026-05-01T09:30+08:00)` returns the first available 2025 annual `roe` revision
- `latest_as_of(..., decision_time=2026-05-15T09:30+08:00)` returns the later restated `roe` revision
- future records with `available_at > decision_time` are excluded

- [x] **Step 3: Test formal-backtest temporal confidence gate**

Expected assertions:
- legacy DSA-style records without `announced_at` map to `TemporalConfidence.UNKNOWN`
- `latest_as_of(..., purpose=FundamentalQueryPurpose.FORMAL_BACKTEST)` rejects unknown confidence
- the same unknown-confidence record can be returned for research-display purpose

- [x] **Step 4: Test validation and ProblemDetails mapping**

Expected assertions:
- duplicate `instrument_id + period_end + item + revision + provider_id` fails
- `available_at < announced_at`, `ingested_at < announced_at`, naive datetimes, missing Bronze lineage, invalid values, and unknown instrument as-of period fail
- Dataset errors map through existing `problem_from_exception()` as `validation_error`

- [x] **Step 5: Run target test and confirm RED**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q`

Expected: fails during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.fundamentals'`.

### Task 2: Implement Dataset Module

**Files:**
- Create: `src/serenity_alpha_lab/datasets/fundamentals.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [x] **Step 1: Add schema constants and enums**

Define:
- `FUNDAMENTALS_SCHEMA_NAME = "dataset.fundamentals"`
- `FUNDAMENTALS_SCHEMA_VERSION = "1.0.0"`
- `FUNDAMENTALS_CONTENT_TYPE = "application/vnd.serenity.dataset.fundamentals+json"`
- `FUNDAMENTALS_PARTITION_KEYS = ("market", "period_year")`
- `FundamentalPeriodType`, `FundamentalQueryPurpose`, and `TemporalConfidence`

- [x] **Step 2: Add `FundamentalRecord`**

Fields:
- identity: `instrument_id`, `period_end`, `period_type`, `item`, `revision`, `provider_id`
- PIT timing: `announced_at`, `available_at`, `ingested_at`
- values and metadata: `value`, `unit`, `currency`, `accounting_standard`, `fiscal_year`, `fiscal_quarter`, `provider_source`, `provider_source_timestamp`, `provider_raw_response_sha256`, `field_lineage`, `source_bronze_artifact_id`, `temporal_confidence`

Validation:
- `available_at` and `ingested_at` are timezone-aware
- `announced_at` may be `None` only with `TemporalConfidence.UNKNOWN`
- known confidence requires `announced_at <= available_at <= ingested_at`
- unknown confidence requires formal backtest exclusion
- values are finite numeric scalars

- [x] **Step 3: Add `FundamentalsDataset`**

Methods:
- `from_provider_batch(...)`
- `from_records(...)`
- `latest_as_of(...)`
- `history_for_item(...)`
- `records_for_instrument(...)`
- `merge_incremental(...)`
- `to_json_bytes()` and `publish(...)`

Query rules:
- always filter `available_at <= decision_time`
- choose the maximum `(period_end, available_at, revision)` for latest item lookups
- reject unknown confidence for `FundamentalQueryPurpose.FORMAL_BACKTEST`
- allow unknown confidence for `FundamentalQueryPurpose.RESEARCH_DISPLAY`

- [x] **Step 4: Export module symbols**

Add constants, enums, records, Dataset, and error class to `src/serenity_alpha_lab/datasets/__init__.py`.

- [x] **Step 5: Run target and related suites**

Run:
- `uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q`
- `uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/architecture/test_architecture_boundaries.py -q`

Expected: target and related suites pass.

### Task 3: Evidence, Status, and Checkpoint

**Files:**
- Create: `docs/fundamentals-pit-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add acceptance evidence doc**

Document scope, schema, PIT query semantics, temporal confidence policy, lineage, validation, verification commands, and explicit non-goals.

- [x] **Step 2: Update progress/status docs**

Mark only `SAL-P2-009` as done after verification. Update P2 progress from `8/20` to `9/20`, total from `37/129` to `38/129`, add `DEC-036` and `AEV-038`, and move next READY task to `SAL-P2-010`.

- [x] **Step 3: Run final verification**

Run:
- `uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q`
- `uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/architecture/test_architecture_boundaries.py -q`
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src tests`
- `scripts/verify-python-dependency-lock.sh`
- `git diff --check`
- `git rev-parse upstream/dsa-v3.26.1`

- [x] **Step 4: Commit only relevant files**

Stage only the P2-009 implementation, tests, evidence, status docs, plan, and task review. Use a Chinese checkpoint commit message that includes completion content, compatibility/risk handling, verification, and `SAL-P2-009, Gate G2`.
