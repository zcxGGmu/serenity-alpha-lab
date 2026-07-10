from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import re
from typing import Mapping, Sequence
from urllib.parse import urlparse


SCHEMA_VERSION = 1
ARTIFACT_TYPE = "stock_analysis_report"
MANIFEST_FILENAME = "analysis-report-manifest.json"
REPORT_RELATIVE_PATH = Path("reports/stock-analysis-report.md")

FORBIDDEN_FIELDS = {
    "operation_advice",
    "buy",
    "sell",
    "target_price",
    "price_target",
    "stop_loss",
    "take_profit",
    "position_size",
    "position_sizing",
    "broker",
    "order",
    "trade_action",
}


@dataclass(frozen=True)
class ArtifactRepositoryError(ValueError):
    status_code: int
    code: str
    reason: str

    def __str__(self) -> str:
        return f"{self.code}:{self.reason}"

    def to_payload(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "reason": self.reason}}


class StockAnalysisArtifactRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load_latest_summary(self) -> dict[str, object]:
        manifest = self.load_latest_manifest()
        return _normalize_summary(manifest)

    def load_latest_manifest(self) -> dict[str, object]:
        manifest = _read_manifest(self.root)
        _validate_manifest(manifest, self.root)
        return _allowlisted_manifest(manifest)

    def load_latest_report(self) -> str:
        manifest = self.load_latest_manifest()
        report_path = _resolve_report_path(self.root, manifest)
        try:
            return report_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ArtifactRepositoryError(
                404,
                "artifact_not_found",
                "stock_analysis_report_missing",
            ) from exc
        except (OSError, UnicodeError) as exc:
            raise ArtifactRepositoryError(
                422,
                "artifact_invalid",
                "stock_analysis_report_unreadable",
            ) from exc


