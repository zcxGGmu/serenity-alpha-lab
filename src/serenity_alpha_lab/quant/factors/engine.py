from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.factors.definitions import FactorDefinition
from serenity_alpha_lab.quant.factors.dsl import FactorExpressionNode, compile_factor_definition

FACTOR_ENGINE_CONTRACT_VERSION = "1.0.0"
FACTOR_ENGINE_VERSION = "factor_engine@1.0.0"
FACTOR_ENGINE_DAG_SCHEMA_NAME = "quant.factor_engine_dag"
FACTOR_ENGINE_DAG_SCHEMA_VERSION = "1.0.0"
FACTOR_CACHE_MANIFEST_SCHEMA_NAME = "quant.factor_cache_manifest"
FACTOR_CACHE_MANIFEST_SCHEMA_VERSION = "1.0.0"

_FACTOR_VERSION_ID_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")


class FactorEngineError(ValueError):
    """Raised when Factor Engine DAG/cache planning input is invalid."""


class FactorPartitionKind(StrEnum):
    TIME_SERIES = "time_series"
    CROSS_SECTION = "cross_section"


class FactorCacheQualityStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FactorDagBuildSpec:
    run_id: str
    stage_id: str
    dataset_versions: Mapping[str, str]
    factor_versions: Mapping[str, str]
    universe_version_id: str
    date_range: Sequence[date]
    contract_version: str = FACTOR_ENGINE_CONTRACT_VERSION
    schema_name: str = FACTOR_ENGINE_DAG_SCHEMA_NAME
    schema_version: str = FACTOR_ENGINE_DAG_SCHEMA_VERSION
    engine_version: str = FACTOR_ENGINE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if not self.dataset_versions:
            raise FactorEngineError("dataset_versions are required")
        dataset_versions = {
            _required_string("dataset name", name): _validate_dataset_version(version)
            for name, version in self.dataset_versions.items()
        }
        object.__setattr__(self, "dataset_versions", MappingProxyType(dataset_versions))
        if not self.factor_versions:
            raise FactorEngineError("factor_versions are required")
        factor_versions = {
            _required_string("factor definition id", factor_id): _validate_factor_version_id(version)
            for factor_id, version in self.factor_versions.items()
        }
        object.__setattr__(self, "factor_versions", MappingProxyType(factor_versions))
        object.__setattr__(
            self,
            "universe_version_id",
            _validate_dataset_version(self.universe_version_id, field_name="universe_version_id"),
        )
        object.__setattr__(self, "date_range", _normalize_date_range(self.date_range))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "dataset_versions": dict(self.dataset_versions),
            "factor_versions": dict(self.factor_versions),
            "universe_version_id": self.universe_version_id,
            "date_range": [self.date_range[0].isoformat(), self.date_range[1].isoformat()],
        }


@dataclass(frozen=True, slots=True)
class FactorDagNode:
    node_id: str
    operation: str
    value_type: str
    dependencies: Sequence[str] = ()
    value: float | str | bool | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source: str | None = None
    factor_definition_ids: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _required_string("node_id", self.node_id))
        object.__setattr__(self, "operation", _required_string("operation", self.operation))
        object.__setattr__(self, "value_type", _required_string("value_type", self.value_type))
        object.__setattr__(self, "dependencies", _string_tuple("dependency", self.dependencies))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(self, "source", _optional_string(self.source))
        object.__setattr__(
            self,
            "factor_definition_ids",
            tuple(sorted(set(_required_string("factor_definition_id", value) for value in self.factor_definition_ids))),
        )

    def with_factor(self, factor_definition_id: str) -> FactorDagNode:
        return FactorDagNode(
            node_id=self.node_id,
            operation=self.operation,
            value_type=self.value_type,
            dependencies=self.dependencies,
            value=self.value,
            parameters=self.parameters,
            source=self.source,
            factor_definition_ids=tuple(sorted(set(self.factor_definition_ids) | {factor_definition_id})),
        )

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "node_id": self.node_id,
            "operation": self.operation,
            "value_type": self.value_type,
            "dependencies": list(self.dependencies),
            "parameters": _thaw_value(self.parameters),
            "factor_definition_ids": list(self.factor_definition_ids),
        }
        if self.value is not None:
            record["value"] = self.value
        if self.source is not None:
            record["source"] = self.source
        return record


