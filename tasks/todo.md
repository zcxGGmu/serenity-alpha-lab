# SAL-P5-017 Agent Golden Regression Evaluation Plan

> Scope: Complete only `SAL-P5-017` by adding offline Agent golden cases, a deterministic stub, a scorer and a regression report. Do not start Gate G5, real Provider/LLM, Worker loop, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read recovery docs and confirm actual git state before implementation.
- [x] Write SAL-P5-017 implementation plan in `docs/superpowers/plans/2026-07-30-agent-golden-regression-evaluation.md`.
- [x] Add failing tests for 50+ golden cases, category/market coverage, scorer thresholds, safety-core checks and prompt/model regression comparison.
- [x] Run focused Red tests and record expected missing-module failure.
- [x] Implement offline `application.agent_evaluation` with golden catalog, deterministic stub, scorer and report DTOs.
- [x] Add architecture guard proving the evaluator stays offline and runtime-free.
- [x] Update SAL-P5-017 evidence doc, progress checklist, development status and review notes.
- [x] Run focused Green tests, related P5 suite, full pytest, compileall, dependency lock, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P5-017`.

## Review

- Implemented `research.agent_evaluation@1.0.0` in `src/serenity_alpha_lab/application/agent_evaluation.py`; default catalog has 56 cases across 7 required categories and CN/HK/US/JP/KR/TW markets.
- Added deterministic `OfflineAgentEvalStub`, `AgentEvaluationScorer` and regression comparison report; baseline metrics are citation accuracy `1.0`, unsupported numeric rate `0.0`, schema success `1.0` and safety core pass.
- Red target failed with missing `agent_evaluation` module as expected; focused Green `5 passed`, related P5 suite `76 passed`, full pytest `495 passed, 3 skipped`.
- Final verification completed before commit: compileall PASS, dependency lock guard PASS (`Resolved 298 packages`), immutable upstream tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, and `git diff --check` PASS.
- Chinese implementation checkpoint created: `91d6d15b feat(P5): 建立 Agent 金标回归评测`. Status-sync commit follows to anchor this hash in recovery docs.

---

# SAL-P5-016 Post-Completion Status Review

> Scope: Update repository recovery state after completed `SAL-P5-016`. Do not start `SAL-P5-017`, Gate G5, real Provider/LLM, Worker loop, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read current recovery handoff, status snapshot, progress checklist, todo and lessons.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Update `docs/development-status.md` to show completed through `SAL-P5-016`, unfinished from `SAL-P5-017`, and current recovery prompt.
- [x] Update `docs/development-progress-checklist.md` tail summary to remove stale `SAL-P5-016` unfinished wording.
- [x] Update `tasks/lessons.md` for the user's repeated instruction to automatically do this after every phase task.
- [x] Run document status-anchor checks and `git diff --check`.
- [x] Create a Chinese status-review checkpoint commit.

## Review

- Current phase remains P5 证据化 Agent、报告与成本治理.
- Gate G4 remains passed; Gate G5 is not passed.
- Completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, `SAL-P4-001..022`, `SAL-P5-001..016`.
- Current unfinished range starts at `SAL-P5-017` Agent 金标与回归评测; `SAL-P5-018` Gate G5 and all P6 release tasks remain incomplete.
- Latest implementation checkpoint entering this review is `518a785f feat(P5): 实现引用 UI 与通知 Outbox`; latest status-sync hash-anchor is `bfc921aa docs: 记录 SAL-P5-016 状态同步 hash`.
- Status-review checkpoint is `b815b7d6 docs: 复核 SAL-P5-016 最新开发状态与恢复提示`; this follow-up records its hash-anchor.

---

# SAL-P5-016 Citation UI And Notification Outbox Implementation Plan

> Scope: Complete only `SAL-P5-016` by adding offline citation expansion UI payloads and a transactional notification Outbox for trusted `ResearchReport` delivery. Do not jump to Agent evaluation, Gate G5, Worker runtime, real Provider/LLM calls, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current development status/progress docs and required P5 evidence/report docs.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Write SAL-P5-016 implementation plan in `docs/superpowers/plans/2026-07-29-citation-ui-notification-outbox.md`.
- [x] Add failing contract tests for report citation UI payload and notification Outbox idempotency.
- [x] Run focused Red tests and record the expected missing-module failures.
- [x] Implement `application.report_delivery` as a pure offline presenter from trusted canonical JSON.
- [x] Implement `repositories.notification_outbox` as SQLAlchemy-backed transactional Outbox metadata only.
- [x] Add DSA Web extension patch `DSA-PATCH-007` for report API client, report page, citation expansion and notification status display.
- [x] Run focused Green tests for Python and DSA Web.
- [x] Update SAL-P5-016 evidence doc, upstream patch registry, progress checklist, development status and review notes.
- [x] Run related P5/report/outbox suite, full pytest, compileall, dependency lock, immutable tag, DSA patch replay and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P5-016`.

