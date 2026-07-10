# Phase 7 Agent, Bot, Desktop, Docker, And CI Design

**Status:** Approved

**Approved:** 2026-07-10

## Goal

Migrate the useful DSA Agent, Bot, Desktop, Docker, and CI capabilities into Serenity-owned, evidence-grounded, local-first runtime and release surfaces without introducing trading automation, implicit network activity, or credential-required startup.

## Governing Direction

- `serenity-alpha-lab` remains the product shell, package, API, UI, and future runtime.
- `daily_stock_analysis` is a source reference only and must never be imported at Serenity runtime.
- Agent and Bot outputs must preserve evidence IDs, provenance, source coverage, readiness, skeptical review, report safety, and research-only semantics.
- External Bot platforms, model providers, notifications, auto-update services, and desktop packaging remain disabled or deferred until explicitly configured and separately verified.
- Protected generated `output/ui/*` artifacts remain external local state and must not be modified, staged, reverted, copied into images, or used as release inputs.

## Approved Scope

### 1. Evidence-Grounded Agent Tools

Add a small provider-neutral Agent package:

- `agents/contracts.py` defines tool parameters, tool definitions, explicit caller context, and JSON-safe research tool results.
- `agents/tools.py` exposes only Serenity-owned research summary and evidence-gap tools.
- `agents/runtime.py` owns registration, allowlisting, default-off visibility, explicit-context enforcement, execution, diagnostics sanitization, and recursive output boundary checks.

The first Agent tools must:

- consume caller-provided `StockAnalysisResult.to_dict()` payloads;
- never fetch market data, query a database, send notifications, or read credentials;
- return `blocked` when context is absent;
- preserve readiness, source coverage, report gate, evidence IDs, and research signals;
- expose missing evidence and risk/source gaps as research tasks;
- reject recursive trading fields such as `operation_advice`, `target_price`, `position_sizing`, `stop_loss`, `take_profit`, `sniper_points`, and broker/order fields;
- remain invisible unless both runtime enablement and caller allowlist permit them.

This phase does not migrate DSA's trading-oriented ReAct prompt, decision agents, portfolio agents, LLM routing, memory database, or provider-specific model adapters.

### 2. Platform-Neutral Research Bot

Add a transport-free Bot package:

- `bot/contracts.py` defines normalized messages and responses without platform SDK types.
- `bot/commands.py` defines research-only `status`, `analyze`, and `evidence-gaps` commands around injected Serenity services.
- `bot/dispatcher.py` owns command parsing, aliases, deterministic rate limiting, explicit enablement, argument validation, and sanitized error responses.

The Bot layer must:

- be disabled by default;
- avoid importing Feishu, DingTalk, Discord, Telegram, Slack, webhook, or notification SDKs;
- reuse the same `StockAnalysisPipeline` and Agent research tool results instead of implementing a second readiness or safety model;
- preserve `blocked` and `needs_work` states rather than rewriting them as recommendations;
- emit research-only Markdown/text and evidence IDs;
- avoid outbound delivery in this phase.

### 3. Runtime Health Diagnostics

Extend `AppRuntimeConfig` and `/health` with non-secret capability diagnostics:

- Agent tools enabled/disabled.
- Bot commands enabled/disabled.
- Bot platform delivery status fixed to `disabled`.
- Desktop runtime mode and packaging status.
- Docker/release mode remains local-first and no-secret.

Health responses must never include API keys, tokens, passwords, webhook URLs, raw exceptions, local absolute paths, or caller research context.

### 4. Desktop Runtime Decision

Do not copy DSA Electron or updater code in Phase 7.

Add a pure `desktop_runtime.py` contract that records:

- local Web/API mode;
- loopback host requirement;
- Serenity CLI backend command;
- web asset directory;
- packaging status `deferred_until_runtime_parity`;
- automatic updates disabled;
- credentials not bundled;
- external network and public bind disabled by default.

Electron packaging can be reconsidered only after:

1. the Serenity web workbench consumes a canonical backend artifact/API instead of fixture-only data;
2. local API routes required by the desktop shell are stable;
3. release artifacts pass the same offline/no-secret gate;
4. updater behavior has a separate threat model and rollback plan.

