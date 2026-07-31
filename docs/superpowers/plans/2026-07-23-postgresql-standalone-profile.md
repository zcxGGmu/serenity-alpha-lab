# PostgreSQL Standalone Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-017` by adding a database profile and repository contract layer that lets desktop/CI SQLite and standalone PostgreSQL share the same connection, health, transaction, time, Decimal and JSON semantics.

**Architecture:** Add a narrow repository infrastructure module that resolves database settings from the existing Runtime Profile facade, builds SQLAlchemy engines with dialect-specific safety settings, exposes readiness diagnostics, and provides a repository contract probe. Keep persistence generic and offline-testable; do not implement Worker lease, PersistentTaskBackend, Quant Core, formal backtest, Evidence Agent, real Provider calls or broad DSA runtime migration.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x, Alembic baseline helpers, Pydantic RuntimeSettings, pytest, existing ProblemDetails/Trace-compatible error boundaries.

---

### Task 1: Red Tests For Database Profile And Repository Contract

**Files:**
- Create: `tests/repositories/test_database_profile.py`
- Create: `tests/repositories/test_repository_contract.py`
- Modify: `tests/repositories/test_storage_migrations.py`

- [ ] **Step 1: Write failing database profile tests**

Cover standalone PostgreSQL URL resolution, SQLite defaults, redacted diagnostics, engine safety options, SQLite PRAGMAs, health checks and startup preflight behavior.

- [ ] **Step 2: Write failing repository contract tests**

Create a shared contract suite for SQLite and optional live PostgreSQL via `SERENITY_TEST_POSTGRES_URL`. Cover UTC time round-trip, `Decimal` precision, JSON payload shape, duplicate key handling and rollback semantics.

- [ ] **Step 3: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py -q`
Expected: FAIL during collection with missing database profile / repository contract module.

### Task 2: Implement Database Profile And Contract Repository

**Files:**
- Create: `src/serenity_alpha_lab/repositories/database.py`
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`
- Modify: `src/serenity_alpha_lab/repositories/storage_migrations.py` if health checks need connection-level preflight helpers

- [ ] **Step 1: Add database settings DTOs**

Implement `DatabaseDialect`, `DatabaseProfileSettings`, `DatabaseProfileError`, profile URL resolution from `RuntimeSettings`, and redacted diagnostics that do not leak credentials.

- [ ] **Step 2: Add engine factory and health check**

Implement `create_database_engine()` with SQLite foreign key/WAL/busy-timeout settings and PostgreSQL pool/statement-timeout settings. Implement `check_database_ready()` using `SELECT 1`, pool diagnostics and optional Alembic head preflight.

- [ ] **Step 3: Add repository contract probe**

Implement a small SQLAlchemy-backed `RepositoryContractProbeRepository` over a stable probe table. Normalize UTC datetimes, `Decimal`, JSON and transaction rollback semantics so SQLite and PostgreSQL callers observe the same behavior.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/repositories/test_storage_migrations.py -q`
Expected: PASS; PostgreSQL live cases skip only when `SERENITY_TEST_POSTGRES_URL` is not provided.

### Task 3: Documentation, Status Sync, And Verification

**Files:**
- Create: `docs/postgresql-standalone-profile.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence document**

Document profile resolution, pool settings, health/readiness behavior, repository contract semantics, PostgreSQL live-test opt-in and explicit exclusions.

- [ ] **Step 2: Update ledgers**

Mark only `SAL-P2-017` as `DONE`, advance P2 to `17/20`, total progress to `46/129`, add evidence references, update current next task to `SAL-P2-018`, and refresh the next-session prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/repositories/test_storage_migrations.py -q
uv run --extra core --extra dev python -m pytest tests/repositories tests/application/test_config_profiles.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: all checks pass; immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
