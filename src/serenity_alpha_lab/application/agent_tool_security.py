from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from urllib.parse import urlparse

from serenity_alpha_lab.evidence.prompt_registry import AgentPromptRole, PromptRunBinding, ToolDeclaration, ToolSideEffect


AGENT_TOOL_SECURITY_CONTRACT_VERSION = "research.agent_tool_security@1.0.0"
AGENT_TOOL_AUTHORIZATION_SCHEMA_NAME = "research.agent_tool_authorization"
AGENT_TOOL_AUTHORIZATION_SCHEMA_VERSION = "1.0.0"

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
_URL_FIELD_NAMES = frozenset({"endpoint", "source_url", "uri", "url"})
_LOCAL_HOST_SUFFIXES = (".internal", ".local", ".localhost")
_PROMPT_INJECTION_RE = re.compile(
    r"("
    r"ignore\s+(all\s+)?(previous|prior|system|developer)\s+instructions|"
    r"disregard\s+(all\s+)?(previous|prior|system|developer)\s+instructions|"
    r"system\s+prompt|developer\s+(message|instruction)|"
    r"(call|run|use|invoke)\s+(a\s+)?(tool|function|api|shell)|"
    r"reveal\s+(the\s+)?(prompt|instructions|secret|token|api\s*key)|"
    r"admin\s*=\s*true|root\s*=\s*true|"
    r"shell\.run|api[_\s-]?key|bearer\s+[a-z0-9._-]+|\btoken\b"
    r")",
    flags=re.IGNORECASE,
)


class AgentToolSecurityError(ValueError):
    """Raised when an Agent tool authorization request is structurally invalid."""


class AgentToolAuthorizationStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class AgentToolSecurityIssueCode(StrEnum):
    TOOL_NOT_BOUND = "tool_not_bound"
    TOOL_NOT_STAGE_ALLOWED = "tool_not_stage_allowed"
    TOOL_SIDE_EFFECT_FORBIDDEN = "tool_side_effect_forbidden"
    TOOL_SCOPE_FORBIDDEN = "tool_scope_forbidden"
    INPUT_SCHEMA_VIOLATION = "input_schema_violation"
    UNSAFE_URL = "unsafe_url"
    PROMPT_INJECTION = "prompt_injection"


@dataclass(frozen=True, slots=True)
class AgentToolSecurityIssue:
    code: AgentToolSecurityIssueCode | str
    message: str
    field_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", AgentToolSecurityIssueCode(self.code))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "field_path", _optional_string(self.field_path))

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "code": self.code.value,
                "message": self.message,
                "field_path": self.field_path,
            }
        )


@dataclass(frozen=True, slots=True)
class AgentToolInvocationRequest:
    run_id: str
    stage_id: str
    trace_id: str
    role: AgentPromptRole | str
    prompt_binding: PromptRunBinding
    tool_name: str
    tool_version: str
    arguments: Mapping[str, Any]
    stage_tool_allowlist: Sequence[str] = ()
    contract_version: str = AGENT_TOOL_SECURITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "role", AgentPromptRole(self.role))
        if type(self.prompt_binding) is not PromptRunBinding:
            raise AgentToolSecurityError("prompt_binding must be a PromptRunBinding")
        if self.prompt_binding.request.run_id != self.run_id:
            raise AgentToolSecurityError("prompt binding run_id must match request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise AgentToolSecurityError("prompt binding stage_id must match request")
        if self.prompt_binding.request.trace_id != self.trace_id:
            raise AgentToolSecurityError("prompt binding trace_id must match request")
        if self.prompt_binding.request.role is not self.role:
            raise AgentToolSecurityError("prompt binding role must match request")
        object.__setattr__(self, "tool_name", _required_string("tool_name", self.tool_name))
        object.__setattr__(self, "tool_version", _required_semver("tool_version", self.tool_version))
        if not isinstance(self.arguments, Mapping):
            raise AgentToolSecurityError("arguments must be a mapping")
        object.__setattr__(self, "arguments", MappingProxyType(_copy_json_value(self.arguments)))
        object.__setattr__(
            self,
            "stage_tool_allowlist",
            tuple(_required_string("stage_tool_allowlist item", item) for item in self.stage_tool_allowlist),
        )
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "trace_id": self.trace_id,
            "role": self.role.value,
            "prompt_binding_hash": self.prompt_binding.binding_hash,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "arguments": _copy_json_value(self.arguments),
            "stage_tool_allowlist": list(self.stage_tool_allowlist),
        }


