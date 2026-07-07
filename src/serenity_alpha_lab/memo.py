from __future__ import annotations

from typing import Iterable, List
from collections import Counter

from .evidence import EvidenceItem
from .scoring import ResearchScore, summarize_scorecard
from .source_coverage import assess_source_coverage, render_source_coverage_markdown


DISCLAIMER = (
    "This memo is research only. It is not investment advice, does not recommend any trade, "
    "and requires independent verification before any capital decision."
)

ZH_DISCLAIMER = "本报告仅供研究，不构成投资建议，不推荐任何交易；任何资金决策前都需要独立验证。"


def generate_memo(
    query: str,
    ticker: str | None,
    evidence: Iterable[EvidenceItem],
    score: ResearchScore,
    language: str = "en",
) -> str:
    items = list(evidence)
    focus_primary_items = _focus_primary_evidence(items, ticker)
    sector_context_primary_items = _sector_context_primary_evidence(items, ticker)
    primary_ids = {item.id for item in focus_primary_items + sector_context_primary_items}
    subject = ticker or query
    zh = language == "zh"
    scorecard = summarize_scorecard(score)
    rating = scorecard.zh_rating if zh else scorecard.rating
    confidence = scorecard.zh_confidence if zh else scorecard.confidence
    gaps = scorecard.zh_gaps if zh else scorecard.gaps
    gap_text = ", ".join(gaps) if gaps else ("无" if zh else "none")
    lines: List[str] = [
        "# Serenity Alpha Lab 研究备忘录" if zh else "# Serenity Alpha Lab Memo",
        "",
        f"**研究问题:** {query}" if zh else f"**Research question:** {query}",
        f"**关注标的:** {subject}" if zh else f"**Ticker focus:** {subject}",
        f"**证据数量:** {len(items)}" if zh else f"**Evidence count:** {len(items)}",
        f"**综合研究评分:** {score.total}/100" if zh else f"**Composite research score:** {score.total}/100",
        f"**Serenity 评级:** {rating}" if zh else f"**Serenity rating:** {rating}",
        f"**研究置信层级:** {confidence}" if zh else f"**Research confidence:** {confidence}",
        f"**关键短板:** {gap_text}" if zh else f"**Key gaps:** {gap_text}",
        "",
        "## 评分卡" if zh else "## Scorecard",
        "",
        "| 因子 | 原始分 | 加权贡献 | 证据 |" if zh else "| Factor | Raw Score | Weighted Contribution | Evidence |",
        "|---|---:|---:|---|",
    ]

    for factor in score.factors.values():
        evidence_refs = ", ".join(factor.evidence_ids) if factor.evidence_ids else ("无" if zh else "none")
        label = factor.name.replace("_", " ")
        if factor.penalty:
            label += " (扣分)" if zh else " (penalty)"
        lines.append(f"| {label} | {factor.value} | {factor.weighted_value:.1f} | {evidence_refs} |")

    if zh:
        lines.extend(
            [
                "",
                "## 投资分析结论",
                "",
                _investment_conclusion(subject=subject, score=score, items=items),
                "",
                "## Serenity 选股因子",
                "",
            ]
        )
        lines.extend(_serenity_factor_takeaways(items))
        lines.extend(["", "## 关键跟踪指标", ""])
        lines.extend(_tracking_indicators(items))

    lines.extend(
        [
            "",
            "## 行业结构图" if zh else "## Industry Structure Map",
            "",
        ]
    )
    lines.extend(_industry_structure_map(items, language=language))
    lines.extend(
        [
            "",
            "## 催化剂时间线" if zh else "## Catalyst Timeline",
            "",
        ]
    )
    lines.extend(_catalyst_timeline(items, language=language))
    lines.extend(
        [
            "",
            "## 证据缺口优先级" if zh else "## Evidence Gap Priority",
            "",
        ]
    )
    lines.extend(_evidence_gap_priority(scorecard.gaps, items, focus=ticker, language=language))

    lines.extend(
        [
            "",
            "## 论点摘要" if zh else "## Thesis Summary",
            "",
            _build_thesis(subject=subject, items=items, language=language),
            "",
            "## 声明类型组合" if zh else "## Claim Type Mix",
            "",
            _claim_type_mix(items, language=language),
            "",
            "## 来源覆盖" if zh else "## Source Coverage",
            "",
            render_source_coverage_markdown(assess_source_coverage(items, focus_ticker=ticker)),
            "",
            "## Primary Source 证据" if zh else "## Primary Source Evidence",
            "",
        ]
    )
    lines.extend(_format_primary_evidence(focus_primary_items, language=language))
    lines.extend(
        [
            "",
            "## 行业上下文证据" if zh else "## Sector Context Evidence",
            "",
        ]
    )
    lines.extend(_format_sector_context_evidence(sector_context_primary_items, language=language))
    lines.extend(
        [
            "",
            "## 支撑证据" if zh else "## Supporting Evidence",
            "",
        ]
    )
    lines.extend(
        _format_evidence(
            [item for item in items if item.direction != "negative" and item.id not in primary_ids],
            language=language,
        )
    )
    lines.extend(["", "## 怀疑者复核" if zh else "## Skeptic Review", ""])
    lines.extend(_skeptic_review(items, language=language))
    lines.extend(["", "## 失效条件" if zh else "## Invalidation Conditions", ""])
    lines.extend(_invalidation_conditions(items, focus=ticker, language=language))
    lines.extend(["", "## 证据补齐行动清单" if zh else "## Evidence Action Plan", ""])
    lines.extend(_evidence_action_plan(scorecard.gaps, items, focus=ticker, language=language))
    lines.extend(["", "## 后续研究任务" if zh else "## Next Research Tasks", ""])
    lines.extend(_next_tasks(items, language=language))
    lines.extend(["", "## 免责声明" if zh else "## Disclaimer", "", ZH_DISCLAIMER if zh else DISCLAIMER, ""])
    return "\n".join(lines)


