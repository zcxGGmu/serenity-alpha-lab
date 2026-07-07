from __future__ import annotations

from dataclasses import replace
import re
from typing import Iterable

from .evidence import EvidenceItem
from .evidence_audit import is_weak_summary


ENRICHED_THEME = "summary-enriched"


def enrich_evidence_summaries(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    enriched_items: list[EvidenceItem] = []

    for item in items:
        if not is_weak_summary(item.summary):
            enriched_items.append(item)
            continue

        themes = list(item.themes)
        if ENRICHED_THEME not in themes:
            themes.append(ENRICHED_THEME)
        enriched_items.append(replace(item, summary=build_enriched_summary(item), themes=themes))

    return enriched_items


def build_enriched_summary(item: EvidenceItem) -> str:
    claim_context = _clean_text(item.claim)
    if ":" in claim_context:
        heading, detail = claim_context.split(":", 1)
        claim_context = f"{heading.strip()}: {detail.strip()}"

    parts = [claim_context]
    if item.tickers:
        parts.append(f"Tickers: {', '.join(item.tickers)}.")
    if item.themes:
        parts.append(f"Themes: {', '.join(item.themes[:4])}.")
    parts.append(f"Source: {item.source_title}.")
    return _truncate(" ".join(part for part in parts if part), 360)


def _clean_text(text: str) -> str:
    text = re.sub(r"`+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
