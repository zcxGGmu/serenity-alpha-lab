from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, Integer, MetaData, String, Table, UniqueConstraint, and_, insert, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import JSON

from serenity_alpha_lab.evidence.report_renderer import RenderedResearchReport


NOTIFICATION_OUTBOX_CONTRACT_VERSION = "research.notification_outbox@1.0.0"
NOTIFICATION_OUTBOX_SCHEMA_NAME = "research.notification_outbox_message"
NOTIFICATION_OUTBOX_SCHEMA_VERSION = "1.0.0"


class NotificationOutboxError(RuntimeError):
    """Base error for report notification Outbox operations."""


class NotificationOutboxConflict(NotificationOutboxError):
    """Raised when a dedupe key is reused for a different immutable message."""


class NotificationOutboxNotFound(NotificationOutboxError):
    """Raised when an Outbox message id is unknown."""


class NotificationChannel(StrEnum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SLACK = "slack"
    TELEGRAM = "telegram"
    WECHAT = "wechat"
    DESKTOP = "desktop"


class NotificationOutboxStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class NotificationOutboxMessage:
    message_id: str
    tenant_id: str
    channel: NotificationChannel
    dedupe_key: str
    status: NotificationOutboxStatus
    attempt: int
    max_attempts: int
    report_id: str
    report_hash: str
    rendering_hash: str
    recipient: Mapping[str, Any]
    payload: Mapping[str, Any]
    created_at: datetime
    updated_at: datetime
    next_attempt_at: datetime
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    sent_at: datetime | None = None
    provider_receipt_id: str | None = None
    last_error: str | None = None
    immutable_hash: str | None = None
    contract_version: str = NOTIFICATION_OUTBOX_CONTRACT_VERSION
    schema_name: str = NOTIFICATION_OUTBOX_SCHEMA_NAME
    schema_version: str = NOTIFICATION_OUTBOX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "message_id", _required_string("message_id", self.message_id))
        object.__setattr__(self, "tenant_id", _required_string("tenant_id", self.tenant_id))
        object.__setattr__(self, "channel", NotificationChannel(self.channel))
        object.__setattr__(self, "dedupe_key", _required_string("dedupe_key", self.dedupe_key))
        object.__setattr__(self, "status", NotificationOutboxStatus(self.status))
        object.__setattr__(self, "attempt", _non_negative_int("attempt", self.attempt))
        object.__setattr__(self, "max_attempts", _positive_int("max_attempts", self.max_attempts))
        object.__setattr__(self, "report_id", _required_string("report_id", self.report_id))
        object.__setattr__(self, "report_hash", _sha256("report_hash", self.report_hash))
        object.__setattr__(self, "rendering_hash", _sha256("rendering_hash", self.rendering_hash))
        object.__setattr__(self, "recipient", _json_mapping("recipient", self.recipient))
        object.__setattr__(self, "payload", _json_mapping("payload", self.payload))
        object.__setattr__(self, "created_at", _require_aware_datetime("created_at", self.created_at))
        object.__setattr__(self, "updated_at", _require_aware_datetime("updated_at", self.updated_at))
        object.__setattr__(self, "next_attempt_at", _require_aware_datetime("next_attempt_at", self.next_attempt_at))
        object.__setattr__(self, "lease_owner", _optional_string(self.lease_owner))
        object.__setattr__(self, "lease_expires_at", _optional_datetime("lease_expires_at", self.lease_expires_at))
        object.__setattr__(self, "sent_at", _optional_datetime("sent_at", self.sent_at))
        object.__setattr__(self, "provider_receipt_id", _optional_string(self.provider_receipt_id))
        object.__setattr__(self, "last_error", _optional_string(self.last_error))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "immutable_hash", self.immutable_hash or _message_immutable_hash(self))

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "message_id": self.message_id,
                "tenant_id": self.tenant_id,
                "channel": self.channel.value,
                "dedupe_key": self.dedupe_key,
                "status": self.status.value,
                "attempt": self.attempt,
                "max_attempts": self.max_attempts,
                "report_id": self.report_id,
                "report_hash": self.report_hash,
                "rendering_hash": self.rendering_hash,
                "recipient": _json_copy(self.recipient),
                "payload": _json_copy(self.payload),
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "next_attempt_at": self.next_attempt_at.isoformat(),
                "lease_owner": self.lease_owner,
                "lease_expires_at": self.lease_expires_at.isoformat() if self.lease_expires_at else None,
                "sent_at": self.sent_at.isoformat() if self.sent_at else None,
                "provider_receipt_id": self.provider_receipt_id,
                "last_error": self.last_error,
                "immutable_hash": self.immutable_hash,
            }
        )


