from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.providers import Provenance, ProviderCapability
from serenity_alpha_lab.repositories.bronze_raw_store import (
    BRONZE_RAW_CONTENT_TYPE,
    BRONZE_RAW_SCHEMA_NAME,
    BRONZE_RAW_SCHEMA_VERSION,
    BronzeRawStore,
    BronzeRawStoreError,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


REQUESTED_AT = datetime(2026, 7, 21, 9, 30, tzinfo=UTC)
FETCHED_AT = datetime(2026, 7, 21, 9, 30, 2, tzinfo=UTC)
RAW_SHA256 = "a" * 64


def make_provenance(**overrides: object) -> Provenance:
    values = {
        "provider_id": "akshare",
        "provider_version": "1.17.0",
        "operation": ProviderCapability.DAILY_BARS,
        "request_parameters": {
            "endpoint": "stock_zh_a_hist",
            "symbol": "600519",
            "api_key": "ak-live-request-secret",
            "headers": {
                "Cookie": "sessionid=request-cookie-secret",
                "User-Agent": "serenity-test",
            },
            "email": "request-owner@example.com",
            "phone": "+86 138 0013 8000",
        },
        "requested_at": REQUESTED_AT,
        "fetched_at": FETCHED_AT,
        "raw_response_sha256": RAW_SHA256,
        "field_lineage": {
            "close": "akshare.stock_zh_a_hist.close",
        },
        "source_timestamp": datetime(2026, 7, 20, tzinfo=UTC),
        "trace_id": "trace-bronze-001",
        "run_id": "run-bronze-001",
        "stage_id": "stage-provider-raw",
    }
    values.update(overrides)
    return Provenance(**values)  # type: ignore[arg-type]


def make_store(tmp_path: Path) -> BronzeRawStore:
    return BronzeRawStore(LocalArtifactStore(tmp_path / "artifacts"))


def raw_response() -> dict[str, object]:
    return {
        "status": 200,
        "headers": {
            "Authorization": "Bearer response-token-secret",
            "Set-Cookie": "sid=response-cookie-secret; Path=/",
            "Content-Type": "application/json",
        },
        "rows": [
            {
                "date": "2026-07-20",
                "close": 1688.5,
                "email": "shareholder@example.com",
                "mobile": "13800138000",
                "identity_card": "110101199001011234",
            }
        ],
        "body": "token=inline-token-secret api_key=inline-key-secret contact=person@example.com phone=13800138000",
    }


def test_bronze_store_publishes_compressed_auditable_raw_response(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    store = BronzeRawStore(artifact_store)

    bronze = store.put_raw_response(raw_response(), provenance=make_provenance())

    manifest = artifact_store.get_manifest(bronze.artifact_id)
    envelope = store.get_envelope(bronze.artifact_id)
    compressed = artifact_store.get_bytes(bronze.artifact_id)

    assert bronze.artifact_id == manifest.artifact_id
    assert bronze.uri == str(manifest.uri)
    assert bronze.provider_id == "akshare"
    assert bronze.operation == ProviderCapability.DAILY_BARS.value
    assert bronze.requested_at == REQUESTED_AT
    assert bronze.fetched_at == FETCHED_AT
    assert bronze.trace_id == "trace-bronze-001"
    assert bronze.produced_by_run_id == "run-bronze-001"
    assert bronze.produced_by_stage_id == "stage-provider-raw"
    assert bronze.retention_tier is ArtifactRetentionTier.ARCHIVE
    assert bronze.source_raw_response_sha256 == RAW_SHA256
    assert len(bronze.sanitized_raw_response_sha256) == 64
    assert bronze.compression == "gzip"

    assert manifest.schema_name == BRONZE_RAW_SCHEMA_NAME
    assert manifest.schema_version == BRONZE_RAW_SCHEMA_VERSION
    assert manifest.content_type == BRONZE_RAW_CONTENT_TYPE
    assert manifest.retention_tier is ArtifactRetentionTier.ARCHIVE
    assert manifest.produced_by_run_id == "run-bronze-001"
    assert manifest.produced_by_stage_id == "stage-provider-raw"

    assert gzip.decompress(compressed)
    assert hashlib.sha256(compressed).hexdigest() == manifest.sha256
    assert envelope["schema_name"] == BRONZE_RAW_SCHEMA_NAME
    assert envelope["schema_version"] == BRONZE_RAW_SCHEMA_VERSION
    assert envelope["provider_id"] == "akshare"
    assert envelope["operation"] == ProviderCapability.DAILY_BARS.value
    assert envelope["requested_at"] == REQUESTED_AT.isoformat()
    assert envelope["fetched_at"] == FETCHED_AT.isoformat()
    assert envelope["source_timestamp"] == datetime(2026, 7, 20, tzinfo=UTC).isoformat()
    assert envelope["request_parameters"]["symbol"] == "600519"
    assert envelope["request_parameters"]["api_key"] == "[REDACTED]"
    assert envelope["request_parameters"]["headers"]["Cookie"] == "[REDACTED]"
    assert envelope["trace_id"] == "trace-bronze-001"
    assert envelope["run_id"] == "run-bronze-001"
    assert envelope["stage_id"] == "stage-provider-raw"
    assert envelope["raw_response"]["headers"]["Authorization"] == "[REDACTED]"
    assert envelope["raw_response"]["headers"]["Set-Cookie"] == "[REDACTED]"
    assert envelope["raw_response"]["rows"][0]["email"] == "[REDACTED]"
    assert envelope["raw_response"]["rows"][0]["mobile"] == "[REDACTED]"
    assert envelope["raw_response"]["rows"][0]["identity_card"] == "[REDACTED]"


def test_bronze_store_redacts_sensitive_values_before_bytes_hit_disk(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    store = BronzeRawStore(artifact_store)

    bronze = store.put_raw_response(raw_response(), provenance=make_provenance())

    manifest_path = artifact_store.manifest_path_for(bronze.artifact_id)
    blob_path = artifact_store.blob_path_for(bronze.compressed_sha256)
    disk_bytes = manifest_path.read_bytes() + blob_path.read_bytes() + gzip.decompress(blob_path.read_bytes())
    forbidden_values = [
        b"ak-live-request-secret",
        b"request-cookie-secret",
        b"request-owner@example.com",
        b"13800138000",
        b"response-token-secret",
        b"response-cookie-secret",
        b"shareholder@example.com",
        b"110101199001011234",
        b"inline-token-secret",
        b"inline-key-secret",
        b"person@example.com",
    ]

    for forbidden in forbidden_values:
        assert forbidden not in disk_bytes


def test_bronze_store_is_deterministic_for_same_sanitized_payload(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    provenance = make_provenance()

    first = store.put_raw_response(raw_response(), provenance=provenance)
    second = store.put_raw_response(raw_response(), provenance=provenance)

    assert second.artifact_id == first.artifact_id
    assert second.compressed_sha256 == first.compressed_sha256
    assert second.sanitized_raw_response_sha256 == first.sanitized_raw_response_sha256


def test_bronze_store_finds_artifacts_by_provider_operation_and_requested_time(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = store.put_raw_response(raw_response(), provenance=make_provenance())
    store.put_raw_response(
        {"ok": True},
        provenance=make_provenance(
            provider_id="yfinance",
            requested_at=REQUESTED_AT + timedelta(minutes=5),
            fetched_at=FETCHED_AT + timedelta(minutes=5),
        ),
    )

    matches = store.find_raw_artifacts(
        provider_id="akshare",
        operation=ProviderCapability.DAILY_BARS,
        requested_at_start=REQUESTED_AT - timedelta(seconds=1),
        requested_at_end=REQUESTED_AT + timedelta(seconds=1),
    )

    assert [match.artifact_id for match in matches] == [first.artifact_id]


def test_bronze_store_rejects_missing_run_attribution(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    with pytest.raises(BronzeRawStoreError, match="produced_by_run_id is required"):
        store.put_raw_response(
            raw_response(),
            provenance=make_provenance(run_id=None, stage_id=None),
        )


def test_bronze_store_accepts_bytes_and_keeps_json_safe_text(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    bronze = store.put_raw_response(
        b'{"ok": true, "token": "byte-secret", "close": 10.5}',
        provenance=make_provenance(request_parameters={"symbol": "600519"}),
    )

    envelope = store.get_envelope(bronze.artifact_id)
    encoded = json.dumps(envelope, sort_keys=True)

    assert envelope["raw_response"]["token"] == "[REDACTED]"
    assert envelope["raw_response"]["close"] == 10.5
    assert "byte-secret" not in encoded
