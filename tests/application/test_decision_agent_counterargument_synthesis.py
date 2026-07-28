from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.application.decision_agent import (
    DecisionAgentError,
    DecisionAgentPromptRequest,
    DecisionCase,
    DecisionCaseSide,
    DecisionConfidenceLevel,
    DecisionDisagreementSummary,
    DecisionInvalidationCondition,
    DecisionRecommendation,
    DecisionStructuredOutput,
    EvidenceScopedDecisionAgent,
)
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
from serenity_alpha_lab.application.intel_agent import (
    EvidenceScopedIntelAgent,
    IntelAgentPromptRequest,
    IntelAgentStructuredEvent,
    IntelAgentStructuredOutput,
    IntelEventImpact,
    IntelEventStrength,
    IntelFreshnessStatus,
    IntelSentiment,
)
from serenity_alpha_lab.application.risk_portfolio_agent import (
    EvidenceScopedRiskPortfolioAgent,
    RiskPortfolioAction,
    RiskPortfolioAgentPromptRequest,
    RiskPortfolioGateStatus,
    RiskPortfolioStructuredOutput,
)
from serenity_alpha_lab.application.technical_agent import (
    EvidenceScopedTechnicalAgent,
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
from serenity_alpha_lab.evidence.source_trust import (
    SourceTrustPolicy,
    UnstructuredSourceInput,
    UnstructuredSourceType,
)


NOW = datetime(2026, 7, 28, 9, 30, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64
HASH_D = "sha256:" + "d" * 64
TECH_DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "1" * 32,
    "factor_values": "dsv_" + "2" * 32,
}
INTEL_DATASET_VERSIONS = {"intel_corpus": "dsv_" + "7" * 32}
RISK_DATASET_VERSIONS = {
    "backtest_artifact": "dsv_" + "3" * 32,
    "adjusted_daily_bars": "dsv_" + "4" * 32,
}


def test_prepare_prompt_payload_combines_prior_roles_and_forbids_runtime_actions() -> None:
    payload = EvidenceScopedDecisionAgent().prepare_prompt_payload(
        DecisionAgentPromptRequest(
            run_id="run-decision",
            stage_id="stage-decision",
            bundle=_decision_bundle(),
            prompt_binding=_decision_binding(),
            technical_result=_technical_result(),
            intel_result=_intel_result(),
            risk_portfolio_result=_risk_portfolio_result(),
        )
    )

    record = payload.to_record()
    serialized = json.dumps(record, sort_keys=True)
    assert record["schema_name"] == "research.agent.decision_prompt_payload"
    assert record["run_id"] == "run-decision"
    assert record["stage_id"] == "stage-decision"
    assert record["bundle"]["role"] == "decision"
    assert record["prompt_binding"]["prompt"]["prompt_id"] == "decision_research"
    assert record["allowed_evidence_ids"] == ["ev_factor", "ev_official", "ev_risk_block"]
    assert set(record["role_result_hashes"]) == {"technical", "intel", "risk_portfolio"}
    assert record["role_result_hashes"]["technical"].startswith("sha256:")
    assert record["role_citation_evidence_ids"]["technical"] == ["ev_factor"]
    assert record["role_citation_evidence_ids"]["intel"] == ["ev_official"]
    assert record["risk_gate_summary"]["status"] == "block"
    assert "call_real_llm" in record["forbidden_actions"]
    assert "render_report" in record["forbidden_actions"]
    assert "execute_backtest_task" in record["forbidden_actions"]
    assert "get_realtime_quote" not in serialized


def test_finalize_output_requires_distinct_bull_bear_and_current_evidence_citations() -> None:
    payload = _decision_payload()
    output = _decision_output()

    result = EvidenceScopedDecisionAgent().finalize_output(payload, output)

    opinion = result.to_dsa_compatible_opinion()
    dashboard = result.to_dsa_dashboard_fields()
    assert opinion["agent_name"] == "decision"
    assert opinion["signal"] == "negative"
    assert opinion["recommendation"] == "blocked"
    assert opinion["confidence_level"] == "medium"
    assert opinion["raw_data"]["bull_case"]["citation_ids"] == ["cit_dec_factor", "cit_dec_official"]
    assert dashboard["final_decision"] == "blocked"
    assert dashboard["risk_gate"]["status"] == "block"
    assert dashboard["ranking_eligible"] is False
    assert dashboard["bull_case"]["thesis"] != dashboard["bear_case"]["thesis"]
    assert dashboard["invalidation_conditions"][0]["citation_ids"] == ["cit_dec_risk"]

    new_fact_citation = _decision_citation("cit_new_fact", _technical_evidence("ev_screen", HASH_D))
    with pytest.raises(DecisionAgentError, match="not cited by prior role outputs"):
        EvidenceScopedDecisionAgent().finalize_output(
            payload,
            _decision_output(
                bull_case=_case(
                    side=DecisionCaseSide.BULL,
                    citation_ids=("cit_new_fact",),
                    thesis="A new unreviewed technical fact is bullish.",
                ),
                citations=(*output.citations, new_fact_citation),
            ),
        )

    with pytest.raises(DecisionAgentError, match="Bull and bear cases must be distinct"):
        EvidenceScopedDecisionAgent().finalize_output(
            payload,
            _decision_output(
                bull_case=_case(side=DecisionCaseSide.BULL, citation_ids=("cit_dec_factor",), thesis="Same thesis"),
                bear_case=_case(side=DecisionCaseSide.BEAR, citation_ids=("cit_dec_factor",), thesis="Same thesis"),
            ),
        )


def test_finalize_output_preserves_risk_hard_gate_and_strong_conclusion_limits() -> None:
    payload = _decision_payload()

    with pytest.raises(DecisionAgentError, match="cannot upgrade hard gate"):
        EvidenceScopedDecisionAgent().finalize_output(
            payload,
            _decision_output(
                recommendation=DecisionRecommendation.BUY,
                confidence_level=DecisionConfidenceLevel.HIGH,
                ranking_eligible=True,
            ),
        )

    with pytest.raises(DecisionAgentError, match="cannot mark ranking eligible"):
        EvidenceScopedDecisionAgent().finalize_output(
            payload,
            _decision_output(
                recommendation=DecisionRecommendation.AVOID,
                ranking_eligible=True,
            ),
        )


def test_finalize_output_requires_deterministic_numeric_claim_consistency() -> None:
    payload = _decision_payload()

    good_numeric_claim = _decision_numeric_claim("cl_dec_factor", "cit_dec_factor")
    result = EvidenceScopedDecisionAgent().finalize_output(
        payload,
        _decision_output(claims=(_risk_gate_claim("cl_dec_risk", "cit_dec_risk", value="block"), good_numeric_claim)),
    )
    assert result.to_record()["output"]["claims"][1]["claim_id"] == "cl_dec_factor"

    with pytest.raises(DecisionAgentError, match="numeric claim unit mismatch"):
        EvidenceScopedDecisionAgent().finalize_output(
            payload,
            _decision_output(claims=(_decision_numeric_claim("cl_bad_unit", "cit_dec_factor", unit="ratio"),)),
        )


def _decision_payload():
    return EvidenceScopedDecisionAgent().prepare_prompt_payload(
        DecisionAgentPromptRequest(
            run_id="run-decision",
            stage_id="stage-decision",
            bundle=_decision_bundle(),
            prompt_binding=_decision_binding(),
            technical_result=_technical_result(),
            intel_result=_intel_result(),
            risk_portfolio_result=_risk_portfolio_result(),
        )
    )


def _decision_binding() -> PromptRunBinding:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.DECISION)
    return registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-decision",
            stage_id="stage-decision",
            trace_id="trace-decision",
            role=AgentPromptRole.DECISION,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )


def _technical_result():
    agent = EvidenceScopedTechnicalAgent()
    payload = agent.prepare_prompt_payload(
        TechnicalAgentPromptRequest(
            run_id="run-technical",
            stage_id="stage-technical",
            bundle=_technical_bundle((_technical_evidence("ev_factor", HASH_A),)),
            prompt_binding=_technical_binding(),
        )
    )
    citation = _technical_citation("cit_factor", "ev_factor")
    claim = _technical_numeric_claim("cl_factor", "cit_factor")
    return agent.finalize_output(
        payload,
        TechnicalAgentStructuredOutput(
            signal=TechnicalSignal.BUY,
            confidence=0.82,
            reasoning="Factor momentum remains positive with cited deterministic evidence.",
            claims=(claim,),
            citations=(citation,),
            key_levels={"support": 1600.0, "resistance": 1800.0, "stop_loss": 1550.0},
            trend_score=82,
            ma_alignment=TechnicalTrendAlignment.BULLISH,
            volume_status=TechnicalVolumeStatus.NORMAL,
            pattern="MA breakout",
            warnings=("No realtime quote was fetched by this adapter.",),
        ),
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


def _technical_bundle(records: tuple[EvidenceRecord, ...]) -> EvidenceBundle:
    return _bundle("bundle-technical", EvidenceBundleRole.TECHNICAL, records)


def _intel_result():
    agent = EvidenceScopedIntelAgent()
    payload = agent.prepare_prompt_payload(
        IntelAgentPromptRequest(
            run_id="run-intel",
            stage_id="stage-intel",
            bundle=_intel_bundle((_intel_evidence("ev_official", HASH_B),)),
            prompt_binding=_intel_binding(),
        )
    )
    citation = _intel_citation("cit_official", "ev_official")
    claim = ResearchClaim(
        claim_id="cl_official",
        kind=ClaimKind.TEMPORAL_FACT,
        statement="The company announcement was available before the decision time.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_official"],
        computation_policy=ClaimComputationPolicy.CITATION_SUMMARY,
        dataset_versions=INTEL_DATASET_VERSIONS,
        run_id="run-intel",
        stage_id="stage-intel",
        artifact_hash=HASH_B,
    )
    return agent.finalize_output(
        payload,
        IntelAgentStructuredOutput(
            summary="Official source confirms capacity expansion with one fresh disclosure.",
            sentiment=IntelSentiment.POSITIVE,
            sentiment_score=72,
            events=(
                IntelAgentStructuredEvent(
                    event_id="event_official",
                    event_time=NOW - timedelta(hours=3),
                    published_at=NOW - timedelta(hours=2),
                    observed_at=NOW - timedelta(hours=1, minutes=45),
                    available_at=NOW - timedelta(hours=1, minutes=40),
                    summary="Company announcement confirms capacity expansion.",
                    impact=IntelEventImpact.POSITIVE,
                    strength=IntelEventStrength.STRONG,
                    freshness_status=IntelFreshnessStatus.FRESH,
                    source_evidence_ids=("ev_official",),
                    citation_ids=("cit_official",),
                ),
            ),
            claims=(claim,),
            citations=(citation,),
            warnings=("No live news search was executed by this adapter.",),
        ),
    )


