from __future__ import annotations

import contextvars
import json
import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Iterator


_trace_context: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar(
    "serenity_trace_context",
    default=None,
)

_SENSITIVE_KEYS = {
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "body",
    "content",
    "credential",
    "credentials",
    "messages",
    "password",
    "prompt",
    "private_body",
    "secret",
    "token",
    "x-api-key",
}

_LOG_RECORD_BUILTINS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
)


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    run_id: str | None = None
    stage_id: str | None = None
    user_id: str | None = None


def generate_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex}"


def current_trace_context() -> TraceContext | None:
    return _trace_context.get()


@contextmanager
def use_trace_context(context: TraceContext) -> Iterator[TraceContext]:
    token = _trace_context.set(context)
    try:
        yield context
    finally:
        _trace_context.reset(token)


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    return value


class TraceContextFilter(logging.Filter):
    """Attach active trace context fields to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = current_trace_context()
        record.trace_id = getattr(record, "trace_id", None) or (context.trace_id if context else None)
        record.run_id = getattr(record, "run_id", None) or (context.run_id if context else None)
        record.stage_id = getattr(record, "stage_id", None) or (context.stage_id if context else None)
        record.user_id = getattr(record, "user_id", None) or (context.user_id if context else None)
        return True


class StructuredLogFormatter(logging.Formatter):
    """Format log records as redacted JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "run_id": getattr(record, "run_id", None),
            "stage_id": getattr(record, "stage_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        for key, value in record.__dict__.items():
            if key in _LOG_RECORD_BUILTINS or key in payload:
                continue
            payload[key] = value
        return json.dumps(redact_sensitive_data(payload), sort_keys=True, default=_json_default)


class TraceContextMiddleware:
    """Framework-neutral ASGI middleware for trace header propagation."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        headers = _headers_to_dict(scope.get("headers", []))
        context = TraceContext(
            trace_id=headers.get("x-trace-id") or generate_trace_id(),
            run_id=headers.get("x-run-id"),
            stage_id=headers.get("x-stage-id"),
            user_id=headers.get("x-user-id"),
        )

        async def send_with_trace(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                response_headers = list(message.get("headers", []))
                if b"x-trace-id" not in {name.lower() for name, _ in response_headers}:
                    response_headers.append((b"x-trace-id", context.trace_id.encode("utf-8")))
                message = {**message, "headers": response_headers}
            await send(message)

        with use_trace_context(context):
            await self._app(scope, receive, send_with_trace)


def _headers_to_dict(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    return {
        key.decode("latin1").lower(): value.decode("latin1")
        for key, value in headers
    }


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return normalized in _SENSITIVE_KEYS or any(part in normalized for part in ("secret", "token", "password"))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
