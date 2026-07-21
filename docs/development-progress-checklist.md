# Serenity Alpha Lab 开发进度跟踪清单

> 清单版本：v1.0<br>
> 创建日期：2026-07-18<br>
> 架构基线：[AI 股票研究与量化平台开发方案](./ai-stock-quant-platform-development-plan.md) v2.0<br>
> 上游锁定基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：[开发状态快照](./development-status.md)
> 使用方式：本文件是 MVP 开发的权威执行账本；任务状态、依赖、验收证据和范围变化均在此更新

## 1. 使用规则

### 1.1 状态

| 标记 | 状态 | 使用规则 |
|---|---|---|
| `- [ ] [TODO]` | 未开始 | 依赖可能尚未满足 |
| `- [ ] [READY]` | 可领取 | Definition of Ready 全部满足 |
| `- [ ] [DOING]` | 进行中 | 必须填写负责人和开始日期；每人最多一个主任务 |
| `- [ ] [BLOCKED]` | 阻塞 | 必须填写阻塞原因、责任人和下一次复查日期 |
| `- [ ] [REVIEW]` | 待评审 | 实现完成，等待代码/业务/安全评审 |
| `- [x] [DONE]` | 已完成 | 验收标准全部满足并附证据 |
| `- [ ] [DEFERRED]` | 延后 | 必须记录批准人、原因和目标版本 |
| `- [ ] [CANCELLED]` | 取消 | 必须记录替代方案或范围决策 |

只勾选 checkbox 而不更新状态标签不算完成。`DONE` 任务不得直接退回 `DOING`；发现问题应创建缺陷任务并建立关联。

### 1.2 角色缩写

| 缩写 | 角色 |
|---|---|
| TL | Tech Lead / 后端负责人 |
| BE | 后端工程师 |
| QE | Quant Engineer |
| FE | Frontend Engineer |
| AI | AI / Full-stack Engineer |
| RE | 投研验收人 |
| SEC | 安全/合规评审人，可由 TL 兼职但必须独立复核高风险项 |

### 1.3 估算与更新

- 估算单位为理想人日 `d`，不含排队时间；超过 3d 的任务应继续拆分。
- 每日更新 `TODO/READY/DOING/BLOCKED/REVIEW/DONE`，每周更新阶段完成率和风险。
- 每项任务在“实际”字段记录实际人日；偏差超过 50% 时在周报解释。
- 新任务使用对应 Phase 的下一个编号，禁止复用或重排已有 ID。
- 依赖变更、验收标准变更和范围删除必须留下日期、原因和批准人。

### 1.4 Definition of Ready

任务进入 `READY` 前必须满足：

- 目标、非目标和用户/系统价值明确。
- 上游依赖已完成或有可用 Stub。
- API、Schema、数据口径或 UX 草案已评审。
- 测试方法、验收证据和回滚方式明确。
- 新依赖已完成许可证、漏洞和维护状态初审。
- 估算不超过 3d；否则已拆分。

### 1.5 全局 Definition of Done

- 实现、迁移、配置和错误路径完成，不只有 happy path。
- 单元/性质/契约/集成/E2E 按风险覆盖，CI 通过。
- 现有 DSA Characterization、OpenAPI 和报告 fixture 无非预期退化。
- 日志、指标、Trace、错误码和用户可理解的失败信息齐全。
- 安全、数据质量、权限、成本和许可证影响已评审。
- 文档、ADR、变更日志、Runbook 和第三方登记同步更新。
- PR 已评审并合入 `main`；验收证据链接到 commit、CI Run、截图或 Artifact。
- 无未处理的 Critical/High；已接受风险有负责人和到期日。

## 2. 总进度看板

> 初始状态全部为 TODO。完成任务后同步更新本表；任务数量由本文件中的稳定 ID 统计。

| Phase | 目标周 | 状态 | 完成/总数 | Gate | 关键输出 |
|---|---:|---|---:|---|---|
| P0 上游接管 | 1 | DONE | 13/13 | G0 PASS | DSA 可重复基线、金标、SBOM |
| P1 工程加固 | 2~3 | DONE | 16/16 | G1 PASS | Lock、领域协议、迁移、兼容外壳 |
| P2 数据与任务 | 3~6 | DOING | 5/20 | G2 | PIT Dataset、Provider 收口、持久任务 |
| P3 筛选与因子 | 6~9 | TODO | 0/17 | G3 | AlphaSift、Factor、Screen Lab |
| P4 回测与风控 | 9~13 | TODO | 0/22 | G4 | Qlib、Ledger、正式回测、Quant Lab |
| P5 Agent 与报告 | 13~16 | TODO | 0/18 | G5 | Evidence、引用、预算、可信报告 |
| P6 发布加固 | 16~18 | TODO | 0/23 | G6 | RC、稳定性、安全、发布与 Runbook |
| **合计** | **16~18 周** | **DOING** | **34/129** |  |  |

容量基线：128 个有数值估算的任务共约 268.5 理想人日，另有 10 个交易日稳定观察。4 人团队按 75%~85% 有效容量约需 16~18 周；5 人团队可争取 13~15 周。任何更短承诺都必须明确减少 MVP 范围或增加人员，不能压缩数据正确性、回测真实性、安全和 Gate。

关键路径：

```text
P0 基线
 -> P1 领域协议/迁移/TaskBackend
 -> P2 Dataset Catalog/PIT/持久任务
 -> P3 Screen/Factor
 -> P4 Backtest/Risk
 -> P5 Evidence/Report
 -> P6 RC/稳定运行
```

允许并行：

- P1 依赖锁与领域协议可以并行，但合并前必须统一项目结构。
- P2 Provider/Data 与 Persistent TaskBackend 可以并行。
- P3 AlphaSift Adapter、Factor Engine、Screen Lab 可以在契约冻结后并行。
- P4 Qlib Adapter、Ledger/Risk、Quant Lab 可以在 BacktestSpec 冻结后并行。
- P5 Agent Stage、Citation Validator、报告 UI 可以在 Evidence Schema 冻结后并行。

## 3. Phase 0：DSA 上游接管与行为基线

### SAL-P0-001 锁定候选上游基线

- [x] [DONE] 选择 DSA release/commit 并记录选择依据
- 元数据：优先级 P0 | 负责人 TL | 估算 0.5d | 实际 0.5d | 依赖 - | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：候选版本评估、commit SHA、发布日期、已知问题、选择/放弃理由。
- 验收：
  - 比较最新稳定 release 与目标 main commit 的测试、修复和兼容风险。
  - 由 TL 批准唯一候选基线；未经 Gate 不再漂移。
- 结果：锁定 `ZhuLinsen/daily_stock_analysis v3.26.1`，commit `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`，release 发布时间 `2026-07-12T10:57:39Z`。
- 放弃候选：`main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa` 比 release 多 2 个 commit、19 个文件变更，涉及未发布 DecisionSignal API/Web/服务语义扩展，登记为后续同步候选。
- 验收证据：见 [DSA 上游基线选择记录](./upstream-baseline-selection.md)；已记录 release/main SHA、GitHub release/compare/actions 验证、已知风险与后续处理。

### SAL-P0-002 导入 DSA Git 历史

- [x] [DONE] 在当前仓库保留 DSA 历史并配置 `origin/upstream`
- 元数据：优先级 P0 | 负责人 TL | 估算 1d | 实际 0.5d | 依赖 SAL-P0-001 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：上游历史、不可变基线标签、remote 配置说明。
- 验收：
  - `upstream` 指向官方 DSA，`origin` 指向本项目。
  - 基线 tag 可解析到锁定 SHA；当前 docs 不丢失。
  - 无压平复制或来源不明的大批文件。
- 结果：已配置 `upstream` remote 指向 `https://github.com/ZhuLinsen/daily_stock_analysis.git`，通过显式 refspec 导入上游 heads/tags，并创建本地基线 tag `upstream/dsa-v3.26.1` 指向 `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。
- 说明：早期会话开始时仓库未配置 `origin` 且无本项目托管 URL；当前已配置 `origin` 指向 `git@github.com:zcxGGmu/serenity-alpha-lab.git`，仍需在后续同步/PR 前复验 `origin/upstream` 双 remote 约束。
- 验收证据：见 [DSA Git 历史导入记录](./upstream-history-import.md)；已记录 remote、tag、SHA、`git fsck` 与工作树状态验证。

### SAL-P0-003 固化基线运行环境

- [x] [DONE] 记录并自动化 Python、Node、OS 和系统依赖
- 元数据：优先级 P0 | 负责人 BE | 估算 1d | 实际 0.5d | 依赖 SAL-P0-002 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：环境矩阵、Bootstrap 命令、依赖缓存策略。
- 验收：
  - Windows、Linux/Docker 至少各有一个受支持环境。
  - 新机器按文档可安装，不依赖开发者全局包。
- 结果：已建立 [DSA 基线运行环境记录](./dsa-baseline-environment.md)，明确 Windows、Linux/CI、Docker 和 Desktop Profile 的 Python/Node/OS/系统依赖；新增 Windows PowerShell 与 Linux/Git Bash bootstrap 脚本，通过本地 tag 物化隔离 worktree，并使用 `.cache/dsa-p0` 缓存依赖。
- 说明：本任务只固化环境入口和安装路径，不宣称后端测试、Web 构建或 Docker 运行通过；这些由 `SAL-P0-004`、`SAL-P0-005`、`SAL-P0-007` 分别验收。
- 验收证据：见 [DSA 基线运行环境记录](./dsa-baseline-environment.md)；已记录上游依赖来源、bootstrap 命令、缓存策略、脚本解析和 worktree 校验。

### SAL-P0-004 建立后端离线测试基线

- [x] [DONE] 原样执行 DSA backend-gate 和离线测试
- 元数据：优先级 P0 | 负责人 BE | 估算 1d | 实际 0.5d | 依赖 SAL-P0-003 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：测试数量、耗时、失败清单、Junit/coverage Artifact。
- 验收：
  - 所有稳定测试通过；不稳定/环境相关测试被分类而非直接跳过。
  - 记录基线约 226 个测试文件对应的实际测试用例数。
- 结果：新增可复跑 wrapper `scripts/run-dsa-backend-offline-baseline.sh`，在锁定 worktree 中运行 syntax、flake8、deterministic、collect 和 offline-tests；所有 phase exit 0。collect 阶段收集 `4455/4459` 个测试（4 个 deselected），offline-tests 最终 `4455 passed, 4 deselected, 48 warnings, 416 subtests passed in 142.10s`。
- 上游补丁：首轮 full gate 暴露 `IntelligenceService` 共享可变 `_DISABLE_REQUEST_PROXIES` 导致的顺序依赖失败；已新增 Characterization Test 和最小本地补丁 `DSA-PATCH-001`，由 `scripts/apply-dsa-baseline-patches.sh` 幂等应用，登记见 [DSA 上游补丁登记](./upstream-patches.md)。
- 验收证据：见 [DSA 后端离线测试基线记录](./backend-offline-test-baseline.md)；phase logs、环境、测试 inventory 和 summary 保存在 `.cache/dsa-p0/backend-offline-artifacts/`。

### SAL-P0-005 建立 Web 测试与构建基线

- [x] [DONE] 执行 DSA Web lint、test、build 和 Smoke
- 元数据：优先级 P0 | 负责人 FE | 估算 1d | 实际 1d | 依赖 SAL-P0-003 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：构建日志、bundle 摘要、关键页面截图、已知 warning。
- 验收：
  - `npm ci`、lint、Vitest、Vite build 通过。
  - Playwright 至少覆盖启动、登录/初始化、分析页和历史页。
- 结果：`npm ci`、`npm run lint`、`npm run build`、`npm run test` 和真实 Playwright smoke 已通过；`npm ci` 安装 461 个 packages，audit 摘要仍为 16 个漏洞（1 low、5 moderate、10 high）；Vite build 生成 `../../static/` 产物，3229 modules transformed。
- 本地补丁：通过 `DSA-PATCH-002` 修正 Alert market region 测试契约；通过 `DSA-PATCH-003` 对齐 Web smoke E2E 与当前 UI/fixture 契约；两个补丁均由 `scripts/apply-dsa-baseline-patches.sh` 幂等应用。
- Smoke：新增 `scripts/seed-dsa-web-smoke-fixture.sh` 生成本地 auth/env/SQLite 历史报告 fixture；`npm run test:smoke -- --reporter=line` 真实执行 13 个 Playwright tests，最终 `13 passed`，无 skipped。
- 限制：本任务不修复 npm audit high 漏洞，不运行 `npm audit fix`，不提交 `.worktrees`、`node_modules`、`static`、`.cache`、Playwright `test-results`、截图或 trace。
- 验收证据：见 [DSA Web 测试与构建基线记录](./web-baseline-test-build.md) 和 [DSA 上游补丁登记](./upstream-patches.md)。

### SAL-P0-006 建立 Desktop、CLI 与 Bot Smoke 基线

- [x] [DONE] 固定桌面端、CLI 和至少一个 Bot 的主路径
- 元数据：优先级 P1 | 负责人 FE/AI | 估算 1d | 实际 0.5d | 依赖 SAL-P0-003 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：可自动化 Smoke、人工验收记录、平台限制。
- 验收：
  - Desktop 可启动并连接本地 API。
  - CLI 可执行一次 Stub 分析；Bot 命令使用离线 Stub 返回。
- 结果：已在锁定 DSA worktree 中完成 Desktop、CLI、本地 API 和 Bot 命令层离线 smoke。Desktop `npm ci` 安装 332 个 packages，`npm test` 47/47 通过；Desktop packaging/installer 测试 6/6 通过；API health 测试 7/7 通过；CLI local backend 测试 77/77 通过；Bot status/dispatcher 测试 25/25 通过；Bot market command 测试 6/6 通过。
- 限制：本任务未执行真实 GUI 人工验收、真实 Bot 平台 webhook、真实 LLM 调用或真实通知发送；这些不属于 P0 smoke 的离线 Stub 范围。Desktop `npm ci` 暴露 9 个漏洞（1 moderate、8 high），不在 P0 中运行 `npm audit fix` 改写上游 lockfile。
- 验收证据：见 [DSA Desktop、CLI 与 Bot Smoke 基线记录](./desktop-cli-bot-smoke-baseline.md)。

### SAL-P0-007 建立 Docker 基线

- [x] [DONE] 构建并运行 DSA analyzer/server Docker Profile
- 元数据：优先级 P0 | 负责人 BE | 估算 1d | 实际 0.5d | 依赖 SAL-P0-003 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：镜像 digest、Compose 启动日志、健康检查。
- 验收：
  - 构建不使用宿主机隐式依赖。
  - server/analyzer 可分别启动，挂载数据在重启后保留。
- 结果：已新增 `scripts/run-dsa-docker-baseline.sh`，通过临时 Docker build context 注入缓存 AlphaSift wheel，避免 Docker build 阶段动态 Git clone 失败；镜像 `serenity-dsa-p0:sal-p0-007` 构建通过，digest 为 `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`。
- Smoke：server profile `/api/health` 返回 `{"status":"ok"}`，容器状态为 `healthy`，analyzer import smoke 返回 `ok-analyzer`。
- 限制：本任务不证明真实 Provider、真实 LLM、真实计划任务或完整分析流程；不生成 Python SBOM、镜像 SBOM 或漏洞报告，这些仍属于 `SAL-P0-011`。
- 验收证据：见 [DSA Docker 基线记录](./docker-baseline.md)。

### SAL-P0-008 冻结 API 与配置契约

- [x] [DONE] 保存 OpenAPI、环境变量和配置 Schema 基线
- 元数据：优先级 P0 | 负责人 BE | 估算 1d | 实际 0.5d | 依赖 SAL-P0-004 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：OpenAPI snapshot、配置字段表、默认值/敏感级别。
- 验收：
  - CI 可检测非预期 API 破坏。
  - 密钥字段、运行时可变字段和废弃字段已标记。
- 结果：新增 `scripts/run-dsa-api-config-baseline.sh`，在锁定 DSA worktree 上应用 `DSA-PATCH-001` 至 `DSA-PATCH-003` 后生成并校验运行时 OpenAPI、Web 设置配置 Schema、环境变量/配置字段 inventory 和摘要哈希；快照提交在 `docs/baselines/dsa-v3.26.1/api-config/`。
- 摘要：OpenAPI `3.1.0` 含 105 paths、119 operations、186 component schemas、1 security scheme；配置 Schema `2026-06-29-claude-code-cli-backend` 含 8 categories、179 registered fields；环境变量/config inventory 含 386 fields，其中 secret 81、server-masked 5、runtime mutable 187、runtime hidden 10、deprecated 4、dynamic pattern 9。
- 限制：上游 `docs/architecture/api_spec.json` 已滞后于当前运行时 FastAPI 生成结果，本项目 P0 以 `create_app().openapi()` 运行时输出作为冻结源；本任务不变更 API/配置行为，不启动真实 Provider、Scheduler、LLM 或 Bot。
- 验收证据：见 [DSA API 与配置契约基线记录](./api-config-contract-baseline.md)；契约快照见 [API/config baseline](./baselines/dsa-v3.26.1/api-config/summary.json)。

### SAL-P0-009 冻结数据库 Schema 与迁移样本

- [x] [DONE] 生成 DSA SQLite Schema 基线和脱敏历史库 fixture
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P0-004 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：Schema dump、表/索引清单、小型历史库、内容哈希。
- 验收：
  - fixture 覆盖分析、信号评价、持仓、会话、LLM usage。
  - fixture 无密钥和个人数据，可用于 CI。
- 结果：新增 `scripts/run-dsa-database-baseline.sh`，在锁定 DSA worktree 上应用 `DSA-PATCH-001` 至 `DSA-PATCH-003` 后，生成并校验 SQLite Schema、表/索引/外键元数据、稳定 SQL fixture、内容哈希与摘要快照；脚本会恢复 `fixture.sql`、执行 `PRAGMA foreign_key_check`，并比较恢复前后行数与内容哈希；提交快照位于 `docs/baselines/dsa-v3.26.1/database/`。
- 摘要：DSA SQLite 基线含 28 张业务表、177 个索引；脱敏 fixture 含 31 行合成数据，覆盖 `analysis_history`、`backtest_results`/`backtest_summaries`、`decision_signals`/outcome/feedback、portfolio、conversation/session、Agent provider trace、`llm_usage` 和 `schema_migrations`。
- 限制：DSA `v3.26.1` 的管理员认证密码、盐和 signed-cookie session 不在 SQLite 中持久化，fixture 不包含 auth secret；运行时 `fixture.sqlite` 只生成在 `.cache/dsa-p0/database-baseline-artifacts/generated/`，提交快照使用稳定 SQL/JSON，因为 SQLite 二进制页/header 字节在同内容重建时不稳定。
- 验收证据：见 [DSA 数据库 Schema 与迁移样本基线记录](./database-schema-baseline.md)；快照见 [database baseline summary](./baselines/dsa-v3.26.1/database/summary.json)。

### SAL-P0-010 冻结报告与信号评价金标

- [x] [DONE] 保存结构化报告、Markdown 和 Signal Evaluation 金标
- 元数据：优先级 P0 | 负责人 AI/QE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P0-004 | 开始 2026-07-19 | 完成 2026-07-20
- 交付物：固定输入、Stub LLM 输出、报告 fixture、评价结果。
- 验收：
  - 单股报告、聚合报告、市场复盘至少各一个。
  - DSA 现有 Backtest 关键指标有可比较的金标。
- 结果：新增 `scripts/run-dsa-report-signal-baseline.sh`，在锁定 DSA worktree 上应用 `DSA-PATCH-001` 至 `DSA-PATCH-003` 后，以离线 Stub LLM、固定时钟和合成行情输入生成结构化报告、单股/聚合/市场复盘 Markdown、DecisionSignal 摘要和 Signal Evaluation 金标；默认模式与 `docs/baselines/dsa-v3.26.1/report-signal/` 做 byte-for-byte diff。
- 摘要：提交 12 个快照文件；结构化报告 2 个，Markdown 报告 3 个，Signal Evaluation cases 6 个；`total_evaluations=6`、`completed_count=5`、`insufficient_count=1`、`direction_accuracy_pct=60.0`、`win_rate_pct=60.0`。
- 限制：本任务不触发真实 Provider、真实 LLM、Scheduler、Bot/Webhook 或真实通知发送；不把 Signal Evaluation 解释为正式组合回测。
- 验收证据：见 [DSA 报告与信号评价金标基线记录](./report-signal-golden-baseline.md)；快照见 [report/signal baseline summary](./baselines/dsa-v3.26.1/report-signal/summary.json)。

### SAL-P0-011 建立供应链基线

- [x] [DONE] 生成 SBOM、许可证、漏洞和动态依赖报告
- 元数据：优先级 P0 | 负责人 SEC | 估算 1d | 实际 1d | 依赖 SAL-P0-003 | 开始 2026-07-19 | 完成 2026-07-19
- 交付物：Python/Node/镜像 SBOM、第三方许可证、漏洞清单。
- 验收：
  - 标记 AlphaSift `git+https` 动态安装、OpenBB/AGPL 和数据服务条款风险。
  - Critical/High 有处理人、计划和截止时间。
- 结果：新增 `scripts/run-dsa-supply-chain-baseline.sh`，生成 Python CycloneDX SBOM（146 components）、Web npm audit（16 vulnerabilities / 10 high / 0 critical）、Web lockfile license inventory（529 packages / 0 UNKNOWN）、Syft image CycloneDX SBOM（7865 components）和 Grype image vulnerability report（933 matches / 39 critical / 84 high）。
- 风险处理计划：Python `setuptools` 漏洞、AlphaSift 非 PyPI 审计缺口、Web npm High、镜像 Critical/High、Python UNKNOWN licenses 与 Node 非主流许可证均已指定 BE/FE/SEC owner、计划和截止任务。
- 验收证据：见 [DSA 供应链基线记录](./supply-chain-baseline.md)；生成 artifact 位于 `.cache/dsa-p0/supply-chain-artifacts/`。

### SAL-P0-012 建立上游维护文档和 CI

- [x] [DONE] 创建 `UPSTREAM_BASE.md`、补丁登记和基线 CI
- 元数据：优先级 P0 | 负责人 TL | 估算 1d | 实际 0.5d | 依赖 SAL-P0-002,SAL-P0-004,SAL-P0-005,SAL-P0-011 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：上游基线文档、patch 分类、CI required checks。
- 验收：
  - 每个本地偏离可归为 compatible/extension/divergence。
  - PR 默认运行后端、Web、Docker 和供应链基线检查。
- 结果：新增根目录 `UPSTREAM_BASE.md`，明确 DSA `v3.26.1` 不可变基线、双 remote、隔离 worktree/cache、上游同步流程、本地偏离分类和 required check 名称；更新 `docs/upstream-patches.md`，将 `DSA-PATCH-001` 至 `DSA-PATCH-003` 归类为 `compatible`，当前无 `divergence`。
- CI：新增 `.github/workflows/p0-required-baselines.yml`，在 PR 和手动触发时运行 `p0-backend-offline-baseline`、`p0-web-baseline`、`p0-contract-and-golden-baselines`、`p0-docker-and-supply-chain-baseline` 四个 required check 候选，覆盖后端、Web、Docker、供应链、API/config、database 和 report/signal baseline。
- 验收证据：见 [UPSTREAM_BASE](../UPSTREAM_BASE.md) 和 [P0 required baselines workflow](../.github/workflows/p0-required-baselines.yml)；本地验证已通过 YAML 解析、引用脚本存在性、baseline scripts `bash -n`、分类/required check 扫描和 `git diff --check`。

### SAL-P0-013 Gate G0：基线接管评审

- [x] [DONE] 决定是否正式采用 DSA 主干
- 元数据：优先级 P0 | 负责人 TL/RE/SEC | 估算 0.5d | 实际 0.5d | 依赖 SAL-P0-001..012 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：Go/No-Go 记录、已知风险、Phase 1 范围。
- 验收：
  - 测试、构建、许可证、上游同步和目标环境均有证据。
  - No-Go 时记录替代方案；Go 后基线变更必须走 ADR。
- 结果：Gate G0 评审结论为 `GO with accepted risks`。Serenity Alpha Lab 正式采用 DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` 作为 P1 工程加固接管基线；P1 入口为 `SAL-P1-001`，先完成上游与模块化 ADR。
- 接受风险：`RSK-006`、`RSK-008`、`RSK-010`、`RSK-011`、`RSK-012` 均已定责并保留后续关闭任务；这些风险不阻断 P1 开始，但继续阻断发布或未评审的上游漂移。
- 验收证据：见 [Gate G0 基线接管评审](./gate-g0-baseline-review.md)；本次轻量验证覆盖 baseline tag/worktree、patch registry、CI workflow YAML、API/config、database、report/signal 摘要断言和状态一致性扫描。

