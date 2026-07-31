from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from serenity_alpha_lab.application.config_profiles import load_runtime_settings
from serenity_alpha_lab.evidence.report_renderer import ResearchReportRenderContext, TrustedResearchReportRenderer
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
    ReportCitation,
    ResearchClaim,
    ResearchReport,
    ResearchReportLevel,
)
from serenity_alpha_lab.repositories.database import create_database_engine, resolve_database_profile
from serenity_alpha_lab.repositories.notification_outbox import (
    NOTIFICATION_OUTBOX_CONTRACT_VERSION,
    NotificationChannel,
    NotificationOutboxConflict,
    NotificationOutboxStatus,
    NotificationOutboxStore,
)


NOW = datetime(2026, 7, 29, 16, 0, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
DATASET_VERSIONS = {"adjusted_daily_bars": "dsv_" + "1" * 32}


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Engine:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": f"sqlite:///{tmp_path / 'notification-outbox.sqlite'}",
        }
    )
    engine = create_database_engine(resolve_database_profile(settings))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def clock() -> DeterministicClock:
    return DeterministicClock()


def test_notification_outbox_dedupes_by_tenant_channel_and_dedupe_key(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    store = NotificationOutboxStore(sqlite_engine, clock=clock)
    store.create_schema()
    rendered = _rendered_report()

    first = store.enqueue_report_notification(
        tenant_id="tenant-alpha",
        channel=NotificationChannel.EMAIL,
        dedupe_key="report:rpt_outbox:email",
        rendered_report=rendered,
        recipient={"kind": "user", "user_id": "user-1"},
        payload={"subject": "Trusted Alpha Report", "summary": "Verified report ready."},
    )
    replay = store.enqueue_report_notification(
        tenant_id="tenant-alpha",
        channel=NotificationChannel.EMAIL,
        dedupe_key="report:rpt_outbox:email",
        rendered_report=rendered,
        recipient={"kind": "user", "user_id": "user-1"},
        payload={"subject": "Trusted Alpha Report", "summary": "Verified report ready."},
    )

    assert replay == first
    assert first.contract_version == NOTIFICATION_OUTBOX_CONTRACT_VERSION
    assert first.status is NotificationOutboxStatus.PENDING
    assert first.attempt == 0
    assert first.report_id == "rpt_outbox"
    assert first.report_hash == rendered.trusted_report.authoritative_json_hash
    assert first.rendering_hash == rendered.rendering_hash
    assert first.payload["summary"] == "Verified report ready."
    assert [message.message_id for message in store.list_messages(tenant_id="tenant-alpha")] == [first.message_id]

    with pytest.raises(NotificationOutboxConflict, match="dedupe_key"):
        store.enqueue_report_notification(
            tenant_id="tenant-alpha",
            channel=NotificationChannel.EMAIL,
            dedupe_key="report:rpt_outbox:email",
            rendered_report=rendered,
            recipient={"kind": "user", "user_id": "user-1"},
            payload={"subject": "Trusted Alpha Report", "summary": "changed"},
        )


def test_notification_outbox_uses_at_least_once_lease_retry_and_sent_status(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    store = NotificationOutboxStore(sqlite_engine, clock=clock)
    store.create_schema()
    rendered = _rendered_report()
    message = store.enqueue_report_notification(
        tenant_id="tenant-alpha",
        channel="webhook",
        dedupe_key="report:rpt_outbox:webhook",
        rendered_report=rendered,
        recipient={"kind": "webhook", "target": "research-report"},
        payload={"body": "Report ready"},
        max_attempts=2,
    )

    first_lease = store.lease_pending(
        tenant_id="tenant-alpha",
        channel=NotificationChannel.WEBHOOK,
        worker_id="worker-notify-1",
        lease_seconds=30,
        limit=1,
    )
    failed = store.mark_failed(
        first_lease[0].message_id,
        worker_id="worker-notify-1",
        error="temporary webhook timeout",
    )
    second_lease = store.lease_pending(
        tenant_id="tenant-alpha",
        channel=NotificationChannel.WEBHOOK,
        worker_id="worker-notify-2",
        lease_seconds=30,
        limit=1,
    )
    sent = store.mark_sent(
        second_lease[0].message_id,
        worker_id="worker-notify-2",
        provider_receipt_id="receipt-123",
    )
    no_more = store.lease_pending(
        tenant_id="tenant-alpha",
        channel=NotificationChannel.WEBHOOK,
        worker_id="worker-notify-3",
        lease_seconds=30,
        limit=1,
    )

    assert first_lease[0].message_id == message.message_id
    assert first_lease[0].status is NotificationOutboxStatus.SENDING
    assert first_lease[0].attempt == 1
    assert failed.status is NotificationOutboxStatus.PENDING
    assert failed.last_error == "temporary webhook timeout"
    assert second_lease[0].attempt == 2
    assert sent.status is NotificationOutboxStatus.SENT
    assert sent.provider_receipt_id == "receipt-123"
    assert sent.sent_at is not None
    assert no_more == ()
    assert store.get_message(message.message_id).status is NotificationOutboxStatus.SENT


def _rendered_report():
    return TrustedResearchReportRenderer().render(_verified_report(), context=_context())


def _context() -> ResearchReportRenderContext:
    return ResearchReportRenderContext(
        title="Trusted Alpha Outbox Report",
        model_provider="openai",
        model_name="gpt-4.1-mini",
        model_version="2026-07-01",
        prompt_versions={"decision": "decision@1.0.0"},
        total_cost_usd="0.123456",
        risk_summary="Risk gate pass.",
        disclaimer="Research only; not investment advice.",
    )


def _verified_report() -> ResearchReport:
    return ResearchReport(
        report_id="rpt_outbox",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[
            EvidenceRecord(
                evidence_id="ev_metric",
                kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
                evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
                title="Backtest metric evidence",
                summary="Formal backtest cumulative return metric.",
                source=EvidenceSource(
                    source_id="metric_report",
                    source_type="artifact",
                    schema_name="quant.backtest.performance_metrics",
                    schema_version="1.0.0",
                    source_uri="artifact://tenant/run/metrics@sha256",
                ),
                available_at=NOW,
                content_hash=HASH_A,
                trust=EvidenceTrustLevel.AUTHORITATIVE,
                dataset_versions=DATASET_VERSIONS,
                run_id="run-backtest",
                stage_id="stage-metrics",
                artifact_id="art_metrics",
                artifact_hash=HASH_A,
                formula_versions={"cumulative_return": "cumulative_return@1.0.0"},
                metadata={"llm_recompute_allowed": False},
            )
        ],
        citations=[
            ReportCitation(
                citation_id="cit_metric",
                evidence_id="ev_metric",
                evidence_field_path="body.returns.cumulative_return",
                cited_value="0.120000",
                unit="ratio",
                formula_version="cumulative_return@1.0.0",
                dataset_versions=DATASET_VERSIONS,
                run_id="run-backtest",
                stage_id="stage-metrics",
                artifact_hash=HASH_A,
            )
        ],
        claims=[
            ResearchClaim(
                claim_id="cl_metric",
                kind=ClaimKind.NUMERIC_METRIC,
                statement="The formal portfolio backtest cumulative return was 12.0%.",
                verification_status=ClaimVerificationStatus.VERIFIED,
                citation_ids=["cit_metric"],
                computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
                value="0.120000",
                unit="ratio",
                formula_version="cumulative_return@1.0.0",
                dataset_versions=DATASET_VERSIONS,
                run_id="run-backtest",
                stage_id="stage-metrics",
                artifact_hash=HASH_A,
            )
        ],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        trace_id="trace-report",
    )
