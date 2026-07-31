from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
    ReportCitation,
)


QUANT_EVIDENCE_ADAPTER_CONTRACT_VERSION = "research.quant_evidence_adapter@1.0.0"
QUANT_EVIDENCE_ADAPTER_SCHEMA_NAME = "research.quant_evidence_adapter"
QUANT_EVIDENCE_ADAPTER_SCHEMA_VERSION = "1.0.0"


class QuantEvidenceAdapterError(ValueError):
    """Raised when quant output cannot be represented as P5 evidence."""


@dataclass(frozen=True, slots=True)
class QuantEvidenceAdapterRecord:
    evidence: EvidenceRecord
    body: Mapping[str, Any]
    citations: tuple[ReportCitation, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_record(),
            "body": _json_ready(self.body),
            "citations": [citation.to_record() for citation in self.citations],
            "contract_version": QUANT_EVIDENCE_ADAPTER_CONTRACT_VERSION,
            "schema_name": QUANT_EVIDENCE_ADAPTER_SCHEMA_NAME,
            "schema_version": QUANT_EVIDENCE_ADAPTER_SCHEMA_VERSION,
        }


class QuantEvidenceAdapter:
    """Pure mapper from already-produced quant DTOs into P5 evidence records."""

    @classmethod
    def default(cls) -> QuantEvidenceAdapter:
        return cls()

    def from_screen_snapshot(
        self,
        snapshot: Any,
        *,
        available_at: datetime,
        artifact_manifest: Any,
    ) -> QuantEvidenceAdapterRecord:
        body = _record_body(snapshot)
        manifest = _validated_manifest(artifact_manifest, body)
        dataset_versions = _mapping(body.get("dataset_versions"), "screen dataset_versions")
        evidence_id = _evidence_id(EvidenceKind.SCREEN_SNAPSHOT, body.get("screen_snapshot_id"), manifest)
        formula_version = f"screen_definition:{_required_string('definition_version_id', body.get('definition_version_id'))}"
        citations = tuple(
            _citation(
                evidence_id=evidence_id,
                path=f"body.results_by_instrument.{instrument_id}.final_score",
                value=result["final_score"],
                unit="score",
                formula_version=formula_version,
                dataset_versions=dataset_versions,
                run_id=_optional_str(body.get("run_id")),
                stage_id=_optional_str(body.get("stage_id")),
                artifact_hash=manifest.artifact_hash,
            )
            for instrument_id, result in sorted(_mapping(body.get("results_by_instrument"), "results_by_instrument").items())
            if isinstance(result, Mapping) and result.get("final_score") is not None
        )
        evidence = self._evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.SCREEN_SNAPSHOT,
            evaluation_scope=EvidenceEvaluationScope.SCREENING,
            title="Screen snapshot evidence",
            summary=_screen_summary(body),
            source_id=_required_string("screen_snapshot_id", body.get("screen_snapshot_id")),
            source_schema=_required_string("schema_name", body.get("schema_name")),
            source_schema_version=_required_string("schema_version", body.get("schema_version")),
            source_contract_version=_optional_str(body.get("contract_version")),
            available_at=available_at,
            manifest=manifest,
            dataset_versions=dataset_versions,
            run_id=_optional_str(body.get("run_id")),
            stage_id=_optional_str(body.get("stage_id")),
            trace_id=_optional_str(body.get("trace_id")),
            formula_versions={
                "screen_definition": formula_version,
                "screen_snapshot": "quant.screen_snapshot@1.0.0",
            },
            metadata={
                "adapter_input": "screen_snapshot",
                "as_of": body.get("as_of"),
                "passed_count": body.get("passed_count"),
                "failed_count": body.get("failed_count"),
                "numeric_citation_count": len(citations),
            },
        )
        return QuantEvidenceAdapterRecord(evidence=evidence, body=body, citations=citations)

    def from_factor_evaluation_report(
        self,
        report: Any,
        *,
        available_at: datetime,
        artifact_manifest: Any,
    ) -> QuantEvidenceAdapterRecord:
        body = _record_body(report)
        spec = _mapping(body.get("spec"), "factor spec")
        manifest = _validated_manifest(artifact_manifest, body)
        dataset_versions = _mapping(spec.get("dataset_versions"), "factor dataset_versions")
        evidence_id = _evidence_id(EvidenceKind.FACTOR_EVALUATION, spec.get("factor_version_id"), manifest)
        metric_set_version = _required_string("metric_set_version", spec.get("metric_set_version"))
        future_return_window = _mapping(spec.get("future_return_window"), "future_return_window")
        formula_versions = {
            "engine": _required_string("engine_version", spec.get("engine_version")),
            "metric_set": metric_set_version,
            "future_return_window": _required_string("future return window version", future_return_window.get("version")),
        }
        citations = tuple(
            citation
            for citation in (
                _optional_numeric_citation(
                    evidence_id=evidence_id,
                    body=body,
                    path="body.ic_summary.mean_ic",
                    unit="correlation",
                    formula_version=metric_set_version,
                    dataset_versions=dataset_versions,
                    run_id=_optional_str(spec.get("run_id")),
                    stage_id=_optional_str(spec.get("stage_id")),
                    artifact_hash=manifest.artifact_hash,
                ),
                _optional_numeric_citation(
                    evidence_id=evidence_id,
                    body=body,
                    path="body.ic_summary.icir",
                    unit="ratio",
                    formula_version=metric_set_version,
                    dataset_versions=dataset_versions,
                    run_id=_optional_str(spec.get("run_id")),
                    stage_id=_optional_str(spec.get("stage_id")),
                    artifact_hash=manifest.artifact_hash,
                ),
                _optional_numeric_citation(
                    evidence_id=evidence_id,
                    body=body,
                    path="body.group_return_summary.long_short_mean_return",
                    unit="ratio",
                    formula_version=metric_set_version,
                    dataset_versions=dataset_versions,
                    run_id=_optional_str(spec.get("run_id")),
                    stage_id=_optional_str(spec.get("stage_id")),
                    artifact_hash=manifest.artifact_hash,
                ),
                _optional_numeric_citation(
                    evidence_id=evidence_id,
                    body=body,
                    path="body.monotonicity.direction_adjusted_score",
                    unit="score",
                    formula_version=metric_set_version,
                    dataset_versions=dataset_versions,
                    run_id=_optional_str(spec.get("run_id")),
                    stage_id=_optional_str(spec.get("stage_id")),
                    artifact_hash=manifest.artifact_hash,
                ),
                _optional_numeric_citation(
                    evidence_id=evidence_id,
                    body=body,
                    path="body.turnover_summary.mean_turnover",
                    unit="ratio",
                    formula_version=metric_set_version,
                    dataset_versions=dataset_versions,
                    run_id=_optional_str(spec.get("run_id")),
                    stage_id=_optional_str(spec.get("stage_id")),
                    artifact_hash=manifest.artifact_hash,
                ),
            )
            if citation is not None
        )
        evidence = self._evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.FACTOR_EVALUATION,
            evaluation_scope=EvidenceEvaluationScope.FACTOR_EVALUATION,
            title="Factor evaluation evidence",
            summary=f"Factor {spec.get('factor_definition_id')} evaluation metrics and lineage.",
            source_id=_required_string("factor_version_id", spec.get("factor_version_id")),
            source_schema=_required_string("schema_name", spec.get("schema_name")),
            source_schema_version=_required_string("schema_version", spec.get("schema_version")),
            source_contract_version=_optional_str(spec.get("contract_version")),
            available_at=available_at,
            manifest=manifest,
            dataset_versions=dataset_versions,
            run_id=_optional_str(spec.get("run_id")),
            stage_id=_optional_str(spec.get("stage_id")),
            formula_versions=formula_versions,
            metadata={
                "adapter_input": "factor_evaluation_report",
                "factor_definition_id": spec.get("factor_definition_id"),
                "factor_version_id": spec.get("factor_version_id"),
                "formal": spec.get("formal"),
                "numeric_citation_count": len(citations),
            },
        )
        return QuantEvidenceAdapterRecord(evidence=evidence, body=body, citations=citations)

    def from_backtest_performance_metrics(
        self,
        report: Any,
        *,
        dataset_versions: Mapping[str, str],
        available_at: datetime,
        artifact_manifest: Any,
    ) -> QuantEvidenceAdapterRecord:
        body = _record_body(report)
        manifest = _validated_manifest(artifact_manifest, body)
        versions = _mapping(dataset_versions, "backtest metrics dataset_versions")
        evidence_id = _evidence_id(EvidenceKind.BACKTEST_PERFORMANCE_METRICS, body.get("report_id"), manifest)
        formula_versions = {
            str(metric_id): str(version)
            for metric_id, version in _mapping(body.get("metric_formula_versions"), "metric_formula_versions").items()
        }
        citations = tuple(
            _citation(
                evidence_id=evidence_id,
                path=path,
                value=value,
                unit=_metric_unit(metric_id),
                formula_version=formula_versions.get(metric_id, _required_string("metric_set_version", body.get("metric_set_version"))),
                dataset_versions=versions,
                run_id=_optional_str(body.get("run_id")),
                stage_id=_optional_str(body.get("stage_id")),
                artifact_hash=manifest.artifact_hash,
            )
            for section in ("returns", "risk", "drawdown", "trading", "costs", "benchmark")
            for metric_id, value, path in _scalar_metric_items(body, section)
        )
        evidence = self._evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
            evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            title="Formal backtest performance metric evidence",
            summary=f"Performance metric report for {body.get('spec_id')} from {body.get('sample_start')} to {body.get('sample_end')}.",
            source_id=_required_string("report_id", body.get("report_id")),
            source_schema=_required_string("schema_name", body.get("schema_name")),
            source_schema_version=_required_string("schema_version", body.get("schema_version")),
            source_contract_version=_optional_str(body.get("contract_version")),
            available_at=available_at,
            manifest=manifest,
            dataset_versions=versions,
            run_id=_optional_str(body.get("run_id")),
            stage_id=_optional_str(body.get("stage_id")),
            formula_versions=formula_versions,
            metadata={
                "adapter_input": "backtest_performance_metrics",
                "spec_id": body.get("spec_id"),
                "spec_hash": body.get("spec_hash"),
                "metric_set_version": body.get("metric_set_version"),
                "numeric_citation_count": len(citations),
            },
        )
        return QuantEvidenceAdapterRecord(evidence=evidence, body=body, citations=citations)

    def from_risk_policy_result(
        self,
        result: Any,
        *,
        dataset_versions: Mapping[str, str],
        available_at: datetime,
        artifact_manifest: Any,
    ) -> QuantEvidenceAdapterRecord:
        body = _record_body(result)
        manifest = _validated_manifest(artifact_manifest, body)
        versions = _mapping(dataset_versions, "risk dataset_versions")
        policy = _mapping(body.get("policy"), "risk policy")
        evidence_id = _evidence_id(EvidenceKind.RISK_POLICY_RESULT, body.get("result_id"), manifest)
        formula_versions = {
            "policy": f"{_required_string('policy_id', policy.get('policy_id'))}@{_required_string('policy_version', policy.get('policy_version'))}",
            "evaluator": _required_string("evaluator_version", body.get("evaluator_version")),
        }
        citations: list[ReportCitation] = [
            _citation(
                evidence_id=evidence_id,
                path="body.status",
                value=_required_string("risk status", body.get("status")),
                unit=None,
                formula_version=formula_versions["evaluator"],
                dataset_versions=versions,
                run_id=_optional_str(body.get("run_id")),
                stage_id=_optional_str(body.get("stage_id")),
                artifact_hash=manifest.artifact_hash,
            )
        ]
        for index, outcome in enumerate(body.get("outcomes", ())):
            if isinstance(outcome, Mapping):
                for field_name, unit in (("observed_value", "ratio"), ("limit_value", "ratio")):
                    if outcome.get(field_name) is not None:
                        citations.append(
                            _citation(
                                evidence_id=evidence_id,
                                path=f"body.outcomes.{index}.{field_name}",
                                value=outcome[field_name],
                                unit=unit,
                                formula_version=formula_versions["evaluator"],
                                dataset_versions=versions,
                                run_id=_optional_str(body.get("run_id")),
                                stage_id=_optional_str(body.get("stage_id")),
                                artifact_hash=manifest.artifact_hash,
                            )
                        )
        evidence = self._evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.RISK_POLICY_RESULT,
            evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            title="Formal backtest risk policy evidence",
            summary=f"Risk policy result {body.get('status')} for {body.get('spec_id')}.",
            source_id=_required_string("result_id", body.get("result_id")),
            source_schema=_required_string("schema_name", body.get("schema_name")),
            source_schema_version=_required_string("schema_version", body.get("schema_version")),
            source_contract_version=_optional_str(body.get("contract_version")),
            available_at=available_at,
            manifest=manifest,
            dataset_versions=versions,
            run_id=_optional_str(body.get("run_id")),
            stage_id=_optional_str(body.get("stage_id")),
            formula_versions=formula_versions,
            metadata={
                "adapter_input": "risk_policy_result",
                "spec_id": body.get("spec_id"),
                "spec_hash": body.get("spec_hash"),
                "risk_status": body.get("status"),
                "numeric_citation_count": sum(1 for citation in citations if citation.unit is not None),
            },
        )
        return QuantEvidenceAdapterRecord(evidence=evidence, body=body, citations=tuple(citations))

    def from_backtest_bias_audit_report(
        self,
        report: Any,
        *,
        dataset_versions: Mapping[str, str],
        available_at: datetime,
        artifact_manifest: Any,
    ) -> QuantEvidenceAdapterRecord:
        body = _record_body(report)
        manifest = _validated_manifest(artifact_manifest, body)
        versions = _mapping(dataset_versions, "bias audit dataset_versions")
        policy = _mapping(body.get("policy"), "bias audit policy")
        evidence_id = _evidence_id(EvidenceKind.BACKTEST_BIAS_AUDIT, body.get("report_id"), manifest)
        formula_versions = {
            "policy": f"{_required_string('policy_id', policy.get('policy_id'))}@{_required_string('policy_version', policy.get('policy_version'))}",
            "auditor": _required_string("auditor_version", body.get("auditor_version")),
        }
        citations: list[ReportCitation] = [
            _citation(
                evidence_id=evidence_id,
                path="body.status",
                value=_required_string("bias audit status", body.get("status")),
                unit=None,
                formula_version=formula_versions["auditor"],
                dataset_versions=versions,
                run_id=_optional_str(body.get("run_id")),
                stage_id=_optional_str(body.get("stage_id")),
                artifact_hash=manifest.artifact_hash,
            )
        ]
        for index, outcome in enumerate(body.get("outcomes", ())):
            if isinstance(outcome, Mapping):
                for field_name, unit in (("observed_value", "ratio"), ("limit_value", "ratio")):
                    if outcome.get(field_name) is not None:
                        citations.append(
                            _citation(
                                evidence_id=evidence_id,
                                path=f"body.outcomes.{index}.{field_name}",
                                value=outcome[field_name],
                                unit=unit,
                                formula_version=formula_versions["auditor"],
                                dataset_versions=versions,
                                run_id=_optional_str(body.get("run_id")),
                                stage_id=_optional_str(body.get("stage_id")),
                                artifact_hash=manifest.artifact_hash,
                            )
                        )
        evidence = self._evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.BACKTEST_BIAS_AUDIT,
            evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            title="Formal backtest bias audit evidence",
            summary=f"Bias audit report {body.get('status')} for {body.get('spec_id')}.",
            source_id=_required_string("report_id", body.get("report_id")),
            source_schema=_required_string("schema_name", body.get("schema_name")),
            source_schema_version=_required_string("schema_version", body.get("schema_version")),
            source_contract_version=_optional_str(body.get("contract_version")),
            available_at=available_at,
            manifest=manifest,
            dataset_versions=versions,
            run_id=_optional_str(body.get("run_id")),
            stage_id=_optional_str(body.get("stage_id")),
            formula_versions=formula_versions,
            metadata={
                "adapter_input": "backtest_bias_audit_report",
                "spec_id": body.get("spec_id"),
                "spec_hash": body.get("spec_hash"),
                "audit_status": body.get("status"),
                "eligible_for_ranking": body.get("eligible_for_ranking"),
                "agent_strong_conclusion_allowed": body.get("agent_strong_conclusion_allowed"),
                "numeric_citation_count": sum(1 for citation in citations if citation.unit is not None),
            },
        )
        return QuantEvidenceAdapterRecord(evidence=evidence, body=body, citations=tuple(citations))

    def _evidence(
        self,
        *,
        evidence_id: str,
        kind: EvidenceKind,
        evaluation_scope: EvidenceEvaluationScope,
        title: str,
        summary: str,
        source_id: str,
        source_schema: str,
        source_schema_version: str,
        source_contract_version: str | None,
        available_at: datetime,
        manifest: _ManifestView,
        dataset_versions: Mapping[str, str],
        formula_versions: Mapping[str, str],
        metadata: Mapping[str, Any],
        run_id: str | None = None,
        stage_id: str | None = None,
        trace_id: str | None = None,
        instrument_id: str | None = None,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=evidence_id,
            kind=kind,
            evaluation_scope=evaluation_scope,
            title=title,
            summary=summary,
            source=EvidenceSource(
                source_id=source_id,
                source_type="artifact",
                schema_name=source_schema,
                schema_version=source_schema_version,
                contract_version=source_contract_version,
                source_uri=manifest.uri,
                producer=QUANT_EVIDENCE_ADAPTER_CONTRACT_VERSION,
            ),
            available_at=available_at,
            content_hash=manifest.artifact_hash,
            trust=EvidenceTrustLevel.AUTHORITATIVE,
            dataset_versions=dict(dataset_versions),
            instrument_id=instrument_id,
            run_id=run_id,
            stage_id=stage_id,
            trace_id=trace_id,
            artifact_id=manifest.artifact_id,
            artifact_hash=manifest.artifact_hash,
            formula_versions=dict(formula_versions),
            metadata={
                "adapter_contract_version": QUANT_EVIDENCE_ADAPTER_CONTRACT_VERSION,
                "adapter_schema_name": QUANT_EVIDENCE_ADAPTER_SCHEMA_NAME,
                "adapter_schema_version": QUANT_EVIDENCE_ADAPTER_SCHEMA_VERSION,
                "artifact": manifest.to_record(),
                "llm_recompute_allowed": False,
                **dict(metadata),
            },
        )


