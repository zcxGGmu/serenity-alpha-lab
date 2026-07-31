# Secret And Config Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P6-003` by freezing framework-neutral secret reference, rotation, diagnostic and config audit contracts without enabling real Provider/LLM/Worker/Qlib/sender/runtime paths.

**Architecture:** Extend the existing `config_profiles` application boundary with metadata-only secret references for environment, OS Keychain and Secret Manager backends. The module records only references, presence, last-four summaries, hashes and audit metadata; it never reads real keychain/secret-manager SDKs, starts runtime calls, writes deployment `.env`, or exposes plaintext values. Config API diagnostics are a derived safe view that contains configured state and last four only for secret fields.

**Tech Stack:** Python dataclasses/enums, Pydantic Settings, hashlib/json deterministic records, pytest contract tests, architecture import guard, Markdown evidence record.

---

## File Structure

- Modify: `src/serenity_alpha_lab/application/config_profiles.py`
  - Add `SecretStorageBackend`, `SecretReference`, `SecretRotationPlan`, `ConfigAuditRecord`, safe API diagnostics and secret-reference validation helpers.
- Modify: `tests/application/test_config_profiles.py`
  - Add `SAL-P6-003` contract tests for keychain/secret-manager references, API redaction, rotation simulation and audit records.
- Modify: `tests/architecture/test_architecture_boundaries.py`
  - Add a `config_profiles.py` import guard that forbids keyring/boto/vault/cloud SDKs, FastAPI, Provider/LLM, Worker, Qlib, SQLAlchemy, integrations, repositories and services.
- Modify: `src/serenity_alpha_lab/application/__init__.py`
  - Export the public secret/config hardening symbols.
- Create: `docs/secret-config-hardening.md`
  - Record contract version, secret reference model, rotation/audit semantics, API diagnostic redaction, non-goals and verification evidence.
- Modify: `docs/development-progress-checklist.md`
  - Mark only `SAL-P6-003` done after verification, advance P6 to `3/23`, total to `109/129`, add DEC/AEV rows and set `SAL-P6-004` as next.
- Modify: `docs/development-status.md`
  - Update completed/unfinished ranges, latest checkpoints, next task and recovery prompt.
- Modify: `tasks/todo.md`
  - Track Red/Green/verification/review for this task.

## Task 1: Red Secret/Config Contract

- [x] **Step 1: Add failing contract tests**

Add tests for:

```python
def test_secret_references_use_keychain_or_secret_manager_without_plaintext_leakage(): ...
def test_config_api_diagnostics_show_only_presence_backend_and_last_four(): ...
def test_secret_rotation_plan_records_old_and_new_reference_hashes_only(): ...
def test_config_audit_record_is_deterministic_and_redacts_sensitive_payloads(): ...
```

- [x] **Step 2: Add architecture guard**

Add `test_config_profiles_secret_hardening_stays_framework_neutral_and_runtime_free()` allowing only stdlib, Pydantic/Pydantic Settings and local config-profile dependencies. Forbid `keyring`, `boto3`, `hvac`, `fastapi`, `requests`, `litellm`, `qlib`, `sqlalchemy`, Provider SDKs, integrations, repositories and services.

- [x] **Step 3: Run Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py -q
uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_config_profiles_secret_hardening_stays_framework_neutral_and_runtime_free -q
```

Expected: focused tests fail because the new secret-reference symbols/functions do not exist; architecture guard may pass only after the target symbol/file expectations are added.

## Task 2: Green Metadata-Only Secret Hardening

- [x] **Step 1: Implement secret references**

Add `SecretStorageBackend` and `SecretReference` with supported URI schemes:

```text
env://OPENAI_API_KEY
keychain://serenity/openai
secretmanager://production/openai
```

Reject raw-looking plaintext values such as `sk-*`, `provider-token-*`, URLs with query/fragment secrets, or unsupported schemes. `to_record()` must include backend, configured state, optional last four and deterministic reference hash; it must not include plaintext secret material.

- [x] **Step 2: Implement safe config API diagnostics**

Add `config_api_diagnostics(settings, secret_references=...)` that keeps non-sensitive config values but renders sensitive fields as:

```python
{
    "configured": True,
    "backend": "secret_manager",
    "last_four": "abcd",
    "source": "secret_reference:secret_manager",
    "sensitive": True,
}
```

It must not include `[REDACTED]` as a stand-in for a hidden value when a last-four summary is available, and serialized diagnostics must not contain full secrets or raw signatures.

- [x] **Step 3: Implement rotation and audit records**

Add `SecretRotationPlan` and `ConfigAuditRecord` that can represent dry-run and approved rotations without retrieving or writing a real secret. Audit records must have stable hashes, actor/tenant/profile/action/status, sanitized field changes and no plaintext secret values.

- [x] **Step 4: Export public symbols and run focused Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py -q
uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_config_profiles_secret_hardening_stays_framework_neutral_and_runtime_free -q
```

Expected: focused config tests and architecture guard pass.

## Task 3: Evidence, Status Sync And Checkpoint

- [x] **Step 1: Add evidence doc**

Create `docs/secret-config-hardening.md` with contract details, non-goals, verification evidence and explicit runtime boundaries.

- [x] **Step 2: Update project registers**

Update progress/status docs for `SAL-P6-003` only. Keep G6 unpassed and set `SAL-P6-004` as the next unfinished task. Do not start `SAL-P6-004`.

- [x] **Step 3: Run final verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_config_profiles.py tests/application/test_auth_rbac.py tests/application/test_resource_authorization.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: focused/related/full suites pass, compile passes, dependency lock passes, immutable upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`, diff hygiene passes.

- [x] **Step 4: Create Chinese checkpoint commit**

Stage only `SAL-P6-003` code/tests/docs/status files. Do not stage `.worktrees`, `.cache`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files. Commit with:

```text
feat(P6): 加固密钥与配置

完成内容：
- ...

兼容性与风险：
- ...

验证：
- ...

关联任务：SAL-P6-003, Gate G6
```

## Scope Guard

- Do not implement `SAL-P6-004+`, SSRF/file upload hardening, SCA gates, OpenTelemetry, backup/restore, Worker loop, Provider/LLM runtime, Qlib runtime, notification sender, production scheduler or release packaging.
- Do not import real OS Keychain, Secret Manager, cloud SDK, FastAPI, requests, LiteLLM, Provider SDKs, Qlib, SQLAlchemy, integrations, repositories, services or DSA runtime from `config_profiles.py`.
- Do not write `.env`, databases, logs, traces, backups or frontend payloads with plaintext secrets.

## Review

- Red target failed as expected during collection with missing `ConfigAuditAction` import (`1 error`) before implementation.
- Implemented metadata-only `SecretReference`, `SecretRotationPlan`, `ConfigAuditRecord` and `config_api_diagnostics()` in the existing `application.config_profiles` boundary.
- Verification evidence recorded: focused Green `13 passed`, architecture guard `1 passed`, related Config/Auth/Resource/Architecture suite `57 passed`, full pytest `515 passed, 3 skipped`, compileall PASS, dependency lock guard PASS and immutable upstream tag `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Scope held: no real Keychain/Secret Manager/cloud SDK, FastAPI route, `.env` write, database persistence, backup/restore, Provider/LLM, Worker loop, Qlib runtime, notification sender, production scheduler, release packaging or formal portfolio backtest promotion was started.
