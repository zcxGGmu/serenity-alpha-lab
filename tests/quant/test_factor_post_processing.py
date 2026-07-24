from __future__ import annotations

from datetime import date

import pytest

from serenity_alpha_lab.quant.factors.post_processing import (
    CrossSectionFactorValue,
    CrossSectionMissingPolicy,
    CrossSectionMissingStrategy,
    CrossSectionPostProcessingSpec,
    FactorPostProcessingError,
    NeutralizationExposure,
    NeutralizationSpec,
    StandardizationMethod,
    StandardizationSpec,
    WinsorizationMethod,
    WinsorizationSpec,
    process_cross_sectional_factor_values,
)


FACTOR_VALUES_VERSION = "dsv_" + "c" * 32
INSTRUMENT_MASTER_VERSION = "dsv_" + "d" * 32


def test_post_processing_spec_records_parameter_schema_and_concrete_dataset_versions() -> None:
    spec = _post_processing_spec()

    assert spec.schema_name == "quant.factor_cross_section_post_processing"
    assert spec.dataset_versions == {
        "factor_values": FACTOR_VALUES_VERSION,
        "instrument_master": INSTRUMENT_MASTER_VERSION,
    }

    record = spec.to_record()
    assert record["dataset_versions"]["factor_values"] == FACTOR_VALUES_VERSION
    assert record["winsorization"] == {"method": "mad", "n_mad": 3.0}
    assert record["standardization"] == {"method": "zscore"}
    assert record["neutralization"]["exposures"] == ["industry", "log_market_cap"]
    assert record["missing_policy"] == {"strategy": "fill_median"}

    with pytest.raises(FactorPostProcessingError, match="concrete Dataset Version"):
        _post_processing_spec(dataset_versions={"factor_values": "latest"})

    with pytest.raises(FactorPostProcessingError, match="lower_quantile"):
        WinsorizationSpec(method=WinsorizationMethod.QUANTILE, lower_quantile=0.90, upper_quantile=0.10)


def test_processor_groups_by_trade_date_handles_missing_outliers_and_constant_columns() -> None:
    rows = (
        CrossSectionFactorValue("600000.XSHG", date(2026, 1, 2), 1.0, industry="bank", market_cap=100.0),
        CrossSectionFactorValue("600001.XSHG", date(2026, 1, 2), 2.0, industry="bank", market_cap=120.0),
        CrossSectionFactorValue("000001.XSHE", date(2026, 1, 2), None, industry="tech", market_cap=80.0),
        CrossSectionFactorValue("000002.XSHE", date(2026, 1, 2), 100.0, industry="tech", market_cap=90.0),
        CrossSectionFactorValue("600010.XSHG", date(2026, 1, 3), 7.0, industry="steel", market_cap=200.0),
        CrossSectionFactorValue("000010.XSHE", date(2026, 1, 3), 7.0, industry="steel", market_cap=210.0),
    )

    result = process_cross_sectional_factor_values(
        rows,
        _post_processing_spec(neutralization=None),
    )

    assert len(result.processed_values) == len(rows)
    assert result.dataset_versions["factor_values"] == FACTOR_VALUES_VERSION

    by_key = {(value.instrument_id, value.trade_date): value for value in result.processed_values}
    missing_row = by_key[("000001.XSHE", date(2026, 1, 2))]
    assert missing_row.filled_value == pytest.approx(2.0)

    outlier_row = by_key[("000002.XSHE", date(2026, 1, 2))]
    assert outlier_row.step_values["winsorized"] < 10.0
    day_one_values = [
        value.processed_value for value in result.processed_values if value.trade_date == date(2026, 1, 2)
    ]
    assert sum(day_one_values) == pytest.approx(0.0, abs=1e-12)

    day_two_values = [
        value.processed_value for value in result.processed_values if value.trade_date == date(2026, 1, 3)
    ]
    assert day_two_values == [0.0, 0.0]
    assert any(warning.code == "standardize_zero_variance" for warning in result.warnings)


