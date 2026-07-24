from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.quant.factors import FactorDirection
from serenity_alpha_lab.quant.factors.evaluation import (
    FACTOR_EVALUATION_ENGINE_VERSION,
    FACTOR_EVALUATION_SCHEMA_NAME,
    FactorEvaluationError,
    FactorEvaluationObservation,
    FactorEvaluationSpec,
    FutureReturnWindow,
    evaluate_factor,
    publish_factor_evaluation_report,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


FACTOR_VALUES_VERSION = "dsv_" + "e" * 32
FORWARD_RETURNS_VERSION = "dsv_" + "f" * 32
INSTRUMENT_MASTER_VERSION = "dsv_" + "1" * 32
FACTOR_VERSION_ID = "fdv_" + "2" * 32
DECISION_TIME = datetime(2026, 1, 2, 15, 30, tzinfo=UTC)
AVAILABLE_AT = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
INGESTED_AT = datetime(2026, 1, 8, 18, 0, tzinfo=UTC)


def test_factor_evaluation_spec_records_metric_schema_and_concrete_dataset_versions() -> None:
    spec = _evaluation_spec()

    assert spec.schema_name == FACTOR_EVALUATION_SCHEMA_NAME
    assert spec.engine_version == FACTOR_EVALUATION_ENGINE_VERSION
    assert spec.dataset_versions == {
        "factor_values": FACTOR_VALUES_VERSION,
        "forward_returns": FORWARD_RETURNS_VERSION,
        "instrument_master": INSTRUMENT_MASTER_VERSION,
    }
    assert spec.future_return_window.to_record() == {
        "horizon": 5,
        "unit": "trading_day",
        "return_field": "forward_return_5d",
        "version": "forward_return_5d_v1",
        "annualization_periods": 252,
    }

    record = spec.to_record()
    assert record["factor_version_id"] == FACTOR_VERSION_ID
    assert record["metric_set_version"] == "factor_evaluation_metrics@1.0.0"
    assert record["quantile_count"] == 3
    assert record["correlation_method"] == "spearman"
    json.dumps(record, sort_keys=True)

    with pytest.raises(FactorEvaluationError, match="concrete Dataset Version"):
        _evaluation_spec(dataset_versions={"factor_values": "latest"})

    with pytest.raises(FactorEvaluationError, match="horizon"):
        FutureReturnWindow(horizon=0, return_field="forward_return_5d", version="forward_return_5d_v1")


def test_evaluate_factor_computes_coverage_ic_group_returns_monotonicity_turnover_and_exposures() -> None:
    report = evaluate_factor(_observations(), _evaluation_spec())

    assert report.schema_name == FACTOR_EVALUATION_SCHEMA_NAME
    assert report.spec.factor_version_id == FACTOR_VERSION_ID
    assert report.coverage.total_universe_count == 18
    assert report.coverage.factor_observation_count == 17
    assert report.coverage.overlap_observation_count == 16
    assert report.coverage.coverage_ratio == pytest.approx(17 / 18)
    assert report.coverage.sample_overlap_ratio == pytest.approx(16 / 18)
    assert report.coverage.factor_only_count == 1
    assert report.coverage.return_only_count == 1

    assert len(report.ic_by_date) == 3
    assert report.ic_summary.mean_ic > 0.80
    assert report.ic_summary.icir is not None
    assert report.ic_summary.annualization_periods == 252
    assert all(metric.method == "spearman" for metric in report.ic_by_date)

    assert tuple(group.group for group in report.group_return_summary.groups) == (1, 2, 3)
    group_returns = [group.mean_forward_return for group in report.group_return_summary.groups]
    assert group_returns == sorted(group_returns)
    assert report.group_return_summary.long_short_mean_return > 0.08
    assert report.monotonicity.direction_adjusted_score > 0.90

    assert len(report.turnover_by_period) == 2
    assert report.turnover_summary.mean_turnover == pytest.approx(0.5)
    assert report.exposure_summary.exposures["beta"].mean_exposure > 1.0
    assert report.exposure_summary.exposures["beta"].factor_correlation > 0.90

    record = report.to_record()
    assert record["coverage"]["total_universe_count"] == 18
    assert record["ic_summary"]["icir"] == report.ic_summary.icir
    assert record["group_return_summary"]["groups"][2]["group"] == 3
    assert any(warning["code"] == "sample_non_overlap" for warning in record["warnings"])
    json.dumps(record, sort_keys=True)


def test_formal_factor_evaluation_rejects_non_pit_factor_observations() -> None:
    observations = (
        FactorEvaluationObservation(
            instrument_id="600000.XSHG",
            trade_date=date(2026, 1, 2),
            decision_time=DECISION_TIME,
            factor_available_at=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
            forward_return_available_at=INGESTED_AT,
            factor_value=1.0,
            forward_return=0.03,
        ),
        FactorEvaluationObservation(
            instrument_id="600001.XSHG",
            trade_date=date(2026, 1, 2),
            decision_time=DECISION_TIME,
            factor_available_at=AVAILABLE_AT,
            forward_return_available_at=INGESTED_AT,
            factor_value=2.0,
            forward_return=0.04,
        ),
    )

    with pytest.raises(FactorEvaluationError, match="PIT"):
        evaluate_factor(observations, _evaluation_spec(formal=True))


def test_factor_evaluation_report_publishes_deterministic_json_artifact(tmp_path) -> None:
    report = evaluate_factor(_observations(), _evaluation_spec())
    store = LocalArtifactStore(tmp_path / "artifacts")
    created_at = datetime(2026, 1, 9, 12, 0, tzinfo=UTC)

    manifest = publish_factor_evaluation_report(
        report,
        store,
        created_at=created_at,
        retention_tier=ArtifactRetentionTier.STANDARD,
    )
    repeated = publish_factor_evaluation_report(
        report,
        store,
        created_at=created_at,
        retention_tier=ArtifactRetentionTier.STANDARD,
    )

    assert repeated.artifact_id == manifest.artifact_id
    assert manifest.schema_name == FACTOR_EVALUATION_SCHEMA_NAME
    assert manifest.schema_version == "1.0.0"
    assert manifest.produced_by_run_id == "run-factor-eval"
    assert manifest.produced_by_stage_id == "stage-factor-eval"

    payload = json.loads(store.get_bytes(manifest.artifact_id).decode("utf-8"))
    assert payload == report.to_record()
    assert payload["spec"]["future_return_window"]["version"] == "forward_return_5d_v1"


def _evaluation_spec(**overrides) -> FactorEvaluationSpec:
    values = {
        "run_id": "run-factor-eval",
        "stage_id": "stage-factor-eval",
        "factor_definition_id": "momentum_20d",
        "factor_version_id": FACTOR_VERSION_ID,
        "dataset_versions": {
            "factor_values": FACTOR_VALUES_VERSION,
            "forward_returns": FORWARD_RETURNS_VERSION,
            "instrument_master": INSTRUMENT_MASTER_VERSION,
        },
        "future_return_window": FutureReturnWindow(
            horizon=5,
            return_field="forward_return_5d",
            version="forward_return_5d_v1",
        ),
        "factor_direction": FactorDirection.HIGHER_IS_BETTER,
        "quantile_count": 3,
        "minimum_ic_observations": 3,
        "exposure_fields": ("beta",),
        "formal": True,
    }
    values.update(overrides)
    return FactorEvaluationSpec(**values)


def _observations() -> tuple[FactorEvaluationObservation, ...]:
    rows: list[FactorEvaluationObservation] = []
    for offset, trade_date in enumerate((date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6))):
        factor_values = (
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            [1.0, 2.0, 3.0, 5.0, 4.0, 6.0],
            [1.0, 2.0, 3.0, 4.0, 6.0, 5.0],
        )[offset]
        returns_by_date = (
            [0.01, 0.02, 0.04, 0.05, 0.08, 0.10],
            [0.02, 0.01, 0.05, 0.11, 0.09, 0.12],
            [0.01, 0.03, 0.02, 0.06, 0.10, 0.09],
        )[offset]
        for index in range(6):
            instrument = f"60000{index}.XSHG"
            factor_value = factor_values[index]
            forward_return = returns_by_date[index]
            if offset == 1 and index == 0:
                factor_value = None
            if offset == 2 and index == 1:
                forward_return = None
            rows.append(
                FactorEvaluationObservation(
                    instrument_id=instrument,
                    trade_date=trade_date,
                    decision_time=DECISION_TIME,
                    factor_available_at=AVAILABLE_AT,
                    forward_return_available_at=INGESTED_AT,
                    factor_value=factor_value,
                    forward_return=forward_return,
                    exposures={"beta": 0.8 + index * 0.1},
                )
            )
    return tuple(rows)
