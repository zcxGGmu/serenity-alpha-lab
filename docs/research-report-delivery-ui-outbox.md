# Research Report Delivery UI And Notification Outbox

> Task: `SAL-P5-016` Citation UI And Notification Outbox<br>
> Date: 2026-07-29<br>
> Status: `APPROVED FOR SAL-P5-017 INPUT ONLY`

## Conclusion

`SAL-P5-016` adds an offline delivery boundary for trusted `ResearchReport` output:

```text
src/serenity_alpha_lab/application/report_delivery.py
src/serenity_alpha_lab/repositories/notification_outbox.py
patches/dsa/v3.26.1/0007-add-research-report-delivery-ui.patch
```

The Python presenter consumes `RenderedResearchReport.trusted_report.authoritative_json` and emits a report-page payload that expands claims to citations, evidence records, source links and artifact hashes. The Outbox store persists notification metadata with tenant/channel/dedupe uniqueness and at-least-once lease/retry/sent status transitions. The DSA Web patch adds a read-only report page for future `/api/v1/research/reports/{report_id}` payloads and notification status display. No sender, Provider, LLM, Worker loop, Qlib runtime or production schedule is started.

## Contracts

| Item | Contract |
|---|---|
| Report delivery UI | `research.report_delivery_ui@1.0.0` |
| Report page schema | `research.report_page` / `1.0.0` |
| Notification Outbox | `research.notification_outbox@1.0.0` |
| Outbox message schema | `research.notification_outbox_message` / `1.0.0` |
| Presenter | `ResearchReportPagePresenter` |
| Page DTO | `ResearchReportPage` |
| Notification DTO | `ResearchReportNotificationStatus` |
| Outbox store | `NotificationOutboxStore` |
| SQL table | `serenity_notification_outbox_messages` |
| DSA Web patch | `DSA-PATCH-007` |

## Report Page Rules

- The only authority is `trusted_report.authoritative_json`; `markdown` and `html` are display strings labeled `derived_from_authoritative_json`.
- The page payload preserves `authoritative_json_hash`, `rendering_hash`, report level, as-of time, generated time, run/trace ids, model/cost context, risk summary, disclaimer and Dataset versions.
- Each claim expands `citation_ids` to citation summaries with evidence field path, cited value, unit, formula version, Dataset versions, run/stage ids and artifact hash.
- Each citation embeds an evidence summary with evidence id/kind/scope/title/summary, source metadata, source URI, Dataset versions, trace/run/stage ids and artifact id/hash.
- Declared API routes are GET-only: `/api/v1/research/reports/{report_id}` and `/api/v1/research/reports/{report_id}/notifications`.

## Outbox Rules

- `NotificationOutboxStore.enqueue_report_notification()` is idempotent by `(tenant_id, channel, dedupe_key)` for the same immutable message hash.
- Reusing a dedupe key with different immutable payload, recipient, report hash or rendering hash raises `NotificationOutboxConflict`.
- `lease_pending()` marks eligible rows as `sending`, increments attempt, records worker lease owner and lease expiry, and allows expired sending rows to be leased again.
- `mark_failed()` returns rows to `pending` until `max_attempts`, then moves them to `dead_letter`.
- `mark_sent()` stores provider receipt metadata and removes the lease; sent rows are not leased again.

## DSA Web Patch

`DSA-PATCH-007` adds a Serenity-only UI extension on top of `DSA v3.26.1` after patches `0001..0006`:

- `src/api/researchReports.ts` GET-only API client for trusted report pages and notification statuses.
- `ResearchReportPage` with canonical authority/hash cards, model/cost/dataset/risk/disclaimer context, expandable claim evidence, source URI and artifact hash display, plus Outbox status cards.
- Lazy route `/research-reports/:reportId`, SidebarNav entry `研究报告 / Research Reports`, and route/nav/i18n tests.
- No send endpoint, no backend route registration, no notification provider call and no DSA runtime source commit.

## Non-Goals

- No Agent goldens, Agent regression evaluation, Gate G5 review or RC approval.
- No real Provider/LLM call, LiteLLM import, Agent/tool execution, Worker loop, Qlib runtime, production scheduler or formal portfolio backtest promotion.
- No notification sender implementation and no email/webhook/Bot side effect.
- No Evidence Store writes, Evidence body reads, Citation repair loop, report publication workflow or production delivery SLA.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_report_delivery_ui.py tests/repositories/test_notification_outbox.py -q` initially failed with missing `serenity_alpha_lab.application.report_delivery` and `serenity_alpha_lab.repositories.notification_outbox` modules |
| Focused Python target | `uv run --extra core --extra dev python -m pytest tests/application/test_report_delivery_ui.py tests/repositories/test_notification_outbox.py tests/architecture/test_architecture_boundaries.py::test_report_delivery_ui_stays_offline_and_runtime_free tests/architecture/test_architecture_boundaries.py::test_notification_outbox_stays_persistence_only_and_sender_free -q` -> `6 passed` |
| DSA Web focused target | `npm run test -- src/api/__tests__/researchReports.test.ts src/pages/__tests__/ResearchReportPage.test.tsx src/App.test.tsx src/components/layout/__tests__/SidebarNav.test.tsx` -> `4 passed files / 26 passed tests` |
| DSA Web lint | `npm run lint` -> PASS |
| DSA Web build | `npm run build` -> PASS; Vite generated `ResearchReportPage-CDhe0e93.js` chunk |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/application/test_report_delivery_ui.py tests/repositories/test_notification_outbox.py tests/evidence/test_report_renderer.py tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_model_routing_cache_budget.py tests/application/test_agent_tool_security.py tests/architecture/test_architecture_boundaries.py -q` -> `79 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `490 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| DSA patch replay | Clean temp DSA worktree + `scripts/apply-dsa-baseline-patches.sh --worktree <temp>` -> `0001` through `0007` applied |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## Approval Record

This record approves trusted report delivery UI payloads and transactional notification Outbox metadata as input to `SAL-P5-017` Agent goldens and regression evaluation only. Gate G5 remains unpassed, and real report delivery still requires later sender/runtime/publishing tasks under explicit profile guards.
