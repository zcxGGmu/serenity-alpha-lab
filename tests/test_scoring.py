from pathlib import Path
from dataclasses import replace
from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.evidence import load_evidence
from serenity_alpha_lab.retrieval import retrieve
from serenity_alpha_lab.scoring import score_research_question, summarize_scorecard


FIXTURE = Path(__file__).parent / "fixtures" / "evidence.jsonl"


def test_scoring_returns_factor_breakdown_and_penalizes_crowding():
    evidence = retrieve(load_evidence(FIXTURE), query="CPO laser bottleneck", ticker="SIVE")
    score = score_research_question(evidence)

    assert 0 < score.total <= 100
    assert score.factors["crowding_risk"].penalty is True
    assert score.factors["bottleneck_scarcity"].value > 0
    assert score.factors["crowding_risk"].weighted_value < 0
    assert "ev-crowding-risk-001" in score.factors["crowding_risk"].evidence_ids


def test_scoring_requires_evidence_for_nonzero_score():
    score = score_research_question([])

    assert score.total == 0
    assert all(factor.value == 0 for factor in score.factors.values())


def test_methodology_claims_have_lower_score_weight_than_inference_claims():
    item = EvidenceItem(
        id="claim-type-weight-sample",
        source_title="Sample source",
        source_url="https://example.com/sample",
        published_at=date(2026, 1, 1),
        claim="CPO laser bottleneck creates scarce optical supply.",
        summary="Sample evidence with direct bottleneck scarcity impact.",
        tickers=["SIVE"],
        themes=["CPO", "laser", "bottleneck"],
        supply_chain_layer="optical components",
        direction="positive",
        strength="derived",
        confidence=0.8,
        factor_impacts={"bottleneck_scarcity": 20},
        claim_type="inference",
    )
    inference_score = score_research_question([replace(item, claim_type="inference")])
    methodology_score = score_research_question([replace(item, claim_type="methodology")])

    assert methodology_score.factors["bottleneck_scarcity"].value < inference_score.factors["bottleneck_scarcity"].value
    assert methodology_score.total < inference_score.total


def test_scorecard_summary_explains_rating_confidence_and_key_gaps():
    score = score_research_question([])

    summary = summarize_scorecard(score)

    assert summary.rating == "Insufficient Evidence"
    assert summary.confidence == "low"
    assert "no_evidence" in summary.gaps
    assert summary.zh_rating == "证据不足"
    assert summary.zh_confidence == "低"