## 4. Phase 1：工程加固与兼容外壳

### SAL-P1-001 批准上游与模块化 ADR

- [x] [DONE] 完成 ADR-001/002 及 Compatibility Facade 决策
- 元数据：优先级 P0 | 负责人 TL | 估算 1d | 实际 0.5d | 依赖 SAL-P0-013 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：上游同步、模块化边界、删除旧路径条件。
- 验收：ADR 包含选项、取舍、后果、回滚和复审日期。
- 结果：新增 ADR-001 和 ADR-002，正式批准受控上游同步策略、不可变 tag 策略、补丁分类、上游候选 commit 处理、渐进式模块化、Compatibility Facade 范围、服务拆分条件、旧路径删除条件、回滚和 Gate G1/2026-08-03 复审要求。
- 上游候选处理：`55946536` 判定为低风险文档候选，不在当前 P1 基线 cherry-pick；`487e49e5` 判定为延期吸收，必须通过 `sync/dsa-487e49e5` 分支、OpenAPI/DecisionSignal/Web/report-signal 影响评审和相关基线刷新后才能推广。
- 验收证据：见 [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) 与 [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md)；本任务未移动 `upstream/dsa-v3.26.1`，未合入 DSA runtime source，未启动 Quant Core、PIT Dataset 或正式回测。

### SAL-P1-002 标准化 Python 项目元数据

- [x] [DONE] 把依赖声明迁入标准 `pyproject.toml`
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-001 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：project metadata、Python 版本、entry points、build backend。
- 验收：
  - DSA CLI/API/Worker/测试入口可安装运行。
  - 原有 requirements 与新声明差异有审查记录。
- 结果：新增根 `pyproject.toml`，以 PEP 621 声明 `serenity-alpha-lab` 项目元数据、Python `>=3.11,<3.13`、`setuptools.build_meta` 构建后端、DSA `v3.26.1` runtime 依赖安装面、pytest/black/isort/ruff/bandit 工具配置，以及 `serenity-alpha-lab`、`serenity-dsa-cli`、`serenity-dsa-api`、`serenity-dsa-worker`、`serenity-dsa-tests` console scripts。
- 依赖审查：新增 [Python 项目元数据审查](./python-project-metadata.md)，记录从 DSA `requirements.txt`、`pyproject.toml`、`setup.cfg` 迁移的内容、差异和 `SAL-P1-003` 延后项；`SAL-P1-003` 后已由 extras/lock 关闭 Serenity root 生产依赖中的动态 Git 安装。
- 验收证据：`tests/architecture/test_project_metadata.py`；`.cache/dsa-p0/venv/bin/python -m pytest tests/architecture -q` 得到 `7 passed`；`.cache/dsa-p0/venv/bin/python -m pip install -e . --no-deps` 成功；`SERENITY_DSA_DRY_RUN=1` 下四个 DSA entry points 均返回 exit 0。

### SAL-P1-003 建立依赖 Extras 与锁文件

- [x] [DONE] 划分 core/providers/desktop/quant/dev 并生成 `uv.lock`
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-002 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：extras、lock、由 lock 导出的兼容 requirements。
- 验收：
  - CI 校验 requirements 不可手工漂移。
  - Desktop 不强制安装 Qlib；生产构建无动态 Git 安装。
- 结果：`pyproject.toml` 已拆分 `core`、`providers`、`desktop`、`quant`、`dev` extras；`uv.lock` 成为权威锁；根 `requirements.txt` 由 `scripts/verify-python-dependency-lock.sh` 导出 `core+providers+desktop` 生产/桌面兼容安装面。
- 依赖边界：`quant` extra 包含 `polars`、`pyarrow`、`duckdb` 和可选 `pyqlib`，但导出的 `requirements.txt` 不包含 `pyqlib`；Serenity root 依赖声明和生产 requirements 不再包含 `git+https` 或 AlphaSift Git URL。AlphaSift 审查后 wheel/package intake 延后至 AlphaSift Adapter 任务，不提交 P0 cache wheel。
- 验收证据：见 [Python 依赖 Extras 与锁文件记录](./python-dependency-lock.md)；`tests/architecture/test_dependency_locking.py`；`scripts/verify-python-dependency-lock.sh` 通过；`.cache/dsa-p0/venv/bin/python -m pytest tests/architecture -q` 得到 `11 passed`；完整 `.cache/dsa-p0/venv/bin/python -m pytest -q` 得到 `15 passed`。

### SAL-P1-004 建立目标包骨架和架构测试

- [x] [DONE] 创建 domain/application/quant/datasets/evidence/integrations 边界
- 元数据：优先级 P0 | 负责人 TL/BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-001 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：包骨架、依赖规则、架构测试。
- 验收：
  - domain 不导入 FastAPI、SQLAlchemy、Pandas、Qlib、LiteLLM。
  - 禁止 quant -> agent/notification、provider -> repository。
- 结果：新增 `src/serenity_alpha_lab/` 目标包骨架，包含 `domain`、`application`、`quant`（`factors`/`screening`/`backtest`/`portfolio`/`risk`）、`datasets`、`evidence`、`integrations`（`dsa`/`data`）、`repositories` 和 `services`；只建立边界和 DSA entry-point compatibility wrapper，未实现 Quant Core、PIT Dataset、正式回测或大规模 DSA runtime source 迁移。
- 架构测试：新增 `tests/architecture/test_architecture_boundaries.py`，通过 AST 检查 `domain` 不导入 FastAPI/SQLAlchemy/Pandas/Qlib/LiteLLM/AKShare 等框架或集成模块，`quant` 不依赖 agent/notification，`integrations` 不直接依赖 repositories。
- 验收证据：`.cache/dsa-p0/venv/bin/python -m pytest tests/architecture -q` 得到 `7 passed`；`.cache/dsa-p0/venv/bin/python -m py_compile $(find src/serenity_alpha_lab tests/architecture -name '*.py' | sort)` 通过；`git diff --check` 通过。

### SAL-P1-005 实现统一 InstrumentId

- [x] [DONE] 定义证券 ID、市场、资产类型和 Provider Symbol Mapping
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-004 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：值对象、解析/格式化、旧代码兼容适配器、测试。
- 验收：
  - A/港/美/日/韩/台典型代码往返无歧义。
  - 裸 6 位代码只在明确市场上下文中接受。
- 结果：新增 `src/serenity_alpha_lab/domain/instruments.py`，定义纯领域 `InstrumentId`、`Market`、`Exchange`、`AssetType`、`ProviderSymbolMapping` 和明确错误类型；canonical 格式为 `<symbol>.<exchange>`，覆盖 A 股、港股、美股、日股、韩股和台股典型代码。
- 兼容映射：`InstrumentId.from_legacy()` 支持 DSA/Yahoo 常见格式，包括 `SH600519`、`600519.SH`、`HK00700`、`0700.HK`、`AAPL` with `market=us`、`7203.T`、`005930.KS`、`035720.KQ`、`2330.TW` 和 `6505.TWO`；`to_provider_symbol("yahoo")` 与 `to_dsa_symbol()` 提供 Provider/旧代码输出。
- 范围限制：本任务未迁移 DSA `normalize_stock_code` 调用点，未实现 Provider、Dataset、PIT 数据、Quant Core、正式回测或大规模 DSA runtime source 迁移。
- 验收证据：见 [InstrumentId 统一证券 ID 领域模型记录](./instrument-id-domain-model.md)；`tests/domain/test_instrument_id.py`；Red 测试先因缺少模块失败，Green 后 `tests/domain/test_instrument_id.py` 得到 `37 passed`，`tests/architecture tests/domain` 得到 `52 passed`。

### SAL-P1-006 实现 Run/Stage/Event 领域模型

- [x] [DONE] 定义运行、阶段、事件、状态转换和幂等规则
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-004 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：领域模型、状态机、错误码、性质测试。
- 验收：
  - 非法终态回退被拒绝。
  - retry 创建新 attempt，事件 ID 单调且只追加。
- 结果：新增 `src/serenity_alpha_lab/domain/run_lifecycle.py`，提供纯领域 `Run`、`Stage`、`RunEvent`、`RunStatus`、`StageStatus`、`EventKind`、`InvalidTransition` 和 `IdempotencyConflict`；事件按 run 内 sequence 单调递增且只追加；终态 run 拒绝回退；retry 显式创建新 run attempt 并保留 parent/idempotency 关系。
- 范围限制：本任务不实现 ArtifactStore、TaskBackend、持久化、Trace middleware、Quant Core、PIT Dataset 或正式回测。
- 验收证据：见 [Run / Stage / Event 领域模型记录](./run-stage-event-domain-model.md)；`tests/domain/test_run_lifecycle.py`；`.cache/dsa-p0/venv/bin/python -m pytest tests/domain -q` 得到 `4 passed`；架构测试继续确认 domain 不导入框架或基础设施。

### SAL-P1-007 实现 Artifact 模型与本地存储

- [x] [DONE] 定义内容寻址 URI、Manifest、哈希和原子发布
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-006 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：ArtifactStore Protocol、本地实现、临时文件清理。
- 验收：
  - 写入失败不产生已发布记录。
  - 哈希、Schema、大小、生产 Run 和保留等级可查询。
- 结果：新增 `src/serenity_alpha_lab/domain/artifacts.py`，定义 `ArtifactUri`、`ArtifactManifest`、`ArtifactRetentionTier`、`ArtifactStore` Protocol 和错误类型；新增 `src/serenity_alpha_lab/repositories/local_artifact_store.py`，以 SHA-256 blob 和 JSON manifest 作为本地内容寻址存储，manifest-last 发布并清理失败写入。
- 范围限制：本任务不实现 Evidence Agent、Dataset Catalog、对象存储、数据库迁移、Provider、Quant Core、PIT Dataset、正式回测或 API endpoint。
- 验收证据：见 [Artifact 模型与本地存储记录](./artifact-store-domain-model.md)；`tests/domain/test_artifacts.py`；`tests/repositories/test_local_artifact_store.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `6 passed`，`tests/architecture tests/domain tests/repositories` 得到 `58 passed`。

### SAL-P1-008 抽取 TaskBackend

- [x] [DONE] 用 Protocol 隔离 DSA `AnalysisTaskQueue`
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-006 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：TaskBackend、InMemory 实现、兼容 Facade。
- 验收：
  - 现有 API 不直接导入 ThreadPoolExecutor。
  - submit/get/cancel/subscribe 跑统一 Contract Test。
- 结果：新增 `src/serenity_alpha_lab/application/task_backend.py`，定义 `TaskCommand`、`TaskRef`、`TaskSnapshot`、`TaskEvent`、`TaskBackend` Protocol、状态/错误类型和 `InMemoryTaskBackend`；新增 `src/serenity_alpha_lab/integrations/dsa/task_backend.py`，以注入式 queue + handler registry 包裹 DSA `submit_background_task()` / `get_task()` / flow events。
- 范围限制：本任务不复制或迁移 DSA `task_queue.py`，不实现持久队列、Celery/Redis/PostgreSQL、Worker runtime、API endpoint、Quant Core、PIT Dataset 或正式回测。
- 验收证据：见 [TaskBackend 协议与 DSA 兼容 Facade 记录](./task-backend-facade.md)；`tests/application/test_task_backend_contract.py`；`tests/integrations/test_dsa_task_backend_facade.py`；`tests/architecture/test_architecture_boundaries.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `12 passed`。

### SAL-P1-009 抽取 ResearchOrchestrator

- [x] [DONE] 为 DSA AgentOrchestrator 建立稳定协议和兼容包装
- 元数据：优先级 P1 | 负责人 AI | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-004 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：输入/输出协议、现有实现 Adapter、Characterization。
- 验收：
  - 现有 Agent API/报告结果不变。
  - Application 层不依赖具体 Agent 类。
