from pathlib import Path

import pytest

from serenity_alpha_lab.sec_companyfacts import (
    CompanyFactSpec,
    companyfacts_to_evidence,
    load_companyfacts_json,
    load_companyfact_specs,
)


FIXTURE = Path(__file__).parent / "fixtures" / "sec_companyfacts_sive.json"


def test_companyfacts_to_evidence_extracts_primary_annual_facts():
    payload = load_companyfacts_json(FIXTURE)

    items = companyfacts_to_evidence(payload, ticker="SIVE", source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK9999999999.json")

    assert len(items) == 3
    assert items[0].tickers == ["SIVE"]
    assert items[0].claim_type == "fact"
    assert items[0].strength == "primary"
    assert items[0].published_at.isoformat() == "2026-02-28"
    assert "SEC companyfacts reports Revenue for SIVE FY2025" in items[0].claim
    assert items[0].factor_impacts["evidence_quality"] == 22


def test_companyfacts_to_evidence_marks_negative_income_direction():
    payload = load_companyfacts_json(FIXTURE)

    items = companyfacts_to_evidence(payload, ticker="SIVE", source_url="https://example.com/sec.json")
    net_income = [item for item in items if "Net Income" in item.claim][0]

    assert net_income.direction == "negative"
    assert "loss" in net_income.summary.lower()


def test_companyfacts_to_evidence_uses_contract_revenue_fallback():
    payload = dict(load_companyfacts_json(FIXTURE))
    us_gaap = dict(payload["facts"]["us-gaap"])
    us_gaap.pop("Revenues")
    us_gaap["RevenueFromContractWithCustomerExcludingAssessedTax"] = {
        "label": "Revenue from Contract with Customer",
        "units": {
            "USD": [
                {
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-03-01",
                    "end": "2025-12-31",
                    "val": 455000000,
                    "accn": "0000000000-26-000002",
                }
            ]
        },
    }
    payload["facts"] = dict(payload["facts"])
    payload["facts"]["us-gaap"] = us_gaap

    items = companyfacts_to_evidence(payload, ticker="SIVE", source_url="https://example.com/sec.json")

    revenue_items = [item for item in items if "Revenue" in item.claim]
    assert len(revenue_items) == 1
    assert "$455,000,000" in revenue_items[0].claim
    assert "revenue" in revenue_items[0].themes
    assert revenue_items[0].factor_impacts["demand_certainty"] == 8


def test_companyfacts_to_evidence_selects_latest_period_end_within_same_filing():
    payload = dict(load_companyfacts_json(FIXTURE))
    us_gaap = dict(payload["facts"]["us-gaap"])
    us_gaap["Revenues"] = {
        "label": "Revenue",
        "units": {
            "USD": [
                {
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-28",
                    "end": "2024-12-31",
                    "val": 390000000,
                    "accn": "0000000000-26-000001",
                },
                {
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-28",
                    "end": "2025-12-31",
                    "val": 420000000,
                    "accn": "0000000000-26-000001",
                },
            ]
        },
    }
    payload["facts"] = dict(payload["facts"])
    payload["facts"]["us-gaap"] = us_gaap

    items = companyfacts_to_evidence(payload, ticker="SIVE", source_url="https://example.com/sec.json")

    revenue = [item for item in items if "Revenue" in item.claim][0]
    assert "$420,000,000" in revenue.claim


def test_companyfacts_to_evidence_prefers_annual_duration_over_quarter_same_end():
    payload = dict(load_companyfacts_json(FIXTURE))
    us_gaap = dict(payload["facts"]["us-gaap"])
    us_gaap["NetIncomeLoss"] = {
        "label": "Net Income (Loss)",
        "units": {
            "USD": [
                {
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-28",
                    "start": "2025-10-01",
                    "end": "2025-12-31",
                    "val": -1000000,
                    "accn": "0000000000-26-000001",
                },
                {
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-28",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "val": -15000000,
                    "accn": "0000000000-26-000001",
                },
            ]
        },
    }
    payload["facts"] = dict(payload["facts"])
    payload["facts"]["us-gaap"] = us_gaap

    items = companyfacts_to_evidence(payload, ticker="SIVE", source_url="https://example.com/sec.json")

    net_income = [item for item in items if "Net Income" in item.claim][0]
    assert "$-15,000,000" in net_income.claim


def test_load_companyfact_specs_reads_manifest(tmp_path):
    manifest = tmp_path / "sources.json"
    fixture_path = Path("tests/fixtures/sec_companyfacts_sive.json").resolve()
    manifest.write_text(
        f'[{{"ticker":"SIVE","cik":"9999999999","path":"{fixture_path}"}}]',
        encoding="utf-8",
    )

    specs = load_companyfact_specs(manifest)

    assert specs == [
        CompanyFactSpec(ticker="SIVE", cik="9999999999", path=fixture_path)
    ]


def test_load_companyfact_specs_resolves_relative_paths_against_manifest_parent(tmp_path):
    manifest_dir = tmp_path / "config"
    manifest_dir.mkdir()
    manifest = manifest_dir / "sources.json"
    manifest.write_text(
        '[{"ticker":"SIVE","cik":"9999999999","path":"../raw/sec_companyfacts_sive.json"}]',
        encoding="utf-8",
    )

    specs = load_companyfact_specs(manifest)

    assert specs[0].path == manifest_dir / "../raw/sec_companyfacts_sive.json"


def test_companyfacts_to_evidence_validates_manifest_cik_against_payload():
    payload = dict(load_companyfacts_json(FIXTURE))

    with pytest.raises(ValueError, match="CIK mismatch"):
        companyfacts_to_evidence(
            payload,
            ticker="SIVE",
            cik="0000000001",
            source_url="https://example.com/sec.json",
        )
