from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.quant.factors.definitions import (
    FACTOR_DEFINITION_SCHEMA_NAME,
    FactorDefinition,
    FactorDefinitionError,
    FactorDefinitionStatus,
    FactorDirection,
    FactorFormula,
    FactorInput,
    FactorInputKind,
    FactorWindow,
    LocalFactorDefinitionRepository,
    MissingValuePolicy,
    MissingValueStrategy,
    PostProcessingStep,
)


CREATED_AT = datetime(2026, 7, 23, 9, 30, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)
RETIRED_AT = datetime(2026, 7, 23, 11, 0, tzinfo=UTC)
FUNDAMENTALS_VERSION = "dsv_" + "a" * 32
BARS_VERSION = "dsv_" + "b" * 32
IMPLEMENTATION_HASH = "sha256:" + "f" * 64


def test_factor_definition_draft_records_complete_versioned_spec_and_is_immutable() -> None:
    draft = _quality_factor_draft()

    assert draft.schema_name == FACTOR_DEFINITION_SCHEMA_NAME
    assert draft.status is FactorDefinitionStatus.DRAFT
    assert draft.definition_id == "quality_composite"
    assert draft.semantic_version == "1.0.0"
    assert draft.dataset_versions == {
        "fundamentals_pit": FUNDAMENTALS_VERSION,
        "adjusted_daily_bars": BARS_VERSION,
    }
    assert draft.spec_hash.startswith("sha256:")
    assert draft.version_id is None

    record = draft.to_record()
    assert record["status"] == "draft"
    assert record["direction"] == "higher_is_better"
    assert record["formula"]["expression"] == "rank(roe_ttm) + rank(gross_margin_ttm) - rank(volatility_20d)"
    assert record["inputs"][0]["dataset_version"] == FUNDAMENTALS_VERSION
    assert record["windows"][0]["length"] == 20
    assert record["missing_value_policy"]["strategy"] == "drop"
    assert record["post_process"][0]["method"] == "winsorize"
    assert record["implementation_hash"] == IMPLEMENTATION_HASH
    json.dumps(record, sort_keys=True)

    with pytest.raises(FrozenInstanceError):
        draft.name = "mutated"  # type: ignore[misc]
    with pytest.raises(TypeError):
        draft.inputs[0].metadata["field"] = "mutated"  # type: ignore[index]
    with pytest.raises(TypeError):
        draft.post_process[0].parameters["upper"] = 1.0  # type: ignore[index]


def test_factor_definition_rejects_latest_alias_and_incomplete_spec() -> None:
    with pytest.raises(FactorDefinitionError, match="concrete Dataset Version"):
        FactorInput(
            input_id="roe_ttm",
            dataset_name="fundamentals_pit",
            dataset_version="latest",
            field_name="roe_ttm",
        )

    with pytest.raises(FactorDefinitionError, match="implementation_hash"):
        _quality_factor_draft(implementation_hash="sha256:not-a-real-hash")

    with pytest.raises(FactorDefinitionError, match="window length"):
        _quality_factor_draft(windows=(FactorWindow(name="bad", length=0, unit="trading_day"),))

    with pytest.raises(FactorDefinitionError, match="fill_value"):
        _quality_factor_draft(
            missing_value_policy=MissingValuePolicy(strategy=MissingValueStrategy.FILL_CONSTANT),
        )

    with pytest.raises(FactorDefinitionError, match="formula expression"):
        _quality_factor_draft(formula=FactorFormula(expression=" "))


