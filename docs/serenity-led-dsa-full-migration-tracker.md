# Serenity-Led DSA Full Migration Tracker

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this tracker task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the migration of complete `daily_stock_analysis` capabilities into `serenity-alpha-lab`, with Serenity remaining the primary project, runtime, UX, and investment research philosophy.

**Architecture:** DSA is the source system. Serenity owns the migrated runtime and adapts DSA stock-analysis features into evidence-backed, provenance-aware, safety-scanned research workflows.

**Tech Stack:** Python 3.11+ / Serenity local-first research engine / migrated DSA provider and analysis modules / FastAPI / React + Vite / pytest / Vitest / Playwright.

---

## Current Status Snapshot

**Updated:** 2026-07-11

### Direction

| Item | Status | Evidence |
| --- | --- | --- |
| Serenity-led direction reset | Completed | User clarified that `serenity-alpha-lab` remains primary and DSA should be fully migrated into it |
| Old DSA-first direction | Superseded | `docs/dsa-first-serenity-core-development-plan.md` and tracker are historical and should not drive new implementation |
| Lessons correction | Completed | `tasks/lessons.md` records Serenity-led DSA migration as the governing rule |
| Task checklist correction | Completed | `tasks/todo.md` tracks Serenity-led migration phases, the completed Phase 7 checklist, and the approved post-migration runtime-parity design checkpoint |

### Repository State

| Repository | Role | Current Notes |
| --- | --- | --- |
| `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab` | Primary project and target runtime | Runtime-parity Tasks 1-4 are complete: canonical manifest `bc281f5`, pure read-only artifact repository `e276ce2`, read-only artifact API/config/CLI `f984174`, and strict frontend decoder/view model `4d95ec3`. The Web now validates the canonical summary field-by-field, preserves real coverage/safety/provenance semantics, rejects unsafe hrefs and recursive trading/broker/order fields, and uses test-only canonical fixtures. Task 5 injectable source/App lifecycle and later browser flow remain unstarted; protected generated UI dirt under `output/ui/*` remains untouched and unstaged |
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
| Phase 7 Agent, Bot, Desktop, Docker, CI | Completed | Implementation commit `f2fd7cd`; adds evidence-grounded Agent tools, platform-neutral default-off Bot, desktop readiness contract, no-secret health diagnostics, non-root Docker runtime, unified offline release gate, and PR/branch/tag CI; `make verify` passed with 221 tests |

Previous DSA-first integration work is useful source research but is no longer the governing product direction.

### Next Work

