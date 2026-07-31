from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.quant.screening.pipeline import (
    SCREEN_PIPELINE_ENGINE_VERSION,
    ScreenPipelineStage,
    ScreenPipelineStageTrace,
)
from serenity_alpha_lab.quant.screening.snapshot import ScreenSnapshot


SCREEN_PERFORMANCE_CONTRACT_VERSION = "quant.screen_performance@1.0.0"
SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME = "quant.screen_performance_reproducibility"
SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION = "1.0.0"
SCREEN_PERFORMANCE_REPORT_CONTENT_TYPE = "application/vnd.serenity.quant.screen-performance+json"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FACTOR_VERSION_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")


class ScreenPerformanceError(ValueError):
    """Raised when screening performance or reproducibility evidence is invalid."""


class ScreenPerformanceAcceptanceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ScreenPerformanceBudget:
    common_screen_slo_ms: float = 3_000.0
    cached_query_slo_ms: float = 500.0
    max_peak_memory_mb: float = 512.0
    max_result_rows: int = 6_000
    max_incremental_recompute_ratio: float = 0.15

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "common_screen_slo_ms",
            _finite_float("common_screen_slo_ms", self.common_screen_slo_ms, minimum=0.0),
        )
        object.__setattr__(
            self,
            "cached_query_slo_ms",
            _finite_float("cached_query_slo_ms", self.cached_query_slo_ms, minimum=0.0),
        )
        object.__setattr__(
            self,
            "max_peak_memory_mb",
            _finite_float("max_peak_memory_mb", self.max_peak_memory_mb, minimum=0.0),
        )
        if type(self.max_result_rows) is not int or self.max_result_rows <= 0:
            raise ScreenPerformanceError("max_result_rows must be a positive integer")
        object.__setattr__(
            self,
            "max_incremental_recompute_ratio",
            _finite_float(
                "max_incremental_recompute_ratio",
                self.max_incremental_recompute_ratio,
                minimum=0.0,
                maximum=1.0,
            ),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "common_screen_slo_ms": self.common_screen_slo_ms,
            "cached_query_slo_ms": self.cached_query_slo_ms,
            "max_peak_memory_mb": self.max_peak_memory_mb,
            "max_result_rows": self.max_result_rows,
            "max_incremental_recompute_ratio": self.max_incremental_recompute_ratio,
        }


@dataclass(frozen=True, slots=True)
class ScreenStagePerformanceSample:
    stage: ScreenPipelineStage | str
    duration_ms: float
    peak_memory_mb: float
    input_count: int
    output_count: int
    excluded_count: int
    warnings: Sequence[str] = ()

    @classmethod
    def from_stage_trace(
        cls,
        trace: ScreenPipelineStageTrace,
        *,
        duration_ms: float,
        peak_memory_mb: float,
    ) -> ScreenStagePerformanceSample:
        if type(trace) is not ScreenPipelineStageTrace:
            raise ScreenPerformanceError("trace must be a ScreenPipelineStageTrace")
        return cls(
            stage=trace.stage,
            duration_ms=duration_ms,
            peak_memory_mb=peak_memory_mb,
            input_count=trace.input_count,
            output_count=trace.output_count,
            excluded_count=trace.excluded_count,
            warnings=trace.warnings,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", ScreenPipelineStage(self.stage))
        object.__setattr__(self, "duration_ms", _finite_float("duration_ms", self.duration_ms, minimum=0.0))
        object.__setattr__(
            self,
            "peak_memory_mb",
            _finite_float("peak_memory_mb", self.peak_memory_mb, minimum=0.0),
        )
        _require_non_negative_int("input_count", self.input_count)
        _require_non_negative_int("output_count", self.output_count)
        _require_non_negative_int("excluded_count", self.excluded_count)
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))

    def to_record(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "duration_ms": self.duration_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "excluded_count": self.excluded_count,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ScreenIncrementalBaseline:
    changed_dataset_versions: Mapping[str, str]
    total_candidate_count: int
    recomputed_candidate_count: int
    changed_factor_versions: Sequence[str] = ()
    changed_trade_dates: Sequence[date] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "changed_dataset_versions", _normalize_dataset_versions(self.changed_dataset_versions))
        if type(self.total_candidate_count) is not int or self.total_candidate_count <= 0:
            raise ScreenPerformanceError("total_candidate_count must be a positive integer")
        _require_non_negative_int("recomputed_candidate_count", self.recomputed_candidate_count)
        if self.recomputed_candidate_count > self.total_candidate_count:
            raise ScreenPerformanceError("recomputed_candidate_count cannot exceed total_candidate_count")
        object.__setattr__(self, "changed_factor_versions", _factor_version_tuple(self.changed_factor_versions))
        object.__setattr__(self, "changed_trade_dates", _date_tuple("changed_trade_dates", self.changed_trade_dates))

    @property
    def recompute_ratio(self) -> float:
        return self.recomputed_candidate_count / self.total_candidate_count

    def to_record(self) -> dict[str, object]:
        return {
            "changed_dataset_versions": dict(self.changed_dataset_versions),
            "changed_factor_versions": list(self.changed_factor_versions),
            "changed_trade_dates": [value.isoformat() for value in self.changed_trade_dates],
            "total_candidate_count": self.total_candidate_count,
            "recomputed_candidate_count": self.recomputed_candidate_count,
            "recompute_ratio": self.recompute_ratio,
        }


