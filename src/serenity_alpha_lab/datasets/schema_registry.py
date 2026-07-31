from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from serenity_alpha_lab.datasets.corporate_actions import (
    ADJUSTED_DAILY_BARS_CONTENT_TYPE,
    ADJUSTED_DAILY_BARS_FIELD_SCHEMA,
    ADJUSTED_DAILY_BARS_PARTITION_KEYS,
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    CORPORATE_ACTIONS_CONTENT_TYPE,
    CORPORATE_ACTIONS_FIELD_SCHEMA,
    CORPORATE_ACTIONS_PARTITION_KEYS,
    CORPORATE_ACTIONS_SCHEMA_NAME,
    CORPORATE_ACTIONS_SCHEMA_VERSION,
)
from serenity_alpha_lab.datasets.fundamentals import (
    FUNDAMENTALS_CONTENT_TYPE,
    FUNDAMENTALS_FIELD_SCHEMA,
    FUNDAMENTALS_PARTITION_KEYS,
    FUNDAMENTALS_SCHEMA_NAME,
    FUNDAMENTALS_SCHEMA_VERSION,
)
from serenity_alpha_lab.datasets.instrument_master import (
    INSTRUMENT_MASTER_CONTENT_TYPE,
    INSTRUMENT_MASTER_FIELD_SCHEMA,
    INSTRUMENT_MASTER_PARTITION_KEYS,
    INSTRUMENT_MASTER_SCHEMA_NAME,
    INSTRUMENT_MASTER_SCHEMA_VERSION,
)
from serenity_alpha_lab.datasets.raw_daily_bars import (
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_FIELD_SCHEMA,
    RAW_DAILY_BARS_PARTITION_KEYS,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
)


_SUPPORTED_LOGICAL_TYPES = frozenset(
    {
        "bool",
        "date32[day]",
        "float64",
        "int64",
        "list<utf8>",
        "timestamp[us, tz=UTC]",
        "utf8",
        "list<struct<system:utf8,version:utf8,level1:utf8,level2:utf8,level3:utf8,"
        "valid_from:date32[day],valid_to:date32[day]>>",
        "list<struct<provider:utf8,symbol:utf8,instrument_id:utf8,valid_from:date32[day],"
        "valid_to:date32[day],source_bronze_artifact_id:utf8>>",
    }
)


class SchemaRegistryError(ValueError):
    """Raised when a dataset schema declaration or registry operation is invalid."""


class SchemaCompatibilityStatus(StrEnum):
    IDENTICAL = "identical"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING = "breaking"


@dataclass(frozen=True, slots=True)
class DatasetSchemaField:
    name: str
    logical_type: str
    nullable: bool = True
    meaning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_string("field name", self.name))
        object.__setattr__(self, "logical_type", _required_string("logical_type", self.logical_type))
        if self.logical_type not in _SUPPORTED_LOGICAL_TYPES:
            raise SchemaRegistryError(f"Unsupported Arrow logical type: {self.logical_type}")
        if type(self.nullable) is not bool:
            raise SchemaRegistryError("nullable must be a bool")
        object.__setattr__(self, "meaning", _optional_string(self.meaning))

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "logical_type": self.logical_type,
            "nullable": self.nullable,
            "meaning": self.meaning,
        }

    @classmethod
    def from_mapping(cls, name: str, logical_type: str, *, nullable: bool | None = None) -> DatasetSchemaField:
        return cls(
            name=name,
            logical_type=logical_type,
            nullable=_default_nullable(name) if nullable is None else nullable,
        )


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityReport:
    status: SchemaCompatibilityStatus
    breaking_changes: tuple[str, ...] = ()
    compatible_changes: tuple[str, ...] = ()

    @property
    def is_backward_compatible(self) -> bool:
        return self.status in {SchemaCompatibilityStatus.IDENTICAL, SchemaCompatibilityStatus.BACKWARD_COMPATIBLE}

    @property
    def requires_major_version(self) -> bool:
        return self.status is SchemaCompatibilityStatus.BREAKING


