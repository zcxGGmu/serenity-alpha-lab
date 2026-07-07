from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .evidence import EvidenceItem
from .readiness import assess_batch_readiness


@dataclass(frozen=True)
class AcquisitionTask:
    ticker: str
    gap_code: str
    priority: str
    source_target: str
    search_prompt: str
    rationale: str
    acceptance_criteria: str
    after_import: str


@dataclass(frozen=True)
class AcquisitionQueue:
    query: str
    limit: int
    tasks: List[AcquisitionTask]


def build_acquisition_queue(
    evidence: Iterable[EvidenceItem],
    *,
    query: str,
    tickers: Sequence[str],
    limit: int = 12,
) -> AcquisitionQueue:
    readiness = assess_batch_readiness(evidence, query=query, tickers=tickers, limit=limit)
    tasks: List[AcquisitionTask] = []
    for candidate in readiness.candidates:
        if candidate.status == "ready":
            continue
        for gap_code in candidate.flag_codes:
            task = _task_for_gap(ticker=candidate.ticker, query=query, gap_code=gap_code)
            if task:
                tasks.append(task)
    return AcquisitionQueue(query=query, limit=limit, tasks=tasks)


def render_acquisition_queue_markdown(queue: AcquisitionQueue, *, language: str = "en") -> str:
    if language == "zh":
        lines = [
            "# 证据采集队列",
            "",
            f"**研究问题:** {queue.query}",
            f"**每个标的检索上限:** {queue.limit}",
            "",
            "| 优先级 | 股票代码 | 缺口 | 来源目标 | 搜索提示 | 补证原因 | 验收标准 | 导入后动作 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    else:
        lines = [
            "# Evidence Acquisition Queue",
            "",
            f"**Research question:** {queue.query}",
            f"**Retrieval limit per ticker:** {queue.limit}",
            "",
            "| Priority | Ticker | Gap | Source Target | Search Prompt | Why It Matters | Acceptance Criteria | After Import |",
            "|---|---|---|---|---|---|---|---|",
        ]
    if not queue.tasks:
        if language == "zh":
            lines.append("| 无 | none | 无 | 未发现需要补采的证据缺口。 | none | 无 | 无 | 无 |")
        else:
            lines.append("| none | none | none | No acquisition gaps found. | none | none | none | none |")
        return "\n".join(lines)

    for task in queue.tasks:
        lines.append(
            f"| {_localize_priority(task.priority, language)} | {task.ticker} | {_localize_gap(task.gap_code, language)} | "
            f"{_localize_source_target(task.source_target, language)} | {task.search_prompt} | "
            f"{_localize_playbook_text(task.rationale, language)} | "
            f"{_localize_playbook_text(task.acceptance_criteria, language)} | "
            f"{_localize_playbook_text(task.after_import, language)} |"
        )
    return "\n".join(lines)


def _task_for_gap(ticker: str, query: str, gap_code: str) -> AcquisitionTask | None:
    compact_query = " ".join(query.split())
    first_query_term = compact_query.split()[0] if compact_query else "evidence"
    if gap_code == "missing_primary_source":
        return AcquisitionTask(
            ticker=ticker,
            gap_code=gap_code,
            priority="high",
            source_target="Primary filing, company release, audited fact, or official investor material",
            search_prompt=f"{ticker} primary filing {first_query_term}",
            rationale="Primary/fact evidence is required before this candidate can clear the research confidence gate.",
            acceptance_criteria="Source title, URL, and source excerpt must directly support the task claim.",
            after_import="Import the evidence, rerun the analysis, and confirm the quality gate improves.",
        )
    if gap_code == "missing_risk_coverage":
        return AcquisitionTask(
            ticker=ticker,
            gap_code=gap_code,
            priority="medium",
            source_target="Risk, negative, or invalidation evidence from filings, earnings calls, or credible third-party sources",
            search_prompt=f"{ticker} risk {compact_query}",
            rationale="Risk coverage is required to avoid a one-sided thesis before promotion.",
            acceptance_criteria="Evidence should include a negative, downside, or invalidation claim tied to the ticker.",
            after_import="Import the evidence, rerun the analysis, and confirm the quality gate improves.",
        )
    if gap_code == "methodology_concentration":
        return AcquisitionTask(
            ticker=ticker,
            gap_code=gap_code,
            priority="medium",
            source_target="Company-specific non-methodology evidence that supports or challenges the thesis",
            search_prompt=f"{ticker} company evidence {compact_query}",
            rationale="Company-specific evidence is required to reduce reliance on methodology-only records.",
            acceptance_criteria="Evidence should support or challenge the ticker-specific thesis with a traceable source excerpt.",
            after_import="Import the evidence, rerun the analysis, and confirm the quality gate improves.",
        )
    if gap_code == "placeholder_concentration":
        return AcquisitionTask(
            ticker=ticker,
            gap_code=gap_code,
            priority="medium",
            source_target="Resolved ticker-specific evidence replacing SERENITY placeholder records",
            search_prompt=f"{ticker} source evidence {compact_query}",
            rationale="Ticker-specific evidence is required to replace SERENITY placeholder records.",
            acceptance_criteria="Evidence should name the ticker and include a traceable source excerpt.",
            after_import="Import the evidence, rerun the analysis, and confirm the quality gate improves.",
        )
    return None


def _localize_priority(priority: str, language: str) -> str:
    if language != "zh":
        return priority
    return {"high": "高", "medium": "中", "low": "低"}.get(priority, priority)


def _localize_gap(gap_code: str, language: str) -> str:
    if language != "zh":
        return gap_code
    return {
        "missing_primary_source": "缺少 primary/fact 来源",
        "missing_risk_coverage": "缺少风险证据",
        "methodology_concentration": "方法论证据过度集中",
        "placeholder_concentration": "SERENITY 占位证据过度集中",
    }.get(gap_code, gap_code)


def _localize_source_target(source_target: str, language: str) -> str:
    if language != "zh":
        return source_target
    return {
        "Primary filing, company release, audited fact, or official investor material": "Primary filing、公司公告、审计事实或官方投资者材料",
        "Risk, negative, or invalidation evidence from filings, earnings calls, or credible third-party sources": "来自 filings、业绩会或可信第三方来源的风险、负面或失效证据",
        "Company-specific non-methodology evidence that supports or challenges the thesis": "支持或挑战论点的公司级非方法论证据",
        "Resolved ticker-specific evidence replacing SERENITY placeholder records": "替换 SERENITY 占位记录的标的级证据",
    }.get(source_target, source_target)


def _localize_playbook_text(value: str, language: str) -> str:
    if language != "zh":
        return value
    return {
        "Primary/fact evidence is required before this candidate can clear the research confidence gate.": "需要 primary/fact 证据才能提升研究置信度门禁。",
        "Source title, URL, and source excerpt must directly support the task claim.": "来源标题、链接和原文摘录必须能直接支撑任务声明。",
        "Import the evidence, rerun the analysis, and confirm the quality gate improves.": "导入证据后重新生成分析，并确认质量门禁改善。",
        "Risk coverage is required to avoid a one-sided thesis before promotion.": "需要风险覆盖，避免在提升研究置信度前形成单边论点。",
        "Evidence should include a negative, downside, or invalidation claim tied to the ticker.": "证据应包含与标的相关的负面、下行或失效声明。",
        "Company-specific evidence is required to reduce reliance on methodology-only records.": "需要公司级证据，降低对纯方法论记录的依赖。",
        "Evidence should support or challenge the ticker-specific thesis with a traceable source excerpt.": "证据应通过可追溯摘录支持或挑战标的级论点。",
        "Ticker-specific evidence is required to replace SERENITY placeholder records.": "需要标的级证据替换 SERENITY 占位记录。",
        "Evidence should name the ticker and include a traceable source excerpt.": "证据应点名标的，并包含可追溯原文摘录。",
    }.get(value, value)
