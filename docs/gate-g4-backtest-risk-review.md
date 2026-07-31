# Gate G4 Backtest And Risk Review

> 任务：`SAL-P4-022` Gate G4：回测与风控评审<br>
> 评审日期：2026-07-26<br>
> Phase：P4 真实组合回测与确定性风控<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`<br>
> 批准范围：`APPROVED FOR P5 EVIDENCE SCHEMA INPUT ONLY`

## 1. Gate 结论

Gate G4 通过。P4 真实组合回测与确定性风控完成度为 `22/22`，项目总完成度推进到 `88/129`，允许进入 `SAL-P5-001` 定义 Evidence/Claim/Report Schema。 本 Gate 将 P4 正式组合回测证据链明确标记为 `formal portfolio backtest` scope。

本结论批准 P4 已冻结的 Screen/Factor/Backtest/Risk/Audit/Metrics/API/Quant Lab 证据链作为 P5 证据建模输入，但不批准直接启动 Evidence Agent、真实 Provider/LLM、Worker loop、Qlib runtime、生产调度或正式组合回测推广。

Gate G4 通过后仍必须遵守以下边界：

- Signal Evaluation、Factor Evaluation 和 Portfolio Backtest 是三类独立评价语义，不能互相替代。
- legacy /api/v1/backtest/* (`/api/v1/backtest/*`) 继续只表示 DSA Signal Evaluation 兼容面；正式组合回测 API 只使用 `/api/v1/quant/backtest-runs`。
- Qlib internal evidence、Dataset conversion artifacts、Screen results、AlphaSift T+N evaluation 和 legacy Signal Evaluation 不得命名为正式组合回测结果。
- P5 可以把 P4 输出映射为结构化 Evidence/Claim，但 LLM 不得自行重算收益、风险、成本、回撤或风控结论。
- 不启动 Evidence Agent，不调用真实 Provider/LLM，不启动 Worker loop，不启动 Qlib runtime，不迁移 DSA runtime source，不移动 `upstream/dsa-v3.26.1`。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| Signal/Factor/Portfolio 语义完全分离 | PASS | `SAL-P4-001` 锁定 legacy Signal Evaluation 金标；`SAL-P4-002` 迁移为 `SignalEvaluationEngine`；`SAL-P3-009` 保持 Factor Evaluation 后验评价；`SAL-P4-003` 起正式 Portfolio Backtest 另建 `BacktestSpec` |
| 正式回测输入输出契约冻结 | PASS | `SAL-P4-003` BacktestSpec 绑定具体 Dataset Version、Universe、Screen/Factor、交易时间、成本、风险和 canonical hash；`SAL-P4-004` BacktestArtifact 只发布 URI-only orders/executions/positions/cash/equity/metrics/audit descriptors |
| Qlib 边界与 ADR-009 受控 | PASS | `SAL-P4-005` 锁定 `pyqlib==0.9.7` 于 optional `quant` extra；`SAL-P4-006` Dataset conversion 不 import Qlib；`SAL-P4-007` Qlib Adapter 只产出 `engine_scope=qlib_quant_engine_adapter` evidence，未启动正式组合回测 |
| 订单、账本、成本和 A 股执行规则可重放 | PASS | `SAL-P4-008` Order State Machine、`SAL-P4-009` Portfolio Ledger、`SAL-P4-010` CostModel、`SAL-P4-011` A-share execution 覆盖订单生命周期、FIFO 账本、费用/滑点、T+1、交易单位、停牌和涨跌停 |
| 公司行动、调仓和目标权重口径明确 | PASS | `SAL-P4-012` Corporate Action Ledger 入账现金分红/送转/拆股/配股/退市清算；`SAL-P4-013` Rebalance target weights 从 Screen/Model 输入生成 created orders，不执行成交或修改账本 |
| Deterministic RiskPolicy 阻断语义有效 | PASS | `SAL-P4-014` RiskPolicy 覆盖个股、行业、风格、流动性、换手、回撤和 `not_evaluable`，并固定 `agent_override_allowed=false` |
| Backtest Bias Audit 与 Metrics 口径冻结 | PASS | `SAL-P4-015` Backtest Bias Audit 覆盖 lookahead、survivorship、PIT availability、sample overlap 和 cost sensitivity；`SAL-P4-016` Backtest Performance Metrics 冻结收益、风险、回撤、交易、成本、基准和行业暴露公式版本 |
| BacktestRun 编排与资源控制边界可用 | PASS | `SAL-P4-017` BacktestRun stage chain 串联 Spec、Engine、Ledger、Risk、Audit、Metrics、Artifacts、Summary；`SAL-P4-018` Resource Control 记录 timeout/cancel/OOM/partial checkpoint，不启动 Worker loop |
| 金标与性质测试覆盖核心组合链路 | PASS | `SAL-P4-019` Backtest Golden fixture 覆盖 3 instruments、20 trading days、60 bars、T+1、停牌、涨跌停、现金分红、费用、清仓和 full/chunked hash equivalence，result hash 为 `sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1` |
| Formal Backtest API 与 legacy API 隔离 | PASS | `SAL-P4-020` Formal Backtest API 冻结 `/api/v1/quant/backtest-runs` create/status/metrics/orders/positions/audit/artifact/cancel route metadata、Idempotency-Key、Artifact 授权和 runtime flags；未注册 legacy route |
| Quant Lab 只展示正式 API 结果 | PASS | `SAL-P4-021` Quant Lab 通过 `DSA-PATCH-006` 接入 `/api/v1/quant/backtest-runs`，明确 Preview/Formal、Artifact validity、Ranking eligibility 三类状态，并保留 legacy `/backtest` 为 Signal Evaluation |
| P1/P2/P3 平台基础未被绕过 | PASS | P4 继续使用 concrete Dataset Version、ProblemDetails、Trace、Artifact、Run/Stage/Event 和 Runtime Profile guard；未调用真实 Provider/LLM，未启动 Worker loop，未迁移 DSA runtime source |

## 3. P4 任务核对

| 任务 | 结论 | 核心证据 |
|---|---|---|
| `SAL-P4-001` | DONE | [DSA Signal Evaluation characterization](./dsa-signal-evaluation-characterization.md) 和 snapshot diff，确认 legacy API 只是 `legacy_signal_evaluation` |
| `SAL-P4-002` | DONE | [SignalEvaluationEngine 迁移记录](./signal-evaluation-engine.md)，保持 P4-001 金标一致 |
| `SAL-P4-003` | DONE | [BacktestSpec Contract](./backtest-spec.md)，正式组合回测输入 canonical hash 和版本 guard |
| `SAL-P4-004` | DONE | [BacktestArtifact Contract](./backtest-artifact.md)，七类必需输出和 compact bundle summary |
| `SAL-P4-005` | DONE | [Qlib 版本锁定与隔离方案](./qlib-version-isolation.md) 与 [ADR-009](./adr/ADR-009-qlib-adapter-boundary-and-version-upgrade-strategy.md) |
| `SAL-P4-006` | DONE | [Qlib Dataset Conversion](./qlib-dataset-conversion.md)，转换 artifact 仅为 adapter 输入 |
| `SAL-P4-007` | DONE | [Qlib QuantEngine Adapter](./qlib-quant-engine-adapter.md)，Recorder 只作 engine evidence |
| `SAL-P4-008` | DONE | [Order State Machine](./order-state-machine.md)，订单状态和事件 replay |
| `SAL-P4-009` | DONE | [Portfolio Ledger](./portfolio-ledger.md)，现金、应收应付、FIFO lot 和 equity reconciliation |
| `SAL-P4-010` | DONE | [Cost And Slippage Model](./cost-slippage-model.md)，费用、滑点、冲击和 participation guard |
| `SAL-P4-011` | DONE | [A-Share Execution Rules](./a-share-execution-rules.md)，T+1、交易单位、停牌和涨跌停 |
| `SAL-P4-012` | DONE | [Corporate Action Ledger Posting](./corporate-action-ledger-posting.md)，公司行动入账 |
| `SAL-P4-013` | DONE | [Rebalance And Target Weights](./rebalance-target-weights.md)，目标权重与 created orders |
| `SAL-P4-014` | DONE | [Deterministic RiskPolicy](./risk-policy.md)，风控 pass/warn/block/not-evaluable |
| `SAL-P4-015` | DONE | [Backtest Bias Audit](./backtest-bias-audit.md)，偏差审计和 promotion guard |
| `SAL-P4-016` | DONE | [Backtest Performance Metrics](./backtest-performance-metrics.md)，统一指标公式版本 |
| `SAL-P4-017` | DONE | [BacktestRun Orchestration](./backtest-run-orchestration.md)，stage chain 与 formal promotion guards |
| `SAL-P4-018` | DONE | [Backtest Resource Control](./backtest-resource-control.md)，资源、取消、超时、OOM 和 checkpoint |
| `SAL-P4-019` | DONE | [Backtest Golden And Property Tests](./backtest-golden-property-tests.md)，固定金标和性质测试 |
| `SAL-P4-020` | DONE | [Formal Backtest API](./backtest-api.md)，框架无关正式 API facade |
| `SAL-P4-021` | DONE | [Quant Lab](./quant-lab.md)，DSA Web extension patch |
| `SAL-P4-022` | DONE | 本 Gate G4 评审记录和 [Gate G4 integration test](../tests/gates/test_gate_g4_backtest_risk_review.py) |

## 4. 接受风险与后续约束

| 风险/限制 | Gate G4 处理 | 后续关闭条件 |
|---|---|---|
| Qlib runtime 尚未在真实 Worker 中运行 | 接受。P4 只批准 Dataset conversion、Qlib Adapter evidence 和 ADR-009 resource policy；默认测试使用 fake/injected facade，不启动 `qlib.init` | 后续 Worker/profile 任务在隔离进程中执行 Qlib runtime，并重跑 fixed-data golden、resource、cancel 和 artifact tolerance 测试 |
| 真实 Provider/LLM 调用仍未接入正式路径 | 接受但继续阻断默认路径。P4 formal backtest 使用离线契约和确定性 fixture，真实调用仍只能由后续 Worker/调度任务通过 profile guard、offline contract 和 fallback trace 接入 | P5/P6 对真实 Provider/LLM 完成 profile guard、预算、fallback trace、审计和 Runbook 后才能启用 |
| Backtest Golden 是合成 fixture，不代表生产收益 | 接受。Gate G4 证明组合链路可重放、可审计、可分页和可追踪，不构成投资结论 | P6 性能/容量、真实数据回放和发布门禁补充生产规模证据 |
| Quant Lab 是 DSA Web extension patch | 接受。`DSA-PATCH-006` 已通过 clean sequential apply；不代表大规模 DSA runtime source migration | 发布前复核 patch registry、Web build、security、packaging 和上游同步策略 |
| Formal API 仍为 framework-neutral facade | 接受。P4 未注册 FastAPI router，避免把未完成 Worker/runtime 暴露为生产接口 | 后续 API facade / Worker execution 任务必须复用 `application.formal_backtest_api@1.0.0` route metadata 和 ProblemDetails 语义 |
| 供应链和发布安全风险延续 | 接受但不批准发布。G0/G1/G2/G3 accepted risks 仍有效，Qlib/AlphaSift/Web/Image 供应链仍需发布门禁 | `SAL-P6-005` 或等效安全/许可证 Gate 修复或正式豁免 |

## 5. 本地评审验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g4_backtest_risk_review.py -q` | Red：`1 failed, 1 passed`，缺少 `docs/gate-g4-backtest-risk-review.md`；Green：`2 passed in 0.53s` |
| Related P4 suite | `37 passed in 0.50s`，覆盖 Gate G4、Formal Backtest API、BacktestRun、Resource Control、Golden、Metrics、BiasAudit、RiskPolicy 与 Qlib version isolation |
| Full pytest | `404 passed, 3 skipped in 2.89s` |
| Compile / lock / tag / diff guards | `compileall` PASS；dependency lock guard PASS (`Resolved 298 packages`)；`upstream/dsa-v3.26.1` 保持 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；`git diff --check` PASS |
| DSA patch-chain guard | live `.worktrees/dsa-v3.26.1` `--check-only` 命中已知已应用 patch context limitation at `0004-add-screen-lab.patch`；clean temporary worktree sequential replay applied `0001` through `0006` successfully |
| Gate G4 executable contract | 使用 `BacktestGoldenRunner` 复核 result hash、covered rules、ledger reconciliation、metrics；通过 `BacktestRunOrchestrator` 串联 engine evidence、RiskPolicy、BiasAudit、Metrics、BacktestArtifactBundle；检查 formal API route metadata 与 legacy `/api/v1/backtest/*` 隔离 |

Gate G4 integration test 明确验证：

- Backtest Golden result hash 为 `sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1`。
- P4 formal run stage chain 为 `spec -> engine -> ledger -> risk -> audit -> metrics -> artifacts -> summary`。
- Risk/Audit pass 且 ranking eligible。
- BacktestRun summary runtime flags 不启动 resource controls、API route、Quant Lab、Worker loop、real Provider 或 real LLM。
- Formal API route metadata 使用 `/api/v1/quant/backtest-runs`，且 operation id 不含 `signal`。
- `BacktestSpec` record 不含 `latest`，`BacktestRunRecord` 不含 `legacy_signal_evaluation`。

## 6. P5 入口约束

P5 第一入口为 `SAL-P5-001` 定义 Evidence/Claim/Report Schema。P5 实现必须沿用 P4 已冻结的证据边界：

- Evidence 可以引用 ScreenSnapshot、Factor Evaluation、BacktestRun summary、BacktestArtifactBundle、RiskPolicyResult、BacktestBiasAuditReport、BacktestPerformanceMetricReport、Formal Backtest API 和 Quant Lab lineage。
- Claim 必须声明 citation/evidence ids、单位、公式版本、Dataset Version、Run/Stage/Event、Artifact hash 和 verification status。
- LLM 不得自行计算或改写收益、风险、回撤、成本、成交、账本或风控状态。
- Evidence Agent、真实 Provider/LLM、Worker loop、Qlib runtime 执行和生产报告生成仍须等待后续显式任务，不得由 Gate G4 直接启动。
- 未通过 RiskPolicy、BiasAudit、Artifact validity 或 ranking eligibility 的 run 不得进入强结论、leaderboard 或自动报告。

## 7. 最终判定

`SAL-P4-022` 判定为 `DONE`。Gate G4 通过后，P4 真实组合回测与确定性风控完成度为 `22/22`，项目进入 P5 证据化 Agent、报告与成本治理阶段。下一步唯一推荐入口是 `SAL-P5-001`，先定义 Evidence/Claim/Report Schema，而不是直接运行 Evidence Agent 或真实 Provider/LLM。
