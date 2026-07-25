from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from serenity_alpha_lab.datasets.corporate_actions import (
    CORPORATE_ACTIONS_SCHEMA_NAME,
    CORPORATE_ACTIONS_SCHEMA_VERSION,
    CorporateAction,
    CorporateActionType,
)
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger, PortfolioLedgerError

CORPORATE_ACTION_LEDGER_PROCESSOR_CONTRACT_VERSION = "quant.corporate_action_ledger_processor@1.0.0"
CORPORATE_ACTION_LEDGER_PROCESSOR_SCHEMA_NAME = "quant.backtest.corporate_action_ledger_processor"
CORPORATE_ACTION_LEDGER_PROCESSOR_SCHEMA_VERSION = "1.0.0"
CORPORATE_ACTION_LEDGER_PROCESSOR_VERSION = "cn_a_share_corporate_action_ledger_processor@1.0.0"
CORPORATE_ACTION_DATASET_SOURCE_SCHEMA = f"{CORPORATE_ACTIONS_SCHEMA_NAME}@{CORPORATE_ACTIONS_SCHEMA_VERSION}"
DELISTING_LIQUIDATION_SOURCE_SCHEMA = "quant.backtest.delisting_liquidation@1.0.0"


@dataclass(frozen=True, slots=True)
class CorporateActionLedgerProcessor:
    contract_version: str = CORPORATE_ACTION_LEDGER_PROCESSOR_CONTRACT_VERSION
    schema_name: str = CORPORATE_ACTION_LEDGER_PROCESSOR_SCHEMA_NAME
    schema_version: str = CORPORATE_ACTION_LEDGER_PROCESSOR_SCHEMA_VERSION
    processor_version: str = CORPORATE_ACTION_LEDGER_PROCESSOR_VERSION

    def apply(
        self,
        ledger: PortfolioLedger,
        action: CorporateAction,
        *,
        event_id: str,
        occurred_at: datetime,
        settlement_date: date | None = None,
    ) -> PortfolioLedger:
        if type(ledger) is not PortfolioLedger:
            raise PortfolioLedgerError("ledger must be a PortfolioLedger")
        if type(action) is not CorporateAction:
            raise PortfolioLedgerError("action must be a CorporateAction")
        action_id = corporate_action_id(action)
        metadata = _dataset_action_metadata(action, processor_version=self.processor_version)

        if action.action_type is CorporateActionType.CASH_DIVIDEND:
            if settlement_date is None:
                raise PortfolioLedgerError("cash dividend posting requires settlement_date")
            return ledger.record_cash_dividend(
                event_id=event_id,
                occurred_at=occurred_at,
                ex_date=action.ex_date,
                settlement_date=settlement_date,
                instrument_id=action.instrument_id,
                cash_dividend_per_share=Decimal(str(action.cash_dividend_per_share)),
                corporate_action_id=action_id,
                source_schema=CORPORATE_ACTION_DATASET_SOURCE_SCHEMA,
                metadata=metadata,
            )
        if action.action_type is CorporateActionType.BONUS_SHARE:
            return ledger.record_bonus_share(
                event_id=event_id,
                occurred_at=occurred_at,
                ex_date=action.ex_date,
                instrument_id=action.instrument_id,
                bonus_share_ratio=Decimal(str(action.bonus_share_ratio)),
                corporate_action_id=action_id,
                source_schema=CORPORATE_ACTION_DATASET_SOURCE_SCHEMA,
                metadata=metadata,
            )
        if action.action_type is CorporateActionType.SHARE_SPLIT:
            return ledger.record_share_split(
                event_id=event_id,
                occurred_at=occurred_at,
                ex_date=action.ex_date,
                instrument_id=action.instrument_id,
                split_ratio=Decimal(str(action.split_ratio)),
                corporate_action_id=action_id,
                source_schema=CORPORATE_ACTION_DATASET_SOURCE_SCHEMA,
                metadata=metadata,
            )
        if action.action_type is CorporateActionType.RIGHTS_ISSUE:
            if settlement_date is None:
                raise PortfolioLedgerError("rights issue posting requires settlement_date")
            if action.rights_issue_price is None:
                raise PortfolioLedgerError("rights issue posting requires rights_issue_price")
            return ledger.record_rights_issue(
                event_id=event_id,
                occurred_at=occurred_at,
                ex_date=action.ex_date,
                settlement_date=settlement_date,
                instrument_id=action.instrument_id,
                rights_issue_ratio=Decimal(str(action.rights_issue_ratio)),
                rights_issue_price=Decimal(str(action.rights_issue_price)),
                corporate_action_id=action_id,
                source_schema=CORPORATE_ACTION_DATASET_SOURCE_SCHEMA,
                metadata=metadata,
            )
        raise PortfolioLedgerError(f"unsupported corporate action type: {action.action_type}")

    def apply_delisting_liquidation(
        self,
        ledger: PortfolioLedger,
        *,
        instrument_id: InstrumentId,
        liquidation_date: date,
        settlement_date: date,
        liquidation_price: Decimal | int | str,
        corporate_action_id: str,
        event_id: str,
        occurred_at: datetime,
        metadata: dict[str, object] | None = None,
    ) -> PortfolioLedger:
        if type(ledger) is not PortfolioLedger:
            raise PortfolioLedgerError("ledger must be a PortfolioLedger")
        if type(instrument_id) is not InstrumentId:
            raise PortfolioLedgerError("instrument_id must be an InstrumentId")
        normalized_metadata = {
            "processor_version": self.processor_version,
            "source": "explicit_delisting_liquidation",
        }
        if metadata:
            normalized_metadata.update(metadata)
        return ledger.record_delisting_liquidation(
            event_id=event_id,
            occurred_at=occurred_at,
            liquidation_date=liquidation_date,
            settlement_date=settlement_date,
            instrument_id=instrument_id,
            liquidation_price=liquidation_price,
            corporate_action_id=corporate_action_id,
            source_schema=DELISTING_LIQUIDATION_SOURCE_SCHEMA,
            metadata=normalized_metadata,
        )


def corporate_action_id(action: CorporateAction) -> str:
    if type(action) is not CorporateAction:
        raise PortfolioLedgerError("action must be a CorporateAction")
    return (
        f"ca:{action.instrument_id.canonical}:"
        f"{action.ex_date.isoformat()}:{action.action_type.value}:{action.provider_id}"
    )


def _dataset_action_metadata(action: CorporateAction, *, processor_version: str) -> dict[str, Any]:
    return {
        "processor_version": processor_version,
        "provider_id": action.provider_id,
        "provider_source": action.provider_source,
        "provider_raw_response_sha256": action.provider_raw_response_sha256,
        "source_bronze_artifact_id": action.source_bronze_artifact_id,
        "ex_date": action.ex_date.isoformat(),
        "action_type": action.action_type.value,
    }
