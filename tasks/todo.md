# SAL-P3-002 AlphaSift Wheel Intake Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-002` by building a reproducible offline AlphaSift Wheel from locked source commit `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, fixing source archive hash, wheel hash, SBOM, license inventory and internal artifact reference. Do not implement ScreeningProvider Adapter, start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, `docs/alphasift-source-review.md`, current Git status and recent commits.
- [x] Inspect P3 task scope, existing dependency lock policy, Docker AlphaSift cache handling, supply-chain baseline patterns, and artifact evidence layout.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-alphasift-wheel-intake.md`.
- [x] Add Red architecture tests for the intake script, manifest, SBOM, license inventory, checksum and review document.
- [x] Implement `scripts/build-alphasift-wheel-intake.sh` to download the codeload source archive, verify SHA-256, build with pinned `SOURCE_DATE_EPOCH`, generate committed evidence and run an offline no-deps install check.
- [x] Run the intake script and commit evidence under `docs/baselines/alphasift-wheel-intake/`.
- [x] Add `docs/alphasift-wheel-intake.md` with build commands, hashes, internal artifact URI, SBOM/license evidence, offline install proof and non-goals.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, this review and next-session prompt.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Stage only `SAL-P3-002` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and do not touch dirty files under `.worktrees/dsa-v3.26.1`.
- Do not add AlphaSift to root `pyproject.toml`, `uv.lock` or generated production `requirements.txt` in this task.
- Do not submit `.cache`, `.worktrees`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, source archives or Wheel binaries.
- Do not start `SAL-P3-003` ScreeningProvider Adapter, CandidateBatch, Factor Engine, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, Worker loops or DSA runtime source migration.
- Preserve Gate G2 boundaries: later Screening/Factor work must use concrete Dataset Versions and reuse Provider Policy/fallback trace, Dataset Catalog/Manifest, Quality Gate, Data Sync, PostgreSQL standalone Profile, PersistentTaskBackend, recoverable events, ProblemDetails, Trace, Artifact and Run/Stage/Event.

## Review: SAL-P3-002

- Added reproducible intake script `scripts/build-alphasift-wheel-intake.sh`; it verifies the locked codeload source archive hash, builds with `SOURCE_DATE_EPOCH=1783081838`, writes manifest/SBOM/license/checksum evidence, and verifies offline no-deps installation from the local wheelhouse.
- Generated committed evidence under `docs/baselines/alphasift-wheel-intake/`: `intake-manifest.json`, `sbom-cyclonedx.json`, `license-inventory.csv`, `license-summary.md`, and `alphasift-wheel.sha256`.
- Added `docs/alphasift-wheel-intake.md` with source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, reproducible wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`, internal artifact URI, offline install command and non-goals.
- Added `tests/architecture/test_alphasift_wheel_intake.py`; Red failed with `4 failed` before the script/evidence/doc existed, and Green passed with `4 passed`.
- Verification completed: intake script regeneration PASS with source SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a` and wheel SHA-256 `b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2`; related architecture suite `10 passed`; full pytest `242 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Review note: attempted read-only code-review/spec-review subagent dispatch after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty optional fields. Local review checked diff scope, manifest/SBOM/license consistency, non-goals, dependency install surface, untracked files and tag immutability.
- Updated progress checklist with `SAL-P3-002` DONE, P3 `2/17`, total `51/129`, `SAL-P3-003` READY, `DEC-049`, `AEV-051`, and `RSK-005` mitigation detail.
- Scope retained: no root `pyproject.toml` / `uv.lock` / production `requirements.txt` AlphaSift install surface change, no Wheel binary committed, no ScreeningProvider/Adapter, no CandidateBatch, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call, no DSA runtime source migration and no tag movement.
- Checkpoint: `50012b44 feat(P3): 构建 AlphaSift 离线 Wheel intake`.

## Review: SAL-P3-002 Status Sync

- Replaced recovery placeholders with actual implementation checkpoint `50012b44 feat(P3): 构建 AlphaSift 离线 Wheel intake`.
- Current next task remains `SAL-P3-003` only; Gate G3 remains未通过, progress remains P3 `2/17`, total `51/129`.
- Status-sync checkpoint will be the commit containing this review, titled `docs: 同步 SAL-P3-002 最新状态与恢复提示`; next startup should confirm the actual hash with `git log -1 --oneline`.

---

# SAL-P3-001 Status Refresh Plan

> Started: 2026-07-23
> Scope: Refresh recovery docs after `SAL-P3-001` checkpoint `4e6d5ee4`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P3-002` implementation in this sync.

## Checklist

- [x] Confirm current Git status and latest checkpoints.
- [x] Update `tasks/lessons.md` to record the repeated requirement to automatically sync status and provide a copyable next-start prompt after each phase task.
- [x] Update `docs/development-status.md` with explicit `4e6d5ee4` delivery checkpoint, current READY task, unfinished scope, strict guardrails, and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the actual `SAL-P3-001` checkpoint.
- [x] Update this review with completed/unfinished boundaries and verification plan.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P3-001 Status Refresh

- Confirmed latest implementation checkpoint: `4e6d5ee4 docs(P3): 完成 AlphaSift 源码审查与锁定`.
- Current recoverable state: Phase P3, Gate G3 not passed, completed `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..020`, `SAL-P3-001`; total progress `50/129`, P3 progress `1/17`.
- Current READY task: `SAL-P3-002` offline AlphaSift Wheel intake; no ScreeningProvider Adapter, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, or DSA runtime source migration in this status sync.
- Updated `tasks/lessons.md` with the repeated habit reminder: after every stage task, automatically sync recovery docs, evidence, `tasks/todo.md` review, and a copyable next-start prompt before final handoff.
- Verification: status-anchor scan found no active stale prior-task or old-progress markers; `git diff --check` PASS.

---

# SAL-P3-001 AlphaSift Source Review Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P3-001` by reviewing and locking AlphaSift source provenance, Apache-2.0 attribution, dependency surface, vulnerability/maintenance risk, known limitations, and replacement/stop-use conditions. Do not build the AlphaSift wheel, write the ScreeningProvider adapter, start Quant Core, start formal backtesting, start Evidence Agent, call real Provider/LLM services, or migrate DSA runtime source.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, `docs/gate-g2-data-task-review.md`, current Git status and recent commits.
- [x] Inspect P3 entry scope, Gate G2 constraints, AlphaSift/DSA existing integration docs, supply-chain baseline, Python dependency lock record, and current DSA AlphaSift pin.
- [x] Query AlphaSift upstream metadata, default branch, latest commit, tag state, repository license, dependencies, tests, open issues/PRs, contributors, and source archive hash.
- [x] Run current-resolution dependency SCA for the AlphaSift declared runtime dependencies using Python 3.11.
- [x] Write Red doc test requiring locked commit, source archive SHA-256, Apache-2.0 attribution, dependency list, SCA result, known limitations, replacement conditions, stop-use conditions, and P3 non-goals.
- [x] Create `docs/alphasift-source-review.md` with version decision, license/NOTICE treatment, vulnerability and maintenance review, platform boundary, upgrade/replacement/stop-use rules, and next task handoff to `SAL-P3-002`.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P3-001`, P3 progress, total progress, `SAL-P3-002` READY, decision/evidence registers, and any risk updates.
- [x] Update `docs/development-status.md` and this review with completed/unfinished scope, verification evidence, checkpoint wording, and next-session prompt.
- [x] Run target doc test, dependency locking test, full pytest, compileall, dependency lock guard, diff/tag checks, and Git status review.
- [x] Stage only `SAL-P3-001` files and create a Chinese checkpoint commit.

## Guardrails

- AlphaSift is accepted only as an L1 snapshot/candidate discovery plugin until later contract work proves otherwise.
- `SAL-P3-001` must not build or commit an AlphaSift wheel; that belongs to `SAL-P3-002`.
- Do not add AlphaSift to root `pyproject.toml`, `uv.lock`, or generated production `requirements.txt` in this task.
- Do not bypass Gate G2 Provider Policy/fallback trace, Dataset Catalog/Manifest, Quality Gate, Runtime Profile, ProblemDetails, Trace, Artifact, or Run/Stage/Event boundaries.
- Do not run real Provider calls, real LLM calls, Quant Core, formal backtesting, Evidence Agent, full Worker execution loops, Compose deployment, or broad DSA runtime source migration.
- Keep `upstream/dsa-v3.26.1` immutable and avoid submitting `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, temp source archives, or unrelated files.

## Review: SAL-P3-001

- Added `docs/alphasift-source-review.md`, locking `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf` with source archive SHA-256 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`, Apache-2.0 attribution, dependency list, current-resolution SCA limits, known limitations, upgrade/replacement rules and stop-use conditions.
- Added `tests/architecture/test_alphasift_source_review.py` to assert the review keeps the source commit, archive hash, license, dependency surface, SCA result, non-goals and stop conditions explicit. Red failed with missing review doc (`2 failed`); Green target passed (`2 passed`).
- Updated `docs/development-progress-checklist.md`: `SAL-P3-001` DONE, P3 `1/17`, total `50/129`, `SAL-P3-002` READY, `DEC-048`, `AEV-050`, and `RSK-005` mitigation detail.
- Updated `docs/development-status.md`: current task is `SAL-P3-002`, Gate G3 remains pending, completed range includes `SAL-P3-001`, and the next-start prompt points to offline Wheel intake.
- Verification: target AlphaSift review + dependency locking tests `6 passed`; full pytest `238 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Checkpoint: `4e6d5ee4 docs(P3): 完成 AlphaSift 源码审查与锁定`。
- Scope retained: no AlphaSift Wheel build, no dependency install surface change, no ScreeningProvider/Adapter, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call and no DSA runtime source migration.

---

# Gate G2 Data and Task Review Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-020` by executing Gate G2 review for Dataset, Provider and persistent task foundations. Reuse P2 Dataset, Provider, PostgreSQL standalone Profile, PersistentTaskBackend, recoverable task event stream, ProblemDetails, Trace, Artifact and Data Sync evidence. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker runtime loops, frontend pages, Compose deployment, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-020` acceptance scope, Gate G1 constraints, P2 evidence records, Provider fallback, Dataset publication, Data Sync and task recovery boundaries.
- [x] Add a Gate G2 offline integration test proving versioned A-share Dataset publication, Provider conflict blocking, persistent task restart recovery, SSE replay and DSA single-stock compatibility path without real Provider calls.
- [x] Run target Gate G2 test, related P2 suite, full pytest, compile, lock, diff and immutable tag verification.
- [x] Create `docs/gate-g2-data-task-review.md` with Gate decision, evidence matrix, accepted risks, P3 entry constraints and verification outputs.
- [x] Update progress checklist, development status, risk/decision/evidence registers, this review and the next-session prompt.
- [x] Stage only `SAL-P2-020` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Gate G2 may approve entry into P3 screening/factor work only; it must not approve Quant Core, formal portfolio backtesting, Evidence Agent, live Provider/LLM calls, release deployment or full Worker execution loops.
- Dataset evidence must use immutable Dataset Version Manifest, Artifact hashes, schema hash, quality metadata, concrete trace/run/stage and explicit latest alias scope.
- Provider evidence must stay offline and contract-backed; stale/missing/error/quarantine/conflict paths must block success rather than silently averaging or advancing checkpoints.
- Task recovery evidence must keep database events authoritative; Celery/Redis routing remains injected/diagnostic and duplicate queue delivery must be neutralized by lease acquisition.
- DSA compatibility evidence must use injected offline manager/profile guard and must not instantiate the real DSA Provider manager.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-020

- Gate decision: `GO with accepted risks`; P2 data and persistent task foundations are complete `20/20`, and P3 starts at `SAL-P3-001`.
- Added `tests/gates/test_gate_g2_data_task_review.py`, covering offline AKShare fixture -> Provider Policy -> versioned A-share Dataset publication, cross-provider conflict quarantine, PersistentTaskBackend restart/SSE replay and DSA single-stock compatibility via injected offline manager.
- Added `docs/gate-g2-data-task-review.md` with Gate decision, evidence matrix, accepted risks and P3 entry constraints.
- Updated `docs/development-progress-checklist.md` with `SAL-P2-020` DONE, P2 `20/20`, total `49/129`, `SAL-P3-001` READY, `DEC-047`, `AEV-049`, and risk due-date updates for `RSK-002` / `RSK-004`.
- Updated `docs/development-status.md` to Phase P3, Gate G3 pending, completed range through `SAL-P2-020`, next READY task `SAL-P3-001`, and a copyable next-start prompt.
- Verification so far: Gate target `3 passed`; related P2 suite `80 passed, 3 skipped`; full pytest `236 passed, 3 skipped`; compileall PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, full Worker loop, Compose deployment, DSA runtime source migration or tag movement.

---

# P2 Recoverable Task Event Stream Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-019` by implementing recoverable task/run event streams with persisted `RunEvent`, SSE `Last-Event-ID` replay, queued orphan redispatch, stalled lease reconciliation, and temporary artifact cleanup. Reuse `PersistentTaskBackend` database-authoritative events, `TaskBackend.subscribe(after_event_id)`, PostgreSQL standalone Profile, ProblemDetails, TraceContext, Artifact temporary boundaries and Data Sync checkpoint semantics. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker execution loops, frontend pages, broad API endpoint migration or DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-019` acceptance scope, PersistentTaskBackend, TaskBackend Protocol, RunEvent domain model, ProblemDetails, TraceContext, ArtifactStore and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-recoverable-task-event-stream.md`.
- [x] Add Red tests for SSE `Last-Event-ID` replay, invalid cursor validation, persisted RunEvent replay after restart, queued orphan redispatch, stalled lease requeue and temporary artifact cleanup.
- [x] Extend `repositories.persistent_task_backend` with persisted run events and queued-orphan redispatch without making queue state authoritative.
- [x] Implement `services.task_event_stream` with SSE frame DTOs, trace-safe event mapping, Last-Event-ID parsing and orphan/stalled reconciler.
- [x] Export service/repository symbols and preserve architecture boundaries without touching DSA runtime source, Provider SDKs, Quant Core or Evidence Agent.
- [x] Add acceptance evidence documentation for `SAL-P2-019`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-019` files and create the required Chinese checkpoint commit. Checkpoint: `15c3d555 feat(P2): 实现可恢复任务事件流`.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Database events remain authoritative; Celery/Redis delivery metadata is diagnostic and duplicate queue deliveries must be neutralized by DB lease acquisition.
- SSE recovery must replay from persisted events using monotonic event IDs; invalid `Last-Event-ID` maps to ProblemDetails-compatible validation failure.
- Reconciler may requeue stalled leases and redispatch old queued tasks, but must not mark stalled work as failed or execute handlers.
- Temporary cleanup may remove only configured artifact temp files older than cutoff; never delete blobs/manifests or Evidence artifacts.
- Tests use local SQLite and injected fake routers only; no real Provider/LLM/network calls, Quant Core, formal backtest or Evidence Agent.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-019

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.services.task_event_stream'`.
- Green implementation: added `services.task_event_stream` with `ServerSentEvent`, `TaskEventStreamService`, `TaskEventReconciler`, `TaskEventReconcilerSummary` and `parse_last_event_id()`, plus service exports.
- Persistence coverage: extended `PersistentTaskBackend` with `serenity_run_events`, `record_run_event()`, `subscribe_run_events()` and `redispatch_queued_orphans()`; task replay still uses `TaskBackend.subscribe(after_event_id)`.
- Recovery coverage: tests cover SSE `Last-Event-ID` replay, invalid cursor `ValidationProblem`, RunEvent persistence after backend restart, queued orphan redispatch, stalled lease requeue, duplicate-delivery lease guard and tmp-only artifact cleanup.
- Verification: target task event stream tests `8 passed`; related TaskBackend/Repository/API/Architecture suite `40 passed, 3 skipped`; full pytest `233 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no full Worker execution loop, formal API endpoint, frontend EventSource page, Compose service, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 PersistentTaskBackend Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-018` by implementing a database-authoritative `PersistentTaskBackend` with Celery/Redis queue routing boundaries, append-only task events, worker lease/heartbeat primitives, cancellation request recording, and expired-lease requeue. Reuse `TaskBackend` Protocol, Run/Event semantics, SQLAlchemy database profile, Alembic preflight assumptions, ProblemDetails-compatible errors, Trace/Artifact boundaries, Dataset/Provider scheduling constraints, and Data Sync Scheduler handoff. Do not start Quant Core, formal backtesting, Evidence Agent, real Provider/LLM calls, full Worker execution loops, API endpoints, SSE recovery, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-018` acceptance scope, TaskBackend Protocol, DSA facade, Run/Stage/Event domain model, database profile, repository contract patterns and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-persistent-task-backend.md`.
- [x] Add Red tests for persisted submit/get/subscribe after backend restart, idempotency replay, explicit task-id conflict, queue routing, cancellation request, lease heartbeat, completion and expired-lease requeue.
- [x] Implement `repositories.persistent_task_backend` with SQLAlchemy tables, `PersistentTaskBackend`, injected `CeleryTaskQueueRouter`, route DTOs, append-only events and lease helpers.
- [x] Export repository symbols and preserve architecture boundaries without importing Celery/Redis into application/domain/datasets or touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-018`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-018` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Database task/run rows and append-only task events are authoritative; Celery/Redis delivery metadata is diagnostic and must not become the source of truth.
- Queue payloads carry task/run IDs, task type and small routing metadata only; DataFrame, prompt text, Provider raw responses and large outputs remain Artifact-backed or out of scope.
- Worker helpers may claim leases, heartbeat, complete, fail and requeue expired leases; they must not execute Quant Core, formal backtest, Evidence Agent, Provider SDKs, LLM calls or DSA runtime tasks in this checkpoint.
- Tests use local SQLite and injected fake Celery-like routers only; optional live PostgreSQL contract remains guarded by `SERENITY_TEST_POSTGRES_URL`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-018

