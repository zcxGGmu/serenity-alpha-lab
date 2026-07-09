# Phase 6 Research Validation And Monitors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate DSA portfolio, backtest, alerts, and notification capabilities into Serenity as research validation and default-off research monitors, without trade automation.

**Architecture:** Add Serenity-owned pure Python modules for portfolio/backtest validation and research monitors. Keep all external delivery channels disabled by default, surface only handoff-ready records, and make local API/config diagnostics prove no secrets or network delivery are required at startup.

**Tech Stack:** Python 3.11+ / dataclasses / local API `http.server` handler / pytest / existing Serenity report-safety and migration-boundary tests.

---

## File Structure

- Create: `src/serenity_alpha_lab/research_validation.py`
  - Owns portfolio observation normalization, portfolio research snapshots, backtest validation summaries, and evidence/ref diagnostics.
- Create: `src/serenity_alpha_lab/research_monitors.py`
  - Owns research monitor rules, dry-run evaluation, notification capability metadata, default-off dispatch plans, and evidence-backed handoff records.
- Modify: `src/serenity_alpha_lab/app/config.py`
  - Adds explicit default-off monitor/notification config fields without reading secret values into health payloads.
- Modify: `src/serenity_alpha_lab/app/local_api.py`
  - Adds health/status diagnostics for research monitors and notifications, preserving no-secret startup behavior.
- Create: `tests/test_research_validation.py`
  - Covers research-only portfolio/backtest validation semantics and rejects trading-automation vocabulary in public payloads.
- Create: `tests/test_research_monitors.py`
  - Covers default-off monitor behavior, local dry-run handoff records, and no active notification delivery.
- Modify: `tests/test_app_api.py`
  - Covers API startup with no secrets and health payload monitor diagnostics.
- Modify during closeout only: `docs/serenity-led-dsa-full-migration-tracker.md`, `tasks/todo.md`, and `tasks/lessons.md`.
- Do not modify: protected generated `output/ui/*` artifacts.

## Source Reference Boundaries

- Use DSA files only as source reference:
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/portfolio.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/backtest.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/api/v1/schemas/alerts.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/core/backtest_engine.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/services/alert_service.py`
  - `/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis/src/notification_capabilities.py`
- Never add Serenity runtime imports from the DSA checkout.
- Convert DSA `portfolio`, `backtest`, `alert`, and `notification` semantics into research-only contracts.
- Do not expose direct buy/sell/hold instructions, target-price promises, position sizing, stop loss/take profit instructions, broker actions, or guaranteed outcomes.

### Task 1: Research Validation Tests

**Files:**
- Create: `tests/test_research_validation.py`
- Create after red: `src/serenity_alpha_lab/research_validation.py`

- [ ] **Step 1: Write failing portfolio validation test**

```python
from datetime import date

from serenity_alpha_lab.research_validation import PortfolioObservation, build_portfolio_research_snapshot


def test_portfolio_snapshot_is_research_validation_not_trade_automation():
    snapshot = build_portfolio_research_snapshot(
        portfolio_id="watchlist-alpha",
        as_of=date(2026, 7, 9),
        observations=[
            PortfolioObservation(
                symbol="SIVE",
                research_weight=0.42,
                evidence_ids=["evidence:sive:primary:2025-10k"],
                thesis="Primary-source margin expansion thesis needs validation.",
                risk_flags=["primary_source_gap_closed"],
            )
        ],
    )

    payload = snapshot.to_dict()
    assert payload["research_only"] is True
    assert payload["validation_scope"] == "portfolio_research_snapshot"
    assert payload["items"][0]["symbol"] == "SIVE"
    assert payload["items"][0]["evidence_ids"] == ["evidence:sive:primary:2025-10k"]
    assert payload["diagnostics"]["automation_enabled"] is False
    rendered = str(payload).lower()
    assert "position_size" not in rendered
    assert "broker" not in rendered
    assert "trade" not in rendered
```

- [ ] **Step 2: Write failing backtest validation test**

```python
from datetime import date

