from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from serenity_alpha_lab.evidence.citation_validator import (
    CitationValidationIssue,
    CitationValidationResult,
    CitationValidator,
)
from serenity_alpha_lab.evidence.schema import ResearchReport, ResearchReportLevel


REPORT_RENDERER_CONTRACT_VERSION = "research.report_renderer@1.0.0"
TRUSTED_RESEARCH_REPORT_SCHEMA_NAME = "research.trusted_research_report"
TRUSTED_RESEARCH_REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_RENDERING_SCHEMA_NAME = "research.report_rendering"
REPORT_RENDERING_SCHEMA_VERSION = "1.0.0"
DEFAULT_REPORT_TEMPLATE_VERSION = "research.trusted_report.markdown_html@1.0.0"

_MONEY_QUANT = Decimal("0.000001")


class ReportRendererError(ValueError):
    """Raised when a report cannot be rendered from trusted structured data."""


@dataclass(frozen=True, slots=True)
class ResearchReportRenderContext:
    title: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_versions: Mapping[str, str]
    total_cost_usd: Decimal | str
    risk_summary: str
    disclaimer: str
    template_version: str = DEFAULT_REPORT_TEMPLATE_VERSION
    contract_version: str = REPORT_RENDERER_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _required_string("title", self.title))
        object.__setattr__(self, "model_provider", _required_string("model_provider", self.model_provider))
        object.__setattr__(self, "model_name", _required_string("model_name", self.model_name))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "prompt_versions", _string_mapping("prompt_versions", self.prompt_versions))
        object.__setattr__(self, "total_cost_usd", _money_string("total_cost_usd", self.total_cost_usd))
        object.__setattr__(self, "risk_summary", _required_string("risk_summary", self.risk_summary))
        object.__setattr__(self, "disclaimer", _required_string("disclaimer", self.disclaimer))
        object.__setattr__(self, "template_version", _required_string("template_version", self.template_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "template_version": self.template_version,
            "title": self.title,
            "model": {
                "provider": self.model_provider,
                "name": self.model_name,
                "version": self.model_version,
            },
            "prompt_versions": dict(self.prompt_versions),
            "cost": {
                "currency": "USD",
                "total_cost_usd": self.total_cost_usd,
            },
            "risk_summary": self.risk_summary,
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True, slots=True)
class TrustedResearchReport:
    validation_result: CitationValidationResult
    context: ResearchReportRenderContext
    contract_version: str = REPORT_RENDERER_CONTRACT_VERSION
    schema_name: str = TRUSTED_RESEARCH_REPORT_SCHEMA_NAME
    schema_version: str = TRUSTED_RESEARCH_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.validation_result) is not CitationValidationResult:
            raise ReportRendererError("validation_result must be a CitationValidationResult")
        if type(self.context) is not ResearchReportRenderContext:
            raise ReportRendererError("context must be a ResearchReportRenderContext")
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    @property
    def report_level(self) -> ResearchReportLevel:
        return self.validation_result.report_level

    @property
    def authoritative_json(self) -> dict[str, Any]:
        report = self.validation_result.validated_report
        record = {
            "authority": "canonical_json",
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "template_version": self.context.template_version,
            "report_id": report.report_id,
            "report_level": self.validation_result.report_level.value,
            "as_of": report.decision_time.isoformat(),
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "run_id": report.run_id,
            "trace_id": report.trace_id,
            "context": self.context.to_record(),
            "summary": {
                "claim_count": len(report.claims),
                "verified_claim_count": sum(1 for claim in report.claims if claim.verification_status.value == "verified"),
                "citation_count": len(report.citations),
                "evidence_count": len(report.evidence),
                "validation_issue_count": self.validation_result.issue_count,
            },
            "validation": _validation_record(self.validation_result),
            "report": report.to_record(),
        }
        return _drop_none(record)

    @property
    def authoritative_json_hash(self) -> str:
        return _hash_record(self.authoritative_json)

    def to_record(self) -> dict[str, Any]:
        record = dict(self.authoritative_json)
        record["authoritative_json_hash"] = self.authoritative_json_hash
        return record


