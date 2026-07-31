"""Create DSA v3.26.1 baseline schema.

Revision ID: 20260720_dsa_v3261_baseline
Revises:
Create Date: 2026-07-20
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "20260720_dsa_v3261_baseline"
down_revision = None
branch_labels = None
depends_on = None

DSA_BASELINE_UPSTREAM_TAG = "v3.26.1"
DSA_BASELINE_UPSTREAM_COMMIT = "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a"
DSA_BASELINE_SCHEMA_VERSION = "2026-06-05-create-all-baseline"
DSA_BASELINE_SCHEMA_SQL_SHA256 = "8d39743b05e5f6b6b7417805ced0fc27d5e5323d2ac04f791ac22c50038a5a51"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        raise RuntimeError("DSA v3.26.1 baseline migration currently supports SQLite only")

    raw_connection = bind.connection
    raw_connection.executescript(_baseline_schema_sql())

    op.execute(
        sa.text(
            """
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES (:version, :description, :applied_at)
            """
        ).bindparams(
            version=DSA_BASELINE_SCHEMA_VERSION,
            description="Baseline schema created through Alembic from DSA v3.26.1 P0 snapshot",
            applied_at=datetime(2026, 1, 5, 9, 30, tzinfo=UTC).replace(tzinfo=None),
        )
    )


def downgrade() -> None:
    raise RuntimeError("DSA v3.26.1 baseline migration is not downgradeable")


def _baseline_schema_sql() -> str:
    return _baseline_schema_sql_path().read_text(encoding="utf-8")


def _baseline_schema_sql_path() -> Path:
    return Path(__file__).resolve().parents[1] / "baselines" / "dsa_v3_26_1_schema.sql"
