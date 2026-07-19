# SAL-P0-011 Supply Chain Baseline Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Gate G0 is not passed, so this task must not start P1, Quant Core, or broad DSA refactoring.

## Checklist

- [x] Review project lessons, current P0 status, and SAL-P0-011 acceptance criteria.
- [x] Confirm existing backend/Docker baseline artifacts and local scanner availability.
- [x] Add a reproducible supply-chain baseline script for Python, Node, Docker image inventory, and scanner checks.
- [x] Generate Python installed dependency SBOM from the isolated `.cache/dsa-p0/venv` without contaminating that venv.
- [x] Generate Docker image package inventory from `serenity-dsa-p0:sal-p0-007`.
- [x] Attempt image SBOM/vulnerability generation with available local tools and classify any scanner gap truthfully.
- [x] Update supply-chain evidence, P0 checklist/status, blocker/risk rows, and recovery notes.
- [x] Verify script syntax, generated artifacts, Git status, and prepare a Chinese checkpoint commit if reviewable.

## Guardrails

- Do not run `npm audit fix`, `npm update`, or rewrite upstream lockfiles.
- Do not install SBOM/scanner tooling into the DSA CI venv used as the target Python environment.
- Do not stage generated `.cache`, `.worktrees`, source mirrors, `node_modules`, `.pyc`, or scanner databases.
- Do not mark `SAL-P0-011` as `DONE` unless Python SBOM, Node/license/vulnerability evidence, image SBOM, and vulnerability summary are all produced or explicitly accepted by the checklist as classified blockers.
- Do not mark Gate G0 complete.

## Review

- Added `scripts/run-dsa-supply-chain-baseline.sh` to generate Python SBOM/license/audit, Web npm audit/license, Docker image inventory, Syft SBOM, and Grype vulnerability artifacts.
- Installed supply-chain scanners outside the DSA target venv: Homebrew `syft`, `grype`, `trivy`; separate `.cache/dsa-p0/supply-chain-tools-venv` with `pip-audit 2.9.0`.
- Generated artifacts under `.cache/dsa-p0/supply-chain-artifacts/` without staging cache output.
- Final summary: Python 146 packages, 1 pip-audit vulnerability, 1 skipped AlphaSift audit, Web npm 16 vulnerabilities / 10 high, image Grype 933 matches / 39 critical / 84 high.
- `SAL-P0-011` is DONE as a P0 baseline with owner/plan/deadline rows for all Critical/High findings; Gate G0 remains open because `SAL-P0-005`, `SAL-P0-008` to `SAL-P0-010`, and `SAL-P0-012` are not complete.
