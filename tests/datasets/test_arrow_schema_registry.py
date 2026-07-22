from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from serenity_alpha_lab.datasets import (
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    CORPORATE_ACTIONS_SCHEMA_NAME,
    CORPORATE_ACTIONS_SCHEMA_VERSION,
    FUNDAMENTALS_SCHEMA_NAME,
    FUNDAMENTALS_SCHEMA_VERSION,
    INSTRUMENT_MASTER_SCHEMA_NAME,
    INSTRUMENT_MASTER_SCHEMA_VERSION,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
)
from serenity_alpha_lab.datasets.schema_registry import (
    ArrowSchemaRegistry,
    DatasetSchemaDeclaration,
    DatasetSchemaField,
    SchemaRegistryError,
    default_dataset_schema_registry,
)


def test_default_registry_contains_p2_dataset_schemas_without_eager_pyarrow_import() -> None:
    registry = default_dataset_schema_registry()

    assert registry.schema_names() == (
        INSTRUMENT_MASTER_SCHEMA_NAME,
        RAW_DAILY_BARS_SCHEMA_NAME,
        CORPORATE_ACTIONS_SCHEMA_NAME,
        ADJUSTED_DAILY_BARS_SCHEMA_NAME,
        FUNDAMENTALS_SCHEMA_NAME,
    )
    assert registry.get(INSTRUMENT_MASTER_SCHEMA_NAME, INSTRUMENT_MASTER_SCHEMA_VERSION).partition_keys == ("market",)
    assert registry.get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION).primary_key == (
        "instrument_id",
        "trade_date",
        "provider_id",
    )
    assert registry.get(CORPORATE_ACTIONS_SCHEMA_NAME, CORPORATE_ACTIONS_SCHEMA_VERSION).primary_key == (
        "instrument_id",
        "ex_date",
        "action_type",
        "provider_id",
    )
    assert registry.get(FUNDAMENTALS_SCHEMA_NAME, FUNDAMENTALS_SCHEMA_VERSION).primary_key == (
        "instrument_id",
        "period_end",
        "item",
        "revision",
        "provider_id",
    )


def test_default_registry_exports_arrow_schema_with_metadata() -> None:
    pa = pytest.importorskip("pyarrow")

    declaration = default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)
    arrow_schema = declaration.to_pyarrow_schema()

    assert arrow_schema.metadata[b"serenity:schema_name"] == RAW_DAILY_BARS_SCHEMA_NAME.encode()
    assert arrow_schema.metadata[b"serenity:schema_version"] == RAW_DAILY_BARS_SCHEMA_VERSION.encode()
    assert arrow_schema.field("trade_date").type == pa.date32()
    assert arrow_schema.field("provider_source_timestamp").type == pa.timestamp("us", tz="UTC")
    assert arrow_schema.field("instrument_id").nullable is False
    assert declaration.schema_hash.startswith("sha256:")


def test_arrow_pandas_polars_roundtrip_preserves_types() -> None:
    pa = pytest.importorskip("pyarrow")
    pl = pytest.importorskip("polars")

    declaration = default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)
    arrow_schema = declaration.to_pyarrow_schema()
    rows = [
        {
            "instrument_id": "600519.XSHG",
            "market": "cn",
            "exchange": "XSHG",
            "trade_date": date(2026, 7, 21),
            "provider_id": "dsa_compatibility",
            "provider_source": "akshare",
            "open": 100.0,
            "high": 102.0,
            "low": 99.5,
            "close": 101.0,
            "volume": 1000.0,
            "amount": 101000.0,
            "currency": "CNY",
            "adjustment": "unadjusted",
            "provider_source_timestamp": datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc),
            "provider_raw_response_sha256": "a" * 64,
            "source_bronze_artifact_id": "artifact://bronze/raw@sha256:" + "b" * 64,
        }
    ]

    table = pa.Table.from_pylist(rows, schema=arrow_schema)
    declaration.validate_pyarrow_schema(table.schema)
    pandas_table = pa.Table.from_pandas(table.to_pandas(), schema=arrow_schema, preserve_index=False)
    declaration.validate_pyarrow_schema(pandas_table.schema)
    polars_table = pl.from_arrow(table).to_arrow()
    declaration.validate_pyarrow_schema(polars_table.schema, strict_nullability=False)

    assert table.schema.field("trade_date").type == pa.date32()
    assert pandas_table.schema.field("provider_source_timestamp").type == pa.timestamp("us", tz="UTC")
    assert polars_table.schema.field("close").type == pa.float64()


