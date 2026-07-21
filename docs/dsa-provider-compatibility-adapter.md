# DSA Provider Compatibility Adapter Record

> Task: `SAL-P2-002` DSA Provider Compatibility Adapter<br>
> Date: 2026-07-21<br>
> Gate: G2 remains not passed<br>
> Scope: Wrap DSA `DataFetcherManager` daily-bar Pandas output behind the frozen Provider domain contract without moving DSA runtime source or making real Provider/LLM calls in tests.

## Summary

`SAL-P2-002` adds a narrow DSA compatibility adapter at `src/serenity_alpha_lab/integrations/dsa/provider_adapter.py`.

The adapter implements the synchronous `MarketDataProvider` shape from `SAL-P2-001` for daily bars and keeps the real DSA import lazy through the existing isolated worktree resolver. Tests use injected fake managers, so CI remains offline and does not instantiate real Provider SDKs.

## Implemented Contract

| Area | Implementation |
|---|---|
| Provider capability | Declares only `daily_bars` for CN/HK/US/JP/KR/TW with schema `market.daily_bars.dsa_compatibility` version `1.0.0`. |
| Instrument mapping | Uses `InstrumentId.to_dsa_symbol()` before calling the DSA manager. Bare 6-digit legacy stock codes are interpreted as CN only inside the stock-history compatibility facade. |
| DSA input | Calls an injected DSA-like `get_daily_data(stock_code, start_date, end_date, days=30)` manager. The real `DataFetcherManager` is created only by `from_runtime_settings()` / `create_default_dsa_data_fetcher_manager()`. |
| Row mapping | Converts DSA Pandas rows into immutable `DataBatch` records: `instrument_id`, `date`, OHLCV, optional `amount`, `pct_chg`, technical fields (`ma5`, `ma10`, `ma20`, `volume_ratio`) and `source`. |
| Provenance | Captures `provider_id` (`dsa:<source>` or `dsa:mixed`), sanitized request parameters, aware timestamps, normalized raw-response SHA-256, field lineage, source timestamp and active trace/run/stage ids. |
| Error mapping | Maps DSA/fetcher failures to `ProviderErrorCategory` values and lets the existing `ProviderProblem` boundary produce `application/problem+json` with trace propagation and redaction. |
| Feature flag facade | `DsaStockHistoryCompatibilityFacade.get_history_data(..., use_provider_contract=True/False)` switches legacy history callers between direct manager output and the provider-contract path without modifying DSA source. |
| Profile boundary | `from_runtime_settings()` rejects CI/default real-manager construction; injected fake/stub managers remain allowed for offline contract tests. |

## Reused P1 Boundaries

- `RuntimeProfile` / `RuntimeSettings`: real DSA manager construction is blocked in CI.
- `ProblemDetails`: `ProviderError` continues to map to stable `provider_error` / HTTP 502 through the existing API error contract.
- `TraceContext`: active `trace_id`, `run_id` and `stage_id` are copied into Provider provenance.
- `InstrumentId`: provider calls use canonical instruments and explicit DSA symbol mapping.
- Compatibility Facade: stock-history switching is isolated in a new facade rather than by modifying DSA runtime source.

`ArtifactStore`, `Run/Stage/Event`, Alembic and persistent task execution are not implemented here; they remain downstream P2 consumers of the Provider contract.

## Verification

Fresh Red/Green evidence for this task:

```text
uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_provider_adapter.py -q
Red: ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.provider_adapter'
Green: 8 passed
```

Required final verification for checkpoint:

```text
uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_provider_adapter.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m py_compile <changed python files>
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Latest checkpoint run:

```text
Adapter target: 8 passed
Related adapter/API/architecture suite: 22 passed
Full pytest: 137 passed
py_compile: PASS
scripts/verify-python-dependency-lock.sh: PASS
git diff --check: PASS
upstream/dsa-v3.26.1: e8a9ca7742e8cb2498c8f491dd76d239b3064e1a
```

## Non-Goals

- No real Provider, real LLM, network probe or DSA SDK call is performed by tests.
- No Bronze raw-data layer, Dataset Catalog, PIT data, fallback policy, persistent task backend, Quant Core, formal backtest or Evidence Agent is implemented.
- No DSA runtime source is copied into the Serenity package; the real DSA import remains lazy and isolated.
- `RSK-004` remains open and Gate G2 remains not passed.
