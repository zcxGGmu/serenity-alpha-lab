from __future__ import annotations

from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.readiness import (
    assess_batch_readiness,
    render_readiness_markdown,
)


def item(
    item_id: str,
    tickers: list[str],
    *,
    direction: str = "positive",
    strength: str = "derived",
    claim_type: str = "inference",
    themes: list[str] | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        source_title=f"Source {item_id}",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim=f"Claim {item_id}",
        summary=f"Summary {item_id}",
        tickers=tickers,
        themes=themes or ["CPO"],
        supply_chain_layer="optical components",
        direction=direction,
        strength=strength,
        confidence=0.75,
        factor_impacts={"evidence_quality": 10},
        claim_type=claim_type,
    )


def test_assess_batch_readiness_ranks_ready_candidates_first():
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
        item("github:AAOI:cpo", ["AAOI"]),
        item("github:LITE:cpo", ["LITE"]),
    ]

    report = assess_batch_readiness(evidence, query="CPO", tickers=["LITE", "AAOI"], limit=8)

    assert [candidate.ticker for candidate in report.candidates] == ["AAOI", "LITE"]
    assert report.candidates[0].status == "ready"
    assert report.candidates[1].status == "blocked"
    assert "missing_primary_source" in report.candidates[1].flag_codes


def test_render_readiness_markdown_includes_ranked_status_table():
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
    ]
    report = assess_batch_readiness(evidence, query="CPO", tickers=["AAOI"], limit=8)

    markdown = render_readiness_markdown(report)

    assert "# Batch Readiness Report" in markdown
    assert "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |" in markdown
    assert "| 1 | AAOI | ready | 2 | 1 | 1 | 0% | 0% | none |" in markdown
