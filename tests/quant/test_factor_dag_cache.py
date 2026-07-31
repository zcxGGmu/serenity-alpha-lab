from __future__ import annotations

import json
from datetime import UTC, date, datetime

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
from serenity_alpha_lab.quant.factors.engine import (
    FACTOR_ENGINE_VERSION,
    FACTOR_CACHE_MANIFEST_SCHEMA_NAME,
    FactorCacheKey,
    FactorCachePartition,
    FactorCacheQualityGate,
    FactorCacheQualityStatus,
    FactorDagBuildSpec,
    FactorEngineError,
    FactorIncrementalChangeSet,
    FactorPartitionKind,
    FactorPartitionPlan,
    build_factor_dag,
    plan_factor_cache_partitions,
    plan_incremental_factor_recompute,
    publish_factor_cache_manifest,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore

BARS_VERSION = "dsv_" + "8" * 32
FUNDAMENTALS_VERSION = "dsv_" + "7" * 32
REVISED_FUNDAMENTALS_VERSION = "dsv_" + "6" * 32
UNIVERSE_VERSION = "dsv_" + "9" * 32
MOMENTUM_VERSION = "fdv_" + "1" * 32
RANKED_MOMENTUM_VERSION = "fdv_" + "2" * 32
BOOK_TO_MARKET_VERSION = "fdv_" + "3" * 32
IMPLEMENTATION_HASH = "sha256:" + "f" * 64
TRADE_DATES = (date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6))
INSTRUMENTS = ("600000.XSHG", "600001.XSHG")


def test_factor_dag_build_spec_requires_concrete_versions_and_records_cache_scope() -> None:
    spec = _build_spec()

    assert spec.engine_version == FACTOR_ENGINE_VERSION
    assert spec.dataset_versions == {"adjusted_daily_bars": BARS_VERSION}
    assert spec.factor_versions == {
        "momentum_20d": MOMENTUM_VERSION,
        "ranked_momentum_20d": RANKED_MOMENTUM_VERSION,
    }
    assert spec.universe_version_id == UNIVERSE_VERSION
    assert spec.date_range == (TRADE_DATES[0], TRADE_DATES[-1])

    record = spec.to_record()
    assert record["schema_name"] == "quant.factor_engine_dag"
    assert record["engine_version"] == FACTOR_ENGINE_VERSION
    assert record["universe_version_id"] == UNIVERSE_VERSION
    json.dumps(record, sort_keys=True)

    with pytest.raises(FactorEngineError, match="concrete Dataset Version"):
        _build_spec(dataset_versions={"adjusted_daily_bars": "latest"})

    with pytest.raises(FactorEngineError, match="universe_version_id"):
        _build_spec(universe_version_id="latest")

    with pytest.raises(FactorEngineError, match="fdv_"):
        _build_spec(factor_versions={"momentum_20d": "bad-version"})


def test_build_factor_dag_deduplicates_common_subexpressions_and_preserves_dependencies() -> None:
    dag = build_factor_dag(_factor_definitions(), _build_spec())

    assert dag.schema_name == "quant.factor_engine_dag"
    assert dag.engine_version == FACTOR_ENGINE_VERSION
    assert dag.dataset_versions == {"adjusted_daily_bars": BARS_VERSION}
    assert dag.factor_dataset_versions == {
        "momentum_20d": {"adjusted_daily_bars": BARS_VERSION},
        "ranked_momentum_20d": {"adjusted_daily_bars": BARS_VERSION},
    }
    assert dag.factor_versions == {
        "momentum_20d": MOMENTUM_VERSION,
        "ranked_momentum_20d": RANKED_MOMENTUM_VERSION,
    }
    assert set(dag.factor_roots) == {"momentum_20d", "ranked_momentum_20d"}

    delay_nodes = [node for node in dag.nodes if node.operation == "delay"]
    guarded_divide_nodes = [node for node in dag.nodes if node.operation == "guarded_divide"]
    assert len(delay_nodes) == 1
    assert len(guarded_divide_nodes) == 1
    assert "momentum_20d" in guarded_divide_nodes[0].factor_definition_ids
    assert "ranked_momentum_20d" in guarded_divide_nodes[0].factor_definition_ids

    record = dag.to_record()
    assert record["node_count"] == len(dag.nodes)
    assert record["factor_dataset_versions"] == {
        "momentum_20d": {"adjusted_daily_bars": BARS_VERSION},
        "ranked_momentum_20d": {"adjusted_daily_bars": BARS_VERSION},
    }
    assert any(node["operation"] == "rank" for node in record["nodes"])
    json.dumps(record, sort_keys=True)

    with pytest.raises(FactorEngineError, match="does not match"):
        build_factor_dag(_factor_definitions()[:1], _build_spec())


