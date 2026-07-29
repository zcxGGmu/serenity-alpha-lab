from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from serenity_alpha_lab.evidence.report_renderer import RenderedResearchReport


REPORT_DELIVERY_UI_CONTRACT_VERSION = "research.report_delivery_ui@1.0.0"
REPORT_PAGE_SCHEMA_NAME = "research.report_page"
REPORT_PAGE_SCHEMA_VERSION = "1.0.0"


class ReportDeliveryError(ValueError):
    """Raised when trusted report delivery UI data cannot be built safely."""


@dataclass(frozen=True, slots=True)
class ReportDeliveryApiRoute:
    method: str
    path: str
    operation_id: str
    response_status: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _required_string("method", self.method).upper())
        object.__setattr__(self, "path", _required_string("path", self.path))
        object.__setattr__(self, "operation_id", _required_string("operation_id", self.operation_id))
        if type(self.response_status) is not int or not 100 <= self.response_status <= 599:
            raise ReportDeliveryError("response_status must be a valid HTTP status code")

    def to_record(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "operation_id": self.operation_id,
            "response_status": self.response_status,
        }


@dataclass(frozen=True, slots=True)
class ResearchReportNotificationStatus:
    message_id: str
    channel: str
    dedupe_key: str
    status: str
    attempt: int
    last_error: str | None = None
    sent_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "message_id", _required_string("message_id", self.message_id))
        object.__setattr__(self, "channel", _required_string("channel", self.channel))
        object.__setattr__(self, "dedupe_key", _required_string("dedupe_key", self.dedupe_key))
        object.__setattr__(self, "status", _required_string("status", self.status))
        if type(self.attempt) is not int or self.attempt < 0:
            raise ReportDeliveryError("attempt must be a non-negative integer")
        object.__setattr__(self, "last_error", _optional_string(self.last_error))
        if self.sent_at is not None:
            object.__setattr__(self, "sent_at", _require_aware_datetime("sent_at", self.sent_at))

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "message_id": self.message_id,
                "channel": self.channel,
                "dedupe_key": self.dedupe_key,
                "status": self.status,
                "attempt": self.attempt,
                "last_error": self.last_error,
                "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            }
        )


@dataclass(frozen=True, slots=True)
class ResearchReportPage:
    body: Mapping[str, Any]
    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.status_code) is not int or not 100 <= self.status_code <= 599:
            raise ReportDeliveryError("status_code must be a valid HTTP status code")
        object.__setattr__(self, "body", _json_copy(self.body))
        object.__setattr__(self, "headers", dict(self.headers))

    def to_record(self) -> dict[str, Any]:
        return dict(self.body)


class ResearchReportPagePresenter:
    """Builds report-page payloads from trusted canonical ResearchReport JSON only."""

    def build(
        self,
        rendered_report: RenderedResearchReport,
        *,
        notification_records: Sequence[ResearchReportNotificationStatus | Mapping[str, Any]] = (),
    ) -> ResearchReportPage:
        if type(rendered_report) is not RenderedResearchReport:
            raise ReportDeliveryError("rendered_report must be a RenderedResearchReport")

        trusted = rendered_report.trusted_report
        authoritative = trusted.authoritative_json
        report = _mapping(authoritative["report"], "report")
        context = _mapping(authoritative["context"], "context")
        validation = _mapping(authoritative["validation"], "validation")
        report_id = _required_string("report_id", str(authoritative["report_id"]))
        citations_by_id = {
            _required_string("citation_id", str(citation["citation_id"])): citation
            for citation in _sequence(report.get("citations"), "citations")
        }
        evidence_by_id = {
            _required_string("evidence_id", str(evidence["evidence_id"])): evidence
            for evidence in _sequence(report.get("evidence"), "evidence")
        }
        expanded_claims = [
            _expand_claim(claim, citations_by_id=citations_by_id, evidence_by_id=evidence_by_id)
            for claim in _sequence(report.get("claims"), "claims")
        ]
        evidence_lineage = [_evidence_summary(evidence) for evidence in evidence_by_id.values()]
        notification_statuses = [_notification_record(item) for item in notification_records]
        citation_graph = {
            "claims": expanded_claims,
            "evidence_lineage": evidence_lineage,
        }
        body = {
            "contract_version": REPORT_DELIVERY_UI_CONTRACT_VERSION,
            "schema": {"name": REPORT_PAGE_SCHEMA_NAME, "version": REPORT_PAGE_SCHEMA_VERSION},
            "authority": authoritative["authority"],
            "authoritative_json_hash": trusted.authoritative_json_hash,
            "rendering_hash": rendered_report.rendering_hash,
            "markdown_source": rendered_report.markdown_source,
            "html_source": rendered_report.html_source,
            "report": {
                "report_id": report_id,
                "report_level": authoritative["report_level"],
                "as_of": authoritative["as_of"],
                "generated_at": authoritative.get("generated_at"),
                "run_id": authoritative.get("run_id"),
                "trace_id": authoritative.get("trace_id"),
            },
            "display_context": context,
            "dataset_versions": _mapping(report.get("dataset_versions"), "dataset_versions"),
            "summary": authoritative.get("summary", {}),
            "validation": validation,
            "claims": expanded_claims,
            "citations": list(citations_by_id.values()),
            "evidence_lineage": evidence_lineage,
            "notification_statuses": notification_statuses,
            "citation_graph_hash": _hash_record(citation_graph),
            "display": {
                "markdown": rendered_report.markdown,
                "html": rendered_report.html,
            },
        }
        headers = {
            "Location": f"/api/v1/research/reports/{report_id}",
            "X-Authoritative-Json-Hash": trusted.authoritative_json_hash,
        }
        return ResearchReportPage(body=_drop_none(body), headers=headers)


