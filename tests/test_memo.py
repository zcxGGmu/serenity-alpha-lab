from pathlib import Path
from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.evidence import load_evidence
from serenity_alpha_lab.memo import generate_memo
from serenity_alpha_lab.retrieval import retrieve
from serenity_alpha_lab.scoring import score_research_question


FIXTURE = Path(__file__).parent / "fixtures" / "evidence.jsonl"


def test_generate_memo_contains_evidence_skeptic_and_guardrails():
    evidence = retrieve(load_evidence(FIXTURE), query="CPO laser bottleneck", ticker="SIVE")
    score = score_research_question(evidence)
    memo = generate_memo(query="CPO laser bottleneck", ticker="SIVE", evidence=evidence, score=score)

    assert "# Serenity Alpha Lab Memo" in memo
    assert "## Scorecard" in memo
    assert "## Supporting Evidence" in memo
    assert "## Claim Type Mix" in memo
    assert "## Skeptic Review" in memo
    assert "## Invalidation Conditions" in memo
    assert "https://zcxggmu.github.io/blog/2026/serenity-aleabitoreddit-may-2026-analysis/" in memo
    assert ", inference, confidence" in memo
    assert "research only" in memo.lower()
    forbidden_phrases = ["you should buy", "you should sell", "target price", "position size"]
    assert not any(phrase in memo.lower() for phrase in forbidden_phrases)


def test_generate_memo_invalidation_conditions_focus_requested_ticker():
    evidence = retrieve(load_evidence(FIXTURE), query="CPO laser bottleneck", ticker="SIVE")
    score = score_research_question(evidence)
    memo = generate_memo(query="CPO laser bottleneck", ticker="SIVE", evidence=evidence, score=score)

    assert "- SIVE fails to show customer qualification progress" in memo


def test_generate_memo_lists_primary_source_evidence_before_supporting_evidence():
    primary = EvidenceItem(
        id="sec-companyfacts:AAOI:revenue",
        source_title="SEC companyfacts AAOI Revenue",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 revenue.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "revenue"],
        supply_chain_layer="company financials",
        direction="neutral",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "demand_certainty": 8},
        claim_type="fact",
    )
    inference = EvidenceItem(
        id="github:aaoi:cpo",
        source_title="Serenity CPO method",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="AAOI CPO bottleneck inference.",
        summary="AAOI appears in CPO bottleneck methodology.",
        tickers=["AAOI"],
        themes=["CPO"],
        supply_chain_layer="methodology",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"bottleneck_scarcity": 10},
        claim_type="inference",
    )
    score = score_research_question([primary, inference])

    memo = generate_memo(query="CPO revenue", ticker="AAOI", evidence=[primary, inference], score=score)

    assert "## Source Coverage" in memo
    assert memo.index("## Source Coverage") < memo.index("## Primary Source Evidence")
    assert "## Primary Source Evidence" in memo
    assert memo.index("## Primary Source Evidence") < memo.index("## Supporting Evidence")
    assert "- **sec-companyfacts:AAOI:revenue**" in memo
    supporting_section = memo.split("## Supporting Evidence", 1)[1].split("## Skeptic Review", 1)[0]
    assert "sec-companyfacts:AAOI:revenue" not in supporting_section