- Checkpoint: `94fd6dac feat(P2): 实现 PersistentTaskBackend`.
- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.persistent_task_backend'`.
- Green implementation: added `PersistentTaskBackend`, `TaskQueueRoute`, `TaskLease`, `TaskQueueRouter`, `CeleryTaskQueueRouter` and `NoopTaskQueueRouter` under `repositories.persistent_task_backend`, plus repository package exports.
- Persistence coverage: database tables `serenity_task_backend_runs` and `serenity_task_backend_events` are authoritative; backend restart preserves `TaskSnapshot`, `subscribe(after_event_id)` replays monotonic task events, and idempotency key replay avoids duplicate dispatch.
- Queue/worker coverage: injected Celery-like router sends only `task_id/run_id/task_type`; tests cover route mapping, cancel-request event, lease claim, heartbeat, completion and expired lease requeue.
- Verification: target persistent backend tests `5 passed`; related TaskBackend/Repository/API/Architecture suite `35 passed, 3 skipped`; full pytest `225 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no full Worker execution loop, API endpoint, SSE `Last-Event-ID`, orphan Reconciler, Compose service, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 PostgreSQL Standalone Profile Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-017` by establishing the PostgreSQL standalone Profile foundations: database configuration, connection pool, readiness checks and a shared Repository Contract suite. Reuse `SAL-P1-012` Alembic helpers and `SAL-P1-014` Runtime Profile; do not start Worker lease, PersistentTaskBackend execution, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-017` acceptance scope, Runtime Profile, Alembic storage migration helpers, existing Repository boundaries, TaskBackend contract and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-postgresql-standalone-profile.md`.
- [x] Add Red tests for standalone PostgreSQL URL resolution, SQLite defaults, engine/pool safety settings, health checks and same Repository Contract semantics.
- [x] Implement `repositories.database` with settings DTOs, engine factory, readiness diagnostics and SQLAlchemy Repository Contract probe.
- [x] Export repository symbols and preserve architecture boundaries without touching DSA runtime source, Provider SDKs, Worker runtime, Quant Core or Evidence Agent.
- [x] Add acceptance evidence documentation for `SAL-P2-017`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, this review and the next-session prompt.
- [x] Stage only `SAL-P2-017` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The database profile layer may create SQLAlchemy engines, run lightweight readiness checks and provide Repository Contract probes only; it must not implement Celery/Redis Worker lease, task execution, Scheduler dispatch, Quant Core, formal backtest or Evidence Agent behavior.
- Tests use local SQLite and optional `SERENITY_TEST_POSTGRES_URL`; no real Provider/LLM/network data calls are allowed.
- Repository Contract semantics must normalize UTC time, `Decimal`, JSON and rollback behavior across SQLite/PostgreSQL rather than relying on dialect quirks.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-017

- Checkpoint: `195765f3 feat(P2): 建立 PostgreSQL standalone Profile`.
- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py -q` failed because `serenity_alpha_lab.repositories.database` did not exist.
- Green implementation: added `DatabaseProfileSettings`, `DatabaseDialect`, `resolve_database_profile()`, `create_database_engine()`, `check_database_ready()`, `RepositoryContractProbeRecord` and `RepositoryContractProbeRepository` under `repositories.database`, plus repository package exports.
- Profile coverage: standalone requires explicit `SERENITY_DATABASE_URL`; PostgreSQL uses `psycopg`, `pool_pre_ping`, pool size/overflow/timeout, `statement_timeout=30000`, redacted diagnostics and `application_name`; SQLite enables foreign keys, busy timeout, WAL for file DBs and `StaticPool` for memory DBs.
- Repository Contract coverage: SQLite and optional live PostgreSQL (`SERENITY_TEST_POSTGRES_URL`) share one suite covering UTC datetime, `Decimal`, date, JSON normalization, duplicate-key conflict wrapping and rollback semantics.
- Verification: target profile/repository/storage tests `10 passed, 3 skipped`; related repositories/config/API/architecture suite `50 passed, 3 skipped`; full pytest `220 passed, 3 skipped`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; `psycopg` import smoke `3.3.4`; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Compose service, PersistentTaskBackend execution, Worker lease/heartbeat, Celery/Redis, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, DSA runtime source migration or tag movement.

---

# P2 SAL-P2-016 Status Refresh Plan

> Started: 2026-07-23
> Scope: Reconfirm recoverable development status after `SAL-P2-016` checkpoints `cfadc415` and `70f82cee`, update lessons for the repeated habit reminder, and keep the next-start prompt ready for `SAL-P2-017`.

## Checklist

- [x] Re-read current Git status, recent commits, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, and `tasks/todo.md`.
- [x] Confirm completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..016`; unfinished work resumes at `SAL-P2-017`.
- [x] Update `tasks/lessons.md` to record the repeated requirement to automatically sync status and provide a copyable next-start prompt after each phase task.
- [x] Refresh `docs/development-status.md`, `docs/development-progress-checklist.md`, and this review with the latest checkpoint anchors and constraints.
- [x] Run status-anchor scans and `git diff --check`, then create the required Chinese status checkpoint commit.

## Review: SAL-P2-016 Status Refresh

- Confirmed latest implementation checkpoint: `cfadc415 feat(P2): 实现增量同步与交易日调度`.
- Confirmed previous status-sync checkpoint: `70f82cee docs: 同步 SAL-P2-016 最新状态与恢复提示`.
- Current recoverable state remains P2 Data/Persistent Tasks, Gate G2 not passed, completed `45/129`, P2 `16/20`, next READY task `SAL-P2-017 PostgreSQL standalone Profile`.
- Scope constraints remain unchanged: no Worker lease, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, tag movement, destructive Git operation, or generated artifact submission.

---

# P2 Data Sync Scheduler Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-016` by implementing incremental data sync planning and trading-day scheduling with checkpoint, lookback window, lock protection, failure retry semantics, and backfill commands. Reuse Trading Calendar, Dataset Catalog/Manifest, Provider Policy/fallback trace, Run/Stage/Event, Trace scalar IDs, and existing Dataset boundaries. Do not start Quant Core, formal backtesting, Evidence Agent, PersistentTaskBackend, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, `docs/ai-stock-quant-platform-development-plan.md`, `docs/gate-g0-baseline-review.md`, current Git status and recent commits.
- [x] Inspect `SAL-P2-016` acceptance scope, Trading Calendar, Dataset Catalog, Raw Daily Bars incremental merge, Provider Policy fallback trace, Run lifecycle, and architecture guardrails.
- [x] Add Red tests for incremental scheduling, non-trading-day skip, checkpoint lookback, lock contention, failed Provider retry without checkpoint advance, idempotent completed-date recording, and historical backfill command planning.
- [x] Implement `services.data_sync` with checkpoint/lock store, `DataSyncScheduler`, `DataSyncRun`, and `DataBackfillCommand` without importing Provider SDKs or mutating Dataset modules.
- [x] Export service symbols and preserve architecture boundaries without touching DSA runtime source, Worker runtime, Quant Core, Evidence Agent, or real Provider/LLM paths.
- [x] Add acceptance evidence documentation for `SAL-P2-016`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-016` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Data sync scheduling consumes existing offline Dataset/Provider artifacts and injected Provider Policy outcomes only; it must not instantiate Provider SDKs, call DSA `DataFetcherManager`, probe networks, or publish real Provider data.
- Incremental runs must use concrete trading dates from `TradingCalendarDataset`, concrete `DatasetVersionManifest` lineage from Catalog, and explicit checkpoint state; `latest` remains discovery-only outside formal runs.
- Failed, quarantined, or exhausted Provider Policy outcomes must not advance checkpoint or create a success illusion; retries and backfills must remain idempotent.
- Tests use synthetic offline fixtures and local deterministic state only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-016

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/services/test_data_sync.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.services.data_sync'`.
- Checkpoint: `cfadc415 feat(P2): 实现增量同步与交易日调度`.
- Green implementation: added `DataSyncScope`, `DataSyncCheckpoint`, `DataSyncLock`, `LocalDataSyncStateStore`, `DataSyncScheduler`, `DataSyncPlan`, `DataBackfillCommand`, `DataSyncTradeDateResult` and `DataSyncRun` under `services.data_sync`, plus public service exports.
- Scheduling coverage: incremental plans use `TradingCalendarDataset`, checkpoint `last_completed_trade_date`, `lookback_window`, non-trading-day skip records and optional `LocalDatasetCatalog` latest lineage; backfill defaults to missing-only and supports explicit completed-date replay.
- Checkpoint and lock coverage: local state persists deterministic JSON checkpoint, validates completed/last-completed consistency, uses file `O_EXCL` scope locks, releases locks on complete/fail via `finally`, and treats duplicate successful trade dates idempotently.
- Provider Policy coverage: only `ProviderPolicyStatus.SELECTED` with a concrete Dataset version advances checkpoint; `EXHAUSTED` / `QUARANTINED` record failure and preserve retry eligibility without success illusion.
- Verification: target data sync test `5 passed`; related Trading Calendar/Catalog/Provider Policy/Run lifecycle/Architecture suite `35 passed`; full pytest `214 passed`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Provider SDK import, DSA `DataFetcherManager`, real Provider/LLM/network call, Bronze/Dataset publish, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, scheduled probe, DSA runtime source migration or tag movement.

---

# P2 SAL-P2-015 Status Sync Plan

> Started: 2026-07-23
> Scope: Refresh recoverable development status after `SAL-P2-015` checkpoint `378ba734`. Make completed/unfinished boundaries explicit, update the next-start prompt, and record the user's repeated habit reminder in project lessons.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, `docs/development-progress-checklist.md`, current Git status and recent commits.
- [x] Replace ambiguous checkpoint placeholders with actual `SAL-P2-015` implementation hash `378ba734`.
- [x] Confirm completed range is `SAL-P0-001..013`, `SAL-P1-001..016`, `SAL-P2-001..015`; unfinished work resumes at `SAL-P2-016`.
- [x] Update `tasks/lessons.md` so future phase-task completion automatically performs status snapshot, progress checklist, evidence, review and next-start prompt synchronization.
- [x] Run status-anchor scans and whitespace diff verification.
- [x] Stage only status-sync documentation files and create the required Chinese checkpoint commit.

## Review: SAL-P2-015 Status Sync

- Updated `docs/development-status.md` and `docs/development-progress-checklist.md` to use actual implementation checkpoint `378ba734 feat(P2): 实现 Provider Policy 与 fallback trace`.
- Preserved current executable task as `SAL-P2-016` and kept Gate G2 as not passed.
- Recorded the user's habit reminder in `tasks/lessons.md`, including the rule that implementation checkpoint hashes must be explicit after each phase task.
- Next-start prompt now points to `SAL-P2-016` and repeats the profile, Provider Policy/fallback trace, Dataset, ADR/Gate and no-early-Quant/Evidence constraints.

---

# P2 Provider Policy Fallback Trace Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-015` by adding an offline Provider Policy and fallback trace layer. Select sources by capability, market, freshness, required fields, data-quality status, and cross-provider conflict threshold. Reuse Provider domain contracts, Provider contract fixtures, Trace scalar attribution, Data Quality status semantics, Dataset publication quarantine vocabulary, and ProblemDetails-compatible validation boundaries. Do not call real Providers/LLMs, do not implement Worker runtime, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, scheduled probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect `SAL-P2-015` acceptance scope, Provider fixtures, Provider domain contracts, quality/publication semantics, API error mapping, and architecture guardrails.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-provider-policy-fallback-trace.md`.
- [x] Add Red tests for first fresh complete source selection, stale/missing-field fallback, Provider error trace, exhausted fallback, and cross-provider close-conflict quarantine.
- [x] Implement `integrations.data.provider_policy` with YAML-compatible policy DTOs, selection engine, fallback attempt trace, conflict records, and deterministic diagnostics.
- [x] Export policy symbols and preserve architecture boundaries without touching DSA runtime source or Provider SDKs.
- [x] Add acceptance evidence documentation for `SAL-P2-015`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-015` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Provider Policy consumes already-normalized offline `DataBatch` / `ProviderError` outcomes only; it must not instantiate Provider SDKs, call DSA `DataFetcherManager`, probe networks, publish Datasets, or mutate Provider fixture snapshots.
- Successful Provider data can still be rejected for stale freshness, missing required fields, quarantine/blocking quality status, schema mismatch, or cross-source conflict.
- Cross-provider conflicts over threshold enter quarantine and must not be hidden by averaging or silent overwrite.
- Tests use synthetic offline fixture cases and local deterministic records only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-015

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_policy'`.
- Green implementation: added `ProviderPolicy`, `ProviderPolicySource`, `ProviderSelectionRequest`, `ProviderPolicyEngine`, `ProviderFallbackAttempt`, `ProviderConflictRecord`, `ProviderFallbackTrace` and `ProviderSelectionResult` under `integrations.data`.
- Selection coverage: first fresh complete source wins by policy priority; stale `DataBatch`, dataset mismatch, missing required fields and `DataQualityStatus.BLOCKING` trigger rejection/fallback; Provider errors are recorded as `provider_<category>` and exhausted attempts return no selected batch.
- Conflict coverage: cross-provider `close` differences over configured bps threshold return `quarantined`, record provider values and primary key, and do not average or silently overwrite.
- Verification: target Provider Policy test `6 passed`; related Provider/Quality/Publication/API/Architecture suite `59 passed`; full pytest `209 passed`; `compileall` PASS; dependency lock PASS; `git diff --check` PASS; immutable `upstream/dsa-v3.26.1` tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope retained: no Provider SDK import, DSA `DataFetcherManager`, real Provider/LLM/network call, Bronze/Dataset write, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, scheduled probe, DSA runtime source migration or tag movement.