| Workstream | Status | Scope |
| --- | --- | --- |
| Post-migration runtime parity design boundary | Completed | Approved API-first latest stock-analysis artifact design committed in `948970b`; spec: `docs/superpowers/specs/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity-design.md` |
| Detailed runtime parity implementation plan | Completed | `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md` maps exact files, red failures, minimal implementations, focused/full verification, protected-file checks, and commit checkpoints |
| Canonical backend artifact/API integration for `apps/serenity-web` | In Progress | Tasks 1-4 are complete through strict decoder/view model commit `4d95ec3`; next add the injectable HTTP source and explicit loading/ready/unavailable/blocked App lifecycle, then complete remaining History/Vite/Playwright parity |
| Real Docker image build and no-secret container `/health` smoke | Environment Blocked | Static Docker rules and `docker compose config` passed, but `/Users/zq/.orbstack/run/docker.sock` was unavailable; rerun the unified gate without `--skip-docker-smoke` when a daemon is available |
| Electron/updater, live Bot adapters, LLM providers, notification delivery, broker/order actions, release publishing | Deferred | Do not start without a separate approved design, threat model, default-off controls, and explicit research-only acceptance criteria |

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
| Phase 7: Agent, Bot, Desktop, Docker, CI | Completed | Implementation commit `f2fd7cd`; research Agent/Bot contracts, desktop readiness, Docker, release gate, and unified CI are implemented and verified; no trading automation or external adapters |

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
- Phase 4: Report And Safety Integration — implementation committed in `3253f13`; later migration and runtime-parity status commits supersede its handoff HEAD.
- Phase 5 Web Workbench Migration — complete and committed in `f8e87d0`.
- Phase 6: Portfolio, Backtest, Alerts, Notifications — implementation committed in `639e255`; handoff docs committed in `1c2eddf`.
- Phase 7: Agent, Bot, Desktop, Docker, CI — implementation committed in `f2fd7cd`; handoff docs committed in `8bba5e0`.
- Post-migration runtime parity design — approved in `948970b`; design handoff committed in `14237a9`.
- Detailed runtime parity implementation planning — complete in `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md`.
- Runtime-parity Task 1 canonical manifest — complete and committed in `bc281f5` (`feat: 完善版本化股票分析工件清单`); Red failed on missing `generated_at`, Green passed, UTC injection hardening was added through an additional Red -> Green loop, and focused regression passed with `17 passed, 2 warnings`.
- Runtime-parity Task 2 pure artifact repository — complete and committed in `e276ce2` (`feat: 添加只读股票分析工件仓库`); initial collection Red failed on the missing module, review-driven Red loops covered deterministic classification, finite numeric checks, forbidden keys, fixed allowlists, provenance URL safety, exact paths, manifest/report symlink escape and loop handling, and stable exception sanitization. Final repository tests passed with `27 passed`; focused manifest/repository/DSA-boundary regression passed with `38 passed, 2 warnings`.
- Runtime-parity Task 3 read-only artifact API/config/CLI — complete and committed in `f984174` (`feat: 暴露只读最新股票分析工件 API`); initial Red produced `7 failed, 5 passed` for the missing config field, unknown CLI option, and generic artifact-route 404. Review-driven Red -> Green loops added exact summary/manifest distinctions, all-route error mapping, missing Markdown classification, generic 404 compatibility, and cross-platform local-path leakage rejection without rejecting valid HTTPS/Serenity URLs, IPv6 hosts, HTML closing tags, or allowlisted market symbols. Final focused tests passed with `69 passed`; backend parity passed with `115 passed, 2 warnings`.
- Runtime-parity Task 3 handoff documentation — complete and committed in `09094ef` (`docs: 记录 runtime parity Task 3 交接`); the tracker, task log, verification evidence, protected output state, and Task 4 restart instructions were synchronized after the implementation commit.
- Runtime-parity Task 4 strict frontend decoder/view model — complete and committed in `4d95ec3` (`feat: 添加严格股票分析工件解码器`); initial Red failed during collection because `canonicalReportArtifact.ts` did not exist. Review-driven Red -> Green loops covered camelCase forbidden keys, impossible calendar dates, legacy sample/panel compatibility, structured safety line numbers, nested array rejection, recursive unknown-field stripping, safe value text, exact API hrefs, provenance URL safety, and detached projections. Final focused tests passed with `67 passed`; full Vitest passed with `68 passed`; production build, `git diff --check`, fixture/runtime boundary, DSA path scan, and specification review passed, with the final quality-review test blind spot resolved in `2ad297a`.
- Runtime-parity Task 4 handoff documentation — complete and committed in `c61ef1b` (`docs: 记录 runtime parity Task 4 交接`); tracker, todo, reusable lesson, protected state, verification evidence, and the exact Task 5 source-test Red boundary were synchronized after the implementation commit.
- Runtime-parity Task 4 review hardening — complete and committed in `2ad297a` (`test: 收紧股票分析工件完整投影回归`); the valid decoder case now compares the entire `ReportArtifact` projection, and `ReportSemantics` locks Focus/External plus structured coverage message/recommendation rendering. Fresh focused `67 passed`, full Vitest `68 passed`, and production build passed.

### Unfinished, Blocked, And Deferred

- **Completed:** the API-first artifact boundary, detailed Red-Green-Refactor plan, Task 1 versioned canonical manifest, Task 2 pure allowlisted repository, Task 3 read-only API/config/CLI, and Task 4 strict frontend decoder/view model.
- **Not started:** Task 5 injectable HTTP source/App lifecycle, the remaining History/Vite/Playwright canonical-artifact flow, and full implementation verification.
- **Environment blocked:** Docker image build and no-secret container `/health` smoke because the Docker/OrbStack daemon socket is unavailable; Docker static rules and Compose parsing passed.
- **Deferred by design:** LLM runtime, live Bot adapters, notification delivery, Electron/updater/installer, broker actions, and release publishing until separately designed and approved.

### Current Branch And Protected State

