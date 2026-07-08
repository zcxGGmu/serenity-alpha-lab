# DSA-First Serenity Core P0-T03 Evidence Quality Service Phase

- [x] Write failing DSA service tests for disabled, enabled, empty context, and adapter exception paths.
- [x] Create `src/serenity/services/evidence_quality_service.py` and `src/serenity/services/__init__.py` in DSA.
- [x] Keep service orchestration limited to adapter plus Serenity pure core scoring, coverage, readiness, and acquisition queue.
- [x] Preserve disabled-by-default and fail-open behavior without provider/API/UI/DB/notification/task-queue imports.
- [x] Verify service tests, adapter tests, core contract tests, static boundary guard, py_compile, and diff cleanliness.
- [x] Commit the DSA P0-T03 implementation with a detailed Chinese message.
- [x] Update `docs/dsa-first-serenity-core-development-tracker.md` and this task log with P0-T03 evidence.

## Design Check-In

- User goal: continue Phase 0 with `P0-T03: Evidence Quality Service POC` after the DSA context adapter is verified.
- Scope: add only a narrow DSA-facing service and focused tests; do not connect service to DSA API, UI, DB, providers, notifications, task queue, report rendering, portfolio, backtest, or alert paths.
- Contract: `EvidenceQualityService(enabled=False).evaluate(context)` returns a stable disabled research audit without calling adapter/core; enabled service returns JSON-serializable research-only evidence quality, readiness, coverage, gaps, acquisition tasks, and diagnostics.
- Fail-open: empty context returns deterministic blocked audit; adapter/core exceptions return `status="failed_open"` with sanitized diagnostics and no upstream exception.
- Safety: service output uses evidence-quality terminology only and does not include DSA trading fields such as `sentiment_score`, `operation_advice`, `action`, `trend_prediction`, `target_price`, `position_sizing`, `sniper_points`, `stop_loss`, or `take_profit`.

## Review

- Red test: `python3.11 -m pytest tests/serenity/services/test_evidence_quality_service.py -q` initially failed with 4 missing-module/import failures, proving the service contract was not implemented yet.
- Implementation: added DSA `src/serenity/services/evidence_quality_service.py` and package initializer with `EvidenceQualityService.evaluate(context: dict[str, Any]) -> dict[str, Any]`.
- Behavior: disabled mode returns `enabled=false` without adapter execution; enabled mode composes `dsa_context_to_evidence`, `score_research_question`, `summarize_scorecard`, `assess_source_coverage`, `assess_batch_readiness`, and `build_acquisition_queue`.
- Boundary behavior: service catches exceptions and returns `status="failed_open"` with sanitized diagnostics; empty context returns stable blocked audit; output remains JSON-serializable and research-only.
- Verification: `python3.11 -m pytest tests/serenity/services/test_evidence_quality_service.py -q` -> `4 passed`; `python3.11 -m pytest tests/serenity/adapters/test_dsa_context_to_evidence.py -q` -> `3 passed`; `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py src/serenity/services/*.py` -> exit 0; `git diff --check` -> exit 0.
- Commit: DSA `a382a0f` (`feat(serenity): 增加 Evidence Quality Service POC`).
- Next step: start `P0-T04: CLI / Script POC Runner`; still keep Phase 0 local-only and do not change DSA API, UI, DB, providers, notifications, task queue, or trading-decision fields.

# DSA-First Serenity Core P0-T02 Context Adapter Phase

- [x] Write DSA adapter tests for complete context, empty context, missing news/fundamentals, and legacy flat keys.
- [x] Create standard-library-only `src/serenity/adapters/dsa_context_to_evidence.py` in DSA.
- [x] Keep adapter input as plain `dict[str, Any]` and avoid binding to DSA large runtime objects.
- [x] Preserve provenance through explicit source types and mark uncertain data as `unverified_context`.
- [x] Verify adapter tests, core contract tests, static boundary guard, py_compile, and diff cleanliness.
- [x] Update `docs/dsa-first-serenity-core-development-tracker.md` and this task log with P0-T02 evidence.
- [x] Stage only P0-T02 handoff files in Serenity and commit with a detailed Chinese message.

## Design Check-In

- User goal: continue Phase 0 with `P0-T02: DSA Context 到 Evidence Adapter` after P0-T01 core contract is verified.
- Scope: add only a deterministic adapter in DSA `src/serenity/adapters` plus focused tests; do not touch DSA API, UI, DB, providers, notifications, task queues, or report semantics.
- Contract: adapter accepts ordinary context dictionaries and emits `EvidenceItem` values consumable by the P0-T01 core contract.
- Source mapping: quote data -> `market_data`, technical blocks -> `technical_indicator`, fundamentals -> `fundamental`, news -> `news`, social context -> `social`, historical context -> `history_context`, uncertain legacy text -> `unverified_context`.
- Safety: never map Serenity evidence or scores into DSA `sentiment_score`, `operation_advice`, `action`, `trend_prediction`, `target_price`, `position_sizing`, `sniper_points`, `stop_loss`, or `take_profit`.

## Review

- Implementation: added DSA `src/serenity/adapters/dsa_context_to_evidence.py` and package initializer to convert DSA analysis context dictionaries into stable Serenity `EvidenceItem` records.
- Input support: adapter handles `subject`, `blocks.quote`, `blocks.technical`, `blocks.fundamentals`, `blocks.news`, `social_context`, `history_context`, and legacy flat keys such as `trend_result`, `fundamental_context`, and `news_context`.
- Boundary behavior: adapter is pure and deterministic, does not mutate input, does not call providers/API/DB/UI/notifications/task queues, and keeps uncertain context as `unverified_context`.
- Verification: `python3.11 -m pytest tests/serenity/adapters/test_dsa_context_to_evidence.py -q` -> `3 passed`; `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py src/serenity/adapters/*.py` -> exit 0; `git diff --check` -> exit 0.
- Commit: DSA `b85b72a` (`feat(serenity): 增加 DSA Context Evidence Adapter`).
- Next step: start `P0-T03: Evidence Quality Service POC`; still keep `SERENITY_RESEARCH_ENABLED=false` default and do not change DSA API, UI, DB, providers, notifications, task queue, or trading-decision fields.

# DSA-First Serenity Core P0-T01 Core Contract Phase

- [x] Write failing DSA core contract tests for normal evidence, empty evidence, and missing source metadata.
- [x] Create minimal standard-library `src/serenity/core/*` modules in DSA.
- [x] Keep core deterministic and free of DSA provider/API/UI/notification/task-queue imports.
- [x] Verify P0-T01 core contract tests and the Global static boundary guard.
- [x] Update `docs/dsa-first-serenity-core-development-tracker.md` and this task log with P0-T01 evidence.
- [x] Stage only P0-T01 files and commit with a detailed Chinese message.

## Design Check-In

- User goal: start Phase 0 from `P0-T01: Serenity Core 最小契约抽取` after Global guardrails are verified.
- Scope: copy/rebuild only minimal evidence, retrieval, scoring, source coverage, readiness, and acquisition queue logic into DSA `src/serenity/core`.
- Contract: `EvidenceItem` uses DSA-facing fields `id`, `title`, `source_type`, `publisher`, `published_at`, `url`, `excerpt`, `claims`, `symbols`, and `metadata`.
- Safety: no Serenity UI, CLI, memo pack, local server, generated output, provider fetches, SQLAlchemy, FastAPI, React assets, notifications, task queue, or cross-repository absolute-path import.
- Empty/missing-source behavior: empty evidence returns stable audit objects; evidence missing source metadata produces explicit gaps rather than fabricated source values.

## Review

- Red test: `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` initially failed with `ModuleNotFoundError: No module named 'src.serenity.core.acquisition_queue'`.
- Implementation: added DSA `src/serenity/core` modules for EvidenceItem, deterministic retrieval, research scoring, source coverage, readiness audit, and acquisition queue, plus package initializers.
- Contract: `EvidenceItem` uses `id`, `title`, `source_type`, `publisher`, `published_at`, `url`, `excerpt`, `claims`, `symbols`, and `metadata`; output audit dicts stay research-only and avoid DSA trading fields.
- Gap handling: empty evidence returns stable blocked audit objects; missing source metadata creates `missing_source_metadata` coverage and acquisition tasks without fabricating publisher, URL, or excerpt.
- Verification: `python3.11 -m pytest tests/serenity/core/test_core_contract.py -q` -> `3 passed`; `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` -> `3 passed`; `python3.11 -m py_compile src/serenity/__init__.py src/serenity/core/*.py` -> exit 0; `EvidenceItem` import smoke passed.
- Commit: DSA `4e34c78` (`feat(serenity): 抽取最小 Core 研究契约`).
- Next step: start `P0-T02: DSA Context 到 Evidence Adapter`; still do not change DSA API, UI, DB, providers, notifications, task queue, or trading-decision fields.

# DSA-First Serenity Core Global Guardrails Phase

- [x] Confirm DSA branch `codex/serenity-phase-0-evidence-bridge` is active from the handoff HEAD.
- [x] Implement G-T01 integration boundary guardrails in DSA docs, README, and `.env.example`.
- [x] Implement G-T02 phase branch / PR / commit conventions in DSA contribution docs and boundary doc.
- [x] Capture G-T03 baseline verification snapshot before Serenity code enters DSA runtime.
- [x] Run fresh validation commands for G-T01, G-T02, and G-T03.
- [x] Update `docs/dsa-first-serenity-core-development-tracker.md` with Global task evidence and next step.
- [x] Stage only Global-phase files in DSA and tracker/todo files in Serenity; leave `output/ui/*` untouched.
- [x] Commit the Global phase with detailed Chinese commit messages.

## Design Check-In

- User goal: continue from the DSA-first handoff and complete Global tasks before starting Phase 0 Evidence Bridge POC.
- Execution order: G-T01 integration boundary guardrails, then G-T02 branch/commit conventions, then G-T03 baseline verification snapshot.
- Product boundary: `daily_stock_analysis` remains the main product and runtime; Serenity Core is auxiliary evidence-quality, research-audit, evidence-gap, and safety-boundary support only.
- Safety boundary: never map Serenity score or quality outputs into DSA `sentiment_score`, `operation_advice`, `action`, `trend_prediction`, target price, position sizing, sniper points, stop loss, or take profit.
- Repository hygiene: do not modify, stage, commit, or roll back existing Serenity `output/ui/*` generated-output dirty changes.

## Review

- DSA branch: created and worked on `codex/serenity-phase-0-evidence-bridge` from baseline commit `bfdee03`.
- G-T01 implementation: added `docs/serenity-integration-boundaries.md`, README auxiliary research note, `.env.example` default `SERENITY_RESEARCH_ENABLED=false`, and static guardrail test `tests/test_serenity_integration_boundaries.py`.
- G-T02 implementation: documented phase branch names, PR requirements, commit scopes, feature flag evidence, verification evidence, risk notes, and rollback requirements in the boundary doc and `docs/CONTRIBUTING.md`.
- G-T03 implementation: added `docs/serenity-baseline-verification.md` with Python/Node versions, backend/frontend baseline commands, exit codes, environment blockers, and recovery conditions.
- Validation: `python3.11 -m pytest tests/test_serenity_integration_boundaries.py -q` passed with `3 passed`; broad backend baseline failed due missing dependencies (`pandas`, `json_repair`) and Python 3.9 default; frontend lint/build failed because `apps/dsa-web/node_modules` is missing.
- Boundary review: a read-only subagent confirmed the document/config coverage and recommended the static guardrail test, which is now implemented.
- Status note: older historical sections below still describe the pre-Global handoff state at the time they were written; the current source of truth is this Global Guardrails Phase plus `docs/dsa-first-serenity-core-development-tracker.md`.

# DSA-First Serenity Core Status Handoff Phase

- [x] Review current tracker, task log, lessons, and repository status.
- [x] Update the tracker with latest completed and incomplete development status.
- [x] Add a copyable restart prompt for continuing from the current progress.
- [x] Record the recurring habit for phase-end status updates, verification, and commits.
- [x] Validate markdown status, placeholder scan, and diff cleanliness.
- [x] Commit this phase with a detailed Chinese commit message.

## Design Check-In

- User goal: update the latest development state so the next Codex session can continue without losing context.
- Status truth: DSA-first plan and tracker are complete and committed at `81a5709`; implementation in the DSA repository has not started.
- Next work: start from `G-T01`, then `G-T02`, `G-T03`, then `P0-T01`.
- Hygiene rule: leave existing `output/ui/*` generated-output dirty changes untouched unless explicitly requested.
- Habit rule: after every phase, update tracker/task status, verify, stage only owned files, and commit with a detailed Chinese message automatically.

## Review

- Implementation: updated `docs/dsa-first-serenity-core-development-tracker.md` with a current development status snapshot, explicit completed/incomplete tables, next-step sequence, workspace caveats, and a copyable restart prompt.
- Status truth: DSA-first planning documents are complete; DSA implementation remains not started, with `G-T01`, `G-T02`, `G-T03`, and all P0-P4 tasks still open.
- Habit persistence: updated `tasks/lessons.md` so future sessions automatically refresh tracker/task status, verify, stage only owned files, and commit after each phase.
- Validation: tracker headings, targeted placeholder scan, restart-prompt markers, and `git diff --check` were run before this phase was staged.
- Repository note: existing `output/ui/*` generated-output changes remain intentionally unstaged.

# DSA-First Serenity Core Development Tracker Phase

- [x] Review the current DSA-first Serenity Core development plan and tracking conventions.
- [x] Create a detailed iterative development tracker under `docs/`.
- [x] Include phase gates, task IDs, dependencies, files, tests, DoD, rollback, and evidence fields.
- [x] Validate markdown headings, placeholder scan, and repository diff cleanliness.
- [x] Record review notes and reusable lessons.

## Design Check-In

- User goal: generate a detailed and rigorous development progress checklist based on the current DSA-first Serenity Core plan so future iterations can execute against it.
- Tracking target: use DSA as the main product and Serenity Core as an auxiliary evidence-quality and research-audit module.
- Execution constraint: checklist must support phase-by-phase implementation, verification-before-done, fail-open behavior, feature-flag rollout, and explicit rollback.
- Persistence constraint: keep `analysis_history.context_snapshot.serenity_research` as the first persistence target and gate any new dedicated table behind an explicit decision record.
- Safety constraint: never map Serenity quality outputs into DSA trading advice, target prices, position sizing, trend prediction, sentiment score, or buy/sell semantics.

## Review

- Implementation: created `docs/dsa-first-serenity-core-development-tracker.md` as the long-running implementation tracker for the DSA-first Serenity Core integration plan.
- Scope: tracker covers global guardrails, Phase 0 evidence bridge POC, Phase 1 report add-on, Phase 2 Agent tools, Phase 3 research-task persistence, Phase 4 provenance/safety guardrails, release readiness, risk decisions, and progress overview.
- Engineering controls: every task includes owner/status metadata, dependencies, target files, implementation checklist, validation commands, DoD, rollback notes, and phase review gates.
- Validation: heading scan completed, placeholder scan returned no matches, referenced DSA and source-plan paths exist, and `git diff --check` passed.
- Repository note: unrelated generated UI output files were already dirty and were left untouched.

# Serenity Alpha Lab Bilingual Diagram README Phase

- [x] Inspect the requested `fireworks-tech-graph` skill and Claude Official style 6 reference.
- [x] Inspect the real project architecture, CLI surfaces, UI routes, evidence model, retrieval, scoring, memo pack, acquisition queue, and coverage modules.
- [x] Create a Claude Official style architecture diagram as SVG and PNG.
- [x] Create a Claude Official style research workflow diagram as SVG and PNG.
- [x] Create a Claude Official style evidence-closure framework diagram as SVG and PNG.
- [x] Update README with English and Chinese diagram sections and architecture explanation.
- [x] Verify SVG syntax, PNG exports, README links, tests, and repository diff.
- [x] Record review notes and reusable lessons.

## Design Check-In

- User goal: deeply analyze the current project, use `fireworks-tech-graph`, draw a group of style 6 Claude Official diagrams, improve the README, and provide both English and Chinese versions.
- Diagram set: system architecture, research generation flow, and evidence-closure framework.
- Style constraint: use Claude Official warm cream background, soft blue input/source nodes, teal processing nodes, beige infrastructure nodes, gray storage/state nodes, rounded boxes, dark strokes, and technical arrow labels.
- Accuracy constraint: diagrams must reflect the actual Python package boundaries and local-first product pipeline, including CLI commands, JSONL/config inputs, topic resolver, retrieval/scoring/readiness, memo/UI generation, HTTP APIs, durable JSON state, and report handoff outputs.
- README constraint: keep the previous Gajae-inspired structure but add visual architecture and bilingual English/Chinese sections without introducing broken image links.

## Review

- Architecture analysis: mapped the current package around evidence ingestion/validation, topic resolution, retrieval, scoring/readiness, memo pack generation, dashboard publication, local HTTP workflow APIs, durable JSON state, and research-only handoff outputs.
- Diagram implementation: generated three Claude Official style 6 diagrams as SVG and PNG under `docs/assets/diagrams/`: system architecture, research generation flow, and evidence closure framework.
- README implementation: updated `README.md` with the architecture visuals and English explanations, then added a full Chinese version in `README.zh.md` with matching diagram references and localized project/workflow documentation.
- Visual QA: rendered PNGs from SVG with `cairosvg`, inspected the generated images, and corrected overlapping state nodes plus clipped framework labels before final export.
- Verification: SVG XML parsing passed, PNG dimensions were validated, README local references reported `missing local refs: none`, `git diff --check` passed, and `python3 -m pytest tests -q` passed with `165 passed`.

# Serenity Alpha Lab README Gajae-Style Redesign Phase

- [x] Review the target `gajae-code` README visual structure and section rhythm.
- [x] Review the current Serenity Alpha Lab README, metadata, and available assets.
- [x] Confirm the README redesign direction before implementation.
- [x] Rewrite README with an adapted center-hero, badges, highlights, product/workflow, install, and development structure.
- [x] Verify markdown readability, local links, commands, and repository diff.
- [x] Record review notes and reusable lessons.

## Design Check-In

- User goal: redesign the Serenity Alpha Lab README with a close structural imitation of `Yeachan-Heo/gajae-code` while keeping all claims accurate to this Python local-first investment research product.
- Reference pattern to adapt: centered hero/title/tagline, badge row, beta/safety note, recent highlights, "What is it?", install, quick start, workflow surface, development, contributors/inspirations/license-style closing.
- Asset constraint: this repository currently has no local `.png`, `.jpg`, `.svg`, or `.webp` files to reference, so the first pass should avoid broken image links and use text/HTML layout instead of fake assets.
- Safety constraint: keep the investment-research boundary explicit; no buy/sell/hold language, target prices, or position sizing.
- Recommended approach: imitate the README architecture and tone strongly, but replace Gajae-specific agent runner concepts with Serenity Alpha Lab concepts such as local evidence, bilingual dashboards, Run Center, project library, evidence tasks, quality gates, and report handoffs.

## Review

- Implementation: rewrote `README.md` into a Gajae-inspired structure with centered identity, badge row, tagline, recent highlights, product explanation, install, quick start, stable run, product/workflow tables, generated outputs, user workflow, importer, report anatomy, development, configuration, lineage, and license sections.
- Asset handling: avoided local image references because this repository currently has no `.png`, `.jpg`, `.svg`, or `.webp` assets, preventing broken README hero links.
- Accuracy boundary: preserved Serenity Alpha Lab's research-only positioning and explicitly excluded buy/sell/hold instructions, target prices, and position sizing.
- Verification: reviewed the rewritten README, ran `git diff --check`, and ran a local-link script that reported `missing local links: none`.
- Repository impact: changed only `README.md` and `tasks/todo.md`.

# Serenity Alpha Lab Filtered Project Handoff Phase

- [x] Record the filtered project handoff phase and product target.
- [x] Add failing UI/HTTP tests for filtered project handoff copy and preview.
- [x] Build a research-only handoff brief from the current filtered project list.
- [x] Render bilingual filtered handoff preview and copy controls.
- [x] Record filtered handoff copies in the review event log.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: let users hand off exactly the current filtered project queue instead of always copying the full saved-project library.
- UX target: saved-project controls should expose a filtered handoff preview, filtered item count, and copy action derived from the active filters and sort order.
- Research boundary: filtered project handoffs summarize workflow metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because filtered handoff copy, preview, helper functions, and metadata were missing.
- Implementation: added `buildFilteredProjectQueueHandoffBrief`, `renderFilteredProjectQueueHandoffPreview`, and `copyFilteredProjectQueueHandoffBrief` so copy/export uses the active project filters and sort order.
- UI implementation: added bilingual filtered handoff controls and preview metadata (`data-filtered-project-handoff`, `data-filtered-project-handoff-action`, `data-filtered-project-handoff-preview`, and `data-filtered-project-handoff-items`).
- Audit implementation: filtered handoff copies append a review timeline event using the existing queue-handoff event family with localized copied-state labels.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.68s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.65s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.73s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest filtered project handoff code; server PID is `34585`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized filtered handoff copy, filtered handoff helper functions, and filtered handoff data attributes.
- Async smoke: `POST /api/analyze-jobs` accepted an `HBM` job; `/api/runs` showed a completed HBM run with `canonical_theme=HBM`, first ticker `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Project Activity Filter Phase

- [x] Record the project activity filter phase and product target.
- [x] Add failing UI/HTTP tests for activity filters and activity sorting.
- [x] Add bilingual activity state controls for all, active, and inactive projects.
- [x] Sort saved projects by activity count without changing research outputs.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make saved projects operable when many reports accumulate by surfacing projects with recent collaboration activity.
- UX target: users should filter projects by activity state and sort by activity count from the existing project library controls.
- Research boundary: project activity filtering is workflow metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the project activity filter, activity sort, state helper functions, and activity filter metadata were missing.
- Implementation: added `projectActivityState`, `projectActivityStateLabel`, and `filterProjectActivity`, plus a bilingual `project-activity-filter` control for all, has-activity, and no-activity states.
- Sorting implementation: added `Most active` / `最活跃` to the saved-project sort selector and ordered records by project-specific review event count when selected.
- Metadata implementation: project cards now expose `data-project-activity-filter` and `data-project-activity-state`, and project search includes activity state, latest activity, and activity summary text.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.68s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.54s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.69s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project activity filter code; server PID is `1325`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized activity filter copy, `id="project-activity-filter"`, `data-project-activity-filter`, `data-project-activity-state`, `projectActivityState`, `projectActivityStateLabel`, and `filterProjectActivity`.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Project Activity Summary Phase

- [x] Record the project activity summary phase and product target.
- [x] Add failing UI/HTTP tests for latest activity summaries on project cards and detail drawers.
- [x] Render compact bilingual project activity summaries from review events.
- [x] Show latest event, event count, and activity metadata without changing research recommendations.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make saved projects easier to triage before opening the full review timeline.
- UX target: project cards and detail drawers should show latest activity, event count, and audit state derived from the existing review event log.
- Research boundary: project activity summaries are collaboration metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because project activity copy, activity helper functions, and activity metadata attributes were missing.
- Implementation: added `projectReviewActivitySummary` and `renderProjectActivitySummary` so project cards and detail drawers show latest activity, event count, latest activity label, and an empty state.
- Interaction implementation: activity summaries reuse the existing review event log and update from project-specific events without changing research scores, rankings, or recommendations.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.67s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.56s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.68s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project activity summary code; server PID is `18856`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized project activity summary copy, `data-project-activity-summary`, `data-project-activity-count`, `data-project-latest-activity`, `projectReviewActivitySummary`, and `renderProjectActivitySummary`.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Collaboration Event View Phase

- [x] Record the collaboration event view phase and product target.
- [x] Add failing UI/HTTP tests for event filters and count summary.
- [x] Render compact bilingual collaboration event filters.
- [x] Let filters narrow the project review timeline by event type.
- [x] Keep the event view operational only, without investment guidance.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make team review history inspectable by event type so saved research projects can be operated as a stable collaborative product workflow.
- UX target: users should filter project review events by all events, status changes, owner changes, detail opens, comparison copies, and queue handoff copies.
- Research boundary: collaboration event filters summarize workflow audit metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose the collaboration event view, event filter, event summary, or event type helper functions.
- Implementation: added a compact collaboration event view in the project review timeline with a type filter and count cards for all, status, owner, detail, comparison, and queue handoff events.
- Interaction implementation: `projectReviewEventTypeLabel`, `renderProjectReviewEventSummary`, and `filterProjectReviewEvents` now keep event counts visible and narrow the review timeline by selected event type.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.68s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.51s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.69s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest collaboration event view code; server PID is `27143`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized collaboration event view copy, `id="project-review-event-filter"`, `id="project-review-event-summary"`, `data-project-review-event-filter`, and `data-project-review-event-count`.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Project Owner Assignment Phase

- [x] Record the project owner assignment phase and product target.
- [x] Add failing UI/API tests for editable project owners and review events.
- [x] Persist project owner metadata through the project library API.
- [x] Add bilingual owner assignment controls on project cards.
- [x] Record owner changes in the review event timeline.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make owner roles editable so shared research queues can be operated by a team instead of only inferred from next actions.
- UX target: users should be able to change the project owner from each saved project card and see the change in the review trail.
- Research boundary: owner assignment is workflow metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_persists_projects tests/test_ui_http_e2e.py::test_http_e2e_project_review_event_api_persists_events -q` first failed because owner assignment controls were missing, `/api/projects` dropped `owner`, and owner-change events were not represented in the UI.
- Implementation: added `projectOwnerOptions` and `updateResearchProjectOwner` so saved project cards can edit owner roles directly, persist the change, and re-render queue filters.
- Persistence implementation: `_normalize_project_record` now preserves `owner` through the project library API.
- Audit implementation: owner changes append an `owner-changed` review event with localized labels (`Owner changed` / `负责人已更新`).
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_persists_projects tests/test_ui_http_e2e.py::test_http_e2e_project_review_event_api_persists_events -q` -> `4 passed in 1.94s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.52s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.72s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project owner assignment code; server PID is `39209`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized owner assignment copy, `projectOwnerOptions`, `updateResearchProjectOwner`, `data-project-owner-value`, and `data-project-owner-select`.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Project Owner Queue Phase