@dataclass(frozen=True, slots=True)
class _ManifestView:
    artifact_id: str
    sha256: str
    artifact_hash: str
    uri: str
    record: Mapping[str, Any]

    def to_record(self) -> dict[str, Any]:
        return dict(self.record)


def _validated_manifest(manifest: Any, body: Mapping[str, Any]) -> _ManifestView:
    if manifest is None:
        raise QuantEvidenceAdapterError("artifact_manifest is required for quant evidence traceability")
    artifact_id = _required_string("artifact_id", getattr(manifest, "artifact_id", None))
    sha256 = _required_string("artifact sha256", getattr(manifest, "sha256", None)).lower()
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise QuantEvidenceAdapterError("artifact_manifest sha256 must be 64 lowercase hex chars")
    body_sha = _sha256_body(body)
    if body_sha != sha256:
        raise QuantEvidenceAdapterError("artifact_manifest sha256 must match canonical quant evidence body")
    record = manifest.to_record() if hasattr(manifest, "to_record") else {"artifact_id": artifact_id, "sha256": sha256}
    return _ManifestView(
        artifact_id=artifact_id,
        sha256=sha256,
        artifact_hash=f"sha256:{sha256}",
        uri=str(getattr(manifest, "uri", "")),
        record=_json_ready(record),
    )


