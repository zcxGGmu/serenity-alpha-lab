# Serenity-Led DSA Full Migration Tracker

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this tracker task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the migration of complete `daily_stock_analysis` capabilities into `serenity-alpha-lab`, with Serenity remaining the primary project, runtime, UX, and investment research philosophy.

**Architecture:** DSA is the source system. Serenity owns the migrated runtime and adapts DSA stock-analysis features into evidence-backed, provenance-aware, safety-scanned research workflows.

**Tech Stack:** Python 3.11+ / Serenity local-first research engine / migrated DSA provider and analysis modules / FastAPI / React + Vite / pytest / Vitest / Playwright.

---

## Current Status Snapshot

**Updated:** 2026-07-09

### Direction

| Item | Status | Evidence |
| --- | --- | --- |
| Serenity-led direction reset | Completed | User clarified that `serenity-alpha-lab` remains primary and DSA should be fully migrated into it |
| Old DSA-first direction | Superseded | `docs/dsa-first-serenity-core-development-plan.md` and tracker are historical and should not drive new implementation |
| Lessons correction | Completed | `tasks/lessons.md` records Serenity-led DSA migration as the governing rule |
| Task checklist correction | Completed | `tasks/todo.md` tracks Serenity-led migration phases and current Phase 3 closeout |

### Repository State

| Repository | Role | Current Notes |
| --- | --- | --- |
| `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` | Primary project and target runtime | Current HEAD before Phase 3 commit: `cb0e2b5`; Phase 3 implementation is ready for commit; protected generated UI dirt under `output/ui/*` remains untouched and must stay unstaged |
| `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` | Source system to migrate from | Current HEAD `95a4b51`; source reference only, not a Serenity runtime dependency |

### Completed Migration Work

| Phase | Status | Evidence |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Serenity commit `b9b0fcb`; `docs/serenity-led-dsa-source-inventory.md`; `tests/test_dsa_migration_boundaries.py`; `make verify` passed |
| Phase 1: Serenity App Runtime Foundation | Completed | Serenity commit `d7187ca`; adds `src/serenity_alpha_lab/app/*`, CLI `serve-app`, and `tests/test_app_api.py`; `make verify` passed with 173 passed |
| Phase 2: Market Data Provider Migration | Completed | Serenity implementation commit `8686d80`; handoff docs commit `cb0e2b5`; adds `src/serenity_alpha_lab/market_data/*` and `tests/test_market_data.py`; `make verify` passed with 180 tests |
| Phase 3: Stock Analysis Pipeline Migration | Completed | Adds Serenity-owned `src/serenity_alpha_lab/analysis/*`, market-data daily-bar manager path, and `tests/test_analysis_pipeline.py`; focused regression passed with `14 passed, 2 warnings`; full `make verify` passed with 184 tests |

Previous DSA-first integration work is useful source research but is no longer the governing product direction.

### Next Phase

| Phase | Status | Scope |
| --- | --- | --- |
| Phase 4: Report And Safety Integration | Next | Migrate report templates, attach provenance refs to key claims, safety-scan actionability language, and produce Markdown/UI-visible reports from stubbed analysis |

### Phase Completion Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Baseline/inventory/guardrails committed in `b9b0fcb` |
| Phase 1: Serenity App Runtime Foundation | Completed | Commit `d7187ca`; app config/API skeleton/CLI wiring implemented; targeted tests, boundary scan, static import scan, and full `make verify` passed |
| Phase 2: Market Data Provider Migration | Completed | Commit `8686d80`; provider contracts, quote/bar normalization, stock-code routing, fallback diagnostics, and stubbed tests implemented; full verification passed |
| Phase 3: Stock Analysis Pipeline Migration | Completed | Serenity-owned context builder and core pipeline convert normalized market data into evidence items, readiness-gated research signals, diagnostics, and report-gate status |
| Phase 4: Report And Safety Integration | Not Started | Next phase after Phase 3 commit |
| Phase 5: Web Workbench Migration | Not Started | Awaiting Phase 4 |
| Phase 6: Portfolio, Backtest, Alerts, Notifications | Not Started | Awaiting Phase 5 |
| Phase 7: Agent, Bot, Desktop, Docker, CI | Not Started | Awaiting Phase 6 |

### Known Constraints

- Do not stage, commit, revert, or overwrite existing protected generated outputs:
  - `output/ui/analyses/manifest.json`
  - `output/ui/reports/deliverable-research-report.md`
  - `output/ui/runs.json`
  - `output/ui/analyses/topic-2bde5fabbc/`
- Do not runtime-import from `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` inside Serenity.
- Do not copy DSA generated caches, `.venv`, `node_modules`, `__pycache__`, or SQLite runtime DB into Serenity.
- Do not preserve DSA trading-language fields as unqualified advice; migrate them into evidence-backed research signals.
- After each phase-level task is verified, update tracker/todo/lessons/restart prompt and commit only owned phase files with a detailed Chinese commit message. Protected generated `output/ui/*` artifacts must remain unstaged unless explicitly requested.

## Completed Phase 0 Baseline