def _build_thesis(subject: str, items: List[EvidenceItem], language: str = "en") -> str:
    if language == "zh":
        if not items:
            return f"尚未为 {subject} 加载证据；当前不应推进投资论点。"

        positive = [item for item in items if item.direction == "positive"]
        negative = [item for item in items if item.direction == "negative"]
        layers = sorted({item.supply_chain_layer for item in items})
        themes = sorted({theme for item in items for theme in item.themes})
        layer_text = "、".join(layers) if layers else "待确认产业链环节"
        theme_text = "、".join(themes[:5]) if themes else "待确认主题"

        return (
            f"{subject} 目前形成的是一个临时性的 Serenity 风格研究案例，覆盖 {layer_text}。"
            f"当前最强主题包括 {theme_text}。该案例由 {len(positive)} 条正向证据支撑，"
            f"同时受到 {len(negative)} 条明确风险证据约束。只有当 primary evidence 进一步确认客户验证、"
            "收入爬坡节奏和替代供给受限时，研究置信度才应提高。"
        )

    if not items:
        return f"No evidence has been loaded for {subject}; the thesis should not be advanced."

    positive = [item for item in items if item.direction == "positive"]
    negative = [item for item in items if item.direction == "negative"]
    layers = sorted({item.supply_chain_layer for item in items})
    themes = sorted({theme for item in items for theme in item.themes})

    return (
        f"{subject} has a provisional Serenity-style research case across "
        f"{', '.join(layers)}. The strongest themes are {', '.join(themes[:5])}. "
        f"The case is supported by {len(positive)} positive evidence item(s) and constrained by "
        f"{len(negative)} explicit risk item(s). Confidence should rise only if primary evidence confirms "
        "customer qualification, revenue ramp timing, and limited substitute supply."
    )


def _investment_conclusion(subject: str, score: ResearchScore, items: List[EvidenceItem]) -> str:
    primary_count = len(_primary_evidence(items))
    risk_count = len([item for item in items if item.direction == "negative" or item.claim_type in {"risk", "invalidation"}])
    if not items:
        return f"{subject} 当前缺少可用证据，只能进入观察池，不能形成有效研究结论。"
    if primary_count == 0:
        return (
            f"{subject} 当前更适合作为候选观察对象，而不是正式高置信研究结论。"
            f"综合研究评分为 {score.total}/100，但缺少 primary source 或 fact 证据，需要优先补齐公司公告、财报或官方材料。"
        )
    return (
        f"{subject} 当前可进入 Serenity 候选池复核。综合研究评分为 {score.total}/100，"
        f"报告使用 {len(items)} 条证据，其中 primary/fact 证据 {primary_count} 条、风险/失效证据 {risk_count} 条。"
        "下一步重点不是给出买卖建议，而是验证景气链条、瓶颈位置和业绩兑现路径。"
    )


