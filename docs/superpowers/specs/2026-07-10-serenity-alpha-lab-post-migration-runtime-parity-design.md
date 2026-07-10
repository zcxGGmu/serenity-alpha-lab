# Post-Migration Runtime Parity: Canonical Report Artifact Design

**Status:** Approved

**Approved:** 2026-07-10

## Goal

Replace the `apps/serenity-web` fixture-only runtime path with a Serenity-owned, read-only canonical stock-analysis artifact API while preserving evidence-first research semantics, provenance, readiness, source coverage, skeptical review, report safety, and research-only boundaries.

## Governing Direction

- `serenity-alpha-lab` remains the product shell, backend, Web application, and future desktop runtime.
- `daily_stock_analysis` remains source reference only; no runtime import or cross-repository file loading is allowed.
- The first parity slice is read-only. It exposes generated Serenity stock-analysis artifacts but does not start analyses, update records, deliver notifications, invoke Agents, or perform broker/order actions.
- The browser must not manufacture readiness, coverage, safety, provenance, or skeptical-review values when the backend contract is incomplete.
- Protected generated `output/ui/*` state remains external and must not be modified, staged, reverted, or used as the implementation fixture.

## Current Gap

The current Web runtime imports `sampleReportArtifact` directly in `apps/serenity-web/src/App.tsx` and passes the same object to Home, Analysis, and History. The existing local API exposes only `/health`, `/version`, and `/run-state`.

The generated `analysis-report-manifest.json` is the correct canonical source family, but its current shape is narrower than the Web view model:

- present: symbol, stock name, research-only flag, report links, structured safety findings, key claims, provenance refs;
- missing: schema version, query, generated timestamp, readiness, report gate, source coverage, skeptical review, and explicit safety boundary.

The Web must therefore consume a stable backend DTO derived from a versioned canonical manifest rather than parsing Markdown, combining unrelated responses, or casting arbitrary JSON to the current TypeScript interface.

## Approved Architecture

```text
StockAnalysisResult
  -> deterministic report/manifest writer
  -> versioned analysis-report-manifest.json
  -> read-only artifact repository
  -> GET /api/artifacts/stock-analysis/latest
  -> strict TypeScript wire decoder and adapter
  -> ReportArtifact view model
  -> Home / Analysis / History placeholder / Report Reader
```

The Markdown report and raw manifest remain canonical artifacts. The API supplies a stable, allowlisted summary DTO and safe links to the current report and manifest endpoints.

### Backend Components

#### Versioned Manifest

Extend the stock-analysis manifest writer in `src/serenity_alpha_lab/analysis/report.py` without removing existing keys.

The manifest must include:

```json
{
  "schema_version": 1,
  "artifact_type": "stock_analysis_report",
  "symbol": "AAPL",
  "stock_name": "Apple Inc.",
  "query": "AAPL market data research",
  "generated_at": "2026-07-10T00:00:00+00:00",
  "research_only": true,
  "readiness": {
    "status": "ready",
    "reason": "readiness_ready",
    "flags": []
  },
  "report_gate": {
    "status": "available",
    "reason": "readiness_ready",
    "research_only": true
  },
  "source_coverage": {
    "status": "ready",
    "focus_ticker": "AAPL",
    "evidence_count": 4,
    "primary_count": 2,
    "risk_count": 1,
    "flags": []
  },
  "skeptical_review": {
    "summary": "Risk coverage uses 1 risk or invalidation evidence item.",
    "counter_thesis": [
      "One negative daily movement is available for skeptical review."
    ]
  },
  "reports": {
    "stock_analysis": "reports/stock-analysis-report.md",
    "ui": "index.html"
  },
  "safety": {
    "passed": true,
    "boundary": "research only; not investment advice",
    "findings": []
  },
  "key_claims": []
}
```

Rules:

