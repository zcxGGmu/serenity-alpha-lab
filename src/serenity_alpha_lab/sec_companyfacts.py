from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .evidence import EvidenceItem


FACT_GROUPS = [
    [("us-gaap", "Revenues", "USD"), ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD")],
    [("us-gaap", "NetIncomeLoss", "USD")],
    [("dei", "EntityCommonStockSharesOutstanding", "shares")],
]


@dataclass(frozen=True)
class CompanyFactSpec:
    ticker: str
    cik: str
    path: Path
    source_url: str | None = None


def load_companyfact_specs(path: Path | str) -> list[CompanyFactSpec]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("SEC companyfacts source manifest must be a JSON array")
    return [_parse_spec(entry, base_dir=manifest_path.parent) for entry in payload]


def load_companyfacts_json(path: Path | str) -> Mapping[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("SEC companyfacts JSON must be an object")
    return payload


def companyfacts_to_evidence(
    payload: Mapping[str, Any],
    *,
    ticker: str,
    source_url: str,
    cik: str | None = None,
    fact_groups: Sequence[Sequence[tuple[str, str, str]]] = FACT_GROUPS,
) -> list[EvidenceItem]:
    normalized_ticker = ticker.upper().lstrip("$")
    if cik is not None:
        _validate_cik(payload, cik)
    items: list[EvidenceItem] = []

    for fact_group in fact_groups:
        selected = _latest_group_fact(payload, fact_group)
        if not selected:
            continue
        namespace, fact_name, unit, fact, latest = selected

        label = str(fact.get("label") or fact_name)
        value = latest["val"]
        fiscal_year = int(latest["fy"])
        filed = date.fromisoformat(str(latest["filed"]))
        accession = str(latest.get("accn") or "")
        items.append(
            EvidenceItem(
                id=_evidence_id(normalized_ticker, namespace, fact_name, fiscal_year, accession),
                source_title=f"SEC companyfacts {normalized_ticker} {label}",
                source_url=source_url,
                published_at=filed,
                claim=f"SEC companyfacts reports {label} for {normalized_ticker} FY{fiscal_year}: {_format_value(value, unit)}.",
                summary=_summary(normalized_ticker, label, fiscal_year, value, unit, accession),
                tickers=[normalized_ticker],
                themes=["SEC companyfacts", "primary-source", _theme_for_fact(fact_name)],
                supply_chain_layer="company financials",
                direction=_direction_for_fact(fact_name, value),
                strength="primary",
                confidence=0.88,
                factor_impacts=_factor_impacts_for_fact(fact_name, value),
                claim_type="fact",
            )
        )

    return items


def _parse_spec(entry: object, *, base_dir: Path) -> CompanyFactSpec:
    if not isinstance(entry, dict):
        raise ValueError("SEC companyfacts manifest entries must be objects")
    ticker = _required_string(entry, "ticker").upper().lstrip("$")
    cik = _required_string(entry, "cik").zfill(10)
    raw_path = Path(_required_string(entry, "path"))
    path = raw_path if raw_path.is_absolute() else base_dir / raw_path
    source_url = entry.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        raise ValueError("source_url must be a string when provided")
    return CompanyFactSpec(ticker=ticker, cik=cik, path=path, source_url=source_url)


def _required_string(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"SEC companyfacts manifest entry requires non-empty {key}")
    return value.strip()


def _validate_cik(payload: Mapping[str, Any], expected_cik: str) -> None:
    payload_cik = payload.get("cik")
    if payload_cik is None:
        raise ValueError("SEC companyfacts payload missing CIK")
    normalized_payload_cik = str(payload_cik).zfill(10)
    normalized_expected_cik = expected_cik.zfill(10)
    if normalized_payload_cik != normalized_expected_cik:
        raise ValueError(f"CIK mismatch: manifest {normalized_expected_cik} does not match payload {normalized_payload_cik}")


def _fact_payload(payload: Mapping[str, Any], namespace: str, fact_name: str) -> Mapping[str, Any] | None:
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return None
    namespace_payload = facts.get(namespace)
    if not isinstance(namespace_payload, dict):
        return None
    fact = namespace_payload.get(fact_name)
    return fact if isinstance(fact, dict) else None


def _latest_group_fact(
    payload: Mapping[str, Any],
    fact_group: Sequence[tuple[str, str, str]],
) -> tuple[str, str, str, Mapping[str, Any], Mapping[str, Any]] | None:
    candidates: list[tuple[str, str, str, Mapping[str, Any], Mapping[str, Any]]] = []
    for namespace, fact_name, unit in fact_group:
        fact = _fact_payload(payload, namespace, fact_name)
        if not fact:
            continue
        unit_values = fact.get("units", {}).get(unit, [])
        if not isinstance(unit_values, list):
            continue
        latest = _latest_annual_filing(unit_values)
        if latest:
            candidates.append((namespace, fact_name, unit, fact, latest))
    if not candidates:
        return None
    return sorted(candidates, key=lambda candidate: _fact_sort_key(candidate[4]), reverse=True)[0]


def _latest_annual_filing(values: Sequence[object]) -> Mapping[str, Any] | None:
    annual_values = [
        value
        for value in values
        if isinstance(value, dict)
        and value.get("fp") == "FY"
        and value.get("form") in {"10-K", "20-F", "40-F"}
        and "fy" in value
        and "filed" in value
        and "val" in value
    ]
    if not annual_values:
        return None
    return sorted(annual_values, key=_fact_sort_key, reverse=True)[0]


def _fact_sort_key(value: Mapping[str, Any]) -> tuple[int, str, str, int]:
    return (int(value["fy"]), str(value["filed"]), str(value.get("end") or ""), _duration_days(value))


def _duration_days(value: Mapping[str, Any]) -> int:
    start = value.get("start")
    end = value.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        return 0
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        return 0


def _summary(ticker: str, label: str, fiscal_year: int, value: object, unit: str, accession: str) -> str:
    accession_text = f" accession {accession}" if accession else ""
    loss_text = " The value is a reported loss." if label.lower().endswith("(loss)") and isinstance(value, (int, float)) and value < 0 else ""
    return (
        f"Primary SEC companyfacts data shows {ticker} FY{fiscal_year} {label} "
        f"of {_format_value(value, unit)} from a filed annual report{accession_text}.{loss_text}"
    )


def _format_value(value: object, unit: str) -> str:
    if isinstance(value, (int, float)):
        if unit == "USD":
            return f"${value:,.0f}"
        return f"{value:,.0f} {unit}"
    return f"{value} {unit}"


def _theme_for_fact(fact_name: str) -> str:
    if fact_name in {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"}:
        return "revenue"
    if fact_name == "NetIncomeLoss":
        return "profitability"
    if fact_name == "EntityCommonStockSharesOutstanding":
        return "share count"
    return fact_name


def _direction_for_fact(fact_name: str, value: object) -> str:
    if fact_name == "NetIncomeLoss" and isinstance(value, (int, float)) and value < 0:
        return "negative"
    return "neutral"


def _factor_impacts_for_fact(fact_name: str, value: object) -> dict[str, int]:
    impacts = {"evidence_quality": 22, "invalidation_clarity": 10}
    if fact_name in {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"}:
        impacts["demand_certainty"] = 8
    if fact_name == "NetIncomeLoss":
        impacts["profitability"] = -8 if isinstance(value, (int, float)) and value < 0 else 8
    return impacts


def _evidence_id(ticker: str, namespace: str, fact_name: str, fiscal_year: int, accession: str) -> str:
    digest = hashlib.sha1(f"{ticker}|{namespace}|{fact_name}|{fiscal_year}|{accession}".encode("utf-8")).hexdigest()[:12]
    return f"sec-companyfacts:{ticker}:{digest}"
