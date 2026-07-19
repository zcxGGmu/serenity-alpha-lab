# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-19<br>
> 最近阶段性任务：`SAL-P0-008` 冻结 API 与配置契约<br>
> 工作区要求：从 `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` 恢复，并重新执行 `git status`，以实际工作区为准<br>
> 当前 Phase：P0 上游接管与行为基线<br>
> 当前 Gate：G0，未通过<br>
> 任务完成度：9/129<br>
> 当前可执行任务：`SAL-P0-009`、`SAL-P0-010`、`SAL-P0-012`，状态均为 `READY`<br>
> 最近可评审交付 checkpoint：`f6b466b0 feat(P0): 冻结 API 与配置契约基线`<br>
> 最新状态同步 checkpoint：本文件所在提交；恢复时以 `git log -1 --oneline` 为准<br>
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
- 完成 `SAL-P0-004`：新增后端离线 gate wrapper、登记 `DSA-PATCH-001` 上游兼容补丁并完成 syntax、flake8、deterministic、collect、offline-tests；离线测试 `4455 passed, 4 deselected`；证据见 [DSA 后端离线测试基线记录](./backend-offline-test-baseline.md) 和 [DSA 上游补丁登记](./upstream-patches.md)。
- 完成 `SAL-P0-005`：登记 `DSA-PATCH-002` 与 `DSA-PATCH-003`，新增 Web smoke fixture seed 脚本，完成 Web `npm ci`、lint、build、Vitest 与真实 Playwright smoke；Vitest `965 passed, 2 skipped`，Playwright smoke `13 passed`；证据见 [DSA Web 测试与构建基线记录](./web-baseline-test-build.md) 和 [DSA 上游补丁登记](./upstream-patches.md)。
- 完成 `SAL-P0-006`：在锁定 DSA worktree 中建立 Desktop、CLI、本地 API 与 Bot 命令层离线 smoke 基线；证据见 [DSA Desktop、CLI 与 Bot Smoke 基线记录](./desktop-cli-bot-smoke-baseline.md)。
- 完成 `SAL-P0-007`：新增可复跑 Docker baseline 脚本，构建镜像并验证 server `/api/health` 与 analyzer import smoke；证据见 [DSA Docker 基线记录](./docker-baseline.md)。
- 完成 `SAL-P0-008`：新增 API/config contract baseline 脚本并冻结运行时 OpenAPI、配置 Schema、环境变量/配置字段 inventory 与摘要哈希；OpenAPI `3.1.0` 含 105 paths、119 operations、186 component schemas，配置 inventory 含 386 fields；证据见 [DSA API 与配置契约基线记录](./api-config-contract-baseline.md) 和 [API/config baseline summary](./baselines/dsa-v3.26.1/api-config/summary.json)。
- 完成 `SAL-P0-011`：新增供应链 baseline 脚本，生成 Python SBOM/license/audit、Web npm audit/license、Syft image SBOM 和 Grype image vulnerabilities；证据见 [DSA 供应链基线记录](./supply-chain-baseline.md)。

## 未完成

### 当前阻塞 Gate G0 的 P0 任务

- `SAL-P0-009`、`SAL-P0-010` 已由后端基线解锁，当前为 `READY`，但尚未冻结数据库 Schema/迁移样本、报告与信号评价金标。
- `SAL-P0-012` 已满足依赖，当前为 `READY`，但尚未建立上游维护文档和 CI required checks；需吸收 `DSA-PATCH-001` 至 `DSA-PATCH-003`、Web smoke fixture 和 `SAL-P0-011` scanner baseline。
- `SAL-P0-013` 仍为 `TODO`，Gate G0 尚未评审，不能进入 P1 或开始 Quant Core/大规模重构。

### 全局未完成