def test_minor_versions_may_only_add_nullable_fields() -> None:
    base = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.0.0",
        fields=(
            DatasetSchemaField("instrument_id", "utf8", nullable=False, meaning="canonical instrument id"),
            DatasetSchemaField("close", "float64", nullable=False, meaning="unadjusted close price"),
        ),
        primary_key=("instrument_id",),
    )
    compatible = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.1.0",
        fields=(
            DatasetSchemaField("instrument_id", "utf8", nullable=False, meaning="canonical instrument id"),
            DatasetSchemaField("close", "float64", nullable=False, meaning="unadjusted close price"),
            DatasetSchemaField("source", "utf8", nullable=True, meaning="optional source name"),
        ),
        primary_key=("instrument_id",),
    )
    breaking_type_change = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.1.0",
        fields=(
            DatasetSchemaField("instrument_id", "utf8", nullable=False, meaning="canonical instrument id"),
            DatasetSchemaField("close", "int64", nullable=False, meaning="unadjusted close price"),
        ),
        primary_key=("instrument_id",),
    )
    breaking_required_add = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.1.0",
        fields=(
            DatasetSchemaField("instrument_id", "utf8", nullable=False, meaning="canonical instrument id"),
            DatasetSchemaField("close", "float64", nullable=False, meaning="unadjusted close price"),
            DatasetSchemaField("required_source", "utf8", nullable=False, meaning="new required source"),
        ),
        primary_key=("instrument_id",),
    )

    assert base.compare_compatibility(compatible).is_backward_compatible is True
    assert base.compare_compatibility(breaking_type_change).is_backward_compatible is False
    assert base.compare_compatibility(breaking_type_change).requires_major_version is True
    assert base.compare_compatibility(breaking_required_add).is_backward_compatible is False


def test_registry_rejects_duplicate_versions_and_minor_breaking_changes() -> None:
    registry = ArrowSchemaRegistry()
    base = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.0.0",
        fields=(DatasetSchemaField("id", "utf8", nullable=False), DatasetSchemaField("value", "float64")),
        primary_key=("id",),
    )
    compatible = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.1.0",
        fields=(
            DatasetSchemaField("id", "utf8", nullable=False),
            DatasetSchemaField("value", "float64"),
            DatasetSchemaField("note", "utf8"),
        ),
        primary_key=("id",),
    )
    breaking_minor = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="1.2.0",
        fields=(DatasetSchemaField("id", "utf8", nullable=False),),
        primary_key=("id",),
    )
    breaking_major = DatasetSchemaDeclaration(
        schema_name="dataset.example",
        schema_version="2.0.0",
        fields=(DatasetSchemaField("id", "utf8", nullable=False),),
        primary_key=("id",),
    )

    registry.register(base)
    registry.register(compatible)

    with pytest.raises(SchemaRegistryError, match="already registered"):
        registry.register(base)
    with pytest.raises(SchemaRegistryError, match="requires a new major version"):
        registry.register(breaking_minor)

    registry.register(breaking_major)
    assert registry.latest("dataset.example").schema_version == "2.0.0"


def test_schema_declaration_validation_rejects_ambiguous_contracts() -> None:
    with pytest.raises(SchemaRegistryError, match="Duplicate schema field"):
        DatasetSchemaDeclaration(
            schema_name="dataset.bad",
            schema_version="1.0.0",
            fields=(DatasetSchemaField("id", "utf8"), DatasetSchemaField("id", "utf8")),
            primary_key=("id",),
        )
    with pytest.raises(SchemaRegistryError, match="primary key field is not declared"):
        DatasetSchemaDeclaration(
            schema_name="dataset.bad",
            schema_version="1.0.0",
            fields=(DatasetSchemaField("id", "utf8"),),
            primary_key=("missing",),
        )
    with pytest.raises(SchemaRegistryError, match="Unsupported Arrow logical type"):
        DatasetSchemaDeclaration(
            schema_name="dataset.bad",
            schema_version="1.0.0",
            fields=(DatasetSchemaField("id", "object"),),
            primary_key=("id",),
        )
