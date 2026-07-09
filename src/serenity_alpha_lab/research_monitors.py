from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence


@dataclass(frozen=True)
class ResearchMonitorRule:
    rule_id: str
    name: str
    target: str
    monitor_type: str
    threshold: Any
    evidence_ids: list[str] = field(default_factory=list)
    enabled: bool = False
    severity: str = "warning"


@dataclass(frozen=True)
class NotificationDispatchPlan:
    status: str
    requested_channels: list[str]
    dispatchable_channels: list[str]
    blocked_channels: list[str]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "requested_channels": list(self.requested_channels),
            "dispatchable_channels": list(self.dispatchable_channels),
            "blocked_channels": list(self.blocked_channels),
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class ResearchMonitorEvaluation:
    rule: ResearchMonitorRule
    observed_value: Any
    triggered: bool
    delivery: NotificationDispatchPlan
    evaluated_at: datetime
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        evidence_ids = list(self.rule.evidence_ids)
        return {
            "rule_id": self.rule.rule_id,
            "name": self.rule.name,
            "target": self.rule.target,
            "monitor_type": self.rule.monitor_type,
            "enabled": bool(self.rule.enabled),
            "research_only": self.research_only,
            "observed_value": self.observed_value,
            "threshold": self.rule.threshold,
            "triggered": self.triggered,
            "severity": self.rule.severity,
            "evaluated_at": self.evaluated_at.isoformat(),
            "delivery": self.delivery.to_dict(),
            "handoff_record": {
                "record_type": "research_monitor_handoff",
                "rule_id": self.rule.rule_id,
                "target": self.rule.target,
                "evidence_ids": evidence_ids,
                "triggered": self.triggered,
                "automation_enabled": False,
                "delivery_status": self.delivery.status,
            },
        }


def build_notification_dispatch_plan(
    *,
    channels: Sequence[str],
    notifications_enabled: bool,
    configured_channels: Sequence[str],
) -> NotificationDispatchPlan:
    requested = [str(channel).strip().lower() for channel in channels if str(channel).strip()]
    configured = {str(channel).strip().lower() for channel in configured_channels if str(channel).strip()}
    if not notifications_enabled:
        return NotificationDispatchPlan(
            status="disabled",
            requested_channels=requested,
            dispatchable_channels=[],
            blocked_channels=requested,
            diagnostics={"reason": "notifications_default_off"},
        )
    dispatchable = [channel for channel in requested if channel in configured]
    blocked = [channel for channel in requested if channel not in configured]
    return NotificationDispatchPlan(
        status="ready_for_handoff" if dispatchable else "not_configured",
        requested_channels=requested,
        dispatchable_channels=dispatchable,
        blocked_channels=blocked,
        diagnostics={"reason": "explicit_enablement_required"},
    )


def evaluate_research_monitor(
    rule: ResearchMonitorRule,
    *,
    observed_value: Any,
    channels: Sequence[str] = (),
    notifications_enabled: bool = False,
    configured_channels: Sequence[str] = (),
) -> ResearchMonitorEvaluation:
    triggered = str(observed_value) == str(rule.threshold)
    delivery = build_notification_dispatch_plan(
        channels=channels,
        notifications_enabled=notifications_enabled and rule.enabled,
        configured_channels=configured_channels,
    )
    return ResearchMonitorEvaluation(
        rule=rule,
        observed_value=observed_value,
        triggered=triggered,
        delivery=delivery,
        evaluated_at=datetime.now(timezone.utc),
    )
