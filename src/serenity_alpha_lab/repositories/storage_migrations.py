from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine


ROOT_DIR = Path(__file__).resolve().parents[3]
ALEMBIC_INI_PATH = ROOT_DIR / "alembic.ini"
MIGRATIONS_DIR = ROOT_DIR / "migrations"
BASELINE_SCHEMA_SQL_PATH = MIGRATIONS_DIR / "baselines" / "dsa_v3_26_1_schema.sql"

HEAD_REVISION = "20260720_dsa_v3261_baseline"
DSA_BASELINE_UPSTREAM_TAG = "v3.26.1"
DSA_BASELINE_UPSTREAM_COMMIT = "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
DSA_BASELINE_SCHEMA_VERSION = "2026-06-05-create-all-baseline"
DSA_BASELINE_SCHEMA_SQL_SHA256 = "8d39743b05e5f6b6b7417805ced0fc27d5e5323d2ac04f791ac22c50038a5a51"


class StorageMigrationError(RuntimeError):
    """Base error for Alembic-backed storage migration operations."""


class StorageMigrationRequired(StorageMigrationError):
    """Raised when a database is not at the configured Alembic head."""


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    database_url: str
    current_revision: str | None
    head_revision: str

    @property
    def is_current(self) -> bool:
        return self.current_revision == self.head_revision


def baseline_schema_sql_path() -> Path:
    return BASELINE_SCHEMA_SQL_PATH


def baseline_schema_sql_sha256() -> str:
    return hashlib.sha256(BASELINE_SCHEMA_SQL_PATH.read_bytes()).hexdigest()


def alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(database_url: str, revision: str = "head") -> MigrationStatus:
    command.upgrade(alembic_config(database_url), revision)
    return current_migration_status(database_url)


def current_migration_status(database_url: str) -> MigrationStatus:
    config = alembic_config(database_url)
    script = ScriptDirectory.from_config(config)
    head_revision = script.get_current_head()
    if head_revision != HEAD_REVISION:
        raise StorageMigrationError(f"Unexpected Alembic head revision: {head_revision}")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
    finally:
        engine.dispose()

    return MigrationStatus(
        database_url=database_url,
        current_revision=current_revision,
        head_revision=head_revision,
    )


def assert_database_at_head(database_url: str) -> MigrationStatus:
    status = current_migration_status(database_url)
    if not status.is_current:
        raise StorageMigrationRequired(
            "Database schema is not at Alembic head: "
            f"current={status.current_revision or 'none'} head={status.head_revision}"
        )
    return status


__all__ = [
    "ALEMBIC_INI_PATH",
    "BASELINE_SCHEMA_SQL_PATH",
    "DSA_BASELINE_SCHEMA_SQL_SHA256",
    "DSA_BASELINE_SCHEMA_VERSION",
    "DSA_BASELINE_UPSTREAM_COMMIT",
    "DSA_BASELINE_UPSTREAM_TAG",
    "HEAD_REVISION",
    "MIGRATIONS_DIR",
    "MigrationStatus",
    "StorageMigrationError",
    "StorageMigrationRequired",
    "alembic_config",
    "assert_database_at_head",
    "baseline_schema_sql_path",
    "baseline_schema_sql_sha256",
    "current_migration_status",
    "upgrade_database",
]
