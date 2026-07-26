# SAL-P4-019 Backtest Golden And Property Test Plan

> Started: 2026-07-26
> Scope: Complete `SAL-P4-019` by adding a deterministic, hand-computable backtest golden fixture and property-style checks for the P4 formal portfolio backtest component chain. Cover 3 securities across 20 trading days, with explicit full-read vs chunked-read equivalence. Do not start formal API routes, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls, Qlib runtime, or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-019 boundaries; platform wrapper injected empty optional fields twice, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-backtest-golden-property-tests.md`.
- [x] Add Red tests for golden fixture summary, order/fill/ledger/equity/metrics expectations, full-read vs chunked-read equivalence, property-style invariants, invalid chunk sizes and import boundary.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/golden.py` with immutable fixture records, deterministic fixture builder, full/chunked readers and a pure golden runner.
- [x] Export golden fixture symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/backtest-golden-property-tests.md` with scope, fixture coverage, expected results, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-019` done, P4 `19/22`, total `85/129`, decision/evidence rows and `SAL-P4-020` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check and `git diff --check`.
- [x] Review, stage only `SAL-P4-019` files and create the required Chinese checkpoint commit.

## Guardrails

- The golden runner is a fixed-data validation harness for P4 component contracts; it must not expose formal API, Quant Lab, Evidence Agent, Worker loop, Qlib runtime, real Provider/LLM calls, or DSA legacy `/api/v1/backtest/*` changes.
- Golden evidence may use the formal portfolio backtest namespace only for the hand-computable fixture contract, and must explicitly state it is not a production promoted backtest or Gate G4 approval.
- Full-read and chunked-read paths must consume identical fixture records and produce identical result records and hashes.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

## Review

- Red target initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.backtest.golden'`.
- Green focused target `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_golden_property.py -q` passed with `4 passed`.
- Related suite passed with `46 passed`; full suite passed with `395 passed, 3 skipped`.
- Compileall, dependency lock guard, DSA patch check, immutable `upstream/dsa-v3.26.1` tag check and `git diff --check` passed.
- Subagent code-review dispatch was attempted but rejected by wrapper schema validation; per lessons, review fell back to local diff inspection plus fresh verification.
- Implementation checkpoint: `81117543 test(P4): 建立回测金标与性质测试`.
- Result hash: `sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1`; final cash/equity `10246.600`, costs `3.400`, realized P&L `196.600`, cumulative return `0.024660`.
