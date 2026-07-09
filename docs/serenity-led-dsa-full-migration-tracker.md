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
| Task checklist correction | Completed | `tasks/todo.md` tracks Serenity-led migration phases and current Phase 4 closeout |

### Repository State

| Repository | Role | Current Notes |
| --- | --- | --- |
| `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` | Primary project and target runtime | Current HEAD is `1c2eddf` (`docs: 记录 Phase 6 研究验证与监控迁移交接`); Phase 6 implementation and handoff docs are complete and committed; protected generated UI dirt under `output/ui/*` remains untouched and must stay unstaged |
| `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` | Source system to migrate from | Current HEAD `95a4b51`; source reference only, not a Serenity runtime dependency |

### Completed Migration Work

| Phase | Status | Evidence |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Serenity commit `b9b0fcb`; `docs/serenity-led-dsa-source-inventory.md`; `tests/test_dsa_migration_boundaries.py`; `make verify` passed |
| Phase 1: Serenity App Runtime Foundation | Completed | Serenity commit `d7187ca`; adds `src/serenity_alpha_lab/app/*`, CLI `serve-app`, and `tests/test_app_api.py`; `make verify` passed with 173 passed |
| Phase 2: Market Data Provider Migration | Completed | Serenity implementation commit `8686d80`; handoff docs commit `cb0e2b5`; adds `src/serenity_alpha_lab/market_data/*` and `tests/test_market_data.py`; `make verify` passed with 180 tests |
| Phase 3: Stock Analysis Pipeline Migration | Completed | Commit `3cf14b3`; adds Serenity-owned `src/serenity_alpha_lab/analysis/*`, market-data daily-bar manager path, and `tests/test_analysis_pipeline.py`; focused regression passed with `14 passed, 2 warnings`; full `make verify` passed with 184 tests |
| Phase 4: Report And Safety Integration | Completed | Commit `3253f13`; adds `src/serenity_alpha_lab/analysis/report.py`, report safety text scanning, CLI `analyze-stock --stub`, and `tests/test_analysis_report.py`; targeted regression passed with `14 passed, 2 warnings`; full `make verify` passed with 189 tests |
| Phase 5 Web Workbench Migration | Completed | Commit `f8e87d0`; Serenity-owned `apps/serenity-web` Vite/React workbench scaffolded with Home, Analysis, History, Settings, Phase 4 report semantics panels, Vitest semantics coverage, and Playwright smoke |
| Phase 6 Portfolio, Backtest, Alerts, Notifications | Completed | Implementation commit `639e255`; handoff docs commit `1c2eddf`; adds Serenity-owned `research_validation.py`, `research_monitors.py`, no-secret/default-off API health diagnostics, and focused tests; `make verify` passed with 194 tests |

Previous DSA-first integration work is useful source research but is no longer the governing product direction.

### Next Phase

| Phase | Status | Scope |
| --- | --- | --- |
| Phase 5: Web Workbench Migration | Completed | Commit `f8e87d0`; Serenity-owned `apps/serenity-web` workbench now covers Home, Analysis, History, Settings, report-reader flow, Phase 4 report semantics panels, Vitest, and Playwright smoke |

### Phase Completion Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0: Migration Baseline And Contract | Completed | Baseline/inventory/guardrails committed in `b9b0fcb` |
| Phase 1: Serenity App Runtime Foundation | Completed | Commit `d7187ca`; app config/API skeleton/CLI wiring implemented; targeted tests, boundary scan, static import scan, and full `make verify` passed |
| Phase 2: Market Data Provider Migration | Completed | Commit `8686d80`; provider contracts, quote/bar normalization, stock-code routing, fallback diagnostics, and stubbed tests implemented; full verification passed |
| Phase 3: Stock Analysis Pipeline Migration | Completed | Commit `3cf14b3`; Serenity-owned context builder and core pipeline convert normalized market data into evidence items, readiness-gated research signals, diagnostics, and report-gate status |
| Phase 4: Report And Safety Integration | Completed | Serenity-owned stock-analysis report generator renders DSA-derived research-only sections, key-claim provenance refs, safety-scanned Markdown, manifest, and UI-visible artifact from stubbed analysis |
| Phase 5: Web Workbench Migration | Completed | Commit `f8e87d0`; incrementally recreated under `apps/serenity-web`; no wholesale DSA React import, no DSA runtime imports, and no copied DSA generated caches |
| Phase 6: Portfolio, Backtest, Alerts, Notifications | Completed | Commit `639e255`; portfolio/backtest migrated as research validation; alerts/notifications migrated as default-off research monitors and handoff records; no trading automation |
| Phase 7: Agent, Bot, Desktop, Docker, CI | Not Started | Next phase |

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

## Development Status Summary

### Completed