- [x] Record the project owner queue phase and product target.
- [x] Add failing UI/HTTP tests for owner queue filtering and handoff metadata.
- [x] Render a compact bilingual owner queue summary near the project queue controls.
- [x] Add owner filtering and item metadata without changing research recommendations.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make saved research projects easier to operate as a shared product workflow, not only an individual report library.
- UX target: users should see which projects are unassigned or owned by evidence, review, rerun, or archive workflow roles before handing off a queue.
- Research boundary: owner queues are workflow assignment metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose `Project owner queue`, owner filtering, owner queue summary, owner helper functions, or owner data attributes.
- Implementation: added bilingual project owner filtering and owner queue cards for unassigned, evidence owner, report reviewer, rerun owner, and archive owner roles.
- Filtering implementation: `projectOwnerForRecord`, `projectOwnerLabel`, `renderProjectOwnerQueueSummary`, and `filterProjectOwnerQueue` now derive workflow owner roles from saved project next actions and include owner metadata in project search and cards.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.66s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.53s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.71s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project owner queue code; server PID is `67522`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized owner queue copy, `id="project-owner-filter"`, `id="project-owner-queue-summary"`, `data-project-owner-queue`, and `data-project-owner-count`.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Project Queue Handoff Preview Phase

- [x] Record the project queue handoff preview phase and product target.
- [x] Add failing UI/HTTP tests for queue handoff preview visibility.
- [x] Render a compact bilingual handoff preview near the queue controls.
- [x] Keep preview content research-only and derived from saved project metadata.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make copied project queue handoffs inspectable before sharing with another reviewer.
- UX target: users should see a compact handoff preview and item count before using the copy queue handoff action.
- Research boundary: handoff previews summarize workflow metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose `Queue handoff preview`, `renderProjectQueueHandoffPreview`, `project-queue-handoff-preview`, or queue handoff preview data attributes.
- Implementation: added a bilingual compact queue handoff preview below the next-action queue controls, rendered from `buildProjectQueueHandoffBrief`, with item count metadata and research-only boundary copy.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.67s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.53s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.71s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest queue handoff preview code; server PID is `82373`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain localized queue handoff preview copy, `id="project-queue-handoff-preview"`, and queue handoff preview data attributes.
- Async smoke: `POST /api/analyze-jobs` completed through `/api/runs`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `href=/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Queue Handoff Event Traceability Phase

- [x] Record the queue handoff event traceability phase and product target.
- [x] Add failing UI/API tests for queue handoff review event labels.
- [x] Add bilingual queue handoff event labels to the review timeline.
- [x] Ensure server-backed review events preserve queue handoff metadata.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make copied project queue handoffs auditable in the same review trail used for project operations.
- UX target: review timelines should display queue handoff copies as explicit queue handoff events instead of generic review events.
- Research boundary: queue handoff events are workflow audit metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_review_event_api_persists_events -q` first failed because `queue-handoff-copied` fell back to a generic review event label and Chinese UI did not expose `已复制队列交接`.
- Implementation: added `review_event_queue_handoff_copied` in Chinese and English copy maps and taught `projectReviewEventLabel` to render `queue-handoff-copied` explicitly.
- API verification: the server-backed `/api/project-events` test now persists and lists a `queue-handoff-copied` event with `projectId=queue-handoff` and the queue handoff label.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_review_event_api_persists_events -q` -> `3 passed in 1.19s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.51s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.69s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest queue handoff event traceability code; server PID is `30119`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain `queue-handoff-copied` and the localized queue handoff event copy.
- Async smoke: `POST /api/analyze-jobs` returned `job-7ab0fc54211d`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Queue Handoff Brief Phase

- [x] Record the project queue handoff brief phase and product target.
- [x] Add failing UI/HTTP tests for copyable queue handoff briefs.
- [x] Build a research-only queue handoff brief grouped by next action.
- [x] Add bilingual copy and UI controls for copying the queue handoff.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make Serenity Alpha Lab usable as a stable research operations product where project queues can be handed off to another reviewer.
- UX target: saved project users should be able to copy a concise next-action queue brief grouped by evidence collection, report review, rerun, and archive work.
- Research boundary: queue handoff briefs summarize workflow metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose `Project queue handoff`, `buildProjectQueueHandoffBrief`, `copyProjectQueueHandoffBrief`, or queue handoff data attributes.
- Implementation: added a bilingual copyable project queue handoff control inside the next-action queue summary.
- Handoff implementation: `buildProjectQueueHandoffBrief` groups saved projects by next action, includes topic, top ticker, quality, next-action reason, and report href, and keeps explicit research-only boundary language.
- Interaction implementation: `copyProjectQueueHandoffBrief` writes the queue handoff to clipboard, updates button feedback, and records a review event.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.67s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.52s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.71s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest queue handoff code; server PID is `97441`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain the project queue handoff copy and `data-project-queue-handoff="research-only"`.
- Async smoke: `POST /api/analyze-jobs` returned `job-b8a873e9c262`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Next-Action Queue Summary Phase

- [x] Record the next-action queue summary phase and product target.
- [x] Add failing UI/HTTP tests for next-action queue counts.
- [x] Render bilingual next-action queue count cards in the project library.
- [x] Let queue count cards set the matching next-action filter.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make Serenity Alpha Lab feel like an operable research product, not only a report generator.
- UX target: saved project users should see how many projects need evidence collection, report review, rerun, or archive handling before touching filters.
- Research boundary: queue counts are workflow triage metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose `Next-action queue`, `project-next-action-queue-summary`, `renderProjectNextActionQueueSummary`, `filterProjectNextActionQueue`, or queue count data attributes.
- Implementation: added a bilingual next-action queue summary with count cards for Collect evidence, Review report, Rerun analysis, and Archive projects.
- Interaction implementation: queue cards call `filterProjectNextActionQueue`, set the `project-next-action-filter`, and re-render the saved project list with the matching workflow step.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.65s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.49s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.64s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest next-action queue summary code; server PID is `46705`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain the next-action queue copy and `id="project-next-action-queue-summary"`.
- Async smoke: `POST /api/analyze-jobs` returned `job-76f739664872`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Next-Action Filtering Phase

- [x] Record the next-action filtering phase and product target.
- [x] Add failing UI/HTTP tests for next-action project filters.
- [x] Add bilingual project-library filter controls for workflow next actions.
- [x] Make project search and filtering include next-action metadata.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: help users operate Serenity Alpha Lab as a stable investment research product by turning saved workflow state into a project queue they can triage.
- UX target: project library users should be able to focus on projects needing evidence collection, report review, reruns, or archive handling without opening each project drawer.
- Research boundary: next-action filters are workflow controls only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` first failed because the UI did not expose `Project next action`, `project-next-action-filter`, `projectNextActionLabel`, or `data-project-next-action-filter`.
- Implementation: added a bilingual project next-action filter to the saved project library with Collect evidence, Review report, Rerun analysis, and Archive project modes.
- Filtering implementation: `projectLibraryFilteredRecords` now filters by `projectNextActionSummary(project).type`, exposes `data-project-next-action-filter`, and includes next-action labels and reasons in project search metadata.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.65s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.51s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.71s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest next-action filter code; server PID is `90822`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain the next-action filter copy and `id="project-next-action-filter"`.
- Async smoke: `POST /api/analyze-jobs` returned `job-63d7049ebcd5`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Next Action Phase

- [x] Record the project next-action phase and product target.
- [x] Add failing UI/HTTP tests for project next-action summaries.
- [x] Enrich saved project API records with workflow next-action summaries.
- [x] Render next-action reason and priority on project cards and detail drawers.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where saved projects tell users what to do next.
- UX target: project library cards and detail drawers should explain whether the next step is evidence collection, rerun, review, delivery, or archive.
- Research boundary: next actions are workflow guidance only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_next_action_summary -q` first failed because the UI had no `projectNextActionSummary` hook and `/api/projects` did not return `nextActionSummary`.
- Implementation: `/api/projects` now enriches saved project records with `nextActionSummary`, deriving workflow next steps from project status, task progress, remaining evidence collection, report href, and delivery state.
- UI implementation: project library cards and project detail drawers now render `Workflow next step` / `工作流下一步`, with `data-project-next-action` and `data-project-next-action-priority` hooks for filtering, tests, and future automation.
- Behavior: if tasks remain `to_collect`, the next action is `Collect missing evidence`; once collection blockers are cleared and task progress exists, the next action becomes `Review report`; delivered and needs-rerun states keep explicit archive/rerun guidance.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_next_action_summary -q` -> `2 passed in 0.68s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `31 passed in 7.66s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `165 passed in 7.94s`.
- Release verification: `make verify` -> `165 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project next-action code; server PID is `48708`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain the next-step copy (`工作流下一步` and `Workflow next step`).
- Async smoke: `POST /api/analyze-jobs` returned `job-6b16a4b62f68`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Evidence Progress Phase

- [x] Record the project evidence progress phase and product target.
- [x] Add failing UI/HTTP tests for project-library task progress propagation.
- [x] Enrich saved project API records with task status progress summaries.
- [x] Render evidence progress on project cards and detail drawers.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where saved projects show evidence collection progress without opening every report.
- UX target: project library cards and detail drawers should show to-collect, collected, verified, and total task counts from durable task-status records.
- Research boundary: evidence progress is workflow state only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_evidence_progress -q` first failed because the UI had no `projectEvidenceProgressSummary` hook and `/api/projects` did not return `evidenceProgressSummary`.
- Implementation: `/api/projects` now enriches saved project records with task-status progress from `task_statuses.json`, summarizing total, verified, collected, and to-collect task counts.
- UI implementation: project library cards and project detail drawers now render `Evidence progress` / `证据进度`, expose `data-project-evidence-progress` and `data-project-verified-tasks`, and keep evidence progress separate from research conclusions.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_evidence_progress -q` -> `2 passed in 0.60s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `30 passed in 6.96s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `164 passed in 7.12s`.
- Release verification: `make verify` -> `164 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project evidence progress code; server PID is `13229`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- UI smoke: rebuilt Chinese and English homepages both contain the evidence progress copy (`证据进度` and `Evidence progress`).
- Async smoke: `POST /api/analyze-jobs` returned `job-4cb5e075acca`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.

# Serenity Alpha Lab Project Quality Propagation Phase

- [x] Record the project quality propagation phase and product target.
- [x] Add failing UI/HTTP tests for project-library quality delta propagation.
- [x] Enrich saved project API records with latest evidence quality summary.
- [x] Render latest evidence impact on project cards and detail drawers.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where saved projects show whether imported evidence improved report quality.
- UX target: project library cards and detail drawers should show the latest evidence quality delta without forcing users to open raw audit history.
- Research boundary: quality deltas are evidence-readiness feedback only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_latest_quality_delta -q` first failed because the UI had no `projectEvidenceQualitySummary` hook and `/api/projects` did not return `evidenceQualitySummary`.
- Implementation: `/api/projects` now enriches saved project records with the latest matching evidence-quality summary from `project_evidence_audits.json`, while preserving project status as user-controlled workflow state.
- UI implementation: project library cards and detail drawers now render `Latest evidence impact` / `最新证据影响`, expose `data-project-quality-delta`, and keep the detailed audit log available in the drawer.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_includes_latest_quality_delta -q` -> `2 passed in 0.61s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `29 passed in 6.46s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `163 passed in 6.60s`.
- Release verification: `make verify` -> `163 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project quality propagation code; server PID is `46808`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async smoke: `POST /api/analyze-jobs` returned `job-f4e115fd7263`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.
- Repository note: this project directory is not currently inside a Git repository, so `git status` is unavailable here.

# Serenity Alpha Lab Import Quality Delta Summary Phase

- [x] Record the import quality delta summary phase and product target.
- [x] Add failing UI/HTTP tests for visible quality delta summaries.
- [x] Summarize latest evidence import quality before/after/delta in project audit UI.
- [x] Preserve existing detailed evidence audit logs and server-backed audit records.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: after importing evidence, make the quality-change loop visible enough that users can see whether the report improved without reading raw audit rows.
- UX target: project evidence audit surfaces should show a compact latest quality delta summary with before score, after score, delta, ticker, and task id.
- Research boundary: quality delta is workflow/evidence readiness feedback only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: the target tests first failed because the UI had no `renderProjectEvidenceQualityDeltaSummary` hook and `/api/project-evidence-audits` did not return a `summary` object.
- Implementation: project evidence audit surfaces now render a compact latest quality delta summary with ticker, task id, before score, after score, and delta while preserving the detailed audit log.
- API implementation: `/api/project-evidence-audits` now returns both `audits` and `summary`; POST, GET, filtered GET, and clear responses all use the same summary helper.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_evidence_audit_api_persists_entries -q` -> `3 passed in 1.18s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 5.95s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.09s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest import quality delta summary code; server PID is `72101`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async smoke: `POST /api/analyze-jobs` returned `job-5a0215ab0c27`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.
- Reusable lesson recorded: evidence audit APIs should return summary-level quality delta data alongside detailed logs so product surfaces can show impact without forcing users to parse audit rows.

# Serenity Alpha Lab Preflight Evidence Import Handoff Phase

- [x] Record the preflight evidence import handoff phase and product target.
- [x] Add failing UI/HTTP tests for evidence task import handoff buttons.
- [x] Render report-deep-link handoff actions for completed run evidence tasks.
- [x] Preserve copyable search prompts while adding import handoff actions.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make preflight evidence gaps actionable beyond copying search prompts, so users can jump from run records into the generated report's evidence import workflow.
- UX target: completed Run History and Job Detail evidence gap tasks should expose a compact button that opens the generated report at the evidence task section.
- Research boundary: import handoff actions are evidence workflow controls only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: the target UI/HTTP test first failed because completed run evidence tasks did not expose `打开补证导入`; after refining the assertion to the API layer, it failed until completed tasks carried `import_handoff_href`.
- Implementation: `renderPreflightEvidenceTasks` now preserves the copy-search prompt action and adds an `openEvidenceTaskImportHandoff` button when a report href is available.
- Persistence: completed run records enrich `evidence_gap_tasks` with `import_handoff_href` through `_evidence_gap_tasks_with_handoff`, pointing to the generated report's `#evidence-tasks` section.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` -> `2 passed in 0.75s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 5.91s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.09s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest preflight evidence import handoff code; server PID is `62997`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async handoff smoke: `POST /api/analyze-jobs` returned `job-cb0376ca16ee`; completed detail retained `canonical_theme=HBM`, first task `MU`, and `import_handoff_href=/analyses/hbm-6f259a8f14/index.zh.html#evidence-tasks`.
- Reusable lesson recorded: completed preflight gap tasks should carry report-section handoff links so users can move from triage to evidence import without searching the generated page.

# Serenity Alpha Lab Evidence Gap Prioritization Phase

- [x] Record the evidence gap prioritization phase and product target.
- [x] Add failing HTTP/UI tests for preflight evidence gap tasks.
- [x] Derive prioritized gap tasks from candidate coverage metadata.
- [x] Persist evidence gap tasks through async job records.
- [x] Render one-click copy prompts in preview, Run History, and Job Detail.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: turn candidate coverage gaps into concrete next actions so users can continue investment research without manually guessing what evidence to collect.
- UX target: preflight preview and job detail should show prioritized evidence actions with copyable search prompts for missing primary/fact and risk coverage.
- Research boundary: gap actions are evidence collection tasks only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` first failed with `KeyError: 'evidence_gap_tasks'`, proving resolver preview and async job records did not expose executable preflight gap actions.
- Implementation: `build_topic_resolution_preview` now derives `evidence_gap_tasks` from candidate-level primary/fact and risk coverage, using prioritized `missing_primary_source` and `missing_risk_coverage` tasks with copyable search prompts.
- Persistence: `_write_run_record`, `_preflight_run_metadata`, and `_merge_run_metadata` now carry `evidence_gap_tasks` through queued, running, failed, retry, and completed async job states.
- UI implementation: the input preview panel now includes `预检补证动作`, and Run History plus Job Detail render compact copyable evidence prompts through `renderPreflightEvidenceTasks`.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` -> `3 passed in 1.28s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 6.03s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.34s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest evidence gap prioritization code; server PID is `99214`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async evidence-gap smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-d5fbfbe25ed3`; completed detail retained `canonical_theme=HBM` and first evidence gap task `MU primary filing HBM`.
- Reusable lesson recorded: preflight evidence gaps should be executable tasks derived from candidate coverage and persisted through the async job lifecycle.

# Serenity Alpha Lab Candidate Coverage Preflight Phase

- [x] Record the candidate coverage preflight phase and product target.
- [x] Add failing HTTP tests for per-candidate coverage metadata.
- [x] Implement candidate-level evidence, primary, and risk counts in resolver preview.
- [x] Persist candidate coverage metadata through async job run records.
- [x] Render compact candidate coverage details in preview, Run History, and Job Detail.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: make the pre-analysis scope auditable enough for stable product use, so users can see not only which candidates will be analyzed but also why each candidate is covered.
- UX target: preview and job detail should show candidate-level evidence, primary-source, and risk coverage before the full report is generated.
- Research boundary: candidate coverage is evidence-readiness metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` first failed with `KeyError: 'candidate_coverage'`, proving the resolver preview and async job records did not expose per-candidate coverage.
- Implementation: `build_topic_resolution_preview` now returns `candidate_coverage` with ticker-level evidence, primary/fact, risk counts, and localized coverage labels; async job records persist the same metadata across queued/running/completed states.
- UI implementation: the input preview panel now includes `候选覆盖明细`, and Run History plus Job Detail render compact candidate coverage chips for queued/running/completed jobs.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` -> `3 passed in 1.18s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 5.90s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.09s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest candidate coverage preflight code; server PID is `21147`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async coverage smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-c0d057bc8fda`; queued and completed detail both retained `canonical_theme=HBM`, `coverage_label=140 条证据`, candidate tickers including `MU/SKHYNIX/SAMSUNG`, and candidate coverage entries such as `MU: 2 条证据`.
- Reusable lesson recorded: candidate-level evidence coverage should be generated during preflight and persisted through job lifecycle so users can audit why each candidate is included before reading reports.

# Serenity Alpha Lab Preflight Job Metadata Phase

- [x] Record the preflight job metadata phase and product target.
- [x] Add failing HTTP tests for persisted preflight metadata on async jobs.
- [x] Persist canonical theme, candidate tickers, and coverage labels when jobs are queued/running.
- [x] Render preflight metadata in Run History and Job Detail without waiting for completion manifests.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where users can trust what the system will analyze before and during background runs.
- UX target: once a user confirms an input preview and launches analysis, Run Center should preserve the resolved scope, candidate set, and evidence coverage even while the job is still queued or running.
- Research boundary: preflight metadata is scope and evidence workflow context only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: `PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` first failed with `KeyError: 'canonical_theme'`, proving async job creation did not persist backend preflight metadata.
- Implementation: async `/api/analyze-jobs` now calls the same topic resolver used by the preview API, persists `canonical_theme`, `candidate_tickers`, `coverage_label`, and `preflight_source` into queued/running/failed/completed run records, and carries preflight metadata through worker updates until completion manifests can enrich it.
- UI implementation: Run History now shows evidence coverage for active jobs, and Job Detail exposes standard theme, candidate tickers, and coverage before a report href exists.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` -> `1 passed in 0.59s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 5.93s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.12s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest preflight job metadata code; server PID is `82026`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async job smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-ae06fec41452`; queued detail preserved `canonical_theme=HBM`, candidate tickers including `MU`, `coverage_label=140 条证据`, `preflight_source=backend`, and completed detail retained the same preflight scope with `/analyses/hbm-6f259a8f14/index.zh.html`.
- Reusable lesson recorded: async analysis jobs need backend-backed preflight metadata at queue time so users can audit scope and candidates before report generation completes.

# Serenity Alpha Lab Job Cancel Detail Panel Phase

- [x] Record the job cancel and detail panel phase and product target.
- [x] Add failing UI and HTTP tests for job cancellation and detail panel hooks.
- [x] Implement cancel semantics for queued/running jobs without losing run history.
- [x] Add Run History job detail and cancel controls backed by job detail lookup.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where users can inspect and control background analysis jobs.
- UX target: Run History should expose job details, retry chain metadata, and a cancel action for queued/running jobs while preserving completed/failed report actions.
- Research boundary: job details and cancellation are workflow controls only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `openJobDetailPanel` / `cancelAnalyzeJob`, and `POST /api/analyze-jobs` treated `{job_id, cancel: true}` as an invalid normal submission.
- Implementation: added cancel semantics for queued/running jobs, `cancelled_at` metadata, cancelled status labeling, a compact Job Detail panel, Run History detail/cancel controls, and worker-side guards so cancelled jobs are not overwritten by late background completion.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_cancel_running_job -q` -> `2 passed in 0.60s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `28 passed in 5.94s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `162 passed in 6.10s`.
- Release verification: `make verify` -> `162 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest job cancel/detail panel code; server PID is `81576`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Job detail smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-d19d52ef9ac0`; `GET /api/analyze-jobs?jobId=job-d19d52ef9ac0` returned job detail; `GET /api/analyze-jobs?jobId=missing-job` returned HTTP 404.
- Reusable lesson recorded: cancellable background jobs need terminal-state guards so late worker completion cannot overwrite user cancellation.

# Serenity Alpha Lab Job Detail Retry Phase

