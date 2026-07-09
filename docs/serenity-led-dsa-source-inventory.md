# Serenity-Led DSA Source Inventory

**Captured:** 2026-07-09

**Serenity target repository:** `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab`

**DSA source repository:** `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis`

**Serenity HEAD at capture:** `e911f6d`

**DSA HEAD at capture:** `95a4b51`

## Purpose

This artifact records the Phase 0 migration baseline before any DSA runtime code is copied into Serenity. `daily_stock_analysis` is the source system for capability migration, while Serenity remains the primary product shell and future runtime.

The inventory is intentionally path-based so later migration tasks can move capability slices module-by-module without creating cross-repository runtime imports.

## Migration Contract

- Serenity owns the future runtime, CLI, app shell, reports, evidence model, provenance, readiness gates, source coverage, skeptical review, safety scans, and research-only guardrails.
- DSA source code may be studied, selectively copied, rewritten, or adapted into Serenity-owned modules.
- Serenity runtime must not import modules from the external DSA checkout.
- DSA trading-oriented concepts must be adapted into evidence-backed research signals before appearing in Serenity outputs.
- External integrations, outbound notifications, live providers, Bot/Desktop packaging, and scheduling must remain default-off until explicitly configured inside Serenity.

## Capability Inventory

| Capability | DSA Source Surface | Serenity Migration Target | Phase 0 Notes |
| --- | --- | --- | --- |
| CLI and scheduler entrypoint | `main.py`, `webui.py`, `src/scheduler.py`, `src/services/runtime_scheduler.py`, `src/services/task_queue.py`, `src/services/task_service.py`, `src/services/run_flow.py`, `scripts/test.sh`, `scripts/ci_gate.sh` | `src/serenity_alpha_lab/cli.py` subcommands such as `analyze-stock`, `serve-app`, `run-schedule` | Preserve CLI workflows, scheduler semantics, async task state, and run-flow diagnostics, but remove DSA product-shell assumptions and adapt output language to research-only semantics. |
| API backend | `server.py`, `api/app.py`, `api/deps.py`, `api/v1/router.py`, `api/v1/endpoints/*`, `api/v1/schemas/*`, `api/middlewares/*` | `src/serenity_alpha_lab/app/*` or equivalent Serenity-owned API package | DSA v1 routes include auth, agent, analysis, history, stocks, backtest, system, usage, portfolio, alerts, decision signals, AlphaSift, intelligence, and health. Preserve CORS/auth/error-middleware contracts behind Serenity-owned config. |
| Web workbench | `apps/dsa-web/src/App.tsx`, `apps/dsa-web/src/pages/*`, `apps/dsa-web/src/api/*`, `apps/dsa-web/src/types/*`, `apps/dsa-web/src/stores/*`, `apps/dsa-web/src/components/*`, `apps/dsa-web/e2e/*`, `apps/dsa-web/package.json`, `static/*` | `apps/serenity-web/*` or Serenity UI generation path | Migrate UX capabilities after API foundation; do not overwrite existing generated Serenity `output/ui/*` artifacts in Phase 0. |
| Desktop app | `apps/dsa-desktop/*`, `scripts/build-desktop-*`, `scripts/verify-desktop-updater-artifacts.ps1` | Later Serenity packaging phase | Desktop packaging is not part of baseline/code migration; keep dependencies and build output out of Serenity until Phase 7. |
| Market data providers | `data_provider/base.py`, `akshare_fetcher.py`, `alphavantage_fetcher.py`, `baostock_fetcher.py`, `efinance_fetcher.py`, `finnhub_fetcher.py`, `longbridge_fetcher.py`, `pytdx_fetcher.py`, `tencent_fetcher.py`, `tickflow_fetcher.py`, `tushare_fetcher.py`, `tw_institutional_fetcher.py`, `yfinance_fetcher.py`, `yfinance_fundamental_adapter.py`, `fundamental_adapter.py`, `realtime_types.py`, `us_index_mapping.py` | `src/serenity_alpha_lab/market_data/*` | Port provider contracts, symbol routing, normalization, realtime types, circuit-breaker behavior, diagnostics, and fallback order with stubbed tests first. Live provider calls remain disabled in CI. |
| Analysis pipeline | `src/core/pipeline.py`, `src/stock_analyzer.py`, `src/analyzer.py`, `src/market_analyzer.py`, `src/services/analysis_service.py`, `src/services/analyzer_service.py`, `src/services/analysis_context_builder.py`, `src/services/run_flow.py`, `src/services/run_diagnostics.py`, `src/schemas/analysis_context_pack.py`, `src/schemas/report_schema.py` | `src/serenity_alpha_lab/analysis/*` | DSA `StockAnalysisPipeline` combines market data, realtime overlays, technical/fundamental context, news, social sentiment, Agent branches, history, diagnostics, and notifications. Serenity migration must convert provider outputs to evidence items and readiness-gated research results. |
| Market phase and strategy logic | `src/core/market_strategy.py`, `src/core/market_profile.py`, `src/core/market_review.py`, `src/core/market_review_runtime.py`, `src/core/trading_calendar.py`, `src/market_phase_prompt.py`, `src/phase_decision_guardrail.py`, `src/daily_market_context_guardrail.py` | `src/serenity_alpha_lab/strategy/*` and `analysis/*` | Treat market phase and decision guardrails as research context and invalidation support. Do not migrate phase logic as deterministic trading instructions. |
| LLM analysis | `src/analyzer.py`, `src/llm/*`, `src/services/analyzer_service.py`, `src/services/generation_backend_status_service.py` | `src/serenity_alpha_lab/agents/*` and evidence-grounded analyst layer | DSA uses LiteLLM and local backend routing. Serenity must require evidence/provenance context before conclusions and keep model/provider configuration default-off. |
| Agent system | `src/agent/*`, `src/agent/tools/*`, `src/agent/agents/*`, `src/agent/skills/*`, `api/v1/endpoints/agent.py`, `api/v1/schemas/agent` equivalents | `src/serenity_alpha_lab/agents/*` | Migrate tools only after evidence-first contracts exist; globally selectable trading tools must be converted into research-only, context-required tools. |
| Search, news, and intelligence | `src/search_service.py`, `src/services/intelligence_service.py`, `src/services/daily_market_context.py`, `src/services/social_sentiment_service.py`, `src/services/alphasift_service.py`, `api/v1/endpoints/intelligence.py`, `src/agent/tools/search_tools.py`, tests such as `tests/test_search_news_freshness.py` | `src/serenity_alpha_lab/intelligence/*` and evidence acquisition services | Search/news outputs must become traceable evidence candidates with freshness/source diagnostics, not unsupported catalysts. |
| Strategy library | `strategies/*.yaml`, `strategies/README.md`, `src/core/market_strategy.py`, `src/agent/strategies/*` | `src/serenity_alpha_lab/strategy/*` | Preserve strategy taxonomy as research lenses; do not migrate direct buy/sell, stop-loss, take-profit, or position-sizing semantics as instructions. |
| Reports and templates | `templates/report_markdown.j2`, `templates/report_brief.j2`, `templates/report_wechat.j2`, `templates/_macros.j2`, `src/services/report_renderer.py`, `src/report_language.py`, `src/formatters.py`, `src/md2img.py`, `apps/dsa-web/src/components/report/*` | Serenity report generator and UI report reader | Every migrated report section must attach provenance refs and pass Serenity report safety scans before being user-visible. Preserve multilingual rendering as a product capability. |
| Storage and history | `src/storage.py`, `src/repositories/*`, `api/v1/endpoints/history.py`, `src/services/history_service.py`, `src/services/history_loader.py`, `data/stock_analysis.db` runtime DB | `src/serenity_alpha_lab/storage/*` | Do not copy runtime SQLite DBs. Create migration adapters and fixtures from schemas/contracts, not live local data files. |
| Portfolio | `api/v1/endpoints/portfolio.py`, `api/v1/schemas/portfolio.py`, `src/services/portfolio_service.py`, `portfolio_alerts.py`, `portfolio_import_service.py`, `portfolio_risk_service.py`, `src/repositories/portfolio_repo.py` | `src/serenity_alpha_lab/portfolio/*` | Migrate as research tracking and risk-review context, not brokerage automation. |
| Backtest | `api/v1/endpoints/backtest.py`, `api/v1/schemas/backtest.py`, `src/core/backtest_engine.py`, `src/services/backtest_service.py`, `src/repositories/backtest_repo.py`, tests `tests/test_backtest*.py` | `src/serenity_alpha_lab/backtest/*` | Present results as historical validation evidence with limitations and no future-performance guarantee. |
| Alerts and notifications | `api/v1/endpoints/alerts.py`, `api/v1/schemas/alerts.py`, `src/services/alert_service.py`, `alert_worker.py`, `alert_indicators.py`, `market_light_alerts.py`, `portfolio_alerts.py`, `src/notification.py`, `src/notification_routing.py`, `src/notification_contracts.py`, `src/notification_sender/*`, `tests/test_notification*.py`, `tests/test_alert*.py` | `src/serenity_alpha_lab/alerts/*`, `notifications/*` | Default-off. Alerts become research monitors and evidence-gap reminders unless user explicitly configures outbound channels. Migrate routing, capability metadata, and sender docs together. |
| Bot integrations | `bot/commands/*`, `bot/platforms/*`, `bot/dispatcher.py`, `bot/handler.py`, `bot/models.py` | Later Serenity Bot phase | Keep platform credentials and network integrations out of early migration. Commands must use Serenity-owned analysis services after migration. |
| Docker and CI | `docker/*`, `.github/workflows/*`, `.github/scripts/*`, `.github/requirements-ci.txt`, `scripts/build-*`, `scripts/check_*` | Serenity release/CI gates after runtime parity | Later migration should include offline release gates, no-secret startup, Docker packaging, frontend tests, and Playwright smoke. |
| Tests and fixtures | `tests/*`, `apps/dsa-web/src/**/__tests__/*`, `apps/dsa-web/e2e/*`, `apps/dsa-desktop/tests/*` | Serenity tests by capability slice | Use DSA tests as behavior references; port focused tests with stubs instead of importing DSA test helpers directly. |
| Existing DSA Serenity bridge | `src/serenity/core/*`, `src/serenity/adapters/dsa_context_to_evidence.py`, `src/serenity/services/*`, `src/serenity/agent_tools/*`, `docs/serenity-research-task-contract.md` | Reconcile into Serenity-native modules before reuse | DSA already contains Serenity-derived evidence, provenance, readiness, retrieval, scoring, report-safety, research-task, and agent-tool code. Compare contracts before copying to avoid duplicate or divergent semantics. |