def _intel_binding() -> PromptRunBinding:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.INTEL)
    return registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-intel",
            stage_id="stage-intel",
            trace_id="trace-intel",
            role=AgentPromptRole.INTEL,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )


def _intel_bundle(records: tuple[EvidenceRecord, ...]) -> EvidenceBundle:
    return _bundle("bundle-intel", EvidenceBundleRole.INTEL, records)


def _risk_portfolio_result():
    agent = EvidenceScopedRiskPortfolioAgent()
    payload = agent.prepare_prompt_payload(
        RiskPortfolioAgentPromptRequest(
            run_id="run-risk-portfolio",
            stage_id="stage-risk-portfolio",
            bundle=_risk_portfolio_bundle((_risk_evidence("ev_risk_block", HASH_C),)),
            prompt_binding=_risk_portfolio_binding(),
        )
    )
    citation = _risk_citation("cit_risk_status", "ev_risk_block", cited_value="block")
    claim = _risk_gate_claim("cl_risk_block", "cit_risk_status", value="block")
    return agent.finalize_output(
        payload,
        RiskPortfolioStructuredOutput(
            gate_status=RiskPortfolioGateStatus.BLOCK,
            portfolio_action=RiskPortfolioAction.AVOID,
            confidence=0.68,
            summary="Risk policy blocks promotion; portfolio context should remain defensive.",
            claims=(claim,),
            citations=(citation,),
            risk_factors=("Max drawdown policy is blocking.",),
            portfolio_constraints=("Do not promote ranking while hard gate is block.",),
            warnings=("Risk hard gate is deterministic and cannot be overridden.",),
        ),
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


def _risk_portfolio_bundle(records: tuple[EvidenceRecord, ...]) -> EvidenceBundle:
    return _bundle("bundle-risk-portfolio", EvidenceBundleRole.RISK_PORTFOLIO, records)


def _decision_bundle(records: tuple[EvidenceRecord, ...] | None = None) -> EvidenceBundle:
    return _bundle(
        "bundle-decision",
        EvidenceBundleRole.DECISION,
        records
        or (
            _technical_evidence("ev_factor", HASH_A),
            _intel_evidence("ev_official", HASH_B),
            _risk_evidence("ev_risk_block", HASH_C),
            _technical_evidence("ev_screen", HASH_D),
        ),
    )


def _bundle(bundle_id: str, role: EvidenceBundleRole, records: tuple[EvidenceRecord, ...]) -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id=bundle_id,
        request=EvidenceBundleRequest(
            tenant_id="tenant-a",
            team_id="team-alpha",
            owner_user_id="user-1",
            instrument_id="600519.XSHG",
            decision_time=NOW,
            role=role,
            budget=EvidenceBundleBudget(max_prompt_tokens=4096),
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
        estimated_tokens=200,
        schema_instruction_tokens=60,
    )


def _technical_evidence(evidence_id: str, content_hash: str) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=EvidenceKind.FACTOR_EVALUATION if evidence_id == "ev_factor" else EvidenceKind.SCREEN_SNAPSHOT,
        evaluation_scope=EvidenceEvaluationScope.FACTOR_EVALUATION
        if evidence_id == "ev_factor"
        else EvidenceEvaluationScope.SCREENING,
        title="Technical evidence",
        summary="Deterministic technical evidence.",
        source=EvidenceSource(
            source_id=f"src_{evidence_id}",
            source_type="artifact",
            schema_name="quant.factor_evaluation" if evidence_id == "ev_factor" else "quant.screen_snapshot",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=content_hash,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=TECH_DATASET_VERSIONS,
        instrument_id="600519.XSHG",
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_id=f"art_{evidence_id}",
        artifact_hash=content_hash,
        formula_versions={"metric_set": "factor_evaluation_metrics@1.0.0"},
        metadata={"llm_recompute_allowed": False},
    )


def _intel_evidence(evidence_id: str, content_hash: str) -> EvidenceRecord:
    available_at = NOW - timedelta(hours=1, minutes=40)
    verdict = SourceTrustPolicy.default().assess(
        UnstructuredSourceInput(
            source_id=f"src_{evidence_id}",
            source_type=UnstructuredSourceType.OFFICIAL_DISCLOSURE,
            url=f"https://example.com/{evidence_id}",
            title="Company disclosure",
            raw_body="Company announcement confirms capacity expansion.",
            published_at=NOW - timedelta(hours=2),
            observed_at=NOW - timedelta(hours=1, minutes=45),
            available_at=available_at,
            publisher="Example Publisher",
        )
    )
    source_record = dict(verdict.to_prompt_safe_record())
    source_record["observed_at"] = (NOW - timedelta(hours=1, minutes=45)).isoformat()
    source_record["event_time"] = (NOW - timedelta(hours=3)).isoformat()
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=EvidenceKind.UNSTRUCTURED_SOURCE,
        evaluation_scope=EvidenceEvaluationScope.MARKET_INTELLIGENCE,
        title="Company disclosure",
        summary="Prompt-safe Intel source evidence.",
        source=EvidenceSource(
            source_id=f"src_{evidence_id}",
            source_type="official_disclosure",
            schema_name="research.source_trust",
            schema_version="1.0.0",
        ),
        available_at=available_at,
        content_hash=content_hash,
        trust=verdict.trust,
        dataset_versions=INTEL_DATASET_VERSIONS,
        instrument_id="600519.XSHG",
        run_id="run-intel-source",
        stage_id="stage-source-trust",
        artifact_id=f"art_{evidence_id}",
        artifact_hash=content_hash,
        metadata={"source_trust": source_record, "llm_recompute_allowed": False},
    )