def test_factor_definition_repository_publishes_immutably_retires_separately_and_audits(tmp_path) -> None:
    repository = LocalFactorDefinitionRepository(tmp_path / "factor-definitions")
    draft = _quality_factor_draft()

    repository.save_draft(draft)
    loaded_draft = repository.get_draft("quality_composite", "1.0.0")
    assert loaded_draft.status is FactorDefinitionStatus.DRAFT
    assert loaded_draft.spec_hash == draft.spec_hash

    published = repository.publish_draft(
        "quality_composite",
        "1.0.0",
        published_at=PUBLISHED_AT,
        published_by_run_id="run-publish",
        published_by_stage_id="stage-publish",
        trace_id="trace-factor",
    )
    assert published.status is FactorDefinitionStatus.PUBLISHED
    assert published.version_id is not None
    assert published.version_id.startswith("fdv_")
    assert published.published_at == PUBLISHED_AT
    assert repository.version_for_semantic("quality_composite", "1.0.0") == published.version_id
    assert repository.get_version(published.version_id).to_record() == published.to_record()

    changed_draft = _quality_factor_draft(formula=FactorFormula(expression="rank(roe_ttm)"))
    repository.save_draft(changed_draft)
    with pytest.raises(FactorDefinitionError, match="published semantic version cannot be modified"):
        repository.publish_draft(
            "quality_composite",
            "1.0.0",
            published_at=PUBLISHED_AT,
            published_by_run_id="run-publish-conflict",
        )

    assert repository.get_version(published.version_id).formula.expression == draft.formula.expression

    retirement = repository.retire_version(
        published.version_id,
        retired_at=RETIRED_AT,
        retired_by_run_id="run-retire",
        reason="superseded by quality_composite@1.1.0",
        trace_id="trace-retire",
    )
    assert retirement.status is FactorDefinitionStatus.RETIRED
    assert retirement.version_id == published.version_id
    assert repository.version_status(published.version_id) is FactorDefinitionStatus.RETIRED
    assert repository.get_version(published.version_id).status is FactorDefinitionStatus.PUBLISHED

    audit_actions = [event.action for event in repository.list_audit_events()]
    assert audit_actions == ["draft_saved", "published", "draft_saved", "retired"]


def _quality_factor_draft(**overrides) -> FactorDefinition:
    values = {
        "definition_id": "quality_composite",
        "semantic_version": "1.0.0",
        "name": "Quality Composite",
        "description": "Ranks profitable companies while penalizing near-term volatility.",
        "category": "quality",
        "direction": FactorDirection.HIGHER_IS_BETTER,
        "formula": FactorFormula(
            expression="rank(roe_ttm) + rank(gross_margin_ttm) - rank(volatility_20d)",
            language="serenity_factor_dsl",
            engine_version="draft-1",
        ),
        "inputs": (
            FactorInput(
                input_id="roe_ttm",
                dataset_name="fundamentals_pit",
                dataset_version=FUNDAMENTALS_VERSION,
                field_name="roe_ttm",
                kind=FactorInputKind.DATASET_FIELD,
                data_type="float64",
                metadata={"temporal": "pit"},
            ),
            FactorInput(
                input_id="gross_margin_ttm",
                dataset_name="fundamentals_pit",
                dataset_version=FUNDAMENTALS_VERSION,
                field_name="gross_margin_ttm",
                kind=FactorInputKind.DATASET_FIELD,
                data_type="float64",
            ),
            FactorInput(
                input_id="volatility_20d",
                dataset_name="adjusted_daily_bars",
                dataset_version=BARS_VERSION,
                field_name="close",
                kind=FactorInputKind.DATASET_FIELD,
                data_type="float64",
            ),
        ),
        "windows": (
            FactorWindow(name="momentum_lookback", length=20, unit="trading_day", min_periods=15),
        ),
        "missing_value_policy": MissingValuePolicy(
            strategy=MissingValueStrategy.DROP,
            max_missing_ratio=0.05,
        ),
        "post_process": (
            PostProcessingStep(method="winsorize", parameters={"lower": 0.01, "upper": 0.99}),
            PostProcessingStep(method="zscore", parameters={"by": "trade_date"}),
        ),
        "implementation_hash": IMPLEMENTATION_HASH,
        "created_at": CREATED_AT,
        "created_by_run_id": "run-factor-draft",
        "source_commit": "07b5d526",
    }
    values.update(overrides)
    return FactorDefinition.draft(**values)