def test_build_factor_dag_rejects_mismatched_published_factor_version() -> None:
    published = _factor_definition(
        definition_id="momentum_20d",
        expression="close / delay(close, 20) - 1",
    ).publish(
        published_at=datetime(2026, 7, 24, 10, 0, tzinfo=UTC),
        published_by_run_id="run-factor-engine",
        published_by_stage_id="stage-factor-engine",
    )

    assert published.version_id is not None
    with pytest.raises(FactorEngineError, match="factor version mismatch"):
        build_factor_dag((published,), _build_spec(factor_versions={"momentum_20d": MOMENTUM_VERSION}))

    dag = build_factor_dag((published,), _build_spec(factor_versions={"momentum_20d": published.version_id}))
    assert dag.factor_versions == {"momentum_20d": published.version_id}


def test_partition_plan_derives_complete_cache_keys_for_time_series_and_cross_section_work() -> None:
    dag = build_factor_dag(_factor_definitions(), _build_spec())

    first = plan_factor_cache_partitions(dag, instruments=INSTRUMENTS, trade_dates=TRADE_DATES)
    repeated = plan_factor_cache_partitions(dag, instruments=INSTRUMENTS, trade_dates=TRADE_DATES)

    assert first.partition_count == len(first.partitions)
    assert tuple(partition.cache_key.key for partition in first.partitions) == tuple(
        partition.cache_key.key for partition in repeated.partitions
    )
    assert first.performance_budget.to_record() == {
        "expected_scan_rows": 12,
        "partition_count": first.partition_count,
        "max_lookback_periods": 20,
    }

    time_series = [partition for partition in first.partitions if partition.partition_kind == "time_series"]
    cross_section = [partition for partition in first.partitions if partition.partition_kind == "cross_section"]
    assert {partition.instrument_id for partition in time_series} == set(INSTRUMENTS)
    assert {partition.trade_date for partition in time_series} == set(TRADE_DATES)
    assert {partition.trade_date for partition in cross_section} == set(TRADE_DATES)
    assert all(
        partition.cache_key.dataset_versions == {"adjusted_daily_bars": BARS_VERSION} for partition in first.partitions
    )
    assert all(partition.cache_key.universe_version_id == UNIVERSE_VERSION for partition in first.partitions)
    assert all(partition.cache_key.engine_version == FACTOR_ENGINE_VERSION for partition in first.partitions)

    sample_key = first.partitions[0].cache_key.to_record()
    assert sample_key["date_range"] == [TRADE_DATES[0].isoformat(), TRADE_DATES[-1].isoformat()]
    assert sample_key["key"].startswith("fck_")
    json.dumps(first.to_record(), sort_keys=True)


