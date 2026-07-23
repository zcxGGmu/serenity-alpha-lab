from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from sqlalchemy.engine import Engine

from serenity_alpha_lab.application.config_profiles import RuntimeProfile, RuntimeSettings, load_runtime_settings
from serenity_alpha_lab.application.task_backend import TaskCommand, TaskStatus
from serenity_alpha_lab.application.tracing import TraceContext, use_trace_context
from serenity_alpha_lab.datasets import (
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
    DatasetFileManifest,
    DatasetPublicationRequest,
    DatasetPublicationStatus,
    DataQualityReport,
    DataQualityStatus,
    LocalDatasetCatalog,
    QualityGatedDatasetPublisher,
    default_dataset_schema_registry,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderCapability
from serenity_alpha_lab.integrations.data.provider_contract_fixtures import (
    ProviderContractFixtureCase,
    default_provider_contract_fixture_catalog,
)
from serenity_alpha_lab.integrations.data.provider_policy import (
    ProviderPolicy,
    ProviderPolicyEngine,
    ProviderPolicyStatus,
    ProviderSelectionRequest,
)
from serenity_alpha_lab.integrations.dsa.provider_adapter import (
    DsaProviderCompatibilityAdapter,
    DsaStockHistoryCompatibilityFacade,
)
from serenity_alpha_lab.repositories.database import create_database_engine, resolve_database_profile
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore
from serenity_alpha_lab.repositories.persistent_task_backend import PersistentTaskBackend, TaskQueueRoute
from serenity_alpha_lab.services.task_event_stream import TaskEventStreamService


NOW = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


class OfflineDsaManager:
    def __init__(self) -> None:
        self.daily_calls: list[dict[str, Any]] = []
        self.name_calls: list[str] = []

    def get_daily_data(self, stock_code: str, start_date=None, end_date=None, days: int = 30):
        self.daily_calls.append(
            {
                "stock_code": stock_code,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
            }
        )
        return (
            pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-07-22"),
                        "open": 1680.0,
                        "high": 1690.0,
                        "low": 1670.0,
                        "close": 1688.0,
                        "volume": 1000,
                        "amount": 1688000.0,
                    }
                ]
            ),
            "EfinanceFetcher",
        )

    def get_stock_name(self, stock_code: str) -> str:
        self.name_calls.append(stock_code)
        return "贵州茅台"


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Engine:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": f"sqlite:///{tmp_path / 'gate-g2.sqlite'}",
        }
    )
    engine = create_database_engine(resolve_database_profile(settings))
    try:
        yield engine
    finally:
        engine.dispose()


