from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


PROMPT_REGISTRY_CONTRACT_VERSION = "research.prompt_registry@1.0.0"
PROMPT_TEMPLATE_SCHEMA_NAME = "research.prompt_template"
PROMPT_TEMPLATE_SCHEMA_VERSION = "1.0.0"
PROMPT_OUTPUT_SCHEMA_SCHEMA_NAME = "research.prompt_output_schema"
PROMPT_OUTPUT_SCHEMA_SCHEMA_VERSION = "1.0.0"
PROMPT_TOOL_SCHEMA_NAME = "research.prompt_tool"
PROMPT_TOOL_SCHEMA_VERSION = "1.0.0"
MODEL_CAPABILITY_SCHEMA_NAME = "research.model_capability"
MODEL_CAPABILITY_SCHEMA_VERSION = "1.0.0"
PROMPT_RUN_BINDING_SCHEMA_NAME = "research.prompt_run_binding"
PROMPT_RUN_BINDING_SCHEMA_VERSION = "1.0.0"

EVIDENCE_BUNDLE_SCHEMA_NAME = "research.evidence_bundle"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_FORBIDDEN_TOOL_SCOPES = frozenset(
    {
        "brokerage",
        "database_write",
        "db_write",
        "filesystem_write",
        "shell",
        "trade",
        "trading",
    }
)


class PromptRegistryError(ValueError):
    """Raised when prompt registry declarations or lookups are unsafe."""


class AgentPromptRole(StrEnum):
    TECHNICAL = "technical"
    INTEL = "intel"
    RISK_PORTFOLIO = "risk_portfolio"
    DECISION = "decision"


class PromptPublicationStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ToolSideEffect(StrEnum):
    NONE = "none"
    READ_ONLY = "read_only"


class RegistryCompatibilityStatus(StrEnum):
    IDENTICAL = "identical"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING = "breaking"


@dataclass(frozen=True, slots=True)
class RegistryCompatibilityReport:
    status: RegistryCompatibilityStatus
    breaking_changes: tuple[str, ...] = ()
    compatible_changes: tuple[str, ...] = ()

    @property
    def is_backward_compatible(self) -> bool:
        return self.status in {
            RegistryCompatibilityStatus.IDENTICAL,
            RegistryCompatibilityStatus.BACKWARD_COMPATIBLE,
        }

    @property
    def requires_major_version(self) -> bool:
        return self.status is RegistryCompatibilityStatus.BREAKING


