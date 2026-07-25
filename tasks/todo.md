# SAL-P4-016 Unified Performance Metrics Plan

> Started: 2026-07-26
> Scope: Complete `SAL-P4-016` by implementing pure deterministic unified performance metrics for formal portfolio backtests. Compute returns, risk, drawdown, trading, turnover, cost, benchmark and industry exposure metrics with formula-version metadata, sample period, frequency, risk-free rate and annualization days. Do not start formal portfolio backtest runs, BacktestRun orchestration, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls, Qlib runtime or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs through `SAL-P4-015`, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-016 boundaries; host wrapper rejected empty optional-field payloads, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-backtest-performance-metrics.md`.
- [x] Add Red contract tests for formula registry, sample metadata, return/risk/drawdown metrics, trading/cost/benchmark/exposure metrics, invalid inputs and import boundary.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/metrics.py` with immutable DTOs, metric registry/formula versions, Decimal output quantization and stable report IDs.
- [x] Export performance metric symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/backtest-performance-metrics.md` with scope, formulas, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-016` done, P4 `16/22`, total `82/129`, decision/evidence rows and `SAL-P4-017` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check and `git diff --check`.
- [x] Review, stage only `SAL-P4-016` files and create the required Chinese checkpoint commit.

## Review: SAL-P4-016

- Added `tests/quant/test_backtest_performance_metrics.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.metrics` (`1 error`), Green focused target is `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/metrics.py` and exported symbols from `quant.backtest`; the module defines `BacktestPerformanceMetricPolicy`, `BacktestMetricRegistry`, `BacktestMetricDefinition`, `BacktestEquityPoint`, `BacktestTurnoverObservation`, `BacktestTradeOutcome`, `BacktestIndustryExposurePoint`, `BacktestPerformanceMetricReport` and `BacktestPerformanceMetricCalculator`.
- Metric registry freezes formula versions for cumulative/annualized return, volatility, Sharpe, Sortino, max drawdown, drawdown duration, Calmar, win rate, profit/loss ratio, turnover, cost ratio, tracking error, information ratio and industry exposure.
- Reports explicitly record sample start/end, frequency, period count, annualization days, risk-free rate, metric set version and formula-version mapping; third-party reporting can consume platform outputs but cannot redefine metric formulas.
- Scope retained: no formal portfolio backtest run, no BacktestRun orchestration, no Ledger/Risk/Audit mutation, no Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call, no Qlib runtime import and no legacy `/api/v1/backtest/*` drift.
- Read-only subagent dispatch for SAL-P4-016 boundary exploration was attempted, but the host wrapper rejected empty optional-field payloads; per lessons, fallback local senior review checked metric formula definitions, sample metadata, cost/turnover binding, no-go scope and import boundary.
- Local senior review found and fixed max drawdown peak-date attribution so later equity highs do not overwrite the peak date tied to the maximum drawdown; the focused contract test now asserts both peak and trough dates.
- Verification: Red target `1 error`; focused target `3 passed`; related Metrics/BiasAudit/RiskPolicy/CostModel/PortfolioLedger/BacktestSpec/Architecture suite `34 passed`; full pytest `382 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Implementation checkpoint: `96101791 feat(P4): 实现统一绩效指标`.
- Status-sync checkpoint: `0ec68022 docs: 同步 SAL-P4-016 checkpoint hash`.
- Status-sync hash-anchor checkpoint: pending this commit; follow-up final anchor will record the actual hash.

## Guardrails

- Performance metrics are a pure calculation layer; they may consume `BacktestSpec`, explicit equity/benchmark points, `CostBreakdown`, turnover observations, closed trade outcomes and industry exposure observations, but must not run strategies, execute orders, mutate Ledger/Risk/Audit, orchestrate BacktestRun, expose API/UI, initialize Qlib or start Worker runtime.
- Every report must carry sample period, frequency, annualization days, risk-free rate and formula versions.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

---

# SAL-P4-015 Backtest Bias Audit Plan

> Started: 2026-07-26
> Scope: Complete `SAL-P4-015` by implementing a pure deterministic backtest bias audit for formal portfolio backtests. Cover lookahead, survivorship, PIT availability, sample overlap and cost sensitivity with hard/warning outcomes. Do not start formal portfolio backtest runs, performance metrics, BacktestRun orchestration, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs through `SAL-P4-014`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-backtest-bias-audit.md`.
- [x] Add Red contract tests for lookahead leakage, survivorship leakage, PIT unavailable/unknown records, sample overlap warnings, cost sensitivity warnings and import boundary.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/audit.py` with immutable DTOs, deterministic rule outcomes, invalid-run promotion guards and stable report IDs.
- [x] Export bias audit symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/backtest-bias-audit.md` with scope, rule semantics, invalid-run guard, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-015` done, P4 `15/22`, total `81/129`, decision/evidence rows and `SAL-P4-016` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-015` files and create the required Chinese checkpoint commit.

## Review: SAL-P4-015

- Added `tests/quant/test_backtest_bias_audit.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.audit` (`1 error`), Green focused target is `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/audit.py` and exported symbols from `quant.backtest`; the module defines `BacktestBiasAuditObservation`, `CostSensitivityScenario`, `BacktestBiasAuditPolicy`, `BiasAuditRuleOutcome`, `BacktestBiasAuditReport`, `BacktestBiasAuditStatus`, `BiasAuditRuleStatus` and `BacktestBiasAuditor`.
- Bias audit covers lookahead data availability, historical as-of universe membership, PIT availability / temporal confidence, sample-overlap warnings, cost-sensitivity warning/block thresholds and deterministic report IDs.
- Hard failures and not-evaluable outcomes mark reports `invalid`, set `eligible_for_ranking=false` and `agent_strong_conclusion_allowed=false`; warning-only reports retain warning rule IDs but remain promotable for later explicit gates.
- Scope retained: no formal portfolio backtest run, no performance metrics, no BacktestRun orchestration, no Ledger/Risk mutation, no Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Verification: Red target `1 error`; focused target `3 passed`; related BiasAudit/RiskPolicy/BacktestSpec/Architecture suite `24 passed`; full pytest `379 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Implementation checkpoint: `c8331b3b feat(P4): 实现回测偏差审计`.
- Status-sync checkpoint: `eb4ffd5a docs: 同步 SAL-P4-015 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `3249dcd7 docs: 记录 SAL-P4-015 状态同步 hash`.
- Final anchor checkpoint: `4b47034f docs: 固化 SAL-P4-015 hash-anchor checkpoint`.

## Guardrails

- BiasAudit is a pure audit layer; it may read `BacktestSpec`, explicit audit observations and explicit cost sensitivity scenario summaries, but must not execute orders, mutate Ledger/Risk, compute performance metrics, orchestrate BacktestRun, expose API/UI, initialize Qlib or start Worker runtime.
- Hard failures mark the report `invalid`, set `eligible_for_ranking=false` and `agent_strong_conclusion_allowed=false`; warning-only reports remain auditable but must surface warning rule IDs.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

---

# SAL-P4-014 Deterministic RiskPolicy Plan

> Started: 2026-07-26
> Scope: Complete `SAL-P4-014` by implementing a pure deterministic RiskPolicy for formal portfolio backtests. Cover individual weight, industry, style, liquidity, turnover and drawdown rules with pass/warn/block/not-evaluable semantics. Do not start formal portfolio backtest runs, bias audit, performance metrics, BacktestRun orchestration, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs through `SAL-P4-013`, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-014 boundaries; host wrapper rejected payload shape, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-risk-policy.md`.
- [x] Add Red contract tests for individual weight, industry exposure, style exposure warning, liquidity floor, turnover, drawdown, not-evaluable blocking and import boundary.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/risk.py` with immutable DTOs, Decimal math, `BacktestRiskSpec` reuse, `PortfolioLedger` state reads and `RebalancePlan` order/target reads only.
- [x] Export RiskPolicy symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/risk-policy.md` with scope, status semantics, rule coverage, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-014` done, P4 `14/22`, total `80/129`, decision/evidence rows and `SAL-P4-015` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-014` files and create the required Chinese checkpoint commit.

## Guardrails

- RiskPolicy is a pure deterministic evaluation layer; it may read `BacktestSpec`, `PortfolioLedger`, `RebalancePlan` and explicit risk inputs, but must not execute orders, mutate Ledger, compute metrics, run bias audit, expose API/UI, initialize Qlib or start Worker orchestration.
- `not_evaluable` defaults to blocking the overall decision; UI/Agent may explain or request rerun with a new rule version but cannot override `block`.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

## Review: SAL-P4-014

- Added `tests/quant/test_risk_policy.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.risk` (`1 error`), Green focused target is `4 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/risk.py` and exported symbols from `quant.backtest`; the module defines `DeterministicRiskPolicy`, `InstrumentRiskProfile`, `RiskRuleOutcome`, `RiskPolicyResult`, `RiskDecisionStatus`, `RiskRuleStatus` and `RiskPolicyEvaluator`.
- RiskPolicy covers max single-name weight, industry exposure, style exposure warning/block limits, liquidity floor, turnover cap and drawdown cap; missing profiles, turnover context or high-water mark produce `not_evaluable` rule outcomes and overall `block`.
- Agent/UI override is explicitly disabled through `agent_override_allowed=false`; later UI/Agent work may explain the block or request a new policy version rerun, but cannot override deterministic gates.
- Read-only subagent dispatch for SAL-P4-014 boundary exploration was attempted, but the host wrapper rejected payload shapes as `message/items` conflicts; per lessons, fallback local senior review checked BacktestRiskSpec reuse, RebalancePlan/Ledger binding, not-evaluable blocking, Agent override guard, no-go scope and import boundary.
- Verification: Red target `1 error`; focused target `4 passed`; related Risk/Rebalance/AShareExecution/CostModel/PortfolioLedger/Order/BacktestSpec/Architecture suite `43 passed`; full pytest `376 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan clean; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no order execution/fills, no Ledger mutation, no bias audit, no performance metrics, no BacktestRun orchestration, no Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `c09dd889 feat(P4): 实现确定性 RiskPolicy`.
- Status-sync checkpoint: `87c0b8d4 docs: 同步 SAL-P4-014 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `23d7d35d docs: 记录 SAL-P4-014 状态同步 hash`.
- Final anchor checkpoint: `8efd14dc docs: 固化 SAL-P4-014 hash-anchor checkpoint`.

---

# SAL-P4-013 Rebalance And Target Weights Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-013` by implementing pure deterministic rebalance and target-weight order generation for formal portfolio backtests. Convert ScreenSnapshot and model signals into constrained created `Order` snapshots / `OrderIntent`s. Do not start formal portfolio backtest runs, market execution/fills, Ledger mutation, Risk/Metric/Audit, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs including A-share execution rules, ScreenSnapshot contracts, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-013 boundaries; host wrapper rejected empty `reasoning_effort`, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-rebalance-target-weights.md`.
- [x] Add Red contract tests for ScreenSnapshot equal/score weighting, model explicit target weights, cash buffer, max-weight cap, min-order skip, lot rounding, sell-before-buy deterministic order creation and import boundary.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/rebalance.py` with immutable DTOs, Decimal math, BacktestSpec/Risk/ExecutionSpec reuse, PortfolioLedger state reads and Order state-machine creation only.
- [x] Export rebalance symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/rebalance-target-weights.md` with scope, target-weight semantics, constraints, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-013` done, P4 `13/22`, total `79/129`, decision/evidence rows and `SAL-P4-014` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-013` files and create the required Chinese checkpoint commit.

## Guardrails

- Rebalance is a pure planning layer; it may create order intents and created order snapshots, but must not accept/fill/expire orders, call AShareExecutionModel, mutate PortfolioLedger, process company actions, compute risk/metrics/audit, expose API/UI, start Qlib runtime or start Worker orchestration.
- Use `BacktestSpec.execution.lot_size`, `BacktestSpec.risk.cash_buffer_pct`, `BacktestSpec.risk.max_weight_per_instrument` and policy-level `min_order_notional` as the explicit constraints for this task; full deterministic RiskPolicy remains `SAL-P4-014`.
- ScreenSnapshot inputs must bind `BacktestSpec.strategy.screen_snapshot_id`; model signals must use explicit target weights or deterministic score weighting and concrete version metadata.
- Buy orders must respect settled cash after buffer and payables; receivables are not counted as available cash. Sell orders are generated before buy orders, but unsettled sell proceeds are not assumed available for same rebalance buys.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

## Review: SAL-P4-013

- Added `tests/quant/test_rebalance_target_weights.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.rebalance` (`1 error`), Green focused target is `4 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/rebalance.py` and exported symbols from `quant.backtest`; the module defines `RebalancePolicy`, `WeightingPolicy`, `ModelSignal`, `TargetWeight`, `SkippedRebalanceOrder`, `RebalancePlan` and `RebalanceOrderGenerator`.
- Rebalance planning covers ScreenSnapshot equal/score weighting, model explicit target weights, cash buffer, max instrument cap, min order notional, lot rounding, sell-before-buy deterministic ordering, stable plan/order/event IDs and concrete model-version binding (`latest` rejected).
- Buy cash is constrained to settled cash after payables and cash buffer; receivables and same-rebalance sell proceeds are not counted as available buy cash.
- Scope retained: generated orders stay at `OrderStatus.CREATED`; no order execution/fills, no `AShareExecutionModel`, no Ledger mutation, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Code-review subagent dispatch was attempted for SAL-P4-013, but the host wrapper rejected both payload shapes as duplicate `message`/`items`; per lessons, fallback local senior review checked target-weight math, cash availability, created-order-only boundary, deterministic IDs, import boundaries and status anchors.
- Verification: focused target `4 passed`; related Rebalance/AShareExecution/CostModel/PortfolioLedger/Order/BacktestSpec/ScreenSnapshot/Architecture suite `42 passed`; full pytest `372 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Implementation checkpoint: `876547f4 feat(P4): 实现调仓与目标权重`.
- Status-sync checkpoint: `38c9e882 docs: 同步 SAL-P4-013 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `fc311881 docs: 记录 SAL-P4-013 状态同步 hash`.
- Final anchor checkpoint: `4497a4e6 docs: 固化 SAL-P4-013 hash-anchor checkpoint`.

---

# SAL-P4-012 Corporate Action Ledger Posting Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-012` by implementing pure deterministic company-action ledger posting for formal portfolio backtests. Support cash dividends, bonus/split shares, rights issues and delisting liquidation. Do not start formal portfolio backtest runs, rebalance/target-weight generation, Risk/Metric/Audit, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 backtest docs, P2 company-action docs, A-share execution rules, order/ledger/cost docs, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-012 boundaries; host wrapper rejected optional `reasoning_effort` payload twice, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-corporate-action-ledger-posting.md`.
- [x] Add Red contract tests for cash dividend receivable, bonus/split share lot adjustment, rights issue payable/new lot, delisting liquidation, deterministic replay and no adjusted-price double counting.
- [x] Extend `src/serenity_alpha_lab/quant/backtest/ledger.py` with immutable corporate-action ledger events and records.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/corporate_actions.py` as a narrow processor for P2 `CorporateAction` records and explicit delisting liquidation fixtures.
- [x] Export company-action ledger symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/corporate-action-ledger-posting.md` with scope, accounting semantics, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-012` done, P4 `12/22`, total `78/129`, decision/evidence rows and `SAL-P4-013` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-012` files and create the required Chinese checkpoint commit.

## Guardrails

- Company-action posting is a pure accounting layer; it may append ledger events but must not generate strategy orders, rebalance targets, market fills, risk checks, metrics, audit reports, API/UI output, Qlib runtime work or Worker orchestration.
- Use P2 `CorporateAction` records as the Dataset input for cash dividends, bonus/split shares and rights issues; delisting liquidation remains an explicit ledger posting fixture until a later Dataset source exists.
- Do not consume adjusted daily bar prices/factors when posting cash/share flows; raw/adjusted price continuity belongs to P2 Dataset derivation and must not be double-counted in Ledger.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

## Review: SAL-P4-012

- Added `tests/quant/test_corporate_action_ledger.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.corporate_actions` (`1 error`), Green focused target is `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/corporate_actions.py` and extended `src/serenity_alpha_lab/quant/backtest/ledger.py`; the module defines `CorporateActionLedgerProcessor`, stable dataset-backed corporate action IDs, explicit delisting liquidation posting, `CorporateActionLedgerType`, `CorporateActionRecord` and `LedgerEventType.CORPORATE_ACTION`.
- Accounting covers cash dividend receivables, bonus/share split pro-rata lot quantity adjustments with unchanged total cost basis, rights issue payables and new lots, delisting liquidation receivables, FIFO realized P&L and deterministic replay.
- No double-counting guard is explicit: Processor consumes P2 `CorporateAction` records and does not read `AdjustedDailyBar`, adjustment factors or adjusted OHLC values; Dataset price continuity remains P2 responsibility.
- Read-only subagent dispatch for SAL-P4-012 boundary exploration was attempted twice, but the host wrapper rejected optional `reasoning_effort` payloads; per lessons, fallback local senior review checked Ledger event semantics, P2 Dataset boundary, no adjusted-price double count, no-go scope and import boundary.
- Verification: Red target `1 error`; focused target `3 passed`; related CorporateActionLedger/PortfolioLedger/P2CorporateActions/AShareExecution/CostModel/Order/BacktestSpec/Architecture suite `41 passed`; full pytest `368 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no rebalance/target-weight generation, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `de50e5ff feat(P4): 实现公司行动入账`.
- Status-sync checkpoint: `c66555c3 docs: 同步 SAL-P4-012 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `07263d73 docs: 记录 SAL-P4-012 状态同步 hash`.

---

# SAL-P4-011 A-Share Execution Rules Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-011` by implementing a pure deterministic A-share execution model for formal portfolio backtests. Support T+1 sellability, trade unit checks, suspension, limit-up/down unfillable cases and audited unfilled-order policy. Do not start formal portfolio backtest runs, corporate-action processors, Risk/Metric/Audit, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 backtest docs, order/ledger/cost docs, ADR-009, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-011 boundaries; host wrapper rejected empty optional fields twice, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-a-share-execution-rules.md`.
- [x] Add Red contract tests for T+1 sellability, lot-size validation, suspension rejection, limit-up/down unfillable handling, keep-open vs expire policy, deterministic audit records and CostModel integration.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/execution.py` with immutable DTOs, Decimal math, `BacktestExecutionSpec` reuse, Order state-machine integration and cost-model binding.
- [x] Export A-share execution model symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/a-share-execution-rules.md` with scope, rules, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-011` done, P4 `11/22`, total `77/129`, decision/evidence rows and `SAL-P4-012` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-011` files and create the required Chinese checkpoint commit.

## Guardrails

- The execution model may accept/reject/expire/fill `Order` snapshots but must not generate strategy orders, mutate the ledger, process company actions, compute risk/metrics/audit, expose API/UI, start Qlib runtime or start Worker orchestration.
- Use `BacktestExecutionSpec` as the single execution parameter source; do not duplicate T+1, lot-size, suspension, limit or unfilled-order assumptions elsewhere.
- Same-bar close execution remains forbidden; close/after-close signals must execute on a later trade date.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion remain outside the formal portfolio backtest namespace.

## Review: SAL-P4-011

- Added `tests/quant/test_a_share_execution_rules.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.execution` (`1 error`), Green focused target is `6 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/execution.py` and exported symbols from `quant.backtest`; the module defines `AShareExecutionModel`, `AShareMarketSnapshot`, `ASharePositionAvailability`, `AShareExecutionResult`, `AShareExecutionAuditRecord` and execution constants.
- Execution model reuses `BacktestExecutionSpec`, `Order` and `CostModel`; it enforces same-date close signal rejection, lot-size guard, suspension/non-trading handling, T+1 sellable quantity, limit-up/down unfillable cases, limit-price crossing and CostModel participation before filling.
- Unfillable orders resolve through explicit `expire_after_rebalance`, `keep_open_until_cancelled` or `reject_order` policies with deterministic audit records; unsupported policies raise `AShareExecutionError`.
- Read-only subagent dispatch for SAL-P4-011 boundary exploration was attempted twice, but the host wrapper rejected empty optional fields; per lessons, fallback local senior review checked BacktestExecutionSpec reuse, order/cost binding, ledger/orchestration boundary, no-go scope and import boundary.
- Verification: Red target `1 error`; focused target `6 passed`; related AShareExecution/CostModel/Order/PortfolioLedger/BacktestSpec/Architecture suite `35 passed`; full pytest `365 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan found only historical SAL-P4-010 review text plus current SAL-P4-011/SAL-P4-012 anchors; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no company-action processor, no strategy-order generation, no ledger mutation, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `30efc785 feat(P4): 实现 A 股执行规则`.
- Status-sync checkpoint: `7c1e214c docs: 同步 SAL-P4-011 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `9acf345d docs: 记录 SAL-P4-011 状态同步 hash`.

---

# SAL-P4-010 Latest Status Refresh

> Started: 2026-07-25
> Scope: Refresh recovery docs after `SAL-P4-010` implementation checkpoint `e194984c`, status-sync checkpoint `e8ad2fd8`, status-sync hash-anchor `ca9eabf2` and final anchor `3a46eccc`; make completed vs unfinished work explicit, update lessons for the repeated habit reminder, and provide a copyable next-session prompt. Do not start `SAL-P4-011`, formal portfolio backtest, company actions, Risk/Metric/Audit, Quant Lab, Evidence Agent, Worker loop or real Provider/LLM calls in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoint chain.
- [x] Update `tasks/lessons.md` with the repeated status-refresh habit after `SAL-P4-010`.
- [x] Update `docs/development-status.md` with completed/unfinished scope, checkpoint anchors, current READY task and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the same recoverable status.
- [x] Run status-anchor scan and `git diff --check`, then create the required Chinese status review checkpoint commit.

## Review: SAL-P4-010 Latest Status Refresh

- Confirmed implementation checkpoint `e194984c feat(P4): 实现费用与滑点模型`.
- Confirmed status-sync checkpoint `e8ad2fd8 docs: 同步 SAL-P4-010 checkpoint hash`.
- Confirmed status-sync hash-anchor checkpoint `ca9eabf2 docs: 记录 SAL-P4-010 状态同步 hash`.
- Confirmed final anchor commit `3a46eccc docs: 固化 SAL-P4-010 hash-anchor checkpoint`.
- Current completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017` and `SAL-P4-001..010`; unfinished P4 work starts at `SAL-P4-011` A 股执行规则.
- Scope retained: no `SAL-P4-011` implementation, no formal portfolio backtest, no company-action processor, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Verification: `git diff --check` PASS; status-anchor scan for stale current `SAL-P4-010` READY / `75/129` / `P4 9/22` only matched historical `SAL-P4-009` review text, while current anchors point to `SAL-P4-011`, P4 `10/22` and total `76/129`.
- Status review checkpoint: `b84593d8 docs: 复核 SAL-P4-010 最新开发状态与恢复提示`.

---

# SAL-P4-010 Cost And Slippage Model Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-010` by implementing a pure deterministic fee, tax, slippage, impact and participation-rate cost model for formal portfolio backtests. Do not start formal portfolio backtest runs, A-share execution rules, corporate-action processors, Risk/Metric/Audit, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 backtest docs, order/ledger docs, ADR-009, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-010 boundaries; host wrapper rejected payload shape, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-cost-slippage-model.md`.
- [x] Add Red contract tests for buy/sell fee asymmetry, minimum commission, slippage/impact effective price, participation-rate rejection, deterministic records and ledger integration.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/costs.py` with immutable DTOs, Decimal math, `BacktestCostSpec` reuse, Order fill binding and participation guard.
- [x] Export Cost Model symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/cost-slippage-model.md` with scope, formulas, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-010` done, P4 `10/22`, total `76/129`, decision/evidence rows and `SAL-P4-011` READY but not started.
- [x] Run focused/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-010` files and create the required Chinese checkpoint commit.

## Review: SAL-P4-010

- Added `tests/quant/test_cost_slippage_model.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.costs` (`1 error`), Green focused target is `4 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/costs.py` and exported symbols from `quant.backtest`; the module defines `CostModel`, `CostBreakdown`, `CostLineItem`, cost model constants and `CostModelError`.
- Cost model reuses `BacktestCostSpec`, binds concrete `BacktestSpec.spec_hash`, validates Order fill membership, computes commission/min commission, sell-only stamp tax, transfer fee, slippage, impact, effective price and pre/post-cost cash amount, and rejects participation-rate breaches.
- Ledger integration remains explicit: callers pass `CostBreakdown.total_cost` into `PortfolioLedger.record_execution(...)`; CostModel does not mutate orders or ledgers.
- Read-only subagent dispatch for SAL-P4-010 boundary exploration was attempted, but the host wrapper rejected empty optional fields and then message/items payload shape; per lessons, fallback local senior review checked BacktestCostSpec reuse, buy/sell asymmetry, participation guard, ledger boundary, no-go scope and import boundary.
- Verification: Red target `1 error`; focused target `4 passed`; related CostModel/PortfolioLedger/Order/BacktestSpec/Architecture suite `29 passed`; full pytest `359 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no A-share T+1/lot/suspension/limit execution rules, no corporate-action processor, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `e194984c feat(P4): 实现费用与滑点模型`.
- Status-sync checkpoint: `e8ad2fd8 docs: 同步 SAL-P4-010 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `ca9eabf2 docs: 记录 SAL-P4-010 状态同步 hash`.

## Guardrails

- CostModel is a pure calculation layer; it may calculate explicit execution costs and effective prices, but it must not mutate orders or ledgers by itself.
- Use `BacktestCostSpec` as the single parameter source; do not duplicate cost assumptions elsewhere.
- Buy and sell cost asymmetry must be explicit: stamp tax applies to sell fills only; commission, transfer fee, slippage and impact apply to both sides.
- Participation-rate checks only reject impossible cost inputs; full A-share execution rules, T+1, lot rounding, suspension and limit-up/down remain `SAL-P4-011`.
- Keep legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion outside the formal portfolio backtest namespace.

---

# SAL-P4-009 Portfolio Ledger Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-009` by implementing a pure formal backtest Portfolio Ledger for cash, position lots, receivables/payables, execution replay, valuation snapshots and reconciliation invariants. Do not start formal portfolio backtest runs, fees/slippage models, A-share execution rules, corporate-action processors, Risk/Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/order-state-machine.md`, P4 backtest docs, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-portfolio-ledger.md`.
- [x] Add Red contract tests for initial cash, buy/sell executions, settlement, position lots, valuation, reconciliation equation, deterministic replay and event conflict rejection.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/ledger.py` with immutable DTOs, append-only events, replay, FIFO position lots, receivables/payables and equity equation checks.
- [x] Export Portfolio Ledger symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/portfolio-ledger.md` with scope, accounting semantics, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-009` done, P4 `9/22`, total `75/129`, decision/evidence rows and `SAL-P4-010` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-009` files and create the required Chinese checkpoint commit.

## Guardrails

- Portfolio Ledger is a pure domain/accounting layer; no order generation, matching engine, cost/slippage model, A-share execution model, corporate-action processor, RiskPolicy, metrics, API, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM call or Qlib runtime.
- Ledger events must be append-only and replayable; duplicate event IDs are idempotent only when payloads are identical.
- Equity must always reconcile as `cash + position_market_value + receivables - payables`.
- Costs may be recorded as explicit execution inputs, but fee/slippage calculation remains `SAL-P4-010`.
- Corporate action events remain out of scope until `SAL-P4-012`; this task only provides the ledger substrate later processors can consume.

## Review: SAL-P4-009

- Added `tests/quant/test_portfolio_ledger.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.ledger` (`1 error`), Green focused target is `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/ledger.py` and exported symbols from `quant.backtest`; the module defines `PortfolioLedger`, `LedgerEvent`, `LedgerEventType`, `PositionLot`, `ExecutionRecord` and `PortfolioLedgerError`.
- Ledger accounting covers initial cash, buy payable, sell receivable, cash settlement, valuation snapshot, FIFO lot reduction, realized P&L on explicit sell fills, equity reconciliation and deterministic replay.
- Contract guards reject sell quantity above current lots, over-settlement, missing valuation prices, spec/run/stage mismatch, non-fill order events, conflicting duplicate event IDs and Qlib/FastAPI/SQLAlchemy import boundary drift.
- Code-review subagent dispatch was attempted, but the host wrapper rejected empty optional fields and then repeated the same schema rejection; per lessons, fallback local senior review checked accounting semantics, replay idempotency, order binding, scope guard and import boundary.
- Verification: focused target `3 passed`; related suite `28 passed`; full pytest `355 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no fees/slippage model, no A-share execution rules, no corporate-action processor, no Risk/Metric/Audit/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `18d6782d feat(P4): 实现 Portfolio Ledger`.
- Status-sync checkpoint: `2d6f78a8 docs: 同步 SAL-P4-009 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `6ecb95d3 docs: 记录 SAL-P4-009 状态同步 hash`.
- Final anchor before this refresh: `dbc6f286 docs: 固化 SAL-P4-009 hash-anchor checkpoint`.
- Latest status review checkpoint: `1627ec4f docs: 复核 SAL-P4-009 最新开发状态与恢复提示`.
- User reminder review: latest docs now keep `SAL-P4-009` as completed, `SAL-P4-010` as the only READY task, P4 at `9/22`, total at `75/129`, and repeat the automatic status-sync/next-start-prompt habit for every future stage task.

---

# SAL-P4-008 Order State Machine Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-008` by defining formal portfolio backtest order intent, order events, state transitions, rejection, partial fill, expiration and idempotent replay. Do not start formal portfolio backtest runs, Ledger/Risk/Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls, A-share execution rules, fees/slippage, corporate-action ledger or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 evidence docs, ADR-009, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-order-state-machine.md`.
- [x] Add Red contract tests for created/accepted/partially_filled/filled/rejected/expired/cancelled transitions, invalid transition rejection, terminal-state immutability and idempotent replay.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/orders.py` with immutable DTOs, validation, append-only events, transition guards, deterministic `to_record()` and replay.
- [x] Export order state machine symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/order-state-machine.md` with scope, state/event semantics, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-008` done, P4 `8/22`, total `74/129`, decision/evidence rows and `SAL-P4-009` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-008` files and create the required Chinese checkpoint commit.

## Guardrails

