# SAL-P5-013 Citation Validator Implementation Plan

> Scope: Complete only `SAL-P5-013` by adding an offline Citation Validator for ResearchReport / ResearchClaim / ReportCitation graphs. The validator must check evidence existence, mandatory citations, value/unit/formula/dataset/run/stage/artifact consistency, decision-time availability and one-attempt repair degradation. Do not jump to report rendering or later P5 tasks. Do not start real Provider/LLM calls, Worker loops, Qlib runtime, production scheduling, report generation or formal backtest promotion.

## Checklist

- [x] Re-read required project docs and confirm `git status --short --branch` / `git log -8 --oneline`.
- [x] Attempt scoped subagent exploration; fallback locally if the wrapper rejects dispatch.
- [x] Create `docs/superpowers/plans/2026-07-28-citation-validator.md`.
- [x] Write Red tests in `tests/evidence/test_citation_validator.py`.
- [x] Run Red focused test and confirm failure for missing `serenity_alpha_lab.evidence.citation_validator`.
- [x] Implement `src/serenity_alpha_lab/evidence/citation_validator.py` as an offline validator.
- [x] Export public symbols from `src/serenity_alpha_lab/evidence/__init__.py`.
- [x] Add architecture guard proving Citation Validator stays offline and runtime-free.
- [x] Add `docs/citation-validator.md`.
- [x] Run focused, related and full verification.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, evidence/risk/decision records, this review section and next startup prompt.
- [x] Create Chinese checkpoint commit for `SAL-P5-013`.

## Current State

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 passed; G5 not passed.
- Completed entering task: `SAL-P5-001..012`.
- Current READY task: `SAL-P5-013` Citation Validator.
- Implementation checkpoint entering task: `83ae4310 feat(P5): 实现模型路由缓存与预算`.
- Latest status-sync checkpoint entering task: `a3224012 docs: 同步 SAL-P5-012 checkpoint hash`.
- Latest status-sync hash-anchor entering task: `a7ab1a52 docs: 记录 SAL-P5-012 状态同步 hash`.
- Latest status review checkpoint entering task: `ac89ccee docs: 复核 SAL-P5-012 最新开发状态与恢复提示`.
- Latest status review hash-anchor entering task: `22014b23 docs: 记录 SAL-P5-012 状态复核 hash`.
- Latest final anchor entering task: `46c78732 docs: 固化 SAL-P5-012 状态复核 hash-anchor`.

## Implementation Notes

- New module should be pure offline evidence logic under `serenity_alpha_lab.evidence`: no Provider SDK, no LiteLLM, no Worker, no SQLAlchemy, no Qlib, no FastAPI, no DSA runtime, no report renderer and no Evidence body reads.
- `CitationValidator` should consume already-constructed `ResearchReport`, `ResearchClaim`, `ReportCitation` and `EvidenceRecord` schema objects.
- Required-citation claims: `numeric_metric`, `temporal_fact`, `risk_gate` and `lineage_fact`; numeric/ratio/price-target values remain `numeric_metric`.
- Numeric claims must keep `deterministic_evidence`; claim value, unit, formula version, dataset versions, run id, stage id and artifact hash must match cited deterministic citations.
- Temporal/directional/value-bearing claims must match cited value when both claim and citation expose a value.
- Citations must point to included evidence and preserve dataset/run/stage/artifact lineage; cited evidence must be available no later than report `decision_time`.
- The repair flow is exactly one caller-supplied repaired report attempt. If a claim still fails after that attempt, remove it from the validated report and downgrade the report level; failed claims must not remain `verified`.
- Keep markdown/HTML report rendering out of scope; `ResearchReport` remains the authority.

## Planned Verification

- Red target: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q`.
- Focused target after implementation: same command should pass.
- Architecture guard: Citation Validator imports only Python stdlib and `serenity_alpha_lab.evidence.schema`.
- Related suite: Citation Validator + Evidence schema + Quant Evidence Adapter + Technical/Intel/RiskPortfolio/Decision adapters + architecture tests.
- Full suite: `uv run --extra core --extra dev python -m pytest -q`, compileall, dependency lock, immutable upstream tag, `git diff --check`.

## Review

- Subagent review fallback: scoped subagent dispatch was attempted for SAL-P5-013 review, but wrapper payload validation rejected the dispatch attempts. Per the project lesson from SAL-P4-006, stopped retries and used local senior review plus fresh verification.
- Red: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.citation_validator'`.
- Initial Green: focused target passed with `3 passed`; local review then found a sharper lineage gap where citation/evidence mismatches were not attached to consuming claims.
- Regression Red: added `test_citation_validator_marks_claim_failed_when_citation_disagrees_with_evidence_lineage`; focused target failed with `IndexError: tuple index out of range` because `failed_claims` was empty.
- Regression Green: propagated broken-citation issues to each consuming claim and deduplicated downgrade warning codes; focused target passed.
- Local robustness review: added low-level invalid report graph checks for missing cited evidence and future-dated evidence, then changed report/claim copying to avoid re-triggering schema validation before issues can be returned.
- Focused target: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` -> `7 passed`.
- Architecture guard: `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_citation_validator_stays_offline_and_runtime_free -q` -> `1 passed`.
- Related P5 suite: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/architecture/test_architecture_boundaries.py -q` -> `59 passed`.
- Full suite: `uv run --extra core --extra dev python -m pytest -q` -> `474 passed, 3 skipped`.
- Compile: `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS.
- Dependency lock: `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages`.
- Immutable upstream tag: `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Diff hygiene: `git diff --check` -> PASS.
- Implementation checkpoint: `dfd82553 feat(P5): 实现 Citation Validator`.
- Status-sync checkpoint: `a64145ac docs: 同步 SAL-P5-013 checkpoint hash`.
- Status-sync hash-anchor checkpoint: `1d421656 docs: 记录 SAL-P5-013 状态同步 hash`.
- Status-sync final anchor checkpoint: `1326b033 docs: 固化 SAL-P5-013 状态同步 hash-anchor`.
- Final anchor record checkpoint: `84424467 docs: 记录 SAL-P5-013 最终锚点`.
## Status Review 2026-07-28

- [x] Re-read current status and git anchors after `SAL-P5-013` final anchor.
- [x] Update `tasks/lessons.md` for the repeated phase-completion status-sync reminder.
- [x] Update recovery state to show `SAL-P5-014` as the next READY task.
- [x] Create Chinese status review checkpoint for `SAL-P5-013`.
- Status review checkpoint: `acceebab docs: 复核 SAL-P5-013 最新开发状态与恢复提示`.
- Status review hash-anchor checkpoint: this `docs: 记录 SAL-P5-013 状态复核 hash` commit will generate it.
- Review: current clean checkpoint entering this review was `84424467 docs: 记录 SAL-P5-013 最终锚点`; no implementation code changed; no Agent tool security, report rendering, real Provider/LLM, Worker, Qlib runtime, production scheduling or formal portfolio backtest was started.
