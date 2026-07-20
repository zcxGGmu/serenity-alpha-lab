from __future__ import annotations

import asyncio
import json
import logging
from io import StringIO

from serenity_alpha_lab.application.tracing import (
    StructuredLogFormatter,
    TraceContext,
    TraceContextFilter,
    TraceContextMiddleware,
    current_trace_context,
    redact_sensitive_data,
    use_trace_context,
)


def test_trace_context_propagates_and_resets() -> None:
    assert current_trace_context() is None

    context = TraceContext(
        trace_id="trace-001",
        run_id="run-001",
        stage_id="stage-collect",
        user_id="user-001",
    )
    with use_trace_context(context):
        assert current_trace_context() == context

    assert current_trace_context() is None


def test_structured_log_formatter_includes_trace_fields_and_redacts_sensitive_values() -> None:
    stream = StringIO()
    logger = logging.getLogger("serenity-test-structured-log")
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler(stream)
    handler.addFilter(TraceContextFilter())
    handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(handler)

    with use_trace_context(TraceContext(trace_id="trace-002", run_id="run-002", stage_id="stage-report")):
        logger.info(
            "provider call",
            extra={
                "event": "provider.request",
                "dataset_version": "dataset-20260720",
                "api_key": "sk-secret",
                "prompt": "very private prompt body",
            },
        )

    payload = json.loads(stream.getvalue())

    assert payload["trace_id"] == "trace-002"
    assert payload["run_id"] == "run-002"
    assert payload["stage_id"] == "stage-report"
    assert payload["event"] == "provider.request"
    assert payload["dataset_version"] == "dataset-20260720"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["prompt"] == "[REDACTED]"
    assert "sk-secret" not in stream.getvalue()
    assert "very private prompt body" not in stream.getvalue()


def test_redactor_handles_nested_sensitive_data() -> None:
    redacted = redact_sensitive_data(
        {
            "headers": {"authorization": "Bearer token", "x-api-key": "secret"},
            "messages": [{"role": "user", "content": "private prompt"}],
            "safe": "kept",
        }
    )

    assert redacted["headers"]["authorization"] == "[REDACTED]"
    assert redacted["headers"]["x-api-key"] == "[REDACTED]"
    assert redacted["messages"] == "[REDACTED]"
    assert redacted["safe"] == "kept"


def test_trace_middleware_reads_headers_adds_response_trace_and_resets_context() -> None:
    seen_contexts: list[TraceContext | None] = []
    sent_messages: list[dict] = []

    async def app(scope, receive, send):
        seen_contexts.append(current_trace_context())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = TraceContextMiddleware(app)
    scope = {
        "type": "http",
        "headers": [
            (b"x-trace-id", b"trace-003"),
            (b"x-run-id", b"run-003"),
            (b"x-stage-id", b"stage-render"),
            (b"x-user-id", b"user-003"),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent_messages.append(message)

    asyncio.run(middleware(scope, receive, send))

    assert seen_contexts == [
        TraceContext(trace_id="trace-003", run_id="run-003", stage_id="stage-render", user_id="user-003")
    ]
    assert (b"x-trace-id", b"trace-003") in sent_messages[0]["headers"]
    assert current_trace_context() is None