@dataclass(frozen=True, slots=True)
class FactorDag:
    build_spec: FactorDagBuildSpec
    nodes: Sequence[FactorDagNode]
    factor_roots: Mapping[str, str]
    factor_operators: Mapping[str, Sequence[str]]
    factor_lookback_periods: Mapping[str, int]
    factor_dataset_versions: Mapping[str, Mapping[str, str]]
    dag_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.build_spec) is not FactorDagBuildSpec:
            raise FactorEngineError("build_spec must be a FactorDagBuildSpec")
        nodes = tuple(sorted(self.nodes, key=lambda node: node.node_id))
        if not nodes:
            raise FactorEngineError("DAG nodes are required")
        node_ids = {node.node_id for node in nodes}
        if len(node_ids) != len(nodes):
            raise FactorEngineError("DAG node_id values must be unique")
        for node in nodes:
            for dependency in node.dependencies:
                if dependency not in node_ids:
                    raise FactorEngineError(f"DAG dependency not found: {dependency}")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "factor_roots", _freeze_string_mapping(self.factor_roots))
        factor_ids = set(self.factor_roots)
        operators = {
            _required_string("factor_definition_id", factor_id): tuple(
                sorted(_required_string("operator", value) for value in values)
            )
            for factor_id, values in self.factor_operators.items()
        }
        if set(operators) != factor_ids:
            raise FactorEngineError("factor_operators must match factor_roots")
        object.__setattr__(self, "factor_operators", MappingProxyType(operators))
        lookbacks = {
            _required_string("factor_definition_id", factor_id): _non_negative_int("lookback_periods", value)
            for factor_id, value in self.factor_lookback_periods.items()
        }
        if set(lookbacks) != factor_ids:
            raise FactorEngineError("factor_lookback_periods must match factor_roots")
        object.__setattr__(self, "factor_lookback_periods", MappingProxyType(lookbacks))
        factor_dataset_versions = _freeze_factor_dataset_versions(self.factor_dataset_versions)
        if set(factor_dataset_versions) != factor_ids:
            raise FactorEngineError("factor_dataset_versions must match factor_roots")
        for factor_id, dataset_versions in factor_dataset_versions.items():
            for dataset_name, dataset_version in dataset_versions.items():
                spec_version = self.build_spec.dataset_versions.get(dataset_name)
                if spec_version != dataset_version:
                    raise FactorEngineError(f"factor_dataset_versions mismatch for {factor_id}.{dataset_name}")
        object.__setattr__(self, "factor_dataset_versions", factor_dataset_versions)
        dag_id = self.dag_id or _stable_id("fdg", self._identity_record())
        object.__setattr__(self, "dag_id", _required_string("dag_id", dag_id))

    @property
    def schema_name(self) -> str:
        return self.build_spec.schema_name

    @property
    def schema_version(self) -> str:
        return self.build_spec.schema_version

    @property
    def engine_version(self) -> str:
        return self.build_spec.engine_version

    @property
    def dataset_versions(self) -> Mapping[str, str]:
        return self.build_spec.dataset_versions

    @property
    def factor_versions(self) -> Mapping[str, str]:
        return self.build_spec.factor_versions

    @property
    def universe_version_id(self) -> str:
        return self.build_spec.universe_version_id

    @property
    def max_lookback_periods(self) -> int:
        return max(self.factor_lookback_periods.values(), default=0)

    def to_record(self) -> dict[str, object]:
        record = self._identity_record()
        record["dag_id"] = self.dag_id
        return record

    def _identity_record(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "build_spec": self.build_spec.to_record(),
            "node_count": len(self.nodes),
            "nodes": [node.to_record() for node in self.nodes],
            "factor_roots": dict(self.factor_roots),
            "factor_operators": {factor_id: list(values) for factor_id, values in self.factor_operators.items()},
            "factor_lookback_periods": dict(self.factor_lookback_periods),
            "factor_dataset_versions": {
                factor_id: dict(dataset_versions)
                for factor_id, dataset_versions in self.factor_dataset_versions.items()
            },
        }


