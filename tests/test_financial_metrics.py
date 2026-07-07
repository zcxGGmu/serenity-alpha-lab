from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.financial_metrics import build_metrics_catalog, render_metrics_catalog_json


def _evidence(
    *,
    ticker: str = "SIVE",
    claim: str,
    summary: str,
    themes: list[str],
    direction: str = "neutral",
    source_title: str = "Primary source",
    published_at: str = "2026-02-28",
) -> EvidenceItem:
    return EvidenceItem(
        id=f"test:{ticker}:{len(claim)}",
        source_title=source_title,
        source_url="https://example.com/source",
        published_at=date.fromisoformat(published_at),
        claim=claim,
        summary=summary,
        tickers=[ticker],
        themes=themes,
        supply_chain_layer="company financials",
        direction=direction,
        strength="primary",
        confidence=0.9,
        factor_impacts={"evidence_quality": 20},
        claim_type="fact",
    )


def test_build_metrics_catalog_derives_source_backed_revenue_growth_and_profitability():
    catalog = build_metrics_catalog(
        [
            _evidence(
                claim="SEC companyfacts reports Revenue for SIVE FY2025: $420,000,000.",
                summary="Primary SEC companyfacts data shows SIVE FY2025 Revenue of $420,000,000.",
                themes=["SEC companyfacts", "primary-source", "revenue"],
            ),
            _evidence(
                claim="SEC companyfacts reports Net Income (Loss) for SIVE FY2025: $-15,000,000.",
                summary="Primary SEC companyfacts data shows SIVE FY2025 Net Income (Loss) of $-15,000,000. The value is a reported loss.",
                themes=["SEC companyfacts", "primary-source", "profitability"],
                direction="negative",
            ),
            _evidence(
                claim="Sivers Semiconductors reported 2025 net sales of SEK 306.6 million, up 40% year over year.",
                summary="Official annual-report evidence shows SIVE 2025 net sales increased to SEK 306.6 million from SEK 219.2 million.",
                themes=["annual-report", "primary-source", "revenue", "CPO"],
                direction="positive",
                source_title="Sivers Annual Report",
            ),
        ]
    )

    assert catalog[0]["ticker"] == "SIVE"
    assert catalog[0]["revenue_growth"] == "40% YoY official report"
    assert catalog[0]["gross_margin"] == "n/a"
    assert catalog[0]["valuation"] == "n/a"
    assert catalog[0]["momentum"] == "reported loss"
    assert catalog[0]["cycle_position"] == "revenue ramp / loss-making"


def test_render_metrics_catalog_json_is_stable_and_ui_compatible():
    catalog = build_metrics_catalog(
        [
            _evidence(
                ticker="AAOI",
                claim="SEC companyfacts reports Revenue for AAOI FY2025: $455,715,000.",
                summary="Primary SEC companyfacts data shows AAOI FY2025 Revenue of $455,715,000.",
                themes=["SEC companyfacts", "primary-source", "revenue"],
            )
        ]
    )

    text = render_metrics_catalog_json(catalog)

    assert '"ticker": "AAOI"' in text
    assert '"revenue_growth": "source-backed revenue $455.7M"' in text
    assert text.endswith("\n")


def test_build_metrics_catalog_does_not_treat_positive_net_income_label_as_loss():
    catalog = build_metrics_catalog(
        [
            _evidence(
                ticker="NVDA",
                claim="SEC companyfacts reports Revenues for NVDA FY2026: $215,938,000,000.",
                summary="Primary SEC companyfacts data shows NVDA FY2026 Revenues of $215,938,000,000.",
                themes=["SEC companyfacts", "primary-source", "revenue"],
            ),
            _evidence(
                ticker="NVDA",
                claim="SEC companyfacts reports Net Income (Loss) for NVDA FY2026: $120,067,000,000.",
                summary="Primary SEC companyfacts data shows NVDA FY2026 Net Income (Loss) of $120,067,000,000.",
                themes=["SEC companyfacts", "primary-source", "profitability"],
            ),
        ]
    )

    assert catalog[0]["ticker"] == "NVDA"
    assert catalog[0]["momentum"] == "reported profitable"
    assert catalog[0]["cycle_position"] == "source-backed revenue base"
