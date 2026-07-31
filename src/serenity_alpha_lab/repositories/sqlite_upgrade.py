from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from serenity_alpha_lab.repositories.storage_migrations import HEAD_REVISION, stamp_database


class SQLiteUpgradeError(RuntimeError):
    """Raised when a legacy SQLite upgrade rehearsal fails."""


class SQLiteUpgradeValidationError(SQLiteUpgradeError):
    """Raised when post-upgrade content validation fails."""


@dataclass(frozen=True, slots=True)
class SQLiteInspection:
    database_path: Path
    row_counts: dict[str, int]
    content_hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class SQLiteUpgradeReport:
    database_path: Path
    backup_path: Path
    target_revision: str
    before: SQLiteInspection
    after: SQLiteInspection
    validation_passed: bool


def restore_sqlite_fixture(fixture_sql_path: str | Path, database_path: str | Path) -> Path:
    fixture_path = Path(fixture_sql_path)
    target_path = Path(database_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path.unlink()

    with sqlite3.connect(target_path) as conn:
        conn.executescript(fixture_path.read_text(encoding="utf-8"))
    return target_path


def inspect_sqlite_database(database_path: str | Path) -> SQLiteInspection:
    path = Path(database_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        table_names = _business_table_names(conn)
        row_counts = {table: _row_count(conn, table) for table in table_names}
        content_hashes = {table: _table_content_hash(conn, table) for table in table_names}

    return SQLiteInspection(database_path=path, row_counts=row_counts, content_hashes=content_hashes)


def upgrade_legacy_sqlite_to_alembic_head(
    database_path: str | Path,
    *,
    backup_path: str | Path | None = None,
    fail_after_backup: bool = False,
) -> SQLiteUpgradeReport:
    path = Path(database_path)
    backup = Path(backup_path) if backup_path is not None else path.with_suffix(f"{path.suffix}.sal-p1-013.bak")
    if not path.exists():
        raise SQLiteUpgradeError(f"SQLite database does not exist: {path}")

    before = inspect_sqlite_database(path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)

    try:
        if fail_after_backup:
            raise SQLiteUpgradeError("Injected failure after backup")

        stamp_database(f"sqlite:///{path}", HEAD_REVISION)
        after = inspect_sqlite_database(path)
        _validate_business_content_unchanged(before, after)
    except Exception:
        shutil.copy2(backup, path)
        raise

    return SQLiteUpgradeReport(
        database_path=path,
        backup_path=backup,
        target_revision=HEAD_REVISION,
        before=before,
        after=after,
        validation_passed=True,
    )


def _business_table_names(conn: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'
            ORDER BY name
            """
        )
    ]


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{_quote_identifier(table)}"').fetchone()[0])


def _table_content_hash(conn: sqlite3.Connection, table: str) -> str:
    columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{_quote_identifier(table)}")')]
    if not columns:
        return sha256(b"[]").hexdigest()

    column_sql = ", ".join(f'"{_quote_identifier(column)}"' for column in columns)
    rows = [
        {column: _normalize_sqlite_value(row[column]) for column in columns}
        for row in conn.execute(f'SELECT {column_sql} FROM "{_quote_identifier(table)}" ORDER BY rowid')
    ]
    payload = json.dumps(rows, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(payload).hexdigest()


def _validate_business_content_unchanged(before: SQLiteInspection, after: SQLiteInspection) -> None:
    if before.row_counts != after.row_counts:
        raise SQLiteUpgradeValidationError("SQLite upgrade changed business table row counts")
    if before.content_hashes != after.content_hashes:
        raise SQLiteUpgradeValidationError("SQLite upgrade changed business table content hashes")


def _normalize_sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    return value


def _quote_identifier(value: str) -> str:
    return value.replace('"', '""')


__all__ = [
    "SQLiteInspection",
    "SQLiteUpgradeError",
    "SQLiteUpgradeReport",
    "SQLiteUpgradeValidationError",
    "inspect_sqlite_database",
    "restore_sqlite_fixture",
    "upgrade_legacy_sqlite_to_alembic_head",
]