- 结果：新增 `src/serenity_alpha_lab/application/research_orchestrator.py`，定义 `ResearchRequest`、`ResearchChatRequest`、`ResearchResult`、`ResearchOrchestrator` Protocol、进度回调和错误类型；新增 `src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py`，以注入式 DSA-like orchestrator 包裹 `run()` / `chat()` 并保留 legacy `AgentResult` 字段语义。
- 范围限制：本任务不修改 DSA API route，不复制 DSA Agent runtime source，不实现 Agent checkpoint、Evidence Agent、Provider/LLM 调用、Quant Core、PIT Dataset 或正式回测。
- 验收证据：见 [ResearchOrchestrator 协议与 DSA 兼容 Facade 记录](./research-orchestrator-facade.md)；`tests/application/test_research_orchestrator_contract.py`；`tests/integrations/test_dsa_research_orchestrator_facade.py`；`tests/architecture/test_architecture_boundaries.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `16 passed`；相关 application/integrations/architecture 套件 `43 passed`，全量 pytest `90 passed`。

### SAL-P1-010 统一 API 错误协议

- [x] [DONE] 引入 `application/problem+json` 和稳定错误码
- 元数据：优先级 P1 | 负责人 BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-004 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：异常映射、中间件、OpenAPI 示例、前端解析。
- 验收：
  - validation/not-found/conflict/provider/internal 可区分。
  - 响应不泄露堆栈、路径或密钥。
- 结果：新增 `src/serenity_alpha_lab/application/api_errors.py`，定义 `ApiErrorCode`、`ProblemDetail`、`ApiProblemError` 常用子类、`problem_from_exception()`、`problem_response_body()`、自由文本脱敏和框架无关 `ProblemDetailsMiddleware`；应用层导出稳定 problem symbols。
- 范围限制：本任务不改写 DSA API route、不刷新 OpenAPI baseline、不实现前端解析、不启动 Provider/LLM、Alembic、PIT Dataset、Quant Core 或正式回测。
- 验收证据：见 [API 错误协议记录](./api-error-protocol.md)；`tests/application/test_api_errors.py`；`tests/architecture/test_architecture_boundaries.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `5 passed`；相关 application/architecture 套件 `41 passed`，全量 pytest `95 passed`。

### SAL-P1-011 统一结构化日志与 Trace

- [x] [DONE] 传播 `trace_id/run_id/stage_id`
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 0.5d | 依赖 SAL-P1-006 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：日志 Schema、middleware、上下文传播、脱敏过滤器。
- 验收：
  - API 到内存任务和 Agent 的同一运行可关联。
  - 密钥、完整 Prompt 和私有正文不进入日志。
