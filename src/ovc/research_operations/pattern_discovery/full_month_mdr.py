from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence


PROGRAMME_ID = "PD-JUNE-FULL-MONTH-MDR"
PLAN_ID = "OVC-PD-JUNE-FULL-MONTH-MDR.v0.1"
PLAN_AMENDMENT_ID = "PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER"
PLAN_VERSION = "0.1+A1"
SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
TARGET_START = datetime(2026, 6, 1, tzinfo=timezone.utc)
TARGET_END = datetime(2026, 7, 1, tzinfo=timezone.utc)
EXPECTED_SOURCE_START = datetime(2026, 5, 30, tzinfo=timezone.utc)
EXPECTED_SOURCE_END = datetime(2026, 7, 3, tzinfo=timezone.utc)


@dataclass(frozen=True, order=True)
class HorizonRequirement:
    requirement_id: str
    duration: timedelta
    authority: str

    def as_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "duration_seconds": int(self.duration.total_seconds()),
            "authority": self.authority,
        }


DEFAULT_REQUIREMENTS: tuple[HorizonRequirement, ...] = (
    HorizonRequirement(
        "C2_15M_LEVEL_HISTORY",
        timedelta(minutes=32 * 15),
        "src/ovc/opt_b/c2/levels.py:_PARAMS[15M].range",
    ),
    HorizonRequirement(
        "C2_2H_LEVEL_HISTORY",
        timedelta(hours=24 * 2),
        "src/ovc/opt_b/c2/levels.py:_PARAMS[2H_A_L].range",
    ),
    HorizonRequirement(
        "PREVIOUS_STATE_CONTINUITY",
        timedelta(hours=2),
        "largest evaluated clock",
    ),
    HorizonRequirement(
        "REPEATED_SWITCHING_TRIGGER_HISTORY",
        timedelta(minutes=6 * 15),
        "src/ovc/research_operations/pattern_discovery/evaluation.py:lookback=6",
    ),
    HorizonRequirement(
        "BOUNDED_CANDIDATE_COMPLETION",
        timedelta(hours=48),
        "OVC-PD-JUNE-FULL-MONTH-MDR.v0.1",
    ),
)


def _utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def derive_context_buffer(
    requirements: Iterable[HorizonRequirement] = DEFAULT_REQUIREMENTS,
) -> timedelta:
    items = tuple(requirements)
    if not items:
        raise ValueError("at least one horizon requirement is required")
    if any(item.duration <= timedelta(0) for item in items):
        raise ValueError("horizon durations must be positive")
    return max(item.duration for item in items)


def derive_source_window(
    requirements: Iterable[HorizonRequirement] = DEFAULT_REQUIREMENTS,
) -> tuple[datetime, datetime]:
    buffer = derive_context_buffer(requirements)
    return TARGET_START - buffer, TARGET_END + buffer


def classify_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    current = value.astimezone(timezone.utc)
    source_start, source_end = derive_source_window()
    if current < source_start or current >= source_end:
        return "OUTSIDE_SOURCE"
    if current < TARGET_START:
        return "CONTEXT_PRE_TARGET"
    if current < TARGET_END:
        return "TARGET_JUNE"
    return "CONTEXT_POST_TARGET"


def iter_m1_partition_days(
    start: datetime,
    end: datetime,
) -> tuple[datetime, ...]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("source bounds must be timezone-aware")
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if start_utc.time() != datetime.min.time() or end_utc.time() != datetime.min.time():
        raise ValueError("M1 source bounds must align to UTC day boundaries")
    if end_utc <= start_utc:
        raise ValueError("source end must follow source start")
    days: list[datetime] = []
    cursor = start_utc
    while cursor < end_utc:
        days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def iter_h1_transport_months(
    start: datetime,
    end: datetime,
) -> tuple[datetime, ...]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("source bounds must be timezone-aware")
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if end_utc <= start_utc:
        raise ValueError("source end must follow source start")
    cursor = start_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    final = (end_utc - timedelta(microseconds=1)).replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    months: list[datetime] = []
    while cursor <= final:
        months.append(cursor)
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return tuple(months)