### 5. Docker Runtime

Create a Serenity-owned multi-stage Docker image:

- Node stage runs `npm ci` and `npm run build` under `apps/serenity-web`.
- Python stage installs the Serenity package, copies the built web assets, and runs as a non-root `serenity` user.
- Default command starts the local API on `0.0.0.0:8010`.
- Health check calls `/health` using Python standard library.
- No `.env`, secrets, DSA checkout, SQLite runtime DB, generated `output/ui/*`, local `node_modules`, caches, or test reports enter the build context.

Add Compose services:

- `api`: Serenity local API on port 8010.
- `web`: static Serenity web build on port 4175.

Neither service performs scheduled analysis, notification delivery, provider calls, or broker actions.

## CI And Release Gate

Add a machine-readable release gate with these properties:

- application checks require no secrets or external providers;
- Python tests, doctor, Agent/Bot/Desktop focused tests, report safety, DSA import boundary, and static scans run locally;
- frontend dependencies are installed by CI before the offline application gate;
- Vitest, frontend build, and Playwright smoke run against deterministic local assets;
- Dockerfile/Compose static checks always run;
- Docker build and no-secret `/health` smoke run when Docker is available;
- pull requests, branch pushes, and tag pushes use the same verification workflow;
- release output reports every check as `passed`, `blocked`, or `skipped` with a reason.

The phrase "offline release gate" means the application tests do not call external market-data, LLM, notification, Bot, broker, or update services. Dependency installation and base-image pulls may still use package registries in CI.

## Data Flow

```text
caller-provided analysis context
  -> ResearchToolContext validation
  -> allowlisted Agent tool
  -> readiness / source coverage / evidence IDs / gaps
  -> recursive safety boundary check
  -> JSON-safe ResearchToolResult
  -> optional platform-neutral Bot formatting
  -> no outbound delivery
```

Docker and desktop surfaces consume only Serenity-owned CLI/API/web assets:

```text
Serenity package + built serenity-web
  -> local API /health
  -> local static web service
  -> future desktop shell after runtime parity gate
```

## Error Handling

- Missing Agent context returns `blocked` with `analysis_context_required`.
- Disabled Agent/Bot capabilities return deterministic disabled diagnostics and perform no service calls.
- Tool execution exceptions return `failed_open` with exception type only; exception messages and paths are not exposed.
- Unknown Bot commands return a help-oriented error without echoing raw payload metadata.
- Docker starts without credentials and reports integrations disabled.
- Release checks fail closed for test, safety, boundary, or required build failures.
- Environment-dependent checks may be `skipped` only with an explicit reason, never silently treated as passed.

## Testing Strategy

- Agent tests cover default-off visibility, allowlists, missing context, recursive trading-field rejection, sanitized failures, and evidence/readiness propagation.
- Bot tests cover command parsing, disabled mode, rate limits, injected pipeline reuse, evidence-gap formatting, unknown commands, and sanitized errors.
- API tests cover non-secret Agent/Bot/Desktop health diagnostics.
- Desktop tests cover loopback-only runtime planning and deferred packaging/update status.
- Release tests cover machine-readable plan semantics, safety/boundary checks, workflow reuse, Docker non-root/no-secret/static rules, and protected artifact exclusion.
- Frontend CI uses existing Vitest and Playwright smoke with Chromium in CI and installed Edge locally.
- Final verification includes focused tests, full `make verify`, frontend build/tests/smoke, Docker smoke when available, DSA import/path scans, safety scans, `git diff --check`, and protected output status comparison.

## Explicit Non-Goals

- No trading recommendations, position sizing, order placement, broker integration, or live trading automation.
- No DSA runtime imports or cross-repository path loading.
- No LLM provider integration or Agent conversation memory.
- No external Bot platform adapters or webhook endpoints.
- No live notification delivery.
- No Electron implementation, auto-update implementation, installer, code signing, or release publishing.
- No database migration or copied DSA SQLite state.
- No modification of protected generated `output/ui/*`.
