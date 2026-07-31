from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.run_lifecycle import EventKind, Run, RunEvent, RunStatus, Stage
from serenity_alpha_lab.quant.backtest.artifacts import BacktestArtifactBundle, BacktestArtifactState
from serenity_alpha_lab.quant.backtest.audit import BacktestBiasAuditReport, BacktestBiasAuditStatus
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.metrics import BacktestPerformanceMetricReport
from serenity_alpha_lab.quant.backtest.risk import RiskDecisionStatus, RiskPolicyResult
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec


BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION = "application.backtest_run_orchestrator@1.0.0"
BACKTEST_RUN_SCHEMA_NAME = "quant.backtest_run"
BACKTEST_RUN_SCHEMA_VERSION = "1.0.0"
BACKTEST_RUN_SUMMARY_CONTENT_TYPE = "application/vnd.serenity.quant.backtest-run+json"
BACKTEST_RUN_ORCHESTRATOR_VERSION = "cn_a_share_backtest_run_orchestrator@1.0.0"
BACKTEST_RUN_TYPE = "formal_portfolio_backtest"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class BacktestRunOrchestratorError(ValueError):
    """Raised when BacktestRun orchestration inputs violate the formal contract."""


class BacktestRunMode(StrEnum):
    PREVIEW = "preview"
    FORMAL = "formal"


class BacktestRunCodeState(StrEnum):
    CLEAN = "clean"
    DIRTY = "dirty"


class BacktestRunStatus(StrEnum):
    SUCCEEDED = "succeeded"


@dataclass(frozen=True, slots=True)
class BacktestRunStageRecord:
    stage_id: str
    name: str
    status: str
    started_at: datetime
    completed_at: datetime
    artifact_ids: Sequence[str] = ()
    output_ids: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "name", _required_string("name", self.name))
        object.__setattr__(self, "status", _required_string("status", self.status))
        _require_aware_datetime("started_at", self.started_at)
        _require_aware_datetime("completed_at", self.completed_at)
        object.__setattr__(self, "artifact_ids", _string_tuple("artifact_id", self.artifact_ids))
        object.__setattr__(self, "output_ids", _string_tuple("output_id", self.output_ids))

    def to_record(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "artifact_ids": list(self.artifact_ids),
            "output_ids": list(self.output_ids),
        }


