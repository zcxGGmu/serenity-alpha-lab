from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.integrations.qlib.dataset_converter import QlibDatasetConversionArtifacts
from serenity_alpha_lab.integrations.qlib.runtime_policy import QlibRuntimeIsolationPolicy, default_qlib_runtime_policy
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec


QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME = "integration.qlib.quant_engine_step"
QLIB_QUANT_ENGINE_STEP_SCHEMA_VERSION = "1.0.0"
QLIB_QUANT_ENGINE_STEP_CONTENT_TYPE = "application/vnd.serenity.integration.qlib.quant-engine-step+json"

QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME = "integration.qlib.quant_engine_run_report"
QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_VERSION = "1.0.0"
QLIB_QUANT_ENGINE_RUN_REPORT_CONTENT_TYPE = (
    "application/vnd.serenity.integration.qlib.quant-engine-run-report+json"
)

QLIB_QUANT_ENGINE_ADAPTER_SCOPE = "qlib_quant_engine_adapter"
QLIB_QUANT_ENGINE_ADAPTER_VERSION = "qlib_quant_engine_adapter@1.0.0"

_FORBIDDEN_CONFIG_KEYS = frozenset({"module_path", "module", "class", "class_name", "import_path"})


class QlibQuantEngineError(ValueError):
    """Raised when Qlib Adapter input or output violates the platform boundary."""


class QlibQuantEngineTemplate(StrEnum):
    LIGHTGBM_DAILY_REBALANCE = "lightgbm_daily_rebalance@1.0.0"
    LINEAR_FACTOR_EVALUATION = "linear_factor_evaluation@1.0.0"


class QlibQuantEngineOperation(StrEnum):
    TRAIN = "train"
    PREDICT = "predict"
    BACKTEST = "backtest"
    EVALUATE_FACTOR = "evaluate_factor"


