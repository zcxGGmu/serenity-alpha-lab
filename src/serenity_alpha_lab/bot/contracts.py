from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BotMessage:
    user_id: str
    content: str
    message_id: str = ""


@dataclass(frozen=True)
class BotResponse:
    status: str
    text: str
    evidence_ids: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "text": self.text,
            "evidence_ids": list(self.evidence_ids),
            "diagnostics": dict(self.diagnostics),
            "research_only": self.research_only,
        }