- 结果：新增 `src/serenity_alpha_lab/application/tracing.py`，定义 `TraceContext`、ContextVar 传播、`TraceContextFilter`、`StructuredLogFormatter`、框架无关 `TraceContextMiddleware` 和递归脱敏函数。
- 范围限制：本任务不接入 OpenTelemetry exporter、Prometheus/Grafana、Provider/Qlib/LLM instrumentation、Agent orchestration、API route rewrite、Quant Core、PIT Dataset 或正式回测。
- 验收证据：见 [结构化日志与 Trace 记录](./structured-trace-logging.md)；`tests/application/test_trace_context.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `4 passed`。

### SAL-P1-012 接入 Alembic

- [x] [DONE] 让 Alembic 成为唯一 Schema 迁移入口
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 0.5d | 依赖 SAL-P0-009 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：baseline revision、迁移命令、启动前检查。
- 验收：
  - 空库可升级；应用启动不再新增手工 DDL。
  - revision 与 DSA 历史 Schema 对应清晰。
- 结果：新增根 `alembic.ini`、`migrations/env.py`、`migrations/script.py.mako`、DSA `v3.26.1` baseline SQL 和 revision `20260720_dsa_v3261_baseline`；新增 `src/serenity_alpha_lab/repositories/storage_migrations.py`，提供 `upgrade_database()`、`current_migration_status()` 和 `assert_database_at_head()`。
- 范围限制：本任务不迁移 DSA runtime `storage.py`，不执行历史 SQLite upgrade rehearsal，不启动 Provider/LLM、PIT Dataset、Quant Core 或正式回测。
- 验收证据：见 [Alembic 存储迁移接入记录](./storage-migration-alembic.md)；`tests/repositories/test_storage_migrations.py`；Red 测试先因缺少 module/migration files 失败，Green 后目标测试得到 `4 passed`；相关 repositories/architecture 套件 `22 passed`，全量 pytest `99 passed`。

### SAL-P1-013 验证历史 SQLite 升级

- [x] [DONE] 从脱敏 DSA fixture 执行 expand/backfill/verify
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-012 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：迁移脚本、校验报告、失败恢复测试。
- 验收：
  - 表/行数/关键聚合与迁移前一致。
  - 中途失败后可恢复备份并重新执行。
- 结果：新增 `src/serenity_alpha_lab/repositories/sqlite_upgrade.py`，可从 P0 `fixture.sql` 恢复脱敏历史库，备份后通过 Alembic `stamp` 升级到 baseline head，验证业务表 row_counts/content_hashes 不变，并在失败时恢复备份。
- 范围限制：本任务不新增业务 schema，不迁移 DSA runtime `storage.py`，不切换 Repository/API 读写路径，不启动 Provider/LLM、PIT Dataset、Quant Core 或正式回测。
- 验收证据：见 [SQLite 历史库升级验证记录](./sqlite-upgrade-verification.md)；`tests/repositories/test_sqlite_upgrade.py`；Red 测试先因缺少 module 失败，Green 后目标测试得到 `4 passed`；相关 repositories/architecture 套件 `26 passed`，全量 pytest `103 passed`。

### SAL-P1-014 整理配置与运行 Profile

- [x] [DONE] 定义 desktop/standalone/ci 配置及密钥边界
- 元数据：优先级 P1 | 负责人 BE/SEC | 估算 2d | 实际 0.5d | 依赖 SAL-P1-002 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：Pydantic Settings、Profile、脱敏诊断、配置来源。
- 验收：
  - 服务 Profile 的 API 不重写部署 `.env`。
  - CI 默认 Stub 且禁止真实模型/Provider 调用。
- 结果：新增 `src/serenity_alpha_lab/application/config_profiles.py`，定义 `RuntimeSettings`、`RuntimeProfile`、`ProfilePolicy`、`ConfigValueSource`、脱敏诊断、CI 边界校验和无副作用配置更新预览；`pydantic-settings>=2.0.0` 纳入 root `core` extra，并同步 `uv.lock` 与 `requirements.txt`。
- 范围限制：本任务不改写 DSA `.env`、不新增 Web/API 路由、不启动部署 automation、Provider/LLM 调用、Alembic、PIT Dataset、Quant Core 或正式回测。
- 验收证据：见 [配置 Profile 与密钥边界记录](./config-profile-facade.md)；`tests/application/test_config_profiles.py`；Red 测试先因缺少模块失败，Green 后目标测试得到 `9 passed`。

### SAL-P1-015 验证 Desktop 兼容和性能基线

- [x] [DONE] 在新 lock/协议/迁移下重跑 DSA 主路径
- 元数据：优先级 P0 | 负责人 FE/BE | 估算 1d | 实际 0.5d | 依赖 SAL-P1-003,SAL-P1-008,SAL-P1-013,SAL-P1-014 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：对比测试、启动时间/内存、兼容问题。
- 验收：
  - P0 Characterization 全通过。
  - 启动时间和单股分析性能退化不超过已批准阈值。
- 结果：新增 `scripts/run-p1-desktop-compatibility-performance.sh`，可复跑 Desktop headless tests、Desktop packaging/API health、CLI local backend、Bot command smoke、API/config、database 和 report/signal golden baseline，并把命令日志与性能摘要写入 `.cache/dsa-p0/p1-desktop-compatibility-performance/`。
- 性能：Desktop 后端 `/api/health` 启动 `5,822ms / 19 probes`，低于 `60,000ms` 阈值；report/signal golden 全脚本 `5,465ms`，低于 `60,000ms` 阈值；离线单股报告生成均值 `0.030ms`，低于 `5,000ms` 阈值。
- 范围限制：本任务不执行真实 GUI 人工验收、Desktop 打包/签名、Web Playwright smoke、Docker/SBOM 复跑、真实 Provider/LLM、PIT Dataset、Quant Core、正式回测或 DSA runtime source 迁移。
- 验收证据：见 [Desktop 兼容和性能基线记录](./desktop-compatibility-performance-baseline.md)；`scripts/run-p1-desktop-compatibility-performance.sh --python /Users/zq/.local/bin/python3.11` PASS；Desktop `npm test` 47 passed；Desktop/API/CLI/Bot pytest `121 passed, 7 warnings`；API/config、database、report/signal snapshots matched。

### SAL-P1-016 Gate G1：工程地基评审

- [x] [DONE] 批准进入数据与持久任务开发
- 元数据：优先级 P0 | 负责人 TL/SEC | 估算 0.5d | 实际 0.5d | 依赖 SAL-P1-001..015 | 开始 2026-07-20 | 完成 2026-07-20
- 交付物：Gate 记录、遗留风险、P2 冻结契约。
- 验收：
  - Lock、架构测试、Run/Artifact/TaskBackend、Alembic 和兼容回归均通过。
  - 未解决阻断项有明确 No-Go 或范围调整。
- 结果：Gate G1 评审结论为 `GO with accepted risks`。P1 工程加固完成度为 `16/16`，允许进入 P2 数据版本、Provider 收口与持久任务开发；供应链、Web audit、Docker image 漏洞继续作为发布前风险，不阻断 P2。
- P2 入口约束：`SAL-P2-001` 起必须复用 P1 `RuntimeProfile`、`ProblemDetail`、`TraceContext`、`ArtifactStore`、`Run/Stage/Event`、Alembic preflight 和 Compatibility Facade；CI 默认继续无真实 key、无真实 Provider/LLM 调用。
- 验收证据：见 [Gate G1 工程地基评审](./gate-g1-engineering-foundation-review.md)；`pytest` root/architecture/domain/application/repositories/integrations `103 passed`；dependency lock、baseline tag、patch check、Desktop 兼容 runner 和 `git diff --check` 均 PASS。

## 5. Phase 2：数据版本、Provider 收口与持久任务

### SAL-P2-001 定义 Provider 领域契约

- [x] [DONE] 实现 Capability、DataBatch、Provenance 和统一错误分类
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-016 | 开始 2026-07-20 | 完成 2026-07-21
- 交付物：MarketDataProvider Protocol、Schema、错误码、Contract Test。
- 验收：
  - retryable/rate-limited/auth/schema-drift/data-invalid/permanent 可区分。
  - DataBatch 携带来源、请求、时间、哈希、新鲜度和 warning。
- 结果：新增纯领域 `Capability`/`ProviderCapabilities`、泛型不可变 `DataBatch`、`Provenance`、`ProviderWarning`、同步 `MarketDataProvider` Protocol 和六类 `ProviderErrorCategory`；Provider 错误在应用边界映射到既有 `ProviderProblem`/`provider_error`，并保留既有 trace 与脱敏规则。
- 范围限制：未实现 DSA Provider Compatibility Adapter、真实 Provider/LLM 调用、Bronze/Dataset/PIT、fallback policy、PersistentTaskBackend、Quant Core、正式回测或 DSA runtime source 迁移。
- 验收证据：见 [Provider 领域契约记录](./provider-domain-contract.md)；`tests/domain/test_provider_contract.py`、`tests/application/test_api_errors.py`、`tests/architecture/test_architecture_boundaries.py`；Provider contract `23 passed`，相关套件 `109 passed`，全量 pytest `128 passed`，py_compile、lock、`git diff --check` 和 immutable tag 校验通过；本轮未声明 Ruff 通过，见 Provider 领域契约记录。

### SAL-P2-002 实现 DSA Provider Compatibility Adapter

- [x] [DONE] 将现有 DataFetcherManager/Pandas 收口到领域契约
- 元数据：优先级 P0 | 负责人 BE | 估算 2.5d | 实际 0.5d | 依赖 SAL-P2-001 | 开始 2026-07-21 | 完成 2026-07-21
- 交付物：Adapter、旧接口 Facade、字段映射和测试。
- 验收：
  - API/业务层不直接调用具体 Fetcher。
  - 旧单股分析可由 Feature Flag 在新旧路径切换。
- 结果：新增 `src/serenity_alpha_lab/integrations/dsa/provider_adapter.py`，通过注入式 DSA-like manager 将 `DataFetcherManager.get_daily_data()` / Pandas 行情输出映射为 `MarketDataProvider` 的不可变 `DataBatch`；Provenance 携带 DSA source、已脱敏请求参数、UTC 时间、SHA-256、field lineage、freshness 和 TraceContext。新增 `DsaStockHistoryCompatibilityFacade`，用 `use_provider_contract` feature flag 在旧历史行情响应和 Provider contract 路径之间切换。
- 范围限制：未修改 DSA runtime source，未执行真实 Provider/LLM 调用，未实现 Bronze/Dataset/PIT、fallback policy、PersistentTaskBackend、Quant Core、正式回测或 Evidence Agent；真实 DSA manager 只通过 profile 允许的 lazy factory 构造，CI 使用注入式 stub。
- 验收证据：见 [DSA Provider Compatibility Adapter 记录](./dsa-provider-compatibility-adapter.md)；`tests/integrations/test_dsa_provider_adapter.py`、`tests/application/test_api_errors.py`、`tests/architecture/test_architecture_boundaries.py`；Red 为缺少 `provider_adapter` module，Green 后 Adapter 目标测试 `8 passed`、相关套件 `22 passed`、全量 pytest `137 passed`。

### SAL-P2-003 完成证券代码兼容迁移

- [x] [DONE] 用 InstrumentId 和 Symbol Mapping 包裹 `normalize_stock_code`
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-005,SAL-P2-002 | 开始 2026-07-21 | 完成 2026-07-21
- 交付物：映射表、有效期、Provider 格式转换、歧义错误。
- 验收：
  - P0 代码转换测试全部通过。
  - 新领域路径不持久化裸 symbol 作为跨市场主键。
- 结果：新增 `src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py`，用不可变 `DsaStockCodeMapping` 和 `DsaStockCodeCompatibilityMapper` 包裹 DSA `normalize_stock_code` 兼容语义；覆盖 A 股前后缀、北交所、港股补零、日/韩/台 Yahoo suffix、美股 ticker、裸 6 位歧义、显式交易所冲突和映射有效期。`DsaProviderCompatibilityAdapter` 和 `DsaStockHistoryCompatibilityFacade` 已通过 mapper 生成 DSA provider symbol，并在 Provenance 中记录 canonical `instrument_ids`、`legacy_stock_codes` 和 `dsa_symbols`。
- 范围限制：未修改 DSA runtime source，未执行真实 Provider/LLM 调用，未实现 Bronze/Dataset/PIT、fallback policy、PersistentTaskBackend、Quant Core、正式回测或 Evidence Agent。
- 验收证据：见 [DSA Symbol Compatibility Migration 记录](./dsa-symbol-compatibility-migration.md)；`tests/integrations/test_dsa_symbol_compatibility.py`、`tests/integrations/test_dsa_provider_adapter.py`、`tests/domain/test_instrument_id.py`、`tests/architecture/test_architecture_boundaries.py`；Red 为缺少 `symbol_compatibility` module，Green 后目标测试 `25 passed`、相关套件 `72 passed`、全量 pytest `155 passed`，py_compile 和 dependency lock 通过。

### SAL-P2-004 建立 Bronze 原始数据层

- [x] [DONE] 保存可审计原始响应和请求元数据
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 0.5d | 依赖 SAL-P1-007,SAL-P2-001 | 开始 2026-07-21 | 完成 2026-07-21
- 交付物：Bronze Artifact Schema、压缩、哈希、保留策略。
- 验收：
  - 原始响应可按 Provider/请求/时间追踪。
  - 密钥、Cookie 和个人信息在落盘前清除。
- 结果：新增 `src/serenity_alpha_lab/repositories/bronze_raw_store.py`，通过既有 `ArtifactStore` 发布 deterministic JSON + gzip Bronze envelope；记录 Provider/operation、请求参数、requested/fetched/source 时间、source raw hash、sanitized payload hash、field lineage、trace/run/stage 和 archive retention，并提供按 provider/operation/requested_at 扫描的本地追踪 helper。
- 安全处理：落盘前递归清洗请求参数与原始响应，覆盖 API key、token、Authorization、Cookie/Set-Cookie、body/content/messages、邮箱、电话和常见身份字段；只保存脱敏 payload，同时保留 `source_raw_response_sha256` 与 `sanitized_raw_response_sha256` 供审计。
- 范围限制：未实现 Dataset Catalog、Silver/PIT、质量门禁、fallback policy、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source 迁移。
- 验收证据：见 [Bronze 原始数据层记录](./bronze-raw-data-layer.md)；`tests/repositories/test_bronze_raw_store.py`、`tests/architecture/test_architecture_boundaries.py`；Red 为缺少 `bronze_raw_store` module，Green 后目标测试 `6 passed`、相关套件 `56 passed`、全量 pytest `162 passed`，py_compile、dependency lock 和 immutable tag 校验通过。

### SAL-P2-005 实现证券主数据 Dataset

- [x] [DONE] 构建历史有效期的 instrument master
- 元数据：优先级 P0 | 负责人 QE | 估算 2d | 实际 0.5d | 依赖 SAL-P2-003,SAL-P2-004 | 开始 2026-07-21 | 完成 2026-07-21
- 交付物：证券、交易所、资产类型、上市/退市、状态和行业 Schema。
- 验收：
  - 主键唯一，Provider 映射有有效期。
  - 可查询任意 as-of 日期的历史证券状态。
- 结果：新增 `src/serenity_alpha_lab/datasets/instrument_master.py`，定义 `InstrumentMasterRecord`、`IndustryClassification`、`ProviderSymbolValidity` 和 `InstrumentMasterDataset`；内部主键复用 canonical `InstrumentId`，Provider symbol 复用 `ProviderSymbolMapping` 并增加有效期，Dataset 支持按 as-of 查询证券状态和 provider mapping，并可通过既有 `ArtifactStore` 发布 deterministic JSON Dataset Artifact。
- 范围限制：未实现交易日历、原始日线、PIT 基本面、fallback policy、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source 迁移。
- 验收证据：见 [Instrument Master Dataset 记录](./instrument-master-dataset.md)；`tests/datasets/test_instrument_master.py`、`tests/architecture/test_architecture_boundaries.py`；Red 为缺少 `instrument_master` module，Green 后目标测试 `3 passed`、相关套件 `15 passed` 和 `81 passed`，全量验证记录见 AEV-034。

### SAL-P2-006 实现交易日历

- [ ] [READY] 统一市场时区、交易日和开闭市时间
- 元数据：优先级 P0 | 负责人 QE | 估算 1.5d | 实际 - | 依赖 SAL-P2-001
- 交付物：Calendar Dataset、查询 API、缓存和边界测试。
- 验收：
  - A 股节假日、半日/异常休市策略明确。
  - UTC 与 Asia/Shanghai 跨日转换金标通过。

### SAL-P2-007 实现原始日线 Dataset

- [ ] [TODO] 定义并落地未复权 OHLCV/amount 日线
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-004,SAL-P2-005,SAL-P2-006
- 交付物：Arrow/Parquet Schema、分区、增量写入、查询。
- 验收：
  - 主键、OHLC、成交量、交易日和重复数据规则通过。
  - 记录保留 Provider 和 source timestamp。

### SAL-P2-008 实现公司行动与复权

- [ ] [TODO] 支持分红、送转、配股和前/后复权因子
- 元数据：优先级 P0 | 负责人 QE | 估算 3d | 实际 - | 依赖 SAL-P2-007
- 交付物：CorporateAction/Adjustment Dataset、算法、金标。
- 验收：
  - 复权序列满足固定样本和性质测试。
  - 原始价格不被覆盖；复权口径显式可选。

### SAL-P2-009 实现 PIT 基本面 Dataset

- [ ] [TODO] 区分 period/announced/available/ingested/revision
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 3d | 实际 - | 依赖 SAL-P2-004,SAL-P2-005
- 交付物：FundamentalRecord Schema、版本查询、可信度等级。
- 验收：
  - 回测查询拒绝 available_at 晚于 decision_time 的记录。
  - 无公告时间的历史 DSA 数据标记 unknown，禁止正式回测。

### SAL-P2-010 建立 Arrow Schema Registry

- [ ] [TODO] 为主数据、日线、公司行动、财务建立版本化 Schema
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 1.5d | 实际 - | 依赖 SAL-P2-005..009
- 交付物：Schema Registry、兼容规则、序列化测试。
- 验收：
  - 新增字段向后兼容；删除/改义需要新 major。
  - Pandas/Polars/Arrow 往返类型不漂移。

### SAL-P2-011 实现 Dataset Catalog 与 Manifest

- [ ] [TODO] 管理不可变版本、血缘、文件哈希和 latest alias
- 元数据：优先级 P0 | 负责人 BE | 估算 2.5d | 实际 - | 依赖 SAL-P1-007,SAL-P2-010
- 交付物：Catalog Repository、Manifest、发布/查询 API。
- 验收：
  - Dataset 发布后不可修改。
  - Run 只引用具体版本；latest 不是正式实验输入。

### SAL-P2-012 实现数据质量规则引擎

- [ ] [TODO] 支持 warning/quarantine/blocking 规则和报告
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-007..011
- 交付物：唯一性、OHLC、连续性、空值、漂移、异常值规则。
- 验收：
  - 每条失败定位到 Dataset/分区/字段/样本。
  - 规则版本写入 Manifest；异常 fixture 全部命中预期等级。

### SAL-P2-013 实现隔离区与原子发布

- [ ] [TODO] 阻止失败 Dataset 更新 latest 并清理临时 Artifact
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 - | 依赖 SAL-P2-011,SAL-P2-012
- 交付物：quarantine 状态、发布事务、垃圾回收。
- 验收：
  - blocking 失败后旧 latest 保持不变。
  - 数据库/文件任一失败不留下成功假象。

### SAL-P2-014 建立 Provider 契约 Fixture

- [ ] [TODO] 覆盖 AKShare、efinance、Tushare、BaoStock 和 YFinance 核心接口
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 3d | 实际 - | 依赖 SAL-P2-002,SAL-P2-010
- 交付物：脱敏响应、Schema、超时/空数据/字段漂移案例。
- 验收：
  - CI 全离线运行。
  - 至少覆盖 A 股主路径和 DSA 已支持的港/美基本路径。

### SAL-P2-015 实现 Provider Policy 与 fallback trace

- [ ] [TODO] 按能力、新鲜度和质量选择来源并记录冲突
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-001,SAL-P2-014
- 交付物：YAML Policy、fallback、cross-check、Run Diagnostics。
- 验收：
  - 成功但陈旧/缺字段的数据会触发 fallback。
  - 跨源差异超阈值进入 quarantine，不静默平均。

### SAL-P2-016 实现增量同步与交易日调度

- [ ] [TODO] 支持 checkpoint、回看窗口、锁和补数
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-006,SAL-P2-011,SAL-P2-015
- 交付物：DataSyncRun、Scheduler、补数命令、幂等测试。
- 验收：
  - 重复执行不产生重复记录。
  - 非交易日、失败重试和历史补数行为明确。

### SAL-P2-017 建立 PostgreSQL standalone Profile

- [ ] [TODO] 实现数据库配置、连接池和 Repository Contract
- 元数据：优先级 P0 | 负责人 BE | 估算 2.5d | 实际 - | 依赖 SAL-P1-012,SAL-P1-014
- 交付物：Compose service、Alembic、Repository 实现、健康检查。
- 验收：
  - SQLite/PostgreSQL 跑同一 Contract Suite。
  - 时间、Decimal、JSON 和事务语义一致。

### SAL-P2-018 实现 PersistentTaskBackend

- [ ] [TODO] 接入 Celery/Redis，数据库 Run/Event 为权威状态
- 元数据：优先级 P0 | 负责人 BE | 估算 3d | 实际 - | 依赖 SAL-P1-008,SAL-P2-017
- 交付物：队列路由、Worker、lease/heartbeat、重试和取消。
- 验收：
  - API 重启不丢任务。
  - Worker 异常后任务可安全重投或从 checkpoint 恢复。

### SAL-P2-019 实现可恢复任务事件流

- [ ] [TODO] 持久化 RunEvent、SSE `Last-Event-ID` 和孤儿 Reconciler
- 元数据：优先级 P0 | 负责人 BE/FE | 估算 2.5d | 实际 - | 依赖 SAL-P2-018
- 交付物：事件 API、前端恢复、stalled 检测、临时制品清理。
- 验收：
  - 浏览器断线重连不漏事件。
  - stalled 与 failed 可区分，重复投递不产生重复副作用。

### SAL-P2-020 Gate G2：数据与任务评审

- [ ] [TODO] 批准 Dataset、Provider 和持久任务进入筛选开发
- 元数据：优先级 P0 | 负责人 TL/QE/SEC | 估算 0.5d | 实际 - | 依赖 SAL-P2-001..019
- 交付物：Gate 记录、Dataset 样本、故障恢复证据。
- 验收：
  - 可发布一个版本化 A 股 Dataset，记录可追溯。
  - Provider 异常阻断有效，API/Worker 重启测试通过。
  - DSA 单股分析兼容路径通过。

## 6. Phase 3：AlphaSift、因子与股票筛选

### SAL-P3-001 审查并锁定 AlphaSift

- [ ] [TODO] 固定源码 commit、Apache-2.0 归因和依赖清单
- 元数据：优先级 P0 | 负责人 TL/SEC | 估算 1d | 实际 - | 依赖 SAL-P2-020
- 交付物：版本决策、许可证/NOTICE、漏洞和维护风险。
- 验收：
  - 已知限制与平台非目标一致。
  - 有升级、替换和停止使用条件。

### SAL-P3-002 构建离线 AlphaSift Wheel

- [ ] [TODO] 移除生产运行时 `git+https` 安装
- 元数据：优先级 P0 | 负责人 BE | 估算 1.5d | 实际 - | 依赖 SAL-P3-001,SAL-P1-003
- 交付物：签名/哈希 Wheel、内部制品引用、SBOM。
- 验收：
  - 断网环境可完成生产安装。
  - lock 和镜像能追溯到源码 commit。

### SAL-P3-003 定义 ScreeningProvider

- [ ] [TODO] 隔离 AlphaSift 与平台 Application/Domain
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 1.5d | 实际 - | 依赖 SAL-P3-002
- 交付物：Protocol、AlphaSift Adapter、Fake 实现。
- 验收：
  - 上层不导入 AlphaSift 内部类。
  - status/strategies/screen 的错误和超时语义统一。

### SAL-P3-004 定义 CandidateBatch 契约

- [ ] [TODO] 标准化候选、层级分数、原因和来源
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 - | 依赖 SAL-P3-003
- 交付物：Candidate/CandidateBatch Schema、版本、Contract Test。
- 验收：
  - 保存 snapshot time、strategy version、L1/L2/L3 分数和 rank。
  - LLM overlay 与确定性分数独立。

### SAL-P3-005 实现 FactorDefinition 版本模型

- [ ] [TODO] 建立 draft/published/retired 和不可变发布
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 - | 依赖 SAL-P2-011
- 交付物：FactorDefinition、Repository、版本 API、审计。
- 验收：
  - 公式、输入、窗口、缺失/后处理和实现哈希完整。
  - 已发布版本不能原地修改。

### SAL-P3-006 实现因子 DSL 与算子白名单

- [ ] [TODO] 支持 delay/rolling/rank/算术/条件等基础表达式
- 元数据：优先级 P0 | 负责人 QE | 估算 3d | 实际 - | 依赖 SAL-P3-005
- 交付物：Parser/AST/Validator/Compiler、错误定位、测试。
- 验收：
  - 不执行任意 Python/module path。
  - 窗口、数据类型、除零和未来引用在编译期或运行期安全失败。

### SAL-P3-007 交付首批 15 个基础因子

- [ ] [TODO] 实现质量、估值、成长、动量、波动和流动性因子
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 3d | 实际 - | 依赖 SAL-P3-006,SAL-P2-009
- 交付物：15+ 因子定义、口径文档、手工/参考金标。
- 验收：
  - 每个因子声明方向、窗口、数据要求和适用市场。
  - 结果与手工样本或可信参考实现一致。

### SAL-P3-008 实现横截面后处理

- [ ] [TODO] 支持 winsorize、标准化、行业/市值中性化和缺失策略
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P3-007
- 交付物：处理器、参数 Schema、数值稳定性测试。
- 验收：
  - 同一交易日只使用当时股票池。
  - 常量列、小样本、缺行业和极值有明确行为。

### SAL-P3-009 实现 Factor Evaluation

- [ ] [TODO] 计算覆盖率、IC/ICIR、分组收益、单调性、换手和暴露
- 元数据：优先级 P0 | 负责人 QE | 估算 3d | 实际 - | 依赖 SAL-P3-008
- 交付物：FactorEvaluationRun、指标、Artifact、API。
- 验收：
  - 指标口径、年化和未来收益窗口版本化。
  - 正式评价通过 PIT 和样本重叠检查。

### SAL-P3-010 实现因子计算 DAG 与缓存

- [ ] [TODO] 编译依赖、公共子表达式和增量重算计划
- 元数据：优先级 P1 | 负责人 QE/BE | 估算 3d | 实际 - | 依赖 SAL-P3-006,SAL-P2-011
- 交付物：DAG、cache key、分区计划、性能指标。
- 验收：
  - cache key 包含 Dataset/Factor/Universe/Engine version。
  - 失败 Run 不发布共享缓存；新交易日只重算受影响分区。

### SAL-P3-011 实现 Historical Universe

- [ ] [TODO] 构建 L0 历史股票池和可交易性硬过滤
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-005,SAL-P2-006
- 交付物：UniverseDefinition/Snapshot、ST/上市/退市/停牌规则。
- 验收：
  - 历史日期不使用当前成分或当前上市状态。
  - 每次排除有规则 ID 和数据证据。

### SAL-P3-012 实现 ScreenDefinition 与 L0~L4 Pipeline

- [ ] [TODO] 组合 Universe、AlphaSift、Factor、Constraint 和 Risk Gate
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 3d | 实际 - | 依赖 SAL-P3-004,SAL-P3-008,SAL-P3-011
- 交付物：ScreenDefinition 版本、Pipeline、阶段 Artifact。
- 验收：
  - 修改权重/过滤器/约束产生新版本。
  - LLM 不能绕过硬过滤，正式 Run 引用发布版本。

### SAL-P3-013 实现 ScreenSnapshot 与解释轨迹

- [ ] [TODO] 保存每只证券 passed/failed-stage/contribution/rank
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2d | 实际 - | 依赖 SAL-P3-012
- 交付物：Result Schema、原因码、对比查询。
- 验收：
  - 用户可解释入选和淘汰原因。
  - 人类文本不是权威判断，结构化原因可重放。

### SAL-P3-014 实现 Quant Screening API

- [ ] [TODO] 提供 factor/screen definition、run、result 和 comparison API
- 元数据：优先级 P0 | 负责人 BE | 估算 2.5d | 实际 - | 依赖 SAL-P3-005,SAL-P3-009,SAL-P3-013
- 交付物：`/api/v1/quant` 路由、202 Run 响应、OpenAPI。
- 验收：
  - 创建接口支持 Idempotency-Key。
  - 结果分页稳定，包含 as-of/dataset/schema/trace。

### SAL-P3-015 实现 Screen Lab

- [ ] [TODO] 构建定义编辑、运行、结果、解释和比较界面
- 元数据：优先级 P0 | 负责人 FE | 估算 3d | 实际 - | 依赖 SAL-P3-014
- 交付物：路由、分步配置、虚拟表格、详情抽屉、状态页。
- 验收：
  - draft/published、Snapshot/History、Preview/Formal 标识清晰。
  - loading/empty/partial/error/stale/permission 状态完整。

### SAL-P3-016 筛选性能与复现验收

- [ ] [TODO] 建立全 A 股性能、内存、增量和结果哈希基线
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 - | 依赖 SAL-P3-009..015
- 交付物：性能报告、容量预算、固定 Run Bundle。
- 验收：
  - 常用因子日更和筛选达到架构方案 SLO。
  - 相同 Dataset/Definition/Engine 结果哈希一致。

### SAL-P3-017 Gate G3：筛选与因子评审

- [ ] [TODO] 批准 Screen/Factor 成为回测输入
- 元数据：优先级 P0 | 负责人 TL/QE/RE | 估算 0.5d | 实际 - | 依赖 SAL-P3-001..016
- 交付物：Gate 记录、因子口径签字、筛选金标。
- 验收：
  - 15+ 因子、AlphaSift 契约、历史股票池、解释轨迹和性能全部通过。
  - 未通过数据/偏差检查的 Screen 不得进入 P4 正式回测。

## 7. Phase 4：真实组合回测与确定性风控

### SAL-P4-001 锁定 DSA Signal Evaluation 行为

- [ ] [TODO] 补齐当前 `BacktestEngine` Characterization 和 API 金标
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 1.5d | 实际 - | 依赖 SAL-P3-017
- 交付物：固定信号、T+N 收益、止盈止损和汇总 fixture。
- 验收：
  - 覆盖买入/卖出/观望、否定文本和缺失行情。
  - 当前结果和异常语义可自动比较。

### SAL-P4-002 迁移为 SignalEvaluationEngine

- [ ] [TODO] 重命名领域语义并保留旧 Backtest API 兼容
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2d | 实际 - | 依赖 SAL-P4-001
- 交付物：新模型/服务名、兼容 Facade、`evaluation_type=signal`。
- 验收：
  - P4-001 金标完全一致。
  - UI/API 不再把信号评价描述为组合策略回测。

### SAL-P4-003 定义 BacktestSpec

- [ ] [TODO] 冻结正式组合回测输入和 Canonical Hash
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 - | 依赖 SAL-P3-017
- 交付物：Dataset/Universe/Strategy/Execution/Cost/Risk Spec。
- 验收：
  - 信号与执行时间、初始资金、基准、费用、随机种子明确。
  - Canonical JSON 在平台间生成相同 spec_hash。

### SAL-P4-004 定义 BacktestArtifact

- [ ] [TODO] 标准化订单、成交、持仓、现金、净值、指标和审计输出
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 2d | 实际 - | 依赖 SAL-P4-003,SAL-P1-007
- 交付物：Arrow/JSON Schema、Artifact Manifest、兼容规则。
- 验收：
  - 大结果通过 URI 传递，API 不嵌入全量 DataFrame。
  - preview/formal/partial/invalid 状态明确。

### SAL-P4-005 锁定 Qlib 版本与隔离方案

- [ ] [TODO] 审查许可证、依赖、平台兼容和 Worker 资源
- 元数据：优先级 P0 | 负责人 QE/SEC | 估算 1.5d | 实际 - | 依赖 SAL-P1-003,SAL-P4-003
- 交付物：Qlib 版本 ADR、quant extra、镜像/Worker 设计。
- 验收：
  - Desktop core 不强制安装 Qlib。
  - Qlib 不在 FastAPI 进程初始化，全局状态被进程隔离。

### SAL-P4-006 实现 Dataset 到 Qlib 转换

- [ ] [TODO] 生成 calendar/instrument/feature 并记录字段映射
- 元数据：优先级 P0 | 负责人 QE | 估算 3d | 实际 - | 依赖 SAL-P4-005,SAL-P2-011
- 交付物：转换器、缓存、双向 lineage、固定样本。
- 验收：
  - 只读取 passed 的不可变 Dataset。
  - 日期、复权、缺失和证券代码与平台口径一致。

### SAL-P4-007 实现 Qlib QuantEngine Adapter

- [ ] [TODO] 包装 train/predict/backtest/evaluate_factor 和 Recorder
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 3d | 实际 - | 依赖 SAL-P4-004,SAL-P4-006
- 交付物：QuantEngine、受控配置模板、Recorder 映射。
- 验收：
  - Qlib 配置不接受任意 module path。
  - 平台 run_id、spec/data/engine version 与 Qlib 记录关联。

### SAL-P4-008 实现订单状态机

- [ ] [TODO] 定义 order、状态事件、拒绝、部分成交和过期
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P4-003
- 交付物：Order/OrderEvent、状态转换、性质测试。
- 验收：
  - 非法转换被拒绝，事件只追加。
  - 同一订单事件重放幂等。

### SAL-P4-009 实现 Portfolio Ledger

- [ ] [TODO] 建立现金、持仓 Lot、应收应付、成交和估值账本
- 元数据：优先级 P0 | 负责人 QE/BE | 估算 3d | 实际 - | 依赖 SAL-P4-008
- 交付物：Ledger、重放器、对账和不变量测试。
- 验收：
  - Ledger 可重放得到相同持仓和净值。
  - 现金 + 持仓 + 应收 - 应付等式始终成立。

### SAL-P4-010 实现费用与滑点模型

- [ ] [TODO] 支持佣金、印花税、过户费、滑点和参与率
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 2d | 实际 - | 依赖 SAL-P4-008
- 交付物：CostModel、参数版本、金标。
- 验收：
  - 买卖方向税费不同，最低佣金和舍入规则明确。
  - 成本前后指标可分别查询。

### SAL-P4-011 实现 A 股执行规则

- [ ] [TODO] 支持 T+1、交易单位、停牌、涨跌停和不可成交
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 3d | 实际 - | 依赖 SAL-P4-008,SAL-P4-010
- 交付物：ExecutionModel、规则版本、边界 fixture。
- 验收：
  - 同 Bar 收盘信号不能以同收盘价无条件成交。
  - 不可成交订单的保留/过期策略可配置并审计。

### SAL-P4-012 实现公司行动入账

- [ ] [TODO] 处理现金分红、送转、配股和退市清算
- 元数据：优先级 P0 | 负责人 QE | 估算 3d | 实际 - | 依赖 SAL-P2-008,SAL-P4-009
- 交付物：CorporateAction Processor、Ledger 事件、金标。
- 验收：
  - 除权前后经济价值和现金流符合口径。
  - 原始/复权价格不会被重复计入。

### SAL-P4-013 实现调仓与目标权重

- [ ] [TODO] 将 Screen/Model Signal 转为受约束订单
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P3-013,SAL-P4-009,SAL-P4-011
- 交付物：RebalancePolicy、WeightingPolicy、订单生成器。
- 验收：
  - 调仓日历、现金缓冲、最小订单和剩余现金明确。
  - 相同输入的订单顺序和数量确定。

### SAL-P4-014 实现确定性 RiskPolicy

- [ ] [TODO] 支持个股、行业、风格、流动性、换手和回撤规则
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 3d | 实际 - | 依赖 SAL-P4-013
- 交付物：版本化规则、pass/warn/block/not-evaluable 结果。
- 验收：
  - not-evaluable 默认阻断。
  - Agent 或 UI 无法覆盖 block，只能请求新规则版本重跑。

### SAL-P4-015 实现回测偏差审计

- [ ] [TODO] 自动检查前视、幸存者、PIT、样本重叠和成本敏感性
- 元数据：优先级 P0 | 负责人 QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-009,SAL-P3-011,SAL-P4-003
- 交付物：AuditReport、hard/warning 规则、异常 fixture。
- 验收：
  - 已知泄漏样本被阻断。
  - invalid Run 不进入排行榜和 Agent 强结论。

### SAL-P4-016 实现统一绩效指标

- [ ] [TODO] 计算收益、风险、回撤、换手、成本和基准指标
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 3d | 实际 - | 依赖 SAL-P4-009,SAL-P4-010
- 交付物：Metric Registry、公式版本、参考对比和文档。
- 验收：
  - Sharpe/Sortino/Calmar/最大回撤等口径明确。
  - 样本期、频率、无风险利率和年化天数写入输出。

### SAL-P4-017 实现 BacktestRun 编排

- [ ] [TODO] 串联 Spec、Qlib/策略、Ledger、Risk、Audit 和 Artifact
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 3d | 实际 - | 依赖 SAL-P4-004,SAL-P4-007,SAL-P4-009..016
- 交付物：Application Use Case、Stage、幂等与重试策略。
- 验收：
  - 相同 spec/data/engine 成功 Run 可复用。
  - 正式 Run 不允许 dirty code，或必须记录补丁哈希并降级。

### SAL-P4-018 实现资源限制、取消和 checkpoint

- [ ] [TODO] 隔离回测子进程并处理 OOM/超时/取消
- 元数据：优先级 P0 | 负责人 BE/QE | 估算 2.5d | 实际 - | 依赖 SAL-P2-018,SAL-P4-017
- 交付物：资源配额、checkpoint、partial 状态、故障测试。
- 验收：
  - API 不因重计算阻塞。
  - 超时/取消不会产生 SUCCEEDED；部分 Artifact 明确标记。

### SAL-P4-019 建立回测金标与性质测试

- [ ] [TODO] 用 3~5 证券、20~60 日手工样本覆盖关键规则
- 元数据：优先级 P0 | 负责人 QE/RE | 估算 3d | 实际 - | 依赖 SAL-P4-008..018
- 交付物：订单/成交/持仓/现金/净值/指标 fixture。
- 验收：
  - 停牌、涨跌停、T+1、费用、公司行动和调仓均覆盖。
  - 分块读取与全量读取结果一致。

### SAL-P4-020 实现真实回测 API

- [ ] [TODO] 提供 `/api/v1/quant/backtest-runs` 和 Artifact 查询
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 - | 依赖 SAL-P4-017,SAL-P4-018
- 交付物：创建/状态/指标/订单/持仓/审计/取消 API。
- 验收：
  - 与旧 Signal Evaluation 路由和 Schema 明确分离。
  - 大列表游标分页，Artifact 下载受权限控制。

### SAL-P4-021 实现 Quant Lab

- [ ] [TODO] 构建回测创建、净值、回撤、交易、持仓和审计界面
- 元数据：优先级 P0 | 负责人 FE | 估算 3d | 实际 - | 依赖 SAL-P4-020
- 交付物：参数页、运行进度、结果 Tabs、导出和一键 Screen 回测。
- 验收：
  - Preview/Formal、valid/invalid 标识不可混淆。
  - 图表有对应原始表和 Artifact 下载。

### SAL-P4-022 Gate G4：回测与风控评审

- [ ] [TODO] 批准正式回测结果进入 Agent Evidence
- 元数据：优先级 P0 | 负责人 TL/QE/RE/SEC | 估算 0.5d | 实际 - | 依赖 SAL-P4-001..021
- 交付物：Gate 记录、金标、偏差审计和性能报告。
- 验收：
  - Signal/Factor/Portfolio 三类评价语义完全分离。
  - Ledger 可重放、结果可复现、偏差门禁和资源隔离通过。

## 8. Phase 5：证据化 Agent、报告与成本治理

### SAL-P5-001 定义 Evidence/Claim/Report Schema

- [ ] [TODO] 冻结证据、主张、引用和报告等级
- 元数据：优先级 P0 | 负责人 AI/BE | 估算 2d | 实际 - | 依赖 SAL-P4-022
- 交付物：Pydantic/JSON Schema、版本规则、示例和测试。
- 验收：
  - Evidence 包含 source、available_at、hash、trust、dataset。
  - Claim 必须声明 citation_ids 和 verification 状态。

### SAL-P5-002 实现 Evidence Store

- [ ] [TODO] 持久化不可变证据、修订和内容寻址正文
- 元数据：优先级 P0 | 负责人 BE/AI | 估算 2.5d | 实际 - | 依赖 SAL-P5-001,SAL-P1-007
- 交付物：Repository、Artifact 正文、查询、去重和权限。
- 验收：
  - 相同内容哈希去重；修订产生新 Evidence。
  - 私有文档按用户/团队隔离。

### SAL-P5-003 实现 EvidenceBundle Builder

- [ ] [TODO] 按证券、决策时间、角色和预算构建最小上下文
- 元数据：优先级 P0 | 负责人 AI | 估算 3d | 实际 - | 依赖 SAL-P5-002
- 交付物：Builder、优先级、去重、裁剪和 Token 估算。
- 验收：
  - 不包含 available_at 晚于 decision_time 的证据。
  - 超限时按优先级裁剪，不破坏 Schema 指令。

### SAL-P5-004 实现来源信任与非结构化清洗

- [ ] [TODO] 对公告、新闻、搜索和社交内容分级与去噪
- 元数据：优先级 P0 | 负责人 AI/SEC | 估算 2.5d | 实际 - | 依赖 SAL-P5-002
- 交付物：TrustPolicy、URL/正文哈希、时间冲突、恶意标记。
- 验收：
  - 低可信来源不能单独支撑强结论。
  - 外部指令不进入系统 Prompt 或工具参数。

### SAL-P5-005 实现 Quant Evidence Adapter

- [ ] [TODO] 把 Screen/Factor/Backtest/Risk 转成结构化证据
- 元数据：优先级 P0 | 负责人 QE/AI | 估算 2d | 实际 - | 依赖 SAL-P4-022,SAL-P5-001
- 交付物：Evidence producer、数值/单位/口径映射、测试。
- 验收：
  - LLM 无需自行计算指标。
  - 数值证据可追溯到具体 Artifact 和公式版本。

### SAL-P5-006 建立 Prompt 与输出 Schema Registry

- [ ] [TODO] 版本化角色 Prompt、工具、模型能力和输出契约
- 元数据：优先级 P0 | 负责人 AI | 估算 2d | 实际 - | 依赖 SAL-P1-009,SAL-P5-001
- 交付物：Registry、发布状态、hash、变更对比。
- 验收：
  - 已发布 Prompt 不可原地修改。
  - Run 保存解析后的 Prompt/Schema/Tool 版本。

### SAL-P5-007 实现 Agent Stage 持久化

- [ ] [TODO] 为 DSA Orchestrator 增加 stage_id、attempt 和 checkpoint
- 元数据：优先级 P0 | 负责人 AI/BE | 估算 3d | 实际 - | 依赖 SAL-P1-006,SAL-P1-009,SAL-P2-018
- 交付物：Stage Repository、恢复、取消、degrade/fail policy。
- 验收：
  - Worker 重启从最后成功阶段恢复。
  - 已成功的模型调用不重复收费。

### SAL-P5-008 改造 Technical Agent

- [ ] [TODO] 只消费技术/因子 Evidence，不让模型重算指标
- 元数据：优先级 P0 | 负责人 AI/QE | 估算 2d | 实际 - | 依赖 SAL-P5-003,SAL-P5-005,SAL-P5-006
- 交付物：Prompt、Schema、兼容输出、回归 fixture。
- 验收：
  - 所有数值 Claim 有 citation。
  - 原 DSA Dashboard 字段在兼容层可继续生成。

### SAL-P5-009 改造 Intel Agent

- [ ] [TODO] 增加来源、发布时间、可信度和冲突处理
- 元数据：优先级 P0 | 负责人 AI | 估算 2.5d | 实际 - | 依赖 SAL-P5-003,SAL-P5-004,SAL-P5-006
- 交付物：搜索结果 Adapter、Prompt、结构化事件输出。
- 验收：
  - 事件时间与抓取时间分离。
  - 重复、陈旧和恶意内容被标记或排除。

### SAL-P5-010 改造 Risk/Portfolio Agent

- [ ] [TODO] 消费确定性 Risk/Portfolio 结果且无权覆盖硬门禁
- 元数据：优先级 P0 | 负责人 AI/QE | 估算 2d | 实际 - | 依赖 SAL-P4-014,SAL-P5-005,SAL-P5-006
- 交付物：Prompt、Schema、risk override 防护、回归。
- 验收：
  - block/not-evaluable 在最终结果保持。
  - Agent 只补充非结构化风险和解释。

### SAL-P5-011 实现多空反证与最终综合

- [ ] [TODO] 增加 Bull/Bear/Disagreement/Decision 受控流程
- 元数据：优先级 P1 | 负责人 AI/RE | 估算 3d | 实际 - | 依赖 SAL-P5-008..010
- 交付物：角色 Stage、冲突摘要、失效条件和置信等级。
- 验收：
  - 多空不能只重复分析员摘要。
  - Final Decision 不新增前序 Evidence 中不存在的事实。

### SAL-P5-012 完善模型路由、缓存与预算

- [ ] [TODO] 在 DSA LiteLLM 上实现调用/Run/日三级预算
- 元数据：优先级 P0 | 负责人 AI/BE | 估算 2.5d | 实际 - | 依赖 SAL-P5-006,SAL-P5-007
- 交付物：ModelInvocation、精确缓存、价格表、限流和降级。
- 验收：
  - 超预算返回 partial/budget-exhausted，不静默继续。
  - cache key 包含 Evidence/Prompt/Model/参数版本。

### SAL-P5-013 实现 Citation Validator

- [ ] [TODO] 校验证据存在、数值一致、时间和方向
- 元数据：优先级 P0 | 负责人 AI/QE | 估算 3d | 实际 - | 依赖 SAL-P5-001,SAL-P5-005,SAL-P5-008..011
- 交付物：Claim Validator、修复流程、报告等级。
- 验收：
  - 数值/日期/比率/价格目标强制引用。
  - 一次修复后仍失败的 Claim 被删除并降级，不能伪装 verified。

### SAL-P5-014 强化 Agent 工具安全

- [ ] [TODO] 默认 deny、参数 Schema、SSRF 和 Prompt Injection 防护
- 元数据：优先级 P0 | 负责人 SEC/AI | 估算 2.5d | 实际 - | 依赖 SAL-P5-004,SAL-P5-006
- 交付物：Tool allowlist、权限/副作用声明、攻击测试集。
- 验收：
  - Agent 无 Shell、交易和任意数据库写权限。
  - 恶意网页不能改变系统规则或发起未授权 URL。

### SAL-P5-015 实现可信 ResearchReport 与 Renderer

- [ ] [TODO] 渲染 verified/partial/insufficient-evidence 报告
- 元数据：优先级 P0 | 负责人 AI/FE | 估算 2.5d | 实际 - | 依赖 SAL-P5-013
- 交付物：权威 JSON、Markdown/HTML Renderer、模板版本。
- 验收：
  - Markdown 不是权威数据源。
  - 报告显示 as-of、Dataset、模型、成本、风险和免责声明。

### SAL-P5-016 实现引用 UI 与通知 Outbox

- [ ] [TODO] 在 DSA Web/桌面/通知展示证据和发送状态
- 元数据：优先级 P0 | 负责人 FE/BE | 估算 3d | 实际 - | 依赖 SAL-P5-015
- 交付物：引用展开、来源链接、Report 页面、Transactional Outbox。
- 验收：
  - 页面可从 Claim 展开到 Evidence/Artifact。
  - 通知至少一次发送但按 dedupe_key 不重复。

### SAL-P5-017 建立 Agent 金标与回归评测

- [ ] [TODO] 完成 50+ 案例、指标、切分和模型/Prompt 对比
- 元数据：优先级 P0 | 负责人 AI/RE/SEC | 估算 3d | 实际 - | 依赖 SAL-P5-008..016
- 交付物：评测集、离线 Stub、评分器、回归报告。
- 验收：
  - 覆盖缺失、异常、事件、冲突、恶意内容和多市场样本。
  - 引用准确率 >=95%，无依据数值率 <1%，安全核心集全通过。

### SAL-P5-018 Gate G5：可信研究评审

- [ ] [TODO] 批准证据化 Agent 和报告进入 RC
- 元数据：优先级 P0 | 负责人 TL/AI/RE/SEC | 估算 0.5d | 实际 - | 依赖 SAL-P5-001..017
- 交付物：Gate 记录、评测、成本和攻击测试报告。
- 验收：
  - Evidence、checkpoint、预算、引用、报告等级和 UI 全链路通过。
  - Agent 无法覆盖 Quant/Risk 硬事实与门禁。

## 9. Phase 6：安全、稳定性与发布加固

### SAL-P6-001 完善认证与 RBAC

- [ ] [TODO] 定义 desktop/standalone/team 的身份和权限模型
- 元数据：优先级 P0 | 负责人 BE/SEC | 估算 2.5d | 实际 - | 依赖 SAL-P5-018
- 交付物：角色、权限矩阵、OIDC 可选接入、API 测试。
- 验收：
  - desktop 本地模式不降低易用性。
  - team 模式的数据、运行、配置和管理权限分离。

### SAL-P6-002 实现资源与 Artifact 授权

- [ ] [TODO] 对 Run、Definition、Evidence、Report 和下载实施对象级权限
- 元数据：优先级 P0 | 负责人 BE/SEC | 估算 2.5d | 实际 - | 依赖 SAL-P6-001
- 交付物：owner/tenant、授权检查、短时签名 URL、审计。
- 验收：
  - 不能通过猜测 ID 或 URI 跨用户读取。
  - 后台 Worker 只获得任务所需最小权限。

### SAL-P6-003 加固密钥与配置

- [ ] [TODO] 接入 Secret Manager/OS Keychain 和配置审计
- 元数据：优先级 P0 | 负责人 SEC/BE | 估算 2d | 实际 - | 依赖 SAL-P1-014,SAL-P6-001
- 交付物：密钥引用、轮换、脱敏诊断、访问审计。
- 验收：
  - 数据库、日志、Trace、前端和备份无明文密钥。
  - 配置 API 只显示存在状态和最后四位。

### SAL-P6-004 加固输入、抓取与报告渲染

- [ ] [TODO] 实施上传限制、SSRF、防恶意 Markdown/HTML
- 元数据：优先级 P0 | 负责人 SEC/BE/FE | 估算 3d | 实际 - | 依赖 SAL-P5-014,SAL-P5-015
- 交付物：URL Policy、文件扫描、sanitizer、安全 Header。
- 验收：
  - 私网/本机地址、危险协议和重定向绕过被阻止。
  - 报告不能执行脚本或注入不安全链接。

### SAL-P6-005 建立安全与供应链门禁

- [ ] [TODO] 集成 Secret/SAST/SCA/license/image/SBOM 扫描
- 元数据：优先级 P0 | 负责人 SEC | 估算 2d | 实际 - | 依赖 SAL-P0-011,SAL-P1-003
- 交付物：CI Job、豁免流程、漏洞 SLA、签名验证。
- 验收：
  - 未豁免 Critical/High 阻断发布。
  - 豁免包含责任人、到期日和补偿控制。

### SAL-P6-006 接入端到端 OpenTelemetry

- [ ] [TODO] 传播 API/Task/Provider/Qlib/LLM/Report/Notify Trace
- 元数据：优先级 P0 | 负责人 BE/AI | 估算 2.5d | 实际 - | 依赖 SAL-P2-019,SAL-P5-012
- 交付物：Trace instrumentation、采样、脱敏和关联查询。
- 验收：
  - 单次 Run 可跨进程完整追踪。
  - Span 不包含完整 Prompt、新闻正文或敏感参数。

### SAL-P6-007 建立指标与 Grafana Dashboard

- [ ] [TODO] 覆盖 API、队列、Provider、Dataset、Quant、Agent 和费用
- 元数据：优先级 P0 | 负责人 BE/AI | 估算 2.5d | 实际 - | 依赖 SAL-P6-006
- 交付物：Prometheus 指标、Dashboard、基线和标签规范。
- 验收：
  - 可查看 P95、队列年龄、数据新鲜度、回测失败、Token/费用。
  - 高基数 ID 不作为指标标签。

### SAL-P6-008 配置 SLO 与告警

- [ ] [TODO] 实现多窗口告警、预算阈值和 Runbook 链接
- 元数据：优先级 P0 | 负责人 TL/BE | 估算 1.5d | 实际 - | 依赖 SAL-P6-007
- 交付物：SLO、告警规则、路由、静默和演练。
- 验收：
  - 单一免费 Provider 波动不直接触发高优先级告警。
  - 数据发布阻断、队列积压和费用超限能及时触发。

### SAL-P6-009 实现备份策略

- [ ] [TODO] 备份数据库、Manifest、Artifact 元数据和用户配置
- 元数据：优先级 P0 | 负责人 BE/SEC | 估算 2d | 实际 - | 依赖 SAL-P2-017,SAL-P6-003
- 交付物：加密备份、保留、校验、RPO/RTO 监控。
- 验收：
  - 市场数据可重建与不可重建用户资产分类清晰。
  - 备份不包含明文密钥。

### SAL-P6-010 完成恢复演练

- [ ] [TODO] 从备份恢复数据库、Run、报告和 Artifact 引用
- 元数据：优先级 P0 | 负责人 BE/SEC | 估算 2d | 实际 - | 依赖 SAL-P6-009
- 交付物：恢复记录、实际 RPO/RTO、缺陷和改进项。
- 验收：
  - 不是只验证数据库启动；关键用户路径可用。
  - 恢复环境与生产隔离，数据一致性校验通过。

### SAL-P6-011 执行性能与容量测试

- [ ] [TODO] 测试全市场筛选、并发查询、回测和 Agent 任务
- 元数据：优先级 P0 | 负责人 BE/QE/AI | 估算 3d | 实际 - | 依赖 SAL-P3-016,SAL-P4-021,SAL-P5-017
- 交付物：负载模型、P50/P95/P99、资源曲线、容量上限。
- 验收：
  - 达到架构方案 SLO，或形成批准的降级/扩容计划。
  - 无无界内存、任务饥饿和 DuckDB 写锁冲突。

### SAL-P6-012 注入 API/Worker/Queue 故障

- [ ] [TODO] 验证重启、超时、重复投递、孤儿任务和取消
- 元数据：优先级 P0 | 负责人 BE | 估算 2.5d | 实际 - | 依赖 SAL-P2-018,SAL-P2-019
- 交付物：故障脚本、预期、恢复时间、数据一致性报告。
- 验收：
  - 无任务静默丢失、重复发布或错误成功状态。
  - Reconciler 和 checkpoint 行为符合设计。

### SAL-P6-013 注入 Provider/LLM 故障

- [ ] [TODO] 验证限流、空数据、Schema 漂移、预算和模型失败
- 元数据：优先级 P0 | 负责人 BE/AI/QE | 估算 2d | 实际 - | 依赖 SAL-P2-015,SAL-P5-012
- 交付物：故障矩阵、fallback/degrade 结果、告警记录。
- 验收：
  - Provider 错误不污染 Dataset。
  - 模型失败/超预算生成明确 partial，不重复收费。

### SAL-P6-014 注入磁盘与 Artifact 故障

- [ ] [TODO] 验证空间不足、写入中断、哈希错误和对象缺失
- 元数据：优先级 P0 | 负责人 BE | 估算 2d | 实际 - | 依赖 SAL-P1-007,SAL-P2-013
- 交付物：故障脚本、原子性和垃圾回收报告。
- 验收：
  - 不生成悬空成功记录。
  - 缺失/损坏 Artifact 可检测、隔离并告警。

### SAL-P6-015 完成端到端主路径测试

- [ ] [TODO] 覆盖同步 -> 筛选 -> 回测 -> 研究 -> 报告 -> 通知
- 元数据：优先级 P0 | 负责人 FE/BE/QE/AI | 估算 3d | 实际 - | 依赖 SAL-P6-011..014
- 交付物：Playwright/API E2E、固定 Run Bundle、截图。
- 验收：
  - desktop 和 standalone 至少各跑一次。
  - 断线、刷新、取消、partial、权限拒绝等状态覆盖。

### SAL-P6-016 完成升级与回滚演练

- [ ] [TODO] 从 DSA 基线/上一 Serenity 版本升级数据库与制品
- 元数据：优先级 P0 | 负责人 TL/BE | 估算 2.5d | 实际 - | 依赖 SAL-P1-013,SAL-P6-010
- 交付物：升级脚本、OpenAPI/Schema diff、回滚记录。
- 验收：
  - 迁移前检查、备份、升级、验证和回滚均自动化。
  - 历史报告、持仓和信号评价保持可访问。

### SAL-P6-017 执行 DSA 上游同步演练

- [ ] [TODO] 在临时分支同步一个后续 DSA release/commit
- 元数据：优先级 P0 | 负责人 TL | 估算 2.5d | 实际 - | 依赖 SAL-P0-012,SAL-P6-015
- 交付物：冲突分类、测试结果、补丁重放成本和决策。
- 验收：
  - 同步不直接发生在 main。
  - 可量化本地 divergence；不可维护冲突触发架构复审。

### SAL-P6-018 构建 Desktop RC

- [ ] [TODO] 打包、签名并验证 Windows/Desktop 安装升级
- 元数据：优先级 P1 | 负责人 FE/SEC | 估算 2.5d | 实际 - | 依赖 SAL-P6-003,SAL-P6-015
- 交付物：安装包、签名、校验和、安装/卸载测试。
- 验收：
  - 新装和升级均可运行，用户数据不被覆盖。
  - 密钥保存在 OS 安全存储。

### SAL-P6-019 构建 standalone RC

- [ ] [TODO] 生成锁定 digest 的 Web/API/Worker/Scheduler 镜像
- 元数据：优先级 P0 | 负责人 BE/SEC | 估算 2d | 实际 - | 依赖 SAL-P6-005,SAL-P6-015
- 交付物：Compose、镜像 digest、健康检查、资源限制。
- 验收：
  - 同一 RC digest 从 staging 推广，不重新构建。
  - 数据库/Redis/Artifact 挂载和升级说明完整。

### SAL-P6-020 完成发布制品与第三方通知

- [ ] [TODO] 生成 release notes、SBOM、许可证、迁移和兼容矩阵
- 元数据：优先级 P0 | 负责人 TL/SEC | 估算 2d | 实际 - | 依赖 SAL-P6-018,SAL-P6-019
- 交付物：RC 发布包、DSA/AlphaSift/Qlib 基线、已知问题。
- 验收：
  - 每个二进制/镜像有来源、digest 和签名。
  - 数据/模型服务条款按 Profile 登记，不把待审组件放入默认商业 Profile。

### SAL-P6-021 完成首套 Runbook

- [ ] [TODO] 覆盖架构方案第 31 节的 12 类故障
- 元数据：优先级 P0 | 负责人 TL/BE/AI | 估算 3d | 实际 - | 依赖 SAL-P6-008,SAL-P6-010,SAL-P6-012..014
- 交付物：可执行 Runbook、dry-run 命令、升级路径。
- 验收：
  - 每份包含症状、影响、确认、止损、恢复、校验和复盘。
  - 至少随机抽取 3 份由非作者演练成功。

### SAL-P6-022 完成 10 个交易日稳定运行

- [ ] [TODO] 在 RC 环境连续运行数据、筛选、回测和研究流水线
- 元数据：优先级 P0 | 负责人 TL/全员 | 估算 10 个交易日观察 | 实际 - | 依赖 SAL-P6-020,SAL-P6-021
- 交付物：每日 SLO、失败、费用、质量和人工干预记录。
- 验收：
  - 无未解释数据缺口、重复任务或严重报告错误。
  - SLO/预算达标；阻断缺陷清零，高风险问题有批准处理计划。

### SAL-P6-023 Gate G6：MVP 发布评审

- [ ] [TODO] 决定 stable 发布或继续 RC
- 元数据：优先级 P0 | 负责人 TL/RE/SEC | 估算 0.5d | 实际 - | 依赖 SAL-P6-001..022
- 交付物：发布决议、签字、遗留风险和下一版本范围。
- 验收：
  - 功能、数据、量化、Agent、安全、运维、许可证和恢复证据齐全。
  - 未通过任一硬 Gate 时不得以“已知问题”名义强行发布。

## 10. 跨阶段持续任务

以下任务不计入 129 个交付任务，但每周必须执行：

- [ ] 每周同步进度看板、实际人日、关键路径和预计完成日期。
- [ ] 每周复核 BLOCKED 任务；超过 2 个工作日必须升级 TL。
- [ ] 每周更新风险登记、许可证/漏洞和数据服务条款变化。
- [ ] 每周检查 DSA upstream release、安全公告和高价值修复。
- [ ] 每周检查 Agent Token/费用、Provider 成功率和 Dataset 质量趋势。
- [ ] 每个 Phase Gate 后重新估算剩余范围，不沿用已经失真的初始估算。
- [ ] 每两周清理 DEFERRED/CANCELLED/过期 Feature Flag 和临时兼容路径。
- [ ] 每个 release 更新 ADR、OpenAPI diff、迁移和 Runbook。

## 11. 周进度记录模板

```markdown
### YYYY-MM-DD 第 N 周