def _risk_evidence(evidence_id: str, content_hash: str) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=EvidenceKind.RISK_POLICY_RESULT,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Risk evidence",
        summary="Deterministic formal portfolio risk evidence.",
        source=EvidenceSource(
            source_id=f"src_{evidence_id}",
            source_type="artifact",
            schema_name="quant.backtest.risk_policy",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=content_hash,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=RISK_DATASET_VERSIONS,
        instrument_id="600519.XSHG",
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_id=f"art_{evidence_id}",
        artifact_hash=content_hash,
        formula_versions={"risk_evaluator": "cn_a_share_deterministic_risk_policy@1.0.0"},
        metadata={
            "llm_recompute_allowed": False,
            "risk_status": "block",
            "blocking_rule_ids": ["max_drawdown"],
            "eligible_for_ranking": False,
            "agent_strong_conclusion_allowed": False,
        },
    )


def _technical_citation(citation_id: str, evidence_id: str) -> ReportCitation:
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence_id,
        evidence_field_path="body.ic_summary.mean_ic",
        cited_value=0.42,
        unit="correlation",
        formula_version="factor_evaluation_metrics@1.0.0",
        dataset_versions=TECH_DATASET_VERSIONS,
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_hash=HASH_A,
    )


def _intel_citation(citation_id: str, evidence_id: str) -> ReportCitation:
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence_id,
        evidence_field_path="metadata.source_trust.cleaned_body",
        cited_value="Company announcement confirms capacity expansion.",
        dataset_versions=INTEL_DATASET_VERSIONS,
        run_id="run-intel-source",
        stage_id="stage-source-trust",
        artifact_hash=HASH_B,
    )


