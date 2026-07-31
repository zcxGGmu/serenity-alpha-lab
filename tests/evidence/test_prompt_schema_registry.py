from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.evidence_bundle_builder import (
    EVIDENCE_BUNDLE_SCHEMA_NAME,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from serenity_alpha_lab.evidence.prompt_registry import (
    AgentPromptRole,
    ModelCapabilityDeclaration,
    OutputSchemaDeclaration,
    PromptDeclaration,
    PromptPublicationStatus,
    PromptRegistryError,
    PromptRunBindingRequest,
    PromptSchemaRegistry,
    RegistryCompatibilityStatus,
    ToolDeclaration,
    ToolSideEffect,
    default_prompt_schema_registry,
)


NOW = datetime(2026, 7, 26, 16, 0, tzinfo=UTC)


def test_default_registry_contains_published_role_prompts_and_resolves_run_binding() -> None:
    registry = default_prompt_schema_registry()

    assert registry.prompt_ids() == (
        "technical_research",
        "intel_research",
        "risk_portfolio_research",
        "decision_research",
    )
    assert registry.output_schema_names() == (
        "research.agent.technical_output",
        "research.agent.intel_output",
        "research.agent.risk_portfolio_output",
        "research.agent.decision_output",
    )

    prompt = registry.default_prompt_for_role(AgentPromptRole.TECHNICAL)
    assert prompt.publication_status is PromptPublicationStatus.PUBLISHED
    assert prompt.prompt_hash.startswith("sha256:")
    assert "never recompute" in prompt.prompt_template.lower()
    assert "evidence_id" in prompt.prompt_template
    assert prompt.evidence_bundle_schema_name == EVIDENCE_BUNDLE_SCHEMA_NAME
    assert prompt.evidence_bundle_schema_version == EVIDENCE_BUNDLE_SCHEMA_VERSION

    binding = registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run_p5_006",
            stage_id="stage_technical",
            trace_id="trace_p5_006",
            role=AgentPromptRole.TECHNICAL,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )
    record = binding.to_record()

    assert record["schema_name"] == "research.prompt_run_binding"
    assert record["prompt"]["prompt_id"] == "technical_research"
    assert record["prompt"]["prompt_hash"] == prompt.prompt_hash
    assert record["output_schema"]["schema_name"] == "research.agent.technical_output"
    assert record["output_schema"]["schema_hash"].startswith("sha256:")
    assert record["model_capability"]["capability_hash"].startswith("sha256:")
    assert record["tools"] == [
        {
            "tool_name": "evidence_bundle.read",
            "tool_version": "1.0.0",
            "tool_hash": registry.get_tool("evidence_bundle.read", "1.0.0").tool_hash,
        }
    ]
    assert "latest" not in json.dumps(record, sort_keys=True)


def test_published_prompt_versions_are_immutable_and_publication_preserves_hash() -> None:
    registry = PromptSchemaRegistry()
    output_schema = _output_schema("research.agent.test_output", "1.0.0")
    tool = ToolDeclaration(
        tool_name="evidence_bundle.read",
        tool_version="1.0.0",
        description="Read prebuilt EvidenceBundle payloads.",
        input_schema={"type": "object", "properties": {"bundle_id": {"type": "string"}}, "required": ["bundle_id"]},
        side_effect=ToolSideEffect.READ_ONLY,
        allowed_scopes=("evidence_bundle",),
    )
    model = ModelCapabilityDeclaration(
        capability_id="offline_json_model",
        capability_version="1.0.0",
        provider_family="registry_only",
        model_family="json_schema_capable",
        supports_json_schema=True,
        supports_tool_calls=False,
        max_context_tokens=8192,
        max_output_tokens=1024,
    )
    registry.register_output_schema(output_schema)
    registry.register_tool(tool)
    registry.register_model_capability(model)

    draft = PromptDeclaration(
        prompt_id="technical_research",
        prompt_version="1.0.0",
        role=AgentPromptRole.TECHNICAL,
        prompt_template="Use only evidence_records and cite evidence_id. Never recompute metrics.",
        output_schema_name=output_schema.schema_name,
        output_schema_version=output_schema.schema_version,
        model_capability_id=model.capability_id,
        model_capability_version=model.capability_version,
        tool_versions={tool.tool_name: tool.tool_version},
        publication_status=PromptPublicationStatus.DRAFT,
    )
    registry.register_prompt(draft)

    published = registry.publish_prompt("technical_research", "1.0.0")

    assert published.publication_status is PromptPublicationStatus.PUBLISHED
    assert published.prompt_hash == draft.prompt_hash

    with pytest.raises(PromptRegistryError, match="already registered"):
        registry.register_prompt(
            PromptDeclaration(
                prompt_id="technical_research",
                prompt_version="1.0.0",
                role=AgentPromptRole.TECHNICAL,
                prompt_template="Changed text for the same published version.",
                output_schema_name=output_schema.schema_name,
                output_schema_version=output_schema.schema_version,
                model_capability_id=model.capability_id,
                model_capability_version=model.capability_version,
                tool_versions={tool.tool_name: tool.tool_version},
            )
        )