def test_partition_plan_rejects_out_of_range_dates_and_deduplicates_inputs() -> None:
    dag = build_factor_dag(_factor_definitions(), _build_spec())

    with pytest.raises(FactorEngineError, match="outside DAG date_range"):
        plan_factor_cache_partitions(
            dag,
            instruments=INSTRUMENTS,
            trade_dates=(TRADE_DATES[0], date(2026, 1, 9)),
        )

    plan = plan_factor_cache_partitions(
        dag,
        instruments=(INSTRUMENTS[0], INSTRUMENTS[0], INSTRUMENTS[1]),
        trade_dates=(TRADE_DATES[0], TRADE_DATES[0], TRADE_DATES[1]),
    )

    partition_ids = tuple(partition.partition_id for partition in plan.partitions)
    assert len(partition_ids) == len(set(partition_ids))
    assert {partition.trade_date for partition in plan.partitions} == set(TRADE_DATES[:2])
    assert plan.performance_budget.expected_scan_rows == 8

    with pytest.raises(FactorEngineError, match="partition_id values must be unique"):
        FactorPartitionPlan(
            dag=dag,
            partitions=(plan.partitions[0], plan.partitions[0]),
            performance_budget=plan.performance_budget,
        )


def test_incremental_recompute_uses_factor_specific_dataset_dependencies() -> None:
    definitions = (
        _factor_definition(
            definition_id="momentum_20d",
            expression="close / delay(close, 20) - 1",
        ),
        _fundamental_factor_definition(),
    )
    dag = build_factor_dag(
        definitions,
        _build_spec(
            dataset_versions={"adjusted_daily_bars": BARS_VERSION, "fundamentals": FUNDAMENTALS_VERSION},
            factor_versions={
                "momentum_20d": MOMENTUM_VERSION,
                "book_to_market": BOOK_TO_MARKET_VERSION,
            },
        ),
    )
    partition_plan = plan_factor_cache_partitions(dag, instruments=INSTRUMENTS, trade_dates=TRADE_DATES)

    assert dag.factor_dataset_versions == {
        "book_to_market": {"fundamentals": FUNDAMENTALS_VERSION},
        "momentum_20d": {"adjusted_daily_bars": BARS_VERSION},
    }
    assert all(
        partition.cache_key.dataset_versions == {"adjusted_daily_bars": BARS_VERSION}
        for partition in partition_plan.partitions
        if partition.factor_definition_id == "momentum_20d"
    )
    assert all(
        partition.cache_key.dataset_versions == {"fundamentals": FUNDAMENTALS_VERSION}
        for partition in partition_plan.partitions
        if partition.factor_definition_id == "book_to_market"
    )

    fundamentals_change = plan_incremental_factor_recompute(
        partition_plan,
        FactorIncrementalChangeSet(changed_dataset_versions={"fundamentals": REVISED_FUNDAMENTALS_VERSION}),
    )
    assert {partition.factor_definition_id for partition in fundamentals_change.partitions} == {"book_to_market"}

    bars_change = plan_incremental_factor_recompute(
        partition_plan,
        FactorIncrementalChangeSet(changed_dataset_versions={"adjusted_daily_bars": BARS_VERSION}),
    )
    assert {partition.factor_definition_id for partition in bars_change.partitions} == {"momentum_20d"}


