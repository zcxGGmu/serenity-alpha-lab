from __future__ import annotations

from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.stock_universe import StockUniverseEntry
from serenity_alpha_lab.topic_resolver import resolve_topic


def item(
    item_id: str,
    tickers: list[str],
    themes: list[str],
    *,
    claim: str = "Claim",
    summary: str = "Summary",
    layer: str = "industry",
    strength: str = "derived",
    claim_type: str = "inference",
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        source_title=f"Source {item_id}",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim=claim,
        summary=summary,
        tickers=tickers,
        themes=themes,
        supply_chain_layer=layer,
        direction="positive",
        strength=strength,
        confidence=0.75,
        factor_impacts={"evidence_quality": 10},
        claim_type=claim_type,
    )


def test_resolve_topic_maps_chinese_industry_to_candidates_and_aliases():
    evidence = [
        item(
            "memory-sive",
            ["SIVE", "AAOI"],
            ["CPO", "AI infrastructure", "memory"],
            claim="AI infrastructure demand links optical bottlenecks and memory.",
        ),
        item(
            "memory-mu",
            ["MU", "SNDK"],
            ["memory", "storage", "HBM"],
            claim="Memory and storage cycle evidence mentions MU and SNDK.",
            strength="primary",
            claim_type="fact",
        ),
        item("unrelated", ["XOM"], ["energy"], claim="Energy evidence."),
    ]

    resolved = resolve_topic("存储芯片", evidence, fallback_tickers=["NVDA"])

    assert resolved.intent == "industry"
    assert resolved.canonical_theme == "memory"
    assert "memory" in resolved.expanded_query
    assert "hbm" in resolved.aliases
    assert resolved.candidate_tickers[:4] == ["MU", "SNDK", "SIVE", "AAOI"]
    assert "NVDA" not in resolved.candidate_tickers


def test_resolve_topic_recognizes_ticker_input_and_keeps_focus_first():
    evidence = [
        item("aaoi-primary", ["AAOI"], ["CPO", "primary-source"], strength="primary", claim_type="fact"),
        item("sive-peer", ["SIVE"], ["CPO"]),
    ]

    resolved = resolve_topic("AAOI", evidence, fallback_tickers=["SIVE", "NVDA"])

    assert resolved.intent == "ticker"
    assert resolved.canonical_theme == "AAOI"
    assert resolved.candidate_tickers[0] == "AAOI"
    assert resolved.expanded_query.startswith("AAOI")


def test_resolve_topic_falls_back_to_configured_candidates_when_evidence_is_sparse():
    resolved = resolve_topic("机器人", [], fallback_tickers=["NVDA", "TSLA"])

    assert resolved.intent == "theme"
    assert resolved.canonical_theme == "机器人"
    assert resolved.candidate_tickers == ["NVDA", "TSLA"]
    assert "机器人" in resolved.expanded_query


def test_resolve_topic_uses_stock_universe_when_evidence_has_no_candidates():
    universe = [
        StockUniverseEntry(
            ticker="MU",
            name="Micron Technology",
            market="US",
            sector="Semiconductors",
            themes=["memory", "HBM"],
            aliases=["存储芯片", "DRAM"],
        ),
        StockUniverseEntry(
            ticker="GIGADEVICE",
            name="兆易创新",
            market="CN",
            sector="Semiconductors",
            themes=["memory", "NOR flash"],
            aliases=["存储芯片", "兆易创新"],
        ),
    ]

    resolved = resolve_topic("存储芯片", [], fallback_tickers=["NVDA"], stock_universe=universe)

    assert resolved.candidate_tickers[:2] == ["MU", "GIGADEVICE"]
    assert "NVDA" not in resolved.candidate_tickers


def test_resolve_topic_keeps_universe_candidates_ahead_of_noisy_evidence_for_known_industry():
    noisy_evidence = [
        item(
            f"memory-noise-{index}",
            [ticker],
            ["memory", "AI infrastructure"],
            claim="AI infrastructure evidence mentions memory pressure.",
        )
        for index, ticker in enumerate(["SIVE", "LITE", "COHR", "AAOI", "AXTI", "NVDA", "IQE", "SOI"])
    ]
    universe = [
        StockUniverseEntry(
            ticker="MU",
            name="Micron Technology",
            market="US",
            sector="Semiconductors",
            themes=["memory", "HBM", "DRAM", "NAND"],
            aliases=["存储芯片", "DRAM"],
        ),
        StockUniverseEntry(
            ticker="GIGADEVICE",
            name="兆易创新",
            market="CN",
            sector="Semiconductors",
            themes=["memory", "NOR flash"],
            aliases=["存储芯片", "兆易创新"],
        ),
    ]

    resolved = resolve_topic(
        "存储芯片",
        noisy_evidence,
        fallback_tickers=["NVDA"],
        stock_universe=universe,
        max_candidates=4,
    )

    assert resolved.intent == "industry"
    assert resolved.candidate_tickers[:2] == ["MU", "GIGADEVICE"]


def test_resolve_topic_treats_hbm_as_known_industry_not_ticker_symbol():
    universe = [
        StockUniverseEntry(
            ticker="MU",
            name="Micron Technology",
            market="US",
            sector="Semiconductors",
            themes=["memory", "HBM", "DRAM"],
            aliases=["HBM", "DRAM"],
        )
    ]

    resolved = resolve_topic("HBM", [], fallback_tickers=["NVDA"], stock_universe=universe)

    assert resolved.intent == "industry"
    assert resolved.canonical_theme == "HBM"
    assert resolved.candidate_tickers[0] == "MU"
    assert "HBM" not in resolved.candidate_tickers
