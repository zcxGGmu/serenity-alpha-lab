from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.ticker_resolution import load_ticker_resolution_rules, resolve_evidence_tickers


def make_item(
    item_id,
    *,
    claim="CPO silicon photonics creates a bottleneck.",
    summary="Silicon photonics and CPO constraints affect the supply chain.",
    tickers=("SERENITY",),
    themes=("CPO",),
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
        supply_chain_layer="component",
        direction="positive",
        strength="derived",
        confidence=0.7,
        factor_impacts={"demand_certainty": 1},
        claim_type="inference",
    )


def test_load_ticker_resolution_rules_normalizes_tickers_and_keywords():
    rules = load_ticker_resolution_rules("tests/fixtures/ticker_rules.json")

    assert rules[0].ticker == "SIVE"
    assert "silicon photonics" in rules[0].keywords
    assert rules[0].theme == "ticker-resolution:SIVE"


def test_resolve_evidence_tickers_adds_matched_tickers_and_trace_theme():
    rules = load_ticker_resolution_rules("tests/fixtures/ticker_rules.json")

    resolved = resolve_evidence_tickers([make_item("a")], rules)

    assert resolved[0].tickers == ["SIVE"]
    assert "ticker-resolution:SIVE" in resolved[0].themes


def test_resolve_evidence_tickers_preserves_existing_tickers_without_duplicates():
    rules = load_ticker_resolution_rules("tests/fixtures/ticker_rules.json")

    resolved = resolve_evidence_tickers([make_item("a", tickers=("SERENITY", "SIVE"))], rules)

    assert resolved[0].tickers == ["SERENITY", "SIVE"]
    assert resolved[0].themes.count("ticker-resolution:SIVE") == 1


def test_resolve_evidence_tickers_removes_placeholder_only_when_rule_matches():
    rules = load_ticker_resolution_rules("tests/fixtures/ticker_rules.json")
    matched = make_item("matched")
    unmatched = make_item("unmatched", claim="General method.", summary="No company linkage.", themes=("methodology",))

    resolved = resolve_evidence_tickers([matched, unmatched], rules)

    assert resolved[0].tickers == ["SIVE"]
    assert list(resolved[1].tickers) == ["SERENITY"]


def test_resolve_evidence_tickers_leaves_unmatched_evidence_unchanged():
    rules = load_ticker_resolution_rules("tests/fixtures/ticker_rules.json")
    original = make_item("a", claim="General method.", summary="No company linkage.", themes=("methodology",))

    resolved = resolve_evidence_tickers([original], rules)

    assert resolved[0] == original
