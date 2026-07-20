from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    """Clock port used by deterministic domain logic."""

    def utc_now_iso(self) -> str:
        """Return the current UTC timestamp as an ISO-8601 string."""
