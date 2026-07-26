# SAL-P5-005 Quant Evidence Adapter Plan

> Scope: Convert already-produced Screen, Factor, Backtest and Risk DTOs into P5 `EvidenceRecord` plus deterministic citation metadata. This task must not run Qlib, compute backtests, call Providers/LLMs, start Worker loops, persist to Evidence Store, render reports or promote formal portfolio backtests.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P5 evidence docs, Source Trust doc, current Git state and relevant quant/application DTOs.
- [x] Finalize `SAL-P5-004` hash-anchor cleanup before starting new implementation; latest prior final anchor is `a724fdb8 docs: 固化 SAL-P5-004 hash-anchor checkpoint`.
- [x] Attempt read-only subagent scope review; wrapper rejected payloads (`reasoning_effort must not be empty`, then `Provide either message or items`), so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Red: add `tests/evidence/test_quant_evidence_adapter.py` proving Screen, Factor, Backtest Metrics and Risk outputs become valid `EvidenceRecord` rows with concrete dataset versions, artifact hashes, formula versions and deterministic citation paths.
- [x] Green: add `src/serenity_alpha_lab/evidence/quant_adapter.py` with a pure offline adapter, canonical body hashing and citation extraction; do not persist evidence or read artifact bodies.
- [x] Export adapter types from `src/serenity_alpha_lab/evidence/__init__.py`.
- [x] Add architecture guard showing `evidence.quant_adapter` remains free of Provider/LLM/Agent/Worker/Qlib/SQLAlchemy/FastAPI/runtime imports.
- [x] Add `docs/quant-evidence-adapter.md` with mapping table, numeric/unit/formula policy, non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-005` done, P5 `5/18`, total `93/129`, new DEC/AEV rows and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-006`; implementation checkpoint `890ac789 feat(P5): 实现 Quant Evidence Adapter` backfilled after checkpoint commit.
- [x] Run focused adapter tests, related Evidence/Schema/Bundle/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, stage only `SAL-P5-005` files and create required Chinese checkpoint commit, then status/hash-anchor docs commit.

## File Targets

- Create: `src/serenity_alpha_lab/evidence/quant_adapter.py` for offline DTO-to-evidence mapping.
- Create: `tests/evidence/test_quant_evidence_adapter.py` for Red/Green contract coverage.
- Modify: `src/serenity_alpha_lab/evidence/__init__.py` to export public adapter symbols.
- Modify: `tests/architecture/test_architecture_boundaries.py` to lock runtime-free imports.
- Create: `docs/quant-evidence-adapter.md` for SAL-P5-005 evidence record.
- Modify: `docs/development-status.md` and `docs/development-progress-checklist.md` only during task status sync.

## Scope Guard

- Adapter consumes caller-provided, already-computed DTOs or DTO-like objects with `to_record()`; it never calls `evaluate_factor()`, Qlib, Provider SDKs, LLMs, databases, worker loops or report renderers.
- Evidence content hash is deterministic canonical JSON, or the supplied `ArtifactManifest` SHA-256 when the manifest represents the same body artifact.
- `dataset_versions` must remain concrete `dsv_*` values and are passed through to `EvidenceRecord`; `latest` must be rejected by the existing schema validator.
- Formal backtest evidence is limited to Gate G4-approved formal kinds; Screen/Factor outputs stay in screening/factor scopes and cannot be relabeled as formal portfolio backtest output.
- Numeric citations must include deterministic field paths, units and formula versions so later LLM stages can cite, not recompute, returns, risk, drawdown, cost, factor and score values.


## Review Notes

- Red target: `1 error`, missing `serenity_alpha_lab.evidence.quant_adapter`.
- Audit extension Red target: `1 failed, 2 passed`, missing `from_backtest_bias_audit_report`.
- Focused target: `3 passed`.
- Related QuantEvidenceAdapter / Evidence schema / SourceTrust / EvidenceStore / EvidenceBundle / Architecture suite: `37 passed`.
- Full pytest: `427 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Local senior review confirmed `evidence.quant_adapter` imports only stdlib plus P5 evidence schema, requires caller-provided ArtifactManifest, never reads artifact bodies, never writes Evidence Store, and performs no Provider/LLM/Worker/Qlib/FastAPI/SQLAlchemy/DSA runtime work.

- Status sync checkpoint: `c539c7b9 docs: 同步 SAL-P5-005 checkpoint hash`; SAL-P5-005 hash-anchor checkpoint `6b101e0f docs: 记录 SAL-P5-005 状态同步 hash` records this status-sync hash.
