from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from serenity_alpha_lab.repositories.storage_migrations import HEAD_REVISION


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SQL = ROOT / "docs" / "baselines" / "dsa-v3.26.1" / "database" / "fixture.sql"


def test_sqlite_fixture_upgrade_stamps_alembic_head_and_preserves_business_content(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.sqlite_upgrade import (
        inspect_sqlite_database,
        restore_sqlite_fixture,
        upgrade_legacy_sqlite_to_alembic_head,
    )

    database_path = tmp_path / "legacy-dsa.sqlite"
    restore_sqlite_fixture(FIXTURE_SQL, database_path)
    before = inspect_sqlite_database(database_path)

    report = upgrade_legacy_sqlite_to_alembic_head(database_path)
    after = inspect_sqlite_database(database_path)

    assert report.validation_passed is True
    assert report.target_revision == HEAD_REVISION
    assert report.before.row_counts == report.after.row_counts == before.row_counts == after.row_counts
    assert report.before.content_hashes == report.after.content_hashes == before.content_hashes == after.content_hashes
    assert report.before.row_counts["analysis_history"] == 2
    assert report.before.row_counts["schema_migrations"] == 1
    assert report.backup_path.exists()
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == HEAD_REVISION


def test_sqlite_fixture_upgrade_is_idempotent_after_success(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.sqlite_upgrade import restore_sqlite_fixture, upgrade_legacy_sqlite_to_alembic_head

    database_path = tmp_path / "legacy-dsa-idempotent.sqlite"
    restore_sqlite_fixture(FIXTURE_SQL, database_path)

    first = upgrade_legacy_sqlite_to_alembic_head(database_path)
    second = upgrade_legacy_sqlite_to_alembic_head(database_path)

    assert first.after.row_counts == second.after.row_counts
    assert first.after.content_hashes == second.after.content_hashes
    assert second.validation_passed is True


def test_sqlite_fixture_upgrade_restores_backup_when_failure_is_injected(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.sqlite_upgrade import (
        SQLiteUpgradeError,
        inspect_sqlite_database,
        restore_sqlite_fixture,
        upgrade_legacy_sqlite_to_alembic_head,
    )

    database_path = tmp_path / "legacy-dsa-failure.sqlite"
    restore_sqlite_fixture(FIXTURE_SQL, database_path)
    before = inspect_sqlite_database(database_path)

    with pytest.raises(SQLiteUpgradeError, match="Injected failure after backup"):
        upgrade_legacy_sqlite_to_alembic_head(database_path, fail_after_backup=True)

    after = inspect_sqlite_database(database_path)
    assert after.row_counts == before.row_counts
    assert after.content_hashes == before.content_hashes
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchone() is None


def test_sqlite_upgrade_code_does_not_import_dsa_storage_or_call_create_all() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "serenity_alpha_lab" / "repositories" / "sqlite_upgrade.py").read_text(encoding="utf-8")
    forbidden = ["src.storage", "DatabaseManager", "metadata.create_all", ".create_all("]

    assert [token for token in forbidden if token in source] == []