_OUTBOX_METADATA = MetaData()
_OUTBOX_TABLE = Table(
    "serenity_notification_outbox_messages",
    _OUTBOX_METADATA,
    Column("message_id", String(96), primary_key=True),
    Column("tenant_id", String(128), nullable=False),
    Column("channel", String(40), nullable=False),
    Column("dedupe_key", String(255), nullable=False),
    Column("status", String(40), nullable=False),
    Column("attempt", Integer(), nullable=False),
    Column("max_attempts", Integer(), nullable=False),
    Column("report_id", String(128), nullable=False),
    Column("report_hash", String(80), nullable=False),
    Column("rendering_hash", String(80), nullable=False),
    Column("recipient_json", JSON(), nullable=False),
    Column("payload_json", JSON(), nullable=False),
    Column("created_at_utc", String(40), nullable=False),
    Column("updated_at_utc", String(40), nullable=False),
    Column("next_attempt_at_utc", String(40), nullable=False),
    Column("lease_owner", String(160), nullable=True),
    Column("lease_expires_at_utc", String(40), nullable=True),
    Column("sent_at_utc", String(40), nullable=True),
    Column("provider_receipt_id", String(255), nullable=True),
    Column("last_error", String(2048), nullable=True),
    Column("immutable_hash", String(80), nullable=False),
    Column("contract_version", String(80), nullable=False),
    Column("schema_name", String(80), nullable=False),
    Column("schema_version", String(40), nullable=False),
    UniqueConstraint("tenant_id", "channel", "dedupe_key", name="uq_serenity_notification_outbox_dedupe"),
)


