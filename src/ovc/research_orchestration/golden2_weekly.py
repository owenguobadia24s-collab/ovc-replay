from __future__ import annotations

import dataclasses
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from ovc.opt_a.role_workspace import Bar, _aggregate_exact
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2_vnext.containers import build_container_graph, build_trailing_range_container
from ovc.opt_b.c2_vnext.formula_profiles import (
    PROFILE_IDS,
    build_formula_bundle,
    evaluate_interaction_profile,
    evaluate_location_profile,
    evaluate_motion_profile,
    evaluate_organisation_profile,
    evaluate_quality_profile,
)
from ovc.opt_b.c2_vnext.horizons import HorizonDefinition, evaluate_horizon
from ovc.opt_b.c2_vnext.levels import build_trailing_range_snapshot
from ovc.opt_b.c2_vnext.observation import build_population, default_gbpusd_calendar, parse_time
from ovc.opt_b.c2_vnext.relations_vnext import (
    build_relation_set,
    fixed_object_crossing,
    point_probe,
    relate_point_to_container,
    relate_point_to_level,
)
from ovc.opt_b.c2_vnext.transitions import classify_transition
from ovc.research_orchestration.serialization import logical_sha256

UTC = timezone.utc
PROGRAMME_ID = "OVC-IROF-GOLDEN2-WEEKLY-E2E-ASSURANCE-v0.1"
POPULATION_ID = "IROF.GOLDEN2.GBPUSD.WEEK.v0_1"
SOURCE_RELEASE_ID = "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2"
SOURCE_MANIFEST_ID = "IROF.GOLDEN2.SOURCE-MANIFEST.v0_1"
C1_RELEASE_ID = "IROF.GOLDEN2.C1.SYNTHETIC.v0_1"
START = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
END = datetime(2026, 6, 8, 0, 0, tzinfo=UTC)
TICK = Decimal("0.00001")
SIDES = ("BID", "ASK")
GAP_START = datetime(2026, 6, 2, 10, 17, tzinfo=UTC)
GAP_END = datetime(2026, 6, 2, 10, 22, tzinfo=UTC)
INCOMPLETE_15M_START = datetime(2026, 6, 3, 14, 15, tzinfo=UTC)


class Golden2Error(ValueError):
    pass


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _hash(value: Any) -> str:
    return logical_sha256(value)


def _delta_ticks(index: int) -> int:
    phase = index % 7200
    if phase < 900:
        return (0, 1, 1, 0, -1, 1, 0, 1)[phase % 8]
    if phase < 1800:
        return (2, 2, 1, 3, 1, 2, 0, 2)[phase % 8]
    if phase < 2700:
        return (-1, 1, -1, 0, 1, -1, 0, 1)[phase % 8]
    if phase < 3600:
        return (4, 3, 5, 2, 4, 1, 3, 5)[phase % 8]
    if phase < 4500:
        return (-3, -2, -4, -1, -3, 0, -2, -4)[phase % 8]
    if phase < 5400:
        return (2, -2, 3, -3, 1, -1, 2, -2)[phase % 8]
    if phase < 6300:
        return (-2, -1, -3, -2, 1, -2, -1, -3)[phase % 8]
    return (3, 2, 1, -1, 2, 3, 0, 2)[phase % 8]


def _wiggle_ticks(index: int) -> int:
    return (2, 2, 3, 2, 1, 2, 3, 1)[index % 8]


def _spread_ticks(index: int) -> int:
    return (10, 11, 12, 11, 13, 12, 11, 10)[index % 8]


def _volume(index: int) -> Decimal:
    base = (10, 12, 15, 11, 18, 14, 13, 16)[index % 8]
    if 2700 <= (index % 7200) < 3600:
        base += 12
    return Decimal(base)


def _is_open_minute(calendar: Any, start: datetime) -> bool:
    return calendar.classify(start, start + timedelta(minutes=1))["status"] == "EXPECTED_EVIDENCE"