| Item | Status | Evidence |
| --- | --- | --- |
| DSA source inventory artifact | Completed | `docs/serenity-led-dsa-source-inventory.md` records DSA source surfaces, generated/runtime exclusions, migration risks, and Serenity/DSA HEADs |
| Import-boundary guard test | Completed | `tests/test_dsa_migration_boundaries.py` checks external DSA checkout path literals, DSA source-package imports, and accidental `src/daily_stock_analysis` package creation |
| Runtime import scan | Completed | `rg -n "daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" src/serenity_alpha_lab` returned no matches |
| Current Serenity baseline | Completed | `make verify` passed: `168 passed, 2 warnings`; doctor ok; `run-cpo-pack` completed with 182 evidence items, 6 ready memos, 0 skipped; coverage matrix written |
| Diff hygiene | Completed | `git diff --check` passed |
| Phase commit habit | Completed | Task log and lessons require committing every verified phase-level task with protected generated UI outputs excluded |
| Phase 0 commit | Completed | Serenity commit `b9b0fcb` (`docs: 完成 Serenity 主导的 DSA 迁移 Phase 0 基线`) |

## Completed Phase 2 Market Data Provider Migration

| Item | Status | Evidence |
| --- | --- | --- |
| Serenity-owned provider contracts | Completed | `src/serenity_alpha_lab/market_data/contracts.py` defines provider config/base contract, normalized quote/bar DTOs, and provider diagnostics |
| Stock-code routing and normalization | Completed | `src/serenity_alpha_lab/market_data/symbols.py` and `normalization.py` cover CN/HK/JP/KR/TW/US representative DSA formats and standard quote/bar coercion |
| Fallback diagnostics | Completed | `MarketDataManager` records attempt status, fallback target, sanitized error type/message, and `fallback_from` using stub providers |
| Default-off credentials | Completed | Credentialed providers are skipped unless their configured env var exists; tests assert no provider call without credentials |
| Stubbed tests | Completed | `tests/test_market_data.py` uses only in-process stubs; no live credentials, external network, or DSA runtime import |
| Targeted verification | Completed | `python3 -m pytest tests/test_market_data.py tests/test_app_api.py tests/test_cli.py tests/test_dsa_migration_boundaries.py -q` -> `43 passed, 2 warnings`; `py_compile`, static import scan, live dependency/cache scan, and `git diff --check` passed |
| Full verification | Completed | `make verify` -> `180 passed, 2 warnings`; doctor ok; `run-cpo-pack` completed with 182 evidence items, 6 ready memos, 0 skipped; coverage matrix ok |
| Independent review fix | Completed | Added regression for non-finite provider prices and changed `_safe_float()` to reject `inf` / `-inf` / `NaN` |

## Completed Phase 3 Stock Analysis Pipeline Migration

| Item | Status | Evidence |
| --- | --- | --- |
| Serenity-owned analysis package | Completed | `src/serenity_alpha_lab/analysis/__init__.py`, `context.py`, and `pipeline.py` define context builder, pipeline, readiness gate, report gate, research signals, diagnostics, and JSON-safe result output |
| Market data to evidence conversion | Completed | Normalized quotes and daily bars become `EvidenceItem` records with stable IDs such as `serenity:market-data:AAPL:quote:2026-07-09`, `serenity://market-data/...` provenance URLs, source excerpts, themes, claim types, and factor impacts |
| Source coverage/readiness gates | Completed | Pipeline evaluates `assess_source_coverage`, returns `ready` / `needs_work` / `blocked`, and blocks report generation unless readiness is ready |
| Research-only signals | Completed | Pipeline exposes score, rating, confidence, gaps, factor scores, evidence IDs, and diagnostics while avoiding DSA trading fields |
| Stubbed end-to-end test | Completed | `tests/test_analysis_pipeline.py` covers context building, report blocking on missing risk coverage, fail-open provider unavailability, and recursive trading-field absence |
| Market-data manager daily bars | Completed | `MarketDataManager.get_daily_bars()` normalizes stubbed daily rows without live network or provider SDKs |
| Targeted verification | Completed | `python3 -m pytest tests/test_analysis_pipeline.py -q` -> `3 passed`; `python3 -m pytest tests/test_analysis_pipeline.py tests/test_market_data.py -q` -> `11 passed`; `python3 -m pytest tests/test_analysis_pipeline.py tests/test_market_data.py tests/test_dsa_migration_boundaries.py -q` -> `14 passed, 2 warnings` |
| Static verification | Completed | `py_compile`, runtime DSA checkout import scan, live dependency/cache scan, and `git diff --check` passed |
| Full verification | Completed | `make verify` -> `184 passed, 2 warnings`; doctor ok; `run-cpo-pack` completed with 182 evidence items, 6 ready memos, 0 skipped; coverage matrix ok |

## Next Task

Start Phase 4:

1. Migrate DSA report templates into Serenity report generation.
2. Attach provenance refs to every key claim and run report safety scans for actionability language.
3. Produce Markdown and UI-visible reports from one stubbed analysis without network, live credentials, provider SDKs, DSA runtime imports, or protected generated UI artifact changes.

