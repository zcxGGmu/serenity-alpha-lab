from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from serenity_alpha_lab.application.config_profiles import (
    ConfigProfileError,
    RuntimeProfile,
    RuntimeSettings,
    load_runtime_settings,
    profile_policy,
)
from serenity_alpha_lab.application.screening_provider import (
    SCREENING_PROVIDER_CONTRACT_VERSION,
    SCREENING_RAW_RESULT_SCHEMA_NAME,
    SCREENING_RAW_RESULT_SCHEMA_VERSION,
    ScreeningProviderError,
    ScreeningProviderErrorCategory,
    ScreeningProviderStatus,
    ScreeningRequest,
    ScreeningResult,
    ScreeningStrategy,
)
from serenity_alpha_lab.application.tracing import current_trace_context


ALPHASIFT_PROVIDER_ID = "alphasift"

ClockFn = Callable[[], datetime]


class AlphaSiftScreeningAdapter:
    """ScreeningProvider adapter over AlphaSift's stable DSA adapter shape.

    AlphaSift is imported lazily and only inside this integration boundary.
    Tests and CI should pass an injected client with the same DSA-adapter
    methods, keeping real provider/LLM paths out of the default test surface.
    """

    provider_id = ALPHASIFT_PROVIDER_ID

    def __init__(
        self,
        *,
        client: Any | None = None,
        settings: RuntimeSettings | None = None,
        clock: ClockFn | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or load_runtime_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._provider_version: str | None = None
        self._alphasift_contract_version: str | None = None

    def status(self) -> ScreeningProviderStatus:
        client = self._client_instance()
        try:
            raw = client.get_status(context=self._base_context())
        except ScreeningProviderError:
            raise
        except ConfigProfileError:
            raise
        except Exception as exc:
            raise _error_from_exception(exc, operation="status") from exc
        if not isinstance(raw, Mapping):
            raise _schema_drift("status", "AlphaSift status response must be a mapping")
        provider_version = _required_payload_string(raw, "version", operation="status")
        contract_version = str(raw.get("contract_version") or "")
        self._provider_version = provider_version
        self._alphasift_contract_version = contract_version or None
        return ScreeningProviderStatus(
            provider_id=self.provider_id,
            available=bool(raw.get("available")),
            provider_version=provider_version,
            contract_version=SCREENING_PROVIDER_CONTRACT_VERSION,
            strategy_count=_payload_non_negative_int(raw, "strategy_count", operation="status"),
            checked_at=_ensure_utc(self._clock()),
            message=_optional_payload_string(raw, "error"),
            trace_id=_trace_field("trace_id"),
        )

    def list_strategies(self) -> tuple[ScreeningStrategy, ...]:
        client = self._client_instance()
        try:
            raw = client.list_strategies(context=self._base_context())
        except ScreeningProviderError:
            raise
        except ConfigProfileError:
            raise
        except Exception as exc:
            raise _error_from_exception(exc, operation="strategies") from exc
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise _schema_drift("strategies", "AlphaSift strategies response must be a sequence")
        return tuple(_strategy_from_payload(item) for item in raw)

    def screen(self, request: ScreeningRequest) -> ScreeningResult:
        if type(request) is not ScreeningRequest:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.INVALID_REQUEST,
                provider_id=self.provider_id,
                operation="screen",
                message="request must be a ScreeningRequest",
            )
        if request.use_llm_overlay:
            self._assert_llm_overlay_allowed()
        client = self._client_instance()
        requested_at = _ensure_utc(request.requested_at or self._clock())
        context = self._context_for_request(request)
        try:
            raw = client.screen(
                request.strategy_id,
                market=request.market,
                max_results=request.max_results,
                use_llm=request.use_llm_overlay,
                context=context,
            )
        except ScreeningProviderError:
            raise
        except ConfigProfileError:
            raise
        except Exception as exc:
            raise _error_from_exception(exc, operation="screen") from exc
        if not isinstance(raw, Mapping):
            raise _schema_drift("screen", "AlphaSift screen response must be a mapping")
        return self._result_from_payload(raw, request=request, requested_at=requested_at)

    def _client_instance(self) -> Any:
        if self._client is not None:
            return self._client
        self._assert_real_alphasift_allowed()
        self._client = importlib.import_module("alphasift.dsa_adapter")
        return self._client

    def _assert_real_alphasift_allowed(self) -> None:
        policy = profile_policy(self._settings)
        if self._settings.profile is RuntimeProfile.CI:
            raise ConfigProfileError("CI profile forbids real AlphaSift provider calls")
        if not policy.provider_calls_allowed:
            raise ConfigProfileError(f"{self._settings.profile.value} profile forbids real AlphaSift provider calls")

    def _assert_llm_overlay_allowed(self) -> None:
        policy = profile_policy(self._settings)
        if not policy.model_calls_allowed:
            raise ConfigProfileError(f"{self._settings.profile.value} profile forbids AlphaSift LLM overlay")

    def _base_context(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field in ("trace_id", "run_id", "stage_id"):
            value = _trace_field(field)
            if value is not None:
                payload[field] = value
        return payload

    def _context_for_request(self, request: ScreeningRequest) -> dict[str, Any]:
        payload = {
            "dataset_versions": dict(request.dataset_versions),
            "trace_id": _trace_field("trace_id"),
            "run_id": _trace_field("run_id"),
            "stage_id": _trace_field("stage_id"),
            "timeout_seconds": request.timeout_seconds,
        }
        if request.context:
            payload["request_context"] = dict(request.context)
        return payload

    def _result_from_payload(
        self,
        payload: Mapping[str, Any],
        *,
        request: ScreeningRequest,
        requested_at: datetime,
    ) -> ScreeningResult:
        candidates = payload.get("candidates", ())
        if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
            raise _schema_drift("screen", "AlphaSift screen candidates must be a sequence")
        normalized_candidates: list[Mapping[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise _schema_drift("screen", "AlphaSift candidate must be a mapping")
            normalized_candidates.append(candidate)
        received_at = _ensure_utc(self._clock())
        return ScreeningResult(
            provider_id=self.provider_id,
            provider_version=self._provider_version or _optional_payload_string(payload, "version") or "",
            strategy_id=_required_payload_string(payload, "strategy", operation="screen"),
            strategy_version=_required_payload_string(payload, "strategy_version", operation="screen"),
            market=_required_payload_string(payload, "market", operation="screen"),
            dataset_versions=request.dataset_versions,
            candidates=tuple(normalized_candidates),
            candidate_count=_payload_non_negative_int(
                payload,
                "candidate_count",
                operation="screen",
                default=len(normalized_candidates),
            ),
            snapshot_count=_payload_non_negative_int(payload, "snapshot_count", operation="screen"),
            after_filter_count=_payload_non_negative_int(payload, "after_filter_count", operation="screen"),
            provider_run_id=_required_payload_string(payload, "run_id", operation="screen"),
            requested_at=requested_at,
            received_at=received_at,
            contract_version=SCREENING_PROVIDER_CONTRACT_VERSION,
            schema_name=SCREENING_RAW_RESULT_SCHEMA_NAME,
            schema_version=SCREENING_RAW_RESULT_SCHEMA_VERSION,
            warnings=_payload_string_sequence(payload, "warnings", operation="screen"),
            source_errors=_payload_string_sequence(payload, "source_errors", operation="screen"),
            llm_overlay_enabled=bool(payload.get("llm_ranked", request.use_llm_overlay)),
            llm_coverage=_optional_payload_float(payload, "llm_coverage", operation="screen"),
            trace_id=_trace_field("trace_id"),
            platform_run_id=_trace_field("run_id"),
            stage_id=_trace_field("stage_id"),
        )


def _strategy_from_payload(payload: Any) -> ScreeningStrategy:
    if not isinstance(payload, Mapping):
        raise _schema_drift("strategies", "AlphaSift strategy item must be a mapping")
    try:
        return ScreeningStrategy(
            strategy_id=_required_payload_string(payload, "id", operation="strategies"),
            name=_required_payload_string(payload, "name", operation="strategies"),
            description=_required_payload_string(payload, "description", operation="strategies"),
            version=_required_payload_string(payload, "version", operation="strategies"),
            category=str(payload.get("category") or "uncategorized"),
            tags=_payload_string_sequence(payload, "tags", operation="strategies"),
            market_scope=_payload_string_sequence(payload, "market_scope", operation="strategies"),
        )
    except ScreeningProviderError:
        raise
    except Exception as exc:
        raise _schema_drift("strategies", str(exc) or type(exc).__name__) from exc


def _error_from_exception(exc: Exception, *, operation: str) -> ScreeningProviderError:
    return ScreeningProviderError(
        category=_classify_exception(exc),
        provider_id=ALPHASIFT_PROVIDER_ID,
        operation=operation,
        message=str(exc) or type(exc).__name__,
    )


def _classify_exception(exc: Exception) -> ScreeningProviderErrorCategory:
    if isinstance(exc, TimeoutError):
        return ScreeningProviderErrorCategory.TIMEOUT
    text = f"{type(exc).__name__} {exc}".lower()
    if any(token in text for token in ("timeout", "timed out", "deadline")):
        return ScreeningProviderErrorCategory.TIMEOUT
    if any(token in text for token in ("schema", "column", "keyerror", "field", "missing")):
        return ScreeningProviderErrorCategory.SCHEMA_DRIFT
    if any(token in text for token in ("empty", "no data", "invalid data")):
        return ScreeningProviderErrorCategory.DATA_INVALID
    if any(token in text for token in ("not found", "unknown", "unsupported", "invalid")):
        return ScreeningProviderErrorCategory.INVALID_REQUEST
    if any(token in text for token in ("unavailable", "connection", "503", "temporar")):
        return ScreeningProviderErrorCategory.UNAVAILABLE
    return ScreeningProviderErrorCategory.UNAVAILABLE


def _schema_drift(operation: str, message: str) -> ScreeningProviderError:
    return ScreeningProviderError(
        category=ScreeningProviderErrorCategory.SCHEMA_DRIFT,
        provider_id=ALPHASIFT_PROVIDER_ID,
        operation=operation,
        message=message,
    )


def _required_payload_string(payload: Mapping[str, Any], key: str, *, operation: str) -> str:
    value = payload.get(key)
    if type(value) is not str or not value.strip():
        raise _schema_drift(operation, f"AlphaSift response field {key} is required")
    return value.strip()


def _optional_payload_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if type(value) is not str:
        return str(value)
    return value.strip() or None


def _payload_non_negative_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    operation: str,
    default: int | None = None,
) -> int:
    value = payload.get(key, default)
    if type(value) is not int or value < 0:
        raise _schema_drift(operation, f"AlphaSift response field {key} must be a non-negative integer")
    return value


def _payload_string_sequence(payload: Mapping[str, Any], key: str, *, operation: str) -> tuple[str, ...]:
    value = payload.get(key, ())
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise _schema_drift(operation, f"AlphaSift response field {key} must be a sequence")
    return tuple(str(item) for item in value)


def _optional_payload_float(payload: Mapping[str, Any], key: str, *, operation: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise _schema_drift(operation, f"AlphaSift response field {key} must be numeric") from exc


def _trace_field(field_name: str) -> str | None:
    context = current_trace_context()
    if context is None:
        return None
    return getattr(context, field_name)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "ALPHASIFT_PROVIDER_ID",
    "AlphaSiftScreeningAdapter",
]