- [x] Record the job detail and retry phase and product target.
- [x] Add failing UI and HTTP tests for job lookup and failed-job retry semantics.
- [x] Implement `GET /api/analyze-jobs?jobId=...` and retry metadata on job submission.
- [x] Preserve Run Center polling and existing `/analyze` compatibility.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where generated analysis jobs are inspectable and failed jobs can be retried cleanly.
- UX target: each run should expose a durable `job_id`, job detail lookup should return a single job record, and retry submissions should preserve the previous query/language while linking the new job to the failed source job.
- Research boundary: job lookup and retry state are workflow infrastructure only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `retryAnalyzeJob` / `retry_job_id`, and `GET /api/analyze-jobs?jobId=...` returned a run list instead of a single job.
- Implementation: added single-job lookup, 404 handling for missing jobs, retry submissions through `retry_job_id`, durable `retry_of_job_id` and `attempt` metadata, and a Run History retry button that submits failed/completed job retries through the async job API before falling back to legacy rerun behavior.
- Reliability fix: added a shared run-record lock and atomic `runs.json` replacement so background worker writes cannot race with job detail reads and produce transient 404s.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_lookup_and_retry_failed_job -q` -> `2 passed in 0.60s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `27 passed in 5.41s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `161 passed in 5.58s`.
- Release verification: `make verify` -> `161 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest job detail/retry code; server PID is `29454`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Job detail smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-da35e29ddbff`; `GET /api/analyze-jobs?jobId=job-da35e29ddbff` returned completed job detail with `/analyses/hbm-6f259a8f14/index.zh.html`; `GET /api/analyze-jobs?jobId=missing-job` returned HTTP 404.
- Reusable lesson recorded: single-job lookup and retry semantics need atomic run-state persistence once background workers update shared JSON state.

# Serenity Alpha Lab Async Analysis Job Queue Phase

- [x] Record the async analysis job queue phase and product target.
- [x] Add failing UI and HTTP tests for background job submission and polling.
- [x] Implement `/api/analyze-jobs` submission, durable job/run state, and polling.
- [x] Keep `/analyze` deep-link compatibility while moving the homepage launcher toward jobs.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where long-running analysis requests do not block the browser and can be polled from the Run Center.
- UX target: submit analysis as a background job, immediately return JSON job metadata, keep Run Center polling durable `/api/runs`, and preserve existing `/analyze` links for direct report navigation and retries.
- Research boundary: async job state is workflow infrastructure only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `/api/analyze-jobs` or `submitAnalyzeJob`, and the backend returned HTTP 404 for job submission.
- Implementation: added `/api/analyze-jobs` JSON submission, durable `job_id` run metadata, a background worker thread for analysis generation, `/api/runs` polling continuity, and frontend `submitAnalyzeJob` fallback to the legacy `/analyze` deep link if async submission fails.
- Compatibility: `/analyze` remains available for direct report navigation, retries, and non-JavaScript fallback while the homepage launcher now prefers background jobs.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_analyze_jobs_submit_runs_in_background -q` -> `2 passed in 0.60s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `26 passed in 4.88s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `160 passed in 5.05s`.
- Release verification: `make verify` -> `160 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest async job queue code; server PID is `61966`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Async smoke: `POST /api/analyze-jobs` returned HTTP 202 with `job-d849a1330c55`, `/api/runs` showed the job running immediately, then completed with `/analyses/hbm-6f259a8f14/index.zh.html` and `completed_at`.
- Reusable lesson recorded: background analysis jobs should be introduced behind a JSON submission API while preserving existing deep-link routes as compatibility and recovery paths.

# Serenity Alpha Lab Run Center Queue Phase

- [x] Record the run-center queue phase and product target.
- [x] Add failing UI and HTTP tests for queued analysis lifecycle metadata.
- [x] Implement queued lifecycle metadata across run records, polling, and bilingual UI.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where analysis launches feel reliable and recoverable.
- UX target: the Run Center should immediately show a queued state, then preserve queued/running/completed timing metadata in durable run history without requiring a full async worker yet.
- Research boundary: run lifecycle state is workflow metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose queued run copy and `/analyze` run records did not persist `queued_at` lifecycle metadata.
- Implementation: analysis launch now writes a queued run record before transitioning to running, preserves `queued_at` through running/completed/failed states, keeps `completed_at` empty for queued/running states, and shows bilingual queued status in the Run Center and run history.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_analysis_writes_running_record_before_completion -q` -> `2 passed in 0.60s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `25 passed in 4.35s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `159 passed in 4.56s`.
- Release verification: `make verify` -> `159 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest queued run lifecycle code; server PID is `12139`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Reusable lesson recorded: run lifecycle should preserve queue metadata as part of the same durable run record before introducing heavier async infrastructure.

# Serenity Alpha Lab Evidence Import Auto-Transition Phase

- [x] Record the evidence import auto-transition phase and product target.
- [x] Add failing HTTP tests for import-driven task status and audit transitions.
- [x] Implement import success status verification, audit capture, and rerun linkage.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where importing evidence automatically advances the evidence workflow.
- UX target: after a successful evidence import, the related task should become verified, the project evidence audit log should record the contribution, and the rerun path should remain visible.
- Research boundary: auto-transition records workflow and evidence-quality metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: the import E2E first failed because successful `/ingest-evidence` updated the regenerated page but did not write a verified task status or project evidence audit record to the server-backed stores.
- Implementation: successful evidence imports now infer the resolved gap, preserve the hidden task id, write the related task as `verified` to `task_statuses.json`, and write an `import-verified-task` contribution entry to `project_evidence_audits.json` with quality-before/after context.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `1 passed in 0.65s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `25 passed in 4.34s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `159 passed in 4.51s`.
- Release verification: `make verify` -> `159 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest evidence import auto-transition code; server PID is `29943`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI still exposes task-status and project-evidence-audit sync helpers; both status and audit APIs return expected payload shapes.
- Reusable lesson recorded: evidence import success should advance task state and audit history in the same server-backed workflow.

# Serenity Alpha Lab Server-Backed Evidence Task Status Phase

- [x] Record the server-backed evidence task status phase and product target.
- [x] Add failing UI and HTTP tests for durable evidence task status persistence.
- [x] Implement evidence task status API, JSON store, and bilingual UI sync.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where evidence task progress survives refreshes, browser changes, and future multi-user review.
- UX target: keep the existing compact task status controls while syncing `to_collect`, `collected`, and `verified` states to a server-backed local JSON store.
- Research boundary: persisted task status records capture workflow metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `syncTaskStatusesFromServer`, server write/clear helpers, `/api/task-statuses`, and the endpoint returned HTTP 404.
- Implementation: added `task_statuses.json` storage helpers, `/api/task-statuses` GET/POST/clear handling, optional project-id filtering, valid status enforcement for `to_collect`, `collected`, and `verified`, plus UI sync/write/clear helpers tied to existing task status controls.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_task_status_api_persists_statuses -q` -> `19 passed in 1.24s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `25 passed in 4.35s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `159 passed in 4.50s`.
- Release verification: `make verify` -> `159 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest server-backed evidence task status code; server PID is `88337`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/task-statuses`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes server-backed task status sync helpers and `/api/task-statuses`; the endpoint returns a `statuses` payload.
- Reusable lesson recorded: evidence task status controls should become server-backed once they drive audit logs and rerun workflow.

# Serenity Alpha Lab Server-Backed Project Evidence Audit Phase

- [x] Record the server-backed project evidence audit phase and product target.
- [x] Add failing UI and HTTP tests for durable project evidence audit persistence.
- [x] Implement project evidence audit API, JSON store, and bilingual UI sync.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where evidence verification and rerun audit trails survive browser changes.
- UX target: keep the compact project detail drawer audit log while syncing records to a server-backed local JSON store.
- Research boundary: persisted audit records capture workflow and quality-context metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `syncProjectEvidenceAuditLogFromServer`, server write/clear helpers, `/api/project-evidence-audits`, and the endpoint returned HTTP 404.
- Implementation: added `project_evidence_audits.json` storage helpers, `/api/project-evidence-audits` GET/POST/clear handling, optional project-id filtering, normalized audit entries, and UI sync/write/clear helpers that keep localStorage as fallback while persisting evidence verification and rerun audit entries.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_evidence_audit_api_persists_entries -q` -> `3 passed in 1.16s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `24 passed in 3.86s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `158 passed in 3.98s`.
- Release verification: `make verify` -> `158 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest server-backed project evidence audit code; server PID is `42669`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/project-evidence-audits`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes the server-backed project evidence audit sync helpers and `/api/project-evidence-audits`; the endpoint returns an `audits` payload.
- Reusable lesson recorded: project evidence audit logs should become server-backed once they are part of reusable project workflow.

# Serenity Alpha Lab Project Evidence Audit Log Phase

- [x] Record the project evidence audit log phase and product target.
- [x] Add failing UI and HTTP tests for project-level evidence contribution audit logs.
- [x] Implement project audit log UI, verified-task event capture, and quality contribution context.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where evidence work leaves a project-level audit trail.
- UX target: show a compact audit log in the project detail drawer so users can see verified tasks, rerun quality context, and contribution history without scanning raw events.
- Research boundary: the audit log records workflow and quality-context metadata only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Project evidence audit log` / `项目证据审计日志`, project evidence audit helper functions, or audit data attributes.
- Implementation: added a bilingual project evidence audit log to the project detail drawer, localStorage-backed bounded audit entries, verified-task audit capture, rerun audit capture, and quality-before/after delta context.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `23 passed in 3.32s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `157 passed in 3.54s`.
- Release verification: `make verify` -> `157 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project evidence audit log code; server PID is `99035`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes project evidence audit copy, audit helper functions, audit data attributes, and verified-task/rerun quality contribution context.
- Reusable lesson recorded: project-level audit logs should summarize evidence-task verification and rerun quality contribution history inside the same drawer as project review actions.

# Serenity Alpha Lab Evidence Verification Rerun Phase

- [x] Record the evidence verification rerun phase and product target.
- [x] Add failing UI and HTTP tests for verified-task rerun and quality delta linkage.
- [x] Implement verified evidence task rerun controls, context persistence, and quality delta display.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue toward a stable Serenity investment research product where evidence tasks naturally lead into rerun and quality comparison.
- UX target: when a user marks an evidence task verified, surface a compact rerun action and quality-delta status near the task instead of forcing the user to manually return to the launch form.
- Research boundary: this phase automates workflow context only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because generated dashboards did not expose `Evidence verification rerun loop` / `证据验证重跑闭环`, verified-task rerun helpers, rerun context attributes, or quality-delta attributes.
- Implementation: added a compact evidence verification rerun loop to each evidence task card, connected task status changes to rerun readiness, persisted verified-task rerun context, and generated project-aware `/analyze` rerun URLs with task id, ticker, and quality-before metadata.
- Empty-state hardening: smoke testing showed the homepage can have no pending evidence tasks; added a regression test and empty-state rerun loop hooks so the workflow model remains visible even before a task appears.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui.py::test_build_dashboard_empty_evidence_tasks_keep_rerun_loop_hooks -q` -> `3 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `23 passed in 3.29s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `157 passed in 3.43s`.
- Release verification: `make verify` -> `157 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest evidence verification rerun code; server PID is `30011`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes verified-task rerun helpers, verified rerun context attributes, quality delta attributes, and bilingual evidence verification rerun loop copy.
- Reusable lesson recorded: evidence-task flows should preserve rerun and quality-delta hooks in both populated and empty task states.

# Serenity Alpha Lab Project Review Closed Loop Phase

- [x] Record the project review closed loop phase and product target.
- [x] Add failing UI and HTTP tests for evidence-task routing and rerun context linkage.
- [x] Implement evidence-gap task focus, project-aware rerun URLs, and rerun quality context.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where review actions lead directly into evidence collection and rerun follow-up.
- UX target: connect the project detail drawer actions to the existing evidence-task queue, analysis rerun route, and quality snapshot workflow instead of leaving them as isolated buttons.
- Research boundary: the closed loop coordinates review workflow only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Evidence gap linked task` / `证据缺口关联任务`, evidence-task routing helpers, project-aware rerun context, or rerun quality attributes.
- Implementation: added project review closed-loop helpers that map evidence-gap actions to task cards, focus the linked evidence task, build project-aware rerun URLs, persist rerun context, and display quality-after-rerun state in the right-side drawer.
- Startup hardening: smoke testing exposed a preview-server startup failure when deleting a stale served pack directory raised `FileNotFoundError`; added a regression test and bounded retry in `_copy_pack_for_serving`.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.66s`.
- Startup regression check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_copy_pack_for_serving_recovers_from_stale_destination_files -q` -> `1 passed in 0.06s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `22 passed in 3.39s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `156 passed in 3.72s`.
- Release verification: `make verify` -> `156 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project review closed-loop code; server PID is `91761`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes evidence-task routing copy, rerun-context helpers, project evidence target attributes, project rerun context attributes, and quality-after-rerun attributes.
- Reusable lesson recorded: review actions should close the loop into visible evidence tasks and rerun context, and local preview startup must tolerate stale served artifact cleanup.

# Serenity Alpha Lab Project Review Action Panel Phase

- [x] Record the project review action panel phase and product target.
- [x] Add failing UI and HTTP tests for a compact actionable review panel in the project detail drawer.
- [x] Implement bilingual review actions for evidence closure, rerun, delivery marking, and report opening.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where project reviews guide the next action, not only record history.
- UX target: keep the right-side project drawer compact while adding a clear action panel that turns project status and evidence gaps into visible next steps.
- Research boundary: action buttons must route review workflow only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Project review action panel` / `项目复核操作面板`, action-panel DOM ids, action handlers, or action data attributes.
- Implementation: added a compact bilingual project review action panel inside the detail drawer with close-evidence-gap, rerun-analysis, mark-delivered, and open-report actions.
- Review behavior: action buttons now derive project context, log review actions to the existing event timeline/API, update delivered status through the project library path, and keep report/rerun routing inside the existing local workflow.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `21 passed in 3.28s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `155 passed in 3.43s`.
- Release verification: `make verify` -> `155 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project review action panel code; server PID is `24903`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated English/Chinese UI exposes action-panel copy, action-panel helpers, project action data attributes, and `/api/project-events` accepted a review-action event.
- Reusable lesson recorded: project detail drawers should pair event history with explicit next-action controls.

# Serenity Alpha Lab Server-Backed Project Review Events Phase

- [x] Record the server-backed project review events phase and product target.
- [x] Add failing UI and HTTP tests for durable project review event persistence.
- [x] Implement a project review event API, JSON store, and bilingual UI sync.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where review timelines survive browser changes and can support future multi-user review.
- UX target: preserve the compact project detail drawer timeline while syncing review events to a server-backed local JSON store.
- Research boundary: persisted review events capture workflow metadata only; they must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Server-backed review event log` / `服务端复核事件日志`, `/api/project-events`, server sync helpers, or a durable review-event API.
- Implementation: added `project_review_events.json` storage helpers, `/api/project-events` GET/POST/clear handling, optional project-id filtering, input validation, and UI sync helpers that keep the local timeline as fallback while writing events to the server.
- Review behavior: opening project details, changing project status, and copying comparison briefs now keep the drawer timeline compact while persisting review events outside browser-only state.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_project_review_event_api_persists_events -q` -> `3 passed in 1.16s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `21 passed in 3.28s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `155 passed in 3.44s`.
- Release verification: `make verify` -> `155 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest server-backed review event code; server PID is `71264`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/project-events`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: `/api/project-events` accepted a POSTed review event, returned it through filtered GET by project id, and the regenerated English/Chinese UI exposed server-backed review event text and sync helpers.
- Reusable lesson recorded: review timelines should graduate to a server-backed event log once they become part of a reusable project workflow.

# Serenity Alpha Lab Project Review Timeline Phase

- [x] Record the project review timeline phase and product target.
- [x] Add failing UI and HTTP tests for a compact review-event history inside the project detail drawer.
- [x] Implement bilingual local review timeline events for detail opens, status changes, and copied comparison briefs.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where saved project reviews leave an auditable trail.
- UX target: keep the project library compact while adding a small project review timeline inside the existing right-side detail drawer.
- Research boundary: the timeline records project-review workflow events only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Project review timeline` / `项目复核时间线`, timeline DOM ids, localStorage helpers, or review-event data attributes.
- Implementation: added a bilingual project review timeline inside the project detail drawer, localStorage-backed review events, bounded event history, event rendering helpers, and workflow hooks for detail opens, status changes, and copied comparison briefs.
- Review behavior: the drawer now records `Detail opened`, `Status changed`, and `Comparison brief copied` events with project id/type attributes while keeping the main project library compact.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.75s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.91s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project review timeline code; server PID is `31471`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Project review timeline`, `Review event history`, timeline helper functions, and review-event data attributes; regenerated HBM Chinese analysis exposes `项目复核时间线`, `复核事件历史`, `暂无复核事件。`, `状态已更新`, `已打开详情`, and `已复制对比简报`.
- Reusable lesson recorded: saved-project review flows should keep a compact event trail inside the same detail drawer.

# Serenity Alpha Lab Project Detail Drawer Phase

- [x] Record the project detail drawer phase and product target.
- [x] Add failing UI and HTTP tests for reviewing saved projects in a right-side detail drawer.
- [x] Implement a compact bilingual project detail drawer with quality, gap, status, next action, and report entry.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where users can inspect saved projects without leaving the current dashboard.
- UX target: add a right-side project detail drawer so saved project cards can open a focused review panel instead of forcing immediate page navigation.
- Research boundary: the drawer reviews project metadata, quality, evidence gaps, status, and report links only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Project detail drawer` / `项目详情抽屉`, review-project controls, detail drawer ids, or detail rendering helpers.
- Implementation: added a bilingual right-side project detail drawer, per-project `Review project` / `复核项目` action, detail rendering helpers, project detail metadata attributes, and a report entry from the drawer.
- Review behavior: the drawer now shows project quality, evidence gap, status, next review action, saved metadata, and report access without leaving the current page.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.75s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.91s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project detail drawer code; server PID is `93440`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Project detail drawer`, `Review project`, `Project review panel`, drawer helper functions, and project detail data attributes; regenerated HBM Chinese analysis exposes `项目详情抽屉`, `复核项目`, `项目复核面板`, and detail drawer hooks.
- Reusable lesson recorded: saved-project lists should open detail drawers for focused review before forcing navigation away from the dashboard.

# Serenity Alpha Lab Project Library Management Phase

- [x] Record the project library management phase and product target.
- [x] Add failing UI and HTTP tests for searching, sorting, and tagging saved projects.
- [x] Implement compact bilingual project search, sort, and tag controls.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where saved projects remain manageable as the library grows.
- UX target: keep the project library compact while adding search, sort, and tag controls so users can quickly find projects by topic, candidate, status, quality, or evidence gap.
- Research boundary: library management only organizes saved research projects and must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose saved-project search, sort, tag filters, project-tag hooks, or filtered-record logic.
- Implementation: added bilingual project-library search, sort, and tag filters; rendered searchable project metadata; added `projectLibraryFilteredRecords`, `projectTagForRecord`, and `sortResearchProjects`; and preserved status filters, server sync, comparison matrix, and copyable comparison brief.
- Management behavior: users can search by topic/candidate/status/gap, sort by most recent, highest quality, or topic, and filter tags for needs-evidence, high-quality, and delivered projects.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.63s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.74s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.91s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project library management code; server PID is `44537`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Search saved projects`, `Sort saved projects`, `Project tags`, tag controls, and project search/tag data attributes; regenerated HBM Chinese analysis exposes `搜索已保存项目`, `排序已保存项目`, `项目标签`, and `全部项目标签`.
- Reusable lesson recorded: saved-project libraries need search, sort, and tag controls before accumulating many analyses.

# Serenity Alpha Lab Comparison Handoff Brief Phase

- [x] Record the comparison handoff brief phase and product target.
- [x] Add failing UI and HTTP tests for copying selected-project comparison briefs.
- [x] Implement a compact bilingual comparison handoff brief inside the project library.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where users can hand off a multi-project comparison to another reviewer.
- UX target: keep the historical comparison matrix compact, but add one explicit copy action that packages selected saved projects into a research-only comparison brief.
- Research boundary: the copied brief must summarize topics, top candidates, quality, gaps, status, and report links only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose `Copy comparison brief` / `复制对比简报`, copied-state text, a research-only comparison brief label, or comparison-brief copy helpers.
- Implementation: added a bilingual `Copy comparison brief` action inside the historical comparison matrix, plus `buildProjectComparisonBrief` and `copyProjectComparisonBrief` helpers that package selected project metadata into a copyable research-only handoff.
- Brief contents: selected projects now copy topic, top candidate, quality, evidence gap, project status, and report href, with an explicit no recommendation / no target price / no position-sizing boundary.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.63s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.74s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.94s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest comparison handoff brief code; server PID is `21371`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Copy comparison brief`, `Comparison brief copied`, `Research-only comparison brief`, `buildProjectComparisonBrief`, `copyProjectComparisonBrief`, and `data-project-comparison-brief`; regenerated HBM Chinese analysis exposes `复制对比简报`, `已复制对比简报`, and `仅供研究的对比简报`.
- Reusable lesson recorded: comparison matrices should include a copyable handoff artifact before users are expected to share multi-analysis reviews.

# Serenity Alpha Lab Historical Analysis Comparison Matrix Phase

- [x] Record the historical comparison matrix phase and product target.
- [x] Add failing UI and HTTP tests for selecting saved projects and comparing historical analyses.
- [x] Implement a compact bilingual historical comparison matrix inside the project library.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where users can compare multiple saved industry, theme, sector, or ticker analyses before reopening reports.
- UX target: keep the dashboard less crowded by adding a compact, selectable comparison matrix inside the existing research project library instead of creating another full page.
- Research boundary: the matrix compares research metadata, quality, evidence gaps, statuses, and report links only; it must not add buy/sell/hold calls, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because generated dashboards did not expose `Historical comparison matrix` / `历史对比矩阵`, selectable project comparison controls, matrix table ids, or comparison rendering helpers.
- Implementation: added bilingual project comparison selection, persisted selected project ids in localStorage, rendered a compact comparison table inside the existing project library, and preserved status filtering plus server-backed project sync.
- Matrix fields: selected projects now compare topic, top candidate, quality score/status, evidence gap, project status, and report entry without adding investment recommendations or trade guidance.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.63s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.74s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.96s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest historical comparison matrix code; server PID is `63045`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Historical comparison matrix`, `Select for comparison`, `Compare selected projects`, `renderProjectComparisonMatrix`, and project comparison data attributes; regenerated HBM Chinese analysis exposes `历史对比矩阵`, `选择对比`, and `对比已选项目`.
- Reusable lesson recorded: persisted project libraries need selectable comparison matrices once users can accumulate multiple analyses.

# Serenity Alpha Lab Project Library Comparison Phase

- [x] Record the project library comparison phase and product target.
- [x] Add failing UI and HTTP tests for project status filters and comparison summary.
- [x] Implement bilingual project status filtering and comparison metrics.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where saved projects can be triaged and compared without reopening every report.
- UX target: keep the project library compact, but add status filtering and a comparison summary so users can compare quality, delivered work, and evidence backlog across saved analyses.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose project status filters, comparison summary copy, stable filter/summary DOM ids, filter logic, or project quality-score data attributes.
- Implementation: added bilingual project status filtering, compact comparison summary metrics, filtered project cards, quality-score parsing, and stable hooks for total projects, average quality score, evidence backlog, and delivered project count.
- UI behavior: project-library rendering now refreshes comparison metrics whenever server/local projects load, projects are saved, projects are cleared, or project statuses change; the status filter hides non-matching cards without leaving the main page.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.65s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.73s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.92s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest project comparison code; server PID is `32460`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Filter projects by status`, `Project comparison summary`, `renderProjectComparisonSummary`, and `data-project-quality-score`; regenerated HBM Chinese analysis exposes `按状态筛选项目`, `项目对比摘要`, `平均质量评分`, and `filterResearchProjects`.
- Reusable lesson recorded: saved project libraries need in-place filters and aggregate comparison metrics before users can reliably manage many analyses.

# Serenity Alpha Lab Persistent Project Library Phase