@dataclass(frozen=True, slots=True)
class OutputSchemaDeclaration:
    schema_name: str
    schema_version: str
    json_schema: Mapping[str, Any]
    description: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = PROMPT_REGISTRY_CONTRACT_VERSION
    declaration_schema_name: str = PROMPT_OUTPUT_SCHEMA_SCHEMA_NAME
    declaration_schema_version: str = PROMPT_OUTPUT_SCHEMA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))
        object.__setattr__(self, "json_schema", MappingProxyType(_json_schema_mapping(self.json_schema)))
        object.__setattr__(self, "description", _optional_string(self.description))
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "declaration_schema_name", _required_string("declaration_schema_name", self.declaration_schema_name))
        object.__setattr__(
            self,
            "declaration_schema_version",
            _required_semver("declaration_schema_version", self.declaration_schema_version),
        )

    @property
    def schema_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def compare_compatibility(self, candidate: OutputSchemaDeclaration) -> RegistryCompatibilityReport:
        if type(candidate) is not OutputSchemaDeclaration:
            raise PromptRegistryError("candidate must be an OutputSchemaDeclaration")
        if candidate.schema_name != self.schema_name:
            raise PromptRegistryError("schema names must match for compatibility comparison")
        if self.schema_hash == candidate.schema_hash:
            return RegistryCompatibilityReport(RegistryCompatibilityStatus.IDENTICAL)

        previous = self.json_schema
        incoming = candidate.json_schema
        breaking_changes: list[str] = []
        compatible_changes: list[str] = []

        if previous.get("type") != incoming.get("type"):
            breaking_changes.append("changed JSON Schema type")
        if previous.get("additionalProperties") != incoming.get("additionalProperties"):
            breaking_changes.append("changed additionalProperties")

        previous_properties = _schema_properties(previous)
        incoming_properties = _schema_properties(incoming)
        previous_required = tuple(previous.get("required", ()))
        incoming_required = tuple(incoming.get("required", ()))

        for field_name, previous_definition in previous_properties.items():
            incoming_definition = incoming_properties.get(field_name)
            if incoming_definition is None:
                breaking_changes.append(f"removed property: {field_name}")
                continue
            if _canonical_json(previous_definition) != _canonical_json(incoming_definition):
                breaking_changes.append(f"changed property schema: {field_name}")

        for field_name in incoming_properties:
            if field_name not in previous_properties:
                if field_name in incoming_required:
                    breaking_changes.append(f"added required property: {field_name}")
                else:
                    compatible_changes.append(f"added optional property: {field_name}")

        if previous_required != incoming_required:
            breaking_changes.append("changed required properties")

        if breaking_changes:
            return RegistryCompatibilityReport(
                RegistryCompatibilityStatus.BREAKING,
                breaking_changes=tuple(breaking_changes),
                compatible_changes=tuple(compatible_changes),
            )
        return RegistryCompatibilityReport(
            RegistryCompatibilityStatus.BACKWARD_COMPATIBLE,
            compatible_changes=tuple(compatible_changes),
        )

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.declaration_schema_name,
            "schema_version": self.declaration_schema_version,
            "output_schema_name": self.schema_name,
            "output_schema_version": self.schema_version,
            "description": self.description,
            "json_schema": _copy_json_value(self.json_schema),
            "metadata": dict(self.metadata),
        }
        if include_hash:
            record["schema_hash"] = self.schema_hash
        return _drop_none(record)


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    tool_name: str
    tool_version: str
    description: str
    input_schema: Mapping[str, Any]
    side_effect: ToolSideEffect = ToolSideEffect.NONE
    allowed_scopes: Sequence[str] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = PROMPT_REGISTRY_CONTRACT_VERSION
    schema_name: str = PROMPT_TOOL_SCHEMA_NAME
    schema_version: str = PROMPT_TOOL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _required_string("tool_name", self.tool_name))
        object.__setattr__(self, "tool_version", _required_semver("tool_version", self.tool_version))
        object.__setattr__(self, "description", _required_string("description", self.description))
        scopes = tuple(_required_string("allowed_scope", scope) for scope in self.allowed_scopes)
        forbidden = sorted(set(scopes) & _FORBIDDEN_TOOL_SCOPES)
        if forbidden:
            raise PromptRegistryError(f"forbidden tool category: {', '.join(forbidden)}")
        object.__setattr__(self, "input_schema", MappingProxyType(_json_schema_mapping(self.input_schema, require_properties=False)))
        object.__setattr__(self, "side_effect", ToolSideEffect(self.side_effect))
        object.__setattr__(self, "allowed_scopes", scopes)
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def tool_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "description": self.description,
            "input_schema": _copy_json_value(self.input_schema),
            "side_effect": self.side_effect.value,
            "allowed_scopes": list(self.allowed_scopes),
            "metadata": dict(self.metadata),
        }
        if include_hash:
            record["tool_hash"] = self.tool_hash
        return record