def _risk_citation(citation_id: str, evidence_id: str, *, cited_value: object) -> ReportCitation:
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence_id,
        evidence_field_path="body.status",
        cited_value=cited_value,
        formula_version="cn_a_share_deterministic_risk_policy@1.0.0",
        dataset_versions=RISK_DATASET_VERSIONS,
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_hash=HASH_C,
    )


def _decision_citation(citation_id: str, evidence: EvidenceRecord) -> ReportCitation:
    if evidence.evidence_id == "ev_factor":
        return ReportCitation(
            citation_id=citation_id,
            evidence_id=evidence.evidence_id,
            evidence_field_path="body.ic_summary.mean_ic",
            cited_value=0.42,
            unit="correlation",
            formula_version="factor_evaluation_metrics@1.0.0",
            dataset_versions=TECH_DATASET_VERSIONS,
            run_id="run-technical",
            stage_id="stage-technical-evidence",
            artifact_hash=evidence.artifact_hash,
        )
    if evidence.evidence_id == "ev_official":
        return ReportCitation(
            citation_id=citation_id,
            evidence_id=evidence.evidence_id,
            evidence_field_path="metadata.source_trust.cleaned_body",
            cited_value="Company announcement confirms capacity expansion.",
            dataset_versions=INTEL_DATASET_VERSIONS,
            run_id="run-intel-source",
            stage_id="stage-source-trust",
            artifact_hash=evidence.artifact_hash,
        )
    return ReportCitation(
        citation_id=citation_id,
        evidence_id=evidence.evidence_id,
        evidence_field_path="body.status",
        cited_value="block",
        formula_version="cn_a_share_deterministic_risk_policy@1.0.0",
        dataset_versions=evidence.dataset_versions,
        run_id=evidence.run_id,
        stage_id=evidence.stage_id,
        artifact_hash=evidence.artifact_hash,
    )


def _technical_numeric_claim(claim_id: str, citation_id: str) -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The factor mean IC is positive at 0.42.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=0.42,
        unit="correlation",
        formula_version="factor_evaluation_metrics@1.0.0",
        dataset_versions=TECH_DATASET_VERSIONS,
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_hash=HASH_A,
    )