@dataclass(frozen=True, slots=True)
class FactorCacheKey:
    factor_definition_id: str
    factor_version_id: str
    dataset_versions: Mapping[str, str]
    universe_version_id: str
    date_range: Sequence[date]
    engine_version: str
    partition_id: str
    partition_kind: FactorPartitionKind | str
    trade_date: date
    instrument_id: str | None = None
    key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "factor_definition_id", _required_string("factor_definition_id", self.factor_definition_id)
        )
        object.__setattr__(self, "factor_version_id", _validate_factor_version_id(self.factor_version_id))
        object.__setattr__(
            self,
            "dataset_versions",
            MappingProxyType(
                {
                    _required_string("dataset name", name): _validate_dataset_version(version)
                    for name, version in self.dataset_versions.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "universe_version_id",
            _validate_dataset_version(self.universe_version_id, field_name="universe_version_id"),
        )
        object.__setattr__(self, "date_range", _normalize_date_range(self.date_range))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "partition_id", _required_string("partition_id", self.partition_id))
        partition_kind = FactorPartitionKind(self.partition_kind)
        object.__setattr__(self, "partition_kind", partition_kind)
        object.__setattr__(self, "trade_date", _normalize_date("trade_date", self.trade_date))
        object.__setattr__(self, "instrument_id", _optional_instrument_id(self.instrument_id))
        if not self.date_range[0] <= self.trade_date <= self.date_range[1]:
            raise FactorEngineError("trade_date outside cache key date_range")
        if partition_kind is FactorPartitionKind.TIME_SERIES and self.instrument_id is None:
            raise FactorEngineError("time_series partitions require instrument_id")
        if partition_kind is FactorPartitionKind.CROSS_SECTION and self.instrument_id is not None:
            raise FactorEngineError("cross_section partitions cannot include instrument_id")
        key = self.key or _stable_id("fck", self._identity_record(include_key=False))
        object.__setattr__(self, "key", _required_string("key", key))

    def to_record(self) -> dict[str, object]:
        return self._identity_record(include_key=True)

    def _identity_record(self, *, include_key: bool) -> dict[str, object]:
        record: dict[str, object] = {
            "factor_definition_id": self.factor_definition_id,
            "factor_version_id": self.factor_version_id,
            "dataset_versions": dict(self.dataset_versions),
            "universe_version_id": self.universe_version_id,
            "date_range": [self.date_range[0].isoformat(), self.date_range[1].isoformat()],
            "engine_version": self.engine_version,
            "partition_id": self.partition_id,
            "partition_kind": self.partition_kind.value,
            "trade_date": self.trade_date.isoformat(),
        }
        if self.instrument_id is not None:
            record["instrument_id"] = self.instrument_id
        if include_key:
            record["key"] = self.key
        return record


@dataclass(frozen=True, slots=True)
class FactorCachePartition:
    partition_id: str
    partition_kind: FactorPartitionKind | str
    factor_definition_id: str
    factor_version_id: str
    trade_date: date
    start_date: date
    end_date: date
    cache_key: FactorCacheKey
    required_operators: Sequence[str]
    lookback_periods: int
    instrument_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "partition_id", _required_string("partition_id", self.partition_id))
        object.__setattr__(self, "partition_kind", FactorPartitionKind(self.partition_kind))
        object.__setattr__(
            self, "factor_definition_id", _required_string("factor_definition_id", self.factor_definition_id)
        )
        object.__setattr__(self, "factor_version_id", _validate_factor_version_id(self.factor_version_id))
        object.__setattr__(self, "trade_date", _normalize_date("trade_date", self.trade_date))
        object.__setattr__(self, "start_date", _normalize_date("start_date", self.start_date))
        object.__setattr__(self, "end_date", _normalize_date("end_date", self.end_date))
        if self.start_date > self.end_date:
            raise FactorEngineError("partition start_date cannot be after end_date")
        if type(self.cache_key) is not FactorCacheKey:
            raise FactorEngineError("cache_key must be a FactorCacheKey")
        object.__setattr__(self, "required_operators", _string_tuple("required operator", self.required_operators))
        object.__setattr__(self, "lookback_periods", _non_negative_int("lookback_periods", self.lookback_periods))
        object.__setattr__(self, "instrument_id", _optional_instrument_id(self.instrument_id))
        if self.partition_kind is FactorPartitionKind.TIME_SERIES and self.instrument_id is None:
            raise FactorEngineError("time_series partitions require instrument_id")
        if self.partition_kind is FactorPartitionKind.CROSS_SECTION and self.instrument_id is not None:
            raise FactorEngineError("cross_section partitions cannot include instrument_id")
        _ensure_cache_key_matches_partition(self.cache_key, self)

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "partition_id": self.partition_id,
            "partition_kind": self.partition_kind.value,
            "factor_definition_id": self.factor_definition_id,
            "factor_version_id": self.factor_version_id,
            "trade_date": self.trade_date.isoformat(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "required_operators": list(self.required_operators),
            "lookback_periods": self.lookback_periods,
            "cache_key": self.cache_key.to_record(),
        }
        if self.instrument_id is not None:
            record["instrument_id"] = self.instrument_id
        return record