@dataclass(frozen=True, slots=True)
class RenderedResearchReport:
    trusted_report: TrustedResearchReport
    markdown: str
    html: str
    markdown_source: str = "derived_from_authoritative_json"
    html_source: str = "derived_from_authoritative_json"
    contract_version: str = REPORT_RENDERER_CONTRACT_VERSION
    schema_name: str = REPORT_RENDERING_SCHEMA_NAME
    schema_version: str = REPORT_RENDERING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.trusted_report) is not TrustedResearchReport:
            raise ReportRendererError("trusted_report must be a TrustedResearchReport")
        object.__setattr__(self, "markdown", _required_string("markdown", self.markdown))
        object.__setattr__(self, "html", _required_string("html", self.html))
        object.__setattr__(self, "markdown_source", _required_string("markdown_source", self.markdown_source))
        object.__setattr__(self, "html_source", _required_string("html_source", self.html_source))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    @property
    def rendering_hash(self) -> str:
        return _hash_record(
            {
                "trusted_report_hash": self.trusted_report.authoritative_json_hash,
                "markdown": self.markdown,
                "html": self.html,
                "markdown_source": self.markdown_source,
                "html_source": self.html_source,
            }
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "trusted_report": self.trusted_report.to_record(),
            "markdown": self.markdown,
            "html": self.html,
            "markdown_source": self.markdown_source,
            "html_source": self.html_source,
            "rendering_hash": self.rendering_hash,
        }


class TrustedResearchReportRenderer:
    """Offline renderer that derives display formats from a validated ResearchReport."""

    def __init__(self, *, citation_validator: CitationValidator | None = None) -> None:
        self._citation_validator = citation_validator or CitationValidator()

    def render(
        self,
        report: ResearchReport,
        *,
        context: ResearchReportRenderContext,
        validation_result: CitationValidationResult | None = None,
    ) -> RenderedResearchReport:
        if type(report) is not ResearchReport:
            raise ReportRendererError("report must be a ResearchReport")
        if type(context) is not ResearchReportRenderContext:
            raise ReportRendererError("context must be a ResearchReportRenderContext")
        result = validation_result if validation_result is not None else self._citation_validator.validate(report)
        if type(result) is not CitationValidationResult:
            raise ReportRendererError("validation_result must be a CitationValidationResult")
        if result.report_id != report.report_id or result.validated_report.report_id != report.report_id:
            raise ReportRendererError("validation_result must match the ResearchReport report_id")

        trusted_report = TrustedResearchReport(validation_result=result, context=context)
        authoritative_json = trusted_report.authoritative_json
        markdown = _render_markdown(authoritative_json, trusted_report.authoritative_json_hash)
        rendered_html = _render_html(authoritative_json, trusted_report.authoritative_json_hash)
        return RenderedResearchReport(trusted_report=trusted_report, markdown=markdown, html=rendered_html)