- Current branch: `codex/phase-4-report-safety`.
- Phase 7 planning commit: `eddf32c` (`docs: 完成 Serenity Phase 7 研究运行与发布规划`).
- Phase 7 implementation commit: `f2fd7cd` (`feat: 完成 Serenity Phase 7 研究运行与发布能力迁移`).
- Phase 7 handoff documentation commit: `8bba5e0` (`docs: 记录 Phase 7 研究运行与发布迁移交接`).
- Phase 7 final completion status refresh commit: `6d1fcbb` (`docs: 刷新 Phase 7 完成状态`).
- Post-migration runtime parity design checkpoint commit: `948970b` (`docs: 固化 post-migration runtime parity 设计`).
- Post-migration runtime parity design handoff commit: `14237a9` (`docs: 记录 runtime parity 设计交接`).
- Post-migration runtime parity pre-planning status refresh: `0efe2bf` (`docs: 刷新 runtime parity 开发状态与启动提示`).
- Approved post-migration runtime parity design: `docs/superpowers/specs/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity-design.md`.
- Detailed post-migration runtime parity plan: `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md`.
- Post-migration runtime parity planning checkpoint commit: `ddff62b` (`docs: 完成 post-migration runtime parity 实施规划`).
- Post-migration runtime parity planning status refresh: `e864cf9` (`docs: 刷新 runtime parity 规划交接状态`).
- Runtime-parity Task 1 implementation commit: `bc281f5` (`feat: 完善版本化股票分析工件清单`).
- Runtime-parity Task 1 handoff commit: `eaacbbf` (`docs: 记录 runtime parity Task 1 交接`).
- Runtime-parity Task 2 implementation commit: `e276ce2` (`feat: 添加只读股票分析工件仓库`).
- Runtime-parity Task 3 implementation commit: `f984174` (`feat: 暴露只读最新股票分析工件 API`).
- Runtime-parity Task 3 handoff docs commit: `09094ef` (`docs: 记录 runtime parity Task 3 交接`).
- Runtime-parity Task 4 implementation commit: `4d95ec3` (`feat: 添加严格股票分析工件解码器`).
- Runtime-parity Task 4 handoff docs commit: `c61ef1b` (`docs: 记录 runtime parity Task 4 交接`).
- Runtime-parity Task 4 review-hardening commit: `2ad297a` (`test: 收紧股票分析工件完整投影回归`).
- Phase 7 handoff documentation is finalized; only protected generated UI artifacts should remain dirty before the next planned development slice.
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

## Phase 7 Planning Checkpoint

| Item | Status | Evidence |
| --- | --- | --- |
| Approved scope | Completed | User approved the safety-first minimum complete migration: Agent tools, platform-neutral Bot, desktop readiness, Docker, and CI; no LLM runtime, live Bot adapters, notifications, Electron, updater, installer, or release publishing |
| Design specification | Completed | `docs/superpowers/specs/2026-07-10-serenity-alpha-lab-phase-7-runtime-release-design.md` |
| Detailed TDD plan | Completed | `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-phase-7-agent-bot-runtime-release.md` |
| Planning commit | Completed | `eddf32c` (`docs: 完成 Serenity Phase 7 研究运行与发布规划`) |
| Agent boundary | Completed | Explicit caller context, default-off visibility, caller allowlist, no implicit I/O, readiness/evidence propagation, recursive trading-field rejection, sanitized failures |
| Bot boundary | Completed | Platform-neutral contracts and commands over Serenity analysis/Agent outputs; default-off with no platform SDK or outbound delivery |
| Desktop decision | Completed | Add loopback runtime/readiness contract only; defer Electron and auto-update until backend artifact/API parity and separate threat-model gates |
| Docker/CI decision | Completed | Non-root no-secret API/Web container plus one machine-readable release gate for Python/frontend/browser/Docker checks across PR/branch/tag workflows |
| Protected output hygiene | Completed | Planning did not intentionally modify, stage, overwrite, copy, or revert protected `output/ui/*` artifacts |
| Implementation status | Completed | Implementation committed in `f2fd7cd`; focused Phase 7 regression, hardening regression, `make verify`, frontend checks, and the unified offline release gate passed with Docker real smoke explicitly blocked by environment |

## Completed Phase 7 Agent, Bot, Desktop, Docker, CI

