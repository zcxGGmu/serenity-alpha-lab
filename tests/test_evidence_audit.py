from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.evidence_audit import audit_evidence, is_weak_summary, render_audit_markdown


def make_item(
    item_id,
    *,
    tickers=("SERENITY",),
    source_title="repo one",
    claim_type="inference",
    direction="positive",
    strength="derived",
    summary="A sufficiently descriptive evidence summary.",
    themes=("CPO",),
    source_excerpt="",
):
    return EvidenceItem(
        id=item_id,
        source_title=source_title,
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="Claim",
        summary=summary,
        tickers=tickers,
        themes=themes,
        supply_chain_layer="component",
        direction=direction,
        strength=strength,
        confidence=0.7,
        factor_impacts={"demand_certainty": 1},
        claim_type=claim_type,
        source_excerpt=source_excerpt,
    )


def test_audit_counts_distributions_and_flags_quality_issues():
    report = audit_evidence(
        [
            make_item("a", source_title="repo one", claim_type="methodology", strength="speculative", summary="short"),
            make_item("b", source_title="repo one", claim_type="methodology"),
            make_item("c", source_title="repo one", claim_type="risk", direction="negative"),
            make_item("d", source_title="repo two", tickers=("SIVE",), claim_type="catalyst"),
        ],
        focus_ticker="SIVE",
    )

    assert report.total_count == 4
    assert report.claim_type_counts["methodology"] == 2
    assert report.ticker_counts["SERENITY"] == 3
    assert report.source_counts["repo one"] == 3
    assert any(flag.code == "placeholder_ticker_concentration" for flag in report.flags)
    assert any(flag.code == "source_concentration" for flag in report.flags)
    assert any(flag.code == "short_summary" for flag in report.flags)


def test_render_audit_markdown_includes_next_fixes():
    report = audit_evidence(
        [make_item("a", claim_type="methodology"), make_item("b", claim_type="methodology")],
        focus_ticker="SIVE",
    )

    markdown = render_audit_markdown(report)

    assert "# Evidence Audit Report" in markdown
    assert "## Quality Flags" in markdown
    assert "## Next Fixes" in markdown
    assert "SIVE" in markdown


def test_audit_short_summary_heuristic_handles_chinese_and_placeholders():
    assert not is_weak_summary("基于 Serenity 推文提炼的产业链分析框架。")
    assert not is_weak_summary("股票投资风险极高，可能损失全部本金。此技能提供的是思维框架和分析方法。")
    assert is_weak_summary("```")
    assert is_weak_summary("English | 中文")


def test_audit_does_not_flag_meaningful_chinese_summary_as_short():
    report = audit_evidence(
        [
            make_item(
                "a",
                source_title="repo one",
                claim_type="risk",
                direction="negative",
                summary="股票投资风险极高，可能损失全部本金。此技能提供的是思维框架和分析方法。",
            ),
            make_item("b", source_title="repo two", tickers=("SIVE",), summary="Demand confirms ramp visibility."),
        ],
        focus_ticker="SIVE",
    )

    assert not any(flag.code == "short_summary" for flag in report.flags)


def test_audit_flags_manual_intake_without_source_excerpt():
    report = audit_evidence(
        [
            make_item(
                "manual:NVDA:risk:cpo-sourcing",
                tickers=("NVDA",),
                themes=("CPO", "risk", "manual-intake"),
                claim_type="risk",
                direction="negative",
            )
        ],
        focus_ticker="NVDA",
    )

    assert any(flag.code == "manual_intake_missing_source_excerpt" for flag in report.flags)


def test_audit_does_not_flag_manual_intake_with_source_excerpt():
    report = audit_evidence(
        [
            make_item(
                "manual:NVDA:risk:cpo-sourcing",
                tickers=("NVDA",),
                themes=("CPO", "risk", "manual-intake"),
                claim_type="risk",
                direction="negative",
                source_excerpt=(
                    "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk."
                ),
            )
        ],
        focus_ticker="NVDA",
    )

    assert not any(flag.code == "manual_intake_missing_source_excerpt" for flag in report.flags)
