from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Sequence

from .evidence import tokenize


@dataclass(frozen=True)
class StockUniverseEntry:
    ticker: str
    name: str
    market: str
    sector: str
    themes: list[str]
    aliases: list[str]


def load_stock_universe(path: Path | str) -> list[StockUniverseEntry]:
    universe_path = Path(path)
    if not universe_path.exists():
        return []

    payload = json.loads(universe_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("stock universe must be a JSON list")

    return [_parse_entry(entry) for entry in payload]


def match_universe_candidates(
    query: str,
    *,
    canonical_theme: str,
    aliases: Sequence[str],
    universe: Iterable[StockUniverseEntry],
    limit: int = 12,
) -> list[str]:
    query_tokens = set(tokenize(" ".join([query, canonical_theme, *aliases])))
    scored: list[tuple[float, int, str]] = []

    for index, entry in enumerate(universe):
        theme_tokens = set(tokenize(" ".join(entry.themes)))
        alias_tokens = set(tokenize(" ".join(entry.aliases)))
        descriptor_tokens = set(tokenize(" ".join([entry.name, entry.market, entry.sector])))

        theme_overlap = len(query_tokens & theme_tokens)
        alias_overlap = len(query_tokens & alias_tokens)
        descriptor_overlap = len(query_tokens & descriptor_tokens)
        exact_alias = any(query.lower() == alias.lower() for alias in entry.aliases)
        exact_theme = any(canonical_theme.lower() == theme.lower() for theme in entry.themes)

        score = theme_overlap * 5 + alias_overlap * 3 + descriptor_overlap
        if exact_theme:
            score += 8
        if exact_alias:
            score += 4
        if score <= 0:
            continue
        scored.append((score, index, entry.ticker))

    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    return _dedupe([ticker for _, _, ticker in scored])[:limit]


def _parse_entry(entry: object) -> StockUniverseEntry:
    if not isinstance(entry, dict):
        raise ValueError("stock universe entries must be objects")
    ticker = _required_string(entry, "ticker").upper().lstrip("$")
    return StockUniverseEntry(
        ticker=ticker,
        name=_required_string(entry, "name"),
        market=_required_string(entry, "market").upper(),
        sector=_required_string(entry, "sector"),
        themes=_string_list(entry, "themes"),
        aliases=_string_list(entry, "aliases"),
    )


def _required_string(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"stock universe entry {key} must be a non-empty string")
    return value.strip()


def _string_list(entry: dict[str, object], key: str) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"stock universe entry {key} must be a non-empty list")
    return _dedupe([str(item).strip() for item in value if str(item).strip()])


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