def _serenity_factor_takeaways(items: List[EvidenceItem]) -> List[str]:
    layers = sorted({item.supply_chain_layer for item in items})
    themes = sorted({theme for item in items for theme in item.themes})
    positive = len([item for item in items if item.direction == "positive"])
    negative = len([item for item in items if item.direction == "negative"])
    return [
        f"- **景气方向:** 当前证据覆盖 {positive} 条正向线索和 {negative} 条负向线索，需要判断需求是否已经传导到订单或收入。",
        f"- **产业链位置:** 已识别环节包括 {('、'.join(layers) if layers else '待确认')}，优先寻找供需最紧、替代最难的节点。",
        f"- **主题映射:** 主要主题包括 {('、'.join(themes[:6]) if themes else '待确认')}，需要区分行业 beta 与公司 alpha。",
        "- **拥挤与失效:** 如果市场关注先于公司证据大幅升温，应降低结论置信度并强化反证跟踪。",
    ]


def _tracking_indicators(items: List[EvidenceItem]) -> List[str]:
    has_primary = bool(_primary_evidence(items))
    return [
        "- 公司公告、财报、电话会中是否出现客户验证、订单、产能或收入爬坡的直接证据。",
        "- 同行业替代供应商是否加速扩产或拿到关键客户资格。",
        "- 收入、毛利率、订单或 backlog 是否与景气逻辑同步改善。",
        "- 主题热度、成交拥挤度和估值预期是否明显跑在基本面之前。",
        "- " + ("继续补充 primary source 以验证现有判断。" if has_primary else "优先补充 primary source；当前结论只能作为研究线索。"),
    ]


def _industry_structure_map(items: List[EvidenceItem], language: str = "en") -> List[str]:
    if language == "zh":
        lines = [
            "| 产业链环节 | 证据数量 | Primary/Fact | 风险 | 代表主题 |",
            "|---|---:|---:|---:|---|",
        ]
        if not items:
            lines.append("| 待确认 | 0 | 0 | 0 | 无 |")
            return lines
    else:
        lines = [
            "| Supply-chain Layer | Evidence Count | Primary/Fact | Risk | Representative Themes |",
            "|---|---:|---:|---:|---|",
        ]
        if not items:
            lines.append("| To confirm | 0 | 0 | 0 | none |")
            return lines

    for layer in sorted({item.supply_chain_layer for item in items}):
        layer_items = [item for item in items if item.supply_chain_layer == layer]
        primary_count = len(_primary_evidence(layer_items))
        risk_count = len([item for item in layer_items if item.direction == "negative" or item.claim_type in {"risk", "invalidation"}])
        themes = sorted({theme for item in layer_items for theme in item.themes})
        theme_text = ", ".join(themes[:5]) if themes else ("无" if language == "zh" else "none")
        lines.append(f"| {layer} | {len(layer_items)} | {primary_count} | {risk_count} | {theme_text} |")
    return lines


def _catalyst_timeline(items: List[EvidenceItem], language: str = "en") -> List[str]:
    if language == "zh":
        lines = ["| 日期 | 类型 | 标的 | 证据 |", "|---|---|---|---|"]
    else:
        lines = ["| Date | Type | Ticker | Evidence |", "|---|---|---|---|"]

    catalyst_items = [
        item
        for item in items
        if item.claim_type in {"catalyst", "fact"} or "revenue" in {theme.lower() for theme in item.themes}
    ]
    if not catalyst_items:
        if language == "zh":
            lines.append("| 待补充 | evidence gap | 待确认 | 尚未识别明确催化剂；优先补充订单、客户验证、财报或收入爬坡证据。 |")
        else:
            lines.append("| To collect | evidence gap | TBD | No explicit catalyst identified; prioritize orders, customer validation, filings, or revenue-ramp evidence. |")
        return lines

    for item in sorted(catalyst_items, key=lambda value: (value.published_at, value.id))[:6]:
        tickers = ", ".join(item.tickers[:4]) if item.tickers else ("待确认" if language == "zh" else "TBD")
        event_type = item.claim_type
        evidence = _table_safe(item.summary)
        lines.append(f"| {item.published_at.isoformat()} | {event_type} | {tickers} | {evidence} |")
    return lines


