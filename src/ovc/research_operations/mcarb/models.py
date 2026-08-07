from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any

AUTHORITY = "RESEARCH_ONLY_NO_MARKET_RUN"

def parse_utc(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    result = datetime.fromisoformat(text)
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise ValueError("timestamp must be UTC")
    return result.astimezone(timezone.utc)

def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("non-finite Decimal")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"

@dataclass(frozen=True)
class PriceBar:
    object_id: str
    side: str
    start_utc: str
    end_utc: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    quality_state: str = "COMPLETE"

    def __post_init__(self) -> None:
        if self.side not in {"BID","ASK"}:
            raise ValueError("side must be BID or ASK")
        if parse_utc(self.start_utc) >= parse_utc(self.end_utc):
            raise ValueError("bar interval must be positive")
        if self.high < max(self.open, self.low, self.close) or self.low > min(self.open, self.high, self.close):
            raise ValueError("invalid OHLC ordering")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume must be non-negative")

@dataclass(frozen=True)
class AuxiliaryMeasurement:
    domain: str
    candidate_id: str
    side: str
    interval_start: str
    interval_end: str
    first_valid_time: str
    admissible_cutoff: str
    parent_ids: tuple[str, ...]
    calculation_version: str
    variant_id: str | None
    comparability_domain_id: str
    missingness_state: str
    value: Decimal | str | dict[str, Any] | None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.domain not in {"AL","ET","VS"}:
            raise ValueError("invalid domain")
        if self.side not in {"BID","ASK"}:
            raise ValueError("invalid side")
        end = parse_utc(self.interval_end)
        first = parse_utc(self.first_valid_time)
        cutoff = parse_utc(self.admissible_cutoff)
        if first < end:
            raise ValueError("first_valid_time cannot precede interval end")
        if first > cutoff:
            raise ValueError("measurement exceeds admissible cutoff")

    @property
    def record_id(self) -> str:
        return "MCARB.M." + canonical_hash(self.to_identity())[:24]

    def to_identity(self) -> dict[str, Any]:
        return {
            "domain": self.domain, "candidate_id": self.candidate_id, "side": self.side,
            "interval_start": self.interval_start, "interval_end": self.interval_end,
            "first_valid_time": self.first_valid_time, "parent_ids": list(self.parent_ids),
            "calculation_version": self.calculation_version, "variant_id": self.variant_id,
            "comparability_domain_id": self.comparability_domain_id,
            "missingness_state": self.missingness_state,
            "value": decimal_text(self.value) if isinstance(self.value, Decimal) else self.value,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id, "instrument_id": "GBPUSD", **self.to_identity(),
            "admissible_cutoff": self.admissible_cutoff,
            "reason_codes": list(self.reason_codes), "authority": AUTHORITY,
        }
