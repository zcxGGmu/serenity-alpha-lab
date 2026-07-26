# Quant Lab

> Status: `APPROVED FOR SAL-P4-022 GATE G4 INPUT ONLY`  
> Task: `SAL-P4-021`  
> Patch: `DSA-PATCH-006` (`patches/dsa/v3.26.1/0006-add-quant-lab.patch`)  
> API input: [Formal Backtest API](./backtest-api.md)

## Scope

Quant Lab is a DSA Web extension for creating and reviewing formal portfolio backtest runs through the framework-neutral `/api/v1/quant/backtest-runs` contract. It is deliberately separate from legacy DSA `/api/v1/backtest/*`, which remains Signal Evaluation only.

The page supports:

- Preview/Formal run creation with an `Idempotency-Key`.
- Compact run status, resource policy, runtime flags and ranking eligibility display.
- Equity/drawdown metric cards backed by the metrics Artifact payload.
- Cursor-paginated raw orders/trades and positions tables.
- Bias audit outcome review and artifact download controls.
- Dataset version, schema, trace/run/stage and Artifact id/hash lineage display.
- Cancellation through `/api/v1/quant/backtest-runs/{run_id}/cancel`.

## UI Contract

Quant Lab uses a dense operational layout matching Screen Lab rather than a marketing page. The top-level status badges intentionally separate:

- Requested/effective mode: `Preview only` or `Formal mode`.
- Artifact validity: `Formal valid`, `Partial artifact`, `Invalid artifact` or `No artifact`.
- Ranking state: `Ranking eligible` or `Not ranking eligible`.

This prevents a preview run with an invalid Artifact from visually appearing as a formal eligible result. The UI also keeps the route label distinct from legacy Signal Evaluation: `/quant-lab` is Quant Lab, while `/backtest` remains `信号评价 / Signal Evaluation`.

## API Lineage

The DSA Web API client introduced by `DSA-PATCH-006` maps camelCase UI payloads to the formal snake_case API contract and camelizes responses:

| UI action | API route |
|---|---|
| Create run | `POST /api/v1/quant/backtest-runs` |
| Load status | `GET /api/v1/quant/backtest-runs/{run_id}` |
| Load metrics | `GET /api/v1/quant/backtest-runs/{run_id}/metrics` |
| Load orders | `GET /api/v1/quant/backtest-runs/{run_id}/orders` |
| Load positions | `GET /api/v1/quant/backtest-runs/{run_id}/positions` |
| Load audit | `GET /api/v1/quant/backtest-runs/{run_id}/audit` |
| Download artifact | `GET /api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}` |
| Cancel run | `POST /api/v1/quant/backtest-runs/{run_id}/cancel` |

Large result rows remain behind orders/positions pagination or artifact payload routes. Compact create/status responses are not expanded into full raw result payloads.

## Non-Goals

This task does not:

- Pass Gate G4 or promote formal portfolio backtests into Evidence Agent.
- Start a Worker loop, Qlib runtime, real Provider call or real LLM call.
- Register a FastAPI router or change the framework-neutral API facade.
- Rename or repurpose legacy `/api/v1/backtest/*` Signal Evaluation.
- Present Qlib internal evidence, Dataset conversion artifacts, Screen results, AlphaSift T+N evaluation or legacy Signal Evaluation as formal portfolio backtest evidence.

## Verification

TDD red evidence:

- `npm run test -- src/api/__tests__/quantBacktest.test.ts` initially failed because `src/api/quantBacktest.ts` did not exist.
- `npm run test -- src/pages/__tests__/QuantLabPage.test.tsx` initially failed because `src/pages/QuantLabPage.tsx` did not exist.
- `npm run test -- src/App.test.tsx src/components/layout/__tests__/SidebarNav.test.tsx` initially failed on missing `/quant-lab` route/nav registration.

Fresh green evidence:

| Command | Result |
|---|---|
| `npm run test -- src/api/__tests__/quantBacktest.test.ts src/pages/__tests__/QuantLabPage.test.tsx src/App.test.tsx src/components/layout/__tests__/SidebarNav.test.tsx` | `4 passed` files / `27 passed` tests |
| `npm run lint` in `.worktrees/dsa-v3.26.1/apps/dsa-web` | PASS |
| `npm run build` in `.worktrees/dsa-v3.26.1/apps/dsa-web` | PASS; Vite built QuantLab chunk `QuantLabPage-CR2xIlDc.js` |
| `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py tests/application/test_backtest_run_orchestration.py tests/application/test_backtest_resource_control.py tests/quant/test_backtest_golden_property.py tests/architecture/test_architecture_boundaries.py -q` | `34 passed` |
| `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS; `Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --worktree /tmp/serenity-dsa-patch-apply-check-20260726131444` on a clean temporary `upstream/dsa-v3.26.1` worktree | Applied `0001` through `0006` sequentially |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git diff --check` | PASS |

The default `scripts/apply-dsa-baseline-patches.sh --check-only` command was not used as the final patch-chain proof after `DSA-PATCH-006`, because the live DSA worktree already includes later hunks that touch files introduced by `DSA-PATCH-004`; reverse-checking an earlier patch against the final cumulative worktree can fail on context even though a clean sequential apply succeeds. The authoritative replay evidence is the clean temporary worktree sequential application above.

## Approval Record

This record approves Quant Lab as the UI input to `SAL-P4-022` Gate G4 only. Gate G4 is still not passed; Evidence Agent, real Provider/LLM calls, Worker runtime and formal backtest promotion remain blocked until later tasks explicitly approve them.
