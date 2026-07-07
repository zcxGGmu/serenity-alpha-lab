from __future__ import annotations

from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.source_coverage import assess_source_coverage, render_source_coverage_markdown


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


def flag_codes(report):
    return {flag.code for flag in report.flags}


def test_assess_source_coverage_flags_missing_primary_source_for_focus_ticker():
    report = assess_source_coverage(
        [item("github:aaoi:cpo", ["AAOI"])],
        focus_ticker="AAOI",
    )

    assert "missing_primary_source" in flag_codes(report)
    assert report.primary_count == 0


def test_assess_source_coverage_flags_missing_risk_coverage():
    report = assess_source_coverage(
        [
            item(
                "sec-companyfacts:AAOI:revenue",
                ["AAOI"],
                strength="primary",
                claim_type="fact",
                themes=["primary-source", "revenue"],
            )
        ],
        focus_ticker="AAOI",
    )

    assert "missing_risk_coverage" in flag_codes(report)
    assert report.risk_count == 0


def test_assess_source_coverage_flags_methodology_concentration():
    report = assess_source_coverage(
        [
            item("github:method:1", ["SERENITY"], claim_type="methodology", themes=["Serenity"]),
            item("github:method:2", ["SERENITY"], claim_type="methodology", themes=["Serenity"]),
            item("github:method:3", ["AAOI"], claim_type="methodology", themes=["Serenity"]),
            item(
                "sec-companyfacts:AAOI:revenue",
                ["AAOI"],
                strength="primary",
                claim_type="fact",
                themes=["primary-source", "revenue"],
            ),
            item("risk:aaoi", ["AAOI"], direction="negative", claim_type="risk"),
        ],
        focus_ticker="AAOI",
        methodology_threshold=0.50,
    )

    assert "methodology_concentration" in flag_codes(report)
    assert report.methodology_share > 0.50


def test_assess_source_coverage_flags_placeholder_concentration():
    report = assess_source_coverage(
        [
            item("github:serenity:1", ["SERENITY"], claim_type="methodology"),
            item("github:serenity:2", ["SERENITY"], claim_type="inference"),
            item(
                "sec-companyfacts:AAOI:revenue",
                ["AAOI"],
                strength="primary",
                claim_type="fact",
                themes=["primary-source", "revenue"],
            ),
            item("risk:aaoi", ["AAOI"], direction="negative", claim_type="risk"),
        ],
        focus_ticker="AAOI",
        placeholder_threshold=0.40,
    )

    assert "placeholder_concentration" in flag_codes(report)
    assert report.placeholder_share > 0.40


def test_assess_source_coverage_good_focus_set_has_no_critical_flags():
    report = assess_source_coverage(
        [
            item(
                "sec-companyfacts:AAOI:revenue",
                ["AAOI"],
                strength="primary",
                claim_type="fact",
                themes=["primary-source", "revenue"],
            ),
            item("risk:aaoi", ["AAOI"], direction="negative", claim_type="risk"),
            item("github:aaoi:cpo", ["AAOI"], claim_type="inference"),
        ],
        focus_ticker="AAOI",
    )

    assert not [flag for flag in report.flags if flag.severity == "critical"]
    assert report.primary_count == 1
    assert report.risk_count == 1


def test_render_source_coverage_markdown_includes_counts_and_recommendations():
    report = assess_source_coverage([item("github:aaoi:cpo", ["AAOI"])], focus_ticker="AAOI")

    markdown = render_source_coverage_markdown(report)

    assert "**Focus ticker:** AAOI" in markdown
    assert "missing_primary_source" in markdown
    assert "Add at least one primary filing" in markdown