- [x] Record the persistent project library phase and product target.
- [x] Add failing HTTP/API and UI tests for server-backed project persistence.
- [x] Implement project storage helpers and `/api/projects` read/write/clear endpoints.
- [x] Sync the bilingual project library UI with the server while preserving local fallback.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where saved analysis projects survive browser changes and can become multi-user ready.
- UX target: keep the compact project library UI, but back it with a server-side project store so saved projects become durable product objects instead of only browser-local state.
- TDD red result: target UI and HTTP tests first failed because dashboards did not expose server project synchronization helpers, `/api/projects`, or a server-backed project-library message, and the HTTP server returned 404 for `/api/projects`.
- Implementation: added `projects.json` storage helpers, `/api/projects` GET/POST endpoints, save/update deduplication by project id, clear support, and normalized project records with query, href, status, quality snapshot, top ticker, gap, and saved timestamp.
- UI sync: project-library initialization now renders local fallback immediately, then syncs from `/api/projects`; save/status updates POST the latest project to the server, and clear removes both local and server-backed projects.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_project_library_api_persists_projects -q` -> `2 passed in 0.58s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `20 passed in 2.76s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `154 passed in 2.91s`.
- Release verification: `make verify` -> `154 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest persistent project library code; server PID is `86344`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/projects`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: English UI exposes `Server-backed project library` and `/api/projects`; regenerated HBM Chinese analysis exposes `研究项目库`, `保存为项目`, and `syncResearchProjectLibraryFromServer`.
- Reusable lesson recorded: project libraries should have a durable server-backed store before adding account features.

# Serenity Alpha Lab Research Project Library Phase

- [x] Record the research project library phase and product target.
- [x] Add failing UI and HTTP tests for local project saving and status tracking.
- [x] Implement bilingual research project library with local persistence.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research product where users can save generated analyses as trackable research projects.
- UX target: add a compact local-first project library with status tracking so the dashboard stays less crowded while users can resume and triage prior industry, theme, sector, or ticker analyses.
- TDD red result: target UI and HTTP tests first failed because generated dashboards did not expose `Research Project Library` / `研究项目库`, save-project controls, project statuses, local project storage helpers, or stable `data-project-*` attributes.
- Implementation: dashboards now render a compact bilingual research project library after the saved workspace, with `Save as project`, clear-projects, project count, localStorage persistence, status editing, quality snapshot, top ticker, gap metadata, and open-project navigation.
- Status model: generated projects default to `Pending evidence` / `待补证据` for `needs-evidence`, `Reviewable` / `可复核` for `publishable`, `Needs rerun` / `需重跑` for `not-publishable`, and users can manually mark `Delivered` / `已交付`.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.63s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.23s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.38s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest research project library code; server PID is `22895`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: regenerated HBM analysis exposes `研究项目库`, `保存为项目`, and `待补证据`; English home exposes `Research Project Library` and `Save as project`.
- Reusable lesson recorded: reusable research products should save analysis pages as project objects with status, quality, ticker, and gap metadata.

# Serenity Alpha Lab Research Action Workbench Phase

- [x] Record the research action workbench phase and product target.
- [x] Add failing UI and HTTP tests for a compact next-step research action workbench.
- [x] Implement bilingual research action workbench with gap, report, queue, and copy-prompt actions.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity investment research system where users can act on generated analysis instead of only reading it.
- UX target: create one compact action workbench that routes users to evidence tasks, deliverable report, acquisition queue, and reusable search prompts without crowding the main page.
- TDD red result: target UI and HTTP tests first failed because generated dashboards did not expose `Research Action Workbench` / `研究动作工作台`, action queue routing, quality-gap metadata, or copyable next-research prompts.
- Implementation: dashboards now render a compact research action workbench after the analysis briefing, with links to evidence tasks, deliverable report, acquisition queue, top candidate report, and a copyable next-research prompt derived from the top candidate and scorecard gaps.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.20s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.36s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest research-action-workbench code; server PID is `39633`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Smoke detail: Chinese and English homepages expose the new research action workbench; regenerated HBM analysis exposes `研究动作工作台` and `复制下一步研究提示`.
- Reusable lesson recorded: generated analysis pages should turn quality gaps into one-click research actions.

# Serenity Alpha Lab Report Reader Navigation Phase

- [x] Record the report reader navigation phase and product target.
- [x] Add failing UI and HTTP tests for reader outline, section jump controls, and report highlights.
- [x] Implement bilingual reader outline and compact highlights inside the existing right-side report drawer.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable user-facing Serenity investment research system where generated reports are easier to inspect and review.
- UX target: improve the right-side report reader with progressive-disclosure navigation and a compact highlights panel, instead of pushing more information into the main dashboard.
- TDD red result: target UI and HTTP tests first failed because the report drawer did not expose `Reader outline` / `报告目录`, `Report highlights` / `报告重点`, section jump controls, or reader navigation helpers.
- Implementation: the right-side report drawer now builds a Markdown heading outline, exposes section jump buttons, extracts compact report highlights from bullets and bold metadata, and resets the reader navigation state when closing or loading a new report.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_report_drawer_renders_markdown_safely tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed in 0.84s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.55s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 3.23s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: cleared the stale `127.0.0.1:8767` listener and restarted the preview service with latest report-reader navigation code; server PID is `83351`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` returned HTTP 200.
- Smoke detail: Chinese and English homepages expose the reader outline; regenerated HBM analysis exposes `报告目录`, `报告重点`, and `交付质量摘要`; manifest remains valid JSON with `quality.score` and `quality.status`.
- Reusable lesson recorded: report readers need in-drawer navigation for long generated research artifacts.

# Serenity Alpha Lab Delivery Quality Summary Phase

- [x] Record the delivery quality summary phase and product target.
- [x] Add failing UI and HTTP tests for compact delivery-package quality status, score, top candidate, gaps, and research-only boundary.
- [x] Implement bilingual delivery quality summary inside the existing delivery package panel.
- [x] Verify targeted tests, UI/E2E tests, full suite, and release checks.
- [x] Rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue the next product phase toward a stable Serenity-based investment research system that can be handed to other users.
- UX target: keep the page less crowded by placing a compact quality summary inside the existing report delivery package instead of adding another large section.
- TDD red result: target UI and HTTP tests first failed because the delivery package did not expose `Delivery quality summary` / `交付质量摘要`, `Research-only package` / `仅供研究`, or delivery-quality data attributes.
- Implementation: the delivery package now reuses the existing report-quality snapshot and renders publish status, quality score, top candidate, remaining gaps, and a research-only package badge in a compact summary strip.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.74s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.19s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.35s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local server restart: restarted `127.0.0.1:8767` with latest delivery-quality-summary code; server PID is `42722`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200.
- Reusable lesson recorded: delivery packages should summarize publish quality at the handoff point without adding another large dashboard section.

# Serenity Alpha Lab Deliverable Report Phase

- [x] Record the deliverable report phase and product target.
- [x] Add failing UI and HTTP tests for an export-ready report panel, print action, and generated deliverable Markdown artifact.
- [x] Implement bilingual deliverable report controls and per-analysis `deliverable-research-report.md` generation.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable user-facing Serenity-based investment research product whose generated analysis can be shared or reviewed as a concise report.
- Added regression coverage for a bilingual `Deliverable Research Report` / `可交付研究报告` panel, a print/save-PDF action, report-workbench filtering, and generated `deliverable-research-report.md` assets.
- The UI now shows an export-ready report panel after the saved workspace with `Open deliverable report` / `打开交付版报告` and `Print / Save PDF` controls.
- Every dashboard build now writes `reports/deliverable-research-report.md`, summarizing research topic, top candidate, candidate ranking, quality gate, evidence gaps, next actions, and research-only boundaries in Chinese.
- The report workbench now treats the deliverable report as its own `deliverable` report type while keeping operational reports separate.
- The implementation remains research-only: no buy/sell/hold recommendation, target price, or position sizing was added.
- TDD red result: target UI and HTTP tests first failed because `Deliverable Research Report`, `可交付研究报告`, `printDeliverableReport`, `data-report-type="deliverable"`, and the generated Markdown artifact were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, and rebuilt bilingual UI.
- Local server restart: restarted `127.0.0.1:8767` with latest deliverable-report code; server PID is `73776`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md`, and `/api/resolve-topic?query=存储芯片&language=zh` returned HTTP 200 and included the expected deliverable report or resolver content.

# Serenity Alpha Lab Saved Research Workspace Phase

- [x] Record the saved research workspace phase and product target.
- [x] Add failing UI and HTTP tests for saved reports, candidate marks, saved sort preference, and quality-gate snapshots.
- [x] Implement bilingual saved research workspace controls backed by local browser persistence.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable user-facing Serenity-based investment research product where users can resume analysis work across generated pages.
- Added regression coverage for a bilingual `Saved Research Workspace` / `研究工作区` on static dashboards and Chinese HTTP-generated analysis pages.
- The generated page now lets users save current report links, candidate marks, the active decision-sort preference, and the report-quality gate snapshot into browser `localStorage`.
- The workspace renders saved reports, candidate marks, saved sort preference, and quality-gate snapshot in a compact panel after the report-quality gate.
- Sort preference stays synchronized after the workspace is saved, so changing the Decision Workbench sort dimension updates the saved workspace state.
- The implementation remains local-first and research-only: no account system, backend user state, buy/sell/hold wording, target prices, or position sizing was added.
- TDD red result: target UI and HTTP tests first failed because `Saved Research Workspace`, `研究工作区`, `saveWorkspaceState`, `workspaceStorageKey`, `data-workspace-report`, and related bilingual copy were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, and rebuilt bilingual UI.
- Local server restart: restarted `127.0.0.1:8767` with latest saved-workspace code; server PID is `97687`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/api/resolve-topic?query=存储芯片&language=zh` returned HTTP 200 and included the expected saved-workspace or resolver content.

# Serenity Alpha Lab Report Quality Gate Phase

- [x] Record the report-quality gate phase and product target.
- [x] Add failing UI and HTTP tests for publish status, quality score, and checklist gaps.
- [x] Implement bilingual report quality gate panel backed by existing score, confidence, evidence, primary, risk, and gap data.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable Serenity-based investment research product that can be trusted by other users.
- Added regression coverage for a bilingual `Report Quality Gate` / `报告质量门禁` on both static dashboard rendering and Chinese HTTP-generated analysis pages.
- The generated page now displays publish status, quality score, evidence depth, primary source depth, risk coverage, quality gaps, and a checklist before users proceed deeper into reports.
- The quality gate reuses existing scorecard preview data, memo rows, evidence/primary/risk counts, and gaps; it does not introduce separate opaque scoring inputs.
- Publish states remain research-product states only: `Publishable`, `Needs evidence`, and `Not publishable`; no buy/sell/hold, target price, or position-sizing language was added.
- TDD red result: target UI and HTTP tests first failed because `Report Quality Gate`, `Publish status`, `Quality score`, `Quality checklist`, `id="report-quality-gate"`, and Chinese equivalents were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, and rebuilt bilingual UI.
- Local server restart: restarted `127.0.0.1:8767` with latest report-quality gate code; server PID is `2123`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze` for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, plus `/api/resolve-topic?query=存储芯片&language=zh`, returned HTTP 200 and included the expected quality-gate content.

# Serenity Alpha Lab Interactive Decision Ranking Phase

- [x] Record the interactive decision-ranking phase and product target.
- [x] Add failing UI and HTTP tests for sort controls, candidate ranking cards, and sort explanations.
- [x] Implement bilingual interactive candidate ranking controls inside the decision workbench.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable Serenity-based investment research product where users can interactively compare candidates after generating an industry, sector, theme, or ticker report.
- Added regression coverage for bilingual sort controls, candidate ranking cards, sort explanations, and HTTP-generated Chinese analysis pages.
- The decision workbench now includes an interactive ranking selector for Serenity score, evidence coverage, primary source coverage, and risk coverage.
- Candidate ranking cards are rendered with sortable data attributes, rank numbers, score labels, rating, confidence, and evidence/primary/risk counts.
- The client-side `updateDecisionRanking()` function reorders candidates in place and updates the visible sort explanation without requiring a page reload.
- The panel keeps the research-only boundary intact and only changes the triage order/explanation, not investment advice or trade instructions.
- TDD red result: target UI and HTTP tests first failed because `Sort candidates by`, `Interactive candidate ranking`, `Sort explanation`, `data-decision-candidate`, `initializeDecisionRanking`, `updateDecisionRanking`, and Chinese equivalents were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, and rebuilt bilingual UI.
- Local server restart: restarted `127.0.0.1:8767` with latest interactive decision-ranking code; server PID is `45468`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze` for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, plus `/api/resolve-topic?query=存储芯片&language=zh`, returned HTTP 200 and included the expected interactive ranking content.

# Serenity Alpha Lab Decision Workbench Phase

- [x] Record the decision-workbench phase and product target.
- [x] Add failing UI and HTTP tests for ranking rationale, drivers, counter-thesis risks, and runner-up explanations.
- [x] Implement bilingual decision workbench panel after the analysis briefing.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab toward a stable Serenity-based investment research product where users can input an industry, sector, theme, or ticker and get a structured research report.
- Added regression coverage for a bilingual `Decision Workbench` / `决策工作台` on both static dashboard rendering and the Chinese HTTP `/analyze` flow.
- The generated page now shows a decision-triage panel immediately after `Analysis Briefing`, with ranking rationale, key drivers, counter-thesis risks, and runner-up explanation.
- The panel reuses existing scorecard preview data, memo row evidence counts, risk/invalidations, and source-backed financial metrics instead of introducing a separate hardcoded decision model.
- The UI keeps research-only boundaries explicit through `Research triage only` / `仅用于研究分诊`, avoiding direct buy/sell/hold language, target prices, or position sizing.
- TDD red result: target UI and HTTP tests first failed because `Decision Workbench`, `Ranking rationale`, `Key drivers`, `Counter-thesis risks`, `Why not other candidates`, and Chinese equivalents were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, and rebuilt bilingual UI.
- Local server restart: restarted `127.0.0.1:8767` with latest decision-workbench code; server PID is `81373`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze` for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, plus `/api/resolve-topic?query=存储芯片&language=zh`, returned HTTP 200 and included the expected decision-workbench content.

# Serenity Alpha Lab Analysis Briefing Phase

- [x] Record the analysis-briefing phase and product target.
- [x] Add failing UI and HTTP tests for report summary and next-action guidance.
- [x] Implement bilingual analysis briefing panel with top candidate, coverage state, key gaps, and next actions.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable Serenity-based investment research product where users can generate a report and immediately understand what to read, what matters, and what to do next.
- Added regression coverage for a bilingual `Analysis Briefing` / `分析简报` panel on both home and generated analysis pages.
- The report page now surfaces top candidate, coverage state, primary evidence gap status, and next actions before the long memo sections.
- Added direct actions to open the top candidate report in the reader and jump to evidence tasks, keeping long reports easier to navigate.
- The briefing panel reuses existing memo rows, scorecard previews, operational evidence-task reports, and localized copy instead of introducing a separate summary data model.
- TDD red result: target UI and HTTP tests first failed because `Analysis Briefing`, `Top candidate`, `Coverage state`, `Primary gap`, `Next actions`, and Chinese equivalents were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and restarted `127.0.0.1:8767`.
- Local smoke: `/index.zh.html`, `/index.html`, and `/analyze` for `存储芯片`, `HBM`, `半导体设备`, and `AAOI` returned HTTP 200 with `分析简报`, `首选候选`, `下一步动作`, and `打开首选报告`; server PID is `8275`.

# Serenity Alpha Lab Backend Input Resolver Phase

- [x] Record the backend input-resolver phase and product target.
- [x] Add failing UI and HTTP tests for backend-backed input parsing preview and confirmation.
- [x] Implement localized `/api/resolve-topic` preview with intent, canonical theme, candidates, evidence coverage, and expected outputs.
- [x] Wire the launcher preview to the backend resolver with a safe client-side fallback.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable Serenity-based investment research product where users can input an industry, sector, theme, or ticker and get a structured research report.
- Added regression coverage for backend-backed input preview copy, `/api/resolve-topic`, localized intent labels, canonical theme resolution, candidate tickers, evidence coverage, and CLI `serve-ui` resolver wiring.
- The launcher preview now calls `/api/resolve-topic` first, then falls back to the local heuristic preview only if the backend preview is unavailable.
- `/api/resolve-topic` now reuses the existing `topic_resolver`, maintained stock universe, local evidence files, and localized UI copy to return intent, canonical theme, aliases, candidate tickers, coverage counts, expected outputs, and backend source metadata.
- `serve-ui` now wires the resolver callback using the same analysis data, stock universe, manual intake file, and ticker configuration used by actual analysis generation.
- TDD red result: target UI and HTTP tests first failed because `fetchAnalysisInputPreview`, backend resolver copy, and `/api/resolve-topic` were missing; the API then returned empty candidates until the HTTP server was wired to the real resolver data source.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed`.
- CLI resolver wiring verification: `PYTHONPATH=src python3 -m pytest tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and restarted `127.0.0.1:8767` with backend resolver support.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, and `/analyze` for `存储芯片`, `HBM`, `半导体设备`, and `AAOI` returned HTTP 200; resolver returned backend candidates including `MU`, `SKHYNIX`, `SAMSUNG`, and `SNDK`.

# Serenity Alpha Lab Report Workbench Phase

- [x] Record the report-workbench phase and product target.
- [x] Add failing UI and HTTP tests for report-workbench filters, drawer summaries, and report actions.
- [x] Implement localized report-workbench controls for recent reports and operational reports.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for a localized Report Workbench, report-type filtering, generated-analysis report actions, operational report actions, and stable evidence-task empty states.
- The homepage and generated analysis pages now include a bilingual `Report Workbench` / `报告工作台` with report-type filtering for generated analyses and operational reports.
- Recent generated reports now have both `Open in reader` / `在阅读器打开` and `Open full page` / `打开完整页面` actions, so users can read reports in the right-side drawer without losing context.
- HTML generated analysis pages can now be previewed in the right-side drawer via an iframe, while Markdown reports continue using the safe Markdown renderer.
- Empty report history now renders a filterable generated-analysis empty-state card, keeping the Report Workbench understandable before any reports are generated.
- Analysis pages now keep the `Evidence Tasks` / `证据任务` section visible even when the acquisition queue has no pending tasks, with an empty state and acquisition-queue action when available.
- TDD red result: report-workbench tests first failed because the homepage lacked `Report Workbench`, type filters, generated-analysis drawer actions, and report-workbench data attributes; the follow-up empty-state test failed because `证据任务` disappeared when the acquisition queue was empty.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_keeps_evidence_tasks_empty_state_visible tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `4 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: restarted `127.0.0.1:8767` with latest report-workbench code and PID `3873`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, and `/api/runs` returned HTTP 200; homepage and HBM analysis include `报告工作台`, `在阅读器打开`, `打开完整页面`, and `证据任务`.

# Serenity Alpha Lab Run Center Polling Phase

- [x] Record the run-center polling phase and product target.
- [x] Add failing UI tests for polling controls, auto-refresh, and completion actions.
- [x] Implement localized Run Center polling from `/api/runs`.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for localized Run Center polling controls, auto-refresh state, terminal completion copy, and latest-report actions.
- The homepage Run Center now starts polling `/api/runs` when users launch an analysis, shows localized in-progress refresh copy, and stops polling on completed or failed terminal states.
- Completed runs now surface an `Open latest report` / `打开最新报告` action backed by the latest backend `href`, so users can open the generated report without digging through history.
- The run history panel now carries explicit `data-run-polling="idle"` state and keeps rendered history synchronized with the backend during polling.
- TDD red result: new polling assertions first failed because `startRunPolling`, `stopRunPolling`, `scheduleRunPolling`, polling state attributes, polling copy, and latest-report actions were missing.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `18 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `152 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: restarted `127.0.0.1:8767` with latest polling-aware Run Center code and PID `92653`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, and `/api/runs` returned HTTP 200; `/api/runs` reported latest `HBM` Chinese analysis as `completed` with `started_at`, `completed_at`, and `/analyses/hbm-6f259a8f14/index.zh.html`.

# Serenity Alpha Lab Run Lifecycle Recovery Phase

- [x] Record the run-lifecycle recovery phase and product target.
- [x] Add failing tests for `running` run records and failed-analysis retry pages.
- [x] Implement running-status persistence before analysis work starts.
- [x] Implement localized failure recovery page with retry action.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue making Serenity Alpha Lab feel like a stable product for stock, industry, theme, and ticker investment research workflows.
- Added regression coverage for lifecycle-aware run records and localized failed-analysis recovery pages.
- `/analyze` now writes a `running` record before calling the analysis builder, then updates the same run to `completed` or `failed` while preserving `started_at`.
- Completed runs now include both `started_at` and `completed_at`, giving the Run Center enough state for future progress timing and polling UX.
- Failed analysis runs now return a localized HTML recovery page instead of the default server error page, with visible retry and home actions.
- TDD red result: new tests first failed because `runs.json` did not exist during analysis execution and failed `/analyze` responses used the default 500 HTML.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui_http_e2e.py::test_http_e2e_analysis_writes_running_record_before_completion tests/test_ui_http_e2e.py::test_http_e2e_failed_analysis_page_has_retry_action -q` -> `2 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `18 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `152 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: restarted `127.0.0.1:8767` with the latest lifecycle-aware run-record code.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, and `/api/runs` returned HTTP 200; `/api/runs` reported latest `HBM` Chinese analysis as `completed` with both `started_at` and `completed_at`.

# Serenity Alpha Lab Run History Panel Phase

- [x] Record the run-history panel phase and product target.
- [x] Add failing UI and HTTP tests for run history, open-report actions, retry actions, and failure diagnostics.
- [x] Implement localized Run Center history panel populated from `/api/runs`.
- [x] Verify targeted tests, full suite, release checks, rebuild artifacts, restart local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue moving Serenity Alpha Lab toward a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for a bilingual Run Center history panel with empty state, recent run rendering, open-report controls, rerun controls, and failed-run diagnostics.
- The homepage Run Center now includes `Run History` / `运行历史`, populated from `/api/runs` through `renderRunHistory()`.
- Each rendered run shows query, status, language, completion time, optional failure details, an `Open report` / `打开报告` action when a report href exists, and a `Rerun` / `重新生成` action.
- The run history panel escapes server-provided values before rendering, keeps failed runs visually distinct, and disables report opening when no href exists.
- TDD red result: new assertions first failed because the Run Center only displayed the latest status and had no history list, open-report action, rerun action, or failure detail surface.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `16 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `150 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: restarted `127.0.0.1:8767` with the latest Run Center history panel code.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, and `/api/runs` returned HTTP 200; `/api/runs` reported latest `HBM` Chinese analysis as `completed` with a valid generated report href.

# Serenity Alpha Lab Backend Run Records Phase

- [x] Record the backend run-record phase and product target.
- [x] Add failing HTTP/UI tests for durable run records, status API, and homepage restore.
- [x] Implement server-side run record persistence for `/analyze` success and failure paths.
- [x] Wire the Run Center UI to fetch backend run history when served locally.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue moving Serenity Alpha Lab from a local research demo toward a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for durable `/analyze` run records, a local `/api/runs` status API, success persistence, failure persistence, and homepage Run Center server sync.
- The local preview server now writes `output/ui/runs.json` for completed and failed analysis runs, including query, language, status, href, error, and `completed_at`.
- The new `/api/runs` endpoint returns recent run history as JSON, allowing the Run Center to restore the latest server-known run instead of depending only on browser `localStorage`.
- The Run Center client now calls `syncRunCenterFromServer()`, maps `completed` records into the completed UI state, and shows failed run state when the backend records an analysis error.
- TDD red result: new assertions first failed because the homepage lacked `syncRunCenterFromServer`, `/api/runs` returned 404, and failed analyses were not persisted anywhere.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets tests/test_ui_http_e2e.py::test_http_e2e_analysis_failure_is_persisted_in_run_api -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `16 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `150 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: restarted `127.0.0.1:8767` with the latest backend run-record code and wrote PID/log files under `output/`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, and `/api/runs` returned HTTP 200; `/api/runs` reported latest `HBM` Chinese analysis as `completed` with a valid generated report href.

# Serenity Alpha Lab Run Center Phase

