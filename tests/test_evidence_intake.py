from __future__ import annotations

from datetime import date

from serenity_alpha_lab.evidence import load_evidence
from serenity_alpha_lab.evidence_intake import (
    append_intake_evidence,
    build_intake_evidence,
    parse_factor_impacts,
    validate_source_excerpt,
    validate_source_url,
)


def test_parse_factor_impacts_accepts_key_value_pairs():
    impacts = parse_factor_impacts(["evidence_quality=8", "supply_elasticity=-5"])

    assert impacts == {"evidence_quality": 8, "supply_elasticity": -5}


def test_validate_source_url_rejects_placeholder_urls():
    try:
        validate_source_url("https://example.com/nvda-risk")
    except ValueError as exc:
        assert "placeholder" in str(exc).lower()
    else:
        raise AssertionError("placeholder source URL should be rejected")


def test_validate_source_url_accepts_https_non_placeholder_url():
    validate_source_url("https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json")


def test_validate_source_excerpt_rejects_blank_or_too_short_trace():
    for source_excerpt in ["", "   ", "too short"]:
        try:
            validate_source_excerpt(source_excerpt)
        except ValueError as exc:
            assert "source excerpt" in str(exc).lower()
        else:
            raise AssertionError("blank or too-short source excerpt should be rejected")


def test_validate_source_excerpt_accepts_decision_useful_trace():
    validate_source_excerpt(
        "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk."
    )


def test_build_intake_evidence_requires_source_excerpt():
    try:
        build_intake_evidence(
            item_id="manual:NVDA:risk:cpo-sourcing",
            source_title="Manual NVDA risk note",
            source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
            published_at="2026-07-04",
            claim="NVDA faces CPO sourcing risk if optical component supply tightens.",
            summary="Manual intake captures a negative/risk item for NVDA CPO sourcing.",
            tickers=["NVDA"],
            themes=["CPO", "risk", "manual-intake"],
            supply_chain_layer="AI accelerator customer",
            direction="negative",
            strength="derived",
            confidence=0.72,
            factor_impacts={"evidence_quality": 8, "supply_elasticity": -5},
            claim_type="risk",
            source_excerpt="",
        )
    except ValueError as exc:
        assert "source excerpt" in str(exc).lower()
    else:
        raise AssertionError("manual intake should require source excerpt")


def test_build_intake_evidence_creates_valid_schema_item():
    item = build_intake_evidence(
        item_id="manual:NVDA:risk:cpo-sourcing",
        source_title="Manual NVDA risk note",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
        published_at="2026-07-04",
        claim="NVDA faces CPO sourcing risk if optical component supply tightens.",
        summary="Manual intake captures a negative/risk item for NVDA CPO sourcing.",
        tickers=["nvda"],
        themes=["CPO", "risk", "manual-intake"],
        supply_chain_layer="AI accelerator customer",
        direction="negative",
        strength="derived",
        confidence=0.72,
        factor_impacts={"evidence_quality": 8, "supply_elasticity": -5},
        claim_type="risk",
        source_excerpt=(
            "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk."
        ),
    )

    assert item.id == "manual:NVDA:risk:cpo-sourcing"
    assert item.published_at == date(2026, 7, 4)
    assert item.tickers == ["NVDA"]
    assert item.claim_type == "risk"
    assert item.direction == "negative"
    assert "issuer identity" in item.source_excerpt


def test_append_intake_evidence_writes_jsonl_and_preserves_existing_rows(tmp_path):
    out = tmp_path / "manual_intake.jsonl"
    out.write_text(
        '{"id":"existing","source_title":"Existing","source_url":"https://example.com/existing",'
        '"published_at":"2026-01-01","claim":"Existing claim","summary":"Existing summary",'
        '"tickers":["AAOI"],"themes":["CPO"],"supply_chain_layer":"optical components",'
        '"direction":"neutral","strength":"derived","confidence":0.6,'
        '"factor_impacts":{"evidence_quality":1},"claim_type":"inference"}\n',
        encoding="utf-8",
    )
    item = build_intake_evidence(
        item_id="manual:NVDA:risk:cpo-sourcing",
        source_title="Manual NVDA risk note",
        source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
        published_at="2026-07-04",
        claim="NVDA faces CPO sourcing risk if optical component supply tightens.",
        summary="Manual intake captures a negative/risk item for NVDA CPO sourcing.",
        tickers=["NVDA"],
        themes=["CPO", "risk", "manual-intake"],
        supply_chain_layer="AI accelerator customer",
        direction="negative",
        strength="derived",
        confidence=0.72,
        factor_impacts={"evidence_quality": 8, "supply_elasticity": -5},
        claim_type="risk",
        source_excerpt=(
            "SEC companyfacts URL validates the issuer identity; analyst note ties the filing to CPO sourcing risk."
        ),
    )

    append_intake_evidence(item, out)

    items = load_evidence(out)
    assert [loaded.id for loaded in items] == ["existing", "manual:NVDA:risk:cpo-sourcing"]
    assert items[-1].factor_impacts["supply_elasticity"] == -5
    assert "issuer identity" in items[-1].source_excerpt
