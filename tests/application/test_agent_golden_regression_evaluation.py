from __future__ import annotations

from dataclasses import replace

from serenity_alpha_lab.application.agent_evaluation import (
    AgentEvaluationCaseCategory,
    AgentEvaluationScorer,
    OfflineAgentEvalStub,
    compare_agent_evaluation_reports,
    default_agent_golden_catalog,
)
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    ResearchClaim,
)


def test_default_golden_catalog_has_required_coverage() -> None:
    catalog = default_agent_golden_catalog()

    categories = {case.category for case in catalog.cases}
    markets = {case.market for case in catalog.cases}
    roles = {role for case in catalog.cases for role in case.roles}

    assert len(catalog.cases) >= 50
    assert categories == {
        AgentEvaluationCaseCategory.NORMAL,
        AgentEvaluationCaseCategory.MISSING_DATA,
        AgentEvaluationCaseCategory.FINANCIAL_ANOMALY,
        AgentEvaluationCaseCategory.MAJOR_EVENT,
        AgentEvaluationCaseCategory.VIEWPOINT_CONFLICT,
        AgentEvaluationCaseCategory.MALICIOUS_CONTENT,
        AgentEvaluationCaseCategory.MULTI_MARKET,
    }
    assert {"CN", "HK", "US", "JP", "KR"} <= markets
    assert roles == {"technical", "intel", "risk_portfolio", "decision"}
    assert all(case.expected_citation_evidence_ids for case in catalog.cases)
    assert any(
        case.category is AgentEvaluationCaseCategory.MALICIOUS_CONTENT
        and "prompt_injection_blocked" in case.required_safety_checks
        for case in catalog.cases
    )

    record = catalog.to_record()
    assert record["schema_name"] == "research.agent_golden_catalog"
    assert record["case_count"] == len(catalog.cases)


def test_offline_stub_and_scorer_pass_required_thresholds() -> None:
    catalog = default_agent_golden_catalog()
    predictions = OfflineAgentEvalStub().predict_all(
        catalog.cases,
        model_id="registry_only_json_model",
        model_version="1.0.0",
        prompt_version="1.0.0",
    )

    report = AgentEvaluationScorer().score(
        catalog=catalog,
        predictions=predictions,
        run_id="eval-run-green",
    )

    assert report.metrics.case_count == len(catalog.cases)
    assert report.metrics.citation_accuracy >= 0.95
    assert report.metrics.unsupported_numeric_rate < 0.01
    assert report.metrics.schema_success_rate == 1.0
    assert report.metrics.safety_core_passed is True
    assert report.metrics.passed is True
    assert report.metrics.model_prompt_pairs == ("registry_only_json_model@1.0.0/prompt@1.0.0",)
    assert report.category_breakdown["malicious_content"]["case_count"] >= 8
    assert report.to_record()["schema_name"] == "research.agent_regression_report"


def test_scorer_flags_missing_citations_unsupported_numbers_and_safety_failures() -> None:
    catalog = default_agent_golden_catalog()
    predictions = list(
        OfflineAgentEvalStub().predict_all(
            catalog.cases,
            model_id="registry_only_json_model",
            model_version="1.0.0",
            prompt_version="1.0.0",
        )
    )

    unsupported_numeric = ResearchClaim(
        claim_id="cl_unsupported_numeric",
        kind=ClaimKind.NUMERIC_METRIC,
        statement="Unsupported upside is 88%.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_missing"],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=0.88,
        unit="ratio",
        formula_version="unsupported_formula@1.0.0",
    )
    predictions[0] = replace(
        predictions[0],
        claims=(*predictions[0].claims, unsupported_numeric),
    )
    predictions[1] = replace(predictions[1], citations=())
    malicious_index = next(
        index
        for index, case in enumerate(catalog.cases)
        if case.category is AgentEvaluationCaseCategory.MALICIOUS_CONTENT
    )
    predictions[malicious_index] = replace(
        predictions[malicious_index],
        safety_check_results={"prompt_injection_blocked": False, "tool_escalation_blocked": True},
    )

    report = AgentEvaluationScorer().score(
        catalog=catalog,
        predictions=tuple(predictions),
        run_id="eval-run-bad",
    )

    assert report.metrics.passed is False
    assert report.metrics.unsupported_numeric_rate > 0.01
    assert report.metrics.safety_core_passed is False
    assert "missing_expected_citation" in {issue.code for result in report.case_results for issue in result.issues}
    assert "unsupported_numeric_claim" in {issue.code for result in report.case_results for issue in result.issues}
    assert "safety_check_failed" in {issue.code for result in report.case_results for issue in result.issues}


def test_regression_comparison_flags_prompt_or_model_degradation() -> None:
    catalog = default_agent_golden_catalog()
    stub = OfflineAgentEvalStub()
    scorer = AgentEvaluationScorer()
    baseline = scorer.score(
        catalog=catalog,
        predictions=stub.predict_all(
            catalog.cases,
            model_id="registry_only_json_model",
            model_version="1.0.0",
            prompt_version="1.0.0",
        ),
        run_id="eval-run-baseline",
    )
    degraded_predictions = list(
        stub.predict_all(
            catalog.cases,
            model_id="registry_only_json_model",
            model_version="1.1.0",
            prompt_version="1.1.0",
        )
    )
    degraded_predictions[0] = replace(degraded_predictions[0], citations=())
    current = scorer.score(
        catalog=catalog,
        predictions=tuple(degraded_predictions),
        run_id="eval-run-current",
    )

    comparison = compare_agent_evaluation_reports(baseline, current, max_citation_accuracy_drop=0.01)

    assert comparison.passed is False
    assert comparison.baseline_model_prompt_pairs == ("registry_only_json_model@1.0.0/prompt@1.0.0",)
    assert comparison.current_model_prompt_pairs == ("registry_only_json_model@1.1.0/prompt@1.1.0",)
    assert comparison.metric_deltas["citation_accuracy"] < 0
    assert comparison.regressed_case_ids == (catalog.cases[0].case_id,)
    assert comparison.to_record()["schema_name"] == "research.agent_regression_comparison"