@dataclass(frozen=True, slots=True)
class FactorCachePerformanceBudget:
    expected_scan_rows: int
    partition_count: int
    max_lookback_periods: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_scan_rows", _non_negative_int("expected_scan_rows", self.expected_scan_rows))
        object.__setattr__(self, "partition_count", _non_negative_int("partition_count", self.partition_count))
        object.__setattr__(
            self, "max_lookback_periods", _non_negative_int("max_lookback_periods", self.max_lookback_periods)
        )

    def to_record(self) -> dict[str, int]:
        return {
            "expected_scan_rows": self.expected_scan_rows,
            "partition_count": self.partition_count,
            "max_lookback_periods": self.max_lookback_periods,
        }


@dataclass(frozen=True, slots=True)
class FactorPartitionPlan:
    dag: FactorDag
    partitions: Sequence[FactorCachePartition]
    performance_budget: FactorCachePerformanceBudget

    def __post_init__(self) -> None:
        if type(self.dag) is not FactorDag:
            raise FactorEngineError("dag must be a FactorDag")
        partitions = tuple(self.partitions)
        for partition in partitions:
            if type(partition) is not FactorCachePartition:
                raise FactorEngineError("partitions must contain FactorCachePartition values")
        partition_ids = [partition.partition_id for partition in partitions]
        if len(partition_ids) != len(set(partition_ids)):
            raise FactorEngineError("partition_id values must be unique")
        partitions = tuple(sorted(partitions, key=lambda partition: partition.partition_id))
        object.__setattr__(self, "partitions", partitions)
        if type(self.performance_budget) is not FactorCachePerformanceBudget:
            raise FactorEngineError("performance_budget must be a FactorCachePerformanceBudget")

    @property
    def partition_count(self) -> int:
        return len(self.partitions)

    def to_record(self) -> dict[str, object]:
        return {
            "dag": self.dag.to_record(),
            "partition_count": self.partition_count,
            "performance_budget": self.performance_budget.to_record(),
            "partitions": [partition.to_record() for partition in self.partitions],
        }


@dataclass(frozen=True, slots=True)
class FactorIncrementalChangeSet:
    changed_dataset_versions: Mapping[str, str] = field(default_factory=dict)
    changed_factor_version_ids: Sequence[str] = ()
    changed_trade_dates: Sequence[date] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "changed_dataset_versions",
            MappingProxyType(
                {
                    _required_string("dataset name", name): _validate_dataset_version(version)
                    for name, version in self.changed_dataset_versions.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "changed_factor_version_ids",
            tuple(sorted(_validate_factor_version_id(value) for value in self.changed_factor_version_ids)),
        )
        object.__setattr__(
            self,
            "changed_trade_dates",
            tuple(sorted(_normalize_date("changed_trade_date", value) for value in self.changed_trade_dates)),
        )

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_dataset_versions or self.changed_factor_version_ids or self.changed_trade_dates)

    def to_record(self) -> dict[str, object]:
        return {
            "changed_dataset_versions": dict(self.changed_dataset_versions),
            "changed_factor_version_ids": list(self.changed_factor_version_ids),
            "changed_trade_dates": [value.isoformat() for value in self.changed_trade_dates],
        }


@dataclass(frozen=True, slots=True)
class FactorIncrementalRecomputePlan:
    change_set: FactorIncrementalChangeSet
    partitions: Sequence[FactorCachePartition]
    reason: str

    def __post_init__(self) -> None:
        if type(self.change_set) is not FactorIncrementalChangeSet:
            raise FactorEngineError("change_set must be a FactorIncrementalChangeSet")
        object.__setattr__(
            self, "partitions", tuple(sorted(self.partitions, key=lambda partition: partition.partition_id))
        )
        object.__setattr__(self, "reason", _required_string("reason", self.reason))

    @property
    def recompute_partition_count(self) -> int:
        return len(self.partitions)

    def to_record(self) -> dict[str, object]:
        return {
            "change_set": self.change_set.to_record(),
            "reason": self.reason,
            "recompute_partition_count": self.recompute_partition_count,
            "partitions": [partition.to_record() for partition in self.partitions],
        }


