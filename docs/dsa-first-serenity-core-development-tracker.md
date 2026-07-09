# DSA-First Serenity Core Development Tracker

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this tracker task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 `daily_stock_analysis` 为主产品与主运行时，按阶段接入 Serenity Core 的证据质量、研究审计、补证闭环和安全边界能力，并让每次迭代都有明确状态、证据、回滚点和验收标准。

**Architecture:** DSA 继续拥有 Web / API / Desktop / Bot、数据源、调度、通知、组合、回测、Agent 与交易报告语义；Serenity Core 只作为辅助研究内核，通过窄接口提供 evidence audit、readiness gate、coverage matrix、evidence gap task 和 provenance guardrail。所有集成默认关闭、fail-open、可回滚，不覆盖 DSA 原有买卖建议、评分、趋势、目标价、仓位或风控逻辑。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / React + Vite / TypeScript / Zustand / deterministic Serenity evidence pipeline / JSONL bridge / pytest / Vitest / Playwright / Docker / GitHub Actions.

---

## 当前开发状态快照

**Updated:** 2026-07-09

### 已完成

| 事项 | 状态 | 证据 |
| --- | --- | --- |
| DSA-first Serenity Core 总体开发方案 | Completed | `docs/dsa-first-serenity-core-development-plan.md`，已在 commit `81a5709` 提交 |
| DSA-first Serenity Core 进度跟踪清单 | Completed | `docs/dsa-first-serenity-core-development-tracker.md`，已在 commit `81a5709` 提交 |
| 项目任务日志更新 | Completed | `tasks/todo.md` 已记录方案和 tracker 两个文档阶段 |
| 长期协作习惯记录 | Completed | `tasks/lessons.md` 已记录阶段完成后精准 stage、验证并提交的规则 |

### 未完成

| 范围 | 当前状态 | 说明 |
| --- | --- | --- |
| DSA 代码集成 | In Progress | Global tasks、Phase 0、Phase 1、Phase 2 Agent Tools 与 Phase 3 `P3-T01` Research Task Data Contract、`P3-T02` Snapshot-Based Task Persistence、`P3-T03` Intelligence Service 接入、`P3-T04` 专表升级决策 Gate 已在 DSA 分支 `codex/serenity-phase-0-evidence-bridge` 完成并验证；下一步为 P3 Phase Review，DB 专表仍未启动 |
| Global tasks | Verified | `G-T01`、`G-T02`、`G-T03` 已在 DSA 分支 `codex/serenity-phase-0-evidence-bridge` 完成并验证 |
| Phase 0 Evidence Bridge POC | Verified | `P0-T01` 至 `P0-T04` 与 Phase 0 review gate 已完成并验证 |
| Phase 1 Analysis Report Add-On | Verified | `P1-T01` API Schema、`P1-T02` Analysis Service 附加 Serenity Audit、`P1-T03` 历史记录 Context Snapshot 持久化、`P1-T04` Web 类型/证据质量面板、`P1-T05` HTTP / UI Smoke 与 P1 Phase Review 已完成并验证 |
| Phase 2 Agent Tools | Verified | `P2-T01` Evidence Quality Agent Tool、`P2-T02` Evidence Gap Agent Tool、`P2-T03` Agent Prompt Boundary Test 与 P2 Phase Review 已完成并验证；review 修复了 feature flag 与 specialist fallback 两个边界缺口 |
| Phase 3 Intelligence Workflow Persistence | In Progress | `P3-T01` Research Task Data Contract、`P3-T02` Snapshot-Based Task Persistence、`P3-T03` Intelligence Service 接入与 `P3-T04` 专表升级决策 Gate 已完成并验证；P3-T04 决策为继续 snapshot-first，不新增 DB 专表；下一步为 P3 Phase Review |
| Phase 4 Provenance Safety Guardrails | Not Started | 等 Phase 3 review 通过后再开始 |

### 当前下一步

Global guardrails、Phase 0 Evidence Bridge POC、Phase 1 Analysis Report Add-On（含 `P1-T01` 至 `P1-T05` 与 P1 Phase Review）、Phase 2 Agent Tools（含 `P2-T01`、`P2-T02`、`P2-T03` 与 P2 Phase Review）和 Phase 3 `P3-T01` Research Task Data Contract、`P3-T02` Snapshot-Based Task Persistence、`P3-T03` Intelligence Service 接入、`P3-T04` 专表升级决策 Gate 已完成并通过验证；下一步继续 Phase 3 Intelligence Workflow Persistence，从 P3 Phase Review 开始。P3-T04 已决策继续 snapshot-first，不新增 DB 专表。

1. 保持 DSA 仓库分支：`codex/serenity-phase-0-evidence-bridge`。
2. 从 P3 Phase Review 开始。
3. 继续保持 `SERENITY_RESEARCH_ENABLED=false` 默认关闭和 fail-open 策略。
4. Phase 3 只允许把 Serenity gaps 设计为可追踪研究任务，不得把 Serenity score 或 task 状态映射到 DSA 交易建议、目标价、仓位、趋势预测或 `sentiment_score`。

### 当前工作区注意事项

- Serenity 当前仓库路径：`/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab`。
- DSA 本地仓库路径：`/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis`。
- 当前 Serenity 仓库仍有既有未提交的 generated UI 输出变更：`output/ui/analyses/manifest.json`、`output/ui/reports/deliverable-research-report.md`、`output/ui/runs.json`、`output/ui/analyses/topic-2bde5fabbc/`。
- 上述 `output/ui/*` 变更不是 DSA-first Serenity Core 文档/规划阶段的一部分；除非用户明确要求，不要 stage、提交、回滚或覆盖它们。

### 下次启动接续提示词

下次新开会话时，可直接发送以下提示词：

```text
请继续在 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab 当前进度上开发。

先阅读并遵守：
1. docs/dsa-first-serenity-core-development-plan.md
2. docs/dsa-first-serenity-core-development-tracker.md
3. tasks/todo.md
4. tasks/lessons.md

当前状态：
- Serenity 仓库路径：/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
- DSA 仓库路径：/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
- DSA 分支：codex/serenity-phase-0-evidence-bridge
- Serenity 最新提交：请以下次启动时 `git rev-parse --short HEAD` 为准；当前 tracker 已刷新到 P3-T04 完成后的状态
- DSA 最新提交：61b52ce docs(serenity): 记录 P3-T04 专表升级决策

已完成：
- Global guardrails：G-T01、G-T02、G-T03
- Phase 0 Evidence Bridge POC：P0-T01、P0-T02、P0-T03、P0-T04 与 Phase 0 review gate
- Phase 1 Analysis Report Add-On：P1-T01、P1-T02、P1-T03、P1-T04、P1-T05 与 P1 Phase Review
- Phase 2 Agent Tools：P2-T01、P2-T02、P2-T03 与 P2 Phase Review
- Phase 3 Intelligence Workflow Persistence：P3-T01 Research Task Data Contract、P3-T02 Snapshot-Based Task Persistence、P3-T03 Intelligence Service 接入、P3-T04 专表升级决策 Gate
- 已新增 research-only `serenity_evidence_quality` Agent tool
- 已新增 research-only `serenity_evidence_gaps` Agent tool
- 两个 tool 均通过 DSA `src/agent/tools/analysis_tools.py` 的 `ALL_ANALYSIS_TOOLS` 注册
- tools 只审计调用方提供的 low-sensitivity analysis `context`
- 缺少 context 返回 `analysis_context_required` blocked diagnostics
- 异常返回 sanitized `failed_open` diagnostics
- 不抓取行情、新闻或 DB，不修改 DSA 交易字段
- P2 Phase Review 已收紧 gate：`SERENITY_RESEARCH_ENABLED=false` 时即使显式研究质量请求也不暴露 tools；`SERENITY_RESEARCH_ENABLED=true` 时仍必须由用户文本显式包含研究质量、证据缺口、来源覆盖或 readiness 意图才暴露 tools
- P2 Phase Review 已移除外部请求 `context.serenity_research_tools_enabled=True` 的绕过能力
- P2 Phase Review 已修复 Specialist `SkillAgent` 空 `required_tools` 时回退全量 registry 的问题
- P3-T01 已新增 DSA `docs/serenity-research-task-contract.md`
- P3-T01 已新增 `SerenityResearchTask`、`SerenityResearchTaskRerunContext`、`SerenityResearchTaskStatusTransition` schema
- P3-T01 已定义 task 状态机：`open -> collecting -> verified` 与 `open -> dismissed`
- P3-T01 已定义至少四类 required gap：`primary_source`、`risk_coverage`、`demand_validation`、`invalidation_plan`
- P3-T01 仍未新增 DB 表、migration、service persistence 或 intelligence workflow 行为
- P3-T02 已新增 DSA `src/serenity/services/research_task_service.py`
- P3-T02 已从 audit acquisition tasks 生成 deterministic research task id
- P3-T02 已把 bounded tasks 写入 `analysis_history.context_snapshot.serenity_research.tasks`
- P3-T02 已支持 snapshot 内 task status 更新：`open -> collecting -> verified` 与 `open -> dismissed`
- P3-T02 已支持 `history_id + task_id` 精确定位，避免同一 query/code/report_type 重复分析误更新
- P3-T02 已对 snapshot tasks 限制 top 20，并逐条通过 `SerenityResearchTask` schema 校验、剥离 trading fields
- P3-T02 未新增 DB 表、migration、provider fetch、Agent prompt、intelligence workflow mutation 或 DSA trading field 映射
- P3-T03 已在 DSA `IntelligenceService` 增加 snapshot-first `list_serenity_research_tasks()` 与 `update_serenity_research_task_status()`
- P3-T03 已新增 `GET /api/v1/intelligence/serenity-research/tasks` 与 `PATCH /api/v1/intelligence/serenity-research/tasks/{task_id}/status`
- P3-T03 已复用 `SerenityResearchTask` schema 暴露 research-only task，并附带 `history_id`、`query_id`、`stock_code`、`report_type` 等 snapshot row anchors
- P3-T03 继续通过 `DatabaseManager.update_analysis_history_serenity_research_task_status()` 写回既有 `context_snapshot.serenity_research.tasks`
- P3-T03 未新增 DB 表、migration、provider fetch、Agent prompt、独立 Serenity 工作台、UI 大页面或 DSA trading field 映射
- P3-T04 已新增 DSA `docs/serenity-persistence-decision-record.md`
- P3-T04 gate 只满足 1 项：跨 report 过滤任务；未满足 owner/assignee、audit trail、恢复/重试队列、snapshot 性能不可接受
- P3-T04 决策：继续 snapshot-first，不新增 `serenity_research_tasks` 或 `serenity_research_task_events`
- P3-T04 已记录未来触发条件：大规模查询性能、并发状态更新、event-level audit trail、多用户 owner/assignee、可靠队列或证据跨报告复用

未完成下一步：
- 从 tracker 的 `P3 Phase Review` 开始
- Phase 3 Intelligence Workflow Persistence 尚未完成
- Phase 4 Provenance Safety Guardrails 尚未开始
- DB 专表尚未启动；目前仍使用 `analysis_history.context_snapshot.serenity_research`

边界要求：
- daily_stock_analysis 仍是主产品和主运行时
- Serenity Core 只做证据质量、研究审计、补证闭环和安全边界辅助
- 不要把 Serenity score 映射到 DSA 的交易建议、目标价、仓位、止损止盈、趋势预测或 sentiment_score
- 不新增交易建议语义，不改变 DSA 原有字段含义
- 继续保持 `SERENITY_RESEARCH_ENABLED=false` 默认关闭和 fail-open 策略
- Phase 3 研究任务只能表示 evidence gaps / follow-up research，不得自动创建交易建议或修改 DSA trading fields
- 继续优先使用 snapshot / metadata；P3-T04 已明确当前不通过专表升级 gate
- P3 Phase Review 只能审查 Phase 3 exit criteria，不新增 DB migration/table，除非后续单独重新打开专表决策 gate

P3-T01 验证证据：
- red check `python3.11 -m pytest tests/api/v1/test_serenity_research_task_schema.py -q` -> collection error，缺少 `SerenityResearchTask` / `SerenityResearchTaskStatusTransition`
- after fix same command -> `9 passed`
- `python3.11 -m pytest tests/serenity/test_serenity_api_schema_contract.py tests/serenity/test_analysis_history_serenity_snapshot.py -q` -> `8 passed`
- `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`
- `python3.11 -m pytest tests/serenity -q` -> `30 passed`
- target `py_compile` -> pass
- safety scan only matched existing boundary docs and broad-regex smoke test name
- `git diff --check` -> pass

P3-T02 验证证据：
- red check `python3.11 -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py -q` -> collection error，缺少 `src.serenity.services.research_task_service`
- after fix same command -> `13 passed`
- schema/history regression `python3.11 -m pytest tests/api/v1/test_serenity_research_task_schema.py tests/serenity/test_analysis_history_serenity_snapshot.py -q` -> `12 passed`
- `python3.11 -m pytest tests/serenity -q` -> `39 passed`
- boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`
- target `py_compile` -> pass
- safety scan only matched existing boundary docs / baseline scan command / broad-regex smoke test name
- DB-table scan only matched contract docs and schema test names; no migration/table added
- `git diff --check` -> pass

