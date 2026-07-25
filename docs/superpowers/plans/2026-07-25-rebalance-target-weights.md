# Rebalance Target Weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P4-013` as a pure deterministic rebalance planner that turns ScreenSnapshot and model-signal inputs into target weights and created `Order` snapshots.

**Architecture:** Add a narrow `quant.backtest.rebalance` module that reads `BacktestSpec`, `PortfolioLedger`, explicit prices and Screen/Model signal records, then emits immutable `RebalancePlan` records plus created `Order` snapshots. It reuses `BacktestExecutionSpec` lot size and `BacktestRiskSpec` cash/max-weight fields, but leaves actual RiskPolicy, A-share execution, fills, ledger mutation, metrics, audit, APIs and workers to later P4 tasks.

**Tech Stack:** Python dataclasses, `Decimal`, existing `InstrumentId`, `BacktestSpec`, `PortfolioLedger`, `OrderIntent` / `Order`, and pytest contract tests.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_rebalance_target_weights.py`
- Read: `tests/quant/test_backtest_spec.py`
- Read: `tests/quant/test_portfolio_ledger.py`
- Read: `tests/quant/test_order_state_machine.py`

- [ ] **Step 1: Write failing tests**

Add tests that import these future public symbols:

```python
from serenity_alpha_lab.quant.backtest.rebalance import (
    REBALANCE_POLICY_CONTRACT_VERSION,
    ModelSignal,
    RebalanceOrderGenerator,
    RebalancePolicy,
    RebalancePolicyError,
    WeightingPolicy,
)
```

Cover these behaviors:

```python
def test_screen_snapshot_rebalance_generates_lot_rounded_created_orders_with_cash_buffer() -> None:
    # Existing holdings: 600519 valued above target and 000001 below target.
    # ScreenSnapshot passed rows: 600519, 000001, 300750.
    # Equal weights, 2% cash buffer, 10% max instrument weight, 100-share lot.
    # Assert sell orders come before buys, each order is only `created`, quantities are lot rounded,
    # buy orders do not exceed settled cash after payables and buffer, and residual cash is recorded.
```

```python
def test_score_weighting_caps_weights_and_skips_min_notional_orders() -> None:
    # Score-proportional screen weights must be capped by max_weight_per_instrument.
    # A tiny target delta under min_order_notional is skipped with a deterministic reason.
```

```python
def test_model_signal_explicit_weights_create_deterministic_orders() -> None:
    # ModelSignal with explicit target_weight values should produce stable target weights,
    # stable plan_id/order_id/event_id values and JSON-friendly records.
```

```python
def test_rebalance_rejects_bad_bindings_and_stays_pure() -> None:
    # Reject ScreenSnapshot id mismatch, latest-like missing bindings, missing price, negative weights,
    # and AST-scan the module to ensure no qlib/pyqlib/fastapi/sqlalchemy imports.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.backtest.rebalance'`.

### Task 2: Rebalance Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/rebalance.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`
- Test: `tests/quant/test_rebalance_target_weights.py`

- [ ] **Step 1: Define immutable DTOs**

Create:

```python
REBALANCE_POLICY_CONTRACT_VERSION = "quant.rebalance_policy@1.0.0"
REBALANCE_POLICY_SCHEMA_NAME = "quant.backtest.rebalance_policy"
REBALANCE_POLICY_SCHEMA_VERSION = "1.0.0"
REBALANCE_ORDER_GENERATOR_VERSION = "cn_a_share_rebalance_order_generator@1.0.0"

class RebalancePolicyError(ValueError): ...
class WeightingPolicy(StrEnum):
    EQUAL_WEIGHT = "equal_weight"
    SCORE_PROPORTIONAL = "score_proportional"
    EXPLICIT_TARGET_WEIGHT = "explicit_target_weight"
```

Then add frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class RebalancePolicy:
    policy_id: str
    policy_version: str
    weighting_policy: WeightingPolicy | str
    min_order_notional: Decimal | int | str
    max_positions: int | None = None
    order_type: OrderType | str = OrderType.MARKET
    time_in_force: TimeInForce | str = TimeInForce.DAY
```

```python
@dataclass(frozen=True, slots=True)
class ModelSignal:
    signal_id: str
    instrument_id: InstrumentId
    as_of: date
    model_version_id: str
    score: Decimal | int | str | None = None
    target_weight: Decimal | int | str | None = None
    rank: int | None = None
