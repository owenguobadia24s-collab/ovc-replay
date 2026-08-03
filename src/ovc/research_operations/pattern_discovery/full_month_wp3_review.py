from __future__ import annotations

import argparse
import hashlib
import json
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

PROGRAMME_ID = "PD-JUNE-FULL-MONTH-MDR"
PACKET_ID = "PD-JUNE-FM-WP3"
REVIEW_ID = "PD-JUNE-FM-WP3-BLINDED-REVIEW-v1"
SOURCE_RUN_ID = "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9"
SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
OUTPUT_MANIFEST_SHA256 = "e805eaa0f8603da644d23d83297fdc5e62142f8051d8583c9c28c9469a3b704b"
DETERMINISTIC_PAYLOAD_HASH = "d784f47395d904b2d78d77cde0a8a40287877692d8b92889ab2eeedef621a24b"
EVALUATOR_VERSION = "PD.TRIGGER_EVALUATOR.v0.1"
PARAMETER_PACK_ID = "C2.PARAMS.GBPUSD.DISCOVERY.v0.1"
TARGET_START = datetime(2026, 6, 1, tzinfo=timezone.utc)
TARGET_END = datetime(2026, 7, 1, tzinfo=timezone.utc)
AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
STRUCTURAL_AXES = AXES[:4]
BOUNDARY_VALUES = {
    "UPPER_REGION", "LOWER_REGION", "NEAR_UPPER_BOUNDARY",
    "NEAR_LOWER_BOUNDARY", "AT_UPPER_BOUNDARY", "AT_LOWER_BOUNDARY",
}
BREACH_VALUES = {"BREACH", "BREACH_ACTIVE", "CROSSING"}
RETURN_INSIDE_VALUES = {"INSIDE", "RETURNED_INSIDE", "RECLAIMED_INSIDE"}
COMPRESSION_VALUES = {"COMPRESSION", "COMPRESSED", "COMPRESSING"}
DISPLACEMENT_VALUES = {
    "DISPLACEMENT", "UP_DISPLACEMENT", "DOWN_DISPLACEMENT",
    "UP_PROGRESS", "DOWN_PROGRESS",
}
UP_VALUES = {
    "UPPER_REGION", "NEAR_UPPER_BOUNDARY", "AT_UPPER_BOUNDARY",
    "UP_PROGRESS", "UP_DISPLACEMENT",
}
DOWN_VALUES = {
    "LOWER_REGION", "NEAR_LOWER_BOUNDARY", "AT_LOWER_BOUNDARY",
    "DOWN_PROGRESS", "DOWN_DISPLACEMENT",
}
CLOCK_CONFIG = {
    "15M": {"seconds": 900, "range_window": 32, "swing_left": 4, "swing_right": 4, "history": 64},
    "2H_A_L": {"seconds": 7200, "range_window": 24, "swing_left": 3, "swing_right": 3, "history": 48},
}


class WP3ReviewError(ValueError):
    pass


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def canonical_json(value: Any) -> str:
    def normalise(item: Any) -> Any:
        if isinstance(item, Decimal):
            return format(item, "f")
        if isinstance(item, Mapping):
            return {key: normalise(item[key]) for key in sorted(item)}
        if isinstance(item, (list, tuple)):
            return [normalise(part) for part in item]
        return item
    return json.dumps(normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{canonical_sha256(value)}"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def week_bucket(value: str) -> str:
    current = parse_utc(value).date()
    if current < date(2026, 6, 1) or current > date(2026, 6, 30):
        raise WP3ReviewError("WP3 review timestamp must be inside June 2026")
    if current <= date(2026, 6, 7):
        return "W1_2026-06-01_07"
    if current <= date(2026, 6, 14):
        return "W2_2026-06-08_14"
    if current <= date(2026, 6, 21):
        return "W3_2026-06-15_21"
    if current <= date(2026, 6, 28):
        return "W4_2026-06-22_28"
    return "W5_2026-06-29_30"


def utc_session(value: str) -> str:
    hour = parse_utc(value).hour
    if hour < 8:
        return "ASIA_00_08"
    if hour < 13:
        return "LONDON_08_13"
    if hour < 21:
        return "NEW_YORK_13_21"
    return "LATE_21_24"


def axis_value(state: Mapping[str, Any], axis: str) -> str | None:
    payload = state["axes"][axis]
    if payload.get("status") != "EVALUATED":
        return None
    value = payload.get("value")
    return None if value is None else str(value)


def build_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any] | None:
    changed = sorted(axis for axis in AXES if previous["axes"][axis] != current["axes"][axis])
    if not changed:
        return None
    identity = {
        "from": previous["c2_state_id"],
        "to": current["c2_state_id"],
        "changed_axes": changed,
        "first_valid_time": current["first_valid_time"],
    }
    return {
        "c2_transition_id": stable_id("c2-transition", identity),
        "from_state_id": previous["c2_state_id"],
        "to_state_id": current["c2_state_id"],
        "changed_axes": changed,
        "first_valid_time": current["first_valid_time"],
        "status": "OBSERVED",
    }


