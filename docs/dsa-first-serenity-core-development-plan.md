# DSA-First Serenity Core Development Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 `daily_stock_analysis` 作为主产品和主运行时，将 Serenity Alpha Lab 收敛为可复用的证据质量、研究审计和补证闭环内核。

**Architecture:** DSA 继续拥有用户入口、行情源、调度、通知、组合、回测、Agent 和交易决策报告。Serenity Core 只提供证据规范化、来源覆盖、readiness gate、补证任务、研究包和安全边界检查，不直接生成或覆盖 DSA 的买卖建议。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / React + Vite / Zustand / Serenity deterministic evidence pipeline / JSONL evidence bridge / pytest + Vitest + Playwright.

---

## 1. 背景与决策

用户最新方向是：

- `daily_stock_analysis` 为主。
- Serenity Alpha Lab / Serenity Core 为辅。
- 产品能力整体向 `daily_stock_analysis` 对齐。
- 保留 Serenity Alpha Lab 的投资研究体系、证据闭环和审计能力。

因此，正确方向不是把 DSA 的大部分代码迁入 Serenity，也不是重写 DSA 的 UI，而是：

1. 以 DSA 为产品壳和运行时。
2. 将 Serenity 抽成窄边界核心模块。
3. 通过 Adapter / Service / Agent Tool / Report Section 渐进接入。
4. 所有接入默认 fail-open，不能拖慢或破坏 DSA 主分析链路。

## 2. 调研证据摘要

### 2.1 DSA 当前能力

本地 DSA 仓库路径：

```text
/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
```

关键事实：

- DSA README 明确是股票智能分析系统，面向 AI 决策报告、评分、趋势、买卖点位、风险警报、催化因素和操作检查清单。
- DSA 覆盖 A 股、港股、美股、日股、韩股、台股和 ETF。
- DSA 已有 Web / API / 桌面端 / Bot / GitHub Actions / Docker / 定时任务 / 通知能力。
- DSA FastAPI v1 聚合 auth、agent、analysis、history、stocks、backtest、system、usage、portfolio、alerts、decision-signals、alphasift、intelligence、health。
- DSA 核心 `StockAnalysisPipeline` 已串起行情、实时、筹码、基本面、技术趋势、资讯搜索、社交舆情、Agent 分支和历史上下文。

主要代码证据：

- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/README.md`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/main.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/server.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/app.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/router.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/endpoints/analysis.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/endpoints/agent.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/core/pipeline.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/analysis_service.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/task_service.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/intelligence_service.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/storage.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/pages/HomePage.tsx`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/apps/dsa-web/src/types/analysis.ts`

### 2.2 Serenity 当前能力

当前 Serenity 仓库路径：

```text
/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
```

关键事实：

- Serenity 是 local-first research engine，不是投资顾问。
- Serenity 明确不生成 buy/sell/hold、target price、position sizing。
- Serenity 核心数据模型是 `EvidenceItem`。
- Serenity 运行链路是 `evidence -> topic resolver -> retrieval -> scorecard -> readiness -> memo pack/dashboard -> evidence tasks -> rerun -> handoff`。
- Serenity 的强项是结构化证据、来源覆盖、研究质量门禁、补证任务、质量 delta、审计与交接。

主要代码证据：

- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/evidence.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/retrieval.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/topic_resolver.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/scoring.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/source_coverage.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/readiness.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/acquisition_queue.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/coverage_matrix.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/evidence_intake.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/report_safety.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/memo_pack.py`
- `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab/src/serenity_alpha_lab/cli.py`

## 3. 核心差异

| 维度 | daily_stock_analysis | Serenity Alpha Lab | 方案判断 |
| --- | --- | --- | --- |
| 产品定位 | 日常股票分析、决策工作台、持仓与提醒 | 证据闭环研究内核 | DSA 为主 |
| 用户入口 | Web、API、桌面、Bot、Actions、Docker | CLI、本地 HTML、local server | 保留 DSA 入口 |
| 输出语义 | 评分、趋势、买卖点、操作建议、警报 | 研究质量、证据覆盖、补证任务 | 不混淆语义 |
| 数据形态 | 行情、新闻、基本面、组合、历史、回测 | JSONL EvidenceItem | 写 Adapter |
| 闭环 | 交易后验、回测、组合、提醒 | 补证、质量 delta、复跑、交接 | 两条闭环并存 |
| UI | React/Vite 工作台 | 静态 HTML 研究页 | 不迁移 Serenity UI |
| 集成风险 | 生命周期复杂、通知/DB/调度副作用多 | research-only 边界强 | 窄接口接入 |

## 4. 目标架构

```text
daily_stock_analysis
  ├─ Web / Desktop / Bot / API
  ├─ Analysis Pipeline
  ├─ Market Data Providers
  ├─ Agent / Strategy Tools
  ├─ Portfolio / Backtest / Alerts / Notifications
  └─ Serenity Integration Layer
       ├─ adapters
       │    ├─ dsa_context_to_evidence.py
       │    ├─ intelligence_to_evidence.py
       │    ├─ fundamentals_to_evidence.py
       │    └─ report_to_evidence.py
       ├─ core
       │    ├─ evidence.py
       │    ├─ retrieval.py
       │    ├─ scoring.py
       │    ├─ source_coverage.py
       │    ├─ readiness.py
       │    └─ acquisition_queue.py
       ├─ services
       │    ├─ evidence_quality_service.py
       │    ├─ research_audit_service.py
       │    └─ research_task_service.py
       ├─ agent_tools
       │    ├─ evidence_quality_tool.py
       │    └─ evidence_gap_tool.py
       └─ report_sections
            └─ serenity_evidence_quality.py
```

### 4.1 Ownership

DSA owns:

- CLI / Web / API / Desktop / Bot entry points.
- Stock code normalization and market routing.
- Data provider fallback and rate limiting.
- LLM provider configuration.
- Analysis task queue and run-flow state.
- Report rendering and notification dispatch.
- Portfolio, backtest, alerts, decision signals.

