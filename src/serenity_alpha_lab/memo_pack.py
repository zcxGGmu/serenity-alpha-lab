from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .evidence import EvidenceItem
from .memo import generate_memo
from .readiness import ReadinessCandidate, assess_batch_readiness
from .retrieval import retrieve
from .scoring import score_research_question, summarize_scorecard


@dataclass(frozen=True)
class MemoPackMemo:
    ticker: str
    filename: str
    markdown: str
    candidate: ReadinessCandidate
    evidence: List[EvidenceItem]


@dataclass(frozen=True)
class MemoPack:
    query: str
    limit: int
    memos: List[MemoPackMemo]
    skipped: List[ReadinessCandidate]
    include_gap_memos: bool = False


@dataclass
class _EvidenceUsage:
    item: EvidenceItem
    memo_files: List[str]
    tickers: List[str]


def build_memo_pack(
    evidence: Iterable[EvidenceItem],
    *,
    query: str,
    tickers: Sequence[str],
    limit: int = 12,
    language: str = "en",
    include_gap_memos: bool = False,
) -> MemoPack:
    items = list(evidence)
    readiness = assess_batch_readiness(items, query=query, tickers=tickers, limit=limit)
    memos: List[MemoPackMemo] = []
    skipped: List[ReadinessCandidate] = []

    for candidate in readiness.candidates:
        if candidate.status != "ready" and not include_gap_memos:
            skipped.append(candidate)
            continue
        matched = retrieve(items, query=query, ticker=candidate.ticker, limit=limit)
        score = score_research_question(matched)
        filename = f"{candidate.ticker.lower()}-memo.md"
        memos.append(
            MemoPackMemo(
                ticker=candidate.ticker,
                filename=filename,
                markdown=generate_memo(
                    query=query,
                    ticker=candidate.ticker,
                    evidence=matched,
                    score=score,
                    language=language,
                ),
                candidate=candidate,
                evidence=matched,
            )
        )

    return MemoPack(query=query, limit=limit, memos=memos, skipped=skipped, include_gap_memos=include_gap_memos)


def write_memo_pack(pack: MemoPack, out_dir: Path | str) -> None:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _clean_generated_pack_files(output_dir)
    for memo in pack.memos:
        (output_dir / memo.filename).write_text(memo.markdown, encoding="utf-8")
    (output_dir / "index.md").write_text(render_memo_pack_index(pack), encoding="utf-8")
    (output_dir / "sources.md").write_text(render_memo_pack_sources(pack), encoding="utf-8")


def render_memo_pack_index(pack: MemoPack) -> str:
    lines = [
        "# Serenity Alpha Lab Memo Pack",
        "",
        f"**Research question:** {pack.query}",
        f"**Retrieval limit per ticker:** {pack.limit}",
        "",
        "| Ticker | Status | Serenity Rating | Confidence | Key Gaps | Memo File | Evidence | Primary/Fact | Risk | Flags |",
        "|---|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for memo in pack.memos:
        coverage = memo.candidate.report
        flags = ", ".join(memo.candidate.flag_codes) if memo.candidate.flag_codes else "none"
        scorecard = summarize_scorecard(score_research_question(memo.evidence))
        gaps = ", ".join(scorecard.gaps) if scorecard.gaps else "none"
        lines.append(
            f"| {memo.ticker} | {memo.candidate.status} | {scorecard.rating} | {scorecard.confidence} | {gaps} | "
            f"{memo.filename} | {coverage.focus_evidence_count} | "
            f"{coverage.primary_count} | {coverage.risk_count} | {flags} |"
        )
    for candidate in pack.skipped:
        coverage = candidate.report
        flags = ", ".join(candidate.flag_codes) if candidate.flag_codes else "none"
        lines.append(
            f"| {candidate.ticker} | {candidate.status} | not generated | not generated | {flags} | not generated | {coverage.focus_evidence_count} | "
            f"{coverage.primary_count} | {coverage.risk_count} | {flags} |"
        )

    lines.extend(["", "## Pack Policy", ""])
    if pack.include_gap_memos:
        lines.append("- UI-launched packs include gap reports for `needs_work` and `blocked` tickers so users can inspect why coverage is incomplete.")
        lines.append("- Treat non-ready reports as research diagnostics, not formal investment memos.")
    else:
        lines.append("- Formal memos are generated only for `ready` tickers.")
        lines.append("- `needs_work` and `blocked` tickers remain in the index with gap reasons.")
    return "\n".join(lines)


def render_memo_pack_sources(pack: MemoPack) -> str:
    lines = [
        "# Evidence Provenance Index",
        "",
        f"**Research question:** {pack.query}",
        f"**Retrieval limit per ticker:** {pack.limit}",
        "",
    ]

    if not pack.memos:
        lines.append("- No ready memo evidence was generated.")
        return "\n".join(lines)

    usages = _primary_evidence_usages(pack)
    lines.extend(["## Primary Evidence", ""])
    if not usages:
        lines.append("- No primary source evidence was used in ready memos.")
        return "\n".join(lines).rstrip() + "\n"

    for usage in usages:
        item = usage.item
        lines.append(
            f"- **{item.id}** [{item.source_title}]({item.source_url}) "
            f"({item.published_at.isoformat()}, {item.strength}, {item.claim_type})"
        )
        lines.append(f"  - **Tickers:** {', '.join(sorted(usage.tickers))}")
        lines.append(f"  - **Used in memos:** {', '.join(sorted(usage.memo_files))}")
        lines.append(f"  - **Claim:** {item.claim}")
        lines.append(f"  - **Summary:** {item.summary}")
        if item.source_excerpt.strip():
            lines.append(f"  - **Source excerpt:** {item.source_excerpt.strip()}")

    return "\n".join(lines).rstrip() + "\n"


def _is_primary_evidence(item: EvidenceItem) -> bool:
    return item.strength == "primary" or item.claim_type == "fact" or "primary-source" in item.themes


def _primary_evidence_usages(pack: MemoPack) -> List[_EvidenceUsage]:
    usages: dict[str, _EvidenceUsage] = {}
    for memo in pack.memos:
        for item in memo.evidence:
            if not _is_primary_evidence(item):
                continue
            usage = usages.get(item.id)
            if usage is None:
                usage = _EvidenceUsage(item=item, memo_files=[], tickers=[])
                usages[item.id] = usage
            _append_unique(usage.memo_files, memo.filename)
            for ticker in item.tickers:
                _append_unique(usage.tickers, ticker)
    return list(usages.values())


def _append_unique(values: List[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _clean_generated_pack_files(output_dir: Path) -> None:
    for path in output_dir.glob("*-memo.md"):
        if path.is_file():
            path.unlink()
    for filename in ["index.md", "sources.md"]:
        path = output_dir / filename
        if path.is_file():
            path.unlink()
