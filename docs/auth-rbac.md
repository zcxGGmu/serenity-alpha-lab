# Auth And RBAC

## Conclusion

`SAL-P6-001` freezes the framework-neutral authentication and RBAC contract for desktop, standalone and team deployment modes. The implementation lives in `src/serenity_alpha_lab/application/auth_rbac.py` and defines `security.auth_rbac@1.0.0`, immutable subjects, resource scopes, role/permission matrices, optional OIDC provider declarations, OIDC claim mapping and API authorization requirements.

This task does not wire FastAPI middleware, verify JWTs, fetch OIDC metadata/JWKs, persist users, create signed artifact URLs, start Workers, call real Providers/LLMs, initialize Qlib, run notification senders, schedule production work or promote formal portfolio backtests.

## Identity Modes

| Mode | Identity model | OIDC required | Usability/Security decision |
|---|---|---:|---|
| `desktop` | Local `AuthRole.LOCAL_OWNER` subject under tenant `local` | No | Keeps local single-user setup usable and grants all current permissions without team setup. |
| `standalone` | Local admin/researcher/viewer/auditor/service-worker roles | No | Suitable for a self-hosted single tenant while still separating read-only and admin surfaces. |
| `team` | Tenant-scoped OIDC or pre-validated external subjects mapped into team roles | Yes | Separates data, run, config and administration permissions; unknown role aliases grant no privileges. |

## Permission Matrix

| Role | Key permissions |
|---|---|
| `local_owner` | All current permissions in desktop mode. |
| `admin` | All current permissions in standalone/team mode. |
| `config_admin` | `config:read`, `config:write`, `audit:read`; no data writes, run creation or user administration. |
| `data_steward` | Dataset/evidence read-write and definition read; no run creation, config write or user administration. |
| `run_operator` | Dataset/definition/evidence/report read plus run create/read/cancel; no dataset writes, config write or user administration. |
| `researcher` | Dataset/definition/run/evidence/report work plus artifact download and notification status reads; no config or user administration. |
| `viewer` | Read-only dataset/definition/run/evidence/report/notification status access. |
| `auditor` | Read-only platform context plus `audit:read`. |
| `service_worker` | `service:execute` and `run:read` only; future worker adapters still need object-level grants in `SAL-P6-002`. |

Tenant mismatch denies by default with `tenant_scope_mismatch`; team mismatch denies non-admin subjects with `team_scope_mismatch`. This is still coarse RBAC: Run/Definition/Evidence/Report object-level ownership, signed download URLs and worker least-privilege grants remain `SAL-P6-002`.

## OIDC Boundary

`OidcProviderConfig` is a declaration object only. It validates non-empty identifiers and HTTPS issuer URLs, records whether a secret reference is configured, and redacts the actual secret reference from `to_record()`.

`OidcClaimMapping` maps pre-validated claim dictionaries into `AuthSubject` values. It supports configurable subject, email, display-name, role and team claim names. Role aliases are explicit allowlists; unknown aliases are ignored and do not grant fallback permissions. The module imports no OIDC/JWT/network libraries and performs no token validation or JWK discovery.

## API Requirements

`default_api_authorization_catalog()` declares protected surfaces for:

| Surface | Example route | Required permission |
|---|---|---|
| Auth/config/user admin | `POST /api/v1/auth/settings`, `POST /api/v1/config`, `GET /api/v1/admin/users` | `user:admin` or `config:write/read` |
| Quant definitions | `POST /api/v1/quant/factor-definitions`, `POST /api/v1/quant/screen-definitions` | `definition:write` |
| Screening runs | `POST /api/v1/quant/screen-runs`, `GET /api/v1/quant/screen-runs/{run_id}` | `run:create` / `run:read` |
| Formal backtest runs | `POST /api/v1/quant/backtest-runs`, `POST /api/v1/quant/backtest-runs/{run_id}/cancel` | `run:create` / `run:cancel` |
| Artifact downloads | `GET /api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}` | `artifact:download` |
| Evidence and reports | `GET/POST /api/v1/research/evidence`, `GET/POST /api/v1/research/reports` | `evidence:*` / `report:*` |
| Notification outbox metadata | `GET /api/v1/research/reports/{report_id}/notifications`, `GET /api/v1/admin/notification-outbox` | `notification_outbox:read/admin` |
| Audit | `GET /api/v1/admin/audit`, formal backtest audit reads | `audit:read` |

The catalog intentionally excludes legacy `/api/v1/backtest/*` Signal Evaluation promotion, notification sender operations and runtime execution semantics.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_auth_rbac.py -q` failed with missing `serenity_alpha_lab.application.auth_rbac` (`1 error`) before implementation. |
| Focused Green | `uv run --extra core --extra dev python -m pytest tests/application/test_auth_rbac.py -q`: `5 passed in 0.41s`. |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_auth_rbac_stays_framework_neutral_and_runtime_free -q`: `1 passed in 0.03s`. |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_auth_rbac.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`: `41 passed in 0.89s`. |
| Full suite | `uv run --extra core --extra dev python -m pytest -q`: `503 passed, 3 skipped in 3.49s`. |
| Compile / lock / tag / diff | `compileall` PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag `upstream/dsa-v3.26.1` remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS. |

## Non-Goals

- No object-level signed Artifact URLs, Run/Definition/Evidence/Report owner policies or object-store policies; those belong to `SAL-P6-002`.
- No Secret Manager/OS Keychain integration or config secret rotation; those belong to `SAL-P6-003`.
- No SSRF/file-upload/report sanitizer hardening; those belong to `SAL-P6-004`.
- No CI security/SBOM gate, OpenTelemetry, backup/restore, chaos testing, production scheduler, Worker loop, real Provider/LLM runtime, Qlib runtime, notification sender or release packaging.
