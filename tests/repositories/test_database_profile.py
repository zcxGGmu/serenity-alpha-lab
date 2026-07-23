from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from serenity_alpha_lab.application.config_profiles import RuntimeProfile, load_runtime_settings
from serenity_alpha_lab.repositories.storage_migrations import upgrade_database


def test_standalone_postgresql_profile_resolves_pool_settings_without_leaking_password() -> None:
    from serenity_alpha_lab.repositories.database import (
        DatabaseDialect,
        resolve_database_profile,
    )

    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "standalone",
            "SERENITY_DATABASE_URL": "postgresql+psycopg://serenity:super-secret@localhost:5432/serenity",
        }
    )

    database = resolve_database_profile(settings)

    assert database.runtime_profile is RuntimeProfile.STANDALONE
    assert database.dialect is DatabaseDialect.POSTGRESQL
    assert database.pool_size == 5
    assert database.max_overflow == 10
    assert database.pool_timeout_seconds == 30
    assert database.statement_timeout_ms == 30_000
    assert "super-secret" not in database.redacted_url
    assert "serenity:***@" in database.redacted_url
    assert database.engine_options()["pool_pre_ping"] is True
    assert database.engine_options()["pool_size"] == 5
    assert database.engine_options()["max_overflow"] == 10
    assert database.engine_options()["pool_timeout"] == 30
    assert database.engine_options()["connect_args"]["options"] == "-c statement_timeout=30000"


def test_ci_sqlite_profile_enables_foreign_keys_busy_timeout_and_health_check(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.database import (
        DatabaseDialect,
        check_database_ready,
        create_database_engine,
        resolve_database_profile,
    )

    database_url = f"sqlite:///{tmp_path / 'contract.sqlite'}"
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": database_url,
        }
    )
    database = resolve_database_profile(settings)

    assert database.dialect is DatabaseDialect.SQLITE
    assert database.sqlite_busy_timeout_ms == 5_000

    engine = create_database_engine(database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5_000

        health = check_database_ready(engine, require_migration_head=False)
        assert health.ready is True
        assert health.dialect is DatabaseDialect.SQLITE
        assert health.ping_succeeded is True
        assert health.alembic_current_revision is None
    finally:
        engine.dispose()


def test_database_readiness_reports_alembic_preflight_status(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.database import (
        check_database_ready,
        create_database_engine,
        resolve_database_profile,
    )

    database_url = f"sqlite:///{tmp_path / 'alembic-head.sqlite'}"
    settings = load_runtime_settings({"SERENITY_PROFILE": "ci", "SERENITY_DATABASE_URL": database_url})
    database = resolve_database_profile(settings)

    engine = create_database_engine(database)
    try:
        missing = check_database_ready(engine, require_migration_head=True)
        assert missing.ready is False
        assert missing.alembic_current_revision is None
        assert missing.alembic_head_revision == "20260720_dsa_v3261_baseline"
        assert "not at Alembic head" in missing.failure_reason
    finally:
        engine.dispose()

    upgrade_database(database_url)

    migrated_engine = create_database_engine(database)
    try:
        ready = check_database_ready(migrated_engine, require_migration_head=True)
        assert ready.ready is True
        assert ready.alembic_current_revision == "20260720_dsa_v3261_baseline"
        assert ready.alembic_head_revision == "20260720_dsa_v3261_baseline"
        assert ready.failure_reason is None
    finally:
        migrated_engine.dispose()