## Copyable Restart Prompt

```text
请继续在 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab 当前进度上开发。

先阅读并遵守：
1. docs/serenity-led-dsa-full-migration-plan.md
2. docs/serenity-led-dsa-full-migration-tracker.md
3. tasks/todo.md
4. tasks/lessons.md

当前方向：
- serenity-alpha-lab 仍然是主体项目、产品壳和未来运行时。
- daily_stock_analysis 是完整功能迁移来源，不是主体运行时。
- 目标是把 DSA 的 CLI、API/Web、市场数据、分析流水线、搜索新闻、Agent、策略、报告、历史、组合、回测、提醒、通知、Bot/Desktop/Docker/CI 等能力迁移进 Serenity。
- 迁移后必须兼容 Serenity 的投资思想：evidence-first、provenance、readiness、source coverage、skeptical review、report safety、research-only guardrails。

仓库：
- Serenity 仓库路径：/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
- DSA 源仓库路径：/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
- Serenity 当前 HEAD：Phase 3 commit 完成后以 `git rev-parse --short HEAD` 为准；Phase 2 handoff docs commit 为 cb0e2b5，Phase 2 implementation commit 为 8686d80，Phase 1 commit 为 d7187ca，Phase 0 baseline commit 为 b9b0fcb。
- DSA 当前 HEAD：95a4b51

已完成：
- Phase 0: Migration Baseline And Contract 已完成并提交。
- Phase 1: Serenity App Runtime Foundation 已完成并提交。
- Phase 2: Market Data Provider Migration 已完成并提交。
- Phase 3: Stock Analysis Pipeline Migration 已完成并准备提交。
- Phase 3 新增 Serenity-owned analysis runtime：
  - src/serenity_alpha_lab/analysis/__init__.py
  - src/serenity_alpha_lab/analysis/context.py
  - src/serenity_alpha_lab/analysis/pipeline.py
- Phase 3 更新 market data runtime：
  - src/serenity_alpha_lab/market_data/manager.py 增加 `get_daily_bars()`。
- Phase 3 tests：
  - tests/test_analysis_pipeline.py
  - tests/test_market_data.py 增加 daily-bar manager regression。
- Phase 3 覆盖：
  - DSA-style analysis context builder source reference
  - normalized quote/daily-bar to Serenity evidence conversion
  - stable market-data provenance IDs and `serenity://market-data/...` URLs
  - source coverage metadata
  - readiness gate and report gate
  - research-only score/rating/confidence/gap signals
  - provider fail-open behavior
  - no DSA trading-field leakage
- Phase 3 tests 使用 in-process stubs，不依赖 live credentials、外部网络、provider SDK 或 DSA runtime import。

当前验证证据：
- Red check: `python3 -m pytest tests/test_analysis_pipeline.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.analysis'`.
- Target green: `python3 -m pytest tests/test_analysis_pipeline.py -q` -> 3 passed.
- Focused regression: `python3 -m pytest tests/test_analysis_pipeline.py tests/test_market_data.py -q` -> 11 passed.
- Boundary regression: `python3 -m pytest tests/test_analysis_pipeline.py tests/test_market_data.py tests/test_dsa_migration_boundaries.py -q` -> 14 passed, 2 warnings.
- Target py_compile passed.
- Runtime static import scan 无 DSA checkout import 命中。
- Live dependency/cache scan 无真实 provider/network/cache 命中。
- `git diff --check` passed.
- Full verification: `make verify` -> 184 passed, 2 warnings；doctor ok；run-cpo-pack ok（182 evidence items, 6 ready memos, 0 skipped）；coverage matrix ok。

未完成 / 下一步：
- Phase 4: Report And Safety Integration 尚未开始。
- 先在 tasks/todo.md 写 Phase 4 可勾选计划。
- 然后迁移 DSA report templates into Serenity report generation。
- 为每个关键 claim 附 provenance refs。
- 为生成报告加入 report safety scans，禁止 unsupported recommendation language。
- 用 stubbed stock analysis 生成 Markdown 和 UI-visible report，无网络端到端验证。

注意：
- 不要修改、stage、提交或回滚 Serenity 既有 generated UI 输出：
  - output/ui/analyses/manifest.json
  - output/ui/reports/deliverable-research-report.md
  - output/ui/runs.json
  - output/ui/analyses/topic-2bde5fabbc/
- 当前工作树中这些 `output/ui/*` 仍显示为本地脏文件/目录，视为受保护外部状态；提交时必须显式排除。
- 不要在 Serenity runtime 中从 DSA checkout 做跨仓库 import。
- 不要复制 DSA .venv、node_modules、__pycache__、SQLite runtime DB 或生成缓存。
- 每个阶段性任务开始前，先在 tasks/todo.md 写可勾选计划。
- 每个阶段性任务完成后，自动更新 tracker、tasks/todo.md、tasks/lessons.md 和 restart prompt，提供新的可复制启动提示词，并只暂存/提交本阶段拥有的文件；不要暂存受保护的 output/ui/*。
```