P3-T03 验证证据：
- red service check `python3.11 -m pytest tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_list_serenity_research_tasks_filters_snapshot_tasks_by_symbol_and_status tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_update_serenity_research_task_status_uses_existing_snapshot_helper -q` -> `2 failed`，缺少 `IntelligenceService` research task list/update 方法
- red API check `python3.11 -m pytest tests/test_intelligence_api.py::IntelligenceApiTestCase::test_list_serenity_research_tasks_from_intelligence_api tests/test_intelligence_api.py::IntelligenceApiTestCase::test_update_serenity_research_task_status_from_intelligence_api -q` -> `2 failed`，新增 routes 返回 404
- after fix focused service/API checks -> `5 passed`
- P3 regression `python3.11 -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py tests/api/v1/test_serenity_research_task_schema.py -q` -> `22 passed`
- intelligence regression `python3.11 -m pytest tests/test_intelligence_service.py tests/test_intelligence_api.py -q` -> `40 passed, 1 warning`
- boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`
- target `py_compile` -> pass
- safety scan only matched existing boundary/baseline docs and broad-regex smoke test name
- DB-table scan matched function/test names plus contract doc mention only; no migration/table added
- `git diff --check` -> pass

P3-T04 验证证据：
- decision gate review：只满足跨 report filtering 1 项，不满足至少两项专表升级条件
- DSA `docs/serenity-persistence-decision-record.md` 记录继续 snapshot-first，不新增 DB 专表
- P3 regression `python3.11 -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py tests/api/v1/test_serenity_research_task_schema.py -q` -> `22 passed`
- intelligence regression `python3.11 -m pytest tests/test_intelligence_service.py tests/test_intelligence_api.py -q` -> `40 passed, 1 warning`
- boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`
- target `py_compile` -> pass
- safety scan only matched existing boundary/baseline docs and broad-regex smoke test name
- DB-table scan matched existing function/test names plus contract/decision docs only; no migration/table added
- `git diff --check` -> pass

已知环境 blocker：
- full `python3.11 -m pytest tests/test_agent_registry.py -q` 此前仍因缺少 `pandas` 在 unrelated `src/storage.py` import 处失败；最近记录为 `1 failed, 58 passed`
- 这是既有环境依赖缺口，不要归因于 Serenity P3-T03

当前工作区注意事项：
- DSA 工作区完成 P3-T04 后应为 clean，HEAD 以后续提交为准
- Serenity 仓库仍有既有未提交 generated UI 输出变更：
  - output/ui/analyses/manifest.json
  - output/ui/reports/deliverable-research-report.md
  - output/ui/runs.json
  - output/ui/analyses/topic-2bde5fabbc/
