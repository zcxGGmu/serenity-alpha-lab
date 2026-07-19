# ADR-002: Progressive Modularization and Compatibility Facade

> Status: Approved<br>
> Date: 2026-07-20<br>
> Related tasks: `SAL-P1-001`, `SAL-P1-004`, `SAL-P1-008`, `SAL-P1-009`, `SAL-P1-012`, `SAL-P1-016`<br>
> Review by: Gate G1 or 2026-08-03, whichever comes first

## Context

DSA is the Serenity product trunk for API, Web, Desktop, Agent, reports, notifications, providers, and existing regression tests. It is not the long-term quantitative core. The development plan requires a staged architecture: keep DSA behavior stable, introduce domain protocols and repositories, then migrate high-risk capabilities behind adapters.

The current repo has frozen P0 behavior but has not merged the DSA runtime source into the working tree. P1 must approve the target modularization rules before source import, dependency hardening, architecture tests, or compatibility wrappers begin.

## Decision

Serenity Alpha Lab will modularize DSA progressively inside one repository before splitting services.

The Compatibility Facade is the only approved bridge between new Serenity modules and legacy DSA implementation during migration. New code must not create second, hidden entry points into legacy DSA services. If a legacy path is still needed, it must be reached through an explicit facade or adapter with characterization tests.

After controlled DSA source import is approved by the relevant P1 implementation task, the target layout is:

```text
src/
  domain/
  application/
  quant/
    factors/
    screening/
    backtest/
    portfolio/
    risk/
  datasets/
  evidence/
  integrations/
    alphasift/
    qlib/
    openbb/
    data/
  repositories/
  services/
workers/
migrations/
prompts/
strategies/
tests/
  characterization/
  contract/
  golden/
  e2e/
infra/
  docker/
  observability/
  sbom/
docs/
  adr/
  architecture/
  migrations/
  runbooks/
```

`src/services` remains a legacy and thin-service area during migration. It must not receive new cross-domain business logic unless an ADR or task explicitly approves it.

## Boundary Rules

1. `domain` must not import FastAPI, SQLAlchemy, Pandas, Qlib, AKShare, LiteLLM, DSA service classes, or infrastructure clients.
2. `application` may orchestrate use cases and ports, but must not contain provider-specific parsing, factor math, or report rendering side effects.
3. `integrations` depends on domain protocols and external libraries; domain must not depend on integrations.
4. `quant` must not depend on Agent, report notification, or UI modules.
5. `datasets` owns Dataset Version, PIT metadata, manifests, and quality gates.
6. `evidence` owns source references, citations, evidence bundles, and validation records.
7. API routes perform validation, auth, and use-case dispatch only.
8. Workers invoke application use cases and must receive persisted `run_id` or `stage_id` context before doing durable work.
9. External DataFrames must be converted at adapter boundaries into versioned internal DTOs or Arrow-compatible artifacts with schema metadata.
10. Any exception to these rules requires either a compatibility facade entry or a follow-up architecture decision.

## Facade Scope

The initial facades approved by this ADR are:

| Facade | Legacy surface it protects | Follow-up task |
|---|---|---|
| `TaskBackend` | DSA `AnalysisTaskQueue` and in-process executor assumptions | `SAL-P1-008` |
| `ResearchOrchestrator` | DSA Agent orchestrator, report generation entry points, and model routing | `SAL-P1-009` |
| `StorageMigrationFacade` | DSA `src/storage.py` schema creation and manual migration behavior | `SAL-P1-012`, `SAL-P1-013` |
| `ConfigProfileFacade` | Existing config registry, `.env`, desktop/standalone/ci runtime profiles | `SAL-P1-014` |
| `ProviderCompatibilityFacade` | Existing DSA provider manager and Pandas-shaped outputs | `SAL-P2-002` |
| `SignalEvaluationFacade` | Existing DSA signal outcome evaluation that is not formal portfolio backtesting | `SAL-P4-001` |

These facades preserve current behavior first. Replacement implementations may be introduced only after characterization or contract tests lock the old behavior.

## Service Split Conditions

No microservice split is approved in P1. A capability may move to a separate worker or service only when all conditions below are met:

1. A stable protocol and contract test suite exists.
2. Data ownership and idempotency rules are explicit.
3. Failure and retry semantics are represented in `Run`, `Stage`, `Event`, or equivalent durable state.
4. Local desktop mode still has an in-process or offline-compatible implementation.
5. The split solves a measured resource, dependency, security, or isolation problem.
6. Rollback can route traffic back through the facade without data loss.

Expected future split candidates:

- Quant/Qlib worker after `BacktestSpec`, artifact, and ledger contracts are stable.
- Data ingestion worker after Dataset Version and provider contracts are stable.
- Agent worker after Evidence, budget, checkpoint, and citation validation contracts are stable.

## Old-Path Deletion Criteria

Legacy paths may be deleted only after all criteria are met:

1. A characterization test captures the old behavior, including error paths.
2. New and old implementations pass the same contract tests.
3. If data is involved, migration follows expand -> backfill -> verify -> switch -> contract.
4. During any dual-write period, record counts, hashes, and key fields are compared.
5. Reads have switched to the new authority for an approved observation window.
6. Public API deprecation has been announced for at least two minor releases when external clients are affected.
7. P0 baseline checks and relevant P1/P2 contract tests pass.
8. `docs/development-progress-checklist.md`, ADRs, runbooks, and migration notes record the deletion.

## Alternatives Considered

### Rewrite DSA Before P1

Rejected. It would discard valuable product behavior, tests, Web/Desktop surfaces, and upstream syncability before the project has replacement contracts.

### Keep DSA as a Black-Box Sidecar

Rejected. It preserves short-term behavior but prevents the domain, run, artifact, migration, and provider contracts from becoming first-class platform concepts.

### Progressive Modularization Through Facades

Accepted. It allows engineering hardening to proceed while keeping DSA behavior stable and testable.

## Consequences

- P1 implementation starts with architecture tests and facades, not Quant Core, PIT Dataset, or formal backtesting.
- Existing DSA APIs and reports must remain stable unless a task explicitly updates frozen snapshots.
- More adapter code is expected in the short term; this is intentional migration scaffolding.
- Each facade creates a deletion obligation. Facades are not permanent dumping grounds.
- Service extraction is postponed until contracts and operational evidence justify it.

## Rollback

If a modularization step regresses behavior:

1. Re-enable the legacy DSA path through the relevant facade.
2. Revert only the failing implementation checkpoint, preserving characterization tests when they are correct.
3. Restore prior snapshot artifacts if approved behavior did not change.
4. Run P0 baseline checks plus the facade contract tests for the affected area.
5. Record the rollback and any new defect task in the progress checklist.

If a boundary rule blocks an urgent fix:

1. Use the smallest compatibility facade exception.
2. Record the exception in the task review notes.
3. Add a follow-up task or decision entry with owner and review date.

## Verification Requirements

Before this ADR is considered satisfied:

- `SAL-P1-001` must not merge DSA runtime source or start Quant Core/PIT/formal backtesting work.
- The progress checklist must mark ADR-001 and ADR-002 as approved and record evidence paths.
- Later P1 code tasks must add architecture tests enforcing the dependency direction described here.
- Gate G1 must verify that facades remain explicit and no new cross-domain legacy service bypass was introduced.