def _read_manifest(root: Path) -> dict[str, object]:
    manifest_path = _resolve_contained_path(
        root,
        Path(MANIFEST_FILENAME),
        "manifest_path_invalid",
    )
    try:
        raw_manifest = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ArtifactRepositoryError(
            404,
            "artifact_not_found",
            "stock_analysis_artifact_missing",
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise ArtifactRepositoryError(
            422,
            "artifact_invalid",
            "manifest_unreadable",
        ) from exc
    try:
        manifest = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise ArtifactRepositoryError(
            422,
            "artifact_invalid",
            "manifest_json_invalid",
        ) from exc
    if not isinstance(manifest, dict):
        raise ArtifactRepositoryError(
            422,
            "artifact_invalid",
            "manifest_object_required",
        )
    return manifest


def _validate_manifest(manifest: Mapping[str, object], root: Path) -> None:
    if _find_forbidden_key(manifest) is not None:
        raise ArtifactRepositoryError(
            422,
            "artifact_invalid",
            "forbidden_field",
        )

    if "schema_version" not in manifest:
        _invalid("schema_version_missing")
    schema_version = manifest["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != SCHEMA_VERSION
    ):
        _invalid("schema_version_unsupported")
    if "artifact_type" not in manifest:
        _invalid("artifact_type_missing")
    if manifest["artifact_type"] != ARTIFACT_TYPE:
        _invalid("artifact_type_unsupported")

    for key in ("symbol", "stock_name", "query"):
        _require_non_empty_string(manifest, key, f"{key}_invalid")
    _validate_generated_at(manifest)

    source_coverage = _require_mapping(
        manifest,
        "source_coverage",
        "source_coverage_missing",
    )
    _validate_source_coverage_numbers(source_coverage)

    if manifest.get("research_only") is not True:
        _blocked("research_only_required")

    report_gate = _require_mapping(
        manifest,
        "report_gate",
        "report_gate_missing",
    )
    if report_gate.get("research_only") is not True:
        _blocked("report_gate_research_only_required")

    raw_safety = manifest.get("safety")
    if not isinstance(raw_safety, Mapping):
        _blocked("report_safety_failed")
    safety = raw_safety
    if safety.get("passed") is not True:
        _blocked("report_safety_failed")

    boundary = safety.get("boundary")
    if (
        not isinstance(boundary, str)
        or not boundary.strip()
        or "research only" not in boundary.lower()
    ):
        _blocked("research_boundary_required")

    readiness = _require_mapping(manifest, "readiness", "readiness_missing")
    _validate_readiness(readiness)
    _validate_report_gate_details(report_gate)
    _validate_source_coverage_details(source_coverage)

    skeptical_review = _require_mapping(
        manifest,
        "skeptical_review",
        "skeptical_review_missing",
    )
    _validate_skeptical_review(skeptical_review)
    _validate_safety_findings(safety)

    reports = _require_mapping(manifest, "reports", "reports_missing")
    _require_non_empty_string(reports, "stock_analysis", "report_path_invalid")
    ui_path = _require_non_empty_string(reports, "ui", "reports_invalid")
    if ui_path != "index.html":
        _invalid("reports_invalid")

    _validate_key_claims(manifest.get("key_claims"))
    _resolve_report_path(root, manifest)


def _validate_generated_at(manifest: Mapping[str, object]) -> None:
    generated_at = _require_non_empty_string(
        manifest,
        "generated_at",
        "generated_at_invalid",
    )
    try:
        parsed = datetime.fromisoformat(generated_at)
    except ValueError:
        _invalid("generated_at_invalid")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _invalid("generated_at_invalid")


def _validate_readiness(readiness: Mapping[str, object]) -> None:
    _require_non_empty_string(readiness, "status", "readiness_invalid")
    _require_non_empty_string(readiness, "reason", "readiness_invalid")
    _require_string_list(readiness, "flags", "readiness_invalid")


def _validate_report_gate_details(
    report_gate: Mapping[str, object],
) -> None:
    _require_non_empty_string(
        report_gate,
        "status",
        "report_gate_invalid",
    )
    _require_non_empty_string(
        report_gate,
        "reason",
        "report_gate_invalid",
    )


def _validate_source_coverage_numbers(
    source_coverage: Mapping[str, object],
) -> None:
    _require_non_empty_string(
        source_coverage,
        "focus_ticker",
        "source_coverage_invalid",
    )
    for key in (
        "evidence_count",
        "focus_evidence_count",
        "primary_count",
        "risk_count",
        "external_non_serenity_count",
    ):
        _require_finite_number(
            source_coverage,
            key,
            "source_coverage_invalid",
            integer=True,
        )
    for key in ("methodology_share", "placeholder_share"):
        _require_finite_number(
            source_coverage,
            key,
            "source_coverage_invalid",
            integer=False,
        )


def _validate_source_coverage_details(
    source_coverage: Mapping[str, object],
) -> None:
    _require_non_empty_string(
        source_coverage,
        "status",
        "source_coverage_invalid",
    )
    flags = _require_list(
        source_coverage,
        "flags",
        "source_coverage_invalid",
    )
    for flag in flags:
        if not isinstance(flag, Mapping):
            _invalid("source_coverage_invalid")
        for key in ("code", "severity", "message", "recommendation"):
            _require_string(flag, key, "source_coverage_invalid")


def _validate_skeptical_review(
    skeptical_review: Mapping[str, object],
) -> None:
    _require_non_empty_string(
        skeptical_review,
        "summary",
        "skeptical_review_invalid",
    )
    counter_thesis = _require_string_list(
        skeptical_review,
        "counter_thesis",
        "skeptical_review_invalid",
    )
    if not counter_thesis or not all(item.strip() for item in counter_thesis):
        _invalid("skeptical_review_invalid")


def _validate_safety_findings(safety: Mapping[str, object]) -> None:
    findings = _require_list(safety, "findings", "report_safety_invalid")
    for finding in findings:
        if not isinstance(finding, Mapping):
            _invalid("report_safety_invalid")
        _require_integer(
            finding,
            "line_number",
            "report_safety_invalid",
        )
        _require_string(finding, "phrase", "report_safety_invalid")
        _require_string(finding, "line", "report_safety_invalid")


def _validate_key_claims(raw_claims: object) -> None:
    if not isinstance(raw_claims, list) or not raw_claims:
        _invalid("key_claims_missing")
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, Mapping):
            _invalid("key_claim_invalid")
        _require_non_empty_string(
            raw_claim,
            "claim_id",
            "key_claim_invalid",
        )
        _require_non_empty_string(raw_claim, "claim", "key_claim_invalid")
        _require_string_list(
            raw_claim,
            "diagnostics",
            "key_claim_invalid",
        )
        provenance_refs = raw_claim.get("provenance_refs")
        if not isinstance(provenance_refs, list) or not provenance_refs:
            _invalid("key_claim_provenance_missing")
        for raw_ref in provenance_refs:
            if not isinstance(raw_ref, Mapping):
                _invalid("key_claim_provenance_missing")
            for key in (
                "evidence_id",
                "source_title",
                "excerpt",
            ):
                _require_non_empty_string(
                    raw_ref,
                    key,
                    "key_claim_provenance_missing",
                )
            source_url = _require_non_empty_string(
                raw_ref,
                "source_url",
                "key_claim_provenance_missing",
            )
            _validate_source_url(source_url)


