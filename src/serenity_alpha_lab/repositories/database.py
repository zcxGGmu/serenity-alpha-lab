from __future__ import annotations

from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Date, MetaData, String, Table, create_engine, delete, event, insert, select, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON

from serenity_alpha_lab.application.config_profiles import RuntimeProfile, RuntimeSettings
from serenity_alpha_lab.repositories.storage_migrations import StorageMigrationError, current_migration_status


class DatabaseProfileError(ValueError):
    """Raised when database profile settings are invalid."""


class RepositoryError(RuntimeError):
    """Base error for SQLAlchemy-backed repository operations."""


class RepositoryConflict(RepositoryError):
    """Raised when repository uniqueness constraints are violated."""


class DatabaseDialect(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass(frozen=True, slots=True)
class DatabaseProfileSettings:
    database_url: str
    runtime_profile: RuntimeProfile
    dialect: DatabaseDialect
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout_seconds: int = 30
    statement_timeout_ms: int | None = None
    sqlite_busy_timeout_ms: int = 5_000
    sqlite_wal_enabled: bool = True
    application_name: str = "serenity-alpha-lab"

    @property
    def redacted_url(self) -> str:
        return make_url(self.database_url).render_as_string(hide_password=True)

    def engine_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "future": True,
            "pool_pre_ping": True,
        }
        if self.dialect is DatabaseDialect.SQLITE:
            options["connect_args"] = {"timeout": self.sqlite_busy_timeout_ms / 1000}
            if _is_memory_sqlite_url(self.database_url):
                options["poolclass"] = StaticPool
            return options

        connect_args: dict[str, Any] = {"application_name": self.application_name}
        if self.statement_timeout_ms is not None:
            connect_args["options"] = f"-c statement_timeout={self.statement_timeout_ms}"

        options.update(
            {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout_seconds,
                "connect_args": connect_args,
            }
        )
        return options


@dataclass(frozen=True, slots=True)
class DatabaseReadiness:
    dialect: DatabaseDialect
    ready: bool
    ping_succeeded: bool
    pool_status: str
    alembic_current_revision: str | None = None
    alembic_head_revision: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RepositoryContractProbeRecord:
    record_id: str
    occurred_at: datetime
    trade_date: date
    amount: Decimal
    payload: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "repository_contract.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _required_string("record_id", self.record_id))
        object.__setattr__(self, "occurred_at", _require_utc_datetime(self.occurred_at))
        object.__setattr__(self, "amount", _coerce_decimal(self.amount))
        object.__setattr__(self, "payload", _normalize_json_value(dict(self.payload)))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))


_CONTRACT_METADATA = MetaData()
_CONTRACT_TABLE = Table(
    "serenity_repository_contract_probe",
    _CONTRACT_METADATA,
    Column("record_id", String(96), primary_key=True),
    Column("occurred_at_utc", String(40), nullable=False),
    Column("trade_date", Date(), nullable=False),
    Column("amount_decimal", String(80), nullable=False),
    Column("payload_json", JSON(), nullable=False),
    Column("schema_version", String(64), nullable=False),
)


class RepositoryContractProbeTransaction:
    def __init__(self, connection) -> None:
        self._connection = connection

    def insert(self, record: RepositoryContractProbeRecord) -> None:
        _insert_contract_record(self._connection, record)


