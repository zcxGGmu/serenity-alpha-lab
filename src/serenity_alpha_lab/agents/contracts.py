from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ResearchToolContext:
    analysis: Mapping[str, Any]
    requested_by: str


@dataclass(frozen=True)
class ResearchToolParameter:
    name: str
    description: str
    kind: str = "string"
    required: bool = False


@dataclass(frozen=True)
class ResearchToolDefinition:
    name: str
    description: str
    parameters: tuple[ResearchToolParameter, ...] = ()
    research_only: bool = True


@dataclass(frozen=True)
class ResearchToolResult:
    tool: str
    status: str
    research_only: bool = True
    payload: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.payload)
        result.update(
            {
                "tool": self.tool,
                "status": self.status,
                "research_only": self.research_only,
                "diagnostics": dict(self.diagnostics),
            }
        )
        return result
