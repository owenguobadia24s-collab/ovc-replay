from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable, Mapping

STRUCTURAL_ACTION = "PHASE_MUTATION"
AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
FORBIDDEN_KEYS = frozenset(
    {
        "outcome",
        "outcomes",
        "future_return",
        "return_label",
        "mfe",
        "mae",
        "probability",
        "edge",
        "risk",
        "exposure",
        "trade",
        "trade_label",
        "order",
        "execution",
        "family_id",
        "cluster_id",
        "medoid_id",
        "variant_id",
        "sensitivity_pack_id",
        "grammar_id",
        "parse_id",
        "semantic_label",
    }
)


class AG2ComparatorError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def logical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise AG2ComparatorError(f"AG2_FORBIDDEN_COMPARATOR_FIELD:{path}.{key}")
            _reject_forbidden(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_forbidden(child, f"{path}[{index}]")


def _axis_payload(raw_axes: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if set(raw_axes) != set(AXES):
        raise AG2ComparatorError("AG2_SRFD_AXIS_SET_MISMATCH")
    output: dict[str, dict[str, Any]] = {}
    for name in AXES:
        raw = raw_axes[name]
        if not isinstance(raw, Mapping):
            raise AG2ComparatorError(f"AG2_SRFD_AXIS_SCHEMA:{name}")
        output[name] = {
            "status": str(raw.get("status") or "").upper(),
            "value": str(raw.get("value")) if raw.get("value") is not None else None,
            "reason_code": (
                str(raw.get("reason_code")) if raw.get("reason_code") is not None else None
            ),
            "measurement": (
                str(raw.get("measurement")) if raw.get("measurement") is not None else None
            ),
        }
    return output


def project_srfd_run_change(
    rows: Iterable[Mapping[str, Any]],
    *,
    clock_id: str = "15M",
) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for source in rows:
        _reject_forbidden(source)
        if not bool(source.get("target_eligible")):
            continue
        if str(source.get("clock")) != clock_id:
            continue
        axes = _axis_payload(source["axes"])
        scope = str(source["evaluation_scope_id"])
        row = {
            "record_id": str(source["c2_state_id"]),
            "first_valid_time": str(source["first_valid_time"]),
            "side": str(source["side"]).upper(),
            "scope_id": scope,
            "clock_id": str(source["clock"]),
            "state_key": "C2.STATE." + logical_sha256({"axes": axes, "scope": scope}),
            "reset_reason": (
                "C2_SCOPE_RESET" if str(source.get("continuity")) == "RESET" else None
            ),
        }
        groups[(row["side"], row["scope_id"], row["clock_id"])].append(row)

    streams: list[list[dict[str, Any]]] = []
    for key in sorted(groups):
        values = sorted(
            groups[key], key=lambda item: (item["first_valid_time"], item["record_id"])
        )
        current: list[dict[str, Any]] = []
        for row in values:
            if row["reset_reason"] is not None and current:
                streams.append(current)
                current = []
            current.append(row)
        if current:
            streams.append(current)

    starts: set[tuple[str, str]] = set()
    transitions: dict[tuple[str, str], dict[str, Any]] = {}
    boundaries: dict[tuple[str, str], dict[str, Any]] = {}
    for stream in streams:
        starts.add((stream[0]["side"], stream[0]["first_valid_time"]))
        previous: dict[str, Any] | None = None
        for row in stream:
            if previous is not None:
                key = (row["side"], row["first_valid_time"])
                is_boundary = row["state_key"] != previous["state_key"]
                transition = {
                    "previous": previous,
                    "current": row,
                    "is_boundary": is_boundary,
                }
                transitions[key] = transition
                if is_boundary:
                    boundaries[key] = transition
            previous = row
    return {
        "row_count": sum(len(stream) for stream in streams),
        "stream_count": len(streams),
        "starts": starts,
        "transitions": transitions,
        "boundaries": boundaries,
    }


def project_c2e_phase_mutation(
    frames: Iterable[Mapping[str, Any]],
    event_stream: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    frame_rows = [dict(item) for item in frames]
    events = [dict(item) for item in event_stream]
    for item in frame_rows:
        _reject_forbidden(item)
    for item in events:
        _reject_forbidden(item)

    frame_by_key = {
        (str(row["side"]).upper(), str(row["first_valid_time"])): row
        for row in frame_rows
    }
    frame_by_observation = {str(row["observation_id"]): row for row in frame_rows}
    genesis = {
        str(row["episode_id"]): row
        for row in events
        if row.get("schema") == "c2e_episode_genesis/v0_2"
    }

    starts: set[tuple[str, str]] = set()
    phase_events: list[tuple[tuple[str, str], dict[str, Any]]] = []
    for event in events:
        if event.get("schema") != "c2e_boundary_event/v0_2":
            continue
        episode_ids = event.get("episode_ids") or []
        if len(episode_ids) != 1:
            continue
        episode_id = str(episode_ids[0])
        if episode_id not in genesis:
            raise AG2ComparatorError("AG2_C2E_BOUNDARY_WITHOUT_GENESIS")
        side = str(genesis[episode_id]["side"]).upper()
        key = (side, str(event["effective_time"]))
        action = str(event.get("lifecycle_action"))
        if action == "BIRTH":
            starts.add(key)
        elif action == STRUCTURAL_ACTION:
            phase_events.append((key, event))

    transitions: dict[tuple[str, str], dict[str, Any]] = {}
    boundaries: dict[tuple[str, str], dict[str, Any]] = {}
    for key, row in frame_by_key.items():
        if key in starts:
            continue
        predecessor = row.get("predecessor_observation_id")
        if predecessor is None:
            raise AG2ComparatorError("AG2_C2E_NONSTART_WITHOUT_PREDECESSOR")
        previous = frame_by_observation.get(str(predecessor))
        if previous is None:
            raise AG2ComparatorError("AG2_C2E_PREDECESSOR_NOT_IN_FRAME_INDEX")
        transitions[key] = {
            "previous": previous,
            "current": row,
            "is_boundary": False,
        }

    for key, event in phase_events:
        if key not in transitions:
            raise AG2ComparatorError("AG2_C2E_PHASE_MUTATION_OUTSIDE_DENOMINATOR")
        transitions[key]["is_boundary"] = True
        transitions[key]["boundary_event_id"] = str(event["boundary_event_id"])
        boundaries[key] = transitions[key]

    return {
        "row_count": len(frame_by_key),
        "stream_count": len(starts),
        "starts": starts,
        "transitions": transitions,
        "boundaries": boundaries,
    }


def compare_structural_boundaries(
    c2e_frames: Iterable[Mapping[str, Any]],
    c2e_event_stream: Iterable[Mapping[str, Any]],
    srfd_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    c2e = project_c2e_phase_mutation(c2e_frames, c2e_event_stream)
    srfd = project_srfd_run_change(srfd_rows)
    if set(c2e["transitions"]) != set(srfd["transitions"]):
        raise AG2ComparatorError("AG2_COMMON_TRANSITION_POPULATION_MISMATCH")
    if c2e["starts"] != srfd["starts"]:
        raise AG2ComparatorError("AG2_STREAM_START_POPULATION_MISMATCH")

    rows: list[dict[str, Any]] = []
    for side, first_valid_time in sorted(c2e["transitions"]):
        c2e_transition = c2e["transitions"][(side, first_valid_time)]
        srfd_transition = srfd["transitions"][(side, first_valid_time)]
        c2e_boundary = bool(c2e_transition["is_boundary"])
        srfd_boundary = bool(srfd_transition["is_boundary"])
        if c2e_boundary and srfd_boundary:
            classification = "BOTH_BOUNDARY"
        elif c2e_boundary:
            classification = "C2E_ONLY"
        elif srfd_boundary:
            classification = "SRFD_ONLY"
        else:
            classification = "NEITHER_BOUNDARY"
        rows.append(
            {
                "side": side,
                "first_valid_time": first_valid_time,
                "classification": classification,
                "c2e_boundary": c2e_boundary,
                "srfd_run_change_boundary": srfd_boundary,
                "c2e_boundary_event_id": c2e_transition.get("boundary_event_id"),
                "c2e_previous_observation_id": c2e_transition["previous"]["observation_id"],
                "c2e_current_observation_id": c2e_transition["current"]["observation_id"],
                "c2e_previous_structural_signature_sha256": c2e_transition["previous"][
                    "structural_signature_sha256"
                ],
                "c2e_current_structural_signature_sha256": c2e_transition["current"][
                    "structural_signature_sha256"
                ],
                "srfd_previous_record_id": srfd_transition["previous"]["record_id"],
                "srfd_current_record_id": srfd_transition["current"]["record_id"],
                "srfd_previous_state_key": srfd_transition["previous"]["state_key"],
                "srfd_current_state_key": srfd_transition["current"]["state_key"],
            }
        )

    classes = ("BOTH_BOUNDARY", "C2E_ONLY", "SRFD_ONLY", "NEITHER_BOUNDARY")
    counts = {name: 0 for name in classes}
    by_side = {
        "ASK": {name: 0 for name in classes},
        "BID": {name: 0 for name in classes},
    }
    for row in rows:
        counts[row["classification"]] += 1
        by_side[row["side"]][row["classification"]] += 1
    return {
        "c2e": c2e,
        "srfd": srfd,
        "rows": rows,
        "counts": counts,
        "by_side": by_side,
    }


def null_control_counts(
    comparison_rows: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    counts = {
        "BOTH_BOUNDARY": 0,
        "C2E_ONLY": 0,
        "SRFD_ONLY": 0,
        "NEITHER_BOUNDARY": 0,
    }
    for row in comparison_rows:
        if bool(row["c2e_boundary"]):
            counts["C2E_ONLY"] += 1
        else:
            counts["NEITHER_BOUNDARY"] += 1
    return counts