@dataclass(frozen=True, slots=True)
class ScreenRunBundle:
    code_version: str
    engine_version: str
    screen_definition_version_id: str
    as_of: date
    dataset_versions: Mapping[str, str]
    result_hash: str
    screen_snapshot_id: str
    pipeline_snapshot_id: str
    schema_name: str
    schema_version: str
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    artifact_manifest: ArtifactManifest | None = None
    bundle_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code_version", _required_string("code_version", self.code_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(
            self,
            "screen_definition_version_id",
            _required_string("screen_definition_version_id", self.screen_definition_version_id),
        )
        _require_date("as_of", self.as_of)
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        object.__setattr__(self, "result_hash", _validate_sha256("result_hash", self.result_hash))
        object.__setattr__(self, "screen_snapshot_id", _required_string("screen_snapshot_id", self.screen_snapshot_id))
        object.__setattr__(self, "pipeline_snapshot_id", _required_string("pipeline_snapshot_id", self.pipeline_snapshot_id))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        if self.artifact_manifest is not None and type(self.artifact_manifest) is not ArtifactManifest:
            raise ScreenPerformanceError("artifact_manifest must be an ArtifactManifest")
        bundle_id = self.bundle_id or _stable_id("srb", self._identity_record(include_bundle_id=False))
        object.__setattr__(self, "bundle_id", _required_string("bundle_id", bundle_id))

    def to_record(self) -> dict[str, Any]:
        record = self._identity_record(include_bundle_id=True)
        return record

    def _identity_record(self, *, include_bundle_id: bool) -> dict[str, Any]:
        record: dict[str, Any] = {
            "code_version": self.code_version,
            "engine_version": self.engine_version,
            "screen_definition_version_id": self.screen_definition_version_id,
            "as_of": self.as_of.isoformat(),
            "dataset_versions": dict(self.dataset_versions),
            "result_hash": self.result_hash,
            "screen_snapshot_id": self.screen_snapshot_id,
            "pipeline_snapshot_id": self.pipeline_snapshot_id,
            "schema": {"name": self.schema_name, "version": self.schema_version},
            "trace": {"trace_id": self.trace_id, "run_id": self.run_id, "stage_id": self.stage_id},
            "artifact": self.artifact_manifest.to_record() if self.artifact_manifest is not None else None,
        }
        if include_bundle_id:
            record["bundle_id"] = self.bundle_id
        return record


