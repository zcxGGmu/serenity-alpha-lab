# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-20<br>
> 最近阶段性任务：`SAL-P1-001` 批准上游与模块化 ADR<br>
> 工作区要求：从 `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` 恢复，并重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P1 工程加固<br>
> 当前 Gate：G1，未通过；G0 已通过（`GO with accepted risks`）<br>
> 任务完成度：14/129<br>
> 当前可执行任务：`SAL-P1-002` 与 `SAL-P1-004`，状态均为 `READY`；后续实现必须遵守 ADR-001/002<br>
> 最近可评审交付 checkpoint：本文件所在提交；恢复时以 `git log -1 --oneline` 为准<br>
> 最新状态同步 checkpoint：本文件所在提交；恢复时以 `git log -1 --oneline` 为准<br>
> 权威清单：[开发进度跟踪清单](./development-progress-checklist.md)

## 已完成

### 规划与协作

- 完成 GitHub 项目调研与选型，确定以 `daily_stock_analysis` 作为产品与 AI 分析主干。
- 完成 DSA 主干融合开发方案，明确 AlphaSift、Qlib、PIT 数据、真实回测、Evidence Agent 和发布边界。
- 完成 129 项原子任务、依赖、验收条件、Gate、风险和证据登记清单。
- 将 4 人团队排期按 268.5 理想人日修正为 16~18 周，并预留 10 个交易日稳定观察。
- 新增 `AGENTS.md`，要求后续会话读取状态/清单、阶段性任务完成后自动同步恢复状态，并在阶段 Gate 后主动提交。

### P0 上游接管

- 完成 `SAL-P0-001` 至 `SAL-P0-003`：锁定 DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`，导入上游历史/tag，并固化 Windows、Linux/CI、Docker、Desktop 运行环境矩阵。
- 完成 `SAL-P0-004`：后端离线 gate 通过，`4455 passed, 4 deselected, 48 warnings, 416 subtests passed`；登记 `DSA-PATCH-001`。
- 完成 `SAL-P0-005`：Web `npm ci`、lint、build、Vitest `965 passed, 2 skipped`、Playwright smoke `13 passed`；登记 `DSA-PATCH-002` 与 `DSA-PATCH-003`。
- 完成 `SAL-P0-006`：Desktop `47/47`、packaging/API `13/13`、CLI local backend `77/77`、Bot status/dispatcher/market `31/31` 离线 smoke。
- 完成 `SAL-P0-007`：Docker 镜像 `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`，server `/api/health` 与 analyzer import smoke 通过。
- 完成 `SAL-P0-008`：冻结运行时 OpenAPI `3.1.0`、105 paths、119 operations、186 component schemas，以及 386 个配置 inventory 字段。
- 完成 `SAL-P0-009`：冻结 SQLite Schema、表/索引/外键元数据和脱敏 fixture；基线含 28 张业务表、177 个索引、31 行 fixture 数据。
- 完成 `SAL-P0-010`：冻结报告与信号评价金标；基线含 2 个结构化报告、3 个 Markdown 报告、6 个 Signal Evaluation cases，`direction_accuracy_pct=60.0`、`win_rate_pct=60.0`。
- 完成 `SAL-P0-011`：生成供应链 baseline；Python SBOM 146 components，Web npm audit 16 vulnerabilities / 10 high，Syft image SBOM 7865 components，Grype 39 critical / 84 high。
- 完成 `SAL-P0-012`：新增 `UPSTREAM_BASE.md`、补丁分类和 `.github/workflows/p0-required-baselines.yml` 四个 P0 required check 候选。
- 完成 `SAL-P0-013`：Gate G0 评审结论为 `GO with accepted risks`；证据见 [Gate G0 基线接管评审](./gate-g0-baseline-review.md)。

### P1 工程加固

- 完成 `SAL-P1-001`：批准 [ADR-001](./adr/ADR-001-upstream-takeover-sync-and-patch-policy.md) 与 [ADR-002](./adr/ADR-002-progressive-modularization-and-compatibility-facade.md)，明确不可变上游 tag、受控 sync 分支、补丁分类、候选 commit 处理、Compatibility Facade、模块边界、服务拆分条件、旧路径删除条件、回滚和复审日期。
- 上游候选处理已定：`55946536` macOS Gatekeeper 文档修复不 cherry-pick 到当前 P1 基线；`487e49e5` DecisionSignal reassessment persistence 延期至 `sync/dsa-487e49e5` 分支评审。

## 未完成

### 当前可执行 P1 任务

- `SAL-P1-002` 当前为 `READY`：标准化 Python 项目元数据，把依赖声明迁入标准 `pyproject.toml`，保持 DSA CLI/API/Worker/测试入口可安装运行。
- `SAL-P1-004` 当前为 `READY`：建立目标包骨架和架构测试，创建 domain/application/quant/datasets/evidence/integrations 边界并验证依赖方向。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P1 至 P6 仍有 115 项工程任务未完成。
- 尚未创建 Serenity 目标运行时代码、Worker、Quant Core、PIT Dataset、正式回测、Evidence Agent 或部署环境。
- 供应链 Critical/High、Python 动态 Git 依赖、Web registry 混用和 Docker 镜像漏洞是已接受的 G0 风险，但继续阻断发布或未评审依赖漂移。

## 当前决策与约束

- Gate G0 已通过；Gate G1 尚未通过。DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` 仍是 P1 工程加固基线。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。
- ADR-001 已批准受控同步策略：所有上游吸收必须经 `sync/dsa-*` 分支、补丁结果登记、相关基线刷新和 Gate/ADR 记录。
- ADR-002 已批准渐进式模块化策略：旧 DSA 路径只能经显式 Compatibility Facade 迁移，P1 不拆微服务。
- DSA 源码通过 `.worktrees/dsa-v3.26.1` 隔离物化；依赖缓存放在 `.cache/dsa-p0`，两者均不提交。
- 当前本地偏离均为 `compatible` 或 `extension`，无 `divergence`；已登记补丁为 `DSA-PATCH-001` 至 `DSA-PATCH-003`。
- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- 后续实现不得绕过 ADR-001/002；不得在对应任务前启动 Quant Core、PIT 数据、正式回测或未经批准的大规模 DSA 源码迁移。

