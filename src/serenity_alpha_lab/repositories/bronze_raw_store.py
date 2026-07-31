from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
)
from serenity_alpha_lab.domain.providers import Provenance, ProviderCapability


BRONZE_RAW_SCHEMA_NAME = "bronze.raw_response"
BRONZE_RAW_SCHEMA_VERSION = "1.0.0"
BRONZE_RAW_CONTENT_TYPE = "application/vnd.serenity.bronze.raw-response+json+gzip"


class BronzeRawStoreError(ValueError):
    """Raised when a Bronze raw-response artifact cannot be published or read."""


@dataclass(frozen=True, slots=True)
class BronzeRawArtifact:
    artifact_id: str
    uri: str
    provider_id: str
    operation: str
    requested_at: datetime
    fetched_at: datetime
    source_raw_response_sha256: str
    sanitized_raw_response_sha256: str
    compressed_sha256: str
    size_bytes: int
    compression: str
    retention_tier: ArtifactRetentionTier
    produced_by_run_id: str
    produced_by_stage_id: str | None
    trace_id: str | None


class BronzeRawStore:
    """Publish sanitized provider raw responses as compressed Bronze artifacts."""

    def __init__(self, artifact_store: ArtifactStore) -> None:
        self._artifact_store = artifact_store

    def put_raw_response(
        self,
        raw_response: object,
        *,
        provenance: Provenance,
        produced_by_run_id: str | None = None,
        produced_by_stage_id: str | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.ARCHIVE,
    ) -> BronzeRawArtifact:
        run_id = _required_string("produced_by_run_id", produced_by_run_id or provenance.run_id)
        stage_id = produced_by_stage_id if produced_by_stage_id is not None else provenance.stage_id
        sanitized_raw_response = _sanitize_value(_decode_raw_response(raw_response))
        sanitized_request_parameters = _sanitize_value(dict(provenance.request_parameters))
        sanitized_raw_response_bytes = _canonical_json_bytes(sanitized_raw_response)
        sanitized_raw_response_sha256 = hashlib.sha256(sanitized_raw_response_bytes).hexdigest()

        envelope = {
            "schema_name": BRONZE_RAW_SCHEMA_NAME,
            "schema_version": BRONZE_RAW_SCHEMA_VERSION,
            "provider_id": provenance.provider_id,
            "provider_version": provenance.provider_version,
            "operation": str(provenance.operation),
            "request_parameters": sanitized_request_parameters,
            "requested_at": provenance.requested_at.isoformat(),
            "fetched_at": provenance.fetched_at.isoformat(),
            "source_timestamp": provenance.source_timestamp.isoformat() if provenance.source_timestamp else None,
            "source_raw_response_sha256": provenance.raw_response_sha256,
            "sanitized_raw_response_sha256": sanitized_raw_response_sha256,
            "field_lineage": dict(provenance.field_lineage),
            "trace_id": provenance.trace_id,
            "run_id": run_id,
            "stage_id": stage_id,
            "raw_response": sanitized_raw_response,
        }
        compressed = gzip.compress(_canonical_json_bytes(envelope), compresslevel=9, mtime=0)
        manifest = self._artifact_store.put_bytes(
            compressed,
            schema_name=BRONZE_RAW_SCHEMA_NAME,
            schema_version=BRONZE_RAW_SCHEMA_VERSION,
            content_type=BRONZE_RAW_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=provenance.fetched_at,
        )
        return _artifact_from_manifest_and_envelope(manifest, envelope)

    def get_envelope(self, artifact_id: str) -> dict[str, Any]:
        compressed = self._artifact_store.get_bytes(artifact_id)
        try:
            payload = gzip.decompress(compressed)
            envelope = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BronzeRawStoreError(f"Bronze raw artifact is not a valid gzip JSON envelope: {artifact_id}") from exc
        if not isinstance(envelope, dict):
            raise BronzeRawStoreError(f"Bronze raw artifact envelope must be a JSON object: {artifact_id}")
        return envelope

    def find_raw_artifacts(
        self,
        *,
        provider_id: str | None = None,
        operation: ProviderCapability | str | None = None,
        requested_at_start: datetime | None = None,
        requested_at_end: datetime | None = None,
    ) -> tuple[BronzeRawArtifact, ...]:
        manifests = self._list_manifests()
        matches: list[BronzeRawArtifact] = []
        operation_value = str(operation) if operation is not None else None
        for manifest in manifests:
            if manifest.schema_name != BRONZE_RAW_SCHEMA_NAME:
                continue
            envelope = self.get_envelope(manifest.artifact_id)
            candidate = _artifact_from_manifest_and_envelope(manifest, envelope)
            if provider_id is not None and candidate.provider_id != provider_id:
                continue
            if operation_value is not None and candidate.operation != operation_value:
                continue
            if requested_at_start is not None and candidate.requested_at < requested_at_start:
                continue
            if requested_at_end is not None and candidate.requested_at > requested_at_end:
                continue
            matches.append(candidate)
        return tuple(sorted(matches, key=lambda artifact: (artifact.requested_at, artifact.artifact_id)))

    def _list_manifests(self) -> Sequence[ArtifactManifest]:
        list_manifests = getattr(self._artifact_store, "list_manifests", None)
        if list_manifests is None:
            raise BronzeRawStoreError("Artifact store does not support manifest scanning")
        manifests = list_manifests()
        if not isinstance(manifests, Sequence):
            raise BronzeRawStoreError("Artifact store returned invalid manifest listing")
        return manifests