---

# P2 Provider Contract Fixtures Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-014` by adding an offline Provider contract fixture corpus for AKShare, efinance, Tushare, BaoStock, and YFinance. Cover sanitized responses, schema bindings, timeout, empty-data, and field-drift cases. Reuse Provider domain contracts, DSA Provider Adapter semantics, Arrow Schema Registry, Trace/Run/Stage scalar attribution, ProblemDetails-compatible provider errors, and Dataset publication boundaries. Do not implement fallback policy, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Provider contract, DSA adapter, Arrow Schema Registry, docs, and tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-provider-contract-fixtures.md`.
- [x] Add Red tests for offline Provider fixture coverage, success batch conversion, timeout/empty/schema-drift errors, deterministic sanitized snapshots, and SDK import avoidance.
- [x] Implement `integrations.data.provider_contract_fixtures` with frozen DTOs, default corpus, Provider `DataBatch` conversion, ProviderError mapping, schema validation, and snapshot writer.
- [x] Export fixture symbols and preserve architecture boundaries without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-014`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-014` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Provider fixtures are offline contract samples only; they must not choose fallbacks, probe live endpoints, instantiate Provider SDKs, or call DSA `DataFetcherManager`.
- Fixtures may expose sanitized raw responses, expected schema metadata, normalized records, and expected error categories; they must not contain secrets, tokens, cookies, absolute local paths, prompts, or personal data.
- Tests use synthetic offline rows and local deterministic JSON only; no real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-014

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.data.provider_contract_fixtures'`.
- Green implementation: added `ProviderContractFixtureCatalog`, `ProviderContractFixtureCase`, `ProviderFixtureSchema`, `ProviderFixtureStatus`, `default_provider_contract_fixture_catalog()` and `write_provider_fixture_snapshots()` under `integrations.data`.
- Fixture coverage: AKShare、efinance、Tushare、BaoStock 和 YFinance all have offline success samples; YFinance covers US and HK basic paths; timeout, empty and schema-drift cases map to `retryable`, `data_invalid` and `schema_drift`.
- Snapshot coverage: generated deterministic sanitized JSON files under `docs/baselines/provider-contract-fixtures/`, with raw-response SHA-256, Provider-facing schema and `dataset.bars_1d_raw@1.0.0` Arrow schema hash.
- Verification: target fixture test `4 passed`; related Provider/Schema/API/Architecture suite `58 passed`; full pytest `203 passed`; compileall, dependency lock, `git diff --check`, snapshot secret scan and immutable tag checks passed. Checkpoint: `5016ced6 feat(P2): 建立 Provider 契约 Fixture`.
- Scope retained: no fallback policy beyond expected error-category fixture labels, no real Provider/LLM/network calls, no PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

## Review: SAL-P2-014 Status Refresh

- User requested another latest-status refresh and a reusable next-start prompt after `SAL-P2-014`.
- Confirmed current state from Git: latest implementation checkpoint `5016ced6 feat(P2): 建立 Provider 契约 Fixture`; previous status-sync checkpoint `8c70cde5 docs: 同步 SAL-P2-014 最新开发状态与恢复提示`.
- Confirmed ledgers remain: P0 `13/13`, P1 `16/16`, P2 `14/20`, total `43/129`; Gate G2 is not passed.
- Updated recovery anchors in `docs/development-status.md`, `docs/development-progress-checklist.md`, and `tasks/lessons.md`; next executable task remains `SAL-P2-015 Provider Policy 与 fallback trace`.

---

# P2 Dataset Atomic Publication Plan

> Started: 2026-07-23
> Scope: Complete `SAL-P2-013` by adding quality-gated Dataset publication, quarantine/held state records, atomic latest promotion, and temporary file cleanup. Reuse Dataset Catalog/Manifest, Data Quality Report metadata, ArtifactStore manifest-last semantics, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible `ValueError` mapping. Do not implement fallback policy, Provider fixtures, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Dataset Catalog, ArtifactStore, Data Quality Rule Engine, docs, and tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-23-dataset-atomic-publication.md`.
- [x] Add Red tests for quality-gated latest promotion, warning/quarantine/blocking latest retention, quarantine records, failed-publish cleanup, and old latest retention.
- [x] Implement `datasets.publication` and narrow Catalog helpers for promote/latest and quarantine record persistence.
- [x] Export publication symbols and preserve architecture boundaries without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-013`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-013` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Only `DataQualityStatus.PASSED` may promote a Dataset version to `latest`; `warning`, `quarantine`, `blocking`, and failed publication attempts must leave the old latest pointer unchanged.
- Publication may persist immutable Dataset Manifest metadata and quarantine/held records only; it must not choose Provider fallback, average across Provider conflicts, or call real Providers.
- Tests use synthetic offline rows and local artifacts only; no real Provider/LLM/network calls.
- Temporary cleanup is limited to explicit temp roots (`ArtifactStore.tmp_root` and `LocalDatasetCatalog.tmp_root`) and must not delete immutable blobs, manifests, aliases, or unrelated directories.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-013

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.publication'`.
- Green implementation: added `QualityGatedDatasetPublisher`, `DatasetPublicationRequest`, `DatasetPublicationResult`, `DatasetPublicationStatus`, explicit `LocalDatasetCatalog.promote_to_latest()`, quarantine record persistence and bounded temp-root cleanup.
- Publication coverage: `passed` quality promotes `latest`; `warning`, `quarantine` and `blocking` write held/quarantine/blocking records and keep old latest; latest-promotion failure propagates and cleans explicit catalog/artifact tmp roots.
- Verification: target publication test `5 passed`; related dataset/artifact/API/architecture suite `66 passed`; full pytest `199 passed`; compileall, dependency lock, `git diff --check` and immutable tag checks passed. Checkpoint: `8edd723a feat(P2): 实现 Dataset 隔离区与原子发布`.
- Scope retained: no fallback policy, Provider fixture/probe, real Provider/LLM/network call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

---

# P2 Data Quality Rule Engine Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-012` by adding an offline data quality rule engine for Dataset snapshots. Reuse Dataset Catalog/Manifest metadata, Arrow Schema Registry declarations, ArtifactStore publishing, ProblemDetails-compatible `ValueError` mapping, trace/run/stage scalar attribution, and existing P2 Dataset record shapes. Do not implement SAL-P2-013 quarantine/latest blocking transactions, fallback policy, Provider fixtures, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset publish patterns, Arrow Schema Registry, Dataset Catalog, ArtifactStore and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-data-quality-rule-engine.md`.
- [x] Add Red tests for warning/quarantine/blocking rules, issue location, manifest metadata, report artifact publishing and ProblemDetails mapping.
- [x] Implement `quality.py` with rule protocol, built-in rules, report DTOs, deterministic report publishing and manifest metadata helper.
- [x] Export quality symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-012`.
- [x] Run target, related, full, compile, lock, diff and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review and the next-session prompt.
- [x] Stage only `SAL-P2-012` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The quality engine may classify reports as `passed`, `warning`, `quarantine` or `blocking`, and may provide manifest metadata; it must not block latest alias updates or implement atomic publish/quarantine cleanup. That remains `SAL-P2-013`.
- Tests use synthetic offline rows and local artifacts only; no real Provider/LLM/network calls.
- Rules must locate every issue by dataset, optional dataset version, partition, primary key, field and sample payload.
- Rule set version and quality status must be available for Dataset Manifest metadata without changing the immutable Catalog transaction semantics.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.

## Review: SAL-P2-012

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.quality'`; a later location hardening assertion also failed before `NullRatioDriftRule` was fixed.
- Green implementation: added `QualityDatasetSnapshot`, `DataQualityIssue`, `DataQualityReport`, `DataQualityEngine`, `DataQualitySeverity`, `DataQualityStatus` and built-in rules for unique primary keys, schema/type checks, OHLC, non-negative fields, null-ratio drift, trading continuity, return outliers, volume spikes and adjustment-factor jumps.
- Report coverage: every tested issue carries dataset/version/partition/field/primary-key/sample context; reports publish deterministic `ArtifactStore` JSON and expose Dataset Manifest metadata for rule set version, quality status, issue counts and report artifact hash.
- Verification: target data-quality test `4 passed`; related dataset/artifact/API/architecture suite `61 passed`; full pytest `194 passed`; compileall, dependency lock, `git diff --check` and immutable tag checks passed. Checkpoint: `3a846c6a feat(P2): 实现数据质量规则引擎`.
- Scope retained: no `SAL-P2-013` latest blocking/quarantine transaction, fallback policy, Provider fixture/probe, real Provider/LLM/network call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration or tag movement.

---

# P2 Dataset Catalog And Manifest Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-011` by adding Dataset Catalog and Manifest support for immutable dataset versions, file hashes, lineage, previous-version links, and mutable `latest` aliases. Reuse P1 `ArtifactStore`, P2 Dataset artifact manifests, Arrow Schema Registry, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation boundaries. Do not start data quality rules, fallback policy, real Provider calls, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset publish patterns, `ArtifactManifest`, `LocalArtifactStore`, Arrow Schema Registry, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-dataset-catalog-manifest.md`.
- [x] Add Red tests for immutable version manifests, file hashes, schema hash binding, lineage, previous version linkage, latest alias resolution, formal-run latest rejection, and atomic alias behavior.
- [x] Implement `catalog.py` with immutable manifest DTOs, version references, local repository persistence, alias resolution, and idempotent immutable publish checks.
- [x] Export catalog symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-011`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-011` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Catalog may register immutable Dataset version metadata and update mutable `latest` aliases only; it must not implement quality rules, quarantine/blocking behavior, fallback policy, Provider fixture probing, Worker runtime, Quant Core, formal backtest or Evidence behavior.
- Published dataset versions are immutable; same version ID can only be observed idempotently if the manifest content is byte-equivalent.
- Formal runs and experiments must resolve concrete `dataset_version` IDs; `latest` is allowed for discovery/research display only.
- Tests stay offline with synthetic artifacts and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.

## Review: SAL-P2-011

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q` failed during collection with `ImportError: cannot import name 'catalog' from 'serenity_alpha_lab.datasets'`.
- Green implementation: added `DatasetFileManifest`, `DatasetVersionManifest`, `DatasetVersionRef`, `DatasetReferencePurpose`, `DatasetVersionRefKind` and `LocalDatasetCatalog`; package exports now expose the catalog API through `serenity_alpha_lab.datasets`.
- Catalog coverage: tests cover immutable version manifest publishing, Artifact URI/SHA-256/file row-count capture, schema hash binding to `ArrowSchemaRegistry`, previous/input lineage, deterministic JSON persistence, idempotent republish and mutation rejection.
- Alias coverage: `latest` is persisted separately after the version manifest; research display can resolve latest, formal experiment resolution rejects latest and requires concrete dataset version; alias publish failure leaves the old latest pointer intact.
- Verification: target catalog `5 passed`; related dataset/artifact/architecture suite `45 passed`; full pytest `190 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed. Checkpoint: `8a77e4cf feat(P2): 实现 Dataset Catalog 与 Manifest`.
- Review note: subagent dispatch was attempted but blocked by client payload validation (`message/items` conflict). Local review checked import boundaries, deterministic manifest bytes, alias failure semantics, immutable version handling and strict scope.
- Scope retained: no data quality rule engine, warning/quarantine/blocking behavior, failed-Dataset latest blocking, fallback policy, Provider fixture/probe, real Provider/LLM call, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Arrow Schema Registry Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-010` by adding an offline, versioned Arrow Schema Registry for instrument master, raw daily bars, corporate actions, adjusted daily bars, and fundamentals. Reuse existing P2 Dataset schema constants, Artifact schema metadata, P1/P2 validation and ProblemDetails boundaries, and lazy optional PyArrow from the `quant` extra. Do not start fallback policy, real Provider calls, Dataset Catalog/latest alias, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset schema constants, deterministic JSON artifact payloads, and optional PyArrow dependency boundary.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-arrow-schema-registry.md`.
- [x] Add Red tests for default registry coverage, PyArrow schema conversion, semantic-version compatibility, duplicate registration, required-field validation, Pandas/Polars/Arrow round-trip stability, and optional PyArrow import behavior.
- [x] Implement `schema_registry.py` with immutable schema declarations, lazy PyArrow conversion, default P2 registrations, canonical hashing, and compatibility reports.
- [x] Add instrument master field schema/partition metadata and export registry symbols.
- [x] Add acceptance evidence documentation for `SAL-P2-010`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-010` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Registry may define Arrow schemas and compatibility checks only; it must not publish Dataset Catalog/latest aliases or enforce quality gates.
- PyArrow must remain lazily imported so root `core+dev` tests still import `serenity_alpha_lab.datasets` without the `quant` extra.
- Minor/patch schema versions may add backward-compatible nullable fields; deleting fields, changing types, or changing existing field meaning requires a new major version.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-010

- Red evidence: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.schema_registry'`.
- Green implementation: added `DatasetSchemaField`, `DatasetSchemaDeclaration`, `SchemaCompatibilityReport`, `SchemaCompatibilityStatus` and `ArrowSchemaRegistry`; default registry now covers instrument master, raw daily bars, corporate actions, adjusted daily bars and PIT fundamentals.
- Compatibility coverage: tests cover duplicate version rejection, semver ordering, nullable-field minor additions, required-field additions, type changes, removed fields, primary-key validation and breaking-change major version rules.
- Arrow coverage: tests cover lazy PyArrow conversion, schema metadata, canonical schema hash, Arrow validation, Arrow -> Pandas -> Arrow and Arrow -> Polars -> Arrow round-trip; Polars nullability loss is explicitly handled with `strict_nullability=False`.
- Reuse coverage: instrument master now exports `INSTRUMENT_MASTER_FIELD_SCHEMA` and `INSTRUMENT_MASTER_PARTITION_KEYS` and publishes deterministic JSON payloads with `field_schema` / `partition_keys`, matching later P2 Dataset patterns.
- Verification: schema registry target `6 passed`; instrument master related `9 passed`; P2 related suite `62 passed`; full pytest `185 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted code-reviewer subagent dispatch multiple times after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked schema ordering, optional PyArrow imports, semver compatibility logic, package exports, circular import risk, scope guardrails and deterministic payload changes.
- Scope retained: no fallback policy, real Provider call, Dataset Catalog/latest alias implementation, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA runtime source migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.
- Status sync: after user reminder, refreshed `docs/development-status.md`, `docs/development-progress-checklist.md`, this checklist, and `tasks/lessons.md` to make the completed/unfinished split, explicit `3e2056fe` delivery checkpoint, `SAL-P2-011` next task, and automatic status-sync habit recoverable in the next session.

---

# P2 PIT Fundamental Dataset Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-009` by adding an offline point-in-time fundamental Dataset. Reuse P2 Provider `DataBatch`/`Provenance`, Instrument Master Dataset, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Distinguish period, announced, available, ingested and revision timing. Do not start fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset patterns and SAL-P2-009 acceptance scope.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-22-pit-fundamental-dataset.md`.
- [x] Add Red tests for PIT schema, period/announced/available/ingested/revision timing, latest-as-of query, temporal confidence gate, Provider batch conversion, Bronze lineage, ArtifactStore publishing, invalid timing, and validation error mapping.
- [x] Implement `FundamentalRecord` and `FundamentalsDataset` with deterministic JSON Artifact publishing, query indexes, revision selection, incremental merge and formal-backtest temporal-confidence guard.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-009`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-009` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Use synthetic offline Provider `DataBatch` records only; do not instantiate or call a real Provider.
- PIT queries must filter `available_at <= decision_time`; latest revisions with later `available_at` must not leak into earlier decisions.
- Historical DSA-style records without trustworthy announcement time must be marked `temporal_confidence=unknown`, allowed only for research display and rejected for formal backtest queries.
- Dataset records may publish deterministic Artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, Worker runtime, Quant Core, formal backtest or Evidence behavior.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-009

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.fundamentals'`.
- Green implementation: added `FundamentalRecord`, `FundamentalsDataset`, `FundamentalPeriodType`, `TemporalConfidence` and `FundamentalQueryPurpose` with deterministic JSON Artifact publishing, Provider `DataBatch` conversion, query indexes and incremental primary-key replacement.
- PIT coverage: tests cover `period_end` / `announced_at` / `available_at` / `ingested_at` / `revision`, `available_at <= decision_time`, latest revision selection, future-revision exclusion, history query, Bronze lineage and source hash propagation.
- Temporal confidence coverage: legacy DSA-style records without trustworthy announcement time are marked `unknown`, allowed for research display, and rejected for formal backtest queries.
- Verification: target fundamentals `4 passed`; related dataset/provider/architecture suite `51 passed`; full pytest `179 passed`; compileall, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted read-only explorer subagent dispatch after tool discovery, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked diff scope, import boundaries, PIT timing invariants, formal-backtest gate, deterministic artifact payload and guardrails.
- Scope retained: no fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, DSA `fundamental_snapshot` formal migration, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Corporate Actions and Adjustments Plan