def test_gate_g2_publishes_traceable_a_share_dataset_from_offline_provider_fixture(tmp_path: Path) -> None:
    fixture_catalog = default_provider_contract_fixture_catalog()
    akshare_batch = _fixture_case(fixture_catalog.success_cases(), "akshare").to_data_batch(
        trace_id="trace-g2-provider",
        run_id="run-g2-dataset",
        stage_id="stage-provider-policy",
    )
    result = ProviderPolicyEngine(_cn_daily_policy()).select(
        _daily_request(),
        provider_results={"akshare": akshare_batch},
    )
    assert result.status is ProviderPolicyStatus.SELECTED

    payload = _canonical_json_bytes(
        {
            "records": [dict(record) for record in result.selected_batch.records],
            "provider_fallback_trace": result.trace.to_record(),
        }
    )
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    data_artifact = artifact_store.put_bytes(
        payload,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        content_type=RAW_DAILY_BARS_CONTENT_TYPE,
        produced_by_run_id="run-g2-dataset",
        produced_by_stage_id="stage-build-raw-bars",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
    catalog = LocalDatasetCatalog(tmp_path / "catalog", schema_registry=default_dataset_schema_registry())
    publisher = QualityGatedDatasetPublisher(catalog=catalog, artifact_store=artifact_store)
    trace_record = result.trace.to_record()
    trace_hash = hashlib.sha256(_canonical_json_bytes(trace_record)).hexdigest()

    publication = publisher.publish(
        DatasetPublicationRequest(
            dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
            schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
            schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
            files=(
                DatasetFileManifest.from_artifact(
                    data_artifact,
                    row_count=len(result.selected_batch.records),
                    partition_values={"market": "cn", "year": "2026", "month": "07"},
                ),
            ),
            quality_report=_passed_quality_report(records_evaluated=len(result.selected_batch.records)),
            created_at=NOW,
            created_by_run_id="run-g2-dataset",
            created_by_stage_id="stage-build-raw-bars",
            trace_id="trace-g2-provider",
            alias_scope="cn",
            metadata={
                "gate": "G2",
                "provider_policy_status": result.status.value,
                "provider_policy_trace_sha256": trace_hash,
                "selected_provider_id": result.selected_provider_id or "",
                "selected_raw_response_sha256": result.selected_batch.provenance.raw_response_sha256,
            },
        )
    )

    latest = catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn")
    schema = default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)
    assert publication.status is DatasetPublicationStatus.PUBLISHED
    assert publication.latest_updated is True
    assert latest == publication.manifest
    assert publication.manifest.schema_hash == schema.schema_hash
    assert publication.manifest.row_count == len(akshare_batch.records)
    assert publication.manifest.trace_id == "trace-g2-provider"
    assert publication.manifest.created_by_run_id == "run-g2-dataset"
    assert publication.manifest.metadata["quality_status"] == DataQualityStatus.PASSED.value
    assert publication.manifest.metadata["provider_policy_status"] == "selected"
    assert publication.manifest.metadata["selected_provider_id"] == "akshare"
    assert publication.manifest.files[0].sha256 == data_artifact.sha256
    assert catalog.list_quarantine_records(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == ()


def test_gate_g2_blocks_provider_conflict_and_recovers_task_events_after_restart(
    sqlite_engine: Engine,
) -> None:
    fixture_catalog = default_provider_contract_fixture_catalog()
    akshare_batch = _fixture_case(fixture_catalog.success_cases(), "akshare").to_data_batch()
    tushare_conflict = _with_close(_fixture_case(fixture_catalog.success_cases(), "tushare").to_data_batch(), 1700.0)
    conflict = ProviderPolicyEngine(
        _cn_daily_policy(cross_check_provider_id="tushare", max_close_diff_bps=5.0)
    ).select(
        _daily_request(),
        provider_results={"akshare": akshare_batch, "tushare": tushare_conflict},
    )
    assert conflict.status is ProviderPolicyStatus.QUARANTINED
    assert conflict.selected_batch is None
    assert conflict.trace.conflicts

    clock = DeterministicClock()
    backend = PersistentTaskBackend(
        sqlite_engine,
        routes=(TaskQueueRoute(task_type="data.sync.daily", queue_name="data", routing_key="data.sync"),),
        clock=clock,
    )
    backend.create_schema()
    ref = backend.submit(
        TaskCommand(
            run_id="run-g2-task",
            task_type="data.sync.daily",
            payload={"dataset_name": "bars_1d_raw", "market": "cn"},
            idempotency_key="gate-g2:data.sync.daily:cn:2026-07-23",
            metadata={"trace_id": "trace-g2-task"},
        )
    )
    restarted = PersistentTaskBackend(
        sqlite_engine,
        routes=(TaskQueueRoute(task_type="data.sync.daily", queue_name="data", routing_key="data.sync"),),
        clock=clock,
    )
    restarted.create_schema()

    snapshot = restarted.get(ref.task_id)
    frames = TaskEventStreamService(task_backend=restarted).task_events(
        ref.task_id,
        last_event_id="0",
        trace_context=TraceContext(trace_id="trace-g2-task", run_id=ref.run_id),
    )

    assert snapshot.status is TaskStatus.QUEUED
    assert snapshot.payload["dataset_name"] == "bars_1d_raw"
    assert [frame.id for frame in frames] == ["1"]
    assert frames[0].event == "task.submitted"
    assert frames[0].data["trace_id"] == "trace-g2-task"
    assert restarted.submit(
        TaskCommand(
            run_id="run-g2-task-duplicate",
            task_type="data.sync.daily",
            payload={"dataset_name": "bars_1d_raw", "market": "cn"},
            idempotency_key="gate-g2:data.sync.daily:cn:2026-07-23",
        )
    ).task_id == ref.task_id


def test_gate_g2_dsa_single_stock_compatibility_path_uses_injected_offline_manager() -> None:
    manager = OfflineDsaManager()
    adapter = DsaProviderCompatibilityAdapter(
        manager=manager,
        settings=RuntimeSettings(profile=RuntimeProfile.CI),
        clock=lambda: NOW,
    )
    facade = DsaStockHistoryCompatibilityFacade(
        manager=manager,
        provider=adapter,
        clock=lambda: date(2026, 7, 23),
    )

    with use_trace_context(TraceContext(trace_id="trace-g2-dsa", run_id="run-g2-dsa", stage_id="stage-dsa")):
        provider_payload = facade.get_history_data("600519", days=5, use_provider_contract=True)

    assert provider_payload["stock_code"] == "600519"
    assert provider_payload["stock_name"] == "贵州茅台"
    assert provider_payload["period"] == "daily"
    assert provider_payload["data"] == [
        {
            "date": "2026-07-22",
            "open": 1680.0,
            "high": 1690.0,
            "low": 1670.0,
            "close": 1688.0,
            "volume": 1000.0,
            "amount": 1688000.0,
            "change_percent": None,
        }
    ]
    assert manager.daily_calls == [
        {
            "stock_code": "SH600519",
            "start_date": "2026-07-13",
            "end_date": "2026-07-23",
            "days": 30,
        }
    ]
    assert manager.name_calls == ["600519"]
    with use_trace_context(TraceContext(trace_id="trace-g2-dsa", run_id="run-g2-dsa", stage_id="stage-dsa")):
        batch = adapter.get_daily_bars([InstrumentId.parse("600519.XSHG")], date(2026, 7, 22), date(2026, 7, 23))
    assert isinstance(batch, DataBatch)
    assert batch.provenance.trace_id == "trace-g2-dsa"
    with pytest.raises(TypeError):
        batch.records[0]["close"] = 0.0  # type: ignore[index]


def _cn_daily_policy(
    *,
    cross_check_provider_id: str | None = None,
    max_close_diff_bps: float | None = None,
) -> ProviderPolicy:
    return ProviderPolicy.from_mapping(
        {
            "policy_id": "gate-g2-cn-bars-fixture-policy",
            "market": "cn",
            "dataset": "bars_1d",
            "priority": ["akshare", "efinance", "tushare", "baostock"],
            "sources": {
                "akshare": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.95},
                "efinance": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.90},
                "tushare": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.92},
                "baostock": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.85},
            },
            "validation": {
                "cross_check_provider": cross_check_provider_id,
                "max_close_diff_bps": max_close_diff_bps,
            },
        }
    )