def _artifact_from_manifest_and_envelope(
    manifest: ArtifactManifest,
    envelope: Mapping[str, Any],
) -> BronzeRawArtifact:
    return BronzeRawArtifact(
        artifact_id=manifest.artifact_id,
        uri=str(manifest.uri),
        provider_id=_required_string("provider_id", envelope.get("provider_id")),
        operation=_required_string("operation", envelope.get("operation")),
        requested_at=_datetime_from_envelope("requested_at", envelope.get("requested_at")),
        fetched_at=_datetime_from_envelope("fetched_at", envelope.get("fetched_at")),
        source_raw_response_sha256=_required_string(
            "source_raw_response_sha256",
            envelope.get("source_raw_response_sha256"),
        ),
        sanitized_raw_response_sha256=_required_string(
            "sanitized_raw_response_sha256",
            envelope.get("sanitized_raw_response_sha256"),
        ),
        compressed_sha256=manifest.sha256,
        size_bytes=manifest.size_bytes,
        compression="gzip",
        retention_tier=manifest.retention_tier,
        produced_by_run_id=manifest.produced_by_run_id,
        produced_by_stage_id=manifest.produced_by_stage_id,
        trace_id=_optional_string(envelope.get("trace_id")),
    )


def _decode_raw_response(raw_response: object) -> object:
    if isinstance(raw_response, bytes | bytearray):
        text = bytes(raw_response).decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    if isinstance(raw_response, str):
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return raw_response
    return raw_response


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


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
        return _sanitize_value(_decode_raw_response(value))
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
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
    "body",
    "content",
    "cookie",
    "credential",
    "credentials",
    "email",
    "id-card",
    "id_card",
    "identity-card",
    "identity_card",
    "messages",
    "mobile",
    "password",
    "personal-id",
    "personal_id",
    "phone",
    "private_body",
    "secret",
    "session",
    "set-cookie",
    "ssn",
    "telephone",
    "token",
    "x-api-key",
}
_SENSITIVE_KEY_PARTS = ("secret", "token", "password", "cookie", "credential")
_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization|cookie|set-cookie)\s*[:=]\s*[^,\s;]+"
)
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)")
_IDENTITY_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return normalized in _SENSITIVE_KEYS or any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    redacted = _ASSIGNMENT_SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = _IDENTITY_RE.sub("[REDACTED_ID]", redacted)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise BronzeRawStoreError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise BronzeRawStoreError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise BronzeRawStoreError("optional string envelope value must be a string")
    normalized = value.strip()
    return normalized or None


def _datetime_from_envelope(field_name: str, value: object | None) -> datetime:
    if type(value) is not str:
        raise BronzeRawStoreError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise BronzeRawStoreError(f"{field_name} must be ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BronzeRawStoreError(f"{field_name} must be timezone-aware")
    return parsed


__all__ = [
    "BRONZE_RAW_CONTENT_TYPE",
    "BRONZE_RAW_SCHEMA_NAME",
    "BRONZE_RAW_SCHEMA_VERSION",
    "BronzeRawArtifact",
    "BronzeRawStore",
    "BronzeRawStoreError",
]
