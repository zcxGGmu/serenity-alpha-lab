# Serenity-Led DSA Full Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep `serenity-alpha-lab` as the primary product and long-term runtime while migrating the complete `daily_stock_analysis` product capabilities into it.

**Architecture:** `daily_stock_analysis` is the source system, not the future shell. Serenity owns the package, CLI, product UI, run records, evidence model, provenance, safety scanner, and research workflow; DSA capabilities are migrated as Serenity-owned modules that preserve practical stock-analysis utility while adapting outputs to evidence-first investment research discipline.

**Tech Stack:** Python 3.11+ / Serenity local-first research engine / DSA FastAPI + SQLAlchemy patterns / React + Vite workbench migration / market data providers / deterministic evidence pipeline / pytest + Vitest + Playwright.

---

## 1. Direction Reset

The previous `DSA-first Serenity Core` direction is now superseded.

Correct product direction:

- Primary repository: `/Users/zq/Desktop/ai-projs/posp/serenity-alpha-lab`.
- Source repository: `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis`.
- Target product: Serenity Alpha Lab with migrated DSA capabilities.
- Investment philosophy: Serenity evidence-first research, provenance, readiness gates, skeptical review, source coverage, and report safety.
- Migration goal: full DSA capability parity, not a narrow optional DSA add-on.

The migration must not create runtime imports from the DSA repository. Source code can be studied, copied selectively, rewritten, or adapted into Serenity-owned modules, with attribution in docs where useful.

## 2. Source Capability Inventory

DSA capabilities to migrate:

| Capability | DSA Source Surface | Serenity Target |
| --- | --- | --- |
| CLI entrypoint | `main.py` | `serenity_alpha_lab.cli` subcommands such as `analyze-stock`, `serve-app`, `run-schedule` |
| API backend | `server.py`, `api/app.py`, `api/v1/*` | Serenity-owned local API package, likely `src/serenity_alpha_lab/app/*` |
| Web workbench | `apps/dsa-web/src/*` | Serenity product UI, initially as a migrated Vite app or static+API hybrid |
| Market data | `data_provider/*` | `src/serenity_alpha_lab/market_data/*` |
| Analysis pipeline | `src/core/pipeline.py`, `src/services/analysis_service.py` | `src/serenity_alpha_lab/analysis/*` |
| LLM analysis | `src/analyzer.py`, `src/agent/*` | Serenity research agents and evidence-grounded analyst layer |
| Search/news | `src/search_service.py` | Serenity evidence acquisition and intelligence intake |
| Storage/history | `src/storage.py`, `data/stock_analysis.db` | Serenity run/project/evidence stores, with migration adapters |
| Reports/templates | `templates/*`, report components | Serenity report generator with DSA-derived sections gated by evidence/provenance |
| Strategies | `strategies/*.yaml` | Serenity strategy library with research-only semantics and guardrails |
| Portfolio/backtest | `api/v1/endpoints/portfolio.py`, `backtest.py`, `src/core/backtest_engine.py` | Serenity portfolio/research validation modules |
| Alerts/notifications | `src/notification*.py`, alert endpoints | Serenity notification layer, default local/off until configured |
| Bot/Desktop/Docker/CI | `bot/*`, `apps/dsa-desktop/*`, `docker/*`, workflows | Later packaging phases after core app parity |

## 3. Target Architecture

```text
serenity-alpha-lab
  ├─ src/serenity_alpha_lab/
  │  ├─ evidence/                 # existing evidence model, provenance, readiness
  │  ├─ market_data/              # migrated DSA data providers behind stable provider contracts
  │  ├─ analysis/                 # stock analysis orchestration, context packs, scoring adapters
  │  ├─ strategy/                 # migrated DSA strategy YAML + Serenity interpretation layer
  │  ├─ intelligence/             # news/search/social evidence acquisition
  │  ├─ app/                      # Serenity-owned FastAPI/local API
  │  ├─ storage/                  # run history, portfolio, alerts, decision traces
  │  ├─ notifications/            # configured outbound channels, default off
  │  ├─ agents/                   # evidence-grounded agent tools
  │  └─ ui/                       # product workbench generation or migrated web assets
  ├─ apps/serenity-web/           # optional migrated React/Vite workbench
  ├─ config/
  ├─ data/
  ├─ tests/
  └─ docs/
```

Key ownership rules:

- Serenity owns the runtime and user-facing product.
- Migrated DSA functions must call Serenity evidence/provenance/readiness services before emitting research conclusions.
- DSA trading vocabulary can be preserved only when converted into auditable research signals.
- No generated `output/ui/*` artifacts should be copied, staged, reverted, or overwritten unless explicitly requested.
- No live broker action, position sizing, guaranteed outcome, or unsupported certainty should be introduced.

