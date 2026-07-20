from __future__ import annotations

import asyncio
import json

from serenity_alpha_lab.application.config_profiles import ConfigProfileError
from serenity_alpha_lab.application.research_orchestrator import ResearchOrchestratorError
from serenity_alpha_lab.application.task_backend import (
    TaskAlreadyExists,
    TaskBackendCapabilityError,
    TaskNotFound,
)
from serenity_alpha_lab.application.tracing import TraceContext, current_trace_context, use_trace_context


def test_problem_detail_serializes_stable_application_problem_body() -> None:
    from serenity_alpha_lab.application.api_errors import (
        ApiErrorCode,
        ValidationProblem,
        problem_response_body,
    )

    problem = ValidationProblem(
        detail="symbol is required",
        instance="/api/v1/research",
        trace_id="trace-api-001",
        errors={"symbol": ["required"], "api_key": "sk-very-secret"},
    ).to_problem_detail()

    body = problem_response_body(problem)

    assert body == {
        "type": "https://serenity-alpha-lab/errors/validation_error",
        "title": "Validation Error",
        "status": 422,
        "detail": "symbol is required",
        "instance": "/api/v1/research",
        "code": ApiErrorCode.VALIDATION_ERROR.value,
        "trace_id": "trace-api-001",
        "errors": {"symbol": ["required"], "api_key": "[REDACTED]"},
    }


def test_exception_mapper_assigns_stable_codes_for_application_errors() -> None:
    from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception

    cases = [
        (TaskNotFound("Task not found: task-001"), 404, ApiErrorCode.NOT_FOUND),
        (TaskAlreadyExists("Task already exists: task-001"), 409, ApiErrorCode.CONFLICT),
        (ConfigProfileError("CI profile forbids real provider calls"), 422, ApiErrorCode.VALIDATION_ERROR),
        (ResearchOrchestratorError("run_id is required"), 422, ApiErrorCode.VALIDATION_ERROR),
        (ResearchOrchestratorError("DSA research orchestrator run failed"), 502, ApiErrorCode.PROVIDER_ERROR),
        (
            TaskBackendCapabilityError("Injected DSA queue does not support cancellation"),
            500,
            ApiErrorCode.INTERNAL_ERROR,
        ),
    ]

    with use_trace_context(TraceContext(trace_id="trace-api-002", run_id="run-002")):
        for exc, expected_status, expected_code in cases:
            problem = problem_from_exception(exc, instance="/api/v1/tasks/task-001")
            assert problem.status == expected_status
            assert problem.code == expected_code
            assert problem.trace_id == "trace-api-002"
            assert problem.instance == "/api/v1/tasks/task-001"


def test_internal_errors_and_freeform_details_are_redacted() -> None:
    from serenity_alpha_lab.application.api_errors import (
        ApiErrorCode,
        problem_from_exception,
        redact_problem_detail,
    )

    unsafe_detail = (
        "Traceback (most recent call last): File \"/Users/zq/private/app.py\", line 7 "
        "api_key=sk-live-secret token=abc123 prompt=private thesis body={'content': 'secret'}"
    )

    redacted = redact_problem_detail(unsafe_detail)
    problem = problem_from_exception(RuntimeError(unsafe_detail), trace_context=TraceContext(trace_id="trace-api-003"))
    body = problem.to_dict()

    assert "Traceback" not in redacted
    assert "/Users/zq" not in redacted
    assert "sk-live-secret" not in redacted
    assert "private thesis" not in redacted
    assert "abc123" not in redacted
    assert problem.status == 500
    assert problem.code == ApiErrorCode.INTERNAL_ERROR
    assert body["detail"] == "An unexpected error occurred."
    assert "Traceback" not in json.dumps(body)


def test_problem_details_middleware_returns_problem_json_and_trace_header() -> None:
    from serenity_alpha_lab.application.api_errors import ApiErrorCode, ProblemDetailsMiddleware

    sent_messages: list[dict] = []

    async def app(scope, receive, send):
        raise TaskNotFound("Task not found: task-404")

    middleware = ProblemDetailsMiddleware(app)
    scope = {
        "type": "http",
        "path": "/api/v1/tasks/task-404",
        "headers": [(b"x-trace-id", b"trace-api-004")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent_messages.append(message)

    asyncio.run(middleware(scope, receive, send))

    response_start, response_body = sent_messages
    headers = dict(response_start["headers"])
    body = json.loads(response_body["body"])

    assert response_start["status"] == 404
    assert headers[b"content-type"] == b"application/problem+json"
    assert headers[b"x-trace-id"] == b"trace-api-004"
    assert body["code"] == ApiErrorCode.NOT_FOUND.value
    assert body["trace_id"] == "trace-api-004"
    assert body["instance"] == "/api/v1/tasks/task-404"
    assert "task-404" in body["detail"]
    assert current_trace_context() is None