@dataclass(frozen=True, slots=True)
class BacktestRunRequest:
    run_id: str
    trace_id: str
    idempotency_key: str
    submitted_at: datetime
    spec: BacktestSpec
    engine_evidence: Mapping[str, Any]
    ledger: PortfolioLedger
    risk_result: RiskPolicyResult
    audit_report: BacktestBiasAuditReport
    metrics_report: BacktestPerformanceMetricReport
    artifact_bundle: BacktestArtifactBundle
    requested_mode: BacktestRunMode | str = BacktestRunMode.FORMAL
    code_state: BacktestRunCodeState | str = BacktestRunCodeState.CLEAN
    patch_hash: str | None = None
    engine_version: str = BACKTEST_RUN_ORCHESTRATOR_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "idempotency_key", _required_string("idempotency_key", self.idempotency_key))
        _require_aware_datetime("submitted_at", self.submitted_at)
        if type(self.spec) is not BacktestSpec:
            raise BacktestRunOrchestratorError("spec must be a BacktestSpec")
        object.__setattr__(self, "engine_evidence", _freeze_mapping(self.engine_evidence))
        if type(self.ledger) is not PortfolioLedger:
            raise BacktestRunOrchestratorError("ledger must be a PortfolioLedger")
        if type(self.risk_result) is not RiskPolicyResult:
            raise BacktestRunOrchestratorError("risk_result must be a RiskPolicyResult")
        if type(self.audit_report) is not BacktestBiasAuditReport:
            raise BacktestRunOrchestratorError("audit_report must be a BacktestBiasAuditReport")
        if type(self.metrics_report) is not BacktestPerformanceMetricReport:
            raise BacktestRunOrchestratorError("metrics_report must be a BacktestPerformanceMetricReport")
        if type(self.artifact_bundle) is not BacktestArtifactBundle:
            raise BacktestRunOrchestratorError("artifact_bundle must be a BacktestArtifactBundle")
        object.__setattr__(self, "requested_mode", _enum_value(BacktestRunMode, "requested_mode", self.requested_mode))
        object.__setattr__(self, "code_state", _enum_value(BacktestRunCodeState, "code_state", self.code_state))
        object.__setattr__(self, "patch_hash", _optional_sha256("patch_hash", self.patch_hash))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def request_payload(self, *, effective_mode: BacktestRunMode | str | None = None) -> dict[str, object]:
        mode = self.requested_mode if effective_mode is None else _enum_value(BacktestRunMode, "effective_mode", effective_mode)
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "idempotency_key": self.idempotency_key,
            "submitted_at": self.submitted_at.isoformat(),
            "requested_mode": self.requested_mode.value,
            "effective_mode": mode.value,
            "code_state": self.code_state.value,
            "patch_hash": self.patch_hash,
            "engine_version": self.engine_version,
            "spec_id": self.spec.spec_id,
            "spec_hash": self.spec.spec_hash,
            "dataset_versions": dict(self.spec.dataset.dataset_versions),
            "dataset_hashes": dict(self.spec.dataset.dataset_hashes),
            "engine_evidence": _thaw_value(self.engine_evidence),
            "metadata": _thaw_value(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class BacktestRunRecord:
    run_id: str
    trace_id: str
    idempotency_key: str
    request_hash: str
    reuse_key: str
    status: BacktestRunStatus | str
    requested_mode: BacktestRunMode | str
    effective_mode: BacktestRunMode | str
    code_state: BacktestRunCodeState | str
    patch_hash: str | None
    spec_id: str
    spec_hash: str
    dataset_versions: Mapping[str, str]
    dataset_hashes: Mapping[str, str]
    engine_version: str
    engine_evidence: Mapping[str, Any]
    lifecycle: Mapping[str, Any]
    stages: Sequence[BacktestRunStageRecord]
    artifact_bundle: BacktestArtifactBundle
    summary_artifact: ArtifactManifest
    eligible_for_ranking: bool
    warning_codes: Sequence[str] = ()
    reused_from_run_id: str | None = None
    submitted_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)
    contract_version: str = BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION
    schema_name: str = BACKTEST_RUN_SCHEMA_NAME
    schema_version: str = BACKTEST_RUN_SCHEMA_VERSION
    orchestrator_version: str = BACKTEST_RUN_ORCHESTRATOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "idempotency_key", _required_string("idempotency_key", self.idempotency_key))
        object.__setattr__(self, "request_hash", _validate_sha256("request_hash", self.request_hash))
        object.__setattr__(self, "reuse_key", _validate_sha256("reuse_key", self.reuse_key))
        object.__setattr__(self, "status", _enum_value(BacktestRunStatus, "status", self.status))
        object.__setattr__(self, "requested_mode", _enum_value(BacktestRunMode, "requested_mode", self.requested_mode))
        object.__setattr__(self, "effective_mode", _enum_value(BacktestRunMode, "effective_mode", self.effective_mode))
        object.__setattr__(self, "code_state", _enum_value(BacktestRunCodeState, "code_state", self.code_state))
        object.__setattr__(self, "patch_hash", _optional_sha256("patch_hash", self.patch_hash))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "dataset_versions", _string_mapping("dataset_versions", self.dataset_versions))
        object.__setattr__(self, "dataset_hashes", _string_mapping("dataset_hashes", self.dataset_hashes))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "engine_evidence", _freeze_mapping(self.engine_evidence))
        object.__setattr__(self, "lifecycle", _freeze_mapping(self.lifecycle))
        stages = tuple(self.stages)
        for stage in stages:
            if type(stage) is not BacktestRunStageRecord:
                raise BacktestRunOrchestratorError("stages must contain BacktestRunStageRecord values")
        object.__setattr__(self, "stages", stages)
        if type(self.artifact_bundle) is not BacktestArtifactBundle:
            raise BacktestRunOrchestratorError("artifact_bundle must be a BacktestArtifactBundle")
        if type(self.summary_artifact) is not ArtifactManifest:
            raise BacktestRunOrchestratorError("summary_artifact must be an ArtifactManifest")
        if type(self.eligible_for_ranking) is not bool:
            raise BacktestRunOrchestratorError("eligible_for_ranking must be boolean")
        object.__setattr__(self, "warning_codes", _string_tuple("warning_code", self.warning_codes))
        object.__setattr__(self, "reused_from_run_id", _optional_string(self.reused_from_run_id))
        _require_aware_datetime("submitted_at", self.submitted_at)
        _require_aware_datetime("completed_at", self.completed_at)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "orchestrator_version", _required_string("orchestrator_version", self.orchestrator_version))

    def for_reuse(self, *, idempotency_key: str, request_hash: str) -> BacktestRunRecord:
        return replace(
            self,
            idempotency_key=_required_string("idempotency_key", idempotency_key),
            request_hash=_validate_sha256("request_hash", request_hash),
            reused_from_run_id=self.run_id,
        )

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "orchestrator_version": self.orchestrator_version,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "idempotency_key": self.idempotency_key,
            "request_hash": self.request_hash,
            "reuse_key": self.reuse_key,
            "status": self.status.value,
            "requested_mode": self.requested_mode.value,
            "effective_mode": self.effective_mode.value,
            "code_state": self.code_state.value,
            "patch_hash": self.patch_hash,
            "eligible_for_ranking": self.eligible_for_ranking,
            "warning_codes": list(self.warning_codes),
            "reused_from_run_id": self.reused_from_run_id,
            "submitted_at": self.submitted_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "spec": {
                "spec_id": self.spec_id,
                "spec_hash": self.spec_hash,
                "dataset_versions": dict(self.dataset_versions),
                "dataset_hashes": dict(self.dataset_hashes),
            },
            "engine_evidence": _thaw_value(self.engine_evidence),
            "lifecycle": _thaw_value(self.lifecycle),
            "stages": [stage.to_record() for stage in self.stages],
            "outputs": {
                "artifact_bundle": {
                    "bundle_id": self.artifact_bundle.bundle_id,
                    "state": self.artifact_bundle.state.value,
                    "output_artifact_ids": [
                        output.artifact_id for output in self.artifact_bundle.outputs.values()
                    ],
                },
                "summary_artifact": self.summary_artifact.to_record(),
            },
            "runtime": _runtime_boundary_record(),
        }