- 不要修改、stage、提交或回滚这些 output/ui/* 生成物，除非我明确要求

工作习惯：
- 每个阶段性任务开始前，先在 `tasks/todo.md` 写可勾选计划
- 实现前核对 tracker entry criteria
- 运行新鲜验证命令
- 每完成阶段性任务后，自动更新：
  - docs/dsa-first-serenity-core-development-tracker.md
  - tasks/todo.md
  - tasks/lessons.md（如有可复用经验）
  - tracker 内“下次启动接续提示词”
  - 最终回复中的可直接复制启动提示词
- restart prompt 必须包含：已完成范围、未完成下一步、最新 Serenity/DSA commit id、验证证据、已知环境 blocker、禁止 stage 的文件
- 只 stage 本阶段相关文件
- 用详细中文 commit message 提交
```

---

## 0. 使用规则

### 0.1 状态枚举

| 状态 | 含义 | 使用规则 |
| --- | --- | --- |
| `Not Started` | 尚未开始 | 默认状态，未产生代码或设计变更 |
| `In Progress` | 正在实现 | 已有分支、草稿、测试或代码变更 |
| `Blocked` | 被明确依赖阻塞 | 必须记录阻塞原因、负责人、解除条件 |
| `In Review` | 已完成实现，等待审查 | 必须附 diff、测试证据和风险说明 |
| `Verified` | 已按 DoD 验证 | 必须附新鲜验证命令与结果 |
| `Released` | 已合入目标分支并发布 | 必须附版本、commit、部署或发布记录 |
| `Deferred` | 主动延期 | 必须记录延期原因和重新评估条件 |
| `Dropped` | 明确取消 | 必须说明取消原因和替代方案 |

### 0.2 任务记录字段

每个任务执行时必须补齐以下字段：

```markdown
Owner:
Status:
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:
```

### 0.3 完成定义

任一任务不能只因“代码写完”标记为完成。至少满足：

- [ ] 需求已映射到明确的文件和接口。
- [ ] 新增或修改的行为有测试覆盖，或记录了不写测试的具体原因。
- [ ] 运行了任务指定的验证命令，并记录 exit code 与关键输出。
- [ ] 失败路径、降级路径、空数据路径和 feature flag 关闭路径已验证。
- [ ] 没有把 Serenity score 混入 DSA 交易建议、目标价、仓位、止损止盈、趋势预测或 `sentiment_score`。
- [ ] 没有引入跨仓库绝对路径 import。
- [ ] 没有让 Serenity audit 阻塞 DSA 主分析链路。
- [ ] 已记录回滚方式。

### 0.4 阶段门禁

| 阶段 | 门禁目标 | 允许发布范围 |
| --- | --- | --- |
| Phase 0 | 证明 evidence bridge 可独立运行 | 仅本地 POC、无 API/UI/DB 变更 |
| Phase 1 | 在 DSA 分析报告中可选展示 evidence quality | API schema + optional UI panel + context snapshot |
| Phase 2 | Agent 可显式查询证据质量和缺口 | Agent tools，默认不影响主 prompt 决策 |
| Phase 3 | 研究任务可持久化和复跑 | `context_snapshot.serenity_research` 优先，必要时再加表 |
| Phase 4 | provenance 和 safety guardrails 可审计 | 报告安全扫描、引用溯源、发布门禁 |

---

## 1. 全局约束清单

### G-T01: 集成边界守卫

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit:
Evidence: DSA `docs/serenity-integration-boundaries.md`、`.env.example`、`README.md`、`docs/CONTRIBUTING.md`、`tests/test_serenity_integration_boundaries.py`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `git diff --check` -> exit 0.
Decision Notes: 按实际 DSA 仓库结构将贡献规范落点从 tracker 原写法 `CONTRIBUTING.md` 校正为 `docs/CONTRIBUTING.md`。根据只读子代理审查，补充静态自动化边界测试，避免 G-T01 只有文档约束。
Rollback Notes: 删除 DSA `docs/serenity-integration-boundaries.md` 与 `tests/test_serenity_integration_boundaries.py`，移除 `.env.example`、`README.md`、`docs/CONTRIBUTING.md` 中 Serenity 段落即可回滚；不影响运行时代码。

**Purpose:** 防止后续迭代把 Serenity 辅助能力扩张成新的产品壳、交易建议引擎或 DSA 主链路阻塞点。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-integration-boundaries.md`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/README.md`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/.env.example`

**Dependencies:** `docs/dsa-first-serenity-core-development-plan.md`

**Checklist:**

- [x] 写清 DSA owns / Serenity owns / forbidden call sites。
- [x] 写清 `SERENITY_RESEARCH_ENABLED=false` 的默认关闭策略。
- [x] 写清 fail-open 策略：Serenity 异常只进入 diagnostics，不影响 DSA analysis success。
- [x] 写清禁止字段映射：`sentiment_score`、`operation_advice`、`action`、`trend_prediction`、`target_price`、`position_sizing`、`sniper_points`、stop loss、take profit。
- [x] 写清 import 方向：DSA application layer -> Serenity services -> adapters -> core。
- [x] 写清跨仓库代码进入 DSA 的方式：复制、vendor、package 三选一，不允许运行时绝对路径 import。
- [x] 增加 G-T01 静态自动化守卫，阻断未来 core 反向 import、绝对路径 import 和 Serenity 质量输出写入 DSA 交易字段。

**Validation:**

```bash
rg -n "SERENITY_RESEARCH_ENABLED|fail-open|sentiment_score|operation_advice|target_price|position_sizing" /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-integration-boundaries.md
git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis diff --check
```

**DoD:**

- [x] 文档中的允许/禁止边界可被工程师直接执行。
- [x] `.env.example` 包含默认关闭的 Serenity 配置。
- [x] README 只描述辅助研究能力，不暗示 Serenity 生成交易建议。
- [x] 静态测试覆盖默认关闭、fail-open、禁止字段映射、未来 `src/serenity/**` import 和字段污染边界。

**Rollback:** 删除新增边界文档、移除 README 和 `.env.example` 的 Serenity 段落。

### G-T02: 分支与提交规范

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit:
Evidence: DSA `docs/serenity-integration-boundaries.md` 第 7 节、`docs/CONTRIBUTING.md` Serenity Core 阶段集成规范；`git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis branch --show-current` -> `codex/serenity-phase-0-evidence-bridge`.
Decision Notes: DSA 仓库无根目录 `CONTRIBUTING.md`，实际落点为 `docs/CONTRIBUTING.md`；阶段提交 scope 统一使用 `docs(serenity)`, `feat(serenity)`, `test(serenity)`。
Rollback Notes: 恢复 `docs/CONTRIBUTING.md` 与边界文档中新增的 Serenity 分支、PR、commit 规范。

**Purpose:** 保证长周期集成可审计、可回退、可分阶段合入。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-integration-boundaries.md`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/CONTRIBUTING.md`

**Dependencies:** G-T01

**Checklist:**

- [x] 建立阶段分支命名：`codex/serenity-phase-0-evidence-bridge` 至 `codex/serenity-phase-4-provenance-safety`。
- [x] 每个阶段至少一个独立 PR，不把 P0-P4 堆成单次大改。
- [x] 提交信息使用 `feat(serenity): ...`、`test(serenity): ...`、`docs(serenity): ...`。
- [x] 每个 PR 描述必须包含 feature flag 状态、验证命令、回滚路径、未完成风险。
- [x] 每个阶段合入前记录 `git diff --stat` 和关键变更文件。

**Validation:**

```bash
git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis status --short
git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis branch --show-current
```

**DoD:**

- [x] 团队可以通过分支和 PR 判断每个阶段的完整性。
- [x] 任一阶段可单独 revert，不影响其他未发布阶段。

**Rollback:** 恢复 CONTRIBUTING 和边界文档中新增的 Serenity 分支规范。

### G-T03: 基线验证快照

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit:
Evidence: DSA `docs/serenity-baseline-verification.md`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; backend baseline `python3.11 -m pytest -m "not network"` -> exit 2 due missing dependencies (`pandas`, `json_repair`); frontend `npm --prefix apps/dsa-web run lint` and `npm --prefix apps/dsa-web run build` -> exit 127 due missing `node_modules`.
Decision Notes: 记录 Python 3.9 默认命令、Python 3.11 可用但依赖未安装、Node/npm 版本和前端依赖缺口；现有 baseline 失败不归因于 Serenity，因为尚未引入 Serenity runtime code。
Rollback Notes: 删除 DSA `docs/serenity-baseline-verification.md`；该文档无运行时副作用。

**Purpose:** 在任何 Serenity 代码进入 DSA 前，记录 DSA 当前可运行基线，避免后续无法判断回归来源。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-baseline-verification.md`

**Dependencies:** G-T01

**Checklist:**

- [x] 记录 Python 版本、Node 版本、包管理器、当前分支、当前 commit。
- [x] 运行 DSA 后端单元测试并记录结果。
- [x] 运行 DSA 前端类型检查、lint 或测试脚本并记录结果。
- [x] 如果测试因环境依赖失败，记录失败命令、错误摘要、缺失依赖、恢复条件。
- [x] 记录现有失败，不把历史失败归因于 Serenity 集成。

**Validation:**

```bash
git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis rev-parse --short HEAD
python --version
node --version
```

**DoD:**

- [x] 有一份可审计的 baseline 文档。
- [x] 后续阶段能对比 baseline 判断新增风险。

**Rollback:** 删除 baseline 文档；不改变代码。

---

## 2. Phase 0: Evidence Bridge POC

**Phase Goal:** 在不改 DSA API、UI、DB 的前提下，证明 DSA analysis context 可以被转换为 Serenity EvidenceItem，并生成稳定的 evidence-quality audit JSON。

**Phase Entry Criteria:**

- [x] G-T01 至 G-T03 已完成或明确豁免。
- [x] DSA 和 Serenity 当前仓库路径存在。
- [x] DSA 主分析链路 baseline 已记录。

**Phase Exit Criteria:**

- [ ] 本地命令可从 DSA sample context 输出 audit JSON。
- [ ] 失败输入、空输入、缺 source 输入均有确定输出。
- [ ] 没有 API/UI/DB 变更。
- [ ] 没有跨仓库 runtime absolute import。

### P0-T01: Serenity Core 最小契约抽取

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `4e34c78`
Evidence: DSA `src/serenity/core/*`, `src/serenity/__init__.py`, `tests/serenity/core/test_core_contract.py`; `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py` -> exit 0; `from src.serenity.core.evidence import EvidenceItem` smoke -> `EvidenceItem`.
Decision Notes: 以 DSA-facing EvidenceItem 字段重建最小 core，而不是直接复制 Serenity Alpha Lab 原模型字段；所有模块只用标准库和同目录 core 依赖，不引入 UI、CLI、memo pack、HTTP server、output writer、provider、SQLAlchemy、FastAPI、notification 或 task queue。缺 source metadata 明确产生 `missing_source_metadata` gap，不补虚假 source。
Rollback Notes: 删除 DSA `/src/serenity/` 和 `/tests/serenity/core/test_core_contract.py`；不会影响 DSA 原有代码路径。

**Purpose:** 从 Serenity Alpha Lab 抽出 DSA 集成所需的最小核心，不携带 UI、CLI、memo pack、local server 或生成物。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/evidence.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/retrieval.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/scoring.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/source_coverage.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/readiness.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/acquisition_queue.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/__init__.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/core/test_core_contract.py`

**Dependencies:** G-T01, G-T03

**Implementation Checklist:**

- [x] 复制或重建 `EvidenceItem` 的最小字段：`id`、`title`、`source_type`、`publisher`、`published_at`、`url`、`excerpt`、`claims`、`symbols`、`metadata`。
- [x] 保留 deterministic scoring / coverage / readiness 逻辑所需函数。
- [x] 删除或不迁入 Serenity UI、CLI、memo pack、HTTP server、output writer、absolute path defaults。
- [x] 所有 core module 只依赖 Python 标准库和同目录 core module。
- [x] 为空 evidence list 返回稳定 audit 结果，而不是抛异常。
- [x] 为缺失 source metadata 的 evidence 产生 gap，而不是补虚假 source。

**Tests:**

```bash
python -m pytest tests/serenity/core/test_core_contract.py -q
python - <<'PY'
from src.serenity.core.evidence import EvidenceItem
print(EvidenceItem.__name__)
PY
```

**DoD:**

- [x] `src/serenity/core/*` 没有 import DSA provider、FastAPI、SQLAlchemy、React asset、notification、task queue。
- [x] 测试覆盖正常 evidence、空 evidence、缺 source evidence。
- [x] `python -m pytest tests/serenity/core/test_core_contract.py -q` 通过。

**Rollback:** 删除 `/src/serenity/core/` 和对应测试，不影响 DSA 原有代码。

### P0-T02: DSA Context 到 Evidence Adapter

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `b85b72a`
Evidence: DSA `src/serenity/adapters/dsa_context_to_evidence.py`, `src/serenity/adapters/__init__.py`, `tests/serenity/adapters/test_dsa_context_to_evidence.py`; `python3.11 -m pytest tests/serenity/adapters/test_dsa_context_to_evidence.py -q` -> `3 passed`; `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py` -> exit 0; `git diff --check` -> exit 0.
Decision Notes: Adapter 输入保持为普通 `dict[str, Any]`，支持 `subject`、`blocks.quote`、`blocks.technical`、`blocks.fundamentals`、`blocks.news`、`social_context`、`history_context` 以及 legacy flat keys；所有 evidence id 使用内容派生的稳定 id；无法证明来源的数据保留为 `unverified_context`，由 core readiness/coverage 继续识别；adapter 不调用 provider、API、DB、UI、notification 或 task queue。
Rollback Notes: 删除 DSA `src/serenity/adapters/` 与 `tests/serenity/adapters/test_dsa_context_to_evidence.py`；不影响 DSA 原有主分析链路、API、UI 或 DB。

**Purpose:** 将 DSA 分析上下文转成 Serenity EvidenceItem，保留来源、摘要、时间、ticker、数据类型与 provenance。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/adapters/dsa_context_to_evidence.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/adapters/__init__.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/adapters/test_dsa_context_to_evidence.py`

**Dependencies:** P0-T01

**Implementation Checklist:**

- [x] 定义 adapter 输入为普通 `dict[str, Any]`，避免直接绑定 DSA 大对象。
- [x] 从行情、基本面、技术指标、新闻、社交舆情、历史上下文中提取 evidence candidates。
- [x] 为每类 evidence 设置明确 `source_type`，例如 `market_data`、`fundamental`、`technical_indicator`、`news`、`social`、`history_context`。
- [x] 对无法证明来源的数据标记 `source_type="unverified_context"`，并让 readiness gate 可识别。
- [x] 生成稳定 `id`，避免同一上下文每次 run 产生不可追踪随机 id。
- [x] 不在 adapter 内调用任何外部数据源。
- [x] 不修改传入 context。

**Tests:**

```bash
python -m pytest tests/serenity/adapters/test_dsa_context_to_evidence.py -q
```

**DoD:**

- [x] adapter 对完整 context、空 context、缺少新闻、缺少基本面的输入都有稳定输出。
- [x] adapter 输出的 EvidenceItem 可被 P0-T01 core 接收。
- [x] 没有网络请求、数据库写入或 provider 调用。

**Rollback:** 删除 adapter 与测试。

### P0-T03: Evidence Quality Service POC

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `a382a0f`
Evidence: DSA `src/serenity/services/evidence_quality_service.py`, `src/serenity/services/__init__.py`, `tests/serenity/services/test_evidence_quality_service.py`; Red test `python3.11 -m pytest tests/serenity/services/test_evidence_quality_service.py -q` initially -> `4 failed` due missing service module; Green validation `python3.11 -m pytest tests/serenity/services/test_evidence_quality_service.py -q` -> `4 passed`; adapter tests -> `3 passed`; core contract -> `3 passed`; boundary guard -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py src/serenity/services/*.py` -> exit 0; `git diff --check` -> exit 0.
Decision Notes: Service defaults to disabled and does not call the adapter when disabled; enabled path composes adapter, scoring, source coverage, readiness and acquisition queue into a stable research-only audit JSON; empty context returns a deterministic blocked audit; adapter/core exceptions return `status="failed_open"` with sanitized diagnostics instead of raising into the DSA main chain. Output keeps evidence quality naming and does not emit DSA trading-decision fields.
Rollback Notes: 删除 DSA `src/serenity/services/` 与 `tests/serenity/services/test_evidence_quality_service.py`；不会影响 DSA 原有 API、UI、DB、provider、notification、task queue 或交易报告语义。

**Purpose:** 提供 DSA 可调用的窄服务接口，输入 DSA context，输出 Serenity audit JSON。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/services/evidence_quality_service.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/services/__init__.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/services/test_evidence_quality_service.py`

**Dependencies:** P0-T02

**Implementation Checklist:**

- [x] 定义 `EvidenceQualityService.evaluate(context: dict[str, Any]) -> dict[str, Any]`。
- [x] 输出字段包含 `enabled`、`status`、`quality_score`、`readiness`、`coverage`、`evidence_count`、`gaps`、`diagnostics`。
- [x] 默认配置关闭时返回 `enabled=false` 和最小 diagnostics。
- [x] 开启配置时调用 adapter、scoring、coverage、readiness。
- [x] 捕获异常并返回 `status="failed_open"`，不向上抛出影响 DSA 主链路。
- [x] 记录异常类型和安全摘要，不记录 secrets 或完整用户敏感输入。

**Tests:**

```bash
python -m pytest tests/serenity/services/test_evidence_quality_service.py -q
```

**DoD:**

- [x] disabled、enabled、empty context、adapter exception 四类测试通过。
- [x] 服务输出可 JSON 序列化。
- [x] 失败路径为 fail-open。

**Rollback:** 删除 service 与测试。

### P0-T04: CLI / Script POC Runner

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `e15e588`
Evidence: DSA `scripts/serenity_evidence_audit_poc.py`, `tests/serenity/test_evidence_audit_poc_script.py`, `tests/fixtures/serenity/dsa_context_full.json`, `docs/serenity-phase-0-poc.md`; Red test `python3.11 -m pytest tests/serenity/test_evidence_audit_poc_script.py -q` initially -> `3 failed` due missing script; enabled script smoke `python3.11 scripts/serenity_evidence_audit_poc.py --sample tests/fixtures/serenity/dsa_context_full.json --enabled` -> exit 0 with parseable audit JSON; runner tests -> `3 passed`; service tests -> `4 passed`; adapter tests -> `3 passed`; core contract -> `3 passed`; boundary guard -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py src/serenity/services/*.py scripts/serenity_evidence_audit_poc.py` -> exit 0; `git diff --check` -> exit 0.
Decision Notes: Runner reads only a local JSON sample and writes audit JSON to stdout; default run remains disabled, and `--enabled` explicitly runs the research audit. The script does not read DSA DB, start FastAPI, call providers, mutate reports, or change API/UI/DB behavior. Documentation records sample input, commands, output fields, and Phase 0 safety boundary.
Rollback Notes: 删除 DSA `scripts/serenity_evidence_audit_poc.py`、`tests/serenity/test_evidence_audit_poc_script.py`、`tests/fixtures/serenity/dsa_context_full.json` 与 `docs/serenity-phase-0-poc.md`；不会影响 DSA 原有运行时。

**Purpose:** 用最小脚本证明 evidence bridge 可独立运行，供后续 Phase 1 接入前验证。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/scripts/serenity_evidence_audit_poc.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/test_evidence_audit_poc_script.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-phase-0-poc.md`

**Dependencies:** P0-T03

**Implementation Checklist:**

- [x] 脚本接受 sample JSON 路径作为输入。
- [x] 脚本输出 audit JSON 到 stdout。
- [x] 脚本支持 `--enabled` 显式开启，默认关闭。
- [x] 示例文档记录 sample 输入、命令、输出字段解释。
- [x] 不读取 DSA DB，不启动 FastAPI，不调用行情 provider。

**Tests:**

```bash
python scripts/serenity_evidence_audit_poc.py --sample tests/fixtures/serenity/dsa_context_full.json --enabled
python -m pytest tests/serenity/test_evidence_audit_poc_script.py -q
```

**DoD:**

- [x] POC 可在本地命令行稳定输出 audit JSON。
- [x] stdout 是可解析 JSON。
- [x] 文档说明 Phase 0 未修改 API/UI/DB。

**Rollback:** 删除 POC script、测试和 Phase 0 POC 文档。

### P0 Phase Review

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit:
Evidence: `python3.11 scripts/serenity_evidence_audit_poc.py --sample tests/fixtures/serenity/dsa_context_full.json --enabled` -> exit 0, parseable audit JSON with `status='blocked'`, `enabled=True`, `research_only=True`, `evidence_count=6`, ticker `600519`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m pytest tests/serenity -q` -> `13 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py src/serenity/services/*.py scripts/serenity_evidence_audit_poc.py` -> exit 0; `rg -n "/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab|serenity_alpha_lab" src/serenity` -> no cross-repo runtime imports; `git diff --check` -> exit 0; DSA `git status --short` -> clean; Phase 1 callsite confirmed at DSA `src/services/analysis_service.py`.
Decision Notes: Phase 0 exit criteria are met: local command outputs stable audit JSON, empty/failure paths are covered by tests, no API/UI/DB changes were introduced, no cross-repository runtime absolute import exists, and Serenity remains disabled-by-default/fail-open/research-only. Existing broad baseline environment failures remain unchanged from G-T03 (`pandas`, `json_repair`, frontend `node_modules` missing) and are not attributed to Serenity.
Rollback Notes: Phase 0 can be reverted by removing DSA `src/serenity/`, `tests/serenity/`, `scripts/serenity_evidence_audit_poc.py`, `tests/fixtures/serenity/dsa_context_full.json`, `docs/serenity-phase-0-poc.md`, and prior Global-phase docs/config changes if a full rollback is required.

**Review Checklist:**

- [x] `python -m pytest tests/serenity -q` 通过或记录明确的环境失败。
- [x] `rg -n "/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab|serenity_alpha_lab" /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity` 无 runtime absolute import。
- [x] `git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis diff --check` 通过。
- [x] 与 baseline 对比，DSA 原有测试没有新增失败。
- [x] Phase 1 接入点已经被确认：`src/services/analysis_service.py`。

---

## 3. Phase 1: Analysis Report Add-On

**Phase Goal:** 在 DSA 分析完成后，以可选附加块的形式返回和展示 Serenity evidence-quality audit，不改变 DSA 原有核心分析结果。

**Phase Entry Criteria:**

- [ ] Phase 0 exit criteria 已满足。
- [ ] `SERENITY_RESEARCH_ENABLED` 默认关闭。
- [ ] API schema 添加策略已确认：新增 optional nested block，不改原字段语义。

**Phase Exit Criteria:**

- [ ] API response 支持 optional `serenity_research`。
- [ ] 历史记录优先写入 `analysis_history.context_snapshot.serenity_research`。
- [ ] Web UI 在报告摘要后展示可选 evidence-quality panel。
- [ ] feature flag 关闭时 UI/API 与原行为一致。

### P1-T01: API Schema 增加 Serenity Audit 类型

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch:
PR:
Commit: DSA `10b9dda` (`feat(serenity): 增加可选 Research Audit API Schema`)
Evidence: Pure schema import smoke passed; `python3.11 -m pytest tests/serenity/test_serenity_api_schema_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/serenity -q` -> `16 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; schema + Serenity `py_compile` passed; static scan found no forbidden trading-decision fields in `api/v1/schemas/serenity.py`; `git diff --check` passed.
Decision Notes: Added optional nested `serenity_research` contract through `api/v1/schemas/serenity.py`, `analysis.py`, and `history.py`; `api/v1/__init__.py` now lazy-loads the router so schema-only imports do not require endpoint/storage dependencies such as `pandas`.
Rollback Notes: Revert DSA commit `10b9dda` to remove the optional schema block and lazy import change.

**Purpose:** 为 Serenity audit 提供稳定 API contract，同时保持向后兼容。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/analysis.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/history.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/api/v1/test_analysis_schema.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/api/v1/test_history_schema.py`

**Dependencies:** P0-T03

**Implementation Checklist:**

- [x] 新增 nested model：`SerenityEvidenceGap`、`SerenityCoverageSummary`、`SerenityReadinessSummary`、`SerenityResearchAudit`。
- [x] 在 analysis response 中新增 optional `serenity_research: SerenityResearchAudit | None`。
- [x] 在 history schema 中从 `context_snapshot.serenity_research` 暴露同名 optional block。
- [x] 保持旧 response fixture 不需要新增字段也能通过解析。
- [x] 禁止修改既有交易语义字段类型或含义。

**Tests:**

```bash
python -m pytest tests/api/v1/test_analysis_schema.py tests/api/v1/test_history_schema.py -q
```

**DoD:**

- [x] 旧 payload 和新 payload 均可解析。
- [x] 新 block 缺省时为 `None` 或不出现，不破坏旧客户端。
- [x] schema 字段命名明确区分 evidence quality 与 investment advice。

**Rollback:** 移除 schema 新增类型和 optional 字段。

### P1-T02: Analysis Service 附加 Serenity Audit

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch:
PR:
Commit: DSA `952c708` (`feat(serenity): 附加可选 Research Audit 到分析响应`)
Evidence: `python3.11 -m py_compile src/services/analysis_service.py src/config.py src/core/config_registry.py api/v1/endpoints/analysis.py tests/serenity/test_analysis_service_serenity.py tests/test_config_registry.py` -> exit 0; `python3.11 -m pytest tests/serenity/test_analysis_service_serenity.py tests/test_config_registry.py::TestSettingsHelpMetadata::test_serenity_research_enabled_is_explicitly_registered tests/serenity/test_serenity_api_schema_contract.py -q` -> `8 passed`; `python3.11 -m pytest tests/serenity -q` -> `20 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_config_registry.py -q` -> `55 passed`; `git diff --check` passed; DSA `git status --short` clean after commit.
Decision Notes: Runtime attach happens only after the DSA base response is built and only when `serenity_research_enabled` is true. The audit is attached as top-level optional `serenity_research`; `SERENITY_RESEARCH_ENABLED=false` does not instantiate `EvidenceQualityService` or add response fields. Exceptions fail open into `status="failed_open"` audit metadata without changing DSA trading fields. Heavy imports in `analysis_service.py` were made lazy so schema/service tests remain runnable in the known missing-`pandas` environment.
Rollback Notes: Revert DSA commit `952c708` to remove runtime attach, config registry/help additions, sync response passthrough, and P1-T02 tests.

**Purpose:** 在 DSA base report 生成后调用 EvidenceQualityService，附加 audit block。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/analysis_service.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/config.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/services/test_analysis_service_serenity.py`

**Dependencies:** P1-T01

**Implementation Checklist:**

- [x] 读取 `SERENITY_RESEARCH_ENABLED`，默认 false。
- [x] 在 base `AnalysisResult` 已完成后构造 context snapshot。
- [x] 调用 `EvidenceQualityService.evaluate(...)`，捕获异常并写 diagnostics。
- [x] 将结果附加到 response optional block。
- [x] feature flag 关闭时不实例化或不执行 expensive audit。
- [x] 不改变评分、趋势、建议、买卖点、风险警报生成逻辑。

**Tests:**

```bash
python -m pytest tests/services/test_analysis_service_serenity.py -q
```

**DoD:**

- [x] flag off 测试证明 response 不含或为空 `serenity_research`。
- [x] flag on 测试证明 response 包含 audit。
- [x] service exception 测试证明 DSA analysis 仍成功。
- [x] 测试断言原 DSA 字段未被 Serenity 改写。

**Rollback:** 移除 `analysis_service.py` 中 Serenity service 调用和 config 项。

### P1-T03: 历史记录 Context Snapshot 持久化

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch:
PR:
Commit: DSA `c193f17`
Evidence: DSA `src/storage.py`, `src/services/analysis_service.py`, `tests/serenity/test_analysis_history_serenity_snapshot.py`, `tests/serenity/test_analysis_service_serenity.py`; focused P1-T03 tests -> `8 passed`; `python3.11 -m pytest tests/serenity -q` -> `24 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; py_compile target files -> exit 0; `git diff --check` -> exit 0.
Decision Notes: 不新增 DB column/migration/table；直接保存路径读取 `result.serenity_research` 并白名单合并到 `context_snapshot.serenity_research`，AnalysisService 因历史保存早于 response attach，新增 best-effort 后置补写 helper，按 `query_id + code + report_type` 精准匹配最新记录；`SAVE_CONTEXT_SNAPSHOT=false` 或缺失 snapshot 时不强行创建快照。
Rollback Notes: Revert DSA commit `c193f17` 即可停止写入和补写 `context_snapshot.serenity_research`；历史中已存在的额外 JSON block 可无害保留，旧读取路径兼容缺失 block。

**Purpose:** 按方案优先将 Serenity audit 写入现有 `analysis_history.context_snapshot.serenity_research`，避免过早新增表。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/storage.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/analysis_service.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/test_analysis_history_serenity_snapshot.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/test_analysis_service_serenity.py`

**Dependencies:** P1-T02

**Implementation Checklist:**

- [x] 确认 `context_snapshot` 当前类型和序列化路径。
- [x] 写入 `context_snapshot["serenity_research"]`，不新增顶层 DB 列。
- [x] 历史读取时保留该 block。
- [x] 老记录缺少该 block 时正常返回。
- [x] snapshot 只存摘要、gap、coverage、readiness、diagnostics，不存完整原始新闻或 secrets。

**Tests:**

```bash
python3.11 -m pytest tests/serenity/test_analysis_history_serenity_snapshot.py tests/serenity/test_analysis_service_serenity.py -q
```

**DoD:**

- [x] 新历史记录可读回 `serenity_research`。
- [x] 老历史记录兼容。
- [x] 没有新增 migration。

**Rollback:** 停止写入 `context_snapshot.serenity_research`；保留已存在历史数据为无害额外 JSON。

### P1-T04: Web 类型与 Evidence Quality Panel

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `8d21280`
Evidence: DSA `apps/dsa-web/src/types/analysis.ts`, `apps/dsa-web/src/components/report/SerenityEvidenceQualityPanel.tsx`, `apps/dsa-web/src/components/report/ReportSummary.tsx`, `apps/dsa-web/src/components/report/index.ts`, `apps/dsa-web/src/components/report/__tests__/SerenityEvidenceQualityPanel.test.tsx`; Red test `npm --prefix apps/dsa-web test -- SerenityEvidenceQualityPanel` initially -> failed because `SerenityEvidenceQualityPanel` did not exist; Green validation target panel test -> `1 passed`, `4 passed`; related report tests -> `3 passed`, `14 passed`; `npm --prefix apps/dsa-web run build` -> pass; `npm --prefix apps/dsa-web run lint` -> pass; boundary guard -> `3 passed`; `tests/serenity -q` -> `24 passed`; forbidden UI phrase scan -> no matches; `git diff --check` -> pass.
Decision Notes: P1-T04 consumes existing optional `serenityResearch` from runtime `AnalysisResult` or historical `AnalysisReport.details.serenityResearch`; panel is intentionally mounted after `AnalysisContextSummary` and before diagnostics/traceability so DSA summary, strategy and news remain primary. `AnalysisContextSummary.tsx` did not require modification because the new panel is a separate report transparency section.
Rollback Notes: Revert DSA commit `8d21280`, or remove `SerenityEvidenceQualityPanel`, the TypeScript `serenityResearch` fields/types, export, tests and ReportSummary mount point; no API, DB or Python runtime rollback is needed.

**Purpose:** 在 DSA Web 报告中展示研究证据质量，不改变主要交易结论区。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/types/analysis.ts`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/components/report/SerenityEvidenceQualityPanel.tsx`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/components/report/ReportSummary.tsx`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/components/report/AnalysisContextSummary.tsx`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/components/report/SerenityEvidenceQualityPanel.test.tsx`

**Dependencies:** P1-T01

**Implementation Checklist:**

- [x] 在 TypeScript types 中新增 optional `serenityResearch`（由 API `serenity_research` camelCase 后消费）。
- [x] Panel 显示 quality score、readiness、source coverage、evidence count、top gaps、diagnostics。
- [x] Panel 文案明确为“研究证据质量”，不是“买卖建议增强”。
- [x] 没有 audit 时不渲染 panel。
- [x] failed-open 时显示“辅助研究审计不可用，主分析未受影响”。
- [x] Panel 放在 DSA decision summary、策略和资讯之后，避免抢占主结论。

**Tests:**

```bash
cd /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web
npm test -- SerenityEvidenceQualityPanel
npm run build
```

**DoD:**

- [x] 有 audit、无 audit、failed-open 三种 UI 状态均有测试。
- [x] TypeScript 类型检查通过（`npm --prefix apps/dsa-web run build`）。
- [x] UI 文案不出现 target price、position sizing、buy/sell/hold 映射。

**Rollback:** 移除 panel、types 新字段和 ReportSummary 挂载点。

### P1-T05: Phase 1 HTTP / UI Smoke

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `00325bd`
Evidence: DSA `tests/serenity/test_phase1_http_ui_smoke.py`, `apps/dsa-web/src/pages/__tests__/HomePage.serenity-smoke.test.tsx`, `docs/serenity-baseline-verification.md`; focused smoke/schema/service tests -> `12 passed`; full Serenity suite -> `28 passed`; boundary guard -> `3 passed`; DSA Web report smoke/panel/diagnostics tests -> `17 passed`; `npm --prefix apps/dsa-web run build` -> pass; `npm --prefix apps/dsa-web run lint` -> pass; audit incremental rough median -> `0.279 ms/response` below `25 ms/response`; forbidden Serenity trading-phrase scan -> no product-code matches; `git diff --check` -> pass.
Decision Notes: Full FastAPI app import still touches known optional environment dependencies (`pandas`, `markdown2`), so P1-T05 uses focused synchronous route-helper and service-shaped smoke coverage rather than attributing broad app import failures to Serenity. Trading-field checks compare flag-on output to a flag-off baseline because DSA may independently normalize action labels from score/advice.
Rollback Notes: P1-T05 adds tests and documentation only; remove the two smoke test files and the P1-T05 baseline documentation section to rollback this stage. Runtime rollback remains `SERENITY_RESEARCH_ENABLED=false` or reverting prior Phase 1 implementation commits.

**Purpose:** 验证 API 与 Web 集成在 flag on/off 下均稳定。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/test_phase1_http_ui_smoke.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/pages/__tests__/HomePage.serenity-smoke.test.tsx`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-baseline-verification.md`

**Dependencies:** P1-T02, P1-T03, P1-T04

**Implementation Checklist:**

- [x] 写 HTTP smoke：flag off response 与 baseline 兼容。
- [x] 写 HTTP smoke：flag on response 包含 optional audit。
- [x] 写 UI smoke：报告页在有 audit 时展示 panel。
- [x] 写 UI smoke：failed-open diagnostics 不阻断报告页。
- [x] 记录性能粗测：audit 增量耗时和可接受阈值。

**Tests:**

```bash
python3.11 -m pytest tests/serenity/test_phase1_http_ui_smoke.py -q
npm --prefix apps/dsa-web test -- HomePage.serenity-smoke
```

**DoD:**

- [x] flag off/on 都通过 smoke。
- [x] failed-open 行为可被测试复现。
- [x] 性能增量记录在文档中。

**Rollback:** 关闭 feature flag；如需代码回滚，revert Phase 1 PR。

### P1 Phase Review

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `1e2f9b6`; Serenity handoff docs commit pending
Evidence: Subagent read-only review found two API schema risks: failed-open audit used `quality.research_quality_score=None` while schema required `int`, and `SerenityResearchAudit` allowed extra top-level fields. Red check `python3.11 -m pytest tests/serenity/test_serenity_api_schema_contract.py::test_analysis_result_response_accepts_failed_open_serenity_research_audit tests/serenity/test_serenity_api_schema_contract.py::test_analysis_result_response_rejects_serenity_research_trading_fields -q` -> `2 failed`; after DSA commit `1e2f9b6`, same command -> `2 passed`; `python3.11 -m py_compile api/v1/schemas/serenity.py tests/serenity/test_serenity_api_schema_contract.py` -> exit 0; focused Phase 1 API/service/schema tests -> `14 passed`; full DSA `tests/serenity -q` -> `30 passed`; boundary guard -> `3 passed`; Web smoke/panel/diagnostics tests -> `4 files passed / 17 tests passed`; `npm --prefix apps/dsa-web run build` -> pass; `npm --prefix apps/dsa-web run lint` -> pass; config scan confirms `src/config.py` default `serenity_research_enabled: bool = False` and `.env.example` `SERENITY_RESEARCH_ENABLED=false`; storage scan confirms reuse of `analysis_history.context_snapshot.serenity_research`; migration inventory found no `migrations/` or `alembic/` directory and no Serenity-specific table; forbidden Serenity trading-phrase scan produced only the broad-regex test function name `test_serenity_audit_incremental_overhead_smoke_under_threshold`.
Decision Notes: Phase 1 exit criteria are met after the API contract hardening fix. Flag-off remains baseline-compatible and does not instantiate/emit effective Serenity audit payloads; flag-on adds only optional research-only `serenity_research`; failed-open diagnostics remain inside the optional audit block and now validate cleanly; history persistence stays in existing `context_snapshot.serenity_research`; no DB table/migration was introduced; DSA trading advice fields are neither rewritten nor semantically extended by Serenity, and API schema now rejects unexpected audit fields such as `operation_advice`.
Rollback Notes: Runtime rollback remains setting `SERENITY_RESEARCH_ENABLED=false`. Code rollback can revert DSA Phase 1 commits `10b9dda`, `952c708`, `c193f17`, `8d21280`, `00325bd`, and `1e2f9b6`; existing historical `context_snapshot.serenity_research` JSON is harmless to leave because old read paths tolerate absent or extra snapshot keys.

**Review Checklist:**

- [x] `SERENITY_RESEARCH_ENABLED=false` 时 DSA API/UI 行为与 baseline 一致。
- [x] `SERENITY_RESEARCH_ENABLED=true` 时只新增 optional evidence-quality block。
- [x] 历史记录使用 `context_snapshot.serenity_research`。
- [x] 没有新增 Serenity 专用表。
- [x] 没有修改 DSA 原有交易建议字段。

---

## 4. Phase 2: Agent Tools

**Phase Goal:** 让 DSA Agent 可以被用户显式调用 Serenity research-quality 能力，但 Agent 默认交易决策链路不被 Serenity 自动改写。

**Phase Entry Criteria:**

- [x] Phase 1 exit criteria 已满足。
- [x] Agent tool 注册方式已确认。
- [x] 用户查询语义与系统自动决策语义已分离。

**Phase Exit Criteria:**

- [ ] Agent registry 中有 evidence quality / evidence gap tools。
- [ ] Tools 只返回研究审计和补证建议。
- [ ] Tool error fail-open，不中断 Agent 会话。
- [ ] Tool 文案不生成交易建议。

### P2-T01: Evidence Quality Agent Tool

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `379ee1b`
Evidence: Red check `python3.11 -m pytest tests/agent/tools/test_serenity_evidence_quality_tool.py -q` -> `5 failed`; after DSA commit `379ee1b`, same command -> `5 passed`; focused registry tests -> `2 passed`; `python3.11 -m pytest tests/serenity -q` -> `30 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; target `py_compile` passed; forbidden Serenity trading-phrase scan only matched existing broad-regex test function name; `git diff --check` passed. Full `tests/test_agent_registry.py -q` still hits known missing `pandas` blocker in unrelated `SkillAgent` import after `58 passed`.
Decision Notes: Tool body lives under `src/serenity/agent_tools` and is exposed through existing `ALL_ANALYSIS_TOOLS` aggregation, avoiding Agent prompt or factory behavior changes. The tool only audits caller-provided low-sensitivity context; missing context returns blocked diagnostics and failures return sanitized fail-open payloads.
Rollback Notes: Revert DSA commit `379ee1b`, or remove `serenity_evidence_quality_tool` from `ALL_ANALYSIS_TOOLS` and delete `src/serenity/agent_tools/*` plus `tests/agent/tools/test_serenity_evidence_quality_tool.py`.

**Purpose:** 提供 Agent 可调用工具，用于回答“这份分析证据质量如何”。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/registry.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/analysis_tools.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/agent_tools/evidence_quality_tool.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/tools/test_serenity_evidence_quality_tool.py`

**Dependencies:** P1-T02

**Implementation Checklist:**

- [x] 定义 tool name：`serenity_evidence_quality`。
- [x] 参数包含 `symbol`、`market`、`analysis_id` 和 optional `context`；`context` 是唯一审计输入，其他字段只做 traceability metadata。
- [x] 输出包含 quality score、readiness、coverage、top gaps、source warning。
- [x] Tool description 明确 research-only。
- [x] Tool 不调用交易建议重算逻辑。
- [x] Tool 失败时返回 diagnostics，而不是抛异常终止 Agent。

**Tests:**

```bash
python -m pytest tests/agent/tools/test_serenity_evidence_quality_tool.py -q
```

**DoD:**

- [x] Tool 已注册且可发现。
- [x] Tool 输出可 JSON 序列化。
- [x] Tool 不修改 Agent 交易信号。

**Rollback:** 从 registry 移除 tool 并删除 `src/serenity/agent_tools/evidence_quality_tool.py`。

### P2-T02: Evidence Gap Agent Tool

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: `ab2ed1e`
Evidence: red check `python3.11 -m pytest tests/agent/tools/test_serenity_evidence_gap_tool.py -q` -> `6 failed`; focused pass -> `6 passed`; registry focused tests -> `2 passed`; `tests/serenity -q` -> `30 passed`; boundary guard -> `3 passed`; target `py_compile` -> pass; forbidden phrase scan only matched existing broad-regex test function name; `git diff --check` -> pass.
Decision Notes: Added explicit-call research-only `serenity_evidence_gaps` Agent tool that requires caller-provided low-sensitivity `context`, normalizes `EvidenceQualityService` acquisition tasks into Phase 3-ready research task suggestions, and does not fetch data, create DB tasks, change prompts, or mutate DSA trading fields.
Rollback Notes: Remove `serenity_evidence_gaps_tool` from `ALL_ANALYSIS_TOOLS`, remove its package export, and delete `src/serenity/agent_tools/evidence_gap_tool.py` plus `tests/agent/tools/test_serenity_evidence_gap_tool.py`.

**Purpose:** 提供 Agent 可调用工具，用于回答“下一步应该补哪些证据”。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/registry.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/analysis_tools.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/agent_tools/evidence_gap_tool.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/tools/test_serenity_evidence_gap_tool.py`

**Dependencies:** P2-T01

**Implementation Checklist:**

- [x] 定义 tool name：`serenity_evidence_gaps`。
- [x] 输出 gap id、reason、source target、acceptance criteria、after-import action。
- [x] 将 gaps 按 severity、source coverage、primary-source need 排序。
- [x] 文案避免“应买入/卖出”，改用“补证后再提升研究置信度”。
- [x] Tool 不创建数据库任务；Phase 2 只返回建议。

**Tests:**

```bash
python -m pytest tests/agent/tools/test_serenity_evidence_gap_tool.py -q
```

**DoD:**

- [x] 有 gaps、无 gaps、audit failed-open 三种输出均稳定。
- [x] 输出可被后续 Phase 3 转成持久任务。

**Rollback:** 从 registry 移除 tool 并删除 gap tool。

### P2-T03: Agent Prompt Boundary Test

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `213db24`
Evidence: red check `python3.11 -m pytest tests/agent/test_serenity_prompt_boundaries.py -q` -> first `3 failed / 2 passed` due missing boundary docs and known optional `pandas` import path, then focused executor red check -> `2 failed / 6 passed` proving default single-agent path exposed Serenity tools; after fixes focused P2-T03 suite -> `8 passed`; P2 tool regression -> `11 passed`; focused registry tests -> `2 passed`; `tests/serenity -q` -> `30 passed`; boundary guard -> `3 passed`; target `py_compile` -> pass; forbidden Serenity trading-phrase scan only matched existing broad-regex test function name; `git diff --check` -> pass.
Decision Notes: Added a P2-T03 boundary test suite covering Serenity tool schema/output cleanliness, default Technical/Intel/Risk/Decision prompts, multi-agent filtered registries, single-agent executor tool declarations, and the registry actually passed to `run_agent_loop`. A read-only reviewer identified that globally registered Serenity tools were still model-selectable in the legacy single-agent executor; `AgentExecutor` now filters `serenity_evidence_quality` and `serenity_evidence_gaps` out of default requests and exposes them only for explicit evidence-quality / evidence-gap / source-coverage / readiness intent or an explicit context opt-in. Boundary docs now include allowed explicit user queries and forbidden automatic trading-field examples.
Rollback Notes: Remove `tests/agent/test_serenity_prompt_boundaries.py`, revert the P2-T03 section in `docs/serenity-integration-boundaries.md`, and remove `SERENITY_RESEARCH_TOOL_NAMES`, `SERENITY_RESEARCH_INTENT_MARKERS`, `_should_expose_serenity_research_tools()`, `_filtered_tool_registry_for_request()`, and request-scoped registry wiring from `src/agent/executor.py`; then reassess Phase 2 explicit-call boundaries before proceeding.

**Purpose:** 防止 Agent 把 Serenity research-only 输出误用为交易建议。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/agent/test_serenity_prompt_boundaries.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-integration-boundaries.md`

**Dependencies:** P2-T01, P2-T02

**Implementation Checklist:**

- [x] 测试 Agent tool descriptions 包含 research-only 边界。
- [x] 测试 tool output 不含 direct buy/sell/hold instruction。
- [x] 测试 Serenity quality score 不写入 trading score 字段。
- [x] 文档补充 Agent 使用示例：用户显式问证据质量时才调用。
- [x] 测试默认 Technical / Intel / Risk / Decision Agent prompts 不自动指示 Serenity tool。
- [x] 测试默认多 Agent filtered registry 与 legacy single-agent executor 均不向模型暴露 Serenity tools。

**Tests:**

```bash
python -m pytest tests/agent/test_serenity_prompt_boundaries.py -q
```

**DoD:**

- [x] Agent 工具边界有自动化测试。
- [x] 文档有用户查询示例和禁止示例。
- [x] 默认 Agent prompt 和 legacy single-agent executor 均保持 explicit-call boundary。

**Rollback:** 移除测试和文档新增段落；保留 Phase 2 tools 需重新评估。

### P2 Phase Review

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `f74720f`
Evidence: red check `python3.11 -m pytest tests/agent/test_serenity_prompt_boundaries.py::test_single_agent_executor_hides_serenity_tools_when_feature_flag_is_off -q` -> `1 failed`, proving explicit research-quality requests still exposed Serenity tools when `SERENITY_RESEARCH_ENABLED=false`; fix commit `18f5d13` added config-gated exposure. Subagent review then found two Important boundary gaps; red check `python3.11 -m pytest tests/agent/test_serenity_prompt_boundaries.py::test_single_agent_executor_ignores_external_context_tool_override tests/agent/test_serenity_prompt_boundaries.py::test_skill_agent_without_required_tools_does_not_receive_global_serenity_registry -q` -> `2 failed`, proving external context override and SkillAgent empty-required-tools fallback exposed global Serenity tools; fix commit `f74720f` removed the external context override and made SkillAgent default to an empty tool whitelist. Final verification: `python3.11 -m pytest tests/agent/test_serenity_prompt_boundaries.py -q` -> `11 passed`; `python3.11 -m pytest tests/agent/tools/test_serenity_evidence_quality_tool.py tests/agent/tools/test_serenity_evidence_gap_tool.py -q` -> `11 passed`; focused registry import/schema tests -> `2 passed`; `python3.11 -m pytest tests/serenity -q` -> `30 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; target `py_compile` -> pass; static flag/boundary scan confirmed default `SERENITY_RESEARCH_ENABLED=false` and Serenity tool registrations; forbidden phrase scan only matched boundary docs and existing broad-regex smoke test name; `git diff --check` -> pass.
Decision Notes: P2 Phase Review confirmed evidence-quality and evidence-gap Agent tools remain research-only, caller-context-only, fail-open, JSON-safe, and isolated from DSA trading fields. Review hardened the executor so Serenity tools are exposed only when `SERENITY_RESEARCH_ENABLED=true` and user text explicitly asks about research quality, evidence gaps, source coverage, or readiness; request-provided `context.serenity_research_tools_enabled=True` no longer bypasses intent gating. Specialist `SkillAgent` now defaults to no tools when a skill has no `required_tools`, avoiding full-registry fallback exposure. The handler-level feature-flag defense-in-depth suggestion is recorded as Minor and deferred until a shared filtered-registry/helper layer is introduced.
Rollback Notes: Revert DSA commits `f74720f` and `18f5d13` to restore prior P2-T03 behavior, then reassess P2 Phase Review before starting Phase 3. If only the SkillAgent fallback change causes issues, restore `self.tool_names` default behavior in `src/agent/skills/skill_agent.py` and keep the executor feature flag gate; rerun P2 prompt-boundary tests before proceeding.

**Review Checklist:**

- [x] Agent tools 只在显式调用时使用。
- [x] Tools 输出不覆盖 DSA 决策字段。
- [x] Agent 工具测试通过。
- [x] 关闭 feature flag 时 tools 不暴露或返回 disabled diagnostics。

---

## 5. Phase 3: Intelligence Workflow Persistence

**Phase Goal:** 将 Serenity gaps 变成可追踪研究任务，并逐步对齐 DSA intelligence workflow；优先使用现有 JSON snapshot 和 intelligence service，不急于新建专表。

**Phase Entry Criteria:**

- [x] Phase 2 exit criteria 已满足。
- [x] 研究任务字段、生命周期和 owner 语义已确认。
- [x] 已明确何时需要新表。

**Phase Exit Criteria:**

- [ ] Evidence gaps 可在历史或 intelligence workflow 中追踪。
- [ ] 任务状态支持 open / collecting / verified / dismissed。
- [ ] 完成任务后可触发 rerun 或生成 rerun 指引。
- [ ] 新表决策有证据支持；未满足条件时继续使用 snapshot。

### P3-T01: Research Task Data Contract

Owner: Codex
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `0c97412`
Evidence: Red check `python3.11 -m pytest tests/api/v1/test_serenity_research_task_schema.py -q` failed during collection because `SerenityResearchTask` / `SerenityResearchTaskStatusTransition` were missing; after DSA commit `0c97412`, same command -> `9 passed`; existing schema/history regression `python3.11 -m pytest tests/serenity/test_serenity_api_schema_contract.py tests/serenity/test_analysis_history_serenity_snapshot.py -q` -> `8 passed`; boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; full Serenity suite `python3.11 -m pytest tests/serenity -q` -> `30 passed`; target `py_compile` -> pass; safety scan only matched existing boundary docs / broad-regex smoke test name; `git diff --check` -> pass.
Decision Notes: P3-T01 defines the research-only task contract without persistence behavior. Added DSA `docs/serenity-research-task-contract.md`, strict task/rerun schemas, status-transition validation, `verified_at` validation, old-history compatibility via default empty `tasks`, and trading-field rejection through strict extra-field schema. The contract places future tasks under `context_snapshot.serenity_research.tasks` and records that DB tables remain blocked until the P3-T04 dedicated-table gate.
Rollback Notes: Revert DSA commit `0c97412` to remove the task contract schema/tests/doc. Existing history records without `serenity_research.tasks` remain compatible because the schema defaults missing tasks to an empty list; no DB table, migration, service persistence, or intelligence workflow behavior was introduced.

**Purpose:** 定义 DSA 中可持久化的 Serenity research task 结构。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-research-task-contract.md`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/history.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/api/v1/test_serenity_research_task_schema.py`

**Dependencies:** P1-T03, P2-T02

**Implementation Checklist:**

- [x] 定义 `task_id`、`symbol`、`market`、`gap_type`、`reason`、`source_target`、`acceptance_criteria`、`status`、`created_at`、`updated_at`、`verified_at`。
- [x] 定义状态机：`open -> collecting -> verified`，以及 `open -> dismissed`。
- [x] 定义 rerun context：`analysis_id`、`quality_before`、`quality_after`、`rerun_url`。
- [x] 明确哪些字段进入 `context_snapshot.serenity_research.tasks`。
- [x] 明确哪些字段未来可能迁入专表。

**Tests:**

```bash
python -m pytest tests/api/v1/test_serenity_research_task_schema.py -q
```

**DoD:**

- [x] schema 可表达至少 primary-source、risk-coverage、demand-validation、invalidation-plan 四类 gap。
- [x] 老历史记录兼容。

**Rollback:** 删除 task contract 文档和 schema 新增任务字段。

### P3-T02: Snapshot-Based Task Persistence

Owner:
Status: Verified
Started: 2026-07-08
Updated: 2026-07-08
Branch:
PR:
Commit: DSA `6774f61`
Evidence: Red check `python3.11 -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py -q` failed during collection because `src.serenity.services.research_task_service` was missing; after DSA commit `6774f61`, same command -> `13 passed`; schema/history regression `python3.11 -m pytest tests/api/v1/test_serenity_research_task_schema.py tests/serenity/test_analysis_history_serenity_snapshot.py -q` -> `12 passed`; full Serenity regression `python3.11 -m pytest tests/serenity -q` -> `39 passed`; boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; target `py_compile` -> pass; safety scan only matched existing boundary docs / baseline scan command / broad-regex smoke test name; DB-table scan only matched contract docs and schema test names; `git diff --check` -> pass.
Decision Notes: P3-T02 keeps snapshot-first persistence. Added `ResearchTaskService` to normalize audit acquisition tasks into deterministic, schema-valid research tasks; `AnalysisService` now attaches bounded tasks before the existing snapshot patch; `DatabaseManager` preserves top 20 sanitized `tasks` under `context_snapshot.serenity_research.tasks` and supports status updates in-place, including `history_id + task_id` precise row targeting. No DB table, migration, provider fetch, Agent prompt change, intelligence workflow mutation, or DSA trading-field mapping was introduced.
Rollback Notes: Revert DSA commit `6774f61` to stop generating and updating snapshot tasks. Historical `context_snapshot.serenity_research.tasks` entries are optional JSON add-ons and can remain readable as inert metadata; no schema downgrade is required because no table or migration was added.

**Purpose:** 在不新增数据库表的情况下，把 evidence gaps 转成可回读任务。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/storage.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/analysis_service.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/services/research_task_service.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/services/test_research_task_service.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/storage/test_serenity_research_tasks_snapshot.py`

**Dependencies:** P3-T01

**Implementation Checklist:**

- [x] 从 audit gaps 生成 deterministic task ids。
- [x] 将 tasks 写入 `context_snapshot.serenity_research.tasks`。
- [x] 如果同一 analysis rerun 产生同一 gap，保持 task id 稳定。
- [x] 支持状态更新写回 snapshot。
- [x] 对 snapshot 太大设置上限，例如最多保留 top 20 tasks 和摘要字段。
- [x] 不引入新数据库 migration。

**Tests:**

```bash
python -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py -q
```

**DoD:**

- [x] tasks 可持久化、回读、状态更新。
- [x] snapshot size 有上限。
- [x] 空 gaps 产生明确 empty state。

**Rollback:** 停止生成 tasks；已写入 snapshot 的 tasks 作为历史附加 JSON 保留。

### P3-T03: Intelligence Service 接入

Owner: Codex
Status: Verified
Started: 2026-07-09
Updated: 2026-07-09
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `4c6f51b`
Evidence: Red service check `python3.11 -m pytest tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_list_serenity_research_tasks_filters_snapshot_tasks_by_symbol_and_status tests/test_intelligence_service.py::IntelligenceServiceTestCase::test_update_serenity_research_task_status_uses_existing_snapshot_helper -q` failed with `2 failed` because `IntelligenceService` had no research task list/update methods; red API check `python3.11 -m pytest tests/test_intelligence_api.py::IntelligenceApiTestCase::test_list_serenity_research_tasks_from_intelligence_api tests/test_intelligence_api.py::IntelligenceApiTestCase::test_update_serenity_research_task_status_from_intelligence_api -q` failed with `2 failed` because routes returned 404. After DSA commit `4c6f51b`, focused service/API checks -> `5 passed`; P3 regression -> `22 passed`; intelligence service/API regression -> `40 passed, 1 warning`; boundary guard -> `3 passed`; target `py_compile` -> pass; safety scan only matched existing boundary/baseline docs and broad-regex smoke test name; DB-table scan matched function/test names plus contract doc mention only; `git diff --check` -> pass.
Decision Notes: P3-T03 exposes snapshot-backed Serenity research tasks through the existing DSA intelligence workflow, not a new Serenity workbench. Added `IntelligenceService.list_serenity_research_tasks()` and `update_serenity_research_task_status()` over `analysis_history.context_snapshot.serenity_research.tasks`, plus minimal `GET /api/v1/intelligence/serenity-research/tasks` and `PATCH /api/v1/intelligence/serenity-research/tasks/{task_id}/status` routes. List responses validate through `SerenityResearchTask`, strip trading fields, and include `history_id`, `query_id`, `stock_code`, and `report_type` anchors so duplicate analysis snapshots can be updated precisely. Status updates continue to use the existing snapshot helper and do not fetch providers, mutate Agent prompts, create DB rows, or map Serenity state to DSA trading fields.
Rollback Notes: Revert DSA commit `4c6f51b` to remove the intelligence service/API exposure while leaving existing snapshot tasks as inert optional JSON metadata. No migration rollback is required because P3-T03 added no table, repository model, background queue, provider fetch path, or UI page.

**Purpose:** 将 research task 暴露给 DSA intelligence workflow，而不是创建第二套 Serenity 工作台。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/intelligence_service.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/intelligence.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/endpoints/intelligence.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/test_intelligence_service.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/test_intelligence_api.py`

**Dependencies:** P3-T02

**Implementation Checklist:**

- [x] 在 intelligence service 中读取 research tasks。
- [x] 支持按 symbol、status、gap_type 过滤。
- [x] 支持 task status update endpoint 或复用现有 action endpoint。
- [x] 确保权限、用户上下文和历史记录访问规则与 DSA 现有模式一致。
- [x] 不把 Serenity 任务页面做成独立产品壳。

**Tests:**

```bash
python -m pytest tests/test_intelligence_service.py tests/test_intelligence_api.py -q
```

**DoD:**

- [x] Intelligence API 能返回和更新 research tasks。
- [x] 权限与 DSA 现有 history/intelligence 规则一致。
- [x] 没有新增 UI 大页面，除非 DSA 现有 intelligence UI 需要轻量展示。

**Rollback:** 移除 intelligence service/endpoints 的 Serenity task 分支。

### P3-T04: 专表升级决策 Gate

Owner: Codex
Status: Verified
Started: 2026-07-09
Updated: 2026-07-09
Branch: `codex/serenity-phase-0-evidence-bridge`
PR:
Commit: DSA `61b52ce`
Evidence: DSA `docs/serenity-persistence-decision-record.md`; decision gate review found only one current table criterion is met, cross-report filtering, below the two-criterion threshold; P3 regression `python3.11 -m pytest tests/serenity/services/test_research_task_service.py tests/storage/test_serenity_research_tasks_snapshot.py tests/api/v1/test_serenity_research_task_schema.py -q` -> `22 passed`; intelligence regression `python3.11 -m pytest tests/test_intelligence_service.py tests/test_intelligence_api.py -q` -> `40 passed, 1 warning`; boundary guard `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; target `py_compile` -> pass; safety scan only matched existing boundary/baseline docs and broad-regex smoke test name; DB-table scan matched existing function/test names plus contract/decision docs only; `git diff --check` -> pass.
Decision Notes: P3-T04 did not approve dedicated tables. Current product behavior already supports cross-report filtering from recent `analysis_history.context_snapshot.serenity_research.tasks`, but there is no current owner/assignee workflow, event-level audit trail, task recovery/retry queue, or benchmark proving snapshot size/query performance is unacceptable. Continue snapshot-first and do not add `serenity_research_tasks`, `serenity_research_task_events`, migrations, repository models, queues, provider fetches, Agent prompt changes, UI pages, or DSA trading-field mappings.
Rollback Notes: Delete DSA `docs/serenity-persistence-decision-record.md` and revert the tracker/task-log updates. No runtime code, DB schema, migration, or stored task data was changed.

**Purpose:** 只有在确有需求时才从 snapshot 升级为 dedicated tables。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-persistence-decision-record.md`
- Optional Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/migrations/versions/<revision>_create_serenity_research_tasks.py`
- Optional Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/storage.py`

**Dependencies:** P3-T03

**Decision Criteria:** 只有满足至少两项才进入专表实现。

- [x] 需要跨 report 过滤任务。
- [ ] 需要任务 owner / assignee。
- [ ] 需要审计 trail。
- [ ] 需要任务恢复和重试队列。
- [ ] snapshot size 或查询性能不可接受。

**Implementation Checklist If Table Is Approved:**

- [ ] 设计 `serenity_research_tasks` 表。Not approved in P3-T04.
- [ ] 设计 `serenity_research_task_events` 表。Not approved in P3-T04.
- [ ] 提供 snapshot -> table migration 或 lazy backfill 策略。Not approved in P3-T04.
- [ ] API 保持向后兼容。Existing snapshot API remains unchanged.
- [ ] rollback plan 包含 migration downgrade。No migration was introduced.

**Tests If Table Is Approved:**

```bash
python -m pytest tests/storage/test_serenity_research_tasks_table.py -q
alembic upgrade head
alembic downgrade -1
```

**DoD:**

- [x] 有明确 decision record。
- [x] 如果未批准专表，文档记录继续使用 snapshot 的原因。
- [x] 如果批准专表，migration upgrade/downgrade 均验证。Not applicable; table was not approved and no migration was introduced.

**Rollback:** 删除 DSA `docs/serenity-persistence-decision-record.md` 并回退 tracker/task-log 更新即可；没有专表实现、migration 或 runtime code 需要回滚。

### P3 Phase Review

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Review Checklist:**

- [ ] Research task 生命周期可追踪。
- [ ] Snapshot 优先原则被遵守或有明确 decision record。
- [ ] Rerun context 不包含交易建议改写。
- [ ] Intelligence workflow 复用 DSA 现有产品能力。

---

## 6. Phase 4: Provenance Safety Guardrails

**Phase Goal:** 为 DSA 报告增加可审计 provenance、引用纪律和 report safety guardrails，确保 research-only 辅助信息不会污染交易建议语义。

**Phase Entry Criteria:**

- [ ] Phase 3 exit criteria 已满足。
- [ ] DSA 报告生成路径和引用字段已确认。
- [ ] 安全扫描词表、允许引用例外和误报处理策略已确认。

**Phase Exit Criteria:**

- [ ] 报告中的 Serenity block 有 provenance namespace。
- [ ] Safety scanner 能区分产品生成文案与 quoted source excerpt。
- [ ] 发布前验证包含 report safety scan。
- [ ] 用户可查看 evidence audit trail 或 diagnostics。

### P4-T01: Provenance Namespace

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Purpose:** 给 Serenity audit、gap、task 和 source reference 建立稳定 provenance namespace。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/provenance.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/services/evidence_quality_service.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/analysis.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/core/test_provenance.py`

**Dependencies:** P1-T02, P3-T02

**Implementation Checklist:**

- [ ] 定义 provenance id 格式：`serenity:<analysis_id>:<evidence_id>` 或同等稳定方案。
- [ ] 为 audit summary、coverage、gap、task 添加 source refs。
- [ ] source ref 包含 title、publisher、url、published_at、excerpt hash 或 claim id。
- [ ] 不存完整敏感上下文。
- [ ] 对缺 source 的 evidence 显示 explicit missing provenance。

**Tests:**

```bash
python -m pytest tests/serenity/core/test_provenance.py -q
```

**DoD:**

- [ ] provenance id 稳定且不泄露本地绝对路径。
- [ ] 缺引用不是静默通过，而是形成 diagnostics 或 gap。

**Rollback:** 从 audit schema 中移除 provenance block。

### P4-T02: Report Safety Scanner

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Purpose:** 扫描 DSA + Serenity 报告，防止 research-only block 产生直接投资指令或越界承诺。

**Files:**

- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/core/report_safety.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/core/test_report_safety.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-integration-boundaries.md`

**Dependencies:** P4-T01

**Implementation Checklist:**

- [ ] 定义 forbidden generated phrases：直接买入/卖出/持有命令、目标价承诺、仓位建议、保证收益、确定性预测。
- [ ] 定义 allowed quoted source excerpt 区域，避免误杀外部来源引用。
- [ ] 扫描 Serenity-generated copy、tool output、UI panel copy。
- [ ] 输出 severity、location、matched phrase、remediation。
- [ ] 默认只拦截 Serenity report section 发布，不拦截 DSA 主链路。

**Tests:**

```bash
python -m pytest tests/serenity/core/test_report_safety.py -q
```

**DoD:**

- [ ] forbidden generated phrase 被拦截。
- [ ] quoted source excerpt 的合法引用不误报。
- [ ] scanner 输出可用于 CI 或 release checklist。

**Rollback:** 禁用 scanner gate，保留日志模式。

### P4-T03: Release Checklist 集成

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Purpose:** 将 Serenity 集成验证加入 DSA 发布流程。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/RELEASE_CHECKLIST.md`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/.github/workflows/ci.yml`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/scripts/serenity_release_check.py`
- Test: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/test_release_check.py`

**Dependencies:** P4-T02

**Implementation Checklist:**

- [ ] Release checklist 添加 flag off/on 验证。
- [ ] CI 添加 Serenity unit tests。
- [ ] CI 添加 report safety scanner。
- [ ] CI 不要求外部数据源或真实 broker token。
- [ ] release script 输出 machine-readable summary。

**Tests:**

```bash
python scripts/serenity_release_check.py
python -m pytest tests/serenity/test_release_check.py -q
```

**DoD:**

- [ ] CI 可在无真实 secrets 环境运行。
- [ ] Release checklist 明确 Serenity failure 的处理方式。
- [ ] 发布流程包含 rollback command 或 revert PR 指引。

**Rollback:** 从 CI 移除 Serenity release check，保留本地手动检查。

### P4-T04: Observability and Diagnostics

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Purpose:** 让 Serenity audit 的运行状态、失败原因和性能开销可见。

**Files:**

- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/serenity/services/evidence_quality_service.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/analysis_service.py`
- Create: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/tests/serenity/services/test_evidence_quality_observability.py`
- Modify: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/docs/serenity-baseline-verification.md`

**Dependencies:** P1-T02, P4-T02

**Implementation Checklist:**

- [ ] Structured log 包含 `serenity.enabled`、`serenity.status`、`evidence_count`、`gap_count`、`duration_ms`。
- [ ] diagnostics 包含 disabled、failed_open、completed 三类状态。
- [ ] 不记录完整用户输入、token、cookies、provider secrets。
- [ ] 性能指标可用于判断是否默认开启。

**Tests:**

```bash
python -m pytest tests/serenity/services/test_evidence_quality_observability.py -q
```

**DoD:**

- [ ] 关键状态可在日志或 diagnostics 中定位。
- [ ] failed-open 的错误摘要可读且不泄露敏感信息。

**Rollback:** 保留 fail-open，移除新增 structured logging 字段。

### P4 Phase Review

Owner:
Status: Not Started
Started:
Updated:
Branch:
PR:
Commit:
Evidence:
Decision Notes:
Rollback Notes:

**Review Checklist:**

- [ ] Provenance 可追踪。
- [ ] Safety scanner 有自动化测试。
- [ ] Release checklist 已接入。
- [ ] Observability 不泄露敏感信息。
- [ ] Serenity 仍是辅助研究内核，不是交易建议引擎。

---

## 7. 跨阶段验证矩阵

| 验证项 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
| --- | --- | --- | --- | --- | --- |
| `git diff --check` | Required | Required | Required | Required | Required |
| Serenity unit tests | Required | Required | Required | Required | Required |
| DSA backend baseline tests | Baseline | Required | Required | Required | Required |
| DSA API schema compatibility | Not Applicable | Required | Required | Required | Required |
| Web typecheck / UI tests | Not Applicable | Required | If touched | If touched | If touched |
| Agent tool tests | Not Applicable | Not Applicable | Required | Required | Required |
| Storage / migration tests | Not Applicable | Snapshot only | Snapshot only | Required | Required |
| Report safety scan | Not Applicable | Advisory | Advisory | Advisory | Required |
| Feature flag off smoke | Required | Required | Required | Required | Required |
| Feature flag on smoke | Required | Required | Required | Required | Required |
| Rollback rehearsal | Required | Required | Required | Required | Required |

### Recommended Full Verification Command Set

根据 DSA 实际脚本名称调整，但每个阶段必须记录实际执行命令和结果。

```bash
git -C /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis diff --check
python -m pytest tests/serenity -q
python -m pytest tests/services tests/api/v1 -q
cd /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web && npm --prefix apps/dsa-web run build
cd /Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web && npm test -- --run
```

---

## 8. 风险与决策日志

### D-001: DSA 为主、Serenity 为辅

- **Status:** Accepted
- **Decision:** DSA 保留产品入口和交易分析能力；Serenity 只提供证据质量与研究审计辅助。
- **Reason:** DSA 已拥有完整产品能力，Serenity 的优势是 evidence discipline，不是替代 DSA UI/runtime。
- **Risk:** 如果后续把 Serenity UI/run center/dashboard 迁入 DSA，会形成双产品壳。
- **Guardrail:** 禁止迁移 Serenity UI 作为 DSA 基座。

### D-002: Snapshot 先于 Dedicated Tables

- **Status:** Accepted
- **Decision:** 首个持久化目标是 `analysis_history.context_snapshot.serenity_research`。
- **Reason:** 降低 migration 风险，适合 Phase 1/2 的 optional add-on。
- **Risk:** 后续跨报告任务管理可能查询困难。
- **Guardrail:** Phase 3 通过 P3-T04 专表升级决策 gate 处理。

### D-003: Fail-Open 默认

- **Status:** Accepted
- **Decision:** Serenity audit 失败不影响 DSA 主分析成功。
- **Reason:** Serenity 是辅助证据质量层，不应破坏用户日常股票分析。
- **Risk:** 用户可能误以为没有 audit 就是证据质量良好。
- **Guardrail:** failed-open diagnostics 必须明确展示“审计不可用”。

### D-004: 不混合评分语义

- **Status:** Accepted
- **Decision:** Serenity quality score 不写入 DSA trading score 或 sentiment score。
- **Reason:** 证据质量与投资结论是两个不同维度。
- **Risk:** UI 或 Agent 为了简洁可能合并分数。
- **Guardrail:** schema、UI、Agent boundary tests 明确禁止映射。

---

## 9. 迭代执行节奏

### 9.1 每个任务的执行顺序

1. 将任务状态改为 `In Progress`。
2. 创建或切换阶段分支。
3. 写 failing test 或兼容性测试。
4. 运行测试确认失败或记录已有失败原因。
5. 实现最小代码。
6. 运行任务指定测试。
7. 运行阶段必要 smoke。
8. 更新本 tracker 的 Evidence / Decision Notes / Rollback Notes。
9. 将任务状态改为 `In Review`。
10. 审查通过后记录 commit / PR。
11. 验证通过后改为 `Verified`。

### 9.2 每个阶段的最小交付包

| 阶段 | 最小交付 | 不应包含 |
| --- | --- | --- |
| Phase 0 | Core + Adapter + Service POC + tests | API、UI、DB migration |
| Phase 1 | Optional API block + snapshot + UI panel | Agent tools、new tables |
| Phase 2 | Agent research-quality tools | 自动改写交易建议 |
| Phase 3 | Research task tracking | 未经 gate 的新表 |
| Phase 4 | Provenance + safety + release checks | 阻塞 DSA 主链路的 hard dependency |

### 9.3 任务拆分原则

- [ ] 一个 PR 只完成一个阶段或一个明确子任务。
- [ ] 能用 snapshot 解决的，不先建表。
- [ ] 能用 optional field 解决的，不改已有字段语义。
- [ ] 能用 adapter 解决的，不让 core import DSA。
- [ ] 能用 fail-open 解决的，不让辅助审计阻塞主流程。
- [ ] 每次引入 UI 前先有 API contract 和 fixtures。
- [ ] 每次引入 persistence 前先有 schema tests。

---

## 10. Release Readiness Checklist

### Pre-Merge

- [ ] 本 tracker 对应任务状态、Evidence、Rollback Notes 已更新。
- [ ] `tasks/todo.md` 已记录当前阶段 review。
- [ ] 相关文档更新，包括边界、配置、运行、回滚。
- [ ] 所有新增 config 默认关闭。
- [ ] 所有新增 API 字段 optional。
- [ ] 所有新增 UI 对缺失字段有空态。
- [ ] 所有新增 Agent tool 有 research-only 边界。
- [ ] 所有新增持久化有兼容老数据测试。

### Verification

- [ ] `git diff --check` 通过。
- [ ] 后端测试通过或记录环境失败。
- [ ] 前端 typecheck/test 通过或记录未触达原因。
- [ ] Feature flag off smoke 通过。
- [ ] Feature flag on smoke 通过。
- [ ] Failed-open smoke 通过。
- [ ] Safety scanner 通过。
- [ ] 无新增 secrets、绝对本地路径、未授权外部网络依赖。

### Release

- [ ] PR 描述包含用户可见变化。
- [ ] PR 描述包含风险和回滚。
- [ ] Release checklist 更新。
- [ ] 部署后检查 API health、analysis run、history read、UI report render。
- [ ] 若发现 Serenity 相关故障，先关闭 feature flag，再评估 revert。

---

## 11. 进度总览

| ID | 阶段 | 任务 | 状态 | 依赖 | 验证证据 |
| --- | --- | --- | --- | --- | --- |
| DOC-T01 | Planning | DSA-first Serenity Core 总体开发方案 | Completed | 用户方向：DSA 为主，Serenity Core 为辅 | commit `81a5709` |
| DOC-T02 | Planning | DSA-first Serenity Core 进度跟踪清单 | Completed | DOC-T01 | commit `81a5709` |
| DOC-T03 | Planning | 当前状态快照与下次启动接续提示词 | Completed | DOC-T02 | tracker 状态快照、接续提示词、`tasks/todo.md` 与 `tasks/lessons.md` 已更新 |
| G-T01 | Global | 集成边界守卫 | Verified | 当前方案 | DSA `tests/test_serenity_integration_boundaries.py` -> `3 passed`; `git diff --check` exit 0 |
| G-T02 | Global | 分支与提交规范 | Verified | G-T01 | DSA branch `codex/serenity-phase-0-evidence-bridge`; DSA `docs/CONTRIBUTING.md` + boundary doc |
| G-T03 | Global | 基线验证快照 | Verified | G-T01 | DSA `docs/serenity-baseline-verification.md`; baseline failures recorded as missing dependency setup |
| P0-T01 | Phase 0 | Serenity Core 最小契约抽取 | Verified | G-T01, G-T03 | DSA commit `4e34c78`; core contract -> `3 passed`; boundary guard -> `3 passed`; py_compile/import smoke passed |
| P0-T02 | Phase 0 | DSA Context 到 Evidence Adapter | Verified | P0-T01 | DSA commit `b85b72a`; adapter tests -> `3 passed`; core contract -> `3 passed`; boundary guard -> `3 passed`; py_compile and diff check passed |
| P0-T03 | Phase 0 | Evidence Quality Service POC | Verified | P0-T02 | DSA commit `a382a0f`; service tests -> `4 passed`; adapter tests -> `3 passed`; core contract -> `3 passed`; boundary guard -> `3 passed`; py_compile and diff check passed |
| P0-T04 | Phase 0 | CLI / Script POC Runner | Verified | P0-T03 | DSA commit `e15e588`; enabled script smoke exit 0; runner tests -> `3 passed`; service tests -> `4 passed`; adapter tests -> `3 passed`; core contract -> `3 passed`; boundary guard -> `3 passed`; py_compile and diff check passed |
| P1-T01 | Phase 1 | API Schema 增加 Serenity Audit 类型 | Verified | P0-T03 | DSA commit `10b9dda`; schema contract tests -> `3 passed`; Serenity suite -> `16 passed`; boundary guard -> `3 passed`; schema py_compile, forbidden-field static scan, and diff check passed |
| P1-T02 | Phase 1 | Analysis Service 附加 Serenity Audit | Verified | P1-T01 | DSA commit `952c708`; P1-T02 focused tests -> `8 passed`; Serenity suite -> `20 passed`; boundary guard -> `3 passed`; config registry -> `55 passed`; py_compile and diff check passed |
| P1-T03 | Phase 1 | 历史记录 Context Snapshot 持久化 | Verified | P1-T02 | DSA commit `c193f17`; focused P1-T03 tests -> `8 passed`; Serenity suite -> `24 passed`; boundary guard -> `3 passed`; py_compile and diff check passed |
| P1-T04 | Phase 1 | Web 类型与 Evidence Quality Panel | Verified | P1-T01 | DSA commit `8d21280`; panel tests -> `4 passed`; related report tests -> `14 passed`; Web build/lint passed; Serenity suite -> `24 passed`; boundary guard -> `3 passed` |
| P1-T05 | Phase 1 | Phase 1 HTTP / UI Smoke | Verified | P1-T02, P1-T03, P1-T04 | DSA commit `00325bd`; focused Phase 1 smoke/schema/service tests -> `12 passed`; Serenity suite -> `28 passed`; boundary guard -> `3 passed`; Web smoke/panel/diagnostics -> `17 passed`; build/lint passed |
| P1-REV | Phase 1 | Phase 1 Review Gate | Verified | P1-T01, P1-T02, P1-T03, P1-T04, P1-T05 | DSA commit `1e2f9b6`; red-green schema hardening tests -> `2 failed` then `2 passed`; focused backend -> `14 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; Web smoke -> `17 passed`; build/lint passed; DB/table and forbidden trading-field scans passed |
| P2-T01 | Phase 2 | Evidence Quality Agent Tool | Verified | P1-T02 | DSA commit `379ee1b`; red-green tool tests -> `5 failed` then `5 passed`; focused registry tests -> `2 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; py_compile, forbidden phrase scan, and diff check passed |
| P2-T02 | Phase 2 | Evidence Gap Agent Tool | Verified | P2-T01 | DSA commit `ab2ed1e`; red-green tool tests -> `6 failed` then `6 passed`; focused registry tests -> `2 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; py_compile, forbidden phrase scan, and diff check passed |
| P2-T03 | Phase 2 | Agent Prompt Boundary Test | Verified | P2-T01, P2-T02 | DSA commit `213db24`; red-green prompt boundary tests -> `3 failed / 2 passed`, executor exposure check -> `2 failed / 6 passed`, final focused suite -> `8 passed`; P2 tool regression -> `11 passed`; registry tests -> `2 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; py_compile, forbidden phrase scan, and diff check passed |
| P2-REV | Phase 2 | Phase 2 Review Gate | Verified | P2-T01, P2-T02, P2-T03 | DSA commit `f74720f`; feature flag red check -> `1 failed` then fixed in `18f5d13`; reviewer boundary red check -> `2 failed` then fixed in `f74720f`; prompt boundary -> `11 passed`; P2 tool regression -> `11 passed`; focused registry import/schema -> `2 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; py_compile and diff check passed |
| P3-T01 | Phase 3 | Research Task Data Contract | Verified | P1-T03, P2-T02, P2-REV | DSA commit `0c97412`; red schema check failed on missing task schema, then `9 passed`; schema/history regression -> `8 passed`; Serenity suite -> `30 passed`; boundary guard -> `3 passed`; py_compile, safety scan, and diff check passed |
| P3-T02 | Phase 3 | Snapshot-Based Task Persistence | Verified | P3-T01 | DSA commit `6774f61`; red persistence check failed on missing service, then `13 passed`; schema/history regression -> `12 passed`; Serenity suite -> `39 passed`; boundary guard -> `3 passed`; py_compile, safety scan, DB-table scan, and diff check passed |
| P3-T03 | Phase 3 | Intelligence Service 接入 | Verified | P3-T02 | DSA commit `4c6f51b`; red service check -> `2 failed` then focused service/API -> `5 passed`; P3 regression -> `22 passed`; intelligence regression -> `40 passed, 1 warning`; boundary guard -> `3 passed`; py_compile, safety scan, DB-table scan, and diff check passed |
| P3-T04 | Phase 3 | 专表升级决策 Gate | Verified | P3-T03 | DSA commit `61b52ce`; decision record added; only cross-report filtering criterion is currently met, so table gate did not pass; P3 regression -> `22 passed`; intelligence regression -> `40 passed, 1 warning`; boundary guard -> `3 passed`; py_compile, safety scan, DB-table scan, and diff check passed |
| P4-T01 | Phase 4 | Provenance Namespace | Not Started | P1-T02, P3-T02 |  |
| P4-T02 | Phase 4 | Report Safety Scanner | Not Started | P4-T01 |  |
| P4-T03 | Phase 4 | Release Checklist 集成 | Not Started | P4-T02 |  |
| P4-T04 | Phase 4 | Observability and Diagnostics | Not Started | P1-T02, P4-T02 |  |

---

## 12. 当前推荐下一步

Global guardrails、Phase 0 review gate、Phase 1 Analysis Report Add-On、Phase 2 Agent Tools（`P2-T01`、`P2-T02`、`P2-T03` 与 P2 Phase Review）以及 `P3-T01` Research Task Data Contract、`P3-T02` Snapshot-Based Task Persistence、`P3-T03` Intelligence Service 接入、`P3-T04` 专表升级决策 Gate 已完成并验证。下一步从 P3 Phase Review 继续，不改变既有交易语义；P3-T04 已明确当前继续 snapshot-first，不新增 DB 专表。

- [x] 创建 DSA 集成分支：`codex/serenity-phase-0-evidence-bridge`。
- [x] 完成 G-T01 至 G-T03。
- [x] 执行 P0-T01。
- [x] 执行 P0-T02。
- [x] 执行 P0-T03。
- [x] 执行 P0-T04。
- [x] 执行 Phase 0 review gate。
- [x] 执行 P1-T01。
- [x] 执行 P1-T02。
- [x] 执行 P1-T03。
- [x] 执行 P1-T04。
- [x] 执行 P1-T05。
- [x] 执行 P1 Phase Review。
- [x] 执行 P2-T01。
- [x] 执行 P2-T02。
- [x] 执行 P2-T03。
- [x] 执行 P2 Phase Review。
- [x] 执行 P3-T01 Research Task Data Contract。
- [x] 执行 P3-T02 Snapshot-Based Task Persistence。
- [x] 执行 P3-T03 Intelligence Service 接入。
- [x] 执行 P3-T04 专表升级决策 Gate。
- [ ] 执行 P3 Phase Review。
