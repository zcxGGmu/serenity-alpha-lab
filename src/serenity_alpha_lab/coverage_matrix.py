from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .evidence import EvidenceItem, tokenize
from .source_coverage import assess_source_coverage
from .stock_universe import StockUniverseEntry


@dataclass(frozen=True)
class CoverageMatrixRow:
    priority: str
    ticker: str
    name: str
    market: str
    matched_themes: list[str]
    evidence_count: int
    primary_count: int
    risk_count: int
    gaps: list[str]
    next_source_target: str
    search_prompt: str


@dataclass(frozen=True)
class CoverageMatrix:
    query: str
    rows: list[CoverageMatrixRow]


def build_coverage_matrix(
    evidence: Iterable[EvidenceItem],
    *,
    universe: Sequence[StockUniverseEntry],
    query: str,
) -> CoverageMatrix:
    items = list(evidence)
    query_tokens = set(tokenize(query))
    rows: list[CoverageMatrixRow] = []

    for entry in universe:
        matched_themes = _matched_themes(entry, query_tokens, query)
        if not matched_themes:
            continue

        coverage = assess_source_coverage(items, focus_ticker=entry.ticker)
        gaps = [flag.code for flag in coverage.flags]
        rows.append(
            CoverageMatrixRow(
                priority=_priority(gaps),
                ticker=entry.ticker,
                name=entry.name,
                market=entry.market,
                matched_themes=matched_themes,
                evidence_count=coverage.focus_evidence_count,
                primary_count=coverage.primary_count,
                risk_count=coverage.risk_count,
                gaps=gaps or ["none"],
                next_source_target=_next_source_target(gaps),
                search_prompt=_search_prompt(entry.ticker, gaps, query),
            )
        )

    rows.sort(key=lambda row: (_priority_rank(row.priority), row.evidence_count, row.primary_count, row.risk_count, row.ticker))
    return CoverageMatrix(query=query, rows=rows)


def render_coverage_matrix_markdown(matrix: CoverageMatrix, *, language: str = "en") -> str:
    if language == "zh":
        lines = [
            "# 股票池覆盖矩阵",
            "",
            f"**查询:** {matrix.query}",
            f"**候选数:** {len(matrix.rows)}",
            "",
            "| 优先级 | 股票代码 | 名称 | 市场 | 主题 | 证据 | Primary/Fact | 风险 | 缺口 | 下一步来源目标 | 搜索提示 |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    else:
        lines = [
            "# Universe Coverage Matrix",
            "",
            f"**Query:** {matrix.query}",
            f"**Candidates:** {len(matrix.rows)}",
            "",
            "| Priority | Ticker | Name | Market | Themes | Evidence | Primary/Fact | Risk | Gaps | Next Source Target | Search Prompt |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    for row in matrix.rows:
        lines.append(
            " | ".join(
                [
                    f"| {_localize_priority(row.priority, language)}",
                    row.ticker,
                    row.name,
                    row.market,
                    ", ".join(row.matched_themes),
                    str(row.evidence_count),
                    str(row.primary_count),
                    str(row.risk_count),
                    ", ".join(_localize_gap(gap, language) for gap in row.gaps),
                    _localize_source_target(row.next_source_target, language),
                    f"{row.search_prompt} |",
                ]
            )
        )
    if not matrix.rows:
        if language == "zh":
            lines.append("| 低 | none | 未匹配到股票池候选 | n/a | n/a | 0 | 0 | 0 | 未匹配股票池 | 扩充股票池 | 为查询补充股票池别名 |")
        else:
            lines.append("| low | none | No matched universe candidates | n/a | n/a | 0 | 0 | 0 | no_universe_match | expand stock universe | add universe aliases for query |")
    lines.append("")
    return "\n".join(lines)


def _matched_themes(entry: StockUniverseEntry, query_tokens: set[str], query: str) -> list[str]:
    compact_query = query.strip().lower()
    matched: list[str] = []
    alias_match = any(compact_query == alias.lower() or compact_query in alias.lower() for alias in entry.aliases)
    for theme in entry.themes:
        theme_tokens = set(tokenize(theme))
        if alias_match or compact_query == theme.lower() or bool(query_tokens & theme_tokens):
            matched.append(theme)
    return matched


def _priority(gaps: Sequence[str]) -> str:
    if "missing_focus_ticker" in gaps or "missing_primary_source" in gaps:
        return "high"
    if "missing_risk_coverage" in gaps:
        return "medium"
    return "low"


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _next_source_target(gaps: Sequence[str]) -> str:
    if "missing_focus_ticker" in gaps or "missing_primary_source" in gaps:
        return "primary filing or official report"
    if "missing_risk_coverage" in gaps:
        return "risk or invalidation source"
    return "monitoring refresh"


def _search_prompt(ticker: str, gaps: Sequence[str], query: str) -> str:
    if "missing_focus_ticker" in gaps or "missing_primary_source" in gaps:
        return f"{ticker} primary filing {query}"
    if "missing_risk_coverage" in gaps:
        return f"{ticker} risk invalidation {query}"
    return f"{ticker} latest official update {query}"


def _localize_priority(priority: str, language: str) -> str:
    if language != "zh":
        return priority
    return {"high": "高", "medium": "中", "low": "低"}.get(priority, priority)


def _localize_gap(gap: str, language: str) -> str:
    if language != "zh":
        return gap
    return {
        "missing_focus_ticker": "缺少直接标的证据",
        "missing_primary_source": "缺少 primary/fact 来源",
        "missing_risk_coverage": "缺少风险证据",
        "methodology_concentration": "方法论证据过度集中",
        "placeholder_concentration": "SERENITY 占位证据过度集中",
        "none": "无",
    }.get(gap, gap)


def _localize_source_target(target: str, language: str) -> str:
    if language != "zh":
        return target
    return {
        "primary filing or official report": "primary filing 或官方报告",
        "risk or invalidation source": "风险或失效证据来源",
        "monitoring refresh": "持续跟踪更新",
    }.get(target, target)
