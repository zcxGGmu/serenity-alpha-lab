from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlparse

from .evidence import EvidenceItem, parse_evidence_item, write_evidence_jsonl


PLACEHOLDER_HOSTS = {
    "example.com",
    "example.net",
    "example.org",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}
PLACEHOLDER_SUFFIXES = (".example", ".invalid", ".localhost", ".test")
MIN_SOURCE_EXCERPT_CHARS = 24


def validate_source_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("source URL must use http or https")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("source URL must include a hostname")
    if hostname in PLACEHOLDER_HOSTS or hostname.endswith(PLACEHOLDER_SUFFIXES):
        raise ValueError(f"placeholder source URL is not allowed: {source_url}")


def validate_source_excerpt(source_excerpt: str) -> None:
    normalized = " ".join(source_excerpt.split())
    if len(normalized) < MIN_SOURCE_EXCERPT_CHARS:
        raise ValueError(
            f"source excerpt must explain how the source supports the claim "
            f"with at least {MIN_SOURCE_EXCERPT_CHARS} non-whitespace characters"
        )


def parse_factor_impacts(values: Sequence[str]) -> dict[str, int]:
    impacts: dict[str, int] = {}
    for raw_value in values:
        if "=" not in raw_value:
            raise ValueError(f"factor impact must use key=value format: {raw_value}")
        key, value = raw_value.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError(f"factor impact key cannot be empty: {raw_value}")
        impacts[normalized_key] = int(value.strip())
    if not impacts:
        raise ValueError("at least one factor impact is required")
    return impacts


def build_intake_evidence(
    *,
    item_id: str,
    source_title: str,
    source_url: str,
    published_at: str,
    claim: str,
    summary: str,
    tickers: Sequence[str],
    themes: Sequence[str],
    supply_chain_layer: str,
    direction: str,
    strength: str,
    confidence: float,
    factor_impacts: Mapping[str, int],
    claim_type: str,
    source_excerpt: str,
) -> EvidenceItem:
    validate_source_url(source_url)
    validate_source_excerpt(source_excerpt)
    payload = {
        "id": item_id,
        "source_title": source_title,
        "source_url": source_url,
        "published_at": date.fromisoformat(published_at).isoformat(),
        "claim": claim,
        "summary": summary,
        "tickers": list(tickers),
        "themes": list(themes),
        "supply_chain_layer": supply_chain_layer,
        "direction": direction,
        "strength": strength,
        "confidence": confidence,
        "factor_impacts": dict(factor_impacts),
        "claim_type": claim_type,
        "source_excerpt": " ".join(source_excerpt.split()),
    }
    return parse_evidence_item(payload)


def append_intake_evidence(item: EvidenceItem, path: Path | str) -> None:
    output_path = Path(path)
    existing: list[EvidenceItem] = []
    if output_path.exists():
        from .evidence import load_evidence

        existing = load_evidence(output_path)
    write_evidence_jsonl([*existing, item], output_path)