def test_cache_dtos_reject_inconsistent_partition_identity() -> None:
    dag = build_factor_dag(_factor_definitions(), _build_spec())
    partition_plan = plan_factor_cache_partitions(dag, instruments=INSTRUMENTS, trade_dates=TRADE_DATES)
    time_series = next(
        partition
        for partition in partition_plan.partitions
        if partition.partition_kind is FactorPartitionKind.TIME_SERIES
    )
    cross_section = next(
        partition
        for partition in partition_plan.partitions
        if partition.partition_kind is FactorPartitionKind.CROSS_SECTION
    )

    with pytest.raises(FactorEngineError, match="time_series partitions require instrument_id"):
        FactorCacheKey(
            factor_definition_id=time_series.factor_definition_id,
            factor_version_id=time_series.factor_version_id,
            dataset_versions=time_series.cache_key.dataset_versions,
            universe_version_id=time_series.cache_key.universe_version_id,
            date_range=time_series.cache_key.date_range,
            engine_version=time_series.cache_key.engine_version,
            partition_id="fcp_missing_instrument",
            partition_kind=FactorPartitionKind.TIME_SERIES,
            trade_date=time_series.trade_date,
        )

    with pytest.raises(FactorEngineError, match="cross_section partitions cannot include instrument_id"):
        FactorCacheKey(
            factor_definition_id=cross_section.factor_definition_id,
            factor_version_id=cross_section.factor_version_id,
            dataset_versions=cross_section.cache_key.dataset_versions,
            universe_version_id=cross_section.cache_key.universe_version_id,
            date_range=cross_section.cache_key.date_range,
            engine_version=cross_section.cache_key.engine_version,
            partition_id="fcp_unexpected_instrument",
            partition_kind=FactorPartitionKind.CROSS_SECTION,
            trade_date=cross_section.trade_date,
            instrument_id=INSTRUMENTS[0],
        )

    mismatched_key = FactorCacheKey(
        factor_definition_id=time_series.factor_definition_id,
        factor_version_id=time_series.factor_version_id,
        dataset_versions=time_series.cache_key.dataset_versions,
        universe_version_id=time_series.cache_key.universe_version_id,
        date_range=time_series.cache_key.date_range,
        engine_version=time_series.cache_key.engine_version,
        partition_id=time_series.partition_id,
        partition_kind=FactorPartitionKind.TIME_SERIES,
        trade_date=TRADE_DATES[-1],
        instrument_id=time_series.instrument_id,
    )
    with pytest.raises(FactorEngineError, match="cache_key trade_date"):
        FactorCachePartition(
            partition_id=time_series.partition_id,
            partition_kind=time_series.partition_kind,
            factor_definition_id=time_series.factor_definition_id,
            factor_version_id=time_series.factor_version_id,
            trade_date=time_series.trade_date,
            start_date=time_series.start_date,
            end_date=time_series.end_date,
            cache_key=mismatched_key,
            required_operators=time_series.required_operators,
            lookback_periods=time_series.lookback_periods,
            instrument_id=time_series.instrument_id,
        )


def test_incremental_recompute_and_quality_gate_prevent_failed_cache_publication(tmp_path) -> None:
    dag = build_factor_dag(_factor_definitions(), _build_spec())
    partition_plan = plan_factor_cache_partitions(dag, instruments=INSTRUMENTS, trade_dates=TRADE_DATES)

    new_day_plan = plan_incremental_factor_recompute(
        partition_plan,
        FactorIncrementalChangeSet(changed_trade_dates=(TRADE_DATES[-1],)),
    )
    assert new_day_plan.reason == "incremental"
    assert new_day_plan.recompute_partition_count < partition_plan.partition_count
    assert {partition.trade_date for partition in new_day_plan.partitions} == {TRADE_DATES[-1]}

    historical_change = plan_incremental_factor_recompute(
        partition_plan,
        FactorIncrementalChangeSet(changed_trade_dates=(TRADE_DATES[0],)),
    )
    assert historical_change.recompute_partition_count == partition_plan.partition_count

    factor_change = plan_incremental_factor_recompute(
        partition_plan,
        FactorIncrementalChangeSet(changed_factor_version_ids=(MOMENTUM_VERSION,)),
    )
    assert {partition.factor_definition_id for partition in factor_change.partitions} == {"momentum_20d"}

    failed_gate = FactorCacheQualityGate(
        status=FactorCacheQualityStatus.FAILED,
        issue_count=1,
        metrics={"missing_ratio": 0.2},
    )
    store = LocalArtifactStore(tmp_path / "artifacts")
    with pytest.raises(FactorEngineError, match="failed quality gate"):
        publish_factor_cache_manifest(
            partition_plan,
            failed_gate,
            store,
            created_at=datetime(2026, 1, 6, 17, 0, tzinfo=UTC),
        )

    passed_gate = FactorCacheQualityGate(
        status=FactorCacheQualityStatus.PASSED,
        issue_count=0,
        metrics={"scan_rows": partition_plan.performance_budget.expected_scan_rows, "peak_memory_mb": 12.5},
        operator_timings_ms={"delay": 3.0, "rank": 1.5},
    )
    manifest = publish_factor_cache_manifest(
        partition_plan,
        passed_gate,
        store,
        created_at=datetime(2026, 1, 6, 17, 0, tzinfo=UTC),
    )
    repeated = publish_factor_cache_manifest(
        partition_plan,
        passed_gate,
        store,
        created_at=datetime(2026, 1, 6, 17, 0, tzinfo=UTC),
    )

    assert repeated.artifact_id == manifest.artifact_id
    assert manifest.schema_name == FACTOR_CACHE_MANIFEST_SCHEMA_NAME
    payload = json.loads(store.get_bytes(manifest.artifact_id).decode("utf-8"))
    assert payload["quality_gate"]["status"] == "passed"
    assert payload["partition_plan"]["partition_count"] == partition_plan.partition_count
    assert payload["partition_plan"]["dag"]["dag_id"] == dag.dag_id