@dataclass(frozen=True, slots=True)
class ModelCapabilityDeclaration:
    capability_id: str
    capability_version: str
    provider_family: str
    model_family: str
    supports_json_schema: bool
    supports_tool_calls: bool
    max_context_tokens: int
    max_output_tokens: int
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = PROMPT_REGISTRY_CONTRACT_VERSION
    schema_name: str = MODEL_CAPABILITY_SCHEMA_NAME
    schema_version: str = MODEL_CAPABILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability_id", _required_string("capability_id", self.capability_id))
        object.__setattr__(self, "capability_version", _required_semver("capability_version", self.capability_version))
        object.__setattr__(self, "provider_family", _required_string("provider_family", self.provider_family))
        object.__setattr__(self, "model_family", _required_string("model_family", self.model_family))
        object.__setattr__(self, "supports_json_schema", _required_bool("supports_json_schema", self.supports_json_schema))
        object.__setattr__(self, "supports_tool_calls", _required_bool("supports_tool_calls", self.supports_tool_calls))
        object.__setattr__(self, "max_context_tokens", _positive_int("max_context_tokens", self.max_context_tokens))
        object.__setattr__(self, "max_output_tokens", _positive_int("max_output_tokens", self.max_output_tokens))
        if self.max_output_tokens > self.max_context_tokens:
            raise PromptRegistryError("max_output_tokens cannot exceed max_context_tokens")
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def capability_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "provider_family": self.provider_family,
            "model_family": self.model_family,
            "supports_json_schema": self.supports_json_schema,
            "supports_tool_calls": self.supports_tool_calls,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "metadata": dict(self.metadata),
        }
        if include_hash:
            record["capability_hash"] = self.capability_hash
        return record


@dataclass(frozen=True, slots=True)
class PromptDeclaration:
    prompt_id: str
    prompt_version: str
    role: AgentPromptRole
    prompt_template: str
    output_schema_name: str
    output_schema_version: str
    model_capability_id: str
    model_capability_version: str
    tool_versions: Mapping[str, str] = field(default_factory=dict)
    evidence_bundle_schema_name: str = EVIDENCE_BUNDLE_SCHEMA_NAME
    evidence_bundle_schema_version: str = EVIDENCE_BUNDLE_SCHEMA_VERSION
    required_policies: Sequence[str] = (
        "use_only_included_evidence",
        "cite_evidence_ids_and_hashes",
        "no_llm_recompute",
    )
    publication_status: PromptPublicationStatus = PromptPublicationStatus.DRAFT
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = PROMPT_REGISTRY_CONTRACT_VERSION
    schema_name: str = PROMPT_TEMPLATE_SCHEMA_NAME
    schema_version: str = PROMPT_TEMPLATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "prompt_id", _required_string("prompt_id", self.prompt_id))
        object.__setattr__(self, "prompt_version", _required_semver("prompt_version", self.prompt_version))
        object.__setattr__(self, "role", AgentPromptRole(self.role))
        object.__setattr__(self, "prompt_template", _required_string("prompt_template", self.prompt_template))
        object.__setattr__(self, "output_schema_name", _required_string("output_schema_name", self.output_schema_name))
        object.__setattr__(
            self,
            "output_schema_version",
            _required_semver("output_schema_version", self.output_schema_version),
        )
        object.__setattr__(self, "model_capability_id", _required_string("model_capability_id", self.model_capability_id))
        object.__setattr__(
            self,
            "model_capability_version",
            _required_semver("model_capability_version", self.model_capability_version),
        )
        object.__setattr__(self, "tool_versions", MappingProxyType(_semver_mapping("tool_versions", self.tool_versions)))
        object.__setattr__(
            self,
            "evidence_bundle_schema_name",
            _required_string("evidence_bundle_schema_name", self.evidence_bundle_schema_name),
        )
        object.__setattr__(
            self,
            "evidence_bundle_schema_version",
            _required_semver("evidence_bundle_schema_version", self.evidence_bundle_schema_version),
        )
        policies = tuple(_required_string("required_policy", policy) for policy in self.required_policies)
        if "no_llm_recompute" not in policies:
            raise PromptRegistryError("required_policies must include no_llm_recompute")
        object.__setattr__(self, "required_policies", policies)
        object.__setattr__(self, "publication_status", PromptPublicationStatus(self.publication_status))
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def prompt_hash(self) -> str:
        return _hash_record(self._immutable_record())

    def publish(self) -> PromptDeclaration:
        return PromptDeclaration(
            prompt_id=self.prompt_id,
            prompt_version=self.prompt_version,
            role=self.role,
            prompt_template=self.prompt_template,
            output_schema_name=self.output_schema_name,
            output_schema_version=self.output_schema_version,
            model_capability_id=self.model_capability_id,
            model_capability_version=self.model_capability_version,
            tool_versions=self.tool_versions,
            evidence_bundle_schema_name=self.evidence_bundle_schema_name,
            evidence_bundle_schema_version=self.evidence_bundle_schema_version,
            required_policies=self.required_policies,
            publication_status=PromptPublicationStatus.PUBLISHED,
            metadata=self.metadata,
            contract_version=self.contract_version,
            schema_name=self.schema_name,
            schema_version=self.schema_version,
        )

    def _immutable_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "role": self.role.value,
            "prompt_template": self.prompt_template,
            "output_schema_name": self.output_schema_name,
            "output_schema_version": self.output_schema_version,
            "model_capability_id": self.model_capability_id,
            "model_capability_version": self.model_capability_version,
            "tool_versions": dict(sorted(self.tool_versions.items())),
            "evidence_bundle_schema_name": self.evidence_bundle_schema_name,
            "evidence_bundle_schema_version": self.evidence_bundle_schema_version,
            "required_policies": list(self.required_policies),
            "metadata": dict(self.metadata),
        }

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = self._immutable_record()
        record["publication_status"] = self.publication_status.value
        if include_hash:
            record["prompt_hash"] = self.prompt_hash
        return record