def _record_body(value: Any) -> Mapping[str, Any]:
    if not hasattr(value, "to_record"):
        raise QuantEvidenceAdapterError("quant output must expose to_record()")
    record = value.to_record()
    if not isinstance(record, Mapping) or not record:
        raise QuantEvidenceAdapterError("quant output to_record() must return a non-empty mapping")
    return _json_ready(record)


def _citation(
    *,
    evidence_id: str,
    path: str,
    value: Any,
    unit: str | None,
    formula_version: str | None,
    dataset_versions: Mapping[str, str],
    run_id: str | None,
    stage_id: str | None,
    artifact_hash: str,
) -> ReportCitation:
    return ReportCitation(
        citation_id=f"cit_{hashlib.sha256(f'{evidence_id}|{path}'.encode('utf-8')).hexdigest()[:24]}",
        evidence_id=evidence_id,
        evidence_field_path=path,
        cited_value=_json_ready(value),
        unit=unit,
        formula_version=formula_version,
        dataset_versions=dict(dataset_versions),
        run_id=run_id,
        stage_id=stage_id,
        artifact_hash=artifact_hash,
    )


def _optional_numeric_citation(
    *,
    evidence_id: str,
    body: Mapping[str, Any],
    path: str,
    unit: str,
    formula_version: str,
    dataset_versions: Mapping[str, str],
    run_id: str | None,
    stage_id: str | None,
    artifact_hash: str,
) -> ReportCitation | None:
    value = _value_at_path(body, path)
    if value is None:
        return None
    return _citation(
        evidence_id=evidence_id,
        path=path,
        value=value,
        unit=unit,
        formula_version=formula_version,
        dataset_versions=dataset_versions,
        run_id=run_id,
        stage_id=stage_id,
        artifact_hash=artifact_hash,
    )


