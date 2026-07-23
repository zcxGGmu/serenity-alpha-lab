from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping

from serenity_alpha_lab.application.config_profiles import ConfigProfileError
from serenity_alpha_lab.application.research_orchestrator import ResearchOrchestratorError
from serenity_alpha_lab.application.screening_provider import ScreeningProviderError
from serenity_alpha_lab.application.task_backend import (
    TaskAlreadyExists,
    TaskBackendCapabilityError,
    TaskNotFound,
)
from serenity_alpha_lab.application.tracing import (
    TraceContext,
    current_trace_context,
    generate_trace_id,
    redact_sensitive_data,
    use_trace_context,
)
from serenity_alpha_lab.domain.providers import ProviderError


PROBLEM_JSON_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE_URL = "https://serenity-alpha-lab/errors"


class ApiErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PROVIDER_ERROR = "provider_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True, slots=True)
class ProblemDetail:
    type: str
    title: str
    status: int
    detail: str
    code: ApiErrorCode
    instance: str | None = None
    trace_id: str | None = None
    errors: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _coerce_error_code(self.code))
        object.__setattr__(self, "detail", redact_problem_detail(self.detail))
        if self.errors is not None:
            object.__setattr__(self, "errors", redact_sensitive_data(dict(self.errors)))

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code.value,
        }
        if self.instance is not None:
            body["instance"] = self.instance
        if self.trace_id is not None:
            body["trace_id"] = self.trace_id
        if self.errors is not None:
            body["errors"] = self.errors
        return body


