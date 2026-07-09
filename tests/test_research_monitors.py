from __future__ import annotations

from serenity_alpha_lab.research_monitors import (
    ResearchMonitorRule,
    build_notification_dispatch_plan,
    evaluate_research_monitor,
)


def test_research_monitor_is_default_off_and_local_dry_run_only():
    rule = ResearchMonitorRule(
        rule_id="monitor:readiness:sive",
        name="SIVE readiness monitor",
        target="SIVE",
        monitor_type="readiness_status",
        threshold="needs_work",
        evidence_ids=["evidence:sive:primary:2025-10k"],
    )

    evaluation = evaluate_research_monitor(rule, observed_value="needs_work")
    payload = evaluation.to_dict()

    assert payload["research_only"] is True
    assert payload["enabled"] is False
    assert payload["triggered"] is True
    assert payload["delivery"]["status"] == "disabled"
    assert payload["handoff_record"]["evidence_ids"] == ["evidence:sive:primary:2025-10k"]
    assert payload["handoff_record"]["automation_enabled"] is False


def test_notification_dispatch_requires_explicit_enablement_and_configured_channel():
    disabled = build_notification_dispatch_plan(
        channels=["email", "slack"],
        notifications_enabled=False,
        configured_channels=["email"],
    )
    assert disabled.to_dict()["status"] == "disabled"
    assert disabled.to_dict()["dispatchable_channels"] == []

    enabled = build_notification_dispatch_plan(
        channels=["email", "slack"],
        notifications_enabled=True,
        configured_channels=["email"],
    )
    payload = enabled.to_dict()
    assert payload["status"] == "ready_for_handoff"
    assert payload["dispatchable_channels"] == ["email"]
    assert payload["blocked_channels"] == ["slack"]