@dataclass(frozen=True, slots=True)
class AgentToolAuthorizationDecision:
    request: AgentToolInvocationRequest
    status: AgentToolAuthorizationStatus | str
    issues: Sequence[AgentToolSecurityIssue] = ()
    safe_arguments: Mapping[str, Any] = field(default_factory=dict)
    tool_hash: str | None = None
    would_execute: bool = False
    contract_version: str = AGENT_TOOL_SECURITY_CONTRACT_VERSION
    schema_name: str = AGENT_TOOL_AUTHORIZATION_SCHEMA_NAME
    schema_version: str = AGENT_TOOL_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.request) is not AgentToolInvocationRequest:
            raise AgentToolSecurityError("request must be an AgentToolInvocationRequest")
        object.__setattr__(self, "status", AgentToolAuthorizationStatus(self.status))
        issues = tuple(self.issues)
        for issue in issues:
            if type(issue) is not AgentToolSecurityIssue:
                raise AgentToolSecurityError("issues must contain AgentToolSecurityIssue objects")
        object.__setattr__(self, "issues", issues)
        if not isinstance(self.safe_arguments, Mapping):
            raise AgentToolSecurityError("safe_arguments must be a mapping")
        object.__setattr__(self, "safe_arguments", MappingProxyType(_copy_json_value(self.safe_arguments)))
        object.__setattr__(self, "tool_hash", _optional_sha256(self.tool_hash))
        object.__setattr__(self, "would_execute", False)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def decision_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "status": self.status.value,
                "request": self.request.to_record(),
                "tool_hash": self.tool_hash,
                "issues": [issue.to_record() for issue in self.issues],
                "safe_arguments": _copy_json_value(self.safe_arguments),
                "would_execute": self.would_execute,
            }
        )
        if include_hash:
            record["decision_hash"] = self.decision_hash
        return record


@dataclass(frozen=True, slots=True)
class AgentToolSecurityGuard:
    allow_http_urls: bool = False

    def authorize(self, request: AgentToolInvocationRequest) -> AgentToolAuthorizationDecision:
        if type(request) is not AgentToolInvocationRequest:
            raise AgentToolSecurityError("request must be an AgentToolInvocationRequest")

        tool = _find_bound_tool(request)
        if tool is None:
            return _deny(
                request,
                AgentToolSecurityIssue(
                    AgentToolSecurityIssueCode.TOOL_NOT_BOUND,
                    f"tool is not bound to prompt: {request.tool_name}@{request.tool_version}",
                ),
            )

        issues: list[AgentToolSecurityIssue] = []
        if request.tool_name not in set(request.stage_tool_allowlist):
            issues.append(
                AgentToolSecurityIssue(
                    AgentToolSecurityIssueCode.TOOL_NOT_STAGE_ALLOWED,
                    f"tool is not in stage allowlist: {request.tool_name}",
                )
            )
            return _decision(request, tool=tool, issues=issues)

        if tool.side_effect not in {ToolSideEffect.NONE, ToolSideEffect.READ_ONLY}:
            issues.append(
                AgentToolSecurityIssue(
                    AgentToolSecurityIssueCode.TOOL_SIDE_EFFECT_FORBIDDEN,
                    f"tool side effect is forbidden: {tool.side_effect.value}",
                )
            )

        forbidden_scopes = sorted(set(tool.allowed_scopes) & _FORBIDDEN_TOOL_SCOPES)
        if forbidden_scopes:
            issues.append(
                AgentToolSecurityIssue(
                    AgentToolSecurityIssueCode.TOOL_SCOPE_FORBIDDEN,
                    "tool scope is forbidden: " + ", ".join(forbidden_scopes),
                )
            )

        schema_issues = _schema_issues(tool.input_schema, request.arguments)
        if schema_issues:
            issues.extend(schema_issues)
            return _decision(request, tool=tool, issues=issues)

        injection_issues = _prompt_injection_issues(request.arguments)
        if injection_issues:
            issues.extend(injection_issues)
            return _decision(request, tool=tool, issues=issues)

        url_issues = _url_issues(
            request.arguments,
            tool=tool,
            allow_http_urls=self.allow_http_urls,
        )
        if url_issues:
            issues.extend(url_issues)
            return _decision(request, tool=tool, issues=issues)

        return _decision(
            request,
            tool=tool,
            issues=(),
            safe_arguments=request.arguments,
        )


