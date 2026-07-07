from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .evidence import EvidenceItem


@dataclass(frozen=True)
class CoverageFlag:
    code: str
    severity: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class SourceCoverageReport:
    focus_ticker: str | None
    evidence_count: int
    focus_evidence_count: int
    primary_count: int
    risk_count: int
    methodology_share: float
    placeholder_share: float
    external_non_serenity_count: int
    flags: List[CoverageFlag]


def assess_source_coverage(
    evidence: Iterable[EvidenceItem],
    focus_ticker: str | None = None,
    *,
    methodology_threshold: float = 0.60,
    placeholder_threshold: float = 0.60,
) -> SourceCoverageReport:
    items = list(evidence)
    normalized_focus = focus_ticker.upper().lstrip("$") if focus_ticker else None
    evidence_count = len(items)
    focus_items = [item for item in items if not normalized_focus or normalized_focus in item.tickers]
    focus_evidence_count = len(focus_items)
    primary_count = sum(1 for item in focus_items if _is_primary_source(item))
    risk_count = sum(1 for item in focus_items if _is_risk_evidence(item))
    methodology_count = sum(1 for item in items if item.claim_type == "methodology")
    placeholder_count = sum(1 for item in items if "SERENITY" in item.tickers)
    external_non_serenity_count = sum(1 for item in items if "SERENITY" not in item.tickers and _is_external_source(item))
    methodology_share = methodology_count / evidence_count if evidence_count else 0.0
    placeholder_share = placeholder_count / evidence_count if evidence_count else 0.0

    flags: List[CoverageFlag] = []
    if normalized_focus and focus_evidence_count == 0:
        flags.append(
            CoverageFlag(
                code="missing_focus_ticker",
                severity="critical",
                message=f"No retrieved evidence directly references {normalized_focus}.",
                recommendation="Add direct ticker evidence before advancing a ticker-focused memo.",
            )
        )
    if normalized_focus and primary_count == 0:
        flags.append(
            CoverageFlag(
                code="missing_primary_source",
                severity="critical",
                message=f"No primary-source or fact evidence was retrieved for {normalized_focus}.",
                recommendation="Add at least one primary filing, company release, or audited fact for the focus ticker.",
            )
        )
    if normalized_focus and risk_count == 0:
        flags.append(
            CoverageFlag(
                code="missing_risk_coverage",
                severity="warning",
                message=f"No negative, risk, or invalidation evidence was retrieved for {normalized_focus}.",
                recommendation="Add direct downside evidence before treating the thesis as balanced.",
            )
        )
    if evidence_count and methodology_share > methodology_threshold:
        flags.append(
            CoverageFlag(
                code="methodology_concentration",
                severity="warning",
                message=f"Methodology evidence is {methodology_share:.0%} of retrieved evidence.",
                recommendation="Increase company-specific and external source coverage before relying on the memo.",
            )
        )
    if evidence_count and placeholder_share > placeholder_threshold:
        flags.append(
            CoverageFlag(
                code="placeholder_concentration",
                severity="warning",
                message=f"Placeholder SERENITY evidence is {placeholder_share:.0%} of retrieved evidence.",
                recommendation="Resolve or replace placeholder evidence with concrete ticker-specific sources.",
            )
        )

    return SourceCoverageReport(
        focus_ticker=normalized_focus,
        evidence_count=evidence_count,
        focus_evidence_count=focus_evidence_count,
        primary_count=primary_count,
        risk_count=risk_count,
        methodology_share=methodology_share,
        placeholder_share=placeholder_share,
        external_non_serenity_count=external_non_serenity_count,
        flags=flags,
    )


def render_source_coverage_markdown(report: SourceCoverageReport) -> str:
    focus = report.focus_ticker or "not specified"
    lines = [
        f"**Focus ticker:** {focus}",
        (
            f"**Coverage counts:** evidence {report.evidence_count}, focus ticker {report.focus_evidence_count}, "
            f"primary/fact {report.primary_count}, risk {report.risk_count}, "
            f"external non-Serenity {report.external_non_serenity_count}"
        ),
        (
            f"**Concentration:** methodology {report.methodology_share:.0%}, "
            f"SERENITY placeholder {report.placeholder_share:.0%}"
        ),
    ]
    if not report.flags:
        lines.append("**Gate result:** No critical coverage flags.")
        return "\n\n".join(lines)

    lines.append("**Coverage flags:**")
    for flag in report.flags:
        lines.append(f"- `{flag.code}` ({flag.severity}): {flag.message} Recommendation: {flag.recommendation}")
    return "\n\n".join(lines)


def _is_primary_source(item: EvidenceItem) -> bool:
    return item.strength == "primary" or item.claim_type == "fact" or "primary-source" in item.themes


def _is_risk_evidence(item: EvidenceItem) -> bool:
    return item.direction == "negative" or item.claim_type in {"risk", "invalidation"}


def _is_external_source(item: EvidenceItem) -> bool:
    text = " ".join([item.id, item.source_title, item.source_url]).lower()
    return "github:" not in item.id.lower() and "serenity" not in text