- `generated_at` is produced once and reused by Markdown and manifest generation.
- `query` comes from the analysis context, not a browser default.
- readiness and report-gate fields come directly from `StockAnalysisResult`.
- source coverage uses the pipeline's actual count and flag data; the API must not invent fixture thresholds.
- skeptical review is deterministic and evidence-backed. It summarizes risk/invalidation coverage and uses negative/risk evidence claims or explicit missing-risk diagnostics as counter-thesis items.
- safety findings remain structured objects.
- every key claim must retain provenance refs; an incomplete claim makes the latest artifact unavailable to the Web instead of being silently supplemented.

#### Artifact Configuration

Add `stock_analysis_artifact_dir` to `AppRuntimeConfig`, defaulting to `output/stock-analysis`.

Add the matching `serve-app --stock-analysis-artifact-dir` CLI option so callers can point the local API at an artifact directory produced by `analyze-stock --out-dir`.

The API may read only:

- `<artifact_dir>/analysis-report-manifest.json`;
- `<artifact_dir>/reports/stock-analysis-report.md`.

It must not accept browser-provided filesystem paths, traverse parent directories, enumerate arbitrary files, or expose absolute local paths.

#### Artifact Repository

Add a small pure module under `src/serenity_alpha_lab/app/` that:

- loads and validates the configured manifest;
- allowlists expected top-level and nested fields;
- rejects missing or unsupported schema versions;
- requires `research_only` to be exactly `true`;
- requires a passed safety result and explicit research boundary;
- requires readiness, source coverage, skeptical review, report gate, and key-claim provenance;
- resolves report paths only within the configured artifact root;
- returns sanitized error codes without raw JSON, exception messages, or local paths.

#### Read-Only API

Add these routes to the existing local API:

- `GET /api/artifacts/stock-analysis/latest`
  - returns the normalized canonical DTO;
  - sets `Cache-Control: no-store`;
  - returns `404 artifact_not_found` when no artifact exists;
  - returns `409 artifact_blocked` when the artifact is not research-only or fails report safety;
  - returns `422 artifact_invalid` when required canonical fields or provenance are missing.
- `GET /api/artifacts/stock-analysis/latest/manifest`
  - returns the validated canonical manifest as JSON.
- `GET /api/artifacts/stock-analysis/latest/report`
  - returns the validated Markdown report with `text/markdown; charset=utf-8`.

The summary DTO uses API-relative hrefs for the report and manifest endpoints. It never returns a filesystem path.

Existing `/health`, `/version`, and `/run-state` behavior remains compatible in this slice. Hardening the raw `latest_run` allowlist and removing `runs_path` belongs to the explicit run-history/API-hardening follow-on slice, not this implementation.

### Frontend Components

#### Wire Contract And View Model

Separate the backend wire type from the UI projection:

- `CanonicalReportArtifact` mirrors the snake_case API response.
- `ReportArtifact` remains the camelCase UI view model.
- safety findings become structured typed objects instead of `string[]`.
- readiness, report-gate, source-coverage, and artifact availability use separate status unions rather than one over-broad `ReportStatus`.

No code may use `as ReportArtifact` to trust network JSON.

#### Decoder And Adapter

Add a pure decoder/adapter that:

- validates required objects, arrays, booleans, strings, and finite numbers;
- requires supported `schema_version`;
- requires `research_only === true`;
- requires safety boundary and `safety.passed === true`;
- requires readiness, report gate, source coverage, skeptical review, and report hrefs;
- requires each key claim to have at least one valid provenance ref;
- maps snake_case to camelCase without adding evidence or conclusions;
- rejects unsafe protocols in report and manifest hrefs;
- preserves structured safety findings and provenance diagnostics.

#### Artifact Source

Add an injectable source:

```ts
export interface ReportArtifactSource {
  loadLatest(signal?: AbortSignal): Promise<ReportArtifact>;
}
```

The production implementation fetches `/api/artifacts/stock-analysis/latest`. Tests may inject a deterministic source backed by `sampleReportArtifact`.

The sample fixture remains test data only and must no longer be imported by the production `App` runtime.

#### App States

`App` owns the asynchronous artifact lifecycle:

- `loading`: render a stable research-artifact loading state;
- `ready`: pass the canonical artifact to existing pages;
- `unavailable`: render the sanitized backend reason and retry action;
- `blocked`: render the research-only or report-safety boundary failure without report links.

