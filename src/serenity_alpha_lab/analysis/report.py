from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from serenity_alpha_lab.report_safety import ReportSafetyFinding, scan_report_text

from .pipeline import StockAnalysisResult


@dataclass(frozen=True)
class ProvenanceRef:
    evidence_id: str
    source_url: str
    source_title: str
    excerpt: str

    def to_dict(self) -> dict[str, str]:
        return {
            "evidence_id": self.evidence_id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class KeyClaim:
    claim_id: str
    claim: str
    provenance_refs: list[ProvenanceRef]
    diagnostics: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "claim": self.claim,
            "provenance_refs": [ref.to_dict() for ref in self.provenance_refs],
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class StockAnalysisReportArtifact:
    markdown_path: Path
    manifest_path: Path
    ui_path: Path
    key_claims: list[KeyClaim]
    safety_findings: list[ReportSafetyFinding]


class ReportSafetyViolation(ValueError):
    def __init__(self, findings: Sequence[ReportSafetyFinding]) -> None:
        super().__init__("generated stock-analysis report failed safety scan")
        self.findings = list(findings)


def render_stock_analysis_report_markdown(
    result: StockAnalysisResult,
    *,
    generated_at: datetime | None = None,
    additional_generated_sections: Mapping[str, str] | None = None,
) -> str:
    key_claims = build_key_claims(result)
    generated_at_value = _resolve_generated_at(generated_at)
    generated_at_label = generated_at_value.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Serenity Stock Analysis Report",
        "",
        f"**Symbol:** {result.symbol}",
        f"**Company:** {result.stock_name or 'n/a'}",
        f"**Market:** {result.market}",
        f"**Query:** {result.context.query}",
        f"**Generated:** {generated_at_label}",
        "**Report nature:** research only; not investment advice.",
        "",
        "## Intelligence Brief",
        "",
        f"- Research status: {result.status}.",
        f"- Readiness status: {result.readiness.status}.",
        f"- Research score: {result.signals.score}/100; rating {result.signals.rating}; confidence {result.signals.confidence}.",
        f"- Primary gaps: {_format_list(result.signals.gaps)}.",
        "",
        "## Data View",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Evidence count | {len(result.evidence)} |",
        f"| Provider status | {result.diagnostics.get('provider_status', 'unknown')} |",
        f"| Source coverage status | {result.readiness.status} |",
        f"| Focus ticker | {result.readiness.source_coverage.get('focus_ticker', result.symbol)} |",
        "",
        "## Research Readiness Guardrails",
        "",
        f"- Report gate: {result.report_gate.status} ({result.report_gate.reason}).",
        f"- Readiness flags: {_format_list(result.readiness.flag_codes)}.",
        "- Generated conclusions must stay tied to cited evidence and missing-source diagnostics.",
        "",
        "## Signal Attribution",
        "",
        "| Factor | Score | Evidence refs |",
        "|---|---:|---|",
    ]
    evidence_refs = ", ".join(result.signals.evidence_ids) if result.signals.evidence_ids else "missing-provenance"
    for factor, score in sorted(result.signals.factor_scores.items()):
        lines.append(f"| {factor.replace('_', ' ')} | {score} | {evidence_refs} |")

    lines.extend(
        [
            "",
            "## Historical Comparison",
            "",
            "| Evidence | Claim | Published | Direction |",
            "|---|---|---|---|",
        ]
    )
    for item in result.evidence[:6]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(str(item.get("id", "missing-provenance"))),
                    _escape_table(str(item.get("claim", ""))),
                    _escape_table(str(item.get("published_at", "n/a"))),
                    _escape_table(str(item.get("direction", "n/a"))),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Key Claims And Provenance", "", "| Claim ID | Claim | Provenance refs |", "|---|---|---|"])
    for claim in key_claims:
        refs = _format_provenance_refs(claim)
        lines.append(f"| {claim.claim_id} | {_escape_table(claim.claim)} | {refs} |")

    lines.extend(
        [
            "",
            "## Research Boundary",
            "",
            "This report adapts DSA-style report sections into Serenity evidence-first research. It summarizes data visibility, source coverage, readiness, signal attribution, and follow-up research gaps. It does not provide trade instructions, price objectives, portfolio allocation guidance, broker actions, or guaranteed outcomes.",
            "",
        ]
    )

    for title, body in (additional_generated_sections or {}).items():
        lines.extend([f"## {title}", "", body.strip(), ""])

    markdown = "\n".join(lines)
    safety = scan_report_text(markdown, path="stock-analysis-report.md")
    if not safety.passed:
        raise ReportSafetyViolation(safety.findings)
    return markdown


