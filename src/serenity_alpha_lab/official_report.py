from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from .evidence import EvidenceItem


@dataclass(frozen=True)
class OfficialReportFactSpec:
    id: str
    claim: str
    summary: str
    source_excerpt: str
    themes: Sequence[str]
    supply_chain_layer: str
    direction: str
    factor_impacts: Mapping[str, int]


@dataclass(frozen=True)
class OfficialReportSourceSpec:
    ticker: str
    source_title: str
    source_url: str
    published_at: str
    text_path: Path
    facts: Sequence[OfficialReportFactSpec]


def load_official_report_specs(path: Path | str) -> list[OfficialReportSourceSpec]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("official report source manifest must be a JSON array")
    return [_parse_source_spec(entry, base_dir=manifest_path.parent) for entry in payload]


def official_report_specs_to_evidence(specs: Sequence[OfficialReportSourceSpec]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for spec in specs:
        report_text = _normalize_text(spec.text_path.read_text(encoding="utf-8"))
        for fact in spec.facts:
            normalized_excerpt = _normalize_text(fact.source_excerpt)
            if normalized_excerpt not in report_text:
                raise ValueError(
                    f"source excerpt for {spec.ticker} fact {fact.id} was not found in {spec.text_path}"
                )
            items.append(_fact_to_evidence(spec, fact))
    return items


def _parse_source_spec(entry: object, *, base_dir: Path) -> OfficialReportSourceSpec:
    if not isinstance(entry, dict):
        raise ValueError("official report manifest entries must be objects")
    raw_text_path = Path(_required_string(entry, "text_path"))
    text_path = raw_text_path if raw_text_path.is_absolute() else base_dir / raw_text_path
    facts_payload = entry.get("facts")
    if not isinstance(facts_payload, list) or not facts_payload:
        raise ValueError("official report manifest entry requires non-empty facts")
    return OfficialReportSourceSpec(
        ticker=_required_string(entry, "ticker").upper().lstrip("$"),
        source_title=_required_string(entry, "source_title"),
        source_url=_required_string(entry, "source_url"),
        published_at=date.fromisoformat(_required_string(entry, "published_at")).isoformat(),
        text_path=text_path,
        facts=[_parse_fact_spec(fact) for fact in facts_payload],
    )


def _parse_fact_spec(entry: object) -> OfficialReportFactSpec:
    if not isinstance(entry, dict):
        raise ValueError("official report fact entries must be objects")
    factor_impacts_raw = entry.get("factor_impacts")
    if not isinstance(factor_impacts_raw, dict) or not factor_impacts_raw:
        raise ValueError("official report fact requires non-empty factor_impacts")
    return OfficialReportFactSpec(
        id=_required_string(entry, "id"),
        claim=_required_string(entry, "claim"),
        summary=_required_string(entry, "summary"),
        source_excerpt=_required_string(entry, "source_excerpt"),
        themes=tuple(_required_string_list(entry, "themes")),
        supply_chain_layer=_required_string(entry, "supply_chain_layer"),
        direction=_required_string(entry, "direction"),
        factor_impacts={str(key): int(value) for key, value in factor_impacts_raw.items()},
    )


def _fact_to_evidence(spec: OfficialReportSourceSpec, fact: OfficialReportFactSpec) -> EvidenceItem:
    return EvidenceItem(
        id=f"official-report:{spec.ticker}:{fact.id}",
        source_title=spec.source_title,
        source_url=spec.source_url,
        published_at=date.fromisoformat(spec.published_at),
        claim=fact.claim,
        summary=fact.summary,
        tickers=[spec.ticker],
        themes=list(fact.themes),
        supply_chain_layer=fact.supply_chain_layer,
        direction=fact.direction,
        strength="primary",
        confidence=0.9,
        factor_impacts=dict(fact.factor_impacts),
        claim_type="fact",
        source_excerpt=" ".join(fact.source_excerpt.split()),
    )


def _required_string(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"official report manifest entry requires non-empty {key}")
    return value.strip()


def _required_string_list(entry: Mapping[str, object], key: str) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"official report manifest entry requires non-empty {key}")
    strings = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"official report manifest {key} entries must be non-empty strings")
        strings.append(item.strip())
    return strings


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
