from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.evidence_bundle_builder import (
    EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS,
    EvidenceBundle,
    EvidenceBundleBudget,
    EvidenceBundleExcludedItem,
    EvidenceBundleItem,
    EvidenceBundleRequest,
    EvidenceBundleRole,
    EvidenceBundleStatus,
)
from serenity_alpha_lab.application.technical_agent import (
    EvidenceScopedTechnicalAgent,
    TechnicalAgentError,
    TechnicalAgentPromptRequest,
    TechnicalAgentStructuredOutput,
    TechnicalSignal,
    TechnicalTrendAlignment,
    TechnicalVolumeStatus,
)
from serenity_alpha_lab.evidence.prompt_registry import (
    AgentPromptRole,
    PromptRunBinding,
    PromptRunBindingRequest,
    default_prompt_schema_registry,
)
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
    ReportCitation,
    ResearchClaim,
)


NOW = datetime(2026, 7, 27, 9, 30, tzinfo=UTC)
DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "1" * 32,
    "factor_values": "dsv_" + "2" * 32,
}
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64


def test_prepare_prompt_payload_uses_technical_prompt_and_no_dsa_tools() -> None:
    bundle = _technical_bundle()
    binding = _technical_binding()

    payload = EvidenceScopedTechnicalAgent().prepare_prompt_payload(
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            bundle=bundle,
            prompt_binding=binding,
        )
    )

    record = payload.to_record()
    serialized = json.dumps(record, sort_keys=True)
    assert record["schema_name"] == "research.agent.technical_prompt_payload"
    assert record["run_id"] == "run-technical"
    assert record["stage_id"] == "stage-technical"
    assert record["bundle"]["bundle_id"] == "bundle-technical"
    assert record["prompt_binding"]["prompt"]["prompt_id"] == "technical_research"
    assert record["allowed_evidence_ids"] == ["ev_screen", "ev_factor"]
    assert record["allowed_evidence_hashes"] == [HASH_A, HASH_B]
    assert "recompute_technical_indicators" in record["forbidden_actions"]
    assert "get_daily_history" not in serialized
    assert "calculate_ma" not in serialized
    assert "get_realtime_quote" not in serialized


def test_prepare_prompt_payload_rejects_formal_backtest_evidence_for_technical_agent() -> None:
    formal_bundle = _technical_bundle(
        items=(
            _evidence(
                "ev_backtest",
                EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
                EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
                content_hash=HASH_A,
            ),
        )
    )

    with pytest.raises(TechnicalAgentError, match="Technical Agent evidence allowlist"):
        EvidenceScopedTechnicalAgent().prepare_prompt_payload(
            TechnicalAgentPromptRequest(
                run_id="run-technical",
                stage_id="stage-technical",
                bundle=formal_bundle,
                prompt_binding=_technical_binding(),
            )
        )


def test_prepare_prompt_payload_rejects_wrong_scope_or_llm_recompute_evidence() -> None:
    api_lineage_factor = _technical_bundle(
        items=(
            _evidence(
                "ev_factor_api_lineage",
                EvidenceKind.FACTOR_EVALUATION,
                EvidenceEvaluationScope.API_LINEAGE,
                content_hash=HASH_A,
            ),
        )
    )
    with pytest.raises(TechnicalAgentError, match="evidence scope"):
        EvidenceScopedTechnicalAgent().prepare_prompt_payload(
            TechnicalAgentPromptRequest(
                run_id="run-technical",
                stage_id="stage-technical",
                bundle=api_lineage_factor,
                prompt_binding=_technical_binding(),
            )
        )

    recomputable_screen = _technical_bundle(
        items=(
            _evidence(
                "ev_recomputable",
                EvidenceKind.SCREEN_SNAPSHOT,
                EvidenceEvaluationScope.SCREENING,
                content_hash=HASH_B,
                metadata={"llm_recompute_allowed": True},
            ),
        )
    )
    with pytest.raises(TechnicalAgentError, match="disallow LLM recompute"):
        EvidenceScopedTechnicalAgent().prepare_prompt_payload(
            TechnicalAgentPromptRequest(
                run_id="run-technical",
                stage_id="stage-technical",
                bundle=recomputable_screen,
                prompt_binding=_technical_binding(),
            )
        )


def test_prepare_prompt_payload_requires_matching_prompt_binding_stage_context() -> None:
    with pytest.raises(TechnicalAgentError, match="stage_id"):
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-other",
            bundle=_technical_bundle(),
            prompt_binding=_technical_binding(),
        )