> Started: 2026-07-22
> Scope: Complete `SAL-P2-008` by adding deterministic corporate action and adjusted daily bars datasets. Reuse P2 Instrument Master, Trading Calendar, Raw Daily Bars, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start PIT/fallback policy, real Provider calls, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing P2 Dataset patterns and SAL-P2-008 acceptance scope.
- [x] Add Red tests for corporate action schema, cash dividends, bonus/share splits, rights offerings, pre/post adjustment factors, raw price immutability, query helpers, artifact publishing, invalid action data, and validation error mapping.
- [x] Implement `CorporateActionsDataset`, adjustment factor calculation, and `AdjustedDailyBarsDataset` over existing raw bars.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-008`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-008` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Use synthetic offline records only; do not instantiate or call a real Provider.
- Preserve raw daily bars unchanged; adjusted prices must be explicit records keyed by `instrument_id + trade_date + provider_id + adjustment`.
- Support cash dividends, bonus/share splits, rights offerings and forward/backward adjustment factors; do not implement portfolio ledger corporate-action accounting.
- Do not create PIT fundamental Dataset, fallback policy, Catalog/latest alias, quality gates, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or network probes.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-008

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_corporate_actions_adjustments.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.corporate_actions'`.
- Green implementation: added `CorporateAction`, `CorporateActionsDataset`, `CorporateActionType`, `AdjustmentMode`, `AdjustedDailyBar` and `AdjustedDailyBarsDataset` with deterministic JSON Artifact publishing, query indexes, explicit adjustment mode keys and incremental primary-key replacement.
- Adjustment coverage: cash dividends, bonus shares/share splits and rights issues are aggregated by instrument/ex-date/provider, priced from the previous raw close, and converted into `forward` and `backward` factors without mutating `RawDailyBarsDataset` records.
- Reuse coverage: P2 Instrument Master as-of validation, Trading Calendar trading-day validation, Raw Daily Bars input, Bronze lineage, P1 `ArtifactStore`, trace/run/stage scalar attribution and existing `ValueError -> validation_error` ProblemDetails mapping are covered by tests.
- Verification: target corporate actions `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `68 passed`; full pytest `175 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: local review found and fixed a provider-scope double-count risk by filtering company actions to the raw bar provider and adding a regression assertion. Attempted independent `code-reviewer` subagent dispatch, but the client rejected payload variants as duplicate `message/items` or empty override fields.
- Scope retained: no PIT fundamental Dataset, fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, Portfolio Ledger corporate-action accounting, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Raw Daily Bars Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-007` by adding a deterministic raw daily bars Dataset for unadjusted OHLCV/amount records. Reuse P2 Provider `DataBatch`/`Provenance`, Instrument Master Dataset, Trading Calendar Dataset, Bronze lineage, ArtifactStore, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start corporate actions/adjusted bars, PIT/fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, quality gates, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing Instrument Master Dataset, Trading Calendar Dataset, Provider daily-bar contract, Bronze raw store, ArtifactStore, ProblemDetails and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-raw-daily-bars-dataset.md`.
- [x] Add Red tests for raw daily bar schema, Provider batch conversion, key uniqueness, OHLC/volume/amount validation, instrument/calendar checks, source timestamp, Bronze lineage, query helpers, ArtifactStore publishing, and validation error mapping.
- [x] Implement `RawDailyBarsDataset` with immutable unadjusted bar records, offline indexes, Provider batch conversion and deterministic JSON ArtifactStore publishing.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-007`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-007` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Raw daily bars may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, adjusted bars, corporate actions, PIT/fallback policy, quality gates, Worker runtime, or Quant Core behavior.
- Consume injected/offline Provider `DataBatch` values only; do not instantiate or call a real Provider.
- Raw bars remain unadjusted; do not add split/dividend/corporate-action or adjusted price behavior.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-007

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.raw_daily_bars'`.
- Green implementation: added `RawDailyBar`, `RawDailyBarsDataset`, Arrow-compatible field schema constants, Provider `DataBatch` conversion, Instrument Master as-of validation, Trading Calendar trading-day validation, immutable offline indexes, deterministic JSON ArtifactStore publishing and primary-key replacement via `merge_incremental()`.
- Reuse coverage: P1/P2 `InstrumentId`, `Market`, Provider `DataBatch`/`Provenance`, `ArtifactStore`, Bronze `source_bronze_artifact_id`, Instrument Master Dataset, Trading Calendar Dataset, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests.
- Verification: target raw daily bars `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `59 passed`; full pytest `172 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted independent `code-reviewer` subagent dispatch multiple times, but the client rejected payload variants as duplicate `message/items` or empty override fields. Local review checked diff scope, imports, OHLC/amount/calendar/master validations, deterministic artifact payload, and guardrails; no Critical or Important issue found.
- Scope retained: no adjusted bars, corporate actions, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Trading Calendar Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-006` by adding a deterministic Trading Calendar Dataset with market time zones, trading dates, open/close sessions, lunch breaks, half-day/ad-hoc closure semantics, query caches, Bronze lineage and ArtifactStore publishing. Reuse P1/P2 Market/InstrumentId identity boundaries, Provider calendar contract shape, Trace/Run/Stage scalar attribution, ProblemDetails-compatible validation errors, ArtifactStore, Bronze lineage and the Instrument Master market model. Do not start raw daily bars, PIT/fallback policy, Dataset Catalog/latest alias, Arrow Schema Registry, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, network probes, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing InstrumentId/Market, Provider calendar contract, ArtifactStore, Bronze raw store, Instrument Master Dataset, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-trading-calendar.md`.
- [x] Add Red tests for market time zones, sessions, A-share holiday/half-day/ad-hoc closure policy, UTC/Asia-Shanghai boundaries, cached queries, Bronze lineage, ArtifactStore publishing, and validation errors.
- [x] Implement `TradingCalendarDataset` with immutable records, in-memory indexes, timezone/session query APIs and deterministic JSON ArtifactStore publishing.
- [x] Export dataset symbols and preserve architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-006`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-006` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-006

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_trading_calendar.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.trading_calendar'`.
- Green implementation: added `MarketSession`, `TradingSessionStatus`, `TradingCalendarDataset`, frozen market timezone mapping, explicit A-share holiday/half-day/ad-hoc closure semantics, UTC conversion helpers, in-memory query indexes, trading-day/previous/next/open-at query APIs and deterministic JSON `ArtifactStore` publishing.
- Reuse coverage: P1 `Market`, P1 `ArtifactStore`, Bronze `source_bronze_artifact_id`, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests; no DSA runtime source or real Provider path was imported.
- Verification: target trading calendar `3 passed`; related dataset/provider/bronze/API/trace/architecture suite `56 passed`; full pytest `169 passed`; py_compile, dependency lock, `git diff --check` and immutable tag check passed.
- Review note: attempted to use subagent tooling for independent exploration/review, but the client repeatedly rejected `spawn_agent` payload variants as duplicate `message/items` or empty override fields. Local senior review checked diff scope, import boundaries, timezone/session invariants, explicit-closure policy and guardrails.
- Scope retained: no raw daily Dataset, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Calendar records may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, raw daily bars, PIT/fallback policy, quality gates, Worker runtime, or Quant Core behavior.
- Use explicit `Market + trade_date` calendar records; do not infer holidays from current date, live Provider responses, or mutable network state.
- A-share holiday, half-day and ad-hoc closure policy is explicit-record based: closed records carry no open/close times, half-day records carry shortened sessions, and exceptional closures use a distinct status/note.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


---

# P2 Instrument Master Dataset Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-005` by adding a historical instrument master Dataset with validity-windowed securities and provider mappings. Reuse P1/P2 InstrumentId, Provider Symbol Mapping, ArtifactStore, Bronze lineage, Trace/Run/Stage scalar attribution, and ProblemDetails-compatible validation errors. Do not start trading calendar, raw daily bars, PIT/fallback policy, Dataset Catalog/latest alias, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing InstrumentId, Provider contract, ArtifactStore, Bronze raw store, Trace, ProblemDetails, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-instrument-master-dataset.md`.
- [x] Add Red tests for instrument schema, historical as-of lookup, provider mapping validity windows, uniqueness/overlap validation, Bronze lineage, and ArtifactStore publishing.
- [x] Implement `InstrumentMasterDataset` with deterministic JSON artifact publishing and offline query helpers.
- [x] Export dataset symbols and add/adjust architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-005`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-005` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-005

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.instrument_master'`.
- Green implementation: added `InstrumentMasterDataset`, `InstrumentMasterRecord`, `IndustryClassification`, `ProviderSymbolValidity`, listing status enum, as-of record/provider-mapping lookup, overlap/duplicate validation and deterministic JSON ArtifactStore publishing.
- Reuse coverage: canonical `InstrumentId`, `ProviderSymbolMapping`, Bronze `source_bronze_artifact_id`, `ArtifactStore`, trace/run/stage scalar attribution and existing ProblemDetails `ValueError -> validation_error` mapping are covered by tests.
- Verification: target instrument master `3 passed`; dataset/architecture suite `15 passed`; related domain/provider/artifact/repository/API/trace suite `81 passed`; full pytest `166 passed`; py_compile, dependency lock and immutable tag checks passed.
- Review note: attempted `code-reviewer` subagent dispatch after tool discovery, but the client rejected both item/message payload attempts as duplicate inputs. Local review checked diff scope, imports, validity-window semantics and guardrails; no DSA runtime import, real Provider/LLM call, PIT/fallback policy, Quant Core, formal backtest or Evidence Agent work was introduced.
- Scope retained: no trading calendar, raw daily bars, PIT fundamental Dataset, Dataset Catalog/latest alias, Arrow Schema Registry, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Instrument master may publish deterministic Dataset artifact bytes, but must not create Dataset Catalog/latest alias, Arrow Schema Registry, Silver/PIT tables, trading calendar, daily bars, fallback policy, or quality gate behavior.
- Provider mappings must be scoped by validity windows and must point back to canonical `InstrumentId`.
- Every record must carry Bronze source artifact lineage for auditability.
- Tests stay offline with synthetic records and make zero real Provider/LLM/network calls.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


---

# P2 Bronze Raw Data Layer Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-004` by adding a Bronze raw data layer that stores sanitized, compressed, content-addressed provider raw responses with auditable request metadata. Reuse P1/P2 ArtifactStore, Provider Provenance, TraceContext, ProblemDetails redaction boundaries, Run/Stage metadata, and compatibility constraints. Do not start Dataset/PIT/fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, and current Git state.
- [x] Inspect existing ArtifactStore, Provider Provenance/DataBatch, Trace redaction, and architecture boundary tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-bronze-raw-data-layer.md`.
- [x] Add Red tests for Bronze artifact schema, gzip compression, hash metadata, provider/request/time traceability, Run/Stage attribution, and secret/Cookie/PII redaction before disk.
- [x] Implement `BronzeRawStore` over the existing `ArtifactStore` contract with deterministic JSON + gzip payloads and local query helpers.
- [x] Export repository symbols and add architecture coverage without touching DSA runtime source.
- [x] Add acceptance evidence documentation for `SAL-P2-004`.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-004` files and create the required Chinese checkpoint commit.

## Review: SAL-P2-004

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.bronze_raw_store'`.
- Green implementation: added `BronzeRawStore`, immutable `BronzeRawArtifact`, deterministic JSON envelope + `gzip` compression, `ArtifactStore` publishing, `get_envelope()`, local `find_raw_artifacts()` scanning, and repository exports.
- Audit coverage: envelope records provider/operation, sanitized request parameters, requested/fetched/source timestamps, source raw hash, sanitized raw payload hash, field lineage, trace/run/stage IDs and archive retention.
- Security coverage: request and raw-response payloads are recursively sanitized before bytes reach `ArtifactStore`; tests assert API key, token, Authorization, Cookie/Set-Cookie, email, phone/mobile and identity-card values are absent from manifest/blob/decompressed bytes.
- Verification: Bronze target `6 passed`; related repositories/provider/trace/architecture suite `56 passed`; full pytest `162 passed`; py_compile, dependency lock, immutable tag check and `git diff --check` passed.
- Scope retained: no Dataset Catalog, Silver/PIT, quality gate, fallback policy, PersistentTaskBackend, Worker runtime, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Bronze may store sanitized raw provider payloads and request metadata only through the existing ArtifactStore boundary; it must not write Dataset Catalog, Silver/PIT tables, quality gates, or fallback policy.
- Store compressed payloads deterministically and preserve both source raw-response hash from Provider Provenance and sanitized payload hash for audits.
- Redact API keys, tokens, Authorization, Cookie/Set-Cookie, prompts/bodies, e-mail, phone/mobile and common identity fields before bytes are handed to ArtifactStore.
- Require Run attribution through `produced_by_run_id` or `Provenance.run_id`; carry stage and trace IDs when available.
- Keep tests offline with synthetic raw responses; make zero real Provider/LLM/network calls.

---