class InMemoryBacktestRunRepository:
    """In-memory BacktestRun repository for contract tests and desktop-local orchestration."""

    def __init__(self) -> None:
        self._by_run_id: dict[str, BacktestRunRecord] = {}
        self._by_idempotency_key: dict[str, BacktestRunRecord] = {}
        self._by_reuse_key: dict[str, BacktestRunRecord] = {}

    def get_by_idempotency_key(self, idempotency_key: str) -> BacktestRunRecord | None:
        return self._by_idempotency_key.get(_required_string("idempotency_key", idempotency_key))

    def get_success_by_reuse_key(self, reuse_key: str) -> BacktestRunRecord | None:
        record = self._by_reuse_key.get(_validate_sha256("reuse_key", reuse_key))
        if record is None or record.status is not BacktestRunStatus.SUCCEEDED:
            return None
        return record

    def save(self, record: BacktestRunRecord) -> None:
        if type(record) is not BacktestRunRecord:
            raise BacktestRunOrchestratorError("record must be a BacktestRunRecord")
        self._by_idempotency_key[record.idempotency_key] = record
        if record.reused_from_run_id is None:
            self._by_run_id[record.run_id] = record
            self._by_reuse_key[record.reuse_key] = record


class BacktestRunOrchestrator:
    def __init__(
        self,
        *,
        repository: InMemoryBacktestRunRepository,
        artifact_store: ArtifactStore,
    ) -> None:
        if type(repository) is not InMemoryBacktestRunRepository:
            raise BacktestRunOrchestratorError("repository must be an InMemoryBacktestRunRepository")
        self._repository = repository
        self._artifact_store = artifact_store

    def finalize(self, request: BacktestRunRequest) -> BacktestRunRecord:
        if type(request) is not BacktestRunRequest:
            raise BacktestRunOrchestratorError("request must be a BacktestRunRequest")
        effective_mode, warnings = self._effective_mode_and_warnings(request)
        request_hash = _sha256_record(request.request_payload(effective_mode=effective_mode))
        existing = self._repository.get_by_idempotency_key(request.idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise BacktestRunOrchestratorError("Idempotency-Key was reused for a different BacktestRun request")
            return existing

        reuse_key = self._reuse_key(request=request, effective_mode=effective_mode)
        reusable = self._repository.get_success_by_reuse_key(reuse_key)
        if reusable is not None:
            reused = reusable.for_reuse(idempotency_key=request.idempotency_key, request_hash=request_hash)
            self._repository.save(reused)
            return reused

        self._validate_cross_layer_bindings(request)
        eligible_for_ranking = self._validate_promotion_guards(request, effective_mode)
        record = self._build_record(
            request=request,
            effective_mode=effective_mode,
            warning_codes=warnings,
            request_hash=request_hash,
            reuse_key=reuse_key,
            eligible_for_ranking=eligible_for_ranking,
        )
        self._repository.save(record)
        return record

    @staticmethod
    def _effective_mode_and_warnings(request: BacktestRunRequest) -> tuple[BacktestRunMode, tuple[str, ...]]:
        if request.requested_mode is BacktestRunMode.FORMAL and request.code_state is BacktestRunCodeState.DIRTY:
            if request.patch_hash is None:
                raise BacktestRunOrchestratorError("formal BacktestRun cannot start from dirty code without patch_hash")
            return BacktestRunMode.PREVIEW, ("dirty_code_downgraded_to_preview",)
        return request.requested_mode, ()

    @staticmethod
    def _reuse_key(*, request: BacktestRunRequest, effective_mode: BacktestRunMode) -> str:
        return _sha256_record(
            {
                "reuse_kind": "backtest-run-v1",
                "spec_hash": request.spec.spec_hash,
                "dataset_hashes": dict(request.spec.dataset.dataset_hashes),
                "engine_version": request.engine_version,
                "effective_mode": effective_mode.value,
                "code_state": request.code_state.value,
                "patch_hash": request.patch_hash,
            }
        )

    @staticmethod
    def _validate_cross_layer_bindings(request: BacktestRunRequest) -> None:
        _require_bound("ledger", request.ledger.spec_id, request.spec.spec_id, "spec_id")
        _require_bound("ledger", request.ledger.spec_hash, request.spec.spec_hash, "spec_hash")
        _require_bound("ledger", request.ledger.run_id, request.run_id, "run_id")
        _require_bound("risk result", request.risk_result.spec_id, request.spec.spec_id, "spec_id")
        _require_bound("risk result", request.risk_result.spec_hash, request.spec.spec_hash, "spec_hash")
        _require_bound("risk result", request.risk_result.run_id, request.run_id, "run_id")
        _require_bound("audit report", request.audit_report.spec_id, request.spec.spec_id, "spec_id")
        _require_bound("audit report", request.audit_report.spec_hash, request.spec.spec_hash, "spec_hash")
        _require_bound("audit report", request.audit_report.run_id, request.run_id, "run_id")
        _require_bound("metrics report", request.metrics_report.spec_id, request.spec.spec_id, "spec_id")
        _require_bound("metrics report", request.metrics_report.spec_hash, request.spec.spec_hash, "spec_hash")
        _require_bound("metrics report", request.metrics_report.run_id, request.run_id, "run_id")
        _require_bound("artifact bundle", request.artifact_bundle.spec_id, request.spec.spec_id, "spec_id")
        _require_bound("artifact bundle", request.artifact_bundle.spec_hash, request.spec.spec_hash, "spec_hash")
        _require_bound("artifact bundle", request.artifact_bundle.run_id, request.run_id, "run_id")
        _require_bound("artifact bundle", dict(request.artifact_bundle.dataset_versions), dict(request.spec.dataset.dataset_versions), "dataset_versions")
        if request.artifact_bundle.trace_id is not None:
            _require_bound("artifact bundle", request.artifact_bundle.trace_id, request.trace_id, "trace_id")

        engine = request.engine_evidence
        _require_bound("engine evidence", str(engine.get("spec_id")), request.spec.spec_id, "spec_id")
        _require_bound("engine evidence", str(engine.get("spec_hash")), request.spec.spec_hash, "spec_hash")
        engine_scope = str(engine.get("engine_scope", ""))
        if engine_scope in {"", "legacy_signal_evaluation"}:
            raise BacktestRunOrchestratorError("engine evidence cannot be legacy Signal Evaluation")
        trace = engine.get("trace")
        if not isinstance(trace, Mapping):
            raise BacktestRunOrchestratorError("engine evidence trace must be a mapping")
        _require_bound("engine evidence", str(trace.get("run_id")), request.run_id, "run_id")
        _require_bound("engine evidence", str(trace.get("trace_id")), request.trace_id, "trace_id")

    @staticmethod
    def _validate_promotion_guards(request: BacktestRunRequest, effective_mode: BacktestRunMode) -> bool:
        if request.risk_result.status is RiskDecisionStatus.BLOCK:
            raise BacktestRunOrchestratorError("formal BacktestRun cannot finalize with risk policy block")
        if request.audit_report.status is BacktestBiasAuditStatus.INVALID:
            raise BacktestRunOrchestratorError("formal BacktestRun cannot finalize with invalid bias audit")
        if effective_mode is BacktestRunMode.FORMAL and request.artifact_bundle.state is not BacktestArtifactState.FORMAL:
            raise BacktestRunOrchestratorError("formal BacktestRun requires formal BacktestArtifactBundle state")
        return (
            effective_mode is BacktestRunMode.FORMAL
            and request.audit_report.eligible_for_ranking
            and request.artifact_bundle.state is BacktestArtifactState.FORMAL
        )

    def _build_record(
        self,
        *,
        request: BacktestRunRequest,
        effective_mode: BacktestRunMode,
        warning_codes: Sequence[str],
        request_hash: str,
        reuse_key: str,
        eligible_for_ranking: bool,
    ) -> BacktestRunRecord:
        run = Run.start(
            run_id=request.run_id,
            run_type=BACKTEST_RUN_TYPE,
            idempotency_key=request.idempotency_key,
            started_at=request.submitted_at,
        )
        stages: list[BacktestRunStageRecord] = []

        def complete_stage(name: str, stage_id: str, *, artifacts: Sequence[str] = (), outputs: Sequence[str] = ()) -> None:
            started = run.start_stage(stage_id=stage_id, name=name, started_at=request.submitted_at)
            run.record_stage_event(stage_id, EventKind.INFO, message=f"{name} validated", occurred_at=request.submitted_at)
            completed = run.complete_stage(stage_id, completed_at=request.submitted_at)
            stages.append(
                BacktestRunStageRecord(
                    stage_id=completed.stage_id,
                    name=completed.name,
                    status=completed.status.value,
                    started_at=started.started_at,
                    completed_at=completed.completed_at or request.submitted_at,
                    artifact_ids=artifacts,
                    output_ids=outputs,
                )
            )

        complete_stage("spec", "stage-spec", outputs=(request.spec.spec_hash,))
        complete_stage(
            "engine",
            str(request.engine_evidence.get("trace", {}).get("stage_id", "stage-engine")),
            artifacts=tuple(str(value) for value in request.engine_evidence.get("step_artifact_ids", ())),
            outputs=(str(request.engine_evidence.get("report_id", "engine_evidence")),),
        )
        complete_stage("ledger", request.ledger.stage_id, outputs=(request.ledger.events[-1].event_id if request.ledger.events else request.ledger.spec_hash,))
        complete_stage("risk", request.risk_result.stage_id, outputs=(request.risk_result.result_id,))
        complete_stage("audit", request.audit_report.stage_id, outputs=(request.audit_report.report_id,))
        complete_stage("metrics", request.metrics_report.stage_id, outputs=(request.metrics_report.report_id,))
        complete_stage(
            "artifacts",
            request.artifact_bundle.stage_id or "stage-artifacts",
            artifacts=tuple(output.artifact_id for output in request.artifact_bundle.outputs.values()),
            outputs=(request.artifact_bundle.bundle_id,),
        )

        summary_payload = self._summary_payload(
            request=request,
            effective_mode=effective_mode,
            warning_codes=tuple(warning_codes),
            request_hash=request_hash,
            reuse_key=reuse_key,
            eligible_for_ranking=eligible_for_ranking,
            stages=tuple(stages),
            lifecycle=_lifecycle_record(run),
        )
        summary_artifact = self._artifact_store.put_bytes(
            _canonical_json_bytes(summary_payload),
            schema_name=BACKTEST_RUN_SCHEMA_NAME,
            schema_version=BACKTEST_RUN_SCHEMA_VERSION,
            content_type=BACKTEST_RUN_SUMMARY_CONTENT_TYPE,
            produced_by_run_id=request.run_id,
            produced_by_stage_id="stage-summary",
            retention_tier=ArtifactRetentionTier.STANDARD,
            created_at=request.submitted_at,
        )
        complete_stage("summary", "stage-summary", artifacts=(summary_artifact.artifact_id,), outputs=(request.run_id,))
        run.complete(completed_at=request.submitted_at)

        return BacktestRunRecord(
            run_id=request.run_id,
            trace_id=request.trace_id,
            idempotency_key=request.idempotency_key,
            request_hash=request_hash,
            reuse_key=reuse_key,
            status=BacktestRunStatus.SUCCEEDED,
            requested_mode=request.requested_mode,
            effective_mode=effective_mode,
            code_state=request.code_state,
            patch_hash=request.patch_hash,
            spec_id=request.spec.spec_id,
            spec_hash=request.spec.spec_hash,
            dataset_versions=request.spec.dataset.dataset_versions,
            dataset_hashes=request.spec.dataset.dataset_hashes,
            engine_version=request.engine_version,
            engine_evidence=request.engine_evidence,
            lifecycle=_lifecycle_record(run),
            stages=tuple(stages),
            artifact_bundle=request.artifact_bundle,
            summary_artifact=summary_artifact,
            eligible_for_ranking=eligible_for_ranking,
            warning_codes=tuple(warning_codes),
            submitted_at=request.submitted_at,
            completed_at=request.submitted_at,
        )

    @staticmethod
    def _summary_payload(
        *,
        request: BacktestRunRequest,
        effective_mode: BacktestRunMode,
        warning_codes: Sequence[str],
        request_hash: str,
        reuse_key: str,
        eligible_for_ranking: bool,
        stages: Sequence[BacktestRunStageRecord],
        lifecycle: Mapping[str, Any],
    ) -> dict[str, object]:
        return {
            "contract_version": BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION,
            "schema_name": BACKTEST_RUN_SCHEMA_NAME,
            "schema_version": BACKTEST_RUN_SCHEMA_VERSION,
            "orchestrator_version": BACKTEST_RUN_ORCHESTRATOR_VERSION,
            "run_id": request.run_id,
            "trace_id": request.trace_id,
            "idempotency_key": request.idempotency_key,
            "request_hash": request_hash,
            "reuse_key": reuse_key,
            "status": BacktestRunStatus.SUCCEEDED.value,
            "requested_mode": request.requested_mode.value,
            "effective_mode": effective_mode.value,
            "code_state": request.code_state.value,
            "patch_hash": request.patch_hash,
            "eligible_for_ranking": eligible_for_ranking,
            "warning_codes": list(warning_codes),
            "submitted_at": request.submitted_at.isoformat(),
            "completed_at": request.submitted_at.isoformat(),
            "spec": {
                "spec_id": request.spec.spec_id,
                "spec_hash": request.spec.spec_hash,
                "dataset_versions": dict(request.spec.dataset.dataset_versions),
                "dataset_hashes": dict(request.spec.dataset.dataset_hashes),
            },
            "engine_evidence": _compact_engine_evidence(request.engine_evidence),
            "layer_outputs": {
                "ledger": {
                    "stage_id": request.ledger.stage_id,
                    "event_count": len(request.ledger.events),
                    "equity": _json_ready(request.ledger.equity),
                },
                "risk": {
                    "result_id": request.risk_result.result_id,
                    "status": request.risk_result.status.value,
                    "blocking_rule_ids": list(request.risk_result.blocking_rule_ids),
                    "warning_rule_ids": list(request.risk_result.warning_rule_ids),
                },
                "audit": {
                    "report_id": request.audit_report.report_id,
                    "status": request.audit_report.status.value,
                    "eligible_for_ranking": request.audit_report.eligible_for_ranking,
                    "hard_failure_rule_ids": list(request.audit_report.hard_failure_rule_ids),
                    "warning_rule_ids": list(request.audit_report.warning_rule_ids),
                },
                "metrics": {
                    "report_id": request.metrics_report.report_id,
                    "metric_set_version": request.metrics_report.metric_set_version,
                    "sample_start": request.metrics_report.sample_start.isoformat(),
                    "sample_end": request.metrics_report.sample_end.isoformat(),
                },
            },
            "lifecycle": _thaw_value(lifecycle),
            "stages": [stage.to_record() for stage in stages],
            "outputs": {
                "artifact_bundle": {
                    "bundle_id": request.artifact_bundle.bundle_id,
                    "state": request.artifact_bundle.state.value,
                    "output_artifact_ids": [
                        output.artifact_id for output in request.artifact_bundle.outputs.values()
                    ],
                }
            },
            "runtime": _runtime_boundary_record(),
        }


def _compact_engine_evidence(engine_evidence: Mapping[str, Any]) -> dict[str, object]:
    return {
        "schema_name": str(engine_evidence.get("schema_name", "")),
        "schema_version": str(engine_evidence.get("schema_version", "")),
        "report_id": str(engine_evidence.get("report_id", "")),
        "engine_scope": str(engine_evidence.get("engine_scope", "")),
        "adapter_version": str(engine_evidence.get("adapter_version", "")),
        "spec_id": str(engine_evidence.get("spec_id", "")),
        "spec_hash": str(engine_evidence.get("spec_hash", "")),
        "operation_count": int(engine_evidence.get("operation_count", 0)),
        "operations": list(engine_evidence.get("operations", ())),
        "step_artifact_ids": list(engine_evidence.get("step_artifact_ids", ())),
        "trace": dict(engine_evidence.get("trace", {})) if isinstance(engine_evidence.get("trace"), Mapping) else {},
    }


def _lifecycle_record(run: Run) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "run_type": run.run_type,
        "idempotency_key": run.idempotency_key,
        "status": run.status.value,
        "attempt": run.attempt,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "failed_at": run.failed_at.isoformat() if run.failed_at else None,
        "failure_reason": run.failure_reason,
        "stages": [_stage_record(stage) for stage in run.stages],
        "events": [_event_record(event) for event in run.events],
    }