def _find_bound_tool(request: AgentToolInvocationRequest) -> ToolDeclaration | None:
    for tool in request.prompt_binding.tools:
        if tool.tool_name == request.tool_name and tool.tool_version == request.tool_version:
            return tool
    return None


def _deny(request: AgentToolInvocationRequest, issue: AgentToolSecurityIssue) -> AgentToolAuthorizationDecision:
    return AgentToolAuthorizationDecision(
        request=request,
        status=AgentToolAuthorizationStatus.DENIED,
        issues=(issue,),
        safe_arguments={},
        tool_hash=None,
    )


def _decision(
    request: AgentToolInvocationRequest,
    *,
    tool: ToolDeclaration,
    issues: Sequence[AgentToolSecurityIssue],
    safe_arguments: Mapping[str, Any] | None = None,
) -> AgentToolAuthorizationDecision:
    issue_tuple = tuple(issues)
    return AgentToolAuthorizationDecision(
        request=request,
        status=AgentToolAuthorizationStatus.DENIED if issue_tuple else AgentToolAuthorizationStatus.ALLOWED,
        issues=issue_tuple,
        safe_arguments={} if issue_tuple else (safe_arguments or {}),
        tool_hash=tool.tool_hash,
    )


def _schema_issues(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> tuple[AgentToolSecurityIssue, ...]:
    messages = _validate_schema(schema, arguments, path="arguments")
    return tuple(
        AgentToolSecurityIssue(
            AgentToolSecurityIssueCode.INPUT_SCHEMA_VIOLATION,
            message,
            field_path=path,
        )
        for path, message in messages
    )


def _validate_schema(schema: Mapping[str, Any], value: Any, *, path: str) -> list[tuple[str, str]]:
    if not isinstance(schema, Mapping):
        return [(path, "schema must be an object")]

    expected = schema.get("type")
    if isinstance(expected, list):
        if any(_matches_type(value, item) for item in expected if isinstance(item, str)):
            return _validate_object_members(schema, value, path=path) if "object" in expected else []
        return [(path, f"expected one of types: {', '.join(str(item) for item in expected)}")]
    if isinstance(expected, str) and not _matches_type(value, expected):
        return [(path, f"expected type {expected}")]

    if expected == "object":
        return _validate_object_members(schema, value, path=path)
    if expected == "array":
        return _validate_array_items(schema, value, path=path)
    return []


def _validate_object_members(schema: Mapping[str, Any], value: Any, *, path: str) -> list[tuple[str, str]]:
    if not isinstance(value, Mapping):
        return [(path, "expected type object")]
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return [(path, "schema properties must be an object")]
    messages: list[tuple[str, str]] = []
    required = schema.get("required", ())
    if not isinstance(required, Sequence) or isinstance(required, str):
        return [(path, "schema required must be a sequence")]
    for field_name in required:
        if field_name not in value:
            messages.append((f"{path}.{field_name}", f"missing required property: {field_name}"))
    if schema.get("additionalProperties") is False:
        extras = sorted(str(field_name) for field_name in value if field_name not in properties)
        for field_name in extras:
            messages.append((f"{path}.{field_name}", f"additional property is not allowed: {field_name}"))
    for field_name, field_schema in properties.items():
        if field_name in value and isinstance(field_schema, Mapping):
            messages.extend(_validate_schema(field_schema, value[field_name], path=f"{path}.{field_name}"))
    return messages


def _validate_array_items(schema: Mapping[str, Any], value: Any, *, path: str) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        return [(path, "expected type array")]
    item_schema = schema.get("items")
    if not isinstance(item_schema, Mapping):
        return []
    messages: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        messages.extend(_validate_schema(item_schema, item, path=f"{path}[{index}]"))
    return messages


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, Mapping)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return type(value) is str
    if expected_type == "integer":
        return type(value) is int
    if expected_type == "number":
        return (type(value) is int or type(value) is float) and type(value) is not bool
    if expected_type == "boolean":
        return type(value) is bool
    if expected_type == "null":
        return value is None
    return True