| Item | Status | Evidence |
| --- | --- | --- |
| Evidence-grounded Agent tools | Completed | `src/serenity_alpha_lab/agents/*` adds frozen contracts, default-off registration, caller allowlists, explicit analysis context, deterministic summary/gap tools, recursive forbidden-field scans, JSON-safe results, fail-closed readiness states, and sanitized `failed_open` diagnostics |
| Platform-neutral research Bot | Completed | `src/serenity_alpha_lab/bot/*` adds normalized messages/responses, explicit command aliases, monotonic sliding-window limits, injected analysis service reuse, Agent-tool reuse, report-safety scanning, sanitized errors, and no platform SDK or outbound delivery |
| Runtime health and desktop readiness | Completed | `AppRuntimeConfig` and `/health` expose non-secret Agent/Bot/Desktop capability status; `desktop_runtime.py` records loopback-only local Web/API commands, deferred packaging, disabled updates, unbundled credentials, and parity requirements |
| Offline release gate | Completed | `release_gate.py` and `scripts/verify_offline_release.py` provide machine-readable `passed`/`blocked`/`skipped` results with reasons, explicit browser/Docker skip controls, bounded path-sanitized output, default-off integration environment, and nonzero blocked exit status |
| Docker runtime | Completed | `.dockerignore`, `docker/Dockerfile`, and `docker/docker-compose.yml` define a multi-stage web build, Python 3.11 non-root API/Web runtime, standard-library `/health` check, no-secret/default-off environment, and protected output/cache exclusions |
| Unified CI | Completed | `.github/workflows/verify.yml` uses Python 3.11, Node 20, Chromium, and the same offline release gate for pull requests, branch pushes, and tag pushes; local Playwright remains on installed Edge |
| Red/green TDD | Completed | Agent, Bot, Desktop/API, release/Docker, and workflow tests each failed before their implementation; final focused Phase 7 regression passed with `39 passed, 2 warnings`, followed by hardening regression `24 passed` |
| Full backend verification | Completed | Fresh `make verify` -> `221 passed, 2 warnings`; doctor ok; `run-cpo-pack` -> 182 evidence items, 6 ready memos, 0 skipped; coverage matrix ok |
| Unified release verification | Completed | `PYTHONPATH=src python3 scripts/verify_offline_release.py --skip-docker-smoke` -> `passed`, 9 checks passed, browser smoke passed on local Edge, Docker static passed, Docker smoke explicitly skipped |
| Docker environment limitation | Recorded | `docker info` failed because `/Users/zq/.orbstack/run/docker.sock` was unavailable; no Docker build or container health claim is made |
| Boundary and safety scans | Completed | No external DSA checkout path or DSA import under runtime/scripts/Docker/web/workflow surfaces; one intentional `daily_stock_analysis` match enforces `.dockerignore`; trading vocabulary matches only Agent forbidden-field constants; `git diff --check` passed |
| Protected output hygiene | Completed | `git status --short output/ui` remains the same four pre-existing protected entries; implementation commit `f2fd7cd` explicitly excluded them |

## Post-Migration Runtime Parity Planning Checkpoint

| Item | Status | Evidence |
| --- | --- | --- |
| Written-spec review | Completed | Approved design re-read against the migration tracker, current backend, current Web fixture path, release boundaries, and protected state |
| Detailed implementation plan | Completed | `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md` |
| Planning checkpoint commit | Completed | `ddff62b` (`docs: 完成 post-migration runtime parity 实施规划`) |
| Planning status refresh | Completed | `e864cf9` (`docs: 刷新 runtime parity 规划交接状态`) |
| Task 3 handoff documentation | Completed | `09094ef` (`docs: 记录 runtime parity Task 3 交接`) records the final backend API evidence and exact Task 4 restart boundary |
| Task 4 strict frontend decoder/view model | Completed | `4d95ec3` adds the production decoder/view model and `2ad297a` locks the complete projected object plus all currently rendered canonical coverage/finding fields |
| Task 4 handoff documentation | Completed | `c61ef1b` (`docs: 记录 runtime parity Task 4 交接`) records the final decoder evidence, scope correction, protected state, reusable lesson, and exact Task 5 restart boundary |
| Backend task mapping | Completed | Manifest, pure repository, latest summary, validated manifest, Markdown endpoint, config, CLI, 404/409/422, path safety, provenance, and leakage tests are mapped to Red -> Green -> Refactor tasks |
| Frontend task mapping | Completed | Strict decoder, real coverage counts, structured findings, injectable source, loading/ready/unavailable/blocked states, retry/abort behavior, fixture removal, Vite proxy, and non-AAPL Playwright interception are mapped |
| Planning baseline | Completed | Pre-implementation evidence remains `40 passed` for focused Python tests and `2 files / 4 tests passed` for Vitest; these are baselines, not runtime-parity implementation evidence |
| Production implementation | In Progress | Tasks 1-4 are complete through decoder/view model commit `4d95ec3`; Task 5 injectable source/App lifecycle, remaining History/Vite/Playwright flow, and full verification remain Not Started |
| Docker real smoke | Environment Blocked | `/Users/zq/.orbstack/run/docker.sock` remains unavailable; no image-build or container-health claim is made |
| External runtime capabilities | Deferred | History aggregation, `/run-state` redesign, static Web hosting, Electron/updater, live Bot/LLM/provider adapters, notification delivery, broker/order actions, and release publishing remain outside this slice |

