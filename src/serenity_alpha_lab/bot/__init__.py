"""Platform-neutral, default-off research Bot contracts and dispatcher."""

from .contracts import BotMessage, BotResponse
from .dispatcher import ResearchBotDispatcher

__all__ = [
    "BotMessage",
    "BotResponse",
    "ResearchBotDispatcher",
]