- 总体状态：GREEN / AMBER / RED
- 当前 Phase / Gate：
- 本周完成任务 ID：
- 下周计划任务 ID：
- 关键路径变化：
- 新增/关闭风险：
- 阻塞项与负责人：
- 估算偏差：
- 质量指标：测试、覆盖率、缺陷、SLO、数据质量、Agent 引用/费用
- 需要决策：
```

状态判定：

- `GREEN`：Gate 预计按期完成，无未控制高风险。
- `AMBER`：关键路径预计延迟 <= 1 周，或存在有缓解方案的高风险。
- `RED`：关键路径预计延迟 > 1 周、硬 Gate 失败、出现未控制安全/数据/许可证风险。

## 12. 阻塞项登记

| ID | 关联任务 | 阻塞原因 | 负责人 | 开始日期 | 下次复查 | 解除条件 | 状态 |
|---|---|---|---|---|---|---|---|
| BLK-001 | - | - | - | - | - | - | CLOSED |
| BLK-002 | SAL-P0-004 | 已解除：CI 依赖可用，backend syntax/flake8/deterministic/collect/offline-tests 已正式复跑并记录；顺序依赖失败通过 `DSA-PATCH-001` 修复 | BE | 2026-07-19 | 2026-07-19 | 已运行 `scripts/run-dsa-backend-offline-baseline.sh`，记录测试数量、失败分类和证据 | CLOSED |
| BLK-003 | SAL-P0-005 | 已解除：`DSA-PATCH-002` 对齐 JP/KR market-light 测试契约；`DSA-PATCH-003` 对齐真实 Web smoke E2E；`scripts/seed-dsa-web-smoke-fixture.sh` 提供本地 auth/history fixture | FE | 2026-07-19 | 2026-07-19 | 已运行 `npm run test` 得到 `965 passed, 2 skipped`；真实 `npm run test:smoke -- --reporter=line` 得到 `13 passed`、无 skipped | CLOSED |
| BLK-004 | SAL-P0-011 | 已解除：Python/Node/镜像 SBOM、许可证和漏洞基线已生成；Critical/High 已登记 owner、计划和截止任务 | SEC | 2026-07-19 | 2026-07-19 | 已运行 `scripts/run-dsa-supply-chain-baseline.sh`，记录 Python audit、Web audit、Syft SBOM 和 Grype 漏洞摘要 | CLOSED |

规则：

- 阻塞超过 2 个工作日由 TL 决定拆分、降级、替代或升级。
- 外部服务等待不应让可并行的 Stub/契约工作停止。
- 解除阻塞后在任务下记录解决方式，不能直接删除登记。

## 13. 风险与决策登记

### 13.1 风险

| ID | 风险 | 概率 | 影响 | 触发信号 | 缓解 | 负责人 | 到期 | 状态 |
|---|---|---|---|---|---|---|---|---|
| RSK-001 | DSA 上游快速分叉 | 高 | 高 | 同步冲突持续增加 | Facade、最小补丁、同步演练 | TL | G6 | OPEN |
| RSK-002 | PIT 数据时间不可信 | 中 | 极高 | 财报缺 announced/available | 可信等级、硬门禁、商业源 | QE | G2 | OPEN |
| RSK-003 | Agent 引用/幻觉 | 高 | 高 | 无依据数字/错引 | Evidence、Validator、金标 | AI | G5 | OPEN |
| RSK-004 | 免费 Provider 不稳定 | 高 | 高 | 限流/Schema 漂移 | `SAL-P2-001` 锁定错误分类、Provenance 和离线 Contract Test；`SAL-P2-015` 继续负责 Policy、fallback 和契约探针 | BE | G2 | OPEN |
| RSK-005 | 许可证/服务条款冲突 | 中 | 高 | 待审依赖进入发行物 | SBOM、Profile 门禁、法律审查 | SEC | G6 | OPEN |
| RSK-006 | 锁定 release 后遗漏 main 上高价值修复 | 中 | 中 | 上游 main 出现文档修复或 DecisionSignal 契约增强 | 已由 ADR-001 关闭初始候选漂移风险：`55946536` 仅作为后续同步/Runbook 文档候选，不改当前基线；`487e49e5` 延期至 `sync/dsa-487e49e5` 分支评审；未来上游快速分叉继续由 `RSK-001` 管理 | TL | SAL-P1-001 | CLOSED |
| RSK-007 | 本地仓库曾未绑定本项目 `origin` 远端 | 中 | 中 | 需要推送 checkpoint、创建 PR 或同步团队远端时发现无 `origin` | 已配置 `origin` 为 `git@github.com:zcxGGmu/serenity-alpha-lab.git`，并保留 `upstream` 为官方 DSA；后续同步/PR 前复验双 remote | TL | SAL-P0-012 | CLOSED |
| RSK-008 | DSA Python 依赖未锁定且包含动态 Git 安装 | 高 | 高 | 新机器或 CI 上 `pip install -r requirements.txt` 或 `[project].dependencies` 解析出不同版本或 AlphaSift Git 依赖不可达 | 已由 `SAL-P1-003` 对 Serenity root 依赖关闭：`uv.lock` 是权威锁，`requirements.txt` 由 lock 导出并由脚本校验漂移，生产/桌面安装面不包含 `git+https` 或 AlphaSift Git URL；DSA 隔离 worktree 保持原样，AlphaSift 审查后 wheel/package intake 由后续 Adapter 任务处理 | BE/SEC | SAL-P1-003 | CLOSED |
| RSK-009 | 当前 Windows PATH 缺少 Python 3.11；Docker daemon 需在恢复时复验 | 中 | 中 | 恢复会话时本地工具链不可用 | 已用 Python 3.11.15 建立 `.cache/dsa-p0/venv` 并完成 `SAL-P0-004`；Orbstack Docker daemon 已用于完成 `SAL-P0-007`，后续 Docker/SBOM 任务仍需先复验 `docker info` | BE | SAL-P0-011 | CLOSED |
| RSK-010 | DSA Web npm audit 存在 10 个 high 漏洞 | 高 | 高 | `npm audit` 输出 16 个漏洞，其中 high 为 10 个 | P0 阶段不运行 `npm audit fix` 改写上游 lock；已在 `SAL-P0-011` 记录 owner/计划，后续由受控上游同步、依赖升级或 `SAL-P6-005` 门禁阻断未豁免 Critical/High | SEC/FE | SAL-P6-005 | OPEN |
| RSK-011 | DSA Web lockfile 混用 npmjs 与 npmmirror resolved URL | 中 | 中 | `package-lock.json` 同时包含 `registry.npmjs.org` 与 `registry.npmmirror.com` | Gate G0 接受该风险；`SAL-P1-003` 仅治理 Python root lock，不改写上游 Web lockfile；后续由受控前端依赖升级或发布前依赖治理统一 registry 策略 | SEC/FE | SAL-P6-005 | OPEN |
| RSK-012 | DSA Docker image 存在 Critical/High 漏洞 | 高 | 高 | Grype 扫描 `serenity-dsa-p0:sal-p0-007` 输出 39 critical、84 high | 已在 `SAL-P0-011` 记录 SBOM 与 Grype baseline；BE/SEC 在 `SAL-P6-005` 前通过修复 base image、apt upgrade、依赖锁或正式豁免关闭 | BE/SEC | SAL-P6-005 | OPEN |

### 13.2 决策

| 决策 ID | 日期 | 问题 | 结论 | ADR/证据 | 影响任务 | 复审日期 |
|---|---|---|---|---|---|---|
| DEC-001 | 2026-07-19 | DSA 正式基线 | 采用 `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；拒绝未发布 `main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa` 作为初始基线 | [upstream-baseline-selection.md](./upstream-baseline-selection.md)；[ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) | SAL-P0-001,SAL-P0-002,SAL-P1-001 | G1 |
| DEC-002 | 2026-07-19 | DSA Git 历史接管方式 | 通过 `upstream` remote 导入上游 heads/tags，创建本地不可变基线 tag `upstream/dsa-v3.26.1`；不合并、不切换、不压平复制 DSA 源码 | [upstream-history-import.md](./upstream-history-import.md)；[ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) | SAL-P0-002,SAL-P0-012,SAL-P1-001 | G1 |
| DEC-003 | 2026-07-19 | DSA 基线环境物化方式 | 通过 `.worktrees/dsa-v3.26.1` 隔离物化上游 tag，通过 `.cache/dsa-p0` 存放 Python/npm 缓存；本项目工作树只提交脚本和文档，不混入 DSA 源码 | [dsa-baseline-environment.md](./dsa-baseline-environment.md) | SAL-P0-003,SAL-P0-004,SAL-P0-005,SAL-P0-007 | G0 |
| DEC-004 | 2026-07-19 | Web 基线失败处理方式 | 对阻断 Gate 的 Web 测试契约漂移采用登记补丁而非产品范围扩展：`DSA-PATCH-002` 保持 market-light 仅支持 `cn/hk/us`，`DSA-PATCH-003` 对齐当前 Web smoke UI/fixture；仍不运行 `npm audit fix` 改写上游 lockfile | [web-baseline-test-build.md](./web-baseline-test-build.md); [upstream-patches.md](./upstream-patches.md) | SAL-P0-005,SAL-P0-011,SAL-P0-012 | G0 |
| DEC-005 | 2026-07-19 | 供应链基线处理方式 | P0 供应链生成 SBOM、license 和漏洞基线，但不在 P0 直接改写上游 lockfile/base image；Critical/High 通过 owner、计划、截止任务进入后续门禁 | [supply-chain-baseline.md](./supply-chain-baseline.md) | SAL-P0-011,SAL-P0-012,SAL-P6-005 | G0 |
| DEC-006 | 2026-07-19 | 锁定 DSA release 上的最小本地补丁 | 对阻断基线 gate 的上游缺陷/测试契约漂移使用可登记、可复跑的 patch 文件；当前携带 `DSA-PATCH-001`、`DSA-PATCH-002`、`DSA-PATCH-003`，补丁只应用到隔离 worktree，不把 DSA 源码混入本项目工作树 | [upstream-patches.md](./upstream-patches.md) | SAL-P0-004,SAL-P0-005,SAL-P0-012 | G0 |
| DEC-007 | 2026-07-19 | API 与配置契约冻结源 | 上游静态 `docs/architecture/api_spec.json` 已滞后，P0 以锁定 worktree 中 `create_app().openapi()` 运行时输出作为 OpenAPI 冻结源；配置契约以 `src.core.config_registry.build_schema_response()`、`Config` dataclass、`.env.example` 和代码环境变量引用生成 inventory | [api-config-contract-baseline.md](./api-config-contract-baseline.md); [baselines/dsa-v3.26.1/api-config/summary.json](./baselines/dsa-v3.26.1/api-config/summary.json) | SAL-P0-008,SAL-P0-012,SAL-P0-013 | G0 |
| DEC-008 | 2026-07-19 | 数据库 Schema 与 fixture 冻结方式 | P0 以锁定 worktree 的 `src.storage.Base.metadata.create_all()` 和 `DatabaseManager` 兼容迁移后的实际 SQLite 形状作为冻结源；提交稳定 SQL/JSON 快照和内容哈希，不提交运行时 SQLite 二进制文件 | [database-schema-baseline.md](./database-schema-baseline.md); [baselines/dsa-v3.26.1/database/summary.json](./baselines/dsa-v3.26.1/database/summary.json) | SAL-P0-009,SAL-P1-012,SAL-P1-013 | G0 |
| DEC-009 | 2026-07-20 | 报告与 Signal Evaluation 金标冻结方式 | P0 以离线 Stub LLM JSON、固定时钟和合成行情输入冻结 DSA 报告渲染与 Signal Evaluation 行为；提交稳定 Markdown/JSON 快照和内容哈希，不触发真实 Provider、真实 LLM 或通知发送 | [report-signal-golden-baseline.md](./report-signal-golden-baseline.md); [baselines/dsa-v3.26.1/report-signal/summary.json](./baselines/dsa-v3.26.1/report-signal/summary.json) | SAL-P0-010,SAL-P4-001,SAL-P5-017 | G0 |
| DEC-010 | 2026-07-20 | 上游维护与 required checks 策略 | P0 通过根目录 `UPSTREAM_BASE.md` 固化上游基线、偏离分类和同步流程；通过 `.github/workflows/p0-required-baselines.yml` 建立四个 required check 候选，覆盖后端、Web、契约/金标、Docker/供应链基线 | [UPSTREAM_BASE.md](../UPSTREAM_BASE.md); [.github/workflows/p0-required-baselines.yml](../.github/workflows/p0-required-baselines.yml) | SAL-P0-012,SAL-P0-013,SAL-P6-017 | G0 |
| DEC-011 | 2026-07-20 | Gate G0 基线接管评审 | `GO with accepted risks`：正式采用 DSA `v3.26.1` 作为 P1 工程加固基线；P0 供应链和依赖风险不阻断 P1，但继续阻断发布或未评审上游漂移 | [gate-g0-baseline-review.md](./gate-g0-baseline-review.md) | SAL-P0-013,SAL-P1-001,SAL-P6-005 | SAL-P1-001 |
| DEC-012 | 2026-07-20 | 上游接管、同步和补丁策略 | 批准 ADR-001：当前基线继续锁定 DSA `v3.26.1`；所有上游吸收必须经 `sync/dsa-*` 分支、补丁结果登记、相关 P0 baseline 刷新和 Gate/ADR 记录；`55946536` 不 cherry-pick，`487e49e5` 延期评审 | [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) | SAL-P1-001,SAL-P1-002,SAL-P6-017 | G1 或 2026-08-03 |
| DEC-013 | 2026-07-20 | 渐进式模块化和 Compatibility Facade | 批准 ADR-002：P1 先在单仓内建立 domain/application/ports/facade 边界，不拆微服务；旧 DSA 路径只能经显式 Facade 迁移；删除旧路径必须满足 characterization、contract、迁移和观察窗口条件 | [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md) | SAL-P1-001,SAL-P1-004,SAL-P1-008,SAL-P1-009,SAL-P1-016 | G1 或 2026-08-03 |
| DEC-014 | 2026-07-20 | P1 Python 元数据与目标包骨架落地方式 | 采用根 `pyproject.toml` + `serenity_alpha_lab` 自有包骨架；DSA runtime source 继续隔离在 `.worktrees/dsa-v3.26.1`，通过 dry-run 可验证的 console wrappers 暴露 CLI/API/Worker/测试入口；extras/lock 和动态 Git 依赖关闭延期至 `SAL-P1-003` | [python-project-metadata.md](./python-project-metadata.md); [pyproject.toml](../pyproject.toml) | SAL-P1-002,SAL-P1-003,SAL-P1-004 | G1 |
| DEC-015 | 2026-07-20 | Python 依赖锁与安装面 | `uv.lock` 是 root Python 权威锁；`requirements.txt` 只导出 `core+providers+desktop`，不含 `quant/dev`，不含 `pyqlib`，不含动态 Git；AlphaSift 生产 intake 延后到审查后 wheel/package 决策 | [python-dependency-lock.md](./python-dependency-lock.md); [pyproject.toml](../pyproject.toml); [uv.lock](../uv.lock); [requirements.txt](../requirements.txt) | SAL-P1-003,SAL-P3-001,SAL-P6-005 | G1 |
| DEC-016 | 2026-07-20 | Run/Stage/Event 领域生命周期 | 采用纯 domain 聚合表达运行状态、阶段、追加事件、retry attempt 和 idempotency conflict；持久化、TaskBackend、Trace 和 Artifact 在后续任务基于该契约实现 | [run-stage-event-domain-model.md](./run-stage-event-domain-model.md); [run_lifecycle.py](../src/serenity_alpha_lab/domain/run_lifecycle.py) | SAL-P1-006,SAL-P1-007,SAL-P1-008,SAL-P1-011 | G1 |
| DEC-017 | 2026-07-20 | 统一证券 ID 和旧 symbol 兼容口径 | 采用纯 domain `InstrumentId` 作为跨市场证券身份，canonical 格式为 `<symbol>.<exchange>`；旧 DSA/Yahoo symbol 通过显式 `from_legacy()`、`ProviderSymbolMapping` 和 `to_dsa_symbol()` 适配；裸 6 位代码无市场上下文时拒绝，避免跨市场主键碰撞 | [instrument-id-domain-model.md](./instrument-id-domain-model.md); [instruments.py](../src/serenity_alpha_lab/domain/instruments.py) | SAL-P1-005,SAL-P2-001,SAL-P2-003,SAL-P2-005 | G1 |
| DEC-018 | 2026-07-20 | Artifact 内容寻址与本地发布口径 | 采用纯 domain Artifact manifest + `ArtifactStore` Protocol；本地实现以 SHA-256 blob 和 JSON manifest 分离存储，manifest 最后原子发布，失败写入不得产生可查询记录 | [artifact-store-domain-model.md](./artifact-store-domain-model.md); [artifacts.py](../src/serenity_alpha_lab/domain/artifacts.py); [local_artifact_store.py](../src/serenity_alpha_lab/repositories/local_artifact_store.py) | SAL-P1-007,SAL-P2-007,SAL-P4-004,SAL-P5-001 | G1 |
| DEC-019 | 2026-07-20 | TaskBackend 兼容外壳口径 | 采用应用层 `TaskBackend` Protocol + `InMemoryTaskBackend`；DSA `AnalysisTaskQueue` 只通过注入式 facade 和 handler registry 包裹，不在 Serenity application/API 直接暴露 `ThreadPoolExecutor` 假设 | [task-backend-facade.md](./task-backend-facade.md); [task_backend.py](../src/serenity_alpha_lab/application/task_backend.py); [task_backend.py](../src/serenity_alpha_lab/integrations/dsa/task_backend.py) | SAL-P1-008,SAL-P2-018,SAL-P1-016 | G1 |
| DEC-020 | 2026-07-20 | 结构化日志与 Trace 上下文口径 | 采用 stdlib-only `TraceContext` + ContextVar + JSON formatter + ASGI middleware；日志输出默认包含 trace/run/stage/user 字段并递归脱敏 secret、token、prompt、messages 和 body/content | [structured-trace-logging.md](./structured-trace-logging.md); [tracing.py](../src/serenity_alpha_lab/application/tracing.py) | SAL-P1-011,SAL-P6-001,SAL-P6-006 | G1 |
| DEC-021 | 2026-07-20 | 配置 Profile 与密钥边界口径 | 采用应用层 `RuntimeSettings` + `RuntimeProfile` + `ProfilePolicy`；CI profile 默认禁用网络、模型和 Provider 调用并拒绝真实 key，standalone/service profile 只允许无副作用预览，不通过 profile API 改写部署 `.env` | [config-profile-facade.md](./config-profile-facade.md); [config_profiles.py](../src/serenity_alpha_lab/application/config_profiles.py) | SAL-P1-014,SAL-P1-010,SAL-P1-012,SAL-P2-001 | G1 |
| DEC-022 | 2026-07-20 | ResearchOrchestrator 兼容外壳口径 | 采用应用层 `ResearchOrchestrator` Protocol + DTO；DSA `AgentOrchestrator` / `AgentExecutor` 只通过注入式 facade 包裹，保留 `AgentResult` 字段语义，不在 application 层导入具体 DSA Agent runtime | [research-orchestrator-facade.md](./research-orchestrator-facade.md); [research_orchestrator.py](../src/serenity_alpha_lab/application/research_orchestrator.py); [research_orchestrator.py](../src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py) | SAL-P1-009,SAL-P5-001,SAL-P5-011 | G1 |
| DEC-023 | 2026-07-20 | API Problem Details 错误协议口径 | 采用应用层 `ProblemDetail` + 稳定 `ApiErrorCode` + 框架无关 ASGI middleware；validation/not-found/conflict/provider/internal 分层映射，未知内部异常不暴露 stack trace、绝对路径、secret、prompt 或 body/content | [api-error-protocol.md](./api-error-protocol.md); [api_errors.py](../src/serenity_alpha_lab/application/api_errors.py) | SAL-P1-010,SAL-P1-016,SAL-P2-001,SAL-P2-018 | G1 |
| DEC-024 | 2026-07-20 | Alembic Schema 入口与 DSA baseline revision | Alembic 成为 Serenity root 唯一新增 Schema 创建入口；首个 revision `20260720_dsa_v3261_baseline` 由 P0 DSA SQLite snapshot 生成，启动前使用 `assert_database_at_head()` 检查而不是静默 `create_all` | [storage-migration-alembic.md](./storage-migration-alembic.md); [alembic.ini](../alembic.ini); [storage_migrations.py](../src/serenity_alpha_lab/repositories/storage_migrations.py) | SAL-P1-012,SAL-P1-013,SAL-P1-015,SAL-P1-016 | G1 |
| DEC-025 | 2026-07-20 | 历史 SQLite 升级验证口径 | 对已有 DSA SQLite 历史库采用 backup -> Alembic stamp -> business row/content hash verify；当前 baseline 不重跑 DDL，`alembic_version` 以外业务内容必须保持不变，失败时恢复备份 | [sqlite-upgrade-verification.md](./sqlite-upgrade-verification.md); [sqlite_upgrade.py](../src/serenity_alpha_lab/repositories/sqlite_upgrade.py) | SAL-P1-013,SAL-P1-015,SAL-P1-016 | G1 |
| DEC-026 | 2026-07-20 | Desktop 兼容与性能基线口径 | `SAL-P1-015` 采用离线 P0 Desktop/API/CLI/Bot/契约金标矩阵和本地性能脚本作为 G1 兼容证据；启动阈值 `60s`、report/signal 阈值 `60s`、离线单股报告生成阈值 `5s`，所有运行产物只落 `.cache/dsa-p0` | [desktop-compatibility-performance-baseline.md](./desktop-compatibility-performance-baseline.md); [run-p1-desktop-compatibility-performance.sh](../scripts/run-p1-desktop-compatibility-performance.sh) | SAL-P1-015,SAL-P1-016 | G1 |
| DEC-027 | 2026-07-20 | Gate G1 工程地基评审 | `GO with accepted risks`：P1 工程加固完成，允许进入 P2；P2 必须沿用 P1 的 lock、domain/application/repository/facade、Artifact、Trace、ProblemDetails、Profile 和 Alembic 边界，供应链/Web/Docker 风险继续阻断发布但不阻断 P2 | [gate-g1-engineering-foundation-review.md](./gate-g1-engineering-foundation-review.md) | SAL-P1-016,SAL-P2-001,SAL-P2-018,SAL-P6-005 | G2 |
| DEC-028 | 2026-07-21 | Provider 领域契约口径 | 采用同步、stdlib-only 的 `MarketDataProvider` Protocol；能力由 `ProviderCapabilities` 声明，结果统一为携带 schema/Provenance/freshness/warnings 的泛型不可变 `DataBatch`；六类 Provider 错误供后续 retry/fallback policy 使用，应用边界统一映射为既有 `provider_error` | [provider-domain-contract.md](./provider-domain-contract.md); [providers.py](../src/serenity_alpha_lab/domain/providers.py); [api_errors.py](../src/serenity_alpha_lab/application/api_errors.py) | SAL-P2-001,SAL-P2-002,SAL-P2-004,SAL-P2-015 | G2 |
| DEC-029 | 2026-07-21 | DSA Provider 兼容适配口径 | 采用窄 adapter 包裹 DSA `DataFetcherManager.get_daily_data()` 和 Pandas daily-bar 输出，真实 DSA manager 只允许通过 profile guard 后 lazy 构造；默认测试路径使用注入式 manager，旧单股历史查询通过显式 feature flag facade 在 legacy 与 Provider contract 路径切换 | [dsa-provider-compatibility-adapter.md](./dsa-provider-compatibility-adapter.md); [provider_adapter.py](../src/serenity_alpha_lab/integrations/dsa/provider_adapter.py); [test_dsa_provider_adapter.py](../tests/integrations/test_dsa_provider_adapter.py) | SAL-P2-002,SAL-P2-003,SAL-P2-004,SAL-P2-015 | G2 |
| DEC-030 | 2026-07-21 | DSA 证券代码兼容迁移口径 | 采用 `DsaStockCodeCompatibilityMapper` 在 DSA integration 边界包裹 `normalize_stock_code` 兼容语义；新领域路径统一携带 `InstrumentId.canonical`，Provider 调用显式生成 `dsa` / `yahoo` symbol mapping，裸 6 位只在 legacy facade 带 CN 上下文时兼容，避免跨市场主键碰撞 | [dsa-symbol-compatibility-migration.md](./dsa-symbol-compatibility-migration.md); [symbol_compatibility.py](../src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py); [test_dsa_symbol_compatibility.py](../tests/integrations/test_dsa_symbol_compatibility.py) | SAL-P2-003,SAL-P2-005,SAL-P2-015 | G2 |
| DEC-031 | 2026-07-21 | Bronze 原始响应审计落盘口径 | 采用 repository 层 `BronzeRawStore` 复用 P1 `ArtifactStore` 内容寻址与 manifest-last 发布；Provider 原始响应先递归脱敏，再写 deterministic JSON + gzip envelope，记录 provider/operation/request/time/source hash/sanitized hash/field lineage/trace/run/stage，默认 archive retention；本任务不发布 Dataset 或实现 fallback policy | [bronze-raw-data-layer.md](./bronze-raw-data-layer.md); [bronze_raw_store.py](../src/serenity_alpha_lab/repositories/bronze_raw_store.py); [test_bronze_raw_store.py](../tests/repositories/test_bronze_raw_store.py) | SAL-P2-004,SAL-P2-005,SAL-P2-007,SAL-P2-015 | G2 |
| DEC-032 | 2026-07-21 | 证券主数据 Dataset 口径 | 采用 `datasets.instrument_master` 表达历史有效期 instrument master；证券身份复用 canonical `InstrumentId`，Provider 外部代码复用 `ProviderSymbolMapping` 并增加有效期和 Bronze lineage；Dataset 发布为 deterministic JSON Artifact，当前不建立 Catalog/latest alias、不实现 PIT/fallback policy 或真实 Provider 调用 | [instrument-master-dataset.md](./instrument-master-dataset.md); [instrument_master.py](../src/serenity_alpha_lab/datasets/instrument_master.py); [test_instrument_master.py](../tests/datasets/test_instrument_master.py) | SAL-P2-005,SAL-P2-006,SAL-P2-007,SAL-P2-009,SAL-P2-011 | G2 |

