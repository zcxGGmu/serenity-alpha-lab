# SAL-P6-002 Resource And Artifact Authorization Implementation Plan

> Scope: Complete only `SAL-P6-002` by adding framework-neutral object-level authorization for Run, Definition, Evidence, Report and Artifact downloads, including owner/tenant policy, short-lived signed Artifact URL contracts, audit records and Worker least-privilege grants. Do not start `SAL-P6-003+`, Secret Manager, SSRF/file-upload hardening, SCA gates, OpenTelemetry, backup/restore, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, notification sender, release packaging or formal backtest promotion.

## Checklist

- [x] Re-read required recovery, security, Auth/RBAC, Artifact, Evidence Store, Backtest API, Research Report Delivery and upstream patch docs.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Add failing contract tests for tenant/team/owner object authorization, guess-resistant IDs, signed Artifact URL expiry/scope, audit records and Worker least-privilege grants.
- [x] Run focused Red target and record expected missing-module failure.
- [x] Implement framework-neutral `application.resource_authorization` using SAL-P6-001 `AuthSubject`, `RbacPolicy`, `AuthPermission` and `ResourceScope`.
- [x] Export public resource-authorization symbols and add an architecture import guard proving no FastAPI/Authlib/JWT/requests/SQLAlchemy/Provider/LLM/Worker/Qlib runtime imports.
- [x] Add `docs/resource-artifact-authorization.md` evidence record and update progress/status registers for P6 `2/23`, total `108/129`, `SAL-P6-003` next.
- [x] Run focused Green, related Auth/RBAC + Artifact/Evidence/Backtest/Report suite, full pytest, compileall, dependency lock, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P6-002`.

## Recovery Anchors

- Phase: P6 安全、稳定性与发布加固.
- Gate: G5 已通过；G6 未通过.
- Completed entering task: `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, `SAL-P4-001..022`, `SAL-P5-001..018`, `SAL-P6-001`.
- Current READY task: `SAL-P6-002` 实现资源与 Artifact 授权.
- Implementation checkpoint entering task: `10397052 feat(P6): 完善认证与 RBAC`.
- Latest status-review final anchor entering task: `3f2160a7 docs: 固化 SAL-P6-001 状态复核 hash-anchor`.
- Strict boundary: do not start `SAL-P6-003+`, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, notification sender, release packaging or formal backtest promotion.

## Review