- Phase 0: Migration Baseline And Contract — complete and committed in `b9b0fcb`.
- Phase 1: Serenity App Runtime Foundation — complete and committed in `d7187ca`.
- Phase 2: Market Data Provider Migration — implementation committed in `8686d80`; handoff docs committed in `cb0e2b5`.
- Phase 3: Stock Analysis Pipeline Migration — implementation committed in `3cf14b3`; handoff docs committed in `5718928`.
- Phase 4: Report And Safety Integration — implementation committed in `3253f13`; handoff docs committed in current HEAD.
- Phase 5 Web Workbench Migration — complete and committed in `f8e87d0`.

### Not Started / Pending

- Phase 6: Portfolio, Backtest, Alerts, Notifications — complete and committed in `639e255`.
- Phase 7: Agent, Bot, Desktop, Docker, CI — next active migration phase.

### Current Branch And Protected State

- Current branch: `codex/phase-4-report-safety`.
- Current HEAD: `1c2eddf` (`docs: 记录 Phase 6 研究验证与监控迁移交接`); verify with `git log -1 --oneline`.
- Current owned migration docs are up to date for Phase 6; only protected generated UI artifacts should remain dirty.
- Protected generated UI artifacts remain intentionally dirty and must not be staged, committed, reverted, or overwritten unless explicitly requested:
  - `output/ui/analyses/manifest.json`
  - `output/ui/reports/deliverable-research-report.md`
  - `output/ui/runs.json`
  - `output/ui/analyses/topic-2bde5fabbc/`

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
| Phase 3 commit | Completed | Serenity commit `3cf14b3` (`feat: 完成 Serenity 股票分析流水线迁移`) |


## Completed Phase 4 Report And Safety Integration

| Item | Status | Evidence |
| --- | --- | --- |
| DSA report template migration | Completed | `src/serenity_alpha_lab/analysis/report.py` adapts DSA sections into Serenity-owned `Intelligence Brief`, `Data View`, `Research Readiness Guardrails`, `Signal Attribution`, `Historical Comparison`, `Key Claims And Provenance`, and `Research Boundary` sections |
| Key-claim provenance refs | Completed | Report key claims include stable `claim:{symbol}:...` IDs plus `serenity:market-data:...` evidence IDs and `serenity://market-data/...` source URLs; missing refs emit explicit `missing-provenance:*` diagnostics |
| Report safety integration | Completed | `scan_report_text()` now scans generated Markdown before artifact writes and returns every forbidden phrase per line; unsupported recommendation language raises `ReportSafetyViolation` before output is written |
| Stubbed no-network report path | Completed | CLI `analyze-stock --stub` runs deterministic in-process market data through `StockAnalysisPipeline` and writes `reports/stock-analysis-report.md`, `analysis-report-manifest.json`, and `index.html` under caller-selected output directories |
| UI-visible report artifact | Completed | `write_stock_analysis_report_artifacts()` emits a small static `index.html` with `data-report-href="reports/stock-analysis-report.md"` without touching protected `output/ui/*` |
| Focused verification | Completed | Red checks first failed on missing `serenity_alpha_lab.analysis.report`, then missing UI/CLI integration; final focused checks `python3 -m pytest tests/test_analysis_report.py tests/test_cli.py::test_cli_analyze_stock_stub_writes_report_artifacts -q` -> `5 passed` |
| Regression verification | Completed | `python3 -m pytest tests/test_analysis_report.py tests/test_report_safety.py tests/test_analysis_pipeline.py tests/test_dsa_migration_boundaries.py tests/test_cli.py::test_cli_analyze_stock_stub_writes_report_artifacts -q` -> `14 passed, 2 warnings` |
| Static/full verification | Completed | `py_compile` passed for Phase 4 modules/tests; runtime DSA checkout import scan returned no matches; safety phrase scan matched only scanner constants and intentional tests; `git diff --check` passed; `make verify` -> `189 passed, 2 warnings`, doctor ok, run-cpo-pack ok, coverage matrix ok |

## Completed Phase 5 Web Workbench Migration

