from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.domain.run_lifecycle import (
    EventKind,
    IdempotencyConflict,
    InvalidTransition,
    Run,
    RunStatus,
    StageStatus,
)


NOW = datetime(2026, 7, 20, 9, 30, tzinfo=UTC)


def test_run_stage_event_lifecycle_is_append_only_and_monotonic() -> None:
    run = Run.start(
        run_id="run-001",
        run_type="research",
        idempotency_key="research:600519:2026-07-20",
        started_at=NOW,
    )

    stage = run.start_stage(stage_id="stage-001", name="collect-evidence", started_at=NOW)
    run.record_stage_event(stage.stage_id, EventKind.INFO, message="provider cache hit", occurred_at=NOW)
    run.complete_stage(stage.stage_id, completed_at=NOW)
    run.complete(completed_at=NOW)

    assert run.status is RunStatus.COMPLETED
    assert run.stages[0].status is StageStatus.COMPLETED
    assert [event.sequence for event in run.events] == [1, 2, 3, 4, 5]
    assert [event.kind for event in run.events] == [
        EventKind.RUN_STARTED,
        EventKind.STAGE_STARTED,
        EventKind.INFO,
        EventKind.STAGE_COMPLETED,
        EventKind.RUN_COMPLETED,
    ]


def test_terminal_run_cannot_move_back_to_active_state() -> None:
    run = Run.start(
        run_id="run-terminal",
        run_type="research",
        idempotency_key="research:000001:2026-07-20",
        started_at=NOW,
    )

    run.complete(completed_at=NOW)

    with pytest.raises(InvalidTransition):
        run.start_stage(stage_id="stage-after-complete", name="illegal", started_at=NOW)

    with pytest.raises(InvalidTransition):
        run.fail(reason="late failure", failed_at=NOW)


def test_retry_creates_new_attempt_and_preserves_original_events() -> None:
    run = Run.start(
        run_id="run-retry",
        run_type="research",
        idempotency_key="research:000002:2026-07-20",
        started_at=NOW,
    )
    run.fail(reason="provider timeout", failed_at=NOW)

    retry = run.retry(new_run_id="run-retry-attempt-2", started_at=NOW)

    assert run.status is RunStatus.FAILED
    assert retry.run_id == "run-retry-attempt-2"
    assert retry.attempt == 2
    assert retry.parent_run_id == "run-retry"
    assert retry.idempotency_key == run.idempotency_key
    assert [event.sequence for event in run.events] == [1, 2]
    assert [event.sequence for event in retry.events] == [1]
    assert retry.events[0].kind is EventKind.RUN_STARTED


def test_idempotency_key_prevents_conflicting_reuse() -> None:
    run = Run.start(
        run_id="run-idempotent",
        run_type="research",
        idempotency_key="research:000003:2026-07-20",
        started_at=NOW,
    )

    same_request = Run.start(
        run_id="run-idempotent-replay",
        run_type="research",
        idempotency_key="research:000003:2026-07-20",
        started_at=NOW,
    )
    conflicting_request = Run.start(
        run_id="run-idempotent-conflict",
        run_type="screen",
        idempotency_key="research:000003:2026-07-20",
        started_at=NOW,
    )

    assert run.same_idempotent_request(same_request)

    with pytest.raises(IdempotencyConflict):
        run.same_idempotent_request(conflicting_request)