Serenity Core owns:

- Evidence schema and validation.
- Evidence provenance and source excerpt discipline.
- Deterministic retrieval.
- Source coverage and readiness checks.
- Scorecard summaries.
- Evidence gap and acquisition tasks.
- Research quality audit metadata.
- Research-only boundary checks where applicable.

### 4.2 Non-Goals

- 不把 DSA UI 大规模迁入 Serenity。
- 不让 Serenity 直接生成 DSA 的买入、卖出、持有、目标价、仓位建议。
- 不复制 DSA `StockAnalysisPipeline` 到 Serenity。
- 不复制 DSA DataFetcherManager fallback 逻辑。
- 不把 Serenity `ui.py` 作为 DSA 页面基座。
- 不让 Serenity 补证/pack 生成阻塞 DSA 主分析。

### 4.3 Import Direction and Dependency Boundary

Hard dependency rule:

```text
DSA application layer
  -> src/serenity/services
     -> src/serenity/adapters
        -> src/serenity/core
```

Allowed dependencies:

| Layer | May Import | Must Not Import |
| --- | --- | --- |
| `src/serenity/core/*` | Python standard library, local Serenity core modules | DSA pipeline, providers, repositories, notification, Agent factory, FastAPI, React assets, CLI, absolute paths |
| `src/serenity/adapters/*` | Serenity core, DSA low-sensitivity data objects or dictionaries | Data provider managers, notification senders, task queues, UI code |
| `src/serenity/services/*` | Serenity adapters/core, logging, config values passed in by caller | Direct provider fetches, report renderer mutation, notification dispatch |
| `src/serenity/agent_tools/*` | Serenity services, DSA `ToolDefinition` / `ToolParameter` | Agent prompt mutation, trade signal recalculation |
| DSA `analysis_service` | `EvidenceQualityService` after base report creation | Serenity CLI/UI/output directory |

Non-negotiable constraints:

- No cross-repository absolute-path imports.
- No runtime imports from `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` inside DSA.
- Serenity pure core must be copied, vendored, or packaged explicitly before use.
- `src/serenity/core/*` must remain deterministic and side-effect free except explicit JSONL read/write helpers.
- Serenity audit must never run inside quote providers, fallback routing, rate-limit handling, database migrations, or task queue scheduling.

### 4.4 Integration Call Sites

Allowed call sites:

| DSA Surface | Allowed Serenity Use | Reason |
| --- | --- | --- |
| `src/services/analysis_service.py` | Attach optional `serenity_audit` after base `AnalysisResult` is built | Keeps DSA main analysis behavior stable |
| `api/v1/schemas/history.py` | Expose optional historical `serenity_research` block | Lets UI consume old/new records safely |
| `apps/dsa-web/src/components/report/ReportSummary.tsx` | Render evidence-quality card after data-context summary | Keeps Serenity below DSA decision summary |
| `src/agent/tools/registry.py` / `src/agent/tools/analysis_tools.py` | Register evidence-quality tools | Lets users ask research-quality questions explicitly |
| `src/services/intelligence_service.py` or repository layer | Persist research task metadata after Phase 3 gate | Avoids a separate Serenity project library |

Forbidden call sites:

- DSA `DataFetcherManager` and individual fetchers.
- Notification sender implementations.
- Alert trigger decision path.
- Portfolio or backtest scoring logic.
- DSA `sentiment_score`, `operation_advice`, `action`, `trend_prediction`, `sniper_points`, stop-loss, take-profit, or position-sizing generation.

### 4.5 Packaging Strategy

Use an explicit packaging decision before implementation:

| Option | Recommendation | Why |
| --- | --- | --- |
| Copy minimal pure modules into DSA `src/serenity/core` | Recommended for Phase 0-1 | Lowest deployment risk; no cross-repo runtime dependency |
| Internal package, e.g. `serenity-alpha-core` | Recommended after contracts stabilize | Enables reuse without dragging UI/CLI |
| Git submodule | Avoid initially | Adds workflow complexity and path coupling |
| PyPI/private package | Later | Useful once versioning and release cadence are mature |

Phase 0 should copy only pure modules and keep a source provenance note in DSA docs. Do not copy `cli.py`, `ui.py`, generated `output/*`, default CPO data, or local server code.

## 5. 推荐落地策略

### Phase 0: Evidence Bridge POC

目标：先验证 DSA 上下文能否稳定转换为 Serenity evidence，不改 DSA 产品行为。

输出：

- `EvidenceItem` 兼容 JSONL。
- 离线 evidence audit。
- readiness / source coverage / evidence gaps 旁路报告。
- No DSA API response change.
- No DSA Web UI change.
- No notification change.
- No database schema change.

建议 DSA 侧新增文件：

```text
src/serenity/adapters/dsa_context_to_evidence.py
src/serenity/services/evidence_quality_service.py
tests/test_serenity_evidence_adapter.py
tests/test_serenity_evidence_quality_service.py
docs/serenity-core-integration.md
```

最小字段映射：

| Serenity 字段 | DSA 来源 | 映射规则 |
| --- | --- | --- |
| `id` | source type + stock code + timestamp/hash | 稳定 hash，避免重复导入 |
| `source_title` | news title / provider name / report section | 不允许空值 |
| `source_url` | news url / provider url / internal provenance | 外部 URL 优先，内部来源用 `dsa://` namespace |
| `published_at` | news time / report time / snapshot time | 无法确认则用分析日期并标记 derived |
| `claim` | 摘要句 / context item summary | 必须是可审计陈述 |
| `summary` | DSA compact summary | 不能直接塞完整 LLM 报告 |
| `tickers` | stock code | 使用 DSA normalize 后代码 |
| `themes` | sector / concept / strategy / market phase | 不要硬编码 Serenity 默认 CPO 主题 |
| `direction` | sentiment / risk / neutral | 不确定时 `neutral` |
| `strength` | official/fundamental/news/LLM | official/fundamental 可 primary/derived；LLM 输出只能 speculative |
| `claim_type` | fact/risk/catalyst/inference | 行情事实为 fact；LLM 判断为 inference |
| `source_excerpt` | 原文片段 / payload excerpt | primary/fact 必须提供 |

