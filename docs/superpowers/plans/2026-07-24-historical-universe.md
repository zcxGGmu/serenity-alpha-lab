# SAL-P3-011 Historical Universe Plan

> Date: 2026-07-24
> Scope: Build the deterministic L0 historical universe contract and snapshot builder. Do not implement ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib adapter, Portfolio Backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop, or DSA runtime source migration.

## Goal

`SAL-P3-011` delivers a point-in-time historical universe layer that can produce an auditable list of tradable instruments for a historical decision date. The builder must use only the instrument, calendar, daily-bar, and explicit trade-status data available for that date, and every exclusion must preserve a rule id plus data evidence.

## Implementation Steps

- Add Red tests for `UniverseDefinition`, concrete `dsv_*` dataset version guards, PIT listing/ST/delisting behavior, suspension and data-availability exclusions, deterministic records, and ArtifactStore publication.
- Implement `serenity_alpha_lab.quant.screening.universe` with immutable definition/snapshot/rule/evidence DTOs, deterministic snapshot id generation, and a pure snapshot builder.
- Export universe symbols from `serenity_alpha_lab.quant.screening`.
- Add `docs/historical-universe.md` with rules, evidence semantics, PIT guardrails, non-goals, and verification evidence.
- Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and `tasks/todo.md` review after verification.
- Run target, related, full, compile, lock, diff, and immutable tag verification.
- Create the required Chinese checkpoint commit for the implementation and a follow-up status-sync commit if needed.

## Guardrails

- `UniverseDefinition.dataset_versions` must use concrete `dsv_*` ids and must reject `latest`.
- `build_historical_universe_snapshot()` must query `InstrumentMasterDataset` as of the requested decision date, never current membership/status.
- Hard filters are deterministic and auditable: listing status, min listing trading days, ST, suspension, and daily-bar availability.
- Every exclusion must include `rule_id`, `rule_version`, `severity`, and at least one `UniverseDataEvidence` record.
- The module must not call Provider/LLM paths, run AlphaSift, compute factor values, build screens, or simulate portfolios.