@dataclass(frozen=True, slots=True)
class PromptRunBindingRequest:
    run_id: str
    stage_id: str
    trace_id: str
    role: AgentPromptRole
    prompt_id: str
    prompt_version: str
    resolved_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "role", AgentPromptRole(self.role))
        object.__setattr__(self, "prompt_id", _required_string("prompt_id", self.prompt_id))
        object.__setattr__(self, "prompt_version", _required_semver("prompt_version", self.prompt_version))
        object.__setattr__(self, "resolved_at", _aware_datetime("resolved_at", self.resolved_at))


@dataclass(frozen=True, slots=True)
class PromptRunBinding:
    request: PromptRunBindingRequest
    prompt: PromptDeclaration
    output_schema: OutputSchemaDeclaration
    tools: tuple[ToolDeclaration, ...]
    model_capability: ModelCapabilityDeclaration
    contract_version: str = PROMPT_REGISTRY_CONTRACT_VERSION
    schema_name: str = PROMPT_RUN_BINDING_SCHEMA_NAME
    schema_version: str = PROMPT_RUN_BINDING_SCHEMA_VERSION

    @property
    def binding_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "run_id": self.request.run_id,
            "stage_id": self.request.stage_id,
            "trace_id": self.request.trace_id,
            "role": self.request.role.value,
            "resolved_at": self.request.resolved_at.isoformat(),
            "prompt": {
                "prompt_id": self.prompt.prompt_id,
                "prompt_version": self.prompt.prompt_version,
                "prompt_hash": self.prompt.prompt_hash,
            },
            "output_schema": {
                "schema_name": self.output_schema.schema_name,
                "schema_version": self.output_schema.schema_version,
                "schema_hash": self.output_schema.schema_hash,
            },
            "tools": [
                {
                    "tool_name": tool.tool_name,
                    "tool_version": tool.tool_version,
                    "tool_hash": tool.tool_hash,
                }
                for tool in self.tools
            ],
            "model_capability": {
                "capability_id": self.model_capability.capability_id,
                "capability_version": self.model_capability.capability_version,
                "capability_hash": self.model_capability.capability_hash,
            },
        }
        if include_hash:
            record["binding_hash"] = self.binding_hash
        return record


