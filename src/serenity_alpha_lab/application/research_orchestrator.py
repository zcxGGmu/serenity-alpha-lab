from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


ProgressCallback = Callable[[dict[str, Any]], None]


class ResearchOrchestratorError(ValueError):
    """Raised when research orchestration requests or adapters fail."""


class ResearchMode(StrEnum):
    DASHBOARD = "dashboard"
    CHAT = "chat"


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    run_id: str
    query: str
    context: Mapping[str, Any] = field(default_factory=dict)
    mode: ResearchMode = ResearchMode.DASHBOARD
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        run_id = self.run_id.strip()
        query = self.query.strip()
        if not run_id:
            raise ResearchOrchestratorError("run_id is required")
        if not query:
            raise ResearchOrchestratorError("query is required")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "query", query)
        object.__setattr__(self, "mode", _coerce_research_mode(self.mode))
        object.__setattr__(self, "context", _copy_mapping(self.context))


@dataclass(frozen=True, slots=True)
class ResearchChatRequest:
    run_id: str
    message: str
    session_id: str
    context: Mapping[str, Any] = field(default_factory=dict)
    skills: tuple[str, ...] | list[str] | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        run_id = self.run_id.strip()
        message = self.message.strip()
        session_id = self.session_id.strip()
        if not run_id:
            raise ResearchOrchestratorError("run_id is required")
        if not message:
            raise ResearchOrchestratorError("message is required")
        if not session_id:
            raise ResearchOrchestratorError("session_id is required")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "context", _copy_mapping(self.context))
        object.__setattr__(self, "skills", None if self.skills is None else tuple(self.skills))


@dataclass(frozen=True, slots=True)
class ResearchResult:
    run_id: str
    success: bool = False
    content: str = ""
    dashboard: Mapping[str, Any] | None = None
    tool_calls_log: list[dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    total_tokens: int = 0
    provider: str = ""
    model: str = ""
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        run_id = self.run_id.strip()
        if not run_id:
            raise ResearchOrchestratorError("run_id is required")
        object.__setattr__(self, "run_id", run_id)
        if self.dashboard is not None:
            object.__setattr__(self, "dashboard", _copy_mapping(self.dashboard))
        object.__setattr__(
            self,
            "tool_calls_log",
            [
                dict(item) if isinstance(item, Mapping) else {"value": item}
                for item in list(self.tool_calls_log)
            ],
        )
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@runtime_checkable
class ResearchOrchestrator(Protocol):
    """Application port for dashboard and chat research orchestration."""

    def run(self, request: ResearchRequest) -> ResearchResult:
        """Run a dashboard-oriented research request."""

    def chat(
        self,
        request: ResearchChatRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> ResearchResult:
        """Run a chat-oriented research request."""


def _coerce_research_mode(value: ResearchMode | str) -> ResearchMode:
    try:
        return value if isinstance(value, ResearchMode) else ResearchMode(value)
    except ValueError as exc:
        raise ResearchOrchestratorError(f"Unknown research mode: {value}") from exc


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, item in dict(value).items():
        copied[str(key)] = _copy_value(item)
    return copied


def _copy_value(value: Any) -> Any:
    try:
        return deepcopy(value)
    except Exception:
        return value