Planning self-review confirms the plan covers every approved design requirement, contains exact file paths and commands, names intended red failures, uses stable DTO/error contracts, preserves actual coverage data, and contains no undefined implementation placeholder.

## Next Task

Begin Task 5 of `docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md`.

1. Create `apps/serenity-web/src/artifacts/reportArtifactSource.test.ts`.
2. Test the relative `/api/artifacts/stock-analysis/latest` request, `AbortSignal`, stable 404/409/422 classification, invalid JSON, decoder failures, network `TypeError`, and `AbortError`.
3. Run `npm --prefix apps/serenity-web test -- src/artifacts/reportArtifactSource.test.ts`.
4. Confirm Red because `reportArtifactSource.ts` does not exist.
5. Implement only `ReportArtifactSource`, `ReportArtifactLoadError`, sanitized error-envelope parsing, and production HTTP loading through `decodeCanonicalReportArtifact`.
6. Then add `App.test.tsx` Red coverage for loading/ready/unavailable/blocked/retry/abort/stale responses before modifying `App.tsx`.
7. Do not start History, Vite proxy, Playwright, static hosting, CORS, or any mutation/trading automation in Task 5.

## Copyable Restart Prompt

```text
请继续在 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab 当前进度上开发。

开始前首先运行：
- git status --short
- git log -5 --oneline --decorate

先阅读并遵守：
1. docs/serenity-led-dsa-full-migration-plan.md
2. docs/serenity-led-dsa-full-migration-tracker.md
3. docs/superpowers/specs/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity-design.md
4. docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md
5. tasks/todo.md
6. tasks/lessons.md
7. 仓库根目录 AGENTS.md（如果存在）

当前方向：
- serenity-alpha-lab 仍然是主体项目、产品壳和未来运行时。
- daily_stock_analysis 是完整功能迁移来源，不是主体运行时。
- Phase 0-7 已完成；后续属于 post-migration runtime parity / release hardening，不做交易自动化。
- 所有后续改动继续兼容 evidence-first、provenance、readiness、source coverage、skeptical review、report safety、research-only guardrails。

仓库：
- Serenity：/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
- DSA source：/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
- 当前分支：codex/phase-4-report-safety
- 最新 runtime parity implementation commit：4d95ec3（feat: 添加严格股票分析工件解码器）。
- 最新已记录 handoff docs commit：c61ef1b（docs: 记录 runtime parity Task 4 交接）；本次状态刷新提交后的实际 HEAD 仍须在启动时通过 git log -5 --oneline --decorate 核对。
- Phase 7 implementation commit：f2fd7cd（feat: 完成 Serenity Phase 7 研究运行与发布能力迁移）
- Phase 7 handoff docs commit：8bba5e0（docs: 记录 Phase 7 研究运行与发布迁移交接）
- Phase 7 final status refresh commit：6d1fcbb（docs: 刷新 Phase 7 完成状态）
- Phase 7 planning commit：eddf32c
- Post-migration runtime parity design checkpoint commit：948970b（docs: 固化 post-migration runtime parity 设计）
- Post-migration runtime parity design handoff commit：14237a9（docs: 记录 runtime parity 设计交接）
- Post-migration runtime parity approved design：docs/superpowers/specs/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity-design.md
- Post-migration runtime parity implementation plan：docs/superpowers/plans/2026-07-10-serenity-alpha-lab-post-migration-runtime-parity.md
- Post-migration runtime parity planning checkpoint commit：ddff62b（docs: 完成 post-migration runtime parity 实施规划）
- Post-migration runtime parity planning status refresh：e864cf9（docs: 刷新 runtime parity 规划交接状态）
- Post-migration runtime parity Task 1 implementation commit：bc281f5（feat: 完善版本化股票分析工件清单）
- Post-migration runtime parity Task 1 handoff commit：eaacbbf（docs: 记录 runtime parity Task 1 交接）
- Post-migration runtime parity Task 2 implementation commit：e276ce2（feat: 添加只读股票分析工件仓库）
- Post-migration runtime parity Task 3 implementation commit：f984174（feat: 暴露只读最新股票分析工件 API）
- Post-migration runtime parity Task 3 handoff docs commit：09094ef（docs: 记录 runtime parity Task 3 交接）
- Post-migration runtime parity Task 4 implementation commit：4d95ec3（feat: 添加严格股票分析工件解码器）
- Post-migration runtime parity Task 4 handoff docs commit：c61ef1b（docs: 记录 runtime parity Task 4 交接）
- Post-migration runtime parity Task 4 review-hardening commit：2ad297a（test: 收紧股票分析工件完整投影回归）
- DSA 当前 HEAD：95a4b51

Phase 7 已完成：
- src/serenity_alpha_lab/agents/*：explicit-context、allowlisted、default-off、evidence-grounded research tools；递归阻断 trading/broker/order 字段；未知 readiness fail-closed；异常仅暴露 error_type。
- src/serenity_alpha_lab/bot/*：platform-neutral status/analyze/evidence-gaps commands；default-off；注入分析服务；monotonic rate limit；Agent 输出复用；report safety 二次扫描；无平台 SDK 或外发。
- src/serenity_alpha_lab/desktop_runtime.py：loopback-only local Web/API plan；Electron/updater/installer deferred；credentials not bundled。
- src/serenity_alpha_lab/app/config.py、local_api.py：no-secret Agent/Bot/Desktop health diagnostics。
- src/serenity_alpha_lab/release_gate.py、scripts/verify_offline_release.py：machine-readable offline gate，required failures block，browser/Docker 只能由调用方显式 skip，结果始终带 reason 并净化 repo 绝对路径。
- .dockerignore、docker/Dockerfile、docker/docker-compose.yml：Node build + Python 3.11 non-root API/Web runtime；外部能力 default-off；不复制 output/ui、DSA checkout、DB、node_modules 或缓存。
- .github/workflows/verify.yml：PR、branch、tag 共用 Python 3.11 + Node 20 + Chromium + unified gate；本机 Playwright 使用 Edge。

最终验证：
- Focused Phase 7 regression：39 passed, 2 warnings。
- Agent/Bot/release hardening regression：24 passed。
- make verify：221 passed, 2 warnings；doctor ok；run-cpo-pack 182 evidence items / 6 ready / 0 skipped；coverage matrix ok。
- Unified gate：PYTHONPATH=src python3 scripts/verify_offline_release.py --skip-docker-smoke -> passed；9 checks passed，Docker smoke 1 skipped。
- Frontend：Vitest 4 passed；build passed；Playwright Edge smoke 1 passed。
- Docker static + docker compose config passed。
- Docker real smoke 未运行：docker info 无法连接 /Users/zq/.orbstack/run/docker.sock，必须记录为环境阻塞，不能宣称通过。
- DSA external path/import scan 无匹配；唯一 daily_stock_analysis 名称是 release gate 对 .dockerignore 的防护断言。
- git diff --check passed。

Completed：
- Phase 0-7 已全部完成。
- 已审计 apps/serenity-web fixture 数据入口、Serenity canonical stock-analysis manifest、local API、测试和发布边界。
- 已批准 API-first latest artifact 方案：版本化 manifest、只读 /api/artifacts/stock-analysis/latest API、严格 TypeScript decoder/adapter、显式 loading/unavailable/blocked 状态。
- 设计明确不在首个 slice 中迁移 history aggregation、旧预览写 API、serve-app 静态托管、Electron、外部 adapter 或交易自动化。
- 设计 spec 已提交为 948970b；设计状态交接已提交为 14237a9。
- 详细 Red-Green-Refactor implementation plan 已创建并同步到 tasks/todo.md。
- 计划锁定 canonical summary DTO、稳定 error envelope、真实 source coverage counts、结构化 safety/coverage findings、纯 artifact repository、injectable ReportArtifactSource、App lifecycle、Vite proxy、Playwright 和完整验证/提交检查点。
- 规划前 focused baseline：Python 40 passed；Frontend Vitest 2 files / 4 tests passed。它们仅是实施前 baseline，不是新 runtime parity 的实现证据。
- Planning checkpoint `ddff62b` 和 planning status refresh `e864cf9` 已提交；它们是实施前基线，当前生产实现已由 Task 1 commit `bc281f5` 启动。
- Task 1 已按 TDD 完成并提交为 `bc281f5`：两条 canonical-manifest 红测试先因 `generated_at` 缺失失败；实现版本化 manifest、单次 UTC 时间复用、真实 source coverage、evidence-backed skeptical review、明确 research-only safety boundary 和 key-claim provenance。
- 代码质量复审发现非 UTC/naive datetime 可能造成时间语义矛盾；新增红测试后实现 UTC 归一化与 naive 拒绝，并锁定 manifest 14 个顶层字段。
- Task 1 Green：`tests/test_analysis_report.py` -> `8 passed`；focused report/pipeline/safety/migration-boundary regression -> `17 passed, 2 warnings`；`git diff --check`、`py_compile`、规格审查和代码质量复审均通过。
- Task 2 已按 TDD 完成并提交为 `e276ce2`：首次运行 `tests/test_stock_analysis_artifacts.py` 因模块不存在产生 collection Red；实现纯标准库、只读、逐层 allowlisted repository 与稳定 404/409/422 error envelope。
- Task 2 review hardening 继续通过 Red -> Green 覆盖 validation order、missing safety/boundary、finite numeric/bool、unknown-field stripping、forbidden-key containing 规则、exact report/UI paths、manifest/report symlink escape 与 loop、trusted provenance URL、bool schema、invalid configured root 和原生异常封装。
- Task 2 Green：repository tests -> `27 passed`；focused manifest/repository/DSA-boundary regression -> `38 passed, 2 warnings`；`git diff --check`、`py_compile` 和代码质量复审通过。
- Task 3 已按 TDD 完成并提交为 `f984174`：初始 API/config/CLI Red 为 `7 failed, 5 passed`，明确覆盖缺失 `stock_analysis_artifact_dir`、未知 CLI option 和三个 artifact routes 的 generic 404。
- Task 3 Green 实现配置默认值、CLI override、latest summary/validated manifest/Markdown 三个只读 API、`Cache-Control: no-store`、JSON/Markdown content type 和稳定 `404/409/422` error envelope，同时保持 `/health`、`/version`、`/run-state` 和 generic 404 兼容。
- Task 3 review hardening 通过多轮 Red -> Green 补齐 all-route error mapping、missing Markdown、固定 API href、可信 URL/IPv6、malformed URL、POSIX/Windows/UNC/file URI 本机路径、HTML closing tag 和有限市场符号边界；最终独立代码审查 PASS。
- Task 3 最终验证：focused repository/API/CLI -> `69 passed`；backend parity -> `115 passed, 2 warnings`；`py_compile`、`git diff --check` 和 DSA runtime import/path scan 通过。
- Task 3 交接文档已提交为 `09094ef`，tracker、todo、验证证据、受保护文件状态和 Task 4 精确起点已同步。
- Task 4 已按 TDD 完成并提交为 `4d95ec3`：初始 decoder Red 因 `canonicalReportArtifact.ts` 缺失在 collection 阶段失败；实现独立 wire/view-model 类型、逐字段投影、固定 API href、有限非负 coverage、timezone-aware 严格时间戳、完整 provenance URL、递归 forbidden-key 和未知字段剥离。
- Task 4 review hardening 通过多轮 Red -> Green 覆盖 camelCase `targetPrice`、非法日历日期、旧 sample/ReportSemantics 类型兼容、structured safety line number、数组嵌套 forbidden field、递归未知字段与安全 value 文本；规格复审 PASS，代码质量复审确认可提交且 Minor 已修。
- Task 4 最终验证：decoder + semantics focused -> `67 passed`；full Vitest -> `68 passed`；`npm --prefix apps/serenity-web run build`、`git diff --check`、fixture/runtime boundary、DSA path scan 和 protected-output staging check 通过。
- Task 4 最终质量复核进一步指出有效 payload 只做部分字段断言；已在 `2ad297a` 改为完整 `ReportArtifact` equality，并补齐 Focus/External、coverage message/recommendation 展示断言。加固后 focused `67 passed`、full Vitest `68 passed`、build passed。

Not Started / 下一步：
- Task 5 injectable HTTP source/App lifecycle、剩余 History/Vite/Playwright canonical-artifact flow 和完整实现验证尚未开始。
- 首先创建 `apps/serenity-web/src/artifacts/reportArtifactSource.test.ts`，只测试 source contract、sanitized errors、relative API endpoint、AbortSignal、invalid JSON、decoder failure 和 network/abort 分类。
- 红测试命令：
  npm --prefix apps/serenity-web test -- src/artifacts/reportArtifactSource.test.ts
- 预期失败：`reportArtifactSource.ts` 尚不存在。
- source Green 后再写 `App.test.tsx` Red；不要提前实现 History、Vite proxy、Playwright、static hosting、CORS 或 mutation/trading automation。

Environment Blocked：
- Docker daemon 可用后，运行不带 --skip-docker-smoke 的 unified gate，补充镜像 build 和 no-secret /health 证据。

Deferred：
- 不要开始 Electron、auto-update、live Bot adapters、LLM provider、notification delivery、broker/order 或 release publishing，除非另行设计、威胁建模和批准。

保护状态：
- 不要修改、stage、提交或回滚：
  - output/ui/analyses/manifest.json
  - output/ui/reports/deliverable-research-report.md
  - output/ui/runs.json
  - output/ui/analyses/topic-2bde5fabbc/
- 当前这些 output/ui/* 仍是受保护外部脏状态；提交时必须显式排除。
- 不要在 Serenity runtime 中跨仓库 import DSA。
- 不要复制 DSA .venv、node_modules、__pycache__、SQLite runtime DB 或生成缓存。
- 每个阶段性任务完成后，自动更新 tracker、tasks/todo.md、tasks/lessons.md 和 restart prompt，明确区分 Completed / Not Started / Environment Blocked / Deferred，并只暂存/提交拥有的文件；这是长期项目习惯，不要等待用户再次提醒。
- 每次启动先运行 git status --short 和 git log -5 --oneline --decorate，核对当前 HEAD、受保护输出和 tracker 状态后再继续。
```