There is no production fallback from unavailable/blocked API data to the AAPL fixture.

The first slice may continue to show the latest artifact on the History page, but it must label this as the latest available artifact rather than a complete history collection. A separate run-history source is deferred.

#### Development Transport

The Web client requests relative `/api/...` URLs.

`vite.config.ts` proxies `/api` to the loopback Serenity API at `http://127.0.0.1:8010` for local development. This avoids wildcard CORS and keeps the browser contract same-origin.

Production static hosting, reverse proxying, and serving `apps/serenity-web/dist` from `serve-app` are separate parity slices. This design does not add permissive CORS or claim complete desktop runtime parity.

## Error And Safety Behavior

- Missing artifact: explicit unavailable state; no fixture fallback.
- Invalid JSON or unsupported schema: `artifact_invalid`; no raw parse error returned.
- `research_only` false or missing: `artifact_blocked`.
- safety missing or failed: `artifact_blocked`.
- readiness/source coverage/skeptical review missing: `artifact_invalid`.
- missing key-claim provenance: `artifact_invalid`.
- report path outside configured root: `artifact_invalid`.
- network failure or aborted request: sanitized Web unavailable state.
- unknown fields are ignored only after required fields pass allowlist validation; forbidden trading/broker/order keys are rejected recursively.

The API and frontend must continue rejecting direct recommendation language, price objectives, position sizing, stop-loss/take-profit instructions, broker actions, and guaranteed outcomes.

## TDD Strategy

Implementation must follow Red -> Green -> Refactor for each layer.

### Backend Red Tests

- manifest writer includes the approved versioned research semantics;
- latest-artifact API returns the canonical DTO and API-relative report links;
- missing artifact returns sanitized 404;
- unsafe or non-research artifact returns blocked;
- incomplete provenance or semantic fields return invalid;
- report and manifest endpoints never escape the configured root;
- no response contains an absolute repository path or raw exception;
- external DSA checkout imports remain absent.

### Frontend Red Tests

- valid canonical JSON decodes and maps without semantic loss;
- missing research-only, safety, readiness, source coverage, skeptical review, or provenance fails closed;
- `App` renders loading, ready, unavailable, and blocked states;
- production `App` no longer imports the sample fixture;
- existing report-semantics trading-language guards remain active;
- Playwright route interception supplies a non-AAPL canonical response that drives Home, Analysis, latest-artifact History, and Report Reader.

## Acceptance Criteria

The slice is complete only when:

1. `apps/serenity-web` production runtime no longer imports `sampleReportArtifact`.
2. The stock-analysis manifest is versioned and carries all evidence/readiness/coverage/skeptical-review/safety semantics required by the Web.
3. The local API exposes validated latest summary, manifest, and Markdown routes without local path leakage.
4. The frontend uses an injectable source plus strict decoder/adapter and never fills missing research semantics from fixture defaults.
5. Missing, invalid, unsafe, and blocked artifacts render explicit states.
6. Report links are API-relative and protocol/path validated.
7. Focused backend/frontend tests, frontend build, Playwright smoke, migration boundaries, report safety, and full verification pass.
8. Protected `output/ui/*` files remain unmodified and unstaged.

## Explicit Non-Goals

- No history aggregation or replacement of `/run-state`.
- No mutation endpoints, analysis-start endpoint, scheduling, notifications, Agent invocation, or provider calls.
- No static Web hosting from `serve-app`.
- No wildcard CORS.
- No Electron, updater, installer, signing, or release publishing.
- No live Bot adapters, LLM providers, broker/order actions, or trading automation.
- No runtime import or filesystem dependency on the external DSA checkout.
- No copying DSA `.venv`, `node_modules`, `__pycache__`, SQLite DBs, generated caches, or output artifacts.
- No modification of protected generated `output/ui/*`.

## Follow-On Slices

After this slice is verified:

1. add a sanitized canonical run-history API and a true `RunHistorySource`;
2. decide same-origin production hosting or a constrained loopback reverse proxy;
3. make the desktop runtime consume the stable API/Web composition;
4. rerun the complete Docker image and no-secret container `/health` smoke when the daemon is available.
