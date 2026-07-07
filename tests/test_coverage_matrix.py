from __future__ import annotations

from datetime import date

from serenity_alpha_lab.coverage_matrix import build_coverage_matrix, render_coverage_matrix_markdown
from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.stock_universe import StockUniverseEntry


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
        themes=themes or ["memory"],
        supply_chain_layer="semiconductors",
        direction=direction,
        strength=strength,
        confidence=0.75,
        factor_impacts={"evidence_quality": 10},
        claim_type=claim_type,
    )


def entry(
    ticker: str,
    name: str,
    *,
    market: str = "US",
    themes: list[str] | None = None,
    aliases: list[str] | None = None,
) -> StockUniverseEntry:
    return StockUniverseEntry(
        ticker=ticker,
        name=name,
        market=market,
        sector="Semiconductors",
        themes=themes or ["memory", "HBM"],
        aliases=aliases or ["存储芯片", "HBM"],
    )


def test_build_coverage_matrix_ranks_theme_universe_gaps():
    universe = [
        entry("AAOI", "Applied Optoelectronics", themes=["CPO"], aliases=["CPO"]),
        entry("MU", "Micron Technology"),
        entry("GIGADEVICE", "兆易创新", market="CN", themes=["memory", "NOR flash"], aliases=["存储芯片", "NOR"]),
    ]
    evidence = [
        item("github:MU:hbm", ["MU"], themes=["memory", "HBM"]),
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source", "CPO"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk", themes=["CPO"]),
    ]

    matrix = build_coverage_matrix(evidence, universe=universe, query="存储芯片")

    assert [row.ticker for row in matrix.rows] == ["GIGADEVICE", "MU"]
    assert matrix.rows[0].priority == "high"
    assert matrix.rows[0].evidence_count == 0
    assert matrix.rows[0].gaps == ["missing_focus_ticker", "missing_primary_source", "missing_risk_coverage"]
    assert "GIGADEVICE primary filing 存储芯片" in matrix.rows[0].search_prompt
    assert matrix.rows[1].priority == "high"
    assert matrix.rows[1].evidence_count == 1
    assert matrix.rows[1].primary_count == 0
    assert matrix.rows[1].risk_count == 0
    assert matrix.rows[1].matched_themes == ["memory", "HBM"]
    assert matrix.rows[1].gaps == ["missing_primary_source", "missing_risk_coverage"]


def test_render_coverage_matrix_markdown_lists_next_source_targets():
    universe = [
        entry("MU", "Micron Technology"),
        entry("GIGADEVICE", "兆易创新", market="CN", themes=["memory", "NOR flash"], aliases=["存储芯片", "NOR"]),
    ]
    matrix = build_coverage_matrix([item("github:MU:hbm", ["MU"])], universe=universe, query="存储芯片")

    markdown = render_coverage_matrix_markdown(matrix)

    assert "# Universe Coverage Matrix" in markdown
    assert "**Query:** 存储芯片" in markdown
    assert "| Priority | Ticker | Name | Market | Themes | Evidence | Primary/Fact | Risk | Gaps | Next Source Target | Search Prompt |" in markdown
    assert "| high | GIGADEVICE | 兆易创新 | CN | memory, NOR flash | 0 | 0 | 0 | missing_focus_ticker, missing_primary_source, missing_risk_coverage | primary filing or official report | GIGADEVICE primary filing 存储芯片 |" in markdown
    assert "| high | MU | Micron Technology | US | memory, HBM | 1 | 0 | 0 | missing_primary_source, missing_risk_coverage | primary filing or official report | MU primary filing 存储芯片 |" in markdown


def test_render_coverage_matrix_markdown_localizes_chinese_report():
    universe = [
        entry("MU", "Micron Technology"),
        entry("GIGADEVICE", "兆易创新", market="CN", themes=["memory", "NOR flash"], aliases=["存储芯片", "NOR"]),
    ]
    matrix = build_coverage_matrix([item("github:MU:hbm", ["MU"])], universe=universe, query="存储芯片")

    markdown = render_coverage_matrix_markdown(matrix, language="zh")

    assert "# 股票池覆盖矩阵" in markdown
    assert "**查询:** 存储芯片" in markdown
    assert "| 优先级 | 股票代码 | 名称 | 市场 | 主题 | 证据 | Primary/Fact | 风险 | 缺口 | 下一步来源目标 | 搜索提示 |" in markdown
    assert "高" in markdown
    assert "缺少直接标的证据, 缺少 primary/fact 来源, 缺少风险证据" in markdown
    assert "primary filing 或官方报告" in markdown
    assert "primary filing 存储芯片" in markdown
    assert "# Universe Coverage Matrix" not in markdown
    assert "**Query:**" not in markdown
