from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Sequence

from .evidence import EvidenceItem


@dataclass(frozen=True)
class AuditFlag:
    code: str
    severity: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class EvidenceAuditReport:
    total_count: int
    focus_ticker: str | None
    claim_type_counts: Mapping[str, int]
    direction_counts: Mapping[str, int]
    strength_counts: Mapping[str, int]
    ticker_counts: Mapping[str, int]
    theme_counts: Mapping[str, int]
    source_counts: Mapping[str, int]
    flags: Sequence[AuditFlag]


def audit_evidence(items: Iterable[EvidenceItem], focus_ticker: str | None = None) -> EvidenceAuditReport:
    evidence = list(items)
    total_count = len(evidence)
    normalized_focus = focus_ticker.upper().lstrip("$") if focus_ticker else None

    claim_type_counts = _sorted_counts(item.claim_type for item in evidence)
    direction_counts = _sorted_counts(item.direction for item in evidence)
    strength_counts = _sorted_counts(item.strength for item in evidence)
    ticker_counts = _sorted_counts(ticker for item in evidence for ticker in item.tickers)
    theme_counts = _sorted_counts(theme for item in evidence for theme in item.themes)
    source_counts = _sorted_counts(item.source_title for item in evidence)

    flags = _quality_flags(
        evidence=evidence,
        total_count=total_count,
        focus_ticker=normalized_focus,
        claim_type_counts=claim_type_counts,
        strength_counts=strength_counts,
        ticker_counts=ticker_counts,
        source_counts=source_counts,
    )

    return EvidenceAuditReport(
        total_count=total_count,
        focus_ticker=normalized_focus,
        claim_type_counts=claim_type_counts,
        direction_counts=direction_counts,
        strength_counts=strength_counts,
        ticker_counts=ticker_counts,
        theme_counts=theme_counts,
        source_counts=source_counts,
        flags=flags,
    )


def render_audit_markdown(report: EvidenceAuditReport) -> str:
    lines = [
        "# Evidence Audit Report",
        "",
        "## Corpus Summary",
        "",
        f"- Total evidence items: {report.total_count}",
        f"- Focus ticker: {report.focus_ticker or 'None'}",
        "",
    ]

    lines.extend(_render_count_section("Claim Types", report.claim_type_counts))
    lines.extend(_render_count_section("Directions", report.direction_counts))
    lines.extend(_render_count_section("Strengths", report.strength_counts))
    lines.extend(_render_count_section("Top Tickers", report.ticker_counts))
    lines.extend(_render_count_section("Top Themes", report.theme_counts))
    lines.extend(_render_count_section("Top Sources", report.source_counts))

    lines.extend(["## Quality Flags", ""])
    if report.flags:
        for flag in report.flags:
            lines.append(f"- **{flag.severity.upper()} / {flag.code}:** {flag.message}")
    else:
        lines.append("- No major corpus quality flags detected.")

    lines.extend(["", "## Next Fixes", ""])
    if report.flags:
        seen_recommendations = []
        for flag in report.flags:
            if flag.recommendation in seen_recommendations:
                continue
            seen_recommendations.append(flag.recommendation)
            lines.append(f"- {flag.recommendation}")
    else:
        lines.append("- Proceed to primary-source connectors and ticker-specific retrieval enrichment.")

    lines.append("")
    return "\n".join(lines)