# P2 Symbol Compatibility Migration Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-003` by wrapping DSA `normalize_stock_code` compatibility semantics with `InstrumentId` and explicit Provider Symbol Mapping. Reuse the P1 `InstrumentId` domain model and P2 DSA Provider Adapter facade. Do not start Bronze/Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA runtime source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, current git state, P1 InstrumentId, and P2 Provider Adapter.
- [x] Inspect DSA `normalize_stock_code` implementation, P0 conversion tests, and current Serenity adapter call path.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-symbol-compatibility-migration.md`.
- [x] Add Red tests for P0-compatible stock-code conversions, ambiguity errors, validity windows, provider mappings, and adapter wrapper usage.
- [x] Implement DSA symbol compatibility mapper and immutable mapping record.
- [x] Wire `DsaProviderCompatibilityAdapter` and `DsaStockHistoryCompatibilityFacade` through the mapper.
- [x] Add architecture guard and evidence documentation.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Stage only `SAL-P2-003` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- Keep legacy payload `stock_code` behavior compatible, but store/carry canonical `instrument_id` for new provider paths and provenance.
- Bare 6-digit symbols may be accepted only through explicit legacy market context; strict domain conversion must keep raising ambiguity errors.
- Do not persist naked symbols as cross-market primary keys; use `InstrumentId.canonical`.
- `SAL-P2-003` is not Bronze/Dataset/PIT/fallback-policy/PersistentTaskBackend work. Gate G2 remains not passed.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-003

- Red evidence: `.cache/dsa-p0/venv/bin/python -m pytest ...` could not run because the documented P0 venv is absent locally; fallback `uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_symbol_compatibility.py tests/integrations/test_dsa_provider_adapter.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.symbol_compatibility'`.
- Green implementation: added `DsaStockCodeCompatibilityMapper`, immutable `DsaStockCodeMapping`, and local `normalize_stock_code_compatible()` mirror for P0 DSA conversion cases; wired `DsaProviderCompatibilityAdapter` and `DsaStockHistoryCompatibilityFacade` through the mapper.
- Compatibility coverage: A-share SH/SZ/SS/BJ prefix/suffix, HK prefix/suffix zero-padding, JP/KR/TW Yahoo suffixes, US ticker, bare 6-digit ambiguity, explicit exchange conflicts, provider symbol mappings, and validity windows.
- Verification so far: target symbol/adapter suite `25 passed`; related symbol/adapter/domain/architecture suite `72 passed`; full pytest `155 passed`; py_compile and `scripts/verify-python-dependency-lock.sh` passed.
- Review note: attempted independent `code-reviewer` dispatch multiple times, but the client rejected payload variants as duplicate message/items inputs. Local diff review found no eager DSA runtime import; the only `data_provider` hit remains the intended lazy import in `provider_adapter.py`.
- Scope retained: no Bronze/Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.

---

# P2 Status Sync After DSA Provider Adapter

> Started: 2026-07-21
> Scope: Refresh latest development status after `SAL-P2-002` checkpoint `68e8fea9`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P2-003` implementation in this sync.

## Checklist

- [x] Confirm current git status and latest checkpoints.
- [x] Update `docs/development-status.md` with explicit `68e8fea9` delivery checkpoint, current READY tasks, unfinished scope, and next-session prompt.
- [x] Update `docs/development-progress-checklist.md` next-step anchor with the actual `SAL-P2-002` checkpoint.
- [x] Record the repeated habit in `tasks/lessons.md`.
- [x] Re-scan state anchors and run `git diff --check`.
- [x] Stage only status-sync docs and create the required Chinese status checkpoint commit.

## Review: P2 Status Sync After DSA Provider Adapter

- Confirmed current branch is `codex/p0-baseline-status`, ahead of origin by 31 before this docs sync, with latest functional checkpoint `68e8fea9 feat(P2): 实现 DSA Provider 兼容适配器`.
- Confirmed completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, and `SAL-P2-001..002`; P2 progress remains `2/20`, total progress remains `31/129`, and Gate G2 remains not passed.
- Confirmed current READY tasks are `SAL-P2-003` and `SAL-P2-004`; `SAL-P2-003` is the preferred next implementation task, while `SAL-P2-004` can be prepared without starting Dataset/PIT/fallback policy or real Provider calls.
- Preserved scope boundaries: no code changes, no DSA source migration, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM call, no tag movement, and no generated/cache artifacts.

---

# P2 DSA Provider Compatibility Adapter Plan

> Started: 2026-07-21
> Scope: Complete `SAL-P2-002` by wrapping DSA `DataFetcherManager`/Pandas daily-bar output behind the frozen Provider domain contract. Reuse P1 Profile, ProblemDetails, TraceContext, Artifact/Run boundaries and Compatibility Facade patterns where they apply. Do not start Dataset/PIT, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM calls, or broad DSA source migration.

## Checklist

- [x] Re-read recovery docs, lessons, development plan, progress checklist, Gate G0 review, current git state, and P2 Provider contract.
- [x] Inspect DSA `DataFetcherManager` daily-data return shape, source handling, diagnostics behavior, and existing DSA market-routing tests.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-21-dsa-provider-compatibility-adapter.md`.
- [x] Add Red tests for the DSA Provider adapter, ProviderError mapping, CI profile guard, trace/provenance propagation, and feature-flag facade switching.
- [x] Implement `DsaProviderCompatibilityAdapter` and stock-history compatibility facade with injected manager support and lazy real-DSA import.
- [x] Add architecture guard and evidence documentation.
- [x] Run target, related, full, compile, lock, diff, and immutable tag verification.
- [x] Update progress checklist, development status, decision/evidence registers, this review, and the next-session prompt.
- [x] Attempt independent code review; tool rejected message/items payload variants, so complete and record local senior review fallback.
- [x] Stage only `SAL-P2-002` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The adapter may lazily import DSA from the isolated worktree, but tests must use injected fakes and make zero real Provider/LLM/network calls.
- Preserve the frozen Provider domain contract from `SAL-P2-001`; do not modify it unless a failing adapter contract exposes a real defect.
- `CI` profile must block constructing a default real DSA manager; injected stub managers remain allowed for offline tests.
- `SAL-P2-002` is not Dataset/Bronze/PIT/fallback-policy/PersistentTaskBackend work. Keep `RSK-004` open and Gate G2 not passed.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated files.


## Review: SAL-P2-002

- Red evidence: `uv run --extra core --extra dev python -m pytest tests/integrations/test_dsa_provider_adapter.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.integrations.dsa.provider_adapter'`.
- Green implementation: added `DsaProviderCompatibilityAdapter`, lazy `create_default_dsa_data_fetcher_manager()`, schema/row normalization, Provider provenance hashing/lineage/TraceContext propagation, ProviderError classification, and `DsaStockHistoryCompatibilityFacade` feature flag switching.
- Boundary review: no DSA runtime source was copied or modified; real `data_provider.base` is referenced only by `importlib.import_module()` inside the lazy factory; AST imports are limited to stdlib, P1 application facades, domain contracts and DSA entrypoint resolver.
- Verification: target adapter tests `8 passed`; related adapter/API/architecture suite `22 passed`; full pytest `137 passed`; py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.
- Review note: attempted to dispatch an independent `code-reviewer` agent multiple times, but the tool rejected both message-plus-items and items-only payload variants as duplicate inputs. Local review found no Critical or Important issues; the only `data_provider` hit is the intended lazy import string, and the only secret token hit is the redaction test fixture.
- Scope retained: no Dataset/Bronze/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, network probe, broad DSA migration, or `upstream/dsa-v3.26.1` tag movement. Gate G2 remains not passed.
- Checkpoint scope: stage only adapter code, adapter exports, tests, evidence docs, progress/status docs and this review; exclude `.worktrees`, `.cache`, `.venv`, pycache and unrelated files.

# P2 Status Sync After Provider Contract

> Started: 2026-07-21
> Scope: Refresh recovery docs after `SAL-P2-001` checkpoint `f7bc8ba8`, make completed vs unfinished work explicit, record the repeated status-sync habit, and provide a copyable next-session prompt. Do not start `SAL-P2-002` implementation in this sync.

## Checklist

- [x] Confirm current git status and latest checkpoints.
- [x] Update `docs/development-status.md` with explicit `f7bc8ba8` delivery checkpoint and `SAL-P2-002` READY continuation.
- [x] Update `docs/development-progress-checklist.md` next-step anchor.
- [x] Record the repeated habit in `tasks/lessons.md`.
- [x] Re-scan state anchors and run `git diff --check`.

## Review: P2 Status Sync After Provider Contract

- Confirmed current Phase remains P2, Gate G2 remains not passed, G0/G1 remain passed, progress remains P0 `13/13`, P1 `16/16`, P2 `1/20`, total `30/129`.
- Confirmed completed scope is `SAL-P0-001..013`, `SAL-P1-001..016`, and `SAL-P2-001`; `SAL-P2-002` is READY and not started.
- Updated recovery wording so the latest functional delivery checkpoint is explicit: `f7bc8ba8 feat(P2): 定义 Provider 领域契约`.
- Preserved scope boundaries: no DSA Adapter, Dataset/PIT, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider/LLM call, or broad DSA source migration.

---

# P2 Provider Domain Contract Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P2-001` by defining a pure-domain, synchronous Provider contract with capabilities, immutable `DataBatch`/`Provenance`, stable failure categories, offline Contract Tests, and reuse of the P1 Problem Details boundary. Do not implement the DSA Adapter, make real Provider/LLM calls, start Dataset/PIT/Quant/formal backtest work, or migrate DSA runtime source.

## Checklist

- [x] Re-read the required recovery documents, confirm Git state, and run the 103-test baseline.
- [x] Inspect P1 domain/application conventions, Gate G1 constraints, ADR-002, and the approved Provider protocol design.
- [x] Write the detailed implementation plan at `docs/superpowers/plans/2026-07-20-provider-domain-contract.md`.
- [x] Add Red tests for Provider capabilities, immutable provenance/batches, freshness, SHA/time validation, six error classes, and Protocol conformance.
- [x] Implement `domain/providers.py` and stable domain exports with no framework/vendor imports.
- [x] Add Red/Green coverage for mapping `ProviderError` through the existing sanitized `ProviderProblem` contract.
- [x] Run target, related, and full verification plus compile/lock/diff/tag checks.
- [x] Add `docs/provider-domain-contract.md` acceptance evidence.
- [x] Update the progress checklist, development status, decision/risk/evidence registers, this review, and the next-session prompt.
- [x] Request specification and code-quality reviews; resolve all material findings.
- [x] Stage only `SAL-P2-001` files and create the required Chinese checkpoint commit.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA runtime source isolated under `.worktrees/dsa-v3.26.1`.
- The domain contract must remain synchronous and stdlib-only except reuse of the pure-domain SHA-256 value validation; it must not import `application`, `integrations`, Pandas, Arrow, Provider SDKs, FastAPI, SQLAlchemy, or repositories.
- `RuntimeProfile` enforcement and `TraceContext` propagation belong to later application/integration callers; provenance carries only scalar correlation IDs and already-sanitized request metadata.
- Reuse `InstrumentId`, `ProviderProblem`, `ArtifactStore` boundaries, `Run/Stage/Event`, Alembic preflight, and Compatibility Facade semantics without implementing their later P2 consumers early.
- Keep `RSK-004` open and Gate G2 not passed. Do not mark `SAL-P2-002` or any Dataset/persistent task work complete.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## Review: SAL-P2-001

- Red evidence: `tests/domain/test_provider_contract.py` initially failed during collection with one `ModuleNotFoundError`; the API mapping test initially failed with `500 != 502` while its other 12 tests passed.
- Green implementation: added `src/serenity_alpha_lab/domain/providers.py` and public exports for Capability, ProviderCapabilities, ProviderWarning, Provenance, generic immutable DataBatch, six ProviderErrorCategory values, ProviderError retry policy, and synchronous runtime-checkable MarketDataProvider; added the existing Problem Details mapping and credential/path redaction coverage.
- Boundary review: Provider domain imports only stdlib plus existing pure-domain `ArtifactUri`, `InstrumentId`, and `Market`; architecture tests reject application/integration/vendor imports. Profile, TraceContext, ArtifactStore, Run/Stage/Event, Alembic, and Compatibility Facade remain explicit caller/follow-on boundaries.
- Review fixes: independent review found bytearray/custom-object immutability bypasses, non-finite retry delays, mutable scalar subclass acceptance, quoted Provider secret leakage, mutable contract-object references, and weak Provenance mapping schema. Local review added mutable mapping-key rejection. The implementation now uses an explicit immutable-value policy, freezes mapping keys and values, validates finite/non-negative retry delays, redacts quoted token/client-secret payloads, and enforces exact Provider value-object types.
- Verification: Provider contract `23 passed`; related `109 passed`; full pytest `128 passed`; py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and immutable `upstream/dsa-v3.26.1` tag check passed. Local Ruff is not claimed as a pass: downloaded Ruff was blocked by the existing `W503` selector config, and a temporary config probe exposed broader existing lint debt outside `SAL-P2-001`.
- Final independent review: earlier Critical/Important findings are closed; no remaining Critical, Important, or Minor issues were reported.
- Scope retained: no DSA Adapter, real Provider/LLM calls, Dataset/PIT, fallback policy, PersistentTaskBackend, Quant Core, formal backtest, or broad DSA source migration. `RSK-004` and Gate G2 remain open/not passed.
- Checkpoint scope: stage only this task's code, tests, evidence, status/ledger files and this plan; exclude `.cache`, `.venv`, `.worktrees`, pycache and unrelated files.

---

# P2 Status Snapshot Sync Plan

> Started: 2026-07-20
> Scope: Respond to the user's status-sync request after Gate G1 by making the repository recovery state explicit, recording the repeated habit in lessons, and providing a copyable next-session prompt without starting `SAL-P2-001` yet.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, `docs/development-status.md`, and `docs/development-progress-checklist.md`.
- [x] Confirm `git status --short --branch` and latest checkpoints show Gate G1 commit `428205b9`.
- [x] Add a new lesson that status synchronization must happen automatically at user-defined stop/prompt nodes.
- [x] Add a status-sync review line to `docs/development-status.md` confirming P2 / Gate G2 / `SAL-P2-001`.
- [x] Re-scan status anchors and run `git diff --check` before reporting completion.

## Review: P2 Status Snapshot Sync

- Confirmed docs already show Phase `P2 数据与持久任务`, Gate `G2 未通过`, G0/G1 passed, total progress `29/129`, and `SAL-P2-001` `READY`.
- Added a persistent lesson so future phase/task completions automatically update status, progress, todo review, evidence, and the next-start prompt before final response.
- This sync does not start `SAL-P2-001`, does not modify code, and does not touch DSA worktree/cache/runtime artifacts.

---

# P1 Gate G1 Engineering Foundation Review Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-016` as the P1 Gate checkpoint. Review all P1 engineering-hardening evidence, decide Gate G1 Go/No-Go, record accepted risks and P2 entry constraints, update project status, and create a Chinese checkpoint commit before notifying the user that the project has reached P2.

## Checklist

- [x] Confirm clean post-`SAL-P1-015` checkpoint state and current branch/log.
- [x] Review Gate G1 criteria, P1 task evidence, decisions, risks, and current status documents.
- [x] Run G1 verification: baseline tag/worktree, registered patch check, root/P1 test suites, dependency lock, Desktop compatibility runner, and whitespace diff.
- [x] Add `docs/gate-g1-engineering-foundation-review.md` with Gate conclusion, evidence matrix, accepted risks, verification, and P2 entry constraints.
- [x] Update `docs/development-progress-checklist.md` to mark `SAL-P1-016` done, set P1 `16/16`, total `29/129`, and promote `SAL-P2-001` to `READY`.
- [x] Update `docs/development-status.md` to move current Phase to P2 and refresh the next-start prompt.
- [x] Stage only relevant `SAL-P1-016` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-016` is a Gate review only: no new runtime feature, no DSA source migration, no Quant Core, no formal backtest, no Evidence Agent, no real Provider/LLM calls, and no cache/worktree/generated artifact commits.
- Gate G1 may approve entering P2, but P2 tasks must continue through explicit task IDs and retain CI/offline boundaries.
- Any accepted risk must be documented with a downstream closure path and must not be reframed as release-ready.

## Review: SAL-P1-016

- Added `docs/gate-g1-engineering-foundation-review.md`, concluding `GO with accepted risks` and documenting P1 `16/16`, total `29/129`, P2 entry approval, accepted release blockers, and `SAL-P2-001` as the next entry.
- Updated `docs/development-progress-checklist.md` with `DEC-027`, `AEV-029`, P1 `DONE`, P2 `DOING`, and `SAL-P2-001` `READY`.
- Updated `docs/development-status.md` so future sessions resume from P2 / Gate G2 with `SAL-P2-001`, not from G1.
- Verification completed: `bootstrap-dsa-baseline.sh --validate-only`, `apply-dsa-baseline-patches.sh --check-only`, root and P1 pytest `103 passed`, dependency lock check, Desktop compatibility runner, `git diff --check`, and baseline tag check all passed.

---

# P1 Desktop Compatibility Performance Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-015` as a P1 engineering-hardening checkpoint. Re-run the locked DSA Desktop/CLI/Bot and contract/golden characterization paths under the current P1 lock/facade/migration state, add a repeatable performance evidence script, and record startup/single-stock stub-analysis timings without changing DSA runtime behavior, moving upstream tags, starting real Provider/LLM calls, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P0 Desktop/CLI/Bot smoke evidence, P0 required baseline jobs, and P1 guardrails.
- [x] Add a repeatable `SAL-P1-015` compatibility/performance runner that keeps generated timing artifacts under `.cache/dsa-p0`.
- [x] Run Desktop npm tests, Desktop packaging/API health, CLI local backend, Bot command smoke, API/config, database, and report/signal baselines.
- [x] Capture startup/import and single-stock report-generation timing against conservative P1 thresholds.
- [x] Run Serenity root pytest/compile/lock/diff/tag verification.
- [x] Add `SAL-P1-015` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-015` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-015` is compatibility/performance evidence only: no DSA source migration, no Desktop package signing/build artifact commit, no Web lockfile rewrite, no Docker image rebuild unless explicitly needed for G1, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- P0 characterization is measured through deterministic/offline paths: Desktop headless tests, packaging/API health, CLI/Bot mocks, API/config snapshots, database fixture, and report/signal golden snapshots.
- Performance thresholds for this first P1 run are conservative baselines rather than optimization claims: Desktop/backend health startup budget `<= 60s`, report/signal golden run `<= 60s`, and single-stock Markdown generation `<= 5s`.

## Review: SAL-P1-015

- Added `scripts/run-p1-desktop-compatibility-performance.sh` as the repeatable compatibility/performance runner. It bootstraps the locked DSA baseline, applies registered patches, runs Desktop/API/CLI/Bot and contract/golden baselines, measures Desktop backend health startup, and writes generated logs/summary only under `.cache/dsa-p0/p1-desktop-compatibility-performance/`.
- Added `docs/desktop-compatibility-performance-baseline.md`, documenting the validation matrix, performance thresholds, no-real-call boundaries, generated artifact policy, and G1 handoff.
- Latest runner evidence passed: Desktop `npm test` `47 passed`, Desktop/API/CLI/Bot pytest `121 passed, 7 warnings`, API/config snapshots matched, database snapshots matched, report/signal snapshots matched, Desktop backend health startup `5,822ms`, single-stock report generation average `0.030ms`, and real Provider/LLM calls zero.
- Updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-015` done, record `DEC-026` / `AEV-028`, move P1 progress to `15/16`, total progress to `28/129`, and promote `SAL-P1-016` to `READY`.
- Final verification recorded before checkpoint commit: `bash -n scripts/run-p1-desktop-compatibility-performance.sh`, full `.cache/dsa-p0/venv/bin/python -m pytest -q`, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1`.

---

# P1 SQLite Upgrade Verification Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-013` as a P1 engineering-hardening checkpoint. Rehearse upgrading the committed sanitized DSA SQLite fixture to the Alembic baseline by backup, stamp, verify, and recovery; do not introduce new schema changes, migrate DSA runtime `storage.py`, start Provider/LLM calls, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P0 fixture SQL/content hashes and `SAL-P1-012` Alembic baseline behavior for existing DSA databases.
- [x] Add Red tests for fixture restore, Alembic stamp/verify, row-count/content-hash preservation, idempotent rerun, and failure recovery from backup.
- [x] Implement SQLite upgrade rehearsal helpers and report DTOs without importing DSA `storage.py` or calling `create_all`.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-013` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-013` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-013` is historical SQLite upgrade verification only: no new business schema, no DSA runtime source migration, no Repository read/write path switch, no Desktop performance run, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- Existing business tables must preserve row counts and content hashes; Alembic may add/update only its version tracking table.
- Any failure after backup must restore the original SQLite file before returning control.

## Review: SAL-P1-013

- Added Red tests in `tests/repositories/test_sqlite_upgrade.py`; initial target run failed on missing `serenity_alpha_lab.repositories.sqlite_upgrade` with `4 failed`.
- Added `src/serenity_alpha_lab/repositories/sqlite_upgrade.py`, defining `SQLiteInspection`, `SQLiteUpgradeReport`, fixture restore, business table inspection, Alembic stamp upgrade, idempotency behavior, validation, and backup restore on failure.
- Extended `storage_migrations.py` with `stamp_database()` so existing DSA SQLite databases can be marked at the Alembic baseline without rerunning DDL.
- Added `docs/sqlite-upgrade-verification.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-013` done, record `DEC-025` / `AEV-027`, move P1 progress to `14/16`, total progress to `27/129`, and promote `SAL-P1-015` to `READY`.
- Verification completed: target SQLite upgrade tests `4 passed`, repositories/architecture `26 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `103 passed`, py_compile for changed repository/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Alembic Migration Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-012` as a P1 engineering-hardening checkpoint. Introduce Alembic as the single schema migration entry for the Serenity root, add a DSA v3.26.1 SQLite baseline revision tied to the P0 database snapshot, and provide startup preflight helpers without rewriting DSA runtime `storage.py`, running Provider/LLM calls, starting PIT Dataset, Quant Core, formal backtesting, or large DSA source migration.

## Checklist

- [x] Review P0 database baseline, ADR-002 `StorageMigrationFacade` scope, and current Python dependency surface.
- [x] Add Red tests for baseline revision metadata, empty SQLite upgrade, startup preflight, and no DSA `storage.py` / `create_all` dependency in migration code.
- [x] Add Alembic to the explicit root core install surface and refresh lock/export if needed.
- [x] Create Alembic config/env/script template, DSA v3.26.1 baseline revision, and committed schema SQL baseline under `migrations/`.
- [x] Implement storage migration facade helpers for upgrade, status, and startup head assertion.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-012` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-012` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-012` is migration foundation only: no DSA source movement, no DSA API route rewrite, no Repository behavior migration, no `SAL-P1-013` historical upgrade rehearsal, no Provider/LLM calls, no PIT Dataset, no Quant Core, and no formal backtest.
- Alembic must be the only new schema creation entry; startup helpers should check revision state rather than silently calling `Base.metadata.create_all()` or DSA `DatabaseManager`.
- Baseline revision must explicitly reference DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` and P0 schema version `2026-06-05-create-all-baseline`.

## Review: SAL-P1-012

- Added Red tests in `tests/repositories/test_storage_migrations.py`; initial target run failed on missing `serenity_alpha_lab.repositories.storage_migrations`, `migrations/env.py`, and baseline revision with `4 failed`.
- Added root Alembic files: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/baselines/dsa_v3_26_1_schema.sql`, and `migrations/versions/20260720_dsa_v3261_baseline.py`.
- Added `src/serenity_alpha_lab/repositories/storage_migrations.py`, defining `MigrationStatus`, `StorageMigrationRequired`, `upgrade_database()`, `current_migration_status()`, `assert_database_at_head()`, and baseline SQL verification helpers.
- Added explicit `alembic>=1.13.0` to root `core` extra and regenerated `uv.lock` / `requirements.txt` through the existing drift guard export path.
- Added `docs/storage-migration-alembic.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-012` done, record `DEC-024` / `AEV-026`, move P1 progress to `13/16`, total progress to `26/129`, and promote `SAL-P1-013` to `READY`.
- Verification completed: target storage migration tests `4 passed`, repositories/architecture `22 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `99 passed`, py_compile for changed repository/migration/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 API Error Protocol Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-010` as a P1 engineering-hardening checkpoint. Define a stable `application/problem+json` error protocol, sanitized problem details, error code mapping, and framework-neutral ASGI middleware without changing existing DSA API routes, OpenAPI snapshots, Provider/LLM behavior, Alembic, PIT Dataset, Quant Core, or formal backtesting.

## Checklist

- [x] Review P1 error requirements, existing TaskBackend/Config/Research errors, Trace context, and ADR-002 API boundary rules.
- [x] Add Red tests for RFC 7807-style serialization, stable error codes, trace_id propagation, validation/not-found/conflict/provider/internal mapping, and secret/path redaction.
- [x] Add Red ASGI middleware tests for `application/problem+json` responses without FastAPI imports.
- [x] Implement application-layer API error DTOs, error classes, exception mapper, redactor, response helpers, and middleware.
- [x] Export public API error symbols from `serenity_alpha_lab.application`.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-010` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-010` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-010` is protocol/middleware foundation only: no DSA API route rewrite, no OpenAPI baseline refresh, no Web client change, no Provider/LLM calls, no Alembic migration, no PIT Dataset, no Quant Core, and no formal backtest.
- Problem details must not expose Python stack traces, absolute file paths, API keys, tokens, prompts, request bodies, or private content.
- Keep middleware framework-neutral and avoid FastAPI/Starlette imports.

## Review: SAL-P1-010

- Added Red tests in `tests/application/test_api_errors.py` and an architecture boundary check in `tests/architecture/test_architecture_boundaries.py`; initial target run failed on missing `serenity_alpha_lab.application.api_errors` with `5 failed`.
- Added `src/serenity_alpha_lab/application/api_errors.py`, defining `ApiErrorCode`, `ProblemDetail`, `ApiProblemError` subclasses, `problem_from_exception()`, `problem_response_body()`, `redact_problem_detail()`, and framework-neutral `ProblemDetailsMiddleware`.
- Mapped existing app errors explicitly: `TaskNotFound` -> `not_found`, `TaskAlreadyExists` -> `conflict`, `ConfigProfileError` / `ValueError` -> `validation_error`, request-validation `ResearchOrchestratorError` -> `validation_error`, DSA/facade `ResearchOrchestratorError` -> `provider_error`, `TaskBackendCapabilityError` / unknown exceptions -> `internal_error`.
- Added `docs/api-error-protocol.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-010` done, record `DEC-023` / `AEV-025`, move P1 progress to `12/16`, and total progress to `25/129`.
- Verification completed: target API error tests `5 passed`, application/architecture `41 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `95 passed`, py_compile for changed application/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 ResearchOrchestrator Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-009` as a P1 engineering-hardening checkpoint. Define a stable application-layer ResearchOrchestrator protocol and an injected DSA compatibility facade for `AgentOrchestrator.run/chat` without copying DSA runtime source, changing API routes, starting Provider/LLM calls, adding persistence, or replacing report generation.

## Checklist

- [x] Review DSA `AgentOrchestrator`/`AgentResult` signatures, existing Agent API call sites, ADR-002 facade scope, and P1 guardrails.
- [x] Add Red application contract tests for Research request/result DTOs, protocol shape, validation, and immutable context handling.
- [x] Add Red integration facade tests for mapping DSA-like `run()` and `chat()` results through an injected orchestrator object.
- [x] Add architecture tests proving the application contract and DSA facade do not import concrete DSA `src.agent` modules.
- [x] Implement application-layer ResearchOrchestrator DTOs, Protocol, progress callback type, errors, and result mapping contract.
- [x] Implement DSA `AgentOrchestrator` compatibility facade using constructor injection and shallow context normalization.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-009` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-009` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-009` is facade/protocol foundation only: no API route migration, no Deep Research rewrite, no Agent checkpoint persistence, no Evidence Agent, no Provider/LLM calls, no Quant Core, no PIT Dataset, and no formal backtest.
- DSA compatibility code must receive an orchestrator-like object by injection; no top-level `src.agent.orchestrator` or broad DSA runtime import.
- Existing DSA result semantics must remain intact: `success/content/dashboard/tool_calls_log/total_steps/total_tokens/provider/model/error` are mapped without reinterpretation.

## Review: SAL-P1-009

- Added Red tests in `tests/application/test_research_orchestrator_contract.py` and `tests/integrations/test_dsa_research_orchestrator_facade.py`; initial target run failed on missing `serenity_alpha_lab.application.research_orchestrator`, then Green passed with target `16 passed`.
- Added architecture coverage in `tests/architecture/test_architecture_boundaries.py` to reject concrete DSA Agent runtime imports from the application contract and DSA facade.
- Added `src/serenity_alpha_lab/application/research_orchestrator.py`, defining `ResearchRequest`, `ResearchChatRequest`, `ResearchResult`, `ResearchOrchestrator`, `ResearchMode`, `ProgressCallback`, and `ResearchOrchestratorError`.
- Added `src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py`, defining `DsaResearchOrchestratorFacade` around an injected DSA-like orchestrator; it maps `run()` / `chat()` results without reinterpreting legacy `AgentResult` fields and normalizes explicit chat skills into `skills` / `strategies`.
- Added `docs/research-orchestrator-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-009` done, record `DEC-022` / `AEV-024`, move P1 progress to `11/16`, and total progress to `24/129`.
- Verification completed: target ResearchOrchestrator tests `16 passed`, application/integrations/architecture `43 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `90 passed`, py_compile for changed application/integration/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Config Profile Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-014` as a P1 engineering-hardening checkpoint. Define desktop/standalone/ci runtime profiles, secret boundaries, redacted diagnostics, and config source tracking without rewriting deployment `.env`, starting Provider/LLM calls, changing DSA runtime config endpoints, or adding deployment automation.

## Checklist

