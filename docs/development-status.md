# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-19<br>
> 最近阶段性任务：`SAL-P0-002` DSA Git 历史导入 checkpoint（最终提交以 `git log -1 --oneline` 为准）<br>
> 工作区要求：恢复时必须重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P0 上游接管与行为基线<br>
> 当前 Gate：G0，未通过<br>
> 任务完成度：2/129<br>
> 当前可执行任务：`SAL-P0-003` 固化基线运行环境<br>
> 权威清单：[开发进度跟踪清单](./development-progress-checklist.md)

## 已完成

### 规划与协作

- 完成 GitHub 项目调研与选型，确定以 `daily_stock_analysis` 作为产品与 AI 分析主干。
- 完成 DSA 主干融合开发方案，明确 AlphaSift、Qlib、PIT 数据、真实回测、Evidence Agent 和发布边界。
- 完成 129 项原子任务、依赖、验收条件、Gate、风险和证据登记清单。
- 将 4 人团队排期按 268.5 理想人日修正为 16~18 周，并预留 10 个交易日稳定观察。
- 新增 `AGENTS.md`，要求后续会话读取状态/清单、阶段性任务完成后自动同步恢复状态，并在阶段 Gate 后主动提交。
- 已创建规划基线提交 `9088456`。

### P0 上游接管

- 完成 `SAL-P0-001`：锁定上游基线为 `ZhuLinsen/daily_stock_analysis v3.26.1`，commit `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；证据见 [DSA 上游基线选择记录](./upstream-baseline-selection.md)。
- 完成 `SAL-P0-002`：配置 `upstream` remote，导入 DSA 上游 heads/tags，创建本地基线标签 `upstream/dsa-v3.26.1` 指向锁定 commit；证据见 [DSA Git 历史导入记录](./upstream-history-import.md)。

## 未完成

### 当前阻塞 Gate G0 的 P0 任务

- `SAL-P0-003` 至 `SAL-P0-012` 尚未建立环境、后端/Web/Desktop/Docker 基线、API/DB/报告金标、SBOM 与上游维护文档。
- `SAL-P0-013` Gate G0 尚未评审，不能进入 P1 或开始 Quant Core/大规模重构。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P0 至 P6 仍有 127 项工程任务未完成。
- 尚未创建运行时代码、数据库、Worker、Quant Core 或部署环境。
- 本地仓库仍未配置本项目 `origin` 远端；当前无托管 URL，已登记为开放风险，后续确定地址后补绑。

## 当前决策与约束

- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- Gate G0 前不得开始 Quant Core 或大规模重构。
- DSA 接管基线已锁定为 `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；未经 Gate G0 或 ADR 批准不漂移到未发布 `main`。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。

## 下一步

1. 领取 `SAL-P0-003`：固化 DSA 基线运行环境，记录 Python、Node、OS 与系统依赖矩阵。
2. 后续确定本项目托管 URL 后，补充配置 `origin` remote 并复验 `origin/upstream` 双 remote 约束。
3. 继续保留后续同步候选：`55946536` macOS Gatekeeper 文档修复、`487e49e` DecisionSignal reassess persist。
4. Gate G0 前继续避免 Quant Core 或大规模重构，优先建立 DSA 可重复运行基线。

## 会话恢复步骤

1. 阅读根目录 `AGENTS.md`。
2. 阅读本文件、[开发方案](./ai-stock-quant-platform-development-plan.md) 和任务清单。
3. 执行 `git status --short --branch` 与 `git log -2 --oneline`，确认工作区和基线。
4. 处理当前 `DOING/BLOCKED/READY` 任务；没有明确状态时以本文件的“当前可执行任务”为准。
5. 每完成一个可评审交付，更新状态、验收证据、风险/决策和相关文档。
6. 每完成一个 Phase Gate，必须完成校验并提交中文 checkpoint；阶段内形成可运行交付时也应单独提交。

## 下次启动提示词

```text
请继续开发 K:\ai-projs\serenity-alpha-lab。

先阅读：
1. AGENTS.md
2. docs/development-status.md
3. docs/development-progress-checklist.md
4. docs/ai-stock-quant-platform-development-plan.md
5. docs/upstream-baseline-selection.md

随后执行 git status --short --branch 和 git log -2 --oneline，确认当前状态。

当前应从 SAL-P0-003 开始：固化 DSA 基线运行环境，记录并自动化 Python、Node、OS 和系统依赖；先复验 upstream remote 与 upstream/dsa-v3.26.1 tag，再开始环境矩阵。

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 每完成阶段性任务，更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险和决策。
- 每形成可评审交付时主动提交详细中文 commit。
- 完成后在 docs/development-status.md 写清楚已完成、未完成、下一步和下次启动提示词。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
