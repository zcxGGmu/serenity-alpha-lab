from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence, Set
from typing import Any, Callable

from .contracts import (
    ResearchToolContext,
    ResearchToolDefinition,
    ResearchToolResult,
)
from .tools import (
    EVIDENCE_GAPS_TOOL_NAME,
    SUMMARY_TOOL_NAME,
    serenity_evidence_gaps,
    serenity_research_summary,
)


ResearchToolHandler = Callable[[ResearchToolContext], ResearchToolResult]

FORBIDDEN_OUTPUT_FIELDS = frozenset(
    {
        "operation_advice",
        "target_price",
        "position_sizing",
        "stop_loss",
        "take_profit",
        "sniper_points",
        "broker",
        "broker_account",
        "broker_action",
        "broker_id",
        "broker_name",
        "broker_order",
        "broker_request",
        "broker_response",
        "order",
        "orders",
        "order_action",
        "order_id",
        "order_price",
        "order_quantity",
        "order_request",
        "order_response",
        "order_side",
        "order_status",
        "order_type",
        "place_order",
        "cancel_order",
        "submit_order",
        "execute_order",
    }
)

_DEFINITIONS = {
    SUMMARY_TOOL_NAME: ResearchToolDefinition(
        name=SUMMARY_TOOL_NAME,
        description=(
            "Summarize caller-provided Serenity readiness, source coverage, "
            "report gate, research signals, and evidence identifiers."
        ),
    ),
    EVIDENCE_GAPS_TOOL_NAME: ResearchToolDefinition(
        name=EVIDENCE_GAPS_TOOL_NAME,
        description=(
            "Normalize caller-provided evidence, primary-source, and risk "
            "coverage gaps into deterministic research-only output."
        ),
    ),
}

_HANDLERS: dict[str, ResearchToolHandler] = {
    SUMMARY_TOOL_NAME: serenity_research_summary,
    EVIDENCE_GAPS_TOOL_NAME: serenity_evidence_gaps,
}


class ResearchToolRegistry:
    def __init__(
        self,
        *,
        enabled: bool,
        allowlist: Iterable[str],
        definitions: Iterable[ResearchToolDefinition],
        handlers: Mapping[str, ResearchToolHandler],
    ) -> None:
        self._enabled = enabled
        self._allowlist = frozenset(allowlist)
        self._definitions = {
            definition.name: definition
            for definition in definitions
        }
        self._handlers = dict(handlers)

    def list_names(self) -> list[str]:
        if not self._enabled:
            return []
        return sorted(
            name
            for name in self._allowlist
            if name in self._definitions and name in self._handlers
        )

    def list_definitions(self) -> list[ResearchToolDefinition]:
        return [
            self._definitions[name]
            for name in self.list_names()
        ]

    def execute(
        self,
        name: str,
        *,
        context: ResearchToolContext | None,
    ) -> ResearchToolResult:
        if name not in self.list_names():
            return _blocked_result(name, reason="tool_not_available")
        if context is None:
            return _blocked_result(name, reason="analysis_context_required")

        forbidden_input = _find_forbidden_fields(context.analysis)
        if forbidden_input:
            return _forbidden_result(name, forbidden_input)

        handler = self._handlers[name]
        try:
            result = handler(context)
            if not isinstance(result, ResearchToolResult):
                raise TypeError("research tool handlers must return ResearchToolResult")

            raw_output = result.to_dict()
            forbidden_output = _find_forbidden_fields(raw_output)
            if forbidden_output:
                return _forbidden_result(name, forbidden_output)

            json_safe_output = _to_json_safe(raw_output)
            if not isinstance(json_safe_output, dict):
                raise TypeError("research tool output must be a mapping")
            diagnostics = json_safe_output.pop("diagnostics", {})
            tool = json_safe_output.pop("tool")
            status = json_safe_output.pop("status")
            research_only = json_safe_output.pop("research_only")
            if not isinstance(diagnostics, Mapping):
                raise TypeError("research tool diagnostics must be a mapping")
            return ResearchToolResult(
                tool=str(tool),
                status=str(status),
                research_only=bool(research_only),
                payload=json_safe_output,
                diagnostics=dict(diagnostics),
            )
        except Exception as exc:
            return _failed_open_result(name, error_type=type(exc).__name__)


def build_research_tool_registry(
    *,
    enabled: bool = False,
    allowlist: Iterable[str] | None = None,
    handlers: Mapping[str, ResearchToolHandler] | None = None,
) -> ResearchToolRegistry:
    registered_handlers = dict(_HANDLERS)
    if handlers is not None:
        for name, handler in handlers.items():
            if name in _DEFINITIONS:
                registered_handlers[name] = handler

    return ResearchToolRegistry(
        enabled=enabled,
        allowlist=allowlist or (),
        definitions=_DEFINITIONS.values(),
        handlers=registered_handlers,
    )


def _blocked_result(tool: str, *, reason: str) -> ResearchToolResult:
    return ResearchToolResult(
        tool=tool,
        status="blocked",
        diagnostics={"reason": reason},
    )


def _forbidden_result(tool: str, fields: Sequence[str]) -> ResearchToolResult:
    return ResearchToolResult(
        tool=tool,
        status="blocked",
        diagnostics={
            "reason": "forbidden_output_field",
            "field": fields[0],
        },
    )


def _failed_open_result(tool: str, *, error_type: str) -> ResearchToolResult:
    return ResearchToolResult(
        tool=tool,
        status="failed_open",
        diagnostics={"error_type": error_type},
    )


def _find_forbidden_fields(value: Any) -> list[str]:
    found: set[str] = set()
    visited: set[int] = set()

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            object_id = id(item)
            if object_id in visited:
                return
            visited.add(object_id)
            for key, nested_value in item.items():
                if isinstance(key, str):
                    normalized_key = _normalize_key(key)
                    if normalized_key in FORBIDDEN_OUTPUT_FIELDS:
                        found.add(normalized_key)
                visit(nested_value)
            return

        if isinstance(item, (str, bytes, bytearray)):
            return

        if isinstance(item, (Sequence, Set)):
            object_id = id(item)
            if object_id in visited:
                return
            visited.add(object_id)
            for nested_value in item:
                visit(nested_value)

    visit(value)
    return sorted(found)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return {
            key: _to_json_safe(value[key])
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        safe_items = [_to_json_safe(item) for item in value]
        return sorted(
            safe_items,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")