### Phase 1: Analysis Report Add-On

目标：在 DSA 分析结果中加入“研究充分性 / 证据质量”板块，但不改变操作建议。

Entry criteria:

- Phase 0 adapter tests pass.
- At least one existing DSA historical report can produce non-empty evidence.
- Empty/malformed evidence returns fail-open `unavailable`.
- Product owner accepts the naming: `研究证据质量` / `Research Evidence Quality`.

建议字段：

```json
{
  "serenity_audit": {
    "enabled": true,
    "status": "ready | needs_work | blocked | unavailable",
    "score": 62,
    "confidence": "medium",
    "evidence_count": 12,
    "primary_count": 3,
    "risk_count": 2,
    "key_gaps": ["primary_source_depth", "risk_coverage"],
    "next_research_tasks": [
      {
        "ticker": "AAPL",
        "gap": "risk_coverage",
        "priority": "high",
        "search_prompt": "AAPL latest 10-K risk factors AI supply chain margin"
      }
    ],
    "provenance": {
      "evidence_version": "sha256:...",
      "generated_at": "2026-07-08T00:00:00Z"
    }
  }
}
```

建议前端区块名称：

- 中文：`研究证据质量`
- 英文：`Research Evidence Quality`

区块文案边界：

- 可以写“当前结论的证据充分性较弱”。
- 可以写“建议补充 primary filing、风险因素和反证来源”。
- 不可以写“因此应该买入/卖出/加仓/减仓”。

Exit criteria:

- API returns optional `serenity_audit` or `details.serenityResearch` without breaking old clients.
- UI renders all five states: `disabled`, `ready`, `needs_work`, `blocked`, `unavailable`.
- Turning `SERENITY_CORE_ENABLED=false` restores exact legacy report behavior.
- Notification output is unchanged unless explicitly configured to include the evidence-quality block.

### Phase 2: Agent Tools

目标：让 DSA Agent 能回答研究质量问题。

新增工具建议：

```text
check_evidence_quality(stock_code, topic?)
list_evidence_gaps(stock_code, topic?)
build_research_tasks(stock_code, topic?)
retrieve_supporting_evidence(stock_code, question?)
```

工具接入点：

- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/registry.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/tools/analysis_tools.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/agent/factory.py`
- `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/endpoints/agent.py`

Agent 回答原则：

- 默认解释“证据足够/不足在哪里”。
- 给出下一步研究任务。
- 避免把 Serenity rating 映射成交易动作。
- Only call tools when the user asks about evidence quality, research confidence, source coverage, gaps, or follow-up research.
- Do not force IntelAgent to use Serenity tools for every trading-signal request.
- Tool output must be JSON-serializable and not include stack traces or internal file paths.

### Phase 3: Intelligence Workflow Integration

目标：把 Serenity 的补证任务纳入 DSA 的情报 / 任务工作流，而不是维护两套项目库。

候选方案：

1. 最小方案：补证任务作为 report metadata，不入库。
2. 中等方案：补证任务写入 DSA intelligence repository。
3. 完整方案：新增 `research_tasks` 表，关联 stock code、analysis id、evidence item、task status。

建议从中等方案开始，因为 DSA 已有 intelligence 能力，改动面低于新建完整任务系统。

Persistence decision gate:

| Requirement | Metadata Is Enough | New Table Required |
| --- | --- | --- |
| Display latest audit on report detail | Yes | No |
| Recompute audit for one report | Yes | No |
| Filter tasks by ticker/status across many reports | No | Yes |
| Multi-user task assignment | No | Yes |
| Task status audit trail | No | Yes |
| Retry recovery after worker crash | No | Yes |

Recommended progression:

1. P0: Store only in `analysis_history.context_snapshot.serenity_research`.
2. P1: Add `serenity_research_runs` if cross-report audit history becomes necessary.
3. P2: Add `serenity_evidence_items` only when evidence reuse/search matters.
4. P3: Add `serenity_research_tasks` only when task state needs filtering, ownership, or audit.

### Phase 4: Report Safety and Provenance Guardrails

目标：保证模型生成内容、引用来源、证据质量标记清晰分离。

注意：

- DSA 允许交易建议，因此不能直接套 Serenity 的 `research-only` 禁词。
- 应改造成 provenance safety scanner：
  - 检查 primary/fact 是否有 source_url/source_excerpt。
  - 检查 LLM 生成内容是否被误标 primary。
  - 检查引用来源和模型推断是否混在同一字段。
  - 检查没有来源的重大事实陈述。

Severity model:

| Severity | Example | Effect |
| --- | --- | --- |
| `error` | Serenity-generated panel says “buy/add/sell” or primary/fact lacks source excerpt | Blocks `ready`, returns `needs_work` or `blocked` |
| `warning` | Derived evidence lacks strong excerpt, stale source, high methodology share | Allows audit but surfaces diagnostic warning |
| `info` | Source excerpt contains a quoted investment-action phrase | Allowed when clearly quoted and not generated by Serenity |

Scanner scope:

- Scan Serenity-generated evidence-quality panel and optional Serenity memo.
- Do not scan DSA's existing strategy fields as Serenity violations.
- Quoted source excerpts may contain investment-action language.
- Product-authored Serenity text must not add investment-action language.

### Phase to Task Mapping

| Phase | Tasks | Product Surface | Database Change | Rollback |
| --- | --- | --- | --- | --- |
| Phase 0 | Task 1-3 | None or local artifact only | None | Delete `src/serenity/*`, disable flag |
| Phase 1 | Task 4-5 | API optional field + report card | None by default | `SERENITY_CORE_ENABLED=false` |
| Phase 2 | Task 6 | Agent tools | None | Unregister tools / disable flag |
| Phase 3 | Task 7 | Evidence task history | Optional metadata/table | Stop reading metadata, keep stored rows |
| Phase 4 | Task 8 + scanner hardening | Diagnostics / release guard | None | Disable scanner flag |

Each phase should ship independently. Do not start Phase 2 until Phase 1 has a stable API fixture and a proven disabled-state rollback.

## 6. 推荐文件结构

在 DSA 仓库中：

```text
src/serenity/
  __init__.py
  contracts.py
  adapters/
    __init__.py
    dsa_context_to_evidence.py
    intelligence_to_evidence.py
    fundamentals_to_evidence.py
  core/
    __init__.py
    evidence.py
    retrieval.py
    scoring.py
    source_coverage.py
    readiness.py
    acquisition_queue.py
  services/
    __init__.py
    evidence_quality_service.py
    research_audit_service.py
  agent_tools/
    __init__.py
    evidence_quality_tool.py
  report_sections/
    __init__.py
    serenity_evidence_quality.py
tests/
  test_serenity_evidence_adapter.py
  test_serenity_evidence_quality_service.py
  test_serenity_agent_tools.py
```

不要在第一阶段引入：

```text
src/serenity/ui.py
src/serenity/cli.py
output/ui/*
Serenity static dashboard assets
```

## 7. Data Contract

### 7.1 EvidenceItem

DSA 内部 Serenity EvidenceItem 应保持和 Serenity Alpha Lab 兼容：

```python
@dataclass(frozen=True)
class EvidenceItem:
    id: str
    source_title: str
    source_url: str
    published_at: date
    claim: str
    summary: str
    tickers: Sequence[str]
    themes: Sequence[str]
    supply_chain_layer: str
    direction: Literal["positive", "negative", "neutral"]
    strength: Literal["primary", "derived", "speculative"]
    confidence: float
    factor_impacts: Mapping[str, int]
    claim_type: Literal["fact", "methodology", "inference", "risk", "catalyst", "invalidation"]
    source_excerpt: str = ""
```

Validation rules:

| Field | Rule |
| --- | --- |
| `id` | Stable string; hash over source type, stock code, source URL or `dsa://` URI, claim, and published date |
| `source_title` | Required non-empty string; max 240 chars in API output |
| `source_url` | Required; external `http(s)` preferred; internal provenance uses `dsa://` namespace |
| `published_at` | ISO date in source market context; provenance `generated_at` uses UTC datetime |
| `claim` | Required audit-ready assertion; max 500 chars in API output |
| `summary` | Required short summary; max 800 chars in API output |
| `tickers` | Normalized DSA stock code list; no empty tickers |
| `themes` | Business themes, sector, strategy, market phase, or source tags; no hardcoded CPO defaults |
| `direction` | `positive`, `negative`, or `neutral`; unknown maps to `neutral` |
| `strength` | `primary`, `derived`, or `speculative`; LLM-generated text defaults to `speculative` |
| `confidence` | Float `0.0-1.0`; invalid values reject the evidence item |
| `factor_impacts` | Non-empty mapping of known or namespaced factors to integer impacts |
| `claim_type` | `fact`, `methodology`, `inference`, `risk`, `catalyst`, or `invalidation` |
| `source_excerpt` | Required for `primary` and `fact`; optional but preferred otherwise |

Classification rules:

- Official filing, exchange announcement, company release with direct excerpt can be `primary`.
- Data provider snapshot can be `derived` unless it carries a direct official source excerpt.
- News article summary is usually `derived`.
- Agent or LLM report text is always `speculative` and `inference` unless backed by separate evidence.
- Missing source URL must use `dsa://` and cannot be `primary`.
- Bad evidence should be dropped with a validation warning unless all evidence fails; if all evidence fails, return audit `unavailable`.

### 7.2 SerenityAudit

DSA-facing result should be stable and small:

```python
@dataclass(frozen=True)
class SerenityAudit:
    status: str
    score: int
    confidence: str
    evidence_count: int
    primary_count: int
    risk_count: int
    key_gaps: list[str]
    top_evidence: list[EvidenceReference]
    next_research_tasks: list[ResearchTask]
    generated_at: datetime
```

Status contract:

| Status | Enabled | Score | Meaning |
| --- | --- | --- | --- |
| `disabled` | false | `null` | Feature is off; no audit attempted |
| `ready` | true | `0-100` | Evidence quality meets configured gate |
| `needs_work` | true | `0-100` | Audit succeeded but gaps remain |
| `blocked` | true | `0-100` or `null` | Evidence is too weak or unsafe to summarize as quality-supported |
| `unavailable` | true | `null` | Audit failed, timed out, or input was malformed; base DSA report still succeeded |

Confidence contract:

```text
low | medium | high | unavailable
```

`disabled` and `unavailable` use `confidence="unavailable"` and `score=null`.

### 7.3 Nested API Types

Recommended Python schema:

```python
SerenityAuditStatus = Literal["disabled", "ready", "needs_work", "blocked", "unavailable"]
SerenityConfidence = Literal["low", "medium", "high", "unavailable"]
SerenityTaskStatus = Literal["open", "collected", "verified", "dismissed"]
SerenityTaskPriority = Literal["high", "medium", "low"]


class SerenityEvidenceReference(BaseModel):
    id: str
    source_title: str
    source_url: str
    published_at: str
    claim: str
    source_excerpt: str = ""
    strength: Literal["primary", "derived", "speculative"]
    claim_type: Literal["fact", "methodology", "inference", "risk", "catalyst", "invalidation"]


class SerenityResearchTask(BaseModel):
    id: str
    ticker: str
    gap: str
    priority: SerenityTaskPriority
    search_prompt: str
    acceptance_criteria: list[str]
    source_targets: list[str]
    status: SerenityTaskStatus = "open"


class SerenityCoverageSummary(BaseModel):
    evidence_count: int = 0
    primary_count: int = 0
    risk_count: int = 0
    methodology_share: float = 0.0
    placeholder_share: float = 0.0
    flags: list[str] = []


class SerenityAuditProvenance(BaseModel):
    evidence_version: str
    generated_at: str
    duration_ms: int
    core_version: str
    config_version: str


class SerenityAuditBlock(BaseModel):
    enabled: bool
    research_only: bool = True
    status: SerenityAuditStatus
    score: int | None = None
    confidence: SerenityConfidence
    coverage: SerenityCoverageSummary
    key_gaps: list[str] = []
    top_evidence: list[SerenityEvidenceReference] = []
    next_research_tasks: list[SerenityResearchTask] = []
    provenance: SerenityAuditProvenance | None = None
    error_type: str | None = None
    message: str | None = None
```

Limits:

| Field | Limit |
| --- | --- |
| `top_evidence` | Max 5 items, sorted by retrieval score then source recency |
| `next_research_tasks` | Max 8 items, sorted by high priority first |
| `source_excerpt` | Max 1,000 chars in API response |
| `claim` | Max 500 chars in API response |
| `summary` | Max 800 chars in API response |
| `search_prompt` | Max 300 chars |

TypeScript must mirror these names in camelCase:

```typescript
export type SerenityAuditStatus = 'disabled' | 'ready' | 'needs_work' | 'blocked' | 'unavailable';
export type SerenityConfidence = 'low' | 'medium' | 'high' | 'unavailable';
```

### 7.4 DSA Provenance Namespace

Internal provenance URI examples:

```text
dsa://analysis/{query_id}/record/{record_id}/section/{section_name}
dsa://analysis/{query_id}/context/{context_hash}
dsa://provider/{provider_name}/snapshot/{snapshot_hash}
dsa://intelligence/{item_id}
dsa://agent/{session_id}/turn/{turn_id}
```

Rules:

- `dsa://` is an internal provenance pointer, not a primary source.
- Evidence with only `dsa://` source URL cannot be `primary`.
- If a `dsa://` item wraps an external article, preserve the external URL separately in `raw_source_url`.
- Hash input must include source URL or internal URI, stock code, claim text, published date, and origin type.
- Hash must not include volatile generated timestamps.

### 7.5 Fail-Open Behavior

If Serenity audit fails:

```json
{
  "serenity_audit": {
    "enabled": true,
    "status": "unavailable",
    "error_type": "adapter_error",
    "message": "Evidence audit unavailable; base DSA analysis completed."
  }
}
```

Rules:

- DSA analysis still succeeds.
- Notifications still send.
- API still returns normal report.
- Error is visible in diagnostics/logs.
- Tests must cover this path.

Failure taxonomy:

| Error Type | Cause | Response |
| --- | --- | --- |
| `disabled` | Feature flag off | `{enabled:false,status:"disabled"}` |
| `adapter_error` | DSA context conversion failed | `unavailable`, include safe message |
| `validation_error` | Evidence schema rejected all items | `unavailable`; if partial items valid, continue as `needs_work` with warnings |
| `timeout` | Audit exceeded budget | `unavailable`, include `duration_ms` |
| `core_error` | Retrieval/scoring/readiness failed | `unavailable`, log stack internally |
| `empty_context` | No usable DSA context | `blocked` if audit ran cleanly; `unavailable` if context malformed |

Do not expose stack traces in API, UI, Agent responses, or notifications.

### 7.6 API Placement

Phase 1 preferred placement:

```text
AnalysisResultResponse.serenity_audit
AnalysisReport.details.serenity_research
HistoryItem.serenity_status? deferred compact list flag
```

Recommended first API surface:

- Put the complete object under historical report detail `details.serenityResearch`.
- Add a compact optional `serenityAudit` to live analysis response only if the same object can be generated without re-querying providers.
- Avoid adding Serenity fields to history list until filtering/search requirements are clear.

Do not store Serenity score in:

- `sentiment_score`
- `operation_advice`
- `action`
- `trend_prediction`
- `strategy`
- alert rule trigger payloads

## 8. Implementation Plan

### Task 1: Extract Minimal Serenity Core Contract

**Files:**

- Create in DSA: `src/serenity/contracts.py`
- Create in DSA: `src/serenity/core/evidence.py`
- Test in DSA: `tests/test_serenity_contracts.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import date
import pytest

from src.serenity.core.evidence import EvidenceValidationError, parse_evidence_item


def test_parse_evidence_item_requires_source_excerpt_for_primary_fact():
    payload = {
        "id": "dsa-news-1",
        "source_title": "Company filing",
        "source_url": "https://example.com/filing",
        "published_at": "2026-07-08",
        "claim": "Revenue increased.",
        "summary": "Revenue increased.",
        "tickers": ["AAPL"],
        "themes": ["fundamentals"],
        "supply_chain_layer": "company",
        "direction": "positive",
        "strength": "primary",
        "confidence": 0.8,
        "factor_impacts": {"evidence_quality": 2},
        "claim_type": "fact",
    }

    with pytest.raises(EvidenceValidationError):
        parse_evidence_item(payload)
```

- [ ] **Step 2: Implement minimal evidence schema**

Port only schema, validation, tokenization, load/write, and dedupe logic from Serenity. Do not port CLI/UI.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_serenity_contracts.py -q
```

Expected: pass.

- [ ] **Step 4: Enforce import boundary**

Add a simple import-boundary test:

```python
from pathlib import Path


FORBIDDEN = (
    "src.core.pipeline",
    "data_provider",
    "src.notification",
    "src.agent.factory",
    "api.",
    "uvicorn",
    "fastapi",
)


def test_serenity_core_has_no_forbidden_runtime_imports():
    root = Path("src/serenity/core")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in FORBIDDEN), path
```

### Task 2: Build DSA Context to Evidence Adapter

**Files:**

- Create in DSA: `src/serenity/adapters/dsa_context_to_evidence.py`
- Test in DSA: `tests/test_serenity_evidence_adapter.py`

- [ ] **Step 1: Write failing tests for news/intelligence/fundamental conversion**

Test requirements:

- News with URL becomes `derived` or `primary` only when original article excerpt exists.
- LLM-generated report text is always `speculative`.
- Fundamental snapshot with provider provenance becomes `derived` or `primary` based on source.
- Missing URL uses `dsa://` namespace and cannot be `primary`.

- [ ] **Step 2: Implement adapter**

Pseudo-interface:

```python
def build_evidence_from_analysis_context(
    *,
    stock_code: str,
    stock_name: str,
    context_snapshot: dict[str, object],
    report_payload: dict[str, object] | None = None,
) -> list[EvidenceItem]:
    ...
```

- [ ] **Step 3: Run adapter tests**

```bash
python -m pytest tests/test_serenity_evidence_adapter.py -q
```

Expected: pass.

- [ ] **Step 4: Add fixture coverage**

Fixtures required:

- News item with external URL and excerpt.
- News item without URL.
- Fundamental snapshot.
- LLM report text.
- Malformed provider payload.
- Empty context snapshot.

### Task 3: Add Evidence Quality Service

**Files:**

- Create in DSA: `src/serenity/services/evidence_quality_service.py`
- Test in DSA: `tests/test_serenity_evidence_quality_service.py`

- [ ] **Step 1: Write failing tests**

Test requirements:

- Returns `SerenityAudit`.
- Includes score, confidence, primary/risk counts, gaps, top evidence, next tasks.
- Empty evidence returns `blocked` or `unavailable` without exception.
- Adapter exception returns fail-open unavailable result.

- [ ] **Step 2: Implement service using Serenity core**

Pseudo-interface:

```python
class EvidenceQualityService:
    def audit_stock_context(
        self,
        *,
        stock_code: str,
        topic: str,
        context_snapshot: dict[str, object],
        report_payload: dict[str, object] | None = None,
    ) -> SerenityAudit:
        ...
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_serenity_evidence_quality_service.py -q
```

Expected: pass.

- [ ] **Step 4: Add timeout and cache behavior**

Implement:

- Timeout budget from `SERENITY_CORE_TIMEOUT_MS`.
- Cache key from `stock_code + query_id/context_hash + config_version + core_version`.
- Safe fallback when cache is corrupt.
- Explicit `duration_ms` in provenance.

### Task 4: Attach Audit to DSA Analysis Response

**Files:**

- Modify in DSA: `src/services/analysis_service.py`
- Modify in DSA: `api/v1/schemas/analysis.py`
- Modify in DSA: `apps/dsa-web/src/types/analysis.ts`
- Test in DSA: existing analysis API tests plus new contract tests.

- [ ] **Step 1: Add schema fields**

Add optional `serenity_audit` fields only. Preserve backward compatibility.

- [ ] **Step 2: Inject after base analysis succeeds**

Add audit call after pipeline result is built, not inside low-level data provider path.

- [ ] **Step 3: Ensure fail-open**

If audit fails, response includes unavailable audit metadata, but report succeeds.

- [ ] **Step 4: Run contract tests**

```bash
python -m pytest tests -k "analysis and serenity" -q
```

Expected: pass.

- [ ] **Step 5: Add backward-compatibility fixture**

Create one old response fixture without `serenity_audit` and one new fixture with it. Tests should prove old clients can ignore the new optional field.

### Task 5: Render Evidence Quality Panel

**Files:**

- Modify in DSA: `apps/dsa-web/src/components/report/ReportSummary.tsx`
- Create in DSA: `apps/dsa-web/src/components/report/SerenityEvidenceQuality.tsx`
- Modify in DSA: `apps/dsa-web/src/types/analysis.ts`
- Test in DSA: `apps/dsa-web/tests/*`

- [ ] **Step 1: Add component tests**

Test visible states:

- ready / needs_work / blocked / unavailable.
- gaps list.
- next research tasks.
- no trading action text introduced by this component.

- [ ] **Step 2: Render panel after overview and before detailed evidence**

The panel should be close to report context, but not above the primary decision summary.

- [ ] **Step 3: Run frontend tests**

```bash
cd apps/dsa-web
npm run lint
npm run test
npm run build
```

Expected: pass.

- [ ] **Step 4: Validate UI semantics**

The component must:

- Display `research_only` badge.
- Render canonical disclaimer: `该板块仅评估研究证据质量，不构成交易建议。`
- Never render buttons or copy that say buy, sell, add, reduce, target price, or position sizing.
- Render unavailable/disabled states as calm informational states, not errors.

### Task 6: Add Agent Tools

**Files:**

- Create in DSA: `src/serenity/agent_tools/evidence_quality_tool.py`
- Modify in DSA: `src/agent/tools/registry.py`
- Test in DSA: `tests/test_serenity_agent_tools.py`

- [ ] **Step 1: Add tests for tool registration and output**

Expected tool names:

- `check_evidence_quality`
- `list_evidence_gaps`
- `build_research_tasks`

- [ ] **Step 2: Implement tools using EvidenceQualityService**

Keep outputs concise and structured.

- [ ] **Step 3: Run agent tool tests**

```bash
python -m pytest tests/test_serenity_agent_tools.py -q
```

Expected: pass.

- [ ] **Step 4: Add semantic guard tests**

Agent tool tests must assert:

- `check_evidence_quality` output contains no trading action recommendation.
- Tool errors return structured unavailable results.
- Tool registration can be disabled without affecting existing tools.

### Task 7: Optional Intelligence Persistence

**Files:**

- Modify in DSA: `src/services/intelligence_service.py`
- Modify in DSA: `src/repositories/intelligence_repo.py`
- Test in DSA: intelligence service tests.

- [ ] **Step 1: Decide persistence shape**

Preferred first pass: store Serenity research tasks as intelligence metadata, not as a new table.

- [ ] **Step 2: Add tests**

Tests must prove tasks can be listed by stock code and status.

- [ ] **Step 3: Implement persistence**

Do not couple to Serenity output directory.

- [ ] **Step 4: Add migration and rollback tests if a table is introduced**

If adding `serenity_research_runs` or `serenity_evidence_items`, tests must cover:

- New database bootstrap.
- Existing database migration.
- Unknown metadata fields preserved.
- Feature disabled after rows exist.

### Task 8: Documentation and Release Readiness

**Files:**

- Modify in DSA: `docs/serenity-core-integration.md`
- Modify in DSA: `.env.example` only if new config is introduced.
- Modify in DSA: `docs/CHANGELOG.md`

- [ ] **Step 1: Document config and behavior**

Document:

- feature flag
- fail-open behavior
- fields added to API
- UI panel semantics
- evidence classification rules

- [ ] **Step 2: Run verification matrix**

```bash
python -m pytest -m "not network"
cd apps/dsa-web && npm run lint && npm run build
```

If touched:

```bash
python scripts/check_ai_assets.py
```

- [ ] **Step 3: Add release runbook**

Document:

- How to enable.
- How to disable.
- How to confirm disabled behavior.
- Where audit logs appear.
- How stale cache is cleared.
- What data remains after rollback.

## 9. Config Strategy

Recommended feature flags:

```env
SERENITY_CORE_ENABLED=false
SERENITY_CORE_FAIL_OPEN=true
SERENITY_CORE_MAX_EVIDENCE=24
SERENITY_CORE_INCLUDE_LLM_REPORT_EVIDENCE=false
SERENITY_CORE_STORE_RESEARCH_TASKS=false
SERENITY_CORE_TIMEOUT_MS=1500
SERENITY_CORE_CACHE_TTL_SECONDS=86400
SERENITY_CORE_TOP_EVIDENCE_LIMIT=5
SERENITY_CORE_TASK_LIMIT=8
SERENITY_CORE_EXCERPT_MAX_CHARS=1000
```

Defaults:

- Disabled by default until Phase 1 is proven.
- Fail-open enabled by default.
- LLM report evidence disabled by default to avoid circular evidence.

Config table:

| Name | Type | Default | Range | Hot Reload | Applies To |
| --- | --- | --- | --- | --- | --- |
| `SERENITY_CORE_ENABLED` | bool | `false` | `true/false` | No; service restart recommended | API, Web, Agent |
| `SERENITY_CORE_FAIL_OPEN` | bool | `true` | `true/false` | No | Analysis service |
| `SERENITY_CORE_MAX_EVIDENCE` | int | `24` | `1-100` | No | Audit service |
| `SERENITY_CORE_INCLUDE_LLM_REPORT_EVIDENCE` | bool | `false` | `true/false` | No | Adapter |
| `SERENITY_CORE_STORE_RESEARCH_TASKS` | bool | `false` | `true/false` | No | Persistence |
| `SERENITY_CORE_TIMEOUT_MS` | int | `1500` | `100-10000` | No | Audit service |
| `SERENITY_CORE_CACHE_TTL_SECONDS` | int | `86400` | `0-604800` | No | Cache |
| `SERENITY_CORE_TOP_EVIDENCE_LIMIT` | int | `5` | `0-20` | No | API/UI |
| `SERENITY_CORE_TASK_LIMIT` | int | `8` | `0-50` | No | API/UI |
| `SERENITY_CORE_EXCERPT_MAX_CHARS` | int | `1000` | `100-5000` | No | API/UI |

Deployment defaults:

| Environment | Default | Notes |
| --- | --- | --- |
| Local CLI | Disabled | Enable explicitly for POC |
| FastAPI Web | Disabled until Phase 1 | Safe for manual testing |
| Docker | Disabled | Add env vars to compose/docs only after Phase 1 |
| GitHub Actions scheduled analysis | Disabled | Avoid changing automated reports initially |
| Desktop app | Disabled | Enable only after frontend panel is stable |
| Bot | Disabled | Enable Agent tools only in Phase 2 |

Config source order should follow existing DSA conventions:

```text
environment variables / .env
  -> config object
  -> request-scoped override only if explicitly supported
  -> service constructor
```

Do not read `.env` directly inside Serenity core.

## 10. Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| DSA trading semantics conflict with Serenity research-only boundary | User confusion, bad report semantics | Serenity panel only discusses evidence quality, not trade action |
| LLM output misclassified as evidence | False confidence | LLM output defaults to speculative/inference and low confidence |
| Serenity audit slows analysis | Poor UX | Run after main result, cache where possible, fail-open |
| Cross-repo path coupling | Deployment breakage | Package or vendor minimal core; no absolute path dependencies |
| UI bloat | Harder maintenance | Add one compact report panel first |
| Duplicate task systems | Workflow fragmentation | Persist tasks in DSA intelligence/research layer, not Serenity output/ui |
| Safety scanner false positives | Blocking valid DSA recommendations | Build DSA-specific provenance scanner, not direct research-only scanner |
| Optional field breaks old clients | API regression | Add schema fixture tests and keep all fields optional |
| Cache returns stale audit | Misleading evidence quality | Include context hash/config/core version in key and expose generated time |
| Agent treats research score as trade signal | Semantic regression | Tool prompt and tests forbid trading actions |
| Persistence pollutes intelligence semantics | Data model drift | Use context metadata first; add dedicated tables only after decision gate |

## 11. Observability and Runbook

### 11.1 Structured Logs

Every audit attempt should log one structured event:

```json
{
  "event": "serenity_audit_completed",
  "analysis_id": "abc123",
  "record_id": 123,
  "stock_code": "AAPL",
  "audit_status": "needs_work",
  "evidence_count": 12,
  "primary_count": 2,
  "risk_count": 1,
  "gap_count": 3,
  "duration_ms": 318,
  "error_type": null,
  "config_enabled": true,
  "core_version": "0.1.0"
}
```

Failure events use `event="serenity_audit_failed"` and must include `error_type` without stack trace in user-facing payloads.

### 11.2 Metrics

Recommended counters/histograms:

- `serenity_audit_attempt_total`
- `serenity_audit_success_total`
- `serenity_audit_failure_total`
- `serenity_audit_timeout_total`
- `serenity_audit_fail_open_total`
- `serenity_evidence_validation_failure_total`
- `serenity_audit_duration_ms`
- `serenity_audit_status_distribution`

If DSA has no metrics backend, log these as structured events first.

### 11.3 Diagnostics

Safe diagnostics returned to API/UI:

- `status`
- `duration_ms`
- `evidence_version`
- `core_version`
- `generated_at`
- `error_type`
- `message`

Never return:

- stack traces
- full provider payloads
- API keys
- raw unpublished user notes
- absolute local paths

### 11.4 Operator Runbook

Common checks:

| Symptom | Likely Layer | Check |
| --- | --- | --- |
| All audits unavailable | Config/service | `SERENITY_CORE_ENABLED`, timeout, import errors |
| Evidence count is zero | Adapter | Context snapshot shape, provider payload mapping |
| Primary count is zero | Provenance | Missing official URL/excerpt |
| UI panel missing | API/frontend | `details.serenityResearch`, TypeScript type mapping |
| Agent returns trade advice from tool | Agent prompt/tool output | Tool semantic guard and category |
| Notifications changed unexpectedly | Integration boundary | Ensure Phase 1 did not alter notification templates |

## 12. Compliance and Product Semantics

### 12.1 Canonical Copy

Chinese:

```text
该板块仅评估研究证据质量，不构成交易建议。
```

English:

```text
This section evaluates research evidence quality only and is not trading advice.
```

Use these exact disclaimers in API examples, UI copy, Agent tool responses, and docs.

### 12.2 Allowed and Forbidden Language

Allowed Serenity-generated language:

- Evidence sufficiency.
- Source coverage.
- Primary source depth.
- Risk evidence coverage.
- Invalidation clarity.
- Research confidence.
- Evidence gaps.
- Next research tasks.
- Source quality warnings.

Forbidden Serenity-generated language:

- Buy/sell/hold/add/reduce calls.
- Target price.
- Stop loss or take profit.
- Position sizing.
- Direct instruction to execute a trade.
- “Because Serenity score is high, buy...”

DSA main report may keep existing trading semantics. The restriction applies to Serenity-generated panels, Serenity Agent tools, Serenity memo attachments, and provenance scanner output.

### 12.3 Score Naming

Use:

```text
serenity_score
research_quality_score
research_confidence
evidence_quality_status
```

Do not use:

```text
sentiment_score
operation_score
buy_score
signal_score
```

This prevents Serenity scorecard from being mistaken for DSA sentiment or action taxonomy.

## 13. Definition of Done

| Phase | Definition of Done |
| --- | --- |
| Phase 0 | JSONL artifact can be generated from one DSA historical record; contract tests pass; no API/UI/notification behavior changes |
| Phase 1 | API field is optional and stable; UI renders five states; disabled flag restores old behavior; no Serenity text changes operation advice |
| Phase 2 | Agent tools register behind flag; tool outputs are structured; semantic guard tests prove no trading action is generated |
| Phase 3 | Research tasks can be queried by stock/status if persisted; status changes are auditable; rollback leaves old records readable |
| Phase 4 | Provenance scanner has severity tests; scanner does not block DSA's legitimate trading report fields; release runbook is documented |

## 14. Verification Matrix

DSA backend:

```bash
python -m pytest -m "not network"
python -m py_compile src/serenity/**/*.py
```

DSA frontend:

```bash
cd apps/dsa-web
npm run lint
npm run test
npm run build
```

Serenity current repo:

```bash
PYTHONPATH=src python3 -m pytest tests -q
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
```

Manual smoke:

- Trigger one DSA analysis.
- Confirm report completes even if Serenity audit is disabled.
- Enable Serenity audit.
- Confirm report includes research evidence quality panel.
- Confirm no Serenity field changes operation advice.
- Confirm Agent can answer evidence gap questions.
- Confirm notifications do not include unexpected Serenity-only trading language.

Additional required tests by phase:

| Phase | Test Class | Required Fixtures |
| --- | --- | --- |
| Phase 0 | Adapter/unit | external news, no-URL news, fundamentals, LLM report, malformed payload, empty context |
| Phase 1 | API/UI contract | `disabled`, `ready`, `needs_work`, `blocked`, `unavailable` |
| Phase 1 | Backward compatibility | old report response without Serenity field |
| Phase 2 | Agent tools | disabled registry, unavailable result, no trading action text |
| Phase 3 | Persistence | existing DB migration, metadata preservation, disabled read path |
| Phase 4 | Safety scanner | generated text violation, quoted excerpt exemption, DSA main report exemption |

Performance checks:

- With `SERENITY_CORE_MAX_EVIDENCE=24`, audit target duration should be under `SERENITY_CORE_TIMEOUT_MS`.
- Cache hit should avoid recomputing retrieval/scoring.
- Audit timeout must not delay base DSA response beyond configured budget.

## 15. Recommended Next Step

Start with Phase 0 in the DSA repository:

1. Create the minimal `src/serenity/` package.
2. Port only Serenity pure core modules.
3. Add `dsa_context_to_evidence` adapter tests first.
4. Generate a local JSONL audit artifact from one existing DSA analysis history record.
5. Review evidence quality manually before touching UI.

This establishes the hard boundary before any report or interface change.
