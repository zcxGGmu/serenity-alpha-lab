from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence


VALID_DIRECTIONS = {"positive", "negative", "neutral"}
VALID_STRENGTHS = {"primary", "derived", "speculative"}
VALID_CLAIM_TYPES = {"fact", "methodology", "inference", "risk", "catalyst", "invalidation"}
REQUIRED_FIELDS = {
    "id",
    "source_title",
    "source_url",
    "published_at",
    "claim",
    "summary",
    "tickers",
    "themes",
    "supply_chain_layer",
    "direction",
    "strength",
    "confidence",
    "factor_impacts",
}


class EvidenceValidationError(ValueError):
    """Raised when an evidence record is malformed."""


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    source_title: str
    source_url: str
    published_at: date
    claim: str
    summary: str
    tickers: Sequence[str]
    themes: Sequence[str]
    supply_chain_layer: str
    direction: str
    strength: str
    confidence: float
    factor_impacts: Mapping[str, int]
    claim_type: str = "inference"
    source_excerpt: str = ""

    @property
    def theme_tokens(self) -> List[str]:
        tokens: List[str] = []
        for theme in self.themes:
            tokens.extend(tokenize(theme))
        return sorted(set(tokens))

    @property
    def search_text(self) -> str:
        return " ".join(
            [
                self.claim,
                self.summary,
                self.source_title,
                self.supply_chain_layer,
                " ".join(self.tickers),
                " ".join(self.themes),
            ]
        )


def tokenize(text: str) -> List[str]:
    return [part.lower() for part in re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]+", text)]


def load_evidence(path: Path | str) -> List[EvidenceItem]:
    evidence_path = Path(path)
    items: List[EvidenceItem] = []
    with evidence_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise EvidenceValidationError(f"line {line_number}: invalid JSON: {exc}") from exc
            items.append(parse_evidence_item(payload, line_number=line_number))
    return items


def load_evidence_files(paths: Sequence[Path | str]) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    seen_ids = set()
    for path in paths:
        for item in load_evidence(path):
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            items.append(item)
    return items


def parse_evidence_item(payload: Mapping[str, object], line_number: int = 0) -> EvidenceItem:
    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        location = f"line {line_number}: " if line_number else ""
        raise EvidenceValidationError(f"{location}missing required fields: {', '.join(missing)}")

    direction = _string(payload, "direction")
    if direction not in VALID_DIRECTIONS:
        raise EvidenceValidationError(f"direction must be one of {sorted(VALID_DIRECTIONS)}")

    strength = _string(payload, "strength")
    if strength not in VALID_STRENGTHS:
        raise EvidenceValidationError(f"strength must be one of {sorted(VALID_STRENGTHS)}")

    confidence = float(payload["confidence"])
    if confidence < 0 or confidence > 1:
        raise EvidenceValidationError("confidence must be between 0 and 1")

    factor_impacts_raw = payload["factor_impacts"]
    if not isinstance(factor_impacts_raw, dict) or not factor_impacts_raw:
        raise EvidenceValidationError("factor_impacts must be a non-empty object")

    factor_impacts: Dict[str, int] = {}
    for factor, value in factor_impacts_raw.items():
        factor_impacts[str(factor)] = int(value)

    claim_type = str(payload.get("claim_type") or _infer_claim_type_from_payload(payload, direction, strength)).strip()
    if claim_type not in VALID_CLAIM_TYPES:
        raise EvidenceValidationError(f"claim_type must be one of {sorted(VALID_CLAIM_TYPES)}")

    source_excerpt = str(payload.get("source_excerpt") or "").strip()

    return EvidenceItem(
        id=_string(payload, "id"),
        source_title=_string(payload, "source_title"),
        source_url=_string(payload, "source_url"),
        published_at=date.fromisoformat(_string(payload, "published_at")),
        claim=_string(payload, "claim"),
        summary=_string(payload, "summary"),
        tickers=_normalize_tickers(_list(payload, "tickers")),
        themes=_normalize_strings(_list(payload, "themes")),
        supply_chain_layer=_string(payload, "supply_chain_layer"),
        direction=direction,
        strength=strength,
        confidence=confidence,
        factor_impacts=factor_impacts,
        claim_type=claim_type,
        source_excerpt=source_excerpt,
    )


def write_evidence_jsonl(items: Iterable[EvidenceItem], path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in items:
            payload = {
                "claim_type": item.claim_type,
                "id": item.id,
                "source_title": item.source_title,
                "source_url": item.source_url,
                "published_at": item.published_at.isoformat(),
                "claim": item.claim,
                "summary": item.summary,
                "tickers": list(item.tickers),
                "themes": list(item.themes),
                "supply_chain_layer": item.supply_chain_layer,
                "direction": item.direction,
                "strength": item.strength,
                "confidence": item.confidence,
                "factor_impacts": dict(item.factor_impacts),
            }
            if item.source_excerpt:
                payload["source_excerpt"] = item.source_excerpt
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def evidence_claim_key(item: EvidenceItem) -> str:
    normalized_claim = _normalize_claim_text(item.summary or item.claim)
    normalized_tickers = ",".join(sorted(item.tickers))
    normalized_themes = ",".join(sorted(theme.lower() for theme in item.themes))
    return f"{normalized_claim}|{normalized_tickers}|{normalized_themes}|{item.claim_type}"


def dedupe_evidence(items: Iterable[EvidenceItem]) -> List[EvidenceItem]:
    deduped: List[EvidenceItem] = []
    seen_ids = set()
    seen_claims = set()

    for item in items:
        claim_key = evidence_claim_key(item)
        if item.id in seen_ids or claim_key in seen_claims:
            continue
        seen_ids.add(item.id)
        seen_claims.add(claim_key)
        deduped.append(item)
    return deduped


def _normalize_claim_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\b(the|a|an|is|are|as|in|of|to|and|or|with)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _infer_claim_type_from_payload(payload: Mapping[str, object], direction: str, strength: str) -> str:
    text = " ".join(
        str(payload.get(key, ""))
        for key in ["claim", "summary", "source_title", "supply_chain_layer"]
    ).lower()
    if direction == "negative":
        if "invalidation" in text or "失效" in text:
            return "invalidation"
        return "risk"
    if "methodology" in text or "skill" in text or "prompt" in text or "方法论" in text:
        return "methodology"
    if "catalyst" in text or "催化" in text:
        return "catalyst"
    if strength == "primary":
        return "fact"
    return "inference"


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _list(payload: Mapping[str, object], key: str) -> List[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise EvidenceValidationError(f"{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise EvidenceValidationError(f"{key} must contain non-empty strings")
    return [item.strip() for item in value]


def _normalize_tickers(values: Sequence[str]) -> List[str]:
    return [value.upper().lstrip("$") for value in values]


def _normalize_strings(values: Sequence[str]) -> List[str]:
    return [value.strip() for value in values]