def test_generate_memo_separates_cross_ticker_primary_evidence_from_focus_primary_section():
    aaoi_primary = EvidenceItem(
        id="sec-companyfacts:AAOI:revenue",
        source_title="SEC companyfacts AAOI Revenue",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 revenue.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "revenue"],
        supply_chain_layer="company financials",
        direction="neutral",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "demand_certainty": 8},
        claim_type="fact",
    )
    sive_primary = EvidenceItem(
        id="official-report:SIVE:net-sales-2025",
        source_title="Sivers Semiconductors Annual Report 2025",
        source_url="https://www.sivers-semiconductors.com/wp-content/uploads/2026/05/Sivers_annualreport_2025_final.pdf",
        published_at=date(2026, 5, 1),
        claim="Sivers Semiconductors reported 2025 net sales of SEK 306.6 million.",
        summary="Official annual-report evidence shows SIVE 2025 net sales increased to SEK 306.6 million.",
        tickers=["SIVE"],
        themes=["annual-report", "primary-source", "revenue", "CPO"],
        supply_chain_layer="company financials",
        direction="positive",
        strength="primary",
        confidence=0.9,
        factor_impacts={"evidence_quality": 24, "demand_certainty": 8},
        claim_type="fact",
        source_excerpt=(
            "The Group's net sales amounted to SEK 306.6 (219.2) million, "
            "an increase of SEK 87.4 million or 40% compared with the previous year."
        ),
    )
    aaoi_inference = EvidenceItem(
        id="github:aaoi:cpo",
        source_title="Serenity CPO method",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="AAOI CPO bottleneck inference.",
        summary="AAOI appears in CPO bottleneck methodology.",
        tickers=["AAOI"],
        themes=["CPO"],
        supply_chain_layer="methodology",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"bottleneck_scarcity": 10},
        claim_type="inference",
    )
    score = score_research_question([aaoi_primary, sive_primary, aaoi_inference])

    memo = generate_memo(
        query="CPO revenue",
        ticker="AAOI",
        evidence=[aaoi_primary, sive_primary, aaoi_inference],
        score=score,
    )

    primary_section = memo.split("## Primary Source Evidence", 1)[1].split("## Sector Context Evidence", 1)[0]
    sector_context_section = memo.split("## Sector Context Evidence", 1)[1].split("## Supporting Evidence", 1)[0]
    supporting_section = memo.split("## Supporting Evidence", 1)[1].split("## Skeptic Review", 1)[0]

    assert "sec-companyfacts:AAOI:revenue" in primary_section
    assert "official-report:SIVE:net-sales-2025" not in primary_section
    assert "official-report:SIVE:net-sales-2025" in sector_context_section
    assert "Official annual-report evidence shows SIVE" in sector_context_section
    assert "official-report:SIVE:net-sales-2025" not in supporting_section


def test_generate_memo_primary_section_includes_negative_primary_facts():
    negative_primary = EvidenceItem(
        id="sec-companyfacts:AAOI:net-income",
        source_title="SEC companyfacts AAOI Net Income",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Net Income for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 net loss.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "profitability"],
        supply_chain_layer="company financials",
        direction="negative",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "profitability": -8},
        claim_type="fact",
    )
    score = score_research_question([negative_primary])

    memo = generate_memo(query="profitability", ticker="AAOI", evidence=[negative_primary], score=score)

    primary_section = memo.split("## Primary Source Evidence", 1)[1].split("## Supporting Evidence", 1)[0]
    assert "sec-companyfacts:AAOI:net-income" in primary_section


def test_generate_memo_includes_source_excerpt_for_primary_evidence():
    primary = EvidenceItem(
        id="official-report:SIVE:net-sales-2025",
        source_title="Sivers Semiconductors Annual Report 2025",
        source_url="https://www.sivers-semiconductors.com/wp-content/uploads/2026/05/Sivers_annualreport_2025_final.pdf",
        published_at=date(2026, 5, 1),
        claim="Sivers Semiconductors reported 2025 net sales of SEK 306.6 million.",
        summary="Official annual-report evidence shows SIVE 2025 net sales increased to SEK 306.6 million.",
        tickers=["SIVE"],
        themes=["annual-report", "primary-source", "revenue", "CPO"],
        supply_chain_layer="company financials",
        direction="positive",
        strength="primary",
        confidence=0.9,
        factor_impacts={"evidence_quality": 24, "demand_certainty": 8},
        claim_type="fact",
        source_excerpt=(
            "The Group’s net sales amounted to SEK 306.6 (219.2) million, "
            "an increase of SEK 87.4 million or 40% compared with the previous year."
        ),
    )
    score = score_research_question([primary])

    memo = generate_memo(query="SIVE CPO revenue", ticker="SIVE", evidence=[primary], score=score)

    primary_section = memo.split("## Primary Source Evidence", 1)[1].split("## Supporting Evidence", 1)[0]
    assert "**Source excerpt:**" in primary_section
    assert "The Group’s net sales amounted to SEK 306.6" in primary_section