def _daily_request() -> ProviderSelectionRequest:
    return ProviderSelectionRequest(
        market=Market.CN,
        capability=ProviderCapability.DAILY_BARS,
        dataset_name="bars_1d",
        required_fields=("open", "high", "low", "close", "volume"),
        evaluation_time=NOW,
        trace_id="trace-g2-provider",
        run_id="run-g2-dataset",
        stage_id="stage-provider-policy",
    )


def _fixture_case(
    cases: tuple[ProviderContractFixtureCase, ...],
    provider_id: str,
) -> ProviderContractFixtureCase:
    return next(case for case in cases if case.provider_id == provider_id and case.market is Market.CN)


def _passed_quality_report(*, records_evaluated: int) -> DataQualityReport:
    schema = default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)
    return DataQualityReport(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        schema_hash=schema.schema_hash,
        rule_set_version="dq-g2-review.1",
        generated_at=NOW,
        records_evaluated=records_evaluated,
        issues=(),
        trace_id="trace-g2-provider",
        run_id="run-g2-dataset",
        stage_id="stage-quality",
    )


def _with_close(batch: DataBatch, close: float) -> DataBatch:
    return DataBatch(
        records=tuple({**dict(record), "close": close} for record in batch.records),
        schema_name=batch.schema_name,
        schema_version=batch.schema_version,
        provenance=batch.provenance,
        fresh_until=batch.fresh_until,
        warnings=batch.warnings,
    )


def _canonical_json_bytes(record: Any) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