from serenity_alpha_lab.research_validation import BacktestObservation, summarize_backtest_validation


def test_backtest_summary_is_historical_validation_not_future_promise():
    summary = summarize_backtest_validation(
        hypothesis_id="hypothesis:sive:margin-expansion",
        observations=[
            BacktestObservation(
                symbol="SIVE",
                analysis_date=date(2026, 6, 1),
                evaluation_window_days=20,
                start_value=10.0,
                end_value=11.5,
                evidence_ids=["evidence:sive:primary:2025-10k"],
            ),
            BacktestObservation(
                symbol="SIVE",
                analysis_date=date(2026, 6, 2),
                evaluation_window_days=20,
                start_value=12.0,
                end_value=11.4,
                evidence_ids=["evidence:sive:market-data:daily-bars"],
            ),
        ],
    )

    payload = summary.to_dict()
    assert payload["research_only"] is True
    assert payload["validation_scope"] == "historical_research_validation"
    assert payload["completed_count"] == 2
    assert payload["positive_count"] == 1
    assert payload["negative_count"] == 1
    assert payload["diagnostics"]["future_performance_disclaimer"] == "historical_validation_only"
    rendered = str(payload).lower()
    assert "guarantee" not in rendered
    assert "take_profit" not in rendered
    assert "stop_loss" not in rendered
```

- [ ] **Step 3: Run red validation tests**

Run: `python3 -m pytest tests/test_research_validation.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.research_validation'`.

- [ ] **Step 4: Implement minimal research validation module**

Create `src/serenity_alpha_lab/research_validation.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean
from typing import Any, Sequence


@dataclass(frozen=True)
class PortfolioObservation:
    symbol: str
    research_weight: float
    evidence_ids: list[str] = field(default_factory=list)
    thesis: str = ""
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol.strip().upper(),
            "research_weight": float(self.research_weight),
            "evidence_ids": list(self.evidence_ids),
            "thesis": self.thesis,
            "risk_flags": list(self.risk_flags),
        }


@dataclass(frozen=True)
class PortfolioResearchSnapshot:
    portfolio_id: str
    as_of: date
    items: list[PortfolioObservation]
    diagnostics: dict[str, Any]
    research_only: bool = True
    validation_scope: str = "portfolio_research_snapshot"

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "as_of": self.as_of.isoformat(),
            "research_only": self.research_only,
            "validation_scope": self.validation_scope,
            "items": [item.to_dict() for item in self.items],
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class BacktestObservation:
    symbol: str
    analysis_date: date
    evaluation_window_days: int
    start_value: float
    end_value: float
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def return_pct(self) -> float:
        if self.start_value <= 0:
            return 0.0
        return (self.end_value - self.start_value) / self.start_value * 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol.strip().upper(),
            "analysis_date": self.analysis_date.isoformat(),
            "evaluation_window_days": int(self.evaluation_window_days),
            "start_value": float(self.start_value),
            "end_value": float(self.end_value),
            "return_pct": self.return_pct,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class BacktestValidationSummary:
    hypothesis_id: str
    observations: list[BacktestObservation]
    diagnostics: dict[str, Any]
    research_only: bool = True
    validation_scope: str = "historical_research_validation"

    def to_dict(self) -> dict[str, Any]:
        returns = [item.return_pct for item in self.observations]
        return {
            "hypothesis_id": self.hypothesis_id,
            "research_only": self.research_only,
            "validation_scope": self.validation_scope,
            "completed_count": len(self.observations),
            "positive_count": sum(1 for value in returns if value > 0),
            "negative_count": sum(1 for value in returns if value < 0),
            "average_return_pct": mean(returns) if returns else None,
            "observations": [item.to_dict() for item in self.observations],
            "diagnostics": dict(self.diagnostics),
        }


def build_portfolio_research_snapshot(
    *,
    portfolio_id: str,
    as_of: date,
    observations: Sequence[PortfolioObservation],
) -> PortfolioResearchSnapshot:
    items = list(observations)
    missing_evidence = [item.symbol for item in items if not item.evidence_ids]
    return PortfolioResearchSnapshot(
        portfolio_id=portfolio_id,
        as_of=as_of,
        items=items,
        diagnostics={
            "automation_enabled": False,
            "broker_integration": "disabled",
            "missing_evidence_symbols": missing_evidence,
        },
    )


def summarize_backtest_validation(
    *,
    hypothesis_id: str,
    observations: Sequence[BacktestObservation],
) -> BacktestValidationSummary:
    items = list(observations)
    return BacktestValidationSummary(
        hypothesis_id=hypothesis_id,
        observations=items,
        diagnostics={
            "future_performance_disclaimer": "historical_validation_only",
            "automation_enabled": False,
            "evaluation_count": len(items),
        },
    )
```