class QlibQuantEngineFacade(Protocol):
    def train(self, config: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def predict(self, config: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def backtest(self, config: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def evaluate_factor(self, config: Mapping[str, Any]) -> Mapping[str, Any]: ...


class LazyQlibQuantEngineFacade:
    """Lazy Qlib boundary for the future dedicated Quant Worker runtime.

    The facade intentionally imports Qlib only from method bodies. A concrete
    worker runner must be injected before real execution so API/domain/import
    paths never gain Qlib global state by accident.
    """

    def train(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._not_wired("train", config)

    def predict(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._not_wired("predict", config)

    def backtest(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._not_wired("backtest", config)

    def evaluate_factor(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._not_wired("evaluate_factor", config)

    @staticmethod
    def _not_wired(operation: str, config: Mapping[str, Any]) -> Mapping[str, Any]:
        importlib.import_module("qlib")
        raise QlibQuantEngineError(
            f"Qlib {operation} execution requires an injected dedicated Quant Worker runner"
        )


@dataclass(frozen=True, slots=True)
class QlibQuantEngineConfig:
    template_id: QlibQuantEngineTemplate | str
    experiment_name: str
    parameters: Mapping[str, Any]
    recorder_tags: Mapping[str, str] = field(default_factory=dict)
    engine_version: str = QLIB_QUANT_ENGINE_ADAPTER_VERSION

    def __post_init__(self) -> None:
        try:
            template_id = QlibQuantEngineTemplate(self.template_id)
        except ValueError as exc:
            raise QlibQuantEngineError("template_id must be an approved Qlib QuantEngine template") from exc
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "experiment_name", _required_string("experiment_name", self.experiment_name))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "parameters", MappingProxyType(_safe_payload("parameters", self.parameters)))
        object.__setattr__(
            self,
            "recorder_tags",
            MappingProxyType(
                {
                    _required_string("recorder tag key", key): _required_string("recorder tag value", value)
                    for key, value in _safe_payload("recorder_tags", self.recorder_tags).items()
                }
            ),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id.value,
            "experiment_name": self.experiment_name,
            "engine_version": self.engine_version,
            "parameters": dict(self.parameters),
            "recorder_tags": dict(self.recorder_tags),
        }


@dataclass(frozen=True, slots=True)
class QlibQuantEngineRequest:
    run_id: str
    stage_id: str
    trace_id: str
    created_at: datetime
    backtest_spec: BacktestSpec
    dataset_conversion_artifacts: QlibDatasetConversionArtifacts
    config: QlibQuantEngineConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        _require_aware_datetime("created_at", self.created_at)
        if type(self.backtest_spec) is not BacktestSpec:
            raise QlibQuantEngineError("backtest_spec must be a BacktestSpec")
        if not str(self.backtest_spec.spec_hash).startswith("sha256:"):
            raise QlibQuantEngineError("BacktestSpec spec_hash is required")
        if type(self.dataset_conversion_artifacts) is not QlibDatasetConversionArtifacts:
            raise QlibQuantEngineError("dataset_conversion_artifacts must be QlibDatasetConversionArtifacts")
        if type(self.config) is not QlibQuantEngineConfig:
            raise QlibQuantEngineError("config must be a QlibQuantEngineConfig")

    @property
    def spec_id(self) -> str:
        return self.backtest_spec.spec_id

    @property
    def spec_hash(self) -> str:
        return self.backtest_spec.spec_hash


@dataclass(frozen=True, slots=True)
class QlibRecorderSnapshot:
    experiment_id: str
    recorder_id: str
    uri: str
    tags: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "experiment_id", _required_string("experiment_id", self.experiment_id))
        object.__setattr__(self, "recorder_id", _required_string("recorder_id", self.recorder_id))
        object.__setattr__(self, "uri", _required_string("uri", self.uri))
        object.__setattr__(
            self,
            "tags",
            MappingProxyType(
                {
                    _required_string("recorder tag key", key): _required_string("recorder tag value", value)
                    for key, value in self.tags.items()
                }
            ),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "recorder_id": self.recorder_id,
            "uri": self.uri,
            "tags": dict(self.tags),
        }


@dataclass(frozen=True, slots=True)
class QlibQuantEngineStepResult:
    operation: QlibQuantEngineOperation
    artifact_manifest: ArtifactManifest
    recorder_snapshot: QlibRecorderSnapshot
    output_hash: str

    def to_record(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "artifact": self.artifact_manifest.to_record(),
            "recorder": self.recorder_snapshot.to_record(),
            "output_hash": self.output_hash,
        }


@dataclass(frozen=True, slots=True)
class QlibQuantEngineRunReport:
    request: QlibQuantEngineRequest
    step_results: Sequence[QlibQuantEngineStepResult]
    report_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not QlibQuantEngineRequest:
            raise QlibQuantEngineError("request must be a QlibQuantEngineRequest")
        results = tuple(self.step_results)
        if not results:
            raise QlibQuantEngineError("step_results cannot be empty")
        for result in results:
            if type(result) is not QlibQuantEngineStepResult:
                raise QlibQuantEngineError("step_results must contain QlibQuantEngineStepResult values")
        object.__setattr__(self, "step_results", results)
        report_id = self.report_id or _stable_id(
            "qer",
            {
                "run_id": self.request.run_id,
                "stage_id": self.request.stage_id,
                "spec_hash": self.request.spec_hash,
                "output_hashes": [result.output_hash for result in results],
            },
        )
        object.__setattr__(self, "report_id", _required_string("report_id", report_id))

    def to_json_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_record())

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_name": QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME,
            "schema_version": QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_VERSION,
            "report_id": self.report_id,
            "adapter_version": QLIB_QUANT_ENGINE_ADAPTER_VERSION,
            "engine_scope": QLIB_QUANT_ENGINE_ADAPTER_SCOPE,
            "spec_id": self.request.spec_id,
            "spec_hash": self.request.spec_hash,
            "dataset_versions": dict(self.request.backtest_spec.dataset.dataset_versions),
            "operation_count": len(self.step_results),
            "operations": [result.operation.value for result in self.step_results],
            "steps": [result.to_record() for result in self.step_results],
            "trace": {
                "trace_id": self.request.trace_id,
                "run_id": self.request.run_id,
                "stage_id": self.request.stage_id,
            },
            "runtime": {
                "formal_portfolio_backtest_started": False,
                "ledger_started": False,
                "risk_started": False,
                "worker_loop_started": False,
            },
        }

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> ArtifactManifest:
        return artifact_store.put_bytes(
            self.to_json_bytes(),
            schema_name=QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME,
            schema_version=QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_VERSION,
            content_type=QLIB_QUANT_ENGINE_RUN_REPORT_CONTENT_TYPE,
            produced_by_run_id=self.request.run_id,
            produced_by_stage_id=self.request.stage_id,
            retention_tier=retention_tier,
            created_at=self.request.created_at,
        )


class QlibQuantEngineAdapter:
    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        facade: QlibQuantEngineFacade | None = None,
        policy: QlibRuntimeIsolationPolicy | None = None,
    ) -> None:
        self._artifact_store = artifact_store
        self._facade = facade or LazyQlibQuantEngineFacade()
        self._policy = policy or default_qlib_runtime_policy()
        if type(self._policy) is not QlibRuntimeIsolationPolicy:
            raise QlibQuantEngineError("policy must be a QlibRuntimeIsolationPolicy")
        if not self._policy.requires_run_stage_context or self._policy.allow_arbitrary_module_path:
            raise QlibQuantEngineError("Qlib policy must require run/stage context and forbid arbitrary module paths")

    def train(self, request: QlibQuantEngineRequest) -> QlibQuantEngineStepResult:
        return self._run(QlibQuantEngineOperation.TRAIN, request)

    def predict(self, request: QlibQuantEngineRequest) -> QlibQuantEngineStepResult:
        return self._run(QlibQuantEngineOperation.PREDICT, request)

    def backtest(self, request: QlibQuantEngineRequest) -> QlibQuantEngineStepResult:
        return self._run(QlibQuantEngineOperation.BACKTEST, request)

    def evaluate_factor(self, request: QlibQuantEngineRequest) -> QlibQuantEngineStepResult:
        return self._run(QlibQuantEngineOperation.EVALUATE_FACTOR, request)

    def build_run_report(
        self,
        *,
        request: QlibQuantEngineRequest,
        step_results: Sequence[QlibQuantEngineStepResult],
    ) -> QlibQuantEngineRunReport:
        return QlibQuantEngineRunReport(request=request, step_results=tuple(step_results))

    def _run(
        self,
        operation: QlibQuantEngineOperation,
        request: QlibQuantEngineRequest,
    ) -> QlibQuantEngineStepResult:
        if type(request) is not QlibQuantEngineRequest:
            raise QlibQuantEngineError("request must be a QlibQuantEngineRequest")
        config = self._config_for(operation, request)
        raw_output = getattr(self._facade, operation.value)(config)
        output = _safe_payload("facade_output", raw_output)
        recorder_snapshot = _recorder_snapshot_from_output(output, request=request, operation=operation)
        payload = self._step_payload(
            operation=operation,
            request=request,
            config=config,
            recorder_snapshot=recorder_snapshot,
            facade_output=output,
        )
        output_hash = "sha256:" + hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
        artifact = self._artifact_store.put_bytes(
            _canonical_json_bytes(payload),
            schema_name=QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME,
            schema_version=QLIB_QUANT_ENGINE_STEP_SCHEMA_VERSION,
            content_type=QLIB_QUANT_ENGINE_STEP_CONTENT_TYPE,
            produced_by_run_id=request.run_id,
            produced_by_stage_id=request.stage_id,
            retention_tier=ArtifactRetentionTier.STANDARD,
            created_at=request.created_at,
        )
        return QlibQuantEngineStepResult(
            operation=operation,
            artifact_manifest=artifact,
            recorder_snapshot=recorder_snapshot,
            output_hash=output_hash,
        )

    def _config_for(self, operation: QlibQuantEngineOperation, request: QlibQuantEngineRequest) -> dict[str, Any]:
        return {
            "operation": operation.value,
            "template_id": request.config.template_id.value,
            "experiment_name": request.config.experiment_name,
            "engine_version": request.config.engine_version,
            "parameters": dict(request.config.parameters),
            "recorder_tags": {
                **dict(request.config.recorder_tags),
                "platform_run_id": request.run_id,
                "platform_stage_id": request.stage_id,
                "platform_trace_id": request.trace_id,
                "backtest_spec_hash": request.spec_hash,
            },
            "platform": {
                "run_id": request.run_id,
                "stage_id": request.stage_id,
                "trace_id": request.trace_id,
                "spec_id": request.spec_id,
                "spec_hash": request.spec_hash,
                "dataset_versions": dict(request.backtest_spec.dataset.dataset_versions),
            },
            "dataset_conversion_artifacts": _dataset_conversion_artifact_records(
                request.dataset_conversion_artifacts
            ),
            "runtime_policy": self._policy.to_record(),
        }

    @staticmethod
    def _step_payload(
        *,
        operation: QlibQuantEngineOperation,
        request: QlibQuantEngineRequest,
        config: Mapping[str, Any],
        recorder_snapshot: QlibRecorderSnapshot,
        facade_output: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_name": QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME,
            "schema_version": QLIB_QUANT_ENGINE_STEP_SCHEMA_VERSION,
            "adapter_version": QLIB_QUANT_ENGINE_ADAPTER_VERSION,
            "engine_scope": QLIB_QUANT_ENGINE_ADAPTER_SCOPE,
            "operation": operation.value,
            "created_at": request.created_at.isoformat(),
            "spec_id": request.spec_id,
            "spec_hash": request.spec_hash,
            "config": dict(config),
            "recorder": recorder_snapshot.to_record(),
            "facade_output": dict(facade_output),
            "runtime": {
                "formal_portfolio_backtest_started": False,
                "ledger_started": False,
                "risk_started": False,
                "worker_loop_started": False,
            },
            "trace": {
                "trace_id": request.trace_id,
                "run_id": request.run_id,
                "stage_id": request.stage_id,
            },
        }


def _dataset_conversion_artifact_records(artifacts: QlibDatasetConversionArtifacts) -> dict[str, dict[str, Any]]:
    return {
        "calendar": artifacts.calendar.to_record(),
        "instruments": artifacts.instruments.to_record(),
        "features": artifacts.features.to_record(),
        "field_mapping": artifacts.field_mapping.to_record(),
        "summary": artifacts.summary.to_record(),
    }


def _recorder_snapshot_from_output(
    output: Mapping[str, Any],
    *,
    request: QlibQuantEngineRequest,
    operation: QlibQuantEngineOperation,
) -> QlibRecorderSnapshot:
    recorder = output.get("recorder")
    if not isinstance(recorder, Mapping):
        raise QlibQuantEngineError("Qlib facade output must include a recorder mapping")
    tags = dict(_safe_payload("recorder.tags", recorder.get("tags", {})))
    tags.update(
        {
            "platform_run_id": request.run_id,
            "platform_stage_id": request.stage_id,
            "platform_trace_id": request.trace_id,
            "backtest_spec_hash": request.spec_hash,
        }
    )
    return QlibRecorderSnapshot(
        experiment_id=str(recorder.get("experiment_id") or request.config.experiment_name),
        recorder_id=str(recorder.get("recorder_id") or f"{request.run_id}-{operation.value}"),
        uri=str(recorder.get("uri") or f"qlib://recorder/{request.run_id}/{operation.value}"),
        tags=tags,
    )


def _safe_payload(path: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _required_string(f"{path} key", str(key))
            if key_text.lower() in _FORBIDDEN_CONFIG_KEYS:
                raise QlibQuantEngineError("config must not accept arbitrary Python module path fields")
            normalized[key_text] = _safe_payload(f"{path}.{key_text}", item)
        return normalized
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return tuple(_safe_payload(f"{path}[]", item) for item in value)
    raise QlibQuantEngineError(f"{path} must be JSON-compatible")


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}_{digest[:32]}"


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _required_string(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QlibQuantEngineError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise QlibQuantEngineError(f"{field_name} must be a timezone-aware datetime")