## Historical Phase 7 Planning Restart Prompt (Superseded)

```text
请继续在 /Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab 当前进度上开发。

先阅读并遵守：
1. docs/serenity-led-dsa-full-migration-plan.md
2. docs/serenity-led-dsa-full-migration-tracker.md
3. tasks/todo.md
4. tasks/lessons.md
5. docs/superpowers/specs/2026-07-10-serenity-alpha-lab-phase-7-runtime-release-design.md
6. docs/superpowers/plans/2026-07-10-serenity-alpha-lab-phase-7-agent-bot-runtime-release.md

当前方向：
- serenity-alpha-lab 仍然是主体项目、产品壳和未来运行时。
- daily_stock_analysis 是完整功能迁移来源，不是主体运行时。
- 迁移后必须兼容 Serenity 的 evidence-first、provenance、readiness、source coverage、skeptical review、report safety、research-only guardrails。

仓库：
- Serenity 仓库路径：/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab
- DSA 源仓库路径：/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis
- 当前分支：codex/phase-4-report-safety
- Phase 7 planning commit：eddf32c（docs: 完成 Serenity Phase 7 研究运行与发布规划）；Phase 6 handoff docs commit 为 1c2eddf；Phase 6 implementation commit 为 639e255；Phase 5 handoff docs commit 为 5cf2f31；Phase 5 implementation commit 为 f8e87d0；Phase 5 planning docs commit 为 d0136e0；Phase 4 implementation commit 为 3253f13；Phase 3 handoff docs commit 为 5718928；Phase 3 implementation commit 为 3cf14b3；Phase 2 handoff docs commit 为 cb0e2b5；Phase 2 implementation commit 为 8686d80；Phase 1 commit 为 d7187ca；Phase 0 baseline commit 为 b9b0fcb。
- DSA 当前 HEAD：95a4b51

已完成：
- Phase 0: Migration Baseline And Contract 已完成并提交。
- Phase 1: Serenity App Runtime Foundation 已完成并提交。
- Phase 2: Market Data Provider Migration 已完成并提交。
- Phase 3: Stock Analysis Pipeline Migration 已完成并提交，commit 为 3cf14b3。
- Phase 4: Report And Safety Integration 已完成实现与验证，implementation commit 为 3253f13。
- Phase 5: Web Workbench Migration 已完成实现、验证并提交，implementation commit 为 f8e87d0。
- Phase 6: Portfolio, Backtest, Alerts, Notifications 已完成实现、验证并提交，implementation commit 为 639e255。
- Phase 7 设计与详细实施计划已完成，生产实现尚未开始。
- Phase 7 planning commit 为 eddf32c。
- Phase 7 approved design：docs/superpowers/specs/2026-07-10-serenity-alpha-lab-phase-7-runtime-release-design.md。
- Phase 7 implementation plan：docs/superpowers/plans/2026-07-10-serenity-alpha-lab-phase-7-agent-bot-runtime-release.md。
- Phase 7 approved scope：evidence-grounded Agent tools、platform-neutral default-off Bot、desktop readiness contract、non-root no-secret Docker、unified offline application release gate。
- Phase 7 excluded scope：trading-oriented Agent prompt、LLM runtime、live Bot adapters、notifications、Electron/updater/installer、release publishing。
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
- 开始 Phase 7 Task 1：先写 tests/test_research_agents.py 红测试，覆盖 default-off visibility、explicit caller context、allowlist、readiness/evidence propagation、recursive trading-field rejection 和 sanitized failure。
- 红测试必须先因 serenity_alpha_lab.agents 模块缺失而失败，再实现最小 Agent contracts/tools/runtime。
- 完成 Task 1 后运行 Agent + analysis pipeline + report + DSA migration boundary focused regression，再进入 Bot 任务。

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
