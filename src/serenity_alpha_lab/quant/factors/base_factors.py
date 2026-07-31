from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.quant.factors.definitions import (
    FactorDefinition,
    FactorDirection,
    FactorFormula,
    FactorInput,
    FactorWindow,
    MissingValuePolicy,
    MissingValueStrategy,
)
from serenity_alpha_lab.quant.factors.dsl import FactorExpressionPlan, compile_factor_definition


BASE_FACTOR_CATALOG_VERSION = "base_factor_catalog@1.0.0"
BASE_FACTOR_CREATED_AT = datetime(2026, 7, 24, 9, 30, tzinfo=UTC)
BASE_FACTOR_CREATED_BY_RUN_ID = "run-sal-p3-007-base-factor-catalog"
BASE_FACTOR_SOURCE_COMMIT = "sal-p3-007-base-factor-definitions"
BASE_FACTOR_APPLICABLE_MARKETS = ("XSHG", "XSHE")
BASE_FACTOR_EXPECTED_CATEGORIES = ("growth", "liquidity", "momentum", "quality", "valuation", "volatility")
BASE_FACTOR_DEFINITION_IDS = (
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
BASE_FACTOR_DATASET_VERSIONS: Mapping[str, str] = MappingProxyType(
    {
        "fundamentals_pit": "dsv_" + "7" * 32,
        "adjusted_daily_bars": "dsv_" + "8" * 32,
    }
)


class BaseFactorCatalogError(ValueError):
    """Raised when the base factor catalog is incomplete or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class BaseFactorInputSpec:
    input_id: str
    dataset_name: str
    field_name: str
    data_type: str = "float64"
    item: str | None = None

    def to_factor_input(self, dataset_versions: Mapping[str, str]) -> FactorInput:
        return FactorInput(
            input_id=self.input_id,
            dataset_name=self.dataset_name,
            dataset_version=_dataset_version_for(self.dataset_name, dataset_versions),
            field_name=self.field_name,
            data_type=self.data_type,
            metadata=_metadata_if_present({"item": self.item}),
        )

    def to_data_requirement(self, dataset_versions: Mapping[str, str]) -> Mapping[str, object]:
        requirement: dict[str, object] = {
            "dataset_name": self.dataset_name,
            "dataset_version": _dataset_version_for(self.dataset_name, dataset_versions),
            "field_name": self.field_name,
        }
        if self.item is not None:
            requirement["item"] = self.item
        return MappingProxyType(requirement)


@dataclass(frozen=True, slots=True)
class BaseFactorSpec:
    definition_id: str
    name: str
    description: str
    category: str
    direction: FactorDirection | str
    expression: str
    inputs: Sequence[BaseFactorInputSpec]
    required_inputs: Sequence[str]
    required_operators: Sequence[str]
    lookback_periods: int
    windows: Sequence[int] = ()
    semantic_version: str = "1.0.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _required_string("definition_id", self.definition_id))
        object.__setattr__(self, "name", _required_string("name", self.name))
        object.__setattr__(self, "description", _required_string("description", self.description))
        object.__setattr__(self, "category", _required_string("category", self.category))
        if self.category not in BASE_FACTOR_EXPECTED_CATEGORIES:
            raise BaseFactorCatalogError(f"unsupported base factor category: {self.category}")
        object.__setattr__(self, "direction", FactorDirection(self.direction))
        object.__setattr__(self, "expression", _required_string("expression", self.expression))
        object.__setattr__(self, "inputs", tuple(self.inputs))
        if not self.inputs:
            raise BaseFactorCatalogError("base factor inputs are required")
        object.__setattr__(self, "required_inputs", _string_tuple("required input", self.required_inputs))
        object.__setattr__(self, "required_operators", _string_tuple("required operator", self.required_operators))
        if type(self.lookback_periods) is not int or self.lookback_periods < 0:
            raise BaseFactorCatalogError("lookback_periods must be a non-negative integer")
        object.__setattr__(self, "windows", _positive_int_tuple("window", self.windows))
        object.__setattr__(self, "semantic_version", _required_string("semantic_version", self.semantic_version))

    def to_definition(self, dataset_versions: Mapping[str, str]) -> FactorDefinition:
        factor_inputs = tuple(input_spec.to_factor_input(dataset_versions) for input_spec in self.inputs)
        reference_plan = {
            "required_inputs": tuple(self.required_inputs),
            "required_operators": tuple(self.required_operators),
            "lookback_periods": self.lookback_periods,
            "dataset_versions": _dataset_versions_for_inputs(factor_inputs),
        }
        metadata = {
            "catalog_version": BASE_FACTOR_CATALOG_VERSION,
            "applicable_markets": BASE_FACTOR_APPLICABLE_MARKETS,
            "data_requirements": tuple(input_spec.to_data_requirement(dataset_versions) for input_spec in self.inputs),
            "reference_plan": reference_plan,
        }
        return FactorDefinition.draft(
            definition_id=self.definition_id,
            semantic_version=self.semantic_version,
            name=self.name,
            description=self.description,
            category=self.category,
            direction=self.direction,
            formula=FactorFormula(
                expression=self.expression,
                language="serenity_factor_dsl",
                engine_version="serenity_factor_dsl@1.0.0",
            ),
            inputs=factor_inputs,
            windows=tuple(
                FactorWindow(name=f"lookback_{window}d", length=window, unit="trading_day", min_periods=1)
                for window in self.windows
            ),
            missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.DROP, max_missing_ratio=0.10),
            post_process=(),
            implementation_hash=_implementation_hash(self),
            created_at=BASE_FACTOR_CREATED_AT,
            created_by_run_id=BASE_FACTOR_CREATED_BY_RUN_ID,
            source_commit=BASE_FACTOR_SOURCE_COMMIT,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class BaseFactorCatalog:
    definitions: Sequence[FactorDefinition]
    catalog_version: str = BASE_FACTOR_CATALOG_VERSION

    def __post_init__(self) -> None:
        definitions = tuple(self.definitions)
        ids = tuple(definition.definition_id for definition in definitions)
        if len(set(ids)) != len(ids):
            raise BaseFactorCatalogError("duplicate base factor definition_id")
        if len(definitions) != len(BASE_FACTOR_DEFINITION_IDS):
            raise BaseFactorCatalogError(
                f"base factor catalog requires exactly {len(BASE_FACTOR_DEFINITION_IDS)} definitions"
            )
        if ids != BASE_FACTOR_DEFINITION_IDS:
            raise BaseFactorCatalogError(f"base factor ids changed: expected {BASE_FACTOR_DEFINITION_IDS}, got {ids}")
        categories = {definition.category for definition in definitions}
        if categories != set(BASE_FACTOR_EXPECTED_CATEGORIES):
            raise BaseFactorCatalogError("base factor catalog must cover every expected category")
        object.__setattr__(self, "definitions", definitions)
        object.__setattr__(self, "catalog_version", _required_string("catalog_version", self.catalog_version))

    @property
    def category_counts(self) -> dict[str, int]:
        counts = Counter(definition.category for definition in self.definitions)
        return {category: counts[category] for category in sorted(counts)}

    def to_record(self) -> dict[str, object]:
        return {
            "catalog_version": self.catalog_version,
            "factor_count": len(self.definitions),
            "factor_ids": [definition.definition_id for definition in self.definitions],
            "category_counts": self.category_counts,
            "definitions": [definition.to_record() for definition in self.definitions],
        }


def base_factor_catalog(
    *,
    dataset_versions: Mapping[str, str] | None = None,
) -> BaseFactorCatalog:
    return BaseFactorCatalog(definitions=base_factor_definitions(dataset_versions=dataset_versions))


def base_factor_definitions(
    *,
    dataset_versions: Mapping[str, str] | None = None,
) -> tuple[FactorDefinition, ...]:
    versions = _normalize_dataset_versions(dataset_versions)
    return tuple(spec.to_definition(versions) for spec in _BASE_FACTOR_SPECS)


def compile_base_factor_plans(
    definitions: Sequence[FactorDefinition] | None = None,
) -> dict[str, FactorExpressionPlan]:
    selected_definitions = tuple(definitions) if definitions is not None else base_factor_definitions()
    catalog = BaseFactorCatalog(definitions=selected_definitions)
    plans: dict[str, FactorExpressionPlan] = {}
    for definition in catalog.definitions:
        plan = compile_factor_definition(definition)
        reference = definition.metadata["reference_plan"]
        _assert_reference_plan(definition.definition_id, plan, reference)
        plans[definition.definition_id] = plan
    return plans


def _fundamental_input(input_id: str, *, item: str | None = None) -> BaseFactorInputSpec:
    return BaseFactorInputSpec(
        input_id=input_id,
        dataset_name="fundamentals_pit",
        field_name="value",
        item=item or input_id,
    )


def _adjusted_bar_input(input_id: str, *, field_name: str | None = None) -> BaseFactorInputSpec:
    return BaseFactorInputSpec(
        input_id=input_id,
        dataset_name="adjusted_daily_bars",
        field_name=field_name or input_id,
    )


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise BaseFactorCatalogError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise BaseFactorCatalogError(f"{field_name} is required")
    return stripped


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_required_string(field_name, value) for value in values)


def _positive_int_tuple(field_name: str, values: Sequence[int]) -> tuple[int, ...]:
    normalized: list[int] = []
    seen: set[int] = set()
    for value in values:
        if type(value) is not int or value <= 0:
            raise BaseFactorCatalogError(f"{field_name} must be a positive integer")
        if value in seen:
            raise BaseFactorCatalogError(f"duplicate {field_name}: {value}")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


_BASE_FACTOR_SPECS = (
    BaseFactorSpec(
        definition_id="roe_ttm",
        name="ROE TTM",
        description="Point-in-time trailing-twelve-month return on equity.",
        category="quality",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="roe_ttm",
        inputs=(_fundamental_input("roe_ttm"),),
        required_inputs=("roe_ttm",),
        required_operators=(),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="gross_margin_ttm",
        name="Gross Margin TTM",
        description="Point-in-time trailing-twelve-month gross margin.",
        category="quality",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="gross_margin_ttm",
        inputs=(_fundamental_input("gross_margin_ttm"),),
        required_inputs=("gross_margin_ttm",),
        required_operators=(),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="cash_flow_to_assets_ttm",
        name="Operating Cash Flow To Assets TTM",
        description="Point-in-time operating cash flow scaled by total assets.",
        category="quality",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="operating_cash_flow_ttm / total_assets",
        inputs=(_fundamental_input("operating_cash_flow_ttm"), _fundamental_input("total_assets")),
        required_inputs=("operating_cash_flow_ttm", "total_assets"),
        required_operators=("guarded_divide",),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="earnings_yield_ttm",
        name="Earnings Yield TTM",
        description="Point-in-time net profit scaled by market capitalization.",
        category="valuation",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="net_profit_ttm / market_cap",
        inputs=(_fundamental_input("net_profit_ttm"), _fundamental_input("market_cap")),
        required_inputs=("market_cap", "net_profit_ttm"),
        required_operators=("guarded_divide",),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="book_to_market",
        name="Book To Market",
        description="Point-in-time book value scaled by market capitalization.",
        category="valuation",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="book_value / market_cap",
        inputs=(_fundamental_input("book_value"), _fundamental_input("market_cap")),
        required_inputs=("book_value", "market_cap"),
        required_operators=("guarded_divide",),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="sales_yield_ttm",
        name="Sales Yield TTM",
        description="Point-in-time revenue scaled by market capitalization.",
        category="valuation",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="revenue_ttm / market_cap",
        inputs=(_fundamental_input("revenue_ttm"), _fundamental_input("market_cap")),
        required_inputs=("market_cap", "revenue_ttm"),
        required_operators=("guarded_divide",),
        lookback_periods=0,
    ),
    BaseFactorSpec(
        definition_id="revenue_growth_yoy",
        name="Revenue Growth YoY",
        description="Point-in-time year-over-year revenue growth using a 252-trading-day lag.",
        category="growth",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="revenue_ttm / delay(revenue_ttm, 252) - 1",
        inputs=(_fundamental_input("revenue_ttm"),),
        required_inputs=("revenue_ttm",),
        required_operators=("delay", "guarded_divide", "sub"),
        lookback_periods=252,
        windows=(252,),
    ),
    BaseFactorSpec(
        definition_id="net_profit_growth_yoy",
        name="Net Profit Growth YoY",
        description="Point-in-time year-over-year net profit growth using a 252-trading-day lag.",
        category="growth",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="net_profit_ttm / delay(net_profit_ttm, 252) - 1",
        inputs=(_fundamental_input("net_profit_ttm"),),
        required_inputs=("net_profit_ttm",),
        required_operators=("delay", "guarded_divide", "sub"),
        lookback_periods=252,
        windows=(252,),
    ),
    BaseFactorSpec(
        definition_id="roe_change_yoy",
        name="ROE Change YoY",
        description="Point-in-time change in trailing ROE versus a 252-trading-day lag.",
        category="growth",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="roe_ttm - delay(roe_ttm, 252)",
        inputs=(_fundamental_input("roe_ttm"),),
        required_inputs=("roe_ttm",),
        required_operators=("delay", "sub"),
        lookback_periods=252,
        windows=(252,),
    ),
    BaseFactorSpec(
        definition_id="momentum_20d",
        name="20D Momentum",
        description="Close-to-close momentum over 20 trading days.",
        category="momentum",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="close / delay(close, 20) - 1",
        inputs=(_adjusted_bar_input("close"),),
        required_inputs=("close",),
        required_operators=("delay", "guarded_divide", "sub"),
        lookback_periods=20,
        windows=(20,),
    ),
    BaseFactorSpec(
        definition_id="momentum_60d",
        name="60D Momentum",
        description="Close-to-close momentum over 60 trading days.",
        category="momentum",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="close / delay(close, 60) - 1",
        inputs=(_adjusted_bar_input("close"),),
        required_inputs=("close",),
        required_operators=("delay", "guarded_divide", "sub"),
        lookback_periods=60,
        windows=(60,),
    ),
    BaseFactorSpec(
        definition_id="volatility_20d",
        name="20D Realized Volatility",
        description="Rolling standard deviation of one-day adjusted close returns.",
        category="volatility",
        direction=FactorDirection.LOWER_IS_BETTER,
        expression="rolling_std(close / delay(close, 1) - 1, 20)",
        inputs=(_adjusted_bar_input("close"),),
        required_inputs=("close",),
        required_operators=("delay", "guarded_divide", "rolling_std", "sub"),
        lookback_periods=21,
        windows=(1, 20),
    ),
    BaseFactorSpec(
        definition_id="downside_volatility_20d",
        name="20D Downside Volatility",
        description="Rolling standard deviation of negative one-day adjusted close returns.",
        category="volatility",
        direction=FactorDirection.LOWER_IS_BETTER,
        expression="rolling_std(where(close / delay(close, 1) - 1 < 0, close / delay(close, 1) - 1, 0), 20)",
        inputs=(_adjusted_bar_input("close"),),
        required_inputs=("close",),
        required_operators=("comparison.lt", "delay", "guarded_divide", "rolling_std", "sub", "where"),
        lookback_periods=21,
        windows=(1, 20),
    ),
    BaseFactorSpec(
        definition_id="amount_liquidity_20d",
        name="20D Amount Liquidity",
        description="Rolling average traded amount over 20 trading days.",
        category="liquidity",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="rolling_mean(amount, 20)",
        inputs=(_adjusted_bar_input("amount"),),
        required_inputs=("amount",),
        required_operators=("rolling_mean",),
        lookback_periods=20,
        windows=(20,),
    ),
    BaseFactorSpec(
        definition_id="volume_liquidity_20d",
        name="20D Volume Liquidity",
        description="Rolling average traded volume over 20 trading days.",
        category="liquidity",
        direction=FactorDirection.HIGHER_IS_BETTER,
        expression="rolling_mean(volume, 20)",
        inputs=(_adjusted_bar_input("volume"),),
        required_inputs=("volume",),
        required_operators=("rolling_mean",),
        lookback_periods=20,
        windows=(20,),
    ),
)


def _normalize_dataset_versions(dataset_versions: Mapping[str, str] | None) -> Mapping[str, str]:
    merged = dict(BASE_FACTOR_DATASET_VERSIONS)
    if dataset_versions:
        merged.update(dataset_versions)
    return MappingProxyType(merged)


def _dataset_version_for(dataset_name: str, dataset_versions: Mapping[str, str]) -> str:
    try:
        return dataset_versions[dataset_name]
    except KeyError as exc:
        raise BaseFactorCatalogError(f"dataset version is required for {dataset_name}") from exc


def _dataset_versions_for_inputs(inputs: Sequence[FactorInput]) -> Mapping[str, str]:
    versions: dict[str, str] = {}
    for input_spec in inputs:
        existing = versions.get(input_spec.dataset_name)
        if existing is not None and existing != input_spec.dataset_version:
            raise BaseFactorCatalogError(f"conflicting dataset version for {input_spec.dataset_name}")
        versions[input_spec.dataset_name] = input_spec.dataset_version
    return MappingProxyType(versions)


def _assert_reference_plan(
    definition_id: str,
    plan: FactorExpressionPlan,
    reference: object,
) -> None:
    if not isinstance(reference, Mapping):
        raise BaseFactorCatalogError(f"{definition_id} missing reference plan")
    if tuple(reference["required_inputs"]) != plan.required_inputs:  # type: ignore[index]
        raise BaseFactorCatalogError(f"{definition_id} required_inputs do not match reference")
    if tuple(reference["required_operators"]) != plan.required_operators:  # type: ignore[index]
        raise BaseFactorCatalogError(f"{definition_id} required_operators do not match reference")
    if reference["lookback_periods"] != plan.lookback_periods:  # type: ignore[index]
        raise BaseFactorCatalogError(f"{definition_id} lookback_periods do not match reference")
    if dict(reference["dataset_versions"]) != dict(plan.dataset_versions):  # type: ignore[index]
        raise BaseFactorCatalogError(f"{definition_id} dataset_versions do not match reference")


def _implementation_hash(spec: BaseFactorSpec) -> str:
    payload = {
        "catalog_version": BASE_FACTOR_CATALOG_VERSION,
        "definition_id": spec.definition_id,
        "semantic_version": spec.semantic_version,
        "expression": spec.expression,
        "required_inputs": tuple(spec.required_inputs),
        "required_operators": tuple(spec.required_operators),
        "lookback_periods": spec.lookback_periods,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _metadata_if_present(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({key: value for key, value in values.items() if value is not None})


__all__ = [
    "BASE_FACTOR_APPLICABLE_MARKETS",
    "BASE_FACTOR_CATALOG_VERSION",
    "BASE_FACTOR_DATASET_VERSIONS",
    "BASE_FACTOR_DEFINITION_IDS",
    "BASE_FACTOR_EXPECTED_CATEGORIES",
    "BaseFactorCatalog",
    "BaseFactorCatalogError",
    "BaseFactorInputSpec",
    "BaseFactorSpec",
    "base_factor_catalog",
    "base_factor_definitions",
    "compile_base_factor_plans",
]