def generate_week_m1() -> dict[str, tuple[Bar, ...]]:
    """Generate deterministic provider-like M1 without encoding downstream labels."""
    calendar = default_gbpusd_calendar()
    bid: list[Bar] = []
    ask: list[Bar] = []
    price = Decimal("1.26800")
    cursor = START
    open_index = 0
    while cursor < END:
        if not _is_open_minute(calendar, cursor):
            cursor += timedelta(minutes=1)
            continue
        open_price = price
        close = open_price + TICK * _delta_ticks(open_index)
        wiggle = TICK * _wiggle_ticks(open_index)
        timestamp_ms = int(cursor.timestamp() * 1000)
        row = Bar(
            timestamp_ms=timestamp_ms,
            open=open_price,
            high=max(open_price, close) + wiggle,
            low=min(open_price, close) - wiggle,
            close=close,
            volume=_volume(open_index),
        )
        spread = TICK * _spread_ticks(open_index)
        ask_row = Bar(
            timestamp_ms=timestamp_ms,
            open=row.open + spread,
            high=row.high + spread,
            low=row.low + spread,
            close=row.close + spread,
            volume=row.volume,
        )
        if not (GAP_START <= cursor < GAP_END):
            bid.append(row)
            ask.append(ask_row)
        price = close
        cursor += timedelta(minutes=1)
        open_index += 1
    return {"BID": tuple(bid), "ASK": tuple(ask)}


def _bar_id(side: str, clock: str, row: Bar) -> str:
    return "IROF.GOLDEN2.BAR." + _hash({"side": side, "clock": clock, "timestamp_ms": row.timestamp_ms})[:24]


def _m1_parent_ids(side: str, row: Bar, minutes: int) -> list[str]:
    return [
        "IROF.GOLDEN2.M1." + _hash({"side": side, "timestamp_ms": row.timestamp_ms + offset * 60_000})[:24]
        for offset in range(minutes)
    ]


def _handoff_payload(side: str, clock: str, row: Bar, minutes: int) -> dict[str, Any]:
    start = datetime.fromtimestamp(row.timestamp_ms / 1000, tz=UTC)
    end = start + timedelta(minutes=minutes)
    return {
        "release_id": SOURCE_RELEASE_ID,
        "manifest_id": SOURCE_MANIFEST_ID,
        "research_role": "DISCOVERY",
        "instrument_id": "GBPUSD",
        "clock_id": clock,
        "price_side": side,
        "source_bar_id": _bar_id(side, clock, row),
        "open_time": _iso(start),
        "close_time": _iso(end),
        "first_valid_time": _iso(end),
        "open": format(row.open, "f"),
        "high": format(row.high, "f"),
        "low": format(row.low, "f"),
        "close": format(row.close, "f"),
        "price_increment": "0.00001",
        "admissibility": "HANDOFF_ELIGIBLE",
        "quality_state": "COMPLETE",
        "synthetic": True,
        "selector_state": "NONE",
        "authority_state": "FIXTURE_ONLY",
        "validation_consumption_state": "DENIED",
        "parent_source_object_ids": [f"IROF.GOLDEN2.SOURCE.M1.{side}"],
        "parent_m1_bar_ids": _m1_parent_ids(side, row, minutes),
    }


