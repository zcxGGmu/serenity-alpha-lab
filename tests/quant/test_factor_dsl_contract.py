from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.quant.factors.definitions import (
    FactorDefinition,
    FactorDirection,
    FactorFormula,
    FactorInput,
    FactorWindow,
    MissingValuePolicy,
    MissingValueStrategy,
)
from serenity_alpha_lab.quant.factors.dsl import (
    FACTOR_DSL_ENGINE_VERSION,
    FactorDslError,
    compile_factor_definition,
    compile_factor_expression,
)


BARS_VERSION = "dsv_" + "b" * 32
IMPLEMENTATION_HASH = "sha256:" + "f" * 64


def test_factor_dsl_compiles_delay_rank_arithmetic_and_conditionals() -> None:
    plan = compile_factor_expression(
        "where(close > delay(close, 20), rank(close / delay(close, 20) - 1), 0)",
        inputs=_inputs("close"),
        windows=_windows(20),
    )

    assert plan.engine_version == FACTOR_DSL_ENGINE_VERSION
    assert plan.expression == "where(close > delay(close, 20), rank(close / delay(close, 20) - 1), 0)"
    assert plan.required_inputs == ("close",)
    assert plan.required_operators == (
        "comparison.gt",
        "delay",
        "guarded_divide",
        "rank",
        "sub",
        "where",
    )
    assert plan.lookback_periods == 20
    assert plan.node.operation == "where"

    record = plan.to_record()
    assert record["engine_version"] == FACTOR_DSL_ENGINE_VERSION
    assert record["required_inputs"] == ["close"]
    assert record["lookback_periods"] == 20
    assert "guarded_divide" in record["required_operators"]
    json.dumps(record, sort_keys=True)


def test_factor_dsl_validates_rolling_windows_against_declared_factor_windows() -> None:
    plan = compile_factor_expression(
        "rolling_mean(close, 20) / rolling_std(close, 20)",
        inputs=_inputs("close"),
        windows=_windows(20),
    )

    assert plan.required_inputs == ("close",)
    assert plan.required_operators == ("guarded_divide", "rolling_mean", "rolling_std")
    assert plan.lookback_periods == 20

    with pytest.raises(FactorDslError, match="declared FactorWindow"):
        compile_factor_expression(
            "rolling_mean(close, 60)",
            inputs=_inputs("close"),
            windows=_windows(20),
        )

    with pytest.raises(FactorDslError, match="declared FactorWindow"):
        compile_factor_expression(
            "delay(close, 60)",
            inputs=_inputs("close"),
            windows=_windows(20),
        )


def test_factor_dsl_compiles_from_factor_definition_and_preserves_dataset_versions() -> None:
    definition = FactorDefinition.draft(
        definition_id="momentum_20d",
        semantic_version="1.0.0",
        name="20D Momentum",
        description="Close-to-close momentum with guarded division.",
        category="momentum",
        direction=FactorDirection.HIGHER_IS_BETTER,
        formula=FactorFormula(
            expression="close / delay(close, 20) - 1",
            engine_version=FACTOR_DSL_ENGINE_VERSION,
        ),
        inputs=_inputs("close"),
        windows=_windows(20),
        missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.DROP),
        implementation_hash=IMPLEMENTATION_HASH,
        created_at=datetime(2026, 7, 24, 9, 30, tzinfo=UTC),
        created_by_run_id="run-factor-dsl",
        source_commit="33611597",
    )

    plan = compile_factor_definition(definition)

    assert plan.definition_id == "momentum_20d"
    assert plan.semantic_version == "1.0.0"
    assert plan.dataset_versions == {"adjusted_daily_bars": BARS_VERSION}
    assert plan.required_operators == ("delay", "guarded_divide", "sub")
    assert plan.lookback_periods == 20


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo bad')",
        "close.__class__",
        "globals()",
        "[x for x in close]",
        "open('/tmp/x')",
        "delay(close, -1)",
        "delay(close, 0)",
        "delay(close, lookback)",
        "rolling_mean(close, -20)",
        "close[0]",
    ],
)
def test_factor_dsl_rejects_arbitrary_python_and_future_references(expression: str) -> None:
    with pytest.raises(FactorDslError):
        compile_factor_expression(expression, inputs=_inputs("close"), windows=_windows(20))


def test_factor_dsl_rejects_unknown_inputs_and_unsafe_type_shapes() -> None:
    with pytest.raises(FactorDslError, match="unknown input"):
        compile_factor_expression("close + unknown_field", inputs=_inputs("close"), windows=_windows(20))

    with pytest.raises(FactorDslError, match="numeric"):
        compile_factor_expression("rank('close')", inputs=_inputs("close"), windows=_windows(20))

    with pytest.raises(FactorDslError, match="boolean"):
        compile_factor_expression("where(close, close, 0)", inputs=_inputs("close"), windows=_windows(20))

    with pytest.raises(FactorDslError, match="numeric data_type"):
        compile_factor_expression(
            "industry_code + 1",
            inputs=_inputs_with_data_type(("industry_code", "string")),
            windows=_windows(20),
        )

    with pytest.raises(FactorDslError, match="not allowed"):
        compile_factor_expression("eval(close)", inputs=_inputs("close"), windows=_windows(20))

    with pytest.raises(FactorDslError, match="language"):
        compile_factor_definition(
            FactorDefinition.draft(
                definition_id="bad_language",
                semantic_version="1.0.0",
                name="Bad Language",
                description="Rejects non-DSL formula languages.",
                category="quality",
                direction=FactorDirection.HIGHER_IS_BETTER,
                formula=FactorFormula(expression="close", language="python"),
                inputs=_inputs("close"),
                windows=_windows(20),
                missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.DROP),
                implementation_hash=IMPLEMENTATION_HASH,
                created_at=datetime(2026, 7, 24, 9, 30, tzinfo=UTC),
                created_by_run_id="run-factor-dsl",
                source_commit="33611597",
            )
        )


def _inputs(*input_ids: str) -> tuple[FactorInput, ...]:
    return _inputs_with_data_type(*((input_id, "float64") for input_id in input_ids))


def _inputs_with_data_type(*input_specs: tuple[str, str | None]) -> tuple[FactorInput, ...]:
    return tuple(
        FactorInput(
            input_id=input_id,
            dataset_name="adjusted_daily_bars",
            dataset_version=BARS_VERSION,
            field_name=input_id,
            data_type=data_type,
        )
        for input_id, data_type in input_specs
    )


def _windows(*lengths: int) -> tuple[FactorWindow, ...]:
    return tuple(
        FactorWindow(name=f"lookback_{length}", length=length, unit="trading_day", min_periods=1)
        for length in lengths
    )
