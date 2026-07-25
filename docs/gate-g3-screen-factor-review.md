# Gate G3 筛选与因子评审

> 任务：`SAL-P3-017` Gate G3：筛选与因子评审<br>
> 评审日期：2026-07-25<br>
> Phase：P3 AlphaSift、因子与股票筛选<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`

## 1. Gate 结论

Gate G3 通过。P3 AlphaSift、因子与股票筛选完成度为 `17/17`，项目总完成度推进到 `66/129`，允许进入 P4 真实组合回测与确定性风控开发。

本结论为 `APPROVED FOR P4`，但只批准把已冻结的 Screen/Factor 契约作为 P4 输入。它不代表已经完成 Quant Core、Qlib、正式组合回测、Evidence Agent 或生产 Worker 接入。

Gate G3 通过后仍必须遵守以下边界：

- 不启动 Quant Core，直到 `SAL-P4-003` 及后续 BacktestSpec/引擎任务建立输入契约。
- 不执行正式回测，直到 P4 明确定义交易时间、成交、费用、组合账本、风险和质量门禁。
- 不启动 Evidence Agent，引用验证和报告 Agent 仍属于 P5。
- 不调用真实 Provider/LLM；真实 Provider/LLM 仍只能在后续 Worker/调度任务中通过 profile guard、离线契约和 fallback trace 接入。
- 不启动 Worker execution loop；数据库 task/run events 仍是当前恢复与审计来源。
- 不迁移 DSA runtime source，不移动 `upstream/dsa-v3.26.1`，不绕过 ADR-001/002。

未通过数据/偏差检查的 Screen 不得进入 P4 正式回测；P4 只能消费具体 `dsv_*` Dataset Version、`fdv_*` Factor Version、`sdv_*` ScreenDefinition 和 `ssn_*` ScreenSnapshot。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| AlphaSift 来源、许可证和制品可审计 | PASS | `SAL-P3-001` 锁定源码 commit、source archive hash、Apache-2.0；`SAL-P3-002` 生成内部 Wheel hash、SBOM、license inventory 和离线安装证据 |
| ScreeningProvider 与 AlphaSift Adapter 不绕过平台边界 | PASS | `SAL-P3-003` 将真实 AlphaSift 限制在 `integrations.alphasift`，CI profile 禁止未注入 client 的真实调用，LLM overlay 受 model-call policy 控制 |
| CandidateBatch 标准化候选、分数、原因和来源 | PASS | `SAL-P3-004` 冻结 `screening.candidate_batch@1.0.0`，覆盖 L1/L2/L3 score records、concrete Dataset Version、rank、reason/source lineage |
| FactorDefinition、DSL、基础因子和后处理口径冻结 | PASS | `SAL-P3-005` 至 `SAL-P3-008` 覆盖 `FactorDefinition`、DSL whitelist、15 个基础因子、横截面 winsorize/neutralize/z-score |
| Factor Evaluation 可作为因子评审证据 | PASS | `SAL-P3-009` 输出覆盖率、IC/ICIR、分组收益、方向调整单调性、换手、暴露和 deterministic Artifact |
| Factor DAG/cache 与 Historical Universe 输入边界可用 | PASS | `SAL-P3-010` 绑定 factor-specific Dataset/Factor/Universe/date-range/engine cache key；`SAL-P3-011` 构建 PIT L0 历史股票池和 deterministic universe version |
| ScreenDefinition Pipeline、ScreenSnapshot 与解释轨迹可回放 | PASS | `SAL-P3-012` 固定 L0~L4 stage trace；`SAL-P3-013` 保留 passed/failed rows、rank/failed-stage invariants、factor contributions 和 authoritative explanation steps |
| Quant Screening API 与 Screen Lab 可消费筛选结果 | PASS | `SAL-P3-014` 提供 `/api/v1/quant` route metadata、idempotent run、stable pagination、comparison 与 ProblemDetails；`SAL-P3-015` 通过 Screen Lab UI 展示 lineage、状态和 comparison |
| 性能、容量、增量和复现契约通过 | PASS | `SAL-P3-016` 在 [筛选性能与复现验收记录](./screen-performance-reproducibility.md)（`docs/screen-performance-reproducibility.md`）中冻结普通筛选 `<=3,000ms`、缓存查询 `<=500ms`、峰值内存 `<=512MB`、结果行 `<=6,000`、增量重算 `<=15%`、canonical result hash 和 Fixed Run Bundle |
| P2/P1 平台基础未被绕过 | PASS | Gate G3 测试覆盖 Dataset Catalog/Manifest concrete version guard、ProblemDetails、Trace、Artifact、Run/Stage/Event；P3 文档持续声明不调用真实 Provider/LLM、不启动 Worker loop、不迁移 DSA runtime source |

## 3. P3 任务核对

| 任务 | 结论 | 核心证据 |
|---|---|---|
| `SAL-P3-001` | DONE | [AlphaSift 源码审查与锁定记录](./alphasift-source-review.md)，锁定 `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf` 与 source archive SHA-256 |
| `SAL-P3-002` | DONE | [AlphaSift 离线 Wheel Intake 记录](./alphasift-wheel-intake.md)，wheel SHA-256、SBOM、license inventory 和 internal artifact URI |
| `SAL-P3-003` | DONE | [ScreeningProvider 契约与 AlphaSift Adapter 记录](./screening-provider-contract.md)，Profile guard、LLM guard 和 ProblemDetails provider mapping |
| `SAL-P3-004` | DONE | [CandidateBatch 候选契约记录](./candidate-batch-contract.md)，标准 CandidateBatch schema、rank、L1/L2/L3 score、reason/source lineage |
| `SAL-P3-005` | DONE | [FactorDefinition 版本模型记录](./factor-definition-version-model.md)，draft/published/retired 生命周期和不可变 manifest |
| `SAL-P3-006` | DONE | [Factor DSL 与算子白名单记录](./factor-dsl-operator-whitelist.md)，AST whitelist、guarded_divide、window/input guard |
| `SAL-P3-007` | DONE | [基础因子定义记录](./base-factor-definitions.md)，15 个基础因子覆盖 quality/valuation/growth/momentum/volatility/liquidity |
| `SAL-P3-008` | DONE | [横截面因子后处理记录](./factor-cross-sectional-post-processing.md)，缺失处理、winsorize、中性化和 z-score |
| `SAL-P3-009` | DONE | [Factor Evaluation 记录](./factor-evaluation.md)，coverage、IC/ICIR、group return、monotonicity、turnover、exposure 和 Artifact |
| `SAL-P3-010` | DONE | [Factor DAG/cache 记录](./factor-dag-cache.md)，CSE、cache key、partition、incremental recompute 和质量门发布 |
| `SAL-P3-011` | DONE | [Historical Universe 记录](./historical-universe.md)，PIT Instrument Master as-of、L0 hard filters 和 deterministic `dsv_*` universe |
| `SAL-P3-012` | DONE | [ScreenDefinition 与 L0-L4 Pipeline 记录](./screen-definition-pipeline.md)，published ScreenDefinition guard、L0~L4 trace 和 deterministic `sps_*` Artifact |
| `SAL-P3-013` | DONE | [ScreenSnapshot 与解释轨迹记录](./screen-snapshot-explanation-trace.md)，passed/failed rows、explanation steps 和 comparison |
| `SAL-P3-014` | DONE | [Quant Screening API 记录](./quant-screening-api.md)，Idempotency-Key、TaskBackend command、stable pagination、single result 和 ProblemDetails |
| `SAL-P3-015` | DONE | [Screen Lab 记录](./screen-lab.md)，DSA Web extension patch、API client、route/nav/i18n、UI states 和 lineage display |
| `SAL-P3-016` | DONE | [筛选性能与复现验收记录](./screen-performance-reproducibility.md)，SLO、capacity、incremental baseline、canonical result hash 和 Fixed Run Bundle |
| `SAL-P3-017` | DONE | 本 Gate G3 评审记录和 [Gate G3 integration test](../tests/gates/test_gate_g3_screen_factor_review.py) |

## 4. 接受风险与后续约束

| 风险/限制 | Gate G3 处理 | 后续关闭条件 |
|---|---|---|
| `RSK-002` PIT 数据时间不可信 | 接受但继续限制正式回测。P3 只允许 concrete Dataset Version、PIT decision-time guard 和 Historical Universe as-of 口径作为输入契约 | P4 正式回测前必须使用可信 PIT Dataset Version；unknown temporal confidence 不得进入 formal backtest |
| `RSK-004` 免费 Provider 不稳定 | 接受但不批准真实调用。P3 使用离线 contract/fake/guard，AlphaSift/Provider 真实路径仍需 Worker/调度层接入 profile guard 和 fallback trace | P6 发布门禁前完成 live probe/SLA/降级 Runbook；P4/P5 真实调用路径必须单独评审 |
| `RSK-005` 许可证/服务条款冲突 | AlphaSift Apache-2.0、SBOM、license inventory 已审；数据服务条款和发行包第三方通知仍未关闭 | `SAL-P6-005` 完成发布安全/许可证门禁或正式豁免 |
| Screen/Factor 仍是 contract-level 离线验收 | 接受。G3 只批准契约作为 P4 输入，不声称已经有可投资组合或真实收益证据 | P4 完成 BacktestSpec、数据质量门、交易成本、ledger/risk 和 deterministic backtest evidence |
| Screen Lab 仍为 Web extension patch | 接受。`DSA-PATCH-004` 属于 extension，不代表 DSA runtime source 大规模迁移 | P6 发布前评审 patch registry、Web build、security 和 packaging |

## 5. 本地评审验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/gates/test_gate_g3_screen_factor_review.py -q` | Red：`1 failed, 1 passed`，缺少 `docs/gate-g3-screen-factor-review.md`；Green：`2 passed` |
| `.venv/bin/python -m pytest tests/gates/test_gate_g3_screen_factor_review.py tests/quant/test_screen_performance_reproducibility.py tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/application/test_quant_screening_api.py tests/quant/test_factor_evaluation.py tests/quant/test_base_factor_definitions.py -q` | PASS：`24 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`312 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | PASS：`0001..0004` already applied |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git diff --check` | PASS |

Gate G3 integration test 使用合成离线数据验证：

- 15 个基础因子 catalog 和 DSL reference plan 可编译。
- Factor Evaluation 生成覆盖率、IC 和 deterministic Artifact。
- ScreenDefinition Pipeline 生成 L0~L4 stage trace。
- ScreenSnapshot 保留结果、解释、Dataset、Trace 和 Artifact 锚点。
- Screen performance report 保留预算、增量、复现和 Fixed Run Bundle。
- Quant Screening API 通过 `Idempotency-Key` 提交 `quant.screen.run`，并稳定分页返回结果。
- ProblemDetails 映射保留 trace id。
- Run/Stage/Event 领域模型可追加并完成 run lifecycle。

## 6. P4 入口约束

P4 第一入口为 `SAL-P4-001` 锁定 DSA Signal Evaluation 行为。P4 实现必须沿用 P3 已冻结的筛选和因子边界：

- P4 可以消费 P3 的 `FactorDefinition`、Factor Evaluation、Historical Universe、ScreenDefinition、ScreenSnapshot、Screen Performance report 和 Quant Screening API records。
- P4 不得把 AlphaSift T+N evaluation、DSA Signal Evaluation 或 Screen result 直接命名为正式组合回测。
- BacktestSpec 必须绑定 concrete Dataset Version、Universe Version、Screen/Factor Version、交易时间、费用、滑点、现金、持仓、风险和随机种子。
- 未通过数据质量、偏差、PIT、复现或性能检查的 ScreenDefinition/ScreenSnapshot 不得进入 formal backtest。
- 真实 Provider/LLM 仍不得进入默认测试路径；后续真实调用必须继续通过 Runtime Profile guard、离线契约、fallback trace、ProblemDetails、Trace、Artifact 和 Run/Stage/Event。

## 7. 最终判定

`SAL-P3-017` 判定为 `DONE`。Gate G3 通过后，P3 AlphaSift、因子与股票筛选完成度为 `17/17`，项目进入 P4。下一步唯一推荐入口是 `SAL-P4-001`，先锁定并纠正 DSA Signal Evaluation 行为，避免把信号评价误标为正式组合回测。