def _build_spec(**overrides) -> FactorDagBuildSpec:
    values = {
        "run_id": "run-factor-engine",
        "stage_id": "stage-factor-engine",
        "dataset_versions": {"adjusted_daily_bars": BARS_VERSION},
        "factor_versions": {
            "momentum_20d": MOMENTUM_VERSION,
            "ranked_momentum_20d": RANKED_MOMENTUM_VERSION,
        },
        "universe_version_id": UNIVERSE_VERSION,
        "date_range": (TRADE_DATES[0], TRADE_DATES[-1]),
    }
    values.update(overrides)
    return FactorDagBuildSpec(**values)


def _factor_definitions() -> tuple[FactorDefinition, ...]:
    return (
        _factor_definition(
            definition_id="momentum_20d",
            expression="close / delay(close, 20) - 1",
        ),
        _factor_definition(
            definition_id="ranked_momentum_20d",
            expression="rank(close / delay(close, 20) - 1)",
        ),
    )


def _factor_definition(
    *,
    definition_id: str,
    expression: str,
    inputs: tuple[FactorInput, ...] | None = None,
    windows: tuple[FactorWindow, ...] | None = None,
    category: str = "momentum",
) -> FactorDefinition:
    return FactorDefinition.draft(
        definition_id=definition_id,
        semantic_version="1.0.0",
        name=definition_id.replace("_", " ").title(),
        description=f"Test factor {definition_id}.",
        category=category,
        direction=FactorDirection.HIGHER_IS_BETTER,
        formula=FactorFormula(expression=expression, engine_version="serenity_factor_dsl@1.0.0"),
        inputs=inputs
        or (
            FactorInput(
                input_id="close",
                dataset_name="adjusted_daily_bars",
                dataset_version=BARS_VERSION,
                field_name="close",
                data_type="float64",
            ),
        ),
        windows=(
            windows
            if windows is not None
            else (FactorWindow(name="lookback_20", length=20, unit="trading_day", min_periods=1),)
        ),
        missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.DROP),
        implementation_hash=IMPLEMENTATION_HASH,
        created_at=datetime(2026, 7, 24, 9, 30, tzinfo=UTC),
        created_by_run_id="run-factor-engine",
        source_commit="sal-p3-010",
    )


def _fundamental_factor_definition() -> FactorDefinition:
    return _factor_definition(
        definition_id="book_to_market",
        expression="book_value / market_cap",
        category="valuation",
        inputs=(
            FactorInput(
                input_id="book_value",
                dataset_name="fundamentals",
                dataset_version=FUNDAMENTALS_VERSION,
                field_name="book_value",
                data_type="float64",
            ),
            FactorInput(
                input_id="market_cap",
                dataset_name="fundamentals",
                dataset_version=FUNDAMENTALS_VERSION,
                field_name="market_cap",
                data_type="float64",
            ),
        ),
        windows=(),
    )