def test_neutralization_removes_industry_and_log_market_cap_exposure_with_missing_industry_bucket() -> None:
    rows = (
        CrossSectionFactorValue("600000.XSHG", date(2026, 1, 2), 11.00, industry="bank", market_cap=100.0),
        CrossSectionFactorValue("600001.XSHG", date(2026, 1, 2), 12.40, industry="bank", market_cap=120.0),
        CrossSectionFactorValue("000001.XSHE", date(2026, 1, 2), 22.00, industry="tech", market_cap=80.0),
        CrossSectionFactorValue("000002.XSHE", date(2026, 1, 2), 23.50, industry="tech", market_cap=160.0),
        CrossSectionFactorValue("600010.XSHG", date(2026, 1, 2), 16.20, industry=None, market_cap=90.0),
        CrossSectionFactorValue("000010.XSHE", date(2026, 1, 2), 17.10, industry=None, market_cap=180.0),
        CrossSectionFactorValue("600011.XSHG", date(2026, 1, 2), 6.50, industry="energy", market_cap=None),
        CrossSectionFactorValue("000011.XSHE", date(2026, 1, 2), 7.20, industry="energy", market_cap=200.0),
    )
    spec = _post_processing_spec(
        winsorization=None,
        standardization=None,
        neutralization=NeutralizationSpec(
            exposures=(NeutralizationExposure.INDUSTRY, NeutralizationExposure.LOG_MARKET_CAP),
            missing_market_cap_strategy=CrossSectionMissingStrategy.FILL_MEDIAN,
        ),
    )

    result = process_cross_sectional_factor_values(rows, spec)

    assert len(result.processed_values) == len(rows)
    assert any(warning.code == "missing_industry_bucketed" for warning in result.warnings)
    assert any(warning.code == "missing_market_cap_filled" for warning in result.warnings)

    by_industry: dict[str, list[float]] = {}
    for value in result.processed_values:
        industry = value.exposures["industry"]
        by_industry.setdefault(industry, []).append(value.processed_value)

    assert "__missing_industry__" in by_industry
    for residuals in by_industry.values():
        assert sum(residuals) == pytest.approx(0.0, abs=1e-10)

    log_caps = [value.exposures["log_market_cap"] for value in result.processed_values]
    residuals = [value.processed_value for value in result.processed_values]
    log_cap_mean = sum(log_caps) / len(log_caps)
    assert sum((log_cap - log_cap_mean) * residual for log_cap, residual in zip(log_caps, residuals)) == pytest.approx(
        0.0,
        abs=1e-10,
    )


def test_drop_missing_policy_and_small_sample_behavior_are_explicit() -> None:
    rows = (
        CrossSectionFactorValue("600000.XSHG", date(2026, 1, 2), None, industry="bank", market_cap=100.0),
        CrossSectionFactorValue("600001.XSHG", date(2026, 1, 2), 3.0, industry="bank", market_cap=120.0),
    )
    spec = _post_processing_spec(
        missing_policy=CrossSectionMissingPolicy(strategy=CrossSectionMissingStrategy.DROP),
        winsorization=None,
        neutralization=None,
    )

    result = process_cross_sectional_factor_values(rows, spec)

    assert [value.instrument_id for value in result.processed_values] == ["600001.XSHG"]
    assert [value.instrument_id for value in result.dropped_values] == ["600000.XSHG"]
    assert result.processed_values[0].processed_value == 0.0
    assert any(warning.code == "missing_values_dropped" for warning in result.warnings)
    assert any(warning.code == "standardize_small_sample" for warning in result.warnings)


def _post_processing_spec(**overrides) -> CrossSectionPostProcessingSpec:
    values = {
        "dataset_versions": {
            "factor_values": FACTOR_VALUES_VERSION,
            "instrument_master": INSTRUMENT_MASTER_VERSION,
        },
        "missing_policy": CrossSectionMissingPolicy(strategy=CrossSectionMissingStrategy.FILL_MEDIAN),
        "winsorization": WinsorizationSpec(method=WinsorizationMethod.MAD, n_mad=3.0),
        "neutralization": NeutralizationSpec(
            exposures=(NeutralizationExposure.INDUSTRY, NeutralizationExposure.LOG_MARKET_CAP)
        ),
        "standardization": StandardizationSpec(method=StandardizationMethod.ZSCORE),
    }
    values.update(overrides)
    return CrossSectionPostProcessingSpec(**values)