def _resolve_report_path(
    root: Path,
    manifest: Mapping[str, object],
) -> Path:
    reports = manifest.get("reports")
    if not isinstance(reports, Mapping):
        _invalid("reports_missing")
    relative_path = reports.get("stock_analysis")
    if not isinstance(relative_path, str) or not relative_path.strip():
        _invalid("report_path_invalid")
    if relative_path != REPORT_RELATIVE_PATH.as_posix():
        _invalid("report_path_invalid")
    return _resolve_contained_path(
        root,
        REPORT_RELATIVE_PATH,
        "report_path_invalid",
    )


def _resolve_contained_path(
    root: Path,
    relative_path: Path,
    reason: str,
) -> Path:
    try:
        root_resolved = root.resolve()
        resolved_path = (root_resolved / relative_path).resolve()
    except (OSError, RuntimeError, ValueError):
        _invalid(reason)
    try:
        resolved_path.relative_to(root_resolved)
    except ValueError:
        _invalid(reason)
    return resolved_path


def _validate_source_url(source_url: str) -> None:
    if any(character.isspace() for character in source_url):
        _invalid("key_claim_provenance_missing")
    try:
        parsed = urlparse(source_url)
        username = parsed.username
        password = parsed.password
    except ValueError:
        _invalid("key_claim_provenance_missing")
    if parsed.scheme not in {"http", "https", "serenity"}:
        _invalid("key_claim_provenance_missing")
    if not parsed.netloc or username or password:
        _invalid("key_claim_provenance_missing")


def _normalize_summary(
    manifest: Mapping[str, object],
) -> dict[str, object]:
    summary = _allowlisted_manifest(manifest)
    summary["reports"] = {
        "stock_analysis": "/api/artifacts/stock-analysis/latest/report",
        "manifest": "/api/artifacts/stock-analysis/latest/manifest",
    }
    return summary