def _quality_flags(
    *,
    evidence: Sequence[EvidenceItem],
    total_count: int,
    focus_ticker: str | None,
    claim_type_counts: Mapping[str, int],
    strength_counts: Mapping[str, int],
    ticker_counts: Mapping[str, int],
    source_counts: Mapping[str, int],
) -> list[AuditFlag]:
    if total_count == 0:
        return [
            AuditFlag(
                code="empty_corpus",
                severity="critical",
                message="No evidence items were provided.",
                recommendation="Import or seed evidence before generating research memos.",
            )
        ]

    flags: list[AuditFlag] = []
    placeholder_count = ticker_counts.get("SERENITY", 0)
    if placeholder_count / total_count >= 0.4:
        flags.append(
            AuditFlag(
                code="placeholder_ticker_concentration",
                severity="warning",
                message=f"{placeholder_count}/{total_count} items use the SERENITY placeholder ticker.",
                recommendation="Map reusable Serenity methodology evidence to concrete tickers only after a source supports the linkage.",
            )
        )

    methodology_count = claim_type_counts.get("methodology", 0)
    if methodology_count / total_count >= 0.4:
        flags.append(
            AuditFlag(
                code="methodology_concentration",
                severity="warning",
                message=f"{methodology_count}/{total_count} items are methodology claims.",
                recommendation="Add more company, product, customer, and supply-chain facts before relying on score outputs.",
            )
        )

    speculative_count = strength_counts.get("speculative", 0)
    if speculative_count / total_count >= 0.35:
        flags.append(
            AuditFlag(
                code="speculative_concentration",
                severity="warning",
                message=f"{speculative_count}/{total_count} items are speculative evidence.",
                recommendation="Prioritize primary and derived evidence from filings, transcripts, technical papers, and original repo docs.",
            )
        )

    if focus_ticker and ticker_counts.get(focus_ticker, 0) == 0:
        flags.append(
            AuditFlag(
                code="missing_focus_ticker",
                severity="critical",
                message=f"No evidence item directly references focus ticker {focus_ticker}.",
                recommendation=f"Import or curate direct {focus_ticker} evidence before producing a ticker memo.",
            )
        )

    top_source, top_source_count = _top_count(source_counts)
    if top_source and top_source_count / total_count >= 0.6:
        flags.append(
            AuditFlag(
                code="source_concentration",
                severity="warning",
                message=f"{top_source_count}/{total_count} items come from one source: {top_source}.",
                recommendation="Broaden source coverage so one repository cannot dominate the research conclusion.",
            )
        )

    short_count = sum(1 for item in evidence if is_weak_summary(item.summary))
    if short_count:
        flags.append(
            AuditFlag(
                code="short_summary",
                severity="info",
                message=f"{short_count}/{total_count} items have very short summaries.",
                recommendation="Expand short summaries into concrete, decision-useful evidence statements.",
            )
        )

    missing_trace_count = sum(1 for item in evidence if _is_manual_intake(item) and not item.source_excerpt.strip())
    if missing_trace_count:
        flags.append(
            AuditFlag(
                code="manual_intake_missing_source_excerpt",
                severity="warning",
                message=f"{missing_trace_count}/{total_count} manual intake items lack a source excerpt.",
                recommendation=(
                    "Add source excerpts to manually ingested evidence so each claim can be traced to the cited source."
                ),
            )
        )

    negative_count = sum(1 for item in evidence if item.direction == "negative")
    if negative_count == 0:
        flags.append(
            AuditFlag(
                code="missing_downside_coverage",
                severity="warning",
                message="The corpus has no negative evidence items.",
                recommendation="Add explicit risk and invalidation evidence before trusting a bullish synthesis.",
            )
        )

    return flags


def _is_manual_intake(item: EvidenceItem) -> bool:
    return item.id.startswith("manual:") or any(theme.lower() == "manual-intake" for theme in item.themes)


def is_weak_summary(summary: str) -> bool:
    cleaned = _clean_summary(summary)
    if not cleaned:
        return True
    lowered = cleaned.lower()
    placeholder_values = {"```", "—", "-", "n/a", "none", "english | 中文"}
    if lowered in placeholder_values:
        return True
    if cleaned.startswith("```") or cleaned.endswith("```"):
        return True

    latin_word_count = len(re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", cleaned))
    cjk_char_count = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
    if cjk_char_count >= 12:
        return False
    if latin_word_count >= 5:
        return False
    return len(cleaned) < 32


def _sorted_counts(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(values)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_count(counts: Mapping[str, int]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    key = next(iter(counts))
    return key, counts[key]


def _render_count_section(title: str, counts: Mapping[str, int], limit: int = 8) -> list[str]:
    lines = [f"## {title}", ""]
    if not counts:
        lines.append("- None")
    else:
        for key, count in list(counts.items())[:limit]:
            lines.append(f"- {key}: {count}")
    lines.append("")
    return lines


def _clean_summary(summary: str) -> str:
    return re.sub(r"\s+", " ", summary).strip()
