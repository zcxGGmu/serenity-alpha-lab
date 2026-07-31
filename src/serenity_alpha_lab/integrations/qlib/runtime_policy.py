from __future__ import annotations

from dataclasses import dataclass
from typing import Any


QLIB_PACKAGE_NAME = "pyqlib"
QLIB_PACKAGE_VERSION = "0.9.7"
QLIB_RUNTIME_SCOPE = "quant_worker_only"
QLIB_WORKER_QUEUE = "worker-quant"


@dataclass(frozen=True, slots=True)
class QlibRuntimeIsolationPolicy:
    package_name: str = QLIB_PACKAGE_NAME
    package_version: str = QLIB_PACKAGE_VERSION
    runtime_scope: str = QLIB_RUNTIME_SCOPE
    queue_name: str = QLIB_WORKER_QUEUE
    process_isolation: str = "dedicated_process"
    forbid_fastapi_initialization: bool = True
    forbid_runtime_import_at_module_import: bool = True
    requires_run_stage_context: bool = True
    allow_arbitrary_module_path: bool = False
    max_cpu_cores: int = 2
    max_memory_mb: int = 4096
    wall_clock_timeout_seconds: int = 3600
    heartbeat_interval_seconds: int = 15
    checkpoint_interval_seconds: int = 300

    def __post_init__(self) -> None:
        _require_non_empty("package_name", self.package_name)
        _require_non_empty("package_version", self.package_version)
        _require_non_empty("runtime_scope", self.runtime_scope)
        _require_non_empty("queue_name", self.queue_name)
        _require_non_empty("process_isolation", self.process_isolation)
        _require_positive_int("max_cpu_cores", self.max_cpu_cores)
        _require_positive_int("max_memory_mb", self.max_memory_mb)
        _require_positive_int("wall_clock_timeout_seconds", self.wall_clock_timeout_seconds)
        _require_positive_int("heartbeat_interval_seconds", self.heartbeat_interval_seconds)
        _require_positive_int("checkpoint_interval_seconds", self.checkpoint_interval_seconds)
        if self.checkpoint_interval_seconds < self.heartbeat_interval_seconds:
            raise ValueError("checkpoint_interval_seconds must be greater than or equal to heartbeat interval")

    def to_record(self) -> dict[str, Any]:
        return {
            "package": {
                "name": self.package_name,
                "version": self.package_version,
            },
            "runtime_scope": self.runtime_scope,
            "queue_name": self.queue_name,
            "process_isolation": self.process_isolation,
            "guards": {
                "forbid_fastapi_initialization": self.forbid_fastapi_initialization,
                "forbid_runtime_import_at_module_import": self.forbid_runtime_import_at_module_import,
                "requires_run_stage_context": self.requires_run_stage_context,
                "allow_arbitrary_module_path": self.allow_arbitrary_module_path,
            },
            "resources": {
                "max_cpu_cores": self.max_cpu_cores,
                "max_memory_mb": self.max_memory_mb,
                "wall_clock_timeout_seconds": self.wall_clock_timeout_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "checkpoint_interval_seconds": self.checkpoint_interval_seconds,
            },
        }


def default_qlib_runtime_policy() -> QlibRuntimeIsolationPolicy:
    return QlibRuntimeIsolationPolicy()


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive_int(field_name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