@dataclass(frozen=True, slots=True)
class ScreenReproducibilityCheck:
    baseline_result_hash: str
    repeated_result_hash: str
    reproducible: bool
    mismatch_reasons: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "baseline_result_hash",
            _validate_sha256("baseline_result_hash", self.baseline_result_hash),
        )
        object.__setattr__(
            self,
            "repeated_result_hash",
            _validate_sha256("repeated_result_hash", self.repeated_result_hash),
        )
        if type(self.reproducible) is not bool:
            raise ScreenPerformanceError("reproducible must be a bool")
        object.__setattr__(self, "mismatch_reasons", _string_tuple("mismatch_reason", self.mismatch_reasons))
        if self.reproducible and self.mismatch_reasons:
            raise ScreenPerformanceError("reproducible checks cannot include mismatch reasons")

    def to_record(self) -> dict[str, object]:
        return {
            "baseline_result_hash": self.baseline_result_hash,
            "repeated_result_hash": self.repeated_result_hash,
            "reproducible": self.reproducible,
            "mismatch_reasons": list(self.mismatch_reasons),
        }


@dataclass(frozen=True, slots=True)
class ScreenPerformanceReport:
    run_bundle: ScreenRunBundle
    budget: ScreenPerformanceBudget
    stage_samples: Sequence[ScreenStagePerformanceSample]
    reproducibility: ScreenReproducibilityCheck
    incremental_baseline: ScreenIncrementalBaseline
    result_row_count: int
    cached_query_duration_ms: float
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    failure_codes: Sequence[str] = ()
    warnings: Sequence[str] = ()
    report_id: str | None = None
    contract_version: str = SCREEN_PERFORMANCE_CONTRACT_VERSION
    schema_name: str = SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME
    schema_version: str = SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.run_bundle) is not ScreenRunBundle:
            raise ScreenPerformanceError("run_bundle must be a ScreenRunBundle")
        if type(self.budget) is not ScreenPerformanceBudget:
            raise ScreenPerformanceError("budget must be a ScreenPerformanceBudget")
        samples = tuple(self.stage_samples)
        if not samples:
            raise ScreenPerformanceError("stage_samples are required")
        for sample in samples:
            if type(sample) is not ScreenStagePerformanceSample:
                raise ScreenPerformanceError("stage_samples must contain ScreenStagePerformanceSample values")
        object.__setattr__(self, "stage_samples", samples)
        if type(self.reproducibility) is not ScreenReproducibilityCheck:
            raise ScreenPerformanceError("reproducibility must be a ScreenReproducibilityCheck")
        if type(self.incremental_baseline) is not ScreenIncrementalBaseline:
            raise ScreenPerformanceError("incremental_baseline must be a ScreenIncrementalBaseline")
        _require_non_negative_int("result_row_count", self.result_row_count)
        object.__setattr__(
            self,
            "cached_query_duration_ms",
            _finite_float("cached_query_duration_ms", self.cached_query_duration_ms, minimum=0.0),
        )
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "failure_codes", _string_tuple("failure_code", self.failure_codes))
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        report_id = self.report_id or _stable_id("spr", self._identity_record(include_report_id=False))
        object.__setattr__(self, "report_id", _required_string("report_id", report_id))

    @property
    def total_duration_ms(self) -> float:
        return sum(sample.duration_ms for sample in self.stage_samples)

    @property
    def peak_memory_mb(self) -> float:
        return max(sample.peak_memory_mb for sample in self.stage_samples)

    @property
    def acceptance_status(self) -> str:
        return (
            ScreenPerformanceAcceptanceStatus.FAILED.value
            if self.failure_codes
            else ScreenPerformanceAcceptanceStatus.PASSED.value
        )

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_record(self) -> dict[str, Any]:
        return self._identity_record(include_report_id=True)

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        produced_by_run_id: str | None = None,
        produced_by_stage_id: str | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> ArtifactManifest:
        run_id = _required_string("produced_by_run_id", produced_by_run_id or self.run_id or self.run_bundle.run_id)
        stage_id = produced_by_stage_id if produced_by_stage_id is not None else self.stage_id or self.run_bundle.stage_id
        return artifact_store.put_bytes(
            self.to_json_bytes(),
            schema_name=SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME,
            schema_version=SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION,
            content_type=SCREEN_PERFORMANCE_REPORT_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )

    def _identity_record(self, *, include_report_id: bool) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at.isoformat(),
            "acceptance_status": self.acceptance_status,
            "failure_codes": list(self.failure_codes),
            "warnings": list(self.warnings),
            "run_bundle": self.run_bundle.to_record(),
            "budget": self.budget.to_record(),
            "observed": {
                "total_duration_ms": self.total_duration_ms,
                "cached_query_duration_ms": self.cached_query_duration_ms,
                "peak_memory_mb": self.peak_memory_mb,
                "result_row_count": self.result_row_count,
            },
            "stage_samples": [sample.to_record() for sample in self.stage_samples],
            "incremental_baseline": self.incremental_baseline.to_record(),
            "reproducibility": self.reproducibility.to_record(),
            "trace": {"trace_id": self.trace_id, "run_id": self.run_id, "stage_id": self.stage_id},
        }
        if include_report_id:
            record["report_id"] = self.report_id
        return record