- [ ] **Step 5: Run green validation tests**

Run: `python3 -m pytest tests/test_research_validation.py -q`

Expected: PASS with `2 passed`.

### Task 2: Default-Off Research Monitor Tests

**Files:**
- Create: `tests/test_research_monitors.py`
- Create after red: `src/serenity_alpha_lab/research_monitors.py`

- [ ] **Step 1: Write failing monitor default-off test**

```python
from serenity_alpha_lab.research_monitors import (
    ResearchMonitorRule,
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
```

- [ ] **Step 2: Write failing notification capability test**

```python
from serenity_alpha_lab.research_monitors import build_notification_dispatch_plan


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
```

- [ ] **Step 3: Run red monitor tests**

Run: `python3 -m pytest tests/test_research_monitors.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.research_monitors'`.

- [ ] **Step 4: Implement minimal research monitors module**

Create `src/serenity_alpha_lab/research_monitors.py` with:

```python
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
```

- [ ] **Step 5: Run green monitor tests**

Run: `python3 -m pytest tests/test_research_monitors.py -q`

Expected: PASS with `2 passed`.

### Task 3: Local API And Config Diagnostics

**Files:**
- Modify: `src/serenity_alpha_lab/app/config.py`
- Modify: `src/serenity_alpha_lab/app/local_api.py`
- Modify: `tests/test_app_api.py`

- [ ] **Step 1: Write failing app health test**

Add to `tests/test_app_api.py`:

```python
from serenity_alpha_lab.app.local_api import _health_payload
from serenity_alpha_lab.app.config import AppRuntimeConfig


def test_health_payload_reports_research_monitors_default_off_without_secrets():
    payload = _health_payload(AppRuntimeConfig())

    assert payload["research_only"] is True
    assert payload["research_monitors"]["enabled"] is False
    assert payload["research_monitors"]["notifications_enabled"] is False
    assert payload["research_monitors"]["delivery_status"] == "disabled"
    assert "token" not in str(payload).lower()
    assert "secret" not in str(payload).lower()
    assert "password" not in str(payload).lower()
```

- [ ] **Step 2: Run red API test**

Run: `python3 -m pytest tests/test_app_api.py::test_health_payload_reports_research_monitors_default_off_without_secrets -q`

Expected: FAIL with `KeyError: 'research_monitors'`.

- [ ] **Step 3: Add default-off config fields**

Add these fields to `AppRuntimeConfig` in `src/serenity_alpha_lab/app/config.py`:

```python
    research_monitors_enabled: bool = False
    research_monitor_notifications_enabled: bool = False
    notification_channels_env_var: str = "SERENITY_NOTIFICATION_CHANNELS"
```

Add this property:

```python
    @property
    def configured_notification_channels(self) -> list[str]:
        value = os.getenv(self.notification_channels_env_var, "")
        return [item.strip().lower() for item in value.split(",") if item.strip()]
```

- [ ] **Step 4: Add health diagnostics without secret values**

Update `_health_payload()` in `src/serenity_alpha_lab/app/local_api.py` with:

```python
        "research_monitors": {
            "enabled": config.research_monitors_enabled,
            "notifications_enabled": config.research_monitor_notifications_enabled,
            "delivery_status": "enabled" if config.research_monitor_notifications_enabled else "disabled",
            "configured_channel_count": len(config.configured_notification_channels),
        },
```

- [ ] **Step 5: Run green API test**

Run: `python3 -m pytest tests/test_app_api.py::test_health_payload_reports_research_monitors_default_off_without_secrets -q`

Expected: PASS.

### Task 4: Phase 6 Boundary Regressions

**Files:**
- Modify if needed: `tests/test_dsa_migration_boundaries.py`

- [ ] **Step 1: Run focused Phase 6 regression**

Run: `python3 -m pytest tests/test_research_validation.py tests/test_research_monitors.py tests/test_app_api.py tests/test_dsa_migration_boundaries.py -q`

Expected: PASS.

- [ ] **Step 2: Run static DSA import/path scan**

Run: `rg -n "daily_stock_analysis|/Users/zq/Desktop/ai-projs/trading/daily_stock_analysis" src/serenity_alpha_lab tests`

Expected: no matches in runtime paths. If docs/tests intentionally mention source reference paths, narrow the scan to `src/serenity_alpha_lab` before recording the guard result.

- [ ] **Step 3: Run research-only safety scan**

Run: `rg -n "operation_advice|position_sizing|target_price|stop_loss|take_profit|broker|place_order|guaranteed return|guarantee" src/serenity_alpha_lab/research_validation.py src/serenity_alpha_lab/research_monitors.py tests/test_research_validation.py tests/test_research_monitors.py`

Expected: no production matches. Test assertions may include forbidden terms only as absence checks.

- [ ] **Step 4: Run diff hygiene**

Run: `git diff --check`

Expected: no whitespace errors.

### Task 5: Closeout Documentation And Full Verification

**Files:**
- Modify: `docs/serenity-led-dsa-full-migration-tracker.md`
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md` if a reusable lesson emerges

- [ ] **Step 1: Run full verification**

Run: `make verify`

Expected: all Python tests pass, `doctor` is healthy, `run-cpo-pack` completes, and migration guard remains clean.

- [ ] **Step 2: Check protected output status**

Run: `git status --short output/ui`

Expected: only the pre-existing protected generated UI dirty files/directories appear. Do not stage, commit, revert, or overwrite them.

- [ ] **Step 3: Update tracker and task log**

Record:

```text
Phase 6 implemented research validation snapshots, historical validation summaries, default-off research monitor dry-runs, no-secret health diagnostics, focused regression evidence, static import scan, safety scan, diff check, full verification result, and protected output status.
```

- [ ] **Step 4: Stage only owned Phase 6 files**

Run:

```bash
git add \
  src/serenity_alpha_lab/research_validation.py \
  src/serenity_alpha_lab/research_monitors.py \
  src/serenity_alpha_lab/app/config.py \
  src/serenity_alpha_lab/app/local_api.py \
  tests/test_research_validation.py \
  tests/test_research_monitors.py \
  tests/test_app_api.py \
  docs/serenity-led-dsa-full-migration-tracker.md \
  docs/superpowers/plans/2026-07-09-serenity-alpha-lab-phase-6-research-validation-monitors.md \
  tasks/todo.md \
  tasks/lessons.md
```

- [ ] **Step 5: Commit Phase 6**

Run:

```bash
git commit -m "feat: 完成 Serenity Phase 6 研究验证与监控迁移"
```

Expected: one commit containing only Phase 6 owned files. Protected `output/ui/*` remains unstaged.

## Implementation Check-In

- Phase 6 should proceed with two small pure modules before any API expansion beyond health/status diagnostics.
- Portfolio and backtest features are research validation artifacts only.
- Alert and notification features are local dry-run research monitors and handoff records only.
- External delivery remains default-off and requires explicit config before a handoff can become dispatchable.
- No live broker action, order placement, trading automation, position sizing, or performance guarantee is in scope.