def _evidence_gap_priority(gaps: List[str], items: List[EvidenceItem], focus: str | None = None, language: str = "en") -> List[str]:
    canonical_gaps = _prioritized_actionable_gaps(gaps, items, focus)
    if not canonical_gaps:
        canonical_gaps = ["maintenance"]

    if language == "zh":
        lines = ["| 优先级 | 缺口 | 影响 | 下一步证据 |", "|---|---|---|---|"]
    else:
        lines = ["| Priority | Gap | Why It Matters | Next Evidence |", "|---|---|---|---|"]

    for index, gap in enumerate(canonical_gaps[:5], start=1):
        why, next_evidence = _gap_priority_copy(gap, items, focus=focus, language=language)
        lines.append(f"| P{index} | {gap} | {why} | {next_evidence} |")
    return lines


def _prioritized_actionable_gaps(gaps: List[str], items: List[EvidenceItem], focus: str | None = None) -> List[str]:
    present = {gap for gap in gaps if gap != "none"}
    if not present:
        return []
    if "no_evidence" in present:
        return ["no_evidence"]

    ordered: List[str] = []
    if "primary_source_depth" in present and not _focus_primary_evidence(items, focus):
        ordered.append("primary_source_depth")
    for gap in ["demand_validation", "invalidation_plan", "crowding_risk"]:
        if gap in present:
            ordered.append(gap)
    if "low_score" in present and not ordered:
        ordered.append("low_score")
    return ordered


def _gap_priority_copy(gap: str, items: List[EvidenceItem], focus: str | None = None, language: str = "en") -> tuple[str, str]:
    subject = focus.upper().lstrip("$") if focus else _fallback_subject(items)
    if language == "zh":
        mapping = {
            "no_evidence": ("没有证据就无法形成可审计研究结论。", f"先为 {subject} 补充公司公告、财报、官方报告或可信第三方证据。"),
            "low_score": ("综合分偏低说明瓶颈、需求、供给或证据质量尚未共振。", f"补充 {subject} 与客户验证、订单、收入或供给约束直接相关的证据。"),
            "primary_source_depth": ("缺少 primary/fact 会让论点停留在推断层。", f"补充 {subject} 的财报、公告、SEC/companyfacts、交易所披露或官方报告。"),
            "demand_validation": ("没有需求验证就无法确认景气是否传导到公司层面。", f"寻找 {subject} 的客户资格、订单、backlog、产能利用率或收入爬坡证据。"),
            "invalidation_plan": ("缺少反证条件会让报告无法及时降级。", "明确客户流失、替代供给扩张、毛利恶化或收入延期的触发条件。"),
            "crowding_risk": ("拥挤度升高会压缩安全边际并放大回撤。", "增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。"),
            "maintenance": ("当前没有主要短板，但结论仍会随新证据过期。", f"继续跟踪 {subject} 的 primary evidence、风险证据和反证条件。"),
        }
        return mapping.get(gap, ("该缺口会降低报告置信度。", "补充可追溯证据并重新评分。"))

    mapping = {
        "no_evidence": ("No auditable research conclusion exists without evidence.", f"Add filings, official reports, or reliable third-party evidence for {subject}."),
        "low_score": ("The score lacks alignment across bottleneck, demand, supply, or evidence quality.", f"Add direct evidence for customer validation, orders, revenue, or supply constraints tied to {subject}."),
        "primary_source_depth": ("Without primary/fact evidence, the thesis remains inference-led.", f"Add filings, company reports, SEC/companyfacts, exchange disclosures, or official reports for {subject}."),
        "demand_validation": ("Demand must be visible at the company level before confidence rises.", f"Collect customer qualification, order, backlog, utilization, or revenue-ramp evidence for {subject}."),
        "invalidation_plan": ("Weak disconfirmation rules make the report hard to downgrade on time.", "Define customer-loss, substitute-supply, margin, or revenue-delay triggers."),
        "crowding_risk": ("Higher crowding compresses margin of safety and amplifies drawdown risk.", "Add valuation, trading-attention, social-interest, and expectation-timing evidence."),
        "maintenance": ("No major gap is currently flagged, but the conclusion can still expire.", f"Continue tracking primary evidence, risk evidence, and invalidation triggers for {subject}."),
    }
    return mapping.get(gap, ("This gap lowers report confidence.", "Add traceable evidence and rerun scoring."))


def _table_safe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _format_evidence(items: List[EvidenceItem], language: str = "en") -> List[str]:
    if not items:
        if language == "zh":
            return ["- 没有匹配到支撑证据。"]
        return ["- No supporting evidence matched the query."]

    lines: List[str] = []
    for item in items:
        confidence = "置信度" if language == "zh" else "confidence"
        lines.append(
            f"- **{item.id}** [{item.source_title}]({item.source_url}) "
            f"({item.published_at.isoformat()}, {item.strength}, {item.claim_type}, {confidence} {item.confidence:.2f}): {item.summary}"
        )
    return lines


