# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-19<br>
> 最近阶段性任务：`SAL-P0-006` Desktop、CLI 与 Bot Smoke 基线（最终提交以 `git log -1 --oneline` 为准）<br>
> 工作区要求：恢复时必须重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P0 上游接管与行为基线<br>
> 当前 Gate：G0，未通过<br>
> 任务完成度：4/129<br>
> 当前可执行任务：`SAL-P0-007` 建立 Docker 基线；也可在本机复跑 `SAL-P0-004` backend-gate/offline-tests，但需单独记录证据（`SAL-P0-005`、`SAL-P0-011` 仍阻塞中）<br>
> 最近开发 checkpoint：本状态已随 `SAL-P0-006` checkpoint 提交；最终以 `git log -1 --oneline` 为准<br>
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
- 完成 `SAL-P0-003`：固化 Windows、Linux/CI、Docker、Desktop 运行环境矩阵，新增隔离 worktree bootstrap 脚本和依赖缓存策略；证据见 [DSA 基线运行环境记录](./dsa-baseline-environment.md)。
- 完成 `SAL-P0-006`：在锁定 DSA worktree 中建立 Desktop、CLI、本地 API 与 Bot 命令层离线 smoke 基线；证据见 [DSA Desktop、CLI 与 Bot Smoke 基线记录](./desktop-cli-bot-smoke-baseline.md)。

### 已提交但未完成的基线尝试

- `SAL-P0-004` 已提交阻塞证据 `31bb444d`：PowerShell bootstrap 失败处理已修正；本机 macOS 已能通过 AlphaSift Git 克隆并安装 CI 依赖，但 backend-gate/offline-tests 尚未单独复跑和记录，任务仍未完成。
- `SAL-P0-005` 已提交阻塞证据 `871a20ab`：Web `npm ci`、lint、build 可运行；Vitest 与真实 Playwright smoke 仍未通过。
- `SAL-P0-011` 已提交阻塞证据 `bfe54630`：供应链初筛已记录；Python SBOM 与镜像 SBOM 仍未完成。

## 未完成

### 当前阻塞 Gate G0 的 P0 任务

- `SAL-P0-004` 后端离线测试基线未完成：历史阻塞证据为 AlphaSift Git 依赖无法从 GitHub 443 克隆；本机 macOS 已在 `SAL-P0-006` 中完成 CI 依赖安装，但仍需单独运行 `backend-gate`/offline-tests 并补齐证据，不能沿用 smoke 结果直接标为完成。
- `SAL-P0-005` Web 测试与构建基线阻塞：`npm ci`、lint、build 已通过，但 Vitest 存在 JP/KR 市场区域测试契约矛盾，Playwright smoke 因缺少 `DSA_WEB_SMOKE_PASSWORD` 全部跳过；证据见 [DSA Web 测试与构建基线尝试记录](./web-baseline-test-build.md)。
- `SAL-P0-011` 供应链基线阻塞：已完成 Web audit、Node 许可证、Python 动态依赖和 Docker CLI/SBOM 插件初筛，但 Python 已安装 SBOM 尚未基于当前可用 CI 环境生成，镜像 SBOM 受 Docker daemon 未运行阻塞；证据见 [DSA 供应链基线尝试记录](./supply-chain-baseline.md)。
- `SAL-P0-004`、`SAL-P0-005`、`SAL-P0-007` 至 `SAL-P0-012` 尚未完整建立后端/Web/Docker 基线、API/DB/报告金标、完整 SBOM 与上游维护文档。
- `SAL-P0-013` Gate G0 尚未评审，不能进入 P1 或开始 Quant Core/大规模重构。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P0 至 P6 仍有 125 项工程任务未完成。
- 尚未创建运行时代码、数据库、Worker、Quant Core 或部署环境。
- 本地仓库当前已配置 `origin` 指向 `git@github.com:zcxGGmu/serenity-alpha-lab.git`，`upstream` 指向 `https://github.com/ZhuLinsen/daily_stock_analysis.git`；后续变更需继续复验双 remote 约束。
- DSA Python 依赖尚未正式锁定，仍含范围版本和 AlphaSift Git 依赖；当前仅通过隔离 cache/worktree 降低污染，供应链与锁文件后续任务继续处理。
- 当前 Windows PATH 未安装 Python 3.11，Docker daemon 未运行；本机 `.cache/dsa-p0/venv` 已使用 Python 3.11.15 完成 CI 依赖安装，`SAL-P0-004` 仍需正式复跑后端 gate/offline-tests，`SAL-P0-007` 需启动 Docker daemon。
- Web lockfile 可安装并构建，但 npm audit 暴露 16 个漏洞（10 个 high），且 lockfile 混用 `registry.npmjs.org` 与 `registry.npmmirror.com`；不得在 P0 基线记录中直接运行 `npm audit fix` 改写上游 lockfile。

## 当前决策与约束

- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- Gate G0 前不得开始 Quant Core 或大规模重构。
- DSA 接管基线已锁定为 `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；未经 Gate G0 或 ADR 批准不漂移到未发布 `main`。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。
- DSA 源码通过 `.worktrees/dsa-v3.26.1` 隔离物化；依赖缓存放在 `.cache/dsa-p0`，两者均不提交。

## 下一步

1. 领取 `SAL-P0-007`：启动 Docker daemon，构建并运行 DSA analyzer/server Docker profile，记录镜像 digest、健康检查和阻塞项。
2. 同步推进 `SAL-P0-004`：复用本机 `.cache/dsa-p0/venv` 重新运行 backend-gate/offline-tests，并单独更新后端基线证据。
3. 解除 `SAL-P0-011` 阻塞：基于已可安装的 Python 环境补齐 Python SBOM；启动 Docker daemon 后补齐镜像 digest、镜像 SBOM 和漏洞摘要。
4. 解除 `SAL-P0-005` 阻塞：明确 JP/KR 市场区域契约，提供 `DSA_WEB_SMOKE_PASSWORD` 与可运行 backend webui-only 环境，再重跑 Vitest 和真实 Playwright smoke。
5. 继续保留后续同步候选：`55946536` macOS Gatekeeper 文档修复、`487e49e` DecisionSignal reassess persist。

## 固定收尾习惯

每个阶段性任务完成、阻塞或形成可评审交付后，都要自动更新本状态快照、进度清单、验收证据、风险/决策登记和下次启动提示词，并创建中文 checkpoint commit；不得等待用户额外提醒。

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

当前应优先推进 SAL-P0-007：启动 Docker daemon，构建并运行 DSA analyzer/server Docker profile，记录镜像 digest、健康检查和阻塞项。也可以在同一 P0 范围内继续 SAL-P0-004：复用 `.cache/dsa-p0/venv` 正式复跑 backend-gate/offline-tests 并单独记录证据。

最近阶段性任务为 SAL-P0-006 Desktop、CLI 与 Bot Smoke 基线；最新 checkpoint 以 `git log -2 --oneline` 的实际结果为准。

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 每完成阶段性任务，更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险和决策。
- 每形成可评审交付时主动提交详细中文 commit。
- 完成后在 docs/development-status.md 写清楚已完成、未完成、下一步和下次启动提示词。
- 这是固定习惯：每个阶段性任务结束后自动做，不需要用户提醒。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
