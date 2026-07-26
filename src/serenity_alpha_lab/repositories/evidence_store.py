from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

from serenity_alpha_lab.domain.artifacts import (
    ArtifactRetentionTier,
    ArtifactStore,
)
from serenity_alpha_lab.evidence.schema import EvidenceRecord


EVIDENCE_BODY_SCHEMA_NAME = "research.evidence_body"
EVIDENCE_BODY_SCHEMA_VERSION = "1.0.0"
EVIDENCE_BODY_CONTENT_TYPE = "application/vnd.serenity.evidence.body+json"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@=-]{0,127}$")


class EvidenceStoreError(ValueError):
    """Base error for Evidence Store contract violations."""


class EvidenceStoreAccessDenied(EvidenceStoreError):
    """Raised when a caller cannot read evidence in a requested scope."""


class EvidenceStoreConflict(EvidenceStoreError):
    """Raised when immutable evidence metadata conflicts with an existing record."""


class EvidenceStoreNotFound(EvidenceStoreError):
    """Raised when evidence metadata or revision metadata is absent."""


class EvidenceAccessScope(StrEnum):
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


class EvidenceRevisionReason(StrEnum):
    CORRECTION = "correction"
    SOURCE_REVISION = "source_revision"
    POLICY_RECLASSIFICATION = "policy_reclassification"
    REDACTION = "redaction"


@dataclass(frozen=True, slots=True)
class PersistedEvidence:
    evidence: EvidenceRecord
    tenant_id: str
    access_scope: EvidenceAccessScope
    body_artifact_id: str
    body_uri: str
    body_sha256: str
    created_at: datetime
    retention_tier: ArtifactRetentionTier
    team_id: str | None = None
    owner_user_id: str | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> PersistedEvidence:
        return cls(
            evidence=EvidenceRecord.model_validate(record["evidence"]),
            tenant_id=_required_string("tenant_id", record["tenant_id"]),
            team_id=_optional_string(record.get("team_id")),
            owner_user_id=_optional_string(record.get("owner_user_id")),
            access_scope=EvidenceAccessScope(str(record["access_scope"])),
            body_artifact_id=_required_string("body_artifact_id", record["body_artifact_id"]),
            body_uri=_required_string("body_uri", record["body_uri"]),
            body_sha256=_sha256_with_algorithm("body_sha256", record["body_sha256"]),
            created_at=_datetime_from_record("created_at", record["created_at"]),
            retention_tier=ArtifactRetentionTier(str(record["retention_tier"])),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.model_dump(mode="json", exclude_none=True),
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "owner_user_id": self.owner_user_id,
            "access_scope": self.access_scope.value,
            "body_artifact_id": self.body_artifact_id,
            "body_uri": self.body_uri,
            "body_sha256": self.body_sha256,
            "created_at": self.created_at.isoformat(),
            "retention_tier": self.retention_tier.value,
        }

    def same_immutable_identity(self, other: PersistedEvidence) -> bool:
        return (
            self.evidence == other.evidence
            and self.tenant_id == other.tenant_id
            and self.team_id == other.team_id
            and self.owner_user_id == other.owner_user_id
            and self.access_scope is other.access_scope
            and self.body_artifact_id == other.body_artifact_id
            and self.body_uri == other.body_uri
            and self.body_sha256 == other.body_sha256
            and self.retention_tier is other.retention_tier
        )


