from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Iterable, Sequence

from .evidence import EvidenceItem, tokenize
from .stock_universe import StockUniverseEntry, match_universe_candidates


THEME_ALIASES: dict[str, tuple[str, list[str], str]] = {
    "存储芯片": ("memory", ["memory", "storage", "dram", "nand", "hbm", "ai", "infrastructure"], "industry"),
    "存储": ("memory", ["memory", "storage", "dram", "nand", "hbm"], "industry"),
    "memory": ("memory", ["storage", "dram", "nand", "hbm"], "industry"),
    "hbm": ("HBM", ["memory", "dram", "ai", "infrastructure", "bandwidth"], "industry"),
    "半导体设备": ("semiconductor equipment", ["semiconductor", "equipment", "capex", "fab", "ai"], "sector"),
    "硅光": ("silicon photonics", ["silicon", "photonics", "optical", "cpo"], "industry"),
    "cpo": ("CPO", ["co-packaged", "optics", "laser", "optical", "interconnect"], "theme"),
}


@dataclass(frozen=True)
class ResolvedTopic:
    original_query: str
    intent: str
    canonical_theme: str
    aliases: list[str]
    expanded_query: str
    candidate_tickers: list[str]


def resolve_topic(
    query: str,
    evidence: Iterable[EvidenceItem],
    *,
    fallback_tickers: Sequence[str],
    stock_universe: Sequence[StockUniverseEntry] | None = None,
    max_candidates: int = 12,
) -> ResolvedTopic:
    compact_query = " ".join(query.split())
    if not compact_query:
        return ResolvedTopic(
            original_query=query,
            intent="theme",
            canonical_theme="",
            aliases=[],
            expanded_query="",
            candidate_tickers=_dedupe_tickers(fallback_tickers)[:max_candidates],
        )

    items = list(evidence)
    canonical_theme, aliases, intent = _resolve_theme(compact_query)
    ticker = "" if _is_known_theme_query(compact_query) else _ticker_query(compact_query)
    if ticker:
        aliases = _aliases_for_query(compact_query)
        return ResolvedTopic(
            original_query=query,
            intent="ticker",
            canonical_theme=ticker,
            aliases=aliases,
            expanded_query=_expanded_query(ticker, aliases),
            candidate_tickers=_dedupe_tickers([ticker, *fallback_tickers])[:max_candidates],
        )

    candidates = _rank_candidates(items, compact_query, canonical_theme, aliases)
    universe_candidates = match_universe_candidates(
        compact_query,
        canonical_theme=canonical_theme,
        aliases=aliases,
        universe=stock_universe or [],
        limit=max_candidates,
    )
    candidates = _merge_candidates(universe_candidates, candidates)
    if not candidates:
        candidates = _dedupe_tickers(fallback_tickers)

    return ResolvedTopic(
        original_query=query,
        intent=intent,
        canonical_theme=canonical_theme,
        aliases=aliases,
        expanded_query=_expanded_query(compact_query, aliases),
        candidate_tickers=candidates[:max_candidates],
    )


def _ticker_query(query: str) -> str:
    if re.fullmatch(r"\$?[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?", query.strip()):
        return query.upper().lstrip("$")
    return ""


def _resolve_theme(query: str) -> tuple[str, list[str], str]:
    lowered = query.lower()
    for trigger, (canonical, aliases, intent) in THEME_ALIASES.items():
        if trigger.lower() in lowered:
            return canonical, aliases, intent
    return query, _aliases_for_query(query), "theme"


def _is_known_theme_query(query: str) -> bool:
    lowered = query.lower()
    return any(trigger.lower() in lowered for trigger in THEME_ALIASES)


def _aliases_for_query(query: str) -> list[str]:
    lowered = query.lower()
    aliases: list[str] = []
    for trigger, (_, values, _) in THEME_ALIASES.items():
        if trigger.lower() in lowered:
            aliases.extend(values)
    return _dedupe_strings(aliases)


def _rank_candidates(
    evidence: Sequence[EvidenceItem],
    query: str,
    canonical_theme: str,
    aliases: Sequence[str],
) -> list[str]:
    query_tokens = set(tokenize(" ".join([query, canonical_theme, *aliases])))
    ticker_scores: defaultdict[str, float] = defaultdict(float)
    ticker_order: dict[str, int] = {}

    for item_index, item in enumerate(evidence):
        item_tokens = set(tokenize(item.search_text))
        theme_tokens = set(item.theme_tokens)
        overlap = len(query_tokens & item_tokens) + len(query_tokens & theme_tokens)
        if overlap <= 0:
            continue

        source_weight = 2.5 if item.strength == "primary" or item.claim_type == "fact" or "primary-source" in item.themes else 1.0
        risk_weight = 0.5 if item.direction == "negative" or item.claim_type in {"risk", "invalidation"} else 0.0
        score = overlap + source_weight + risk_weight + item.confidence
        for ticker_index, ticker in enumerate(item.tickers):
            normalized = ticker.upper().lstrip("$")
            if normalized == "SERENITY":
                continue
            ticker_order.setdefault(normalized, item_index * 1000 + ticker_index)
            ticker_scores[normalized] += score

    return [
        ticker
        for ticker, _ in sorted(
            ticker_scores.items(),
            key=lambda pair: (-pair[1], ticker_order.get(pair[0], 10_000), pair[0]),
        )
    ]


def _expanded_query(query: str, aliases: Sequence[str]) -> str:
    parts = [query, *_dedupe_strings(aliases)]
    return " ".join(part for part in parts if part)


def _merge_candidates(evidence_candidates: Sequence[str], universe_candidates: Sequence[str]) -> list[str]:
    if not evidence_candidates:
        return _dedupe_tickers(universe_candidates)
    return _dedupe_tickers([*evidence_candidates, *universe_candidates])


def _dedupe_tickers(values: Sequence[str]) -> list[str]:
    return _dedupe_strings([value.upper().lstrip("$") for value in values if value])


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result