## Runtime And Generated Exclusions

Never copy these DSA artifacts into Serenity:

- `.venv/`
- `node_modules/`
- `__pycache__/`
- `.pytest_cache/`
- Runtime SQLite DBs such as `data/stock_analysis.db`
- Generated static bundles under `static/assets/`
- Frontend build output such as `apps/dsa-web/dist/` if present
- Desktop/backend build output such as `apps/dsa-desktop/dist/`, root `dist/`, or root `build/` if present
- Local logs, provider caches, screenshots, temporary downloads, and any credential-bearing `.env` files

## Migration Risk Notes

- DSA `src/storage.py` is a large monolithic SQLAlchemy schema. Migrate schema boundaries and repositories deliberately rather than copying services without their persistence contracts.
- Provider migration has high dependency risk because DSA uses multiple SDKs and external APIs: efinance, AkShare, Tushare, Longbridge, TickFlow, Finnhub, AlphaVantage, Tavily, SerpAPI, LiteLLM, and OpenAI-compatible providers.
- The DSA React workbench expects Node and npm toolchains, local API contracts, and bundled static hosting from `api/app.py`; rebuild Serenity-owned frontend assets instead of copying generated static bundles.
- Existing DSA `src/serenity/*` overlaps with Serenity's native evidence/retrieval/scoring concepts. Contract reconciliation should precede any code import.
- Notification and Bot surfaces are credential-heavy and platform-specific. Migrate config schemas, safe defaults, and docs with any sender or platform adapter.
- `data/stock_analysis.db` is runtime state, not source. If historical records are needed later, handle them as an explicit data export/import migration with sanitized fixtures.

## Protected Serenity Artifacts

Phase 0 must not modify, stage, commit, or revert these existing local generated UI outputs:

- `output/ui/analyses/manifest.json`
- `output/ui/reports/deliverable-research-report.md`
- `output/ui/runs.json`
- `output/ui/analyses/topic-2bde5fabbc/`

## Phase 0 Completion Criteria

- This inventory is present in Serenity docs and records both repository HEADs.
- An executable import-boundary test exists in Serenity and scans runtime source for external DSA checkout imports.
- Current Serenity baseline is verified before any DSA code migration.
- Tracker, task log, lessons, and restart prompt are updated with validation evidence and remaining next steps.