## 已接受风险

- `RSK-008`：Python 依赖未正式锁定且含 AlphaSift Git 依赖；由 `SAL-P1-003` 引入正式 lock/extras/离线缓存关闭。
- `RSK-010`：Web npm audit 仍有 10 个 high；后续由受控升级或 `SAL-P6-005` 发布安全门禁关闭/豁免。
- `RSK-011`：Web lockfile 混用 npmjs 与 npmmirror resolved URL；后续由 `SAL-P1-003` 或发布前依赖治理统一策略。
- `RSK-012`：Docker image Grype 仍有 39 critical / 84 high；由 `SAL-P6-005` 前修复或正式豁免。

## 下一步

1. 优先执行 `SAL-P1-002` 标准化 Python 项目元数据。
2. 可并行执行 `SAL-P1-004` 建立目标包骨架和架构测试。
3. 保持 P0 required checks 作为基线保护；任何上游吸收必须遵守 ADR-001，任何模块化实现必须遵守 ADR-002。

## 本次状态复核

- 2026-07-20：完成 `SAL-P1-001`，批准上游与模块化 ADR。当前已完成 `SAL-P0-001` 至 `SAL-P0-013` 和 `SAL-P1-001`，Gate G0 已通过，Gate G1 未通过；`SAL-P1-002` 与 `SAL-P1-004` 是下一步 `READY` 任务。
- 本状态文档已明确列出已完成、未完成、当前约束、已接受风险、下一步和下次启动提示词；后续每个阶段性任务结束时继续自动同步这些内容。

## 固定收尾习惯

每个阶段性任务完成、阻塞或形成可评审交付后，都要自动更新本状态快照、进度清单、验收证据、风险/决策登记、`tasks/todo.md` review 和下次启动提示词，并创建中文 checkpoint commit；不得等待用户额外提醒。

## 会话恢复步骤

1. 阅读根目录 `AGENTS.md`。
2. 阅读 `tasks/lessons.md`，先吸收本项目已记录的纠正规则。
3. 阅读本文件、[开发方案](./ai-stock-quant-platform-development-plan.md) 和任务清单。
4. 执行 `git status --short --branch` 与 `git log -3 --oneline`，确认工作区和基线。
5. 处理当前 `DOING/BLOCKED/READY` 任务；没有明确状态时以本文件的“当前可执行任务”为准。
6. 每完成一个可评审交付，更新状态、验收证据、风险/决策和相关文档。
7. 每完成一个 Phase Gate，必须完成校验并提交中文 checkpoint；阶段内形成可运行交付时也应单独提交。

## 下次启动提示词

```text
请继续开发 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab。

先阅读：
1. AGENTS.md
2. tasks/lessons.md
3. docs/development-status.md
4. docs/development-progress-checklist.md
5. docs/ai-stock-quant-platform-development-plan.md
6. docs/gate-g0-baseline-review.md

随后执行 git status --short --branch 和 git log -3 --oneline，确认当前状态。

当前状态：
- Phase：P1 工程加固
- Gate：G1 未通过；G0 已通过（GO with accepted risks）
- 已完成：SAL-P0-001 至 SAL-P0-013，SAL-P1-001
- 最近完成：SAL-P1-001 批准上游与模块化 ADR
- 最近可评审交付 checkpoint：本提示词所在提交；启动后以 git log -1 --oneline 确认
- 最新状态同步 checkpoint：本提示词所在提交；启动后以 git log -1 --oneline 确认
- 进度：P0 13/13，P1 1/16，总计 14/129

下一步优先执行：
1. SAL-P1-002 标准化 Python 项目元数据
2. SAL-P1-004 建立目标包骨架和架构测试

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- 不要移动 `upstream/dsa-v3.26.1` tag。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 不提交 .worktrees、.cache、node_modules、static、Playwright artifacts、pycache 或无关未跟踪目录。
- 后续实现必须遵守 ADR-001/002；不要在对应任务前开始 Quant Core、PIT Dataset、正式回测或未经批准的大规模 DSA 源码迁移。
- 每完成阶段性任务，自动更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险、决策、tasks/todo.md review 和下次启动提示词。
- 每形成可评审交付时主动提交详细中文 commit。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
