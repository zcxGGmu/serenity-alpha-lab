# SAL-P0-007 Docker Baseline Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Gate G0 is not passed, so this task must not start P1, Quant Core, or broad DSA refactoring.

## Checklist

- [x] Review project lessons and current P0 status.
- [x] Confirm Docker CLI, Compose, Buildx, and daemon availability.
- [x] Inspect locked DSA Dockerfile, compose profile, entrypoint, and documented health endpoint.
- [x] Build locked DSA Docker image from `.worktrees/dsa-v3.26.1`.
- [x] Run server profile and verify `/api/health`.
- [x] Run analyzer profile enough to classify startup/runtime behavior without real secrets.
- [x] Record image digest, compose status, logs, health output, and any blockers.
- [x] Update P0 checklist/status/evidence truthfully.
- [x] Verify Git status and create a Chinese checkpoint commit if reviewable.

## Guardrails

- Do not modify DSA upstream source unless the Docker baseline reveals a concrete script/config defect.
- Do not mark `SAL-P0-007` as `DONE` unless image build, server health, and analyzer/server profile evidence are all captured.
- Do not mark `SAL-P0-004`, `SAL-P0-005`, `SAL-P0-011`, or Gate G0 complete.
- Do not stage generated DSA source mirrors, Docker layers, caches, `.worktrees`, `.cache`, `.pyc`, or build artifacts.


## Review

- Result: `SAL-P0-007` Docker baseline is executable via `scripts/run-dsa-docker-baseline.sh`; image build, server health, and analyzer import smoke passed.
- Engineering change: added a project-level baseline script that injects the cached AlphaSift wheel into a temporary Docker context instead of relying on flaky dynamic Git clone during Docker build.
- Evidence: image digest `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076`, `/api/health` returned `status=ok`, analyzer smoke returned `ok-analyzer`.
- Follow-up: update P0 checklist/status/evidence, then move to `SAL-P0-004` backend gate/offline-tests or `SAL-P0-011` SBOM.