def _decision_numeric_claim(claim_id: str, citation_id: str, *, unit: str = "correlation") -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The decision cites the factor mean IC at 0.42.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=0.42,
        unit=unit,
        formula_version="factor_evaluation_metrics@1.0.0",
        dataset_versions=TECH_DATASET_VERSIONS,
        run_id="run-technical",
        stage_id="stage-technical-evidence",
        artifact_hash=HASH_A,
    )


def _risk_gate_claim(claim_id: str, citation_id: str, *, value: str) -> ResearchClaim:
    return ResearchClaim(
        claim_id=claim_id,
        kind=ClaimKind.RISK_GATE,
        statement=f"Deterministic risk gate status is {value}.",
        verification_status=ClaimVerificationStatus.BLOCKED,
        citation_ids=[citation_id],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=value,
        formula_version="cn_a_share_deterministic_risk_policy@1.0.0",
        dataset_versions=RISK_DATASET_VERSIONS,
        run_id="run-formal-backtest",
        stage_id="stage-risk-evidence",
        artifact_hash=HASH_C,
    )


def _case(
    *,
    side: DecisionCaseSide,
    citation_ids: tuple[str, ...],
    thesis: str,
    source_roles: tuple[str, ...] = ("technical",),
) -> DecisionCase:
    return DecisionCase(
        case_id=f"{side.value}_case",
        side=side,
        thesis=thesis,
        factors=(f"{side.value} factor supported by cited evidence.",),
        citation_ids=citation_ids,
        source_roles=source_roles,
    )


def _decision_output(
    *,
    recommendation: DecisionRecommendation = DecisionRecommendation.BLOCKED,
    confidence_level: DecisionConfidenceLevel = DecisionConfidenceLevel.MEDIUM,
    ranking_eligible: bool = False,
    bull_case: DecisionCase | None = None,
    bear_case: DecisionCase | None = None,
    claims: tuple[ResearchClaim, ...] | None = None,
    citations: tuple[ReportCitation, ...] | None = None,
) -> DecisionStructuredOutput:
    decision_citations = citations or (
        _decision_citation("cit_dec_factor", _technical_evidence("ev_factor", HASH_A)),
        _decision_citation("cit_dec_official", _intel_evidence("ev_official", HASH_B)),
        _decision_citation("cit_dec_risk", _risk_evidence("ev_risk_block", HASH_C)),
    )
    return DecisionStructuredOutput(
        recommendation=recommendation,
        confidence_level=confidence_level,
        confidence=0.61,
        summary="Bullish technical and official disclosure evidence is outweighed by a deterministic risk block.",
        bull_case=bull_case
        or _case(
            side=DecisionCaseSide.BULL,
            citation_ids=("cit_dec_factor", "cit_dec_official"),
            thesis="Technical factor strength and official disclosure create a bull case.",
            source_roles=("technical", "intel"),
        ),
        bear_case=bear_case
        or _case(
            side=DecisionCaseSide.BEAR,
            citation_ids=("cit_dec_risk",),
            thesis="The deterministic risk gate blocks promotion and ranking.",
            source_roles=("risk_portfolio",),
        ),
        disagreement=DecisionDisagreementSummary(
            summary="Technical and Intel signals are constructive, but Risk/Portfolio hard gate is blocking.",
            unresolved_conflicts=("Risk gate overrides constructive non-risk evidence.",),
            citation_ids=("cit_dec_factor", "cit_dec_risk"),
        ),
        invalidation_conditions=(
            DecisionInvalidationCondition(
                condition_id="inv_risk_gate",
                description="Decision can improve only after a new deterministic risk run no longer blocks promotion.",
                citation_ids=("cit_dec_risk",),
            ),
        ),
        claims=claims or (_risk_gate_claim("cl_dec_risk", "cit_dec_risk", value="block"),),
        citations=decision_citations,
        ranking_eligible=ranking_eligible,
        warnings=("Final decision did not run a model or provider.",),
        limitations=("Citation Validator and report rendering remain later tasks.",),
    )