- [x] Review P1 profile requirements, DSA config baseline, dependency surface, and ADR-002 facade boundary.
- [x] Add Red tests for runtime profile policies, CI key/network rejection, redacted diagnostics, source tracking, and no `.env` rewrite from service profile preview.
- [x] Add direct `pydantic-settings` dependency to the root core install surface and refresh lock/export if needed.
- [x] Implement application-layer `ConfigProfileFacade`, Pydantic settings model, profile policy, diagnostics, and update preview.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-014` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-014` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-014` is configuration/profile foundation only: no DSA `.env` rewrite integration, no Web/API route changes, no deployment profile rewrite, no Provider/LLM calls, no Alembic, no PIT Dataset, no Quant Core, and no formal backtest.
- CI profile must default to offline/stub behavior and reject real model/provider secrets.
- Diagnostics must not expose complete API keys, provider tokens, prompts, body content, credentials, or deployment secret values.

## Review: SAL-P1-014

- Added Red tests in `tests/application/test_config_profiles.py`; initial target run failed on missing `serenity_alpha_lab.application.config_profiles`, then Green passed with target `9 passed`.
- Added `src/serenity_alpha_lab/application/config_profiles.py`, defining `RuntimeSettings`, `RuntimeProfile`, `ProfilePolicy`, `ConfigValueSource`, `ConfigProfileError`, source-tracked loading, redacted diagnostics, CI boundary enforcement, and side-effect-free update preview.
- Added direct root `core` dependency `pydantic-settings>=2.0.0`; refreshed minimal `uv.lock` project metadata and regenerated `requirements.txt` through the existing lock/export guard.
- Added `docs/config-profile-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-014` done, record `DEC-021` / `AEV-023`, move P1 progress to `10/16`, total progress to `23/129`, and promote `SAL-P1-012` to `READY`.
- Verification completed: target Config Profile tests `9 passed`, application/architecture `29 passed`, P1 related application/architecture/domain/repositories/integrations `79 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `79 passed`, py_compile for changed application/test files, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Trace and Structured Logging Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-011` as a P1 engineering-hardening checkpoint. Define trace context propagation, structured JSON log schema, redaction, and lightweight ASGI middleware without adding OpenTelemetry exporters, metrics backend, Provider/Qlib/LLM instrumentation, or API endpoint rewrites.

## Checklist

- [x] Review observability requirements, Run/Stage model, TaskBackend context, and logging redaction constraints.
- [x] Add Red tests for trace context propagation and reset behavior.
- [x] Add Red tests for structured JSON logging with trace/run/stage/user/module fields and secret/prompt redaction.
- [x] Add Red tests for ASGI-compatible trace middleware header propagation.
- [x] Implement stdlib-only trace context, redactor, logging filter, JSON formatter, and ASGI middleware.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-011` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-011` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-011` is observability foundation only: no OpenTelemetry exporter, Prometheus/Grafana, Provider/Qlib/LLM instrumentation, Agent orchestration changes, API route rewrites, PIT Dataset, Quant Core, or formal backtest.
- Do not log secrets, tokens, full prompts, private body text, or request payloads by default.
- Middleware must be framework-neutral and avoid FastAPI/Starlette imports.

## Review: SAL-P1-011

- Added Red tests in `tests/application/test_trace_context.py`; initial target run failed on missing `serenity_alpha_lab.application.tracing`, then Green passed with target `4 passed`.
- Added `src/serenity_alpha_lab/application/tracing.py`, defining `TraceContext`, `use_trace_context()`, `current_trace_context()`, `TraceContextFilter`, `StructuredLogFormatter`, `TraceContextMiddleware`, `generate_trace_id()` and `redact_sensitive_data()`.
- Structured JSON logs include timestamp, level, logger, module, message, trace_id, run_id, stage_id and user_id; `extra` fields are recursively redacted for secrets, tokens, authorization, api keys, prompts, messages, bodies and content.
- Added `docs/structured-trace-logging.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-011` done, record `DEC-020` / `AEV-022`, move P1 progress to `9/16`, and total progress to `22/129`.
- Verification completed: target Trace tests `4 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `70 passed`, py_compile for application/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 TaskBackend Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-008` as a P1 engineering-hardening checkpoint. Define a stable TaskBackend protocol, in-memory implementation, and DSA compatibility facade without moving upstream, importing broad DSA runtime source, starting persistent task queues, or introducing Celery/Redis/PostgreSQL behavior.

## Checklist

- [x] Review current P1 state, ADR-002 facade scope, DSA `AnalysisTaskQueue` signatures, and thread-pool boundary risk.
- [x] Add Red contract tests for `TaskBackend.submit/get/request_cancel/subscribe`.
- [x] Add Red compatibility facade tests for wrapping an injected DSA-like queue without importing DSA runtime.
- [x] Add architecture test ensuring Serenity application/DSA facade modules do not import `ThreadPoolExecutor` directly.
- [x] Implement application-layer TaskBackend DTOs, Protocol, errors, and InMemory implementation.
- [x] Implement DSA `AnalysisTaskQueue` compatibility facade using handler registry and injected queue object.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-008` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-008` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-008` may define a facade around DSA queue shape but must not copy/migrate DSA runtime source into Serenity.
- No `ThreadPoolExecutor`, Celery, Redis, PostgreSQL persistence, Worker runtime, PIT Dataset, Quant Core, formal backtest, or API endpoint implementation in this task.
- DSA compatibility code must receive queue/handlers by injection; no top-level `src.services.task_queue` import.

## Review: SAL-P1-008

- Added Red tests in `tests/application/test_task_backend_contract.py` and `tests/integrations/test_dsa_task_backend_facade.py`; initial target run failed on missing `serenity_alpha_lab.application.task_backend`, then Green passed with target `12 passed`.
- Added architecture coverage in `tests/architecture/test_architecture_boundaries.py` to reject direct `ThreadPoolExecutor` imports from `application` and `integrations/dsa` modules.
- Added `src/serenity_alpha_lab/application/task_backend.py`, defining `TaskBackend`, `TaskCommand`, `TaskRef`, `TaskSnapshot`, `TaskEvent`, status/error types, `InMemoryTaskBackend`, and DSA legacy status mapping without importing DSA runtime or thread pools.
- Added `src/serenity_alpha_lab/integrations/dsa/task_backend.py`, defining `DsaAnalysisTaskQueueBackend` around an injected queue and handler registry; it maps `submit_background_task()`, `get_task()`, optional cancel methods, and flow events into the stable TaskBackend contract.
- Added `docs/task-backend-facade.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-008` done, record `DEC-019` / `AEV-021`, move P1 progress to `8/16`, and total progress to `21/129`.
- Verification completed: target TaskBackend tests `12 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `66 passed`, py_compile for application/integration/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.

---

# P1 Artifact Store Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-007` as a P1 engineering-hardening checkpoint. Define pure artifact domain contracts and a local content-addressed store without starting Evidence Agent, Dataset Catalog, PIT Dataset, Quant Core, formal backtesting, database migration, or broad DSA source movement.

## Checklist

- [x] Review current P1 state, ADR-001/002 guardrails, existing Run domain model, and architecture boundaries.
- [x] Add Red tests for Artifact URI/Manifest metadata and local store atomic publish behavior.
- [x] Run target Red tests and confirm they fail for missing Artifact modules.
- [x] Implement pure domain Artifact model and `ArtifactStore` Protocol.
- [x] Implement local filesystem ArtifactStore with content-addressed blobs, JSON manifests, temp-file cleanup, and hash verification.
- [x] Run target and broader pytest/compile/lock/diff verification.
- [x] Add `SAL-P1-007` evidence documentation.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section.
- [x] Stage only relevant `SAL-P1-007` files and create a Chinese checkpoint commit.

## Guardrails

- `SAL-P1-007` is Artifact domain/storage only: no Provider migration, Dataset Catalog, PIT data, Quant Core, formal backtest, database migration, Evidence Agent, API endpoint, or large DSA runtime source migration.
- Domain code must stay pure and must not import framework, repository, service, vendor, or DSA runtime modules.
- Local storage must publish manifests last; failed writes must not create queryable published records and must clean temporary files.

## Review: SAL-P1-007

- Added Red tests in `tests/domain/test_artifacts.py` and `tests/repositories/test_local_artifact_store.py`; initial target run failed on missing `serenity_alpha_lab.domain.artifacts`, then Green passed with `6 passed`.
- Added `src/serenity_alpha_lab/domain/artifacts.py`, defining pure domain `ArtifactUri`, `ArtifactManifest`, `ArtifactRetentionTier`, `ArtifactStore`, and artifact error types without importing repositories, frameworks, providers, or DSA runtime code.
- Added `src/serenity_alpha_lab/repositories/local_artifact_store.py`, implementing local SHA-256 blob storage, JSON manifests, idempotent record reuse, manifest-last atomic publish, temp cleanup, and hash/size validation on reads.
- Added `docs/artifact-store-domain-model.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-007` done, record `DEC-018` / `AEV-020`, move P1 progress to `7/16`, and total progress to `20/129`.
- Verification completed: target Artifact tests `6 passed`, related architecture/domain/repositories tests `58 passed`, full `.cache/dsa-p0/venv/bin/python -m pytest -q` `58 passed`, py_compile for domain/repository/test paths, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed; checkpoint commit `5525f6da feat(P1): 实现 Artifact 模型与本地存储` created.

---

# P1 InstrumentId Domain Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-005` as a P1 engineering-hardening checkpoint. Define a pure domain `InstrumentId` value object, market/exchange/asset-type vocabulary, and provider/legacy symbol mapping without starting Provider migration, PIT Dataset, Quant Core, formal backtesting, or broad DSA source movement.

## Checklist

- [x] Review recovery docs, lessons, status, progress checklist, development plan, Gate G0 review, ADR-001/002, Git status, recent commits, and DSA symbol normalization references.
- [x] Write Red tests for A/HK/US/JP/KR/TW `InstrumentId` parsing, formatting, provider symbol mapping, and ambiguous bare-code rejection.
- [x] Implement pure domain `InstrumentId`, `Market`, `Exchange`, `AssetType`, errors, and provider/legacy mapping helpers.
- [x] Export public domain symbols and keep architecture boundaries clean.
- [x] Add `SAL-P1-005` evidence documentation.
- [x] Run targeted domain tests, architecture tests, full pytest, py_compile, dependency lock drift guard, upstream tag check, and `git diff --check`.
- [x] Update progress checklist, status snapshot, decision/evidence registers, and this review section.
- [x] Stage only relevant files and create a Chinese checkpoint commit after verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products.
- `SAL-P1-005` is pure domain/compatibility modeling only: no Provider implementation, Dataset Catalog, PIT data, Quant Core, formal backtest, database migration, or large DSA runtime source migration.
- Bare six-digit codes must remain ambiguous unless explicit market context is supplied.

## Review: SAL-P1-005

- Added `tests/domain/test_instrument_id.py` as the Red/Green contract for canonical A/HK/US/JP/KR/TW round-trips, legacy DSA/Yahoo symbol intake, provider symbol mapping, DSA compatibility symbols, and ambiguous bare-code rejection. Initial Red failed on missing `serenity_alpha_lab.domain.instruments`.
- Added `src/serenity_alpha_lab/domain/instruments.py`, defining pure domain `InstrumentId`, `Market`, `Exchange`, `AssetType`, `ProviderSymbolMapping`, `AmbiguousInstrumentSymbol`, `InvalidInstrumentSymbol`, and `UnsupportedProvider` without importing DSA runtime, data providers, frameworks, or persistence.
- Exported InstrumentId symbols from `src/serenity_alpha_lab/domain/__init__.py`; architecture tests continue to enforce domain/framework and infrastructure boundaries.
- Added `docs/instrument-id-domain-model.md`; updated `docs/development-progress-checklist.md` and `docs/development-status.md` to mark `SAL-P1-005` done, record `DEC-017` / `AEV-019`, move P1 progress to `6/16`, and total progress to `19/129`.
- Verification completed: target Red/Green test, `.cache/dsa-p0/venv/bin/python -m pytest tests/domain/test_instrument_id.py -q` (`37 passed`), `.cache/dsa-p0/venv/bin/python -m pytest tests/architecture tests/domain -q` (`52 passed`), full `.cache/dsa-p0/venv/bin/python -m pytest -q` (`52 passed`), py_compile, `scripts/verify-python-dependency-lock.sh`, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1` (`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`) passed.
- Local review found no blocking correctness issue; scope remains pure domain modeling only, with Provider migration, Dataset master data, PIT semantics, Quant Core, and formal backtesting deferred to their explicit tasks.

---

# P1 Dependency Lock and Run Domain Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-003` and `SAL-P1-006` as separate but adjacent P1 engineering-hardening checkpoints. Preserve ADR-001/002 guardrails: do not move `upstream/dsa-v3.26.1`, do not import broad DSA runtime source, and do not start Quant Core, PIT Dataset, formal backtesting, or unapproved DSA migration.

## Checklist

- [x] Review recovery docs, lessons, status, progress checklist, development plan, Gate G0 review, ADR-001/002, Git status, and recent commits.
- [x] Write Red tests for dependency extras, lock/requirements drift guard, and absence of production dynamic Git dependencies.
- [x] Split Python dependencies into `core`, `providers`, `desktop`, `quant`, and `dev` install surfaces; generate `uv.lock` and exported requirements files.
- [x] Run dependency Red/Green validation, `uv lock --check`, requirements drift guard, architecture tests, and metadata checks.
- [x] Write Red tests for Run/Stage/Event state transitions, retry attempts, monotonic append-only event IDs, and idempotency keys.
- [x] Implement pure domain Run/Stage/Event model without framework, data provider, DSA, Quant Core, PIT Dataset, or backtest behavior.
- [x] Run domain tests, architecture boundary tests, py_compile, and `git diff --check`.
- [x] Update progress checklist, status snapshot, risk/decision/evidence registers, and this review section.
- [x] Stage only relevant files and create Chinese checkpoint commit(s) after verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products beyond approved dependency lock/requirements outputs.
- `SAL-P1-003` may create lock and exported requirements, but must not perform broad dependency upgrades unrelated to reproducing the P1 dependency graph.
- `SAL-P1-006` is pure domain state modeling only: no ArtifactStore, TaskBackend, persistence, Trace middleware, Quant Core, PIT Dataset, or formal backtest implementation.

## Review: SAL-P1-003 / SAL-P1-006

- Added `tests/architecture/test_dependency_locking.py` as the Red/Green contract for extras, lock presence, generated requirements, drift guard, and dynamic Git exclusion; initial Red failed on old default dependencies, AlphaSift Git dependency, missing `uv.lock`, missing `requirements.txt`, and missing guard script.
- Split root Python install surfaces in `pyproject.toml` into `core`, `providers`, `desktop`, `quant`, and `dev`; generated `uv.lock` and lock-derived `requirements.txt` for `core+providers+desktop` only.
- Added `scripts/verify-python-dependency-lock.sh`, which runs `uv lock --check`, re-exports the production requirements surface with a stable header, and diffs against committed `requirements.txt`.
- Removed Serenity root production dependency on dynamic AlphaSift Git install; DSA isolated worktree is unchanged, and reviewed AlphaSift wheel/package intake remains deferred to the later AlphaSift adapter task.
- Added `tests/domain/test_run_lifecycle.py` as the Red/Green contract for append-only monotonic events, terminal rollback rejection, retry new attempts, and idempotency conflict handling; initial Red failed on the missing `run_lifecycle` module.
- Added `src/serenity_alpha_lab/domain/run_lifecycle.py` and exported domain symbols from `domain/__init__.py`; no persistence, ArtifactStore, TaskBackend, Trace middleware, Quant Core, PIT Dataset, or formal backtest behavior was introduced.
- Added `docs/python-dependency-lock.md` and `docs/run-stage-event-domain-model.md`; updated `docs/python-project-metadata.md`, `docs/development-progress-checklist.md`, and `docs/development-status.md` to reflect then-current `SAL-P1-003`/`SAL-P1-006` completion, P1 progress, total progress, and `RSK-008` closure.
- Verification completed: `scripts/verify-python-dependency-lock.sh`, `pytest tests/architecture tests/domain -q`, full `pytest -q`, `py_compile`, editable install `pip install -e . --no-deps`, DSA dry-run entrypoint smoke, and `git diff --check` passed.

---

# P1 Python Metadata and Architecture Skeleton Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-002` and `SAL-P1-004` as one small engineering-hardening checkpoint. Preserve ADR-001/002 guardrails: do not move `upstream/dsa-v3.26.1`, do not copy broad DSA runtime source into the working tree, and do not start Quant Core, PIT Dataset, formal backtesting, or unapproved DSA migration.

