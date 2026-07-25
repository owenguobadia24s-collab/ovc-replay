from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from typing import Mapping, Sequence


REGISTRY_VERSION = "B-LANG-0.1"
PARAMETER_SET_ID = "B-LANG-0.1-SEED"


class Direction(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"


class TermStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class State(StrEnum):
    NEUTRAL = "NEUTRAL"
    COMPRESSED = "COMPRESSED"
    DISPLACING_UP = "DISPLACING_UP"
    DISPLACING_DOWN = "DISPLACING_DOWN"
    AMBIGUOUS = "AMBIGUOUS"


class LevelStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    INVALID = "INVALID"


def dec(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class Bar:
    bar_id: str
    instrument_id: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    price_increment: Decimal = Decimal("0.00001")
    source_id: str = "DUKASCOPY_HISTORICAL"
    source_release_id: str = "fixture"
    price_side: str = "BID"
    status: str = "CLOSED"

    def __post_init__(self) -> None:
        for name in ("open", "high", "low", "close", "price_increment"):
            object.__setattr__(self, name, dec(getattr(self, name)))
        if self.open_time.tzinfo is None or self.close_time.tzinfo is None:
            raise ValueError("bar timestamps must be timezone-aware")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must follow open_time")
        if self.status != "CLOSED":
            raise ValueError("only CLOSED bars are admissible")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC values must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("invalid OHLC envelope")
        if self.price_increment <= 0:
            raise ValueError("price_increment must be positive")
        if self.price_side not in {"BID", "ASK", "MID"}:
            raise ValueError("price_side must be BID, ASK or MID")


@dataclass(frozen=True, slots=True)
class ReferenceLevel:
    level_id: str
    level_type: str
    price: Decimal
    created_at: datetime
    first_valid_time: datetime
    construction_rule_id: str = "fixture-rule"
    construction_rule_version: str = "0.1"
    source_bar_ids: tuple[str, ...] = ()
    instrument_id: str = "GBPUSD"
    timeframe: str = "15M"
    source_release_id: str = "fixture"
    price_side: str = "BID"
    status: LevelStatus = LevelStatus.ACTIVE
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", dec(self.price))
        object.__setattr__(self, "status", LevelStatus(self.status))
        object.__setattr__(self, "source_bar_ids", tuple(self.source_bar_ids))
        if self.created_at.tzinfo is None or self.first_valid_time.tzinfo is None:
            raise ValueError("level timestamps must be timezone-aware")
        if self.first_valid_time < self.created_at:
            raise ValueError("level cannot become valid before creation")
        if self.price <= 0:
            raise ValueError("level price must be positive")
        if self.price_side not in {"BID", "ASK", "MID"}:
            raise ValueError("level price_side must be BID, ASK or MID")
        if self.retired_at is not None:
            if self.retired_at.tzinfo is None:
                raise ValueError("retired_at must be timezone-aware")
            if self.retired_at < self.first_valid_time:
                raise ValueError("level cannot retire before first_valid_time")


@dataclass(frozen=True, slots=True)
class TermRecord:
    term_id: str
    instrument_id: str
    timeframe: str
    direction: Direction
    anchor_time: datetime
    first_valid_time: datetime
    status: TermStatus
    input_bar_ids: tuple[str, ...]
    source_release_id: str
    measurements: Mapping[str, str] = field(default_factory=dict)
    reference_level_id: str | None = None
    reason_codes: tuple[str, ...] = ()
    term_version: str = REGISTRY_VERSION
    parameter_set_id: str = PARAMETER_SET_ID
    term_record_id: str = field(init=False)

    def __post_init__(self) -> None:
        payload = {
            "term_id": self.term_id,
            "term_version": self.term_version,
            "instrument_id": self.instrument_id,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "anchor_time": self.anchor_time.astimezone(timezone.utc).isoformat(),
            "first_valid_time": self.first_valid_time.astimezone(timezone.utc).isoformat(),
            "reference_level_id": self.reference_level_id,
            "input_bar_ids": list(self.input_bar_ids),
            "parameter_set_id": self.parameter_set_id,
            "source_release_id": self.source_release_id,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        object.__setattr__(self, "term_record_id", hashlib.sha256(canonical.encode()).hexdigest())


def assert_compatible_bars(bars: Sequence[Bar]) -> None:
    if not bars:
        raise ValueError("at least one bar is required")
    instrument = bars[0].instrument_id
    timeframe = bars[0].timeframe
    release = bars[0].source_release_id
    previous_close_time: datetime | None = None
    seen: set[str] = set()
    for bar in bars:
        if (bar.instrument_id, bar.timeframe, bar.source_release_id) != (
            instrument,
            timeframe,
            release,
        ):
            raise ValueError("bars must share instrument, timeframe and source release")
        if bar.bar_id in seen:
            raise ValueError("duplicate bar_id")
        if previous_close_time is not None and bar.open_time < previous_close_time:
            raise ValueError("bars must be ordered and non-overlapping")
        if previous_close_time is not None and bar.open_time != previous_close_time:
            raise ValueError("classifier windows must be contiguous")
        seen.add(bar.bar_id)
        previous_close_time = bar.close_time