@dataclass(frozen=True, slots=True)
class EvidenceRevisionRecord:
    revision_id: str
    tenant_id: str
    previous_evidence_id: str
    replacement_evidence_id: str
    reason: EvidenceRevisionReason
    created_at: datetime
    note: str | None = None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        previous_evidence_id: str,
        replacement_evidence_id: str,
        reason: EvidenceRevisionReason,
        created_at: datetime,
        note: str | None = None,
    ) -> EvidenceRevisionRecord:
        normalized_tenant = _safe_id("tenant_id", tenant_id)
        normalized_previous = _safe_id("previous_evidence_id", previous_evidence_id)
        normalized_replacement = _safe_id("replacement_evidence_id", replacement_evidence_id)
        normalized_note = _optional_string(note)
        _require_aware_datetime("created_at", created_at)
        revision_id = _revision_id(
            normalized_tenant,
            normalized_previous,
            normalized_replacement,
            reason,
            normalized_note,
            created_at,
        )
        return cls(
            revision_id=revision_id,
            tenant_id=normalized_tenant,
            previous_evidence_id=normalized_previous,
            replacement_evidence_id=normalized_replacement,
            reason=reason,
            created_at=created_at,
            note=normalized_note,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> EvidenceRevisionRecord:
        return cls(
            revision_id=_required_string("revision_id", record["revision_id"]),
            tenant_id=_required_string("tenant_id", record["tenant_id"]),
            previous_evidence_id=_required_string("previous_evidence_id", record["previous_evidence_id"]),
            replacement_evidence_id=_required_string("replacement_evidence_id", record["replacement_evidence_id"]),
            reason=EvidenceRevisionReason(str(record["reason"])),
            created_at=_datetime_from_record("created_at", record["created_at"]),
            note=_optional_string(record.get("note")),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "tenant_id": self.tenant_id,
            "previous_evidence_id": self.previous_evidence_id,
            "replacement_evidence_id": self.replacement_evidence_id,
            "reason": self.reason.value,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }


class LocalEvidenceStore:
    """Filesystem-backed Evidence Store with immutable metadata records."""

    def __init__(self, root: str | Path, *, artifact_store: ArtifactStore) -> None:
        self.root = Path(root)
        self._artifact_store = artifact_store

    @property
    def record_root(self) -> Path:
        return self.root / "records"

    @property
    def revision_root(self) -> Path:
        return self.root / "revisions"

    @property
    def tmp_root(self) -> Path:
        return self.root / "tmp"

    def put_evidence(
        self,
        evidence: EvidenceRecord,
        body: object,
        *,
        tenant_id: str,
        created_at: datetime,
        team_id: str | None = None,
        owner_user_id: str | None = None,
        access_scope: EvidenceAccessScope = EvidenceAccessScope.PUBLIC,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.ARCHIVE,
    ) -> PersistedEvidence:
        if type(evidence) is not EvidenceRecord:
            raise EvidenceStoreError("evidence must be an EvidenceRecord")
        normalized_tenant = _safe_id("tenant_id", tenant_id)
        normalized_team = _optional_safe_id("team_id", team_id)
        normalized_owner = _optional_safe_id("owner_user_id", owner_user_id)
        normalized_scope = EvidenceAccessScope(access_scope)
        _validate_scope(normalized_scope, normalized_team, normalized_owner)
        _require_aware_datetime("created_at", created_at)

        body_bytes = _canonical_json_bytes(_sanitize_value(_decode_body(body)))
        body_sha256 = f"sha256:{hashlib.sha256(body_bytes).hexdigest()}"
        manifest = self._artifact_store.put_bytes(
            body_bytes,
            schema_name=EVIDENCE_BODY_SCHEMA_NAME,
            schema_version=EVIDENCE_BODY_SCHEMA_VERSION,
            content_type=EVIDENCE_BODY_CONTENT_TYPE,
            produced_by_run_id=evidence.run_id or f"evidence:{evidence.evidence_id}",
            produced_by_stage_id=evidence.stage_id,
            retention_tier=retention_tier,
            created_at=created_at,
        )
        evidence_to_store = evidence.model_copy(
            update={
                "content_hash": body_sha256,
                "artifact_id": manifest.artifact_id,
                "artifact_hash": body_sha256,
            }
        )
        persisted = PersistedEvidence(
            evidence=evidence_to_store,
            tenant_id=normalized_tenant,
            team_id=normalized_team,
            owner_user_id=normalized_owner,
            access_scope=normalized_scope,
            body_artifact_id=manifest.artifact_id,
            body_uri=str(manifest.uri),
            body_sha256=body_sha256,
            created_at=created_at,
            retention_tier=retention_tier,
        )
        path = self._record_path(normalized_tenant, evidence.evidence_id)
        if path.exists():
            existing = self._read_persisted(path)
            if existing.same_immutable_identity(persisted):
                return existing
            raise EvidenceStoreConflict(f"Evidence already exists with different immutable metadata: {evidence.evidence_id}")

        self._write_json(path, persisted.to_record())
        return persisted

    def revise_evidence(
        self,
        *,
        previous_evidence_id: str,
        replacement_evidence: EvidenceRecord,
        body: object,
        tenant_id: str,
        created_at: datetime,
        reason: EvidenceRevisionReason,
        note: str | None = None,
        team_id: str | None = None,
        owner_user_id: str | None = None,
        access_scope: EvidenceAccessScope | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.ARCHIVE,
    ) -> EvidenceRevisionRecord:
        previous = self.get_evidence(
            previous_evidence_id,
            tenant_id=tenant_id,
            team_id=team_id,
            owner_user_id=owner_user_id,
        )
        persisted = self.put_evidence(
            replacement_evidence,
            body,
            tenant_id=tenant_id,
            team_id=team_id if team_id is not None else previous.team_id,
            owner_user_id=owner_user_id if owner_user_id is not None else previous.owner_user_id,
            access_scope=access_scope if access_scope is not None else previous.access_scope,
            created_at=created_at,
            retention_tier=retention_tier,
        )
        revision = EvidenceRevisionRecord.create(
            tenant_id=tenant_id,
            previous_evidence_id=previous.evidence.evidence_id,
            replacement_evidence_id=persisted.evidence.evidence_id,
            reason=EvidenceRevisionReason(reason),
            note=note,
            created_at=created_at,
        )
        path = self._revision_path(revision.tenant_id, revision.revision_id)
        if path.exists():
            existing = self._read_revision(path)
            if existing == revision:
                return existing
            raise EvidenceStoreConflict(f"Evidence revision already exists with different metadata: {revision.revision_id}")
        self._write_json(path, revision.to_record())
        return revision

    def get_evidence(
        self,
        evidence_id: str,
        *,
        tenant_id: str,
        team_id: str | None = None,
        owner_user_id: str | None = None,
    ) -> PersistedEvidence:
        path = self._record_path(_safe_id("tenant_id", tenant_id), evidence_id)
        if not path.exists():
            raise EvidenceStoreNotFound(f"Evidence not found: {evidence_id}")
        persisted = self._read_persisted(path)
        self._assert_access(persisted, team_id=team_id, owner_user_id=owner_user_id)
        return persisted

    def find_evidence(
        self,
        *,
        tenant_id: str,
        team_id: str | None = None,
        owner_user_id: str | None = None,
        kind: str | None = None,
    ) -> tuple[PersistedEvidence, ...]:
        tenant = _safe_id("tenant_id", tenant_id)
        root = self.record_root / tenant
        if not root.exists():
            return ()
        matches: list[PersistedEvidence] = []
        for path in sorted(root.glob("*.json")):
            persisted = self._read_persisted(path)
            try:
                self._assert_access(persisted, team_id=team_id, owner_user_id=owner_user_id)
            except EvidenceStoreAccessDenied:
                continue
            if kind is not None and persisted.evidence.kind.value != kind:
                continue
            matches.append(persisted)
        return tuple(sorted(matches, key=lambda item: (item.created_at, item.evidence.evidence_id)))

    def list_revisions(
        self,
        *,
        tenant_id: str,
    ) -> tuple[EvidenceRevisionRecord, ...]:
        tenant = _safe_id("tenant_id", tenant_id)
        root = self.revision_root / tenant
        if not root.exists():
            return ()
        return tuple(sorted((self._read_revision(path) for path in root.glob("*.json")), key=lambda item: item.created_at))

    def _record_path(self, tenant_id: str, evidence_id: str) -> Path:
        return self.record_root / _safe_id("tenant_id", tenant_id) / f"{_safe_id('evidence_id', evidence_id)}.json"

    def _revision_path(self, tenant_id: str, revision_id: str) -> Path:
        return self.revision_root / _safe_id("tenant_id", tenant_id) / f"{_safe_id('revision_id', revision_id)}.json"

    def _read_persisted(self, path: Path) -> PersistedEvidence:
        try:
            return PersistedEvidence.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise EvidenceStoreNotFound(f"Evidence metadata not found: {path.stem}") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise EvidenceStoreError(f"Evidence metadata is invalid: {path}") from exc

    def _read_revision(self, path: Path) -> EvidenceRevisionRecord:
        try:
            return EvidenceRevisionRecord.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise EvidenceStoreNotFound(f"Evidence revision not found: {path.stem}") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise EvidenceStoreError(f"Evidence revision metadata is invalid: {path}") from exc

    def _write_json(self, path: Path, record: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        tmp = self.tmp_root / f"{path.stem}.{token}.tmp"
        try:
            with tmp.open("wb") as handle:
                handle.write(json.dumps(record, indent=2, sort_keys=True).encode("utf-8"))
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _assert_access(
        persisted: PersistedEvidence,
        *,
        team_id: str | None,
        owner_user_id: str | None,
    ) -> None:
        normalized_team = _optional_safe_id("team_id", team_id)
        normalized_owner = _optional_safe_id("owner_user_id", owner_user_id)
        if persisted.access_scope is EvidenceAccessScope.PUBLIC:
            return
        if persisted.team_id is not None and persisted.team_id != normalized_team:
            raise EvidenceStoreAccessDenied("Evidence is not visible to this team")
        if persisted.access_scope is EvidenceAccessScope.PRIVATE and persisted.owner_user_id != normalized_owner:
            raise EvidenceStoreAccessDenied("Evidence is not visible to this user")


def _validate_scope(
    access_scope: EvidenceAccessScope,
    team_id: str | None,
    owner_user_id: str | None,
) -> None:
    if access_scope is EvidenceAccessScope.PRIVATE and owner_user_id is None:
        raise EvidenceStoreAccessDenied("private evidence requires owner_user_id")
    if access_scope is EvidenceAccessScope.TEAM and team_id is None:
        raise EvidenceStoreAccessDenied("team evidence requires team_id")


def _revision_id(
    tenant_id: str,
    previous_evidence_id: str,
    replacement_evidence_id: str,
    reason: EvidenceRevisionReason,
    note: str | None,
    created_at: datetime,
) -> str:
    source = "\0".join(
        [
            "evidence-revision-v1",
            tenant_id,
            previous_evidence_id,
            replacement_evidence_id,
            reason.value,
            note or "",
            created_at.isoformat(),
        ]
    )
    return f"evr_{hashlib.sha256(source.encode('utf-8')).hexdigest()[:32]}"


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode_body(body: object) -> object:
    if isinstance(body, bytes | bytearray):
        text = bytes(body).decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return body


def _sanitize_value(value: object) -> object:
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = str(key)
            if _is_sensitive_key(normalized_key):
                sanitized[normalized_key] = "[REDACTED]"
            else:
                sanitized[normalized_key] = _sanitize_value(item)
        return sanitized
    if isinstance(value, bytes | bytearray):
        return _sanitize_value(_decode_body(value))
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted((_sanitize_value(item) for item in value), key=str)
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)


_SENSITIVE_KEYS = {
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "password",
    "private_body",
    "raw_prompt",
    "secret",
    "session",
    "set-cookie",
    "token",
    "x-api-key",
}
_SENSITIVE_KEY_PARTS = ("api_key", "apikey", "secret", "token", "password", "cookie", "credential")
_SECRET_TEXT_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*([A-Za-z0-9_\-./+=]{6,})"
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower()
    return normalized in _SENSITIVE_KEYS or any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    return _SECRET_TEXT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def _safe_id(field_name: str, value: object) -> str:
    normalized = _required_string(field_name, value)
    if not _SAFE_ID_RE.fullmatch(normalized):
        raise EvidenceStoreError(f"{field_name} contains unsupported characters")
    return normalized


def _optional_safe_id(field_name: str, value: object | None) -> str | None:
    if value is None:
        return None
    return _safe_id(field_name, value)


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise EvidenceStoreError(f"{field_name} is required")
    return value


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _datetime_from_record(field_name: str, value: object) -> datetime:
    if type(value) is not str:
        raise EvidenceStoreError(f"{field_name} must be an ISO datetime string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceStoreError(f"{field_name} must be an ISO datetime string") from exc
    _require_aware_datetime(field_name, parsed)
    return parsed


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceStoreError(f"{field_name} must be timezone-aware")


def _sha256_with_algorithm(field_name: str, value: object) -> str:
    normalized = _required_string(field_name, value)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", normalized):
        raise EvidenceStoreError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return normalized