@dataclass(frozen=True, slots=True)
class FactorCacheQualityGate:
    status: FactorCacheQualityStatus | str
    issue_count: int
    metrics: Mapping[str, float | int] = field(default_factory=dict)
    operator_timings_ms: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", FactorCacheQualityStatus(self.status))
        object.__setattr__(self, "issue_count", _non_negative_int("issue_count", self.issue_count))
        object.__setattr__(self, "metrics", _freeze_numeric_mapping(self.metrics))
        object.__setattr__(self, "operator_timings_ms", _freeze_numeric_mapping(self.operator_timings_ms))

    def to_record(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "issue_count": self.issue_count,
            "metrics": dict(self.metrics),
            "operator_timings_ms": dict(self.operator_timings_ms),
        }


@dataclass(frozen=True, slots=True)
class FactorCacheManifest:
    partition_plan: FactorPartitionPlan
    quality_gate: FactorCacheQualityGate
    created_at: datetime
    contract_version: str = FACTOR_ENGINE_CONTRACT_VERSION
    schema_name: str = FACTOR_CACHE_MANIFEST_SCHEMA_NAME
    schema_version: str = FACTOR_CACHE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.partition_plan) is not FactorPartitionPlan:
            raise FactorEngineError("partition_plan must be a FactorPartitionPlan")
        if type(self.quality_gate) is not FactorCacheQualityGate:
            raise FactorEngineError("quality_gate must be a FactorCacheQualityGate")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
            "quality_gate": self.quality_gate.to_record(),
            "partition_plan": self.partition_plan.to_record(),
        }


def build_factor_dag(
    definitions: Sequence[FactorDefinition],
    spec: FactorDagBuildSpec,
) -> FactorDag:
    if type(spec) is not FactorDagBuildSpec:
        raise FactorEngineError("spec must be a FactorDagBuildSpec")
    selected_definitions = tuple(definitions)
    if not selected_definitions:
        raise FactorEngineError("factor definitions are required")
    for definition in selected_definitions:
        if type(definition) is not FactorDefinition:
            raise FactorEngineError("definitions must contain FactorDefinition values")

    nodes_by_signature: dict[str, FactorDagNode] = {}
    factor_roots: dict[str, str] = {}
    factor_operators: dict[str, tuple[str, ...]] = {}
    factor_lookbacks: dict[str, int] = {}
    factor_dataset_versions: dict[str, Mapping[str, str]] = {}
    definition_ids = tuple(definition.definition_id for definition in selected_definitions)
    if len(set(definition_ids)) != len(definition_ids):
        raise FactorEngineError("factor definitions must have unique definition_id values")
    if set(definition_ids) != set(spec.factor_versions):
        raise FactorEngineError("factor_versions does not match provided factor definitions")

    for definition in selected_definitions:
        factor_version_id = spec.factor_versions.get(definition.definition_id)
        if factor_version_id is None:
            raise FactorEngineError(f"factor_versions missing definition_id: {definition.definition_id}")
        _ensure_factor_version_matches_definition(definition, factor_version_id)
        plan = compile_factor_definition(definition)
        _ensure_dataset_versions_match(definition.definition_id, plan.dataset_versions, spec)
        root_id = _intern_expression_node(
            plan.node,
            factor_definition_id=definition.definition_id,
            nodes_by_signature=nodes_by_signature,
        )
        factor_roots[definition.definition_id] = root_id
        factor_operators[definition.definition_id] = tuple(plan.required_operators)
        factor_lookbacks[definition.definition_id] = plan.lookback_periods
        factor_dataset_versions[definition.definition_id] = plan.dataset_versions

    return FactorDag(
        build_spec=spec,
        nodes=tuple(nodes_by_signature.values()),
        factor_roots=factor_roots,
        factor_operators=factor_operators,
        factor_lookback_periods=factor_lookbacks,
        factor_dataset_versions=factor_dataset_versions,
    )