def default_a_share_screening_budget() -> ScreenPerformanceBudget:
    return ScreenPerformanceBudget()


def screen_result_hash(snapshot: ScreenSnapshot, *, code_version: str, engine_version: str) -> str:
    if type(snapshot) is not ScreenSnapshot:
        raise ScreenPerformanceError("snapshot must be a ScreenSnapshot")
    payload = _screen_result_identity(snapshot, code_version=code_version, engine_version=engine_version)
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def build_screen_run_bundle(
    snapshot: ScreenSnapshot,
    *,
    code_version: str,
    engine_version: str = SCREEN_PIPELINE_ENGINE_VERSION,
    artifact_manifest: ArtifactManifest | None = None,
) -> ScreenRunBundle:
    if type(snapshot) is not ScreenSnapshot:
        raise ScreenPerformanceError("snapshot must be a ScreenSnapshot")
    return ScreenRunBundle(
        code_version=code_version,
        engine_version=engine_version,
        screen_definition_version_id=snapshot.definition_version_id,
        as_of=snapshot.as_of,
        dataset_versions=snapshot.dataset_versions,
        result_hash=screen_result_hash(snapshot, code_version=code_version, engine_version=engine_version),
        screen_snapshot_id=snapshot.screen_snapshot_id,
        pipeline_snapshot_id=snapshot.pipeline_snapshot_id,
        schema_name=snapshot.schema_name,
        schema_version=snapshot.schema_version,
        trace_id=snapshot.trace_id,
        run_id=snapshot.run_id,
        stage_id=snapshot.stage_id,
        artifact_manifest=artifact_manifest,
    )


def evaluate_screen_reproducibility(
    baseline: ScreenSnapshot,
    repeated: ScreenSnapshot,
    *,
    code_version: str,
    engine_version: str,
) -> ScreenReproducibilityCheck:
    if type(baseline) is not ScreenSnapshot or type(repeated) is not ScreenSnapshot:
        raise ScreenPerformanceError("baseline and repeated must be ScreenSnapshot values")
    baseline_hash = screen_result_hash(baseline, code_version=code_version, engine_version=engine_version)
    repeated_hash = screen_result_hash(repeated, code_version=code_version, engine_version=engine_version)
    mismatch_reasons: list[str] = []
    if baseline.definition_version_id != repeated.definition_version_id:
        mismatch_reasons.append("screen_definition_version_mismatch")
    if baseline.as_of != repeated.as_of:
        mismatch_reasons.append("as_of_mismatch")
    if dict(baseline.dataset_versions) != dict(repeated.dataset_versions):
        mismatch_reasons.append("dataset_versions_mismatch")
    if baseline_hash != repeated_hash:
        mismatch_reasons.append("result_hash_mismatch")
    return ScreenReproducibilityCheck(
        baseline_result_hash=baseline_hash,
        repeated_result_hash=repeated_hash,
        reproducible=not mismatch_reasons,
        mismatch_reasons=tuple(mismatch_reasons),
    )