def _stage_record(stage: Stage) -> dict[str, object]:
    return {
        "stage_id": stage.stage_id,
        "name": stage.name,
        "status": stage.status.value,
        "attempt": stage.attempt,
        "started_at": stage.started_at.isoformat(),
        "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
        "failed_at": stage.failed_at.isoformat() if stage.failed_at else None,
        "failure_reason": stage.failure_reason,
    }


def _event_record(event: RunEvent) -> dict[str, object]:
    return {
        "run_id": event.run_id,
        "sequence": event.sequence,
        "kind": event.kind.value,
        "occurred_at": event.occurred_at.isoformat(),
        "message": event.message,
        "stage_id": event.stage_id,
    }


def _runtime_boundary_record() -> dict[str, bool]:
    return {
        "resource_controls_started": False,
        "api_route_started": False,
        "quant_lab_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
    }


def _require_bound(label: str, observed: object, expected: object, field_name: str) -> None:
    if observed != expected:
        raise BacktestRunOrchestratorError(f"{label} {field_name} must match BacktestSpec/run context")


def _sha256_record(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(record)).hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(_json_ready(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BacktestRunOrchestratorError("mapping value must be a Mapping")
    return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return _json_ready(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


def _string_mapping(field_name: str, value: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise BacktestRunOrchestratorError(f"{field_name} must be a mapping")
    return MappingProxyType({
        _required_string(f"{field_name}.key", str(key)): _required_string(f"{field_name}.{key}", str(item))
        for key, item in value.items()
    })


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_required_string(field_name, str(value)) for value in values)


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return value if isinstance(value, enum_type) else enum_type(str(value))
    except ValueError as exc:
        raise BacktestRunOrchestratorError(f"{field_name} has invalid value: {value}") from exc


def _validate_sha256(field_name: str, value: object) -> str:
    text = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(text):
        raise BacktestRunOrchestratorError(f"{field_name} must be sha256:<64 hex>")
    return text


def _optional_sha256(field_name: str, value: object | None) -> str | None:
    if value is None:
        return None
    return _validate_sha256(field_name, value)


def _required_string(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BacktestRunOrchestratorError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    return _required_string("value", value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestRunOrchestratorError(f"{field_name} must be a timezone-aware datetime")


__all__ = [
    "BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION",
    "BACKTEST_RUN_ORCHESTRATOR_VERSION",
    "BACKTEST_RUN_SCHEMA_NAME",
    "BACKTEST_RUN_SCHEMA_VERSION",
    "BACKTEST_RUN_SUMMARY_CONTENT_TYPE",
    "BACKTEST_RUN_TYPE",
    "BacktestRunCodeState",
    "BacktestRunMode",
    "BacktestRunOrchestrator",
    "BacktestRunOrchestratorError",
    "BacktestRunRecord",
    "BacktestRunRequest",
    "BacktestRunStageRecord",
    "BacktestRunStatus",
    "InMemoryBacktestRunRepository",
]
