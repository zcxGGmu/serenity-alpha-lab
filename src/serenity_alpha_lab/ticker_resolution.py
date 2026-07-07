from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .evidence import EvidenceItem


@dataclass(frozen=True)
class TickerResolutionRule:
    ticker: str
    keywords: Sequence[str]
    theme: str


def load_ticker_resolution_rules(path: Path | str) -> list[TickerResolutionRule]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ticker resolution rules must be a JSON array")

    return [_parse_rule(entry) for entry in payload]


def resolve_evidence_tickers(
    items: Iterable[EvidenceItem],
    rules: Sequence[TickerResolutionRule],
) -> list[EvidenceItem]:
    resolved_items: list[EvidenceItem] = []

    for item in items:
        tickers = list(item.tickers)
        themes = list(item.themes)
        matched = False

        for rule in rules:
            if not _matches_rule(item, rule):
                continue
            matched = True
            if rule.ticker not in tickers:
                tickers.append(rule.ticker)
            if rule.theme not in themes:
                themes.append(rule.theme)

        if not matched:
            resolved_items.append(item)
            continue

        if list(item.tickers) == ["SERENITY"]:
            tickers = [ticker for ticker in tickers if ticker != "SERENITY"]

        resolved_items.append(replace(item, tickers=tickers, themes=themes))

    return resolved_items


def _parse_rule(entry: object) -> TickerResolutionRule:
    if not isinstance(entry, dict):
        raise ValueError("ticker resolution rule entries must be objects")

    ticker = _required_string(entry, "ticker").upper().lstrip("$")
    keywords = [keyword.lower() for keyword in _required_string_list(entry, "keywords")]
    theme = str(entry.get("theme") or f"ticker-resolution:{ticker}").strip()
    if not theme:
        raise ValueError("ticker resolution rule theme must be non-empty")

    return TickerResolutionRule(ticker=ticker, keywords=keywords, theme=theme)


def _matches_rule(item: EvidenceItem, rule: TickerResolutionRule) -> bool:
    text = item.search_text.lower()
    return any(keyword in text for keyword in rule.keywords)


def _required_string(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"ticker resolution rule requires non-empty {key}")
    return value.strip()


def _required_string_list(entry: Mapping[str, object], key: str) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"ticker resolution rule requires non-empty {key}")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"ticker resolution rule {key} must contain non-empty strings")
    return [item.strip() for item in value]
