# BacktestSpec Contract

> 任务：`SAL-P4-003` 定义正式 `BacktestSpec`<br>
> 日期：2026-07-25<br>
> 前置任务：[`SAL-P4-002` SignalEvaluationEngine](./signal-evaluation-engine.md)<br>
> 结论：正式组合回测输入契约已冻结；`SAL-P4-004` 可在本任务后定义 `BacktestArtifact`

## 1. 交付结论

`SAL-P4-003` 新增平台正式组合回测输入契约：

```text
src/serenity_alpha_lab/quant/backtest/spec.py
tests/quant/test_backtest_spec.py
```

该契约只定义不可变 `BacktestSpec` 与 Dataset、Universe、Strategy、Execution、Cost、Risk 六组输入，不执行订单生成、成交撮合、Ledger 重放、绩效指标、偏差审计、Qlib Adapter、API、UI 或 Worker runtime。

正式组合回测从本契约开始，与 legacy DSA `/api/v1/backtest/*` Signal Evaluation 兼容面分离。DSA Signal Evaluation、AlphaSift T+N evaluation 和 Screen result 均不能直接命名为正式组合回测。

## 2. 契约组成

| 组件 | 类 | 冻结内容 |
|---|---|---|
| Dataset | `BacktestDatasetSpec` | `adjusted_daily_bars`、`raw_daily_bars`、`trading_calendar`、`corporate_actions`、`instrument_master` 的具体 `dsv_*` 版本和 `sha256:*` Dataset hash |
| Universe | `BacktestUniverseSpec` | 具体 `universe_version_id`、股票池名称、as-of 日期和 PIT membership policy |
| Strategy | `BacktestStrategySpec` | 策略 ID/version/kind、source commit、代码 hash、`sdv_*` ScreenDefinition、`ssn_*` ScreenSnapshot 和 `fdv_*` Factor versions |
| Execution | `BacktestExecutionSpec` | 信号时间、执行时间、信号价格字段、执行价格字段、调仓/估值日历、调仓频率、结算滞后、交易单位和随机种子 |
| Cost | `BacktestCostSpec` | 佣金、最低佣金、印花税、过户费、滑点、冲击成本和最大成交参与率 |
| Risk | `BacktestRiskSpec` | 风控规则版本、个股/行业/换手上限、现金缓冲和流动性下限 |

组合层 `BacktestSpec` 还绑定起止日期、基准、币种、初始资金、现金利率、输出级别、schema/contract/engine version 和 `spec_hash`。

## 3. Canonical Hash

`BacktestSpec.spec_hash` 使用 Canonical JSON 生成：

```text
spec_hash = sha256(canonical_json(spec_payload))
```

Canonical JSON 使用 `sort_keys=True` 和紧凑 separators，`Decimal` 按字符串输出，Dataset mapping 会按 key 排序。`created_at`、`created_by_run_id` 和 `spec_hash` 本身不进入 hash payload，因此相同正式输入在不同平台和不同创建时间下生成相同 hash。

当前测试覆盖：

- Dataset mapping 插入顺序变化不改变 `canonical_json()` 或 `spec_hash`。
- 费用等语义输入变化会改变 `spec_hash`。
- `to_record()` 输出可 JSON 序列化，并保留 `spec_hash`、创建时间和创建 run。

## 4. 硬校验

`BacktestSpec` 当前拒绝以下输入：

- Dataset 或 Universe 使用 `latest` alias，而不是具体 `dsv_*`。
- Dataset hash 缺失、hash key 与版本 key 不一致，或 hash 不符合 `sha256:<64 hex>`。
- Strategy 使用 `legacy_signal_evaluation`。
- ScreenDefinition、ScreenSnapshot、Factor version 不符合 `sdv_*`、`ssn_*`、`fdv_*`。
- 同一根 Bar 的 close 信号以同一根 Bar close 无条件执行。
- 起止日期倒置、初始资金非正、费用为负、参与率/风控比例越界、交易单位或随机种子无效。

## 5. 非目标

本任务没有启动正式组合回测运行，没有定义 `BacktestArtifact`，没有实现 Qlib、订单状态机、Portfolio Ledger、费用/slippage 计算、A 股执行规则、公司行动入账、RiskPolicy、偏差审计、绩效指标、BacktestRun 编排、资源隔离、真实回测 API、Quant Lab、Evidence Agent、真实 Provider/LLM 或 Worker loop。

## 6. 验证记录

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_backtest_spec.py -q` | Red：初始 `1 error`，缺少 `serenity_alpha_lab.quant.backtest.spec`；Green `3 passed` |
| `.venv/bin/python -m pytest tests/quant/test_backtest_spec.py tests/architecture/test_dsa_signal_evaluation_engine_migration.py tests/architecture/test_dsa_signal_evaluation_characterization.py tests/architecture/test_architecture_boundaries.py -q` | `26 passed` |
| `.venv/bin/python -m pytest -q` | `327 passed, 3 skipped` |
| `.venv/bin/python -m compileall -q src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS，`Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | PASS，`0001..0005` already applied |
| `git rev-parse upstream/dsa-v3.26.1` | PASS，仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git diff --check` | PASS |

## 7. 后续入口

`SAL-P4-004` 当前可进入 `READY`：基于本 `BacktestSpec` 定义 `BacktestArtifact`，标准化订单、成交、持仓、现金、净值、指标和审计输出。后续仍不得跳过 P4 清单直接启动正式组合回测 API、Quant Lab 或 Evidence Agent。
