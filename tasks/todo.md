# SAL-P0-005 Web Baseline Recovery Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Gate G0 is not passed, so this task must not start P1, Quant Core, or broad DSA refactoring.

## Checklist

- [x] Review project lessons, current P0 status, and SAL-P0-005 acceptance criteria.
- [x] Reinstall Web dependencies in the locked DSA worktree without changing the lockfile.
- [x] Reproduce the AlertRuleForm Vitest failure and collect the actual assertion output.
- [x] Register a minimal DSA baseline patch for the JP/KR market-region test contract.
- [x] Apply the registered patch through `scripts/apply-dsa-baseline-patches.sh`.
- [x] Re-run targeted AlertRuleForm tests, full Web Vitest, lint, and build.
- [x] Attempt real Playwright smoke with controlled local auth settings; classify any remaining blocker truthfully.
- [x] Update Web evidence, P0 checklist/status, blocker/risk rows, and recovery notes.
- [x] Verify Git status and create a Chinese checkpoint commit if reviewable.

## Guardrails

- Do not run `npm audit fix`, `npm update`, or rewrite upstream lockfiles.
- Do not commit `.worktrees`, `node_modules`, `static`, Playwright artifacts, screenshots, `.cache`, or pycache.
- Do not mark `SAL-P0-005` as `DONE` unless Vitest, lint, build, and a non-skipped Playwright smoke are all proven.
- Do not mark Gate G0 complete.
- Keep DSA source changes as registered patch files under `patches/dsa/v3.26.1/`.

## Review

- Registered `DSA-PATCH-002` for the AlertRuleForm JP/KR market-light contract mismatch.
- Registered `DSA-PATCH-003` for Web smoke E2E contract drift: first-time auth setup, current Home stock workspace, ReportMarkdown fixture path, chat selector, and settings language assertions.
- Added `scripts/seed-dsa-web-smoke-fixture.sh` to create a local auth/env/SQLite fixture for non-skipped Playwright smoke.
- Fresh verification completed: patch check passed for `0001`/`0002`/`0003`; `npm run lint` passed; `npm run build` passed; `npm run test` returned `90 passed` files / `965 passed, 2 skipped`; `npm run test:smoke -- --reporter=line` returned `13 passed`.
- Final diff/status review is scoped to SAL-P0-005 files only; checkpoint commit will include the registered patch files, smoke fixture script, and synchronized evidence/status docs.