- Order state machine is a pure contract/domain layer; no Ledger/cash/position replay, fees/slippage, A-share execution rules, corporate actions, RiskPolicy, metrics, API, Quant Lab, Evidence Agent, Worker loop, real Provider/LLM call or Qlib runtime.
- Every state change must be represented as an immutable event; replay must be deterministic and duplicate event IDs must be idempotent only when the payload is identical.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset conversion and Qlib internal backtest evidence stay outside the formal portfolio backtest namespace.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P4-008

- Added `tests/quant/test_order_state_machine.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.orders` (`1 error`), Green focused target is `5 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/orders.py` and exported symbols from `quant.backtest`; the module defines `OrderIntent`, `OrderEvent`, `Order`, `OrderSide`, `OrderType`, `TimeInForce`, `OrderStatus` and `OrderEventType` for `created/accepted/partially_filled/filled/rejected/expired/cancelled` states.
- Contract guards reject fill-before-accept, overfills, terminal mutations, conflicting duplicate `event_id` payloads, missing terminal reasons, invalid timestamps/quantities and invalid `BacktestSpec` hash binding; duplicate event IDs are idempotent only when payloads are identical.
- Added `docs/order-state-machine.md`, `DEC-072` and `AEV-074`; progress now moves to P4 `8/22`, total `74/129`, with `SAL-P4-009` Portfolio Ledger READY but not started.
- Code-review subagent dispatch was attempted, but the host wrapper repeatedly rejected optional field and `message`/`items` payload shapes; fallback local senior review checked transition semantics, replay idempotency, terminal states, import boundary and no-go scope.
- Verification: focused target `5 passed`; related suite `25 passed`; full pytest `352 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call, no fees/slippage, no A-share execution rules, no company-action ledger, no metrics/audit and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `4927ba6f feat(P4): 实现订单状态机`.
- Status-sync checkpoint: `e58823a4 docs: 同步 SAL-P4-008 checkpoint hash`.

---

# SAL-P4-007 Latest Status Refresh

> Started: 2026-07-25
> Scope: Refresh recovery docs after `SAL-P4-007` implementation checkpoint `6e81ae6f` and status-sync checkpoint `8bc892d4`; make completed vs unfinished work explicit, update lessons for the repeated habit reminder, and provide a copyable next-session prompt. Do not start `SAL-P4-008`, formal portfolio backtest, Qlib runtime, Ledger/Risk, Evidence Agent, Worker loop or real Provider/LLM calls in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoint chain.
- [x] Update `tasks/lessons.md` with the repeated status-refresh habit after `SAL-P4-007`.
- [x] Update `docs/development-status.md` with completed/unfinished scope, latest checkpoint anchors, current READY task and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the same recoverable status.
- [x] Run status-anchor scan and `git diff --check`, then create the required Chinese status review checkpoint commit.

## Review: SAL-P4-007 Latest Status Refresh

- Confirmed implementation checkpoint `6e81ae6f feat(P4): 实现 Qlib QuantEngine Adapter`.
- Confirmed status-sync checkpoint `8bc892d4 docs: 同步 SAL-P4-007 checkpoint hash`.
- Current completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, and `SAL-P4-001..007`; unfinished P4 work starts at `SAL-P4-008` Order state machine.
- Current READY task is `SAL-P4-008`; this sync did not start `SAL-P4-008`, formal portfolio backtest, Qlib runtime, Ledger/Risk, Evidence Agent, Worker loop or real Provider/LLM calls.
- Updated `tasks/lessons.md` to reinforce that every stage task must automatically finish with status docs, progress checklist, review notes, lessons when corrected, and a copyable next-session prompt.
- Status review checkpoint: `dc88df2d docs: 复核 SAL-P4-007 最新开发状态与恢复提示`.

---

# SAL-P4-007 Qlib QuantEngine Adapter Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-007` by implementing a Qlib QuantEngine Adapter boundary that wraps train/predict/backtest/evaluate_factor and Recorder metadata. Do not start a formal portfolio backtest run, Ledger/Risk/Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls, arbitrary module-path config, or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 evidence docs, Qlib isolation/conversion docs, ADR-009, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-qlib-quant-engine-adapter.md`.
- [x] Add Red contract tests for controlled config templates, run/stage/spec/dataset binding, fake-facade train/predict/backtest/evaluate_factor calls, Recorder mapping and no Qlib runtime import at module import.
- [x] Implement `src/serenity_alpha_lab/integrations/qlib/quant_engine_adapter.py` with immutable DTOs, injectable/lazy facade, deterministic evidence Artifact publishing and controlled template validation.
- [x] Export adapter symbols from `src/serenity_alpha_lab/integrations/qlib/__init__.py` without importing or initializing Qlib runtime.
- [x] Add `docs/qlib-quant-engine-adapter.md` with scope, config templates, Recorder mapping, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-007` done, P4 `7/22`, total `73/129`, decision/evidence rows and `SAL-P4-008` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-007` files and create the required Chinese checkpoint commit.

## Guardrails

- Qlib Adapter may wrap engine operations and Recorder metadata only inside the dedicated Quant Worker boundary; no FastAPI import/startup initialization.
- Config inputs must use approved template IDs and must not accept `module_path`, `class`, `module`, `import_path` or arbitrary dotted Python paths from API/UI/YAML/strategy payloads.
- Qlib internal backtest output is engine evidence only in this task; formal orders/fills/ledger/risk/metrics/audit remain `SAL-P4-008..016`.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result and Dataset conversion artifacts must stay outside the formal portfolio backtest namespace.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P4-007

- Added `tests/integrations/test_qlib_quant_engine_adapter.py`; initial Red failed with missing `serenity_alpha_lab.integrations.qlib.quant_engine_adapter` (`1 error`), Green focused target is `4 passed`.
- Added `src/serenity_alpha_lab/integrations/qlib/quant_engine_adapter.py` and exported symbols from `integrations.qlib`; the module defines controlled `QlibQuantEngineTemplate`, `QlibQuantEngineConfig`, `QlibQuantEngineRequest`, injectable/lazy facade boundary, `QlibRecorderSnapshot`, step result and run report contracts.
- Adapter wraps `train`, `predict`, `backtest` and `evaluate_factor` through an injected facade, publishes deterministic `integration.qlib.quant_engine_step@1.0.0` artifacts and compact `integration.qlib.quant_engine_run_report@1.0.0`, and tags Recorder metadata with platform `run_id`, `stage_id`, `trace_id` and `BacktestSpec.spec_hash`.
- Contract guards reject unknown templates and arbitrary module path fields (`module_path`, `module`, `class`, `class_name`, `import_path`), require concrete platform context and `QlibDatasetConversionArtifacts`, and keep Qlib/FastAPI/SQLAlchemy out of import-time AST.
- Code-review subagent dispatch was attempted, but the host wrapper rejected payload shape with message/items conflicts; fallback local senior review checked ADR-009 compliance, runtime import boundary, config path guards, Recorder mapping, deterministic artifact payloads and no-go scope.
- Verification: focused target `4 passed`; related suite `23 passed`; full pytest `347 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no orders/fills, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift; Qlib internal backtest remains adapter evidence only.
- Implementation checkpoint: `6e81ae6f feat(P4): 实现 Qlib QuantEngine Adapter`.

---

# SAL-P4-006 Latest Status Refresh

> Started: 2026-07-25
> Scope: Refresh recovery docs after `SAL-P4-006` checkpoints `1c5c6e81`, `76089299`, `64c7998e` and final anchor `ea244bdc`; make completed vs unfinished work explicit, update lessons for the repeated habit reminder, and provide a copyable next-session prompt. Do not start `SAL-P4-007`, Qlib runtime, formal portfolio backtest, Ledger/Risk, Evidence Agent, Worker loop or real Provider/LLM calls in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoint chain.
- [x] Update `tasks/lessons.md` with the repeated status-refresh habit after `SAL-P4-006`.
- [x] Update `docs/development-status.md` with completed/unfinished scope, latest checkpoint anchors, current READY task and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the same recoverable status.
- [x] Run status-anchor scan and `git diff --check`, then create the required Chinese status review checkpoint commit.

## Review: SAL-P4-006 Latest Status Refresh

- Confirmed implementation checkpoint `1c5c6e81 feat(P4): 实现 Dataset 到 Qlib 转换`.
- Confirmed status-sync checkpoint `76089299 docs: 同步 SAL-P4-006 checkpoint hash`.
- Confirmed status-sync hash-anchor checkpoint `64c7998e docs: 记录 SAL-P4-006 状态同步 hash`.
- Confirmed final anchor commit `ea244bdc docs: 固化 SAL-P4-006 hash-anchor checkpoint`.
- Current completed scope remains `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, and `SAL-P4-001..006`; current READY task is `SAL-P4-007` Qlib QuantEngine Adapter.
- Scope retained: no `SAL-P4-007` implementation, no Qlib runtime, no formal portfolio backtest, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no `upstream/dsa-v3.26.1` tag movement.
- Status review checkpoint: `459bc76e docs: 复核 SAL-P4-006 最新开发状态与恢复提示`.

---

# SAL-P4-006 Qlib Dataset Conversion Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-006` by converting passed, immutable platform Dataset versions into Qlib calendar/instrument/feature artifacts with bidirectional field mapping. Do not initialize Qlib runtime, do not start formal portfolio backtest runs, Qlib Adapter, Ledger/Risk/Quant Lab, Evidence Agent, real Provider/LLM calls, Worker loop, or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P4 evidence docs, ADR-009, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-qlib-dataset-conversion.md`.
- [x] Add Red contract tests for Dataset-to-Qlib calendar/instrument/feature conversion, field lineage, passed/published manifest guard, deterministic Artifact publication and no Qlib runtime import.
- [x] Implement `src/serenity_alpha_lab/integrations/qlib/dataset_converter.py` with immutable DTOs, deterministic bytes, conversion warnings and ArtifactStore publication.
- [x] Export converter symbols from `src/serenity_alpha_lab/integrations/qlib/__init__.py` without importing Qlib runtime.
- [x] Add `docs/qlib-dataset-conversion.md` with source Dataset requirements, output artifacts, field mapping, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-006` done, P4 `6/22`, total `72/129`, `DEC-070`, `AEV-072`, and `SAL-P4-007` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-006` files and create the required Chinese checkpoint commit.

## Guardrails

- Converter inputs must bind concrete `dsv_*` Dataset versions with `quality_status=passed` and `publication_status=published`; no `latest`, held, quarantined or blocking Dataset may feed Qlib conversion.
- Calendar dates, instrument code mapping, adjustment mode, missing bars and field lineage must preserve platform Dataset semantics and be visible in the conversion summary.
- This task generates deterministic offline artifacts only; it must not call `qlib.init`, import Qlib runtime, run train/predict/backtest, generate orders/fills, replay ledger, compute metrics, expose APIs, or start Worker loops.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation and Screen result must stay outside the formal portfolio backtest namespace.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P4-006

- Added `tests/integrations/test_qlib_dataset_conversion.py`; initial Red failed with missing `serenity_alpha_lab.integrations.qlib.dataset_converter` (`1 error`), Green focused target is `8 passed`.
- Added `src/serenity_alpha_lab/integrations/qlib/dataset_converter.py` and exported symbols from `integrations.qlib`; the module converts passed/published `TradingCalendarDataset`, `InstrumentMasterDataset` and `AdjustedDailyBarsDataset` inputs to deterministic Qlib calendar, instrument, feature, field-mapping and compact summary artifacts.
- Contract guards require concrete `dsv_*` `DatasetVersionManifest` inputs, matching Dataset schema names/versions, `quality_status=passed`, `publication_status=published`, non-empty calendar/features and no Qlib/FastAPI/SQLAlchemy runtime imports.
- Added `docs/qlib-dataset-conversion.md`, `DEC-070` and `AEV-072`; progress now moves to P4 `6/22`, total `72/129`, with `SAL-P4-007` READY but not started.
- Code-review subagent dispatch was attempted, but the host wrapper rejected payloads with empty optional fields and message/items exclusivity; fallback local senior review checked deterministic bytes, source lineage, schema/status guards, runtime import boundary and no-go scope.
- Verification: focused target `8 passed`; related suite `52 passed`; full pytest `343 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan and `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no `qlib.init`, no Qlib Adapter, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `1c5c6e81 feat(P4): 实现 Dataset 到 Qlib 转换`.
- Status-sync checkpoint: `76089299 docs: 同步 SAL-P4-006 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `64c7998e docs: 记录 SAL-P4-006 状态同步 hash`.

---

