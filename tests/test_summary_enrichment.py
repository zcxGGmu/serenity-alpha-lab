from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.summary_enrichment import build_enriched_summary, enrich_evidence_summaries


def make_item(
    item_id,
    *,
    claim="Install: ```",
    summary="```",
    tickers=("SERENITY",),
    themes=("Serenity",),
    claim_type="methodology",
):
    return EvidenceItem(
        id=item_id,
        source_title="repo README.md",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim=claim,
        summary=summary,
        tickers=tickers,
        themes=themes,
        supply_chain_layer="methodology",
        direction="neutral",
        strength="derived",
        confidence=0.6,
        factor_impacts={"evidence_quality": 1},
        claim_type=claim_type,
    )


def test_build_enriched_summary_uses_claim_context_tickers_and_themes():
    summary = build_enriched_summary(
        make_item(
            "a",
            claim="产业链卡脖子框架: 真正的价值在上游关键节点。",
            tickers=("SIVE", "AAOI"),
            themes=("CPO", "supply-chain bottleneck"),
        )
    )

    assert "产业链卡脖子框架" in summary
    assert "Tickers: SIVE, AAOI" in summary
    assert "Themes: CPO, supply-chain bottleneck" in summary


def test_enrich_evidence_summaries_replaces_weak_summary_and_marks_theme():
    item = make_item("a", claim="路径说明: 使用项目内 skills 目录安装 Serenity 技能。", summary="```")

    enriched = enrich_evidence_summaries([item])

    assert enriched[0].summary != "```"
    assert "路径说明" in enriched[0].summary
    assert "summary-enriched" in enriched[0].themes


def test_enrich_evidence_summaries_preserves_good_summary():
    item = make_item(
        "a",
        summary="股票投资风险极高，可能损失全部本金。此技能提供的是思维框架和分析方法。",
    )

    enriched = enrich_evidence_summaries([item])

    assert enriched[0] == item
