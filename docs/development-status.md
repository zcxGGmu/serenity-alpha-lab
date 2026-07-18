# Serenity Alpha Lab 当前开发状态

> 最后更新：2026-07-19<br>
> 上一个规划基线提交：`9088456`<br>
> 工作区基线：该提交后为 clean；恢复时必须重新执行 `git status`<br>
> 当前 Phase：P0 上游接管与行为基线<br>
> 当前 Gate：G0，未通过<br>
> 任务完成度：0/129<br>
> 当前可执行任务：`SAL-P0-001` 锁定候选上游基线<br>
> 权威清单：[开发进度跟踪清单](./development-progress-checklist.md)

## 已完成

- 完成 GitHub 项目调研与选型，确定以 `daily_stock_analysis` 作为产品与 AI 分析主干。
- 完成 DSA 主干融合开发方案，明确 AlphaSift、Qlib、PIT 数据、真实回测、Evidence Agent 和发布边界。
- 完成 129 项原子任务、依赖、验收条件、Gate、风险和证据登记清单。
- 将 4 人团队排期按 268.5 理想人日修正为 16~18 周，并预留 10 个交易日稳定观察。
- 新增 `AGENTS.md`，要求后续会话读取状态/清单并在阶段 Gate 后主动提交。
- 已创建规划基线提交 `9088456`。

## 未完成

- 尚未导入或 fork DSA 上游源码；当前仓库只有规划、清单和协作约定。
- P0 至 P6 的 129 项工程任务均未完成。
- 尚未锁定最终 DSA release/commit，`v3.26.1` 只是候选基线。
- 尚未执行 DSA 后端、Web、Desktop、Docker 的真实基线测试。
- 尚未创建运行时代码、数据库、Worker、Quant Core 或部署环境。

## 当前决策与约束

- DSA 是产品主干，不是量化内核；真实组合回测、PIT 数据和硬风控必须独立实现。
- AlphaSift 只负责候选发现/快照筛选；Qlib 只能通过独立 Quant Worker Adapter 接入。
- 任何历史回测必须使用不可变 Dataset Version 与 `available_at <= decision_time` 的数据。
- 不接入实盘交易；LLM 没有交易、Shell 或任意数据库写权限。
- Gate G0 前不得开始 Quant Core 或大规模重构。

## 下一步

1. 领取并执行 `SAL-P0-001`：比较 DSA `v3.26.1` 与候选 main commit，锁定唯一基线。
2. 在清单中将任务更新为 `DOING`，填写负责人、开始日期和实际人日。
3. 完成后记录选择依据和 commit SHA，更新本文件、任务清单、风险/决策登记。
4. 运行对应验证，提交中文 Git checkpoint；之后继续 `SAL-P0-002`。

## 会话恢复步骤

1. 阅读根目录 `AGENTS.md`。
2. 阅读本文件、[开发方案](./ai-stock-quant-platform-development-plan.md) 和任务清单。
3. 执行 `git status --short --branch` 与 `git log -1 --oneline`，确认工作区和基线。
4. 处理当前 `DOING/BLOCKED/READY` 任务；没有明确状态时以本文件的“当前可执行任务”为准。
5. 每完成一个可评审交付，更新状态、验收证据、风险/决策和相关文档。
6. 每完成一个 Phase Gate，必须完成校验并提交中文 checkpoint；阶段内形成可运行交付时也应单独提交。

> 本文件是状态快照，不替代任务清单。发生冲突时，以任务清单中的任务状态、依赖和 Gate 证据为准。