def test_generate_memo_keeps_primary_evidence_without_source_excerpt():
    primary = EvidenceItem(
        id="sec-companyfacts:AAOI:revenue",
        source_title="SEC companyfacts AAOI Revenue",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 revenue.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "revenue"],
        supply_chain_layer="company financials",
        direction="neutral",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "demand_certainty": 8},
        claim_type="fact",
    )
    score = score_research_question([primary])

    memo = generate_memo(query="AAOI revenue", ticker="AAOI", evidence=[primary], score=score)

    primary_section = memo.split("## Primary Source Evidence", 1)[1].split("## Supporting Evidence", 1)[0]
    assert "sec-companyfacts:AAOI:revenue" in primary_section
    assert "**Source excerpt:**" not in primary_section


def test_generate_memo_can_render_chinese_report():
    primary = EvidenceItem(
        id="sec-companyfacts:AAOI:revenue",
        source_title="SEC companyfacts AAOI Revenue",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 revenue.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "revenue"],
        supply_chain_layer="company financials",
        direction="neutral",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "demand_certainty": 8},
        claim_type="fact",
        source_excerpt="Revenue was reported in the SEC companyfacts dataset.",
    )
    risk = EvidenceItem(
        id="risk:AAOI",
        source_title="Risk source",
        source_url="https://example.com/risk",
        published_at=date(2026, 1, 1),
        claim="AAOI risk evidence.",
        summary="Customer concentration remains a risk.",
        tickers=["AAOI"],
        themes=["risk"],
        supply_chain_layer="company financials",
        direction="negative",
        strength="derived",
        confidence=0.7,
        factor_impacts={"risk": -10},
        claim_type="risk",
    )
    score = score_research_question([primary, risk])

    memo = generate_memo(query="存储芯片", ticker="AAOI", evidence=[primary, risk], score=score, language="zh")

    assert "# Serenity Alpha Lab 研究备忘录" in memo
    assert "**研究问题:** 存储芯片" in memo
    assert "## 评分卡" in memo
    assert "**Serenity 评级:**" in memo
    assert "**研究置信层级:**" in memo
    assert "**关键短板:**" in memo
    assert "## 投资分析结论" in memo
    assert "## Serenity 选股因子" in memo
    assert "## 关键跟踪指标" in memo
    assert "## 论点摘要" in memo
    assert "## Primary Source 证据" in memo
    assert "## 怀疑者复核" in memo
    assert "## 失效条件" in memo
    assert "仅供研究" in memo
    assert "This memo is research only" not in memo


def test_generate_memo_includes_actionable_evidence_plan_for_gaps():
    inference = EvidenceItem(
        id="github:aaoi:cpo",
        source_title="Serenity CPO method",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="AAOI CPO bottleneck inference.",
        summary="AAOI appears in CPO bottleneck methodology, but primary evidence is not yet deep enough.",
        tickers=["AAOI"],
        themes=["CPO"],
        supply_chain_layer="methodology",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"bottleneck_scarcity": 8},
        claim_type="inference",
    )
    score = score_research_question([inference])

    memo = generate_memo(query="CPO revenue", ticker="AAOI", evidence=[inference], score=score)

    assert "## Evidence Action Plan" in memo
    assert "**Primary source depth:** Add company filings, official reports, SEC/companyfacts, or exchange disclosures for AAOI." in memo
    assert "**Demand validation:** Collect customer qualification, order, backlog, or revenue-ramp evidence tied to AAOI." in memo
    assert "**Promotion gate:** Keep AAOI in watchlist status until the evidence gaps above are resolved." in memo


def test_generate_memo_localizes_evidence_action_plan_for_chinese_reports():
    inference = EvidenceItem(
        id="github:aaoi:cpo",
        source_title="Serenity CPO method",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="AAOI CPO bottleneck inference.",
        summary="AAOI appears in CPO bottleneck methodology, but primary evidence is not yet deep enough.",
        tickers=["AAOI"],
        themes=["CPO"],
        supply_chain_layer="methodology",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"bottleneck_scarcity": 8},
        claim_type="inference",
    )
    score = score_research_question([inference])

    memo = generate_memo(query="CPO revenue", ticker="AAOI", evidence=[inference], score=score, language="zh")

    assert "## 证据补齐行动清单" in memo
    assert "**Primary source 深度:** 补充 AAOI 的公司公告、财报、官方报告、SEC/companyfacts 或交易所披露。" in memo
    assert "**需求验证:** 收集与 AAOI 直接相关的客户验证、订单、backlog 或收入爬坡证据。" in memo
    assert "**晋级门槛:** 在上述证据短板解决前，AAOI 只能保持观察池状态。" in memo