class RepositoryContractProbeRepository:
    """Small SQLAlchemy repository used to verify cross-profile semantics."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_schema(self) -> None:
        _CONTRACT_METADATA.create_all(self._engine, tables=[_CONTRACT_TABLE])

    def clear(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(_CONTRACT_TABLE))

    def insert(self, record: RepositoryContractProbeRecord) -> None:
        with self._engine.begin() as connection:
            _insert_contract_record(connection, record)

    def get(self, record_id: str) -> RepositoryContractProbeRecord | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(_CONTRACT_TABLE).where(_CONTRACT_TABLE.c.record_id == _required_string("record_id", record_id))
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _record_from_row(row)

    @contextmanager
    def transaction(self) -> Iterator[RepositoryContractProbeTransaction]:
        with self._engine.connect() as connection:
            transaction = connection.begin()
            try:
                yield RepositoryContractProbeTransaction(connection)
            except BaseException:
                transaction.rollback()
                raise
            else:
                transaction.commit()


def resolve_database_profile(settings: RuntimeSettings, *, default_data_dir: str | Path | None = None) -> DatabaseProfileSettings:
    database_url = settings.database_url or _default_database_url(settings.profile, default_data_dir=default_data_dir)
    parsed = make_url(database_url)
    dialect = _dialect_from_url(parsed)

    if settings.profile is RuntimeProfile.STANDALONE and settings.database_url is None:
        raise DatabaseProfileError("standalone profile requires SERENITY_DATABASE_URL")

    statement_timeout_ms = 30_000 if dialect is DatabaseDialect.POSTGRESQL else None
    return DatabaseProfileSettings(
        database_url=database_url,
        runtime_profile=settings.profile,
        dialect=dialect,
        statement_timeout_ms=statement_timeout_ms,
    )


def create_database_engine(settings: DatabaseProfileSettings) -> Engine:
    engine = create_engine(settings.database_url, **settings.engine_options())
    if settings.dialect is DatabaseDialect.SQLITE:
        _install_sqlite_pragmas(engine, settings)
    return engine


def check_database_ready(engine: Engine, *, require_migration_head: bool = True) -> DatabaseReadiness:
    dialect = _dialect_from_engine(engine)
    pool_status = _pool_status(engine)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        return DatabaseReadiness(
            dialect=dialect,
            ready=False,
            ping_succeeded=False,
            pool_status=pool_status,
            failure_reason=f"database ping failed: {exc.__class__.__name__}",
        )

    if not require_migration_head:
        return DatabaseReadiness(dialect=dialect, ready=True, ping_succeeded=True, pool_status=pool_status)

    try:
        status = current_migration_status(_engine_url_for_migration(engine))
    except StorageMigrationError as exc:
        return DatabaseReadiness(
            dialect=dialect,
            ready=False,
            ping_succeeded=True,
            pool_status=pool_status,
            failure_reason=str(exc),
        )
    except SQLAlchemyError as exc:
        return DatabaseReadiness(
            dialect=dialect,
            ready=False,
            ping_succeeded=True,
            pool_status=pool_status,
            failure_reason=f"migration preflight failed: {exc.__class__.__name__}",
        )

    if not status.is_current:
        return DatabaseReadiness(
            dialect=dialect,
            ready=False,
            ping_succeeded=True,
            pool_status=pool_status,
            alembic_current_revision=status.current_revision,
            alembic_head_revision=status.head_revision,
            failure_reason=(
                "Database schema is not at Alembic head: "
                f"current={status.current_revision or 'none'} head={status.head_revision}"
            ),
        )

    return DatabaseReadiness(
        dialect=dialect,
        ready=True,
        ping_succeeded=True,
        pool_status=pool_status,
        alembic_current_revision=status.current_revision,
        alembic_head_revision=status.head_revision,
    )


def _insert_contract_record(connection, record: RepositoryContractProbeRecord) -> None:
    values = {
        "record_id": record.record_id,
        "occurred_at_utc": record.occurred_at.isoformat(),
        "trade_date": record.trade_date,
        "amount_decimal": format(record.amount, "f"),
        "payload_json": dict(record.payload),
        "schema_version": record.schema_version,
    }
    try:
        connection.execute(insert(_CONTRACT_TABLE).values(**values))
    except IntegrityError as exc:
        raise RepositoryConflict(f"Repository contract record already exists: {record.record_id}") from exc


def _record_from_row(row: Mapping[str, Any]) -> RepositoryContractProbeRecord:
    return RepositoryContractProbeRecord(
        record_id=str(row["record_id"]),
        occurred_at=datetime.fromisoformat(str(row["occurred_at_utc"])).astimezone(UTC),
        trade_date=row["trade_date"],
        amount=Decimal(str(row["amount_decimal"])),
        payload=dict(row["payload_json"]),
        schema_version=str(row["schema_version"]),
    )


def _install_sqlite_pragmas(engine: Engine, settings: DatabaseProfileSettings) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_connection_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            if settings.sqlite_wal_enabled and not _is_memory_sqlite_url(settings.database_url):
                cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def _default_database_url(profile: RuntimeProfile, *, default_data_dir: str | Path | None) -> str:
    if profile is RuntimeProfile.CI:
        return "sqlite:///:memory:"

    root = Path(default_data_dir) if default_data_dir is not None else Path("data")
    filename = "serenity-desktop.sqlite" if profile is RuntimeProfile.DESKTOP else "serenity-standalone.sqlite"
    return f"sqlite:///{(root / filename).as_posix()}"


def _dialect_from_url(url: URL) -> DatabaseDialect:
    backend = url.get_backend_name()
    if backend == "sqlite":
        return DatabaseDialect.SQLITE
    if backend in {"postgresql", "postgres"}:
        return DatabaseDialect.POSTGRESQL
    raise DatabaseProfileError(f"Unsupported database dialect: {backend}")


def _dialect_from_engine(engine: Engine) -> DatabaseDialect:
    name = engine.dialect.name
    if name == "sqlite":
        return DatabaseDialect.SQLITE
    if name == "postgresql":
        return DatabaseDialect.POSTGRESQL
    raise DatabaseProfileError(f"Unsupported database dialect: {name}")


def _is_memory_sqlite_url(database_url: str) -> bool:
    parsed = make_url(database_url)
    return parsed.get_backend_name() == "sqlite" and (parsed.database in {None, "", ":memory:"})


def _engine_url_for_migration(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _pool_status(engine: Engine) -> str:
    status = getattr(engine.pool, "status", None)
    if callable(status):
        return str(status())
    return engine.pool.__class__.__name__


def _required_string(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RepositoryError(f"{field_name} is required")
    return value


def _require_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise RepositoryError("occurred_at must be timezone-aware")
    return value.astimezone(UTC)


def _coerce_decimal(value: Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RepositoryError("amount must be a Decimal-compatible value") from exc


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return _require_utc_datetime(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized: MutableMapping[str, Any] = {}
        for key, item in value.items():
            normalized[str(key)] = _normalize_json_value(item)
        return dict(normalized)
    if isinstance(value, tuple | list):
        return [_normalize_json_value(item) for item in value]
    return value


__all__ = [
    "DatabaseDialect",
    "DatabaseProfileError",
    "DatabaseProfileSettings",
    "DatabaseReadiness",
    "RepositoryConflict",
    "RepositoryContractProbeRecord",
    "RepositoryContractProbeRepository",
    "RepositoryContractProbeTransaction",
    "RepositoryError",
    "check_database_ready",
    "create_database_engine",
    "resolve_database_profile",
]