- [x] Record the run-center phase and workflow target.
- [x] Add failing UI and HTTP tests for analysis run status, steps, retry, and local restore.
- [x] Implement localized run center status UI and client-side state handling.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable, user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for a bilingual homepage `Run Center` / `运行中心` that makes analysis execution status, steps, retry, and restore behavior visible.
- The homepage now shows the current run, localized waiting/running/completed status copy, and four explicit analysis steps: resolve universe, build memo pack, publish dashboard, and open report.
- Added client-side `initializeRunCenter()`, `updateRunCenter()`, `runCenterStorageKey()`, and `retryLastRun()` so the last run is saved in `localStorage`, restored on reload, and rerunnable from the existing launcher.
- Submit and example-launch flows now immediately update the run center before navigation, giving users feedback that analysis generation has started.
- TDD red result: new assertions first failed because the homepage had the workbench and launcher but no run-center UI, run steps, retry action, or restore functions.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `15 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `149 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, and refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Local server restart: stopped old PID `70148`, started PID `32387` on `127.0.0.1:8767`, and wrote logs to `output/ui-server.log`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, HBM acquisition queue, and HBM coverage matrix all returned HTTP 200 with expected Run Center and Chinese report snippets.

# Serenity Alpha Lab Product Workbench Phase

- [x] Record the product workbench phase and workflow target.
- [x] Add failing UI and HTTP tests for homepage workflow guidance and example actions.
- [x] Implement localized workbench workflow, example launch actions, and clearer next-step guidance.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab into a stable, user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for a homepage product workbench that explains the analysis workflow and exposes example launches.
- The bilingual UI now renders a `Research Workflow` / `研究工作台` section immediately after the analysis launcher.
- The workflow makes the intended user path explicit: define scope, compare candidates, read reports, and close evidence gaps.
- Added quick-start buttons for `HBM` and `memory chips` / `存储芯片`; each writes the example query into the analysis launcher and submits the existing `/analyze` flow.
- TDD red result: new assertions first failed because the homepage had a launcher and report library, but no product-level workflow guidance or example actions.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `15 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `149 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, and restarted the local server on `127.0.0.1:8767`.
- Local smoke: `/index.zh.html` and `/analyses/hbm-6f259a8f14/index.zh.html` returned HTTP 200 with `研究工作台`, example launch controls, imported evidence history, and resolved indicators; HBM acquisition queue and coverage matrix reports also returned HTTP 200.

# Serenity Alpha Lab Evidence History Persistence Phase

- [x] Review import data flow and evidence-task rendering anchors.
- [x] Add failing tests for persisted imported-evidence history and resolved task indicators.
- [x] Implement manual evidence history loading, task matching, and localized resolved states.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue developing Serenity Alpha Lab toward a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for persisted imported-evidence history, resolved task indicators, and reload behavior after a valid evidence import.
- Evidence task cards now load manual intake history from `manual_intake_guarded.jsonl`, match it by ticker and canonical evidence gap, and render the imported source title, id, date, and claim under the relevant task.
- Resolved evidence tasks now render localized `Resolved` / `已解决` status and `Resolved by imported evidence` / `已由导入证据解决`, with server-rendered `data-task-status="verified"` so reloads preserve completion state.
- Imported evidence whose original task disappears after the gap is closed is still rendered as a completed history card, so users can see which source resolved the prior gap.
- TDD red result: new tests first failed because `render_dashboard_html` did not accept imported evidence, `build_dashboard` did not load manual intake history, and refreshed analysis pages only showed a one-time import banner.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task tests/test_ui.py::test_build_dashboard_loads_manual_intake_history_for_analysis_page tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `15 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `149 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the coverage matrix, rebuilt bilingual UI, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, and restarted the local server on `127.0.0.1:8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md`, and `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md` returned HTTP 200 with expected Chinese snippets, imported evidence history, and resolved indicators.

# Serenity Alpha Lab Evidence Import UX Phase

- [x] Record the evidence-import UX phase and workflow target.
- [x] Add failing UI and HTTP E2E tests for import feedback, error recovery, and history visibility.
- [x] Implement localized form helper copy, submit feedback, error pages, and imported evidence history.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue making Serenity Alpha Lab usable as a stable product, with evidence import that gives clear feedback instead of behaving like a bare HTML form.
- Added regression coverage for localized evidence import helper text, required-field guidance, submit-in-progress feedback, imported-evidence history, and readable HTTP error recovery.
- Evidence task forms now show guidance for what to paste, a required-fields reminder, an `aria-live` import status, a submit loading state, and an imported-evidence placeholder.
- The import route now returns a localized HTML error page for rejected evidence, including a recovery instruction and the underlying validation detail.
- Successful imports now inject a visible success summary into the regenerated analysis page, including the imported source title and the resolved evidence gap.
- TDD red result: the new UI and HTTP E2E assertions failed because evidence forms lacked helper copy, submit status, import history, and readable error pages.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `13 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `147 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the default coverage matrix, rebuilt bilingual UI, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, and restarted the local server on `127.0.0.1:8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md`, and `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md` returned HTTP 200 with expected Chinese snippets and evidence import UX controls.

# Serenity Alpha Lab Evidence Import Loop Phase

- [x] Record the evidence-import loop phase and workflow target.
- [x] Add failing UI and HTTP E2E tests for manual evidence import.
- [x] Implement analysis-page evidence import form and `/ingest-evidence` server route.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue turning Serenity Alpha Lab into a stable user-facing Serenity-based stock, industry, theme, and ticker investment research product.
- Added regression coverage for visible analysis-page evidence import forms and HTTP-level `/ingest-evidence` behavior.
- Evidence task cards now include localized `Add Evidence` / `补充证据` forms with source title, source URL, and source excerpt fields, plus hidden query, language, ticker, evidence id, claim, and summary context.
- The local preview server now supports POST `/ingest-evidence`, validates through the guarded manual-intake path, appends evidence, rebuilds the matching analysis, writes a success banner, and redirects back to the generated report page.
- `serve-ui` now wires a default guarded intake callback using `--manual-intake-out` and includes the manual intake file in UI-launched analyses after it exists.
- `_build_theme_analysis_dashboard` now skips not-yet-created optional evidence files so first-run analysis does not fail before any manual evidence has been collected.
- TDD red result: the new UI/E2E assertions initially failed because task cards were read-only and `_build_dashboard_handler` had no ingest route.
- Root-cause fix: the first HTTP E2E failure came from treating a missing `manual_intake_guarded.jsonl` as a required analysis input; later assertions were adjusted to verify the correct gap transition after primary evidence is imported.
- Target verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_render_dashboard_html_localizes_visible_evidence_tasks tests/test_ui.py::test_build_dashboard_surfaces_acquisition_queue_tasks tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `4 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `13 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `147 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed the default pack, rebuilt the default coverage matrix, rebuilt bilingual UI, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, and restarted the local server on `127.0.0.1:8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md`, and `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md` returned HTTP 200 with expected Chinese snippets and evidence import controls.

# Serenity Alpha Lab Evidence Task Status Phase

- [x] Record the status-tracking phase and expected workflow.
- [x] Add failing UI and HTTP E2E tests for evidence task status controls.
- [x] Implement local status controls, persistence, and restore behavior.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and reusable lessons.

## Review

- User goal: continue turning visible evidence tasks into a usable research workflow for a stable investment-analysis product.
- Added regression coverage for `Task Status` / `任务状态` controls on visible evidence task cards.
- Evidence task cards now include status options: `To collect`, `Collected`, `Verified` / `待采集`, `已采集`, `已验证`.
- Each task card has a stable `data-task-id` and `data-task-status` attribute so task progress can be tracked per generated analysis page.
- Added client-side `initializeTaskStatuses()` and `updateTaskStatus()` logic to save task status in `localStorage` and restore it when the page is reopened.
- TDD red result: the status assertions failed because task cards were visible but still read-only.
- Target verification after implementation: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_render_dashboard_html_localizes_visible_evidence_tasks tests/test_ui.py::test_build_dashboard_surfaces_acquisition_queue_tasks tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `4 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `13 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `147 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, rebuilt bilingual UI, ran report safety scans, and restarted the local server on `127.0.0.1:8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` returned HTTP 200 with expected task-status snippets.

# Serenity Alpha Lab Visible Evidence Tasks Phase

- [x] Record this phase and close any stale completed checklist items.
- [x] Add failing UI tests for a visible evidence-task section on analysis pages.
- [x] Render localized evidence acquisition tasks directly in the dashboard.
- [x] Run targeted tests, full verification, rebuild product artifacts, restart the local UI, and smoke test HTTP paths.
- [x] Record review notes and any reusable lessons.

## Review

- User goal: continue turning Serenity Alpha Lab into a stable user-facing investment research product, with analysis pages that expose the next research actions directly.
- Added regression tests for a visible `Evidence Tasks` / `证据任务` section sourced from the acquisition queue.
- The dashboard now parses `reports/evidence-acquisition-queue.md` and renders the highest-priority ticker evidence tasks as cards directly on generated analysis pages.
- Each evidence task shows priority, ticker, gap, source target, and search prompt, with a copy button for the search prompt.
- Chinese analysis pages localize visible gap labels, source-target labels, section copy, and copy-prompt controls.
- TDD red result: the new UI and HTTP E2E assertions failed because generated pages only linked to the acquisition queue report and did not render visible evidence-task cards.
- Target verification after implementation: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_render_dashboard_html_localizes_visible_evidence_tasks tests/test_ui.py::test_build_dashboard_surfaces_acquisition_queue_tasks tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `4 passed`.
- UI verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `13 passed`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `147 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, rebuilt bilingual UI, and restarted the local server on `127.0.0.1:8767`.
- Safety scans: default pack and generated analysis packs both wrote report-safety scans with no command failures.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md`, and `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md` returned HTTP 200 with expected snippets.

# Serenity Alpha Lab Chinese Operational Reports Phase

- [x] Add failing tests for Chinese coverage-matrix and acquisition-queue report bodies.
- [x] Implement `language="zh"` rendering for operational report Markdown.
- [x] Wire Chinese UI-launched analyses to write localized operational reports.
- [x] Run full verification, product rebuild, safety scans, local UI smoke checks, and record review notes.

## Review

- User goal: keep Chinese UI-generated analysis pages fully localized, including operational reports opened from the report drawer.
- Added Chinese rendering coverage for `render_coverage_matrix_markdown(..., language="zh")` and `render_acquisition_queue_markdown(..., language="zh")`.
- Chinese coverage matrices now render `股票池覆盖矩阵`, `查询`, localized column headers, priority labels, gap names, and source-target descriptions.
- Chinese acquisition queues now render `证据采集队列`, `研究问题`, localized table labels, priority labels, gap names, and source-target descriptions.
- `_build_theme_analysis_dashboard` now writes localized operational reports when launched with `language="zh"`.
- HTTP E2E now verifies a launched Chinese `HBM` analysis serves Chinese operational report bodies, not just Chinese UI buttons.
- Target localization verification: `PYTHONPATH=src python3 -m pytest tests/test_coverage_matrix.py::test_render_coverage_matrix_markdown_localizes_chinese_report tests/test_acquisition_queue.py::test_render_acquisition_queue_markdown_localizes_chinese_report tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed`.
- Broader targeted verification: `PYTHONPATH=src python3 -m pytest tests/test_coverage_matrix.py tests/test_acquisition_queue.py tests/test_ui_http_e2e.py tests/test_release_hardening.py -q` -> `15 passed`.
- Full suite verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `145 passed`.
- Release verification: `make verify` ran full tests, `doctor`, `run-cpo-pack`, and `build-coverage-matrix` successfully.
- Product rebuild: regenerated source-backed metrics, refreshed Chinese analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`, rebuilt bilingual UI, and restarted the local server on `127.0.0.1:8767`.
- Safety scans: default pack and generated analysis packs both wrote report-safety scans with no command failures.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` returned HTTP 200 with expected Chinese report snippets.

# Serenity Alpha Lab Analysis Acquisition Queue Phase

- [x] Inspect existing acquisition queue contracts and analysis generation flow.
- [x] Add failing HTTP E2E coverage for generated analysis acquisition reports.
- [x] Generate per-analysis `evidence-acquisition-queue.md` reports.
- [x] Expose the acquisition queue through the generated analysis page report drawer.
- [x] Run full verification, product rebuild, safety scans, local UI smoke checks, and record review notes.

## Review

- User goal: make each generated industry/theme/ticker analysis tell users what evidence to collect next, not just show report summaries.
- Added per-analysis evidence acquisition queue generation in `_build_theme_analysis_dashboard`.
- Generated analysis pages now publish `reports/evidence-acquisition-queue.md` next to `reports/universe-coverage-matrix.md`.
- The UI operational report section now supports both `Open Coverage Matrix` / `打开覆盖矩阵` and `Open Acquisition Queue` / `打开采集队列`.
- Added HTTP E2E assertions that a launched `HBM` analysis exposes both report drawer buttons and serves the matching `HBM` acquisition queue.
- Verification: targeted acquisition queue and HTTP E2E tests passed; full suite passed with 143 tests before the Chinese localization follow-up.

# Serenity Alpha Lab Universe Coverage Matrix Phase

- [x] Review existing source coverage, readiness, acquisition queue, and stock-universe behavior.
- [x] Add failing tests for a universe-level coverage matrix and CLI output.
- [x] Implement a coverage matrix that maps theme candidates to evidence coverage, gaps, priority, and next source targets.
- [x] Document the operator workflow for checking industry/theme universe coverage.
- [x] Run targeted tests, full verification, regenerate product artifacts, and record review notes.

## Review

- User goal: keep advancing Serenity Alpha Lab toward a stable user-facing investment research product where industry/theme/ticker pages do not hide evidence coverage gaps.
- Added `src/serenity_alpha_lab/coverage_matrix.py`, which matches a query against the maintained stock universe and ranks candidates by evidence count, primary/fact coverage, risk coverage, coverage gaps, priority, and next source-search prompt.
- Added the `build-coverage-matrix` CLI command for producing `output/reports/universe-coverage-matrix.md` from local evidence and `config/stock_universe.json`.
- Added `make coverage-matrix` and included it in `make verify`, so release verification now checks both default memo generation and universe-level industry coverage.
- Updated `README.md`, `docs/OPERATIONS.md`, and `docs/RELEASE_CHECKLIST.md` with the coverage-matrix workflow and output contract.
- Added regression coverage for matrix ranking, Markdown rendering, CLI output, and release-hardening docs/Makefile checks.
- TDD red result: coverage-matrix tests initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.coverage_matrix'`.
- Target verification after implementation: `PYTHONPATH=src python3 -m pytest tests/test_coverage_matrix.py tests/test_cli.py::test_cli_build_coverage_matrix_writes_theme_universe_report tests/test_release_hardening.py -q` -> `11 passed`.
- Full test verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `142 passed`.
- Product artifact verification: `doctor` reported required inputs `ok`; `run-cpo-pack --allow-skipped` generated 182 combined evidence items, 6 ready memos, and 0 skipped; `build-coverage-matrix` wrote `output/reports/universe-coverage-matrix.md`.
- Current `存储芯片` matrix shows six matched candidates, with high-priority source gaps for `GIGADEVICE`, `MONTAGE`, `SAMSUNG`, `SKHYNIX`, `MU`, and `SNDK`, making the next evidence-acquisition targets explicit before UI promotion.
- Fixed a UI publishing gap found during HTTP smoke: `output/reports/universe-coverage-matrix.md` now copies into `output/ui/reports/universe-coverage-matrix.md`, and the homepage renders an `Open Coverage Matrix` / `打开覆盖矩阵` button that opens the report in the right-side drawer.
- Added regression coverage for the served coverage-matrix asset and visible bilingual homepage entry.

# Serenity Alpha Lab Evidence Audit Phase

# Serenity Alpha Lab Report Quality Phase

- [x] Inspect memo generation, scoring gaps, and current report tests.
- [x] Add failing tests for industry structure, catalyst timeline, and evidence-gap priority sections.
- [x] Implement bilingual report-quality sections in generated memos.
- [x] Update docs with the richer report contract.
- [x] Run targeted tests, full verification, safety scans, and local UI smoke checks.
- [x] Record review notes and lessons.

## Review

- User goal: improve generated reports so the UI product feels closer to formal investment research, not just evidence dumps.
- Added bilingual memo sections: `Industry Structure Map` / `行业结构图`, `Catalyst Timeline` / `催化剂时间线`, and `Evidence Gap Priority` / `证据缺口优先级`.
- The industry structure map groups evidence by supply-chain layer and shows evidence count, primary/fact coverage, risk count, and representative themes.
- The catalyst timeline surfaces dated fact/catalyst/revenue evidence so users can scan what events or disclosures matter next.
- The evidence-gap priority table converts scorecard gaps into ordered, actionable research tasks, prioritizing evidence collection over generic low-score labels.
- Added regression tests for English and Chinese report-quality sections.
- Updated `README.md`, `docs/OPERATIONS.md`, and `docs/RELEASE_CHECKLIST.md` with the richer report contract.
- Target verification: `python3 -m pytest tests/test_memo.py::test_generate_memo_includes_report_quality_sections tests/test_memo.py::test_generate_memo_localizes_report_quality_sections_for_chinese_reports -q` -> `2 passed`.
- Full verification: `python3 -m pytest tests -q` -> `139 passed`.
- Product rebuild: regenerated source-backed metrics, default CPO pack, bilingual homepage, and existing analysis pages for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Safety scan verification: default pack scanned 6 reports with `**Findings:** 0`; generated analysis packs scanned 49 reports with `**Findings:** 0`.
- Local smoke: restarted `127.0.0.1:8767`; Chinese homepage, English homepage, AAOI Chinese analysis page, and AAOI memo returned HTTP 200.

# Serenity Alpha Lab UI HTTP E2E Phase

- [x] Add task checklist and inspect current UI server, `/analyze` route, fixtures, and existing tests.
- [x] Add an HTTP E2E test for the Chinese analysis generation flow.
- [x] Fix server or test support issues found by the E2E test.
- [x] Update operations/release docs with the E2E smoke workflow.
- [x] Run full verification and local UI smoke checks.
- [x] Record review notes and lessons.

## Review

- User goal: keep advancing toward a product that can be stably used by others through the UI, not only by CLI-generated artifacts.
- Added `tests/test_ui_http_e2e.py`, a real HTTP-level E2E smoke test for the Chinese analysis flow.
- The E2E test starts an ephemeral local server, opens the Chinese homepage, calls `/analyze?query=存储芯片&language=zh`, follows the generated analysis URL, verifies candidate comparison and report drawer wiring, then fetches the generated Chinese memo asset.
- Added `make e2e` to run the HTTP UI smoke test directly.
- Updated `README.md`, `docs/OPERATIONS.md`, and `docs/RELEASE_CHECKLIST.md` so future UI/server changes run the E2E check before handoff.
- Target verification: `python3 -m pytest tests/test_ui_http_e2e.py tests/test_release_hardening.py -q` -> `9 passed`.
- Full verification: `python3 -m pytest tests -q` -> `137 passed`.
- Product rebuild: `build-financial-metrics` wrote 6 source-backed metric rows; `build-ui --language both` regenerated English and Chinese dashboards.
- Safety scan verification: default pack and generated analysis packs both wrote report-safety scans with zero findings.
- Local smoke: restarted `127.0.0.1:8767`; `/index.zh.html`, `/index.html`, `/analyses/aaoi-5622b4c1f7/index.zh.html`, and `/pack/aaoi-memo.md` all returned HTTP 200.

# Serenity Alpha Lab Report Safety Scanner Phase

- [x] Create task checklist and inspect existing CLI, memo generation, and release guardrail tests.
- [x] Add failing tests for report-safety scanning that distinguishes generated advice from quoted evidence.
- [x] Implement a reusable report safety scanner and CLI command.
- [x] Update release docs with the safety scan workflow.
- [x] Run full verification and local UI smoke checks.
- [x] Record review notes and any new lessons.

## Review

- User goal: keep moving the project toward a stable product that other users can trust for Serenity-style industry, sector, theme, and ticker research.
- Added `src/serenity_alpha_lab/report_safety.py`, a reusable Markdown report scanner that flags generated-report recommendation wording such as direct buy/sell/hold phrasing, target-price language, and position-sizing language.
- Added `scan-report-safety` CLI command, returning exit code `4` when product-authored report text violates safety guardrails and `0` when reports are clean.
- The scanner ignores quoted source-evidence lines so raw external excerpts containing phrases such as `buy / sell / hold` do not create false release blockers.
- Added tests covering unsafe generated prose, quoted evidence false-positive avoidance, Markdown scan rendering, and CLI behavior.
- Updated `README.md`, `docs/OPERATIONS.md`, and `docs/RELEASE_CHECKLIST.md` with the new report-safety scan workflow.
- Generated safety outputs: `output/reports/report-safety-scan.md` and `output/reports/report-safety-scan-analyses.md`.
- Target TDD verification: new report-safety tests initially failed because `serenity_alpha_lab.report_safety` did not exist, then passed after implementation.
- Full verification: `python3 -m pytest tests -q` -> `136 passed`.
- Product rebuild: `build-financial-metrics` wrote 6 source-backed metric rows; `build-ui --language both` regenerated English and Chinese dashboards.
- Safety scan verification: default pack scanned 6 reports with `**Findings:** 0`; generated analysis packs scanned 49 reports with `**Findings:** 0`.
- Local smoke: restarted `127.0.0.1:8767`; `/index.zh.html`, `/index.html`, `/analyses/aaoi-5622b4c1f7/index.zh.html`, and `/pack/aaoi-memo.md` all returned HTTP 200.

# Serenity Alpha Lab Product Handoff Docs Phase

- [x] Review current README, install, operations, release checklist, CLI, Makefile, and generated UI outputs.
- [x] Update user-facing handoff docs for the current Serenity stock/industry analysis workflow.
- [x] Update operations and release checks for metrics generation, bilingual UI, report library, drawer reports, and local smoke tests.
- [x] Run full tests plus local HTTP smoke checks after documentation updates.
- [x] Record review notes and lessons from the documentation phase.

## Review

- User goal: make the project usable by others as a stable Serenity-based stock, industry, sector, and theme investment research product.
- Updated `README.md` with the current product identity, Chinese-first user workflow, local server URL, analysis launcher behavior, report library, candidate comparison, drawer reports, source-backed metrics, and research-only guardrails.
- Updated `INSTALL.md` and `docs/OPERATIONS.md` with the current `run-cpo-pack --allow-skipped`, `build-financial-metrics`, bilingual `build-ui`, and `serve-ui --host 127.0.0.1 --port 8767 --language both` flow.
- Updated `docs/RELEASE_CHECKLIST.md` with full tests, source-backed metrics generation, bilingual UI rebuild, generated analysis smoke checks, drawer rendering checks, Chinese report sections, and evidence safety checks.
- Captured a lesson from the release-checklist regression: exact canonical compliance phrases such as `research only` must be preserved where tests assert them.
- Full verification: `python3 -m pytest tests -q` -> `131 passed`.
- Product rebuild: `build-financial-metrics` wrote 6 source-backed metric rows; `build-ui --language both` regenerated English and Chinese dashboards.
- Local smoke: restarted `127.0.0.1:8767`; `/index.zh.html`, `/index.html`, `/analyses/aaoi-5622b4c1f7/index.zh.html`, and `/pack/aaoi-memo.md` all returned HTTP 200.
- Follow-up: the release safety review should eventually distinguish generated investment recommendations from quoted source evidence, because raw evidence excerpts may contain words such as buy/sell/hold even when the product itself remains research-only.

# Serenity Alpha Lab Report Reader Polish Phase

- [x] Define product gap: the side drawer currently renders reports as raw Markdown text instead of a readable product report view.
- [x] Add regression tests for formatted report drawer rendering and escaping behavior.
- [x] Implement a safe lightweight Markdown-to-HTML renderer for fetched memo files.
- [x] Rebuild UI analyses and smoke test opening formatted reports from the drawer.

## Review

- User goal: make generated reports comfortable for real users to read inside the UI, not just technically accessible.
- Added a lightweight in-browser Markdown renderer for memo drawer reports.
- Reports now render as structured headings, paragraphs, lists, and bold inline text instead of raw `<pre>` blocks.
- Added HTML escaping before inline Markdown formatting so fetched memo content cannot inject arbitrary HTML/script into the drawer.
- Added drawer reading styles for `markdown-body`, section headings, list spacing, and strong labels.
- Target verification: `python3 -m pytest tests/test_ui.py::test_report_drawer_renders_markdown_safely tests/test_ui.py::test_build_dashboard_writes_static_html -q` -> `2 passed`.
- Full verification: `python3 -m pytest tests -q` -> `131 passed`.
- Local smoke: regenerated source-backed metrics, rebuilt `存储芯片`, `HBM`, `半导体设备`, and `AAOI` analyses, restarted `127.0.0.1:8767`; Chinese homepage and AAOI page returned HTTP 200 and include formatted drawer rendering code.