| Item | Status | Evidence |
| --- | --- | --- |
| Serenity-owned frontend toolchain | Completed | Added `apps/serenity-web` with Vite, React, TypeScript, Vitest, Playwright, `package.json`, `package-lock.json`, and local config files; generated install/build/test artifacts are ignored and not tracked |
| Core product shell and routes | Completed | `src/App.tsx` and `src/routes.ts` expose only Home, Analysis, History, and Settings for Phase 5; route tests reject early chat, portfolio, backtest, alerts, DSA branding, and source-app route drift |
| Report artifact UI semantics | Completed | `ReportSemanticsPanel` and `ReportReader` render fixture-backed readiness, provenance, source coverage, skeptical review, report safety, Markdown href, manifest href, and research-only boundary semantics |
| Phase 5 pages | Completed | Home summarizes workflow state, Analysis renders report semantics and opens the report reader, History shows local report package metadata, and Settings documents default-off local/runtime guardrails |
| Vitest semantics coverage | Completed | `apps/serenity-web/src/components/ReportSemantics.test.tsx` covers readiness, provenance refs, source coverage, skeptical review, safety boundary, and forbidden trading-language absence; `src/routes.test.ts` covers exact Phase 5 routes |
| Playwright smoke coverage | Completed | `apps/serenity-web/e2e/app-shell.spec.ts` covers shell navigation across Home, Analysis, History, Settings plus the report-reader flow and `data-report-href` Markdown handoff |
| Focused frontend verification | Completed | `npm run build` -> exit 0; `npm test -- --run` -> 2 files, 4 tests passed; `npm run test:smoke -- --reporter=line` -> 1 msedge smoke passed |
| Migration guard verification | Completed | `python3 -m pytest tests/test_dsa_migration_boundaries.py -q` -> 3 passed, 2 warnings; static scan for external DSA checkout/import/path returned no matches under `src/serenity_alpha_lab apps/serenity-web` |
| Full verification | Completed | `make verify` -> 189 passed, 2 warnings; doctor ok; run-cpo-pack ok; coverage matrix ok |
| Protected output hygiene | Completed | `git status --short output/ui` still shows only pre-existing protected generated output dirt; Phase 5 did not stage, commit, revert, or overwrite protected `output/ui/*` artifacts |

## Completed Phase 6 Portfolio, Backtest, Alerts, Notifications

| Item | Status | Evidence |
| --- | --- | --- |
| Phase 6 implementation plan | Completed | `docs/superpowers/plans/2026-07-09-serenity-alpha-lab-phase-6-research-validation-monitors.md` records the TDD tasks, file boundaries, and research-only/default-off monitor scope |
| Portfolio research validation | Completed | `src/serenity_alpha_lab/research_validation.py` adds `PortfolioObservation` and `PortfolioResearchSnapshot` as research-only validation artifacts with evidence IDs and automation disabled diagnostics |
| Historical backtest validation | Completed | `BacktestObservation` and `BacktestValidationSummary` summarize historical validation evidence, positive/negative counts, average return, evidence IDs, and `historical_validation_only` diagnostics without future-performance promises |
| Default-off research monitors | Completed | `src/serenity_alpha_lab/research_monitors.py` adds `ResearchMonitorRule`, dry-run evaluations, handoff records, and notification dispatch plans that are disabled unless explicitly enabled and configured |
| No-secret API startup diagnostics | Completed | `AppRuntimeConfig` and `/health` payload now expose research monitor enablement, notification enablement, delivery status, and configured channel count without secret/token/password values |
| Red/green TDD evidence | Completed | New Phase 6 tests first failed on missing modules; API health test failed with missing `research_monitors`; after implementation `tests/test_research_validation.py tests/test_research_monitors.py` -> `4 passed`, and targeted API health -> `1 passed` |
| Focused regression | Completed | `python3 -m pytest tests/test_research_validation.py tests/test_research_monitors.py tests/test_app_api.py tests/test_dsa_migration_boundaries.py -q` -> `12 passed, 2 warnings` |
| Boundary and safety scans | Completed | Runtime DSA scan under `src/serenity_alpha_lab` returned no matches; Phase 6 safety scan matched only absence assertions in tests; `git diff --check` passed |
| Full verification | Completed | `make verify` -> `194 passed, 2 warnings`; doctor ok; run-cpo-pack ok; coverage matrix ok |
| Protected output hygiene | Completed | `git status --short output/ui` still shows only pre-existing protected generated output dirt; Phase 6 did not stage, commit, revert, or overwrite protected `output/ui/*` artifacts |

## Next Task

Start Phase 7: Agent, Bot, Desktop, Docker, CI.

1. Begin Phase 7 by planning Agent, Bot, Desktop, Docker, and CI migration boundaries.
2. Preserve Serenity evidence-first provenance, readiness, source coverage, skeptical review, report safety, and research-only guardrails.
3. Keep optional/bot/desktop/Docker integrations default-off until explicitly configured.
4. Continue excluding protected `output/ui/*` artifacts from staging and commits.

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
- 迁移后必须兼容 Serenity 的 evidence-first、provenance、readiness、source coverage、skeptical review、report safety、research-only guardrails。

