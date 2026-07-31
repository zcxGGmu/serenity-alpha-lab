from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest


def test_dsa_baseline_revision_metadata_matches_p0_database_snapshot() -> None:
    from serenity_alpha_lab.repositories.storage_migrations import (
        DSA_BASELINE_SCHEMA_SQL_SHA256,
        DSA_BASELINE_SCHEMA_VERSION,
        DSA_BASELINE_UPSTREAM_COMMIT,
        DSA_BASELINE_UPSTREAM_TAG,
        HEAD_REVISION,
        baseline_schema_sql_path,
    )

    schema_path = baseline_schema_sql_path()

    assert HEAD_REVISION == "20260720_dsa_v3261_baseline"
    assert DSA_BASELINE_UPSTREAM_TAG == "v3.26.1"
    assert DSA_BASELINE_UPSTREAM_COMMIT == "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
    assert DSA_BASELINE_SCHEMA_VERSION == "2026-06-05-create-all-baseline"
    assert schema_path.exists()
    assert hashlib.sha256(schema_path.read_bytes()).hexdigest() == DSA_BASELINE_SCHEMA_SQL_SHA256
    assert DSA_BASELINE_SCHEMA_SQL_SHA256 == "8d39743b05e5f6b6b7417805ced0fc27d5e5323d2ac04f791ac22c50038a5a51"


def test_alembic_upgrade_empty_sqlite_database_creates_dsa_baseline_schema(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.storage_migrations import HEAD_REVISION, upgrade_database

    database_path = tmp_path / "empty-dsa-baseline.sqlite"

    upgrade_database(f"sqlite:///{database_path}")

    with sqlite3.connect(database_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'
                """
            )
        }
        index_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        alembic_revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        dsa_schema_version = conn.execute("SELECT version FROM schema_migrations").fetchone()[0]

    assert len(table_names) == 28
    assert "analysis_history" in table_names
    assert "schema_migrations" in table_names
    assert index_count == 177
    assert alembic_revision == HEAD_REVISION
    assert dsa_schema_version == "2026-06-05-create-all-baseline"


def test_startup_preflight_requires_database_to_be_at_alembic_head(tmp_path: Path) -> None:
    from serenity_alpha_lab.repositories.storage_migrations import (
        HEAD_REVISION,
        StorageMigrationRequired,
        assert_database_at_head,
        current_migration_status,
        upgrade_database,
    )

    database_url = f"sqlite:///{tmp_path / 'startup-preflight.sqlite'}"

    initial_status = current_migration_status(database_url)
    assert initial_status.current_revision is None
    assert initial_status.head_revision == HEAD_REVISION
    assert initial_status.is_current is False
    with pytest.raises(StorageMigrationRequired, match="Database schema is not at Alembic head"):
        assert_database_at_head(database_url)

    upgrade_database(database_url)

    migrated_status = assert_database_at_head(database_url)
    assert migrated_status.current_revision == HEAD_REVISION
    assert migrated_status.head_revision == HEAD_REVISION
    assert migrated_status.is_current is True


def test_migration_code_does_not_import_dsa_storage_or_call_create_all() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "src" / "serenity_alpha_lab" / "repositories" / "storage_migrations.py",
        root / "migrations" / "env.py",
        root / "migrations" / "versions" / "20260720_dsa_v3261_baseline.py",
    ]

    missing = [str(path.relative_to(root)) for path in paths if not path.exists()]
    assert missing == []

    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    forbidden = ["src.storage", "DatabaseManager", "metadata.create_all", ".create_all("]

    assert [token for token in forbidden if token in combined] == []