# Serenity Alpha Lab Evidence Action Plan Phase

- [x] Define product gap: generated reports need actionable evidence acquisition steps, not only static gap labels.
- [x] Add regression tests for English and Chinese evidence action-plan sections.
- [x] Implement report-level evidence action plans from scorecard gaps and source coverage.
- [x] Rebuild UI analyses and verify generated Chinese reports include actionable next evidence steps.

## Review

- User goal: make each investment-analysis report tell users what evidence to collect next before raising confidence.
- Added a dedicated `Evidence Action Plan` / `证据补齐行动清单` section to generated reports.
- Action plans now map scorecard gaps to concrete evidence tasks such as primary-source depth, demand validation, invalidation planning, crowding review, and promotion gates.
- Chinese reports now tell users exactly what evidence to collect before raising confidence or moving a ticker beyond watchlist status.
- Target verification: `python3 -m pytest tests/test_memo.py::test_generate_memo_includes_actionable_evidence_plan_for_gaps tests/test_memo.py::test_generate_memo_localizes_evidence_action_plan_for_chinese_reports -q` -> `2 passed`.
- Full verification: `python3 -m pytest tests -q` -> `130 passed`.
- Local smoke: regenerated source-backed metrics and Chinese analyses, restarted `127.0.0.1:8767`; homepage and AAOI analysis page returned HTTP 200, and generated Chinese memo files include `## 证据补齐行动清单` plus actionable items.

# Serenity Alpha Lab Chinese Metric Localization Phase

- [x] Define product gap: Chinese UI metric labels are localized, but source-backed metric values still render as English phrases.
- [x] Add regression tests for Chinese display-time localization of metric values.
- [x] Implement UI-only metric value localization while keeping the metrics catalog stable and language-neutral.
- [x] Rebuild UI analyses and verify Chinese report pages show localized metric values.

## Review

- User goal: make the product usable for Chinese investors, with report pages and candidate comparisons readable in Chinese.
- Added display-time localization for source-backed metric values in Chinese candidate comparison tables.
- Kept `config/financial_metrics.json` language-neutral and stable while rendering Chinese phrases only in the Chinese UI.
- Localized source-backed revenue, reported profitability/loss, official YoY growth, and cycle-position labels.
- Target verification: `python3 -m pytest tests/test_ui.py::test_render_dashboard_html_localizes_chinese_metric_values -q` -> `1 passed`.
- Full verification: `python3 -m pytest tests -q` -> `128 passed`.
- Local smoke: regenerated source-backed metrics, rebuilt `存储芯片`, `HBM`, `半导体设备`, and `AAOI` analyses, restarted `127.0.0.1:8767`; Chinese homepage, AAOI page, and semiconductor-equipment page returned HTTP 200 with localized metric values and no leaked English metric enums.

# Serenity Alpha Lab Source-Backed Metrics Phase

- [x] Define product gap: local metric catalog needs source-backed generation, not only manually maintained fields.
- [x] Add regression tests for deriving revenue growth and profitability context from local evidence.
- [x] Implement a metrics builder that converts primary company evidence into dashboard metric rows.
- [x] Add a CLI path to generate `config/financial_metrics.json` from local evidence files.
- [x] Regenerate UI analyses and verify source-backed metrics appear in Chinese report pages.

## Review

- User goal: move closer to a stable product where industry, ticker, and sector analysis includes comparable financial context grounded in available local evidence.
- Added `src/serenity_alpha_lab/financial_metrics.py` to derive UI-compatible metrics from primary evidence.
- Added `build-financial-metrics` CLI command so `config/financial_metrics.json` can be regenerated from local evidence JSONL files.
- Fixed profitability classification so accounting labels such as `Net Income (Loss)` do not mark positive net income as a loss.
- Updated UI metric loading so project builds refresh stale `output/ui/metrics.json` from `config/financial_metrics.json`, while isolated builds can still inherit parent metrics.
- Generated source-backed metrics now include revenue base / YoY revenue context, profitability momentum, and cycle-position labels for locally covered tickers.
- Target verification: `python3 -m pytest tests/test_financial_metrics.py tests/test_cli.py::test_cli_build_financial_metrics_writes_source_backed_catalog -q` -> `4 passed`.
- Full verification: `python3 -m pytest tests -q` -> `127 passed`.
- Local smoke: regenerated source-backed metrics, rebuilt `存储芯片`, `HBM`, `半导体设备`, and `AAOI` analyses, restarted `127.0.0.1:8767`; Chinese/English homepages plus AAOI and semiconductor-equipment Chinese pages returned HTTP 200 and include source-backed metric values.

# Serenity Alpha Lab Financial Metrics Phase

- [x] Define product gap: candidate comparison needs local financial and market metrics, not only evidence-derived scores.
- [x] Add regression tests for loading a metrics catalog and rendering metrics-enriched comparison rows.
- [x] Implement optional local metrics catalog support for dashboard generation.
- [x] Add revenue growth, gross margin, valuation, momentum, and cycle position to the candidate comparison table.
- [x] Regenerate UI analyses and verify local smoke paths.

## Review

- User goal: move the product closer to a usable investment analysis system by combining Serenity evidence scoring with comparable financial and market context.
- Added a maintained local metrics catalog at `config/financial_metrics.json`, copied into `output/ui/metrics.json` during UI builds.
- Candidate comparison tables now show revenue growth, gross margin, valuation, momentum, and cycle position in English and Chinese dashboards.
- Generated analysis pages under `output/ui/analyses/...` now search parent UI directories for `metrics.json`, so deep report pages reuse the same metrics catalog.
- Metrics remain research-context fields: missing or not-yet-source-backed values render as `n/a` rather than invented precision.
- Target verification: `python3 -m pytest tests/test_ui.py::test_build_dashboard_copies_config_metrics_catalog tests/test_ui.py::test_build_dashboard_uses_parent_ui_metrics_for_analysis_pages -q` -> `2 passed`.
- Full verification: `python3 -m pytest tests -q` -> `122 passed`.
- Local smoke: regenerated `存储芯片`, `HBM`, `半导体设备`, and `AAOI` analyses plus bilingual home UI; restarted `127.0.0.1:8767`; Chinese/English homepage, `存储芯片`, and `HBM` pages returned HTTP 200 and include financial/market metric columns.

# Serenity Alpha Lab Candidate Comparison Phase

- [x] Define product gap: industry pages need a compact candidate comparison table, not only separate memo cards.
- [x] Add regression tests for comparison rows with score, rating, confidence, gaps, and evidence coverage.
- [x] Implement bilingual candidate comparison table on dashboard pages.
- [x] Regenerate UI analyses and verify local smoke paths.

## Review

- User goal: make industry investment analysis easier to use by comparing multiple candidates side by side before opening full reports.
- Added a bilingual `Candidate Comparison` / `候选对比` section to dashboard pages.
- The comparison table shows ticker, status, score, rating, confidence, key gaps, evidence count, primary/fact count, and risk count.
- The table reuses memo-preview scorecard metadata so the comparison table, report cards, and full memos remain consistent.
- Target verification: `python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html -q` -> `2 passed`.
- Full verification: `python3 -m pytest tests -q` -> `119 passed`.
- Local smoke: regenerated `存储芯片`, `HBM`, `半导体设备`, and `AAOI` analyses plus bilingual home UI; restarted `127.0.0.1:8767`; Chinese homepage, English homepage, `存储芯片`, and `HBM` analysis pages returned HTTP 200 and include candidate-comparison content.

# Serenity Alpha Lab Report Library Phase

- [x] Define product gap: generated analysis pages need a homepage report library instead of relying on direct links.
- [x] Add regression tests for persisted analysis history and homepage report-library rendering.
- [x] Implement analysis manifest persistence when industry/theme/ticker analyses are generated.
- [x] Render recent reports on English and Chinese home dashboards with direct report links.
- [x] Regenerate UI analyses and verify local smoke paths.

## Review

- User goal: make the product usable by others, with generated industry and ticker reports discoverable from the UI after creation.
- Added `output/ui/analyses/manifest.json` as a persisted report-history index for UI-generated analyses.
- Updated analysis generation to write query, intent, canonical theme, candidate tickers, and Chinese/English report links into the manifest.
- Updated the homepage dashboard to render a bilingual `Recent Reports` / `最近报告` report library from the manifest.
- The report library now links directly to generated analysis pages such as `存储芯片`, `HBM`, `半导体设备`, and `AAOI`.
- Target verification: `python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` -> `3 passed`.
- Full verification: `python3 -m pytest tests -q` -> `119 passed`.
- Local smoke: regenerated analyses and bilingual UI; restarted `127.0.0.1:8767`; Chinese homepage, English homepage, and `存储芯片` analysis page returned HTTP 200. Homepage now includes `最近报告`, `Recent Reports`, `存储芯片`, `HBM`, and report links.

# Serenity Alpha Lab Scorecard Phase

- [x] Define product gap: users need a visible Serenity rating, confidence tier, and key gaps, not only a raw score.
- [x] Add regression tests for scorecard rating labels in scoring, memos, memo-pack index, and dashboard previews.
- [x] Implement scorecard summary helpers while preserving research-only guardrails.
- [x] Surface scorecard rating, confidence, and gaps in Chinese/English reports and UI cards.
- [x] Regenerate UI analyses and verify local smoke paths.

## Review

- User goal: continue toward a stable Serenity stock-selection product where industry, ticker, and sector inputs produce understandable investment research reports rather than raw diagnostics.
- Added scorecard summary output with Serenity rating, research confidence tier, and key evidence gaps.
- Surfaced the scorecard summary in Chinese and English memo headers while preserving research-only guardrails.
- Expanded memo-pack index columns to include `Serenity Rating`, `Confidence`, and `Key Gaps` for portfolio-level triage.
- Updated UI preview cards and report cards to show rating, confidence, and key gaps before opening full reports.
- Target verification: `python3 -m pytest tests/test_scoring.py tests/test_memo.py::test_generate_memo_can_render_chinese_report tests/test_memo_pack.py::test_render_memo_pack_index_lists_memos_and_gap_reasons tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui.py::test_build_dashboard_writes_static_html -q` -> `8 passed`.
- Full verification: `python3 -m pytest tests -q` -> `119 passed`.
- Local smoke: regenerated bilingual UI and analyses for `存储芯片`, `HBM`, `半导体设备`, and `AAOI`; restarted `127.0.0.1:8767`; Chinese homepage, `存储芯片`, and `HBM` pages returned HTTP 200 and include `Serenity 评级`, `置信层级`, and `关键短板`.
- Generated Chinese memos now include `**Serenity 评级:**`, `**研究置信层级:**`, `**关键短板:**`, `## 评分卡`, and `仅供研究`.

# Serenity Alpha Lab Stock Universe Phase

- [x] Define gap: industry/theme inputs need a maintained stock universe, not only evidence-derived tickers.
- [x] Add regression tests for universe-backed candidate expansion.
- [x] Implement stock universe catalog loading and validation.
- [x] Integrate stock universe candidates into topic resolver and UI-launched analysis.
- [x] Regenerate UI analyses and verify local smoke paths.

## Review

- User goal: keep advancing toward a stable Serenity stock-selection product where industry, ticker, and sector inputs produce useful candidate sets and investment research reports.
- Added `stock_universe` catalog support through `config/stock_universe.json`, including memory/HBM, semiconductor equipment, and optical interconnect candidates.
- Fixed topic resolution so known themes such as `HBM` are treated as industry/theme inputs rather than accidental ticker symbols.
- Fixed candidate ordering so maintained stock-universe matches stay visible ahead of noisy evidence-derived candidates for industry analysis pages.
- Target verification: `python3 -m pytest tests/test_topic_resolver.py tests/test_stock_universe.py -q` -> `8 passed`.
- Full verification: `python3 -m pytest tests -q` -> `118 passed`.
- Local smoke: regenerated bilingual UI and analysis pages; restarted `127.0.0.1:8767`; `index.zh.html`, `index.html`, `存储芯片`, and `HBM` analysis pages returned HTTP 200.
- `存储芯片` candidate line now includes `MU`, `SKHYNIX`, `SAMSUNG`, `SNDK`, `MONTAGE`, and `GIGADEVICE`; generated Chinese memos include `投资分析结论`, `Serenity 选股因子`, `关键跟踪指标`, and `仅供研究`.

# Serenity Alpha Lab General Stock Selection Phase

- [x] Define next product target: users can input an industry, sector, theme, or ticker and receive a Serenity-style investment research report.
- [x] Add regression tests for query intent parsing, candidate ticker generation, and Chinese investment-report sections.
- [x] Implement a topic resolver that converts user input into canonical themes, aliases, and candidate tickers.
- [x] Wire UI-launched analysis to resolver-generated candidates instead of only fixed default tickers.
- [x] Upgrade Chinese memo output from evidence memo to investment-analysis report structure.
- [x] Verify targeted tests, full suite, and local UI smoke checks.

## Review

- User goal: Serenity Alpha Lab should become a Serenity-based stock selection and investment analysis system, not only a CPO memo pack viewer.
- Added `topic_resolver` to classify user input as ticker, industry, sector, or theme; expand aliases such as `存储芯片 -> memory/storage/DRAM/NAND/HBM`; and rank candidate tickers from evidence.
- UI-launched analysis now uses resolver-generated candidates within the configured ticker boundary, so industry inputs produce a candidate pool instead of blindly using the old fixed list.
- Chinese reports now include investment-analysis sections: `投资分析结论`, `Serenity 选股因子`, and `关键跟踪指标`, while preserving research-only guardrails.
- Target verification: `python3 -m pytest tests/test_topic_resolver.py tests/test_memo.py::test_generate_memo_can_render_chinese_report tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` -> `5 passed`.
- Full verification: `python3 -m pytest tests -q` -> `113 passed`.
- Local smoke: restarted `127.0.0.1:8767`; `index.zh.html`, `存储芯片` analysis page, and a generated memo returned HTTP 200. The memo includes the new Chinese investment sections and `仅供研究`.

# Serenity Alpha Lab Chinese Report Phase

- [x] Reproduce user-facing issue: Chinese UI still opened English memo bodies.
- [x] Add regression coverage for Chinese memo generation through memo, pack, and UI-launched analysis.
- [x] Implement Chinese memo rendering and preview extraction fallback.
- [x] Verify targeted tests, full suite, and local UI smoke checks.
- [x] Regenerate current Chinese analysis pages.

## Review

- User correction: the dashboard language switch was not enough; the full report content opened from the right-side drawer also needs to be Chinese.
- Fix: memo generation now accepts `language="zh"`, memo packs pass that through, Chinese UI-launched analyses generate Chinese report bodies, and dashboard previews can extract Chinese headings.
- Product behavior: UI-launched packs now include diagnostic gap reports for non-ready tickers so users can still read why evidence coverage is incomplete.
- Target verification: `python3 -m pytest tests/test_retrieval.py::test_retrieve_expands_chinese_industry_theme_aliases tests/test_memo.py::test_generate_memo_can_render_chinese_report tests/test_memo_pack.py::test_build_memo_pack_can_generate_chinese_memos tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` -> `4 passed`.
- Full verification: `python3 -m pytest tests -q` -> `110 passed`.
- Regenerated pages: `output/ui/index.html`, `output/ui/index.zh.html`, and Chinese analyses for `存储芯片`, `HBM`, and `半导体设备`.

# Serenity Alpha Lab UI Timeout Fix Phase

- [x] Reproduce user-facing issue: valid UI links timed out instead of loading.
- [x] Identify root cause: the local preview server was single-threaded and could be blocked by a stuck browser connection.
- [x] Add regression coverage for threaded preview server behavior.
- [ ] Verify tests, restart local UI, and smoke test all shared links.

## Review

- User correction: links that previously worked became unreachable because every request to `127.0.0.1:8767` timed out while the old preview server process was still alive.

# Serenity Alpha Lab Memo Drawer UI Phase

- [x] Reproduce user-facing issue: memo links can 404 from the served UI root.
- [x] Clarify UX target: compact overview with reports opened in a right-side drawer.
- [x] Add regression tests for served memo links and drawer controls.
- [x] Copy served memo assets into the UI root when needed.
- [x] Replace direct memo navigation with right-side drawer report reading.
- [x] Verify tests, restart local UI, and smoke test memo opening.

## Review

- User correction: `打开备忘录` links were failing with 404, and the generated dashboard felt too crowded because report content was flattened into the page instead of opened on demand.
- Fix: dashboard generation now copies memo pack assets into the served UI directory and opens reports through a right-side drawer using `data-memo-href` instead of direct external relative links.
- Target verification: `python3 -m pytest tests/test_ui.py -q` -> `3 passed`.
- Full verification: `python3 -m pytest tests -q` -> `107 passed`.
- Local smoke test: restarted `127.0.0.1:8767`; `/pack/sive-memo.md` and `/pack/aaoi-memo.md` returned HTTP 200, and generated analysis pages include `id="memo-drawer"`, `查看报告`, and `openMemoDrawer`.

# Serenity Alpha Lab Launch Feedback Phase

- [x] Reproduce HBM launch path and confirm backend route returns a generated page.
- [x] Identify UX root cause: submit has no visible loading or live status feedback.
- [ ] Add regression tests for launch feedback text and live region.
- [ ] Implement submit loading state and screen-reader status.
- [ ] Verify targeted tests and full suite.
- [ ] Restart local UI and smoke test `HBM`.

## Review

- User correction: entering `HBM` launched successfully server-side, but the UI did not show immediate feedback, making the product feel unresponsive.

# Serenity Alpha Lab Theme Launch UI Phase

- [x] Clarify that page search only filters the current research pack.
- [x] Add visible `Start analysis` / `启动分析` controls.
- [x] Add local `/analyze` server route for new industry themes.
- [x] Wire UI-launched analysis to readiness, memo-pack, and bilingual dashboard generation.
- [x] Verify target tests and full suite.
- [x] Restart local UI and smoke test `存储芯片`.

## Review

- User correction: entering `存储芯片` in the current search box had no start button because the box only filtered the existing CPO dashboard.
- Target verification: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` -> `4 passed`.
- Full verification: `python3 -m pytest tests -q` -> `107 passed`.
- Local smoke test: `http://127.0.0.1:8767/analyze?query=存储芯片&language=zh` redirected to `/analyses/topic-602483dcf3/index.zh.html` and returned HTTP 200 with `存储芯片`, `启动分析`, and `Serenity Alpha Lab`.

# Serenity Alpha Lab Bilingual UI Phase

- [x] Create bilingual UI phase plan.
- [x] Add failing tests for English and Chinese dashboard generation.
- [x] Implement locale-aware UI rendering.
- [x] Add `build-ui --language en|zh|both`.
- [x] Update documentation and usage notes.
- [x] Regenerate both UI files.
- [x] Run full verification and HTTP smoke checks.

## Review

- Red check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_bilingual_dashboards -q` failed because `index.zh.html` was not generated and `build-ui` did not accept `--language`.
- Target green check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_bilingual_dashboards -q` -> `4 passed in 0.04s`.
- Full verification: `python3 -m pytest tests -q` passed; `build-ui --language both` generated `output/ui/index.html` and `output/ui/index.zh.html`; HTTP smoke checks passed for both language URLs.

# Serenity Alpha Lab Local UI Phase

# Serenity Alpha Lab Interactive UI Phase

# Serenity Alpha Lab UI Server Restart Fix

- [x] Reproduce local UI URL failure from stale server restart.
- [x] Record the server restart lesson.
- [x] Enable reusable local preview server sockets.
- [x] Verify target tests and restart smoke path.
- [x] Restart the UI on a confirmed reachable URL.

## Review

- Failure observed: after terminating previous PID `74419`, `serve-ui` failed with `OSError: [Errno 48] Address already in use` while binding `127.0.0.1:8767`.
- Fix verification: target UI tests passed with `4 passed in 0.07s`; full suite passed with `105 passed`; restarted UI responded with HTTP 200 at `http://127.0.0.1:8767/index.html` using PID `86862`.

- [x] Create interactive UI phase plan.
- [x] Add failing tests for dashboard controls and local server command.
- [x] Implement search, status filters, ticker focus, and provenance expansion.
- [x] Add `serve-ui` CLI command.
- [x] Add Makefile and documentation entry points.
- [x] Regenerate `output/ui/index.html`.
- [x] Run full verification.

## Review

- Red check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` failed because search controls and `serve_dashboard` did not exist.
- Target green check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server -q` -> `3 passed in 0.04s`.
- Full verification: `python3 -m pytest tests -q` -> `105 passed in 0.16s`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- UI generation: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui` wrote `output/ui/index.html`; smoke check confirmed search controls, filter script, core sections, and all six tickers are present.
- Local HTTP smoke check: `serve-ui` responded successfully at `http://127.0.0.1:8766/index.html` during verification.

- [x] Create local UI phase plan.
- [x] Add failing tests for dashboard rendering and CLI generation.
- [x] Implement static dashboard parser and renderer.
- [x] Add `build-ui` CLI command.
- [x] Add Makefile and documentation entry points.
- [x] Generate `output/ui/index.html`.
- [x] Run full verification.

## Review

- Red check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_dashboard -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.ui'`.
- Target green check: `python3 -m pytest tests/test_ui.py tests/test_cli.py::test_cli_build_ui_writes_dashboard -q` -> `3 passed in 0.04s`.
- Full verification: `python3 -m pytest tests -q` -> `104 passed in 0.14s`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- UI generation: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui` wrote `output/ui/index.html`; smoke check confirmed key sections and tickers are present.

- [x] Create local task tracker for the evidence audit phase.
- [x] Write the audit implementation plan.
- [x] Add failing tests for evidence audit behavior.
- [x] Implement `evidence_audit` module.
- [x] Add `audit-evidence` CLI subcommand.
- [x] Generate `output/reports/evidence-audit.md` from imported GitHub evidence.
- [x] Run full verification.

## Review

- Baseline before audit work: `python3 -m pytest tests -q` -> `19 passed in 0.04s`.
- Red check: `python3 -m pytest tests/test_evidence_audit.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence_audit'`.
- CLI red check: `python3 -m pytest tests/test_cli.py::test_cli_audit_evidence_writes_report -q` failed because `audit-evidence` routed to memo mode and required `--query`.
- Local audit verification: `python3 -m pytest tests/test_evidence_audit.py -q && python3 -m pytest tests/test_cli.py::test_cli_audit_evidence_writes_report -q` -> `2 passed in 0.01s`; `1 passed in 0.02s`.
- Generated report: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/imported/github_evidence.jsonl --ticker SIVE --out output/reports/evidence-audit.md`.
- Real corpus audit result: 164 evidence items; top quality flags are `placeholder_ticker_concentration` at 113/164 and `short_summary` at 18/164.
- Full verification: `python3 -m pytest tests -q` -> `22 passed in 0.07s`.

# Serenity Alpha Lab Ticker Resolution Phase

- [x] Create ticker resolution phase plan.
- [x] Add failing tests for ticker resolution behavior.
- [x] Implement `ticker_resolution` module.
- [x] Add `resolve-tickers` CLI subcommand.
- [x] Create conservative real ticker resolution rules.
- [x] Generate `data/enriched/github_evidence_resolved.jsonl`.
- [x] Generate `output/reports/evidence-audit-resolved.md`.
- [x] Run full verification.

## Review

- Starting point: prior audit flagged `placeholder_ticker_concentration` at 113/164 and `short_summary` at 18/164.
- Resolver red check: `python3 -m pytest tests/test_ticker_resolution.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.ticker_resolution'`.
- Resolver green check: `python3 -m pytest tests/test_ticker_resolution.py -q` -> `4 passed in 0.01s`.
- CLI red check: `python3 -m pytest tests/test_cli.py::test_cli_resolve_tickers_writes_enriched_jsonl -q` failed because `resolve-tickers` routed to memo mode and required `--query`.
- CLI green check: `python3 -m pytest tests/test_cli.py::test_cli_resolve_tickers_writes_enriched_jsonl -q` -> `1 passed in 0.01s`.
- Real evidence keyword scan showed CPO evidence already intersects with `SIVE`, `AXTI`, `AAOI`, `LITE`, and `COHR`; rules were kept keyword-gated instead of blanket-mapping every `SERENITY` item.
- First enrichment pass appended concrete tickers but did not reduce `SERENITY`; regression test added to remove placeholder only when the original ticker set is exactly `["SERENITY"]` and a rule matches.
- Resolver verification after placeholder fix: `python3 -m pytest tests/test_ticker_resolution.py -q` -> `5 passed in 0.01s`.
- Generated resolved evidence: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli resolve-tickers --data data/imported/github_evidence.jsonl --rules config/ticker_resolution_rules.json --out data/enriched/github_evidence_resolved.jsonl`.
- Generated resolved audit: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_evidence_resolved.jsonl --ticker SIVE --out output/reports/evidence-audit-resolved.md`.
- Audit delta: `SERENITY` placeholder ticker count improved from 113/164 to 99/164; resolved themes added `SIVE` 50, `AAOI` 43, `LITE` 43, `COHR` 41, and `AXTI` 21.
- Full verification: `python3 -m pytest tests -q` -> `28 passed in 0.05s`.