def _format_primary_evidence(items: List[EvidenceItem], language: str = "en") -> List[str]:
    if not items:
        if language == "zh":
            return ["- 没有匹配到 primary source 证据。"]
        return ["- No primary source evidence matched the query."]

    lines: List[str] = []
    for item in items:
        lines.extend(_format_evidence([item], language=language))
        if item.source_excerpt.strip():
            label = "来源摘录" if language == "zh" else "Source excerpt"
            lines.append(f"  - **{label}:** {item.source_excerpt.strip()}")
    return lines


def _format_sector_context_evidence(items: List[EvidenceItem], language: str = "en") -> List[str]:
    if not items:
        if language == "zh":
            return ["- 没有匹配到跨标的 primary source 上下文。"]
        return ["- No cross-ticker primary source context matched the query."]
    return _format_primary_evidence(items, language=language)


def _primary_evidence(items: List[EvidenceItem]) -> List[EvidenceItem]:
    return [
        item
        for item in items
        if item.strength == "primary" or item.claim_type == "fact" or "primary-source" in item.themes
    ]


def _focus_primary_evidence(items: List[EvidenceItem], ticker: str | None) -> List[EvidenceItem]:
    primary_items = _primary_evidence(items)
    if not ticker:
        return primary_items

    focus = _normalize_ticker(ticker)
    return [item for item in primary_items if focus in {_normalize_ticker(value) for value in item.tickers}]


def _sector_context_primary_evidence(items: List[EvidenceItem], ticker: str | None) -> List[EvidenceItem]:
    if not ticker:
        return []

    focus_primary_ids = {item.id for item in _focus_primary_evidence(items, ticker)}
    return [item for item in _primary_evidence(items) if item.id not in focus_primary_ids]


def _normalize_ticker(ticker: str) -> str:
    return ticker.upper().lstrip("$")


def _claim_type_mix(items: List[EvidenceItem], language: str = "en") -> str:
    if not items:
        if language == "zh":
            return "没有匹配到证据。"
        return "No evidence matched the query."
    counts = Counter(item.claim_type for item in items)
    return ", ".join(f"{claim_type}: {count}" for claim_type, count in sorted(counts.items()))


def _skeptic_review(items: List[EvidenceItem], language: str = "en") -> List[str]:
    negative = [item for item in items if item.direction == "negative"]
    speculative = [item for item in items if item.strength == "speculative"]
    lines: List[str] = []

    if negative:
        for item in negative:
            prefix = "风险证据" if language == "zh" else "Risk evidence"
            lines.append(f"- {prefix} `{item.id}`: {item.summary}")
    else:
        if language == "zh":
            lines.append("- 没有检索到直接负面证据；这代表研究缺口，不代表风险已经排除。")
        else:
            lines.append("- No direct negative evidence was retrieved; this is a research gap, not a clean bill of health.")

    if speculative:
        ids = ", ".join(item.id for item in speculative)
        if language == "zh":
            lines.append(f"- 推测性证据在提高置信度前需要进一步确认：{ids}。")
        else:
            lines.append(f"- Speculative evidence needs confirmation before conviction rises: {ids}.")

    if language == "zh":
        lines.append("- 检查社交关注度是否已经跑在公司确认的客户爬坡之前。")
        lines.append("- 将瓶颈候选标的与替代供应商、客户内部采购方案进行对比。")
    else:
        lines.append("- Check whether social attention is moving faster than company-confirmed customer ramps.")
        lines.append("- Compare the bottleneck candidate against substitute suppliers and internal customer sourcing options.")
    return lines


def _invalidation_conditions(items: List[EvidenceItem], focus: str | None = None, language: str = "en") -> List[str]:
    tickers = sorted({ticker for item in items for ticker in item.tickers})
    subject = focus.upper().lstrip("$") if focus else (", ".join(tickers[:5]) if tickers else "the candidate")
    if language == "zh":
        return [
            f"- {subject} 无法展示客户验证进展或 design-in 证据。",
            "- 收入爬坡时间推迟，但估值或市场关注度已经提前反映成功预期。",
            "- 替代供应商扩张快于预期，削弱原先判断的瓶颈属性。",
            "- Primary filings、电话会记录或客户数据与推断的供应链角色相矛盾。",
        ]
    return [
        f"- {subject} fails to show customer qualification progress or design-in evidence.",
        "- Revenue ramp timing slips while valuation or attention already discounts success.",
        "- Alternative suppliers expand faster than expected and remove the bottleneck.",
        "- Primary filings, transcripts, or customer data contradict the inferred supply-chain role.",
    ]