def build_opt_a_week() -> dict[str, Any]:
    raw = generate_week_m1()
    derived: dict[str, dict[str, tuple[Bar, ...]]] = {"15M": {}, "2H_A_L": {}}
    quarantine: list[dict[str, Any]] = []
    for side in SIDES:
        for clock, minutes in (("15M", 15), ("2H_A_L", 120)):
            rows, rejected = _aggregate_exact(raw[side], minutes=minutes)
            derived[clock][side] = tuple(rows)
            quarantine.extend({**item, "clock": clock, "side": side} for item in rejected)
    body = {
        "population_id": POPULATION_ID,
        "population_mode": "SYNTHETIC_GENERATED",
        "instrument_id": "GBPUSD",
        "interval_start": _iso(START),
        "interval_end": _iso(END),
        "m1_counts": {side: len(raw[side]) for side in SIDES},
        "derived_counts": {clock: {side: len(derived[clock][side]) for side in SIDES} for clock in derived},
        "quarantine_count": len(quarantine),
        "quarantine_reason_counts": dict(sorted(Counter(item["reason"] for item in quarantine).items())),
        "gap": {"start": _iso(GAP_START), "end": _iso(GAP_END), "minutes": 5},
        "authority": "FIXTURE_ONLY",
    }
    body["logical_hash"] = _hash(body)
    return {"raw": raw, "derived": derived, "quarantine": quarantine, "summary": body}


def build_c1_week(opt_a: Mapping[str, Any]) -> dict[str, Any]:
    handoff: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for clock, minutes in (("15M", 15), ("2H_A_L", 120)):
        for side in SIDES:
            payloads = [_handoff_payload(side, clock, row, minutes) for row in opt_a["derived"][clock][side]]
            handoff.extend(payloads)
            prior: dict[str, Any] | None = None
            for payload in payloads:
                result = dataclasses.asdict(build_c1(payload, prior))
                records.append(result)
                counts[f"{clock}:{side}"] += 1
                prior = payload
    body = {
        "record_count": len(records),
        "by_clock_side": dict(sorted(counts.items())),
        "synthetic_count": sum(1 for row in records if row["synthetic"]),
        "records_hash": _hash(records),
        "authority": "FIXTURE_ONLY",
    }
    return {"handoff": handoff, "records": records, "summary": body}


def _source_bar_map(opt_a: Mapping[str, Any]) -> dict[tuple[str, str], Bar]:
    result: dict[tuple[str, str], Bar] = {}
    for side in SIDES:
        for row in opt_a["derived"]["15M"][side]:
            start = datetime.fromtimestamp(row.timestamp_ms / 1000, tz=UTC)
            result[(_iso(start), side)] = row
    return result


def _c2_evidence(c1: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    handoff_by_bar = {str(row["source_bar_id"]): row for row in c1["handoff"] if row["clock_id"] == "15M"}
    for record in c1["records"]:
        if record["clock_id"] != "15M":
            continue
        source = handoff_by_bar[str(record["source_bar_id"])]
        start = str(record["open_time"])
        incomplete = parse_time(start) == INCOMPLETE_15M_START
        rows.append({
            "interval_start": start,
            "interval_end": str(record["close_time"]),
            "side": str(record["price_side"]),
            "source_record_id": str(record["record_id"]),
            "opt_a_release_id": SOURCE_RELEASE_ID,
            "opt_a_record_id": str(source["source_bar_id"]),
            "c1_release_id": C1_RELEASE_ID,
            "c1_record_id": str(record["record_id"]),
            "complete": not incomplete,
            "reason": "GOLDEN2_SYNTHETIC_INCOMPLETE_INTERVAL" if incomplete else None,
        })
    return rows


def _horizon_definition(side: str) -> HorizonDefinition:
    return HorizonDefinition(
        horizon_id=f"IROF.GOLDEN2.HORIZON.TRAILING.4.{side}.v0_1",
        kind="TRAILING_COUNT",
        semantic_type="OBSERVATION_COUNT",
        unit="OBSERVATION",
        grain="15M_C2_OBSERVATION",
        source_basis=POPULATION_ID,
        applicability_scope=("GBPUSD", side, "GOLDEN2"),
        consumer_classes=("C2_MEASUREMENT",),
        causal_class="CAUSAL_BACKWARD",
        continuity_policy="SAME_CONTINUITY_SEGMENT",
        first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID",
        version="v0_1",
        maturity="SHADOW_EXPERIMENT",
        clock_id="LATTICE.15M.UTC_0000.v1",
        count=4,
        template=False,
        benchmark_only=False,
        canonical=False,
    )


def _quality_components(outputs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "component_id": str(item["profile_output_id"]),
            "status": str(item["computability"]),
            "reason_codes": list(item["reason_codes"]),
            "source_ids": list(item["source_ids"]),
            "first_valid_time": str(item["as_of_time"]),
            "censored": False,
            "ambiguous": False,
            "conflict": False,
        }
        for item in outputs
    ]


