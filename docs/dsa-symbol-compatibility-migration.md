# DSA Symbol Compatibility Migration Record

> Task: `SAL-P2-003` 证券代码兼容迁移<br>
> Date: 2026-07-21<br>
> Gate: G2 remains not passed<br>
> Scope: Wrap DSA `normalize_stock_code` compatibility semantics with `InstrumentId` and explicit Provider Symbol Mapping without modifying DSA runtime source.

## Summary

`SAL-P2-003` adds `src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py`.

The new mapper converts legacy DSA stock-code strings into immutable `DsaStockCodeMapping` values that carry:

- Canonical `InstrumentId` (`<symbol>.<exchange>`) for new Serenity paths.
- DSA-compatible legacy normalized stock code matching P0 `normalize_stock_code` behavior.
- Explicit DSA and Yahoo provider symbols through `ProviderSymbolMapping`.
- Optional `valid_from` / `valid_to` mapping windows for future security master records.

The DSA Provider adapter now uses this mapper before calling the DSA-like manager, so Provider provenance records canonical `instrument_ids`, `legacy_stock_codes`, and `dsa_symbols`.

## Compatibility Coverage

| Legacy Input | Legacy Normalized | InstrumentId | DSA Symbol | Yahoo Symbol |
|---|---:|---|---|---|
| `SH.600519`, `SS600519`, `600519.SS` | `600519` | `600519.XSHG` | `SH600519` | `600519.SS` |
| `BJ.920748` | `920748` | `920748.XBSE` | `BJ920748` | `920748.BJ` |
| `1810.HK`, `hk700` | `HK01810`, `HK00700` | `01810.XHKG`, `00700.XHKG` | `HK01810`, `HK00700` | `01810.HK`, `00700.HK` |
| `7203.t` | `7203.T` | `7203.XTKS` | `7203.T` | `7203.T` |
| `005930.ks`, `035720.kq` | `005930.KS`, `035720.KQ` | `005930.XKRX`, `035720.XKOS` | same as legacy | same as legacy |
| `2330.tw`, `6505.two` | `2330.TW`, `6505.TWO` | `2330.XTAI`, `6505.ROCO` | same as legacy | same as legacy |
| `AAPL` | `AAPL` | `AAPL.XNAS` | `AAPL` | `AAPL` |

Bare six-digit strings remain ambiguous in strict domain conversion. Legacy DSA compatibility paths may pass `market=Market.CN` to preserve existing A-share API behavior, but new provider records use `InstrumentId.canonical` and do not persist naked symbols as cross-market keys.

## Adapter Changes

- `DsaProviderCompatibilityAdapter` accepts an injectable `DsaStockCodeCompatibilityMapper`.
- `get_daily_bars()` maps each `InstrumentId` through the compatibility mapper before calling `manager.get_daily_data()`.
- Provenance request parameters now include:
  - `instrument_ids`: canonical IDs such as `600519.XSHG`.
  - `legacy_stock_codes`: DSA-normalized compatibility codes such as `600519`.
  - `dsa_symbols`: provider call symbols such as `SH600519`.
- `DsaStockHistoryCompatibilityFacade` uses the mapper to interpret bare six-digit legacy requests as CN only at the legacy facade boundary.

## Reused Boundaries

- `InstrumentId` remains the only new-domain security identity.
- `ProviderSymbolMapping` carries provider-specific external symbols.
- `DsaProviderCompatibilityAdapter` remains the only DSA daily-bar Provider adapter.
- Profile, ProblemDetails and Trace behavior from `SAL-P2-002` remain unchanged.

## Verification

Fresh Red/Green evidence for this task:

```text
uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py -q
Red: ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.symbol_compatibility'
Green: 25 passed
```

Required final verification for checkpoint:

```text
uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py tests/domain/test_instrument_id.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m py_compile src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py src/serenity_alpha_lab/integrations/dsa/provider_adapter.py src/serenity_alpha_lab/integrations/dsa/__init__.py
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

## Non-Goals

- No DSA runtime source was modified or copied into `src/serenity_alpha_lab`.
- No Bronze raw-data layer, Dataset Catalog, PIT data, fallback policy, persistent task backend, Quant Core, formal backtest or Evidence Agent is implemented.
- No real Provider, real LLM or network call is introduced.
- `SAL-P2-004` remains `READY`, `RSK-004` remains open and Gate G2 remains not passed.