def test_finalize_output_requires_cited_numeric_claims_from_current_bundle() -> None:
    payload = EvidenceScopedTechnicalAgent().prepare_prompt_payload(
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            bundle=_technical_bundle(),
            prompt_binding=_technical_binding(),
        )
    )
    citation = _citation("cit_factor_ic", "ev_factor")
    claim = _numeric_claim("cl_factor_ic", "cit_factor_ic")
    output = _structured_output(claims=(claim,), citations=(citation,))

    result = EvidenceScopedTechnicalAgent().finalize_output(payload, output)

    opinion = result.to_dsa_compatible_opinion()
    dashboard = result.to_dsa_dashboard_fields()
    assert opinion["agent_name"] == "technical"
    assert opinion["signal"] == "buy"
    assert opinion["confidence"] == 0.82
    assert opinion["key_levels"] == {"resistance": 1800.0, "stop_loss": 1550.0, "support": 1600.0}
    assert opinion["raw_data"]["claims"][0]["claim_id"] == "cl_factor_ic"
    assert opinion["raw_data"]["citations"][0]["evidence_id"] == "ev_factor"
    assert dashboard["technical_analysis"] == "Factor momentum remains positive with cited deterministic evidence."
    assert dashboard["ma_analysis"] == "bullish"
    assert dashboard["volume_analysis"] == "normal"
    assert dashboard["data_perspective"]["price_position"]["support_level"] == 1600.0
    assert dashboard["data_perspective"]["price_position"]["resistance_level"] == 1800.0
    assert dashboard["data_perspective"]["volume_analysis"] == {
        "volume_ratio": None,
        "volume_status": "normal",
        "turnover_rate": None,
        "volume_meaning": "Derived from cited technical evidence; no realtime volume recomputation was performed.",
    }
    assert dashboard["pattern_analysis"] == "MA breakout"
    assert dashboard["trend_status"] == {
        "ma_alignment": "bullish",
        "is_bullish": True,
        "trend_score": 82,
    }


def test_finalize_output_rejects_unknown_output_citation_or_bundle_evidence() -> None:
    payload = EvidenceScopedTechnicalAgent().prepare_prompt_payload(
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            bundle=_technical_bundle(),
            prompt_binding=_technical_binding(),
        )
    )
    claim = _numeric_claim("cl_missing_citation", "cit_missing")

    with pytest.raises(TechnicalAgentError, match="unknown citation_id"):
        EvidenceScopedTechnicalAgent().finalize_output(payload, _structured_output(claims=(claim,), citations=()))

    unknown_citation = _citation("cit_unknown", "ev_unknown")
    unknown_claim = _numeric_claim("cl_unknown_evidence", "cit_unknown")
    with pytest.raises(TechnicalAgentError, match="not included in the EvidenceBundle"):
        EvidenceScopedTechnicalAgent().finalize_output(
            payload,
            _structured_output(claims=(unknown_claim,), citations=(unknown_citation,)),
        )


def test_finalize_output_rejects_numeric_claim_citation_mismatches() -> None:
    payload = EvidenceScopedTechnicalAgent().prepare_prompt_payload(
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            bundle=_technical_bundle(),
            prompt_binding=_technical_binding(),
        )
    )

    mismatch_cases = (
        (
            _numeric_claim("cl_value_mismatch", "cit_factor_ic", value=0.41),
            _citation("cit_factor_ic", "ev_factor"),
            "cited_value",
        ),
        (
            _numeric_claim("cl_unit_mismatch", "cit_factor_ic", unit="ratio"),
            _citation("cit_factor_ic", "ev_factor"),
            "unit",
        ),
        (
            _numeric_claim("cl_formula_mismatch", "cit_factor_ic", formula_version="other_formula@1.0.0"),
            _citation("cit_factor_ic", "ev_factor"),
            "formula_version",
        ),
        (
            _numeric_claim("cl_dataset_mismatch", "cit_factor_ic", dataset_versions={"adjusted_daily_bars": "dsv_" + "3" * 32}),
            _citation("cit_factor_ic", "ev_factor"),
            "dataset_versions",
        ),
        (
            _numeric_claim("cl_artifact_mismatch", "cit_factor_ic", artifact_hash=HASH_A),
            _citation("cit_factor_ic", "ev_factor"),
            "artifact_hash",
        ),
        (
            _numeric_claim("cl_missing_citation_artifact", "cit_factor_ic"),
            _citation("cit_factor_ic", "ev_factor", artifact_hash=None),
            "artifact_hash",
        ),
    )

    for claim, citation, message in mismatch_cases:
        with pytest.raises(TechnicalAgentError, match=message):
            EvidenceScopedTechnicalAgent().finalize_output(
                payload,
                _structured_output(claims=(claim,), citations=(citation,)),
            )


