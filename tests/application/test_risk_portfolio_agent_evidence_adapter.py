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
from serenity_alpha_lab.application.risk_portfolio_agent import (
    EvidenceScopedRiskPortfolioAgent,
    RiskPortfolioAction,
    RiskPortfolioAgentError,
    RiskPortfolioAgentPromptRequest,
    RiskPortfolioGateStatus,
    RiskPortfolioStructuredOutput,
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


NOW = datetime(2026, 7, 28, 9, 30, tzinfo=UTC)
DATASET_VERSIONS = {
    "backtest_artifact": "dsv_" + "1" * 32,
    "adjusted_daily_bars": "dsv_" + "2" * 32,
}
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64


def test_prepare_prompt_payload_preserves_hard_gate_and_forbids_overrides() -> None:
    bundle = _risk_portfolio_bundle()
    binding = _risk_portfolio_binding()

    payload = EvidenceScopedRiskPortfolioAgent().prepare_prompt_payload(
        RiskPortfolioAgentPromptRequest(
            run_id="run-risk-portfolio",
            stage_id="stage-risk-portfolio",
            bundle=bundle,
            prompt_binding=binding,
        )
    )

    record = payload.to_record()
    serialized = json.dumps(record, sort_keys=True)
    assert record["schema_name"] == "research.agent.risk_portfolio_prompt_payload"
    assert record["run_id"] == "run-risk-portfolio"
    assert record["stage_id"] == "stage-risk-portfolio"
    assert record["bundle"]["role"] == "risk_portfolio"
    assert record["prompt_binding"]["prompt"]["prompt_id"] == "risk_portfolio_research"
    assert record["allowed_evidence_ids"] == ["ev_risk_block", "ev_metrics"]
    assert record["hard_gate_summary"]["status"] == "block"
    assert record["hard_gate_summary"]["blocking_evidence_ids"] == ["ev_risk_block"]
    assert record["hard_gate_summary"]["not_evaluable_rule_ids"] == []
    assert "override_risk_policy" in record["forbidden_actions"]
    assert "execute_backtest_task" not in serialized
    assert "place_order" not in serialized
    assert "initialize_qlib_runtime" in record["forbidden_actions"]


def test_prepare_prompt_payload_rejects_non_formal_or_recomputable_evidence() -> None:
    screen_bundle = _risk_portfolio_bundle(
        items=(
            _evidence(
                "ev_screen",
                EvidenceKind.SCREEN_SNAPSHOT,
                EvidenceEvaluationScope.SCREENING,
                content_hash=HASH_A,
            ),
        )
    )

    with pytest.raises(RiskPortfolioAgentError, match="evidence allowlist"):
        EvidenceScopedRiskPortfolioAgent().prepare_prompt_payload(
            RiskPortfolioAgentPromptRequest(
                run_id="run-risk-portfolio",
                stage_id="stage-risk-portfolio",
                bundle=screen_bundle,
                prompt_binding=_risk_portfolio_binding(),
            )
        )

    recomputable_risk = _risk_portfolio_bundle(
        items=(
            _evidence(
                "ev_recomputable",
                EvidenceKind.RISK_POLICY_RESULT,
                EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
                content_hash=HASH_B,
                metadata={"llm_recompute_allowed": True, "risk_status": "pass"},
            ),
        )
    )
    with pytest.raises(RiskPortfolioAgentError, match="disallow LLM recompute"):
        EvidenceScopedRiskPortfolioAgent().prepare_prompt_payload(
            RiskPortfolioAgentPromptRequest(
                run_id="run-risk-portfolio",
                stage_id="stage-risk-portfolio",
                bundle=recomputable_risk,
                prompt_binding=_risk_portfolio_binding(),
            )
        )


def test_finalize_output_preserves_block_and_not_evaluable_hard_gates() -> None:
    block_payload = _payload(_risk_portfolio_bundle())
    citation = _citation("cit_risk_status", "ev_risk_block", cited_value="block")
    claim = _risk_gate_claim("cl_risk_block", "cit_risk_status", value="block")

    upgraded_block = _structured_output(
        gate_status=RiskPortfolioGateStatus.PASS,
        portfolio_action=RiskPortfolioAction.ELIGIBLE,
        claims=(claim,),
        citations=(citation,),
    )
    with pytest.raises(RiskPortfolioAgentError, match="cannot upgrade hard gate"):
        EvidenceScopedRiskPortfolioAgent().finalize_output(block_payload, upgraded_block)

    not_evaluable_payload = _payload(
        _risk_portfolio_bundle(
            items=(
                _evidence(
                    "ev_risk_ne",
                    EvidenceKind.RISK_POLICY_RESULT,
                    EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
                    content_hash=HASH_A,
                    metadata={
                        "risk_status": "pass",
                        "not_evaluable_rule_ids": ["liquidity_profile"],
                    },
                ),
            )
        )
    )
    not_evaluable_claim = _risk_gate_claim("cl_risk_ne", "cit_risk_ne", value="not_evaluable")
    not_evaluable_citation = _citation("cit_risk_ne", "ev_risk_ne", cited_value="not_evaluable")

    with pytest.raises(RiskPortfolioAgentError, match="cannot upgrade hard gate"):
        EvidenceScopedRiskPortfolioAgent().finalize_output(
            not_evaluable_payload,
            _structured_output(
                gate_status=RiskPortfolioGateStatus.PASS,
                portfolio_action=RiskPortfolioAction.ELIGIBLE,
                claims=(not_evaluable_claim,),
                citations=(not_evaluable_citation,),
            ),
        )

    result = EvidenceScopedRiskPortfolioAgent().finalize_output(
        not_evaluable_payload,
        _structured_output(
            gate_status=RiskPortfolioGateStatus.NOT_EVALUABLE,
            portfolio_action=RiskPortfolioAction.INSUFFICIENT_EVIDENCE,
            claims=(not_evaluable_claim,),
            citations=(not_evaluable_citation,),
        ),
    )
    assert result.to_dsa_dashboard_fields()["hard_gates"]["status"] == "not_evaluable"


def test_finalize_output_requires_current_bundle_citations_and_numeric_consistency() -> None:
    payload = _payload(_risk_portfolio_bundle())
    numeric_claim = _numeric_claim("cl_sharpe", "cit_sharpe")
    numeric_citation = _citation("cit_sharpe", "ev_metrics", cited_value=1.23, unit="ratio")

    result = EvidenceScopedRiskPortfolioAgent().finalize_output(
        payload,
        _structured_output(
            gate_status=RiskPortfolioGateStatus.BLOCK,
            portfolio_action=RiskPortfolioAction.AVOID,
            claims=(
                _risk_gate_claim("cl_block", "cit_risk_status", value="block"),
                numeric_claim,
            ),
            citations=(_citation("cit_risk_status", "ev_risk_block", cited_value="block"), numeric_citation),
        ),
    )

    opinion = result.to_dsa_compatible_opinion()
    dashboard = result.to_dsa_dashboard_fields()
    assert opinion["agent_name"] == "risk_portfolio"
    assert opinion["risk_status"] == "block"
    assert opinion["portfolio_action"] == "avoid"
    assert opinion["raw_data"]["claims"][1]["claim_id"] == "cl_sharpe"
    assert dashboard["risk_status"] == "block"
    assert dashboard["portfolio_constraints"] == ["Do not promote ranking while hard gate is block."]
    assert dashboard["citations"][1]["evidence_id"] == "ev_metrics"

    with pytest.raises(RiskPortfolioAgentError, match="not included in the EvidenceBundle"):
        EvidenceScopedRiskPortfolioAgent().finalize_output(
            payload,
            _structured_output(
                gate_status=RiskPortfolioGateStatus.BLOCK,
                portfolio_action=RiskPortfolioAction.AVOID,
                claims=(_numeric_claim("cl_unknown", "cit_unknown"),),
                citations=(_citation("cit_unknown", "ev_unknown", cited_value=1.23, unit="ratio"),),
            ),
        )

    with pytest.raises(RiskPortfolioAgentError, match="unit mismatch"):
        EvidenceScopedRiskPortfolioAgent().finalize_output(
            payload,
            _structured_output(
                gate_status=RiskPortfolioGateStatus.BLOCK,
                portfolio_action=RiskPortfolioAction.AVOID,
                claims=(_numeric_claim("cl_unit_mismatch", "cit_sharpe", unit="percent"),),
                citations=(numeric_citation,),
            ),
        )


def _payload(bundle: EvidenceBundle):
    return EvidenceScopedRiskPortfolioAgent().prepare_prompt_payload(
        RiskPortfolioAgentPromptRequest(
            run_id="run-risk-portfolio",
            stage_id="stage-risk-portfolio",
            bundle=bundle,
            prompt_binding=_risk_portfolio_binding(),
        )
    )


def _risk_portfolio_binding() -> PromptRunBinding:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.RISK_PORTFOLIO)
    return registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-risk-portfolio",
            stage_id="stage-risk-portfolio",
            trace_id="trace-risk-portfolio",
            role=AgentPromptRole.RISK_PORTFOLIO,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )


def _risk_portfolio_bundle(items: tuple[EvidenceRecord, ...] | None = None) -> EvidenceBundle:
    records = items or (
        _evidence(
            "ev_risk_block",
            EvidenceKind.RISK_POLICY_RESULT,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            content_hash=HASH_A,
            metadata={"risk_status": "block", "blocking_rule_ids": ["max_drawdown"]},
        ),
        _evidence(
            "ev_metrics",
            EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            content_hash=HASH_B,
            metadata={"metric_set_version": "backtest_performance_metrics@1.0.0"},
        ),
    )
    return EvidenceBundle(
        bundle_id="bundle-risk-portfolio",
        request=EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id="600519.XSHG",
            decision_time=NOW,
            role=EvidenceBundleRole.RISK_PORTFOLIO,
            budget=EvidenceBundleBudget(max_prompt_tokens=2048),
        ),
        schema_instructions=EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS,
        status=EvidenceBundleStatus.COMPLETE,
        items=tuple(
            EvidenceBundleItem(
                evidence=record,
                priority_score=100 - index,
                priority_reasons=("test_fixture",),
                estimated_tokens=40,
            )
            for index, record in enumerate(records)
        ),
        excluded_items=tuple[EvidenceBundleExcludedItem, ...](),
        estimated_tokens=160,
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
        summary=f"{kind.value} deterministic formal portfolio evidence.",
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
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_id=f"art_{evidence_id}",
        artifact_hash=content_hash,
        formula_versions={"risk_evaluator": "cn_a_share_deterministic_risk_policy@1.0.0"},
        metadata={"llm_recompute_allowed": False, **(metadata or {})},
    )