def direction(state: Mapping[str, Any] | None) -> str | None:
    if state is None:
        return None
    for axis in ("LOCATION", "MOTION"):
        value = axis_value(state, axis)
        if value in UP_VALUES:
            return "UP"
        if value in DOWN_VALUES:
            return "DOWN"
    return None


def evaluate_trigger_rules(
    history: Sequence[Mapping[str, Any]],
    *,
    previous_parent: Mapping[str, Any] | None = None,
    current_parent: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    if len(history) < 2:
        raise WP3ReviewError("trigger evaluation requires at least two states")
    previous, current = history[-2], history[-1]
    transition = build_transition(previous, current)
    changed = set(() if transition is None else transition["changed_axes"])
    result: dict[str, dict[str, Any]] = {}

    previous_location = axis_value(previous, "LOCATION")
    current_location = axis_value(current, "LOCATION")
    if previous_location is None or current_location is None:
        result["BOUNDARY_ZONE_ENTRY"] = {"status": "NOT_EVALUABLE", "reason": "LOCATION_NOT_EVALUABLE"}
    else:
        fired = current_location in BOUNDARY_VALUES and previous_location not in BOUNDARY_VALUES and "LOCATION" in changed
        result["BOUNDARY_ZONE_ENTRY"] = {"status": "FIRED" if fired else "NOT_FIRED", "reason": None}

    previous_interaction = axis_value(previous, "INTERACTION")
    current_interaction = axis_value(current, "INTERACTION")
    if previous_interaction is None or current_interaction is None:
        result["BREACH_ACTIVE"] = {"status": "NOT_EVALUABLE", "reason": "INTERACTION_NOT_EVALUABLE"}
        result["RETURN_INSIDE"] = {"status": "NOT_EVALUABLE", "reason": "INTERACTION_NOT_EVALUABLE"}
    else:
        breach = current_interaction in BREACH_VALUES and previous_interaction not in BREACH_VALUES and "INTERACTION" in changed
        returned = previous_interaction in BREACH_VALUES and current_interaction in RETURN_INSIDE_VALUES and "INTERACTION" in changed
        result["BREACH_ACTIVE"] = {"status": "FIRED" if breach else "NOT_FIRED", "reason": None}
        result["RETURN_INSIDE"] = {"status": "FIRED" if returned else "NOT_FIRED", "reason": None}

    previous_organisation = axis_value(previous, "ORGANISATION")
    current_motion = axis_value(current, "MOTION")
    if previous_organisation is None or current_motion is None:
        result["COMPRESSION_TO_DISPLACEMENT"] = {"status": "NOT_EVALUABLE", "reason": "ORGANISATION_OR_MOTION_NOT_EVALUABLE"}
    else:
        fired = previous_organisation in COMPRESSION_VALUES and current_motion in DISPLACEMENT_VALUES and bool(changed & {"ORGANISATION", "MOTION"})
        result["COMPRESSION_TO_DISPLACEMENT"] = {"status": "FIRED" if fired else "NOT_FIRED", "reason": None}

    motion_values = [axis_value(item, "MOTION") for item in history]
    if motion_values[-1] is None:
        result["LONG_PERSISTENCE"] = {"status": "NOT_EVALUABLE", "reason": "MOTION_NOT_EVALUABLE"}
    else:
        run = 0
        for value in reversed(motion_values):
            if value == motion_values[-1]:
                run += 1
            else:
                break
        result["LONG_PERSISTENCE"] = {"status": "FIRED" if run == 4 else "NOT_FIRED", "reason": None, "run_length": run}

    selected = motion_values[-6:]
    if any(value is None for value in selected):
        result["REPEATED_SWITCHING"] = {"status": "NOT_EVALUABLE", "reason": "MOTION_HISTORY_NOT_EVALUABLE"}
    else:
        switches = sum(before != after for before, after in zip(selected, selected[1:]))
        prior_switches = sum(before != after for before, after in zip(selected[:-1], selected[1:-1]))
        fired = switches >= 3 and prior_switches < 3
        result["REPEATED_SWITCHING"] = {"status": "FIRED" if fired else "NOT_FIRED", "reason": None, "switches": switches}

    previous_local_direction = direction(previous)
    current_local_direction = direction(current)
    previous_parent_direction = direction(previous_parent)
    current_parent_direction = direction(current_parent)
    if current_local_direction is None or current_parent_direction is None:
        result["LOCAL_PARENT_CONFLICT"] = {"status": "NOT_EVALUABLE", "reason": "CROSS_SCALE_DIRECTION_NOT_EVALUABLE"}
        result["ALIGNMENT_GAINED"] = {"status": "NOT_EVALUABLE", "reason": "CROSS_SCALE_DIRECTION_NOT_EVALUABLE"}
    else:
        previous_conflict = previous_local_direction is not None and previous_parent_direction is not None and previous_local_direction != previous_parent_direction
        current_conflict = current_local_direction != current_parent_direction
        result["LOCAL_PARENT_CONFLICT"] = {"status": "FIRED" if current_conflict and not previous_conflict else "NOT_FIRED", "reason": None}
        result["ALIGNMENT_GAINED"] = {"status": "FIRED" if previous_conflict and not current_conflict else "NOT_FIRED", "reason": None}
    return result


def reconstruct_active_levels(
    states: Sequence[Mapping[str, Any]],
    bars: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    if not states:
        return {}
    clock = str(states[0]["clock"])
    config = CLOCK_CONFIG[clock]
    bars_by_end = {str(item["end_utc"]): item for item in bars if item.get("quality_state") == "COMPLETE"}
    history: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    active_swings: dict[str, dict[str, Any]] = {}
    previous_time: datetime | None = None
    output: dict[str, list[dict[str, Any]]] = {}

    for state in states:
        timestamp = str(state["first_valid_time"])
        current_time = parse_utc(timestamp)
        if timestamp not in bars_by_end:
            raise WP3ReviewError(f"complete state bar unavailable:{timestamp}")
        if state.get("continuity") == "RESET" or (
            previous_time is not None and (current_time - previous_time).total_seconds() != config["seconds"]
        ):
            history = []
            active_swings = {}
        history.append((state, bars_by_end[timestamp]))
        history = history[-config["history"] :]
        levels: dict[str, dict[str, Any]] = {}

        if len(history) >= config["range_window"]:
            window = history[-config["range_window"] :]
            high = max(Decimal(str(item[1]["high"])) for item in window)
            low = min(Decimal(str(item[1]["low"])) for item in window)
            for level_type, value in (
                ("RANGE_HIGH", high),
                ("RANGE_LOW", low),
                ("MIDPOINT", (high + low) / Decimal("2")),
            ):
                source_ids = [str(item[0]["parent_c1_record_id"]) for item in window]
                identity = {
                    "type_id": level_type,
                    "clock": clock,
                    "price_side": state["side"],
                    "source_record_ids": source_ids,
                    "first_valid_time": timestamp,
                    "parameter_pack_id": PARAMETER_PACK_ID,
                    "value": value,
                }
                levels[level_type] = {
                    "level_id": stable_id("c2-level", identity),
                    "level_type": level_type,
                    "value": format(value, "f"),
                    "first_valid_time": timestamp,
                    "source_c1_record_count": len(source_ids),
                }

        for level_type, field in (("SWING_HIGH", "high"), ("SWING_LOW", "low")):
            left = config["swing_left"]
            right = config["swing_right"]
            found: dict[str, Any] | None = None
            for centre in range(len(history) - right - 1, left - 1, -1):
                window = history[centre - left : centre + right + 1]
                values = [Decimal(str(item[1][field])) for item in window]
                candidate = values[left]
                other = values[:left] + values[left + 1 :]
                confirmed = candidate > max(other) if level_type == "SWING_HIGH" else candidate < min(other)
                if not confirmed:
                    continue
                source_ids = [str(item[0]["parent_c1_record_id"]) for item in window]
                first_valid = str(window[-1][0]["first_valid_time"])
                identity = {
                    "type_id": level_type,
                    "clock": clock,
                    "price_side": state["side"],
                    "source_record_ids": source_ids,
                    "first_valid_time": first_valid,
                    "parameter_pack_id": PARAMETER_PACK_ID,
                    "value": candidate,
                }
                found = {
                    "level_id": stable_id("c2-level", identity),
                    "level_type": level_type,
                    "value": format(candidate, "f"),
                    "first_valid_time": first_valid,
                    "source_c1_record_count": len(source_ids),
                }
                break
            if found is not None:
                active_swings[level_type] = found
                levels[level_type] = found
            elif level_type in active_swings:
                levels[level_type] = active_swings[level_type]

        actual_ids = set(str(item) for item in state.get("level_ids", []))
        generated_ids = set(item["level_id"] for item in levels.values())
        if actual_ids != generated_ids:
            raise WP3ReviewError(f"active level reconstruction mismatch:{timestamp}")
        output[timestamp] = sorted(levels.values(), key=lambda item: item["level_id"])
        previous_time = current_time
    return output


def validate_blinded_card(card: Mapping[str, Any]) -> None:
    required = {
        "blind_id", "card_payload_sha256", "event_timestamp_utc",
        "event_row_alias", "observations", "deterministic_calculation_inputs",
        "source_completeness_summary", "review_questions", "blinding",
    }
    missing = sorted(required - set(card))
    if missing:
        raise WP3ReviewError(f"card required fields unavailable:{missing}")
    if card["event_row_alias"] != "R05" or len(card["observations"]) != 9:
        raise WP3ReviewError("card must contain four pre-event, event and four post-event rows")
    if any(key in card for key in ("selection_class", "fired_rules", "rule_outcomes", "expected_trigger_correctness")):
        raise WP3ReviewError("blinded card leaks sealed answer data")
    for observation in card["observations"]:
        if observation["source_completeness"]["review_card_presentation_omission_count"] != 0:
            raise WP3ReviewError("review card presentation omission is not zero")
        if observation.get("corresponding_2h_parent_state") is None:
            raise WP3ReviewError("corresponding 2H parent state unavailable")
        current = parse_utc(str(observation["first_valid_time"]))
        if not TARGET_START <= current < TARGET_END:
            raise WP3ReviewError("review observation is outside the June target")
    body = dict(card)
    claimed = str(body.pop("card_payload_sha256"))
    if canonical_sha256(body) != claimed:
        raise WP3ReviewError(f"card payload hash mismatch:{card['blind_id']}")


def validate_batch(batch: Mapping[str, Any]) -> None:
    cards = batch.get("cards")
    if not isinstance(cards, list) or len(cards) != 8:
        raise WP3ReviewError("each WP3 review batch must contain eight cards")
    for card in cards:
        validate_blinded_card(card)
    if canonical_sha256(cards) != batch.get("cards_canonical_sha256"):
        raise WP3ReviewError("batch cards hash mismatch")


def verify_external_files(root: Path, expected: Sequence[Mapping[str, Any]]) -> None:
    for item in expected:
        path = root / str(item["name"])
        if not path.is_file():
            raise WP3ReviewError(f"external artifact unavailable:{path}")
        if path.stat().st_size != int(item["size_bytes"]):
            raise WP3ReviewError(f"external artifact size mismatch:{path.name}")
        if sha_file(path) != item["sha256"]:
            raise WP3ReviewError(f"external artifact SHA-256 mismatch:{path.name}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify PD-JUNE-FM-WP3 blinded review artifacts.")
    parser.add_argument("reviewer_root", type=Path)
    parser.add_argument("--sealed-root", type=Path)
    args = parser.parse_args(argv)
    for path in sorted(args.reviewer_root.glob("PD_JUNE_FM_WP3_BLINDED_REVIEW_BATCH_*.json")):
        validate_batch(json.loads(path.read_text(encoding="utf-8")))
    if args.sealed_root is not None:
        answer = args.sealed_root / "PD_JUNE_FM_WP3_SEALED_ANSWER_KEY.json"
        if not answer.is_file():
            raise WP3ReviewError("sealed answer key unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