def _evidence_action_plan(gaps: List[str], items: List[EvidenceItem], focus: str | None = None, language: str = "en") -> List[str]:
    subject = focus.upper().lstrip("$") if focus else _fallback_subject(items)
    canonical_gaps = set(gaps)
    if "none" in canonical_gaps:
        canonical_gaps = set()

    lines: List[str] = []
    if language == "zh":
        if "primary_source_depth" in canonical_gaps or not _focus_primary_evidence(items, focus):
            lines.append(f"- **Primary source 深度:** 补充 {subject} 的公司公告、财报、官方报告、SEC/companyfacts 或交易所披露。")
        if "demand_validation" in canonical_gaps:
            lines.append(f"- **需求验证:** 收集与 {subject} 直接相关的客户验证、订单、backlog 或收入爬坡证据。")
        if "invalidation_plan" in canonical_gaps:
            lines.append(f"- **反证计划:** 明确哪些客户流失、替代供应扩张、毛利率恶化或收入延期会推翻当前论点。")
        if "crowding_risk" in canonical_gaps:
            lines.append("- **拥挤度复核:** 增加估值、成交热度、社媒关注和预期兑现节奏的对照证据。")
        if "low_score" in canonical_gaps or "no_evidence" in canonical_gaps:
            lines.append(f"- **晋级门槛:** 在上述证据短板解决前，{subject} 只能保持观察池状态。")
        if not lines:
            lines.append(f"- **维护动作:** 继续跟踪 {subject} 的新增 primary evidence、风险证据和反证条件，避免结论过期。")
        return lines

    if "primary_source_depth" in canonical_gaps or not _focus_primary_evidence(items, focus):
        lines.append(f"- **Primary source depth:** Add company filings, official reports, SEC/companyfacts, or exchange disclosures for {subject}.")
    if "demand_validation" in canonical_gaps:
        lines.append(f"- **Demand validation:** Collect customer qualification, order, backlog, or revenue-ramp evidence tied to {subject}.")
    if "invalidation_plan" in canonical_gaps:
        lines.append("- **Invalidation plan:** Define which customer loss, substitute supply expansion, margin deterioration, or revenue delay would break the thesis.")
    if "crowding_risk" in canonical_gaps:
        lines.append("- **Crowding review:** Add valuation, trading-attention, social-interest, and expectation-timing evidence.")
    if "low_score" in canonical_gaps or "no_evidence" in canonical_gaps:
        lines.append(f"- **Promotion gate:** Keep {subject} in watchlist status until the evidence gaps above are resolved.")
    if not lines:
        lines.append(f"- **Maintenance:** Continue tracking new primary evidence, risk evidence, and invalidation conditions for {subject}.")
    return lines


def _fallback_subject(items: List[EvidenceItem]) -> str:
    tickers = sorted({ticker.upper().lstrip("$") for item in items for ticker in item.tickers})
    return ", ".join(tickers[:5]) if tickers else "the candidate"


def _next_tasks(items: List[EvidenceItem], language: str = "en") -> List[str]:
    layers = sorted({item.supply_chain_layer for item in items})
    layer_text = ", ".join(layers) if layers else "the mapped supply-chain layer"
    if language == "zh":
        zh_layer_text = "、".join(layers) if layers else "已映射的产业链环节"
        return [
            f"- 为 {zh_layer_text} 建立来源表，覆盖 primary filings、客户引用和产能线索。",
            "- 对每一条关键论点区分直接证据与推断链接。",
            "- 跟踪会改变需求确定性、供给弹性或交易拥挤度的新证据。",
            "- 为每个关键论点步骤补充至少一个非 Serenity 来源。",
        ]
    return [
        f"- Build a source table for {layer_text} with primary filings, customer references, and capacity clues.",
        "- Separate direct evidence from inferred links for every material claim.",
        "- Track new evidence that changes demand certainty, supply elasticity, or crowding risk.",
        "- Add at least one non-Serenity source for each critical thesis step.",
    ]
