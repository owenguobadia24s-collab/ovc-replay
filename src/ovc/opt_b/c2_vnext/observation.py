"""Deterministic C2 vNext observation, calendar, lattice and continuity foundation.

This package is shadow-only. It creates no active selector, release, parent,
semantic, probability, risk, exposure or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

UTC = timezone.utc
SIDES = ("BID", "ASK")
EXPECTATION_STATUSES = (
    "EXPECTED_EVIDENCE", "SCHEDULED_CLOSURE", "EXCEPTIONAL_CLOSURE",
    "OUTSIDE_EFFECTIVE_RANGE",
)
EVIDENCE_STATUSES = (
    "PRESENT_COMPLETE", "PRESENT_INCOMPLETE", "ABSENT", "CORRUPT",
    "UNKNOWN_ABSENCE", "NOT_EXPECTED",
)
CONTINUITY_STATUSES = (
    "SEGMENT_START", "CONTIGUOUS", "GAP_RESET", "CLOSURE_BOUNDARY",
    "PARTITION_BOUNDARY", "UNKNOWN_BREAK",
)
PROHIBITED_CAUSAL_KEYS = {
    "parent_id", "parent_state", "future", "future_value", "outcome",
    "forward_outcome", "next_state",
}


class ObservationContractError(ValueError):
    """Raised when a normative observation invariant is violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise ObservationContractError(marker)


