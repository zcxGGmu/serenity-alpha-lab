# ADR-001: DSA Upstream Takeover, Sync, and Patch Policy

> Status: Approved<br>
> Date: 2026-07-20<br>
> Related tasks: `SAL-P1-001`, `SAL-P0-001`, `SAL-P0-002`, `SAL-P0-012`, `SAL-P0-013`<br>
> Review by: Gate G1 or 2026-08-03, whichever comes first

## Context

Gate G0 approved DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` as the Serenity Alpha Lab engineering hardening baseline. The project has imported DSA Git history and frozen P0 behavior, but the DSA runtime source has not yet been merged into the Serenity working tree.

The P0 baseline carries three registered local patches, all classified as `compatible`, and several accepted risks. The most immediate upstream drift risk is `RSK-006`: after the locked release, upstream contains at least two candidate commits:

- `55946536` - documentation-only macOS Gatekeeper packaging fix.
- `487e49e5` - DecisionSignal reassessment persistence feature touching API, Web, services, tests, and OpenAPI documentation.

P1 must preserve upstream syncability while allowing controlled engineering hardening. It must not silently move the baseline, follow upstream `main`, or absorb runtime semantics without rerunning the relevant baseline checks.

## Decision

Serenity Alpha Lab will use a controlled-sync policy:

1. `upstream/dsa-v3.26.1` remains immutable and must resolve to `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
2. The P1 baseline remains DSA `v3.26.1`; upstream `main` is not the development baseline.
3. Runtime source import, when needed by later P1 tasks, must be a dedicated checkpoint based on `upstream/dsa-v3.26.1` and must not use ad hoc file copying from `.worktrees`.
4. Upstream evaluation happens only on explicit `sync/dsa-<version-or-sha>` branches, never directly on the active development branch.
5. A new immutable baseline tag is created only after a sync branch passes review. Candidate branches may be discarded without affecting existing tags.
6. Local deviations remain classified as:
   - `compatible`: preserves runtime semantics or fixes deterministic baseline blockers.
   - `extension`: Serenity-only docs, scripts, fixtures, CI, or snapshots outside upstream runtime source.
   - `divergence`: changes upstream runtime/product semantics and requires ADR or Gate approval.
7. Every upstream sync review must replay local patches and record each patch outcome as `absorbed`, `still-needed`, `conflict`, or `obsolete`.
8. Sync promotion requires refreshing affected P0 snapshots and running the relevant P0 required checks before any new baseline is accepted.

## Candidate Commit Triage

### `55946536` macOS Gatekeeper Documentation Fix

Decision: accept as a low-risk sync candidate, but do not cherry-pick it into the current P1 baseline.

Rationale:

- It changes only `docs/CHANGELOG.md` and `docs/desktop-package.md`.
- It does not affect API, database, Web, report, signal, Docker, or supply-chain baselines.
- It is useful packaging knowledge for later Desktop/RC work, but not required for P1 architecture hardening.

Handling:

- Include it in the next `sync/dsa-*` evaluation branch by ancestry, or mirror the operational guidance in a future Desktop packaging runbook if that runbook is created before an upstream sync.
- No P1 runtime behavior changes are approved by this documentation fix.

### `487e49e5` DecisionSignal Reassessment Persistence

Decision: defer absorption. It is not approved for the current P1 baseline.

Rationale:

- It touches 18 files across FastAPI endpoints, schemas, Web API/types/pages/tests, services, OpenAPI docs, and DecisionSignal tests.
- It changes DecisionSignal reassessment persistence semantics, which may alter the frozen API/config baseline and report/signal behavior.
- It should be reviewed after the Compatibility Facade and architecture tests exist, so the project can decide whether it is an upstream-compatible feature or a Serenity divergence.

Handling:

- Evaluate only on a dedicated `sync/dsa-487e49e5` branch.
- Require OpenAPI diff review, targeted DecisionSignal characterization, Web test review, and report/signal baseline impact review before promotion.
- Do not treat this feature as part of formal portfolio backtesting or Quant Core scope.

## Alternatives Considered

### Follow Upstream `main`

Rejected. It minimizes short-term drift but makes P0 evidence unstable, invalidates Gate G0's fixed baseline, and risks importing unreviewed API or schema changes.

### Freeze Forever on `v3.26.1`

Rejected. It protects P0 evidence but ignores security fixes, packaging fixes, and upstream bug fixes that may reduce local patch load.

### Controlled Sync Branches

Accepted. It keeps the release baseline reproducible while preserving a path to absorb upstream value with explicit evidence.

## Consequences

- P1 tasks may rely on `v3.26.1` behavior unless an approved sync branch replaces the baseline.
- `RSK-006` remains open until at least one sync rehearsal proves the process or the candidate commits are formally rejected.
- P0 required checks stay relevant after P1 starts; they are the regression backstop for upstream drift.
- Any `divergence` must be visible in `docs/upstream-patches.md`, the progress checklist decision register, and the relevant ADR/Gate record.
- Dependency/security risks accepted in G0 remain release blockers until closed or formally waived in later Gates.

## Rollback

If a sync branch fails review:

1. Abandon the sync branch; do not modify `upstream/dsa-v3.26.1`.
2. Keep active development pinned to the last approved baseline.
3. Preserve failure evidence in the relevant task or Gate notes if the failure affects future planning.
4. Recreate the isolated worktree from the approved immutable tag.
5. Re-run affected baseline checks before resuming feature work if the failed sync touched local caches or generated artifacts.

If a promoted baseline later regresses:

1. Revert the promotion commit or branch merge.
2. Restore the prior baseline tag references and snapshot files from Git history.
3. Re-run P0 required checks and any P1 contract tests affected by the regression.
4. Record the rollback in `docs/development-progress-checklist.md` and `docs/development-status.md`.

## Verification Requirements

Before this ADR is considered satisfied:

- `git rev-parse upstream/dsa-v3.26.1` must still return `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- No DSA runtime source may be merged into the Serenity working tree by `SAL-P1-001`.
- `docs/upstream-patches.md` and `UPSTREAM_BASE.md` must remain consistent with the classification model in this ADR.
- `SAL-P1-001` must update the decision register and evidence register.