@dataclass(slots=True)
class PromptSchemaRegistry:
    _output_schemas: dict[tuple[str, str], OutputSchemaDeclaration] = field(default_factory=dict)
    _output_schema_order: list[str] = field(default_factory=list)
    _tools: dict[tuple[str, str], ToolDeclaration] = field(default_factory=dict)
    _tool_order: list[str] = field(default_factory=list)
    _model_capabilities: dict[tuple[str, str], ModelCapabilityDeclaration] = field(default_factory=dict)
    _model_capability_order: list[str] = field(default_factory=list)
    _prompts: dict[tuple[str, str], PromptDeclaration] = field(default_factory=dict)
    _prompt_order: list[str] = field(default_factory=list)

    def register_output_schema(self, declaration: OutputSchemaDeclaration) -> OutputSchemaDeclaration:
        if type(declaration) is not OutputSchemaDeclaration:
            raise PromptRegistryError("declaration must be an OutputSchemaDeclaration")
        key = (declaration.schema_name, declaration.schema_version)
        if key in self._output_schemas:
            raise PromptRegistryError(
                f"Output schema {declaration.schema_name} version {declaration.schema_version} is already registered"
            )
        existing_versions = self.output_schema_versions(declaration.schema_name)
        if existing_versions:
            latest = self.latest_output_schema(declaration.schema_name)
            if _parse_semver(declaration.schema_version) <= _parse_semver(latest.schema_version):
                raise PromptRegistryError(
                    f"Output schema {declaration.schema_name} version {declaration.schema_version} "
                    f"must be newer than {latest.schema_version}"
                )
            compatibility = latest.compare_compatibility(declaration)
            if (
                not compatibility.is_backward_compatible
                and _parse_semver(declaration.schema_version)[0] == _parse_semver(latest.schema_version)[0]
            ):
                raise PromptRegistryError(
                    f"Output schema {declaration.schema_name} change requires a new major version: "
                    + "; ".join(compatibility.breaking_changes)
                )
        elif declaration.schema_name not in self._output_schema_order:
            self._output_schema_order.append(declaration.schema_name)
        self._output_schemas[key] = declaration
        return declaration

    def register_tool(self, declaration: ToolDeclaration) -> ToolDeclaration:
        if type(declaration) is not ToolDeclaration:
            raise PromptRegistryError("declaration must be a ToolDeclaration")
        key = (declaration.tool_name, declaration.tool_version)
        if key in self._tools:
            raise PromptRegistryError(
                f"Tool {declaration.tool_name} version {declaration.tool_version} is already registered"
            )
        if declaration.side_effect not in {ToolSideEffect.NONE, ToolSideEffect.READ_ONLY}:
            raise PromptRegistryError("tool side effects must be none or read_only")
        if declaration.tool_name not in self._tool_order:
            self._tool_order.append(declaration.tool_name)
        self._tools[key] = declaration
        return declaration

    def register_model_capability(self, declaration: ModelCapabilityDeclaration) -> ModelCapabilityDeclaration:
        if type(declaration) is not ModelCapabilityDeclaration:
            raise PromptRegistryError("declaration must be a ModelCapabilityDeclaration")
        key = (declaration.capability_id, declaration.capability_version)
        if key in self._model_capabilities:
            raise PromptRegistryError(
                f"Model capability {declaration.capability_id} version {declaration.capability_version} "
                "is already registered"
            )
        if declaration.capability_id not in self._model_capability_order:
            self._model_capability_order.append(declaration.capability_id)
        self._model_capabilities[key] = declaration
        return declaration

    def register_prompt(self, declaration: PromptDeclaration) -> PromptDeclaration:
        if type(declaration) is not PromptDeclaration:
            raise PromptRegistryError("declaration must be a PromptDeclaration")
        key = (declaration.prompt_id, declaration.prompt_version)
        if key in self._prompts:
            raise PromptRegistryError(
                f"Prompt {declaration.prompt_id} version {declaration.prompt_version} is already registered"
            )
        self._validate_prompt_references(declaration)
        if declaration.prompt_id not in self._prompt_order:
            self._prompt_order.append(declaration.prompt_id)
        self._prompts[key] = declaration
        return declaration

    def publish_prompt(self, prompt_id: str, prompt_version: str) -> PromptDeclaration:
        key = (_required_string("prompt_id", prompt_id), _required_semver("prompt_version", prompt_version))
        prompt = self.get_prompt(*key)
        self._validate_prompt_references(prompt)
        if prompt.publication_status is PromptPublicationStatus.PUBLISHED:
            return prompt
        published = prompt.publish()
        self._prompts[key] = published
        return published

    def resolve_for_run(self, request: PromptRunBindingRequest) -> PromptRunBinding:
        if type(request) is not PromptRunBindingRequest:
            raise PromptRegistryError("request must be a PromptRunBindingRequest")
        prompt = self.get_prompt(request.prompt_id, request.prompt_version)
        if prompt.publication_status is not PromptPublicationStatus.PUBLISHED:
            raise PromptRegistryError("run prompt binding requires a published prompt")
        if prompt.role is not request.role:
            raise PromptRegistryError("prompt role does not match request role")
        output_schema, tools, model = self._validate_prompt_references(prompt)
        return PromptRunBinding(
            request=request,
            prompt=prompt,
            output_schema=output_schema,
            tools=tools,
            model_capability=model,
        )

    def get_output_schema(self, schema_name: str, schema_version: str) -> OutputSchemaDeclaration:
        key = (_required_string("schema_name", schema_name), _required_semver("schema_version", schema_version))
        try:
            return self._output_schemas[key]
        except KeyError as exc:
            raise PromptRegistryError(f"Output schema not registered: {key[0]} {key[1]}") from exc

    def latest_output_schema(self, schema_name: str) -> OutputSchemaDeclaration:
        schema_id = _required_string("schema_name", schema_name)
        versions = [version for name, version in self._output_schemas if name == schema_id]
        if not versions:
            raise PromptRegistryError(f"Output schema not registered: {schema_id}")
        return self.get_output_schema(schema_id, max(versions, key=_parse_semver))

    def output_schema_versions(self, schema_name: str) -> tuple[str, ...]:
        schema_id = _required_string("schema_name", schema_name)
        versions = [version for name, version in self._output_schemas if name == schema_id]
        return tuple(sorted(versions, key=_parse_semver))

    def output_schema_names(self) -> tuple[str, ...]:
        return tuple(self._output_schema_order)

    def get_tool(self, tool_name: str, tool_version: str) -> ToolDeclaration:
        key = (_required_string("tool_name", tool_name), _required_semver("tool_version", tool_version))
        try:
            return self._tools[key]
        except KeyError as exc:
            raise PromptRegistryError(f"Tool not registered: {key[0]} {key[1]}") from exc

    def get_model_capability(self, capability_id: str, capability_version: str) -> ModelCapabilityDeclaration:
        key = (
            _required_string("capability_id", capability_id),
            _required_semver("capability_version", capability_version),
        )
        try:
            return self._model_capabilities[key]
        except KeyError as exc:
            raise PromptRegistryError(f"Model capability not registered: {key[0]} {key[1]}") from exc

    def get_prompt(self, prompt_id: str, prompt_version: str) -> PromptDeclaration:
        key = (_required_string("prompt_id", prompt_id), _required_semver("prompt_version", prompt_version))
        try:
            return self._prompts[key]
        except KeyError as exc:
            raise PromptRegistryError(f"Prompt not registered: {key[0]} {key[1]}") from exc

    def prompt_ids(self) -> tuple[str, ...]:
        return tuple(self._prompt_order)

    def default_prompt_for_role(self, role: AgentPromptRole | str) -> PromptDeclaration:
        prompt_role = AgentPromptRole(role)
        matches = [
            prompt
            for prompt in self._prompts.values()
            if prompt.role is prompt_role and prompt.publication_status is PromptPublicationStatus.PUBLISHED
        ]
        if not matches:
            raise PromptRegistryError(f"No published default prompt for role: {prompt_role.value}")
        return max(matches, key=lambda item: _parse_semver(item.prompt_version))

    def _validate_prompt_references(
        self,
        prompt: PromptDeclaration,
    ) -> tuple[OutputSchemaDeclaration, tuple[ToolDeclaration, ...], ModelCapabilityDeclaration]:
        output_schema = self.get_output_schema(prompt.output_schema_name, prompt.output_schema_version)
        model = self.get_model_capability(prompt.model_capability_id, prompt.model_capability_version)
        if not model.supports_json_schema:
            raise PromptRegistryError("model capability must support JSON Schema outputs")
        tools = tuple(self.get_tool(name, version) for name, version in sorted(prompt.tool_versions.items()))
        for tool in tools:
            if tool.side_effect not in {ToolSideEffect.NONE, ToolSideEffect.READ_ONLY}:
                raise PromptRegistryError("published prompts may only reference no-side-effect/read-only tools")
        return output_schema, tools, model