def test_output_schema_versions_allow_only_backward_compatible_minor_changes() -> None:
    base = _output_schema("research.agent.example_output", "1.0.0")
    compatible = OutputSchemaDeclaration(
        schema_name="research.agent.example_output",
        schema_version="1.1.0",
        json_schema={
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "citations": {"type": "array"},
                "warnings": {"type": "array"},
            },
            "required": ["claims", "citations"],
            "additionalProperties": False,
        },
    )
    breaking_minor = OutputSchemaDeclaration(
        schema_name="research.agent.example_output",
        schema_version="1.2.0",
        json_schema={
            "type": "object",
            "properties": {"claims": {"type": "object"}},
            "required": ["claims"],
            "additionalProperties": False,
        },
    )
    breaking_major = OutputSchemaDeclaration(
        schema_name="research.agent.example_output",
        schema_version="2.0.0",
        json_schema={
            "type": "object",
            "properties": {"claims": {"type": "object"}},
            "required": ["claims"],
            "additionalProperties": False,
        },
    )

    assert base.compare_compatibility(compatible).status is RegistryCompatibilityStatus.BACKWARD_COMPATIBLE
    assert base.compare_compatibility(breaking_minor).requires_major_version is True

    registry = PromptSchemaRegistry()
    registry.register_output_schema(base)
    registry.register_output_schema(compatible)
    with pytest.raises(PromptRegistryError, match="requires a new major version"):
        registry.register_output_schema(breaking_minor)

    registry.register_output_schema(breaking_major)
    assert registry.latest_output_schema("research.agent.example_output").schema_version == "2.0.0"


def test_registry_rejects_latest_aliases_unsafe_tools_and_unpublished_prompt_resolution() -> None:
    with pytest.raises(PromptRegistryError, match="semantic version"):
        _output_schema("research.agent.bad_output", "latest")

    with pytest.raises(PromptRegistryError, match="forbidden tool category"):
        ToolDeclaration(
            tool_name="shell.run",
            tool_version="1.0.0",
            description="Run shell commands.",
            input_schema={"type": "object"},
            side_effect=ToolSideEffect.READ_ONLY,
            allowed_scopes=("shell",),
        )

    registry = PromptSchemaRegistry()
    output_schema = _output_schema("research.agent.test_output", "1.0.0")
    tool = ToolDeclaration(
        tool_name="evidence_bundle.read",
        tool_version="1.0.0",
        description="Read prebuilt EvidenceBundle payloads.",
        input_schema={"type": "object"},
        side_effect=ToolSideEffect.READ_ONLY,
        allowed_scopes=("evidence_bundle",),
    )
    model = ModelCapabilityDeclaration(
        capability_id="offline_json_model",
        capability_version="1.0.0",
        provider_family="registry_only",
        model_family="json_schema_capable",
        supports_json_schema=True,
        supports_tool_calls=False,
        max_context_tokens=8192,
        max_output_tokens=1024,
    )
    registry.register_output_schema(output_schema)
    registry.register_tool(tool)
    registry.register_model_capability(model)
    registry.register_prompt(
        PromptDeclaration(
            prompt_id="technical_research",
            prompt_version="1.0.0",
            role=AgentPromptRole.TECHNICAL,
            prompt_template="Use only evidence_records and cite evidence_id.",
            output_schema_name=output_schema.schema_name,
            output_schema_version=output_schema.schema_version,
            model_capability_id=model.capability_id,
            model_capability_version=model.capability_version,
            tool_versions={tool.tool_name: tool.tool_version},
            publication_status=PromptPublicationStatus.DRAFT,
        )
    )

    with pytest.raises(PromptRegistryError, match="published"):
        registry.resolve_for_run(
            PromptRunBindingRequest(
                run_id="run_bad",
                stage_id="stage_bad",
                trace_id="trace_bad",
                role=AgentPromptRole.TECHNICAL,
                prompt_id="technical_research",
                prompt_version="1.0.0",
                resolved_at=NOW,
            )
        )


def _output_schema(schema_name: str, schema_version: str) -> OutputSchemaDeclaration:
    return OutputSchemaDeclaration(
        schema_name=schema_name,
        schema_version=schema_version,
        json_schema={
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "citations": {"type": "array"},
            },
            "required": ["claims", "citations"],
            "additionalProperties": False,
        },
    )