## Checklist

- [x] Review session recovery docs, ADR-001/002, P1 task definitions, current Git state, and existing tracked project files.
- [x] Write Red tests for root `pyproject.toml`, installable entry points, package importability, and ADR-002 architecture boundaries.
- [x] Run targeted Red tests and record the expected failures.
- [x] Add root `pyproject.toml` with standard PEP 621 project metadata, Python version, build backend, DSA-derived dependencies, console entry points, and tool configuration.
- [x] Create minimal `src/serenity_alpha_lab` package skeleton for `domain`, `application`, `quant`, `datasets`, `evidence`, `integrations`, `repositories`, and `services` without implementing Quant Core or PIT Dataset behavior.
- [x] Add DSA compatibility entry-point wrappers that resolve the isolated DSA worktree and support dry-run validation without copying DSA runtime source.
- [x] Add dependency-difference review notes documenting what moved from DSA requirements/tool config and what remains deferred to `SAL-P1-003`.
- [x] Run targeted Green tests, editable install smoke with `--no-deps`, architecture checks, metadata parse checks, and `git diff --check`.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, and this review section with evidence and next-step state.
- [x] Stage only relevant P1 files and create a Chinese checkpoint commit if verification passes.

## Guardrails

- Keep `upstream/dsa-v3.26.1` immutable and DSA source isolated under `.worktrees/dsa-v3.26.1`.
- Do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache, or generated build products.
- Keep `SAL-P1-003` scope separate: no `uv.lock`, no finalized extras split, no dependency upgrade/remediation beyond pyproject metadata normalization.
- Keep `SAL-P1-004` as skeleton and architecture tests only: no factor math, dataset catalog, formal backtest, Qlib integration, or provider migration.

## Review: SAL-P1-002 / SAL-P1-004

- Added root `pyproject.toml` with PEP 621 metadata, Python `>=3.11,<3.13`, `setuptools.build_meta`, DSA-derived runtime dependencies, DSA dry-run console scripts, and pytest/format/lint tool configuration.
- Added `docs/python-project-metadata.md` to document the migration from DSA `requirements.txt`, `pyproject.toml`, and `setup.cfg`, plus explicit `SAL-P1-003` deferrals for extras, lock generation, and AlphaSift dynamic Git closure.
- Added `src/serenity_alpha_lab/` package skeleton for `domain`, `application`, `quant`, `datasets`, `evidence`, `integrations`, `repositories`, and `services`; no Quant Core, PIT Dataset, formal backtest, provider migration, or broad DSA runtime source import was introduced.
- Added DSA compatibility wrappers under `src/serenity_alpha_lab/integrations/dsa/entrypoints.py`, resolving `.worktrees/dsa-v3.26.1` and supporting `SERENITY_DSA_DRY_RUN=1` for CLI/API/Worker/test entry-point validation.
- Added Red/Green architecture tests under `tests/architecture/`: initial Red failed on missing `pyproject.toml`, package skeleton, and entrypoint modules; final Green passed with `7 passed`.
- Verification completed: `pytest tests/architecture -q`, full `pytest -q`, editable install `pip install -e . --no-deps`, installed console-script dry-runs, `py_compile`, metadata parse, forbidden-token scan, and `git diff --check` passed. `ruff` was not run because it is not installed in `.cache/dsa-p0/venv`.
- Updated `docs/development-progress-checklist.md` and `docs/development-status.md`: `SAL-P1-002` and `SAL-P1-004` are `DONE`, P1 progress is 3/16, total progress is 16/129, and recommended next tasks are `SAL-P1-003` and `SAL-P1-006`.

---

# P1 ADR Approval Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-001` only. Approve upstream takeover/sync policy and progressive modularization decisions before any Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration.

## Checklist

- [x] Review `AGENTS.md`, `tasks/lessons.md`, development status, progress checklist, development plan, Gate G0 review, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P1 engineering hardening preparation; Gate G0 passed; `SAL-P1-001` is `READY`.
- [x] Write ADR-001 for upstream takeover, immutable tag policy, sync branches, patch classification, candidate commit triage, rollback, and review cadence.
- [x] Write ADR-002 for progressive modularization, Compatibility Facade, module boundaries, service-split conditions, old-path deletion criteria, rollback, and review cadence.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P1-001`, including DONE status, actual effort, decision/evidence entries, risk updates, and next `READY` tasks.
- [x] Update `docs/development-status.md` for current Phase/Gate, completed/unfinished work, next executable tasks, latest checkpoint placeholder, and next-start prompt.
- [x] Add `SAL-P1-001` review notes here after verification.
- [x] Run lightweight ADR verification: required ADR sections, stale status scan, forbidden source migration check, link/path checks, `git diff --check`, and Git status review.
- [x] Stage only relevant `SAL-P1-001` files and create a Chinese checkpoint commit.

## Guardrails

- Do not move, delete, or reuse `upstream/dsa-v3.26.1`.
- Do not copy or merge DSA runtime source into the main working tree in this task.
- Do not start Quant Core, PIT Dataset, formal backtesting, Qlib integration, or large DSA source migration before these ADRs are approved.
- Do not submit `.worktrees`, `.cache`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked directories.
- Keep accepted G0 risks visible; ADR approval does not make release security risks acceptable.

## Review: SAL-P1-001

- Added `docs/adr/ADR-001-upstream-takeover-sync-and-patch-policy.md`, approving the immutable DSA `v3.26.1` baseline, controlled `sync/dsa-*` branches, patch classification, sync rollback, and candidate commit triage.
- Added `docs/adr/ADR-002-progressive-modularization-and-compatibility-facade.md`, approving progressive modularization, explicit Compatibility Facade boundaries, service-split conditions, old-path deletion criteria, rollback, and Gate G1/2026-08-03 review timing.
- Updated `docs/development-progress-checklist.md`: `SAL-P1-001` is `DONE`, P1 progress is 1/16, total progress is 14/129, `SAL-P1-002` and `SAL-P1-004` are `READY`, `RSK-006` is closed by ADR triage, and `DEC-012` / `DEC-013` / `AEV-014` record decisions and evidence.
- Updated `docs/development-status.md`: current Gate is G1 not passed, latest completed task is `SAL-P1-001`, next executable tasks are `SAL-P1-002` and `SAL-P1-004`, and the next-start prompt reflects the new recovery point.
- Verification completed for `SAL-P1-001`: ADR required sections, immutable tag check, active status anchors, no runtime/cache path changes, and `git diff --check` all passed.

---

# P0 Remaining Gate Baseline Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Complete `SAL-P0-010` first, then `SAL-P0-012`, then run `SAL-P0-013` Gate G0 review. Do not start P1, Quant Core, or broad DSA source migration before G0 passes.

## Checklist

- [x] Review `AGENTS.md`, project lessons, development status, progress checklist, development plan, upstream baseline selection, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P0, Gate G0 not passed; `SAL-P0-010` and `SAL-P0-012` are `READY`; `SAL-P0-013` remains gated by P0 completion.
- [x] Dispatch read-only subagents for report/signal baseline discovery, existing baseline-script pattern discovery, and upstream/CI discovery.
- [x] Run the Red check for `SAL-P0-010`: `scripts/run-dsa-report-signal-baseline.sh` is missing, so report/signal goldens are not yet reproducible.
- [x] Inspect DSA report rendering, report schema, notification report fixtures, DecisionSignal summary, and Backtest/Signal Evaluation metric paths in `.worktrees/dsa-v3.26.1`.
- [x] Add `scripts/run-dsa-report-signal-baseline.sh` using the established baseline pattern: validate tag/worktree, apply registered patches, validate worktree diff, run offline/stub generation, compare committed snapshots, and support `--update-snapshots`.
- [x] Commit stable `SAL-P0-010` snapshots under `docs/baselines/dsa-v3.26.1/report-signal/`, including structured report input/output, Markdown single-stock/aggregate/market-review goldens, signal evaluation input/output, content hashes, and `summary.json`.
- [x] Write `docs/report-signal-golden-baseline.md` with commands, fixture coverage, hashes, limitations, and non-goals.
- [x] Verify `SAL-P0-010`: baseline script update and compare runs, relevant upstream report/backtest tests, `bash -n`, `git diff --check`, committed-fixture guards, and summary assertions.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P0-010`, P0 progress from 10/13 to 11/13, evidence registry, decisions, risks, and dependencies.
- [x] Update `docs/development-status.md` after `SAL-P0-010` with completed/unfinished tasks, next actions, latest checkpoint placeholders, and a fresh next-start prompt.
- [x] Add this task's review section to `tasks/todo.md`.
- [x] Stage only relevant `SAL-P0-010` files and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-012`: create upstream maintenance documentation and CI required checks after the report/signal baseline exists.
- [x] Verify `SAL-P0-012`, update status/checklist/evidence, and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-013` only after all P0 tasks are `DONE`; run Gate G0 review, record Go/No-Go, update status/checklist, and create a Chinese checkpoint commit.

## Guardrails

- Gate G0 is now passed by `SAL-P0-013`; keep the accepted risks visible and do not treat them as release approval.
- `SAL-P0-010` must use offline fixture/stub inputs only; no real Provider, real LLM, scheduler, webhook, or notification send.
- `SAL-P0-012` must include the actual P0 baseline scripts/artifacts and patch registry, not aspirational CI checks.
- `SAL-P1-001` is now complete; follow ADR-001/002 before starting dependent P1 code, and do not start Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration outside the approved task sequence.
- The DSA source remains isolated in `.worktrees/dsa-v3.26.1`; do not copy upstream runtime source into the project tree.
- Do not submit `.cache`, `.worktrees`, runtime SQLite binaries, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## SAL-P0-012 Plan

- [x] Create root `UPSTREAM_BASE.md` covering upstream baseline, remote/tag policy, local worktree/cache layout, patch classification, baseline artifacts, sync procedure, and required check names.
- [x] Update `docs/upstream-patches.md` so each local deviation is explicitly classified as `compatible`, `extension`, or `divergence`.
- [x] Add `.github/workflows/p0-required-baselines.yml` with PR/workflow_dispatch required jobs for backend offline, Web build/test/smoke, contract/golden snapshots, Docker smoke, and supply-chain baseline.
- [x] Validate workflow YAML and referenced script paths without running heavyweight CI jobs locally.
- [x] Update `docs/development-progress-checklist.md` and `docs/development-status.md` for `SAL-P0-012`, moving P0 progress to 12/13 while keeping Gate G0 blocked until `SAL-P0-013`.
- [x] Add `SAL-P0-012` review notes here and create a Chinese checkpoint commit.

## SAL-P0-013 Plan

- [x] Confirm `SAL-P0-001` through `SAL-P0-012` are `DONE` and that no P0 evidence gaps remain.
- [x] Write `docs/gate-g0-baseline-review.md` with Gate G0 Go/No-Go decision, evidence matrix, accepted risks, and P1 entry constraints.
- [x] Update `docs/development-progress-checklist.md`: mark `SAL-P0-013` `DONE`, move P0 and total progress to `13/13` and `13/129`, and add `DEC-011` / `AEV-013`.
- [x] Update `docs/development-status.md` for Gate G0 passed, next executable task `SAL-P1-001`, accepted risks, and fresh resume prompt.
- [x] Run lightweight Gate G0 verification, update this review section, stage only G0 files, and create a Chinese checkpoint commit.

## Review: SAL-P0-013

- Created `docs/gate-g0-baseline-review.md` with the Gate G0 decision `GO with accepted risks`, evidence matrix, accepted risk register, and P1 entry constraints.
- Updated `docs/development-progress-checklist.md`: P0 is `DONE` at 13/13, total progress is 13/129, `SAL-P0-013` is `DONE`, `SAL-P1-001` is `READY`, and `DEC-011` / `AEV-013` record the Gate decision and evidence.
- Updated `docs/development-status.md`: current phase moves to P1 engineering hardening preparation, Gate G0 is passed, next task is `SAL-P1-001`, and the next-start prompt reflects the new recovery state.
- Accepted but did not fix G0 risks `RSK-006`, `RSK-008`, `RSK-010`, `RSK-011`, and `RSK-012`; these remain assigned to P1/P6 closure paths and do not permit release until closed or formally waived.
- Verification scope for `SAL-P0-013`: locked baseline validation, patch registry check, workflow YAML parse, API/config/database/report-signal summary assertions, stale-status scan, and `git diff --check`.

## Review: SAL-P0-012

- Added `UPSTREAM_BASE.md`, documenting the immutable DSA `v3.26.1` baseline, origin/upstream remotes, isolated worktree/cache layout, sync procedure, local deviation taxonomy, baseline scripts, and required check names.
- Updated `docs/upstream-patches.md` so `DSA-PATCH-001` through `DSA-PATCH-003` are explicitly classified as `compatible`; current P0 has no `divergence`.
- Added `.github/workflows/p0-required-baselines.yml` with four PR/workflow_dispatch check jobs: backend offline, Web baseline, contract/golden snapshots, and Docker/supply-chain baseline.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-012` is `DONE`, P0 is 12/13, total progress is 12/129, `SAL-P0-013` is now `READY`, and `AEV-012` / `DEC-010` document evidence and CI strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-013`; Gate G0 remains not passed and P1/Quant Core remain blocked.
- Verification completed for `SAL-P0-012`: workflow YAML parsed, referenced scripts exist, baseline scripts pass `bash -n`, required check names and patch classifications are present, and `git diff --check` passed.

## Review: SAL-P0-010

- Added `scripts/run-dsa-report-signal-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, enforces registered worktree diff boundaries, generates offline report/signal fixtures, and compares committed snapshots by default.
- Added stable report/signal baseline artifacts under `docs/baselines/dsa-v3.26.1/report-signal/`: fixed inputs, Stub LLM responses, structured reports, single-stock/aggregate/market-review Markdown, Signal Evaluation details/summary, DecisionSignal summary, content hashes, and `summary.json`.
- Wrote `docs/report-signal-golden-baseline.md` with coverage, hash inventory, CI usage, verification commands, non-goals, and the decision to use offline Stub LLM/Provider-free inputs only.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-010` is `DONE`, P0 is 11/13, total progress is 11/129, and `AEV-011` / `DEC-009` document evidence and artifact strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-012`; Gate G0 remains not passed; `SAL-P0-013` remains gated by P0 completion.
- Verification completed for `SAL-P0-010`: baseline script generation and compare runs, `bash -n`, targeted upstream report/backtest tests `137 passed`, `git diff --check`, stale-progress scans, committed-fixture guard, secret/local-path scans, and `summary.json` assertions.

## Previous Review: SAL-P0-009

- Added `scripts/run-dsa-database-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, creates a sanitized SQLite fixture, dumps schema/index metadata, and compares committed SQL/JSON snapshots.
- Added stable database baseline artifacts under `docs/baselines/dsa-v3.26.1/database/`: `schema.sql`, `schema-metadata.json`, `fixture.sql`, `fixture-summary.json`, `content-hashes.json`, and `summary.json`.
- Wrote `docs/database-schema-baseline.md` with fixture coverage, hashes, verification commands, limitations, and the decision not to commit runtime `fixture.sqlite`.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-009` is `DONE`, P0 is 10/13, total progress is 10/129, and `AEV-010` / `DEC-008` document evidence and artifact strategy.
- Verification completed for `SAL-P0-009`: baseline script generation and compare runs, `bash -n`, `git diff --check`, stale-progress scans, committed-fixture guard, and `summary.json` assertions.