# Serenity Alpha Lab Summary Quality Phase

- [x] Create summary quality phase plan.
- [x] Add failing tests for multilingual audit summary quality.
- [x] Add failing tests for deterministic summary enrichment.
- [x] Implement multilingual weak-summary heuristic.
- [x] Implement `summary_enrichment` module.
- [x] Add `enrich-summaries` CLI subcommand.
- [x] Generate `data/enriched/github_evidence_resolved_summaries.jsonl`.
- [x] Generate `output/reports/evidence-audit-summary-enriched.md`.
- [x] Run full verification.

## Review

- Starting point: resolved audit still reported `short_summary` at 18/164, but sample inspection showed many Chinese summaries are meaningful and only misclassified because `split()` is English-centric.
- Red check: `python3 -m pytest tests/test_evidence_audit.py tests/test_summary_enrichment.py -q` failed because `is_weak_summary` and `summary_enrichment` did not exist.
- Module green check: `python3 -m pytest tests/test_evidence_audit.py tests/test_summary_enrichment.py -q` -> `7 passed in 0.01s`.
- CLI red check: `python3 -m pytest tests/test_cli.py::test_cli_enrich_summaries_writes_jsonl -q` failed because `enrich-summaries` routed to memo mode and required `--query`.
- CLI green check: `python3 -m pytest tests/test_cli.py::test_cli_enrich_summaries_writes_jsonl -q` -> `1 passed in 0.02s`.
- Generated summary-enriched evidence: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli enrich-summaries --data data/enriched/github_evidence_resolved.jsonl --out data/enriched/github_evidence_resolved_summaries.jsonl`.
- Generated summary-enriched audit: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_evidence_resolved_summaries.jsonl --ticker SIVE --out output/reports/evidence-audit-summary-enriched.md`.
- Audit delta: old English-only audit reported `short_summary` at 18/164; multilingual heuristic found 7 truly weak summaries; summary enrichment reduced weak summaries from 7 to 0.
- Full verification: `python3 -m pytest tests -q` -> `34 passed in 0.05s`.

# Serenity Alpha Lab SEC Companyfacts Primary Source Phase

- [x] Create SEC companyfacts connector plan.
- [x] Add failing tests for SEC companyfacts parsing and evidence conversion.
- [x] Implement `sec_companyfacts` module.
- [x] Add `import-sec-companyfacts` CLI subcommand.
- [x] Create local SEC companyfacts source manifest.
- [x] Generate `data/primary/sec_companyfacts_evidence.jsonl`.
- [x] Generate `output/reports/evidence-audit-primary.md`.
- [x] Run full verification.

## Review

- Starting point: summary-enriched audit has no short-summary flag, but still reports `placeholder_ticker_concentration` at 99/164. Primary-source evidence should increase ticker-specific fact density rather than mutate Serenity methodology evidence.
- Red check: `python3 -m pytest tests/test_sec_companyfacts.py -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.sec_companyfacts'`.
- Parser green check: `python3 -m pytest tests/test_sec_companyfacts.py -q` -> `3 passed in 0.01s`.
- CLI red check: `python3 -m pytest tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q` failed because `import-sec-companyfacts` routed to memo mode and required `--data` / `--query`.

# Serenity Alpha Lab Source Coverage Gate Phase

- [x] Create source coverage gate phase plan.
- [x] Add failing tests for source coverage behavior.
- [x] Implement `source_coverage` module.
- [x] Integrate source coverage section into memos.
- [x] Generate `output/memos/aaoi-cpo-coverage.md`.
- [x] Run full verification.

## Review

- Starting point: primary-source facts are ranked and shown in memos, but memo readers still lack an explicit quality gate that distinguishes adequate ticker coverage from methodology-heavy or placeholder-heavy evidence.
- Red check: `python3 -m pytest tests/test_source_coverage.py tests/test_memo.py::test_generate_memo_lists_primary_source_evidence_before_supporting_evidence -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.source_coverage'`.
- Target green check: `python3 -m pytest tests/test_source_coverage.py tests/test_memo.py::test_generate_memo_lists_primary_source_evidence_before_supporting_evidence -q` -> `7 passed in 0.02s`.
- Generated coverage memo: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --ticker AAOI --out output/memos/aaoi-cpo-coverage.md --limit 16`.
- Real memo coverage check: AAOI retrieved evidence has 16 items, 16 focus ticker items, 3 primary/fact items, 4 risk items, 6% methodology concentration, 0% SERENITY placeholder concentration, and no critical coverage flags.
- Full verification: `python3 -m pytest tests -q` -> `53 passed in 0.07s`.

# Serenity Alpha Lab Primary Retrieval Boost Phase

- [x] Create primary retrieval boost plan.
- [x] Add failing tests for primary-source retrieval ranking.
- [x] Add failing tests for memo primary-source section.
- [x] Implement retrieval primary/fact boost.
- [x] Implement memo `Primary Source Evidence` section.
- [x] Generate `output/memos/aaoi-cpo-primary.md`.
- [x] Run full verification.

## Review

- Starting point: SEC primary facts exist in `data/enriched/github_plus_primary.jsonl`, but retrieval/memo still treat them as ordinary evidence.
- Retrieval red check: `python3 -m pytest tests/test_retrieval.py -q` failed because ticker-focused methodology evidence outranked focus ticker SEC primary fact evidence.
- Retrieval green check: `python3 -m pytest tests/test_retrieval.py -q` -> `2 passed in 0.01s`.
- Memo red check: `python3 -m pytest tests/test_memo.py -q` failed because `## Primary Source Evidence` did not exist.
- Memo section refinement: added tests to ensure primary facts are not duplicated in general supporting evidence and negative primary facts still appear in the primary section.
- Target verification: `python3 -m pytest tests/test_retrieval.py tests/test_memo.py -q` -> `6 passed in 0.02s`.
- Generated primary-boosted memo: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --ticker AAOI --out output/memos/aaoi-cpo-primary.md --limit 16`.
- Real memo check: `Primary Source Evidence` contains AAOI SEC net income, revenue, and share count facts; general `Supporting Evidence` no longer repeats the primary revenue item.
- Full verification: `python3 -m pytest tests -q` -> `47 passed in 0.06s`.

# Serenity Alpha Lab Check Coverage CLI Phase

- [x] Create check coverage CLI phase plan.
- [x] Add failing CLI coverage report test.
- [x] Implement `check-coverage` CLI subcommand.
- [x] Generate `output/reports/aaoi-cpo-coverage.md`.
- [x] Run full verification.

## Review

- Starting point: memo generation now includes source coverage, but there is no standalone command to assess research readiness before generating a full memo.
- Red check: `python3 -m pytest tests/test_cli.py::test_cli_check_coverage_writes_report -q` failed because `check-coverage` was not recognized by the base memo parser.
- Target green check: `python3 -m pytest tests/test_cli.py::test_cli_check_coverage_writes_report -q` -> `1 passed in 0.02s`.
- Generated standalone coverage report: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli check-coverage --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --ticker AAOI --out output/reports/aaoi-cpo-coverage.md --limit 16`.
- Real report coverage check: AAOI retrieved evidence has 16 items, 16 focus ticker items, 3 primary/fact items, 4 risk items, 6% methodology concentration, 0% SERENITY placeholder concentration, and no critical coverage flags.
- Full verification: `python3 -m pytest tests -q` -> `54 passed in 0.07s`.

# Serenity Alpha Lab Batch Readiness Scanner Phase

- [x] Create batch readiness scanner phase plan.
- [x] Add failing batch readiness tests.
- [x] Implement `readiness` module.
- [x] Add `scan-readiness` CLI subcommand.
- [x] Generate `output/reports/cpo-readiness.md`.
- [x] Run full verification.

## Review

- Starting point: `check-coverage` can evaluate one query/ticker pair, but there is no batch view to compare multiple Serenity candidates and prioritize memo generation.
- Red check: `python3 -m pytest tests/test_readiness.py tests/test_cli.py::test_cli_scan_readiness_writes_report -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.readiness'`.
- Target green check: `python3 -m pytest tests/test_readiness.py tests/test_cli.py::test_cli_scan_readiness_writes_report -q` -> `3 passed in 0.02s`.
- Generated batch readiness report: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-readiness --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out output/reports/cpo-readiness.md --limit 16`.
- Real readiness ranking: `AAOI`, `COHR`, `LITE`, and `AXTI` are `ready`; `NVDA` is `needs_work` due to `missing_risk_coverage`; `SIVE` is `blocked` due to `missing_primary_source`.
- Full verification: `python3 -m pytest tests -q` -> `57 passed in 0.07s`.

# Serenity Alpha Lab Auto Memo Pack Phase

- [x] Create auto memo pack phase plan.
- [x] Add failing auto memo pack tests.
- [x] Implement `memo_pack` module.
- [x] Add `generate-pack` CLI subcommand.
- [x] Generate `output/packs/cpo/index.md`.
- [x] Run full verification.

## Review

- Starting point: readiness scanner identifies ready, needs-work, and blocked tickers, but memo generation is still one ticker at a time and does not automatically skip weak candidates.
- Red check: `python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.memo_pack'`.
- Target green check: `python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q` -> `3 passed in 0.04s`.
- Generated memo pack: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out-dir output/packs/cpo --limit 16`.
- Real pack output: generated formal memos for `AAOI`, `COHR`, `LITE`, and `AXTI`; skipped `NVDA` due to `missing_risk_coverage`; skipped `SIVE` due to `missing_primary_source`.
- Full verification: `python3 -m pytest tests -q` -> `60 passed in 0.17s`.

# Serenity Alpha Lab Acquisition Queue Phase

- [x] Create acquisition queue phase plan.
- [x] Add failing acquisition queue tests.
- [x] Implement `acquisition_queue` module.
- [x] Add `build-acquisition-queue` CLI subcommand.
- [x] Generate `output/reports/cpo-acquisition-queue.md`.
- [x] Run full verification.

## Review

- Starting point: auto memo pack skips `NVDA` and `SIVE` with gap reasons, but those reasons are not yet converted into explicit evidence acquisition tasks.
- Red check: `python3 -m pytest tests/test_acquisition_queue.py tests/test_cli.py::test_cli_build_acquisition_queue_writes_report -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.acquisition_queue'`.
- Target green check: `python3 -m pytest tests/test_acquisition_queue.py tests/test_cli.py::test_cli_build_acquisition_queue_writes_report -q` -> `3 passed in 0.02s`.
- Generated acquisition queue: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-acquisition-queue --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out output/reports/cpo-acquisition-queue.md --limit 16`.
- Real queue output: `NVDA` needs medium-priority risk/invalidation evidence; `SIVE` needs high-priority primary filing/company-release/audited-fact evidence.
- Full verification: `python3 -m pytest tests -q` -> `63 passed in 0.21s`.

# Serenity Alpha Lab Evidence Intake Workflow Phase

- [x] Create evidence intake workflow phase plan.
- [x] Add failing evidence intake workflow tests.
- [x] Implement `evidence_intake` module.
- [x] Add `ingest-task-evidence` CLI subcommand.
- [x] Generate sample intake evidence and refreshed outputs.
- [x] Run full verification.

## Review

- Starting point: acquisition queue identifies what evidence to collect, but the project has no structured intake command to append manually collected evidence and rerun readiness/memo-pack outputs.
- Red check: `python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence_intake'`.
- Refresh defect check: sample intake added `manual:NVDA:risk:cpo-sourcing`, but refreshed readiness still showed `NVDA` as `needs_work` because focus-ticker risk evidence was squeezed out of the top-16 retrieval set by primary facts.
- Retrieval regression red check: `python3 -m pytest tests/test_retrieval.py::test_retrieve_includes_recent_focus_ticker_risk_intake_with_primary_facts -q` failed because the manual NVDA risk item was absent from retrieved results.
- Target green check: `python3 -m pytest tests/test_retrieval.py::test_retrieve_includes_recent_focus_ticker_risk_intake_with_primary_facts tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs -q` -> `5 passed in 0.03s`.
- Generated sample intake evidence: `data/enriched/manual_intake.jsonl` with `manual:NVDA:risk:cpo-sourcing`.
- Generated refreshed readiness report: `output/reports/cpo-readiness-refreshed.md`; `NVDA` moved from `needs_work` to `ready` after the manual risk evidence entered retrieval.
- Generated refreshed memo pack: `output/packs/cpo-refreshed`; now includes `nvda-memo.md` alongside `AAOI`, `AXTI`, `COHR`, and `LITE` memos.
- Full verification: `python3 -m pytest tests -q` -> `68 passed in 0.09s`.

# Serenity Alpha Lab Intake Source Guardrails Phase

- [x] Create intake source guardrails phase plan.
- [x] Add failing source guardrail tests.
- [x] Implement intake source URL validation.
- [x] Verify rejected placeholder intake writes no formal outputs.
- [x] Generate guarded sample outputs.
- [x] Run full verification.

## Review

- Starting point: `ingest-task-evidence` can append evidence and refresh memo packs, but it currently allows placeholder URLs such as `https://example.com/...`, which can promote sample evidence into formal outputs.
- Red check: `python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_placeholder_source_before_refresh tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs -q` failed because `validate_source_url` did not exist.
- Target green check: `python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_placeholder_source_before_refresh tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs -q` -> `7 passed in 0.07s`.
- Placeholder source verification: `ingest-task-evidence` with `https://example.com/nvda-risk` exited non-zero, wrote no intake JSONL, and produced no readiness or pack outputs.
- Guarded intake output: `data/enriched/manual_intake_guarded.jsonl` was written with a non-placeholder SEC URL source.
- Guarded refreshed outputs: `output/reports/cpo-readiness-guarded.md` and `output/packs/cpo-guarded/index.md` were generated; `NVDA` remains `ready` with guarded risk coverage.
- Full verification: `python3 -m pytest tests -q` -> `71 passed in 0.10s`.
- CLI green check: `python3 -m pytest tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q` -> `1 passed in 0.02s`.
- Pulled SEC companyfacts snapshots for `NVDA`, `AAOI`, `LITE`, `COHR`, and `AXTI` from official SEC endpoints into `data/primary/raw/`.
- Reviewer feedback handled:
  - High: FY fact selection could choose quarter-duration rows. Added duration-aware sorting and regression tests.
  - Medium: source paths were CWD-relative. `load_companyfact_specs()` now resolves relative paths against the manifest parent.
  - Medium: revenue fallback facts lost revenue semantics. `RevenueFromContractWithCustomerExcludingAssessedTax` now maps to `revenue` and `demand_certainty`.
  - Medium: manifest CIK was not validated. CLI now passes expected CIK and the connector raises on CIK mismatch.
- Reviewer-fix target verification: `python3 -m pytest tests/test_sec_companyfacts.py tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q` -> `9 passed in 0.04s`.
- Generated SEC primary evidence: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-sec-companyfacts --sources config/sec_companyfacts_sources.json --out data/primary/sec_companyfacts_evidence.jsonl` -> 15 primary fact items.
- Generated combined corpus: `data/enriched/github_plus_primary.jsonl` -> 179 items.
- Generated primary audit: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_plus_primary.jsonl --ticker SIVE --out output/reports/evidence-audit-primary.md`.
- Manifest-relative path verification from outside project root: `PYTHONPATH=/Users/zq/Desktop/ai-projs/posp/agent-test/serenity-alpha-lab/src python3 -m serenity_alpha_lab.cli import-sec-companyfacts --sources /Users/zq/Desktop/ai-projs/posp/agent-test/serenity-alpha-lab/config/sec_companyfacts_sources.json --out /tmp/sec-companyfacts-XXXXXX.jsonl` -> 15 lines.
- Full verification: `python3 -m pytest tests -q` -> `43 passed in 0.13s`.
- Parser green check: `python3 -m pytest tests/test_sec_companyfacts.py -q` -> `3 passed in 0.01s`.
- CLI red check: `python3 -m pytest tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q` failed because `import-sec-companyfacts` routed to memo mode and required `--data` / `--query`.

# Serenity Alpha Lab Source Claim Traceability Phase

- [x] Create source-claim traceability phase plan.
- [x] Add failing traceability guardrail tests.
- [x] Implement source excerpt schema and intake validation.
- [x] Add manual-intake traceability audit flag.
- [x] Regenerate guarded sample outputs with source excerpt.
- [x] Run full verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-source-claim-traceability.md`.
- Red check: `python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh tests/test_evidence_audit.py::test_audit_flags_manual_intake_without_source_excerpt -q` failed with `ImportError: cannot import name 'validate_source_excerpt'`.
- Target green check: `python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs tests/test_evidence_audit.py::test_audit_flags_manual_intake_without_source_excerpt tests/test_evidence_audit.py::test_audit_does_not_flag_manual_intake_with_source_excerpt -q` -> `12 passed in 0.06s`.
- Regenerated guarded intake output: `data/enriched/manual_intake_guarded.jsonl` now has one manual intake row and every row has `source_excerpt`.
- Guarded intake audit check: `audit_evidence(data/enriched/manual_intake_guarded.jsonl, focus_ticker="NVDA")` no longer reports `manual_intake_missing_source_excerpt`; only `source_concentration` remains for the one-row sample file.
- Regenerated guarded readiness and memo pack: `output/reports/cpo-readiness-guarded.md` and `output/packs/cpo-guarded/index.md`.
- Full verification: `python3 -m pytest tests -q` -> `77 passed in 0.11s`.
- Final guarded data check: `guarded_rows=1`, `all_guarded_rows_have_source_excerpt=True`, `guarded_audit_flags=source_concentration`.

# Serenity Alpha Lab SIVE Primary Source Phase

- [x] Confirm SIVE readiness gap and source constraints.
- [x] Acquire official Sivers Semiconductors 2025 Annual Report PDF.
- [x] Extract annual-report text locally with Python PDF tooling.
- [x] Create SIVE primary source implementation plan.
- [x] Add failing official-report importer tests.
- [x] Implement official-report primary evidence importer.
- [x] Generate SIVE official primary evidence.
- [x] Rebuild combined corpus and guarded outputs.
- [x] Run full verification.

## Review

- Starting point: `output/reports/cpo-readiness-guarded.md` shows `SIVE` as `blocked` with `missing_primary_source`.
- Existing SEC companyfacts manifest does not include SIVE; adding fake SEC data would violate source quality.
- Acquired official PDF: `data/primary/raw/sivers_annualreport_2025_final.pdf` from `https://www.sivers-semiconductors.com/wp-content/uploads/2026/05/Sivers_annualreport_2025_final.pdf`.
- Extracted text to `data/primary/raw/sivers_annualreport_2025_final.txt` using available Python PDF tooling.
- Relevant source text found: 2025 annual revenues increased 40% YoY to SEK 307m; net sales were SEK 306.6m; pipeline expanded to co-packaged optics (CPO).
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-sive-primary-source.md`.
- Red check: `python3 -m pytest tests/test_official_report.py tests/test_cli.py::test_cli_import_official_report_writes_primary_evidence_jsonl -q` failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.official_report'`.
- Target green check: `python3 -m pytest tests/test_official_report.py tests/test_cli.py::test_cli_import_official_report_writes_primary_evidence_jsonl -q` -> `4 passed in 0.03s`.
- Imported SIVE official evidence: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-official-report --sources config/official_report_sources.json --out data/primary/sive_official_report_evidence.jsonl` -> 3 primary fact items.
- Rebuilt combined corpus: `data/enriched/github_plus_primary.jsonl` -> 182 items, including 3 SIVE primary/fact items from the official Sivers Semiconductors annual report.
- Regenerated guarded readiness and memo pack: `SIVE` moved from `blocked` / `missing_primary_source` to `ready`; `output/packs/cpo-guarded/index.md` now includes `sive-memo.md`.
- Full verification: `python3 -m pytest tests -q` -> `81 passed in 0.11s`.
- Final SIVE readiness check: `sive_official_items=3`, `sive_official_primary_fact_items=3`, `sive_items_have_source_excerpt=True`, `sive_status=ready`, `sive_flags=none`, `sive_primary_count=3`, `sive_risk_count=6`, `sive_memo_exists=True`.

# Serenity Alpha Lab Memo Traceability Phase

- [x] Review current memo output and evidence schema.
- [x] Create memo traceability implementation plan.
- [x] Add failing memo source-excerpt tests.
- [x] Implement primary evidence source excerpt rendering.
- [x] Regenerate guarded memo pack.
- [x] Run full verification.

## Review

- Starting point: `source_excerpt` is present on primary official-report evidence, but `## Primary Source Evidence` only renders summaries.
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-memo-traceability.md`.
- Red check: `python3 -m pytest tests/test_memo.py::test_generate_memo_includes_source_excerpt_for_primary_evidence tests/test_memo.py::test_generate_memo_keeps_primary_evidence_without_source_excerpt -q` failed because `**Source excerpt:**` was missing from the primary evidence section.
- Target green check: `python3 -m pytest tests/test_memo.py::test_generate_memo_includes_source_excerpt_for_primary_evidence tests/test_memo.py::test_generate_memo_keeps_primary_evidence_without_source_excerpt -q` -> `2 passed in 0.01s`.
- Regenerated guarded memo pack: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out-dir output/packs/cpo-guarded --limit 16`.
- SIVE memo traceability check: `output/packs/cpo-guarded/sive-memo.md` now shows `**Source excerpt:**` lines for all three official-report primary facts.
- Memo target verification: `python3 -m pytest tests/test_memo.py -q` -> `6 passed in 0.01s`.
- Full verification: `python3 -m pytest tests -q` -> `83 passed in 0.10s`.

# Serenity Alpha Lab Evidence Provenance Index Phase

- [x] Review memo pack generation logic and current pack output.
- [x] Create provenance index implementation plan.
- [x] Add failing `sources.md` tests.
- [x] Implement pack-level provenance index rendering.
- [x] Regenerate guarded pack with `sources.md`.
- [x] Run full verification.

## Review

- Starting point: `write_memo_pack()` writes individual memo files and `index.md`, but there is no centralized source/provenance index for primary evidence.
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-provenance-index.md`.
- Red check: `python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q` failed with `ImportError: cannot import name 'render_memo_pack_sources'`.
- Target green check: `python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q` -> `5 passed in 0.04s`.
- Regenerated guarded memo pack: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out-dir output/packs/cpo-guarded --limit 16`.
- Provenance output written: `output/packs/cpo-guarded/sources.md`.
- SIVE provenance check: `sources.md` contains `## SIVE`, `sive-memo.md`, all three `official-report:SIVE:*` primary facts, and `**Source excerpt:**` lines.
- Full verification: `python3 -m pytest tests -q` -> `85 passed in 0.10s`.

# Serenity Alpha Lab Productized Pipeline Phase

- [x] Review project entrypoints, dependencies, and current run workflow.
- [x] Create productized pipeline implementation plan.
- [x] Add failing one-command pipeline test.
- [x] Implement `run-cpo-pack` stable CLI entrypoint.
- [x] Update README with product quick start.
- [x] Regenerate default product outputs.
- [x] Run full verification.

