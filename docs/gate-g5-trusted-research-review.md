# Gate G5 Trusted Research Review

> 任务：`SAL-P5-018` Gate G5：可信研究评审<br>
> 评审日期：2026-07-30<br>
> Phase：P5 证据化 Agent、报告与成本治理<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`<br>
> 批准范围：`APPROVED FOR P6 RC HARDENING INPUT ONLY`

## 1. Gate 结论

Gate G5 通过。P5 证据化 Agent、可信 ResearchReport、引用 UI、通知 Outbox metadata、模型预算与 Agent Golden 评测完成度为 `18/18`，项目总完成度推进到 `106/129`，允许进入 `SAL-P6-001` 认证与 RBAC 的发布加固入口。

本结论批准 P5 已冻结的离线可信研究链作为 P6 RC hardening 输入：Evidence、EvidenceBundle、Prompt/Schema、Agent stage metadata、Technical/Intel/Risk/Portfolio/Decision adapter、Model Routing、Citation Validator、Agent Tool Security、Trusted ResearchReport Renderer、Research Report Delivery UI、Notification Outbox 和 Agent Golden regression evaluation 可以进入 RC 级安全、权限、E2E、性能、迁移、发布和运维加固。

本 Gate 不批准生产 runtime 扩围。Gate G5 通过后仍必须遵守以下边界：

- 不调用真实 Provider/LLM，不启动 Worker loop，不启动 Qlib runtime，不启动生产调度，不推广正式组合回测。
- 不执行 Agent/tool runtime，不读取 Evidence body 作为模型输入，不写 Evidence Store repair，不发送通知 sender，不注册生产后端 route。
- Agent 无法覆盖 Quant/Risk 硬事实与门禁；`block`、`not_evaluable`、`eligible_for_ranking=false` 和 `agent_strong_conclusion_allowed=false` 仍是确定性约束。
- LLM 不得自行重算收益、风险、回撤、成本、成交、账本或风控状态；numeric Claim 必须来自 deterministic evidence 并通过 Citation Validator。
- Screen result、Factor Evaluation、legacy Signal Evaluation、Qlib internal evidence、Dataset conversion artifacts 和 AlphaSift T+N evaluation 不得命名为正式组合回测结果。
- `SAL-P6-001` 之后的发布加固任务必须继续以 profile guard、审计、权限、配置、SLO、故障注入和 Runbook 关闭 runtime 风险。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| Evidence/Claim/Report Schema 冻结且 formal scope 不混淆 | PASS | `SAL-P5-001` 冻结 `research.evidence@1.0.0`、`research.claim@1.0.0`、`research.report@1.0.0`；Quant source matrix 明确 formal portfolio backtest 只来自 Gate G4 批准的 P4 输出 |
| Evidence Store 与 EvidenceBundle 保持离线、可追踪和预算化 | PASS | `SAL-P5-002` LocalEvidenceStore 使用 sanitized body artifact 与 immutable metadata；`SAL-P5-003` EvidenceBundle 按 tenant/team/user、decision time、role 和 deterministic token budget 构造上下文 |
| Source Trust 和 Quant Evidence Adapter 防止污染与重算 | PASS | `SAL-P5-004` Source Trust 移除外部 prompt/tool 指令并输出 prompt-safe hashes；`SAL-P5-005` Quant Evidence Adapter 只映射既有 DTO，设置 `llm_recompute_allowed=false` |
| Prompt/Schema/Stage/Model 版本可复现 | PASS | `SAL-P5-006` Prompt Registry 拒绝 `latest`，记录 prompt/schema/tool/model hashes；`SAL-P5-007` Agent Stage Store 只持久化 checkpoint 和成功 receipt metadata；`SAL-P5-012` Model Routing 构造精确 cache key、预算和 rate-limit fallback |
| Role Agent adapter 只消费证据并保留硬门禁 | PASS | `SAL-P5-008` Technical Agent 拒绝 formal backtest/risk evidence；`SAL-P5-009` Intel Agent 只使用 source-trust-backed unstructured evidence；`SAL-P5-010` Risk/Portfolio Agent 保留 deterministic hard gate；`SAL-P5-011` Decision Agent 要求多空反证、前序引用一致并禁止升级 risk hard gate |
| Citation、报告、UI 和 Outbox 全链路可审计 | PASS | `SAL-P5-013` Citation Validator 校验 mandatory citations、lineage、one-attempt repair deletion；`SAL-P5-015` Trusted ResearchReport Renderer 以 canonical JSON 为唯一权威；`SAL-P5-016` Research Report Delivery UI 展开 claim/citation/evidence/source/artifact，Outbox 只保存 metadata 和 lease/retry/sent/dead_letter 状态 |
| 工具安全和恶意内容防护有效 | PASS | `SAL-P5-014` Agent Tool Security 默认拒绝未绑定/未授权工具，校验 JSON-Schema subset、SSRF URL 和 prompt-injection arguments；Gate G5 executable test 验证 malicious source 清洗和 `shell.run` 拒绝 |
| Agent Golden regression 达到 G5 阈值 | PASS | `SAL-P5-017` 默认 catalog 56 cases，覆盖 normal、missing_data、financial_anomaly、major_event、viewpoint_conflict、malicious_content、multi_market；Claim 引用准确率 `1.0`，无依据数值率 `0.0`，schema success `1.0`，safety core passed |
| P4/G4 约束未被绕过 | PASS | Gate G5 继承 Gate G4：legacy `/api/v1/backtest/*` 仍只表示 Signal Evaluation，正式组合回测 API 仍是 `/api/v1/quant/backtest-runs`，P5 报告只能引用已冻结 evidence，不能推广生产回测 |
| P6 入口明确且不提前实现 | PASS | 本 Gate 仅把 `SAL-P6-001` 设为下一步，不实现认证/RBAC、真实 Worker、Provider/LLM runtime、Qlib runtime、生产调度、通知 sender 或发布包 |

## 3. P5 任务核对

| 任务 | 结论 | 核心证据 |
|---|---|---|
| `SAL-P5-001` | DONE | [Evidence / Claim / Report Schema](./evidence-claim-report-schema.md) |
| `SAL-P5-002` | DONE | [Evidence Store](./evidence-store.md) |
| `SAL-P5-003` | DONE | [EvidenceBundle Builder](./evidence-bundle-builder.md) |
| `SAL-P5-004` | DONE | [Source Trust and Unstructured Cleaning](./source-trust-unstructured-cleaning.md) |
| `SAL-P5-005` | DONE | [Quant Evidence Adapter](./quant-evidence-adapter.md) |
| `SAL-P5-006` | DONE | [Prompt and Output Schema Registry](./prompt-output-schema-registry.md) |
| `SAL-P5-007` | DONE | [Agent Stage Persistence](./agent-stage-persistence.md) |
| `SAL-P5-008` | DONE | [Technical Agent Evidence Adapter](./technical-agent-evidence-adapter.md) |
| `SAL-P5-009` | DONE | [Intel Agent Evidence Adapter](./intel-agent-evidence-adapter.md) |
| `SAL-P5-010` | DONE | [Risk/Portfolio Agent Evidence Adapter](./risk-portfolio-agent-evidence-adapter.md) |
| `SAL-P5-011` | DONE | [Decision Agent Counterargument and Final Synthesis](./decision-agent-counterargument-synthesis.md) |
| `SAL-P5-012` | DONE | [Model Routing, Cache and Budget](./model-routing-cache-budget.md) |
| `SAL-P5-013` | DONE | [Citation Validator](./citation-validator.md) |
| `SAL-P5-014` | DONE | [Agent Tool Security](./agent-tool-security.md) |
| `SAL-P5-015` | DONE | [Trusted ResearchReport Renderer](./trusted-research-report-renderer.md) |
| `SAL-P5-016` | DONE | [Research Report Delivery UI And Notification Outbox](./research-report-delivery-ui-outbox.md) |
| `SAL-P5-017` | DONE | [Agent Golden Regression Evaluation](./agent-golden-regression-evaluation.md) |
| `SAL-P5-018` | DONE | 本 Gate G5 评审记录和 [Gate G5 integration test](../tests/gates/test_gate_g5_trusted_research_review.py) |

## 4. 接受风险与后续约束

| 风险/限制 | Gate G5 处理 | 后续关闭条件 |
|---|---|---|
| P5 仍为离线合约和 deterministic stub，不执行真实 Agent/LLM | 接受。Gate G5 证明可信研究链路可审计、可降级、可复现并满足金标阈值，但不证明真实模型质量 | 后续 Worker/Provider/LLM runtime 任务必须在 profile guard、budget/cache、fallback trace、observability 和 replay tests 下单独启用 |
| Notification Outbox 没有 sender | 接受。Outbox metadata、幂等、lease、retry、dead_letter 已通过；发送器属于发布加固/通知 runtime 范围 | 后续通知 sender 必须通过 RBAC、配置、审计、重试和无重复发送验证 |
| 报告 UI 仍是 DSA Web extension patch | 接受。`DSA-PATCH-007` 是 GET-only UI extension，不注册 backend route，不改变上游 Agent/runtime 语义 | 发布前继续复核 patch registry、Web build、权限、安全和上游同步策略 |
| P4 formal backtest evidence 仍是固定合约/fixture 输入 | 接受。Gate G5 只批准可信研究使用已冻结 evidence，不构成生产收益或投资建议 | P6 真实数据回放、容量、稳定性、风控、合规和发布门禁补充生产规模证据 |
| 供应链/Web/Image 高危风险延续 | 接受但继续阻断发布。G0/G1/G2/G3/G4 accepted risks 仍有效 | `SAL-P6-005` 或等效安全/许可证 Gate 修复或正式豁免 |

`RSK-003` Agent 引用/幻觉在离线可信研究 RC 输入边界内关闭：Citation Validator、Agent Tool Security、trusted renderer、delivery UI 和 56-case Agent Golden regression 已共同覆盖错引、无依据数值和恶意内容核心风险。真实 Provider/LLM runtime 质量与成本风险转入 P6 runtime/profile/observability 门禁继续管理。

## 5. 本地评审验证

| 验证 | 结果 |
|---|---|
| Focused Red | `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py -q`：最终 Red 为 `1 failed, 1 passed`，缺少 `docs/gate-g5-trusted-research-review.md`；测试编写期间曾校准 existing GET-only route operation id 为 `getResearchReportPage` |
| Focused Green | `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py -q`：`2 passed in 0.39s` |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py tests/application/test_agent_golden_regression_evaluation.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_model_routing_cache_budget.py tests/application/test_agent_tool_security.py tests/evidence/test_citation_validator.py tests/evidence/test_report_renderer.py tests/application/test_report_delivery_ui.py tests/repositories/test_notification_outbox.py tests/architecture/test_architecture_boundaries.py -q`：`78 passed in 1.02s` |
| Full pytest / compile / lock / patch / tag / diff guards | Full pytest `497 passed, 3 skipped in 4.01s`；compileall PASS；dependency lock guard PASS（`Resolved 298 packages`）；live patched DSA worktree `--check-only` hit expected already-applied context conflict at `0004`，clean temp DSA worktree sequentially applied `0001..0007`；immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；`git diff --check` PASS |
| Gate G5 executable contract | 验证 TrustedResearchReport canonical JSON authority、ResearchReportPage claim/citation/evidence/artifact 展开、Agent Golden 56-case 阈值、Model Routing cache hit 零成本复用、Source Trust malicious instruction 清洗、AgentToolSecurity 对 `shell.run` 默认拒绝、GET-only report routes 和无 sender operation |

## 6. P6 入口约束

P6 第一入口为 `SAL-P6-001` 完善认证与 RBAC。P6 实现必须沿用 P5 已冻结的可信研究边界：

- API/Worker/Provider/LLM/notification sender 启用前必须先有 profile guard、权限、审计、配置、预算、fallback trace 和故障注入证据。
- ResearchReport 的权威数据源继续是 canonical JSON；Markdown/HTML/UI 仅为派生展示。
- 模型输出不能覆盖 deterministic quant/risk facts；引用失败必须降级或删除 Claim。
- Outbox sender、真实 Provider/LLM、Worker loop、Qlib runtime、生产调度和正式组合回测推广都必须等待后续明确任务。
- 任何用户可见报告继续显示数据版本、run/stage/artifact lineage、模型/成本上下文、risk summary 和免责声明。

## 7. 最终判定

`SAL-P5-018` 判定为 `DONE`。Gate G5 通过后，P5 证据化 Agent、报告与成本治理完成度为 `18/18`，项目进入 P6 安全、稳定性与发布加固阶段。下一步唯一推荐入口是 `SAL-P6-001`，先定义 desktop/standalone/team 的身份和权限模型，而不是启动真实 Provider/LLM、Worker loop、Qlib runtime、生产调度、通知 sender 或正式组合回测推广。