# SAL-P4-005 Qlib Version And Isolation Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-005` by locking the Qlib/pyqlib dependency version, documenting license/platform/dependency evidence, and freezing the Quant Worker isolation/resource policy. Do not start formal portfolio backtest runs, Qlib runtime initialization, Ledger/Risk/Quant Lab, Evidence Agent, real Provider/LLM calls, Worker loop, or legacy DSA Backtest API changes.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/dsa-signal-evaluation-characterization.md`, `docs/signal-evaluation-engine.md`, `docs/backtest-spec.md`, `docs/backtest-artifact.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-qlib-version-isolation.md`.
- [x] Add Red architecture tests for exact `pyqlib==0.9.7` quant extra pin, production/Desktop requirements exclusion, Qlib evidence docs, worker-only policy, no FastAPI/runtime import, and no formal backtest execution.
- [x] Lock `pyproject.toml` quant extra to exact `pyqlib==0.9.7` and refresh `uv.lock` without adding Qlib to production `requirements.txt`.
- [x] Add Qlib isolation policy module under `src/serenity_alpha_lab/integrations/qlib/` without importing Qlib.
- [x] Add `docs/qlib-version-isolation.md` and ADR-009 with license, dependency, platform compatibility, upgrade/stop-use conditions, and Worker resource isolation.
- [x] Update progress checklist/status docs with `SAL-P4-005` done, P4 `5/22`, total `71/129`, `DEC-069`, `AEV-071`, and `SAL-P4-006` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-005` files and create the required Chinese checkpoint commit.

## Guardrails

- Qlib is optional `quant` extra only; production/Desktop `requirements.txt` must continue to exclude `pyqlib`.
- Qlib may be initialized only in a dedicated Quant Worker process after `run_id` / `stage_id` context exists; never in FastAPI import/startup or shared application/domain modules.
- This task freezes version and isolation policy only; it must not convert datasets, invoke `qlib.init`, run Qlib workflows, create orders/fills, replay ledger, compute risk/metrics, expose backtest API, or start Worker loops.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation and Screen result must stay outside the formal portfolio backtest namespace.

## Review: SAL-P4-005

- Added `tests/architecture/test_qlib_version_isolation.py`; initial Red failed with missing exact pin/doc/ADR/policy module (`4 failed, 1 passed`), Green target now `5 passed`.
- Updated `pyproject.toml` to lock `pyqlib==0.9.7` under optional `quant` only, refreshed `uv.lock`, and verified `scripts/verify-python-dependency-lock.sh` keeps production/Desktop `requirements.txt` free of `pyqlib`.
- Added `src/serenity_alpha_lab/integrations/qlib/runtime_policy.py` and exports; the module imports no Qlib/FastAPI/SQLAlchemy runtime and freezes `worker-quant`, dedicated process, 2 CPU, 4096MB, 3600s timeout, 15s heartbeat and 300s checkpoint defaults.
- Added `docs/qlib-version-isolation.md` and `docs/adr/ADR-009-qlib-adapter-boundary-and-version-upgrade-strategy.md` documenting MIT license classifier, Python/platform wheel compatibility, direct dependencies, upgrade/stop-use conditions, and Qlib worker-only constraints.
- Updated `docs/python-dependency-lock.md`, progress/status docs, `DEC-069`, `AEV-071`; `SAL-P4-006` is now READY but not started.
- Verification: target `5 passed`; related Qlib/dependency/architecture suite `23 passed`; full pytest `335 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan and `git diff --check` PASS.
- Scope retained: no formal portfolio backtest run, no `qlib.init`, no Dataset-to-Qlib conversion, no Qlib Adapter, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `82580fdb feat(P4): 锁定 Qlib 版本与隔离方案`.
- Status-sync checkpoint: `800bef4e docs: 同步 SAL-P4-005 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `ee5761ba docs: 记录 SAL-P4-005 状态同步 hash`.
- Latest status refresh checkpoint: `6bbca629 docs: 复核 SAL-P4-005 最新开发状态与恢复提示`; it keeps `SAL-P4-006` as READY and did not start any forbidden runtime or formal portfolio backtest work.

---

# SAL-P4-004 BacktestArtifact Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-004` by defining the formal `BacktestArtifact` output contract and compact bundle manifest. Do not run formal portfolio backtests, Evidence Agent, real Provider/LLM, Qlib, Ledger, Risk, Quant Lab or Worker loop. Legacy DSA Signal Evaluation, AlphaSift T+N evaluation and Screen result stay outside the formal portfolio backtest namespace.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/dsa-signal-evaluation-characterization.md`, `docs/signal-evaluation-engine.md`, `docs/backtest-spec.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-backtest-artifact.md`.
- [x] Add Red contract tests for required orders/executions/positions/cash/equity/metrics/audit outputs, URI-only large result descriptors, preview/formal/partial/invalid states, deterministic bundle summary publishing and invalid contract rejection.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/artifacts.py` with immutable DTOs, validation, compact `to_record()`, deterministic JSON bytes and ArtifactStore publication.
- [x] Export BacktestArtifact symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/backtest-artifact.md` with output schema map, state semantics, URI-only API boundary, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-004` done, P4 `4/22`, total `70/129`, `DEC-068`, `AEV-070`, and `SAL-P4-005` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-004` files and create the required Chinese checkpoint commit.

## Guardrails

- `BacktestArtifact` is only a formal portfolio backtest output contract; no order generation, fill matching, ledger replay, metrics computation, Qlib adapter, API, UI or Worker execution in this task.
- Large tabular outputs must be represented by `ArtifactManifest`/URI plus schema, row count and content hash; API summaries must not embed full DataFrames or rows.
- Bundle states must distinguish `preview`, `formal`, `partial` and `invalid`; invalid/partial bundles must carry explicit errors or warnings.
- Legacy `/api/v1/backtest/*`, DSA Signal Evaluation, AlphaSift T+N evaluation and Screen results must not be named or treated as formal portfolio backtests.

## Review: SAL-P4-004

- Added `tests/quant/test_backtest_artifact.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.artifacts` (`1 error`), Green target now `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/artifacts.py` and exported symbols from `quant.backtest`; the module defines immutable `BacktestOutputArtifact`, `BacktestArtifactBundle`, required output kind/state enums, compact canonical JSON bytes and `ArtifactStore` publication.
- Contract guards require orders/executions/positions/cash/equity_curve/metrics/audit descriptors, concrete `dsv_*` Dataset Versions, matching manifest/content hashes and valid `preview/formal/partial/invalid` state payloads; it rejects `legacy_signal_evaluation` engine scope.
- Added `docs/backtest-artifact.md`, `DEC-068`, `AEV-070`; updated progress/status docs so `SAL-P4-004` is DONE, P4 is `4/22`, total is `70/129`, and `SAL-P4-005` is READY.
- Verification: target `3 passed`; related P4/Architecture suite `15 passed`; full pytest `330 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Code-review subagent dispatch was attempted but the host wrapper repeatedly rejected `message`/`items` payload shape; fallback local senior review checked URI-only output boundaries, required output coverage, state validation, deterministic summary publishing, no execution entrypoints and no-go boundaries.
- Scope retained: no formal portfolio backtest run, no Qlib runtime, no order generation/fill matching, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `471e5857 feat(P4): 定义正式 BacktestArtifact`; status-sync checkpoint: `87dae329 docs: 同步 SAL-P4-004 checkpoint hash`.

---

# SAL-P4-003 BacktestSpec Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-003` by defining the formal `BacktestSpec` input contract and canonical hash. Do not run formal portfolio backtests, Evidence Agent, real Provider/LLM, Qlib, Ledger, Risk engine, Quant Lab or Worker loop. Legacy DSA Signal Evaluation remains only a compatibility surface.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/dsa-signal-evaluation-characterization.md`, `docs/signal-evaluation-engine.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-backtest-spec.md`.
- [x] Add Red contract tests for formal Dataset/Universe/Strategy/Execution/Cost/Risk inputs, canonical hash stability, concrete Dataset Version guards, legacy Signal Evaluation rejection and same-bar close execution rejection.
- [x] Implement `src/serenity_alpha_lab/quant/backtest/spec.py` with immutable DTOs, validation, `to_record()`, canonical JSON and `spec_hash`.
- [x] Export BacktestSpec symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py`.
- [x] Add `docs/backtest-spec.md` with formal scope, canonical hash semantics, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-003` done, P4 `3/22`, total `69/129`, `DEC-067`, `AEV-069`, and `SAL-P4-004` READY but not started.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-003` files and create the required Chinese checkpoint commit.

## Guardrails

- `BacktestSpec` is only a formal portfolio backtest input contract; no order generation, fills, ledger replay, metrics, Qlib adapter, API, UI or Worker execution in this task.
- Legacy `/api/v1/backtest/*`, DSA Signal Evaluation, AlphaSift T+N evaluation and Screen results must not be named or treated as formal portfolio backtests.
- Canonical hash must exclude wall-clock/runtime state and be stable across mapping insertion order.
- Formal inputs must bind concrete `dsv_*`, `sdv_*`, `fdv_*`, `sha256:*`, signal timing, execution timing, initial capital, benchmark, fees, risk limits and random seed.

## Review: SAL-P4-003

- Added `tests/quant/test_backtest_spec.py`; initial Red failed with missing `serenity_alpha_lab.quant.backtest.spec` (`1 error`), Green target now `3 passed`.
- Added `src/serenity_alpha_lab/quant/backtest/spec.py` and exported symbols from `quant.backtest`; the module defines immutable Dataset/Universe/Strategy/Execution/Cost/Risk DTOs, `BacktestSpec`, canonical JSON and `spec_hash`.
- Contract guards reject `latest` Dataset alias, missing Dataset hashes, invalid `dsv_*`/`sdv_*`/`ssn_*`/`fdv_*`/`sha256:*` values, legacy Signal Evaluation strategy kind and same-bar close signal execution.
- Added `docs/backtest-spec.md`, `DEC-067`, `AEV-069`; updated progress/status docs so `SAL-P4-003` is DONE, P4 is `3/22`, total is `69/129`, and `SAL-P4-004` is READY.
- Verification: target `3 passed`; related P4/Architecture suite `26 passed`; full pytest `327 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check `0001..0005` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Code-review subagent dispatch was attempted but the client wrapper repeatedly rejected `message`/`items` payload shape; fallback local senior review checked hash determinism, version guards, scope boundaries, no execution entrypoints and status anchors.
- Scope retained: no `BacktestArtifact`, no formal portfolio backtest run, no Qlib, no orders/fills, no Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call and no legacy `/api/v1/backtest/*` drift.
- Implementation checkpoint: `1ecfaa2d feat(P4): 定义正式 BacktestSpec`; follow-up status-sync checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P4-002 SignalEvaluationEngine Migration Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-002` by migrating DSA Signal Evaluation semantics to `SignalEvaluationEngine`, preserving legacy `/api/v1/backtest/*` compatibility and keeping `SAL-P4-001` snapshots byte-for-byte identical. Do not start formal portfolio backtesting, Evidence Agent, real Provider/LLM calls or `BacktestSpec`; `SAL-P4-003` must wait until this task is complete.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/dsa-signal-evaluation-characterization.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-signal-evaluation-engine.md`.
- [x] Add Red root quant tests proving `SignalEvaluationEngine` exactly matches `SAL-P4-001` engine, structured signal and summary snapshots.
- [x] Add Red architecture test proving the DSA compatibility patch introduces `SignalEvaluationEngine`, `evaluation_type=signal`, and UI Signal Evaluation wording without starting formal backtest APIs.
- [x] Implement `src/serenity_alpha_lab/quant/signal_evaluation.py` and export the new engine.
- [x] Add DSA patch `0005-migrate-signal-evaluation-engine.patch` that keeps legacy Backtest API paths/schemas compatible while migrating service/UI naming.
- [x] Verify `scripts/run-dsa-signal-evaluation-characterization.sh` keeps all `SAL-P4-001` snapshots unchanged.
- [x] Add `docs/signal-evaluation-engine.md` with migration semantics, compatibility boundary, `evaluation_type=signal`, verification evidence and non-goals.
- [x] Update progress checklist/status docs with `SAL-P4-002` done, P4 `2/22`, total `68/129`, `DEC-066`, `AEV-068`, and `SAL-P4-003` READY but not started.
- [x] Run target, related, full Python, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Review, stage only `SAL-P4-002` files and create the required Chinese checkpoint commit.

## Guardrails

- `SAL-P4-001` snapshot JSON must remain byte-for-byte identical; any route/schema change that alters `api-surface.json` is out of scope.
- Legacy `/api/v1/backtest/*`, `Backtest*` schema names and Agent `get_*_backtest_summary` tools remain compatibility surfaces only.
- New semantics must be named `SignalEvaluationEngine` with `evaluation_type=signal`; visible UI copy should describe signal evaluation, not portfolio strategy backtesting.
- No `BacktestSpec`, Qlib, ledger, order/execution, portfolio risk, Quant Lab, Evidence Agent, Worker loop or real Provider/LLM call in this task.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.


## Review: SAL-P4-002

- Added `tests/quant/test_signal_evaluation_engine.py`; initial Red failed with missing `serenity_alpha_lab.quant.signal_evaluation`, Green root parity is `3 passed` against `SAL-P4-001` text signal, structured DecisionSignal and summary goldens.
- Added `src/serenity_alpha_lab/quant/signal_evaluation.py` and exported `SignalEvaluationEngine`, `SignalEvaluationConfig`, `evaluation_type=signal`, `semantic_scope=legacy_signal_evaluation`, plus compatibility aliases for legacy `BacktestEngine` naming.
- Added `tests/architecture/test_dsa_signal_evaluation_engine_migration.py`; Red initially failed because patch `0005` was missing, then captured and fixed the registered-new-file guard gap in `scripts/run-dsa-signal-evaluation-characterization.sh`.
- Added `DSA-PATCH-005` with DSA `src/core/signal_evaluation_engine.py`, backend service migration, diagnostics metadata and DSA Web visible copy changed to “信号评价 / Signal Evaluation” while preserving legacy `/backtest` and `/api/v1/backtest/*` compatibility.
- Added `docs/signal-evaluation-engine.md`; updated `docs/upstream-patches.md`, `docs/development-progress-checklist.md`, `docs/development-status.md`, `DEC-066`, `AEV-068`, and moved `SAL-P4-003` to READY without starting it.
- Verification: root + migration + characterization suite `11 passed`; DSA Web focused Vitest `3 files / 26 passed`; DSA Python focused suite `95 passed, 1 warning`; P4-001 snapshot script PASS; DSA patch check `0001..0005` already applied; full pytest `324 passed, 3 skipped`; compileall PASS; dependency lock guard PASS; immutable tag check PASS; status-anchor scan PASS; `git diff --check` PASS. Commit step is being completed in this checkpoint.
- Scope retained: no `BacktestSpec`, no formal portfolio backtest run, no Qlib/Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call, no baseline JSON drift and no tag movement.
- Implementation checkpoint: `6760b838 feat(P4): 迁移 SignalEvaluationEngine 语义`; follow-up status-sync checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P4-001 DSA Signal Evaluation Characterization Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P4-001` by locking current DSA `BacktestEngine` / Signal Evaluation behavior, legacy `/api/v1/backtest/*` API schemas and Agent read-tool surfaces. Do not start `SAL-P4-002`, define `BacktestSpec`, execute formal portfolio backtests, start Evidence Agent, call real Provider/LLM, start Worker execution loop or migrate DSA runtime source.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, Gate G3/P4 entry evidence, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-dsa-signal-evaluation-characterization.md`.
- [x] Add Red characterization tests for P4 Signal Evaluation baseline files, required behavior cases, API surface metadata and non-formal-backtest naming boundary.
- [x] Add deterministic `scripts/run-dsa-signal-evaluation-characterization.sh` with locked DSA worktree validation and snapshot diff/update flow.
- [x] Generate committed P4 baseline snapshots under `docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/`.
- [x] Add `docs/dsa-signal-evaluation-characterization.md` with semantics, API goldens, accepted risks, explicit non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P4-001` done status, P4 `1/22`, total `67/129`, `DEC-065`, `AEV-067` and `SAL-P4-002` READY.
- [x] Update `docs/development-status.md` and this review with latest completed/unfinished ranges, checkpoint anchors and copyable next-session prompt.
- [x] Run target/baseline/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Perform review, stage only `SAL-P4-001` files and create the required Chinese checkpoint commit.

## Guardrails

- DSA `BacktestEngine` and `/api/v1/backtest/*` names are legacy Signal Evaluation surfaces only; this task must not call them formal portfolio backtests.
- P4-001 freezes current behavior and goldens; it must not rename code to `SignalEvaluationEngine` because that is `SAL-P4-002`.
- Formal `BacktestSpec`, Qlib, ledger, order/execution, portfolio risk, Quant Lab, Evidence Agent, real Provider/LLM calls and Worker execution remain out of scope.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P4-001

- Added `tests/architecture/test_dsa_signal_evaluation_characterization.py`; initial Red target failed with missing P4 baseline/script/doc (`5 failed`), Green target now `5 passed`.
- Added `scripts/run-dsa-signal-evaluation-characterization.sh` and 7 committed snapshots under `docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/`; script output confirms snapshots match the locked DSA worktree.
- Added `docs/dsa-signal-evaluation-characterization.md` documenting DSA `BacktestEngine` semantics, legacy `/api/v1/backtest/*` API goldens, Agent read-tool scope, summary metrics, non-goals and P4 follow-on constraints.
- Updated `docs/development-progress-checklist.md`: `SAL-P4-001` is DONE, P4 is `1/22`, total progress is `67/129`, `DEC-065` and `AEV-067` are registered, `SAL-P4-002` is READY, and `SAL-P4-003` now depends on `SAL-P4-002`.
- Updated `docs/development-status.md` and next-session prompt to resume at `SAL-P4-002` while keeping Gate G4 unpassed and formal BacktestSpec blocked until Signal Evaluation naming is migrated.
- Verification: target `5 passed`; baseline script PASS; related architecture suite `32 passed`; full pytest `317 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check reports `0001..0004` already applied; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan and `git diff --check` PASS.
- Review: code-review subagent dispatch was attempted but the client rejected payloads around empty optional fields and `message`/`items` conflicts; fallback local review checked script path safety, snapshot determinism, API/tool semantics, status anchors and no-go boundaries, and fixed one wording issue so `SAL-P4-003` explicitly waits for `SAL-P4-002`.
- Scope retained: no `SAL-P4-002` implementation, no `BacktestSpec`, no formal portfolio backtest, no Qlib/Ledger/Risk/Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM call, no DSA runtime source migration, no dependency surface change and no tag movement.
- Implementation checkpoint: `31eebf67 feat(P4): 锁定 DSA Signal Evaluation 行为`; follow-up status-sync checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P3-017 Gate G3 Screen Factor Review Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P3-017` by reviewing and approving P3 Screen/Factor outputs as P4 inputs. Reuse all `SAL-P3-001..016` evidence, especially `docs/screen-performance-reproducibility.md`. Do not start Quant Core/Qlib implementation, formal backtest execution, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P3 evidence docs, `docs/screen-performance-reproducibility.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-gate-g3-screen-factor-review.md`.
- [x] Add Red Gate G3 tests for review document existence and executable offline contract coverage across AlphaSift, factors, screening, API, ProblemDetails, Trace, Artifact, Dataset/Manifest and Run/Stage/Event.
- [x] Add `docs/gate-g3-screen-factor-review.md` with Gate conclusion, P3 task evidence matrix, pass/fail conditions, accepted risks and P4 entry constraints.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P3-017` done status, P3 `17/17`, total `66/129`, `DEC-064` and `AEV-066`.
- [x] Update `docs/development-status.md` and this review with latest completed/unfinished ranges, checkpoint anchors and copyable next-session prompt.
- [x] Run target/related/full Python verification, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.
- [x] Perform review, stage only `SAL-P3-017` files and create the required Chinese checkpoint commit.

## Guardrails

- Gate G3 may approve Screen/Factor contracts as P4 inputs, but must not implement or execute Quant Core/Qlib, formal backtesting, Evidence Agent, real Provider/LLM calls or Worker runtime.
- Approval must be grounded in `SAL-P3-001..016` evidence and must explicitly cover Screen Lab, Quant Screening API, ScreenSnapshot, ScreenDefinition Pipeline, CandidateBatch, FactorDefinition, Factor Evaluation, Dataset Catalog/Manifest, ProblemDetails, Trace, Artifact, Run/Stage/Event and performance/reproducibility.
- Any data, bias or reproducibility gap must block affected ScreenDefinition versions from entering P4 formal backtest.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-017

- Added `docs/gate-g3-screen-factor-review.md` with Gate G3 conclusion `GO with accepted risks`, P3 task evidence matrix, accepted risks, P4 entry constraints and explicit no-go boundaries.
- Added `tests/gates/test_gate_g3_screen_factor_review.py`; Red failed on missing Gate G3 review doc (`1 failed, 1 passed`), Green target `2 passed`.
- Executable Gate G3 test covers 15 base factors, Factor Evaluation Artifact, ScreenDefinition L0-L4 trace, ScreenSnapshot Artifact, performance/reproducibility report, Quant Screening API idempotency/replay/pagination, ProblemDetails trace, concrete Dataset Version guard and Run/Stage/Event lifecycle.
- Updated `docs/development-progress-checklist.md`: `SAL-P3-017` is DONE, P3 is `17/17`, total progress is `66/129`, P4 is READY, `SAL-P4-001` is READY, `DEC-064` and `AEV-066` are registered.
- Updated `docs/development-status.md` and next-session prompt to restore at P4/G4 with `SAL-P4-001` as the next task.
- Verification: target `2 passed`; related Gate/P3 suite `24 passed`; full pytest `312 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check reports `0001..0004` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; status-anchor scan and `git diff --check` PASS.
- Review: code-review subagent dispatch was attempted three times, but the client rejected payloads with empty optional fields or `message`/`items` conflicts; fallback local senior review checked Gate scope, evidence coverage, executable contract assertions, status anchors, P4 entry constraints and staged-file boundaries.
- Scope retained: no Quant Core/Qlib implementation, no formal backtest execution, no Evidence Agent, no real Provider/LLM calls, no Worker execution loop, no DSA runtime source migration, no dependency surface change and no tag movement.
- Implementation checkpoint: `a1078532 docs(P3): 通过 Gate G3 筛选与因子评审`; follow-up status-sync checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P3-016 Screen Performance And Reproducibility Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P3-016` by adding a deterministic screening performance/reproducibility acceptance layer that reuses Screen Lab, Quant Screening API, ScreenSnapshot, ScreenDefinition Pipeline, CandidateBatch, FactorDefinition, Factor Evaluation, Dataset Catalog/Manifest, ProblemDetails, Trace, Artifact and Run/Stage/Event contracts. Do not start `SAL-P3-017`, Quant Core/Qlib, formal backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read required handoff docs, current Git state, TDD/verification/plan skills, Screen Lab/API/snapshot/pipeline implementation and SAL-P3-016 acceptance.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-screen-performance-reproducibility.md`.
- [x] Add Red contract tests for screening performance budget, stage timing/memory samples, incremental baseline, deterministic result hash, repeated snapshot reproducibility, fixed Run Bundle and deterministic Artifact publication.
- [x] Implement `quant.screening.performance` with immutable DTOs, budget evaluation, canonical result hashing, run bundle generation, reproducibility comparison and ArtifactStore publishing.
- [x] Export performance/reproducibility symbols from `quant.screening`.
- [x] Add `docs/screen-performance-reproducibility.md` with SLO/budget, run bundle schema, reproducibility semantics, non-goals and verification evidence.
- [x] Update progress checklist, development status, evidence/decision registers and this review.
- [x] Run target, related, full Python, compileall, dependency lock guard, patch check, immutable tag check and `git diff --check`.
- [x] Perform local senior review, stage only SAL-P3-016 files and create the required Chinese checkpoint commit.

## Guardrails

- Reproducibility hash must be derived from concrete `dsv_*` Dataset Versions, `sdv_*` ScreenDefinition, engine/code versions and canonical ScreenSnapshot result rows, not from wall-clock time or run-specific trace IDs.
- Performance report must preserve stage traces, timing, memory and capacity budgets without reimplementing ScreenDefinition Pipeline or ScreenSnapshot logic.
- Incremental baseline is an acceptance record over existing Factor DAG/cache and screen inputs; this task must not execute real factor values, Worker loops, Quant Core/Qlib or formal backtests.
- Fixed Run Bundle must retain `as_of`, dataset/schema/trace/run/stage, snapshot/pipeline ids, result hash and optional Artifact manifests for Screen Lab/API consumption.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-016

- Added `src/serenity_alpha_lab/quant/screening/performance.py` with immutable `ScreenPerformanceBudget`, `ScreenStagePerformanceSample`, `ScreenIncrementalBaseline`, `ScreenRunBundle`, `ScreenReproducibilityCheck` and `ScreenPerformanceReport`.
- Added canonical `screen_result_hash()` and fixed Run Bundle generation; the result hash binds code version, engine version, `sdv_*`, `as_of`, concrete `dsv_*` versions and canonical `ScreenSnapshot.results`, while excluding wall-clock time, trace/run/stage ids and snapshot/pipeline ids.
- Added deterministic report Artifact publication and SLO/budget failure codes for common screening duration, cached query duration, peak memory, result rows, incremental recompute ratio and reproducibility drift.
- Fixed an existing import cycle by making Quant Screening API exports lazy in `application.__init__`; direct `from serenity_alpha_lab.application import QuantScreeningApiService` remains supported.
- Local senior review found and fixed one report consistency issue: observed `result_row_count` now comes from `ScreenSnapshot` result rows rather than the last stage sample.
- Code-review subagent dispatch was attempted repeatedly, but the host wrapper rejected payloads with empty optional `items`/`reasoning_effort`; fallback was local senior review over the focused diff plus fresh verification.
- Verification: target `3 passed`; import-cycle check PASS; related suite `41 passed`; full pytest `310 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; DSA patch check reports `0001..0004` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope retained: no `SAL-P3-017`, Quant Core/Qlib, formal backtest, Evidence Agent, real Provider/LLM call, Worker execution loop, DSA runtime source migration, dependency surface change or tag movement.
- Implementation checkpoint: `e7569c83 feat(P3): 实现筛选性能与复现验收`; status-sync checkpoint: `4f7dd5dc docs: 同步 SAL-P3-016 checkpoint hash`; final status-review checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P3-015 Latest Status Refresh And Habit Reinforcement

> Started: 2026-07-25
> Scope: Refresh recovery documents after `SAL-P3-015` implementation/status checkpoints, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-016` implementation in this sync.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist anchors, current Git status and recent commits.
- [x] Confirm latest implementation checkpoint `847e5263 feat(P3): 实现 Screen Lab`, latest landed status-sync checkpoint `fa0ba469 docs: 同步 SAL-P3-015 checkpoint hash`, and latest landed status-review checkpoint `3c19b937 docs: 复核 SAL-P3-015 最新开发状态`.
- [x] Reconfirm completed scope through `SAL-P3-015`, unfinished scope from `SAL-P3-016`, Gate G3 not passed, and strict no-go boundaries.
- [x] Update `docs/development-status.md`, `docs/development-progress-checklist.md`, this review, and `tasks/lessons.md` with the repeated habit reminder.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P3-015 Latest Status Refresh And Habit Reinforcement

- Confirmed branch `codex/p0-baseline-status` was clean before edits and ahead of origin by 98 commits.
- Confirmed latest log before edits: `3c19b937 docs: 复核 SAL-P3-015 最新开发状态`, `fa0ba469 docs: 同步 SAL-P3-015 checkpoint hash`, `847e5263 feat(P3): 实现 Screen Lab`.
- Updated recovery status so the completed range remains explicit through `SAL-P3-015`, unfinished work begins at `SAL-P3-016`, and Gate G3 remains unpassed.
- Updated next-session guidance so only `SAL-P3-016` is next; `SAL-P3-017`, Quant Core, formal backtest, Evidence Agent, real Provider/LLM, Worker loop and DSA runtime source migration remain out of scope.
- Recorded the user reminder in `tasks/lessons.md`: every stage task must automatically end with state docs, progress checklist, evidence/risk/decision updates, `tasks/todo.md` review, latest checkpoint anchors and a copyable startup prompt.
- Verification: status-anchor scan found `847e5263` / `fa0ba469` / `3c19b937`, `SAL-P3-016`, P3 `15/17` and total `64/129`; `git diff --check` PASS.

---

# SAL-P3-015 Screen Lab Plan

> Started: 2026-07-25
> Scope: Complete `SAL-P3-015` by adding a DSA Web Screen Lab extension patch that reuses the frozen Quant Screening API, ScreenSnapshot, ScreenDefinition, CandidateBatch, FactorDefinition, Factor Evaluation, Dataset/Manifest, ProblemDetails, Trace, Artifact and Run/Stage/Event contracts. Do not start `SAL-P3-016`, `SAL-P3-017`, Quant Core/Qlib, formal backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read required handoff docs, current Git state, frontend/coding/TDD/verification skills, ADR-001/002, DSA patch workflow and web routing/test patterns.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-25-screen-lab.md`.
- [x] Add Red DSA Web API client tests for `/api/v1/quant` route metadata, Idempotency-Key screen run submission, stable result pagination, single-result lookup and comparison calls.
- [x] Implement `src/api/quantScreening.ts` in the isolated DSA worktree with typed DTOs and snake_case/camelCase conversion.
- [x] Add Red Screen Lab page tests covering definition edit controls, draft/published labels, Snapshot/History, Preview/Formal labels, loading/empty/partial/error/stale/permission states, result rows, explanation drawer and comparison.
- [x] Implement `ScreenLabPage` using the Quant Screening API client and existing DSA UI primitives without calling legacy AlphaSift endpoints for Screen Lab data.
- [x] Add route/nav/i18n integration for `/screen-lab` and update route tests.
- [x] Generate and register `patches/dsa/v3.26.1/0004-add-screen-lab.patch` as a DSA `extension` patch.
- [x] Add `docs/screen-lab.md`, update `docs/upstream-patches.md`, progress/status docs, evidence/decision registers and this review.
- [x] Run target web tests, related web tests, Python related/full tests, compileall, dependency lock guard, patch check, immutable tag check and `git diff --check`.
- [x] Perform local senior review because subagent dispatch still fails with empty optional fields, then stage only tracked SAL-P3-015 files and create the required Chinese checkpoint commit.

## Guardrails

- Screen Lab must display Quant API output lineage: `as_of`, concrete `dsv_*` Dataset Versions, schema, trace/run/stage, snapshot/pipeline ids and Artifact manifest.
- Draft/published definitions, Snapshot/History, and Preview/Formal run modes must be visually distinct and test-covered.
- UI state coverage must include loading, empty, partial, error, stale and permission-denied; empty tables must not masquerade as loaded results.
- No legacy AlphaSift API, real Provider/LLM, Worker loop, Quant Core/Qlib, formal backtest or Evidence Agent may be introduced in this task.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-015

- Added `patches/dsa/v3.26.1/0004-add-screen-lab.patch` as a DSA Web extension patch over the isolated `.worktrees/dsa-v3.26.1` runtime source; the generated patch contains only Screen Lab web files and one nav regression test update.
- Added typed `quantScreeningApi` coverage for `/api/v1/quant/screen-runs`, required `Idempotency-Key`, stable result pagination, single-result explanation lookup and run comparison; request bodies are converted to snake_case and responses to camelCase.
- Added `ScreenLabPage` with definition inputs, draft/published badges, Snapshot/History panels, Preview/Formal run modes, loading/empty/partial/stale/error/permission states, result rows, explanation drawer and comparison flow.
- Wired `/screen-lab` route, SidebarNav item and zh/en labels before legacy `/screening`; updated `SidebarNav.test.tsx` after full Vitest caught the stale expected order.
- Verification: target web `4 files / 24 passed`; full web Vitest `92 passed files, 973 passed, 2 skipped`; `npm run lint` PASS; `npm run build` PASS; Python related `25 passed`; full pytest `307 passed, 3 skipped`; compileall PASS; lock guard PASS; patch check reports `0001..0004` already applied; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: code-review subagent dispatch was retried but the client wrapper still injected empty optional fields and rejected `reasoning_effort`; local senior review checked patch scope, no legacy AlphaSift Screen Lab data calls, route/nav/i18n consistency, UI states, Quant API lineage display and no-go boundaries.
- Scope retained: no `SAL-P3-016`, `SAL-P3-017`, Quant Core/Qlib, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency surface change, static artifact submission or tag movement.
- Implementation checkpoint: `847e5263 feat(P3): 实现 Screen Lab`; status sync checkpoint: `fa0ba469 docs: 同步 SAL-P3-015 checkpoint hash`; final status review checkpoint is created after this review update and should be confirmed with `git log -1 --oneline`.

---

# SAL-P3-014 Latest Status Refresh

> Started: 2026-07-25
> Scope: Refresh recovery documents after `SAL-P3-014` implementation/status checkpoints, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-015` implementation in this sync.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist anchors, current Git status and recent commits.
- [x] Confirm latest implementation checkpoint `dd4e9465 feat(P3): 实现 Quant Screening API` and latest landed status-sync checkpoint `cd0d6c6f docs: 同步 SAL-P3-014 checkpoint hash`.
- [x] Reconfirm completed scope through `SAL-P3-014`, unfinished scope from `SAL-P3-015`, Gate G3 not passed, and strict no-go boundaries.
- [x] Update `docs/development-status.md`, `docs/development-progress-checklist.md`, this review, and `tasks/lessons.md` with the repeated habit reminder.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P3-014 Latest Status Refresh

- Confirmed branch `codex/p0-baseline-status` was clean before edits and ahead of origin by 94 commits.
- Confirmed latest log before edits: `cd0d6c6f docs: 同步 SAL-P3-014 checkpoint hash`, `dd4e9465 feat(P3): 实现 Quant Screening API`, `7f363739 docs: 复核 SAL-P3-013 最新开发状态`.
- Updated recovery status so the completed range is explicit through `SAL-P3-014`, unfinished work begins at `SAL-P3-015`, and Gate G3 remains unpassed.
- Updated next-session guidance so only `SAL-P3-015 Screen Lab` is next; `SAL-P3-016`, `SAL-P3-017`, Quant Core, formal backtest, Evidence Agent, real Provider/LLM, Worker loop and DSA runtime source migration remain out of scope.
- Recorded the user reminder in `tasks/lessons.md`: every stage task must automatically end with state docs, progress checklist, evidence, risk/decision updates, `tasks/todo.md` review, latest checkpoint anchors and a copyable startup prompt.

---

# SAL-P3-014 Quant Screening API Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-014` by adding a framework-neutral Quant Screening API contract for factor/screen definitions, asynchronous screen runs, stable paginated results and snapshot comparison. Reuse `ScreenSnapshot`, `ScreenDefinition`, `CandidateBatch`, `FactorDefinition`, Factor Evaluation, Dataset Catalog/Manifest, `ProblemDetails`, `Trace`, `Artifact`, `TaskBackend` and Run/Stage/Event. Do not implement Screen Lab UI, Quant Core/Qlib adapter, Portfolio Backtest, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, `docs/factor-definition-version-model.md`, `docs/factor-dsl-operator-whitelist.md`, `docs/base-factor-definitions.md`, `docs/factor-cross-sectional-post-processing.md`, `docs/factor-evaluation.md`, `docs/factor-dag-cache.md`, `docs/historical-universe.md`, `docs/screen-definition-pipeline.md`, `docs/screen-snapshot-explanation-trace.md`, current Git status and recent commits.
- [x] Confirm working baseline: branch `codex/p0-baseline-status`, clean worktree, latest commits `7f363739`, `e0ca42d9`, `10d97975`, current task `SAL-P3-014`.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-quant-screening-api.md`.
- [x] Add Red API contract tests for route metadata, definition create payloads, Idempotency-Key 202 run response, stable cursor pagination, row lookup, comparison response and validation errors.
- [x] Implement `application.quant_screening_api` with immutable route/request/response DTOs, in-memory repository, `TaskBackend` submission, `ScreenSnapshot` result pagination and comparison helpers.
- [x] Export Quant Screening API symbols from `application`.
- [x] Add `docs/quant-screening-api.md` with routes, response schema, idempotency, pagination, ProblemDetails/Trace/Artifact semantics, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Perform local senior review or subagent review if tooling works, then stage only `SAL-P3-014` files and create the required Chinese checkpoint commit.

## Guardrails

- API rows must expose explicit `as_of`, concrete `dsv_*` Dataset Versions, schema name/version, trace/run/stage, snapshot/artifact ids and deterministic pagination metadata.
- `Idempotency-Key` is required for run creation and must replay the same `202` response for the same request without creating duplicate tasks.
- Query endpoints read existing `ScreenSnapshot` results; this task does not execute real AlphaSift, factor engines, real Provider/LLM calls, Qlib, formal backtests or Worker loops.
- ScreenDefinition and FactorDefinition endpoints store/version definitions only; they must not compute factors, run screens, or mutate published manifests outside existing contracts.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-014

- Added `src/serenity_alpha_lab/application/quant_screening_api.py` with `application.quant_screening_api@1.0.0`, `/api/v1/quant` route metadata, response DTOs, `QuantScreeningRunRequest`, `QuantScreeningRunRecord`, `InMemoryQuantScreeningRepository` and `QuantScreeningApiService`.
- Definition endpoints return JSON-ready FactorDefinition and ScreenDefinition records with schema and trace metadata; they do not execute factors, run screens or mutate published manifests beyond existing DTO contracts.
- Screen run creation requires `Idempotency-Key`, submits a queued `TaskBackend` command with task type `quant.screen.run`, replays the same `202 Accepted` response for identical requests and rejects conflicting reuse.
- Result endpoints page existing `ScreenSnapshot.results` with stable offset cursors and explicit `as_of`, concrete Dataset Versions, schema, trace/run/stage, snapshot/pipeline ids and optional Artifact manifest; single-result lookup uses canonical `InstrumentId`.
- Comparison endpoint reuses `compare_screen_snapshots()` and returns `quant.screen_snapshot_comparison@1.0.0`; it remains deterministic local comparison, not a backtest or risk gate.
- Added `tests/application/test_quant_screening_api.py`; Red failed with missing `serenity_alpha_lab.application.quant_screening_api`, Green target `5 passed`.
- Added `docs/quant-screening-api.md`, `docs/superpowers/plans/2026-07-24-quant-screening-api.md`, `DEC-061` and `AEV-063`; updated P3 progress to `14/17`, total progress to `63/129`, and moved `SAL-P3-015` to `READY`.
- Implementation checkpoint: `dd4e9465 feat(P3): 实现 Quant Screening API`.
- Final verification: target `5 passed`; related suite `45 passed`; full pytest `307 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: subagent dispatch was attempted but the client wrapper again rejected the payload with `reasoning_effort must not be empty`; local senior review checked idempotency replay/conflict semantics, JSON-ready responses, pagination cursor stability, trace/artifact metadata, exports, docs/status consistency and no-go boundaries; no Critical or Important issue remains.
- Scope retained: no Screen Lab UI, real FastAPI/DSA endpoint facade, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-013 Status Refresh And Habit Reinforcement

> Started: 2026-07-24
> Scope: Refresh latest recovery docs after `SAL-P3-013` implementation/status checkpoints, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-014` implementation in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoints.
- [x] Replace status-sync placeholder wording with actual checkpoint `e0ca42d9 docs: 同步 SAL-P3-013 checkpoint hash`.
- [x] Reconfirm completed scope through `SAL-P3-013`, unfinished scope from `SAL-P3-014`, and strict no-go boundaries in recovery docs.
- [x] Record the repeated habit reminder in `tasks/lessons.md`.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P3-013 Status Refresh

- Confirmed latest implementation checkpoint: `10d97975 feat(P3): 实现 ScreenSnapshot 解释轨迹`.
- Confirmed latest status-sync checkpoint: `e0ca42d9 docs: 同步 SAL-P3-013 checkpoint hash`.
- Updated `docs/development-status.md` and `docs/development-progress-checklist.md` so next-session recovery can continue at `SAL-P3-014` without manually resolving placeholder commit text.
- Updated `tasks/lessons.md` to preserve the rule that every stage task must end with status docs, progress ledger, evidence, `tasks/todo.md` review and a copyable startup prompt.
- Scope retained: no `SAL-P3-014` implementation, no frontend, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call, no Worker loop and no DSA runtime source migration.

---

# SAL-P3-013 ScreenSnapshot And Explanation Trace Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-013` by adding a deterministic ScreenSnapshot result schema, per-security passed/failed-stage records, score contribution detail, replayable structured explanation trace and comparison helper. Do not implement Quant Screening API, Screen Lab UI, Quant Core/Qlib adapter, Portfolio Backtest, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, `docs/factor-definition-version-model.md`, `docs/factor-dsl-operator-whitelist.md`, `docs/base-factor-definitions.md`, `docs/factor-cross-sectional-post-processing.md`, `docs/factor-evaluation.md`, `docs/factor-dag-cache.md`, `docs/historical-universe.md`, `docs/screen-definition-pipeline.md`, current Git status and recent commits.
- [x] Confirm working baseline with `git status --short --branch`, `git log -3 --oneline`, worktree detection and existing ScreenDefinition target tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-screen-snapshot-explanation-trace.md`.
- [x] Add Red contract tests for result schema, passed/failed-stage rows, score contribution records, structured explanation replay, comparison query and deterministic ArtifactStore publication.
- [x] Implement `quant.screening.snapshot` with immutable ScreenSnapshot DTOs, deterministic IDs, builder from `ScreenPipelineSnapshot`, comparison helper and publisher.
- [x] Export ScreenSnapshot symbols from `quant.screening`.
- [x] Add `docs/screen-snapshot-explanation-trace.md` with schema, explanation trace semantics, comparison rules, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record client/tool fallback, then stage only `SAL-P3-013` files and create the required Chinese checkpoint commit.

## Guardrails

- ScreenSnapshot is a deterministic result projection over the existing `ScreenPipelineSnapshot`; do not change P3-012 pipeline semantics unless a failing regression proves a root-cause issue.
- Structured `stage/rule_id/reason/scores/factor_contributions/source_ids` is authoritative; any human summary is non-authoritative and must be replayable from structured fields.
- Every snapshot must retain concrete Dataset Version ids, ScreenDefinition version, pipeline snapshot id, as-of, trace/run/stage and schema metadata.
- Comparison query is local deterministic comparison only; do not implement Quant Screening API, pagination, UI, database repository or Worker loop.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-013

- Added `src/serenity_alpha_lab/quant/screening/snapshot.py` with immutable `ScreenSnapshot`, result rows, explanation steps, comparison DTOs, deterministic `ssn_*` IDs, builder from `ScreenPipelineSnapshot` and deterministic ArtifactStore publication.
- Snapshot construction preserves concrete Dataset Version ids, `pipeline_snapshot_id`, `definition_version_id`, `as_of`, trace/run/stage, passed/failed counts, per-instrument result lookup and sorted passed/failed output rows.
- Result validation enforces one row per `InstrumentId`, contiguous ranks for passed rows, failed-stage requirements for failed rows, finite scores, concrete `dsv_*` Dataset Versions and exactly `ssn_<32 hex>` snapshot IDs.
- Structured explanation fields remain authoritative; display `summary` is non-authoritative and comparison stays a local pure helper for passed-set, status, rank and score deltas.
- Added `tests/quant/test_screen_snapshot.py`; Red failed with missing `serenity_alpha_lab.quant.screening.snapshot`; Green target `3 passed`.
- Added `docs/screen-snapshot-explanation-trace.md`, `docs/superpowers/plans/2026-07-24-screen-snapshot-explanation-trace.md`, `DEC-060` and `AEV-062`; updated P3 progress to `13/17`, total progress to `62/129`, and moved `SAL-P3-014` to `READY`.
- Implementation checkpoint: `10d97975 feat(P3): 实现 ScreenSnapshot 解释轨迹`.
- Final verification: target `3 passed`; related ScreenSnapshot/ScreenDefinition/HistoricalUniverse/FactorPostProcessing/CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `39 passed`; full pytest `302 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: independent code-review subagent dispatch was attempted but the client wrapper rejected payloads with `reasoning_effort must not be empty`; local senior review found and fixed one contract drift where manual `screen_snapshot_id` validation allowed 32-64 hex instead of exactly 32 hex. No Critical or Important issue remains.
- Scope retained: no Quant Screening API, Screen Lab UI, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-012 ScreenDefinition And L0-L4 Pipeline Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-012` by adding a deterministic ScreenDefinition version model and L0-L4 pipeline contract that composes Historical Universe, ScreeningProvider/CandidateBatch, post-processed factors, optional LLM overlay and simple portfolio/risk gates. Do not implement ScreenSnapshot, Quant Screening API, Screen Lab UI, Quant Core/Qlib adapter, Portfolio Backtest, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/historical-universe.md`, current Git status and recent commits.
- [x] Inspect CandidateBatch, ScreeningProvider, Historical Universe, factor post-processing, Factor DAG/cache and ArtifactStore patterns for immutable DTOs, concrete Dataset Version guards, deterministic records and artifact publication.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-screen-definition-pipeline.md`.
- [x] Add Red contract tests for ScreenDefinition versioning, published-run guard, stage ordering, LLM overlay hard-filter boundary, L4 constraints and deterministic ArtifactStore publication.
- [x] Implement `quant.screening.pipeline` with immutable definition/stage/snapshot DTOs, deterministic version ids, L0-L4 execution and publisher.
- [x] Export ScreenDefinition/pipeline symbols from `quant.screening`.
- [x] Add `docs/screen-definition-pipeline.md` with stage semantics, score/constraint rules, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record client/tool fallback, then stage only `SAL-P3-012` files and create the required Chinese checkpoint commit.

## Guardrails

- Every ScreenDefinition and formal run must bind concrete `dsv_*` Dataset Version ids; `latest` remains forbidden.
- Formal pipeline execution must require a published ScreenDefinition version and preserve a full resolved definition snapshot.
- L0 Historical Universe hard filters run before provider/factor/LLM/risk scoring; LLM overlay cannot reintroduce an excluded security.
- L4 constraints in this task are deterministic screen gates only, not a portfolio backtest or full Risk Engine.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-012

- Added `src/serenity_alpha_lab/quant/screening/pipeline.py` with `ScreenDefinition`, provider/factor/LLM/risk stage specs, stage traces, pipeline candidates/exclusions, deterministic `sdv_*` definition version ids and deterministic `sps_*` pipeline snapshot ids.
- Pipeline execution requires a published ScreenDefinition, concrete `dsv_*` Dataset Version ids, matching universe/provider/CandidateBatch/factor versions and exact `as_of` alignment.
- L0 Historical Universe runs before provider/factor/LLM/final scoring; provider candidates outside L0 are excluded with `l0_universe_member` and cannot be restored by L3 overlay.
- L2 factor scoring consumes post-processed factor results, combines configured `fdv_*` factor weights and normalizes candidate factor scores inside the run.
- L4 currently implements deterministic screen gates only: `top_n` and `max_per_industry`; this is not a formal portfolio Risk Engine or backtest.
- Added `tests/quant/test_screen_definition_pipeline.py`; Red failed with missing `serenity_alpha_lab.quant.screening.pipeline`; regression Red failed `1 failed, 2 passed` when CandidateBatch dataset version guard was temporarily removed; Green target `3 passed`.
- Added `docs/screen-definition-pipeline.md`, `docs/superpowers/plans/2026-07-24-screen-definition-pipeline.md`, `DEC-059` and `AEV-061`; updated P3 progress to `12/17`, total progress to `61/129`, and moved `SAL-P3-013` to `READY`.
- Final verification: target `3 passed`; related ScreenDefinition/HistoricalUniverse/FactorPostProcessing/FactorDAG/CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `44 passed`; full pytest `299 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted independent code-review subagent dispatch, but the client wrapper rejected payloads with `reasoning_effort must not be empty` and `Provide either message or items, but not both`; local senior review found and fixed CandidateBatch dataset-version mismatch coverage, then checked stage ordering, L0 hard-filter precedence, LLM overlay non-bypass, version hashing, dataset guards, deterministic artifact output, docs/status consistency and no-go boundaries; no Critical or Important issue remains.
- Scope retained: no ScreenSnapshot, Quant Screening API, Screen Lab UI, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-011 Historical Universe Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-011` by adding a deterministic L0 Historical Universe contract and snapshot builder for point-in-time listing status, ST, delisting, suspension and daily-bar data availability hard filters. Do not implement ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib adapter, Portfolio Backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/factor-dag-cache.md`, current Git status and recent commits.
- [x] Inspect Instrument Master, Trading Calendar, Raw Daily Bars, Factor DAG/cache and ArtifactStore patterns for immutable DTOs, concrete Dataset Version guards, deterministic records and artifact publication.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-historical-universe.md`.
- [x] Add Red contract tests for UniverseDefinition, PIT membership/status behavior, ST/listing/delisting/suspension/data-availability exclusions, deterministic snapshot records and ArtifactStore publication.
- [x] Implement `quant.screening.universe` with immutable universe specs, members, exclusions, rule evidence, deterministic snapshot id and publisher.
- [x] Export Historical Universe symbols from `quant.screening`.
- [x] Add `docs/historical-universe.md` with rule semantics, evidence requirements, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record client/tool fallback, then stage only `SAL-P3-011` files and create the required Chinese checkpoint commit.

## Guardrails

- Every universe run must bind concrete `dsv_*` Dataset Version ids; `latest` remains forbidden.
- Historical membership must query Instrument Master as-of the decision date, not current constituents or current listing/ST status.
- Exclusions must carry deterministic `rule_id`, `rule_version`, severity and data evidence records with Dataset Version/source references.
- Suspension and daily-bar availability are hard filters only for L0 universe construction; this task does not define L1/L2 screen stages.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-011

- Added `src/serenity_alpha_lab/quant/screening/universe.py` with `UniverseDefinition`, `UniverseSnapshot`, `UniverseMember`, `UniverseExclusion`, `UniverseDataEvidence`, `UniverseInstrumentTradeStatus`, `build_historical_universe_snapshot()` and `publish_historical_universe_snapshot()`.
- Historical Universe requires concrete `dsv_*` versions for `instrument_master`, `trading_calendar`, `raw_daily_bars` and `instrument_trade_status`; `latest` is rejected.
- Snapshot construction queries Instrument Master as-of the decision date, validates `as_of` is a trading day, applies active/listing-days/ST/suspension/daily-bar hard filters and preserves rule-level Dataset/Bronze evidence for every exclusion.
- `UniverseSnapshot.universe_version_id` is derived as deterministic `dsv_*`; repeated ArtifactStore publication produces identical artifact id/hash.
- Added `tests/quant/test_historical_universe.py`; Red failed with missing `serenity_alpha_lab.quant.screening.universe`, Green target `4 passed`.
- Added `docs/historical-universe.md`, `docs/superpowers/plans/2026-07-24-historical-universe.md`, `DEC-058` and `AEV-060`; updated P3 progress to `11/17`, total progress to `60/129`, and moved `SAL-P3-012` to `READY`.
- Implementation checkpoint: `adc7741f feat(P3): 实现 Historical Universe`.
- Final verification: target `4 passed`; related suite `45 passed`; full pytest `296 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted explorer/code-review subagent dispatch, but the client wrapper rejected payloads by injecting empty optional fields (`reasoning_effort must not be empty`). Local senior review checked PIT status behavior, rule ordering, exclusion evidence completeness, deterministic version/artifact output, exports, docs/status consistency and no-go boundaries; no Critical or Important issue found.
- Scope retained: no ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-010 Factor DAG Cache Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-010` by adding a deterministic Factor calculation DAG/cache contract for dependency compilation, common subexpression reuse, cache key derivation, partition planning, incremental recompute planning and quality-gated cache manifest publication. Do not execute factor values, implement Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib adapter, Portfolio Backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/factor-evaluation.md`, current Git status and recent commits.
- [x] Inspect existing FactorDefinition, Factor DSL, base factor, post-processing, evaluation, Dataset Catalog and ArtifactStore patterns for immutable DTOs, concrete Dataset Version guards, deterministic records and artifact publication.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-factor-dag-cache.md`.
- [x] Add Red contract tests for DAG build specs, common subexpression reuse, cache key completeness, partition planning, incremental recompute planning and quality-gated cache manifest artifact publication.
- [x] Implement `quant.factors.engine` with immutable DAG/cache specs, node/cache/partition/recompute/manifest DTOs, deterministic planners and artifact publisher.
- [x] Export Factor DAG/cache symbols from `quant.factors`.
- [x] Add `docs/factor-dag-cache.md` with graph semantics, cache key fields, partition policy, incremental recompute policy, quality gate, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record client/tool fallback, then stage only `SAL-P3-010` files and create the required Chinese checkpoint commit.

## Guardrails

- Every cache key must include concrete Dataset Version ids, factor version id, universe version id, date range, engine version and partition id; no `latest` alias is allowed.
- DAG planning may compile Factor DSL and deduplicate shared expression nodes, but must not execute factor values or publish factor-value datasets.
- Time-series operators partition by instrument; cross-sectional operators partition by trade date; incremental recompute must include lookback windows affected by changed inputs.
- Cache manifests may be published only when quality gate status is `passed`; failed runs must not pollute shared cache.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-010

- Added `src/serenity_alpha_lab/quant/factors/engine.py` with `FactorDagBuildSpec`, `FactorDagNode`, `FactorDag`, cache key/partition/plan DTOs, incremental recompute DTOs, quality gate DTOs, `build_factor_dag()`, `plan_factor_cache_partitions()`, `plan_incremental_factor_recompute()` and `publish_factor_cache_manifest()`.
- DAG build compiles Factor DSL plans, deduplicates common expression nodes, binds published `FactorDefinition.version_id` to the spec's `fdv_*` factor version, records each factor's actual Dataset Version dependencies and rejects `latest` aliases.
- Cache planning now keys each partition by factor-specific Dataset Versions, factor version, universe version, date range, engine version, partition kind/date/instrument and partition id; duplicate instrument/date inputs are deduped, out-of-range trade dates are rejected and partition/cache identity mismatches fail construction.
- Incremental recompute uses lookback windows for date changes, factor version ids for factor changes and factor-specific dataset dependency maps for Dataset Version changes, so unrelated Dataset changes do not recompute unrelated factor partitions.
- Cache manifest publication is deterministic JSON through `ArtifactStore` and is blocked unless `FactorCacheQualityGate.status == passed`.
- Added `tests/quant/test_factor_dag_cache.py`; initial Red failed with missing `serenity_alpha_lab.quant.factors.engine`; review regression Red captured `5 failed, 3 passed`; Green target `8 passed`.
- Added `docs/factor-dag-cache.md`, `docs/superpowers/plans/2026-07-24-factor-dag-cache.md`, `DEC-057` and `AEV-059`; updated P3 progress to `10/17`, total progress to `59/129`, and moved `SAL-P3-011` to `READY`.
- Implementation checkpoint: `d34b8690 feat(P3): 实现 Factor DAG cache`.
- Final verification: target `8 passed`; factor related suite `37 passed`; related P3/Architecture suite `62 passed`; full pytest `292 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted independent `code-reviewer` dispatch multiple times, but the client wrapper rejected payloads by injecting empty or conflicting optional fields (`reasoning_effort must not be empty`; `Provide either message or items, but not both`). Local senior review checked published-version binding, factor-specific cache key scope, partition date/dedup guards, DTO identity invariants, deterministic artifact output, exports, docs/status consistency and no-go boundaries; no Critical or Important issue found.
- Scope retained: no factor value execution, factor values Dataset publication, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-009 Factor Evaluation Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-009` by adding a deterministic Factor Evaluation contract and offline evaluator for coverage, IC/ICIR, forward return quantile groups, monotonicity, turnover and exposure summaries. Persist the evaluation report as deterministic JSON via the existing `ArtifactStore` contract. Do not implement factor calculation DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib adapter, Portfolio Backtest, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `SAL-P3-009` acceptance, existing factor contracts, artifact store patterns, current Git status and recent commits.
- [x] Add Red contract tests for `FactorEvaluationSpec`, PIT/sample-overlap guards, IC/ICIR, quantile group returns, monotonicity, turnover, exposure summaries and deterministic artifact publication.
- [x] Implement `quant.factors.evaluation` with immutable specs, input rows, metrics, report DTOs, validation, deterministic evaluator and artifact publisher.
- [x] Export Factor Evaluation symbols from `quant.factors`.
- [x] Add `docs/factor-evaluation.md` with metric definitions, future-return window versioning, PIT/overlap guards, non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, this review and next-session prompt, including the actual `SAL-P3-008` checkpoint `dc23e769`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent review or record tool fallback, then stage only `SAL-P3-009` files and create the required Chinese checkpoint commit.

## Guardrails

- Evaluation inputs must reference concrete `dsv_*` Dataset Version ids; `latest` remains forbidden.
- Formal evaluation must reject rows where factor values are not PIT-valid at the decision time, or where factor/forward-return samples do not overlap on `instrument_id + trade_date`.
- Future-return windows must be explicitly versioned in the spec, including horizon, unit and return field semantics.
- Metric output is deterministic and JSON-friendly; warnings must explain small samples, missing pairs, empty bins, zero variance, rank-deficient monotonicity and exposure gaps.
- This task evaluates already-produced factor values only; it does not compute factor values, build cache/DAG, select a historical universe, run screens, simulate portfolios, call Qlib, or invoke real Provider/LLM paths.

## Review: SAL-P3-009

- Added `src/serenity_alpha_lab/quant/factors/evaluation.py` with `FutureReturnWindow`, `FactorEvaluationSpec`, `FactorEvaluationObservation`, coverage/IC/group/monotonicity/turnover/exposure DTOs, `evaluate_factor()` and `publish_factor_evaluation_report()`.
- Evaluation spec requires concrete `dsv_*` Dataset Version ids and `fdv_*` factor versions; `latest` is rejected.
- Formal evaluation rejects non-PIT factor values where `factor_available_at > decision_time`; forward returns are allowed to be available after decision time because they are labels.
- Metrics use the factor/forward-return intersection sample and record `sample_non_overlap`; report includes coverage ratios, Spearman/Pearson IC, ICIR annualization, quantile group returns, direction-adjusted monotonicity, Top/Bottom target-group turnover and exposure summary.
- Reports publish deterministic JSON through `ArtifactStore` with `produced_by_run_id` / `produced_by_stage_id`.
- Added `tests/quant/test_factor_evaluation.py`; Red failed with missing `serenity_alpha_lab.quant.factors.evaluation`, Green target `4 passed`.
- Added `docs/factor-evaluation.md`, `docs/superpowers/plans/2026-07-24-factor-evaluation.md`, `DEC-056` and `AEV-058`; updated P3 progress to `9/17`, total progress to `58/129`, moved `SAL-P3-010` and `SAL-P3-011` to `READY`, and backfilled `SAL-P3-008` checkpoint as `dc23e769`.
- Implementation checkpoint: `fb7beb02 feat(P3): 实现 Factor Evaluation`; follow-up status-sync checkpoint title is `docs: 同步 SAL-P3-009 checkpoint hash`.
- Final verification: target `4 passed`; factor related suite `29 passed`; related P3/Architecture suite `54 passed`; full pytest `284 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted independent `code-reviewer` and `python-reviewer` subagents, but both remained running without findings inside the wait window and were closed. Local senior review checked diff scope, metric semantics, PIT guard, sample-overlap behavior, deterministic artifact output, exports, docs/status consistency and no-go boundaries; no Critical or Important issue found.
- Scope retained: no factor execution, factor values Dataset publication, DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core/Qlib Adapter, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-008 Cross-Sectional Post-Processing Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-008` by adding a deterministic cross-sectional factor post-processing contract and processor for winsorization, standardization, industry / market-cap neutralization and missing-value handling. The processor consumes explicit per-date universe snapshots and concrete Dataset Version references. Do not implement Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, `docs/factor-definition-version-model.md`, `docs/factor-dsl-operator-whitelist.md`, `docs/base-factor-definitions.md`, current Git status and recent commits.
- [x] Add Red contract tests for post-processing parameter schema, concrete Dataset Version references, same-date grouping, missing handling, winsorization, z-score stability, industry / log-market-cap neutralization, constant columns, small samples, missing industry and outliers.
- [x] Implement `quant.factors.post_processing` with immutable specs, input/output DTOs, deterministic processor and JSON-friendly records.
- [x] Export post-processing symbols from `quant.factors`.
- [x] Add `docs/factor-cross-sectional-post-processing.md` with schema, execution order, non-goals, edge-case behavior and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record client/tool fallback, then stage only `SAL-P3-008` files and create the required Chinese checkpoint commit.

## Guardrails

- Each post-processing run must reference concrete `dsv_*` Dataset Version ids; `latest` remains forbidden.
- Processing must group by `trade_date` and only use rows provided for that date's current universe snapshot.
- Missing industry and market-cap exposure handling must be explicit and auditable, not silent.
- Constant columns, one-name groups and small samples must return deterministic neutral output plus warnings rather than NaN/inf.
- This task does not compute raw factor values, publish factor-value datasets, evaluate factors, build DAG/cache, create ScreenDefinition/ScreenSnapshot/Screen Lab/API, start Quant Core/formal backtest/Evidence Agent, invoke real Provider/LLM paths, implement Worker loops or migrate DSA runtime source.


## Review: SAL-P3-008

- Added `src/serenity_alpha_lab/quant/factors/post_processing.py` with `CrossSectionPostProcessingSpec`, missing/winsorization/neutralization/standardization specs, input/output DTOs, warning records and `process_cross_sectional_factor_values()`.
- Processor groups strictly by `trade_date`, consumes only explicit rows for that date, and requires concrete `dsv_*` Dataset Version references in the spec.
- Supports missing `drop`/`fill_median`/`fill_constant`/`zero`, MAD and quantile winsorization, industry bucket neutralization, `log_market_cap` OLS residualization and z-score standardization.
- Edge cases are explicit: constant columns and small samples return 0.0 with warnings, missing industry enters `__missing_industry__`, missing market cap is configured as drop/fill, rank-deficient OLS returns residuals with warning, and outliers are clipped before standardization.
- Added `tests/quant/test_factor_post_processing.py`; Red failed with missing `serenity_alpha_lab.quant.factors.post_processing`, Green target `4 passed`.
- Added `docs/factor-cross-sectional-post-processing.md`, `DEC-055` and `AEV-057`; updated P3 progress to `8/17`, total progress to `57/129`, and moved `SAL-P3-009` to `READY`.
- Final verification: target `4 passed`; factor related suite `25 passed`; related P3/Architecture suite `50 passed`; full pytest `280 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: independent subagent dispatch was unavailable from the current client path after earlier payload validation issues; local senior review covered diff scope, dsv guardrails, per-date grouping, OLS edge cases, warning semantics, exports, docs/status consistency and no-go boundaries. No Critical or Important issue found.
- Scope retained: no raw factor execution, factor values Dataset publication, Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-007 Latest Status Refresh Plan

> Started: 2026-07-24
> Scope: Refresh recovery-facing documentation after `27b87c2e feat(P3): 交付首批基础因子` and `e3ce4840 docs: 同步 SAL-P3-007 checkpoint hash`; clearly mark completed vs unfinished work, record the repeated automatic status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-008` implementation in this status-refresh task.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, current Git status and recent commits.
- [x] Update `tasks/lessons.md` with the repeated automatic status-sync reminder.
- [x] Update `docs/development-status.md` with current completed/unfinished ranges, actual implementation checkpoint, previous status-sync checkpoint and refreshed next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step summary with the same recovery anchors.
- [x] Record this review in `tasks/todo.md`.
- [x] Run status-anchor scan and `git diff --check`.
- [x] Stage only status-sync files and create the required Chinese checkpoint commit.

## Review: SAL-P3-007 Latest Status Refresh

- Completed range remains `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..007`; unfinished work starts at `SAL-P3-008` and P4/P5/P6 remain untouched.
- Current Phase remains P3; Gate G3 remains not passed; G0/G1/G2 remain passed as `GO with accepted risks`.
- Current READY task remains `SAL-P3-008` cross-sectional post-processing; this sync deliberately does not start implementation.
- Recovery anchors now name implementation checkpoint `27b87c2e feat(P3): 交付首批基础因子` and previous status-sync checkpoint `e3ce4840 docs: 同步 SAL-P3-007 checkpoint hash`.
- Habit reinforced: after every stage task, automatically update status/progress/evidence/`tasks/todo.md` review/lessons as needed, then provide a copyable restart prompt with the actual latest docs checkpoint hash.

---

# SAL-P3-007 Base Factor Definitions Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-007` by publishing the first base factor catalog with at least 15 versioned `FactorDefinition` drafts across quality, valuation, growth, momentum, volatility and liquidity. Use existing P2 Dataset Version semantics and the `SAL-P3-006` DSL compiler to verify formula plans against hand-authored references. Do not execute factor values, implement post-processing execution, Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, `docs/factor-definition-version-model.md`, `docs/factor-dsl-operator-whitelist.md`, current Git status and recent commits.
- [x] Add Red contract tests for a 15+ base factor catalog, categories, concrete Dataset Version references, direction/window/market metadata, formula compilation and hand-authored plan goldens.
- [x] Implement `quant.factors.base_factors` with immutable catalog specs, `BaseFactorCatalog`, `base_factor_definitions()` and `compile_base_factor_plans()`.
- [x] Export base-factor catalog symbols from `quant.factors`.
- [x] Add `docs/base-factor-definitions.md` with factor table, formulas, data requirements, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review or record tool fallback, then stage only `SAL-P3-007` files and create the required Chinese checkpoint commit.

## Guardrails

- Every base factor must reference concrete `dsv_*` Dataset Version ids through `FactorInput`; `latest` remains forbidden.
- Each factor must declare direction, category, applicable markets, data requirements, windows where relevant and hand-authored expected DSL plan metadata.
- Formula validation is compile-only: compare DSL plan operators/lookback/inputs/dataset versions to references, but do not compute factor values.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-007

- Added `src/serenity_alpha_lab/quant/factors/base_factors.py` with `base_factor_catalog@1.0.0`, `BaseFactorCatalog`, `BaseFactorSpec`, `BaseFactorInputSpec`, `base_factor_definitions()` and `compile_base_factor_plans()`.
- Catalog contains exactly 15 factor definition drafts: 3 quality, 3 valuation, 3 growth, 2 momentum, 2 volatility and 2 liquidity factors.
- Each definition uses concrete `dsv_*` references for `fundamentals_pit` and/or `adjusted_daily_bars`, declares direction, windows, applicable markets, data requirements and a hand-authored DSL reference plan.
- Added `tests/quant/test_base_factor_definitions.py`; Red failed with missing base factor exports, Green target `4 passed`.
- Added `docs/base-factor-definitions.md`, `DEC-054` and `AEV-056`; updated P3 progress to `7/17`, total progress to `56/129`, and moved `SAL-P3-008` to `READY`.
- Implementation checkpoint: `27b87c2e feat(P3): 交付首批基础因子`; follow-up status-sync checkpoint `e3ce4840 docs: 同步 SAL-P3-007 checkpoint hash` recorded this actual hash in recovery docs.
- Final verification: target `4 passed`; factor-only related suite `21 passed`; related P3/Architecture suite `46 passed`; full pytest `276 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: independent code-review subagent dispatch was still blocked by client payload validation (`Provide either message or items, but not both`). Local senior review checked diff scope, no-go boundaries, concrete Dataset Version guardrails, immutable metadata, DSL reference matching, public exports, docs/status consistency and unused imports; no Critical or Important issue found.
- Scope retained: no factor value execution, post-processing execution, Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-006 Latest Status Refresh Plan

> Started: 2026-07-24
> Scope: Refresh recovery-facing documentation after `a63822d0 feat(P3): 实现因子 DSL 与算子白名单` and `6ee91eed docs: 同步 SAL-P3-006 checkpoint hash`; clearly mark completed vs unfinished work, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-007` implementation in this status-refresh task.

## Checklist

- [x] Re-read current `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `tasks/todo.md`, current Git status and recent commits.
- [x] Update `tasks/lessons.md` with the repeated automatic status-sync habit reminder.
- [x] Update `docs/development-status.md` with current completed/unfinished ranges, actual implementation checkpoint, previous status-sync checkpoint and refreshed next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step summary with the same recovery anchors.
- [x] Record this review in `tasks/todo.md`.
- [x] Run status-anchor scan and `git diff --check`.
- [x] Stage only status-sync files and create the required Chinese checkpoint commit.

## Review: SAL-P3-006 Latest Status Refresh

- Completed range remains `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..006`; unfinished work starts at `SAL-P3-007` and P4/P5/P6 remain untouched.
- Current Phase remains P3; Gate G3 remains not passed; G0/G1/G2 remain passed as `GO with accepted risks`.
- Current READY task remains `SAL-P3-007` base factor definitions; this sync deliberately does not start implementation.
- Recovery anchors now name implementation checkpoint `a63822d0 feat(P3): 实现因子 DSL 与算子白名单` and previous status-sync checkpoint `6ee91eed docs: 同步 SAL-P3-006 checkpoint hash`.
- Habit reinforced: after every stage task, automatically update status/progress/evidence/`tasks/todo.md` review/lessons as needed, then provide a copyable restart prompt.

---

# SAL-P3-006 Factor DSL and Operator Whitelist Plan

> Started: 2026-07-24
> Scope: Complete `SAL-P3-006` by adding a pure, whitelisted factor DSL parser/AST/validator/compiler contract for deterministic factor formulas. Support delay, rolling, rank, arithmetic, comparison and conditional expressions. Do not implement factor value execution, base factor catalog, post-processing execution, Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, Screen Lab, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, `docs/factor-definition-version-model.md`, current Git status and recent commits.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-24-factor-dsl-operator-whitelist.md`.
- [x] Add Red contract tests for DSL parsing, AST serialization, compiler output, whitelisted operators, input/window validation, future-reference rejection, division guards, type guards and arbitrary Python rejection.
- [x] Implement `quant.factors.dsl` with tokenizer/parser, immutable AST nodes, validator and execution-plan compiler.
- [x] Export Factor DSL symbols from `quant.factors`.
- [x] Add `docs/factor-dsl-operator-whitelist.md` with grammar, operators, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Attempt independent code review and record fallback local review when client payload validation blocked dispatch.
- [x] Stage only `SAL-P3-006` files and create the required Chinese checkpoint commit.

## Guardrails

- DSL expressions must only reference declared `FactorInput.input_id` values and whitelisted operators.
- `delay()` periods must be positive and cannot create future references; `rolling_*()` windows must be positive and must fit declared `FactorWindow` entries.
- Division must compile through an explicit guarded divide operation, not an unguarded Python division.
- Parser/validator must reject arbitrary Python syntax, attribute access, indexing, comprehensions, imports, lambdas, unknown calls and module paths.
- This task compiles a deterministic plan only; it does not execute factor values, publish caches, start Qlib/Quant Core, run formal backtests, start Evidence Agent, invoke real Provider/LLM paths, implement Worker execution loops or migrate DSA runtime source.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-006

- Added `src/serenity_alpha_lab/quant/factors/dsl.py` with `FactorExpressionPlan`, `FactorExpressionNode`, `FactorDslValueType`, `compile_factor_expression()` and `compile_factor_definition()`.
- Parser uses Python AST only as a syntax frontend; allowed output is a platform plan, not executable Python.
- Whitelist covers declared inputs, finite constants, arithmetic, comparison, boolean, `where`, `delay`, rolling operators, `rank`, `abs`, `log` and `sqrt`; `/` compiles to `guarded_divide`.
- Safety checks reject arbitrary Python/module paths, attribute/index access, comprehensions, lambdas, unknown calls, keyword args, unknown inputs, invalid types, non-positive/future periods, undeclared windows and literal division by zero.
- Added `docs/factor-dsl-operator-whitelist.md`, `DEC-053` and `AEV-055`; updated P3 progress to `6/17`, total progress to `55/129`, and moved `SAL-P3-007` to `READY`.
- Red evidence: target contract test failed with missing `serenity_alpha_lab.quant.factors.dsl`.
- Final verification: target `14 passed`; related FactorDSL/FactorDefinition/CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `42 passed`; full pytest `272 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted independent `code-reviewer` subagent dispatch through multiple native payload variants, but the client rejected each as duplicate `message/items` because an empty `message` field was injected by the wrapper. Local senior review checked diff scope, AST safety boundary, data type guard, Dataset Version continuity, FactorWindow validation, package exports, docs/status consistency and no-go guardrails; no Critical or Important issue found.
- Scope retained: no base factor definitions, factor execution, post-processing execution, Factor Evaluation, DAG/cache, Historical Universe, ScreenDefinition, ScreenSnapshot, Quant Screening API, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-005 Status Sync Plan

> Started: 2026-07-24
> Scope: Refresh recovery-facing documentation after `d405e6ab feat(P3): 实现 FactorDefinition 版本模型`, clearly mark completed vs unfinished work, update the next-session prompt, and record the user's repeated habit reminder in lessons. Do not start `SAL-P3-006` implementation in this status-sync task.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current development status, progress checklist, current Git status and recent commits.
- [x] Replace remaining `SAL-P3-005` checkpoint placeholders with actual implementation checkpoint `d405e6ab feat(P3): 实现 FactorDefinition 版本模型`.
- [x] Update `docs/development-status.md` with 2026-07-24 status review, completed/unfinished ranges, current READY task and refreshed next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step summary with the actual implementation checkpoint and pending status-sync checkpoint title.
- [x] Record the repeated “每个阶段性任务完成后自动状态同步并给出提示词” habit in `tasks/lessons.md`.
- [x] Run status-anchor scans and `git diff --check`.
- [x] Stage only status-sync files and create the required Chinese checkpoint commit.

## Review: SAL-P3-005 Status Sync

- Latest completed range remains `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..005`; unfinished work starts at `SAL-P3-006`.
- Current Phase remains P3, Gate G3 remains not passed, and G0/G1/G2 remain passed as `GO with accepted risks`.
- Current READY task is `SAL-P3-006` Factor DSL and operator whitelist; this sync deliberately does not start implementation.
- Recovery prompt now includes `docs/factor-definition-version-model.md`, actual implementation checkpoint `d405e6ab`, and the status-sync checkpoint title.
- Habit reinforced: after every stage task, automatically update status/progress/evidence/`tasks/todo.md` review/lessons as needed, then provide a copyable restart prompt.

---

# SAL-P3-005 FactorDefinition Version Model Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-005` by defining versioned FactorDefinition contracts and a local repository that supports mutable drafts, immutable published versions, retirement records and append-only audit evidence. Do not implement Factor DSL execution, factor calculation DAG/cache, base factors, Factor Evaluation, ScreenDefinition, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, Worker execution loop or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, `docs/candidate-batch-contract.md`, current Git status and recent commits.
- [x] Inspect CandidateBatch, ScreeningProvider, Dataset Catalog and package boundary patterns for immutable dataclasses, concrete Dataset Version validation, JSON-friendly `to_record()` and local manifest repositories.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-factor-definition-version-model.md`.
- [x] Add Red contract tests for complete FactorDefinition specs, concrete Dataset Version references, immutable nested records, draft/published/retired lifecycle, repository conflict prevention and audit events.
- [x] Implement `quant.factors.definitions` with FactorDefinition DTOs, lifecycle helpers, immutable publication and local repository.
- [x] Export FactorDefinition symbols from `quant.factors`.
- [x] Add `docs/factor-definition-version-model.md` with schema, lifecycle, non-goals and verification evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Stage only `SAL-P3-005` files and create the required Chinese checkpoint commit.

## Guardrails

- FactorDefinition references must use concrete `dsv_*` Dataset Version ids; `latest` remains forbidden for formal factor definitions.
- Drafts may be overwritten before publication; published version manifests are immutable and same `definition_id + semantic_version` cannot point to changed content.
- Retirement must be represented as a separate lifecycle/audit record, not by editing the published manifest in place.
- This task only models definitions and version lifecycle; no DSL parsing/execution, factor values, DAG/cache, Qlib, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop or DSA runtime source migration.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-005

- Added `src/serenity_alpha_lab/quant/factors/definitions.py` with immutable `FactorDefinition`, `FactorFormula`, `FactorInput`, `FactorWindow`, `MissingValuePolicy`, `PostProcessingStep`, lifecycle/status enums, retirement records, audit events and `LocalFactorDefinitionRepository`.
- Published versions derive `fdv_*` from canonical spec hash; same `definition_id + semantic_version` cannot be republished to different content, and retirement is stored separately so `get_version()` remains the immutable published record.
- Exported FactorDefinition symbols from `quant.factors` and added `tests/quant/test_factor_definition_contract.py`.
- Added `docs/factor-definition-version-model.md`, `DEC-052` and `AEV-054`; updated P3 progress to `5/17`, total progress to `54/129`, and moved `SAL-P3-006` to `READY`.
- Red evidence: target contract test failed with missing `serenity_alpha_lab.quant.factors.definitions`.
- Verification: target `3 passed`; related FactorDefinition/CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `28 passed`; full pytest `258 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Factor DSL parser/compiler, Factor Engine, DAG/cache, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.

---

# SAL-P3-004 CandidateBatch Contract Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-004` by defining immutable `Candidate` / `CandidateBatch` contracts with standardized candidates, L1/L2/L3 score records, reason codes, source lineage, rank, strategy version, discovery time and source snapshot time. Do not implement FactorDefinition, Factor Engine, Screen Lab, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker loop, or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, `docs/screening-provider-contract.md`, current Git status and recent commits.
- [x] Inspect `SAL-P3-004` acceptance scope, `ScreeningProvider` raw result contract, Dataset Version rules, InstrumentId patterns, API ProblemDetails mapping and architecture boundaries.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-candidate-batch-contract.md`.
- [x] Add Red contract tests for CandidateBatch fields, immutability, deterministic serialization, score layer independence, invalid dataset versions, duplicate ranks and ScreeningResult metadata bridge.
- [x] Implement `application.candidate_batch` DTOs, validation, `to_record()` and `candidate_batch_from_screening_result()`.
- [x] Export CandidateBatch contract symbols from `application.__init__`.
- [x] Add `docs/candidate-batch-contract.md` with schema, validation, non-goals and evidence.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Stage only `SAL-P3-004` files and create the required Chinese checkpoint commit.

## Guardrails

- CandidateBatch is a standard contract only; no FactorDefinition, Factor DSL, factor computation DAG, ScreenDefinition pipeline, Screen Lab UI, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, full Worker loop or broad DSA runtime migration.
- CandidateBatch must consume concrete `dsv_*` Dataset Version ids and preserve `ScreeningProvider` trace/run/stage/provider metadata.
- LLM overlay must be represented as an independent L3 score and must not overwrite deterministic L1/L2 values.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-004

- Added `src/serenity_alpha_lab/application/candidate_batch.py` with `CandidateBatch`, `Candidate`, `CandidateLayerScore`, `CandidateReason`, `CandidateSource`, score/source enums, concrete Dataset Version validation, rank/timestamp/source checks, immutable nested records and JSON-friendly `to_record()`.
- Added `candidate_batch_from_screening_result()` to carry `ScreeningResult` provider/strategy/dataset/count/timing/trace metadata without parsing raw provider candidates.
- Exported CandidateBatch symbols from `application.__init__` and added `tests/application/test_candidate_batch_contract.py`.
- Added `docs/candidate-batch-contract.md`, `DEC-051` and `AEV-053`; updated P3 progress to `4/17`, total progress to `53/129`, and moved `SAL-P3-005` to `READY`.
- Red evidence: target contract test failed with missing `serenity_alpha_lab.application.candidate_batch`.
- Verification: target `3 passed`; related CandidateBatch/ScreeningProvider/AlphaSift/Architecture suite `25 passed`; full pytest `255 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no FactorDefinition, Factor Engine, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, Worker loop, DSA runtime source migration, dependency install surface change or tag movement.
- Checkpoint: `07b5d526 feat(P3): 定义 CandidateBatch 候选契约`.

---

# SAL-P3-003 ScreeningProvider Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-003` by defining a platform `ScreeningProvider` contract, AlphaSift Adapter and Fake implementation. Keep AlphaSift internals out of platform Application/Domain. Do not implement `CandidateBatch`, Factor Engine, Screen Lab, Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, `docs/alphasift-wheel-intake.md`, current Git status and recent commits.
- [x] Inspect P3 task scope, AlphaSift `dsa_adapter`, existing Provider/Facade patterns, ProblemDetails, TraceContext, Dataset Catalog `DatasetVersionRef`, and architecture boundaries.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-screening-provider.md`.
- [x] Add Red application contract tests for `ScreeningProvider`, concrete Dataset Version enforcement, immutable DTOs, unified errors and Fake implementation.
- [x] Implement `application.screening_provider` and exports.
- [x] Add Red integration tests for `AlphaSiftScreeningAdapter` status/strategies/screen mapping, profile guard, trace propagation, error and timeout semantics.
- [x] Implement `integrations.alphasift` adapter and ProblemDetails mapping.
- [x] Add architecture boundary tests proving application/domain do not import AlphaSift internals.
- [x] Add `docs/screening-provider-contract.md` with evidence, non-goals and verification.
- [x] Update progress checklist, development status, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Stage only `SAL-P3-003` files and create the required Chinese checkpoint commit.

## Guardrails

- AlphaSift may only be accessed through the Serenity `ScreeningProvider` port; Application/Domain must not import `alphasift` or AlphaSift dataclasses.
- Screening requests must reference concrete `dsv_*` Dataset Version ids; `latest` aliases remain discovery/display only and cannot drive screening execution.
- LLM overlay remains disabled by default and is recorded separately when requested; it must not overwrite deterministic screening scores.
- Tests must use injected fake clients only; no real Provider/LLM/network calls, no full Worker loop, no Quant Core, no formal backtest and no Evidence Agent.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P3-003

- Added `src/serenity_alpha_lab/application/screening_provider.py` with `ScreeningProvider` Protocol, immutable status/strategy/request/result DTOs, concrete `dsv_*` Dataset Version enforcement, unified `ScreeningProviderError` categories and deterministic `FakeScreeningProvider`.
- Added `src/serenity_alpha_lab/integrations/alphasift/provider_adapter.py` and package exports; AlphaSift is only lazily imported through `alphasift.dsa_adapter` when no injected client is supplied and profile guard allows it.
- Added ProblemDetails mapping for `ScreeningProviderError`, plus architecture tests that prevent Application/Domain from importing AlphaSift and keep the AlphaSift adapter import lazy.
- Added `docs/screening-provider-contract.md`, `DEC-050` and `AEV-052`; updated P3 progress to `3/17`, total progress to `52/129`, and moved `SAL-P3-004` to `READY`.
- Red evidence: application contract test failed with missing `serenity_alpha_lab.application.screening_provider`; adapter test failed with missing `serenity_alpha_lab.integrations.alphasift`.
- Verification: contract target `3 passed`; adapter target `5 passed`; related application/integration/architecture suite `22 passed`; full pytest `252 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no CandidateBatch schema, Factor Engine, Screen Lab, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, full Worker loop, DSA runtime source migration, dependency install surface change or tag movement.
- Checkpoint: `1a622a1a feat(P3): 定义 ScreeningProvider 契约与 AlphaSift adapter`.

---

# SAL-P3-002 AlphaSift Wheel Intake Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-002` by building a reproducible offline AlphaSift Wheel from locked source commit `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, fixing source archive hash, wheel hash, SBOM, license inventory and internal artifact reference. Do not implement ScreeningProvider Adapter, start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, or DSA runtime source migration.

## Review: SAL-P3-002 User-Requested Status Refresh

- Refreshed `docs/development-status.md` next-start prompt to include `docs/alphasift-source-review.md` and `docs/alphasift-wheel-intake.md` as required recovery evidence.
- Recorded the repeated status-sync habit reminder in `tasks/lessons.md`.
- Current completed range remains `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..002`; current READY task remains `SAL-P3-003`; Gate G3 remains not passed; progress remains P3 `2/17`, total `51/129`.
- Latest implementation checkpoint remains `50012b44 feat(P3): 构建 AlphaSift 离线 Wheel intake`; previous status-sync checkpoint is `c53daa65 docs: 同步 SAL-P3-002 最新状态与恢复提示`; this refresh will create a new docs checkpoint.

---

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, current Git status and recent commits.
- [x] Inspect P3 task scope, existing dependency lock policy, Docker AlphaSift cache handling, supply-chain baseline patterns, and artifact evidence layout.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-alphasift-wheel-intake.md`.
- [x] Add Red architecture tests for the intake script, manifest, SBOM, license inventory, checksum and review document.
- [x] Implement `scripts/build-alphasift-wheel-intake.sh` to download the codeload source archive, verify SHA-256, build with pinned `SOURCE_DATE_EPOCH`, generate committed evidence and run an offline no-deps install check.
- [x] Run the intake script and commit evidence under `docs/baselines/alphasift-wheel-intake/`.
- [x] Add `docs/alphasift-wheel-intake.md` with build commands, hashes, internal artifact URI, SBOM/license evidence, offline install proof and non-goals.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Stage only `SAL-P3-002` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and do not touch dirty files under `.worktrees/dsa-v3.26.1`.
- Do not add AlphaSift to root `pyproject.toml`, `uv.lock` or generated production `requirements.txt` in this task.
- Do not submit `.cache`, `.worktrees`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, source archives or Wheel binaries.
- Do not start `SAL-P3-003` ScreeningProvider Adapter, CandidateBatch, Factor Engine, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, Worker loops or DSA runtime source migration.
- Preserve Gate G2 boundaries: later Screening/Factor work must use concrete Dataset Versions and reuse Provider Policy/fallback trace, Dataset Catalog/Manifest, Quality Gate, Data Sync, PostgreSQL standalone Profile, PersistentTaskBackend, recoverable events, ProblemDetails, Trace, Artifact and Run/Stage/Event.

## Review: SAL-P3-002

- Added reproducible intake script `scripts/build-alphasift-wheel-intake.sh`; it verifies the locked codeload source archive hash, builds with `SOURCE_DATE_EPOCH=1783081838`, writes manifest/SBOM/license/checksum evidence, and verifies offline no-deps installation from the local wheelhouse.
- Generated committed evidence under `docs/baselines/alphasift-wheel-intake/`: `intake-manifest.json`, `sbom-cyclonedx.json`, `license-inventory.csv`, `license-summary.md`, and `alphasift-wheel.sha256`.
- Added `docs/alphasift-wheel-intake.md` with source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, reproducible wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`, internal artifact URI, offline install command and non-goals.
- Added `tests/architecture/test_alphasift_wheel_intake.py`; Red failed with `4 failed` before the script/evidence/doc existed, and Green passed with `4 passed`.
- Verification completed: intake script regeneration PASS with source SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a` and wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`; related architecture suite `10 passed`; full pytest `242 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted read-only code-review/spec-review subagent dispatch after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty optional fields. Local review checked diff scope, manifest/SBOM/license consistency, non-goals, dependency install surface, untracked files and tag immutability.
- Updated progress checklist with `SAL-P3-002` DONE, P3 `2/17`, total `51/129`, `SAL-P3-003` READY, `DEC-049`, `AEV-051`, and `RSK-005` mitigation detail.
- Scope retained: no root `pyproject.toml` / `uv.lock` / production `requirements.txt` AlphaSift install surface change, no Wheel binary committed, no ScreeningProvider/Adapter, no CandidateBatch, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call, no DSA runtime source migration and no tag movement.
- Checkpoint: `50012b44 feat(P3): 构建 AlphaSift 离线 Wheel intake`.

## Review: SAL-P3-002 Status Sync

- Replaced recovery placeholders with actual implementation checkpoint `50012b44 feat(P3): 构建 AlphaSift 离线 Wheel intake`.
- Current next task remains `SAL-P3-003` only; Gate G3 remains未通过, progress remains P3 `2/17`, total `51/129`.
- Status-sync checkpoint will be the commit containing this review, titled `docs: 同步 SAL-P3-002 最新状态与恢复提示`; next startup should confirm the actual hash with `git log -1 --oneline`.

---

# SAL-P3-001 Status Refresh Plan

> Started: 2026-07-23
> Scope: Refresh recovery docs after `SAL-P3-001` checkpoint `4e6d5ee4`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-002` implementation in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoints.
- [x] Update `tasks/lessons.md` to record the repeated requirement to automatically sync status and provide a copyable next-start prompt after each phase task.
- [x] Update `docs/development-status.md` with explicit `4e6d5ee4` delivery checkpoint, current READY task, unfinished scope, strict guardrails, and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the actual `SAL-P3-001` checkpoint.
- [x] Update this review with completed/unfinished boundaries and verification plan.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P3-001 Status Refresh

- Confirmed latest implementation checkpoint: `4e6d5ee4 docs(P3): 完成 AlphaSift 源码审查与锁定`.
- Current recoverable state: Phase P3, Gate G3 not passed, completed `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001`; total progress `50/129`, P3 progress `1/17`.
- Current READY task: `SAL-P3-002` offline AlphaSift Wheel intake; no ScreeningProvider Adapter, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, or DSA runtime source migration in this status sync.
- Updated `tasks/lessons.md` with the repeated habit reminder: after every stage task, automatically sync recovery docs, evidence, `tasks/todo.md` review, and a copyable next-start prompt before final handoff.
- Verification: status-anchor scan found no active stale prior-task or old-progress markers; `git diff --check` PASS.

---

# SAL-P3-001 AlphaSift Source Review Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-001` by reviewing and locking AlphaSift source provenance, Apache-2.0 attribution, dependency surface, vulnerability/maintenance risk, known limitations, and replacement/stop-use conditions. Do not build the AlphaSift wheel, write the ScreeningProvider adapter, start Quant Core, start formal backtesting, start Evidence Agent, call real Provider/LLM services, or migrate DSA runtime source.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, current Git status and recent commits.
- [x] Inspect P3 entry scope, Gate G2 constraints, AlphaSift/DSA existing integration docs, supply-chain baseline, Python dependency lock record, and current DSA AlphaSift pin.
- [x] Query AlphaSift upstream metadata, default branch, latest commit, tag state, repository license, dependencies, tests, open issues/PRs, contributors, and source archive hash.
- [x] Run current-resolution dependency SCA for the AlphaSift declared runtime dependencies using Python 3.11.
- [x] Write Red doc test requiring locked commit, source archive SHA-256, Apache-2.0 attribution, dependency list, SCA result, known limitations, replacement conditions, stop-use conditions, and P3 non-goals.
- [x] Create `docs/alphasift-source-review.md` with version decision, license/NOTICE treatment, vulnerability and maintenance review, platform boundary, upgrade/replacement/stop-use rules, and next task handoff to `SAL-P3-002`.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P3-001`, P3 progress, total progress, `SAL-P3-002` READY, decision/evidence registers, and any risk updates.
- [x] Update `docs/development-status.md` and this review with completed/unfinished scope, verification evidence, checkpoint wording, and next-session prompt.
- [x] Run target doc test, dependency locking test, full pytest, compileall, dependency lock guard, diff/tag checks, and Git status review.
- [x] Stage only `SAL-P3-001` files and create a Chinese checkpoint commit.

## Guardrails

- AlphaSift is accepted only as an L1 snapshot/candidate discovery plugin until later contract work proves otherwise.
- `SAL-P3-001` must not build or commit an AlphaSift wheel; that belongs to `SAL-P3-002`.
- Do not add AlphaSift to root `pyproject.toml`, `uv.lock`, or generated production `requirements.txt` in this task.
- Do not bypass Gate G2 Provider Policy/fallback trace, Dataset Catalog/Manifest, Quality Gate, Runtime Profile, ProblemDetails, Trace, Artifact, or Run/Stage/Event boundaries.
- Do not run real Provider calls, real LLM calls, Quant Core, formal backtesting, Evidence Agent, full Worker execution loops, Compose deployment, or broad DSA runtime source migration.
- Keep `upstream/dsa-v3.26.1` immutable and avoid submitting `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, temp source archives, or unrelated files.

## Review: SAL-P3-001

- Added `docs/alphasift-source-review.md`, locking `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf` with source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, Apache-2.0 attribution, dependency list, current-resolution SCA limits, known limitations, upgrade/replacement rules and stop-use conditions.
- Added `tests/architecture/test_alphasift_source_review.py` to assert the review keeps the source commit, archive hash, license, dependency surface, SCA result, non-goals and stop conditions explicit. Red failed with missing review doc (`2 failed`); Green target passed (`2 passed`).
- Updated `docs/development-progress-checklist.md`: `SAL-P3-001` DONE, P3 `1/17`, total `50/129`, `SAL-P3-002` READY, `DEC-048`, `AEV-050`, and `RSK-005` mitigation detail.
- Updated `docs/development-status.md`: current task is `SAL-P3-002`, Gate G3 remains pending, completed range includes `SAL-P3-001`, and the next-start prompt points to offline Wheel intake.
- Verification: target AlphaSift review + dependency locking tests `6 passed`; full pytest `238 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Checkpoint: `4e6d5ee4 docs(P3): 完成 AlphaSift 源码审查与锁定`。
- Scope retained: no AlphaSift Wheel build, no dependency install surface change, no ScreeningProvider/Adapter, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call and no DSA runtime source migration.

---

# Gate G2 Data and Task Review Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-020` by executing Gate G2 review for Dataset, Provider and persistent task foundations. Reuse P2 Dataset, Provider, PostgreSQL standalone Profile, PersistentTaskBackend, recoverable task event stream, ProblemDetails, Trace, Artifact and Data Sync evidence. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker runtime loops, frontend pages, Compose deployment, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-020` acceptance scope, Gate G1 constraints, P2 evidence records, Provider fallback, Dataset publication, Data Sync and task recovery boundaries.
- [x] Add a Gate G2 offline integration test proving versioned A-share Dataset publication, Provider conflict blocking, persistent task restart recovery, SSE replay and DSA single-stock compatibility path without real Provider calls.
- [x] Run target Gate G2 test, related P2 suite, full pytest, compile, lock, diff and immutable tag verification.
- [x] Create `docs/gate-g2-data-task-review.md` with Gate decision, evidence matrix, accepted risks, P3 entry constraints and verification outputs.
- [x] Update progress checklist, development status, risk/decision/evidence registers, this review and the next-session prompt.
- [x] Stage only `SAL-P2-020` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Gate G2 may approve entry into P3 screening/factor work only; it must not approve Quant Core, formal portfolio backtesting, Evidence Agent, live Provider/LLM calls, release deployment or full Worker execution loops.
- Dataset evidence must use immutable Dataset Version Manifest, Artifact hashes, schema hash, quality metadata, concrete trace/run/stage and explicit latest alias scope.
- Provider evidence must stay offline and contract-backed; stale/missing/error/quarantine/conflict paths must block success rather than silently averaging or advancing checkpoints.
- Task recovery evidence must keep database events authoritative; Celery/Redis routing remains injected/diagnostic and duplicate queue delivery must be neutralized by lease acquisition.
- DSA compatibility evidence must use injected offline manager/profile guard and must not instantiate the real DSA Provider manager.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-020

- Gate decision: `GO with accepted risks`; P2 data and persistent task foundations are complete `20/20`, and P3 starts at `SAL-P3-001`.
- Added `tests/gates/test_gate_g2_data_task_review.py`, covering offline AKShare fixture -> Provider Policy -> versioned A-share Dataset publication, cross-provider conflict quarantine, PersistentTaskBackend restart/SSE replay and DSA single-stock compatibility via injected offline manager.
- Added `docs/gate-g2-data-task-review.md` with Gate decision, evidence matrix, accepted risks and P3 entry constraints.
- Updated `docs/development-progress-checklist.md` with `SAL-P2-020` DONE, P2 `20/20`, total `49/129`, `SAL-P3-001` READY, `DEC-047`, `AEV-049`, and risk due-date updates for `RSK-002` / `RSK-004`.
- Updated `docs/development-status.md` to Phase P3, Gate G3 pending, completed range through `SAL-P2-020`, next READY task `SAL-P3-001`, and a copyable next-start prompt.
- Verification so far: Gate target `3 passed`; related P2 suite `80 passed, 3 skipped`; full pytest `236 passed, 3 skipped`; compileall PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, full Worker loop, Compose deployment, DSA runtime source migration or tag movement.

---

# P2 Recoverable Task Event Stream Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-019` by implementing recoverable task/run event streams with persisted `RunEvent`, SSE `Last-Event-ID` replay, queued orphan redispatch, stalled lease reconciliation, and temporary artifact cleanup. Reuse `PersistentTaskBackend` database-authoritative events, `TaskBackend.subscribe(after_event_id)`, PostgreSQL standalone Profile, ProblemDetails, TraceContext, Artifact temporary boundaries and Data Sync checkpoint semantics. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker execution loops, frontend pages, broad API endpoint migration or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-019` acceptance scope, PersistentTaskBackend, TaskBackend Protocol, RunEvent domain model, ProblemDetails, TraceContext, ArtifactStore and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-recoverable-task-event-stream.md`.
- [x] Add Red tests for SSE `Last-Event-ID` replay, invalid cursor validation, persisted RunEvent replay after restart, queued orphan redispatch, stalled lease requeue and temporary artifact cleanup.
- [x] Extend `repositories.persistent_task_backend` with persisted run events and queued-orphan redispatch without making queue state authoritative.
- [x] Implement `services.task_event_stream` with SSE frame DTOs, trace-safe event mapping, Last-Event-ID parsing and orphan/stalled reconciler.
- [x] Export service/repository symbols and preserve architecture boundaries without touching DSA runtime source, Provider SDKs, Quant Core or Evidence Agent.
- [x] Add acceptance evidence documentation for `SAL-P2-019`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-019` files and create the required Chinese checkpoint commit. Checkpoint: `15c3d555 feat(P2): 实现可恢复任务事件流`.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Database events remain authoritative; Celery/Redis delivery metadata is diagnostic and duplicate queue deliveries must be neutralized by DB lease acquisition.
- SSE recovery must replay from persisted events using monotonic event IDs; invalid `Last-Event-ID` maps to ProblemDetails-compatible validation failure.
- Reconciler may requeue stalled leases and redispatch old queued tasks, but must not mark stalled work as failed or execute handlers.
- Temporary cleanup may remove only configured artifact temp files older than cutoff; never delete blobs/manifests or Evidence artifacts.
- Tests use local SQLite and injected fake routers only; no real Provider/LLM/network calls, Quant Core, formal backtest or Evidence Agent.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-019

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.services.task_event_stream'`.
- Green implementation: added `services.task_event_stream` with `ServerSentEvent`, `TaskEventStreamService`, `TaskEventReconciler`, `TaskEventReconcilerSummary` and `parse_last_event_id()`, plus service exports.
- Persistence coverage: extended `PersistentTaskBackend` with `serenity_run_events`, `record_run_event()`, `subscribe_run_events()` and `redispatch_queued_orphans()`; task replay still uses `TaskBackend.subscribe(after_event_id)`.
- Recovery coverage: tests cover SSE `Last-Event-ID` replay, invalid cursor `ValidationProblem`, RunEvent persistence after backend restart, queued orphan redispatch, stalled lease requeue, duplicate-delivery lease guard and tmp-only artifact cleanup.
- Verification: target task event stream tests `8 passed`; related TaskBackend/Repository/API/Architecture suite `40 passed, 3 skipped`; full pytest `233 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no full Worker execution loop, formal API endpoint, frontend EventSource page, Compose service, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 PersistentTaskBackend Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-018` by implementing a database-authoritative `PersistentTaskBackend` with Celery/Redis queue routing boundaries, append-only task events, worker lease/heartbeat primitives, cancellation request recording, and expired-lease requeue. Reuse `TaskBackend` Protocol, Run/Event semantics, SQLAlchemy database profile, Alembic preflight assumptions, ProblemDetails-compatible errors, Trace/Artifact boundaries, Dataset/Provider scheduling constraints, and Data Sync Scheduler handoff. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker execution loops, API endpoints, SSE recovery, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-018` acceptance scope, TaskBackend Protocol, DSA facade, Run/Stage/Event domain model, database profile, repository contract patterns and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-persistent-task-backend.md`.
- [x] Add Red tests for persisted submit/get/subscribe after backend restart, idempotency replay, explicit task-id conflict, queue routing, cancellation request, lease heartbeat, completion and expired-lease requeue.
- [x] Implement `repositories.persistent_task_backend` with SQLAlchemy tables, `PersistentTaskBackend`, injected `CeleryTaskQueueRouter`, route DTOs, append-only events and lease helpers.
- [x] Export repository symbols and preserve architecture boundaries without importing Celery/Redis into application/domain/datasets or touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-018`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-018` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Database task/run rows and append-only task events are authoritative; Celery/Redis delivery metadata is diagnostic and must not become the source of truth.
- Queue payloads carry task/run IDs, task type and small routing metadata only; DataFrame, prompt text, Provider raw responses and large outputs remain Artifact-backed or out of scope.
- Worker helpers may claim leases, heartbeat, complete, fail and requeue expired leases; they must not execute Quant Core, formal backtest, Evidence Agent, Provider SDKs, LLM calls or DSA runtime tasks in this checkpoint.
- Tests use local SQLite and injected fake Celery-like routers only; optional live PostgreSQL contract remains guarded by `SERENITY_TEST_POSTGRES_URL`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-018

- Checkpoint: `94fd6dac feat(P2): 实现 PersistentTaskBackend`.
- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.persistent_task_backend'`.
- Green implementation: added `PersistentTaskBackend`, `TaskQueueRoute`, `TaskLease`, `TaskQueueRouter`, `CeleryTaskQueueRouter` and `NoopTaskQueueRouter` under `repositories.persistent_task_backend`, plus repository package exports.
- Persistence coverage: database tables `serenity_task_backend_runs` and `serenity_task_backend_events` are authoritative; backend restart preserves `TaskSnapshot`, `subscribe(after_event_id)` replays monotonic task events, and idempotency key replay avoids duplicate dispatch.
- Queue/worker coverage: injected Celery-like router sends only `task_id/run_id/task_type`; tests cover route mapping, cancel-request event, lease claim, heartbeat, completion and expired lease requeue.
- Verification: target persistent backend tests `5 passed`; related TaskBackend/Repository/API/Architecture suite `35 passed, 3 skipped`; full pytest `225 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no full Worker execution loop, API endpoint, SSE `Last-Event-ID`, orphan Reconciler, Compose service, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 PostgreSQL Standalone Profile Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-017` by establishing the PostgreSQL standalone Profile foundations: database configuration, connection pool, readiness checks and a shared Repository Contract suite. Reuse `SAL-P1-012` Alembic helpers and `SAL-P1-014` Runtime Profile; do not start Worker lease, PersistentTaskBackend execution, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-017` acceptance scope, Runtime Profile, Alembic storage migration helpers, existing Repository boundaries, TaskBackend contract and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-postgresql-standalone-profile.md`.
- [x] Add Red tests for standalone PostgreSQL URL resolution, SQLite defaults, engine/pool safety settings, health checks and same Repository Contract semantics.
- [x] Implement `repositories.database` with settings DTOs, engine factory, readiness diagnostics and SQLAlchemy Repository Contract probe.
- [x] Export repository symbols and preserve architecture boundaries without touching DSA runtime source, Provider SDKs, Worker runtime, Quant Core or Evidence Agent.
- [x] Add acceptance evidence documentation for `SAL-P2-017`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-017` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The database profile layer may create SQLAlchemy engines, run lightweight readiness checks and provide Repository Contract probes only; it must not implement Celery/Redis Worker lease, task execution, Scheduler dispatch, Quant Core, formal backtest or Evidence Agent behavior.
- Tests use local SQLite and optional `SERENITY_TEST_POSTGRES_URL`; no real Provider/LLM/network data calls are allowed.
- Repository Contract semantics must normalize UTC time, `Decimal`, JSON and rollback behavior across SQLite/PostgreSQL rather than relying on dialect quirks.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-017

- Checkpoint: `195765f3 feat(P2): 建立 PostgreSQL standalone Profile`.
- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py -q` failed because `serenity_alpha_lab.repositories.database` did not exist.
- Green implementation: added `DatabaseProfileSettings`, `DatabaseDialect`, `resolve_database_profile()`, `create_database_engine()`, `check_database_ready()`, `RepositoryContractProbeRecord` and `RepositoryContractProbeRepository` under `repositories.database`, plus repository package exports.
- Profile coverage: standalone requires explicit `SERENITY_DATABASE_URL`; PostgreSQL uses `psycopg`, `pool_pre_ping`, pool size/overflow/timeout, `statement_timeout=30000`, redacted diagnostics and `application_name`; SQLite enables foreign keys, busy timeout, WAL for file DBs and `StaticPool` for memory DBs.
- Repository Contract coverage: SQLite and optional live PostgreSQL (`SERENITY_TEST_POSTGRES_URL`) share one suite covering UTC datetime, `Decimal`, date, JSON normalization, duplicate-key conflict wrapping and rollback semantics.
- Verification: target profile/repository/storage tests `10 passed, 3 skipped`; related repositories/config/API/architecture suite `50 passed, 3 skipped`; full pytest `220 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; `psycopg` import smoke `3.3.4`; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Compose service, PersistentTaskBackend execution, Worker lease/heartbeat, Celery/Redis, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 SAL-P2-016 Status Refresh Plan

> Started: 2026-07-23
> Scope: Reconfirm recoverable development status after `SAL-P2-016` checkpoints `cfadc415` and `70f82cee`, update lessons for the repeated habit reminder, and keep the next-start prompt ready for `SAL-P2-017`.

## Checklist

- [x] Re-read current Git status, recent commits, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, and `tasks/todo.md`.
- [x] Confirm completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..016`; unfinished work resumes at `SAL-P2-017`.
- [x] Update `tasks/lessons.md` to record the repeated requirement to automatically sync status and provide a copyable next-start prompt after each phase task.
- [x] Refresh `docs/development-status.md`, `docs/development-progress-checklist.md`, and this review with the latest checkpoint anchors and constraints.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P2-016 Status Refresh

- Confirmed latest implementation checkpoint: `cfadc415 feat(P2): 实现增量同步与交易日调度`.
- Confirmed previous status-sync checkpoint: `70f82cee docs: 同步 SAL-P2-016 最新状态与恢复提示`.
- Current recoverable state remains P2 Data/Persistent Tasks, Gate G2 not passed, completed `45/129`, P2 `16/20`, next READY task `SAL-P2-017 PostgreSQL standalone Profile`.
- Scope constraints remain unchanged: no Worker lease, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, tag movement, destructive Git operation, or generated artifact submission.

---

# P2 Data Sync Scheduler Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-016` by implementing incremental data sync planning and trading-day scheduling with checkpoint, lookback window, lock protection, failure retry semantics, and backfill commands. Reuse Trading Calendar, Dataset Catalog/Manifest, Provider Policy/fallback trace, Run/Stage/Event, Trace scalar IDs, and existing Dataset boundaries. Do not start Quant Core, formal backtesting, Evidence Agent, PersistentTaskBackend, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-016` acceptance scope, Trading Calendar, Dataset Catalog, Raw Daily Bars incremental merge, Provider Policy fallback trace, Run lifecycle, and architecture guardrails.
- [x] Add Red tests for incremental scheduling, non-trading-day skip, checkpoint lookback, lock contention, failed Provider retry without checkpoint advance, idempotent completed-date recording, and historical backfill command planning.
- [x] Implement `services.data_sync` with checkpoint/lock store, `DataSyncScheduler`, `DataSyncRun`, and `DataBackfillCommand` without importing Provider SDKs or mutating Dataset modules.
- [x] Export service symbols and preserve architecture boundaries without touching DSA runtime source, Worker runtime, Quant Core, Evidence Agent, or real Provider/LLM paths.
- [x] Add acceptance evidence documentation for `SAL-P2-016`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-016` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Data sync scheduling consumes existing offline Dataset/Provider artifacts and injected Provider Policy outcomes only; it must not instantiate Provider SDKs, call DSA `DataFetcherManager`, probe networks, or publish real Provider data.
- Incremental runs must use concrete trading dates from `TradingCalendarDataset`, concrete `DatasetVersionManifest` lineage from Catalog, and explicit checkpoint state; `latest` remains discovery-only outside formal runs.
- Failed, quarantined, or exhausted Provider Policy outcomes must not advance checkpoint or create a success illusion; retries and backfills must remain idempotent.
- Tests use synthetic offline fixtures and local deterministic state only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-016

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/services/test_data_sync.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.services.data_sync'`.
- Checkpoint: `cfadc415 feat(P2): 实现增量同步与交易日调度`.
- Green implementation: added `DataSyncScope`, `DataSyncCheckpoint`, `DataSyncLock`, `LocalDataSyncStateStore`, `DataSyncScheduler`, `DataSyncPlan`, `DataBackfillCommand`, `DataSyncTradeDateResult` and `DataSyncRun` under `services.data_sync`, plus public service exports.
- Scheduling coverage: incremental plans use `TradingCalendarDataset`, checkpoint `last_completed_trade_date`, `lookback_window`, non-trading-day skip records and optional `LocalDatasetCatalog` latest lineage; backfill defaults to missing-only and supports explicit completed-date replay.
- Checkpoint and lock coverage: local state persists deterministic JSON checkpoint, validates completed/last-completed consistency, uses file `O_EXCL` scope locks, releases locks on complete/fail via `finally`, and treats duplicate successful trade dates idempotently.
- Provider Policy coverage: only `ProviderPolicyStatus.SELECTED` with a concrete Dataset version advances checkpoint; `EXHAUSTED` / `QUARANTINED` record failure and preserve retry eligibility without success illusion.
- Verification: target data sync test `5 passed`; related Trading Calendar/Catalog/Provider Policy/Run lifecycle/Architecture suite `35 passed`; full pytest `214 passed`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Provider SDK import, DSA `DataFetcherManager`, real Provider/LLM/network call, Bronze/Dataset publish, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, scheduled probe, DSA runtime source migration or tag movement.

---

# P2 SAL-P2-015 Status Sync Plan

> Started: 2026-07-23
> Scope: Refresh recoverable development status after `SAL-P2-015` checkpoint `378ba734`. Make completed/unfinished boundaries explicit, update the next-start prompt, and record the user's repeated habit reminder in project lessons.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, current Git status and recent commits.
- [x] Replace ambiguous checkpoint placeholders with actual `SAL-P2-015` implementation hash `378ba734`.
- [x] Confirm completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..015`; unfinished work resumes at `SAL-P2-016`.
- [x] Update `tasks/lessons.md` so future phase-task completion automatically performs status snapshot, progress checklist, evidence, review and next-start prompt synchronization.
- [x] Run status-anchor scans and whitespace diff verification.
- [x] Stage only status-sync documentation files and create the required Chinese checkpoint commit.

## Review: SAL-P2-015 Status Sync

- Updated `docs/development-status.md` and `docs/development-progress-checklist.md` to use actual implementation checkpoint `378ba734 feat(P2): 实现 Provider Policy 与 fallback trace`.
- Preserved current executable task as `SAL-P2-016` and kept Gate G2 as not passed.
- Recorded the user's habit reminder in `tasks/lessons.md`, including the rule that implementation checkpoint hashes must be explicit after each phase task.
- Next-start prompt now points to `SAL-P2-016` and repeats the profile, Provider Policy/fallback trace, Dataset, ADR/Gate and no-early-Quant/Evidence constraints.

---

# P2 Provider Policy Fallback Trace Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-015` by adding an offline Provider Policy and fallback trace layer. Select sources by capability, market, freshness, required fields, data-quality status, and cross-provider conflict threshold. Reuse Provider domain contracts, Provider contract fixtures, Trace scalar attribution, Data Quality status semantics, Dataset publication quarantine vocabulary, and ProblemDetails-compatible validation boundaries. Do not call real Providers/LLMs, do not implement Worker runtime, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, scheduled probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect `SAL-P2-015` acceptance scope, Provider fixtures, Provider domain contracts, quality/publication semantics, API error mapping, and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-provider-policy-fallback-trace.md`.
- [x] Add Red tests for first fresh complete source selection, stale/missing-field fallback, Provider error trace, exhausted fallback, and cross-provider close-conflict quarantine.
- [x] Implement `integrations.data.provider_policy` with YAML-compatible policy DTOs, selection engine, fallback attempt trace, conflict records, and deterministic diagnostics.
- [x] Export policy symbols and preserve architecture boundaries without touching DSA runtime source or Provider SDKs.
- [x] Add acceptance evidence documentation for `SAL-P2-015`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-015` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Provider Policy consumes already-normalized offline `DataBatch` / `ProviderError` outcomes only; it must not instantiate Provider SDKs, call DSA `DataFetcherManager`, probe networks, publish Datasets, or mutate Provider fixture snapshots.
- Successful Provider data can still be rejected for stale freshness, missing required fields, quarantine/blocking quality status, schema mismatch, or cross-source conflict.
- Cross-provider conflicts over threshold enter quarantine and must not be hidden by averaging or silent overwrite.
- Tests use synthetic offline fixture cases and local deterministic records only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-015

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_policy'`.
- Green implementation: added `ProviderPolicy`, `ProviderPolicySource`, `ProviderSelectionRequest`, `ProviderPolicyEngine`, `ProviderFallbackAttempt`, `ProviderConflictRecord`, `ProviderFallbackTrace` and `ProviderSelectionResult` under `integrations.data`.
- Selection coverage: first fresh complete source wins by policy priority; stale `DataBatch`, dataset mismatch, missing required fields and `DataQualityStatus.BLOCKING` trigger rejection/fallback; Provider errors are recorded as `provider_<category>` and exhausted attempts return no selected batch.
- Conflict coverage: cross-provider `close` differences over configured bps threshold return `quarantined`, record provider values and primary key, and do not average or silently overwrite.
- Verification: target Provider Policy test `6 passed`; related Provider/Quality/Publication/API/Architecture suite `59 passed`; full pytest `209 passed`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Provider SDK import, DSA `DataFetcherManager`, real Provider/LLM/network call, Bronze/Dataset write, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, scheduled probe, DSA runtime source migration or tag movement.

---

# P2 Provider Contract Fixtures Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-014` by adding an offline Provider contract fixture corpus for AKShare, efinance, Tushare, BaoStock, and YFinance. Cover sanitized responses, schema bindings, timeout, empty-data, and field-drift cases. Reuse Provider domain contracts, DSA Provider Adapter semantics, Arrow Schema Registry, Trace/Run/Stage scalar attribution, ProblemDetails-compatible provider errors, and Dataset publication boundaries. Do not implement fallback policy, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Provider contract, DSA adapter, Arrow Schema Registry, docs, and tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-provider-contract-fixtures.md`.
- [x] Add Red tests for offline Provider fixture coverage, success batch conversion, timeout/empty/schema-drift errors, deterministic sanitized snapshots, and SDK import avoidance.
- [x] Implement `integrations.data.provider_contract_fixtures` with frozen DTOs, default corpus, Provider `DataBatch` conversion, ProviderError mapping, schema validation, and snapshot writer.
- [x] Export fixture symbols and preserve architecture boundaries without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-014`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-014` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Provider fixtures are offline contract samples only; they must not choose fallbacks, probe live endpoints, instantiate Provider SDKs, or call DSA `DataFetcherManager`.
- Fixtures may expose sanitized raw responses, expected schema metadata, normalized records, and expected error categories; they must not contain secrets, tokens, cookies, absolute local paths, prompts, or personal data.
- Tests use synthetic offline rows and local deterministic JSON only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-014

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_contract_fixtures'`.
- Green implementation: added `ProviderContractFixtureCatalog`, `ProviderContractFixtureCase`, `ProviderFixtureSchema`, `ProviderFixtureStatus`, `default_provider_contract_fixture_catalog()` and `write_provider_fixture_snapshots()` under `integrations.data`.
- Fixture coverage: AKShare、efinance、Tushare、BaoStock 和 YFinance all have offline success samples; YFinance covers US and HK basic paths; timeout, empty and schema-drift cases map to `retryable`, `data_invalid` and `schema_drift`.
- Snapshot coverage: generated deterministic sanitized JSON files under `docs/baselines/provider-contract-fixtures/`, with raw-response SHA-256, Provider-facing schema and `dataset.bars_1d_raw@1.0.0` Arrow schema hash.
- Verification: target fixture test `4 passed`; related Provider/Schema/API/Architecture suite `58 passed`; full pytest `203 passed`; compileall, dependency lock, `git diff --check`, snapshot secret scan and immutable tag checks passed. Checkpoint: `5016ced6 feat(P2): 建立 Provider 契约 Fixture`.
- Scope retained: no fallback policy beyond expected error-category fixture labels, no real Provider/LLM/network calls, no PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

## Review: SAL-P2-014 Status Refresh

- User requested another latest-status refresh and a reusable next-start prompt after `SAL-P2-014`.
- Confirmed current state from Git: latest implementation checkpoint `5016ced6 feat(P2): 建立 Provider 契约 Fixture`; previous status-sync checkpoint `8c70cde5 docs: 同步 SAL-P2-014 最新开发状态与恢复提示`.
- Confirmed ledgers remain: P0 `13/13`, P1 `16/16`, P2 `14/20`, total `43/129`; Gate G2 is not passed.
- Updated recovery anchors in `docs/development-status.md`, `docs/development-progress-checklist.md`, and `tasks/lessons.md`; next executable task remains `SAL-P2-015 Provider Policy 与 fallback trace`.

---

# P2 Dataset Atomic Publication Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-013` by adding quality-gated Dataset publication, quarantine/held state records, atomic latest promotion, and temporary file cleanup. Reuse Dataset Catalog/Manifest, Data Quality Report metadata, ArtifactStore manifest-last semantics, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible `ValueError` mapping. Do not implement fallback policy, Provider fixtures, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Dataset Catalog, ArtifactStore, Data Quality Rule Engine, docs, and tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-dataset-atomic-publication.md`.
- [x] Add Red tests for quality-gated latest promotion, warning/quarantine/blocking latest retention, quarantine records, failed-publish cleanup, and old latest retention.
- [x] Implement `datasets.publication` and narrow Catalog helpers for promote/latest and quarantine record persistence.
- [x] Export publication symbols and preserve architecture boundaries without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-013`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-013` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Only `DataQualityStatus.PASSED` may promote a Dataset version to `latest`; `warning`, `quarantine`, `blocking`, and failed publication attempts must leave the old latest pointer unchanged.
- Publication may persist immutable Dataset Manifest metadata and quarantine/held records only; it must not choose Provider fallback, average across Provider conflicts, or call real Providers.
- Tests use synthetic offline rows and local artifacts only; no real Provider/LLM/network calls.
- Temporary cleanup is limited to explicit temp roots (`ArtifactStore.tmp_root` and `LocalDatasetCatalog.tmp_root`) and must not delete immutable blobs, manifests, aliases, or unrelated directories.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-013

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.publication'`.
- Green implementation: added `QualityGatedDatasetPublisher`, `DatasetPublicationRequest`, `DatasetPublicationResult`, `DatasetPublicationStatus`, explicit `LocalDatasetCatalog.promote_to_latest()`, quarantine record persistence and bounded temp-root cleanup.
- Publication coverage: `passed` quality promotes `latest`; `warning`, `quarantine` and `blocking` write held/quarantine/blocking records and keep old latest; latest-promotion failure propagates and cleans explicit catalog/artifact tmp roots.
- Verification: target publication test `5 passed`; related dataset/artifact/API/architecture suite `66 passed`; full pytest `199 passed`; compileall, dependency lock, `git diff --check` and immutable tag checks passed. Checkpoint: `8edd723a feat(P2): 实现 Dataset 隔离区与原子发布`.
- Scope retained: no fallback policy, Provider fixture/probe, real Provider/LLM/network call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

---

# P2 Data Quality Rule Engine Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-012` by adding an offline data quality rule engine for Dataset snapshots. Reuse Dataset Catalog/Manifest metadata, Arrow Schema Registry declarations, ArtifactStore publishing, ProblemDetails-compatible `ValueError` mapping, trace/run/stage scalar attribution, and existing P2 Dataset record shapes. Do not implement SAL-P2-013 quarantine/latest blocking transactions, fallback policy, Provider fixtures, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset publish patterns, Arrow Schema Registry, Dataset Catalog, ArtifactStore and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-data-quality-rule-engine.md`.
- [x] Add Red tests for warning/quarantine/blocking rules, issue location, manifest metadata, report artifact publishing and ProblemDetails mapping.
- [x] Implement `quality.py` with rule protocol, built-in rules, report DTOs, deterministic report publishing and manifest metadata helper.
- [x] Export quality symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-012`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review and the next-session prompt.
- [x] Stage only `SAL-P2-012` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The quality engine may classify reports as `passed`, `warning`, `quarantine` or `blocking`, and may provide manifest metadata; it must not block latest alias updates or implement atomic publish/quarantine cleanup. That remains `SAL-P2-013`.
- Tests use synthetic offline rows and local artifacts only; no real Provider/LLM/network calls.
- Rules must locate every issue by dataset, optional dataset version, partition, primary key, field and sample payload.
- Rule set version and quality status must be available for Dataset Manifest metadata without changing the immutable Catalog transaction semantics.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-012

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.quality'`; a later location hardening assertion also failed before `NullRatioDriftRule` was fixed.
- Green implementation: added `QualityDatasetSnapshot`, `DataQualityIssue`, `DataQualityReport`, `DataQualityEngine`, `DataQualitySeverity`, `DataQualityStatus` and built-in rules for unique primary keys, schema/type checks, OHLC, non-negative fields, null-ratio drift, trading continuity, return outliers, volume spikes and adjustment-factor jumps.
- Report coverage: every tested issue carries dataset/version/partition/field/primary-key/sample context; reports publish deterministic `ArtifactStore` JSON and expose Dataset Manifest metadata for rule set version, quality status, issue counts and report artifact hash.
- Verification: target data-quality test `4 passed`; related dataset/artifact/API/architecture suite `61 passed`; full pytest `194 passed`; compileall, dependency lock, `git diff --check` and immutable tag checks passed. Checkpoint: `3a846c6a feat(P2): 实现数据质量规则引擎`.
- Scope retained: no `SAL-P2-013` latest blocking/quarantine transaction, fallback policy, Provider fixture/probe, real Provider/LLM/network call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

---

# P2 Dataset Catalog And Manifest Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-011` by adding Dataset Catalog and Manifest support for immutable dataset versions, file hashes, lineage, previous-version links, and mutable `latest` aliases. Reuse P1 `ArtifactStore`, P2 Dataset artifact manifests, Arrow Schema Registry, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation boundaries. Do not start data quality rules, fallback policy, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset publish patterns, `ArtifactManifest`, `LocalArtifactStore`, Arrow Schema Registry, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-dataset-catalog-manifest.md`.
- [x] Add Red tests for immutable version manifests, file hashes, schema hash binding, lineage, previous version linkage, latest alias resolution, formal-run latest rejection, and atomic alias behavior.
- [x] Implement `catalog.py` with immutable manifest DTOs, version references, local repository persistence, alias resolution, and idempotent immutable publish checks.
- [x] Export catalog symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-011`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-011` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Catalog may register immutable Dataset version metadata and update mutable `latest` aliases only; it must not implement quality rules, quarantine/blocking behavior, fallback policy, Provider fixture probing, Worker runtime, Quant Core, formal backtest or Evidence behavior.
- Published dataset versions are immutable; same version ID can only be observed idempotently if the manifest content is byte-equivalent.
- Formal runs and experiments must resolve concrete `dataset_version` IDs; `latest` is allowed for discovery/research display only.
- Tests stay offline with synthetic artifacts and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-011

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q` failed during collection with `ImportError: cannot import name 'catalog' from 'serenity_alpha_lab.datasets'`.
- Green implementation: added `DatasetFileManifest`, `DatasetVersionManifest`, `DatasetVersionRef`, `DatasetReferencePurpose`, `DatasetVersionRefKind` and `LocalDatasetCatalog`; package exports now expose the catalog API through `serenity_alpha_lab.datasets`.
- Catalog coverage: tests cover immutable version manifest publishing, Artifact URI/SHA-256/file row-count capture, schema hash binding to `ArrowSchemaRegistry`, previous/input lineage, deterministic JSON persistence, idempotent republish and mutation rejection.
- Alias coverage: `latest` is persisted separately after the version manifest; research display can resolve latest, formal experiment resolution rejects latest and requires concrete dataset version; alias publish failure leaves the old latest pointer intact.
- Verification: target catalog `5 passed`; related dataset/artifact/architecture suite `45 passed`; full pytest `190 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed. Checkpoint: `8a77e4cf feat(P2): 实现 Dataset Catalog 与 Manifest`.
- Review note: subagent dispatch was attempted but blocked by client payload validation (`message/items` conflict). Local review checked import boundaries, deterministic manifest bytes, alias failure semantics, immutable version handling and strict scope.
- Scope retained: no data quality rule engine, warning/quarantine/blocking behavior, failed-Dataset latest blocking, fallback policy, Provider fixture/probe, real Provider/LLM call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Arrow Schema Registry Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-010` by adding an offline, versioned Arrow Schema Registry for instrument master, raw daily bars, corporate actions, adjusted daily bars, and fundamentals. Reuse existing P2 Dataset schema constants, Artifact schema metadata, P1/P2 validation and ProblemDetails boundaries, and lazy optional PyArrow from the `quant` extra. Do not start fallback policy, real Provider calls, Dataset Catalog/latest alias, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset schema constants, deterministic JSON artifact payloads, and optional PyArrow dependency boundary.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-arrow-schema-registry.md`.
- [x] Add Red tests for default registry coverage, PyArrow schema conversion, semantic-version compatibility, duplicate registration, required-field validation, Pandas/Polars/Arrow round-trip stability, and optional PyArrow import behavior.
- [x] Implement `schema_registry.py` with immutable schema declarations, lazy PyArrow conversion, default P2 registrations, canonical hashing, and compatibility reports.
- [x] Add instrument master field schema/partition metadata and export registry symbols.
- [x] Add acceptance evidence documentation for `SAL-P2-010`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-010` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Registry may define Arrow schemas and compatibility checks only; it must not publish Dataset Catalog/latest aliases or enforce quality gates.
- PyArrow must remain lazily imported so root `core+dev` tests still import `serenity_alpha_lab.datasets` without the `quant` extra.
- Minor/patch schema versions may add backward-compatible nullable fields; deleting fields, changing types, or changing existing field meaning requires a new major version.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-010

- Red evidence: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.schema_registry'`.
- Green implementation: added `DatasetSchemaField`, `DatasetSchemaDeclaration`, `SchemaCompatibilityReport`, `SchemaCompatibilityStatus` and `ArrowSchemaRegistry`; default registry now covers instrument master, raw daily bars, corporate actions, adjusted daily bars and PIT fundamentals.
- Compatibility coverage: tests cover duplicate version rejection, semver ordering, nullable-field minor additions, required-field additions, type changes, removed fields, primary-key validation and breaking-change major version rules.
- Arrow coverage: tests cover lazy PyArrow conversion, schema metadata, canonical schema hash, Arrow validation, Arrow -> Pandas -> Arrow and Arrow -> Polars -> Arrow round-trip; Polars nullability loss is explicitly handled with `strict_nullability=False`.
- Reuse coverage: instrument master now exports `INSTRUMENT_MASTER_FIELD_SCHEMA` and `INSTRUMENT_MASTER_PARTITION_KEYS` and publishes deterministic JSON payloads with `field_schema` / `partition_keys`, matching later P2 Dataset patterns.
- Verification: schema registry target `6 passed`; instrument master related `9 passed`; P2 related suite `62 passed`; full pytest `185 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted code-reviewer subagent dispatch multiple times after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked schema ordering, optional PyArrow imports, semver compatibility logic, package exports, circular import risk, scope guardrails and deterministic payload changes.
- Scope retained: no fallback policy, real Provider call, Dataset Catalog/latest alias implementation, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.
- Status sync: after user reminder, refreshed `docs/development-status.md`, `docs/development-progress-checklist.md`, this checklist, and `tasks/lessons.md` to make the completed/unfinished split, explicit `3e2056fe` delivery checkpoint, `SAL-P2-011` next task, and automatic status-sync habit recoverable in the next session.

---

# P2 PIT Fundamental Dataset Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-009` by adding an offline point-in-time fundamental Dataset. Reuse P2 Provider `DataBatch`/`Provenance`, Instrument Master Dataset, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Distinguish period, announced, available, ingested and revision timing. Do not start fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset patterns and SAL-P2-009 acceptance scope.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-pit-fundamental-dataset.md`.
- [x] Add Red tests for PIT schema, period/announced/available/ingested/revision timing, latest-as-of query, temporal confidence gate, Provider batch conversion, Bronze lineage, ArtifactStore publishing, invalid timing, and validation error mapping.
- [x] Implement `FundamentalRecord` and `FundamentalsDataset` with deterministic JSON Artifact publishing, query indexes, revision selection, incremental merge and formal-backtest temporal-confidence guard.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-009`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-009` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Use synthetic offline Provider `DataBatch` records only; do not instantiate or call a real Provider.
- PIT queries must filter `available_at <= decision_time`; latest revisions with later `available_at` must not leak into earlier decisions.
- Historical DSA-style records without trustworthy announcement time must be marked `temporal_confidence=unknown`, allowed only for research display and rejected for formal backtest queries.
- Dataset records may publish deterministic Artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, Worker runtime, Quant Core, formal backtest or Evidence behavior.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-009

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.fundamentals'`.
- Green implementation: added `FundamentalRecord`, `FundamentalsDataset`, `FundamentalPeriodType`, `TemporalConfidence` and `FundamentalQueryPurpose` with deterministic JSON Artifact publishing, Provider `DataBatch` conversion, query indexes and incremental primary-key replacement.
- PIT coverage: tests cover `period_end` / `announced_at` / `available_at` / `ingested_at` / `revision`, `available_at <= decision_time`, latest revision selection, future-revision exclusion, history query, Bronze lineage and source hash propagation.
- Temporal confidence coverage: legacy DSA-style records without trustworthy announcement time are marked `unknown`, allowed for research display, and rejected for formal backtest queries.
- Verification: target fundamentals `4 passed`; related dataset/provider/architecture suite `51 passed`; full pytest `179 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted read-only explorer subagent dispatch after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked diff scope, import boundaries, PIT timing invariants, formal-backtest gate, deterministic artifact payload and guardrails.
- Scope retained: no fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA `fundamental_snapshot` formal migration, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

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

---

# P2 Raw Daily Bars Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-007` by adding a deterministic raw daily bars Dataset for unadjusted OHLCV/amount records. Reuse P2 Provider `DataBatch`/`Provenance`, Instrument Master Dataset, Trading Calendar Dataset, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start corporate actions/adjusted bars, PIT/fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Instrument Master Dataset, Trading Calendar Dataset, Provider daily-bar contract, Bronze raw store, ArtifactStore, ProblemDetails and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-raw-daily-bars-dataset.md`.
- [x] Add Red tests for raw daily bar schema, Provider batch conversion, key uniqueness, OHLC/volume/amount validation, instrument/calendar checks, source timestamp, Bronze lineage, query helpers, ArtifactStore publishing, and validation error mapping.
- [x] Implement `RawDailyBarsDataset` with immutable unadjusted bar records, offline indexes, Provider batch conversion and deterministic JSON ArtifactStore publishing.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-007`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-007` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Raw daily bars may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, adjusted bars, corporate actions, PIT/fallback policy, quality gates, Worker runtime, or Quant Core behavior.
- Consume injected/offline Provider `DataBatch` values only; do not instantiate or call a real Provider.
- Raw bars remain unadjusted; do not add split/dividend/corporate-action or adjusted price behavior.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-007

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.raw_daily_bars'`.
- Green implementation: added `RawDailyBar`, `RawDailyBarsDataset`, Arrow-compatible field schema constants, Provider `DataBatch` conversion, Instrument Master as-of validation, Trading Calendar trading-day validation, immutable offline indexes, deterministic JSON ArtifactStore publishing and primary-key replacement via `merge_incremental()`.
- Reuse coverage: P1/P2 `InstrumentId`, `Market`, Provider `DataBatch`/`Provenance`, `ArtifactStore`, Bronze `source_bronze_artifact_id`, Instrument Master Dataset, Trading Calendar Dataset, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests.
- Verification: target raw daily bars `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `59 passed`; full pytest `172 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted independent `code-reviewer` subagent dispatch multiple times, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked diff scope, imports, OHLC/amount/calendar/master validations, deterministic artifact payload, and guardrails; no Critical or Important issue found.
- Scope retained: no adjusted bars, corporate actions, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Trading Calendar Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-006` by adding a deterministic Trading Calendar Dataset with market time zones, trading dates, open/close sessions, lunch breaks, half-day/ad-hoc closure semantics, query caches, Bronze lineage and ArtifactStore publishing. Reuse P1/P2 Market/InstrumentId identity boundaries, Provider calendar contract shape, Trace/Run/Stage scalar attribution, ProblemDetails-compatible validation errors, ArtifactStore, Bronze lineage and the Instrument Master market model. Do not start raw daily bars, PIT/fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing InstrumentId/Market, Provider calendar contract, ArtifactStore, Bronze raw store, Instrument Master Dataset, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-trading-calendar.md`.
- [x] Add Red tests for market time zones, sessions, A-share holiday/half-day/ad-hoc closure policy, UTC/Asia-Shanghai boundaries, cached queries, Bronze lineage, ArtifactStore publishing, and validation errors.
- [x] Implement `TradingCalendarDataset` with immutable records, in-memory indexes, timezone/session query APIs and deterministic JSON ArtifactStore publishing.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-006`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-006` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-006

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.trading_calendar'`.
- Green implementation: added `MarketSession`, `TradingSessionStatus`, `TradingCalendarDataset`, frozen market timezone mapping, explicit A-share holiday/half-day/ad-hoc closure semantics, UTC conversion helpers, in-memory query indexes, trading-day/previous/next/open-at query APIs and deterministic JSON `ArtifactStore` publishing.
- Reuse coverage: P1 `Market`, P1 `ArtifactStore`, Bronze `source_bronze_artifact_id`, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests; no DSA runtime source or real Provider path was imported.
- Verification: target trading calendar `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `56 passed`; full pytest `169 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted to use subagent tooling for independent exploration/review, but the client repeatedly rejected `spawn_agent` payload variants as duplicate `message/items` or empty override fields. Local senior review checked diff scope, import boundaries, timezone/session invariants, explicit-closure policy and guardrails.
- Scope retained: no raw daily Dataset, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Calendar records may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, raw daily bars, PIT/fallback policy, quality gates, Worker runtime, or Quant Core behavior.
- Use explicit `Market + trade_date` calendar records; do not infer holidays from current date, live Provider responses, or mutable network state.
- A-share holiday, half-day and ad-hoc closure policy is explicit-record based: closed records carry no open/close times, half-day records carry shortened sessions, and exceptional closures use a distinct status/note.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


---

# P2 Instrument Master Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-005` by adding a historical instrument master Dataset with validity-windowed securities and provider mappings. Reuse P1/P2 InstrumentId, Provider Symbol Mapping, ArtifactStore, Bronze lineage, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start trading calendar, raw daily bars, PIT/fallback policy, Dataset Catalog/latest alias, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing InstrumentId, Provider contract, ArtifactStore, Bronze raw store, Trace, ProblemDetails, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-instrument-master-dataset.md`.
- [x] Add Red tests for instrument schema, historical as-of lookup, provider mapping validity windows, uniqueness/overlap validation, Bronze lineage, and ArtifactStore publishing.
- [x] Implement `InstrumentMasterDataset` with deterministic JSON artifact publishing and offline query helpers.
- [x] Export dataset symbols and add/adjust architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-005`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-005` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-005

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.instrument_master'`.
- Green implementation: added `InstrumentMasterDataset`, `InstrumentMasterRecord`, `IndustryClassification`, `ProviderSymbolValidity`, listing status enum, as-of record/provider-mapping lookup, overlap/duplicate validation and deterministic JSON ArtifactStore publishing.
- Reuse coverage: canonical `InstrumentId`, `ProviderSymbolMapping`, Bronze `source_bronze_artifact_id`, `ArtifactStore`, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests.
- Verification: target instrument master `3 passed`; dataset/architecture suite `15 passed`; related domain/provider/artifact/repository/API/trace suite `81 passed`; full pytest `166 passed`; py_compile, dependency lock and immutable tag checks passed.
- Review note: attempted `code-reviewer` subagent dispatch after tool discovery, but the client rejected both item/message payload attempts as duplicate inputs. Local review checked diff scope, imports, validity-window semantics and guardrails; no DSA runtime import, real Provider/LLM call, PIT/fallback policy, Quant Core, formal backtest or Evidence Agent work was introduced.
- Scope retained: no trading calendar, raw daily bars, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Instrument master may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, Silver/PIT tables, trading calendar, daily bars, fallback policy, or quality gate behavior.
- Provider mappings must be scoped by validity windows and must point back to canonical `InstrumentId`.
- Every record must carry Bronze source artifact lineage for auditability.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


---

# P2 Bronze Raw Data Layer Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-004` by adding a Bronze raw data layer that stores sanitized, compressed, content-addressed provider raw responses with auditable request metadata. Reuse P1/P2 ArtifactStore, Provider Provenance, TraceContext, ProblemDetails redaction boundaries, Run/Stage metadata, and compatibility constraints. Do not start Dataset/PIT/fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing ArtifactStore, Provider Provenance/DataBatch, Trace redaction, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-bronze-raw-data-layer.md`.
- [x] Add Red tests for Bronze artifact schema, gzip compression, hash metadata, provider/request/time traceability, Run/Stage attribution, and secret/Cookie/PII redaction before disk.
- [x] Implement `BronzeRawStore` over the existing `ArtifactStore` contract with deterministic JSON + gzip payloads and local query helpers.
- [x] Export repository symbols and add architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-004`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-004` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-004

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.bronze_raw_store'`.
- Green implementation: added `BronzeRawStore`, immutable `BronzeRawArtifact`, deterministic JSON envelope + `gzip` compression, `ArtifactStore` publishing, `get_envelope()`, local `find_raw_artifacts()` scanning, and repository exports.
- Audit coverage: envelope records provider/operation, sanitized request parameters, requested/fetched/source timestamps, source raw hash, sanitized raw payload hash, field lineage, trace/run/stage IDs and archive retention.
- Security coverage: request and raw-response payloads are recursively sanitized before bytes reach `ArtifactStore`; tests assert API key, token, Authorization, Cookie/Set-Cookie, email, phone/mobile and identity-card values are absent from manifest/blob/decompressed bytes.
- Verification: Bronze target `6 passed`; related repositories/provider/trace/architecture suite `56 passed`; full pytest `162 passed`; py_compile, dependency lock, immutable tag check and `git diff --check` passed.
- Scope retained: no Dataset Catalog, Silver/PIT, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Bronze may store sanitized raw provider payloads and request metadata only through the existing ArtifactStore boundary; it must not write Dataset Catalog, Silver/PIT tables, quality gates, or fallback policy.
- Store compressed payloads deterministically and preserve both source raw-response hash from Provider Provenance and sanitized payload hash for audits.
- Redact API keys, tokens, Authorization, Cookie/Set-Cookie, prompts/bodies, e-mail, phone/mobile and common identity fields before bytes are handed to ArtifactStore.
- Require Run attribution through `produced_by_run_id` or `Provenance.run_id`; carry stage and trace IDs when available.
- Keep tests offline with synthetic raw responses; make zero real Provider/LLM/network calls.

---

# P2 Symbol Compatibility Migration Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-003` by wrapping DSA `normalize_stock_code` compatibility semantics with `InstrumentId` and explicit Provider Symbol Mapping. Reuse the P1 `InstrumentId` domain model and P2 DSA Provider Adapter facade. Do not start Bronze/Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, current git state, P1 InstrumentId, and P2 Provider Adapter.
- [x] Inspect DSA `normalize_stock_code` implementation, P0 conversion tests, and current Serenity adapter call path.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-symbol-compatibility-migration.md`.
- [x] Add Red tests for P0-compatible stock-code conversions, ambiguity errors, validity windows, provider mappings, and adapter wrapper usage.
- [x] Implement DSA symbol compatibility mapper and immutable mapping record.
- [x] Wire `DsaProviderCompatibilityAdapter` and `DsaStockHistoryCompatibilityFacade` through the mapper.
- [x] Add architecture guard and evidence documentation.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-003` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Keep legacy payload `stock_code` behavior compatible, but store/carry canonical `instrument_id` for new provider paths and provenance.
- Bare 6-digit symbols may be accepted only through explicit legacy market context; strict domain conversion must keep raising ambiguity errors.
- Do not persist naked symbols as cross-market primary keys; use `InstrumentId.canonical`.
- `SAL-P2-003` is not Bronze/Dataset/PIT/fallback-policy/PersistentTaskBackend work. Gate G2 remains not passed.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-003

- Red evidence: `.cache/dsa-p0/venv/bin/python -m pytest ...` could not run because the documented P0 venv is absent locally; fallback `uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.symbol_compatibility'`.
- Green implementation: added `DsaStockCodeCompatibilityMapper`, immutable `DsaStockCodeMapping`, and local `normalize_stock_code_compatible()` mirror for P0 DSA conversion cases; wired `DsaProviderCompatibilityAdapter` and `DsaStockHistoryCompatibilityFacade` through the mapper.
- Compatibility coverage: A-share SH/SZ/SS/BJ prefix/suffix, HK prefix/suffix zero-padding, JP/KR/TW Yahoo suffixes, US ticker, bare 6-digit ambiguity, explicit exchange conflicts, provider symbol mappings, and validity windows.
- Verification so far: target symbol/adapter suite `25 passed`; related symbol/adapter/domain/architecture suite `72 passed`; full pytest `155 passed`; py_compile and `scripts/verify-python-dependency-lock.sh` passed.
- Review note: attempted independent `code-reviewer` dispatch multiple times, but the client rejected payload variants as duplicate message/items inputs. Local diff review found no eager DSA runtime import; the only `data_provider` hit remains the intended lazy import in `provider_adapter.py`.
- Scope retained: no Bronze/Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Status Sync After DSA Provider Adapter

> Started: 2026-07-21
> Scope: Refresh latest development status after `SAL-P2-002` checkpoint `68e8fea9`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P2-003` implementation in this sync.

## Checklist

- [x] Confirm current git status and latest checkpoints.
- [x] Update `docs/development-status.md` with explicit `68e8fea9` delivery checkpoint, current READY tasks, unfinished scope, and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the actual `SAL-P2-002` checkpoint.
- [x] Record the repeated habit in `tasks/lessons.md`.
- [x] Re-scan state anchors and run `git diff --check`.
- [x] Stage only status-sync docs and create the required Chinese status checkpoint commit.

## Review: P2 Status Sync After DSA Provider Adapter

- Confirmed current branch is `codex/p0-baseline-status`, ahead of origin by 31 before this docs sync, with latest functional checkpoint `68e8fea9 feat(P2): 实现 DSA Provider 兼容适配器`.
- Confirmed completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, and `SAL-P2-001..002`; P2 progress remains `2/20`, total progress remains `31/129`, and Gate G2 remains not passed.
- Confirmed current READY tasks are `SAL-P2-003` and `SAL-P2-004`; `SAL-P2-003` is the preferred next implementation task, while `SAL-P2-004` can be prepared without starting Dataset/PIT/fallback policy or real Provider calls.
- Preserved scope boundaries: no code changes, no DSA source migration, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call, no tag movement, and no generated/cache artifacts.

---

# P2 DSA Provider Compatibility Adapter Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-002` by wrapping DSA `DataFetcherManager`/Pandas daily-bar output behind the frozen Provider domain contract. Reuse P1 Profile, ProblemDetails, TraceContext, Artifact/Run boundaries and Compatibility Facade patterns where they apply. Do not start Dataset/PIT, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, current git state, and P2 Provider contract.
- [x] Inspect DSA `DataFetcherManager` daily-data return shape, source handling, diagnostics behavior, and existing DSA market-routing tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-dsa-provider-compatibility-adapter.md`.
- [x] Add Red tests for the DSA Provider adapter, ProviderError mapping, CI profile guard, trace/provenance propagation, and feature-flag facade switching.
- [x] Implement `DsaProviderCompatibilityAdapter` and stock-history compatibility facade with injected manager support and lazy real-DSA import.
- [x] Add architecture guard and evidence documentation.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Attempt independent code review; tool rejected message/items payload variants, so complete and record local senior review fallback.
- [x] Stage only `SAL-P2-002` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The adapter may lazily import DSA from the isolated worktree, but tests must use injected fakes and make zero real Provider/LLM/network calls.
- Preserve the frozen Provider domain contract from `SAL-P2-001`; do not modify it unless a failing adapter contract exposes a real defect.
- `CI` profile must block constructing a default real DSA manager; injected stub managers remain allowed for offline tests.
- `SAL-P2-002` is not Dataset/Bronze/PIT/fallback-policy/PersistentTaskBackend work. Keep `RSK-004` open and Gate G2 not passed.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-002

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_provider_adapter.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.provider_adapter'`.
- Green implementation: added `DsaProviderCompatibilityAdapter`, lazy `create_default_dsa_data_fetcher_manager()`, schema/row normalization, Provider provenance hashing/lineage/TraceContext propagation, ProviderError classification, and `DsaStockHistoryCompatibilityFacade` feature flag switching.
- Boundary review: no DSA runtime source was copied or modified; real `data_provider.base` is referenced only by `importlib.import_module()` inside the lazy factory; AST imports are limited to stdlib, P1 application facades, domain contracts and DSA entrypoint resolver.
- Verification: target adapter tests `8 passed`; related adapter/API/architecture suite `22 passed`; full pytest `137 passed`; py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.
- Review note: attempted to dispatch an independent `code-reviewer` agent multiple times, but the tool rejected both message-plus-items and items-only payload variants as duplicate inputs. Local review found no Critical or Important issues; the only `data_provider` hit is the intended lazy import string, and the only secret token hit is the redaction test fixture.
- Scope retained: no Dataset/Bronze/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.
- Checkpoint scope: stage only adapter code, adapter exports, tests, evidence docs, progress/status docs and this review; exclude `.worktrees`, `.cache`, `.venv`, pycache and unrelated files.

# P2 Status Sync After Provider Contract

> Started: 2026-07-21
> Scope: Refresh recovery docs after `SAL-P2-001` checkpoint `f7bc8ba8`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P2-002` implementation in this sync.

## Checklist

- [x] Confirm current git status and latest checkpoints.
- [x] Update `docs/development-status.md` with explicit `f7bc8ba8` delivery checkpoint and `SAL-P2-002` READY continuation.
- [x] Update `docs/development-progress-checklist.md` next-step anchor.
- [x] Record the repeated habit in `tasks/lessons.md`.
- [x] Re-scan state anchors and run `git diff --check`.

## Review: P2 Status Sync After Provider Contract

- Confirmed current Phase remains P2, Gate G2 remains not passed, G0/G1 remain passed, progress remains P0 `13/13`, P1 `16/16`, P2 `1/20`, total `30/129`.
- Confirmed completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, and `SAL-P2-001`; `SAL-P2-002` is READY and not started.
- Updated recovery wording so the latest functional delivery checkpoint is explicit: `f7bc8ba8 feat(P2): 定义 Provider 领域契约`.
- Preserved scope boundaries: no DSA Adapter, Dataset/PIT, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, or broad DSA source migration.

---

# P2 Provider Domain Contract Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P2-001` by defining a pure-domain, synchronous Provider contract with capabilities, immutable `DataBatch`/`Provenance`, stable failure categories, offline Contract Tests, and reuse of the P1 Problem Details boundary. Do not implement the DSA Adapter, make real Provider/LLM calls, start Dataset/PIT/Quant/formal backtest work, or migrate DSA runtime source.

## Checklist

- [x] Re-read the required recovery documents, confirm Git state, and run the 103-test baseline.
- [x] Inspect P1 domain/application conventions, Gate G1 constraints, ADR-002, and the approved Provider protocol design.
- [x] Write the detailed implementation plan at `docs/superpowers/plans/2026-07-20-provider-domain-contract.md`.
- [x] Add Red tests for Provider capabilities, immutable provenance/batches, freshness, SHA/time validation, six error classes, and Protocol conformance.
- [x] Implement `domain/providers.py` and stable domain exports with no framework/vendor imports.
- [x] Add Red/Green coverage for mapping `ProviderError` through the existing sanitized `ProviderProblem` contract.
- [x] Run target, related, and full verification plus compile/lock/diff/tag checks.
- [x] Add `docs/provider-domain-contract.md` acceptance evidence.
- [x] Update the progress checklist, development status, decision/risk/evidence registers, this review, and the next-session prompt.
- [x] Request specification and code-quality reviews; resolve all material findings.
- [x] Stage only `SAL-P2-001` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The domain contract must remain synchronous and stdlib-only except reuse of the pure-domain SHA-256 value validation; it must not import `application`, `integrations`, Pandas, Arrow, Provider SDKs, FastAPI, SQLAlchemy, or repositories.
- `RuntimeProfile` enforcement and `TraceContext` propagation belong to later application/integration callers; provenance carries only scalar correlation IDs and already-sanitized request metadata.
- Reuse `InstrumentId`, `ProviderProblem`, `ArtifactStore` boundaries, `Run/Stage/Event`, Alembic preflight, and Compatibility Facade semantics without implementing their later P2 consumers early.
- Keep `RSK-004` open and Gate G2 not passed. Do not mark `SAL-P2-002` or any Dataset/persistent task work complete.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## Review: SAL-P2-001

- Red evidence: `tests/domain/test_provider_contract.py` initially failed during collection with one `ModuleNotFoundError`; the API mapping test initially failed with `500 != 502` while its other 12 tests passed.
- Green implementation: added `src/serenity_alpha_lab/domain/providers.py` and public exports for Capability, ProviderCapabilities, ProviderWarning, Provenance, generic immutable DataBatch, six ProviderErrorCategory values, ProviderError retry policy, and synchronous runtime-checkable MarketDataProvider; added the existing Problem Details mapping and credential/path redaction coverage.
- Boundary review: Provider domain imports only stdlib plus existing pure-domain `ArtifactUri`, `InstrumentId`, and `Market`; architecture tests reject application/integration/vendor imports. Profile, TraceContext, ArtifactStore, Run/Stage/Event, Alembic, and Compatibility Facade remain explicit caller/follow-on boundaries.
- Review fixes: independent review found bytearray/custom-object immutability bypasses, non-finite retry delays, mutable scalar subclass acceptance, quoted Provider secret leakage, mutable contract-object references, and weak Provenance mapping schema. Local review added mutable mapping-key rejection. The implementation now uses an explicit immutable-value policy, freezes mapping keys and values, validates finite/non-negative retry delays, redacts quoted token/client-secret payloads, and enforces exact Provider value-object types.
- Verification: Provider contract `23 passed`; related `109 passed`; full pytest `128 passed`; py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and immutable `upstream/dsa-v3.26.1` tag check passed. Local Ruff is not claimed as a pass: downloaded Ruff was blocked by the existing `W503` selector config, and a temporary config probe exposed broader existing lint debt outside `SAL-P2-001`.
- Final independent review: earlier Critical/Important findings are closed; no remaining Critical, Important, or Minor issues were reported.
- Scope retained: no DSA Adapter, real Provider/LLM calls, Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, or broad DSA source migration. `RSK-004` and Gate G2 remain open/not passed.
- Checkpoint scope: stage only this task's code, tests, evidence, status/ledger files and this plan; exclude `.cache`, `.venv`, `.worktrees`, pycache and unrelated files.

---

# P2 Status Snapshot Sync Plan

> Started: 2026-07-20
> Scope: Respond to the user's status-sync request after Gate G1 by making the repository recovery state explicit, recording the repeated habit in lessons, and providing a copyable next-session prompt without starting `SAL-P2-001` yet.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, and `docs/development-progress-checklist.md`.
- [x] Confirm `git status --short --branch` and latest checkpoints show Gate G1 commit `428205b9`.
- [x] Add a new lesson that status synchronization must happen automatically at user-defined stop/prompt nodes.
- [x] Add a status-sync review line to `docs/development-status.md` confirming P2 / Gate G2 / `SAL-P2-001`.
- [x] Re-scan status anchors and run `git diff --check` before reporting completion.

## Review: P2 Status Snapshot Sync

- Confirmed docs already show Phase `P2 数据与持久任务`, Gate `G2 未通过`, G0/G1 passed, total progress `29/129`, and `SAL-P2-001` `READY`.
- Added a persistent lesson so future phase/task completions automatically update status, progress, todo review, evidence, and the next-start prompt before final response.
- This sync does not start `SAL-P2-001`, does not modify code, and does not touch DSA worktree/cache/runtime artifacts.

---

# P1 Gate G1 Engineering Foundation Review Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-016` as the P1 Gate checkpoint. Review all P1 engineering-hardening evidence, decide Gate G1 Go/No-Go, record accepted risks and P2 entry constraints, update project status, and create a Chinese checkpoint commit before notifying the user that the project has reached P2.

## Checklist

- [x] Confirm clean post-`SAL-P1-015` checkpoint state and current branch/log.
- [x] Review Gate G1 criteria, P1 task evidence, decisions, risks, and current status documents.
- [x] Run G1 verification: baseline tag/worktree, registered patch check, root/P1 test suites, dependency lock, Desktop compatibility runner, and whitespace diff.
- [x] Add `docs/gate-g1-engineering-foundation-review.md` with Gate conclusion, evidence matrix, accepted risks, verification, and P2 entry constraints.
- [x] Update `docs/development-progress-checklist.md` to mark `SAL-P1-016` done, set P1 `16/16`, total `29/129`, and promote `SAL-P2-001` to `READY`.
- [x] Update `docs/development-status.md` to move current Phase to P2 and refresh the next-start prompt.
- [x] Stage only relevant `SAL-P1-016` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-016` is a Gate review only: no new runtime feature, no DSA source migration, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM calls, and no cache/worktree/generated artifact commits.
- Gate G1 may approve entering P2, but P2 tasks must continue through explicit task IDs and retain CI/offline boundaries.
- Any accepted risk must be documented with a downstream closure path and must not be reframed as release-ready.

## Review: SAL-P1-016

- Added `docs/gate-g1-engineering-foundation-review.md`, concluding `GO with accepted risks` and documenting P1 `16/16`, total `29/129`, P2 entry approval, accepted release blockers, and `SAL-P2-001` as the next entry.
- Updated `docs/development-progress-checklist.md` with `DEC-027`, `AEV-029`, P1 `DONE`, P2 `DOING`, and `SAL-P2-001` `READY`.
- Updated `docs/development-status.md` so future sessions resume from P2 / Gate G2 with `SAL-P2-001`, not from G1.
- Verification completed: `bootstrap-dsa-baseline.sh --validate-only`, `apply-dsa-baseline-patches.sh --check-only`, root and P1 pytest `103 passed`, dependency lock check, Desktop compatibility runner, `git diff --check`, and baseline tag check all passed.

---

# P1 Desktop Compatibility Performance Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-015` as a P1 engineering-hardening checkpoint. Re-run the locked DSA Desktop/CLI/Bot and contract/golden characterization paths under the current P1 lock/facade/migration state, add a repeatable performance evidence script, and record startup/single-stock stub-analysis timings without changing DSA runtime behavior, moving upstream tags, starting real Provider/LLM calls, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P0 Desktop/CLI/Bot smoke evidence, P0 required baseline jobs, and P1 guardrails.
- [x] Add a repeatable `SAL-P1-015` compatibility/performance runner that keeps generated timing artifacts under `.cache/dsa-p0`.
- [x] Run Desktop npm tests, Desktop packaging/API health, CLI local backend, Bot command smoke, API/config, database, and report/signal baselines.
- [x] Capture startup/import and single-stock report-generation timing against conservative P1 thresholds.
- [x] Run Serenity root pytest/compile/lock/diff/tag verification.
- [x] Add `SAL-P1-015` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-015` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-015` is compatibility/performance evidence only: no DSA source migration, no Desktop package signing/build artifact commit, no Web lockfile rewrite, no Docker image rebuild unless explicitly needed for G1, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- P0 characterization is measured through deterministic/offline paths: Desktop headless tests, packaging/API health, CLI/Bot mocks, API/config snapshots, database fixture, and report/signal golden snapshots.
- Performance thresholds for this first P1 run are conservative baselines rather than optimization claims: Desktop/backend health startup budget `<= 60s`, report/signal golden run `<= 60s`, and single-stock Markdown generation `<= 5s`.

## Review: SAL-P1-015

- Added `scripts/run-p1-desktop-compatibility-performance.sh` as the repeatable compatibility/performance runner. It bootstraps the locked DSA baseline, applies registered patches, runs Desktop/API/CLI/Bot and contract/golden baselines, measures Desktop backend health startup, and writes generated logs/summary only under `.cache/dsa-p0/p1-desktop-compatibility-performance/`.
- Added `docs/desktop-compatibility-performance-baseline.md`, documenting the validation matrix, performance thresholds, no-real-call boundaries, generated artifact policy, and G1 handoff.
- Latest runner evidence passed: Desktop `npm test` `47 passed`, Desktop/API/CLI/Bot pytest `121 passed, 7 warnings`, API/config snapshots matched, database snapshots matched, report/signal snapshots matched, Desktop backend health startup `5,822ms`, single-stock report generation average `0.030ms`, and real Provider/LLM calls zero.
- Updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-015` done, record `DEC-026` / `AEV-028`, move P1 progress to `15/16`, total progress to `28/129`, and promote `SAL-P1-016` to `READY`.
- Final verification recorded before checkpoint commit: `bash -n scripts/run-p1-desktop-compatibility-performance.sh`, full `.cache/dsa-p0/venv/bin/python -m pytest -q`, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1`.

---

# P1 SQLite Upgrade Verification Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-013` as a P1 engineering-hardening checkpoint. Rehearse upgrading the committed sanitized DSA SQLite fixture to the Alembic baseline by backup, stamp, verify, and recovery; do not introduce new schema changes, migrate DSA runtime `storage.py`, start Provider/LLM calls, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P0 fixture SQL/content hashes and `SAL-P1-012` Alembic baseline behavior for existing DSA databases.
- [x] Add Red tests for fixture restore, Alembic stamp/verify, row-count/content-hash preservation, idempotent rerun, and failure recovery from backup.
- [x] Implement SQLite upgrade rehearsal helpers and report DTOs without importing DSA `storage.py` or calling `create_all`.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-013` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-013` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-013` is historical SQLite upgrade verification only: no new business schema, no DSA runtime source migration, no Repository read/write path switch, no Desktop performance run, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- Existing business tables must preserve row counts and content hashes; Alembic may add/update only its version tracking table.
- Any failure after backup must restore the original SQLite file before returning control.

## Review: SAL-P1-013

- Added Red tests in `tests/repositories/test_sqlite_upgrade.py`; initial target run failed on missing `serenity_alpha_lab.repositories.sqlite_upgrade` with `4 failed`.
- Added `src/serenity_alpha_lab/repositories/sqlite_upgrade.py`, defining `SQLiteInspection`, `SQLiteUpgradeReport`, fixture restore, business table inspection, Alembic stamp upgrade, idempotency behavior, validation, and backup restore on failure.
- Extended `storage_migrations.py` with `stamp_database()` so existing DSA SQLite databases can be marked at the Alembic baseline without rerunning DDL.
- Added `docs/sqlite-upgrade-verification.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-013` done, record `DEC-025` / `AEV-027`, move P1 progress to `14/16`, total progress to `27/129`, and promote `SAL-P1-015` to `READY`.
- Verification completed: target SQLite upgrade tests `4 passed`, repositories/architecture `26 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `103 passed`, py_compile for changed repository/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Alembic Migration Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-012` as a P1 engineering-hardening checkpoint. Introduce Alembic as the single schema migration entry for the Serenity root, add a DSA v3.26.1 SQLite baseline revision tied to the P0 database snapshot, and provide startup preflight helpers without rewriting DSA runtime `storage.py`, running Provider/LLM calls, starting PIT Dataset, Quant Core, formal backtesting, or large DSA source migration.

## Checklist

- [x] Review P0 database baseline, ADR-002 `StorageMigrationFacade` scope, and current Python dependency surface.
- [x] Add Red tests for baseline revision metadata, empty SQLite upgrade, startup preflight, and no DSA `storage.py` / `create_all` dependency in migration code.
- [x] Add Alembic to the explicit root core install surface and refresh lock/export if needed.
- [x] Create Alembic config/env/script template, DSA v3.26.1 baseline revision, and committed schema SQL baseline under `migrations/`.
- [x] Implement storage migration facade helpers for upgrade, status, and startup head assertion.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-012` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-012` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-012` is migration foundation only: no DSA source movement, no DSA API route rewrite, no Repository behavior migration, no `SAL-P1-013` historical upgrade rehearsal, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- Alembic must be the only new schema creation entry; startup helpers should check revision state rather than silently calling `Base.metadata.create_all()` or DSA `DatabaseManager`.
- Baseline revision must explicitly reference DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` and P0 schema version `2026-06-05-create-all-baseline`.

## Review: SAL-P1-012

- Added Red tests in `tests/repositories/test_storage_migrations.py`; initial target run failed on missing `serenity_alpha_lab.repositories.storage_migrations`, `migrations/env.py`, and baseline revision with `4 failed`.
- Added root Alembic files: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/baselines/dsa_v3_26_1_schema.sql`, and `migrations/versions/20260720_dsa_v3261_baseline.py`.
- Added `src/serenity_alpha_lab/repositories/storage_migrations.py`, defining `MigrationStatus`, `StorageMigrationRequired`, `upgrade_database()`, `current_migration_status()`, `assert_database_at_head()`, and baseline SQL verification helpers.
- Added explicit `alembic>=1.13.0` to root `core` extra and regenerated `uv.lock` / `requirements.txt` through the existing drift guard export path.
- Added `docs/storage-migration-alembic.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-012` done, record `DEC-024` / `AEV-026`, move P1 progress to `13/16`, total progress to `26/129`, and promote `SAL-P1-013` to `READY`.
- Verification completed: target storage migration tests `4 passed`, repositories/architecture `22 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `99 passed`, py_compile for changed repository/migration/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 API Error Protocol Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-010` as a P1 engineering-hardening checkpoint. Define a stable `application/problem+json` error protocol, sanitized problem details, error code mapping, and framework-neutral ASGI middleware without changing existing DSA API routes, OpenAPI snapshots, Provider/LLM behavior, Alembic, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P1 error requirements, existing TaskBackend/Config/Research errors, Trace context, and ADR-002 API boundary rules.
- [x] Add Red tests for RFC 7807-style serialization, stable error codes, trace_id propagation, validation/not-found/conflict/provider/internal mapping, and secret/path redaction.
- [x] Add Red ASGI middleware tests for `application/problem+json` responses without FastAPI imports.
- [x] Implement application-layer API error DTOs, error classes, exception mapper, redactor, response helpers, and middleware.
- [x] Export public API error symbols from `serenity_alpha_lab.application`.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-010` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-010` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-010` is protocol/middleware foundation only: no DSA API route rewrite, no OpenAPI baseline refresh, no Web client change, no Provider/LLM calls, no Alembic migration, no PIT Dataset, no Quant Core, and no formal backtest.
- Problem details must not expose Python stack traces, absolute file paths, API keys, tokens, prompts, request bodies, or private content.
- Keep middleware framework-neutral and avoid FastAPI/Starlette imports.

## Review: SAL-P1-010

- Added Red tests in `tests/application/test_api_errors.py` and an architecture boundary check in `tests/architecture/test_architecture_boundaries.py`; initial target run failed on missing `serenity_alpha_lab.application.api_errors` with `5 failed`.
- Added `src/serenity_alpha_lab/application/api_errors.py`, defining `ApiErrorCode`, `ProblemDetail`, `ApiProblemError` subclasses, `problem_from_exception()`, `problem_response_body()`, `redact_problem_detail()`, and framework-neutral `ProblemDetailsMiddleware`.
- Mapped existing app errors explicitly: `TaskNotFound` -> `not_found`, `TaskAlreadyExists` -> `conflict`, `ConfigProfileError` / `ValueError` -> `validation_error`, request-validation `ResearchOrchestratorError` -> `validation_error`, DSA/facade `ResearchOrchestratorError` -> `provider_error`, `TaskBackendCapabilityError` / unknown exceptions -> `internal_error`.
- Added `docs/api-error-protocol.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-010` done, record `DEC-023` / `AEV-025`, move P1 progress to `12/16`, and total progress to `25/129`.
- Verification completed: target API error tests `5 passed`, application/architecture `41 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `95 passed`, py_compile for changed application/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 ResearchOrchestrator Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-009` as a P1 engineering-hardening checkpoint. Define a stable application-layer ResearchOrchestrator protocol and an injected DSA compatibility facade for `AgentOrchestrator.run/chat` without copying DSA runtime source, changing API routes, starting Provider/LLM calls, adding persistence, or replacing report generation.

## Checklist

- [x] Review DSA `AgentOrchestrator`/`AgentResult` signatures, existing Agent API call sites, ADR-002 facade scope, and P1 guardrails.
- [x] Add Red application contract tests for Research request/result DTOs, protocol shape, validation, and immutable context handling.
- [x] Add Red integration facade tests for mapping DSA-like `run()` and `chat()` results through an injected orchestrator object.
- [x] Add architecture tests proving the application contract and DSA facade do not import concrete DSA `src.agent` modules.
- [x] Implement application-layer ResearchOrchestrator DTOs, Protocol, progress callback type, errors, and result mapping contract.
- [x] Implement DSA `AgentOrchestrator` compatibility facade using constructor injection and shallow context normalization.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-009` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-009` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-009` is facade/protocol foundation only: no API route migration, no Deep Research rewrite, no Agent checkpoint persistence, no Evidence Agent, no Provider/LLM calls, no Quant Core, no PIT Dataset, and no formal backtest.
- DSA compatibility code must receive an orchestrator-like object by injection; no top-level `src.agent.orchestrator` or broad DSA runtime import.
- Existing DSA result semantics must remain intact: `success/content/dashboard/tool_calls_log/total_steps/total_tokens/provider/model/error` are mapped without reinterpretation.

## Review: SAL-P1-009

- Added Red tests in `tests/application/test_research_orchestrator_contract.py` and `tests/integrations/test_dsa_research_orchestrator_facade.py`; initial target run failed on missing `serenity_alpha_lab.application.research_orchestrator`, then Green passed with target `16 passed`.
- Added architecture coverage in `tests/architecture/test_architecture_boundaries.py` to reject concrete DSA Agent runtime imports from the application contract and DSA facade.
- Added `src/serenity_alpha_lab/application/research_orchestrator.py`, defining `ResearchRequest`, `ResearchChatRequest`, `ResearchResult`, `ResearchOrchestrator`, `ResearchMode`, `ProgressCallback`, and `ResearchOrchestratorError`.
- Added `src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py`, defining `DsaResearchOrchestratorFacade` around an injected DSA-like orchestrator; it maps `run()` / `chat()` results without reinterpreting legacy `AgentResult` fields and normalizes explicit chat skills into `skills` / `strategies`.
- Added `docs/research-orchestrator-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-009` done, record `DEC-022` / `AEV-024`, move P1 progress to `11/16`, and total progress to `24/129`.
- Verification completed: target ResearchOrchestrator tests `16 passed`, application/integrations/architecture `43 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `90 passed`, py_compile for changed application/integration/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Config Profile Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-014` as a P1 engineering-hardening checkpoint. Define desktop/standalone/ci runtime profiles, secret boundaries, redacted diagnostics, and config source tracking without rewriting deployment `.env`, starting Provider/LLM calls, changing DSA runtime config endpoints, or adding deployment automation.

## Checklist

- [x] Review P1 profile requirements, DSA config baseline, dependency surface, and ADR-002 facade boundary.
- [x] Add Red tests for runtime profile policies, CI key/network rejection, redacted diagnostics, source tracking, and no `.env` rewrite from service profile preview.
- [x] Add direct `pydantic-settings` dependency to the root core install surface and refresh lock/export if needed.
- [x] Implement application-layer `ConfigProfileFacade`, Pydantic settings model, profile policy, diagnostics, and update preview.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-014` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-014` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-014` is configuration/profile foundation only: no DSA `.env` rewrite integration, no Web/API route changes, no deployment profile rewrite, no Provider/LLM calls, no Alembic, no PIT Dataset, no Quant Core, and no formal backtest.
- CI profile must default to offline/stub behavior and reject real model/provider secrets.
- Diagnostics must not expose complete API keys, provider tokens, prompts, body content, credentials, or deployment secret values.

## Review: SAL-P1-014

- Added Red tests in `tests/application/test_config_profiles.py`; initial target run failed on missing `serenity_alpha_lab.application.config_profiles`, then Green passed with target `9 passed`.
- Added `src/serenity_alpha_lab/application/config_profiles.py`, defining `RuntimeSettings`, `RuntimeProfile`, `ProfilePolicy`, `ConfigValueSource`, `ConfigProfileError`, source-tracked loading, redacted diagnostics, CI boundary enforcement, and side-effect-free update preview.
- Added direct root `core` dependency `pydantic-settings>=2.0.0`; refreshed minimal `uv.lock` project metadata and regenerated `requirements.txt` through the existing lock/export guard.
- Added `docs/config-profile-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-014` done, record `DEC-021` / `AEV-023`, move P1 progress to `10/16`, total progress to `23/129`, and promote `SAL-P1-012` to `READY`.
- Verification completed: target Config Profile tests `9 passed`, application/architecture `29 passed`, P1 related application/architecture/domain/repositories/integrations `79 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `79 passed`, py_compile for changed application/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Trace and Structured Logging Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-011` as a P1 engineering-hardening checkpoint. Define trace context propagation, structured JSON log schema, redaction, and lightweight ASGI middleware without adding OpenTelemetry exporters, metrics backend, Provider/Qlib/LLM instrumentation, or API endpoint rewrites.

## Checklist

- [x] Review observability requirements, Run/Stage model, TaskBackend context, and logging redaction constraints.
- [x] Add Red tests for trace context propagation and reset behavior.
- [x] Add Red tests for structured JSON logging with trace/run/stage/user/module fields and secret/prompt redaction.
- [x] Add Red tests for ASGI-compatible trace middleware header propagation.
- [x] Implement stdlib-only trace context, redactor, logging filter, JSON formatter, and ASGI middleware.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-011` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-011` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-011` is observability foundation only: no OpenTelemetry exporter, Prometheus/Grafana, Provider/Qlib/LLM instrumentation, Agent orchestration changes, API route rewrites, PIT Dataset, Quant Core, or formal backtest.
- Do not log secrets, tokens, full prompts, private body text, or request payloads by default.
- Middleware must be framework-neutral and avoid FastAPI/Starlette imports.

## Review: SAL-P1-011

- Added Red tests in `tests/application/test_trace_context.py`; initial target run failed on missing `serenity_alpha_lab.application.tracing`, then Green passed with target `4 passed`.
- Added `src/serenity_alpha_lab/application/tracing.py`, defining `TraceContext`, `use_trace_context()`, `current_trace_context()`, `TraceContextFilter`, `StructuredLogFormatter`, `TraceContextMiddleware`, `generate_trace_id()` and `redact_sensitive_data()`.
- Structured JSON logs include timestamp, level, logger, module, message, trace_id, run_id, stage_id and user_id; `extra` fields are recursively redacted for secrets, tokens, authorization, api keys, prompts, messages, bodies and content.
- Added `docs/structured-trace-logging.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-011` done, record `DEC-020` / `AEV-022`, move P1 progress to `9/16`, and total progress to `22/129`.
- Verification completed: target Trace tests `4 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `70 passed`, py_compile for application/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 TaskBackend Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-008` as a P1 engineering-hardening checkpoint. Define a stable TaskBackend protocol, in-memory implementation, and DSA compatibility facade without moving upstream, importing broad DSA runtime source, starting persistent task queues, or introducing Celery/Redis/PostgreSQL behavior.

## Checklist

- [x] Review current P1 state, ADR-002 facade scope, DSA `AnalysisTaskQueue` signatures, and thread-pool boundary risk.
- [x] Add Red contract tests for `TaskBackend.submit/get/request_cancel/subscribe`.
- [x] Add Red compatibility facade tests for wrapping an injected DSA-like queue without importing DSA runtime.
- [x] Add architecture test ensuring Serenity application/DSA facade modules do not import `ThreadPoolExecutor` directly.
- [x] Implement application-layer TaskBackend DTOs, Protocol, errors, and InMemory implementation.
- [x] Implement DSA `AnalysisTaskQueue` compatibility facade using handler registry and injected queue object.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-008` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-008` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-008` may define a facade around DSA queue shape but must not copy/migrate DSA runtime source into Serenity.
- No `ThreadPoolExecutor`, Celery, Redis, PostgreSQL persistence, Worker runtime, PIT Dataset, Quant Core, formal backtest, or API endpoint implementation in this task.
- DSA compatibility code must receive queue/handlers by injection; no top-level `src.services.task_queue` import.

## Review: SAL-P1-008

- Added Red tests in `tests/application/test_task_backend_contract.py` and `tests/integrations/test_dsa_task_backend_facade.py`; initial target run failed on missing `serenity_alpha_lab.application.task_backend`, then Green passed with target `12 passed`.
- Added architecture coverage in `tests/architecture/test_architecture_boundaries.py` to reject direct `ThreadPoolExecutor` imports from `application` and `integrations/dsa` modules.
- Added `src/serenity_alpha_lab/application/task_backend.py`, defining `TaskBackend`, `TaskCommand`, `TaskRef`, `TaskSnapshot`, `TaskEvent`, status/error types, `InMemoryTaskBackend`, and DSA legacy status mapping without importing DSA runtime or thread pools.
- Added `src/serenity_alpha_lab/integrations/dsa/task_backend.py`, defining `DsaAnalysisTaskQueueBackend` around an injected queue and handler registry; it maps `submit_background_task()`, `get_task()`, optional cancel methods, and flow events into the stable TaskBackend contract.
- Added `docs/task-backend-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-008` done, record `DEC-019` / `AEV-021`, move P1 progress to `8/16`, and total progress to `21/129`.
- Verification completed: target TaskBackend tests `12 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `66 passed`, py_compile for application/integration/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Artifact Store Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-007` as a P1 engineering-hardening checkpoint. Define pure artifact domain contracts and a local content-addressed store without starting Evidence Agent, Dataset Catalog, PIT Dataset, Quant Core, formal backtesting, database migration, or broad DSA source movement.

## Checklist

- [x] Review current P1 state, ADR-001/002 guardrails, existing Run domain model, and architecture boundaries.
- [x] Add Red tests for Artifact URI/Manifest metadata and local store atomic publish behavior.
- [x] Run target Red tests and confirm they fail for missing Artifact modules.
- [x] Implement pure domain Artifact model and `ArtifactStore` Protocol.
- [x] Implement local filesystem ArtifactStore with content-addressed blobs, JSON manifests, temp-file cleanup, and hash verification.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-007` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-007` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-007` is Artifact domain/storage only: no Provider migration, Dataset Catalog, PIT data, Quant Core, formal backtest, database migration, Evidence Agent, API endpoint, or large DSA runtime source migration.
- Domain code must stay pure and must not import framework, repository, service, vendor, or DSA runtime modules.
- Local storage must publish manifests last; failed writes must not create queryable published records and must clean temporary files.

## Review: SAL-P1-007

- Added Red tests in `tests/domain/test_artifacts.py` and `tests/repositories/test_local_artifact_store.py`; initial target run failed on missing `serenity_alpha_lab.domain.artifacts`, then Green passed with `6 passed`.
- Added `src/serenity_alpha_lab/domain/artifacts.py`, defining pure domain `ArtifactUri`, `ArtifactManifest`, `ArtifactRetentionTier`, `ArtifactStore`, and artifact error types without importing repositories, frameworks, providers, or DSA runtime code.
- Added `src/serenity_alpha_lab/repositories/local_artifact_store.py`, implementing local SHA-256 blob storage, JSON manifests, idempotent record reuse, manifest-last atomic publish, temp cleanup, and hash/size validation on reads.
- Added `docs/artifact-store-domain-model.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-007` done, record `DEC-018` / `AEV-020`, move P1 progress to `7/16`, and total progress to `20/129`.
- Verification completed: target Artifact tests `6 passed`, related architecture/domain/repositories tests `58 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `58 passed`, py_compile for domain/repository/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed; checkpoint commit `5525f6da feat(P1): 实现 Artifact 模型与本地存储` created.

---

# P1 InstrumentId Domain Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-005` as a P1 engineering-hardening checkpoint. Define a pure domain `InstrumentId` value object, market/exchange/asset-type vocabulary, and provider/legacy symbol mapping without starting Provider migration, PIT Dataset, Quant Core, formal backtesting, or broad DSA source movement.

## Checklist

- [x] Review recovery docs, lessons, status, progress checklist, development plan, Gate G0 review, ADR-001/002, Git status, recent commits, and DSA symbol normalization references.
- [x] Write Red tests for A/HK/US/JP/KR/TW `InstrumentId` parsing, formatting, provider symbol mapping, and ambiguous bare-code rejection.
- [x] Implement pure domain `InstrumentId`, `Market`, `Exchange`, `AssetType`, errors, and provider/legacy mapping helpers.
- [x] Export public domain symbols and keep architecture boundaries clean.
- [x] Add `SAL-P1-005` evidence documentation.
- [x] Run targeted domain tests, architecture tests, full pytest, py_compile, dependency lock drift guard, upstream tag check, and `git diff --check`.
- [x] Update progress checklist, status snapshot, decision/evidence registers, and this review section.
- [x] Stage only relevant files and create a Chinese checkpoint commit after verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products.
- `SAL-P1-005` is pure domain/compatibility modeling only: no Provider implementation, Dataset Catalog, PIT data, Quant Core, formal backtest, database migration, or large DSA runtime source migration.
- Bare six-digit codes must remain ambiguous unless explicit market context is supplied.

## Review: SAL-P1-005

- Added `tests/domain/test_instrument_id.py` as the Red/Green contract for canonical A/HK/US/JP/KR/TW round-trips, legacy DSA/Yahoo symbol intake, provider symbol mapping, DSA compatibility symbols, and ambiguous bare-code rejection. Initial Red failed on missing `serenity_alpha_lab.domain.instruments`.
- Added `src/serenity_alpha_lab/domain/instruments.py`, defining pure domain `InstrumentId`, `Market`, `Exchange`, `AssetType`, `ProviderSymbolMapping`, `AmbiguousInstrumentSymbol`, `InvalidInstrumentSymbol`, and `UnsupportedProvider` without importing DSA runtime, data providers, frameworks, or persistence.
- Exported InstrumentId symbols from `src/serenity_alpha_lab/domain/__init__.py`; architecture tests continue to enforce domain/framework and infrastructure boundaries.
- Added `docs/instrument-id-domain-model.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-005` done, record `DEC-017` / `AEV-019`, move P1 progress to `6/16`, and total progress to `19/129`.
- Verification completed: target Red/Green test, `.cache/dsa-p0/venv/bin/python -m pytest tests/domain/test_instrument_id.py -q` (`37 passed`), `.cache/dsa-p0/venv/bin/python -m pytest tests/architecture tests/domain -q` (`52 passed`), full `.cache/dsa-p0/venv/bin/python -m pytest -q` (`52 passed`), py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.
- Local review found no blocking correctness issue; scope remains pure domain modeling only, with Provider migration, Dataset master data, PIT semantics, Quant Core, and formal backtesting deferred to their explicit tasks.

---

# P1 Dependency Lock and Run Domain Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-003` and `SAL-P1-006` as separate but adjacent P1 engineering-hardening checkpoints. Preserve ADR-001/002 guardrails: do not move `upstream/dsa-v3.26.1`, do not import broad DSA runtime source, and do not start Quant Core, PIT Dataset, formal backtesting, or unapproved DSA migration.

## Checklist

- [x] Review recovery docs, lessons, status, progress checklist, development plan, Gate G0 review, ADR-001/002, Git status, and recent commits.
- [x] Write Red tests for dependency extras, lock/requirements drift guard, and absence of production dynamic Git dependencies.
- [x] Split Python dependencies into `core`, `providers`, `desktop`, `quant`, and `dev` install surfaces; generate `uv.lock` and exported requirements files.
- [x] Run dependency Red/Green validation, `uv lock --check`, requirements drift guard, architecture tests, and metadata checks.
- [x] Write Red tests for Run/Stage/Event state transitions, retry attempts, monotonic append-only event IDs, and idempotency keys.
- [x] Implement pure domain Run/Stage/Event model without framework, data provider, DSA, Quant Core, PIT Dataset, or backtest behavior.
- [x] Run domain tests, architecture boundary tests, py_compile, and `git diff --check`.
- [x] Update progress checklist, status snapshot, risk/decision/evidence registers, and this review section.
- [x] Stage only relevant files and create Chinese checkpoint commit(s) after verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products beyond approved dependency lock/requirements outputs.
- `SAL-P1-003` may create lock and exported requirements, but must not perform broad dependency upgrades unrelated to reproducing the P1 dependency graph.
- `SAL-P1-006` is pure domain state modeling only: no ArtifactStore, TaskBackend, persistence, Trace middleware, Quant Core, PIT Dataset, or formal backtest implementation.

## Review: SAL-P1-003 / SAL-P1-006

- Added `tests/architecture/test_dependency_locking.py` as the Red/Green contract for extras, lock presence, generated requirements, drift guard, and dynamic Git exclusion; initial Red failed on old default dependencies, AlphaSift Git dependency, missing `uv.lock`, missing `requirements.txt`, and missing guard script.
- Split root Python install surfaces in `pyproject.toml` into `core`, `providers`, `desktop`, `quant`, and `dev`; generated `uv.lock` and lock-derived `requirements.txt` for `core+providers+desktop` only.
- Added `scripts/verify-python-dependency-lock.sh`, which runs `uv lock --check`, re-exports the production requirements surface with a stable header, and diffs against committed `requirements.txt`.
- Removed Serenity root production dependency on dynamic AlphaSift Git install; DSA isolated worktree is unchanged, and reviewed AlphaSift wheel/package intake remains deferred to the later AlphaSift adapter task.
- Added `tests/domain/test_run_lifecycle.py` as the Red/Green contract for append-only monotonic events, terminal rollback rejection, retry new attempts, and idempotency conflict handling; initial Red failed on the missing `run_lifecycle` module.
- Added `src/serenity_alpha_lab/domain/run_lifecycle.py` and exported domain symbols from `domain/__init__.py`; no persistence, ArtifactStore, TaskBackend, Trace middleware, Quant Core, PIT Dataset, or formal backtest behavior was introduced.
- Added `docs/python-dependency-lock.md` and `docs/run-stage-event-domain-model.md`; updated `docs/python-project-metadata.md`, `docs/development-progress-checklist.md`, and `docs/development-status.md` to reflect then-current `SAL-P1-003`/`SAL-P1-006` completion, P1 progress, total progress, and `RSK-008` closure.
- Verification completed: `scripts/verify-python-dependency-lock.sh`, `pytest tests/architecture tests/domain -q`, full `pytest -q`, `py_compile`, editable install `pip install -e . --no-deps`, DSA dry-run entrypoint smoke, and `git diff --check` passed.

---

# P1 Python Metadata and Architecture Skeleton Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-002` and `SAL-P1-004` as one small engineering-hardening checkpoint. Preserve ADR-001/002 guardrails: do not move `upstream/dsa-v3.26.1`, do not copy broad DSA runtime source into the working tree, and do not start Quant Core, PIT Dataset, formal backtesting, or unapproved DSA migration.

## Checklist

- [x] Review session recovery docs, ADR-001/002, P1 task definitions, current Git state, and existing tracked project files.
- [x] Write Red tests for root `pyproject.toml`, installable entry points, package importability, and ADR-002 architecture boundaries.
- [x] Run targeted Red tests and record the expected failures.
- [x] Add root `pyproject.toml` with standard PEP 621 project metadata, Python version, build backend, DSA-derived dependencies, console entry points, and tool configuration.
- [x] Create minimal `src/serenity_alpha_lab` package skeleton for `domain`, `application`, `quant`, `datasets`, `evidence`, `integrations`, `repositories`, and `services` without implementing Quant Core or PIT Dataset behavior.
- [x] Add DSA compatibility entry-point wrappers that resolve the isolated DSA worktree and support dry-run validation without copying DSA runtime source.
- [x] Add dependency-difference review notes documenting what moved from DSA requirements/tool config and what remains deferred to `SAL-P1-003`.
- [x] Run targeted Green tests, editable install smoke with `--no-deps`, architecture checks, metadata parse checks, and `git diff --check`.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section with evidence and next-step state.
- [x] Stage only relevant P1 files and create a Chinese checkpoint commit if verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products.
- Keep `SAL-P1-003` scope separate: no `uv.lock`, no finalized extras split, no dependency upgrade/remediation beyond pyproject metadata normalization.
- Keep `SAL-P1-004` as skeleton and architecture tests only: no factor math, dataset catalog, formal backtest, Qlib integration, or provider migration.

## Review: SAL-P1-002 / SAL-P1-004

- Added root `pyproject.toml` with PEP 621 metadata, Python `>=3.11,<3.13`, `setuptools.build_meta`, DSA-derived runtime dependencies, DSA dry-run console scripts, and pytest/format/lint tool configuration.
- Added `docs/python-project-metadata.md` to document the migration from DSA `requirements.txt`, `pyproject.toml`, and `setup.cfg`, plus explicit `SAL-P1-003` deferrals for extras, lock generation, and AlphaSift dynamic Git closure.
- Added `src/serenity_alpha_lab/` package skeleton for `domain`, `application`, `quant`, `datasets`, `evidence`, `integrations`, `repositories`, and `services`; no Quant Core, PIT Dataset, formal backtest, provider migration, or broad DSA runtime source import was introduced.
- Added DSA compatibility wrappers under `src/serenity_alpha_lab/integrations/dsa/entrypoints.py`, resolving `.worktrees/dsa-v3.26.1` and supporting `SERENITY_DSA_DRY_RUN=1` for CLI/API/Worker/test entry-point validation.
- Added Red/Green architecture tests under `tests/architecture/`: initial Red failed on missing `pyproject.toml`, package skeleton, and entrypoint modules; final Green passed with `7 passed`.
- Verification completed: `pytest tests/architecture -q`, full `pytest -q`, editable install `pip install -e . --no-deps`, installed console-script dry-runs, `py_compile`, metadata parse, forbidden-token scan, and `git diff --check` passed. `ruff` was not run because it is not installed in `.cache/dsa-p0/venv`.
- Updated `docs/development-progress-checklist.md` and `docs/development-status.md`: `SAL-P1-002` and `SAL-P1-004` are `DONE`, P1 progress is 3/16, total progress is 16/129, and recommended next tasks are `SAL-P1-003` and `SAL-P1-006`.

---

# P1 ADR Approval Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-001` only. Approve upstream takeover/sync policy and progressive modularization decisions before any Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration.

## Checklist

- [x] Review `AGENTS.md`, `tasks/lessons.md`, development status, progress checklist, development plan, Gate G0 review, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P1 engineering hardening preparation; Gate G0 passed; `SAL-P1-001` is `READY`.
- [x] Write ADR-001 for upstream takeover, immutable tag policy, sync branches, patch classification, candidate commit triage, rollback, and review cadence.
- [x] Write ADR-002 for progressive modularization, Compatibility Facade, module boundaries, service-split conditions, old-path deletion criteria, rollback, and review cadence.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P1-001`, including DONE status, actual effort, decision/evidence entries, risk updates, and next `READY` tasks.
- [x] Update `docs/development-status.md` for current Phase/Gate, completed/unfinished work, next executable tasks, latest checkpoint placeholder, and next-start prompt.
- [x] Add `SAL-P1-001` review notes here after verification.
- [x] Run lightweight ADR verification: required ADR sections, stale status scan, forbidden source migration check, link/path checks, `git diff --check`, and Git status review.
- [x] Stage only relevant `SAL-P1-001` files and create a Chinese checkpoint commit.

## Guardrails

- Do not move, delete, or reuse `upstream/dsa-v3.26.1`.
- Do not copy or merge DSA runtime source into the main working tree in this task.
- Do not start Quant Core, PIT Dataset, formal backtesting, Qlib integration, or large DSA source migration before these ADRs are approved.
- Do not submit `.worktrees`, `.cache`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked directories.
- Keep accepted G0 risks visible; ADR approval does not make release security risks acceptable.

## Review: SAL-P1-001

- Added `docs/adr/ADR-001-upstream-takeover-sync-and-patch-policy.md`, approving the immutable DSA `v3.26.1` baseline, controlled `sync/dsa-*` branches, patch classification, sync rollback, and candidate commit triage.
- Added `docs/adr/ADR-002-progressive-modularization-and-compatibility-facade.md`, approving progressive modularization, explicit Compatibility Facade boundaries, service-split conditions, old-path deletion criteria, rollback, and Gate G1/2026-08-03 review timing.
- Updated `docs/development-progress-checklist.md`: `SAL-P1-001` is `DONE`, P1 progress is 1/16, total progress is 14/129, `SAL-P1-002` and `SAL-P1-004` are `READY`, `RSK-006` is closed by ADR triage, and `DEC-012` / `DEC-013` / `AEV-014` record decisions and evidence.
- Updated `docs/development-status.md`: current Gate is G1 not passed, latest completed task is `SAL-P1-001`, next executable tasks are `SAL-P1-002` and `SAL-P1-004`, and the next-start prompt reflects the new recovery point.
- Verification completed for `SAL-P1-001`: ADR required sections, immutable tag check, active status anchors, no runtime/cache path changes, and `git diff --check` all passed.

---

# P0 Remaining Gate Baseline Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Complete `SAL-P0-010` first, then `SAL-P0-012`, then run `SAL-P0-013` Gate G0 review. Do not start P1, Quant Core, or broad DSA source migration before G0 passes.

## Checklist

- [x] Review `AGENTS.md`, project lessons, development status, progress checklist, development plan, upstream baseline selection, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P0, Gate G0 not passed; `SAL-P0-010` and `SAL-P0-012` are `READY`; `SAL-P0-013` remains gated by P0 completion.
- [x] Dispatch read-only subagents for report/signal baseline discovery, existing baseline-script pattern discovery, and upstream/CI discovery.
- [x] Run the Red check for `SAL-P0-010`: `scripts/run-dsa-report-signal-baseline.sh` is missing, so report/signal goldens are not yet reproducible.
- [x] Inspect DSA report rendering, report schema, notification report fixtures, DecisionSignal summary, and Backtest/Signal Evaluation metric paths in `.worktrees/dsa-v3.26.1`.
- [x] Add `scripts/run-dsa-report-signal-baseline.sh` using the established baseline pattern: validate tag/worktree, apply registered patches, validate worktree diff, run offline/stub generation, compare committed snapshots, and support `--update-snapshots`.
- [x] Commit stable `SAL-P0-010` snapshots under `docs/baselines/dsa-v3.26.1/report-signal/`, including structured report input/output, Markdown single-stock/aggregate/market-review goldens, signal evaluation input/output, content hashes, and `summary.json`.
- [x] Write `docs/report-signal-golden-baseline.md` with commands, fixture coverage, hashes, limitations, and non-goals.
- [x] Verify `SAL-P0-010`: baseline script update and compare runs, relevant upstream report/backtest tests, `bash -n`, `git diff --check`, committed-fixture guards, and summary assertions.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P0-010`, P0 progress from 10/13 to 11/13, evidence registry, decisions, risks, and dependencies.
- [x] Update `docs/development-status.md` after `SAL-P0-010` with completed/unfinished tasks, next actions, latest checkpoint placeholders, and a fresh next-start prompt.
- [x] Add this task's review section to `tasks/todo.md`.
- [x] Stage only relevant `SAL-P0-010` files and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-012`: create upstream maintenance documentation and CI required checks after the report/signal baseline exists.
- [x] Verify `SAL-P0-012`, update status/checklist/evidence, and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-013` only after all P0 tasks are `DONE`; run Gate G0 review, record Go/No-Go, update status/checklist, and create a Chinese checkpoint commit.

## Guardrails

- Gate G0 is now passed by `SAL-P0-013`; keep the accepted risks visible and do not treat them as release approval.
- `SAL-P0-010` must use offline fixture/stub inputs only; no real Provider, real LLM, scheduler, webhook, or notification send.
- `SAL-P0-012` must include the actual P0 baseline scripts/artifacts and patch registry, not aspirational CI checks.
- `SAL-P1-001` is now complete; follow ADR-001/002 before starting dependent P1 code, and do not start Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration outside the approved task sequence.
- The DSA source remains isolated in `.worktrees/dsa-v3.26.1`; do not copy upstream runtime source into the project tree.
- Do not submit `.cache`, `.worktrees`, runtime SQLite binaries, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## SAL-P0-012 Plan

- [x] Create root `UPSTREAM_BASE.md` covering upstream baseline, remote/tag policy, local worktree/cache layout, patch classification, baseline artifacts, sync procedure, and required check names.
- [x] Update `docs/upstream-patches.md` so each local deviation is explicitly classified as `compatible`, `extension`, or `divergence`.
- [x] Add `.github/workflows/p0-required-baselines.yml` with PR/workflow_dispatch required jobs for backend offline, Web build/test/smoke, contract/golden snapshots, Docker smoke, and supply-chain baseline.
- [x] Validate workflow YAML and referenced script paths without running heavyweight CI jobs locally.
- [x] Update `docs/development-progress-checklist.md` and `docs/development-status.md` for `SAL-P0-012`, moving P0 progress to 12/13 while keeping Gate G0 blocked until `SAL-P0-013`.
- [x] Add `SAL-P0-012` review notes here and create a Chinese checkpoint commit.

## SAL-P0-013 Plan

- [x] Confirm `SAL-P0-001` through `SAL-P0-012` are `DONE` and that no P0 evidence gaps remain.
- [x] Write `docs/gate-g0-baseline-review.md` with Gate G0 Go/No-Go decision, evidence matrix, accepted risks, and P1 entry constraints.
- [x] Update `docs/development-progress-checklist.md`: mark `SAL-P0-013` `DONE`, move P0 and total progress to `13/13` and `13/129`, and add `DEC-011` / `AEV-013`.
- [x] Update `docs/development-status.md` for Gate G0 passed, next executable task `SAL-P1-001`, accepted risks, and fresh resume prompt.
- [x] Run lightweight Gate G0 verification, update this review section, stage only G0 files, and create a Chinese checkpoint commit.

## Review: SAL-P0-013

- Created `docs/gate-g0-baseline-review.md` with the Gate G0 decision `GO with accepted risks`, evidence matrix, accepted risk register, and P1 entry constraints.
- Updated `docs/development-progress-checklist.md`: P0 is `DONE` at 13/13, total progress is 13/129, `SAL-P0-013` is `DONE`, `SAL-P1-001` is `READY`, and `DEC-011` / `AEV-013` record the Gate decision and evidence.
- Updated `docs/development-status.md`: current phase moves to P1 engineering hardening preparation, Gate G0 is passed, next task is `SAL-P1-001`, and the next-start prompt reflects the new recovery state.
- Accepted but did not fix G0 risks `RSK-006`, `RSK-008`, `RSK-010`, `RSK-011`, and `RSK-012`; these remain assigned to P1/P6 closure paths and do not permit release until closed or formally waived.
- Verification scope for `SAL-P0-013`: locked baseline validation, patch registry check, workflow YAML parse, API/config/database/report-signal summary assertions, stale-status scan, and `git diff --check`.

## Review: SAL-P0-012

- Added `UPSTREAM_BASE.md`, documenting the immutable DSA `v3.26.1` baseline, origin/upstream remotes, isolated worktree/cache layout, sync procedure, local deviation taxonomy, baseline scripts, and required check names.
- Updated `docs/upstream-patches.md` so `DSA-PATCH-001` through `DSA-PATCH-003` are explicitly classified as `compatible`; current P0 has no `divergence`.
- Added `.github/workflows/p0-required-baselines.yml` with four PR/workflow_dispatch check jobs: backend offline, Web baseline, contract/golden snapshots, and Docker/supply-chain baseline.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-012` is `DONE`, P0 is 12/13, total progress is 12/129, `SAL-P0-013` is now `READY`, and `AEV-012` / `DEC-010` document evidence and CI strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-013`; Gate G0 remains not passed and P1/Quant Core remain blocked.
- Verification completed for `SAL-P0-012`: workflow YAML parsed, referenced scripts exist, baseline scripts pass `bash -n`, required check names and patch classifications are present, and `git diff --check` passed.

## Review: SAL-P0-010

- Added `scripts/run-dsa-report-signal-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, enforces registered worktree diff boundaries, generates offline report/signal fixtures, and compares committed snapshots by default.
- Added stable report/signal baseline artifacts under `docs/baselines/dsa-v3.26.1/report-signal/`: fixed inputs, Stub LLM responses, structured reports, single-stock/aggregate/market-review Markdown, Signal Evaluation details/summary, DecisionSignal summary, content hashes, and `summary.json`.
- Wrote `docs/report-signal-golden-baseline.md` with coverage, hash inventory, CI usage, verification commands, non-goals, and the decision to use offline Stub LLM/Provider-free inputs only.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-010` is `DONE`, P0 is 11/13, total progress is 11/129, and `AEV-011` / `DEC-009` document evidence and artifact strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-012`; Gate G0 remains not passed; `SAL-P0-013` remains gated by P0 completion.
- Verification completed for `SAL-P0-010`: baseline script generation and compare runs, `bash -n`, targeted upstream report/backtest tests `137 passed`, `git diff --check`, stale-progress scans, committed-fixture guard, secret/local-path scans, and `summary.json` assertions.

## Previous Review: SAL-P0-009

- Added `scripts/run-dsa-database-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, creates a sanitized SQLite fixture, dumps schema/index metadata, and compares committed SQL/JSON snapshots.
- Added stable database baseline artifacts under `docs/baselines/dsa-v3.26.1/database/`: `schema.sql`, `schema-metadata.json`, `fixture.sql`, `fixture-summary.json`, `content-hashes.json`, and `summary.json`.
- Wrote `docs/database-schema-baseline.md` with fixture coverage, hashes, verification commands, limitations, and the decision not to commit runtime `fixture.sqlite`.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-009` is `DONE`, P0 is 10/13, total progress is 10/129, and `AEV-010` / `DEC-008` document evidence and artifact strategy.
- Verification completed for `SAL-P0-009`: baseline script generation and compare runs, `bash -n`, `git diff --check`, stale-progress scans, committed-fixture guard, and `summary.json` assertions.