- Plan check-in completed in this file before code changes. Implementation stayed application-layer only and runtime-free.
- Red target failed as expected with missing `serenity_alpha_lab.application.resource_authorization` (`1 error`); architecture guard Red failed because the module file did not exist (`1 failed`).
- Implemented `security.resource_artifact_authorization@1.0.0` in `src/serenity_alpha_lab/application/resource_authorization.py`: tenant/team/private owner authorization, Artifact parent-read binding, deterministic audit records, percent-encoded HMAC signed URL issue/verify, duplicated signature/query rejection, and run-bound task-scoped Worker grants.
- Verification completed before checkpoint: focused Green `6 passed`, architecture guard `1 passed`, related suite `62 passed`, full pytest `510 passed, 3 skipped`, compileall PASS, dependency lock guard PASS (`Resolved 298 packages`), immutable tag `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, `git diff --check` PASS.
- Scope held: no Secret Manager/OS Keychain, FastAPI middleware, object-store adapter, real Provider/LLM, Worker loop, Qlib runtime, notification sender, production scheduler, release packaging or formal portfolio backtest promotion was started.
- Chinese implementation checkpoint: `33f76bad feat(P6): 实现资源与 Artifact 授权`; recovery docs are updated with the actual hash.

---

# SAL-P6-001 Post-Completion Status Review

> Scope: Refresh recovery state after completed `SAL-P6-001` and the latest user reminder. Do not start `SAL-P6-002` implementation, `SAL-P6-003+`, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, notification sender or formal backtest promotion.

## Checklist

- [x] Re-read current recovery docs, progress checklist, todo and lessons.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Update `docs/development-status.md` to show completed through `SAL-P6-001`, unfinished from `SAL-P6-002`, current checkpoints and recovery prompt.
- [x] Update `docs/development-progress-checklist.md` tail summary with the latest `SAL-P6-001` anchors.
- [x] Update `tasks/lessons.md` for the repeated instruction to automatically do this after every phase task.
- [x] Run document status-anchor checks and `git diff --check`.
- [x] Create a Chinese status-review checkpoint commit.

## Review

- Current phase remains P6 安全、稳定性与发布加固; Gate G5 is passed and G6 is not passed.
- Completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, `SAL-P4-001..022`, `SAL-P5-001..018`, `SAL-P6-001`; unfinished range starts at `SAL-P6-002`.
- Latest implementation checkpoint entering this review is `10397052 feat(P6): 完善认证与 RBAC`; latest status-sync checkpoint is `23878a6d docs: 同步 SAL-P6-001 checkpoint hash`; latest status-sync hash record is `a44e6483 docs: 记录 SAL-P6-001 状态同步 hash`; latest status-sync final anchor is `f4912114 docs: 固化 SAL-P6-001 状态同步 hash-anchor`.
- Status-review checkpoint created: `3cd35100 docs: 复核 SAL-P6-001 最新开发状态与恢复提示`; status-review hash-record checkpoint created: `86691933 docs: 记录 SAL-P6-001 状态复核 hash`.

---

# SAL-P6-001 Auth And RBAC Implementation Plan

> Scope: Complete only `SAL-P6-001` by freezing the desktop/standalone/team identity model, RBAC role/permission matrix, optional OIDC claim-mapping contract and API authorization requirements. Do not start `SAL-P6-002` object-level signed URL authorization, Secret Manager, SSRF/file-upload hardening, SCA gates, OpenTelemetry, backup/restore, Worker loop, real Provider/LLM, Qlib runtime, notification sender, production scheduler, release packaging or formal backtest promotion.

## Checklist

- [x] Re-read required recovery, P0-P5 evidence, P6 entry, security and upstream-patch docs.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Write SAL-P6-001 implementation plan in `docs/superpowers/plans/2026-07-30-auth-rbac.md`.
- [x] Add failing contract tests for desktop usability, team RBAC separation, optional OIDC claim mapping, API route requirements and deterministic redacted records.
- [x] Run focused Red target and record expected missing-module failure.
- [x] Implement framework-neutral `application.auth_rbac` identity, policy, route catalog and OIDC declaration/claim mapping.
- [x] Export public RBAC symbols and add an architecture import guard.
- [x] Add `docs/auth-rbac.md` evidence record and update progress/status registers for P6 `1/23`, total `107/129`, `SAL-P6-002` next.
- [x] Run focused Green, related suite, full pytest, compileall, dependency lock, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P6-001`.

## Review

- Plan check-in completed before code changes. Implementation stayed application-layer only and runtime-free.
- Red target failed as expected with missing `serenity_alpha_lab.application.auth_rbac` (`1 error`).
- Implemented `security.auth_rbac@1.0.0` in `src/serenity_alpha_lab/application/auth_rbac.py`: desktop local owner, standalone local roles, team-mode data/run/config/admin separation, tenant/team mismatch denies, optional OIDC declaration/claim mapping and deterministic API authorization catalog.
- Verification completed before checkpoint: focused Green `5 passed`, architecture guard `1 passed`, related suite `41 passed`, full pytest `503 passed, 3 skipped`, compileall PASS, dependency lock guard PASS (`Resolved 298 packages`), immutable tag `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, `git diff --check` PASS.
- Scope held: no `SAL-P6-002` signed URL/object policy, Secret Manager, SSRF/file-upload hardening, SCA gates, OpenTelemetry, Worker loop, real Provider/LLM, Qlib runtime, notification sender, production scheduler, release packaging or formal backtest promotion was started.
- Chinese implementation checkpoint created: `10397052 feat(P6): 完善认证与 RBAC`; status-sync checkpoint created: `23878a6d docs: 同步 SAL-P6-001 checkpoint hash`; status-sync hash-anchor checkpoint created: `a44e6483 docs: 记录 SAL-P6-001 状态同步 hash`.

---

# SAL-P5-018 Post-Completion Status Sync

> Scope: Record the actual `SAL-P5-018` checkpoint hash, refresh recovery prompts, and capture the repeated lesson to always do this automatically after every phase task. Do not start `SAL-P6-001` implementation, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, notification sender or formal backtest promotion.

## Checklist

- [x] Confirm latest checkpoint with `git log -8 --oneline`.
- [x] Update `docs/development-status.md` and next startup prompt with `e65172b1 docs(P5): 通过 Gate G5 可信研究评审`.
- [x] Update `docs/development-progress-checklist.md` tail summary with the same checkpoint and next task `SAL-P6-001`.
- [x] Update `tasks/todo.md` review to include the actual checkpoint hash.
- [x] Update `tasks/lessons.md` for the repeated automatic post-stage status-sync habit.
- [x] Create Chinese status-sync checkpoint commit.

## Review

- Status-sync checkpoint created: `7d4d2e65 docs: 同步 SAL-P5-018 checkpoint hash`; this docs-only sync records `e65172b1` as the Gate G5 checkpoint and keeps `SAL-P6-001` as next without starting P6 implementation or runtime scope.

---

# SAL-P5-018 Gate G5 Trusted Research Review Plan

> Scope: Complete only `SAL-P5-018` Gate G5 by adding the trusted research review record, executable gate test and state/checklist sync. Do not start real Provider/LLM, Worker loop, Qlib runtime, production scheduling, formal backtest promotion or P6 implementation beyond naming `SAL-P6-001` as next.

## Checklist

- [x] Re-read required recovery, evidence, report, security, evaluation and upstream patch docs.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Write SAL-P5-018 implementation plan in `docs/superpowers/plans/2026-07-30-gate-g5-trusted-research-review.md`.
- [x] Add failing Gate G5 review test covering document approval, trusted report expansion, Agent evaluation thresholds, model cache/budget and tool security boundaries.
- [x] Run focused Red target and record expected missing-review-document failure.
- [x] Add `docs/gate-g5-trusted-research-review.md` with conclusion, evidence matrix, accepted risks, P6 entry constraints and verification record.
- [x] Update progress checklist, development status, decision/evidence rows and next startup prompt for P5 `18/18`, total `106/129`, Gate G5 passed with accepted risks and `SAL-P6-001` next.
- [x] Run focused Green test, related P5 suite, full pytest, compileall, dependency lock, patch replay/check-only, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P5-018`.