def test_generate_memo_includes_report_quality_sections():
    primary = EvidenceItem(
        id="sec-companyfacts:AAOI:revenue",
        source_title="SEC companyfacts AAOI Revenue",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001158114.json",
        published_at=date(2026, 2, 26),
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI FY2025 revenue.",
        tickers=["AAOI"],
        themes=["SEC companyfacts", "primary-source", "revenue", "CPO"],
        supply_chain_layer="company financials",
        direction="neutral",
        strength="primary",
        confidence=0.88,
        factor_impacts={"evidence_quality": 22, "demand_certainty": 8},
        claim_type="fact",
    )
    catalyst = EvidenceItem(
        id="catalyst:AAOI:customer-qualification",
        source_title="AAOI qualification note",
        source_url="https://example.com/catalyst",
        published_at=date(2026, 3, 15),
        claim="AAOI customer qualification can become a catalyst if it converts into visible revenue.",
        summary="Customer qualification evidence would matter most if it turns into orders or revenue ramp disclosure.",
        tickers=["AAOI"],
        themes=["CPO", "customer qualification"],
        supply_chain_layer="component",
        direction="positive",
        strength="derived",
        confidence=0.72,
        factor_impacts={"demand_certainty": 12, "invalidation_clarity": 8},
        claim_type="catalyst",
    )
    risk = EvidenceItem(
        id="risk:AAOI:crowding",
        source_title="Crowding risk note",
        source_url="https://example.com/risk",
        published_at=date(2026, 4, 1),
        claim="AAOI attention can become crowded before company evidence confirms the ramp.",
        summary="Social attention may move faster than company-confirmed demand.",
        tickers=["AAOI"],
        themes=["crowding", "risk"],
        supply_chain_layer="market_structure",
        direction="negative",
        strength="derived",
        confidence=0.74,
        factor_impacts={"crowding_risk": 40, "invalidation_clarity": 8},
        claim_type="risk",
    )
    score = score_research_question([primary, catalyst, risk])

    memo = generate_memo(query="CPO revenue", ticker="AAOI", evidence=[primary, catalyst, risk], score=score)

    assert "## Industry Structure Map" in memo
    assert "| Supply-chain Layer | Evidence Count | Primary/Fact | Risk | Representative Themes |" in memo
    assert "| company financials | 1 | 1 | 0 | CPO, SEC companyfacts, primary-source, revenue |" in memo
    assert "| component | 1 | 0 | 0 | CPO, customer qualification |" in memo
    assert "| market_structure | 1 | 0 | 1 | crowding, risk |" in memo
    assert "## Catalyst Timeline" in memo
    assert "| 2026-03-15 | catalyst | AAOI | Customer qualification evidence would matter most" in memo
    assert "## Evidence Gap Priority" in memo
    assert "| Priority | Gap | Why It Matters | Next Evidence |" in memo
    assert "| P1 | demand_validation |" in memo
    assert "| P2 | invalidation_plan |" in memo
    assert "| P3 | crowding_risk |" in memo


def test_generate_memo_localizes_report_quality_sections_for_chinese_reports():
    inference = EvidenceItem(
        id="github:aaoi:cpo",
        source_title="Serenity CPO method",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="AAOI CPO bottleneck inference.",
        summary="AAOI appears in CPO bottleneck methodology, but primary evidence is not yet deep enough.",
        tickers=["AAOI"],
        themes=["CPO", "customer qualification"],
        supply_chain_layer="component",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"bottleneck_scarcity": 8},
        claim_type="inference",
    )
    score = score_research_question([inference])

    memo = generate_memo(query="CPO revenue", ticker="AAOI", evidence=[inference], score=score, language="zh")

    assert "## 行业结构图" in memo
    assert "| 产业链环节 | 证据数量 | Primary/Fact | 风险 | 代表主题 |" in memo
    assert "| component | 1 | 0 | 0 | CPO, customer qualification |" in memo
    assert "## 催化剂时间线" in memo
    assert "| 日期 | 类型 | 标的 | 证据 |" in memo
    assert "## 证据缺口优先级" in memo
    assert "| 优先级 | 缺口 | 影响 | 下一步证据 |" in memo
    assert "| P1 | primary_source_depth |" in memo
    assert "| P2 | demand_validation |" in memo