def default_prompt_schema_registry() -> PromptSchemaRegistry:
    registry = PromptSchemaRegistry()
    for role in (
        AgentPromptRole.TECHNICAL,
        AgentPromptRole.INTEL,
        AgentPromptRole.RISK_PORTFOLIO,
        AgentPromptRole.DECISION,
    ):
        registry.register_output_schema(_role_output_schema(role))
    registry.register_tool(
        ToolDeclaration(
            tool_name="evidence_bundle.read",
            tool_version="1.0.0",
            description="Read an already-built EvidenceBundle prompt payload by id.",
            input_schema={
                "type": "object",
                "properties": {"bundle_id": {"type": "string"}},
                "required": ["bundle_id"],
                "additionalProperties": False,
            },
            side_effect=ToolSideEffect.READ_ONLY,
            allowed_scopes=("evidence_bundle",),
            metadata={"runtime": "registry_only_no_execution"},
        )
    )
    registry.register_model_capability(
        ModelCapabilityDeclaration(
            capability_id="registry_only_json_model",
            capability_version="1.0.0",
            provider_family="registry_only",
            model_family="json_schema_capable",
            supports_json_schema=True,
            supports_tool_calls=False,
            max_context_tokens=8192,
            max_output_tokens=2048,
            metadata={"calls_real_model": "false"},
        )
    )
    for prompt in _default_prompts():
        registry.register_prompt(prompt)
        registry.publish_prompt(prompt.prompt_id, prompt.prompt_version)
    return registry


