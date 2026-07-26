# SAL-P5-001 Evidence / Claim / Report Schema Plan

> Scope: Define the versioned P5 evidence, citation, claim and report schema boundary. This task may map P3 Screen/Factor and P4 formal backtest records into referenceable schema kinds, but it must not start Evidence Agent, real Provider/LLM calls, Worker loop, Qlib runtime, production scheduling or report generation.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, Gate G0/G2/G3/G4 records, P3/P4 evidence docs, ADR-009, current Git status and recent commits.
- [x] Confirm current branch and checkpoints: `codex/p0-baseline-status` is clean, ahead of origin, and latest log starts with `4fc665f2`, `f7fc3c80`, `1466c11c`, `e2e6ef9d`, `8f3cfb79`, `6e8bb74a`, `52830c20`, `70303f8f`.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-evidence-claim-report-schema.md`.
- [x] Red: add `tests/evidence/test_evidence_schema_contract.py` that fails while the P5 evidence schema module is missing.
- [x] Green: add `src/serenity_alpha_lab/evidence/schema.py` with Evidence, Citation, Claim, Report and JSON Schema contracts.
- [x] Update `src/serenity_alpha_lab/evidence/__init__.py` exports.
- [x] Add `docs/evidence-claim-report-schema.md` with schema semantics, P3/P4 source mapping and strict LLM/legacy naming guardrails.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-001` done, P5 `1/18`, total `89/129`, `AEV-089`, `DEC-087` and P5 next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint placeholders, completion range and next startup prompt for `SAL-P5-002`.
- [x] Run focused evidence tests, related architecture tests, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, record subagent fallback, stage only `SAL-P5-001` files and create required Chinese checkpoint commit.

## Scope Guard

- Evidence may reference ScreenSnapshot, Factor Evaluation, BacktestRun summary, BacktestArtifactBundle, RiskPolicyResult, BacktestBiasAuditReport, BacktestPerformanceMetricReport, Formal Backtest API records and Quant Lab lineage.
- Evidence/Claim schema must keep Signal Evaluation, Factor Evaluation, Screen result and formal Portfolio Backtest as separate evaluation semantics.
- Claim must declare citation IDs and verification status; quantitative claims must also declare unit, formula version, Dataset Version, Run/Stage/Event and Artifact hash when applicable.
- LLM-authored claims may summarize or narrate cited facts, but must not compute or rewrite returns, risk, drawdown, cost, orders, ledger state or deterministic gate outcomes.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion artifacts must not be named as formal portfolio backtest output.
- This task must not implement Evidence Store persistence, EvidenceBundle Builder, Quant Evidence Adapter, Citation Validator, Agent stage execution, model routing, renderer, UI or notification outbox.

## Review Notes

- Started 2026-07-26 from a clean working tree after `SAL-P4-022` final handoff anchors.
- Subagent dispatch attempted once with full payload and once with minimal payload; both were rejected by host wrapper optional-field validation (`reasoning_effort must not be empty`). Per `tasks/lessons.md`, fallback is local senior review plus fresh verification.
- Red target: `1 error`, missing `serenity_alpha_lab.evidence.schema`.
- Green focused target: `5 passed`.
- Related Evidence/Architecture suite: `20 passed`.
- Full pytest: `410 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Local senior review confirmed `evidence.schema` imports only stdlib + Pydantic, preserves P3/P4 evidence scope separation, rejects `latest`, rejects ScreenSnapshot as formal portfolio backtest evidence, and does not start Evidence Agent, Provider/LLM, Worker loop or Qlib runtime.
- Implementation checkpoint: `25f6ed45 feat(P5): 定义 Evidence Claim Report Schema`.
- Status-sync checkpoint: `539b4652 docs: 同步 SAL-P5-001 checkpoint hash`.