def _technical_binding() -> PromptRunBinding:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.TECHNICAL)
    return registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            trace_id="trace-technical",
            role=AgentPromptRole.TECHNICAL,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )


def _technical_bundle(items: tuple[EvidenceRecord, ...] | None = None) -> EvidenceBundle:
    records = items or (
        _evidence("ev_screen", EvidenceKind.SCREEN_SNAPSHOT, EvidenceEvaluationScope.SCREENING, content_hash=HASH_A),
        _evidence("ev_factor", EvidenceKind.FACTOR_EVALUATION, EvidenceEvaluationScope.FACTOR_EVALUATION, content_hash=HASH_B),
    )
    return EvidenceBundle(
        bundle_id="bundle-technical",
        request=EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id="600519.XSHG",
            decision_time=NOW,
            role=EvidenceBundleRole.TECHNICAL,
            budget=EvidenceBundleBudget(max_prompt_tokens=2048),
        ),
        schema_instructions=EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS,
        status=EvidenceBundleStatus.COMPLETE,
        items=tuple(
            EvidenceBundleItem(
                evidence=record,
                priority_score=100 - index,
                priority_reasons=("test_fixture",),
                estimated_tokens=30,
            )
            for index, record in enumerate(records)
        ),
        excluded_items=tuple[EvidenceBundleExcludedItem, ...](),
        estimated_tokens=120,
        schema_instruction_tokens=60,
    )


def _evidence(
    evidence_id: str,
    kind: EvidenceKind,
    scope: EvidenceEvaluationScope,
    *,
    content_hash: str,
    metadata: dict[str, object] | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=kind,
        evaluation_scope=scope,
        title=f"{kind.value} evidence",
        summary=f"{kind.value} deterministic technical evidence.",
        source=EvidenceSource(
            source_id=f"src_{evidence_id}",
            source_type="artifact",
            schema_name=_source_schema(kind),
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=content_hash,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=DATASET_VERSIONS,
        instrument_id="600519.XSHG",
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_id=f"art_{evidence_id}",
        artifact_hash=content_hash,
        formula_versions={"metric_set": "factor_evaluation_metrics@1.0.0"},
        metadata={"llm_recompute_allowed": False, **(metadata or {})},
    )


def _source_schema(kind: EvidenceKind) -> str:
    return {
        EvidenceKind.SCREEN_SNAPSHOT: "quant.screen_snapshot",
        EvidenceKind.SCREEN_PIPELINE_SNAPSHOT: "quant.screen_pipeline_snapshot",
        EvidenceKind.FACTOR_EVALUATION: "quant.factor_evaluation",
        EvidenceKind.FACTOR_CACHE_MANIFEST: "quant.factor_cache_manifest",
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: "quant.backtest.performance_metrics",
    }[kind]


def _citation(citation_id: str, evidence_id: str, *, artifact_hash: str | None = HASH_B) -> ReportCitation:
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence_id,
        evidence_field_path="body.ic_summary.mean_ic",
        cited_value=0.42,
        unit="correlation",
        formula_version="factor_evaluation_metrics@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_hash=artifact_hash,
    )


def _numeric_claim(
    claim_id: str,
    citation_id: str,
    *,
    value: float = 0.42,
    unit: str = "correlation",
    formula_version: str = "factor_evaluation_metrics@1.0.0",
    dataset_versions: dict[str, str] | None = None,
    artifact_hash: str | None = HASH_B,
) -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The factor mean IC is positive at 0.42.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=value,
        unit=unit,
        formula_version=formula_version,
        dataset_versions=dataset_versions or DATASET_VERSIONS,
        run_id="run-technical",
        stage_id="stage-technical",
        artifact_hash=artifact_hash,
    )


def _structured_output(
    *,
    claims: tuple[ResearchClaim, ...],
    citations: tuple[ReportCitation, ...],
) -> TechnicalAgentStructuredOutput:
    return TechnicalAgentStructuredOutput(
        signal=TechnicalSignal.BUY,
        confidence=0.82,
        reasoning="Factor momentum remains positive with cited deterministic evidence.",
        claims=claims,
        citations=citations,
        key_levels={"support": 1600.0, "resistance": 1800.0, "stop_loss": 1550.0},
        trend_score=82,
        ma_alignment=TechnicalTrendAlignment.BULLISH,
        volume_status=TechnicalVolumeStatus.NORMAL,
        pattern="MA breakout",
        warnings=("No realtime quote was fetched by this adapter.",),
        limitations=(),
    )