def _role_output_schema(role: AgentPromptRole) -> OutputSchemaDeclaration:
    schema_name = f"research.agent.{role.value}_output"
    return OutputSchemaDeclaration(
        schema_name=schema_name,
        schema_version="1.0.0",
        description=f"Structured {role.value} Agent output contract for cited research claims.",
        json_schema={
            "type": "object",
            "properties": {
                "claims": {"type": "array", "items": {"type": "object"}},
                "citations": {"type": "array", "items": {"type": "object"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["claims", "citations"],
            "additionalProperties": False,
        },
        metadata={"role": role.value, "claim_source": "research.evidence@1.0.0"},
    )


def _default_prompts() -> tuple[PromptDeclaration, ...]:
    common = (
        "Use only included EvidenceBundle evidence_records. Preserve every evidence_id, content_hash, "
        "artifact_hash, dataset_versions, run_id and stage_id in citations. Numeric claims must cite "
        "deterministic evidence with formula_version. Never recompute returns, risk, drawdown, costs, "
        "orders, ledger state, gate outcomes or source trust labels. If evidence is missing, return "
        "insufficient_evidence rather than inventing facts."
    )
    prompts = (
        (
            "technical_research",
            AgentPromptRole.TECHNICAL,
            common
            + " Focus on technical, factor and deterministic quant evidence; keep Screen/Factor evidence "
            "outside formal portfolio backtest conclusions.",
        ),
        (
            "intel_research",
            AgentPromptRole.INTEL,
            common
            + " Use source trust metadata, published_at, observed_at and corroboration flags; low or "
            "untrusted sources cannot support strong claims alone.",
        ),
        (
            "risk_portfolio_research",
            AgentPromptRole.RISK_PORTFOLIO,
            common
            + " RiskPolicy block or not_evaluable outcomes are hard gates. Explain them but do not override "
            "risk, bias audit, cost, ledger or portfolio constraints.",
        ),
        (
            "decision_research",
            AgentPromptRole.DECISION,
            common
            + " Synthesize only cited preceding evidence. Do not introduce new facts or upgrade report level "
            "when citations are missing or conflicts remain unresolved.",
        ),
    )
    return tuple(
        PromptDeclaration(
            prompt_id=prompt_id,
            prompt_version="1.0.0",
            role=role,
            prompt_template=template,
            output_schema_name=f"research.agent.{role.value}_output",
            output_schema_version="1.0.0",
            model_capability_id="registry_only_json_model",
            model_capability_version="1.0.0",
            tool_versions={"evidence_bundle.read": "1.0.0"},
            publication_status=PromptPublicationStatus.DRAFT,
            metadata={"default": "true"},
        )
        for prompt_id, role, template in prompts
    )


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise PromptRegistryError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _required_semver(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SEMVER_RE.fullmatch(value):
        raise PromptRegistryError(f"{field_name} must be a semantic version")
    return value


def _parse_semver(value: str) -> tuple[int, int, int]:
    value = _required_semver("version", value)
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _required_bool(field_name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise PromptRegistryError(f"{field_name} must be a bool")
    return value


def _positive_int(field_name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise PromptRegistryError(f"{field_name} must be a positive integer")
    return value


def _aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise PromptRegistryError(f"{field_name} must be timezone-aware")
    return value


def _semver_mapping(field_name: str, value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise PromptRegistryError(f"{field_name} must be a mapping")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized[_required_string(f"{field_name} key", key)] = _required_semver(f"{field_name} version", item)
    return dict(sorted(normalized.items()))


def _string_mapping(field_name: str, value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise PromptRegistryError(f"{field_name} must be a mapping")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized[_required_string(f"{field_name} key", key)] = _required_string(f"{field_name} value", item)
    return dict(sorted(normalized.items()))


def _json_schema_mapping(value: Mapping[str, Any], *, require_properties: bool = True) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PromptRegistryError("json_schema must be a mapping")
    copied = _copy_json_value(value)
    if copied.get("type") != "object":
        raise PromptRegistryError("json_schema type must be object")
    copied.setdefault("properties", {})
    properties = copied.get("properties")
    if type(properties) is not dict or (require_properties and not properties):
        raise PromptRegistryError("json_schema properties are required")
    required = copied.get("required", [])
    if type(required) is not list or any(type(item) is not str or not item for item in required):
        raise PromptRegistryError("json_schema required must be a string list")
    missing_required = sorted(set(required) - set(properties))
    if missing_required:
        raise PromptRegistryError("json_schema required fields must be declared properties")
    _canonical_json(copied)
    return copied


def _schema_properties(schema: Mapping[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    if type(properties) is not dict:
        raise PromptRegistryError("json_schema properties must be a mapping")
    return dict(properties)


def _copy_json_value(value: Any) -> Any:
    return json.loads(_canonical_json(_plain_json_value(value)))


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise PromptRegistryError("value must be JSON serializable") from exc


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = _canonical_json(record).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _drop_none(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


def _sha256(value: str) -> str:
    value = _required_string("sha256", value)
    if not _SHA256_RE.fullmatch(value):
        raise PromptRegistryError("hash must match sha256:<64 lowercase hex chars>")
    return value
