# Secret And Config Hardening

> Task: `SAL-P6-003` Harden secrets and configuration<br>
> Date: 2026-07-31<br>
> Status: `APPROVED FOR SAL-P6-004 INPUT ONLY`

## Conclusion

`SAL-P6-003` extends the existing `SAL-P1-014` configuration profile facade with framework-neutral secret and config hardening contracts:

```text
src/serenity_alpha_lab/application/config_profiles.py
tests/application/test_config_profiles.py
tests/architecture/test_architecture_boundaries.py
```

The implementation adds metadata-only Secret Manager/OS Keychain references, safe config API diagnostics, dry-run rotation plans and deterministic config audit records. It does not import real OS Keychain or Secret Manager SDKs, write deployment `.env`, register API routes, start real Providers/LLMs, start a Worker loop, initialize Qlib, send notifications, schedule production work, package releases or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Secret backends | `environment`, `os_keychain`, `secret_manager` |
| Secret reference | `SecretReference` |
| Rotation plan | `SecretRotationPlan` |
| Config audit record | `ConfigAuditRecord` |
| API-safe diagnostics | `config_api_diagnostics()` |

## Secret References

`SecretReference` stores only where a secret lives, not the secret value. Supported URI schemes are:

```text
env://OPENAI_API_KEY
keychain://serenity/openai-api-key
secretmanager://production/openai-api-key
```

Reference URIs with query strings, fragments, unsupported schemes or raw-looking plaintext key material are rejected. Public `to_record()` output contains backend, configured state, optional last four, optional version and a deterministic reference hash. Storage records may include the reference URI so future adapters can resolve the secret, but they still never contain plaintext secret values.

## Config API Diagnostics

`config_api_diagnostics()` is the P6 API-facing diagnostic contract. Non-sensitive fields keep their safe values and source metadata. Sensitive fields are rendered only as:

- `configured`
- `backend`
- `last_four`
- `source`
- `sensitive`

The API diagnostic payload never includes `value` for secret fields and does not use full secret values as redaction placeholders. Environment-backed secrets can show only last four; Secret Manager/Keychain-backed fields show the caller-provided reference summary.

## Rotation And Audit

`SecretRotationPlan` records dry-run or approved rotation intent between two distinct `SecretReference` values. It validates same-field rotation, bounded timestamps and different reference hashes, then emits `scr_*` rotation IDs without raw reference URIs.

`ConfigAuditRecord` captures who viewed diagnostics, previewed config updates or planned secret rotations. Audit records include actor, tenant, profile, action, status, sanitized before/after values and metadata, plus deterministic `cad_*` IDs and `sha256:*` hashes. Metadata keys or values that look like secrets are redacted before serialization.

## Non-Goals

- No real Secret Manager, cloud KMS, Vault or OS Keychain client integration.
- No FastAPI config route, middleware, frontend settings page or persistence adapter wiring.
- No `.env` mutation, database migration, backup/restore, release packaging or notification sender.
- No real Provider/LLM calls, Worker loop, Qlib runtime, production scheduler or formal portfolio backtest promotion.
- No SSRF/file-upload/report sanitizer hardening; those remain `SAL-P6-004`.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py -q` failed during collection with missing `ConfigAuditAction` from `serenity_alpha_lab.application.config_profiles` (`1 error`) before implementation. |
| Architecture guard Red/initial | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_config_profiles_secret_hardening_stays_framework_neutral_and_runtime_free -q`: initial guard `1 passed` because the file was still runtime-free before the new symbols existed. |
| Focused Green | `uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py -q`: `13 passed in 0.52s`. |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_config_profiles_secret_hardening_stays_framework_neutral_and_runtime_free -q`: `1 passed in 0.01s`. |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py tests/application/test_auth_rbac.py tests/application/test_resource_authorization.py tests/architecture/test_architecture_boundaries.py -q`: `57 passed in 0.91s`. |
| Full suite | `uv run --extra core --extra dev python -m pytest -q`: `515 passed, 3 skipped in 4.10s`. |
| Compile / lock / tag | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag `upstream/dsa-v3.26.1` remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`. |

## Approval Record

This record approves metadata-only key/config hardening as input to `SAL-P6-004` input, fetch and report-rendering hardening. Runtime secret backends, config API route wiring, persistence adapters, real Provider/LLM calls, Worker execution, Qlib runtime, notification sending and release packaging still require later P6 tasks and profile-guarded runtime evidence.
