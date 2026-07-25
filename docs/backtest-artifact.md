# BacktestArtifact Contract

> 任务：`SAL-P4-004` 定义 `BacktestArtifact`<br>
> 日期：2026-07-25<br>
> 前置任务：[`SAL-P4-003` BacktestSpec](./backtest-spec.md)<br>
> 结论：正式组合回测输出契约已冻结；`SAL-P4-005` 可在本任务后锁定 Qlib 版本与隔离方案

## 1. 交付结论

`SAL-P4-004` 新增平台正式组合回测输出契约：

```text
src/serenity_alpha_lab/quant/backtest/artifacts.py
tests/quant/test_backtest_artifact.py
```

该契约只定义不可变 `BacktestArtifactBundle` 与输出描述符，不执行订单生成、成交撮合、Portfolio Ledger 重放、绩效指标计算、偏差审计、Qlib Adapter、API、UI 或 Worker runtime。

正式组合回测输出从本契约开始与 legacy DSA `/api/v1/backtest/*` Signal Evaluation 兼容面分离。DSA Signal Evaluation、AlphaSift T+N evaluation 和 Screen result 均不能直接命名为正式组合回测。

## 2. 输出组成

| 输出 | `BacktestArtifactKind` | 标准内容 |
|---|---|---|
| 订单 | `orders` | 订单意图、目标数量、状态、拒绝/过期原因和分区键 |
| 成交 | `executions` | 成交数量、价格、成本、滑点、成交时间和源订单 |
| 持仓 | `positions` | 证券、数量、成本、估值、市值、权重和 lot/日期切片 |
| 现金 | `cash` | 可用现金、冻结现金、应收应付、股息/费用/税费现金流 |
| 净值 | `equity_curve` | 估值日期、组合净值、收益、基准和回撤输入 |
| 指标 | `metrics` | 收益、风险、回撤、换手、成本和基准相关指标 |
| 审计 | `audit` | PIT、执行、流动性、公司行动、偏差和完整性审计记录 |

每个输出都通过 `BacktestOutputArtifact` 记录：

- `schema_name` / `schema_version`
- `artifact_id` / `artifact_uri`
- `content_hash`
- `row_count`
- `partition_keys`
- 底层 `ArtifactManifest`

API 与任务状态只传递这些 compact descriptors，不嵌入完整 DataFrame、Arrow table 或原始记录行。

## 3. Bundle 状态

`BacktestArtifactBundle.state` 冻结四种状态：

| 状态 | 语义 |
|---|---|
| `preview` | 预览输出，可来自短区间、抽样或 dry-run；允许 warning |
| `formal` | 正式输出描述符完整且无 error |
| `partial` | 输出描述符存在但结果不完整；必须携带 warning 或 error |
| `invalid` | 输出不满足正式使用条件；必须携带 error |

Bundle 必须绑定：

- `spec_id` 和 `BacktestSpec.spec_hash`
- 具体 `dsv_*` Dataset Version
- `engine_scope=formal_portfolio_backtest`
- `trace_id`、`run_id`、`stage_id`
- 七类 required output kinds

契约拒绝 `latest` Dataset alias、缺少 required output、负 row count、manifest/hash 不一致、无原因的 partial/invalid 状态，以及 `legacy_signal_evaluation` engine scope。

## 4. Artifact 发布

`publish_backtest_artifact_bundle()` 只发布 compact bundle summary：

```text
schema_name = quant.backtest_artifact_bundle
schema_version = 1.0.0
content_type = application/vnd.serenity.quant.backtest-artifact-bundle+json
```

大结果表必须作为独立 `ArtifactManifest` 存储，并由 bundle 通过 URI、hash、schema 和 row count 引用。重复发布同一 bundle 会得到 deterministic summary bytes 和相同 artifact manifest。

## 5. 非目标

本任务没有启动正式组合回测运行，没有实现 Qlib、订单状态机、Portfolio Ledger、费用/slippage 计算、A 股执行规则、公司行动入账、RiskPolicy、偏差审计、绩效指标计算、BacktestRun 编排、资源隔离、真实回测 API、Quant Lab、Evidence Agent、真实 Provider/LLM 或 Worker loop。

## 6. 验证记录

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_backtest_artifact.py -q` | Red：初始 `1 error`，缺少 `serenity_alpha_lab.quant.backtest.artifacts`；Green `3 passed` |
| `.venv/bin/python -m pytest tests/quant/test_backtest_artifact.py tests/quant/test_backtest_spec.py tests/architecture/test_dsa_signal_evaluation_engine_migration.py tests/architecture/test_dsa_signal_evaluation_characterization.py -q` | `15 passed` |
| `.venv/bin/python -m compileall -q src tests` | PASS |
| `.venv/bin/python -m pytest -q` | `330 passed, 3 skipped` |
| `scripts/verify-python-dependency-lock.sh` | PASS，`Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | PASS，`0001..0005` already applied |
| `git rev-parse upstream/dsa-v3.26.1` | PASS，仍为 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git diff --check` | PASS |

## 7. 后续入口

`SAL-P4-005` 当前可进入 `READY`：锁定 Qlib 版本与隔离方案。后续仍不得跳过 P4 清单直接启动正式组合回测 API、Quant Lab、Evidence Agent、真实 Provider/LLM 或 Worker loop。
