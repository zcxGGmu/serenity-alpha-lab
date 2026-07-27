from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, Integer, MetaData, PrimaryKeyConstraint, String, Table, and_, insert, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import JSON

from serenity_alpha_lab.evidence.prompt_registry import AgentPromptRole, PromptRunBinding


ClockFn = Callable[[], datetime]

AGENT_STAGE_STORE_CONTRACT_VERSION = "research.agent_stage_store@1.0.0"
AGENT_STAGE_CHECKPOINT_SCHEMA_NAME = "research.agent_stage_checkpoint"
AGENT_STAGE_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
AGENT_MODEL_CALL_RECEIPT_SCHEMA_NAME = "research.agent_model_call_receipt"
AGENT_MODEL_CALL_RECEIPT_SCHEMA_VERSION = "1.0.0"
AGENT_RUN_RESUME_PLAN_SCHEMA_NAME = "research.agent_run_resume_plan"
AGENT_RUN_RESUME_PLAN_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_STAGE_ID_RE = re.compile(r"^stage_[0-9a-f]{24}$")


class AgentStageStoreError(RuntimeError):
    """Base error for Agent stage persistence operations."""


class AgentStageStoreConflict(AgentStageStoreError):
    """Raised when immutable stage or model-call metadata conflicts."""


class AgentStageNotFound(AgentStageStoreError):
    """Raised when a stage id is unknown to the store."""


class AgentStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class AgentStageFailurePolicy(StrEnum):
    DEGRADE = "degrade"
    SKIP = "skip"
    FAIL_RUN = "fail_run"


class AgentStageResumeAction(StrEnum):
    RUN = "run"
    REUSE_MODEL_CALL = "reuse_model_call"
    SKIP_REUSED = "skip_reused"
    STOP_FAILED = "stop_failed"
    STOP_CANCELLED = "stop_cancelled"


@dataclass(frozen=True, slots=True)
class AgentStageDefinition:
    run_id: str
    stage_name: str
    role: AgentPromptRole | str
    input_hash: str
    prompt_version: str
    sequence: int
    failure_policy: AgentStageFailurePolicy | str
    max_input_tokens: int
    max_output_tokens: int
    timeout_seconds: int
    max_retries: int
    tool_allowlist: Sequence[str] = ()
    stage_id: str | None = None
    contract_version: str = AGENT_STAGE_STORE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_name", _required_string("stage_name", self.stage_name))
        object.__setattr__(self, "role", AgentPromptRole(self.role))
        object.__setattr__(self, "input_hash", _sha256("input_hash", self.input_hash))
        object.__setattr__(self, "prompt_version", _required_semver("prompt_version", self.prompt_version))
        object.__setattr__(self, "sequence", _non_negative_int("sequence", self.sequence))
        object.__setattr__(self, "failure_policy", AgentStageFailurePolicy(self.failure_policy))
        object.__setattr__(self, "max_input_tokens", _positive_int("max_input_tokens", self.max_input_tokens))
        object.__setattr__(self, "max_output_tokens", _positive_int("max_output_tokens", self.max_output_tokens))
        object.__setattr__(self, "timeout_seconds", _positive_int("timeout_seconds", self.timeout_seconds))
        object.__setattr__(self, "max_retries", _non_negative_int("max_retries", self.max_retries))
        object.__setattr__(
            self,
            "tool_allowlist",
            tuple(_required_string("tool_allowlist item", item) for item in self.tool_allowlist),
        )
        stage_id = self.stage_id or deterministic_agent_stage_id(
            run_id=self.run_id,
            stage_name=self.stage_name,
            input_hash=self.input_hash,
            prompt_version=self.prompt_version,
        )
        object.__setattr__(self, "stage_id", _stage_id(stage_id))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "stage_id": self.stage_id,
            "run_id": self.run_id,
            "stage_name": self.stage_name,
            "role": self.role.value,
            "input_hash": self.input_hash,
            "prompt_version": self.prompt_version,
            "sequence": self.sequence,
            "failure_policy": self.failure_policy.value,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "tool_allowlist": list(self.tool_allowlist),
        }


