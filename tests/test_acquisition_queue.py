from __future__ import annotations

from datetime import date

from serenity_alpha_lab.acquisition_queue import (
    build_acquisition_queue,
    render_acquisition_queue_markdown,
)
from serenity_alpha_lab.evidence import EvidenceItem


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


def test_build_acquisition_queue_maps_readiness_flags_to_tasks():
    evidence = [
        item("sec:NVDA:revenue", ["NVDA"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("github:SIVE:cpo", ["SIVE"]),
    ]

    queue = build_acquisition_queue(evidence, query="CPO", tickers=["NVDA", "SIVE"], limit=8)

    assert [task.ticker for task in queue.tasks] == ["NVDA", "SIVE", "SIVE"]
    assert queue.tasks[0].gap_code == "missing_risk_coverage"
    assert queue.tasks[0].priority == "medium"
    assert "risk" in queue.tasks[0].source_target.lower()
    assert "risk coverage" in queue.tasks[0].rationale.lower()
    assert "negative" in queue.tasks[0].acceptance_criteria.lower()
    assert "rerun" in queue.tasks[0].after_import.lower()
    assert queue.tasks[1].gap_code == "missing_primary_source"
    assert queue.tasks[1].priority == "high"
    assert "primary filing" in queue.tasks[1].source_target.lower()
    assert "primary" in queue.tasks[1].rationale.lower()
    assert "source excerpt" in queue.tasks[1].acceptance_criteria.lower()
    assert "quality gate" in queue.tasks[1].after_import.lower()


def test_render_acquisition_queue_markdown_lists_actionable_sources():
    evidence = [item("github:SIVE:cpo", ["SIVE"])]
    queue = build_acquisition_queue(evidence, query="CPO", tickers=["SIVE"], limit=8)

    markdown = render_acquisition_queue_markdown(queue)

    assert "# Evidence Acquisition Queue" in markdown
    assert "| Priority | Ticker | Gap | Source Target | Search Prompt | Why It Matters | Acceptance Criteria | After Import |" in markdown
    assert "missing_primary_source" in markdown
    assert "SIVE primary filing CPO" in markdown
    assert "Primary/fact evidence is required before this candidate can clear the research confidence gate." in markdown
    assert "Source title, URL, and source excerpt must directly support the task claim." in markdown
    assert "Import the evidence, rerun the analysis, and confirm the quality gate improves." in markdown


def test_render_acquisition_queue_markdown_localizes_chinese_report():
    evidence = [item("github:SIVE:cpo", ["SIVE"])]
    queue = build_acquisition_queue(evidence, query="CPO", tickers=["SIVE"], limit=8)

    markdown = render_acquisition_queue_markdown(queue, language="zh")

    assert "# 证据采集队列" in markdown
    assert "**研究问题:** CPO" in markdown
    assert "**每个标的检索上限:** 8" in markdown
    assert "| 优先级 | 股票代码 | 缺口 | 来源目标 | 搜索提示 | 补证原因 | 验收标准 | 导入后动作 |" in markdown
    assert "高" in markdown
    assert "缺少 primary/fact 来源" in markdown
    assert "Primary filing、公司公告、审计事实或官方投资者材料" in markdown
    assert "SIVE primary filing CPO" in markdown
    assert "需要 primary/fact 证据才能提升研究置信度门禁。" in markdown
    assert "来源标题、链接和原文摘录必须能直接支撑任务声明。" in markdown
    assert "导入证据后重新生成分析，并确认质量门禁改善。" in markdown
    assert "# Evidence Acquisition Queue" not in markdown
    assert "**Research question:**" not in markdown
