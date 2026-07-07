from pathlib import Path

import pytest

from serenity_alpha_lab.evidence import (
    EvidenceItem,
    EvidenceValidationError,
    dedupe_evidence,
    evidence_claim_key,
    load_evidence,
    write_evidence_jsonl,
)


FIXTURE = Path(__file__).parent / "fixtures" / "evidence.jsonl"


def test_load_evidence_normalizes_tickers_and_themes():
    items = load_evidence(FIXTURE)

    assert len(items) == 4
    assert items[0].tickers[0] == "SIVE"
    assert "cpo" in items[0].theme_tokens
    assert items[0].factor_impacts["demand_certainty"] == 18
    assert items[0].claim_type == "inference"


def test_load_evidence_rejects_missing_required_source_url(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"id":"bad","source_title":"Missing URL","published_at":"2026-01-01",'
        '"claim":"Bad claim","summary":"Bad","tickers":["SIVE"],"themes":["CPO"],'
        '"supply_chain_layer":"component","direction":"positive","strength":"derived",'
        '"confidence":0.5,"factor_impacts":{"demand_certainty":1}}\n',
        encoding="utf-8",
    )

    with pytest.raises(EvidenceValidationError, match="source_url"):
        load_evidence(bad)


def test_write_evidence_jsonl_persists_claim_type(tmp_path):
    item = load_evidence(FIXTURE)[0]
    out = tmp_path / "evidence.jsonl"

    write_evidence_jsonl([item], out)

    text = out.read_text(encoding="utf-8")
    assert '"claim_type": "inference"' in text


def test_dedupe_evidence_collapses_semantic_duplicates():
    item = load_evidence(FIXTURE)[0]
    duplicate = EvidenceItem(
        id="different-id",
        source_title=item.source_title,
        source_url=item.source_url,
        published_at=item.published_at,
        claim=item.claim.upper(),
        summary=item.summary,
        tickers=item.tickers,
        themes=item.themes,
        supply_chain_layer=item.supply_chain_layer,
        direction=item.direction,
        strength=item.strength,
        confidence=item.confidence,
        factor_impacts=item.factor_impacts,
        claim_type=item.claim_type,
    )

    deduped = dedupe_evidence([item, duplicate])

    assert len(deduped) == 1
    assert evidence_claim_key(item) == evidence_claim_key(duplicate)
