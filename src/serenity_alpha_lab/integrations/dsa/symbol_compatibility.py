from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from serenity_alpha_lab.domain.instruments import (
    InstrumentId,
    InvalidInstrumentSymbol,
    Market,
    ProviderSymbolMapping,
    UnsupportedProvider,
)


StockCodeNormalizer = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class DsaStockCodeMapping:
    """Instrument-backed mapping for DSA legacy stock-code compatibility."""

    raw_symbol: str
    instrument_id: InstrumentId
    legacy_stock_code: str
    dsa_symbol: str
    provider_mappings: Sequence[ProviderSymbolMapping]
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        raw_symbol = _required_string("raw_symbol", self.raw_symbol)
        legacy_stock_code = _required_string("legacy_stock_code", self.legacy_stock_code)
        dsa_symbol = _required_string("dsa_symbol", self.dsa_symbol)
        if type(self.instrument_id) is not InstrumentId:
            raise TypeError("DsaStockCodeMapping requires an InstrumentId")

        mappings = tuple(self.provider_mappings)
        if not mappings:
            raise ValueError("provider_mappings is required")
        seen_providers: set[str] = set()
        for mapping in mappings:
            if type(mapping) is not ProviderSymbolMapping:
                raise TypeError("provider_mappings must contain ProviderSymbolMapping values")
            if mapping.instrument_id != self.instrument_id:
                raise ValueError("provider mapping instrument_id must match mapping instrument_id")
            if mapping.provider in seen_providers:
                raise ValueError(f"duplicate provider mapping: {mapping.provider}")
            seen_providers.add(mapping.provider)

        if self.valid_from is not None and type(self.valid_from) is not date:
            raise TypeError("valid_from must be a date")
        if self.valid_to is not None and type(self.valid_to) is not date:
            raise TypeError("valid_to must be a date")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot be before valid_from")

        object.__setattr__(self, "raw_symbol", raw_symbol)
        object.__setattr__(self, "legacy_stock_code", legacy_stock_code)
        object.__setattr__(self, "dsa_symbol", dsa_symbol)
        object.__setattr__(self, "provider_mappings", mappings)

    def provider_symbol(self, provider: str) -> str:
        provider_id = _normalize_provider(provider)
        for mapping in self.provider_mappings:
            if mapping.provider == provider_id:
                return mapping.symbol
        raise UnsupportedProvider(f"Unsupported provider mapping: {provider}")


class DsaStockCodeCompatibilityMapper:
    """Map legacy DSA stock-code strings to canonical Serenity instruments."""

    def __init__(self, *, normalize_stock_code: StockCodeNormalizer | None = None) -> None:
        self._normalize_stock_code = normalize_stock_code or normalize_stock_code_compatible

    def from_legacy(
        self,
        stock_code: str,
        *,
        market: Market | str | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
    ) -> DsaStockCodeMapping:
        raw_symbol = _required_string("stock_code", stock_code)
        instrument = InstrumentId.from_legacy(raw_symbol, market=market)
        return self.from_instrument(
            instrument,
            raw_symbol=raw_symbol,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def from_instrument(
        self,
        instrument: InstrumentId,
        *,
        raw_symbol: str | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
    ) -> DsaStockCodeMapping:
        if type(instrument) is not InstrumentId:
            raise TypeError("from_instrument requires an InstrumentId")
        dsa_symbol = instrument.to_dsa_symbol()
        legacy_stock_code = self._normalize_stock_code(dsa_symbol)
        expected_legacy = normalize_stock_code_compatible(dsa_symbol)
        if legacy_stock_code != expected_legacy:
            raise InvalidInstrumentSymbol(
                f"normalize_stock_code produced {legacy_stock_code!r} for "
                f"{instrument.canonical}, expected {expected_legacy!r}"
            )
        return DsaStockCodeMapping(
            raw_symbol=raw_symbol or instrument.canonical,
            instrument_id=instrument,
            legacy_stock_code=legacy_stock_code,
            dsa_symbol=dsa_symbol,
            provider_mappings=_provider_mappings(instrument),
            valid_from=valid_from,
            valid_to=valid_to,
        )


def normalize_stock_code_compatible(stock_code: str) -> str:
    """Local compatibility mirror of DSA v3.26.1 normalize_stock_code()."""

    code = str(stock_code).strip()
    upper = code.upper()

    if upper.startswith("HK") and not upper.startswith("HK."):
        candidate = upper[2:]
        if candidate.isdigit() and 1 <= len(candidate) <= 5:
            return f"HK{candidate.zfill(5)}"

    if upper.startswith(("SH", "SZ", "SS")) and not upper.startswith(("SH.", "SZ.", "SS.")):
        candidate = code[2:]
        if candidate.isdigit() and len(candidate) in (5, 6):
            return candidate

    if upper.startswith(("SH.", "SZ.", "SS.")):
        candidate = code[3:]
        if candidate.isdigit() and len(candidate) in (5, 6):
            return candidate

    if upper.startswith("BJ") and not upper.startswith("BJ."):
        candidate = code[2:]
        if candidate.isdigit() and len(candidate) == 6:
            return candidate

    if upper.startswith("BJ."):
        candidate = code[3:]
        if candidate.isdigit() and len(candidate) == 6:
            return candidate

    if "." in code:
        base, suffix = code.rsplit(".", 1)
        suffix_upper = suffix.upper()
        if suffix_upper == "T" and base.isdigit() and len(base) in (4, 5):
            return f"{base}.{suffix_upper}"
        if suffix_upper in {"KS", "KQ"} and base.isdigit() and len(base) == 6:
            return f"{base}.{suffix_upper}"
        if suffix_upper in {"TW", "TWO"} and base.isdigit() and 4 <= len(base) <= 6:
            return f"{base}.{suffix_upper}"
        if suffix_upper == "HK" and base.isdigit() and 1 <= len(base) <= 5:
            return f"HK{base.zfill(5)}"
        if base.upper() in {"SH", "SS", "SZ", "BJ"} and suffix.isdigit():
            return suffix
        if suffix_upper in {"SH", "SZ", "SS", "BJ"} and base.isdigit():
            return base

    return code


def _provider_mappings(instrument: InstrumentId) -> tuple[ProviderSymbolMapping, ...]:
    return (
        instrument.to_provider_symbol("dsa"),
        instrument.to_provider_symbol("yahoo"),
    )


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_provider(provider: str) -> str:
    provider_id = str(provider or "").strip().lower()
    if not provider_id:
        raise UnsupportedProvider("provider is required")
    return provider_id


__all__ = [
    "DsaStockCodeCompatibilityMapper",
    "DsaStockCodeMapping",
    "StockCodeNormalizer",
    "normalize_stock_code_compatible",
]
