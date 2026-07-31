from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from serenity_alpha_lab.application.config_profiles import load_runtime_settings
from serenity_alpha_lab.evidence.prompt_registry import (
    AgentPromptRole,
    PromptRunBindingRequest,
    default_prompt_schema_registry,
)
from serenity_alpha_lab.repositories.agent_stage_store import (
    AgentModelCallReceipt,
    AgentStageDefinition,
    AgentStageFailurePolicy,
    AgentStageResumeAction,
    AgentStageStatus,
    AgentStageStore,
    AgentStageStoreConflict,
    AgentStageStoreError,
    deterministic_agent_stage_id,
)
from serenity_alpha_lab.repositories.database import create_database_engine, resolve_database_profile


NOW = datetime(2026, 7, 27, 9, 30, tzinfo=UTC)
INPUT_HASH = "sha256:" + "1" * 64
REQUEST_HASH = "sha256:" + "2" * 64
RESPONSE_HASH = "sha256:" + "3" * 64
OUTPUT_HASH = "sha256:" + "4" * 64


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Engine:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": f"sqlite:///{tmp_path / 'agent-stage-store.sqlite'}",
        }
    )
    engine = create_database_engine(resolve_database_profile(settings))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def clock() -> DeterministicClock:
    return DeterministicClock()


def test_agent_stage_store_persists_prompt_binding_and_resumes_after_restart(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    registry = default_prompt_schema_registry()
    technical_prompt = registry.default_prompt_for_role(AgentPromptRole.TECHNICAL)
    decision_prompt = registry.default_prompt_for_role(AgentPromptRole.DECISION)
    technical = _definition(
        stage_name="technical",
        role=AgentPromptRole.TECHNICAL,
        prompt_version=technical_prompt.prompt_version,
        sequence=1,
    )
    decision = _definition(
        stage_name="decision",
        role=AgentPromptRole.DECISION,
        prompt_version=decision_prompt.prompt_version,
        sequence=2,
    )
    technical_binding = registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-agent-stage-001",
            stage_id=technical.stage_id,
            trace_id="trace-agent-stage-001",
            role=AgentPromptRole.TECHNICAL,
            prompt_id=technical_prompt.prompt_id,
            prompt_version=technical_prompt.prompt_version,
            resolved_at=NOW,
        )
    )
    decision_binding = registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-agent-stage-001",
            stage_id=decision.stage_id,
            trace_id="trace-agent-stage-001",
            role=AgentPromptRole.DECISION,
            prompt_id=decision_prompt.prompt_id,
            prompt_version=decision_prompt.prompt_version,
            resolved_at=NOW,
        )
    )
    store = AgentStageStore(sqlite_engine, clock=clock)
    store.create_schema()

    checkpoint = store.register_stage(technical, prompt_binding=technical_binding)
    store.register_stage(decision, prompt_binding=decision_binding)
    store.start_stage(checkpoint.stage_id, attempt=1)
    receipt = store.record_model_call_success(checkpoint.stage_id, _receipt(technical_binding.binding_hash))
    completed = store.complete_stage(
        checkpoint.stage_id,
        output_hash=OUTPUT_HASH,
        output_record={"claims": [], "citations": []},
    )

    restarted = AgentStageStore(sqlite_engine, clock=clock)
    restarted.create_schema()
    persisted = restarted.get_stage(checkpoint.stage_id)
    plan = restarted.resume_plan("run-agent-stage-001")

    assert completed.status is AgentStageStatus.SUCCEEDED
    assert persisted.status is AgentStageStatus.SUCCEEDED
    assert persisted.prompt_binding["binding_hash"] == technical_binding.binding_hash
    assert persisted.output_hash == OUTPUT_HASH
    assert receipt.idempotency_key == "model-call:technical:001"
    assert [(item.stage_id, item.action) for item in plan.items] == [
        (technical.stage_id, AgentStageResumeAction.SKIP_REUSED),
        (decision.stage_id, AgentStageResumeAction.RUN),
    ]
    assert plan.next_stage_id == decision.stage_id


def test_successful_model_call_receipt_is_idempotent_and_conflicts_on_changed_hash(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.TECHNICAL)
    definition = _definition(run_id="run-agent-stage-002", prompt_version=prompt.prompt_version)
    binding = registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-agent-stage-002",
            stage_id=definition.stage_id,
            trace_id="trace-agent-stage-002",
            role=AgentPromptRole.TECHNICAL,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )
    store = AgentStageStore(sqlite_engine, clock=clock)
    store.create_schema()
    checkpoint = store.register_stage(
        definition,
        prompt_binding=binding,
    )
    store.start_stage(checkpoint.stage_id, attempt=1)

    first = store.record_model_call_success(checkpoint.stage_id, _receipt(binding.binding_hash))
    replay = store.record_model_call_success(checkpoint.stage_id, _receipt(binding.binding_hash))
    plan = store.resume_plan("run-agent-stage-002")

    assert replay == first
    assert store.model_call_receipts(checkpoint.stage_id) == (first,)
    assert plan.items[0].action is AgentStageResumeAction.REUSE_MODEL_CALL
    assert plan.items[0].model_call_receipt_hash == first.receipt_hash

    with pytest.raises(AgentStageStoreConflict, match="Model call idempotency conflict"):
        store.record_model_call_success(
            checkpoint.stage_id,
            replace(_receipt(binding.binding_hash), response_hash="sha256:" + "5" * 64),
        )