class ApiProblemError(Exception):
    default_code = ApiErrorCode.INTERNAL_ERROR
    default_status = 500
    default_title = "Internal Error"
    default_detail = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        *,
        title: str | None = None,
        status: int | None = None,
        code: ApiErrorCode | str | None = None,
        type: str | None = None,
        instance: str | None = None,
        trace_id: str | None = None,
        errors: Mapping[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.default_detail
        self.title = title or self.default_title
        self.status = status or self.default_status
        self.code = _coerce_error_code(code or self.default_code)
        self.type = type or problem_type_uri(self.code)
        self.instance = instance
        self.trace_id = trace_id
        self.errors = dict(errors) if errors is not None else None
        super().__init__(self.detail)

    def to_problem_detail(
        self,
        *,
        trace_context: TraceContext | None = None,
        instance: str | None = None,
    ) -> ProblemDetail:
        return ProblemDetail(
            type=self.type,
            title=self.title,
            status=self.status,
            detail=self.detail,
            instance=instance or self.instance,
            code=self.code,
            trace_id=self.trace_id or _trace_id_from_context(trace_context),
            errors=self.errors,
        )


class ValidationProblem(ApiProblemError):
    default_code = ApiErrorCode.VALIDATION_ERROR
    default_status = 422
    default_title = "Validation Error"
    default_detail = "Request validation failed."


class NotFoundProblem(ApiProblemError):
    default_code = ApiErrorCode.NOT_FOUND
    default_status = 404
    default_title = "Not Found"
    default_detail = "The requested resource was not found."


class ConflictProblem(ApiProblemError):
    default_code = ApiErrorCode.CONFLICT
    default_status = 409
    default_title = "Conflict"
    default_detail = "The request conflicts with the current resource state."


class ProviderProblem(ApiProblemError):
    default_code = ApiErrorCode.PROVIDER_ERROR
    default_status = 502
    default_title = "Provider Error"
    default_detail = "An upstream provider failed."


class InternalProblem(ApiProblemError):
    default_code = ApiErrorCode.INTERNAL_ERROR
    default_status = 500
    default_title = "Internal Error"
    default_detail = "An unexpected error occurred."


class ProblemDetailsMiddleware:
    """Framework-neutral ASGI middleware that emits application/problem+json."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        active_context = current_trace_context()
        context = active_context or _trace_context_from_scope(scope)
        response_started = False

        async def send_tracking_start(message: dict[str, Any]) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            if active_context is not None:
                await self._app(scope, receive, send_tracking_start)
            else:
                with use_trace_context(context):
                    await self._app(scope, receive, send_tracking_start)
        except Exception as exc:
            if response_started:
                raise
            problem = problem_from_exception(exc, trace_context=context, instance=_instance_from_scope(scope))
            body = json.dumps(problem_response_body(problem), sort_keys=True).encode("utf-8")
            headers = [
                (b"content-type", PROBLEM_JSON_CONTENT_TYPE.encode("ascii")),
                (b"x-trace-id", (problem.trace_id or context.trace_id).encode("utf-8")),
            ]
            await send({"type": "http.response.start", "status": problem.status, "headers": headers})
            await send({"type": "http.response.body", "body": body})


def problem_type_uri(code: ApiErrorCode | str) -> str:
    return f"{PROBLEM_TYPE_BASE_URL}/{_coerce_error_code(code).value}"


def problem_response_body(problem: ProblemDetail | ApiProblemError) -> dict[str, Any]:
    if isinstance(problem, ApiProblemError):
        problem = problem.to_problem_detail()
    return problem.to_dict()


def problem_from_exception(
    exc: Exception,
    *,
    trace_context: TraceContext | None = None,
    instance: str | None = None,
) -> ProblemDetail:
    if isinstance(exc, ApiProblemError):
        return exc.to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, TaskNotFound):
        return NotFoundProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, TaskAlreadyExists):
        return ConflictProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, ConfigProfileError):
        return ValidationProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, ResearchOrchestratorError):
        if _is_research_validation_error(str(exc)):
            return ValidationProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
        return ProviderProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, ScreeningProviderError):
        return ProviderProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, ProviderError):
        return ProviderProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, ValueError):
        return ValidationProblem(str(exc)).to_problem_detail(trace_context=trace_context, instance=instance)
    if isinstance(exc, TaskBackendCapabilityError):
        return InternalProblem().to_problem_detail(trace_context=trace_context, instance=instance)
    return InternalProblem().to_problem_detail(trace_context=trace_context, instance=instance)


def redact_problem_detail(detail: Any) -> str:
    text = "" if detail is None else str(detail)
    if _looks_like_stack_trace(text):
        return "Internal error detail redacted."

    text = _POSIX_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _WINDOWS_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _BEARER_RE.sub(r"\1[REDACTED]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(_redact_secret_assignment, text)
    text = _API_KEY_VALUE_RE.sub("[REDACTED]", text)
    text = _PRIVATE_PAYLOAD_RE.sub(r"\1=[REDACTED]", text)
    return text


def _coerce_error_code(value: ApiErrorCode | str) -> ApiErrorCode:
    return value if isinstance(value, ApiErrorCode) else ApiErrorCode(value)


def _trace_id_from_context(trace_context: TraceContext | None) -> str | None:
    context = trace_context or current_trace_context()
    return context.trace_id if context is not None else None


def _trace_context_from_scope(scope: Mapping[str, Any]) -> TraceContext:
    headers = _headers_to_dict(scope.get("headers", []))
    return TraceContext(
        trace_id=headers.get("x-trace-id") or generate_trace_id(),
        run_id=headers.get("x-run-id"),
        stage_id=headers.get("x-stage-id"),
        user_id=headers.get("x-user-id"),
    )


def _headers_to_dict(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    return {
        key.decode("latin1").lower(): value.decode("latin1")
        for key, value in headers
    }


def _instance_from_scope(scope: Mapping[str, Any]) -> str | None:
    path = scope.get("path")
    return str(path) if path else None


def _looks_like_stack_trace(text: str) -> bool:
    return "Traceback (most recent call last):" in text or bool(_PYTHON_FILE_TRACE_RE.search(text))


def _is_research_validation_error(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized.endswith(" is required") or normalized.startswith("unknown research mode:")


_POSIX_PATH_RE = re.compile(r"(?<![\w])/(?:Users|home|tmp|var|private|opt|etc|Volumes)/[^\s,'\")]+")
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\(?:Users|Temp|Windows|Program Files)[^\s,'\")]+")
_PYTHON_FILE_TRACE_RE = re.compile(r"File \"[^\"]+\", line \d+")
_API_KEY_VALUE_RE = re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{8,}\b")
_BEARER_RE = re.compile(r"(?i)\b(authorization\s*[:=]\s*bearer\s+)[^\s,;]+")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<prefix>['\"]?\b"
    r"(?:api[-_]?key|(?:access|refresh)[-_]?token|client[-_]?secret|token|secret|password)"
    r"\b['\"]?\s*[:=]\s*)"
    r"(?P<quote>['\"]?)(?P<secret>.*?)(?P=quote)(?=[\s,;}]|$)"
)
_PRIVATE_PAYLOAD_RE = re.compile(
    r"(?i)\b(prompt|body|content|messages|private[-_]?body)\s*[:=]\s*.+?(?=\s+\w[\w-]*\s*[:=]|$)"
)


def _redact_secret_assignment(match: re.Match[str]) -> str:
    quote = match.group("quote") or ""
    return f"{match.group('prefix')}{quote}[REDACTED]{quote}"


__all__ = [
    "ApiErrorCode",
    "ApiProblemError",
    "ConflictProblem",
    "InternalProblem",
    "NotFoundProblem",
    "PROBLEM_JSON_CONTENT_TYPE",
    "PROBLEM_TYPE_BASE_URL",
    "ProblemDetail",
    "ProblemDetailsMiddleware",
    "ProviderProblem",
    "ValidationProblem",
    "problem_from_exception",
    "problem_response_body",
    "problem_type_uri",
    "redact_problem_detail",
]