- 当前仓库已导入 DSA 上游 Git 历史和基线 tag，但尚未把 DSA 源码合入本项目工作树。
- P0 至 P6 仍有 120 项工程任务未完成。
- 尚未创建运行时代码、数据库、Worker、Quant Core 或部署环境。
- 本地仓库当前已配置 `origin` 指向 `git@github.com:zcxGGmu/serenity-alpha-lab.git`，`upstream` 指向 `https://github.com/ZhuLinsen/daily_stock_analysis.git`；后续变更需继续复验双 remote 约束。
- DSA Python 依赖尚未正式锁定，仍含范围版本和 AlphaSift Git 依赖；`SAL-P0-011` 已完成 SBOM/audit baseline，正式锁文件和离线缓存策略后续由 `SAL-P1-003` 处理。
- 本机 `.cache/dsa-p0/venv` 已使用 Python 3.11.15 完成 CI 依赖安装并通过后端离线 gate；Windows PATH 缺少 Python 3.11 不再阻塞 `SAL-P0-004`，但跨平台恢复时仍需复验实际工具链。
- Web lockfile 可安装并构建，但 npm audit 暴露 16 个漏洞（10 个 high），且 lockfile 混用 `registry.npmjs.org` 与 `registry.npmmirror.com`；不得在 P0 基线记录中直接运行 `npm audit fix` 改写上游 lockfile。Docker image Grype baseline 暴露 39 critical、84 high，后续由 `SAL-P6-005` 发布安全门禁关闭或豁免。

## 当前决策与约束

- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- Gate G0 前不得开始 Quant Core 或大规模重构。
- DSA 接管基线已锁定为 `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`；未经 Gate G0 或 ADR 批准不漂移到未发布 `main`。
- `upstream/dsa-v3.26.1` 是本地不可变基线标签；后续升级必须新建 `sync/dsa-<version>` 分支和新基线 tag，不得移动该标签。
- DSA 源码通过 `.worktrees/dsa-v3.26.1` 隔离物化；依赖缓存放在 `.cache/dsa-p0`，两者均不提交。
- 阻断基线 gate 的上游缺陷/测试契约漂移通过可登记、可复跑的本地 patch 文件处理；当前登记补丁为 `DSA-PATCH-001` 至 `DSA-PATCH-003`，见 [DSA 上游补丁登记](./upstream-patches.md)。
- API 与配置契约冻结源为锁定 worktree 的运行时 FastAPI OpenAPI 和配置 registry/dataclass/env inventory；上游静态 `docs/architecture/api_spec.json` 已滞后，不作为 Serenity P0 的权威冻结源。

## 下一步

1. 启动 `SAL-P0-009` 和 `SAL-P0-010`：在后端/Web/API 配置契约基线已通过的前提下冻结数据库 Schema/迁移样本、报告与信号评价金标。
2. 推进 `SAL-P0-012`：建立上游维护文档和 CI required checks，纳入 `DSA-PATCH-001` 至 `DSA-PATCH-003`、Web smoke fixture 和供应链 scanner baseline。
3. 准备 `SAL-P0-013` Gate G0：汇总 P0 测试、构建、许可证、补丁和目标环境证据；通过前不得进入 P1 或 Quant Core。
4. 继续保留后续同步候选：`55946536` macOS Gatekeeper 文档修复、`487e49e` DecisionSignal reassess persist。

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
6. docs/upstream-baseline-selection.md

随后执行 git status --short --branch 和 git log -3 --oneline，确认当前状态。

当前状态：
- Phase：P0 上游接管与行为基线
- Gate：G0 未通过
- 已完成：SAL-P0-001 至 SAL-P0-008，以及 SAL-P0-011
- 最近完成：SAL-P0-008 冻结 API 与配置契约
- 最近可评审交付 checkpoint：f6b466b0 feat(P0): 冻结 API 与配置契约基线
- 最新状态同步 checkpoint：本提示词所在提交；启动后以 git log -1 --oneline 确认
- 进度：P0 9/13，总计 9/129

下一步优先执行：
1. SAL-P0-009 冻结数据库 Schema 与迁移样本
2. SAL-P0-010 冻结报告与信号评价金标
3. SAL-P0-012 建立上游维护文档和 CI required checks
4. SAL-P0-013 Gate G0 评审

严格遵守 AGENTS.md：
- 不要把未完成任务标为完成。
- Gate G0 前不得开始 P1、Quant Core 或大规模 DSA 迁移。
- 保留用户已有改动，不执行破坏性 Git 操作。
- 不提交 .worktrees、.cache、node_modules、static、Playwright artifacts、pycache 或无关未跟踪目录。
- 每完成阶段性任务，自动更新 docs/development-status.md、docs/development-progress-checklist.md、验收证据、风险、决策、tasks/todo.md review 和下次启动提示词。
- 每形成可评审交付时主动提交详细中文 commit。
- 完成后在 docs/development-status.md 写清楚已完成、未完成、下一步和下次启动提示词。
- 这是固定习惯：每个阶段性任务结束后自动做，不需要用户提醒。
```

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