def _render_markdown(record: Mapping[str, Any], authoritative_hash: str) -> str:
    context = _mapping(record["context"], "context")
    report = _mapping(record["report"], "report")
    validation = _mapping(record["validation"], "validation")
    lines = [
        f"# {context['title']}",
        "",
        f"Report Level: {record['report_level']}",
        f"As Of: {record['as_of']}",
        f"Generated At: {record.get('generated_at') or 'not recorded'}",
        f"Authority: canonical_json ({authoritative_hash})",
        f"Template: {record['template_version']}",
        f"Model: {context['model']['provider']} / {context['model']['name']} / {context['model']['version']}",
        f"Cost: USD {context['cost']['total_cost_usd']}",
        f"Risk: {context['risk_summary']}",
        f"Disclaimer: {context['disclaimer']}",
        "",
        "## Dataset Versions",
    ]
    for name, version in sorted(_mapping(report.get("dataset_versions"), "dataset_versions").items()):
        lines.append(f"- {name}: {version}")

    lines.extend(["", "## Claims"])
    claims = list(report.get("claims") or [])
    if not claims:
        lines.append("- No verified claims available.")
    for claim in claims:
        citations = ", ".join(claim.get("citation_ids") or []) or "none"
        lines.append(
            f"- [{claim['claim_id']}] {claim['statement']} "
            f"({claim['verification_status']}; citations: {citations})"
        )
        if claim.get("warnings"):
            lines.append(f"  warnings: {', '.join(claim['warnings'])}")

    lines.extend(["", "## Citations"])
    citations = list(report.get("citations") or [])
    if not citations:
        lines.append("- No citations available.")
    for citation in citations:
        lines.append(
            f"- [{citation['citation_id']}] evidence={citation['evidence_id']} "
            f"path={citation['evidence_field_path']}"
        )

    lines.extend(["", "## Evidence"])
    evidence_records = list(report.get("evidence") or [])
    if not evidence_records:
        lines.append("- No evidence records available.")
    for evidence in evidence_records:
        lines.append(
            f"- [{evidence['evidence_id']}] {evidence['title']} "
            f"({evidence['kind']}/{evidence['evaluation_scope']}; trust={evidence['trust']}; "
            f"available_at={evidence['available_at']})"
        )

    warnings = list(report.get("warnings") or [])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    issues = list(validation.get("issues") or [])
    if issues:
        lines.extend(["", "## Validation Issues"])
        for issue in issues:
            location = " ".join(
                item
                for item in (
                    f"claim={issue.get('claim_id')}" if issue.get("claim_id") else "",
                    f"citation={issue.get('citation_id')}" if issue.get("citation_id") else "",
                    f"evidence={issue.get('evidence_id')}" if issue.get("evidence_id") else "",
                )
                if item
            )
            lines.append(f"- {issue['code']}: {issue['message']}" + (f" ({location})" if location else ""))

    return "\n".join(lines).rstrip() + "\n"


def _render_html(record: Mapping[str, Any], authoritative_hash: str) -> str:
    context = _mapping(record["context"], "context")
    report = _mapping(record["report"], "report")
    validation = _mapping(record["validation"], "validation")

    parts = [
        f'<article class="trusted-research-report" data-authoritative-json-hash="{_e(authoritative_hash)}">',
        f"<h1>{_e(context['title'])}</h1>",
        "<dl>",
        f"<dt>Report Level</dt><dd>{_e(record['report_level'])}</dd>",
        f"<dt>As Of</dt><dd>{_e(record['as_of'])}</dd>",
        f"<dt>Generated At</dt><dd>{_e(record.get('generated_at') or 'not recorded')}</dd>",
        f"<dt>Authority</dt><dd>canonical_json ({_e(authoritative_hash)})</dd>",
        f"<dt>Template</dt><dd>{_e(record['template_version'])}</dd>",
        f"<dt>Model</dt><dd>{_e(context['model']['provider'])} / {_e(context['model']['name'])} / {_e(context['model']['version'])}</dd>",
        f"<dt>Cost</dt><dd>USD {_e(context['cost']['total_cost_usd'])}</dd>",
        f"<dt>Risk</dt><dd>{_e(context['risk_summary'])}</dd>",
        f"<dt>Disclaimer</dt><dd>{_e(context['disclaimer'])}</dd>",
        "</dl>",
        "<section><h2>Dataset Versions</h2><ul>",
    ]
    for name, version in sorted(_mapping(report.get("dataset_versions"), "dataset_versions").items()):
        parts.append(f"<li>{_e(name)}: {_e(version)}</li>")
    parts.append("</ul></section>")

    parts.append("<section><h2>Claims</h2><ul>")
    claims = list(report.get("claims") or [])
    if not claims:
        parts.append("<li>No verified claims available.</li>")
    for claim in claims:
        citations = ", ".join(claim.get("citation_ids") or []) or "none"
        parts.append(
            f"<li><strong>[{_e(claim['claim_id'])}]</strong> {_e(claim['statement'])} "
            f"({_e(claim['verification_status'])}; citations: {_e(citations)})</li>"
        )
    parts.append("</ul></section>")

    parts.append("<section><h2>Citations</h2><ul>")
    citations = list(report.get("citations") or [])
    if not citations:
        parts.append("<li>No citations available.</li>")
    for citation in citations:
        parts.append(
            f"<li><strong>[{_e(citation['citation_id'])}]</strong> evidence={_e(citation['evidence_id'])} "
            f"path={_e(citation['evidence_field_path'])}</li>"
        )
    parts.append("</ul></section>")

    parts.append("<section><h2>Evidence</h2><ul>")
    evidence_records = list(report.get("evidence") or [])
    if not evidence_records:
        parts.append("<li>No evidence records available.</li>")
    for evidence in evidence_records:
        parts.append(
            f"<li><strong>[{_e(evidence['evidence_id'])}]</strong> {_e(evidence['title'])} "
            f"({_e(evidence['kind'])}/{_e(evidence['evaluation_scope'])}; "
            f"trust={_e(evidence['trust'])}; available_at={_e(evidence['available_at'])})</li>"
        )
    parts.append("</ul></section>")

    warnings = list(report.get("warnings") or [])
    if warnings:
        parts.append("<section><h2>Warnings</h2><ul>")
        parts.extend(f"<li>{_e(warning)}</li>" for warning in warnings)
        parts.append("</ul></section>")

    issues = list(validation.get("issues") or [])
    if issues:
        parts.append("<section><h2>Validation Issues</h2><ul>")
        for issue in issues:
            parts.append(f"<li>{_e(issue['code'])}: {_e(issue['message'])}</li>")
        parts.append("</ul></section>")

    parts.append("</article>")
    return "".join(parts)