## 4. Semantic Migration Rules

DSA has practical trading-oriented fields such as score, trend, operation advice, sniper points, alerts, catalysts, and decision signals. Serenity must adapt these into research artifacts:

| DSA Concept | Serenity Interpretation |
| --- | --- |
| `sentiment_score` / report score | research signal score with evidence coverage and confidence |
| `operation_advice` | hypothesis/actionability note, not standalone instruction |
| buy/sell/hold language | guarded research triage label only when evidence-backed and safety-scanned |
| target/stop/take-profit levels | scenario/risk levels with source and assumptions, not direct trade instructions |
| trend prediction | probabilistic thesis with invalidation triggers |
| catalyst | source-backed catalyst claim |
| risk alert | evidence-backed risk or missing-evidence warning |
| backtest result | historical validation evidence, not future-performance guarantee |

## 5. Phased Execution Plan

### Phase 0: Migration Baseline And Contract

- [ ] Freeze current Serenity generated UI outputs as protected local artifacts.
- [ ] Capture DSA runtime capability inventory from code and tests.
- [ ] Write import-boundary tests proving Serenity does not runtime-import the external DSA checkout.
- [ ] Define migrated package layout and naming conventions.
- [ ] Define config ownership and default-off external integration behavior.
- [ ] Verify current Serenity `make verify` baseline before migration edits.

### Phase 1: Serenity App Runtime Foundation

- [ ] Add Serenity-owned app config model for local API/Web runtime.
- [ ] Add local API skeleton with health, version, and run-state endpoints.
- [ ] Add tests for API startup without market-data credentials.
- [ ] Wire CLI command `serve-app` to the Serenity API.
- [ ] Keep existing static dashboard commands working.

### Phase 2: Market Data Provider Migration

- [ ] Port DSA provider contracts into `market_data`.
- [ ] Migrate provider normalization and stock-code routing.
- [ ] Add provider fallback order with timeouts and diagnostics.
- [ ] Add tests using stubs, not live market data.
- [ ] Keep optional provider credentials default-off.

### Phase 3: Stock Analysis Pipeline Migration

- [ ] Port DSA analysis context builder and core pipeline into Serenity-owned modules.
- [ ] Convert raw provider outputs into Serenity evidence items.
- [ ] Add evidence coverage/readiness gates before report generation.
- [ ] Add analysis result schema that preserves useful DSA fields as research signals.
- [ ] Verify one stubbed stock analysis end-to-end without network.

### Phase 4: Report And Safety Integration

- [ ] Migrate report templates into Serenity report generation.
- [ ] Add report safety scans for all generated actionability language.
- [ ] Attach provenance refs to every key claim.
- [ ] Add tests that unsupported recommendation language fails.
- [ ] Produce Markdown and UI-visible reports from one stubbed analysis.

### Phase 5: Web Workbench Migration

- [ ] Decide whether to import DSA React app as `apps/serenity-web` or incrementally recreate pages.
- [ ] Migrate navigation shell and core pages: Home, Analysis, History, Settings.
- [ ] Adapt DSA report components to Serenity evidence/readiness panels.
- [ ] Add Vitest coverage for key report semantics.
- [ ] Add Playwright smoke against the Serenity-owned app.

### Phase 6: Portfolio, Backtest, Alerts, Notifications

- [ ] Migrate portfolio and backtest models as research validation tools.
- [ ] Migrate alert rules as research monitors, not trading automation.
- [ ] Migrate notification channels default-off with explicit config checks.
- [ ] Add tests for no-secret startup and local-only operation.
- [ ] Add evidence-backed alert/report handoff records.

### Phase 7: Agent, Bot, Desktop, Docker, CI

- [ ] Migrate DSA Agent tools into Serenity evidence-grounded agents.
- [ ] Migrate bot commands around Serenity-owned analysis services.
- [ ] Evaluate desktop packaging only after web/API parity.
- [ ] Add Docker/CI release gates for Serenity app runtime.
- [ ] Add a full offline release checklist.

## 6. Verification Matrix

Minimum checks before declaring each phase complete:

- `python3 -m pytest tests -q` in Serenity.
- Targeted tests for newly migrated modules.
- `python3 -m serenity_alpha_lab.cli doctor` remains healthy.
- Static scan confirms no external DSA checkout imports.
- Report safety scan passes for generated outputs.
- No protected `output/ui/*` generated artifacts are staged.

Additional checks when Web/API work begins:

- API health endpoint starts locally without secrets.
- Frontend unit tests pass.
- Playwright smoke covers primary workflow.
- Network-dependent providers are stubbed in CI.

## 7. Immediate Next Step

Start with Phase 0. Do not copy large DSA directories wholesale yet. First create executable migration guardrails and a small inventory artifact so later code moves can be reviewed module-by-module.