仓库：
- Serenity 仓库路径：/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
- DSA 源仓库路径：/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
- 当前分支：codex/phase-4-report-safety
- Serenity 当前 HEAD：1c2eddf（docs: 记录 Phase 6 研究验证与监控迁移交接）；Phase 6 handoff docs commit 为 1c2eddf；Phase 6 implementation commit 为 639e255；Phase 5 handoff docs commit 为 5cf2f31；Phase 5 implementation commit 为 f8e87d0；Phase 5 planning docs commit 为 d0136e0；Phase 4 implementation commit 为 3253f13；Phase 3 handoff docs commit 为 5718928；Phase 3 implementation commit 为 3cf14b3；Phase 2 handoff docs commit 为 cb0e2b5；Phase 2 implementation commit 为 8686d80；Phase 1 commit 为 d7187ca；Phase 0 baseline commit 为 b9b0fcb。
- DSA 当前 HEAD：95a4b51

已完成：
- Phase 0: Migration Baseline And Contract 已完成并提交。
- Phase 1: Serenity App Runtime Foundation 已完成并提交。
- Phase 2: Market Data Provider Migration 已完成并提交。
- Phase 3: Stock Analysis Pipeline Migration 已完成并提交，commit 为 3cf14b3。
- Phase 4: Report And Safety Integration 已完成实现与验证，implementation commit 为 3253f13。
- Phase 5: Web Workbench Migration 已完成实现、验证并提交，implementation commit 为 f8e87d0。
- Phase 6: Portfolio, Backtest, Alerts, Notifications 已完成实现、验证并提交，implementation commit 为 639e255。
- Phase 6 新增/更新：
  - src/serenity_alpha_lab/research_validation.py：portfolio research snapshots and historical validation summaries。
  - src/serenity_alpha_lab/research_monitors.py：default-off research monitor rules, dry-run evaluations, dispatch plans, and handoff records。
  - src/serenity_alpha_lab/app/config.py、src/serenity_alpha_lab/app/local_api.py：no-secret/default-off research monitor health diagnostics。
  - tests/test_research_validation.py、tests/test_research_monitors.py、tests/test_app_api.py：Phase 6 TDD coverage。
  - docs/superpowers/plans/2026-07-09-serenity-alpha-lab-phase-6-research-validation-monitors.md：Phase 6 execution plan。

当前验证证据：
- Red validation check: `python3 -m pytest tests/test_research_validation.py tests/test_research_monitors.py -q` initially failed with missing `serenity_alpha_lab.research_validation` and `serenity_alpha_lab.research_monitors` modules.
- Green validation/monitor check: `python3 -m pytest tests/test_research_validation.py tests/test_research_monitors.py -q` -> 4 passed.
- Red API health check: `python3 -m pytest tests/test_app_api.py::test_health_payload_reports_research_monitors_default_off_without_secrets -q` failed with `KeyError: 'research_monitors'`.
- Green API health check: `python3 -m pytest tests/test_app_api.py::test_health_payload_reports_research_monitors_default_off_without_secrets -q` -> 1 passed.
- Focused regression: `python3 -m pytest tests/test_research_validation.py tests/test_research_monitors.py tests/test_app_api.py tests/test_dsa_migration_boundaries.py -q` -> 12 passed, 2 warnings.
- Runtime static import/path scan for `daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` under `src/serenity_alpha_lab` returned no matches.
- Phase 6 safety scan matched only absence assertions in `tests/test_research_validation.py`; no production module matches.
- `git diff --check` passed.
- Protected output status: `git status --short output/ui` still shows only protected generated UI dirt.
- Full verification: `make verify` -> 194 passed, 2 warnings；doctor ok；run-cpo-pack ok（182 evidence items, 6 ready memos, 0 skipped）；coverage matrix ok。

未完成 / 下一步：
- 下一阶段：Phase 7 Agent, Bot, Desktop, Docker, CI。
- Phase 7 要把 DSA Agent/bot/desktop/docker/CI 能力迁移为 Serenity-owned、evidence-grounded、default-off/local-first 的运行与发布能力，不做交易自动化。

注意：
- 不要修改、stage、提交或回滚 Serenity 既有 generated UI 输出：
  - output/ui/analyses/manifest.json
  - output/ui/reports/deliverable-research-report.md
  - output/ui/runs.json
  - output/ui/analyses/topic-2bde5fabbc/
- 当前工作树中这些 `output/ui/*` 仍显示为本地脏文件/目录，视为受保护外部状态；提交时必须显式排除。
- 不要在 Serenity runtime 中从 DSA checkout 做跨仓库 import。
- 不要复制 DSA .venv、node_modules、__pycache__、SQLite runtime DB 或生成缓存；Phase 5 前端本地 `node_modules/dist/test-results/playwright-report` 也必须保持未追踪、提交前清理。
- 每个阶段性任务开始前，先在 tasks/todo.md 写可勾选计划。
- 每个阶段性任务完成后，自动更新 tracker、tasks/todo.md、tasks/lessons.md 和 restart prompt，提供新的可复制启动提示词，并只暂存/提交本阶段拥有的文件；不要暂存受保护的 output/ui/*。用户已再次确认希望把这个习惯长期保留。
```
