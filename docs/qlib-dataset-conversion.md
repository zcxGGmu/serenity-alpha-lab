# Qlib Dataset Conversion

> Task: `SAL-P4-006` Dataset 到 Qlib 转换
> Date: 2026-07-25
> Status: `APPROVED FOR SAL-P4-007 ADAPTER INPUT ONLY`

## Conclusion

`SAL-P4-006` adds a pure integration-boundary converter that turns already
published platform Dataset versions into deterministic Qlib calendar,
instrument, feature, field-mapping and compact summary artifacts.

The converter does not import Qlib, does not call `qlib.init`, does not start a
Qlib Adapter, and does not run a formal portfolio backtest. Its output is an
offline artifact bundle that later `SAL-P4-007` can consume inside the dedicated
Quant Worker boundary approved by ADR-009.

## Source Dataset Requirements

The conversion input is `QlibDatasetConversionSpec`, plus in-memory Dataset
objects for the same immutable versions:

| Dataset key | Required schema | Required status | Purpose |
|---|---|---|---|
| `trading_calendar` | `dataset.trading_calendar@1.0.0` | `quality_status=passed`, `publication_status=published` | Qlib trading-day calendar lines |
| `instrument_master` | `dataset.instrument_master@1.0.0` | `quality_status=passed`, `publication_status=published` | Qlib symbols and instrument validity windows |
| `adjusted_daily_bars` | `dataset.bars_1d_adjusted@1.0.0` | `quality_status=passed`, `publication_status=published` | Qlib daily feature rows |

Every manifest must be a concrete `DatasetVersionManifest` with a `dsv_*`
version id, source file hashes, schema hash and run/stage/trace lineage. Held,
quarantined, blocked, warning-only, schema-mismatched or unpublished Dataset
versions are rejected before conversion.

## Output Artifacts

| Artifact | Schema | Content type | Contents |
|---|---|---|---|
| Calendar | `integration.qlib.calendar@1.0.0` | `text/plain; charset=utf-8` | One ISO trading date per line, sorted ascending |
| Instruments | `integration.qlib.instrument@1.0.0` | `text/plain; charset=utf-8` | `qlib_symbol`, first feature date and last feature date per instrument |
| Features | `integration.qlib.feature@1.0.0` | `application/vnd.serenity.integration.qlib.feature+json` | Stable JSON rows keyed by Qlib symbol and trade date |
| Field mapping | `integration.qlib.field_mapping@1.0.0` | `application/vnd.serenity.integration.qlib.field-mapping+json` | Bidirectional platform-to-Qlib and Qlib-to-platform lineage |
| Summary | `integration.qlib.dataset_conversion@1.0.0` | `application/vnd.serenity.integration.qlib.dataset-conversion+json` | Compact bundle descriptor, artifact URIs, hashes, row counts and source versions |

The summary intentionally stores artifact descriptors and counts, not full
feature rows. Large payloads remain behind `ArtifactManifest` URIs and SHA-256
content hashes.

## Symbol Mapping

`InstrumentId` remains the platform identity. CN exchange prefixes are mapped
explicitly for Qlib compatibility:

| Platform exchange | Platform example | Qlib symbol |
|---|---|---|
| `XSHG` | `600519.XSHG` | `SH600519` |
| `XSHE` | `000001.XSHE` | `SZ000001` |
| `XBSE` | `430047.XBSE` | `BJ430047` |

The reverse mapping is retained in the field-mapping artifact and per-record
lineage, so Qlib outputs can resolve back to canonical platform instruments.

## Feature Field Mapping

| Platform field | Qlib field | Transform |
|---|---|---|
| `open` | `$open` | Identity numeric mapping from adjusted daily bars |
| `high` | `$high` | Identity numeric mapping from adjusted daily bars |
| `low` | `$low` | Identity numeric mapping from adjusted daily bars |
| `close` | `$close` | Identity numeric mapping from adjusted daily bars |
| `volume` | `$volume` | Identity numeric mapping from adjusted daily bars |
| `amount` | `$amount` | Identity numeric mapping from adjusted daily bars |
| `adjustment_factor` | `$factor` | Identity numeric mapping from adjusted daily bars |

The converter filters by market, requested date range, adjustment mode,
optional provider id and open trading days. Missing bars are not filled. Gaps
inside an instrument's converted validity window are emitted as explicit
`missing_feature_bar` warnings in the summary metadata.

## Non-Goals

- No Qlib runtime import, `qlib.init`, Recorder, Handler, model training,
  prediction, factor evaluation or Qlib backtest execution.
- No formal portfolio backtest run, order generation, fill matching, Portfolio
  Ledger replay, RiskPolicy evaluation, performance metrics or Quant Lab UI.
- No Evidence Agent, real Provider/LLM call, Worker loop or DSA runtime source
  migration.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation and Screen results
  remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_dataset_conversion.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.integrations.qlib.dataset_converter` |
| Focused target | `8 passed` |
| Related suite | `52 passed` across Qlib conversion/isolation, Dataset primitives, BacktestSpec/Artifact and architecture boundaries |
| Full suite | `343 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` PASS, patches `0001` through `0005` already applied |
| Immutable upstream tag | `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` PASS |
| Runtime boundary | AST import guard confirms converter imports no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy` |

## Scope Guard

This record only approves the deterministic Dataset conversion bundle as a
future Qlib Adapter input. `SAL-P4-007` may wrap Qlib inside the dedicated Quant
Worker boundary, but it must still respect ADR-009: no arbitrary module paths,
no FastAPI import-time initialization, and no direct promotion of conversion
artifacts into a formal backtest without `BacktestSpec`, `BacktestArtifact`,
Ledger/Risk and G4 validation.