## Recovery Anchors

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 已通过；G5 未通过.
- Completed entering task: `SAL-P5-001..015`.
- Current READY task: `SAL-P5-016` 引用 UI 与通知 Outbox.
- Implementation checkpoint entering task: `a816cf72 feat(P5): 实现可信 ResearchReport Renderer`.
- Latest status-sync checkpoint entering task: `f9e9c961 docs: 同步 SAL-P5-015 checkpoint hash`.
- Latest status-sync hash-anchor entering task: `65a0e446 docs: 记录 SAL-P5-015 状态同步 hash`.
- Latest status-review checkpoint entering task: `124f69a7 docs: 复核 SAL-P5-015 最新开发状态与恢复提示`.
- Latest status-review hash-anchor entering task: `ead0ca32 docs: 记录 SAL-P5-015 状态复核 hash`.
- Strict boundary: do not start `SAL-P5-017`, Gate G5, real Provider/LLM, Worker loop, Qlib runtime, production scheduler or formal backtest promotion.

## Implementation Notes

- Target UI presenter: `src/serenity_alpha_lab/application/report_delivery.py`.
- Target Outbox repository: `src/serenity_alpha_lab/repositories/notification_outbox.py`.
- Target tests: `tests/application/test_report_delivery_ui.py`, `tests/repositories/test_notification_outbox.py`, `tests/architecture/test_architecture_boundaries.py`, and DSA Web patch tests.
- Expected contracts: `research.report_delivery_ui@1.0.0` and `research.notification_outbox@1.0.0`.
- Trusted input: `RenderedResearchReport` / `TrustedResearchReport` produced by `TrustedResearchReportRenderer`.
- UI output: report page JSON derived from authoritative JSON only, with claim -> citation -> evidence -> source/artifact expansion, dataset/time/model/cost/risk/disclaimer fields and notification status rows.
- Outbox output: report notification messages with tenant/channel/dedupe_key uniqueness, at-least-once lease/retry semantics and no real sender execution.
- DSA Web patch: add `/research-reports/:reportId` route, API client under `/api/v1/research/reports`, report page citation expansion controls and notification status display; no backend route registration or real notification sending.

## Review

- Implemented `research.report_delivery_ui@1.0.0` in `src/serenity_alpha_lab/application/report_delivery.py`; presenter expands trusted canonical JSON claims into citation/evidence/source/artifact payloads and declares GET-only report/notification routes.
- Implemented `research.notification_outbox@1.0.0` in `src/serenity_alpha_lab/repositories/notification_outbox.py`; SQLAlchemy store supports tenant/channel/dedupe idempotency, immutable conflict detection, lease/retry/sent/dead_letter metadata, and no sender side effects.
- Added DSA Web patch `DSA-PATCH-007` with `researchReports` API client, `/research-reports/:reportId` page, SidebarNav/i18n route integration, citation expansion UI and Outbox status cards; patch replay applies after `0001..0006`.
- Verification completed before commit: Python focused `6 passed`, DSA Web focused `4 files / 26 tests passed`, DSA lint/build PASS, related P5 suite `79 passed`, full pytest `490 passed, 3 skipped`, compileall/lock/tag/patch replay PASS.
- Scope held: did not start SAL-P5-017, Gate G5, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, notification sender, backend route registration or formal portfolio backtest promotion.