```

Also define `TargetWeight`, `SkippedRebalanceOrder`, and `RebalancePlan` with `to_record()` methods that stringify `Decimal`s and include `plan_id`, `target_weight_sum`, `cash_buffer_amount`, `available_buy_cash`, `planned_buy_notional`, `planned_sell_notional`, `residual_cash`, `orders`, and `skipped_orders`.

- [ ] **Step 2: Implement target-weight builders**

`RebalanceOrderGenerator` constructor must accept `spec: BacktestSpec` and `policy: RebalancePolicy`, validate exact types, and reuse:

```python
lot_size = spec.execution.lot_size
cash_buffer_pct = spec.risk.cash_buffer_pct
max_weight_per_instrument = spec.risk.max_weight_per_instrument
```

Implement:

```python
def target_weights_from_screen_snapshot(self, snapshot: ScreenSnapshot) -> tuple[TargetWeight, ...]
def target_weights_from_model_signals(self, signals: Sequence[ModelSignal]) -> tuple[TargetWeight, ...]
```

Rules:
- ScreenSnapshot id must equal `spec.strategy.screen_snapshot_id`.
- Use passed rows only, sorted by rank.
- Apply `policy.max_positions` before weighting.
- Equal weighting assigns each selected instrument the same share of `1 - cash_buffer_pct`.
- Score weighting uses positive `final_score` / `score`; zero or missing aggregate score is rejected.
- Explicit model target weights must be non-negative and sum to at most `1 - cash_buffer_pct`.
- Every target is capped at `spec.risk.max_weight_per_instrument`; capped residual remains cash.

- [ ] **Step 3: Implement order generation**

Implement:

```python
def build_plan(
    self,
    *,
    ledger: PortfolioLedger,
    target_weights: Sequence[TargetWeight],
    prices: Mapping[InstrumentId | str, Decimal | int | str],
    trade_date: date,
    signal_time: datetime,
    created_at: datetime,
    source_snapshot_id: str | None = None,
    source_model_version_id: str | None = None,
) -> RebalancePlan
```

Rules:
- Ledger `run_id`, `stage_id`, `spec_id`, and `spec_hash` must match the spec.
- Prices must cover every current holding and target instrument.
- Portfolio equity comes from `ledger.equity`.
- Buy cash budget is `max(ledger.cash_balance - ledger.payables - equity * cash_buffer_pct, 0)`.
- Receivables are not available buy cash.
- Delta notional is `target_value - current_market_value`.
- Quantity is floored to `spec.execution.lot_size`.
- Skip zero-lot or under-`min_order_notional` deltas with deterministic `SkippedRebalanceOrder`.
- Generate sell orders before buy orders; within side, sort by instrument canonical.
- Do not assume sell proceeds can fund same-rebalance buys.
- Create `Order` snapshots using `Order.create(...)`; do not accept, fill, expire, execute, or mutate the ledger.
- Derive stable `plan_id`, `order_id`, and created event IDs from canonical JSON inputs.

- [ ] **Step 4: Export public symbols**

Update `src/serenity_alpha_lab/quant/backtest/__init__.py` to export the constants, DTOs, error, enum and generator.

- [ ] **Step 5: Run focused tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py -q`

Expected: PASS.

### Task 3: Evidence And Status

**Files:**
- Create: `docs/rebalance-target-weights.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**

Create `docs/rebalance-target-weights.md` with sections:
- Conclusion
- Contract
- Target weight rules
- Order generation rules
- Scope guard
- Verification

Explicitly state no formal portfolio backtest run, no execution/fill, no ledger mutation, no RiskPolicy, no metrics, no audit, no Quant Lab, no Evidence Agent, no Worker loop, no real Provider/LLM and no legacy `/api/v1/backtest/*` drift.

- [ ] **Step 2: Update progress checklist**

Mark `SAL-P4-013` as `DONE`, set P4 to `13/22`, total to `79/129`, add `DEC-077` and `AEV-079`, and make `SAL-P4-014` `READY` without starting it.

- [ ] **Step 3: Update development status**

Update current task/status text, completed P4 list, latest checkpoint placeholders, progress, and next-session prompt so it points to `SAL-P4-014` deterministic RiskPolicy.

- [ ] **Step 4: Update task review**

Add `Review: SAL-P4-013` to the top task section in `tasks/todo.md`, including Red failure, Green focused/related/full verification, subagent fallback, scope guard and checkpoint hashes after commit.

### Task 4: Verification And Commit

**Files:**
- Verify all files touched by Tasks 1-3.

- [ ] **Step 1: Run target and related suites**

Run:

```bash
uv run --extra core --extra dev python -m pytest \
  tests/quant/test_rebalance_target_weights.py \
  tests/quant/test_a_share_execution_rules.py \
  tests/quant/test_cost_slippage_model.py \
  tests/quant/test_portfolio_ledger.py \
  tests/quant/test_order_state_machine.py \
  tests/quant/test_backtest_spec.py \
  tests/quant/test_screen_snapshot.py \
  tests/architecture/test_architecture_boundaries.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run full and hygiene checks**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: pytest PASS, compileall PASS, lock guard PASS, DSA patches already applied, tag hash remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, diff check PASS.

- [ ] **Step 3: Commit**

Stage only SAL-P4-013 implementation, tests and docs. Commit with:

```bash
git commit -m "feat(P4): 实现调仓与目标权重" \
  -m "完成内容：" \
  -m "- 新增 RebalancePolicy、WeightingPolicy、ModelSignal、TargetWeight 与 RebalanceOrderGenerator" \
  -m "- 将 ScreenSnapshot 和模型信号转为受现金缓冲、持仓权重、最小订单与交易单位约束的 created orders" \
  -m "兼容性与风险：" \
  -m "- 不启动正式组合回测、不执行成交、不修改 Ledger、不实现 Risk/Metric/Audit/API/Worker" \
  -m "- 保持 legacy Signal Evaluation 与正式组合回测命名隔离" \
  -m "验证：" \
  -m "- uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py -q" \
  -m "- uv run --extra core --extra dev python -m pytest -q" \
  -m "- compileall、dependency lock、DSA patch check、immutable tag 和 git diff --check 通过" \
  -m "关联任务：SAL-P4-013, Gate G4"
```