def _prompt_injection_issues(arguments: Mapping[str, Any]) -> tuple[AgentToolSecurityIssue, ...]:
    issues: list[AgentToolSecurityIssue] = []
    for path, value in _iter_string_values(arguments):
        if _PROMPT_INJECTION_RE.search(value):
            issues.append(
                AgentToolSecurityIssue(
                    AgentToolSecurityIssueCode.PROMPT_INJECTION,
                    "tool argument contains external prompt/tool instructions",
                    field_path=path,
                )
            )
    return tuple(issues)


def _url_issues(
    arguments: Mapping[str, Any],
    *,
    tool: ToolDeclaration,
    allow_http_urls: bool,
) -> tuple[AgentToolSecurityIssue, ...]:
    url_fields = set(_URL_FIELD_NAMES)
    declared_fields = tool.metadata.get("url_argument_names")
    if declared_fields:
        url_fields.update(_split_csv(declared_fields))
    allowed_hosts = set(_split_csv(tool.metadata.get("allowed_url_hosts", "")))

    issues: list[AgentToolSecurityIssue] = []
    for path, value in _iter_string_values(arguments):
        field_name = _argument_field_name(path)
        if field_name not in url_fields:
            continue
        issue = _unsafe_url_issue(value, path=path, allowed_hosts=allowed_hosts, allow_http_urls=allow_http_urls)
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def _argument_field_name(path: str) -> str:
    return path.rsplit(".", maxsplit=1)[-1].split("[", maxsplit=1)[0].lower()


def _unsafe_url_issue(
    value: str,
    *,
    path: str,
    allowed_hosts: set[str],
    allow_http_urls: bool,
) -> AgentToolSecurityIssue | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return _unsafe_url(path, "URL scheme must be http or https")
    if parsed.scheme == "http" and not allow_http_urls:
        return _unsafe_url(path, "URL scheme must be https")
    if parsed.username or parsed.password:
        return _unsafe_url(path, "URL credentials are forbidden")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return _unsafe_url(path, "URL host is required")
    if host == "localhost" or host.endswith(_LOCAL_HOST_SUFFIXES):
        return _unsafe_url(path, "local hostnames are forbidden")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return _unsafe_url(path, "local or private IP addresses are forbidden")
    if allowed_hosts and host not in {item.lower().rstrip(".") for item in allowed_hosts}:
        return _unsafe_url(path, "URL host is not in the tool allowlist")
    return None


def _unsafe_url(path: str, message: str) -> AgentToolSecurityIssue:
    return AgentToolSecurityIssue(AgentToolSecurityIssueCode.UNSAFE_URL, message, field_path=path)


def _iter_string_values(value: Any, *, path: str = "arguments") -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.extend(_iter_string_values(item, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_iter_string_values(item, path=f"{path}[{index}]"))
    elif type(value) is str:
        found.append((path, value))
    return tuple(found)


def _split_csv(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise AgentToolSecurityError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _required_semver(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not re.fullmatch(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", value):
        raise AgentToolSecurityError(f"{field_name} must be a semantic version")
    return value


def _optional_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    value = _required_string("sha256", value)
    if not re.fullmatch(r"^sha256:[0-9a-f]{64}$", value):
        raise AgentToolSecurityError("sha256 must use sha256:<64 lowercase hex>")
    return value


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
        raise AgentToolSecurityError("value must be JSON serializable") from exc


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = _canonical_json(record).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}