class NotificationOutboxStore:
    """SQLAlchemy-backed transactional Outbox for report notification metadata.

    This store never calls email, webhook or Bot sender code. Senders lease rows, perform their
    side effects outside this repository, then mark the row sent or failed with a receipt/error.
    """

    def __init__(self, engine: Engine, *, clock=None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_schema(self) -> None:
        _OUTBOX_METADATA.create_all(self._engine, tables=[_OUTBOX_TABLE])

    def enqueue_report_notification(
        self,
        *,
        tenant_id: str,
        channel: NotificationChannel | str,
        dedupe_key: str,
        rendered_report: RenderedResearchReport,
        recipient: Mapping[str, Any],
        payload: Mapping[str, Any],
        max_attempts: int = 3,
    ) -> NotificationOutboxMessage:
        tenant = _required_string("tenant_id", tenant_id)
        normalized_channel = NotificationChannel(channel)
        normalized_dedupe_key = _required_string("dedupe_key", dedupe_key)
        if type(rendered_report) is not RenderedResearchReport:
            raise NotificationOutboxError("rendered_report must be a RenderedResearchReport")
        now = self._now()
        message = NotificationOutboxMessage(
            message_id=_deterministic_message_id(
                tenant_id=tenant,
                channel=normalized_channel,
                dedupe_key=normalized_dedupe_key,
            ),
            tenant_id=tenant,
            channel=normalized_channel,
            dedupe_key=normalized_dedupe_key,
            status=NotificationOutboxStatus.PENDING,
            attempt=0,
            max_attempts=max_attempts,
            report_id=rendered_report.trusted_report.authoritative_json["report_id"],
            report_hash=rendered_report.trusted_report.authoritative_json_hash,
            rendering_hash=rendered_report.rendering_hash,
            recipient=recipient,
            payload=payload,
            created_at=now,
            updated_at=now,
            next_attempt_at=now,
        )
        with self._engine.begin() as connection:
            existing = self._row_by_dedupe(
                connection,
                tenant_id=message.tenant_id,
                channel=message.channel,
                dedupe_key=message.dedupe_key,
            )
            if existing is not None:
                persisted = _message_from_row(existing)
                if persisted.immutable_hash != message.immutable_hash:
                    raise NotificationOutboxConflict(
                        f"dedupe_key reused for different notification message: {message.dedupe_key}"
                    )
                return persisted
            try:
                connection.execute(insert(_OUTBOX_TABLE).values(**_message_to_row(message)))
            except IntegrityError as exc:
                raise NotificationOutboxConflict(
                    f"dedupe_key reused for different notification message: {message.dedupe_key}"
                ) from exc
        return message

    def lease_pending(
        self,
        *,
        tenant_id: str,
        channel: NotificationChannel | str,
        worker_id: str,
        lease_seconds: int,
        limit: int = 10,
    ) -> tuple[NotificationOutboxMessage, ...]:
        tenant = _required_string("tenant_id", tenant_id)
        normalized_channel = NotificationChannel(channel)
        worker = _required_string("worker_id", worker_id)
        seconds = _positive_int("lease_seconds", lease_seconds)
        max_rows = _positive_int("limit", limit)
        now = self._now()
        lease_expires_at = now + timedelta(seconds=seconds)
        leased: list[NotificationOutboxMessage] = []
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(_OUTBOX_TABLE)
                    .where(
                        and_(
                            _OUTBOX_TABLE.c.tenant_id == tenant,
                            _OUTBOX_TABLE.c.channel == normalized_channel.value,
                            _OUTBOX_TABLE.c.status.in_(
                                [NotificationOutboxStatus.PENDING.value, NotificationOutboxStatus.SENDING.value]
                            ),
                            _OUTBOX_TABLE.c.next_attempt_at_utc <= _datetime_to_record(now),
                            _OUTBOX_TABLE.c.attempt < _OUTBOX_TABLE.c.max_attempts,
                        )
                    )
                    .order_by(_OUTBOX_TABLE.c.next_attempt_at_utc, _OUTBOX_TABLE.c.created_at_utc, _OUTBOX_TABLE.c.message_id)
                    .limit(max_rows)
                )
                .mappings()
                .all()
            )
            for row in rows:
                if row["status"] == NotificationOutboxStatus.SENDING.value:
                    lease_expires_at_utc = row["lease_expires_at_utc"]
                    if lease_expires_at_utc is not None and _datetime_from_record(lease_expires_at_utc) > now:
                        continue
                next_attempt = int(row["attempt"]) + 1
                connection.execute(
                    update(_OUTBOX_TABLE)
                    .where(_OUTBOX_TABLE.c.message_id == row["message_id"])
                    .values(
                        status=NotificationOutboxStatus.SENDING.value,
                        attempt=next_attempt,
                        updated_at_utc=_datetime_to_record(now),
                        lease_owner=worker,
                        lease_expires_at_utc=_datetime_to_record(lease_expires_at),
                        last_error=None,
                    )
                )
                updated = self._require_row(connection, str(row["message_id"]))
                leased.append(_message_from_row(updated))
        return tuple(leased)

    def mark_sent(
        self,
        message_id: str,
        *,
        worker_id: str,
        provider_receipt_id: str,
    ) -> NotificationOutboxMessage:
        message = _required_string("message_id", message_id)
        worker = _required_string("worker_id", worker_id)
        receipt = _required_string("provider_receipt_id", provider_receipt_id)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_leased_row(connection, message, worker_id=worker)
            connection.execute(
                update(_OUTBOX_TABLE)
                .where(_OUTBOX_TABLE.c.message_id == row["message_id"])
                .values(
                    status=NotificationOutboxStatus.SENT.value,
                    updated_at_utc=_datetime_to_record(now),
                    lease_owner=None,
                    lease_expires_at_utc=None,
                    sent_at_utc=_datetime_to_record(now),
                    provider_receipt_id=receipt,
                    last_error=None,
                )
            )
            return _message_from_row(self._require_row(connection, message))

    def mark_failed(
        self,
        message_id: str,
        *,
        worker_id: str,
        error: str,
        retry_delay_seconds: int = 0,
    ) -> NotificationOutboxMessage:
        message = _required_string("message_id", message_id)
        worker = _required_string("worker_id", worker_id)
        failure = _required_string("error", error)
        if type(retry_delay_seconds) is not int or retry_delay_seconds < 0:
            raise NotificationOutboxError("retry_delay_seconds must be a non-negative integer")
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_leased_row(connection, message, worker_id=worker)
            attempt = int(row["attempt"])
            max_attempts = int(row["max_attempts"])
            next_status = (
                NotificationOutboxStatus.DEAD_LETTER
                if attempt >= max_attempts
                else NotificationOutboxStatus.PENDING
            )
            connection.execute(
                update(_OUTBOX_TABLE)
                .where(_OUTBOX_TABLE.c.message_id == row["message_id"])
                .values(
                    status=next_status.value,
                    updated_at_utc=_datetime_to_record(now),
                    next_attempt_at_utc=_datetime_to_record(now + timedelta(seconds=retry_delay_seconds)),
                    lease_owner=None,
                    lease_expires_at_utc=None,
                    last_error=failure,
                )
            )
            return _message_from_row(self._require_row(connection, message))

    def get_message(self, message_id: str) -> NotificationOutboxMessage:
        with self._engine.connect() as connection:
            return _message_from_row(self._require_row(connection, _required_string("message_id", message_id)))

    def list_messages(self, *, tenant_id: str) -> tuple[NotificationOutboxMessage, ...]:
        tenant = _required_string("tenant_id", tenant_id)
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(_OUTBOX_TABLE)
                    .where(_OUTBOX_TABLE.c.tenant_id == tenant)
                    .order_by(_OUTBOX_TABLE.c.created_at_utc, _OUTBOX_TABLE.c.message_id)
                )
                .mappings()
                .all()
            )
        return tuple(_message_from_row(row) for row in rows)

    def _row_by_dedupe(
        self,
        connection: Connection,
        *,
        tenant_id: str,
        channel: NotificationChannel,
        dedupe_key: str,
    ) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(_OUTBOX_TABLE).where(
                    and_(
                        _OUTBOX_TABLE.c.tenant_id == tenant_id,
                        _OUTBOX_TABLE.c.channel == channel.value,
                        _OUTBOX_TABLE.c.dedupe_key == dedupe_key,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    def _require_row(self, connection: Connection, message_id: str) -> Mapping[str, Any]:
        row = (
            connection.execute(select(_OUTBOX_TABLE).where(_OUTBOX_TABLE.c.message_id == message_id))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise NotificationOutboxNotFound(f"Notification Outbox message not found: {message_id}")
        return row

    def _require_leased_row(self, connection: Connection, message_id: str, *, worker_id: str) -> Mapping[str, Any]:
        row = self._require_row(connection, message_id)
        if row["status"] != NotificationOutboxStatus.SENDING.value:
            raise NotificationOutboxError(f"Notification Outbox message is not leased for sending: {message_id}")
        if row["lease_owner"] != worker_id:
            raise NotificationOutboxError(f"Notification Outbox lease is owned by another worker: {message_id}")
        return row

    def _now(self) -> datetime:
        return _require_aware_datetime("clock", self._clock())


def _message_to_row(message: NotificationOutboxMessage) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "tenant_id": message.tenant_id,
        "channel": message.channel.value,
        "dedupe_key": message.dedupe_key,
        "status": message.status.value,
        "attempt": message.attempt,
        "max_attempts": message.max_attempts,
        "report_id": message.report_id,
        "report_hash": message.report_hash,
        "rendering_hash": message.rendering_hash,
        "recipient_json": _json_copy(message.recipient),
        "payload_json": _json_copy(message.payload),
        "created_at_utc": _datetime_to_record(message.created_at),
        "updated_at_utc": _datetime_to_record(message.updated_at),
        "next_attempt_at_utc": _datetime_to_record(message.next_attempt_at),
        "lease_owner": message.lease_owner,
        "lease_expires_at_utc": _datetime_to_record(message.lease_expires_at) if message.lease_expires_at else None,
        "sent_at_utc": _datetime_to_record(message.sent_at) if message.sent_at else None,
        "provider_receipt_id": message.provider_receipt_id,
        "last_error": message.last_error,
        "immutable_hash": message.immutable_hash,
        "contract_version": message.contract_version,
        "schema_name": message.schema_name,
        "schema_version": message.schema_version,
    }


def _message_from_row(row: Mapping[str, Any]) -> NotificationOutboxMessage:
    return NotificationOutboxMessage(
        message_id=str(row["message_id"]),
        tenant_id=str(row["tenant_id"]),
        channel=NotificationChannel(str(row["channel"])),
        dedupe_key=str(row["dedupe_key"]),
        status=NotificationOutboxStatus(str(row["status"])),
        attempt=int(row["attempt"]),
        max_attempts=int(row["max_attempts"]),
        report_id=str(row["report_id"]),
        report_hash=str(row["report_hash"]),
        rendering_hash=str(row["rendering_hash"]),
        recipient=_json_mapping("recipient", row["recipient_json"]),
        payload=_json_mapping("payload", row["payload_json"]),
        created_at=_datetime_from_record(row["created_at_utc"]),
        updated_at=_datetime_from_record(row["updated_at_utc"]),
        next_attempt_at=_datetime_from_record(row["next_attempt_at_utc"]),
        lease_owner=row["lease_owner"],
        lease_expires_at=_optional_datetime("lease_expires_at", row["lease_expires_at_utc"]),
        sent_at=_optional_datetime("sent_at", row["sent_at_utc"]),
        provider_receipt_id=row["provider_receipt_id"],
        last_error=row["last_error"],
        immutable_hash=str(row["immutable_hash"]),
        contract_version=str(row["contract_version"]),
        schema_name=str(row["schema_name"]),
        schema_version=str(row["schema_version"]),
    )


def _deterministic_message_id(*, tenant_id: str, channel: NotificationChannel, dedupe_key: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}\0{channel.value}\0{dedupe_key}".encode("utf-8")).hexdigest()
    return f"msg_{digest[:32]}"


def _message_immutable_hash(message: NotificationOutboxMessage) -> str:
    return _hash_record(
        {
            "tenant_id": message.tenant_id,
            "channel": message.channel.value,
            "dedupe_key": message.dedupe_key,
            "report_id": message.report_id,
            "report_hash": message.report_hash,
            "rendering_hash": message.rendering_hash,
            "recipient": message.recipient,
            "payload": message.payload,
            "max_attempts": message.max_attempts,
            "contract_version": message.contract_version,
            "schema_name": message.schema_name,
            "schema_version": message.schema_version,
        }
    )


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise NotificationOutboxError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _positive_int(field_name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise NotificationOutboxError(f"{field_name} must be a positive integer")
    return value


def _non_negative_int(field_name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise NotificationOutboxError(f"{field_name} must be a non-negative integer")
    return value


def _sha256(field_name: str, value: str) -> str:
    normalized = _required_string(field_name, value)
    if not normalized.startswith("sha256:") or len(normalized) != 71:
        raise NotificationOutboxError(f"{field_name} must be sha256:<64 hex>")
    try:
        int(normalized.removeprefix("sha256:"), 16)
    except ValueError as exc:
        raise NotificationOutboxError(f"{field_name} must be sha256:<64 hex>") from exc
    return normalized.lower()


def _require_aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise NotificationOutboxError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _optional_datetime(field_name: str, value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _require_aware_datetime(field_name, value)
    return _datetime_from_record(value)


def _datetime_to_record(value: datetime) -> str:
    return _require_aware_datetime("datetime", value).isoformat()


def _datetime_from_record(value: Any) -> datetime:
    return datetime.fromisoformat(str(value)).astimezone(UTC)


def _json_mapping(field_name: str, value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise NotificationOutboxError(f"{field_name} must be a mapping")
    return _json_copy(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    if isinstance(value, datetime):
        return _require_aware_datetime("datetime", value).isoformat()
    if isinstance(value, StrEnum):
        return value.value
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise NotificationOutboxError("value must be JSON serializable") from exc


def _json_copy(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _hash_record(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


__all__ = [
    "NOTIFICATION_OUTBOX_CONTRACT_VERSION",
    "NOTIFICATION_OUTBOX_SCHEMA_NAME",
    "NOTIFICATION_OUTBOX_SCHEMA_VERSION",
    "NotificationChannel",
    "NotificationOutboxConflict",
    "NotificationOutboxError",
    "NotificationOutboxMessage",
    "NotificationOutboxNotFound",
    "NotificationOutboxStatus",
    "NotificationOutboxStore",
]