def _allowlisted_manifest(
    manifest: Mapping[str, object],
) -> dict[str, object]:
    readiness = _mapping(manifest["readiness"])
    report_gate = _mapping(manifest["report_gate"])
    source_coverage = _mapping(manifest["source_coverage"])
    skeptical_review = _mapping(manifest["skeptical_review"])
    reports = _mapping(manifest["reports"])
    safety = _mapping(manifest["safety"])

    return {
        "schema_version": manifest["schema_version"],
        "artifact_type": manifest["artifact_type"],
        "symbol": manifest["symbol"],
        "stock_name": manifest["stock_name"],
        "query": manifest["query"],
        "generated_at": manifest["generated_at"],
        "research_only": manifest["research_only"],
        "readiness": {
            "status": readiness["status"],
            "reason": readiness["reason"],
            "flags": list(_sequence(readiness["flags"])),
        },
        "report_gate": {
            "status": report_gate["status"],
            "reason": report_gate["reason"],
            "research_only": report_gate["research_only"],
        },
        "source_coverage": {
            "status": source_coverage["status"],
            "focus_ticker": source_coverage["focus_ticker"],
            "evidence_count": source_coverage["evidence_count"],
            "focus_evidence_count": source_coverage["focus_evidence_count"],
            "primary_count": source_coverage["primary_count"],
            "risk_count": source_coverage["risk_count"],
            "methodology_share": source_coverage["methodology_share"],
            "placeholder_share": source_coverage["placeholder_share"],
            "external_non_serenity_count": source_coverage[
                "external_non_serenity_count"
            ],
            "flags": [
                {
                    "code": flag["code"],
                    "severity": flag["severity"],
                    "message": flag["message"],
                    "recommendation": flag["recommendation"],
                }
                for raw_flag in _sequence(source_coverage["flags"])
                for flag in [_mapping(raw_flag)]
            ],
        },
        "skeptical_review": {
            "summary": skeptical_review["summary"],
            "counter_thesis": list(
                _sequence(skeptical_review["counter_thesis"])
            ),
        },
        "reports": {
            "stock_analysis": reports["stock_analysis"],
            "ui": reports["ui"],
        },
        "safety": {
            "passed": safety["passed"],
            "boundary": safety["boundary"],
            "findings": [
                {
                    "line_number": finding["line_number"],
                    "phrase": finding["phrase"],
                    "line": finding["line"],
                }
                for raw_finding in _sequence(safety["findings"])
                for finding in [_mapping(raw_finding)]
            ],
        },
        "key_claims": [
            {
                "claim_id": claim["claim_id"],
                "claim": claim["claim"],
                "provenance_refs": [
                    {
                        "evidence_id": ref["evidence_id"],
                        "source_url": ref["source_url"],
                        "source_title": ref["source_title"],
                        "excerpt": ref["excerpt"],
                    }
                    for raw_ref in _sequence(claim["provenance_refs"])
                    for ref in [_mapping(raw_ref)]
                ],
                "diagnostics": list(_sequence(claim["diagnostics"])),
            }
            for raw_claim in _sequence(manifest["key_claims"])
            for claim in [_mapping(raw_claim)]
        ],
    }


def _find_forbidden_key(value: object) -> str | None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if _is_forbidden_key(key):
                return key
            nested = _find_forbidden_key(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for item in value:
            nested = _find_forbidden_key(item)
            if nested is not None:
                return nested
    return None


def _is_forbidden_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    return any(forbidden in normalized for forbidden in FORBIDDEN_FIELDS)


def _require_mapping(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> Mapping[str, object]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        _invalid(reason)
    return value


def _require_list(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        _invalid(reason)
    return value


def _require_string(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        _invalid(reason)
    return value


def _require_non_empty_string(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> str:
    value = _require_string(mapping, key, reason)
    if not value.strip():
        _invalid(reason)
    return value


def _require_string_list(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> list[str]:
    value = _require_list(mapping, key, reason)
    if not all(isinstance(item, str) for item in value):
        _invalid(reason)
    return value


def _require_finite_number(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
    *,
    integer: bool,
) -> int | float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(reason)
    if integer and not isinstance(value, int):
        _invalid(reason)
    if not math.isfinite(float(value)) or value < 0:
        _invalid(reason)
    return value


def _require_integer(
    mapping: Mapping[str, object],
    key: str,
    reason: str,
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(reason)
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("validated artifact mapping expected")
    return value


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise TypeError("validated artifact sequence expected")
    return value


def _invalid(reason: str) -> None:
    raise ArtifactRepositoryError(422, "artifact_invalid", reason)


def _blocked(reason: str) -> None:
    raise ArtifactRepositoryError(409, "artifact_blocked", reason)
