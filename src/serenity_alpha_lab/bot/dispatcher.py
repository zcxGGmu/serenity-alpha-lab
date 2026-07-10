from __future__ import annotations

from collections.abc import Callable, Mapping
import re
import time
from typing import Any

from .commands import (
    run_analysis_command,
    run_evidence_gaps_command,
    run_status_command,
)
from .contracts import BotMessage, BotResponse


_COMMAND_ALIASES = {
    "status": "status",
    "s": "status",
    "状态": "status",
    "analyze": "analyze",
    "analysis": "analyze",
    "a": "analyze",
    "分析": "analyze",
    "evidence-gaps": "evidence-gaps",
    "evidence_gaps": "evidence-gaps",
    "gaps": "evidence-gaps",
    "证据缺口": "evidence-gaps",
}
_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,15}$")


class ResearchBotDispatcher:
    def __init__(
        self,
        *,
        analyze: Callable[[str], Any],
        enabled: bool = False,
        max_requests: int = 10,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._analyze = analyze
        self._enabled = enabled
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        self._clock = clock
        self._request_times: dict[str, list[float]] = {}

    def parse_command(self, content: str) -> tuple[str | None, list[str]]:
        text = (content or "").strip()
        if not text:
            return None, []
        if text.startswith("/"):
            text = text[1:].strip()
        parts = text.split()
        if not parts:
            return None, []
        raw_command = parts[0]
        command = _COMMAND_ALIASES.get(raw_command.lower())
        if command is None:
            command = _COMMAND_ALIASES.get(raw_command)
        return command, parts[1:]

    def dispatch(self, message: BotMessage) -> BotResponse:
        if not self._enabled:
            return BotResponse(
                status="disabled",
                text="Serenity research Bot commands are disabled by default.",
                diagnostics={"reason": "research_bot_default_off"},
            )

        command, args = self.parse_command(message.content)
        if command is None:
            return BotResponse(
                status="error",
                text=(
                    "Unknown command. Help: /status, /analyze <symbol>, "
                    "/evidence-gaps <symbol>."
                ),
                diagnostics={"reason": "unknown_command"},
            )

        if not self._rate_limit_allows(message.user_id):
            return BotResponse(
                status="rate_limited",
                text="Research command rate limit exceeded.",
                diagnostics={
                    "reason": "rate_limit_exceeded",
                    "window_seconds": self._window_seconds,
                },
            )

        if command == "status":
            if args:
                return self._argument_error()
            return run_status_command()

        symbol = self._validated_symbol(args)
        if symbol is None:
            return self._argument_error()

        try:
            analysis = _analysis_mapping(self._analyze(symbol))
            if command == "analyze":
                return run_analysis_command(
                    analysis,
                    requested_by=message.user_id,
                )
            return run_evidence_gaps_command(
                analysis,
                requested_by=message.user_id,
            )
        except Exception as exc:
            return BotResponse(
                status="failed_open",
                text=(
                    "The local research command failed open without exposing "
                    "internal details."
                ),
                diagnostics={"error_type": type(exc).__name__},
            )

    def _rate_limit_allows(self, user_id: str) -> bool:
        now = self._clock()
        window_start = now - self._window_seconds
        active = [
            timestamp
            for timestamp in self._request_times.get(user_id, [])
            if timestamp > window_start
        ]
        if len(active) >= self._max_requests:
            self._request_times[user_id] = active
            return False
        active.append(now)
        self._request_times[user_id] = active
        return True

    @staticmethod
    def _validated_symbol(args: list[str]) -> str | None:
        if len(args) != 1:
            return None
        symbol = args[0].strip()
        if not _SYMBOL_PATTERN.fullmatch(symbol):
            return None
        return symbol.upper()

    @staticmethod
    def _argument_error() -> BotResponse:
        return BotResponse(
            status="error",
            text=(
                "Invalid arguments. Help: /analyze <symbol> or "
                "/evidence-gaps <symbol>."
            ),
            diagnostics={"reason": "invalid_arguments"},
        )


def _analysis_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        if isinstance(payload, Mapping):
            return dict(payload)
    raise TypeError("analysis service must return a mapping or to_dict() object")