@dataclass(frozen=True, slots=True)
class AgentModelCallReceipt:
    call_id: str
    idempotency_key: str
    provider_family: str
    model_family: str
    prompt_binding_hash: str
    request_hash: str
    response_hash: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal | str
    latency_ms: int
    completed_at: datetime
    contract_version: str = AGENT_STAGE_STORE_CONTRACT_VERSION
    schema_name: str = AGENT_MODEL_CALL_RECEIPT_SCHEMA_NAME
    schema_version: str = AGENT_MODEL_CALL_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "call_id", _required_string("call_id", self.call_id))
        object.__setattr__(self, "idempotency_key", _required_string("idempotency_key", self.idempotency_key))
        object.__setattr__(self, "provider_family", _required_string("provider_family", self.provider_family))
        object.__setattr__(self, "model_family", _required_string("model_family", self.model_family))
        object.__setattr__(self, "prompt_binding_hash", _sha256("prompt_binding_hash", self.prompt_binding_hash))
        object.__setattr__(self, "request_hash", _sha256("request_hash", self.request_hash))
        object.__setattr__(self, "response_hash", _sha256("response_hash", self.response_hash))
        object.__setattr__(self, "prompt_tokens", _non_negative_int("prompt_tokens", self.prompt_tokens))
        object.__setattr__(self, "completion_tokens", _non_negative_int("completion_tokens", self.completion_tokens))
        object.__setattr__(self, "cost_usd", _decimal_string("cost_usd", self.cost_usd))
        object.__setattr__(self, "latency_ms", _non_negative_int("latency_ms", self.latency_ms))
        object.__setattr__(self, "completed_at", _require_aware_datetime("completed_at", self.completed_at))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def receipt_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "call_id": self.call_id,
            "idempotency_key": self.idempotency_key,
            "provider_family": self.provider_family,
            "model_family": self.model_family,
            "prompt_binding_hash": self.prompt_binding_hash,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "completed_at": self.completed_at.isoformat(),
        }
        if include_hash:
            record["receipt_hash"] = self.receipt_hash
        return record


@dataclass(frozen=True, slots=True)
class AgentStageCheckpoint:
    definition: AgentStageDefinition
    status: AgentStageStatus
    attempt: int
    prompt_binding: Mapping[str, Any]
    prompt_binding_hash: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    failure_reason: str | None = None
    output_hash: str | None = None
    output_record: Mapping[str, Any] | None = None
    contract_version: str = AGENT_STAGE_STORE_CONTRACT_VERSION
    schema_name: str = AGENT_STAGE_CHECKPOINT_SCHEMA_NAME
    schema_version: str = AGENT_STAGE_CHECKPOINT_SCHEMA_VERSION

    @property
    def stage_id(self) -> str:
        return self.definition.stage_id or ""

    @property
    def run_id(self) -> str:
        return self.definition.run_id

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "definition": self.definition.to_record(),
                "status": self.status.value,
                "attempt": self.attempt,
                "prompt_binding": _copy_json_value(self.prompt_binding),
                "prompt_binding_hash": self.prompt_binding_hash,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
                "failure_reason": self.failure_reason,
                "output_hash": self.output_hash,
                "output_record": _copy_json_value(self.output_record) if self.output_record is not None else None,
            }
        )


@dataclass(frozen=True, slots=True)
class AgentStageResumeItem:
    stage_id: str
    status: AgentStageStatus
    action: AgentStageResumeAction
    attempt: int
    reason: str
    model_call_receipt_hash: str | None = None

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "stage_id": self.stage_id,
                "status": self.status.value,
                "action": self.action.value,
                "attempt": self.attempt,
                "reason": self.reason,
                "model_call_receipt_hash": self.model_call_receipt_hash,
            }
        )


@dataclass(frozen=True, slots=True)
class AgentRunResumePlan:
    run_id: str
    items: tuple[AgentStageResumeItem, ...]
    next_stage_id: str | None
    contract_version: str = AGENT_STAGE_STORE_CONTRACT_VERSION
    schema_name: str = AGENT_RUN_RESUME_PLAN_SCHEMA_NAME
    schema_version: str = AGENT_RUN_RESUME_PLAN_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "run_id": self.run_id,
                "items": [item.to_record() for item in self.items],
                "next_stage_id": self.next_stage_id,
            }
        )


_AGENT_STAGE_METADATA = MetaData()

