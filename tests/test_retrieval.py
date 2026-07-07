from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.retrieval import retrieve


def make_item(
    item_id,
    *,
    claim="Generic claim",
    summary="Generic summary",
    tickers=("AAOI",),
    themes=("CPO",),
    strength="derived",
    claim_type="inference",
    confidence=0.7,
    direction="neutral",
    published_at=date(2026, 1, 1),
):
    return EvidenceItem(
        id=item_id,
        source_title="Source",
        source_url="https://example.com",
        published_at=published_at,
        claim=claim,
        summary=summary,
        tickers=tickers,
        themes=themes,
        supply_chain_layer="company financials" if strength == "primary" else "methodology",
        direction=direction,
        strength=strength,
        confidence=confidence,
        factor_impacts={"evidence_quality": 1},
        claim_type=claim_type,
    )


def test_retrieve_ranks_focus_ticker_primary_fact_above_methodology():
    primary_fact = make_item(
        "primary-aaoi-revenue",
        claim="SEC companyfacts reports Revenue for AAOI FY2025.",
        summary="Primary SEC companyfacts data shows AAOI revenue.",
        themes=("SEC companyfacts", "primary-source", "revenue"),
        strength="primary",
        claim_type="fact",
        confidence=0.88,
    )
    methodology = make_item(
        "methodology-aaoi-cpo",
        claim="CPO laser bottleneck methodology for AAOI.",
        summary="Serenity methodology maps AAOI through CPO bottleneck analysis.",
        themes=("CPO", "laser", "supply-chain bottleneck"),
        strength="derived",
        claim_type="methodology",
        confidence=0.9,
    )

    results = retrieve([methodology, primary_fact], query="CPO laser bottleneck", ticker="AAOI", limit=2)

    assert [item.id for item in results] == ["primary-aaoi-revenue", "methodology-aaoi-cpo"]


def test_retrieve_does_not_let_unrelated_primary_fact_beat_focus_evidence():
    unrelated_primary = make_item(
        "primary-nvda-revenue",
        claim="SEC companyfacts reports Revenue for NVDA FY2026.",
        summary="Primary SEC companyfacts data shows NVDA revenue.",
        tickers=("NVDA",),
        themes=("SEC companyfacts", "primary-source", "revenue"),
        strength="primary",
        claim_type="fact",
        confidence=0.88,
    )
    focus_inference = make_item(
        "aaoi-cpo-inference",
        claim="AAOI appears in CPO laser bottleneck work.",
        summary="AAOI has direct CPO laser bottleneck relevance.",
        themes=("CPO", "laser"),
        strength="derived",
        claim_type="inference",
        confidence=0.7,
    )

    results = retrieve([unrelated_primary, focus_inference], query="CPO laser bottleneck", ticker="AAOI", limit=1)

    assert results[0].id == "aaoi-cpo-inference"


def test_retrieve_includes_recent_focus_ticker_risk_intake_with_primary_facts():
    evidence = [
        make_item(
            f"primary-nvda-{index}",
            claim=f"SEC companyfacts reports NVDA fact {index}.",
            summary=f"Primary SEC companyfacts data shows NVDA fact {index}.",
            tickers=("NVDA",),
            themes=("SEC companyfacts", "primary-source", "revenue"),
            strength="primary",
            claim_type="fact",
            confidence=0.88,
        )
        for index in range(18)
    ]
    risk_intake = make_item(
        "manual:nvda:risk:cpo-sourcing",
        claim="NVDA faces CPO sourcing risk if optical component supply tightens.",
        summary="Manual intake captures a negative risk item for NVDA CPO sourcing.",
        tickers=("NVDA",),
        themes=("CPO", "risk", "manual-intake"),
        strength="derived",
        claim_type="risk",
        confidence=0.72,
        direction="negative",
        published_at=date(2026, 7, 4),
    )

    results = retrieve(
        [*evidence, risk_intake],
        query="CPO laser bottleneck revenue profitability",
        ticker="NVDA",
        limit=16,
    )

    assert "manual:nvda:risk:cpo-sourcing" in [item.id for item in results]


def test_retrieve_expands_chinese_industry_theme_aliases():
    primary_fact = make_item(
        "primary-sive-cpo",
        claim="SIVE annual report discusses co-packaged optics opportunity expansion.",
        summary="Primary annual-report evidence links SIVE to CPO and optical interconnect opportunities.",
        tickers=("SIVE",),
        themes=("annual-report", "primary-source", "CPO", "photonics"),
        strength="primary",
        claim_type="fact",
        confidence=0.88,
    )
    risk = make_item(
        "risk-sive-cpo",
        claim="SIVE CPO thesis can be invalidated if qualification stalls.",
        summary="Customer qualification timing remains a risk for the SIVE CPO path.",
        tickers=("SIVE",),
        themes=("CPO", "risk"),
        direction="negative",
        claim_type="risk",
        confidence=0.72,
    )

    results = retrieve([primary_fact, risk], query="存储芯片", ticker="SIVE", limit=8)

    assert [item.id for item in results] == ["risk-sive-cpo", "primary-sive-cpo"]