def _expand_claim(
    claim: Mapping[str, Any],
    *,
    citations_by_id: Mapping[str, Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    claim_id = _required_string("claim_id", str(claim["claim_id"]))
    citation_ids = [str(citation_id) for citation_id in claim.get("citation_ids", [])]
    citations = []
    for citation_id in citation_ids:
        citation = citations_by_id.get(citation_id)
        if citation is None:
            raise ReportDeliveryError(f"claim {claim_id} references missing citation {citation_id}")
        evidence_id = _required_string("evidence_id", str(citation["evidence_id"]))
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise ReportDeliveryError(f"citation {citation_id} references missing evidence {evidence_id}")
        citations.append(_citation_summary(citation, evidence=evidence))

    record = dict(claim)
    record["citation_ids"] = citation_ids
    record["citations"] = citations
    return _drop_none(record)


def _citation_summary(citation: Mapping[str, Any], *, evidence: Mapping[str, Any]) -> dict[str, Any]:
    return _drop_none(
        {
            "citation_id": citation["citation_id"],
            "evidence_id": citation["evidence_id"],
            "evidence_field_path": citation["evidence_field_path"],
            "cited_value": citation.get("cited_value"),
            "unit": citation.get("unit"),
            "formula_version": citation.get("formula_version"),
            "dataset_versions": citation.get("dataset_versions", {}),
            "run_id": citation.get("run_id"),
            "stage_id": citation.get("stage_id"),
            "artifact_hash": citation.get("artifact_hash"),
            "evidence": _evidence_summary(evidence),
        }
    )


def _evidence_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(evidence.get("source"), "source")
    artifact = _drop_none(
        {
            "artifact_id": evidence.get("artifact_id"),
            "artifact_hash": evidence.get("artifact_hash"),
        }
    )
    return _drop_none(
        {
            "evidence_id": evidence["evidence_id"],
            "kind": evidence["kind"],
            "evaluation_scope": evidence["evaluation_scope"],
            "title": evidence["title"],
            "summary": evidence["summary"],
            "available_at": evidence["available_at"],
            "trust": evidence["trust"],
            "source": source,
            "source_link": source.get("source_uri"),
            "dataset_versions": evidence.get("dataset_versions", {}),
            "run_id": evidence.get("run_id"),
            "stage_id": evidence.get("stage_id"),
            "trace_id": evidence.get("trace_id"),
            "artifact": artifact if artifact else None,
            "formula_versions": evidence.get("formula_versions", {}),
        }
    )


def _notification_record(item: ResearchReportNotificationStatus | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(item, ResearchReportNotificationStatus):
        return item.to_record()
    if hasattr(item, "to_record"):
        return _json_copy(item.to_record())  # type: ignore[no-any-return, attr-defined]
    return _json_copy(item)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportDeliveryError(f"{field_name} must be a mapping")
    return value


def _sequence(value: Any, field_name: str) -> Sequence[Mapping[str, Any]]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise ReportDeliveryError(f"{field_name} must be a sequence")
    for item in value:
        if not isinstance(item, Mapping):
            raise ReportDeliveryError(f"{field_name} items must be mappings")
    return value


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise ReportDeliveryError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _require_aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ReportDeliveryError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _json_copy(value: Any) -> Any:
    return json.loads(_canonical_json(_json_ready(value)))


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    if isinstance(value, datetime):
        return _require_aware_datetime("datetime", value).isoformat()
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise ReportDeliveryError("value must be JSON serializable") from exc


def _hash_record(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


REPORT_DELIVERY_UI_ROUTES = (
    ReportDeliveryApiRoute(
        method="GET",
        path="/api/v1/research/reports/{report_id}",
        operation_id="getResearchReportPage",
        response_status=200,
    ),
    ReportDeliveryApiRoute(
        method="GET",
        path="/api/v1/research/reports/{report_id}/notifications",
        operation_id="listResearchReportNotificationStatuses",
        response_status=200,
    ),
)


__all__ = [
    "REPORT_DELIVERY_UI_CONTRACT_VERSION",
    "REPORT_DELIVERY_UI_ROUTES",
    "REPORT_PAGE_SCHEMA_NAME",
    "REPORT_PAGE_SCHEMA_VERSION",
    "ReportDeliveryApiRoute",
    "ReportDeliveryError",
    "ResearchReportNotificationStatus",
    "ResearchReportPage",
    "ResearchReportPagePresenter",
]