## 14. 验收证据登记

| Evidence ID | 任务/Gate | 类型 | 路径/URL | commit/版本 | 评审人 | 日期 |
|---|---|---|---|---|---|---|
| AEV-001 | SAL-P0-001 | 报告/API 查询记录 | [upstream-baseline-selection.md](./upstream-baseline-selection.md) | DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; candidate `main@487e49e565ffd1b96a7cf4d855f99cee3c981eaa` | TL | 2026-07-19 |
| AEV-002 | SAL-P0-002 | Git remote/tag/对象完整性记录 | [upstream-history-import.md](./upstream-history-import.md) | `upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `upstream/main @ 487e49e565ffd1b96a7cf4d855f99cee3c981eaa` | TL | 2026-07-19 |
| AEV-003 | SAL-P0-003 | 环境矩阵与 bootstrap 校验记录 | [dsa-baseline-environment.md](./dsa-baseline-environment.md) | Python 3.11/3.12；Node `>=20.19.0 <27`；Docker `python:3.11-slim-bookworm`；DSA `upstream/dsa-v3.26.1` | BE | 2026-07-19 |
| AEV-004 | SAL-P0-004 | 后端离线 gate 通过记录 | [backend-offline-test-baseline.md](./backend-offline-test-baseline.md) | DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; Python `3.11.15`; pytest `9.1.1`; `DSA-PATCH-001`; `4455 passed, 4 deselected` | BE | 2026-07-19 |
| AEV-005 | SAL-P0-005 | Web 依赖安装、lint、test、build、smoke 基线记录 | [web-baseline-test-build.md](./web-baseline-test-build.md) | DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; Node `v24.12.0`; npm `11.6.2`; Vite `7.3.1`; `DSA-PATCH-002`; `DSA-PATCH-003`; Vitest `965 passed, 2 skipped`; Playwright smoke `13 passed` | FE | 2026-07-19 |
| AEV-006 | SAL-P0-011 | 供应链 SBOM、许可证和漏洞基线记录 | [supply-chain-baseline.md](./supply-chain-baseline.md) | Python SBOM 146 components; Web npm audit 16 vulnerabilities / 10 high; Web license inventory 529 packages; Syft image SBOM 7865 components; Grype 39 critical / 84 high | SEC | 2026-07-19 |
| AEV-007 | SAL-P0-006 | Desktop、CLI、本地 API 与 Bot 离线 smoke 记录 | [desktop-cli-bot-smoke-baseline.md](./desktop-cli-bot-smoke-baseline.md) | DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; Python `3.11.15`; Node `v25.9.0`; npm `11.12.1` | FE/AI | 2026-07-19 |
| AEV-008 | SAL-P0-007 | Docker build、server health 与 analyzer import smoke 记录 | [docker-baseline.md](./docker-baseline.md) | `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`; Docker `29.4.0`; Compose `5.1.3` | BE | 2026-07-19 |
| AEV-009 | SAL-P0-008 | OpenAPI 与配置契约快照、diff gate 记录 | [api-config-contract-baseline.md](./api-config-contract-baseline.md); [baselines/dsa-v3.26.1/api-config/summary.json](./baselines/dsa-v3.26.1/api-config/summary.json) | OpenAPI `3.1.0`; 105 paths / 119 operations / 186 schemas; config schema 179 fields; config inventory 386 fields; `scripts/run-dsa-api-config-baseline.sh` PASS | BE | 2026-07-19 |
| AEV-010 | SAL-P0-009 | SQLite Schema、表/索引元数据、脱敏 fixture 与内容哈希基线 | [database-schema-baseline.md](./database-schema-baseline.md); [baselines/dsa-v3.26.1/database/summary.json](./baselines/dsa-v3.26.1/database/summary.json) | 28 tables; 177 indexes; 31 fixture rows; `scripts/run-dsa-database-baseline.sh` PASS; SQL restore/FK/content-hash round-trip PASS; `fixture.sql` SHA-256 `382f4719d813f20b233786d90b0b5de66637a40d7ae35de61c69c4b0f57fa931` | BE | 2026-07-19 |
| AEV-011 | SAL-P0-010 | 报告 Markdown、结构化报告、Signal Evaluation 与内容哈希金标 | [report-signal-golden-baseline.md](./report-signal-golden-baseline.md); [baselines/dsa-v3.26.1/report-signal/summary.json](./baselines/dsa-v3.26.1/report-signal/summary.json) | 2 structured reports; 3 Markdown reports; 6 Signal Evaluation cases; `scripts/run-dsa-report-signal-baseline.sh` PASS; targeted upstream tests `137 passed`; `summary.json` SHA-256 `01e7c0ec1a7070f5e7923414e7ef57f1ef5eb40d9c3bbf26da4ce3529bed0adb` | AI/QE | 2026-07-20 |
| AEV-012 | SAL-P0-012 | 上游维护文档、偏离分类和 CI required checks 记录 | [UPSTREAM_BASE.md](../UPSTREAM_BASE.md); [.github/workflows/p0-required-baselines.yml](../.github/workflows/p0-required-baselines.yml); [upstream-patches.md](./upstream-patches.md) | `DSA-PATCH-001..003` classified `compatible`; no current `divergence`; required checks: backend, web, contract/golden, docker/supply-chain; workflow YAML parse PASS; referenced scripts present; `git diff --check` PASS | TL | 2026-07-20 |
| AEV-013 | SAL-P0-013 / Gate G0 | Gate G0 Go/No-Go 评审、接受风险和 P1 入口约束 | [gate-g0-baseline-review.md](./gate-g0-baseline-review.md) | Decision `GO with accepted risks`; P0 13/13; baseline `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; accepted risks `RSK-006`, `RSK-008`, `RSK-010`, `RSK-011`, `RSK-012`; lightweight verification PASS | TL/RE/SEC | 2026-07-20 |
| AEV-014 | SAL-P1-001 | ADR-001/ADR-002 批准记录和候选上游 commit 处理 | [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md); [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md) | DSA baseline remains `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `55946536` doc-only candidate deferred; `487e49e5` DecisionSignal persistence candidate deferred to sync branch; no runtime source import in SAL-P1-001 | TL | 2026-07-20 |
| AEV-015 | SAL-P1-002 | Python 项目元数据、依赖声明迁移和安装入口验证 | [pyproject.toml](../pyproject.toml); [python-project-metadata.md](./python-project-metadata.md); [test_project_metadata.py](../tests/architecture/test_project_metadata.py) | PEP 621 metadata; Python `>=3.11,<3.13`; 42 runtime dependencies migrated from DSA baseline; `pip install -e . --no-deps` PASS; DSA CLI/API/Worker/test dry-run scripts exit 0 | BE | 2026-07-20 |
| AEV-016 | SAL-P1-004 | 目标包骨架和架构边界测试 | [src/serenity_alpha_lab](../src/serenity_alpha_lab); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | package skeleton created; architecture tests enforce domain/framework, quant/agent-notification, integration/repository boundaries; `pytest tests/architecture -q` PASS `7 passed`; `py_compile` PASS; no Quant Core/PIT/formal backtest implementation | TL/BE | 2026-07-20 |
| AEV-017 | SAL-P1-003 | Python extras、lock、requirements 导出和 drift guard | [python-dependency-lock.md](./python-dependency-lock.md); [uv.lock](../uv.lock); [requirements.txt](../requirements.txt); [verify-python-dependency-lock.sh](../scripts/verify-python-dependency-lock.sh); [test_dependency_locking.py](../tests/architecture/test_dependency_locking.py) | `uv lock` resolved 296 packages; `scripts/verify-python-dependency-lock.sh` PASS; production requirements excludes `pyqlib` and dynamic Git; architecture tests `11 passed`; full pytest `15 passed` | BE/SEC | 2026-07-20 |
| AEV-018 | SAL-P1-006 | Run/Stage/Event 纯领域模型和状态转换测试 | [run-stage-event-domain-model.md](./run-stage-event-domain-model.md); [run_lifecycle.py](../src/serenity_alpha_lab/domain/run_lifecycle.py); [test_run_lifecycle.py](../tests/domain/test_run_lifecycle.py) | append-only monotonic events, terminal rollback rejection, retry new attempt, idempotency conflict; domain tests `4 passed`; py_compile PASS | BE | 2026-07-20 |
| AEV-019 | SAL-P1-005 | InstrumentId 纯领域模型、旧 symbol 兼容映射和跨市场往返测试 | [instrument-id-domain-model.md](./instrument-id-domain-model.md); [instruments.py](../src/serenity_alpha_lab/domain/instruments.py); [test_instrument_id.py](../tests/domain/test_instrument_id.py) | A/HK/US/JP/KR/TW canonical round-trip; DSA/Yahoo legacy mapping; bare 6-digit ambiguity guard; target Red failed on missing module; Green `37 passed`; architecture/domain `52 passed` | QE/BE | 2026-07-20 |
| AEV-020 | SAL-P1-007 | Artifact 纯领域模型、本地内容寻址存储和原子发布测试 | [artifact-store-domain-model.md](./artifact-store-domain-model.md); [artifacts.py](../src/serenity_alpha_lab/domain/artifacts.py); [local_artifact_store.py](../src/serenity_alpha_lab/repositories/local_artifact_store.py); [test_artifacts.py](../tests/domain/test_artifacts.py); [test_local_artifact_store.py](../tests/repositories/test_local_artifact_store.py) | content-addressed URI/manifest; failed manifest publish leaves no record/temp/blob files; hash/size/schema/run/retention queryable; target Green `6 passed`; architecture/domain/repositories `58 passed` | BE | 2026-07-20 |
| AEV-021 | SAL-P1-008 | TaskBackend Protocol、InMemory 实现、DSA 兼容 Facade 和线程池边界测试 | [task-backend-facade.md](./task-backend-facade.md); [task_backend.py](../src/serenity_alpha_lab/application/task_backend.py); [task_backend.py](../src/serenity_alpha_lab/integrations/dsa/task_backend.py); [test_task_backend_contract.py](../tests/application/test_task_backend_contract.py); [test_dsa_task_backend_facade.py](../tests/integrations/test_dsa_task_backend_facade.py) | submit/get/cancel/subscribe contract; DSA injected queue facade; no application/facade ThreadPoolExecutor import; target Green `12 passed`; full pytest `66 passed` | BE | 2026-07-20 |
| AEV-022 | SAL-P1-011 | Trace context、结构化 JSON 日志、脱敏和 ASGI middleware 测试 | [structured-trace-logging.md](./structured-trace-logging.md); [tracing.py](../src/serenity_alpha_lab/application/tracing.py); [test_trace_context.py](../tests/application/test_trace_context.py) | trace/run/stage/user propagation; JSON formatter; secret/prompt/body redaction; ASGI x-trace-id response propagation; target Green `4 passed`; full pytest `70 passed` | BE | 2026-07-20 |
| AEV-023 | SAL-P1-014 | 配置 Profile、CI 密钥边界、脱敏诊断和无副作用更新预览测试 | [config-profile-facade.md](./config-profile-facade.md); [config_profiles.py](../src/serenity_alpha_lab/application/config_profiles.py); [test_config_profiles.py](../tests/application/test_config_profiles.py) | desktop/standalone/ci policy; CI rejects real key/network; diagnostics redacts secrets and tracks env source; service profile preview does not rewrite `.env`; target Green `9 passed`; full pytest `79 passed` | BE/SEC | 2026-07-20 |
| AEV-024 | SAL-P1-009 | ResearchOrchestrator Protocol、DSA 兼容 Facade 和架构边界测试 | [research-orchestrator-facade.md](./research-orchestrator-facade.md); [research_orchestrator.py](../src/serenity_alpha_lab/application/research_orchestrator.py); [research_orchestrator.py](../src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py); [test_research_orchestrator_contract.py](../tests/application/test_research_orchestrator_contract.py); [test_dsa_research_orchestrator_facade.py](../tests/integrations/test_dsa_research_orchestrator_facade.py) | stable run/chat DTOs; DSA injected orchestrator facade; no application/facade concrete DSA Agent import; target Green `16 passed`; related suite `43 passed`; full pytest `90 passed`; py_compile/lock/diff/tag checks PASS | AI/BE | 2026-07-20 |
| AEV-025 | SAL-P1-010 | API Problem Details、异常映射、脱敏和 ASGI middleware 测试 | [api-error-protocol.md](./api-error-protocol.md); [api_errors.py](../src/serenity_alpha_lab/application/api_errors.py); [test_api_errors.py](../tests/application/test_api_errors.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | stable `application/problem+json` body; validation/not-found/conflict/provider/internal mapping; trace_id header/body propagation; stack/path/secret/prompt/body redaction; target Green `5 passed`; related suite `41 passed`; full pytest `95 passed`; py_compile/lock/diff/tag checks PASS | BE/SEC | 2026-07-20 |
| AEV-026 | SAL-P1-012 | Alembic baseline revision、空库升级和启动前 preflight 测试 | [storage-migration-alembic.md](./storage-migration-alembic.md); [alembic.ini](../alembic.ini); [20260720_dsa_v3261_baseline.py](../migrations/versions/20260720_dsa_v3261_baseline.py); [storage_migrations.py](../src/serenity_alpha_lab/repositories/storage_migrations.py); [test_storage_migrations.py](../tests/repositories/test_storage_migrations.py) | DSA baseline revision metadata; empty SQLite creates 28 tables / 177 indexes; `schema_migrations` and `alembic_version` set; startup preflight rejects missing revision; target Green `4 passed`; related suite `22 passed`; full pytest `99 passed`; py_compile/lock/diff/tag checks PASS | BE | 2026-07-20 |
| AEV-027 | SAL-P1-013 | SQLite fixture upgrade、内容校验和失败恢复测试 | [sqlite-upgrade-verification.md](./sqlite-upgrade-verification.md); [sqlite_upgrade.py](../src/serenity_alpha_lab/repositories/sqlite_upgrade.py); [test_sqlite_upgrade.py](../tests/repositories/test_sqlite_upgrade.py) | P0 fixture restore; Alembic stamp to `20260720_dsa_v3261_baseline`; business row_counts/content_hashes preserved; idempotent rerun; injected failure restores backup; target Green `4 passed`; related suite `26 passed`; full pytest `103 passed`; py_compile/lock/diff/tag checks PASS | BE | 2026-07-20 |
| AEV-028 | SAL-P1-015 | Desktop 兼容和性能基线脚本、离线 smoke 与性能摘要 | [desktop-compatibility-performance-baseline.md](./desktop-compatibility-performance-baseline.md); [run-p1-desktop-compatibility-performance.sh](../scripts/run-p1-desktop-compatibility-performance.sh) | DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; Desktop `npm test` `47 passed`; Desktop/API/CLI/Bot pytest `121 passed, 7 warnings`; API/config/database/report-signal snapshots matched; Desktop backend health startup `5,822ms`; single-stock report avg `0.030ms`; real Provider/LLM calls zero; generated artifacts under `.cache/dsa-p0` | FE/BE | 2026-07-20 |
| AEV-029 | SAL-P1-016 / Gate G1 | Gate G1 Go/No-Go 评审、P2 入口约束和本地验证记录 | [gate-g1-engineering-foundation-review.md](./gate-g1-engineering-foundation-review.md) | Decision `GO with accepted risks`; P1 `16/16`; total `29/129`; baseline/worktree tag check PASS; registered patch check PASS; root and architecture/domain/application/repositories/integrations pytest `103 passed`; dependency lock PASS; Desktop compatibility runner PASS; `git diff --check` PASS | TL/SEC | 2026-07-20 |
| AEV-030 | SAL-P2-001 | Provider 领域契约、Provenance/Batch 不变量、错误分类和离线 Contract Test 记录 | [provider-domain-contract.md](./provider-domain-contract.md); [providers.py](../src/serenity_alpha_lab/domain/providers.py); [test_provider_contract.py](../tests/domain/test_provider_contract.py); [test_api_errors.py](../tests/application/test_api_errors.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | Provider contract `23 passed`; related suite `109 passed`; full pytest `128 passed`; Red captured domain collection error, Provider mapping `500 != 502`, bytearray immutability, non-finite retry-delay, mutable scalar subclass, mutable mapping-key, quoted secret, contract-object, and lineage/schema failures; py_compile/lock/diff/tag checks PASS; no real Provider/LLM calls; Ruff not claimed due existing lint/config debt | BE/QE | 2026-07-21 |
| AEV-031 | SAL-P2-002 | DSA Provider Adapter、Compatibility Facade、架构边界和离线测试记录 | [dsa-provider-compatibility-adapter.md](./dsa-provider-compatibility-adapter.md); [provider_adapter.py](../src/serenity_alpha_lab/integrations/dsa/provider_adapter.py); [test_dsa_provider_adapter.py](../tests/integrations/test_dsa_provider_adapter.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | Adapter target `8 passed`; related suite `22 passed`; full pytest `137 passed`; Red captured missing adapter module; py_compile/lock/diff/tag checks PASS; no DSA runtime source migration and no real Provider/LLM calls | BE/QE | 2026-07-21 |
| AEV-032 | SAL-P2-003 | DSA 证券代码兼容迁移、Provider Symbol Mapping 和架构边界记录 | [dsa-symbol-compatibility-migration.md](./dsa-symbol-compatibility-migration.md); [symbol_compatibility.py](../src/serenity_alpha_lab/integrations/dsa/symbol_compatibility.py); [test_dsa_symbol_compatibility.py](../tests/integrations/test_dsa_symbol_compatibility.py); [test_dsa_provider_adapter.py](../tests/integrations/test_dsa_provider_adapter.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | Symbol target `25 passed`; related suite `72 passed`; full pytest `155 passed`; Red captured missing `symbol_compatibility` module; py_compile/lock checks PASS; no DSA runtime source migration, no Bronze/Dataset/PIT/fallback policy and no real Provider/LLM calls | BE/QE | 2026-07-21 |
| AEV-033 | SAL-P2-004 | Bronze 原始响应层、压缩 Artifact、脱敏和本地追踪测试记录 | [bronze-raw-data-layer.md](./bronze-raw-data-layer.md); [bronze_raw_store.py](../src/serenity_alpha_lab/repositories/bronze_raw_store.py); [test_bronze_raw_store.py](../tests/repositories/test_bronze_raw_store.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | Bronze target `6 passed`; related suite `56 passed`; full pytest `162 passed`; Red captured missing `bronze_raw_store` module; gzip deterministic payload, source/sanitized hash, provider/request/time query and secret/Cookie/PII redaction covered; py_compile/lock/tag checks PASS; no Dataset/PIT/fallback policy and no real Provider/LLM calls | BE/QE | 2026-07-21 |
| AEV-034 | SAL-P2-005 | 证券主数据 Dataset、历史 as-of 查询、Provider 映射有效期和 Artifact 发布测试记录 | [instrument-master-dataset.md](./instrument-master-dataset.md); [instrument_master.py](../src/serenity_alpha_lab/datasets/instrument_master.py); [test_instrument_master.py](../tests/datasets/test_instrument_master.py); [test_architecture_boundaries.py](../tests/architecture/test_architecture_boundaries.py) | Instrument master target `3 passed`; related suite `15 passed` and `81 passed`; full pytest `166 passed`; Red captured missing `instrument_master` module; deterministic JSON Artifact, Bronze lineage, as-of active/delisted lookup, provider mapping windows, overlap/duplicate validation and ProblemDetails validation mapping covered; py_compile/lock/tag checks PASS; no trading calendar/raw daily/PIT/fallback policy and no real Provider/LLM calls | BE/QE | 2026-07-21 |

允许的证据：

- CI Run/Junit/coverage/性能和安全扫描 Artifact。
- 固定 Dataset/Run/Backtest/Agent Evaluation Bundle 及哈希。
- OpenAPI/Schema/迁移 diff。
- UI 截图或 Playwright Trace。
- ADR、业务口径签字、许可证/安全评审记录。

口头确认、开发者本地“测试过”和不可复现截图不能作为 Gate 唯一证据。

## 15. 范围变更记录

| Change ID | 日期 | 提出人 | 变更 | 原因 | 工期影响 | 批准人 | 关联任务 |
|---|---|---|---|---|---|---|---|
| CHG-001 | - | - | - | - | - | - | - |

变更控制：

- 新需求先判断是 MVP 必需、风险修复还是增强功能。
- 新增超过 3 人日或影响 Gate 的范围必须先调整估算/依赖，再开始实现。
- 不允许通过降低数据正确性、回测真实性、安全或许可证门槛换取赶工。
- 被移出 MVP 的任务标记 DEFERRED，并指定目标版本和恢复条件。

## 16. 缺陷分级与处理

| 等级 | 定义 | 响应 |
|---|---|---|
| S0 | 数据泄露、错误实盘行为、不可恢复数据损坏 | 立即停止发布/服务，最高优先修复 |
| S1 | 错误回测结论、PIT 泄漏、权限绕过、任务/资金账不一致 | 阻断 Gate/发布，24h 内定责 |
| S2 | 核心功能失败、有可用绕行、明显性能退化 | 当前 Phase 修复 |
| S3 | 次要 UX、文档、小范围兼容问题 | 排入正常 backlog |

缺陷 ID 使用 `BUG-<Phase>-NNN`，必须关联发现测试、受影响版本和回归任务。S0/S1 修复后需要独立评审与事后复盘。

## 17. 下一步

当前已完成 `SAL-P0-001` 至 `SAL-P0-013`、`SAL-P1-001` 至 `SAL-P1-016`、`SAL-P2-001` 至 `SAL-P2-005`，完成度为 34/129；最近可评审交付为本次 `SAL-P2-005` 证券主数据 Dataset checkpoint；Gate G0 与 Gate G1 已通过，Gate G2 未通过。下一步优先执行 `SAL-P2-006` 交易日历；后续实现必须遵守 ADR-001/002 和 Gate G1 入口约束，不得在对应任务前启动 PIT/fallback policy、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或未经批准的大规模 DSA 源码迁移。