def _value_at_path(body: Mapping[str, Any], path: str) -> Any:
    parts = path.split(".")
    if not parts or parts[0] != "body":
        raise QuantEvidenceAdapterError("citation path must start with body")
    current: Any = body
    for part in parts[1:]:
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        if isinstance(current, (list, tuple)):
            current = current[int(part)]
            continue
        return None
    return current


def _scalar_metric_items(body: Mapping[str, Any], section: str) -> tuple[tuple[str, Any, str], ...]:
    metrics = body.get(section)
    if not isinstance(metrics, Mapping):
        return ()
    return tuple(
        (str(metric_id), value, f"body.{section}.{metric_id}")
        for metric_id, value in sorted(metrics.items())
        if not isinstance(value, (Mapping, list, tuple)) and value is not None
    )


def _metric_unit(metric_id: str) -> str:
    if metric_id in {"sharpe_ratio", "sortino_ratio", "calmar_ratio", "profit_loss_ratio", "information_ratio"}:
        return "ratio"
    if metric_id == "max_drawdown_duration_periods":
        return "period"
    return "ratio"


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise QuantEvidenceAdapterError(f"{field_name} must be a non-empty mapping")
    return _json_ready(value)


def _screen_summary(body: Mapping[str, Any]) -> str:
    return (
        f"Screen snapshot {body.get('screen_snapshot_id')} contains "
        f"{body.get('passed_count')} passed and {body.get('failed_count')} failed instruments."
    )


def _evidence_id(kind: EvidenceKind, source_id: Any, manifest: _ManifestView) -> str:
    source = _required_string("source_id", source_id)
    digest = hashlib.sha256(f"{kind.value}|{source}|{manifest.sha256}".encode("utf-8")).hexdigest()[:24]
    return f"ev_{kind.value}_{digest}"


def _sha256_body(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(body)).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(_json_ready(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _required_string(field_name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise QuantEvidenceAdapterError(f"{field_name} is required")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


__all__ = [
    "QUANT_EVIDENCE_ADAPTER_CONTRACT_VERSION",
    "QUANT_EVIDENCE_ADAPTER_SCHEMA_NAME",
    "QUANT_EVIDENCE_ADAPTER_SCHEMA_VERSION",
    "QuantEvidenceAdapter",
    "QuantEvidenceAdapterError",
    "QuantEvidenceAdapterRecord",
]
