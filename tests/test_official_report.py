from pathlib import Path

import pytest

from serenity_alpha_lab.official_report import (
    OfficialReportFactSpec,
    OfficialReportSourceSpec,
    load_official_report_specs,
    official_report_specs_to_evidence,
)


FIXTURE = Path(__file__).parent / "fixtures" / "official_report_sources.json"


def test_load_official_report_specs_resolves_text_paths_against_manifest_parent():
    specs = load_official_report_specs(FIXTURE)

    assert specs[0].ticker == "SIVE"
    assert specs[0].text_path == Path(__file__).parent / "fixtures" / "sivers_annualreport_excerpt.txt"
    assert specs[0].facts[0].id == "net-sales-2025"


def test_official_report_specs_to_evidence_emits_primary_fact_items():
    specs = load_official_report_specs(FIXTURE)

    items = official_report_specs_to_evidence(specs)

    assert len(items) == 2
    assert items[0].id == "official-report:SIVE:net-sales-2025"
    assert items[0].tickers == ["SIVE"]
    assert items[0].strength == "primary"
    assert items[0].claim_type == "fact"
    assert items[0].source_excerpt.startswith("The Group’s net sales")
    assert items[0].factor_impacts["evidence_quality"] == 24
    assert any("co-packaged optics" in item.claim for item in items)


def test_official_report_specs_to_evidence_rejects_missing_source_excerpt(tmp_path):
    text = tmp_path / "report.txt"
    text.write_text("This report does not include the referenced excerpt.", encoding="utf-8")
    spec = OfficialReportSourceSpec(
        ticker="SIVE",
        source_title="Sivers Semiconductors Annual Report 2025",
        source_url="https://www.sivers-semiconductors.com/report.pdf",
        published_at="2026-05-01",
        text_path=text,
        facts=[
            OfficialReportFactSpec(
                id="missing",
                claim="Missing excerpt claim",
                summary="Missing excerpt summary.",
                source_excerpt="The Group’s net sales amounted to SEK 306.6 million.",
                themes=("annual-report", "primary-source"),
                supply_chain_layer="company financials",
                direction="positive",
                factor_impacts={"evidence_quality": 24},
            )
        ],
    )

    with pytest.raises(ValueError, match="source excerpt"):
        official_report_specs_to_evidence([spec])