## Review

- Starting point: product outputs are reliable, but users still need to run several lower-level commands manually.
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-productized-pipeline.md`.
- Red check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q` failed because `run-cpo-pack` routed to the base memo parser and required `--data` / `--out`.
- Target green check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q` -> `1 passed in 0.03s`.
- Default product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- Product outputs regenerated: `output/reports/cpo-readiness-guarded.md`, `output/packs/cpo-guarded/index.md`, and `output/packs/cpo-guarded/sources.md`.
- Readiness result: `SIVE`, `AAOI`, `AXTI`, `COHR`, `LITE`, and `NVDA` are all `ready` with no flags.
- SIVE provenance check: `sources.md` contains `## SIVE`, `sive-memo.md`, all three official-report SIVE facts, and `**Source excerpt:**` lines.
- Full verification: `python3 -m pytest tests -q` -> `86 passed in 0.11s`.

# Serenity Alpha Lab Release Hardening Phase

- [x] Review current package metadata, Makefile/docs state, and memo-pack write behavior.
- [x] Create release hardening implementation plan.
- [x] Add failing release hardening tests.
- [x] Add console script, Makefile, and operations guide.
- [x] Clean stale generated memo-pack outputs before writing.
- [x] Run default product command.
- [x] Run full verification.

## Review

- Starting point: `run-cpo-pack` works, but there is no installable console script, Makefile, operations guide, or stale output cleanup.
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-release-hardening.md`.
- Red check: `python3 -m pytest tests/test_release_hardening.py tests/test_memo_pack.py::test_write_memo_pack_removes_stale_generated_memos -q` failed because `[project.scripts]`, `Makefile`, `docs/OPERATIONS.md`, and stale output cleanup were missing.
- Target green check: `python3 -m pytest tests/test_release_hardening.py tests/test_memo_pack.py::test_write_memo_pack_removes_stale_generated_memos -q` -> `4 passed in 0.04s`.
- Release verification: `make verify` -> `90 passed in 0.11s`, then `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`.
- Stale output cleanup check: a temporary `output/packs/cpo-guarded/stale-memo.md` was removed by `make verify`.
- Product outputs present after release run: `output/reports/cpo-readiness-guarded.md`, `output/packs/cpo-guarded/index.md`, and `output/packs/cpo-guarded/sources.md`.
- Readiness result: `SIVE`, `AAOI`, `AXTI`, `COHR`, `LITE`, and `NVDA` are all `ready` with no flags.
- Final full verification: `python3 -m pytest tests -q` -> `90 passed in 0.11s`.

# Serenity Alpha Lab Provenance Usage Map Phase

- [x] Review current `sources.md` renderer and duplicate source output.
- [x] Create provenance usage map implementation plan.
- [x] Add failing provenance usage map tests.
- [x] Implement deduplicated primary evidence usage map.
- [x] Regenerate product outputs.
- [x] Run full verification.

## Review

- Starting point: `sources.md` repeats the same primary evidence under multiple ticker memo sections.
- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-provenance-usage-map.md`.
- Red check: `python3 -m pytest tests/test_memo_pack.py::test_render_memo_pack_sources_lists_primary_evidence_provenance tests/test_memo_pack.py::test_render_memo_pack_sources_deduplicates_shared_evidence_usage -q` failed because `sources.md` had no `## Primary Evidence` section and repeated shared evidence under multiple memo sections.
- Target green check: `python3 -m pytest tests/test_memo_pack.py::test_render_memo_pack_sources_lists_primary_evidence_provenance tests/test_memo_pack.py::test_render_memo_pack_sources_deduplicates_shared_evidence_usage -q` -> `2 passed in 0.03s`.
- Memo pack verification: `python3 -m pytest tests/test_memo_pack.py -q` -> `6 passed in 0.02s`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- Dedupe check: `output/packs/cpo-guarded/sources.md` contains one bullet for `official-report:SIVE:net-sales-2025` and lists `aaoi-memo.md, axti-memo.md, cohr-memo.md, lite-memo.md, nvda-memo.md, sive-memo.md` under `**Used in memos:**`.
- Full verification: `python3 -m pytest tests -q` -> `91 passed in 0.13s`.

# Serenity Alpha Lab Focus Evidence Isolation Phase

- [x] Create focus evidence isolation implementation plan.
- [x] Add failing memo test for cross-ticker primary evidence separation.
- [x] Implement focus primary and sector-context evidence rendering.
- [x] Regenerate product outputs.
- [x] Run full verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-focus-evidence-isolation.md`.
- Red check: `python3 -m pytest tests/test_memo.py::test_generate_memo_separates_cross_ticker_primary_evidence_from_focus_primary_section -q` failed because `## Sector Context Evidence` did not exist.
- Focused green check: `python3 -m pytest tests/test_memo.py -q` -> `7 passed in 0.03s`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- AAOI memo partition check: `official-report:SIVE:net-sales-2025` is absent from `## Primary Source Evidence`, present in `## Sector Context Evidence`, and `## Sector Context Evidence` exists.
- Cross-memo partition check: `AAOI`, `AXTI`, `COHR`, `LITE`, and `NVDA` memos all keep `official-report:SIVE:net-sales-2025` out of their primary section and place it in sector context.
- Full verification: `python3 -m pytest tests -q` -> `92 passed in 0.29s`.

# Serenity Alpha Lab Input Preflight Phase

- [x] Create input preflight implementation plan.
- [x] Add failing run-cpo-pack missing input test.
- [x] Implement required input preflight.
- [x] Regenerate product outputs.
- [x] Run full verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-input-preflight.md`.
- Red check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_fast_when_required_inputs_are_missing -q` failed with raw `FileNotFoundError` from missing base evidence.
- Target green check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_fast_when_required_inputs_are_missing tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q` -> `2 passed in 0.03s`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- Full verification: `python3 -m pytest tests -q` -> `93 passed in 0.11s`.

# Serenity Alpha Lab Doctor Command Phase

- [x] Create doctor command implementation plan.
- [x] Add failing doctor CLI tests.
- [x] Implement doctor command.
- [x] Update user-facing docs.
- [x] Run product verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-doctor.md`.
- Red check: `python3 -m pytest tests/test_cli.py::test_cli_doctor_reports_ok_when_required_inputs_exist tests/test_cli.py::test_cli_doctor_reports_missing_required_inputs -q` failed because `doctor` was not recognized and fell through to the base memo parser.
- Target green check: `python3 -m pytest tests/test_cli.py::test_cli_doctor_reports_ok_when_required_inputs_exist tests/test_cli.py::test_cli_doctor_reports_missing_required_inputs -q` -> `2 passed in 0.03s`.
- Product health check: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor` -> `required inputs: ok`, `optional manual intake: ok`.
- Product run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack` -> `combined 182 evidence items; ready memos 6; skipped 0`.
- Full verification: `python3 -m pytest tests -q` -> `95 passed in 0.11s`.

# Serenity Alpha Lab Verify Doctor Phase

- [x] Create verify doctor implementation plan.
- [x] Add failing release hardening test for Makefile doctor target.
- [x] Add Makefile doctor target and verify dependency.
- [x] Update operations docs.
- [x] Run release verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-verify-doctor.md`.
- Red check: `python3 -m pytest tests/test_release_hardening.py::test_release_makefile_exposes_standard_targets -q` failed because `Makefile` did not expose a `doctor` target.
- Target green check: `python3 -m pytest tests/test_release_hardening.py::test_release_makefile_exposes_standard_targets -q` -> `1 passed in 0.01s`.
- Release verification: `make verify` now runs tests, `doctor`, and `run-cpo-pack`; result was `95 passed`, `required inputs: ok`, `optional manual intake: ok`, and `combined 182 evidence items; ready memos 6; skipped 0`.
- Final full verification: `python3 -m pytest tests -q` -> `95 passed in 0.11s`.

# Serenity Alpha Lab Pack Quality Gate Phase

- [x] Create pack quality gate implementation plan.
- [x] Add failing skipped-memo quality gate test.
- [x] Implement run-cpo-pack skipped candidate gate.
- [x] Run release verification.
- [x] Record review.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-pack-quality-gate.md`.
- Red check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_when_candidates_are_skipped_without_override -q` failed because `run-cpo-pack` returned `0` even when `AAOI` was skipped.
- Target green check: `python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_fails_when_candidates_are_skipped_without_override tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q` -> `2 passed in 0.04s`.
- Release verification: `make verify` -> `96 passed`, `doctor` reported required inputs ok, and `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`.
- Final full verification: `python3 -m pytest tests -q` -> `96 passed in 0.11s`.

# Serenity Alpha Lab Release Artifacts Phase

- [x] Create release artifacts implementation plan.
- [x] Add failing release artifact tests.
- [x] Create changelog, release checklist, and CI workflow.
- [x] Update README release links.
- [x] Run release verification.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-release-artifacts.md`.
- Red check: `python3 -m pytest tests/test_release_hardening.py -q` failed because `CHANGELOG.md`, `docs/RELEASE_CHECKLIST.md`, and `.github/workflows/verify.yml` did not exist.
- Target green check: `python3 -m pytest tests/test_release_hardening.py -q` -> `6 passed in 0.02s`.
- Release verification: `make verify` -> `99 passed`, `doctor` reported required inputs ok, and `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`.
- Final full verification: `python3 -m pytest tests -q` -> `99 passed in 0.19s`.

# Serenity Alpha Lab Install Smoke Phase

- [x] Create install smoke implementation plan.
- [x] Add failing install and smoke tests.
- [x] Create install docs and smoke target.
- [x] Run smoke and release verification.
- [x] Record review.

## Review

- Plan saved to `docs/superpowers/plans/2026-07-04-serenity-alpha-lab-install-smoke.md`.
- Red check: `python3 -m pytest tests/test_release_hardening.py -q` failed because `INSTALL.md`, `make smoke`, and CI smoke coverage were missing.
- First install verification exposed a packaging issue: `python3 -m pip install -e .` failed because the project lacked a compatible editable-install backend for the local pip/setuptools combination.
- Packaging fix: added `setuptools.build_meta`, src-layout package discovery, and a minimal `setup.py` compatibility shim for legacy editable installs.
- Target green check: `python3 -m pytest tests/test_release_hardening.py -q` -> `8 passed in 0.04s`.
- Editable install verification: `python3 -m pip install -e .` installed `serenity-alpha-lab-0.1.0` successfully.
- Installed smoke verification: `make smoke` ran the installed console script, `doctor` reported required inputs ok, and `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`.
- Release verification: `make verify` -> `101 passed`, `doctor` reported required inputs ok, and `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`.
- Final full verification: `python3 -m pytest tests -q` -> `101 passed in 0.24s`.

# Serenity Alpha Lab Deliverable Evidence Traceability Phase

- [x] Add failing tests for deliverable report source traceability.
- [x] Pass parsed primary sources into deliverable report generation.
- [x] Render a concise key-source evidence section in Chinese deliverables.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Record review evidence and reusable lesson.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because `deliverable-research-report.md` did not contain `## 关键来源与证据`.
- Implementation: passed parsed primary sources into deliverable report generation and rendered source title, source id, memo usage, claim, and source excerpt in the deliverable Markdown.
- Edge handling: reports without parsed primary sources keep a visible empty state instead of fabricating source evidence.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_build_dashboard_writes_static_html tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.64s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.21s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.35s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files.
- Local smoke: restarted `serve-ui` on port `8767`, regenerated `HBM`, and verified `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all return `200`; the HBM deliverable now contains `## 关键来源与证据` and source rows.

# Serenity Alpha Lab Handoff Bundle Copy Phase

- [x] Add failing tests for one-click delivery package handoff copy.
- [x] Add bilingual copy for the handoff bundle action and copied state.
- [x] Generate a concise handoff checklist from delivery package artifacts.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because the delivery package did not expose `Copy handoff bundle` / `复制交接清单`, `copyHandoffBundle`, or per-artifact handoff metadata.
- Implementation: the delivery package now includes a one-click handoff bundle button, localized copied state, and `data-handoff-artifact-title` / `data-handoff-artifact-href` metadata for each asset.
- UI behavior: `copyHandoffBundle()` builds a concise checklist with absolute URLs for the deliverable report, analysis manifest, coverage matrix, and evidence acquisition queue, then copies it to the clipboard.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.61s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.21s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.46s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `99597`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md`, `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` all returned HTTP 200; generated Chinese and English pages include the one-click handoff bundle controls.

# Serenity Alpha Lab Reader Toolbar Phase

- [x] Add failing tests for a right-side reader toolbar.
- [x] Add bilingual copy for current report link, copy current link, and open full page actions.
- [x] Render reader toolbar state when a report opens in the drawer.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because the right-side report reader did not expose a toolbar, current report link, copy-current-link action, or open-full-page action.
- Implementation: the report drawer now includes a localized toolbar with current report URL, `copyCurrentReaderLink()`, and `openCurrentReaderReport()`; opening a report updates the toolbar with an absolute URL and closing the drawer clears the state.
- UI behavior: users can open any report in the right-side reader, copy the exact current report link from inside the drawer, or jump to the full page without returning to the report card.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.71s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.32s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.68s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `53724`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200; homepage and HBM analysis page both include the reader toolbar controls.

# Serenity Alpha Lab Delivery Package Panel Phase

- [x] Add failing tests for a consolidated report delivery package panel.
- [x] Add bilingual copy for delivery package actions and reader shortcuts.
- [x] Render report, manifest, coverage matrix, and evidence queue shortcuts in one compact panel.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because generated dashboards did not expose a consolidated `Report Delivery Package` / `报告交付包` panel or artifact shortcuts for deliverable, manifest, coverage matrix, and evidence queue.
- Implementation: dashboards now render a compact `delivery-package` panel below the deliverable report section, with reader-open and copy-link actions for the deliverable report, `analysis-manifest.json`, coverage matrix, and evidence acquisition queue.
- UI behavior: each artifact card carries a stable `data-package-artifact` key, opens in the existing right-side report drawer, and reuses `copyShareLink()` for shareable absolute URLs.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.81s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.51s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 3.04s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `44900`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, `/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md`, `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200; the generated Chinese HBM page includes the delivery package and all four artifact shortcuts.

# Serenity Alpha Lab Share Handoff Controls Phase

- [x] Add failing tests for report and manifest share handoff controls.
- [x] Add bilingual copy for share handoff, copy report link, and copy manifest link actions.
- [x] Render compact share controls beside deliverable and operational report actions.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because generated dashboards did not expose `Share handoff` / `分享交接`, copy report/manifest actions, `copyShareLink`, or `data-share-href` targets.
- Implementation: deliverable reports now show a compact `Share handoff` / `分享交接` row with copy-report and copy-manifest buttons; operational report cards now include copy-link actions, using `Copy manifest link` for `analysis-manifest.json`.
- UI behavior: `copyShareLink()` resolves relative report hrefs against the current analysis URL, writes the absolute URL to the clipboard when available, and gives immediate localized copied feedback.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.73s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.35s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.77s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `13156`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md` all returned HTTP 200; the generated Chinese HBM page includes `分享交接`, `复制报告链接`, `复制清单链接`, and the expected share hrefs.

# Serenity Alpha Lab Evidence Playbook Phase

- [x] Add failing tests for evidence acquisition playbook fields.
- [x] Add rationale, acceptance criteria, and after-import actions to acquisition tasks.
- [x] Render playbook fields in Markdown acquisition queues and UI task cards.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke the generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_acquisition_queue.py tests/test_cli.py::test_cli_build_acquisition_queue_writes_report tests/test_ui.py::test_render_dashboard_html_localizes_visible_evidence_tasks tests/test_ui.py::test_build_dashboard_surfaces_acquisition_queue_tasks tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because acquisition tasks lacked playbook fields and UI cards did not show `补证原因`, `验收标准`, or `导入后动作`.
- Implementation: acquisition tasks now carry `rationale`, `acceptance_criteria`, and `after_import`; Markdown queues include `Why It Matters`, `Acceptance Criteria`, and `After Import`, localized as `补证原因`, `验收标准`, and `导入后动作`.
- UI behavior: task cards render the playbook block when tasks exist, while empty queues retain a clean empty state instead of showing irrelevant next-action text.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_acquisition_queue.py tests/test_cli.py::test_cli_build_acquisition_queue_writes_report tests/test_ui.py::test_render_dashboard_html_localizes_visible_evidence_tasks tests/test_ui.py::test_build_dashboard_surfaces_acquisition_queue_tasks tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `7 passed in 0.75s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_acquisition_queue.py tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `22 passed in 2.40s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.86s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` all return `200`; the HBM queue has the playbook columns and correctly shows the no-task empty state.

# Serenity Alpha Lab Evidence Import Feedback Loop Phase

- [x] Add failing tests for closed-loop import feedback.
- [x] Render imported evidence impact in task history and success banners.
- [x] Show closed gap, quality gate impact, and remaining evidence work after import.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task tests/test_ui.py::test_build_dashboard_loads_manual_intake_history_for_analysis_page tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because imported evidence history and success banners did not show `Import Impact` / `导入影响`.
- Implementation: imported evidence history and `/ingest-evidence` success banners now show the closed gap, quality gate impact, and remaining evidence work in English and Chinese.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task tests/test_ui.py::test_build_dashboard_loads_manual_intake_history_for_analysis_page tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed in 0.78s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.19s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.41s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767`.
- Local smoke: `/index.zh.html`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` all return `200`; HBM currently has no pending evidence tasks, so no import form is expected on that page, while the queue still exposes playbook headers.

# Serenity Alpha Lab Evidence Quality Delta Phase

- [x] Add failing tests for import quality before/after feedback.
- [x] Capture current report quality score in evidence import forms.
- [x] Render before score, after score, and quality score delta in import feedback.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task tests/test_ui.py::test_build_dashboard_loads_manual_intake_history_for_analysis_page tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because evidence import feedback did not show quality before import, quality after import, or quality score change.
- Implementation: report quality scoring is now captured once as a page-level snapshot, passed into evidence import forms as hidden `quality_before_score` / `quality_before_status` fields, and reused by the import success banner.
- UI behavior: imported evidence history shows localized unavailable states when no reliable baseline exists; `/ingest-evidence` success feedback shows before score, after score parsed from the regenerated report, and the score delta when both sides are available.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task tests/test_ui.py::test_build_dashboard_loads_manual_intake_history_for_analysis_page tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `3 passed in 0.61s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.19s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.35s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `73712`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` all returned HTTP 200.

# Serenity Alpha Lab Analysis Manifest Phase

- [x] Add failing tests for per-analysis manifest artifacts.
- [x] Generate `analysis-manifest.json` alongside each analysis dashboard.
- [x] Include input resolution, candidate tickers, quality snapshot, report links, and research-only boundary.
- [x] Link the manifest from the UI report workbench.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because generated analyses did not create `analysis-manifest.json` and the UI did not expose an analysis manifest link.
- Implementation: each generated analysis now writes `analysis-manifest.json` with query, language, intent, canonical theme, expanded query, candidate tickers, quality score/status, report links, and `research_only: true`.
- UI behavior: the manifest is now loaded as an operational report and surfaced as `Analysis Manifest` / `分析清单` with a reader action alongside deliverable, coverage matrix, and evidence acquisition reports.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_cli.py::test_cli_serve_ui_builds_dashboard_and_invokes_server tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.66s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.19s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.35s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `20908`.
- Local smoke: `/index.zh.html`, `/index.html`, `/api/resolve-topic?query=存储芯片&language=zh`, `/analyze?query=HBM&language=zh`, `/analyses/hbm-6f259a8f14/index.zh.html`, `/analyses/hbm-6f259a8f14/analysis-manifest.json`, and `/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md` all returned HTTP 200.

# Serenity Alpha Lab Run Manifest Summary Phase

- [x] Add failing tests for run history manifest summaries.
- [x] Persist manifest href, candidate tickers, canonical theme, and quality snapshot into completed run records.
- [x] Render quality and candidate summary in the Run Center history.
- [x] Add a Run Center action to open the analysis manifest.
- [x] Run focused UI/E2E tests and full release verification.
- [x] Refresh local bilingual UI and smoke generated product paths.

## Review

- Red check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` failed because Run Center history did not show manifest-backed quality/candidate summaries and `/api/runs` did not include `manifest_href`.
- Implementation: completed run records now read the generated `analysis-manifest.json` and persist manifest href, canonical theme, candidate tickers, quality score, and quality status into `runs.json`.
- UI behavior: Run Center history now renders quality score/status and candidate tickers/canonical theme, and includes an `Open analysis manifest` / `打开分析清单` action.
- Target green check: `PYTHONPATH=src python3 -m pytest tests/test_ui.py::test_render_dashboard_html_contains_product_sections tests/test_ui_http_e2e.py::test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets -q` -> `2 passed in 0.72s`.
- UI/E2E verification: `PYTHONPATH=src python3 -m pytest tests/test_ui.py tests/test_ui_http_e2e.py -q` -> `19 passed in 2.34s`.
- Full verification: `PYTHONPATH=src python3 -m pytest tests -q` -> `153 passed in 2.76s`.
- Release verification: `make verify` -> `153 passed`, `doctor` reported required inputs ok, `run-cpo-pack` generated `combined 182 evidence items; ready memos 6; skipped 0`, and the coverage matrix rebuilt.
- Product refresh: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both` rebuilt English and Chinese UI files; `serve-ui` restarted on port `8767` with server PID `56434`.
- Local smoke: `/index.zh.html`, `/index.html`, `/analyze?query=HBM&language=zh`, `/api/runs`, `/analyses/hbm-6f259a8f14/index.zh.html`, and `/analyses/hbm-6f259a8f14/analysis-manifest.json` all returned HTTP 200; `/api/runs` includes manifest href, candidate tickers, quality score, and quality status.
# DSA-First Serenity Core Development Plan Phase

- [x] Review project lessons and current task-management requirements.
- [x] Inspect current Serenity Alpha Lab architecture and reusable core boundaries.
- [x] Research public and local `daily_stock_analysis` project structure.
- [x] Re-anchor final conclusions to `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis`.
- [x] Write a detailed development plan under `docs/`.
- [x] Validate markdown references and repository diff.

## Review

- User goal: make `daily_stock_analysis` the primary product while using Serenity Alpha Lab as the auxiliary investment-research evidence system.
- Architecture decision: preserve DSA as Web/API/Desktop/Bot/market-data/notification/portfolio/backtest shell; integrate Serenity as a narrow evidence-quality, readiness, audit, and evidence-gap layer.
- Research correction: the final plan uses the local DSA path `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis` as implementation evidence rather than relying only on the temporary public clone.
- Deliverable: added `docs/dsa-first-serenity-core-development-plan.md` with phased architecture, file-level integration points, contracts, tasks, risks, and verification matrix.
- Validation: placeholder scan, heading scan, referenced local-path existence check, and `git diff --check` passed; the new docs file is untracked until staged.

# DSA-First Serenity Core Plan Hardening Phase

- [x] Review `writing-plans` guidance and existing development plan.
- [x] Run focused read-only review for engineering completeness gaps.
- [x] Run focused read-only review for DSA/Serenity product architecture gaps.
- [x] Inspect DSA schema, Agent registry, and intelligence persistence anchors.
- [x] Expand the development plan with code-boundary, data-contract, migration, config, failure, observability, compliance, and Definition of Done details.
- [x] Validate updated markdown, placeholder scan, referenced paths, and diff.

## Review

- User goal: further improve the DSA-first Serenity Core plan with best-practice implementation details for each part.
- Hardening focus: added import direction rules, allowed/forbidden call sites, packaging choices, phase gates, nested API contracts, `dsa://` provenance, failure taxonomy, config table, deployment defaults, observability, compliance copy, and phase-level Definition of Done.
- Product boundary reinforced: DSA keeps trading semantics and product shell; Serenity-generated surfaces only describe research evidence quality and follow-up research tasks.
- Validation: updated plan headings, new-document placeholder scan, referenced DSA/Serenity path checks, and `git diff --check` passed; historical `tasks/todo.md` text still contains older review wording outside this task.