def test_failure_policy_and_cancel_are_explicit_without_executing_agent_runtime(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    registry = default_prompt_schema_registry()
    intel_prompt = registry.default_prompt_for_role(AgentPromptRole.INTEL)
    decision_prompt = registry.default_prompt_for_role(AgentPromptRole.DECISION)
    store = AgentStageStore(sqlite_engine, clock=clock)
    store.create_schema()
    degrade_definition = _definition(
        run_id="run-agent-stage-003",
        stage_name="intel",
        role=AgentPromptRole.INTEL,
        prompt_version=intel_prompt.prompt_version,
        failure_policy=AgentStageFailurePolicy.DEGRADE,
        sequence=1,
    )
    skip_definition = _definition(
        run_id="run-agent-stage-003",
        stage_name="optional-social-context",
        role=AgentPromptRole.INTEL,
        prompt_version=intel_prompt.prompt_version,
        failure_policy=AgentStageFailurePolicy.SKIP,
        sequence=2,
    )
    fail_definition = _definition(
        run_id="run-agent-stage-003",
        stage_name="decision",
        role=AgentPromptRole.DECISION,
        prompt_version=decision_prompt.prompt_version,
        failure_policy=AgentStageFailurePolicy.FAIL_RUN,
        sequence=3,
    )
    degrade = store.register_stage(
        degrade_definition,
        prompt_binding=_binding(
            registry,
            prompt=intel_prompt,
            definition=degrade_definition,
            trace_id="trace-agent-stage-003",
        ),
    )
    skip = store.register_stage(
        skip_definition,
        prompt_binding=_binding(
            registry,
            prompt=intel_prompt,
            definition=skip_definition,
            trace_id="trace-agent-stage-003",
        ),
    )
    fail = store.register_stage(
        fail_definition,
        prompt_binding=_binding(
            registry,
            prompt=decision_prompt,
            definition=fail_definition,
            trace_id="trace-agent-stage-003",
        ),
    )

    store.start_stage(degrade.stage_id, attempt=1)
    degraded = store.record_stage_failure(degrade.stage_id, reason="source trust conflict")
    skipped = store.record_stage_failure(skip.stage_id, reason="optional source missing")
    store.start_stage(fail.stage_id, attempt=1)
    cancelled_count = store.request_cancel("run-agent-stage-003", reason="user cancelled")
    plan = store.resume_plan("run-agent-stage-003")

    assert degraded.status is AgentStageStatus.DEGRADED
    assert skipped.status is AgentStageStatus.SKIPPED
    assert cancelled_count == 1
    assert store.get_stage(fail.stage_id).status is AgentStageStatus.CANCELLED
    assert [(item.stage_id, item.action) for item in plan.items] == [
        (degrade.stage_id, AgentStageResumeAction.SKIP_REUSED),
        (skip.stage_id, AgentStageResumeAction.SKIP_REUSED),
        (fail.stage_id, AgentStageResumeAction.STOP_CANCELLED),
    ]


def test_deterministic_stage_id_requires_concrete_prompt_version_and_hash() -> None:
    first = deterministic_agent_stage_id(
        run_id="run-agent-stage-004",
        stage_name="technical",
        input_hash=INPUT_HASH,
        prompt_version="1.0.0",
    )
    second = deterministic_agent_stage_id(
        run_id="run-agent-stage-004",
        stage_name="technical",
        input_hash=INPUT_HASH,
        prompt_version="1.0.0",
    )

    assert first == second
    assert first.startswith("stage_")

    with pytest.raises(AgentStageStoreError, match="semantic version"):
        deterministic_agent_stage_id(
            run_id="run-agent-stage-004",
            stage_name="technical",
            input_hash=INPUT_HASH,
            prompt_version="latest",
        )

    with pytest.raises(AgentStageStoreError, match="sha256"):
        _definition(input_hash="latest")


def _definition(
    *,
    run_id: str = "run-agent-stage-001",
    stage_name: str = "technical",
    role: AgentPromptRole = AgentPromptRole.TECHNICAL,
    input_hash: str = INPUT_HASH,
    prompt_version: str = "1.0.0",
    sequence: int = 1,
    failure_policy: AgentStageFailurePolicy = AgentStageFailurePolicy.FAIL_RUN,
) -> AgentStageDefinition:
    return AgentStageDefinition(
        run_id=run_id,
        stage_name=stage_name,
        role=role,
        input_hash=input_hash,
        prompt_version=prompt_version,
        sequence=sequence,
        failure_policy=failure_policy,
        max_input_tokens=4_000,
        max_output_tokens=1_000,
        timeout_seconds=60,
        max_retries=1,
        tool_allowlist=("evidence_bundle.read",),
    )


def _receipt(prompt_binding_hash: str) -> AgentModelCallReceipt:
    return AgentModelCallReceipt(
        call_id="call-technical-001",
        idempotency_key="model-call:technical:001",
        provider_family="registry_only",
        model_family="json_schema_capable",
        prompt_binding_hash=prompt_binding_hash,
        request_hash=REQUEST_HASH,
        response_hash=RESPONSE_HASH,
        prompt_tokens=120,
        completion_tokens=80,
        cost_usd=Decimal("0.0123"),
        latency_ms=250,
        completed_at=NOW,
    )


def _binding(
    registry,
    *,
    prompt,
    definition: AgentStageDefinition,
    trace_id: str,
):
    return registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id=definition.run_id,
            stage_id=definition.stage_id,
            trace_id=trace_id,
            role=definition.role,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )
