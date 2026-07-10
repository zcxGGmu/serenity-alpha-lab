from __future__ import annotations

import json
from pathlib import Path

import pytest

from serenity_alpha_lab.app.stock_analysis_artifacts import (
    ArtifactRepositoryError,
    StockAnalysisArtifactRepository,
)


def write_canonical_artifact(root: Path, *, mutate=None) -> None:
    manifest = {
        "schema_version": 1,
        "artifact_type": "stock_analysis_report",
        "symbol": "MSFT",
        "stock_name": "Microsoft Corporation",
        "query": "MSFT market data research",
        "generated_at": "2026-07-10T00:00:00+00:00",
        "research_only": True,
        "readiness": {
            "status": "ready",
            "reason": "readiness_ready",
            "flags": [],
        },
        "report_gate": {
            "status": "available",
            "reason": "readiness_ready",
            "research_only": True,
        },
        "source_coverage": {
            "status": "ready",
            "focus_ticker": "MSFT",
            "evidence_count": 4,
            "focus_evidence_count": 4,
            "primary_count": 3,
            "risk_count": 1,
            "methodology_share": 0.0,
            "placeholder_share": 0.0,
            "external_non_serenity_count": 0,
            "flags": [],
        },
        "skeptical_review": {
            "summary": "Risk coverage uses 1 risk or invalidation evidence item.",
            "counter_thesis": ["MSFT closed lower on 2026-07-08."],
        },
        "reports": {
            "stock_analysis": "reports/stock-analysis-report.md",
            "ui": "index.html",
        },
        "safety": {
            "passed": True,
            "boundary": "research only; not investment advice",
            "findings": [],
        },
        "key_claims": [
            {
                "claim_id": "claim:MSFT:readiness",
                "claim": "Readiness is ready.",
                "provenance_refs": [
                    {
                        "evidence_id": "serenity:market-data:MSFT:quote:2026-07-10",
                        "source_url": "serenity://market-data/MSFT/quote/2026-07-10",
                        "source_title": "MSFT quote",
                        "excerpt": "Normalized quote evidence.",
                    }
                ],
                "diagnostics": [],
            }
        ],
    }
    if mutate is not None:
        mutate(manifest)
    (root / "reports").mkdir(parents=True)
    (root / "analysis-report-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (root / "reports" / "stock-analysis-report.md").write_text(
        "# MSFT Research Report\n",
        encoding="utf-8",
    )


def test_repository_returns_allowlisted_summary_and_validated_artifacts(tmp_path) -> None:
    write_canonical_artifact(tmp_path)
    repository = StockAnalysisArtifactRepository(tmp_path)

    summary = repository.load_latest_summary()
    manifest = repository.load_latest_manifest()
    report = repository.load_latest_report()

    assert summary["symbol"] == "MSFT"
    assert summary["reports"] == {
        "stock_analysis": "/api/artifacts/stock-analysis/latest/report",
        "manifest": "/api/artifacts/stock-analysis/latest/manifest",
    }
    assert "ui" not in summary["reports"]
    assert manifest["schema_version"] == 1
    assert report == "# MSFT Research Report\n"
    assert str(tmp_path) not in json.dumps(summary)


@pytest.mark.parametrize(
    ("mutate", "status_code", "code", "reason"),
    [
        (
            lambda payload: payload.update(research_only=False),
            409,
            "artifact_blocked",
            "research_only_required",
        ),
        (
            lambda payload: payload["safety"].update(passed=False),
            409,
            "artifact_blocked",
            "report_safety_failed",
        ),
        (
            lambda payload: payload.pop("readiness"),
            422,
            "artifact_invalid",
            "readiness_missing",
        ),
        (
            lambda payload: payload.update(schema_version=2),
            422,
            "artifact_invalid",
            "schema_version_unsupported",
        ),
        (
            lambda payload: payload["key_claims"][0].update(provenance_refs=[]),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda payload: payload["reports"].update(
                stock_analysis="../secret.md"
            ),
            422,
            "artifact_invalid",
            "report_path_invalid",
        ),
        (
            lambda payload: payload.update(
                nested={"operation_advice": "buy"}
            ),
            422,
            "artifact_invalid",
            "forbidden_field",
        ),
        (
            lambda payload: payload.update(
                nested={"brokerage_account": "hidden"}
            ),
            422,
            "artifact_invalid",
            "forbidden_field",
        ),
        (
            lambda payload: payload.update(schema_version=True),
            422,
            "artifact_invalid",
            "schema_version_unsupported",
        ),
        (
            lambda payload: payload["reports"].update(
                stock_analysis="reports/./stock-analysis-report.md"
            ),
            422,
            "artifact_invalid",
            "report_path_invalid",
        ),
        (
            lambda payload: payload["key_claims"][0][
                "provenance_refs"
            ][0].update(source_url="/Users/private/evidence.txt"),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda payload: payload["key_claims"][0][
                "provenance_refs"
            ][0].update(source_url="https://[::1"),
            422,
            "artifact_invalid",
            "key_claim_provenance_missing",
        ),
        (
            lambda payload: payload["reports"].update(
                ui="/Users/private/index.html"
            ),
            422,
            "artifact_invalid",
            "reports_invalid",
        ),
    ],
)
def test_repository_fails_closed_with_sanitized_errors(
    tmp_path,
    mutate,
    status_code,
    code,
    reason,
) -> None:
    write_canonical_artifact(tmp_path, mutate=mutate)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.status_code == status_code
    assert exc_info.value.code == code
    assert exc_info.value.reason == reason
    assert str(tmp_path) not in str(exc_info.value)


def test_repository_reports_missing_and_invalid_json_without_raw_details(tmp_path) -> None:
    repository = StockAnalysisArtifactRepository(tmp_path)
    with pytest.raises(ArtifactRepositoryError) as missing:
        repository.load_latest_summary()
    assert missing.value.to_payload() == {
        "error": {
            "code": "artifact_not_found",
            "reason": "stock_analysis_artifact_missing",
        }
    }

    (tmp_path / "analysis-report-manifest.json").write_text(
        "{",
        encoding="utf-8",
    )
    with pytest.raises(ArtifactRepositoryError) as invalid:
        repository.load_latest_summary()
    assert invalid.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "manifest_json_invalid",
        }
    }


@pytest.mark.parametrize(
    ("mutate", "status_code", "code", "reason"),
    [
        (
            lambda payload: payload.pop("safety"),
            409,
            "artifact_blocked",
            "report_safety_failed",
        ),
        (
            lambda payload: payload["safety"].update(boundary=""),
            409,
            "artifact_blocked",
            "research_boundary_required",
        ),
        (
            lambda payload: payload["source_coverage"].update(
                evidence_count=float("nan")
            ),
            422,
            "artifact_invalid",
            "source_coverage_invalid",
        ),
        (
            lambda payload: payload["source_coverage"].update(
                risk_count=True
            ),
            422,
            "artifact_invalid",
            "source_coverage_invalid",
        ),
        (
            lambda payload: payload["reports"].pop("ui"),
            422,
            "artifact_invalid",
            "reports_invalid",
        ),
    ],
)
def test_repository_validates_blocking_and_numeric_boundaries(
    tmp_path,
    mutate,
    status_code,
    code,
    reason,
) -> None:
    write_canonical_artifact(tmp_path, mutate=mutate)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.status_code == status_code
    assert exc_info.value.code == code
    assert exc_info.value.reason == reason
    assert str(tmp_path) not in str(exc_info.value)


def test_repository_strips_unknown_benign_fields_from_returned_objects(tmp_path) -> None:
    def add_unknown_fields(payload) -> None:
        payload["internal_debug"] = {"note": "not for clients"}
        payload["readiness"]["internal_state"] = "hidden"
        payload["key_claims"][0]["provenance_refs"][0]["local_path"] = (
            "/tmp/private-source.txt"
        )

    write_canonical_artifact(tmp_path, mutate=add_unknown_fields)
    repository = StockAnalysisArtifactRepository(tmp_path)

    summary = repository.load_latest_summary()
    manifest = repository.load_latest_manifest()

    serialized = json.dumps(
        {"summary": summary, "manifest": manifest},
        ensure_ascii=False,
    )
    assert "internal_debug" not in serialized
    assert "internal_state" not in serialized
    assert "local_path" not in serialized
    assert "/tmp/private-source.txt" not in serialized


def test_repository_rejects_report_symlink_escape(tmp_path) -> None:
    write_canonical_artifact(tmp_path)
    external_report = tmp_path.parent / "external-report.md"
    external_report.write_text("# External\n", encoding="utf-8")
    report_path = tmp_path / "reports" / "stock-analysis-report.md"
    report_path.unlink()
    report_path.symlink_to(external_report)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "report_path_invalid",
        }
    }
    assert str(tmp_path) not in str(exc_info.value)


def test_repository_rejects_manifest_symlink_escape(tmp_path) -> None:
    outside_root = tmp_path.parent / f"{tmp_path.name}-outside"
    outside_root.mkdir()
    write_canonical_artifact(outside_root)
    write_canonical_artifact(tmp_path)
    manifest_path = tmp_path / "analysis-report-manifest.json"
    manifest_path.unlink()
    manifest_path.symlink_to(
        outside_root / "analysis-report-manifest.json"
    )
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "manifest_path_invalid",
        }
    }
    assert str(tmp_path) not in str(exc_info.value)


def test_repository_sanitizes_report_symlink_loop(tmp_path) -> None:
    write_canonical_artifact(tmp_path)
    report_path = tmp_path / "reports" / "stock-analysis-report.md"
    report_path.unlink()
    report_path.symlink_to(report_path.name)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "report_path_invalid",
        }
    }
    assert str(tmp_path) not in str(exc_info.value)


@pytest.mark.parametrize(
    ("mutate", "status_code", "code", "reason"),
    [
        (
            lambda payload: (
                payload.update(research_only=False),
                payload["source_coverage"].update(
                    evidence_count=float("inf")
                ),
            ),
            422,
            "artifact_invalid",
            "source_coverage_invalid",
        ),
        (
            lambda payload: (
                payload.pop("readiness"),
                payload["safety"].update(passed=False),
            ),
            409,
            "artifact_blocked",
            "report_safety_failed",
        ),
    ],
)
def test_repository_uses_locked_validation_order(
    tmp_path,
    mutate,
    status_code,
    code,
    reason,
) -> None:
    write_canonical_artifact(tmp_path, mutate=mutate)
    repository = StockAnalysisArtifactRepository(tmp_path)

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.status_code == status_code
    assert exc_info.value.code == code
    assert exc_info.value.reason == reason


def test_repository_sanitizes_invalid_configured_root() -> None:
    repository = StockAnalysisArtifactRepository(Path("invalid\0root"))

    with pytest.raises(ArtifactRepositoryError) as exc_info:
        repository.load_latest_summary()

    assert exc_info.value.to_payload() == {
        "error": {
            "code": "artifact_invalid",
            "reason": "manifest_path_invalid",
        }
    }
    assert "\0" not in str(exc_info.value)
    assert "root" not in str(exc_info.value)