def _validation_record(result: CitationValidationResult) -> dict[str, Any]:
    return {
        "schema_name": result.schema_name,
        "schema_version": result.schema_version,
        "contract_version": result.contract_version,
        "report_id": result.report_id,
        "report_level": result.report_level.value,
        "issue_count": result.issue_count,
        "repair_attempted": result.repair_attempted,
        "removed_claim_ids": list(result.removed_claim_ids),
        "issues": [_issue_record(issue) for issue in result.issues],
        "failed_claims": [claim.to_record() for claim in result.failed_claims],
    }


def _issue_record(issue: CitationValidationIssue) -> dict[str, Any]:
    return _drop_none(issue.to_record())


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportRendererError(f"{field_name} must be a mapping")
    return value


def _string_mapping(field_name: str, value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ReportRendererError(f"{field_name} is required")
    return {
        _required_string(f"{field_name} key", key): _required_string(f"{field_name} value", item)
        for key, item in sorted(value.items())
    }


def _money_string(field_name: str, value: Decimal | str) -> str:
    try:
        amount = Decimal(str(value))
    except Exception as exc:  # pragma: no cover - exact Decimal exception varies by input type
        raise ReportRendererError(f"{field_name} must be a decimal amount") from exc
    if amount < Decimal("0"):
        raise ReportRendererError(f"{field_name} cannot be negative")
    return str(amount.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP))


def _hash_record(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(_json_ready(record), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise ReportRendererError(f"{field_name} is required")
    return value


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


__all__ = [
    "DEFAULT_REPORT_TEMPLATE_VERSION",
    "REPORT_RENDERER_CONTRACT_VERSION",
    "REPORT_RENDERING_SCHEMA_NAME",
    "REPORT_RENDERING_SCHEMA_VERSION",
    "TRUSTED_RESEARCH_REPORT_SCHEMA_NAME",
    "TRUSTED_RESEARCH_REPORT_SCHEMA_VERSION",
    "RenderedResearchReport",
    "ReportRendererError",
    "ResearchReportRenderContext",
    "TrustedResearchReport",
    "TrustedResearchReportRenderer",
]