def build_screen_performance_report(
    *,
    snapshot: ScreenSnapshot,
    repeated_snapshot: ScreenSnapshot,
    code_version: str,
    engine_version: str = SCREEN_PIPELINE_ENGINE_VERSION,
    stage_samples: Sequence[ScreenStagePerformanceSample],
    incremental_baseline: ScreenIncrementalBaseline,
    budget: ScreenPerformanceBudget | None = None,
    cached_query_duration_ms: float,
    created_at: datetime,
    artifact_manifest: ArtifactManifest | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    stage_id: str | None = None,
    warnings: Sequence[str] = (),
) -> ScreenPerformanceReport:
    budget = budget or default_a_share_screening_budget()
    samples = tuple(stage_samples)
    run_bundle = build_screen_run_bundle(
        snapshot,
        code_version=code_version,
        engine_version=engine_version,
        artifact_manifest=artifact_manifest,
    )
    reproducibility = evaluate_screen_reproducibility(
        snapshot,
        repeated_snapshot,
        code_version=code_version,
        engine_version=engine_version,
    )
    cached_duration = _finite_float("cached_query_duration_ms", cached_query_duration_ms, minimum=0.0)
    failure_codes = _budget_failure_codes(
        budget=budget,
        samples=samples,
        cached_query_duration_ms=cached_duration,
        result_row_count=snapshot.passed_count + snapshot.failed_count,
        incremental_baseline=incremental_baseline,
    )
    if not reproducibility.reproducible:
        failure_codes.append("result_reproducibility_failed")
    return ScreenPerformanceReport(
        run_bundle=run_bundle,
        budget=budget,
        stage_samples=samples,
        reproducibility=reproducibility,
        incremental_baseline=incremental_baseline,
        result_row_count=snapshot.passed_count + snapshot.failed_count,
        cached_query_duration_ms=cached_duration,
        created_at=created_at,
        trace_id=trace_id or snapshot.trace_id,
        run_id=run_id or snapshot.run_id,
        stage_id=stage_id or snapshot.stage_id,
        failure_codes=tuple(failure_codes),
        warnings=warnings,
    )