def write_stock_analysis_report_artifacts(
    result: StockAnalysisResult,
    output_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> StockAnalysisReportArtifact:
    root = Path(output_dir)
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = reports_dir / "stock-analysis-report.md"
    manifest_path = root / "analysis-report-manifest.json"
    ui_path = root / "index.html"
    generated_at_value = _resolve_generated_at(generated_at)
    markdown = render_stock_analysis_report_markdown(
        result,
        generated_at=generated_at_value,
    )
    key_claims = build_key_claims(result)
    safety = scan_report_text(markdown, path=markdown_path)
    if not safety.passed:
        raise ReportSafetyViolation(safety.findings)
    markdown_path.write_text(markdown, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "stock_analysis_report",
                "symbol": result.symbol,
                "stock_name": result.stock_name,
                "query": result.context.query,
                "generated_at": generated_at_value.isoformat(),
                "research_only": result.research_only,
                "readiness": {
                    "status": result.readiness.status,
                    "reason": result.report_gate.reason,
                    "flags": list(result.readiness.flag_codes),
                },
                "report_gate": result.report_gate.to_dict(),
                "source_coverage": build_source_coverage_summary(result),
                "skeptical_review": build_skeptical_review(result),
                "reports": {"stock_analysis": "reports/stock-analysis-report.md", "ui": "index.html"},
                "safety": {
                    "passed": safety.passed,
                    "boundary": "research only; not investment advice",
                    "findings": [
                        {
                            "line_number": finding.line_number,
                            "phrase": finding.phrase,
                            "line": finding.line,
                        }
                        for finding in safety.findings
                    ],
                },
                "key_claims": [claim.to_dict() for claim in key_claims],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ui_path.write_text(_render_report_ui(result, markdown_path.name), encoding="utf-8")
    return StockAnalysisReportArtifact(
        markdown_path=markdown_path,
        manifest_path=manifest_path,
        ui_path=ui_path,
        key_claims=key_claims,
        safety_findings=list(safety.findings),
    )


def _resolve_generated_at(generated_at: datetime | None) -> datetime:
    if generated_at is None:
        return datetime.now(timezone.utc)
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return generated_at.astimezone(timezone.utc)


def build_source_coverage_summary(result: StockAnalysisResult) -> dict[str, object]:
    coverage = result.readiness.source_coverage
    flags = []
    for raw_flag in coverage.get("flags", []):
        if not isinstance(raw_flag, Mapping):
            continue
        flags.append(
            {
                "code": str(raw_flag.get("code", "")),
                "severity": str(raw_flag.get("severity", "")),
                "message": str(raw_flag.get("message", "")),
                "recommendation": str(raw_flag.get("recommendation", "")),
            }
        )
    return {
        "status": result.readiness.status,
        "focus_ticker": str(coverage.get("focus_ticker") or result.symbol),
        "evidence_count": int(coverage.get("evidence_count", 0)),
        "focus_evidence_count": int(coverage.get("focus_evidence_count", 0)),
        "primary_count": int(coverage.get("primary_count", 0)),
        "risk_count": int(coverage.get("risk_count", 0)),
        "methodology_share": float(coverage.get("methodology_share", 0.0)),
        "placeholder_share": float(coverage.get("placeholder_share", 0.0)),
        "external_non_serenity_count": int(
            coverage.get("external_non_serenity_count", 0)
        ),
        "flags": flags,
    }


def build_skeptical_review(result: StockAnalysisResult) -> dict[str, object]:
    risk_items = [
        item
        for item in result.evidence
        if str(item.get("claim_type")) in {"risk", "invalidation"}
        or str(item.get("direction")) == "negative"
    ]
    if risk_items:
        return {
            "summary": (
                f"Risk coverage uses {len(risk_items)} risk or invalidation "
                "evidence item."
            ),
            "counter_thesis": [
                str(item.get("claim", "")).strip()
                for item in risk_items
                if str(item.get("claim", "")).strip()
            ],
        }
    missing_risk = next(
        (
            flag
            for flag in result.readiness.source_coverage.get("flags", [])
            if isinstance(flag, Mapping)
            and flag.get("code") == "missing_risk_coverage"
        ),
        None,
    )
    diagnostic = (
        "missing_risk_coverage: "
        + str(missing_risk.get("message", "")).strip()
        if isinstance(missing_risk, Mapping)
        else "missing_risk_coverage: No risk evidence is available."
    )
    return {
        "summary": (
            "Risk coverage is incomplete because no risk or invalidation "
            "evidence item is available."
        ),
        "counter_thesis": [diagnostic],
    }


def build_key_claims(result: StockAnalysisResult) -> list[KeyClaim]:
    evidence = list(result.evidence)
    quote_refs = _refs_for(evidence, preferred=lambda item: ":quote:" in str(item.get("id", "")))
    all_refs = _refs_for(evidence, preferred=lambda item: True)
    risk_refs = _refs_for(
        evidence,
        preferred=lambda item: str(item.get("claim_type")) in {"risk", "invalidation"} or str(item.get("direction")) == "negative",
    )
    return [
        KeyClaim(
            claim_id=f"claim:{result.symbol}:latest-normalized-quote",
            claim=_quote_claim(result),
            provenance_refs=quote_refs,
            diagnostics=[] if quote_refs else ["missing-provenance:quote"],
        ),
        KeyClaim(
            claim_id=f"claim:{result.symbol}:readiness",
            claim=f"Readiness is {result.readiness.status} with flags {_format_list(result.readiness.flag_codes)}.",
            provenance_refs=all_refs,
            diagnostics=[] if all_refs else ["missing-provenance:readiness"],
        ),
        KeyClaim(
            claim_id=f"claim:{result.symbol}:research-score",
            claim=f"Research score is {result.signals.score}/100 with {result.signals.confidence} confidence.",
            provenance_refs=all_refs,
            diagnostics=[] if all_refs else ["missing-provenance:research-score"],
        ),
        KeyClaim(
            claim_id=f"claim:{result.symbol}:risk-coverage",
            claim=f"Risk coverage uses {len(risk_refs)} risk or invalidation evidence item(s).",
            provenance_refs=risk_refs or all_refs,
            diagnostics=[] if risk_refs else ["missing-provenance:risk-coverage"],
        ),
    ]


def _quote_claim(result: StockAnalysisResult) -> str:
    quote = next((item for item in result.evidence if ":quote:" in str(item.get("id", ""))), None)
    if quote:
        return str(quote.get("claim", "Latest normalized quote is available."))
    return "Latest normalized quote is unavailable."


def _refs_for(evidence: Sequence[Mapping[str, object]], *, preferred) -> list[ProvenanceRef]:
    refs: list[ProvenanceRef] = []
    for item in evidence:
        if not preferred(item):
            continue
        evidence_id = str(item.get("id", "")).strip()
        source_url = str(item.get("source_url", "")).strip()
        if not evidence_id or not source_url:
            continue
        refs.append(
            ProvenanceRef(
                evidence_id=evidence_id,
                source_url=source_url,
                source_title=str(item.get("source_title", "")).strip(),
                excerpt=str(item.get("source_excerpt", "")).strip(),
            )
        )
    return refs


def _format_provenance_refs(claim: KeyClaim) -> str:
    if not claim.provenance_refs:
        return ", ".join(claim.diagnostics) or "missing-provenance"
    return "<br>".join(
        f"{_escape_table(ref.evidence_id)} ({_escape_table(ref.source_url)})" for ref in claim.provenance_refs[:4]
    )


def _format_list(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "none"


def _escape_table(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().replace("|", "\\|")


def _render_report_ui(result: StockAnalysisResult, report_filename: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            "  <title>Serenity Stock Analysis Report</title>",
            "</head>",
            "<body>",
            "  <main>",
            "    <h1>Serenity Stock Analysis Report</h1>",
            f"    <p><strong>Symbol:</strong> {result.symbol}</p>",
            f"    <p><strong>Research score:</strong> {result.signals.score}/100</p>",
            "    <p>This page is research only and is not investment advice.</p>",
            f'    <a data-report-href="reports/{report_filename}" href="reports/{report_filename}">Open Markdown report</a>',
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )
