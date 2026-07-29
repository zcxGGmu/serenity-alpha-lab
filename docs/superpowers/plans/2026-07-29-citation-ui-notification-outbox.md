# Citation UI And Notification Outbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver `SAL-P5-016` citation expansion UI payloads and transactional notification Outbox without starting Agent evaluation, real runtime execution, or report publication.

**Architecture:** Add a framework-neutral presenter that consumes `RenderedResearchReport` canonical JSON and emits report-page data with claim/citation/evidence/source/artifact expansion. Add a SQLAlchemy repository for notification Outbox metadata with tenant/channel/dedupe uniqueness, lease/retry/send status transitions, and no sender execution. Add a DSA Web extension patch that consumes the future research report API and displays citations plus Outbox status.

**Tech Stack:** Python 3.11 dataclasses, SQLAlchemy 2.x, existing P5 evidence schema/renderer, Vitest/React patch in DSA Web, pytest contract tests.

---

### Task 1: Root Contract Tests

**Files:**
- Create: `tests/application/test_report_delivery_ui.py`
- Create: `tests/repositories/test_notification_outbox.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Write failing UI contract test**

```python
from serenity_alpha_lab.application.report_delivery import ResearchReportPagePresenter

def test_report_page_expands_claims_to_citations_evidence_and_artifacts():
    page = ResearchReportPagePresenter().build(rendered_report, notification_records=[...])
    assert page.body["authority"] == "canonical_json"
    assert page.body["claims"][0]["citations"][0]["evidence"]["artifact"]["artifact_hash"].startswith("sha256:")
```

- [x] **Step 2: Write failing Outbox contract test**

```python
from serenity_alpha_lab.repositories.notification_outbox import NotificationOutboxStore

def test_outbox_dedupes_by_tenant_channel_and_dedupe_key(sqlite_engine):
    first = store.enqueue_report_notification(...)
    replay = store.enqueue_report_notification(...)
    assert replay == first
```

- [x] **Step 3: Run Red tests**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_report_delivery_ui.py tests/repositories/test_notification_outbox.py -q`

Expected: collection errors for missing `serenity_alpha_lab.application.report_delivery` and `serenity_alpha_lab.repositories.notification_outbox`.

### Task 2: Report Page Presenter

**Files:**
- Create: `src/serenity_alpha_lab/application/report_delivery.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Implement immutable page DTOs**

Implement `ReportDeliveryApiRoute`, `ResearchReportPage`, `ResearchReportNotificationStatus` and `ResearchReportPagePresenter`.

- [x] **Step 2: Preserve canonical authority**

The presenter must read `RenderedResearchReport.trusted_report.authoritative_json`; Markdown and HTML are display fields only and must be labeled `derived_from_authoritative_json`.

- [x] **Step 3: Expand citation graph**

For each claim, attach citations with `evidence_id`, field path, cited value/unit/formula/dataset/run/stage/artifact hash, and an evidence summary containing source URI plus artifact id/hash.

- [x] **Step 4: Run focused Green**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_report_delivery_ui.py -q`

Expected: `passed`.

### Task 3: Notification Outbox Store

**Files:**
- Create: `src/serenity_alpha_lab/repositories/notification_outbox.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Implement Outbox schema**

Table: `serenity_notification_outbox_messages` with `message_id`, `tenant_id`, `report_id`, `channel`, `dedupe_key`, `status`, `attempt`, `max_attempts`, `payload_json`, report/rendering hashes, lease fields and receipt fields.

- [x] **Step 2: Implement enqueue/dedupe**

`enqueue_report_notification()` must be idempotent for the same immutable message and raise conflict if a dedupe key is reused with different report hash, payload, or channel semantics.

- [x] **Step 3: Implement at-least-once transitions**

`lease_pending()` marks pending messages as sending and increments attempt; `mark_failed()` retries until `max_attempts`; `mark_sent()` stores provider receipt and prevents duplicate pending delivery.

- [x] **Step 4: Run focused Green**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_notification_outbox.py -q`

Expected: `passed`.

### Task 4: DSA Web Patch

**Files:**
- Add: `patches/dsa/v3.26.1/0007-add-research-report-delivery-ui.patch`
- Modify: `docs/upstream-patches.md`
- Modify: `docs/development-progress-checklist.md`

- [x] **Step 1: Create temp DSA worktree from locked tag**

Run: create a disposable worktree under `.cache`, apply patches `0001..0006`, then add the P5-016 Web changes there.

- [x] **Step 2: Add Web API and page**

Add `researchReports.ts`, API tests, `ResearchReportPage.tsx`, page tests, route `/research-reports/:reportId`, sidebar/nav labels if needed, and citation expansion UI.

- [x] **Step 3: Export patch**

Generate `0007-add-research-report-delivery-ui.patch` from the temp worktree diff after patches `0001..0006`.

- [x] **Step 4: Run Web focused tests**

Run the new API/page/route tests in the temp worktree. Then run lint/build if time permits.

### Task 5: Documentation And Verification

**Files:**
- Create: `docs/research-report-delivery-ui-outbox.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `docs/upstream-patches.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Update evidence doc and registries**

Record contracts, non-goals, Red/Green evidence, DSA patch scope and no-runtime boundary.

- [x] **Step 2: Run related suite**

Run focused tests, related P5/report/outbox suite, full pytest, compileall, dependency lock guard, immutable tag, DSA patch replay and `git diff --check`.

- [x] **Step 3: Commit**

Create a Chinese checkpoint commit for `SAL-P5-016` after docs/status are synchronized.