def publish_screen_performance_report(
    report: ScreenPerformanceReport,
    artifact_store: ArtifactStore,
    *,
    produced_by_run_id: str | None = None,
    produced_by_stage_id: str | None = None,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(report) is not ScreenPerformanceReport:
        raise ScreenPerformanceError("report must be a ScreenPerformanceReport")
    return report.publish(
        artifact_store,
        produced_by_run_id=produced_by_run_id,
        produced_by_stage_id=produced_by_stage_id,
        retention_tier=retention_tier,
    )


def _budget_failure_codes(
    *,
    budget: ScreenPerformanceBudget,
    samples: Sequence[ScreenStagePerformanceSample],
    cached_query_duration_ms: float,
    result_row_count: int,
    incremental_baseline: ScreenIncrementalBaseline,
) -> list[str]:
    total_duration_ms = sum(sample.duration_ms for sample in samples)
    peak_memory_mb = max((sample.peak_memory_mb for sample in samples), default=0.0)
    failures: list[str] = []
    if total_duration_ms > budget.common_screen_slo_ms:
        failures.append("common_screen_slo_exceeded")
    if cached_query_duration_ms > budget.cached_query_slo_ms:
        failures.append("cached_query_slo_exceeded")
    if peak_memory_mb > budget.max_peak_memory_mb:
        failures.append("peak_memory_budget_exceeded")
    if result_row_count > budget.max_result_rows:
        failures.append("result_row_budget_exceeded")
    if incremental_baseline.recompute_ratio > budget.max_incremental_recompute_ratio:
        failures.append("incremental_recompute_ratio_exceeded")
    return failures


def _screen_result_identity(snapshot: ScreenSnapshot, *, code_version: str, engine_version: str) -> dict[str, Any]:
    return {
        "contract_version": SCREEN_PERFORMANCE_CONTRACT_VERSION,
        "code_version": _required_string("code_version", code_version),
        "engine_version": _required_string("engine_version", engine_version),
        "screen_snapshot_schema": {"name": snapshot.schema_name, "version": snapshot.schema_version},
        "screen_definition_version_id": snapshot.definition_version_id,
        "as_of": snapshot.as_of.isoformat(),
        "dataset_versions": dict(snapshot.dataset_versions),
        "passed_count": snapshot.passed_count,
        "failed_count": snapshot.failed_count,
        "results": [result.to_record() for result in snapshot.results],
    }


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:32]}"


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise ScreenPerformanceError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise ScreenPerformanceError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version)
        for name, version in dataset_versions.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_dataset_version(value: object) -> str:
    version = _required_string("dataset_version", value)
    if version.lower() == "latest":
        raise ScreenPerformanceError("Screen performance evidence requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise ScreenPerformanceError("Screen performance evidence requires concrete Dataset Version ids") from exc
    return version


def _factor_version_tuple(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ScreenPerformanceError("changed_factor_versions must be a sequence")
    normalized = tuple(_required_string("factor_version_id", value) for value in values)
    for value in normalized:
        if not _FACTOR_VERSION_RE.fullmatch(value):
            raise ScreenPerformanceError("factor_version_id must be fdv_<hex>")
    return tuple(sorted(normalized))


def _date_tuple(field_name: str, values: Sequence[date]) -> tuple[date, ...]:
    if isinstance(values, str):
        raise ScreenPerformanceError(f"{field_name} must be a sequence")
    normalized = tuple(values)
    for value in normalized:
        _require_date(field_name, value)
    return tuple(sorted(normalized))


def _validate_sha256(field_name: str, value: object) -> str:
    text = _required_string(field_name, value)
    if not _HASH_RE.fullmatch(text):
        raise ScreenPerformanceError(f"{field_name} must be sha256:<64 lowercase hex>")
    return text


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise ScreenPerformanceError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise ScreenPerformanceError(f"{field_name} is required")
    return stripped


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("value", value)


def _finite_float(
    field_name: str,
    value: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise ScreenPerformanceError(f"{field_name} must be finite")
    normalized = float(value)
    if minimum is not None and normalized < minimum:
        raise ScreenPerformanceError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise ScreenPerformanceError(f"{field_name} must be <= {maximum}")
    return normalized


def _require_non_negative_int(field_name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ScreenPerformanceError(f"{field_name} cannot be negative")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise ScreenPerformanceError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ScreenPerformanceError(f"{field_name} must be timezone-aware")


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ScreenPerformanceError(f"{field_name} values must be a sequence")
    return tuple(_required_string(field_name, value) for value in values)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


__all__ = [
    "SCREEN_PERFORMANCE_CONTRACT_VERSION",
    "SCREEN_PERFORMANCE_REPORT_CONTENT_TYPE",
    "SCREEN_PERFORMANCE_REPORT_SCHEMA_NAME",
    "SCREEN_PERFORMANCE_REPORT_SCHEMA_VERSION",
    "ScreenIncrementalBaseline",
    "ScreenPerformanceAcceptanceStatus",
    "ScreenPerformanceBudget",
    "ScreenPerformanceError",
    "ScreenPerformanceReport",
    "ScreenReproducibilityCheck",
    "ScreenRunBundle",
    "ScreenStagePerformanceSample",
    "build_screen_performance_report",
    "build_screen_run_bundle",
    "default_a_share_screening_budget",
    "evaluate_screen_reproducibility",
    "publish_screen_performance_report",
    "screen_result_hash",
]
