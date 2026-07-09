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
| Lessons correction | Completed | `tasks/lessons.md` now records Serenity-led DSA migration as the governing rule |
| Task checklist correction | Completed | `tasks/todo.md` now starts `Serenity-Led Full DSA Migration Reset` |

### Repository State

| Repository | Role | Current Notes |
| --- | --- | --- |
| `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` | Primary project and target runtime | Use `git rev-parse --short HEAD` for current HEAD; Phase 0 baseline commit is `b9b0fcb`; Phase 1 commit is `d7187ca`; protected generated UI dirt under `output/ui/*` remains untouched and must stay unstaged |
| `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` | Source system to migrate from | Current HEAD `95a4b51`; local `.venv` now has core dependencies except optional `alphasift` Git dependency |

### Completed Migration Work

| Phase | Status | Evidence |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Serenity commit `b9b0fcb`; `docs/serenity-led-dsa-source-inventory.md`; `tests/test_dsa_migration_boundaries.py`; `make verify` passed |
| Phase 1: Serenity App Runtime Foundation | Completed | Serenity commit `d7187ca`; adds `src/serenity_alpha_lab/app/*`, CLI `serve-app`, and `tests/test_app_api.py`; `make verify` passed with 173 passed |

Previous DSA-first integration work is useful source research but is no longer the governing product direction.

### Next Phase

| Phase | Status | Scope |
| --- | --- | --- |
| Phase 2: Market Data Provider Migration | Next | Port DSA provider contracts into Serenity-owned `market_data` modules with stubbed tests and default-off credentials |

### Phase Completion Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Baseline/inventory/guardrails committed in `b9b0fcb` |
| Phase 1: Serenity App Runtime Foundation | Completed | Commit `d7187ca`; app config/API skeleton/CLI wiring implemented; targeted tests, boundary scan, static import scan, and full `make verify` passed |
| Phase 2: Market Data Provider Migration | Not Started | Next phase after Phase 1 verification commit |
| Phase 3: Stock Analysis Pipeline Migration | Not Started | Awaiting Phase 2 |
| Phase 4: Report And Safety Integration | Not Started | Awaiting Phase 3 |
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
| Phase commit habit | Completed | Task log and lessons now require committing every verified phase-level task with protected generated UI outputs excluded |
| Phase 0 commit | Completed | Serenity commit `b9b0fcb` (`docs: 完成 Serenity 主导的 DSA 迁移 Phase 0 基线`) |

## Next Task

Start Phase 2:

1. Add Serenity-owned market-data provider contracts under `src/serenity_alpha_lab/market_data/*`.
2. Migrate DSA provider normalization and stock-code routing into Serenity-owned modules.
3. Add stubbed provider tests with no live credentials or external network dependency.

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
- Serenity 当前 HEAD：以 `git rev-parse --short HEAD` 为准；Phase 1 commit 为 d7187ca，Phase 0 baseline commit 为 b9b0fcb。
- DSA 当前 HEAD：95a4b51

当前状态：
- Phase 0: Migration Baseline And Contract 已完成并提交。
- Phase 0 commit：b9b0fcb（`docs: 完成 Serenity 主导的 DSA 迁移 Phase 0 基线`）。
- 最新状态文档：本 tracker 已刷新到 Phase 1 completed / Phase 2 next；若需要精确 commit，以 `git rev-parse --short HEAD` 为准。
- Phase 1: Serenity App Runtime Foundation 已完成并提交，commit 为 d7187ca（`feat: 完成 Serenity App Runtime Foundation`）。
- Phase 1 已添加 Serenity-owned app runtime：`src/serenity_alpha_lab/app/config.py`、`src/serenity_alpha_lab/app/local_api.py`、`src/serenity_alpha_lab/app/__init__.py`。
- Phase 1 API skeleton endpoints：`GET /health`、`GET /version`、`GET /run-state`；默认 research-only、无市场数据凭据也可启动；`/run-state` 兼容现有 `{ "runs": [...] }` 和旧 top-level list 两种 JSON 形状。
- Phase 1 CLI：新增 `serenity-alpha-lab serve-app`，不触发 `build_dashboard`，并保留 `build-ui` / `serve-ui` 静态 dashboard 命令。
- Phase 1 tests：`tests/test_app_api.py` 与 `tests/test_cli.py::test_cli_serve_app_invokes_serenity_api_without_building_static_dashboard` 覆盖无凭据启动、health/version/run-state、CLI wiring、静态 UI 不被 rebuild。
- 当前 targeted 验证证据：`python3 -m pytest tests/test_app_api.py tests/test_cli.py tests/test_dsa_migration_boundaries.py -q` -> 36 passed, 2 warnings；`git diff --check` passed；`rg -n "daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" src/serenity_alpha_lab` 无命中。
- 当前 full verification 证据：`make verify` -> 173 passed, 2 warnings；doctor ok；run-cpo-pack ok（182 combined evidence items, 6 ready memos, 0 skipped）；coverage matrix ok。
- 下一步从 Phase 2: Market Data Provider Migration 开始。

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
- 每个阶段性任务完成后，更新 tracker、tasks/todo.md、tasks/lessons.md 和 restart prompt，提供新的可复制启动提示词，并只暂存/提交本阶段拥有的文件；不要暂存受保护的 `output/ui/*`。
```
