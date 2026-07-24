from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from serenity_alpha_lab.quant.factors import (
    BASE_FACTOR_CATALOG_VERSION,
    BASE_FACTOR_EXPECTED_CATEGORIES,
    BaseFactorCatalog,
    base_factor_catalog,
    base_factor_definitions,
    compile_base_factor_plans,
)
from serenity_alpha_lab.quant.factors.definitions import FactorDefinitionStatus


EXPECTED_FACTOR_IDS = (
    "roe_ttm",
    "gross_margin_ttm",
    "cash_flow_to_assets_ttm",
    "earnings_yield_ttm",
    "book_to_market",
    "sales_yield_ttm",
    "revenue_growth_yoy",
    "net_profit_growth_yoy",
    "roe_change_yoy",
    "momentum_20d",
    "momentum_60d",
    "volatility_20d",
    "downside_volatility_20d",
    "amount_liquidity_20d",
    "volume_liquidity_20d",
)


def test_base_factor_catalog_exposes_first_15_versioned_definitions() -> None:
    catalog = base_factor_catalog()
    definitions = catalog.definitions

    assert isinstance(catalog, BaseFactorCatalog)
    assert catalog.catalog_version == BASE_FACTOR_CATALOG_VERSION
    assert tuple(definition.definition_id for definition in definitions) == EXPECTED_FACTOR_IDS
    assert len(definitions) == 15
    assert len({definition.definition_id for definition in definitions}) == 15
    assert {definition.category for definition in definitions} == set(BASE_FACTOR_EXPECTED_CATEGORIES)

    category_counts = catalog.category_counts
    assert category_counts == {
        "growth": 3,
        "liquidity": 2,
        "momentum": 2,
        "quality": 3,
        "valuation": 3,
        "volatility": 2,
    }

    record = catalog.to_record()
    assert record["catalog_version"] == BASE_FACTOR_CATALOG_VERSION
    assert record["factor_count"] == 15
    assert record["category_counts"] == category_counts
    json.dumps(record, sort_keys=True)

    with pytest.raises(FrozenInstanceError):
        catalog.catalog_version = "mutated"  # type: ignore[misc]
    with pytest.raises(TypeError):
        definitions[0].metadata["category"] = "mutated"  # type: ignore[index]


def test_base_factors_declare_direction_data_requirements_windows_and_markets() -> None:
    definitions_by_id = {definition.definition_id: definition for definition in base_factor_definitions()}

    for definition in definitions_by_id.values():
        assert definition.status is FactorDefinitionStatus.DRAFT
        assert definition.semantic_version == "1.0.0"
        assert definition.formula.language == "serenity_factor_dsl"
        assert definition.metadata["catalog_version"] == BASE_FACTOR_CATALOG_VERSION
        assert definition.metadata["applicable_markets"] == ("XSHG", "XSHE")
        assert definition.metadata["reference_plan"]["dataset_versions"] == dict(definition.dataset_versions)
        assert definition.metadata["data_requirements"]
        assert all(version.startswith("dsv_") for version in definition.dataset_versions.values())
        assert "latest" not in definition.dataset_versions.values()

    assert definitions_by_id["roe_ttm"].direction.value == "higher_is_better"
    assert definitions_by_id["book_to_market"].category == "valuation"
    assert definitions_by_id["volatility_20d"].direction.value == "lower_is_better"
    assert tuple(window.length for window in definitions_by_id["revenue_growth_yoy"].windows) == (252,)
    assert tuple(window.length for window in definitions_by_id["downside_volatility_20d"].windows) == (1, 20)

    roe_requirement = definitions_by_id["roe_ttm"].metadata["data_requirements"][0]
    assert roe_requirement == {
        "dataset_name": "fundamentals_pit",
        "dataset_version": definitions_by_id["roe_ttm"].dataset_versions["fundamentals_pit"],
        "field_name": "value",
        "item": "roe_ttm",
    }
    close_requirement = definitions_by_id["momentum_20d"].metadata["data_requirements"][0]
    assert close_requirement["dataset_name"] == "adjusted_daily_bars"
    assert close_requirement["field_name"] == "close"


def test_base_factor_formulas_compile_to_hand_authored_reference_plans() -> None:
    definitions = base_factor_definitions()
    plans = compile_base_factor_plans(definitions)

    assert tuple(plans) == EXPECTED_FACTOR_IDS

    for definition in definitions:
        plan = plans[definition.definition_id]
        reference = definition.metadata["reference_plan"]

        assert plan.definition_id == definition.definition_id
        assert plan.semantic_version == definition.semantic_version
        assert plan.required_inputs == tuple(reference["required_inputs"])
        assert plan.required_operators == tuple(reference["required_operators"])
        assert plan.lookback_periods == reference["lookback_periods"]
        assert dict(plan.dataset_versions) == reference["dataset_versions"]

    assert plans["momentum_20d"].required_operators == ("delay", "guarded_divide", "sub")
    assert plans["momentum_20d"].lookback_periods == 20
    assert plans["volatility_20d"].required_operators == (
        "delay",
        "guarded_divide",
        "rolling_std",
        "sub",
    )
    assert plans["volatility_20d"].lookback_periods == 21
    assert plans["downside_volatility_20d"].required_operators == (
        "comparison.lt",
        "delay",
        "guarded_divide",
        "rolling_std",
        "sub",
        "where",
    )
    assert plans["downside_volatility_20d"].lookback_periods == 21


def test_base_factor_catalog_rejects_missing_or_duplicate_required_factors() -> None:
    definitions = base_factor_definitions()

    with pytest.raises(ValueError, match="base factor catalog requires exactly"):
        BaseFactorCatalog(definitions=definitions[:-1])

    with pytest.raises(ValueError, match="duplicate base factor definition_id"):
        BaseFactorCatalog(definitions=definitions + (definitions[0],))
