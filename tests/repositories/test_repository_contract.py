from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.application.config_profiles import load_runtime_settings


@dataclass(frozen=True, slots=True)
class RepositoryBackend:
    name: str
    database_url: str


@pytest.fixture(params=["sqlite", "postgresql"])
def repository_backend(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[RepositoryBackend]:
    if request.param == "postgresql":
        database_url = os.environ.get("SERENITY_TEST_POSTGRES_URL")
        if not database_url:
            pytest.skip("SERENITY_TEST_POSTGRES_URL is not configured")
        yield RepositoryBackend(name="postgresql", database_url=database_url)
        return

    yield RepositoryBackend(name="sqlite", database_url=f"sqlite:///{tmp_path / 'repository-contract.sqlite'}")


@pytest.fixture
def repository(repository_backend: RepositoryBackend):
    from serenity_alpha_lab.repositories.database import (
        RepositoryContractProbeRepository,
        create_database_engine,
        resolve_database_profile,
    )

    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": repository_backend.database_url,
        }
    )
    database = resolve_database_profile(settings)
    engine = create_database_engine(database)
    repo = RepositoryContractProbeRepository(engine)
    repo.create_schema()
    repo.clear()
    try:
        yield repo
    finally:
        repo.clear()
        engine.dispose()


def make_record(record_id: str = "repo-contract-001"):
    from serenity_alpha_lab.repositories.database import RepositoryContractProbeRecord

    return RepositoryContractProbeRecord(
        record_id=record_id,
        occurred_at=datetime(2026, 7, 23, 1, 30, 15, 123456, tzinfo=UTC),
        trade_date=date(2026, 7, 23),
        amount=Decimal("123456789.123456"),
        payload={
            "instrument_id": "600519.XSHG",
            "flags": {"pit_safe": True, "source": "contract"},
            "values": [1, "two", Decimal("3.140000")],
        },
        schema_version="repository_contract.v1",
    )


def test_repository_contract_round_trips_time_decimal_json_and_date(repository) -> None:
    record = make_record()

    repository.insert(record)
    loaded = repository.get(record.record_id)

    assert loaded == record
    assert loaded.occurred_at.tzinfo is UTC
    assert loaded.occurred_at.isoformat() == "2026-07-23T01:30:15.123456+00:00"
    assert loaded.trade_date == date(2026, 7, 23)
    assert loaded.amount == Decimal("123456789.123456")
    assert loaded.payload == {
        "instrument_id": "600519.XSHG",
        "flags": {"pit_safe": True, "source": "contract"},
        "values": [1, "two", "3.140000"],
    }


def test_repository_contract_duplicate_keys_raise_stable_error(repository) -> None:
    from serenity_alpha_lab.repositories.database import RepositoryConflict

    record = make_record()
    repository.insert(record)

    with pytest.raises(RepositoryConflict, match="already exists"):
        repository.insert(record)


def test_repository_contract_rolls_back_failed_transactions(repository) -> None:
    record = make_record("repo-contract-rollback")

    with pytest.raises(RuntimeError, match="force rollback"):
        with repository.transaction() as transaction:
            transaction.insert(record)
            raise RuntimeError("force rollback")

    assert repository.get(record.record_id) is None
