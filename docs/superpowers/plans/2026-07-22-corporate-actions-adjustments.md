# P2 Corporate Actions and Adjustments Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-008` by adding deterministic corporate action and adjusted daily bars datasets. Reuse P2 Instrument Master, Trading Calendar, Raw Daily Bars, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start PIT/fallback policy, real Provider calls, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset patterns and SAL-P2-008 acceptance scope.
- [x] Add Red tests for corporate action schema, cash dividends, bonus/share splits, rights offerings, pre/post adjustment factors, raw price immutability, query helpers, artifact publishing, invalid action data, and validation error mapping.
- [x] Implement `CorporateActionsDataset`, adjustment factor calculation, and `AdjustedDailyBarsDataset` over existing raw bars.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-008`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-008` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Use synthetic offline records only; do not instantiate or call a real Provider.
- Preserve raw daily bars unchanged; adjusted prices must be explicit records keyed by `instrument_id + trade_date + provider_id + adjustment`.
- Support cash dividends, bonus/share splits, rights offerings and forward/backward adjustment factors; do not implement portfolio ledger corporate-action accounting.
- Do not create PIT fundamental Dataset, fallback policy, Catalog/latest alias, quality gates, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or network probes.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-008

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_corporate_actions_adjustments.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.corporate_actions'`.
- Green implementation: added `CorporateAction`, `CorporateActionsDataset`, `CorporateActionType`, `AdjustmentMode`, `AdjustedDailyBar` and `AdjustedDailyBarsDataset` with deterministic JSON Artifact publishing, query indexes, explicit adjustment mode keys and incremental primary-key replacement.
- Adjustment coverage: cash dividends, bonus shares/share splits and rights issues are aggregated by instrument/ex-date/provider, priced from the previous raw close, and converted into `forward` and `backward` factors without mutating `RawDailyBarsDataset` records.
- Reuse coverage: P2 Instrument Master as-of validation, Trading Calendar trading-day validation, Raw Daily Bars input, Bronze lineage, P1 `ArtifactStore`, trace/run/stage scalar attribution and existing `ValueError -> validation_error` ProblemDetails mapping are covered by tests.
- Verification: target corporate actions `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `68 passed`; full pytest `175 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: local review found and fixed a provider-scope double-count risk by filtering company actions to the raw bar provider and adding a regression assertion. Attempted independent `code-reviewer` subagent dispatch, but the client rejected payload variants as duplicate `message/items` or empty override fields.
- Scope retained: no PIT fundamental Dataset, fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, Portfolio Ledger corporate-action accounting, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.
