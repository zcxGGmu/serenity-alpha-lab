from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .evidence import EvidenceItem


FACTOR_NAMES = [
    "bottleneck_scarcity",
    "demand_certainty",
    "supply_elasticity",
    "evidence_quality",
    "crowding_risk",
    "invalidation_clarity",
]

FACTOR_WEIGHTS = {
    "bottleneck_scarcity": 0.24,
    "demand_certainty": 0.22,
    "supply_elasticity": 0.16,
    "evidence_quality": 0.16,
    "crowding_risk": -0.12,
    "invalidation_clarity": 0.10,
}

CLAIM_TYPE_WEIGHTS = {
    "fact": 1.0,
    "catalyst": 0.9,
    "inference": 0.75,
    "methodology": 0.25,
    "risk": 0.35,
    "invalidation": 0.3,
}

RISK_FACTOR_WEIGHTS = {
    "risk": {
        "crowding_risk": 1.0,
        "invalidation_clarity": 0.8,
    },
    "invalidation": {
        "crowding_risk": 0.9,
        "invalidation_clarity": 0.9,
    },
}


@dataclass(frozen=True)
class FactorScore:
    name: str
    value: int
    weighted_value: float
    evidence_ids: List[str]
    penalty: bool = False


@dataclass(frozen=True)
class ResearchScore:
    total: int
    factors: Dict[str, FactorScore]
    evidence_count: int


@dataclass(frozen=True)
class ScorecardSummary:
    rating: str
    confidence: str
    gaps: List[str]
    zh_rating: str
    zh_confidence: str
    zh_gaps: List[str]


def score_research_question(evidence: Iterable[EvidenceItem]) -> ResearchScore:
    items = list(evidence)
    if not items:
        return ResearchScore(
            total=0,
            evidence_count=0,
            factors={
                name: FactorScore(name=name, value=0, weighted_value=0.0, evidence_ids=[], penalty=name == "crowding_risk")
                for name in FACTOR_NAMES
            },
        )

    factors: Dict[str, FactorScore] = {}
    total = 0.0

    for name in FACTOR_NAMES:
        value, evidence_ids = _factor_value(name, items)
        penalty = name == "crowding_risk"
        weighted_value = value * FACTOR_WEIGHTS[name]
        total += weighted_value
        factors[name] = FactorScore(
            name=name,
            value=value,
            weighted_value=weighted_value,
            evidence_ids=evidence_ids,
            penalty=penalty,
        )

    primary_or_derived = [item for item in items if item.strength in {"primary", "derived"}]
    speculative_count = len([item for item in items if item.strength == "speculative"])
    if not primary_or_derived and speculative_count:
        total -= 12
    if speculative_count > len(primary_or_derived) + 1:
        total -= 6

    normalized_total = max(0, min(100, round(total)))
    return ResearchScore(total=normalized_total, factors=factors, evidence_count=len(items))


def summarize_scorecard(score: ResearchScore) -> ScorecardSummary:
    gaps = _scorecard_gaps(score)
    if score.evidence_count == 0:
        rating = "Insufficient Evidence"
        confidence = "low"
    elif score.total >= 70 and not gaps:
        rating = "High-Conviction Research Candidate"
        confidence = "high"
    elif score.total >= 45 and "primary_source_depth" not in gaps:
        rating = "Review Candidate"
        confidence = "medium"
    else:
        rating = "Watchlist Candidate"
        confidence = "low"

    return ScorecardSummary(
        rating=rating,
        confidence=confidence,
        gaps=gaps,
        zh_rating=_zh_rating(rating),
        zh_confidence={"high": "高", "medium": "中", "low": "低"}[confidence],
        zh_gaps=[_zh_gap(gap) for gap in gaps],
    )


def _scorecard_gaps(score: ResearchScore) -> List[str]:
    if score.evidence_count == 0:
        return ["no_evidence"]

    gaps: List[str] = []
    if score.total < 45:
        gaps.append("low_score")
    if score.factors["evidence_quality"].value < 20:
        gaps.append("primary_source_depth")
    if score.factors["demand_certainty"].value < 15:
        gaps.append("demand_validation")
    if score.factors["invalidation_clarity"].value < 10:
        gaps.append("invalidation_plan")
    if score.factors["crowding_risk"].value >= 35:
        gaps.append("crowding_risk")
    return gaps or ["none"]


def _zh_rating(rating: str) -> str:
    return {
        "Insufficient Evidence": "证据不足",
        "Watchlist Candidate": "观察池候选",
        "Review Candidate": "复核候选",
        "High-Conviction Research Candidate": "高置信研究候选",
    }.get(rating, rating)


def _zh_gap(gap: str) -> str:
    return {
        "no_evidence": "缺少证据",
        "low_score": "综合评分偏低",
        "primary_source_depth": "primary source 深度不足",
        "demand_validation": "需求验证不足",
        "invalidation_plan": "失效条件不够清晰",
        "crowding_risk": "拥挤风险偏高",
        "none": "无主要短板",
    }.get(gap, gap)


def _factor_value(name: str, items: List[EvidenceItem]) -> tuple[int, List[str]]:
    raw_value = 0.0
    evidence_ids: List[str] = []

    for item in items:
        impact = item.factor_impacts.get(name)
        if impact is None:
            continue

        confidence_adjusted = impact * item.confidence
        confidence_adjusted *= _claim_type_weight(item.claim_type, name)
        if item.direction == "negative" and name != "crowding_risk":
            confidence_adjusted *= -0.5
        elif item.direction == "negative" and name == "crowding_risk":
            confidence_adjusted *= 1.25
        elif item.direction == "neutral":
            confidence_adjusted *= 0.5

        raw_value += confidence_adjusted
        evidence_ids.append(item.id)

    capped_value = max(0, min(100, round(raw_value)))
    return capped_value, evidence_ids


def _claim_type_weight(claim_type: str, factor_name: str) -> float:
    if claim_type in RISK_FACTOR_WEIGHTS:
        return RISK_FACTOR_WEIGHTS[claim_type].get(factor_name, CLAIM_TYPE_WEIGHTS[claim_type])
    return CLAIM_TYPE_WEIGHTS.get(claim_type, 0.6)