## Review

- Completed Gate G5 trusted research review for `SAL-P5-018`; P5 is now `18/18`, total progress is `106/129`, and `SAL-P6-001` is the next READY entry.
- Red target failed as expected with missing `docs/gate-g5-trusted-research-review.md` (`1 failed, 1 passed`); focused Green passed (`2 passed`).
- Verification completed: related P5 suite `78 passed`, full pytest `497 passed, 3 skipped`, compileall PASS, dependency lock guard PASS, immutable tag `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, `git diff --check` PASS.
- DSA patch validation note: live patched worktree `--check-only` hit expected already-applied context conflict at `0004`; clean temp DSA worktree sequentially applied `0001..0007` successfully.
- Scope held: no real Provider/LLM, Agent/tool runtime, Worker loop, Qlib runtime, notification sender, production scheduler, P6 implementation or formal backtest promotion was started.
- Chinese checkpoint commit created: `e65172b1 docs(P5): 通过 Gate G5 可信研究评审`.

---

# SAL-P5-017 Post-Completion Status Review

> Scope: Update repository recovery state after completed `SAL-P5-017`. Do not start `SAL-P5-018`, Gate G5 execution, real Provider/LLM, Worker loop, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read current recovery docs and confirm actual git state.
- [x] Update `docs/development-status.md` to show completed through `SAL-P5-017`, unfinished from `SAL-P5-018`, current checkpoints and recovery prompt.
- [x] Update `docs/development-progress-checklist.md` tail summary so latest status-review anchors no longer point at `SAL-P5-016`.
- [x] Update `tasks/lessons.md` for the repeated instruction to automatically perform status docs, recovery prompt and checkpoint commits after each phase task.
- [x] Run document status-anchor checks and `git diff --check`.
- [x] Create Chinese status-review checkpoint and follow-up hash-anchor commit.

## Review

- Confirmed current phase remains P5 and Gate G5 is not passed.
- Completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001..017`, `SAL-P4-001..022`, `SAL-P5-001..017`; unfinished range starts at `SAL-P5-018` Gate G5 and P6 remains incomplete.
- Latest implementation checkpoint entering this review is `91d6d15b feat(P5): 建立 Agent 金标回归评测`; latest status-sync checkpoint is `4607532d docs: 同步 SAL-P5-017 checkpoint hash`; latest status-sync hash-anchor is `6e75580a docs: 记录 SAL-P5-017 状态同步 hash`.
- Status-review checkpoint created: `62cdcf23 docs: 复核 SAL-P5-017 最新开发状态与恢复提示`; status-review hash-anchor created: `839293a4 docs: 记录 SAL-P5-017 状态复核 hash`.

---

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
- Chinese implementation checkpoint created: `91d6d15b feat(P5): 建立 Agent 金标回归评测`. Status-sync checkpoint created: `4607532d docs: 同步 SAL-P5-017 checkpoint hash`; hash-anchor checkpoint created: `6e75580a docs: 记录 SAL-P5-017 状态同步 hash`.

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