def plan_factor_cache_partitions(
    dag: FactorDag,
    *,
    instruments: Sequence[str],
    trade_dates: Sequence[date],
) -> FactorPartitionPlan:
    if type(dag) is not FactorDag:
        raise FactorEngineError("dag must be a FactorDag")
    normalized_instruments = tuple(
        sorted(set(_optional_instrument_id(value) for value in instruments if value is not None))
    )
    if not normalized_instruments:
        raise FactorEngineError("instruments are required")
    normalized_dates = tuple(sorted(set(_normalize_date("trade_date", value) for value in trade_dates)))
    if not normalized_dates:
        raise FactorEngineError("trade_dates are required")
    start, end = dag.build_spec.date_range
    if any(trade_date < start or trade_date > end for trade_date in normalized_dates):
        raise FactorEngineError("trade_date outside DAG date_range")

    partitions: list[FactorCachePartition] = []
    for factor_definition_id in sorted(dag.factor_roots):
        operators = tuple(dag.factor_operators[factor_definition_id])
        lookback = dag.factor_lookback_periods[factor_definition_id]
        factor_version_id = dag.factor_versions[factor_definition_id]
        if _requires_time_series_partition(operators):
            for instrument_id in normalized_instruments:
                for index, trade_date in enumerate(normalized_dates):
                    start_date = normalized_dates[max(0, index - lookback)]
                    partitions.append(
                        _make_partition(
                            dag=dag,
                            factor_definition_id=factor_definition_id,
                            factor_version_id=factor_version_id,
                            partition_kind=FactorPartitionKind.TIME_SERIES,
                            trade_date=trade_date,
                            start_date=start_date,
                            end_date=trade_date,
                            required_operators=operators,
                            lookback_periods=lookback,
                            instrument_id=instrument_id,
                        )
                    )
        if _requires_cross_section_partition(operators):
            for index, trade_date in enumerate(normalized_dates):
                start_date = normalized_dates[max(0, index - lookback)]
                partitions.append(
                    _make_partition(
                        dag=dag,
                        factor_definition_id=factor_definition_id,
                        factor_version_id=factor_version_id,
                        partition_kind=FactorPartitionKind.CROSS_SECTION,
                        trade_date=trade_date,
                        start_date=start_date,
                        end_date=trade_date,
                        required_operators=operators,
                        lookback_periods=lookback,
                    )
                )

    budget = FactorCachePerformanceBudget(
        expected_scan_rows=len(normalized_instruments) * len(normalized_dates) * len(dag.factor_roots),
        partition_count=len(partitions),
        max_lookback_periods=dag.max_lookback_periods,
    )
    return FactorPartitionPlan(dag=dag, partitions=tuple(partitions), performance_budget=budget)


def plan_incremental_factor_recompute(
    partition_plan: FactorPartitionPlan,
    change_set: FactorIncrementalChangeSet,
) -> FactorIncrementalRecomputePlan:
    if type(partition_plan) is not FactorPartitionPlan:
        raise FactorEngineError("partition_plan must be a FactorPartitionPlan")
    if type(change_set) is not FactorIncrementalChangeSet:
        raise FactorEngineError("change_set must be a FactorIncrementalChangeSet")
    if not change_set.has_changes:
        return FactorIncrementalRecomputePlan(change_set=change_set, partitions=(), reason="no_changes")

    changed_dataset_names = set(change_set.changed_dataset_versions)
    changed_factor_versions = set(change_set.changed_factor_version_ids)
    changed_dates = set(change_set.changed_trade_dates)
    selected: list[FactorCachePartition] = []
    for partition in partition_plan.partitions:
        include = False
        if changed_dataset_names and changed_dataset_names & set(partition.cache_key.dataset_versions):
            include = True
        if partition.factor_version_id in changed_factor_versions:
            include = True
        if changed_dates and any(
            partition.start_date <= changed_date <= partition.end_date for changed_date in changed_dates
        ):
            include = True
        if include:
            selected.append(partition)
    return FactorIncrementalRecomputePlan(change_set=change_set, partitions=tuple(selected), reason="incremental")