def _transition(previous: Mapping[str, Any], current: Mapping[str, Any], side: str) -> dict[str, Any]:
    before = {"record_id": previous["profile_output_id"], "facts": previous["facts"], "computability": previous["computability"]}
    after = {"record_id": current["profile_output_id"], "facts": current["facts"], "computability": current["computability"]}
    return classify_transition(
        before,
        after,
        previous_time=str(previous["as_of_time"]),
        current_time=str(current["as_of_time"]),
        profile_id=PROFILE_IDS[str(current["axis"])],
        scope_id=side,
        measurement_fields=("facts",),
        computability_fields=("computability",),
    )


def build_c2_week(opt_a: Mapping[str, Any], c1: Mapping[str, Any]) -> dict[str, Any]:
    evidence = _c2_evidence(c1)
    population = build_population(
        _iso(START), _iso(END), instrument="GBPUSD", calendar=default_gbpusd_calendar(),
        evidence_rows=evidence, sides=SIDES, partition_id="IROF.GOLDEN2.WEEK",
    )
    bars = _source_bar_map(opt_a)
    observations = json.loads(json.dumps(population["observations"]))
    for obs in observations:
        bar = bars.get((str(obs["interval_start"]), str(obs["side"])))
        if bar is not None:
            obs.update({"open": float(bar.open), "high": float(bar.high), "low": float(bar.low), "close": float(bar.close)})
    by_side_segment: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for obs in observations:
        if obs["projection_eligibility"]["eligible"]:
            by_side_segment[(str(obs["side"]), str(obs["continuity"]["segment_id"]))].append(obs)

    snapshots: list[dict[str, Any]] = []
    for (side, segment_id), segment in sorted(by_side_segment.items()):
        segment.sort(key=lambda item: item["interval_start"])
        previous_snapshot: dict[str, Any] | None = None
        for index in range(3, len(segment)):
            current = segment[index]
            prefix = segment[: index + 1]
            horizon = evaluate_horizon(
                _horizon_definition(side), prefix,
                as_of_observation_id=current["observation_id"], consumer_class="C2_MEASUREMENT",
            )
            member_ids = set(horizon["member_observation_ids"])
            members = [item for item in prefix if item["observation_id"] in member_ids]
            if len(members) != 4:
                continue
            levels = build_trailing_range_snapshot(members, horizon_id=horizon["horizon_id"], clock_id="LATTICE.15M.UTC_0000.v1")
            container = build_trailing_range_container(levels)
            graph = build_container_graph([container])
            probe = point_probe(value=current["close"], source_record_id=current["observation_id"], first_valid_time=current["first_valid_time"], probe_label="CLOSE")
            level_relations = [relate_point_to_level(probe, level, precision=5) for level in levels]
            container_relation = relate_point_to_container(probe, container, precision=5)
            level_set = build_relation_set(
                scope_type="LOCAL_LEVELS", subject_observation_id=current["observation_id"],
                candidate_object_ids=[item["level_id"] for item in levels], relations=level_relations,
                exclusions=[], as_of_time=current["first_valid_time"],
            )
            container_set = build_relation_set(
                scope_type="LOCAL_MEASUREMENT_CONTAINERS", subject_observation_id=current["observation_id"],
                candidate_object_ids=[container["container_id"]], relations=[container_relation],
                exclusions=[], as_of_time=current["first_valid_time"],
            )
            location = evaluate_location_profile([level_set, container_set], [*level_relations, container_relation], as_of_time=current["first_valid_time"])
            motion = evaluate_motion_profile(horizon, price_delta=float(current["close"]) - float(members[0]["close"]), relation_deltas=[], as_of_time=current["first_valid_time"])
            organisation = evaluate_organisation_profile(graph, swing_graph=None, as_of_time=current["first_valid_time"])
            crossings: list[dict[str, Any]] = []
            if previous_snapshot is not None:
                fixed = previous_snapshot["levels"][0]
                crossings.append(fixed_object_crossing(
                    object_id=fixed["level_id"], object_value=fixed["value"], previous_value=previous_snapshot["close"],
                    current_value=current["close"], previous_time=previous_snapshot["first_valid_time"],
                    current_time=current["first_valid_time"], precision=5, evidence_mode="OHLC_SPAN",
                ))
            interaction = evaluate_interaction_profile(relation_deltas=[], crossing_evidence=crossings, reference_changes=[], as_of_time=current["first_valid_time"])
            quality = evaluate_quality_profile(_quality_components([location, motion, organisation, interaction]), as_of_time=current["first_valid_time"])
            outputs = [location, motion, organisation, interaction, quality]
            bundle = build_formula_bundle(outputs, as_of_time=current["first_valid_time"])
            transitions: list[dict[str, Any]] = []
            if previous_snapshot is not None:
                previous_by_axis = {row["axis"]: row for row in previous_snapshot["formula_outputs"]}
                transitions = [_transition(previous_by_axis[row["axis"]], row, side) for row in outputs]
            snapshot = {
                "observation_id": current["observation_id"], "side": side, "continuity_segment_id": segment_id,
                "interval_start": current["interval_start"], "first_valid_time": current["first_valid_time"], "close": current["close"],
                "horizon": horizon, "levels": levels, "container": container, "container_graph": graph,
                "level_relation_set": level_set, "container_relation_set": container_set,
                "formula_outputs": outputs, "formula_bundle": bundle, "transition_records": transitions,
                "authority": "SHADOW_FROZEN_READ_ONLY",
            }
            snapshot["logical_hash"] = _hash(snapshot)
            snapshots.append(snapshot)
            previous_snapshot = snapshot

    axis_counts: Counter[str] = Counter()
    for snapshot in snapshots:
        for row in snapshot["formula_outputs"]:
            axis_counts[f"{row['axis']}:{row['computability']}"] += 1
    body = {
        "population_id": population["population_id"], "expected_slot_count": population["expected_slot_count"],
        "observation_count": population["observation_count"], "expectation_counts": population["expectation_counts"],
        "evidence_counts": population["evidence_counts"], "continuity_counts": population["continuity_counts"],
        "structural_snapshot_count": len(snapshots), "transition_count": sum(len(item["transition_records"]) for item in snapshots),
        "axis_computability_counts": dict(sorted(axis_counts.items())),
        "separate_side_snapshot_counts": dict(sorted(Counter(item["side"] for item in snapshots).items())),
        "chronology_pass": all(item["interval_start"] < item["first_valid_time"] for item in snapshots),
        "authority": "SHADOW_FROZEN_READ_ONLY",
    }
    body["logical_hash"] = _hash(body)
    return {"population": population, "observations": observations, "snapshots": snapshots, "summary": body}


def run_weekly_upstream() -> dict[str, Any]:
    opt_a = build_opt_a_week()
    c1 = build_c1_week(opt_a)
    c2 = build_c2_week(opt_a, c1)
    summary = {
        "programme_id": PROGRAMME_ID, "population_id": POPULATION_ID,
        "opt_a": opt_a["summary"], "c1": c1["summary"], "c2": c2["summary"],
        "hidden_generator_truth_consumed": False, "real_market_data": False,
        "validation_consumed": False, "authority_effect": "NONE",
    }
    summary["logical_hash"] = _hash(summary)
    return {"opt_a": opt_a, "c1": c1, "c2": c2, "summary": summary}
