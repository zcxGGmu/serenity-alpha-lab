from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .evidence import EvidenceItem
from .retrieval import retrieve
from .source_coverage import SourceCoverageReport, assess_source_coverage


@dataclass(frozen=True)
class ReadinessCandidate:
    ticker: str
    status: str
    report: SourceCoverageReport

    @property
    def flag_codes(self) -> List[str]:
        return [flag.code for flag in self.report.flags]


@dataclass(frozen=True)
class BatchReadinessReport:
    query: str
    limit: int
    candidates: List[ReadinessCandidate]


def assess_batch_readiness(
    evidence: Iterable[EvidenceItem],
    *,
    query: str,
    tickers: Sequence[str],
    limit: int = 12,
) -> BatchReadinessReport:
    items = list(evidence)
    candidates = [
        _assess_candidate(items, query=query, ticker=ticker, limit=limit)
        for ticker in _normalize_tickers(tickers)
    ]
    candidates.sort(key=_candidate_sort_key)
    return BatchReadinessReport(query=query, limit=limit, candidates=candidates)


def render_readiness_markdown(report: BatchReadinessReport) -> str:
    lines = [
        "# Batch Readiness Report",
        "",
        f"**Research question:** {report.query}",
        f"**Retrieval limit per ticker:** {report.limit}",
        "",
        "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for rank, candidate in enumerate(report.candidates, start=1):
        coverage = candidate.report
        flags = ", ".join(candidate.flag_codes) if candidate.flag_codes else "none"
        lines.append(
            f"| {rank} | {candidate.ticker} | {candidate.status} | {coverage.evidence_count} | "
            f"{coverage.primary_count} | {coverage.risk_count} | {coverage.methodology_share:.0%} | "
            f"{coverage.placeholder_share:.0%} | {flags} |"
        )
    lines.extend(["", "## Next Actions", ""])
    for candidate in report.candidates:
        if candidate.status == "ready":
            lines.append(f"- {candidate.ticker}: ready for formal memo generation.")
        elif candidate.status == "needs_work":
            lines.append(f"- {candidate.ticker}: address warning flags before raising conviction.")
        else:
            lines.append(f"- {candidate.ticker}: blocked until critical coverage gaps are filled.")
    return "\n".join(lines)


def _assess_candidate(
    evidence: Sequence[EvidenceItem],
    *,
    query: str,
    ticker: str,
    limit: int,
) -> ReadinessCandidate:
    matched = retrieve(evidence, query=query, ticker=ticker, limit=limit)
    report = assess_source_coverage(matched, focus_ticker=ticker)
    return ReadinessCandidate(ticker=ticker, status=_status_for_report(report), report=report)


def _status_for_report(report: SourceCoverageReport) -> str:
    if any(flag.severity == "critical" for flag in report.flags):
        return "blocked"
    if report.flags:
        return "needs_work"
    return "ready"


def _candidate_sort_key(candidate: ReadinessCandidate) -> tuple[int, int, int, int, str]:
    status_rank = {"ready": 0, "needs_work": 1, "blocked": 2}[candidate.status]
    coverage = candidate.report
    return (
        status_rank,
        -coverage.primary_count,
        -coverage.risk_count,
        -coverage.evidence_count,
        candidate.ticker,
    )


def _normalize_tickers(tickers: Sequence[str]) -> List[str]:
    return [ticker.upper().lstrip("$") for ticker in tickers]