def iter_native_h1_transport_months(
    start: datetime,
    end: datetime,
) -> tuple[datetime, ...]:
    """Return native H1 months retained by operator amendment A1.

    July 2026 native H1 is intentionally not requested because the provider
    object is unavailable. July 1-2 remain M1 context and are aggregated into
    H1 locally from complete M1 hours.
    """

    return tuple(
        month
        for month in iter_h1_transport_months(start, end)
        if month < TARGET_END
    )


def build_source_profile(
    requirements: Sequence[HorizonRequirement] = DEFAULT_REQUIREMENTS,
) -> dict[str, object]:
    source_start, source_end = derive_source_window(requirements)
    buffer = derive_context_buffer(requirements)
    days = iter_m1_partition_days(source_start, source_end)
    native_h1_months = iter_native_h1_transport_months(source_start, source_end)
    profile: dict[str, object] = {
        "schema": "ovc-pd-june-full-month-mdr-source-profile/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": PLAN_VERSION,
        "plan_amendment": PLAN_AMENDMENT_ID,
        "source_slice_id": SOURCE_SLICE_ID,
        "instrument": "GBPUSD",
        "provider": "DUKASCOPY",
        "sides": ["BID", "ASK"],
        "target_start_utc": _utc(TARGET_START),
        "target_end_exclusive_utc": _utc(TARGET_END),
        "source_start_utc": _utc(source_start),
        "source_end_exclusive_utc": _utc(source_end),
        "context_buffer_seconds_each_side": int(buffer.total_seconds()),
        "context_requirements": [item.as_dict() for item in requirements],
        "target_eligibility": "TARGET_JUNE_ONLY",
        "pre_target_class": "CONTEXT_PRE_TARGET",
        "post_target_class": "CONTEXT_POST_TARGET",
        "m1_daily_partition_count_per_side": len(days),
        "m1_daily_partition_dates_utc": [item.strftime("%Y-%m-%d") for item in days],
        "h1_monthly_transport_count_per_side": len(native_h1_months),
        "h1_monthly_transport_months_utc": [
            item.strftime("%Y-%m") for item in native_h1_months
        ],
        "native_july_h1_transport": "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE",
        "post_target_h1_context": "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS",
        "logical_streams": ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        "provider_execution_location": "OPERATOR_LOCAL_ONLY",
        "provider_execution_in_ci": "DENIED",
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
    }
    validate_source_profile(profile)
    return profile


def validate_source_profile(profile: dict[str, object]) -> None:
    source_start, source_end = derive_source_window()
    if source_start != EXPECTED_SOURCE_START or source_end != EXPECTED_SOURCE_END:
        raise AssertionError("derived source window no longer matches the approved plan")
    if profile["target_start_utc"] != _utc(TARGET_START):
        raise AssertionError("target start drift")
    if profile["target_end_exclusive_utc"] != _utc(TARGET_END):
        raise AssertionError("target end drift")
    if profile["source_start_utc"] != _utc(EXPECTED_SOURCE_START):
        raise AssertionError("source start drift")
    if profile["source_end_exclusive_utc"] != _utc(EXPECTED_SOURCE_END):
        raise AssertionError("source end drift")
    if profile["m1_daily_partition_count_per_side"] != 34:
        raise AssertionError("unexpected M1 partition count")
    if profile["h1_monthly_transport_months_utc"] != ["2026-05", "2026-06"]:
        raise AssertionError("unexpected native H1 transport months")
    if profile["native_july_h1_transport"] != (
        "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE"
    ):
        raise AssertionError("July native H1 waiver drift")
    if profile["post_target_h1_context"] != (
        "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS"
    ):
        raise AssertionError("post-target H1 derivation drift")
    if profile["provider_execution_in_ci"] != "DENIED":
        raise AssertionError("provider execution must remain denied in CI")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the deterministic PD-JUNE-FULL-MONTH-MDR source profile."
    )
    parser.add_argument("command", choices=("profile",))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    print(json.dumps(build_source_profile(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