def publish_factor_cache_manifest(
    partition_plan: FactorPartitionPlan,
    quality_gate: FactorCacheQualityGate,
    artifact_store: ArtifactStore,
    *,
    created_at: datetime,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(partition_plan) is not FactorPartitionPlan:
        raise FactorEngineError("partition_plan must be a FactorPartitionPlan")
    if type(quality_gate) is not FactorCacheQualityGate:
        raise FactorEngineError("quality_gate must be a FactorCacheQualityGate")
    if quality_gate.status is not FactorCacheQualityStatus.PASSED:
        raise FactorEngineError("failed quality gate cannot publish shared factor cache manifest")
    manifest = FactorCacheManifest(partition_plan=partition_plan, quality_gate=quality_gate, created_at=created_at)
    payload = json.dumps(manifest.to_record(), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    return artifact_store.put_bytes(
        payload,
        schema_name=manifest.schema_name,
        schema_version=manifest.schema_version,
        content_type="application/json",
        produced_by_run_id=partition_plan.dag.build_spec.run_id,
        produced_by_stage_id=partition_plan.dag.build_spec.stage_id,
        retention_tier=retention_tier,
        created_at=created_at,
    )


def _intern_expression_node(
    node: FactorExpressionNode,
    *,
    factor_definition_id: str,
    nodes_by_signature: dict[str, FactorDagNode],
) -> str:
    child_ids = tuple(
        _intern_expression_node(
            child,
            factor_definition_id=factor_definition_id,
            nodes_by_signature=nodes_by_signature,
        )
        for child in node.children
    )
    signature_record = {
        "operation": node.operation,
        "value_type": node.value_type.value,
        "value": node.value,
        "parameters": _thaw_value(node.parameters),
        "source": node.source,
        "dependencies": list(child_ids),
    }
    signature = _stable_json(signature_record)
    node_id = _stable_id("fdn", signature_record)
    existing = nodes_by_signature.get(signature)
    if existing is None:
        nodes_by_signature[signature] = FactorDagNode(
            node_id=node_id,
            operation=node.operation,
            value_type=node.value_type.value,
            dependencies=child_ids,
            value=node.value,
            parameters=node.parameters,
            source=node.source,
            factor_definition_ids=(factor_definition_id,),
        )
        return node_id

    nodes_by_signature[signature] = existing.with_factor(factor_definition_id)
    return node_id


def _make_partition(
    *,
    dag: FactorDag,
    factor_definition_id: str,
    factor_version_id: str,
    partition_kind: FactorPartitionKind,
    trade_date: date,
    start_date: date,
    end_date: date,
    required_operators: Sequence[str],
    lookback_periods: int,
    instrument_id: str | None = None,
) -> FactorCachePartition:
    identity = {
        "dag_id": dag.dag_id,
        "factor_definition_id": factor_definition_id,
        "factor_version_id": factor_version_id,
        "partition_kind": partition_kind.value,
        "trade_date": trade_date.isoformat(),
        "instrument_id": instrument_id,
    }
    partition_id = _stable_id("fcp", identity)
    cache_key = FactorCacheKey(
        factor_definition_id=factor_definition_id,
        factor_version_id=factor_version_id,
        dataset_versions=dag.factor_dataset_versions[factor_definition_id],
        universe_version_id=dag.universe_version_id,
        date_range=dag.build_spec.date_range,
        engine_version=dag.engine_version,
        partition_id=partition_id,
        partition_kind=partition_kind,
        trade_date=trade_date,
        instrument_id=instrument_id,
    )
    return FactorCachePartition(
        partition_id=partition_id,
        partition_kind=partition_kind,
        factor_definition_id=factor_definition_id,
        factor_version_id=factor_version_id,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        cache_key=cache_key,
        required_operators=required_operators,
        lookback_periods=lookback_periods,
        instrument_id=instrument_id,
    )


def _ensure_factor_version_matches_definition(definition: FactorDefinition, factor_version_id: str) -> None:
    if definition.version_id is not None and definition.version_id != factor_version_id:
        raise FactorEngineError(f"factor version mismatch for {definition.definition_id}")


def _ensure_dataset_versions_match(
    factor_definition_id: str,
    dataset_versions: Mapping[str, str],
    spec: FactorDagBuildSpec,
) -> None:
    for dataset_name, version in dataset_versions.items():
        spec_version = spec.dataset_versions.get(dataset_name)
        if spec_version is None:
            raise FactorEngineError(
                f"dataset_versions missing required dataset for {factor_definition_id}: {dataset_name}"
            )
        if spec_version != version:
            raise FactorEngineError(f"dataset version mismatch for {factor_definition_id}.{dataset_name}")


def _ensure_cache_key_matches_partition(cache_key: FactorCacheKey, partition: FactorCachePartition) -> None:
    if cache_key.partition_id != partition.partition_id:
        raise FactorEngineError("cache_key partition_id must match partition_id")
    if cache_key.factor_definition_id != partition.factor_definition_id:
        raise FactorEngineError("cache_key factor_definition_id must match partition factor_definition_id")
    if cache_key.factor_version_id != partition.factor_version_id:
        raise FactorEngineError("cache_key factor_version_id must match partition factor_version_id")
    if cache_key.partition_kind is not partition.partition_kind:
        raise FactorEngineError("cache_key partition_kind must match partition partition_kind")
    if cache_key.trade_date != partition.trade_date:
        raise FactorEngineError("cache_key trade_date must match partition trade_date")
    if cache_key.instrument_id != partition.instrument_id:
        raise FactorEngineError("cache_key instrument_id must match partition instrument_id")


def _requires_time_series_partition(operators: Sequence[str]) -> bool:
    return any(operator == "delay" or operator.startswith("rolling_") for operator in operators)


def _requires_cross_section_partition(operators: Sequence[str]) -> bool:
    return "rank" in operators or not _requires_time_series_partition(operators)


def _stable_id(prefix: str, record: object) -> str:
    return f"{prefix}_{hashlib.sha256(_stable_json(record).encode('utf-8')).hexdigest()[:32]}"


def _stable_json(record: object) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise FactorEngineError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise FactorEngineError(f"{field_name} is required")
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _validate_dataset_version(value: object, *, field_name: str = "dataset_version") -> str:
    try:
        return DatasetVersionRef.version(str(value)).version_id or ""
    except DatasetCatalogError as exc:
        raise FactorEngineError(f"{field_name} must be a concrete Dataset Version id (dsv_*)") from exc


def _validate_factor_version_id(value: object) -> str:
    normalized = _required_string("factor_version_id", value)
    if not _FACTOR_VERSION_ID_RE.fullmatch(normalized):
        raise FactorEngineError("factor_version_id must be a concrete fdv_* version id")
    return normalized


def _normalize_date_range(values: Sequence[date]) -> tuple[date, date]:
    value_tuple = tuple(values)
    if len(value_tuple) != 2:
        raise FactorEngineError("date_range must contain start and end dates")
    start = _normalize_date("date_range start", value_tuple[0])
    end = _normalize_date("date_range end", value_tuple[1])
    if start > end:
        raise FactorEngineError("date_range start cannot be after end")
    return (start, end)


def _normalize_date(field_name: str, value: date) -> date:
    if type(value) is datetime:
        return value.date()
    if type(value) is not date:
        raise FactorEngineError(f"{field_name} must be a date")
    return value


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FactorEngineError(f"{field_name} must be a timezone-aware datetime")


def _optional_instrument_id(value: object) -> str | None:
    if value is None:
        return None
    return InstrumentId.parse(str(value)).canonical


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_required_string(field_name, value) for value in values)


def _non_negative_int(field_name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise FactorEngineError(f"{field_name} must be a non-negative integer")
    return value


def _freeze_string_mapping(values: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(
        {
            _required_string("mapping key", key): _required_string("mapping value", value)
            for key, value in values.items()
        }
    )


def _freeze_factor_dataset_versions(values: Mapping[str, Mapping[str, str]]) -> Mapping[str, Mapping[str, str]]:
    normalized: dict[str, Mapping[str, str]] = {}
    for factor_id, dataset_versions in values.items():
        if not isinstance(dataset_versions, Mapping):
            raise FactorEngineError("factor_dataset_versions values must be mappings")
        normalized[_required_string("factor_definition_id", factor_id)] = MappingProxyType(
            {
                _required_string("dataset name", name): _validate_dataset_version(version)
                for name, version in dataset_versions.items()
            }
        )
    return MappingProxyType(normalized)


def _freeze_numeric_mapping(values: Mapping[str, float | int]) -> Mapping[str, float | int]:
    normalized: dict[str, float | int] = {}
    for key, value in values.items():
        normalized[_required_string("metric name", key)] = _finite_number("metric value", value)
    return MappingProxyType(normalized)


def _finite_number(field_name: str, value: object) -> float | int:
    if type(value) is int:
        return value
    if type(value) is float:
        if value != value or value in {float("inf"), float("-inf")}:
            raise FactorEngineError(f"{field_name} must be finite")
        return value
    raise FactorEngineError(f"{field_name} must be numeric")


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _freeze_value(value) for key, value in values.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value
