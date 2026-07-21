"""Repository boundary skeleton."""

from serenity_alpha_lab.repositories.bronze_raw_store import (
    BRONZE_RAW_CONTENT_TYPE,
    BRONZE_RAW_SCHEMA_NAME,
    BRONZE_RAW_SCHEMA_VERSION,
    BronzeRawArtifact,
    BronzeRawStore,
    BronzeRawStoreError,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore
from serenity_alpha_lab.repositories.storage_migrations import (
    MigrationStatus,
    StorageMigrationError,
    StorageMigrationRequired,
    assert_database_at_head,
    current_migration_status,
    stamp_database,
    upgrade_database,
)
from serenity_alpha_lab.repositories.sqlite_upgrade import (
    SQLiteInspection,
    SQLiteUpgradeError,
    SQLiteUpgradeReport,
    SQLiteUpgradeValidationError,
    inspect_sqlite_database,
    restore_sqlite_fixture,
    upgrade_legacy_sqlite_to_alembic_head,
)

__all__ = [
    "BRONZE_RAW_CONTENT_TYPE",
    "BRONZE_RAW_SCHEMA_NAME",
    "BRONZE_RAW_SCHEMA_VERSION",
    "BronzeRawArtifact",
    "BronzeRawStore",
    "BronzeRawStoreError",
    "LocalArtifactStore",
    "MigrationStatus",
    "StorageMigrationError",
    "StorageMigrationRequired",
    "SQLiteInspection",
    "SQLiteUpgradeError",
    "SQLiteUpgradeReport",
    "SQLiteUpgradeValidationError",
    "assert_database_at_head",
    "current_migration_status",
    "inspect_sqlite_database",
    "restore_sqlite_fixture",
    "stamp_database",
    "upgrade_legacy_sqlite_to_alembic_head",
    "upgrade_database",
]