def parse_time(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{hashlib.sha256(canonical_bytes(value)).hexdigest()[:length]}"


def _aligned(value: datetime, minutes: int) -> bool:
    return value.second == 0 and value.microsecond == 0 and value.minute % minutes == 0


@dataclass(frozen=True)
class ClosureInterval:
    start: datetime
    end: datetime
    closure_id: str
    classification: str = "EXCEPTIONAL_CLOSURE"
    source_ref: str = "FIXTURE_ONLY"

    def __post_init__(self) -> None:
        _require(self.start.tzinfo is not None and self.end.tzinfo is not None, "CLOSURE_TIMEZONE")
        _require(parse_time(self.start) < parse_time(self.end), "CLOSURE_INTERVAL")
        _require(self.classification in {"EXCEPTIONAL_CLOSURE", "SCHEDULED_CLOSURE"}, "CLOSURE_CLASS")

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return parse_time(start) < parse_time(self.end) and parse_time(self.start) < parse_time(end)


@dataclass(frozen=True)
class InstrumentCalendar:
    calendar_id: str
    instrument: str
    timezone_name: str
    effective_start: datetime
    effective_end: datetime
    weekly_close_weekday: int = 4
    weekly_close_hour: int = 17
    weekly_open_weekday: int = 6
    weekly_open_hour: int = 17
    exceptional_closures: tuple[ClosureInterval, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require(parse_time(self.effective_start) < parse_time(self.effective_end), "CALENDAR_EFFECTIVE_RANGE")
        _require(bool(self.source_refs), "CALENDAR_SOURCE_REF")

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def _weekly_closed(self, instant: datetime) -> bool:
        local = instant.astimezone(self.zone)
        wd = local.weekday()
        clock = (local.hour, local.minute, local.second, local.microsecond)
        close_clock = (self.weekly_close_hour, 0, 0, 0)
        open_clock = (self.weekly_open_hour, 0, 0, 0)
        if wd == self.weekly_close_weekday and clock >= close_clock:
            return True
        if self.weekly_close_weekday < wd < self.weekly_open_weekday:
            return True
        if wd == self.weekly_open_weekday and clock < open_clock:
            return True
        return False

    def classify(self, start: datetime, end: datetime) -> dict[str, Any]:
        start = parse_time(start)
        end = parse_time(end)
        _require(start < end, "CALENDAR_INTERVAL")
        if start < parse_time(self.effective_start) or end > parse_time(self.effective_end):
            return {"status": "OUTSIDE_EFFECTIVE_RANGE", "calendar_id": self.calendar_id,
                    "closure_id": None, "source_refs": list(self.source_refs)}
        matches = [item for item in self.exceptional_closures if item.overlaps(start, end)]
        _require(len(matches) <= 1, "OVERLAPPING_CALENDAR_CLOSURES")
        if matches:
            item = matches[0]
            return {"status": item.classification, "calendar_id": self.calendar_id,
                    "closure_id": item.closure_id,
                    "source_refs": [item.source_ref, *self.source_refs]}
        end_probe = end - timedelta(microseconds=1)
        start_closed = self._weekly_closed(start)
        end_closed = self._weekly_closed(end_probe)
        _require(start_closed == end_closed, "SLOT_STRADDLES_CALENDAR_BOUNDARY")
        return {"status": "SCHEDULED_CLOSURE" if start_closed else "EXPECTED_EVIDENCE",
                "calendar_id": self.calendar_id,
                "closure_id": "WEEKLY.FX.NY_1700" if start_closed else None,
                "source_refs": list(self.source_refs)}


@dataclass(frozen=True)
class LatticeProfile:
    lattice_id: str
    interval_minutes: int
    anchor_minute_utc: int
    maturity: str
    active: bool = False

    def __post_init__(self) -> None:
        _require(self.interval_minutes > 0, "LATTICE_INTERVAL")
        _require(0 <= self.anchor_minute_utc < 24 * 60, "LATTICE_ANCHOR")
        _require(self.maturity in {"NORMATIVE_BOUNDARY", "SHADOW_EXPERIMENT"}, "LATTICE_MATURITY")
        _require(not self.active, "LATTICE_ACTIVATION_DENIED")

    def membership(self, observation_id: str, start: datetime, end: datetime) -> dict[str, Any]:
        start = parse_time(start)
        end = parse_time(end)
        epoch = datetime(1970, 1, 1, tzinfo=UTC)
        minutes = int((start - epoch).total_seconds() // 60)
        shifted = minutes - self.anchor_minute_utc
        bucket_number = shifted // self.interval_minutes
        bucket_start = epoch + timedelta(minutes=bucket_number * self.interval_minutes + self.anchor_minute_utc)
        bucket_end = bucket_start + timedelta(minutes=self.interval_minutes)
        _require(bucket_start <= start < end <= bucket_end, "OBSERVATION_CROSSES_LATTICE_BUCKET")
        identity = {"lattice_id": self.lattice_id, "observation_id": observation_id,
                    "bucket_start": iso(bucket_start), "bucket_end": iso(bucket_end)}
        return {"membership_id": digest("C2.LATTICE.MEMBERSHIP", identity), **identity,
                "maturity": self.maturity, "authority": "REFERENCE_ONLY"}


def default_gbpusd_calendar() -> InstrumentCalendar:
    return InstrumentCalendar(
        calendar_id="OVC.CALENDAR.GBPUSD.NY_1700.v1", instrument="GBPUSD",
        timezone_name="America/New_York",
        effective_start=datetime(2020, 1, 1, tzinfo=UTC),
        effective_end=datetime(2031, 1, 1, tzinfo=UTC),
        source_refs=("OVC_CALENDAR_POLICY_GBPUSD_v1",),
    )


def baseline_lattices() -> tuple[LatticeProfile, ...]:
    return (
        LatticeProfile("LATTICE.15M.UTC_0000.v1", 15, 0, "NORMATIVE_BOUNDARY"),
        LatticeProfile("LATTICE.2H.UTC_0000.v1", 120, 0, "NORMATIVE_BOUNDARY"),
    )


def alternative_lattices() -> tuple[LatticeProfile, ...]:
    return (LatticeProfile("LATTICE.2H.UTC_0100.v1", 120, 60, "SHADOW_EXPERIMENT"),)


def enumerate_slots(start: str | datetime, end: str | datetime, *, instrument: str,
                    calendar: InstrumentCalendar, sides: Sequence[str] = SIDES,
                    interval_minutes: int = 15, partition_id: str = "DEFAULT") -> list[dict[str, Any]]:
    start_dt = parse_time(start)
    end_dt = parse_time(end)
    _require(calendar.instrument == instrument, "CALENDAR_INSTRUMENT")
    _require(start_dt < end_dt, "ENUMERATION_RANGE")
    _require(_aligned(start_dt, interval_minutes) and _aligned(end_dt, interval_minutes), "SLOT_ALIGNMENT")
    _require(len(sides) == len(set(sides)) and all(side in SIDES for side in sides), "SIDE_SET")
    slots: list[dict[str, Any]] = []
    cursor = start_dt
    while cursor < end_dt:
        slot_end = cursor + timedelta(minutes=interval_minutes)
        _require(slot_end <= end_dt, "PARTIAL_SLOT")
        expectation = calendar.classify(cursor, slot_end)
        for side in sides:
            identity = {"instrument": instrument, "side": side,
                        "interval_start": iso(cursor), "interval_end": iso(slot_end),
                        "partition_id": partition_id}
            slots.append({"slot_id": digest("C2.SLOT", identity), **identity,
                          "expectation": expectation})
        cursor = slot_end
    _require(len({slot["slot_id"] for slot in slots}) == len(slots), "DUPLICATE_SLOT_ID")
    return slots


def _evidence_index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in rows:
        row = copy.deepcopy(dict(raw))
        for key in PROHIBITED_CAUSAL_KEYS:
            _require(key not in row, f"PROHIBITED_CAUSAL_KEY:{key}")
        side = row.get("side")
        _require(side in SIDES, "EVIDENCE_SIDE")
        start = iso(parse_time(row["interval_start"]))
        end = iso(parse_time(row["interval_end"]))
        _require(parse_time(start) < parse_time(end), "EVIDENCE_INTERVAL")
        key = (start, end, side)
        _require(key not in result, "DUPLICATE_EVIDENCE")
        row["interval_start"] = start
        row["interval_end"] = end
        result[key] = row
    return result


def bind_evidence(slots: Sequence[Mapping[str, Any]], evidence_rows: Sequence[Mapping[str, Any]], *,
                  lattices: Sequence[LatticeProfile] | None = None,
                  absence_classes: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    lattices = tuple(lattices or baseline_lattices())
    absence_classes = dict(absence_classes or {})
    indexed = _evidence_index(evidence_rows)
    slot_keys = {(slot["interval_start"], slot["interval_end"], slot["side"]): slot["slot_id"]
                 for slot in slots}
    _require(not sorted(set(indexed) - set(slot_keys)), "UNEXPECTED_EVIDENCE_INTERVAL")
    observations: list[dict[str, Any]] = []
    for slot_raw in slots:
        slot = copy.deepcopy(dict(slot_raw))
        key = (slot["interval_start"], slot["interval_end"], slot["side"])
        row = indexed.get(key)
        expectation_status = slot["expectation"]["status"]
        evidence_reason: str | None = None
        if expectation_status in {"SCHEDULED_CLOSURE", "EXCEPTIONAL_CLOSURE", "OUTSIDE_EFFECTIVE_RANGE"}:
            if row is None:
                evidence_status = "NOT_EXPECTED"
            else:
                evidence_status = "CORRUPT"
                evidence_reason = "EVIDENCE_DURING_NON_OPEN_INTERVAL"
        elif row is None:
            absence_class = absence_classes.get(slot["slot_id"], "PROVIDER_ABSENCE")
            if absence_class == "UNKNOWN":
                evidence_status = "UNKNOWN_ABSENCE"
                evidence_reason = "UNKNOWN_ABSENCE"
            else:
                _require(absence_class in {"PROVIDER_ABSENCE", "SOURCE_GAP"}, "ABSENCE_CLASS")
                evidence_status = "ABSENT"
                evidence_reason = absence_class
        elif bool(row.get("corrupt", False)):
            evidence_status = "CORRUPT"
            evidence_reason = str(row.get("reason") or "SOURCE_CORRUPTION")
        elif not bool(row.get("complete", True)):
            evidence_status = "PRESENT_INCOMPLETE"
            evidence_reason = str(row.get("reason") or "INCOMPLETE_SOURCE_EVIDENCE")
        else:
            evidence_status = "PRESENT_COMPLETE"
        eligible = expectation_status == "EXPECTED_EVIDENCE" and evidence_status == "PRESENT_COMPLETE"
        identity = {"schema": "c2_observation/vnext-r1", "instrument": slot["instrument"],
                    "side": slot["side"], "interval_start": slot["interval_start"],
                    "interval_end": slot["interval_end"], "slot_id": slot["slot_id"],
                    "calendar_id": slot["expectation"]["calendar_id"],
                    "partition_id": slot["partition_id"]}
        observation_id = digest("C2.OBSERVATION", identity)
        memberships = [profile.membership(observation_id, parse_time(slot["interval_start"]),
                                          parse_time(slot["interval_end"])) for profile in lattices]
        lineage = {"opt_a_release_id": row.get("opt_a_release_id") if row else None,
                   "opt_a_record_id": row.get("opt_a_record_id") if row else None,
                   "c1_release_id": row.get("c1_release_id") if row else None,
                   "c1_record_id": row.get("c1_record_id") if row else None}
        record = {
            "schema": "c2_observation/vnext-r1", "observation_id": observation_id,
            "instrument": slot["instrument"], "side": slot["side"],
            "interval_start": slot["interval_start"], "interval_end": slot["interval_end"],
            "first_valid_time": slot["interval_end"], "slot_id": slot["slot_id"],
            "partition_id": slot["partition_id"], "calendar": slot["expectation"],
            "expectation": {"status": expectation_status},
            "evidence": {"status": evidence_status, "reason": evidence_reason,
                         "source_record_id": row.get("source_record_id") if row else None},
            "projection_eligibility": {"eligible": eligible,
                                       "reason": None if eligible else f"{expectation_status}:{evidence_status}"},
            "lineage": lineage, "continuity": {"status": None, "segment_id": None},
            "lattice_memberships": memberships, "maturity": "SHADOW_EXPERIMENT",
            "authority": {"active_selector": "NONE", "release": "NONE",
                          "publication": "NONE", "semantic": "NONE"},
        }
        record["content_sha256"] = hashlib.sha256(canonical_bytes(record)).hexdigest()
        observations.append(record)
    _require(len(observations) == len(slots), "SLOT_OBSERVATION_CARDINALITY")
    _require(len({item["slot_id"] for item in observations}) == len(slots), "SLOT_ACCOUNTED_MORE_THAN_ONCE")
    return observations


def assign_continuity(observations: Sequence[Mapping[str, Any]], *,
                      partition_boundary_starts: Iterable[str | datetime] = ()) -> list[dict[str, Any]]:
    boundary_set = {iso(parse_time(value)) for value in partition_boundary_starts}
    copied = [copy.deepcopy(dict(value)) for value in observations]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in copied:
        groups.setdefault((item["instrument"], item["side"]), []).append(item)
    output: list[dict[str, Any]] = []
    for group_key, items in sorted(groups.items()):
        items.sort(key=lambda x: (x["interval_start"], x["observation_id"]))
        active_segment: str | None = None
        previous_end: str | None = None
        previous_eligible = False
        segment_ordinal = 0
        for item in items:
            start = item["interval_start"]
            expectation = item["expectation"]["status"]
            evidence = item["evidence"]["status"]
            eligible = bool(item["projection_eligibility"]["eligible"])
            if start in boundary_set:
                status = "PARTITION_BOUNDARY"; active_segment = None; previous_eligible = False
            elif expectation in {"SCHEDULED_CLOSURE", "EXCEPTIONAL_CLOSURE"}:
                status = "CLOSURE_BOUNDARY"; active_segment = None; previous_eligible = False
            elif evidence == "UNKNOWN_ABSENCE":
                status = "UNKNOWN_BREAK"; active_segment = None; previous_eligible = False
            elif not eligible:
                status = "GAP_RESET"; active_segment = None; previous_eligible = False
            elif previous_eligible and previous_end == start and active_segment is not None:
                status = "CONTIGUOUS"
            else:
                status = "SEGMENT_START"
                segment_ordinal += 1
                active_segment = digest("C2.CONTINUITY.SEGMENT",
                                        {"instrument": group_key[0], "side": group_key[1],
                                         "start": start, "ordinal": segment_ordinal})
            item["continuity"] = {"status": status, "segment_id": active_segment if eligible else None}
            item["content_sha256"] = hashlib.sha256(canonical_bytes(
                {k: v for k, v in item.items() if k != "content_sha256"})).hexdigest()
            output.append(item)
            previous_end = item["interval_end"]
            previous_eligible = eligible
    output.sort(key=lambda x: (x["interval_start"], x["side"], x["observation_id"]))
    return output


def build_population(start: str | datetime, end: str | datetime, *, instrument: str,
                     calendar: InstrumentCalendar, evidence_rows: Sequence[Mapping[str, Any]],
                     sides: Sequence[str] = SIDES, lattices: Sequence[LatticeProfile] | None = None,
                     absence_classes: Mapping[str, str] | None = None,
                     partition_id: str = "DEFAULT",
                     partition_boundary_starts: Iterable[str | datetime] = ()) -> dict[str, Any]:
    slots = enumerate_slots(start, end, instrument=instrument, calendar=calendar,
                            sides=sides, partition_id=partition_id)
    observations = assign_continuity(
        bind_evidence(slots, evidence_rows, lattices=lattices, absence_classes=absence_classes),
        partition_boundary_starts=partition_boundary_starts,
    )
    expectation_counts: dict[str, int] = {}
    evidence_counts: dict[str, int] = {}
    continuity_counts: dict[str, int] = {}
    for item in observations:
        expectation_counts[item["expectation"]["status"]] = expectation_counts.get(item["expectation"]["status"], 0) + 1
        evidence_counts[item["evidence"]["status"]] = evidence_counts.get(item["evidence"]["status"], 0) + 1
        continuity_counts[item["continuity"]["status"]] = continuity_counts.get(item["continuity"]["status"], 0) + 1
    population_identity = {"instrument": instrument, "start": iso(parse_time(start)),
                           "end": iso(parse_time(end)), "sides": list(sides),
                           "slot_ids": [slot["slot_id"] for slot in slots],
                           "observation_ids": [item["observation_id"] for item in observations]}
    return {"schema": "c2_observation_population_ledger/vnext-r1",
            "population_id": digest("C2.OBSERVATION.POPULATION", population_identity),
            "instrument": instrument, "start": iso(parse_time(start)), "end": iso(parse_time(end)),
            "expected_slot_count": len(slots), "observation_count": len(observations),
            "unique_slot_count": len({item["slot_id"] for item in observations}),
            "expectation_counts": dict(sorted(expectation_counts.items())),
            "evidence_counts": dict(sorted(evidence_counts.items())),
            "continuity_counts": dict(sorted(continuity_counts.items())),
            "observations": observations, "authority": "SHADOW_ONLY"}


def project_lattice(observations: Sequence[Mapping[str, Any]], profile: LatticeProfile) -> list[dict[str, Any]]:
    result = [profile.membership(item["observation_id"], parse_time(item["interval_start"]),
                                 parse_time(item["interval_end"])) for item in observations]
    _require(len(result) == len(observations), "LATTICE_PROJECTION_CARDINALITY")
    _require({item["observation_id"] for item in result} ==
             {item["observation_id"] for item in observations}, "LATTICE_COPIED_OR_DROPPED_OBSERVATION")
    return result


def build_legacy_crosswalk(legacy_intervals: Sequence[Mapping[str, Any]],
                           observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    legacy_copy = copy.deepcopy(list(legacy_intervals))
    observation_index = {(item["instrument"], item["side"], item["interval_start"], item["interval_end"]):
                         item["observation_id"] for item in observations}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for legacy in legacy_copy:
        legacy_id = str(legacy["legacy_interval_id"])
        _require(legacy_id not in seen, "DUPLICATE_LEGACY_INTERVAL")
        seen.add(legacy_id)
        key = (str(legacy["instrument"]), str(legacy["side"]),
               iso(parse_time(legacy["interval_start"])), iso(parse_time(legacy["interval_end"])))
        observation_id = observation_index.get(key)
        body = {"legacy_interval_id": legacy_id, "observation_id": observation_id,
                "match_status": "MATCHED_EXACT_INTERVAL_SIDE" if observation_id else "UNMATCHED",
                "reason": None if observation_id else "NO_EXACT_INTERVAL_SIDE_MATCH"}
        records.append({"crosswalk_id": digest("C2.LEGACY.OBSERVATION.XWALK", body), **body,
                        "legacy_mutated": False, "authority": "AUDIT_ONLY"})
    records.sort(key=lambda x: x["legacy_interval_id"])
    return records
