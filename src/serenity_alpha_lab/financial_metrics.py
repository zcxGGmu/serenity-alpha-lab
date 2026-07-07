from __future__ import annotations

import json
import re
from typing import Iterable

from .evidence import EvidenceItem


METRIC_FIELDS = ["revenue_growth", "gross_margin", "valuation", "momentum", "cycle_position"]


def build_metrics_catalog(evidence: Iterable[EvidenceItem]) -> list[dict[str, str]]:
    by_ticker: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        if item.strength != "primary" or item.claim_type != "fact":
            continue
        for ticker in item.tickers:
            normalized = ticker.upper().lstrip("$")
            by_ticker.setdefault(normalized, []).append(item)

    rows: list[dict[str, str]] = []
    for ticker in sorted(by_ticker):
        items = by_ticker[ticker]
        revenue_growth = _revenue_growth(items)
        momentum = _momentum(items)
        rows.append(
            {
                "ticker": ticker,
                "revenue_growth": revenue_growth,
                "gross_margin": "n/a",
                "valuation": "n/a",
                "momentum": momentum,
                "cycle_position": _cycle_position(revenue_growth, momentum),
            }
        )
    return rows


def render_metrics_catalog_json(catalog: list[dict[str, str]]) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"


def _revenue_growth(items: list[EvidenceItem]) -> str:
    official = _latest_item(
        item
        for item in items
        if _is_revenue_item(item)
        and _is_official_report_item(item)
        and _extract_percent(item.claim + " " + item.summary)
    )
    if official:
        return f"{_extract_percent(official.claim + ' ' + official.summary)} YoY official report"

    revenue = _latest_item(item for item in items if _is_revenue_item(item))
    if revenue:
        value = _extract_money(revenue.claim + " " + revenue.summary)
        if value:
            return f"source-backed revenue {value}"
    return "n/a"


def _momentum(items: list[EvidenceItem]) -> str:
    profitability = _latest_item(item for item in items if _is_profitability_item(item))
    if not profitability:
        return "n/a"
    text = f"{profitability.claim} {profitability.summary}".lower()
    money_value = _extract_first_money_value(text)
    if money_value is not None:
        return "reported loss" if money_value < 0 else "reported profitable"
    if profitability.direction == "negative" or "reported loss" in text or "$-" in text:
        return "reported loss"
    return "reported profitable"


def _cycle_position(revenue_growth: str, momentum: str) -> str:
    if revenue_growth != "n/a" and momentum == "reported loss":
        return "revenue ramp / loss-making"
    if revenue_growth != "n/a":
        return "source-backed revenue base"
    if momentum != "n/a":
        return "profitability watch"
    return "n/a"


def _is_revenue_item(item: EvidenceItem) -> bool:
    text = " ".join([item.claim, item.summary, item.source_title, " ".join(item.themes)]).lower()
    return "revenue" in text or "net sales" in text


def _is_profitability_item(item: EvidenceItem) -> bool:
    text = " ".join([item.claim, item.summary, item.source_title, " ".join(item.themes)]).lower()
    return "net income" in text or "profitability" in text or "profit after tax" in text


def _is_official_report_item(item: EvidenceItem) -> bool:
    text = " ".join([item.id, item.source_title, " ".join(item.themes)]).lower()
    return "official-report" in text or "annual-report" in text or "annual report" in text


def _latest_item(items: Iterable[EvidenceItem]) -> EvidenceItem | None:
    candidates = list(items)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.published_at, item.id), reverse=True)[0]


def _extract_percent(text: str) -> str:
    match = re.search(r"(?<![\d.])(-?\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return ""
    value = match.group(1)
    return f"{value}%"


def _extract_money(text: str) -> str:
    match = re.search(r"\$(-?\d[\d,]*(?:\.\d+)?)", text)
    if not match:
        return ""
    value = float(match.group(1).replace(",", ""))
    return _format_money_value(value)


def _extract_first_money_value(text: str) -> float | None:
    match = re.search(r"\$(-?\d[\d,]*(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _format_money_value(value: float) -> str:
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000_000:
        return f"${sign}{abs_value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"${sign}{abs_value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"${sign}{abs_value / 1_000:.1f}K"
    return f"${sign}{abs_value:.0f}"