def _source_schema(kind: EvidenceKind) -> str:
    return {
        EvidenceKind.RISK_POLICY_RESULT: "quant.backtest.risk_policy",
        EvidenceKind.BACKTEST_BIAS_AUDIT: "quant.backtest.bias_audit",
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: "quant.backtest.performance_metrics",
        EvidenceKind.BACKTEST_RUN_SUMMARY: "quant.backtest_run",
        EvidenceKind.BACKTEST_ARTIFACT_BUNDLE: "quant.backtest_artifact_bundle",
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: "application.formal_backtest_api",
        EvidenceKind.SCREEN_SNAPSHOT: "quant.screen_snapshot",
    }[kind]


def _citation(
    citation_id: str,
    evidence_id: str,
    *,
    cited_value: object,
    unit: str | None = None,
    formula_version: str = "cn_a_share_deterministic_risk_policy@1.0.0",
) -> ReportCitation:
    artifact_hash = HASH_B if evidence_id == "ev_metrics" else HASH_A
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence_id,
        evidence_field_path="body.status" if unit is None else "body.risk.sharpe_ratio",
        cited_value=cited_value,
        unit=unit,
        formula_version=formula_version,
        dataset_versions=DATASET_VERSIONS,
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_hash=artifact_hash,
    )


def _risk_gate_claim(claim_id: str, citation_id: str, *, value: str) -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.RISK_GATE,
        statement=f"Deterministic risk gate status is {value}.",
        verification_status=ClaimVerificationStatus.BLOCKED if value == "block" else ClaimVerificationStatus.PARTIAL,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=value,
        formula_version="cn_a_share_deterministic_risk_policy@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_hash=HASH_A,
    )


def _numeric_claim(
    claim_id: str,
    citation_id: str,
    *,
    value: float = 1.23,
    unit: str = "ratio",
) -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The cited formal backtest Sharpe ratio is 1.23.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=value,
        unit=unit,
        formula_version="cn_a_share_deterministic_risk_policy@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_hash=HASH_B,
    )


def _structured_output(
    *,
    gate_status: RiskPortfolioGateStatus,
    portfolio_action: RiskPortfolioAction,
    claims: tuple[ResearchClaim, ...],
    citations: tuple[ReportCitation, ...],
) -> RiskPortfolioStructuredOutput:
    return RiskPortfolioStructuredOutput(
        gate_status=gate_status,
        portfolio_action=portfolio_action,
        confidence=0.68,
        summary="Risk policy result blocks promotion; portfolio context should remain defensive.",
        claims=claims,
        citations=citations,
        risk_factors=("Drawdown threshold breached.",),
        portfolio_constraints=("Do not promote ranking while hard gate is block.",),
        warnings=("No risk rule was recomputed by this adapter.",),
        limitations=("Only cited formal backtest evidence is available.",),
    )
