from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Optional

from .evidence import EvidenceItem, tokenize

QUERY_ALIASES = {
    "存储芯片": ["memory", "storage", "dram", "nand", "hbm", "ai", "infrastructure", "cpo"],
    "存储": ["memory", "storage", "dram", "nand", "hbm"],
    "半导体设备": ["semiconductor", "equipment", "capex", "ai", "infrastructure"],
    "硅光": ["silicon", "photonics", "optical", "cpo"],
}


@dataclass(frozen=True)
class RankedEvidence:
    item: EvidenceItem
    score: float


def retrieve(
    evidence: Iterable[EvidenceItem],
    query: str,
    ticker: Optional[str] = None,
    limit: int = 12,
) -> List[EvidenceItem]:
    query_tokens = _query_tokens(query)
    normalized_ticker = ticker.upper().lstrip("$") if ticker else None
    ranked: List[RankedEvidence] = []

    for item in evidence:
        score = _score_item(item, query_tokens=query_tokens, ticker=normalized_ticker)
        if score > 0:
            ranked.append(RankedEvidence(item=item, score=score))

    ranked.sort(key=lambda ranked_item: (-ranked_item.score, ranked_item.item.published_at, ranked_item.item.id))
    return [ranked_item.item for ranked_item in ranked[:limit]]


def _query_tokens(query: str) -> set[str]:
    tokens = set(tokenize(query))
    lowered = query.lower()
    for trigger, aliases in QUERY_ALIASES.items():
        if trigger in lowered:
            tokens.update(aliases)
    return tokens


def _score_item(item: EvidenceItem, query_tokens: set[str], ticker: Optional[str]) -> float:
    item_tokens = set(tokenize(item.search_text))
    overlap = len(query_tokens & item_tokens)
    theme_overlap = len(query_tokens & set(item.theme_tokens))
    score = overlap * 3 + theme_overlap * 4 + item.confidence * 5
    ticker_match = bool(ticker and ticker in item.tickers)
    relevance_match = bool(overlap or theme_overlap or ticker_match)

    if ticker_match:
        score += 20

    if relevance_match:
        if item.strength == "primary":
            score += 10
        if item.claim_type == "fact":
            score += 8
        if "primary-source" in item.themes:
            score += 4
        if ticker_match and item.strength == "primary":
            score += 8
        if ticker_match and (item.direction == "negative" or item.claim_type in {"risk", "invalidation"}):
            score += 32

    if item.claim_type == "methodology":
        score -= 4

    if item.published_at >= date(2026, 6, 1):
        score += 2

    if item.direction == "negative":
        score += 1

    return score