_AGENT_STAGE_TABLE = Table(
    "serenity_agent_stage_checkpoints",
    _AGENT_STAGE_METADATA,
    Column("stage_id", String(128), primary_key=True),
    Column("run_id", String(128), nullable=False),
    Column("stage_name", String(160), nullable=False),
    Column("role", String(64), nullable=False),
    Column("input_hash", String(96), nullable=False),
    Column("prompt_version", String(32), nullable=False),
    Column("sequence", Integer(), nullable=False),
    Column("failure_policy", String(32), nullable=False),
    Column("max_input_tokens", Integer(), nullable=False),
    Column("max_output_tokens", Integer(), nullable=False),
    Column("timeout_seconds", Integer(), nullable=False),
    Column("max_retries", Integer(), nullable=False),
    Column("tool_allowlist_json", JSON(), nullable=False),
    Column("prompt_binding_json", JSON(), nullable=False),
    Column("prompt_binding_hash", String(96), nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempt", Integer(), nullable=False),
    Column("created_at_utc", String(40), nullable=False),
    Column("updated_at_utc", String(40), nullable=False),
    Column("started_at_utc", String(40), nullable=True),
    Column("completed_at_utc", String(40), nullable=True),
    Column("cancelled_at_utc", String(40), nullable=True),
    Column("failure_reason", String(2048), nullable=True),
    Column("output_hash", String(96), nullable=True),
    Column("output_json", JSON(), nullable=True),
)

_AGENT_MODEL_CALL_TABLE = Table(
    "serenity_agent_model_call_receipts",
    _AGENT_STAGE_METADATA,
    Column("idempotency_key", String(255), nullable=False),
    Column("stage_id", String(128), nullable=False),
    Column("run_id", String(128), nullable=False),
    Column("call_id", String(128), nullable=False),
    Column("provider_family", String(128), nullable=False),
    Column("model_family", String(128), nullable=False),
    Column("prompt_binding_hash", String(96), nullable=False),
    Column("request_hash", String(96), nullable=False),
    Column("response_hash", String(96), nullable=False),
    Column("prompt_tokens", Integer(), nullable=False),
    Column("completion_tokens", Integer(), nullable=False),
    Column("cost_usd", String(64), nullable=False),
    Column("latency_ms", Integer(), nullable=False),
    Column("completed_at_utc", String(40), nullable=False),
    Column("receipt_json", JSON(), nullable=False),
    Column("receipt_hash", String(96), nullable=False),
    PrimaryKeyConstraint("idempotency_key", name="pk_serenity_agent_model_call_receipts"),
)


class AgentStageStore:
    """SQLAlchemy-backed Agent stage checkpoint store.

    The store persists stage metadata, prompt bindings and model-call receipts only. It never
    invokes models, tools, providers or worker handlers.
    """

    def __init__(self, engine: Engine, *, clock: ClockFn | None = None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_schema(self) -> None:
        _AGENT_STAGE_METADATA.create_all(
            self._engine,
            tables=[_AGENT_STAGE_TABLE, _AGENT_MODEL_CALL_TABLE],
        )

    def register_stage(
        self,
        definition: AgentStageDefinition,
        *,
        prompt_binding: PromptRunBinding | Mapping[str, Any],
    ) -> AgentStageCheckpoint:
        if type(definition) is not AgentStageDefinition:
            raise AgentStageStoreError("definition must be an AgentStageDefinition")
        binding_record = _prompt_binding_record(prompt_binding)
        _validate_binding_matches_definition(binding_record, definition)
        binding_hash = _sha256("prompt_binding_hash", str(binding_record.get("binding_hash")))
        now = self._now()
        values = {
            **_definition_columns(definition),
            "tool_allowlist_json": list(definition.tool_allowlist),
            "prompt_binding_json": binding_record,
            "prompt_binding_hash": binding_hash,
            "status": AgentStageStatus.PENDING.value,
            "attempt": 0,
            "created_at_utc": _datetime_to_record(now),
            "updated_at_utc": _datetime_to_record(now),
            "started_at_utc": None,
            "completed_at_utc": None,
            "cancelled_at_utc": None,
            "failure_reason": None,
            "output_hash": None,
            "output_json": None,
        }
        with self._engine.begin() as connection:
            existing = self._stage_row(connection, definition.stage_id or "")
            if existing is not None:
                checkpoint = _checkpoint_from_row(existing)
                if _stage_immutable_record(existing) == _stage_immutable_record(values):
                    return checkpoint
                raise AgentStageStoreConflict(f"Agent stage metadata conflict: {definition.stage_id}")
            connection.execute(insert(_AGENT_STAGE_TABLE).values(**values))
            return _checkpoint_from_row(self._require_stage_row(connection, definition.stage_id or ""))

    def get_stage(self, stage_id: str) -> AgentStageCheckpoint:
        with self._engine.connect() as connection:
            row = self._require_stage_row(connection, stage_id)
        return _checkpoint_from_row(row)

    def list_stages(self, run_id: str) -> tuple[AgentStageCheckpoint, ...]:
        normalized_run_id = _required_string("run_id", run_id)
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(_AGENT_STAGE_TABLE)
                    .where(_AGENT_STAGE_TABLE.c.run_id == normalized_run_id)
                    .order_by(_AGENT_STAGE_TABLE.c.sequence, _AGENT_STAGE_TABLE.c.stage_id)
                )
                .mappings()
                .all()
            )
        return tuple(_checkpoint_from_row(row) for row in rows)

    def start_stage(self, stage_id: str, *, attempt: int) -> AgentStageCheckpoint:
        normalized_stage_id = _stage_id(stage_id)
        normalized_attempt = _positive_int("attempt", attempt)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_stage_row(connection, normalized_stage_id)
            checkpoint = _checkpoint_from_row(row)
            if checkpoint.status in {
                AgentStageStatus.SUCCEEDED,
                AgentStageStatus.DEGRADED,
                AgentStageStatus.SKIPPED,
                AgentStageStatus.FAILED,
                AgentStageStatus.CANCELLED,
            }:
                return checkpoint
            if normalized_attempt > checkpoint.definition.max_retries + 1:
                raise AgentStageStoreError("attempt exceeds max_retries")
            connection.execute(
                update(_AGENT_STAGE_TABLE)
                .where(_AGENT_STAGE_TABLE.c.stage_id == normalized_stage_id)
                .values(
                    status=AgentStageStatus.RUNNING.value,
                    attempt=normalized_attempt,
                    started_at_utc=row["started_at_utc"] or _datetime_to_record(now),
                    updated_at_utc=_datetime_to_record(now),
                )
            )
            return _checkpoint_from_row(self._require_stage_row(connection, normalized_stage_id))

    def record_model_call_success(
        self,
        stage_id: str,
        receipt: AgentModelCallReceipt,
    ) -> AgentModelCallReceipt:
        if type(receipt) is not AgentModelCallReceipt:
            raise AgentStageStoreError("receipt must be an AgentModelCallReceipt")
        normalized_stage_id = _stage_id(stage_id)
        with self._engine.begin() as connection:
            stage_row = self._require_stage_row(connection, normalized_stage_id)
            stage = _checkpoint_from_row(stage_row)
            if receipt.prompt_binding_hash != stage.prompt_binding_hash:
                raise AgentStageStoreConflict("Model call prompt binding hash does not match stage checkpoint")
            existing = self._model_call_row(connection, receipt.idempotency_key)
            if existing is not None:
                persisted = _receipt_from_row(existing)
                if persisted == receipt and str(existing["stage_id"]) == normalized_stage_id:
                    return persisted
                raise AgentStageStoreConflict("Model call idempotency conflict")
            values = _receipt_to_row(receipt, stage)
            try:
                connection.execute(insert(_AGENT_MODEL_CALL_TABLE).values(**values))
            except IntegrityError as exc:
                raise AgentStageStoreConflict("Model call idempotency conflict") from exc
        return receipt

    def model_call_receipts(self, stage_id: str) -> tuple[AgentModelCallReceipt, ...]:
        normalized_stage_id = _stage_id(stage_id)
        with self._engine.connect() as connection:
            self._require_stage_row(connection, normalized_stage_id)
            rows = (
                connection.execute(
                    select(_AGENT_MODEL_CALL_TABLE)
                    .where(_AGENT_MODEL_CALL_TABLE.c.stage_id == normalized_stage_id)
                    .order_by(_AGENT_MODEL_CALL_TABLE.c.completed_at_utc, _AGENT_MODEL_CALL_TABLE.c.call_id)
                )
                .mappings()
                .all()
            )
        return tuple(_receipt_from_row(row) for row in rows)

    def complete_stage(
        self,
        stage_id: str,
        *,
        output_hash: str,
        output_record: Mapping[str, Any],
    ) -> AgentStageCheckpoint:
        normalized_stage_id = _stage_id(stage_id)
        normalized_output_hash = _sha256("output_hash", output_hash)
        output_json = _copy_json_value(output_record)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_stage_row(connection, normalized_stage_id)
            checkpoint = _checkpoint_from_row(row)
            if checkpoint.status is AgentStageStatus.SUCCEEDED:
                if checkpoint.output_hash == normalized_output_hash and _copy_json_value(checkpoint.output_record) == output_json:
                    return checkpoint
                raise AgentStageStoreConflict("Stage completion output conflict")
            if checkpoint.status in {AgentStageStatus.CANCELLED, AgentStageStatus.FAILED}:
                raise AgentStageStoreError(f"Stage is terminal: {checkpoint.status.value}")
            connection.execute(
                update(_AGENT_STAGE_TABLE)
                .where(_AGENT_STAGE_TABLE.c.stage_id == normalized_stage_id)
                .values(
                    status=AgentStageStatus.SUCCEEDED.value,
                    output_hash=normalized_output_hash,
                    output_json=output_json,
                    completed_at_utc=_datetime_to_record(now),
                    updated_at_utc=_datetime_to_record(now),
                    failure_reason=None,
                )
            )
            return _checkpoint_from_row(self._require_stage_row(connection, normalized_stage_id))

    def record_stage_failure(self, stage_id: str, *, reason: str) -> AgentStageCheckpoint:
        normalized_stage_id = _stage_id(stage_id)
        failure_reason = _required_string("reason", reason)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_stage_row(connection, normalized_stage_id)
            checkpoint = _checkpoint_from_row(row)
            if checkpoint.status in {AgentStageStatus.SUCCEEDED, AgentStageStatus.DEGRADED, AgentStageStatus.SKIPPED}:
                return checkpoint
            if checkpoint.status is AgentStageStatus.CANCELLED:
                return checkpoint
            status = _status_for_failure_policy(checkpoint.definition.failure_policy)
            connection.execute(
                update(_AGENT_STAGE_TABLE)
                .where(_AGENT_STAGE_TABLE.c.stage_id == normalized_stage_id)
                .values(
                    status=status.value,
                    failure_reason=failure_reason,
                    completed_at_utc=_datetime_to_record(now),
                    updated_at_utc=_datetime_to_record(now),
                )
            )
            return _checkpoint_from_row(self._require_stage_row(connection, normalized_stage_id))

    def request_cancel(self, run_id: str, *, reason: str) -> int:
        normalized_run_id = _required_string("run_id", run_id)
        failure_reason = _required_string("reason", reason)
        now = self._now()
        cancelled = 0
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(_AGENT_STAGE_TABLE)
                    .where(
                        and_(
                            _AGENT_STAGE_TABLE.c.run_id == normalized_run_id,
                            _AGENT_STAGE_TABLE.c.status.in_(
                                [AgentStageStatus.PENDING.value, AgentStageStatus.RUNNING.value]
                            ),
                        )
                    )
                    .order_by(_AGENT_STAGE_TABLE.c.sequence, _AGENT_STAGE_TABLE.c.stage_id)
                )
                .mappings()
                .all()
            )
            for row in rows:
                connection.execute(
                    update(_AGENT_STAGE_TABLE)
                    .where(_AGENT_STAGE_TABLE.c.stage_id == row["stage_id"])
                    .values(
                        status=AgentStageStatus.CANCELLED.value,
                        cancelled_at_utc=_datetime_to_record(now),
                        updated_at_utc=_datetime_to_record(now),
                        failure_reason=failure_reason,
                    )
                )
                cancelled += 1
        return cancelled

    def resume_plan(self, run_id: str) -> AgentRunResumePlan:
        stages = self.list_stages(run_id)
        items: list[AgentStageResumeItem] = []
        next_stage_id: str | None = None
        with self._engine.connect() as connection:
            for stage in stages:
                receipt_hash = self._latest_receipt_hash(connection, stage.stage_id)
                action, reason = _resume_action(stage, receipt_hash=receipt_hash)
                if next_stage_id is None and action in {
                    AgentStageResumeAction.RUN,
                    AgentStageResumeAction.REUSE_MODEL_CALL,
                }:
                    next_stage_id = stage.stage_id
                items.append(
                    AgentStageResumeItem(
                        stage_id=stage.stage_id,
                        status=stage.status,
                        action=action,
                        attempt=stage.attempt,
                        reason=reason,
                        model_call_receipt_hash=receipt_hash,
                    )
                )
                if action in {AgentStageResumeAction.STOP_CANCELLED, AgentStageResumeAction.STOP_FAILED}:
                    break
        return AgentRunResumePlan(run_id=_required_string("run_id", run_id), items=tuple(items), next_stage_id=next_stage_id)

    def _now(self) -> datetime:
        return _require_aware_datetime("clock", self._clock())

    def _stage_row(self, connection: Connection, stage_id: str) -> Mapping[str, Any] | None:
        return (
            connection.execute(select(_AGENT_STAGE_TABLE).where(_AGENT_STAGE_TABLE.c.stage_id == _stage_id(stage_id)))
            .mappings()
            .one_or_none()
        )

    def _require_stage_row(self, connection: Connection, stage_id: str) -> Mapping[str, Any]:
        row = self._stage_row(connection, stage_id)
        if row is None:
            raise AgentStageNotFound(f"Agent stage not found: {stage_id}")
        return row

    def _model_call_row(self, connection: Connection, idempotency_key: str) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(_AGENT_MODEL_CALL_TABLE).where(
                    _AGENT_MODEL_CALL_TABLE.c.idempotency_key == _required_string("idempotency_key", idempotency_key)
                )
            )
            .mappings()
            .one_or_none()
        )

    def _latest_receipt_hash(self, connection: Connection, stage_id: str) -> str | None:
        row = (
            connection.execute(
                select(_AGENT_MODEL_CALL_TABLE)
                .where(_AGENT_MODEL_CALL_TABLE.c.stage_id == _stage_id(stage_id))
                .order_by(_AGENT_MODEL_CALL_TABLE.c.completed_at_utc.desc(), _AGENT_MODEL_CALL_TABLE.c.call_id.desc())
                .limit(1)
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else str(row["receipt_hash"])


def deterministic_agent_stage_id(
    *,
    run_id: str,
    stage_name: str,
    input_hash: str,
    prompt_version: str,
) -> str:
    payload = {
        "run_id": _required_string("run_id", run_id),
        "stage_name": _required_string("stage_name", stage_name),
        "input_hash": _sha256("input_hash", input_hash),
        "prompt_version": _required_semver("prompt_version", prompt_version),
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:24]
    return f"stage_{digest}"


def _status_for_failure_policy(policy: AgentStageFailurePolicy) -> AgentStageStatus:
    if policy is AgentStageFailurePolicy.DEGRADE:
        return AgentStageStatus.DEGRADED
    if policy is AgentStageFailurePolicy.SKIP:
        return AgentStageStatus.SKIPPED
    return AgentStageStatus.FAILED


def _resume_action(stage: AgentStageCheckpoint, *, receipt_hash: str | None) -> tuple[AgentStageResumeAction, str]:
    if stage.status in {AgentStageStatus.SUCCEEDED, AgentStageStatus.DEGRADED, AgentStageStatus.SKIPPED}:
        return AgentStageResumeAction.SKIP_REUSED, f"{stage.status.value} checkpoint already persisted"
    if stage.status is AgentStageStatus.RUNNING and receipt_hash is not None:
        return AgentStageResumeAction.REUSE_MODEL_CALL, "model call receipt already persisted"
    if stage.status in {AgentStageStatus.PENDING, AgentStageStatus.RUNNING}:
        return AgentStageResumeAction.RUN, "stage needs execution by caller"
    if stage.status is AgentStageStatus.CANCELLED:
        return AgentStageResumeAction.STOP_CANCELLED, "run was cancelled"
    return AgentStageResumeAction.STOP_FAILED, "stage failed with fail_run policy"


def _definition_columns(definition: AgentStageDefinition) -> dict[str, Any]:
    return {
        "stage_id": definition.stage_id,
        "run_id": definition.run_id,
        "stage_name": definition.stage_name,
        "role": definition.role.value,
        "input_hash": definition.input_hash,
        "prompt_version": definition.prompt_version,
        "sequence": definition.sequence,
        "failure_policy": definition.failure_policy.value,
        "max_input_tokens": definition.max_input_tokens,
        "max_output_tokens": definition.max_output_tokens,
        "timeout_seconds": definition.timeout_seconds,
        "max_retries": definition.max_retries,
    }


def _stage_immutable_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage_id": str(row["stage_id"]),
        "run_id": str(row["run_id"]),
        "stage_name": str(row["stage_name"]),
        "role": str(row["role"]),
        "input_hash": str(row["input_hash"]),
        "prompt_version": str(row["prompt_version"]),
        "sequence": int(row["sequence"]),
        "failure_policy": str(row["failure_policy"]),
        "max_input_tokens": int(row["max_input_tokens"]),
        "max_output_tokens": int(row["max_output_tokens"]),
        "timeout_seconds": int(row["timeout_seconds"]),
        "max_retries": int(row["max_retries"]),
        "tool_allowlist_json": _copy_json_value(row["tool_allowlist_json"]),
        "prompt_binding_json": _copy_json_value(row["prompt_binding_json"]),
        "prompt_binding_hash": str(row["prompt_binding_hash"]),
    }


def _checkpoint_from_row(row: Mapping[str, Any]) -> AgentStageCheckpoint:
    definition = AgentStageDefinition(
        stage_id=str(row["stage_id"]),
        run_id=str(row["run_id"]),
        stage_name=str(row["stage_name"]),
        role=AgentPromptRole(str(row["role"])),
        input_hash=str(row["input_hash"]),
        prompt_version=str(row["prompt_version"]),
        sequence=int(row["sequence"]),
        failure_policy=AgentStageFailurePolicy(str(row["failure_policy"])),
        max_input_tokens=int(row["max_input_tokens"]),
        max_output_tokens=int(row["max_output_tokens"]),
        timeout_seconds=int(row["timeout_seconds"]),
        max_retries=int(row["max_retries"]),
        tool_allowlist=tuple(str(item) for item in _copy_json_value(row["tool_allowlist_json"])),
    )
    return AgentStageCheckpoint(
        definition=definition,
        status=AgentStageStatus(str(row["status"])),
        attempt=int(row["attempt"]),
        prompt_binding=_copy_json_value(row["prompt_binding_json"]),
        prompt_binding_hash=str(row["prompt_binding_hash"]),
        created_at=_datetime_from_record(row["created_at_utc"]),
        updated_at=_datetime_from_record(row["updated_at_utc"]),
        started_at=_optional_datetime(row["started_at_utc"]),
        completed_at=_optional_datetime(row["completed_at_utc"]),
        cancelled_at=_optional_datetime(row["cancelled_at_utc"]),
        failure_reason=row["failure_reason"],
        output_hash=row["output_hash"],
        output_record=_copy_json_value(row["output_json"]) if row["output_json"] is not None else None,
    )


def _prompt_binding_record(prompt_binding: PromptRunBinding | Mapping[str, Any]) -> dict[str, Any]:
    if type(prompt_binding) is PromptRunBinding:
        return prompt_binding.to_record()
    if isinstance(prompt_binding, Mapping):
        record = _copy_json_value(prompt_binding)
        if type(record) is dict:
            return record
    raise AgentStageStoreError("prompt_binding must be a PromptRunBinding or mapping")


def _validate_binding_matches_definition(
    binding_record: Mapping[str, Any],
    definition: AgentStageDefinition,
) -> None:
    expected = {
        "run_id": definition.run_id,
        "stage_id": definition.stage_id,
        "role": definition.role.value,
        "prompt_version": definition.prompt_version,
    }
    actual_prompt = binding_record.get("prompt")
    actual_prompt_version = actual_prompt.get("prompt_version") if isinstance(actual_prompt, Mapping) else None
    actual = {
        "run_id": binding_record.get("run_id"),
        "stage_id": binding_record.get("stage_id"),
        "role": binding_record.get("role"),
        "prompt_version": actual_prompt_version,
    }
    mismatches = [key for key, value in expected.items() if actual.get(key) != value]
    if mismatches:
        raise AgentStageStoreConflict("Prompt run binding does not match stage definition: " + ", ".join(mismatches))


def _receipt_to_row(receipt: AgentModelCallReceipt, stage: AgentStageCheckpoint) -> dict[str, Any]:
    return {
        "idempotency_key": receipt.idempotency_key,
        "stage_id": stage.stage_id,
        "run_id": stage.run_id,
        "call_id": receipt.call_id,
        "provider_family": receipt.provider_family,
        "model_family": receipt.model_family,
        "prompt_binding_hash": receipt.prompt_binding_hash,
        "request_hash": receipt.request_hash,
        "response_hash": receipt.response_hash,
        "prompt_tokens": receipt.prompt_tokens,
        "completion_tokens": receipt.completion_tokens,
        "cost_usd": receipt.cost_usd,
        "latency_ms": receipt.latency_ms,
        "completed_at_utc": _datetime_to_record(receipt.completed_at),
        "receipt_json": receipt.to_record(),
        "receipt_hash": receipt.receipt_hash,
    }


def _receipt_from_row(row: Mapping[str, Any]) -> AgentModelCallReceipt:
    return AgentModelCallReceipt(
        call_id=str(row["call_id"]),
        idempotency_key=str(row["idempotency_key"]),
        provider_family=str(row["provider_family"]),
        model_family=str(row["model_family"]),
        prompt_binding_hash=str(row["prompt_binding_hash"]),
        request_hash=str(row["request_hash"]),
        response_hash=str(row["response_hash"]),
        prompt_tokens=int(row["prompt_tokens"]),
        completion_tokens=int(row["completion_tokens"]),
        cost_usd=str(row["cost_usd"]),
        latency_ms=int(row["latency_ms"]),
        completed_at=_datetime_from_record(row["completed_at_utc"]),
    )


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise AgentStageStoreError(f"{field_name} is required")
    return value


def _stage_id(value: str) -> str:
    value = _required_string("stage_id", value)
    if not _STAGE_ID_RE.fullmatch(value):
        raise AgentStageStoreError("stage_id must be generated by deterministic_agent_stage_id")
    return value


def _required_semver(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SEMVER_RE.fullmatch(value):
        raise AgentStageStoreError(f"{field_name} must be a semantic version")
    return value


def _sha256(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(value):
        raise AgentStageStoreError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return value


def _positive_int(field_name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise AgentStageStoreError(f"{field_name} must be a positive integer")
    return value


def _non_negative_int(field_name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise AgentStageStoreError(f"{field_name} must be a non-negative integer")
    return value


def _decimal_string(field_name: str, value: Decimal | str) -> str:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise AgentStageStoreError(f"{field_name} must be a decimal") from exc
    if parsed < 0:
        raise AgentStageStoreError(f"{field_name} must be non-negative")
    return format(parsed, "f")


def _require_aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise AgentStageStoreError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _datetime_to_record(value: datetime) -> str:
    return _require_aware_datetime("datetime", value).isoformat()


def _datetime_from_record(value: Any) -> datetime:
    return datetime.fromisoformat(str(value)).astimezone(UTC)


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _datetime_from_record(value)


def _copy_json_value(value: Any) -> Any:
    return json.loads(_canonical_json(_plain_json_value(value)))


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return _require_aware_datetime("datetime", value).isoformat()
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise AgentStageStoreError("value must be JSON serializable") from exc


def _hash_record(record: Mapping[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(record).encode('utf-8')).hexdigest()}"


def _drop_none(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


__all__ = [
    "AGENT_MODEL_CALL_RECEIPT_SCHEMA_NAME",
    "AGENT_MODEL_CALL_RECEIPT_SCHEMA_VERSION",
    "AGENT_RUN_RESUME_PLAN_SCHEMA_NAME",
    "AGENT_RUN_RESUME_PLAN_SCHEMA_VERSION",
    "AGENT_STAGE_CHECKPOINT_SCHEMA_NAME",
    "AGENT_STAGE_CHECKPOINT_SCHEMA_VERSION",
    "AGENT_STAGE_STORE_CONTRACT_VERSION",
    "AgentModelCallReceipt",
    "AgentRunResumePlan",
    "AgentStageCheckpoint",
    "AgentStageDefinition",
    "AgentStageFailurePolicy",
    "AgentStageNotFound",
    "AgentStageResumeAction",
    "AgentStageResumeItem",
    "AgentStageStatus",
    "AgentStageStore",
    "AgentStageStoreConflict",
    "AgentStageStoreError",
    "deterministic_agent_stage_id",
]