@dataclass(frozen=True, slots=True)
class DatasetSchemaDeclaration:
    schema_name: str
    schema_version: str
    fields: Sequence[DatasetSchemaField]
    primary_key: Sequence[str]
    partition_keys: Sequence[str] = ()
    content_type: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        _parse_semver(self.schema_version)
        object.__setattr__(self, "content_type", _optional_string(self.content_type))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

        fields = tuple(self.fields)
        if not fields:
            raise SchemaRegistryError("schema fields are required")
        for schema_field in fields:
            if type(schema_field) is not DatasetSchemaField:
                raise SchemaRegistryError("fields must contain DatasetSchemaField values")
        field_names: set[str] = set()
        for schema_field in fields:
            if schema_field.name in field_names:
                raise SchemaRegistryError(f"Duplicate schema field: {schema_field.name}")
            field_names.add(schema_field.name)
        object.__setattr__(self, "fields", fields)

        primary_key = tuple(_required_string("primary key field", key) for key in self.primary_key)
        if not primary_key:
            raise SchemaRegistryError("primary_key is required")
        for key in primary_key:
            if key not in field_names:
                raise SchemaRegistryError(f"primary key field is not declared: {key}")
        object.__setattr__(self, "primary_key", primary_key)

        partition_keys = tuple(_required_string("partition key field", key) for key in self.partition_keys)
        object.__setattr__(self, "partition_keys", partition_keys)

    @property
    def schema_hash(self) -> str:
        payload = json.dumps(self.to_record(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(schema_field.name for schema_field in self.fields)

    def field(self, name: str) -> DatasetSchemaField:
        field_name = _required_string("field name", name)
        for schema_field in self.fields:
            if schema_field.name == field_name:
                return schema_field
        raise SchemaRegistryError(f"schema field not found: {field_name}")

    def to_record(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "fields": [schema_field.to_record() for schema_field in self.fields],
            "primary_key": list(self.primary_key),
            "partition_keys": list(self.partition_keys),
            "content_type": self.content_type,
            "metadata": dict(self.metadata),
        }

    def to_pyarrow_schema(self):
        pa = _import_pyarrow()
        metadata = {
            b"serenity:schema_name": self.schema_name.encode("utf-8"),
            b"serenity:schema_version": self.schema_version.encode("utf-8"),
            b"serenity:schema_hash": self.schema_hash.encode("utf-8"),
            b"serenity:primary_key": json.dumps(list(self.primary_key), separators=(",", ":")).encode("utf-8"),
            b"serenity:partition_keys": json.dumps(list(self.partition_keys), separators=(",", ":")).encode("utf-8"),
        }
        if self.content_type:
            metadata[b"serenity:content_type"] = self.content_type.encode("utf-8")
        for key, value in self.metadata.items():
            metadata[f"serenity:{key}".encode("utf-8")] = value.encode("utf-8")
        return pa.schema(
            [
                pa.field(
                    schema_field.name,
                    _logical_type_to_arrow(schema_field.logical_type),
                    nullable=schema_field.nullable,
                    metadata=_field_metadata(schema_field),
                )
                for schema_field in self.fields
            ],
            metadata=metadata,
        )

    def validate_pyarrow_schema(self, schema, *, strict_nullability: bool = True) -> None:
        pa = _import_pyarrow()
        if not isinstance(schema, pa.Schema):
            raise SchemaRegistryError("schema must be a pyarrow.Schema")
        incoming_names = tuple(field.name for field in schema)
        if incoming_names != self.field_names:
            raise SchemaRegistryError(f"Arrow schema fields changed: expected {self.field_names}, got {incoming_names}")
        for expected_field, incoming_field in zip(self.fields, schema):
            if not _arrow_types_equivalent(incoming_field.type, expected_field.logical_type):
                raise SchemaRegistryError(
                    f"Arrow field type changed for {expected_field.name}: "
                    f"expected {expected_field.logical_type}, got {incoming_field.type}"
                )
            if strict_nullability and incoming_field.nullable != expected_field.nullable:
                raise SchemaRegistryError(
                    f"Arrow field nullability changed for {expected_field.name}: "
                    f"expected {expected_field.nullable}, got {incoming_field.nullable}"
                )

    def compare_compatibility(self, candidate: DatasetSchemaDeclaration) -> SchemaCompatibilityReport:
        if type(candidate) is not DatasetSchemaDeclaration:
            raise SchemaRegistryError("candidate must be a DatasetSchemaDeclaration")
        if candidate.schema_name != self.schema_name:
            raise SchemaRegistryError("schema names must match for compatibility comparison")
        if self.schema_hash == candidate.schema_hash:
            return SchemaCompatibilityReport(status=SchemaCompatibilityStatus.IDENTICAL)

        breaking_changes: list[str] = []
        compatible_changes: list[str] = []
        previous_by_name = {schema_field.name: schema_field for schema_field in self.fields}
        candidate_by_name = {schema_field.name: schema_field for schema_field in candidate.fields}

        for field_name, previous_field in previous_by_name.items():
            candidate_field = candidate_by_name.get(field_name)
            if candidate_field is None:
                breaking_changes.append(f"removed field: {field_name}")
                continue
            if candidate_field.logical_type != previous_field.logical_type:
                breaking_changes.append(
                    f"changed field type: {field_name} {previous_field.logical_type} -> {candidate_field.logical_type}"
                )
            if previous_field.nullable and not candidate_field.nullable:
                breaking_changes.append(f"made nullable field required: {field_name}")
            if previous_field.meaning and candidate_field.meaning and previous_field.meaning != candidate_field.meaning:
                breaking_changes.append(f"changed field meaning: {field_name}")

        for field_name, candidate_field in candidate_by_name.items():
            if field_name not in previous_by_name:
                if candidate_field.nullable:
                    compatible_changes.append(f"added nullable field: {field_name}")
                else:
                    breaking_changes.append(f"added required field: {field_name}")

        if self.primary_key != candidate.primary_key:
            breaking_changes.append("changed primary key")
        if self.partition_keys != candidate.partition_keys:
            breaking_changes.append("changed partition keys")
        if self.content_type != candidate.content_type:
            breaking_changes.append("changed content type")

        if breaking_changes:
            return SchemaCompatibilityReport(
                status=SchemaCompatibilityStatus.BREAKING,
                breaking_changes=tuple(breaking_changes),
                compatible_changes=tuple(compatible_changes),
            )
        return SchemaCompatibilityReport(
            status=SchemaCompatibilityStatus.BACKWARD_COMPATIBLE,
            compatible_changes=tuple(compatible_changes),
        )


@dataclass(slots=True)
class ArrowSchemaRegistry:
    _schemas: dict[tuple[str, str], DatasetSchemaDeclaration] = field(default_factory=dict)
    _schema_order: list[str] = field(default_factory=list)

    def register(self, declaration: DatasetSchemaDeclaration) -> DatasetSchemaDeclaration:
        if type(declaration) is not DatasetSchemaDeclaration:
            raise SchemaRegistryError("declaration must be a DatasetSchemaDeclaration")
        key = (declaration.schema_name, declaration.schema_version)
        if key in self._schemas:
            raise SchemaRegistryError(
                f"Schema {declaration.schema_name} version {declaration.schema_version} is already registered"
            )

        existing_versions = self.versions(declaration.schema_name)
        if existing_versions:
            latest = self.latest(declaration.schema_name)
            if _parse_semver(declaration.schema_version) <= _parse_semver(latest.schema_version):
                raise SchemaRegistryError(
                    f"Schema {declaration.schema_name} version {declaration.schema_version} "
                    f"must be newer than {latest.schema_version}"
                )
            compatibility = latest.compare_compatibility(declaration)
            latest_major = _parse_semver(latest.schema_version)[0]
            declaration_major = _parse_semver(declaration.schema_version)[0]
            if not compatibility.is_backward_compatible and declaration_major == latest_major:
                raise SchemaRegistryError(
                    f"Schema {declaration.schema_name} change requires a new major version: "
                    + "; ".join(compatibility.breaking_changes)
                )
        elif declaration.schema_name not in self._schema_order:
            self._schema_order.append(declaration.schema_name)

        self._schemas[key] = declaration
        return declaration

    def get(self, schema_name: str, schema_version: str) -> DatasetSchemaDeclaration:
        key = (_required_string("schema_name", schema_name), _required_string("schema_version", schema_version))
        try:
            return self._schemas[key]
        except KeyError as exc:
            raise SchemaRegistryError(f"Schema not registered: {key[0]} {key[1]}") from exc

    def latest(self, schema_name: str) -> DatasetSchemaDeclaration:
        schema_id = _required_string("schema_name", schema_name)
        declarations = [declaration for key, declaration in self._schemas.items() if key[0] == schema_id]
        if not declarations:
            raise SchemaRegistryError(f"Schema not registered: {schema_id}")
        return max(declarations, key=lambda declaration: _parse_semver(declaration.schema_version))

    def versions(self, schema_name: str) -> tuple[str, ...]:
        schema_id = _required_string("schema_name", schema_name)
        versions = [version for name, version in self._schemas if name == schema_id]
        return tuple(sorted(versions, key=_parse_semver))

    def schema_names(self) -> tuple[str, ...]:
        return tuple(self._schema_order)

    def declarations(self) -> tuple[DatasetSchemaDeclaration, ...]:
        declarations: list[DatasetSchemaDeclaration] = []
        for schema_name in self._schema_order:
            declarations.extend(self.get(schema_name, version) for version in self.versions(schema_name))
        return tuple(declarations)


def default_dataset_schema_registry() -> ArrowSchemaRegistry:
    registry = ArrowSchemaRegistry()
    for declaration in (
        _declaration_from_field_schema(
            schema_name=INSTRUMENT_MASTER_SCHEMA_NAME,
            schema_version=INSTRUMENT_MASTER_SCHEMA_VERSION,
            field_schema=INSTRUMENT_MASTER_FIELD_SCHEMA,
            primary_key=("instrument_id", "valid_from"),
            partition_keys=INSTRUMENT_MASTER_PARTITION_KEYS,
            content_type=INSTRUMENT_MASTER_CONTENT_TYPE,
        ),
        _declaration_from_field_schema(
            schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
            schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
            field_schema=RAW_DAILY_BARS_FIELD_SCHEMA,
            primary_key=("instrument_id", "trade_date", "provider_id"),
            partition_keys=RAW_DAILY_BARS_PARTITION_KEYS,
            content_type=RAW_DAILY_BARS_CONTENT_TYPE,
        ),
        _declaration_from_field_schema(
            schema_name=CORPORATE_ACTIONS_SCHEMA_NAME,
            schema_version=CORPORATE_ACTIONS_SCHEMA_VERSION,
            field_schema=CORPORATE_ACTIONS_FIELD_SCHEMA,
            primary_key=("instrument_id", "ex_date", "action_type", "provider_id"),
            partition_keys=CORPORATE_ACTIONS_PARTITION_KEYS,
            content_type=CORPORATE_ACTIONS_CONTENT_TYPE,
        ),
        _declaration_from_field_schema(
            schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
            schema_version=ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
            field_schema=ADJUSTED_DAILY_BARS_FIELD_SCHEMA,
            primary_key=("instrument_id", "trade_date", "provider_id", "adjustment"),
            partition_keys=ADJUSTED_DAILY_BARS_PARTITION_KEYS,
            content_type=ADJUSTED_DAILY_BARS_CONTENT_TYPE,
        ),
        _declaration_from_field_schema(
            schema_name=FUNDAMENTALS_SCHEMA_NAME,
            schema_version=FUNDAMENTALS_SCHEMA_VERSION,
            field_schema=FUNDAMENTALS_FIELD_SCHEMA,
            primary_key=("instrument_id", "period_end", "item", "revision", "provider_id"),
            partition_keys=FUNDAMENTALS_PARTITION_KEYS,
            content_type=FUNDAMENTALS_CONTENT_TYPE,
        ),
    ):
        registry.register(declaration)
    return registry


def _declaration_from_field_schema(
    *,
    schema_name: str,
    schema_version: str,
    field_schema: Mapping[str, str],
    primary_key: Sequence[str],
    partition_keys: Sequence[str],
    content_type: str,
) -> DatasetSchemaDeclaration:
    return DatasetSchemaDeclaration(
        schema_name=schema_name,
        schema_version=schema_version,
        fields=tuple(
            DatasetSchemaField.from_mapping(field_name, logical_type)
            for field_name, logical_type in field_schema.items()
        ),
        primary_key=primary_key,
        partition_keys=partition_keys,
        content_type=content_type,
    )


def _default_nullable(field_name: str) -> bool:
    required_fields = {
        "action_type",
        "adjustment",
        "adjustment_factor",
        "amount",
        "asset_type",
        "available_at",
        "board",
        "cash_dividend_per_share",
        "close",
        "created_at",
        "currency",
        "ex_date",
        "exchange",
        "field_lineage",
        "fiscal_year",
        "high",
        "ingested_at",
        "instrument_id",
        "is_st",
        "item",
        "listed_on",
        "listing_status",
        "low",
        "market",
        "name",
        "open",
        "period_end",
        "period_type",
        "provider_id",
        "provider_raw_response_sha256",
        "provider_source",
        "revision",
        "source_bronze_artifact_id",
        "source_raw_bronze_artifact_id",
        "split_ratio",
        "symbol",
        "temporal_confidence",
        "trade_date",
        "valid_from",
        "value",
        "volume",
    }
    return field_name not in required_fields


def _field_metadata(schema_field: DatasetSchemaField) -> Mapping[bytes, bytes]:
    metadata = {b"serenity:logical_type": schema_field.logical_type.encode("utf-8")}
    if schema_field.meaning:
        metadata[b"serenity:meaning"] = schema_field.meaning.encode("utf-8")
    return metadata


def _logical_type_to_arrow(logical_type: str):
    pa = _import_pyarrow()
    if logical_type == "bool":
        return pa.bool_()
    if logical_type == "date32[day]":
        return pa.date32()
    if logical_type == "float64":
        return pa.float64()
    if logical_type == "int64":
        return pa.int64()
    if logical_type == "list<utf8>":
        return pa.list_(pa.string())
    if logical_type == "timestamp[us, tz=UTC]":
        return pa.timestamp("us", tz="UTC")
    if logical_type == "utf8":
        return pa.string()
    if logical_type.startswith("list<struct<system:utf8"):
        return pa.list_(
            pa.struct(
                [
                    pa.field("system", pa.string(), nullable=False),
                    pa.field("version", pa.string(), nullable=False),
                    pa.field("level1", pa.string(), nullable=False),
                    pa.field("level2", pa.string()),
                    pa.field("level3", pa.string()),
                    pa.field("valid_from", pa.date32(), nullable=False),
                    pa.field("valid_to", pa.date32()),
                ]
            )
        )
    if logical_type.startswith("list<struct<provider:utf8"):
        return pa.list_(
            pa.struct(
                [
                    pa.field("provider", pa.string(), nullable=False),
                    pa.field("symbol", pa.string(), nullable=False),
                    pa.field("instrument_id", pa.string(), nullable=False),
                    pa.field("valid_from", pa.date32(), nullable=False),
                    pa.field("valid_to", pa.date32()),
                    pa.field("source_bronze_artifact_id", pa.string(), nullable=False),
                ]
            )
        )
    raise SchemaRegistryError(f"Unsupported Arrow logical type: {logical_type}")


def _arrow_types_equivalent(incoming_type, logical_type: str) -> bool:
    pa = _import_pyarrow()
    expected_type = _logical_type_to_arrow(logical_type)
    if incoming_type == expected_type:
        return True
    if logical_type == "utf8" and (pa.types.is_string(incoming_type) or pa.types.is_large_string(incoming_type)):
        return True
    return False


def _import_pyarrow():
    try:
        import pyarrow as pa
    except ModuleNotFoundError as exc:
        raise SchemaRegistryError("PyArrow is required for Arrow schema conversion; install the quant extra") from exc
    return pa


def _parse_semver(version: str) -> tuple[int, int, int]:
    parts = _required_string("schema_version", version).split(".")
    if len(parts) != 3:
        raise SchemaRegistryError(f"schema_version must be semantic major.minor.patch: {version}")
    try:
        parsed = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise SchemaRegistryError(f"schema_version must be numeric semantic version: {version}") from exc
    if any(part < 0 for part in parsed):
        raise SchemaRegistryError(f"schema_version cannot contain negative components: {version}")
    return parsed  # type: ignore[return-value]


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise SchemaRegistryError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise SchemaRegistryError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise SchemaRegistryError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


__all__ = [
    "ArrowSchemaRegistry",
    "DatasetSchemaDeclaration",
    "DatasetSchemaField",
    "SchemaCompatibilityReport",
    "SchemaCompatibilityStatus",
    "SchemaRegistryError",
    "default_dataset_schema_registry",
]
