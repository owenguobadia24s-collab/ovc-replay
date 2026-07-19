from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import csv
import hashlib
from pathlib import Path
from typing import Iterable, Sequence

from ..models import Bar


SUPPORTED_TIME_FORMATS = (
    "%d.%m.%Y %H:%M:%S.%f",
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)


@dataclass(frozen=True, slots=True)
class RejectedBucket:
    bucket_start: datetime
    expected_bars: int
    observed_bars: int
    reason: str


@dataclass(frozen=True, slots=True)
class AggregationResult:
    accepted: tuple[Bar, ...]
    rejected: tuple[RejectedBucket, ...]


def _parse_timestamp(value: str) -> datetime:
    cleaned = value.strip().replace(" GMT", "").replace(" UTC", "")
    if cleaned.isdigit():
        epoch = int(cleaned)
        seconds = Decimal(epoch) / (Decimal(1000) if epoch >= 1_000_000_000_000 else Decimal(1))
        return datetime.fromtimestamp(float(seconds), tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in SUPPORTED_TIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unsupported Dukascopy timestamp: {value!r}")


def _timestamp_field(row: dict[str, str]) -> str:
    normalized = {key.strip().lower().replace("_", " "): value for key, value in row.items() if key}
    for key in ("local time", "timestamp", "time", "utc", "gmt"):
        if key in normalized and normalized[key] != "":
            return normalized[key]
    timezone_columns = [value for key, value in row.items() if key and "/" in key and value]
    if len(timezone_columns) == 1:
        return timezone_columns[0]
    raise ValueError("missing or ambiguous timestamp column")


def _field(row: dict[str, str], *names: str) -> str:
    normalized = {key.strip().lower().replace("_", " "): value for key, value in row.items() if key}
    for name in names:
        key = name.lower().replace("_", " ")
        if key in normalized and normalized[key] != "":
            return normalized[key]
    raise ValueError(f"missing CSV field; expected one of {names}")


def read_dukascopy_csv(
    path: str | Path,
    *,
    instrument_id: str = "GBPUSD",
    price_side: str = "BID",
    source_release_id: str,
    source_timeframe: str = "1M",
    price_increment: Decimal = Decimal("0.00001"),
) -> tuple[Bar, ...]:
    """Read a Dukascopy OHLC export and normalize timestamps to UTC."""
    if price_side not in {"BID", "ASK"}:
        raise ValueError("Dukascopy CSV adapter accepts BID or ASK, not inferred MID")
    durations = {"1M": timedelta(minutes=1), "1H": timedelta(hours=1)}
    if source_timeframe not in durations:
        raise ValueError("source_timeframe must be 1M or 1H")
    csv_path = Path(path)
    text = csv_path.read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;")
    rows = csv.DictReader(text.splitlines(), dialect=dialect)
    result: list[Bar] = []
    for index, row in enumerate(rows):
        open_time = _parse_timestamp(_timestamp_field(row))
        close_time = open_time + durations[source_timeframe]
        bar = Bar(
            bar_id=f"dukascopy:{source_release_id}:{instrument_id}:{source_timeframe}:{price_side}:{open_time.isoformat()}",
            instrument_id=instrument_id,
            timeframe=source_timeframe,
            open_time=open_time,
            close_time=close_time,
            open=Decimal(_field(row, "Open")),
            high=Decimal(_field(row, "High")),
            low=Decimal(_field(row, "Low")),
            close=Decimal(_field(row, "Close")),
            price_increment=price_increment,
            source_id="DUKASCOPY_HISTORICAL_EXPORT",
            source_release_id=source_release_id,
            price_side=price_side,
        )
        if result and bar.open_time <= result[-1].open_time:
            raise ValueError(f"CSV timestamps must be strictly increasing; row {index + 2}")
        result.append(bar)
    if not result:
        raise ValueError("Dukascopy CSV contains no data rows")
    return tuple(result)


def _bucket_start(value: datetime, minutes: int) -> datetime:
    epoch_minutes = int(value.timestamp()) // 60
    floored = epoch_minutes - (epoch_minutes % minutes)
    return datetime.fromtimestamp(floored * 60, tz=timezone.utc)


def _aggregate_bucket(bars: Sequence[Bar], timeframe: str, minutes: int, bucket: datetime) -> Bar:
    source_ids = "|".join(bar.bar_id for bar in bars)
    digest = hashlib.sha256(source_ids.encode()).hexdigest()[:24]
    return Bar(
        bar_id=f"agg:{timeframe}:{bucket.isoformat()}:{digest}",
        instrument_id=bars[0].instrument_id,
        timeframe=timeframe,
        open_time=bucket,
        close_time=bucket + timedelta(minutes=minutes),
        open=bars[0].open,
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
        price_increment=bars[0].price_increment,
        source_id=bars[0].source_id,
        source_release_id=bars[0].source_release_id,
        price_side=bars[0].price_side,
    )


def aggregate_bars(bars: Iterable[Bar], *, target_timeframe: str) -> AggregationResult:
    """Aggregate supported complete UTC buckets without filling missing inputs."""
    source = tuple(bars)
    if not source:
        raise ValueError("aggregation requires bars")
    specifications = {
        ("1M", "15M"): (15, 15),
        ("15M", "2H"): (120, 8),
        ("1H", "2H"): (120, 2),
    }
    key = (source[0].timeframe, target_timeframe)
    if key not in specifications:
        raise ValueError(f"unsupported aggregation {key[0]}->{key[1]}")
    minutes, expected_count = specifications[key]
    identity = (source[0].instrument_id, source[0].source_id, source[0].source_release_id, source[0].price_side)
    groups: dict[datetime, list[Bar]] = {}
    previous_time: datetime | None = None
    for bar in source:
        if (bar.instrument_id, bar.source_id, bar.source_release_id, bar.price_side) != identity:
            raise ValueError("aggregation inputs must share source identity and price side")
        if bar.timeframe != key[0]:
            raise ValueError("mixed source timeframes")
        if previous_time is not None and bar.open_time <= previous_time:
            raise ValueError("aggregation inputs must be strictly ordered")
        previous_time = bar.open_time
        groups.setdefault(_bucket_start(bar.open_time, minutes), []).append(bar)
    accepted: list[Bar] = []
    rejected: list[RejectedBucket] = []
    source_minutes = {"1M": 1, "15M": 15, "1H": 60}[key[0]]
    for bucket, members in sorted(groups.items()):
        expected_times = {bucket + timedelta(minutes=source_minutes * i) for i in range(expected_count)}
        observed_times = {member.open_time for member in members}
        if len(members) != expected_count or observed_times != expected_times:
            rejected.append(RejectedBucket(bucket, expected_count, len(members), "INCOMPLETE_OR_MISALIGNED_BUCKET"))
            continue
        accepted.append(_aggregate_bucket(members, target_timeframe, minutes, bucket))
    return AggregationResult(tuple(accepted), tuple(rejected))
