# Resource And Artifact Authorization

> Task: `SAL-P6-002` Implement resource and Artifact authorization<br>
> Date: 2026-07-30<br>
> Status: `APPROVED FOR SAL-P6-003 INPUT ONLY`

## Conclusion

`SAL-P6-002` adds a framework-neutral object authorization layer on top of the `SAL-P6-001` Auth/RBAC contract:

```text
src/serenity_alpha_lab/application/resource_authorization.py
tests/application/test_resource_authorization.py
```

The module freezes `security.resource_artifact_authorization@1.0.0` and covers object-level authorization for Run, Definition, Evidence, Report and Artifact download resources. It implements tenant/team/owner checks, short-lived signed Artifact download URL contracts, deterministic audit records and task-scoped Worker grants. It does not wire FastAPI middleware, connect object storage, integrate Secret Manager, fetch OIDC/JWK metadata, start Workers, call real Providers/LLMs, initialize Qlib, run notification senders, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Contract version | `security.resource_artifact_authorization@1.0.0` |
| Schema | `security.resource_authorization` / `1.0.0` |
| Resource descriptor | `ResourceDescriptor` |
| Visibility | `private`, `team`, `tenant` |
| Policy | `ResourceAuthorizationPolicy` |
| Audit record | `ResourceAuthorizationAuditRecord` |
| Artifact download grant | `ArtifactDownloadGrant` |
| Signed URL issuer | `SignedArtifactUrlIssuer` |
| Worker grant | `WorkerResourceGrant` |

## Object Authorization

`ResourceAuthorizationPolicy` first delegates coarse permission checks to `RbacPolicy.authorize()` and then applies object-level rules:

- Tenant mismatch always denies, including guessed IDs from other tenants.
- Team-visible resources require matching team unless the subject is an admin/local owner.
- Private resources require matching `owner_user_id` unless the subject is an admin/local owner.
- Artifact downloads require `artifact:download` on the artifact and read access to the parent Run/Definition/Evidence/Report resource.
- Decisions always include deterministic audit metadata with subject, permission, resource scope, status, issue code and decision hash.

The resource model is intentionally metadata-only. It can be populated from Run, Definition, Evidence, Report or Artifact manifests by future API adapters without importing repositories, FastAPI routers or object-store SDKs into the authorization module.

## Signed URLs

`SignedArtifactUrlIssuer` signs canonical Artifact scope metadata with HMAC-SHA256 using caller-provided bytes. The URL is short-lived, bound to subject id, tenant id, artifact id, artifact SHA-256, resource scope hash, expiry and nonce. Verification handles percent-encoded Artifact ids and fails for tampered artifact ids, duplicated required query values, scope mismatch or expired URLs.

The signed URL record stores only a `signature_hash`; audit records do not include raw URL query strings, raw signatures or signing keys. Secret storage, key rotation and OS Keychain/Secret Manager integration remain `SAL-P6-003`.

## Worker Grants

`WorkerResourceGrant` creates a least-privilege task grant only after the `service_worker` subject is authorized for `service:execute` and `run:read` on the target run. Artifact grants must be produced by that run (`parent_resource_kind=run` and matching `parent_resource_id`). The grant is scoped to:

- one `task_id`;
- one `run_id`;
- explicit Artifact ids produced for that run;
- only `run:read` and `artifact:download`;
- a bounded expiry timestamp.

The grant rejects wildcard access, unrelated Artifact ids, unrelated task ids, unrelated subjects and permissions outside the grant.

## Non-Goals

- No FastAPI middleware/router registration or production route wiring.
- No object storage adapter, S3 pre-signed URL integration or filesystem download endpoint.
- No Secret Manager, OS Keychain, signing-key rotation or config audit; those belong to `SAL-P6-003`.
- No SSRF/file-upload/report sanitizer hardening; those belong to `SAL-P6-004`.
- No real Provider/LLM calls, Worker loop, Qlib runtime, production scheduler, notification sender, release packaging or formal portfolio backtest promotion.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_resource_authorization.py -q` failed with missing `serenity_alpha_lab.application.resource_authorization` (`1 error`) before implementation. |
| Red architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_resource_authorization_stays_framework_neutral_and_runtime_free -q` failed because `src/serenity_alpha_lab/application/resource_authorization.py` did not exist. |
| Focused Green | `uv run --extra core --extra dev python -m pytest tests/application/test_resource_authorization.py -q`: `6 passed in 0.37s`. |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_resource_authorization_stays_framework_neutral_and_runtime_free -q`: `1 passed in 0.01s`. |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_resource_authorization.py tests/application/test_auth_rbac.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py tests/repositories/test_evidence_store.py tests/application/test_backtest_api.py tests/application/test_report_delivery_ui.py tests/architecture/test_architecture_boundaries.py -q`: `62 passed in 1.09s`. |
| Full suite | `uv run --extra core --extra dev python -m pytest -q`: `510 passed, 3 skipped in 3.07s`. |
| Compile / lock / tag / diff | `compileall` PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag `upstream/dsa-v3.26.1` remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS. |

## Approval Record

This record approves object-level Resource and Artifact authorization as input to `SAL-P6-003` key/config hardening only. Runtime API middleware, signed object-store URL integration, Worker execution and notification sending still require later P6 tasks and profile-guarded runtime evidence.
