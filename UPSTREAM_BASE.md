# Serenity Alpha Lab Upstream Base

> Phase: P0 上游接管与行为基线<br>
> Gate: G0，未通过<br>
> Last updated: 2026-07-20<br>
> Upstream: `ZhuLinsen/daily_stock_analysis`<br>
> Locked baseline: `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`

## 1. Baseline Policy

Serenity Alpha Lab uses DSA `v3.26.1` as the immutable P0 upstream baseline. The local tag `upstream/dsa-v3.26.1` must resolve to `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

Do not move, delete, or reuse the `upstream/dsa-v3.26.1` tag. Upstream upgrades must use a new `sync/dsa-<version>` branch and a new `upstream/dsa-v<version>` tag, followed by a full baseline refresh and Gate review.

Required remotes:

| Remote | URL | Purpose |
|---|---|---|
| `origin` | `git@github.com:zcxGGmu/serenity-alpha-lab.git` | Serenity project repository |
| `upstream` | `https://github.com/ZhuLinsen/daily_stock_analysis.git` | Official DSA source repository |

The DSA source is materialized only as an isolated worktree:

```text
.worktrees/dsa-v3.26.1
```

Dependency caches, generated logs, runtime SQLite files, Playwright output, SBOMs and diff artifacts stay under:

```text
.cache/dsa-p0
```

Neither `.worktrees` nor `.cache` is committed.

## 2. Local Deviations

Local deviations are classified as:

| Classification | Meaning |
|---|---|
| `compatible` | Preserves upstream runtime behavior while fixing a baseline blocker, test contradiction, deterministic CI issue, or isolated compatibility bug |
| `extension` | Adds Serenity-only scripts, fixtures, CI, docs, or baseline snapshots outside upstream runtime source |
| `divergence` | Changes upstream runtime/product semantics and requires ADR or Gate approval |

Current deviations:

| ID | Classification | Files | Reason | Upstream source impact |
|---|---|---|---|---|
| `DSA-PATCH-001` | `compatible` | `patches/dsa/v3.26.1/0001-isolate-intelligence-request-proxies.patch` | Isolates mutable request proxy defaults so backend offline tests are order-independent | Applies only to isolated worktree; intended upstream bugfix candidate |
| `DSA-PATCH-002` | `compatible` | `patches/dsa/v3.26.1/0002-align-alert-market-region-test-contract.patch` | Aligns a contradictory Web unit test with the current `cn/hk/us` market-light contract | Test-only patch in isolated worktree |
| `DSA-PATCH-003` | `compatible` | `patches/dsa/v3.26.1/0003-align-web-smoke-e2e-contract.patch` | Aligns Playwright smoke specs with current login, workspace, settings and report fixture behavior | E2E-test-only patch in isolated worktree |
| P0 baseline scripts | `extension` | `scripts/bootstrap-dsa-baseline.sh`, `scripts/apply-dsa-baseline-patches.sh`, `scripts/run-dsa-*baseline.sh`, `scripts/seed-dsa-web-smoke-fixture.sh` | Makes P0 evidence reproducible from the locked upstream ref | Serenity-only orchestration outside upstream source |
| P0 snapshots and records | `extension` | `docs/baselines/dsa-v3.26.1/**`, `docs/*baseline*.md`, `docs/upstream-patches.md` | Freezes behavior, contracts, schema, reports and supply-chain evidence for Gate G0 | Serenity-only evidence |
| P0 required workflow | `extension` | `.github/workflows/p0-required-baselines.yml` | Runs default PR checks for the frozen P0 baseline | Serenity-only CI |

No current P0 deviation is classified as `divergence`.

## 3. Baseline Scripts

| Script | Required check coverage |
|---|---|
| `scripts/bootstrap-dsa-baseline.sh` | Materializes the locked DSA worktree and installs local Python/npm dependencies |
| `scripts/apply-dsa-baseline-patches.sh` | Applies or checks registered compatibility patches |
| `scripts/run-dsa-backend-offline-baseline.sh` | Backend syntax, flake8, deterministic checks, pytest collection and offline tests |
| `scripts/run-dsa-docker-baseline.sh` | Docker build plus server/analyzer smoke |
| `scripts/run-dsa-api-config-baseline.sh` | OpenAPI and config contract byte-for-byte snapshot comparison |
| `scripts/run-dsa-database-baseline.sh` | SQLite schema, metadata, fixture and restore/hash validation |
| `scripts/run-dsa-report-signal-baseline.sh` | Structured report, Markdown report, DecisionSignal and Signal Evaluation golden snapshot comparison |
| `scripts/run-dsa-supply-chain-baseline.sh` | Python/Web/image SBOM, license and vulnerability baseline generation |
| `scripts/seed-dsa-web-smoke-fixture.sh` | Local Web smoke auth and report fixture seeding |

## 4. Required PR Checks

The default P0 required workflow is `.github/workflows/p0-required-baselines.yml`. Configure branch protection to require these check names before merging into the protected branch:

| Required check | Purpose |
|---|---|
| `p0-backend-offline-baseline` | Runs the locked DSA backend offline baseline |
| `p0-web-baseline` | Runs Web `npm ci`, lint, build, Vitest and Playwright smoke with the local fixture |
| `p0-contract-and-golden-baselines` | Runs API/config, database and report/signal snapshot compare gates |
| `p0-docker-and-supply-chain-baseline` | Builds/smokes the Docker baseline and generates supply-chain scanner artifacts |

These jobs are intentionally heavier than ordinary lint checks. They are P0 required checks because Gate G0 is a takeover baseline, not feature development.

## 5. Sync Procedure

When a new DSA release or selected upstream commit is evaluated:

1. Create an isolated branch, for example `sync/dsa-vX.Y.Z`.
2. Fetch upstream refs and create a new immutable local baseline tag, for example `upstream/dsa-vX.Y.Z`.
3. Materialize a new worktree under `.worktrees/dsa-vX.Y.Z`.
4. Replay each registered patch and classify the outcome:
   - `absorbed`: upstream already contains equivalent behavior, remove local patch after evidence update.
   - `still-needed`: patch applies and remains compatible.
   - `conflict`: patch no longer applies; resolve in the sync branch and record the reason.
   - `obsolete`: behavior is no longer needed; remove with evidence.
5. Refresh all P0 baseline snapshots intentionally with `--update-snapshots`.
6. Review diffs in API/config, database, report/signal, Docker, Web, backend tests and supply-chain findings.
7. Update `UPSTREAM_BASE.md`, `docs/upstream-patches.md`, evidence records and ADR/Gate notes.
8. Run the P0 required workflow and record Go/No-Go before promoting the new baseline.

## 6. Non-Goals

- Do not merge DSA source into the Serenity working tree before Gate approval.
- Do not run `npm audit fix`, `npm update`, broad dependency upgrades, or Docker base image upgrades inside P0 baseline commits.
- Do not replace `v3.26.1` with upstream `main` or an unreleased commit before Gate G0/ADR approval.
- Do not treat DSA Signal Evaluation as formal portfolio backtesting; that remains in P4.
