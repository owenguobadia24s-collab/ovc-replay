"""Immutable C2 vNext level, lifecycle, graph and selector foundation.

Shadow-only: no active pivot parameter, selector, formula, release or publication
is created by this module.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

UTC = timezone.utc
CANDIDATE_STATUSES = (
    "UNIQUE_CONFIRMED", "AMBIGUOUS_PLATEAU", "REJECTED_NOT_EXTREME",
    "CENSORED_CONFIRMATION",
)
LEVEL_FAMILIES = (
    "WINDOW_BOUNDARY", "CONFIRMED_PIVOT", "DERIVED_REFERENCE",
    "CONTEXT_REFERENCE", "CONTAINER_BOUNDARY_REFERENCE",
)
LEVEL_TYPES = (
    "TRAILING_RANGE_HIGH", "TRAILING_RANGE_LOW", "TRAILING_RANGE_MIDPOINT",
    "CONFIRMED_SWING_HIGH", "CONFIRMED_SWING_LOW", "LINKED_PARENT_LEVEL",
    "CONTAINER_UPPER_POINTER", "CONTAINER_LOWER_POINTER", "CONTAINER_CENTRE_POINTER",
)
LIFECYCLE_EVENTS = (
    "DEFINED", "REFRESHED", "SUPERSEDED", "STALE_FOR_CONSUMER",
    "RETIRED_FOR_CONSUMER", "INVALIDATED_SOURCE",
)
SELECTOR_REASONS = (
    "SELECTED_UNIQUE", "NO_ELIGIBLE_CANDIDATE", "TIED_CANDIDATES",
    "EXCLUDED_FAMILY", "EXCLUDED_TYPE", "NOT_FIRST_VALID_AS_OF",
    "CONSUMER_STALE", "LIFECYCLE_UNAVAILABLE",
)


class LevelContractError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise LevelContractError(marker)


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


@dataclass(frozen=True)
class PivotPolicy:
    policy_id: str
    left_count: int
    right_count: int
    clock_id: str
    structural_depth: str = "S0"
    generation_method: str = "RAW_OBSERVATION_PIVOT"
    maturity: str = "SHADOW_EXPERIMENT"
    active: bool = False
    canonical: bool = False

    def __post_init__(self) -> None:
        _require(self.left_count > 0 and self.right_count > 0, "PIVOT_COUNTS")
        _require(self.structural_depth in {"S0", "S1", "S2"}, "STRUCTURAL_DEPTH")
        _require(self.generation_method in {"RAW_OBSERVATION_PIVOT", "PIVOT_OF_PIVOTS"}, "GENERATION_METHOD")
        _require(self.maturity == "SHADOW_EXPERIMENT", "PIVOT_MATURITY")
        _require(not self.active, "PIVOT_POLICY_ACTIVATION_DENIED")
        _require(not self.canonical, "CANONICAL_PIVOT_POLICY_DENIED")


def baseline_pivot_policies() -> tuple[PivotPolicy, ...]:
    return (
        PivotPolicy("PIVOT.15M.2L2R.S0.r1", 2, 2, "LATTICE.15M.UTC_0000.v1"),
        PivotPolicy("PIVOT.2H.2L2R.S0.r1", 2, 2, "LATTICE.2H.UTC_0000.v1"),
    )


def _eligible(item: Mapping[str, Any]) -> bool:
    return bool(item.get("projection_eligibility", {}).get("eligible", True))


def _price(item: Mapping[str, Any], polarity: str) -> float:
    key = "high" if polarity == "HIGH" else "low"
    _require(key in item, f"PRICE_FIELD_REQUIRED:{key}")
    value = item[key]
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), "PRICE_VALUE")
    return float(value)


def detect_pivot_candidates(
    observations: Sequence[Mapping[str, Any]],
    *,
    policy: PivotPolicy,
    polarity: str,
) -> list[dict[str, Any]]:
    """Emit one evidence record per possible anchor, including rejection/censoring."""
    _require(polarity in {"HIGH", "LOW"}, "PIVOT_POLARITY")
    items = [copy.deepcopy(dict(item)) for item in observations]
    items.sort(key=lambda item: (parse_time(str(item["first_valid_time"])), str(item["observation_id"])))
    _require(len({str(item["observation_id"]) for item in items}) == len(items), "DUPLICATE_OBSERVATION_ID")
    output: list[dict[str, Any]] = []
    for index, anchor in enumerate(items):
        left_start = index - policy.left_count
        right_end = index + policy.right_count
        candidate_identity = {
            "policy_id": policy.policy_id,
            "anchor_observation_id": anchor["observation_id"],
            "polarity": polarity,
            "clock_id": policy.clock_id,
            "side": anchor.get("side"),
            "release_id": anchor.get("lineage", {}).get("opt_a_release_id"),
        }
        body: dict[str, Any] = {
            "candidate_id": digest("C2.LEVEL.CANDIDATE", candidate_identity),
            "policy_id": policy.policy_id,
            "polarity": polarity,
            "anchor_observation_id": anchor["observation_id"],
            "anchor_time": anchor.get("interval_end", anchor["first_valid_time"]),
            "anchor_price": _price(anchor, polarity),
            "clock_id": policy.clock_id,
            "structural_depth": policy.structural_depth,
            "generation_method": policy.generation_method,
            "instrument": anchor.get("instrument"),
            "side": anchor.get("side"),
            "source_release_id": anchor.get("lineage", {}).get("opt_a_release_id"),
            "first_valid_time": None,
            "status": "CENSORED_CONFIRMATION",
            "reason": None,
            "member_observation_ids": [],
            "tie_observation_ids": [],
            "maturity": "SHADOW_EXPERIMENT",
            "authority": "CANDIDATE_EVIDENCE_ONLY",
        }
        if left_start < 0:
            body["reason"] = "LEFT_WARM_UP_INSUFFICIENT"
            output.append(body)
            continue
        if right_end >= len(items):
            body["reason"] = "RIGHT_CONFIRMATION_UNAVAILABLE"
            output.append(body)
            continue
        window = items[left_start:right_end + 1]
        body["member_observation_ids"] = [item["observation_id"] for item in window]
        if not all(_eligible(item) for item in window):
            body["reason"] = "INELIGIBLE_OR_CENSORED_MEMBER"
            output.append(body)
            continue
        segments = {item.get("continuity", {}).get("segment_id") for item in window}
        if len(segments) != 1 or None in segments:
            body["reason"] = "DISCONTINUITY_OR_RESET"
            output.append(body)
            continue
        confirmation = window[-1]
        body["first_valid_time"] = confirmation["first_valid_time"]
        anchor_price = body["anchor_price"]
        prices = [_price(item, polarity) for item in window]
        extreme = max(prices) if polarity == "HIGH" else min(prices)
        ties = [item["observation_id"] for item in window if _price(item, polarity) == extreme]
        body["tie_observation_ids"] = ties
        if anchor_price != extreme:
            body["status"] = "REJECTED_NOT_EXTREME"
            body["reason"] = "ANCHOR_NOT_WINDOW_EXTREME"
        elif len(ties) > 1:
            body["status"] = "AMBIGUOUS_PLATEAU"
            body["reason"] = "COMPOUND_ANCHOR_RULE_NOT_APPROVED"
        else:
            body["status"] = "UNIQUE_CONFIRMED"
            body["reason"] = "REGISTERED_LEFT_RIGHT_RULE_PASSED"
        output.append(body)
    return output


def _definition_base(
    *,
    family: str,
    level_type: str,
    value: float,
    first_valid_time: str,
    anchor_time: str,
    instrument: str,
    side: str,
    clock_id: str,
    structural_depth: str,
    origin: str,
    source_ids: Sequence[str],
    lineage_id: str,
    parent_level_ids: Sequence[str] = (),
    source_release_id: str | None = None,
) -> dict[str, Any]:
    _require(family in LEVEL_FAMILIES, "LEVEL_FAMILY")
    _require(level_type in LEVEL_TYPES, "LEVEL_TYPE")
    _require(structural_depth in {"S0", "S1", "S2", "NA"}, "STRUCTURAL_DEPTH")
    identity = {
        "family": family, "level_type": level_type, "value": value,
        "first_valid_time": first_valid_time, "instrument": instrument, "side": side,
        "clock_id": clock_id, "structural_depth": structural_depth, "origin": origin,
        "source_ids": list(source_ids), "parent_level_ids": list(parent_level_ids),
        "source_release_id": source_release_id,
    }
    definition_id = digest("C2.REFERENCE_LEVEL", identity)
    body = {
        "schema": "c2_reference_level/vnext-r1",
        "level_id": definition_id,
        "family": family,
        "level_type": level_type,
        "value": float(value),
        "first_valid_time": iso(parse_time(first_valid_time)),
        "anchor_time": iso(parse_time(anchor_time)),
        "instrument": instrument,
        "side": side,
        "clock_id": clock_id,
        "structural_depth": structural_depth,
        "origin": origin,
        "source_ids": list(source_ids),
        "source_release_id": source_release_id,
        "lineage_id": lineage_id,
        "parent_level_ids": list(parent_level_ids),
        "immutable": True,
        "maturity": "SHADOW_EXPERIMENT",
        "authority": {"active_selector": "NONE", "parameter_activation": "NONE", "release": "NONE"},
    }
    body["content_sha256"] = hashlib.sha256(canonical_bytes(body)).hexdigest()
    return body


def build_confirmed_pivot_level(candidate: Mapping[str, Any]) -> dict[str, Any]:
    _require(candidate.get("status") == "UNIQUE_CONFIRMED", "CANDIDATE_NOT_CONFIRMED")
    _require(candidate.get("first_valid_time") is not None, "CANDIDATE_FIRST_VALID_REQUIRED")
    polarity = str(candidate["polarity"])
    level_type = "CONFIRMED_SWING_HIGH" if polarity == "HIGH" else "CONFIRMED_SWING_LOW"
    lineage_id = digest("C2.SWING.LINEAGE", {
        "anchor_observation_id": candidate["anchor_observation_id"],
        "policy_id": candidate["policy_id"],
        "polarity": polarity,
    })
    return _definition_base(
        family="CONFIRMED_PIVOT",
        level_type=level_type,
        value=float(candidate["anchor_price"]),
        first_valid_time=str(candidate["first_valid_time"]),
        anchor_time=str(candidate["anchor_time"]),
        instrument=str(candidate["instrument"]),
        side=str(candidate["side"]),
        clock_id=str(candidate["clock_id"]),
        structural_depth=str(candidate["structural_depth"]),
        origin="ENDOGENOUS_PRICE_STRUCTURE",
        source_ids=[str(candidate["candidate_id"]), *[str(item) for item in candidate["member_observation_ids"]]],
        lineage_id=lineage_id,
        source_release_id=candidate.get("source_release_id"),
    )


def build_trailing_range_snapshot(
    observations: Sequence[Mapping[str, Any]],
    *,
    horizon_id: str,
    clock_id: str,
) -> list[dict[str, Any]]:
    items = [copy.deepcopy(dict(item)) for item in observations]
    _require(bool(items), "TRAILING_RANGE_EMPTY")
    items.sort(key=lambda item: parse_time(str(item["first_valid_time"])))
    _require(all(_eligible(item) for item in items), "TRAILING_RANGE_MEMBER_INELIGIBLE")
    segments = {item.get("continuity", {}).get("segment_id") for item in items}
    _require(len(segments) == 1 and None not in segments, "TRAILING_RANGE_DISCONTINUITY")
    for left, right in zip(items, items[1:]):
        _require(left["interval_end"] == right["interval_start"], "TRAILING_RANGE_NONCONTIGUOUS")
    high_value = max(float(item["high"]) for item in items)
    low_value = min(float(item["low"]) for item in items)
    high_anchor = next(item for item in items if float(item["high"]) == high_value)
    low_anchor = next(item for item in items if float(item["low"]) == low_value)
    as_of = str(items[-1]["first_valid_time"])
    common = {
        "first_valid_time": as_of,
        "instrument": str(items[-1]["instrument"]),
        "side": str(items[-1]["side"]),
        "clock_id": clock_id,
        "structural_depth": "NA",
        "origin": "ENDOGENOUS_TRAILING_MEASUREMENT",
        "source_ids": [str(item["observation_id"]) for item in items],
        "source_release_id": items[-1].get("lineage", {}).get("opt_a_release_id"),
    }
    high_lineage = digest("C2.RANGE.LINEAGE", {"horizon_id": horizon_id, "type": "HIGH", "anchor": high_anchor["observation_id"], "side": common["side"], "clock_id": clock_id})
    low_lineage = digest("C2.RANGE.LINEAGE", {"horizon_id": horizon_id, "type": "LOW", "anchor": low_anchor["observation_id"], "side": common["side"], "clock_id": clock_id})
    high = _definition_base(family="WINDOW_BOUNDARY", level_type="TRAILING_RANGE_HIGH", value=high_value, anchor_time=str(high_anchor["interval_end"]), lineage_id=high_lineage, **common)
    low = _definition_base(family="WINDOW_BOUNDARY", level_type="TRAILING_RANGE_LOW", value=low_value, anchor_time=str(low_anchor["interval_end"]), lineage_id=low_lineage, **common)
    midpoint_value = (high_value + low_value) / 2.0
    midpoint_lineage = digest("C2.RANGE.MIDPOINT.LINEAGE", {"high_lineage": high_lineage, "low_lineage": low_lineage, "horizon_id": horizon_id})
    midpoint = _definition_base(
        family="DERIVED_REFERENCE", level_type="TRAILING_RANGE_MIDPOINT",
        value=midpoint_value, anchor_time=as_of, lineage_id=midpoint_lineage,
        parent_level_ids=[high["level_id"], low["level_id"]], **common,
    )
    for item in (high, low, midpoint):
        item["horizon_id"] = horizon_id
        item["snapshot_version"] = digest("C2.RANGE.SNAPSHOT", {"as_of": as_of, "member_ids": common["source_ids"], "level_type": item["level_type"]})
        item["content_sha256"] = hashlib.sha256(canonical_bytes({k: v for k, v in item.items() if k != "content_sha256"})).hexdigest()
    return [high, low, midpoint]


def build_context_reference(parent_level: Mapping[str, Any], *, local_scope_id: str, as_of_time: str) -> dict[str, Any]:
    _require(parse_time(str(parent_level["first_valid_time"])) <= parse_time(as_of_time), "PARENT_LEVEL_NOT_FIRST_VALID")
    body = _definition_base(
        family="CONTEXT_REFERENCE", level_type="LINKED_PARENT_LEVEL",
        value=float(parent_level["value"]), first_valid_time=as_of_time,
        anchor_time=str(parent_level["anchor_time"]), instrument=str(parent_level["instrument"]),
        side=str(parent_level["side"]), clock_id=str(parent_level["clock_id"]),
        structural_depth=str(parent_level["structural_depth"]), origin="LINKED_PARENT_CONTEXT",
        source_ids=[str(parent_level["level_id"])],
        lineage_id=digest("C2.CONTEXT.LEVEL.LINK", {"parent_level_id": parent_level["level_id"], "local_scope_id": local_scope_id}),
        parent_level_ids=[str(parent_level["level_id"])], source_release_id=parent_level.get("source_release_id"),
    )
    body["local_scope_id"] = local_scope_id
    body["parent_authority_preserved"] = True
    body["content_sha256"] = hashlib.sha256(canonical_bytes({k: v for k, v in body.items() if k != "content_sha256"})).hexdigest()
    return body


def make_lifecycle_event(
    level: Mapping[str, Any], *, event_type: str, event_time: str,
    reason: str, consumer_id: str | None = None, superseding_level_id: str | None = None,
) -> dict[str, Any]:
    _require(event_type in LIFECYCLE_EVENTS, "LIFECYCLE_EVENT_TYPE")
    _require(parse_time(event_time) >= parse_time(str(level["first_valid_time"])), "LIFECYCLE_BEFORE_LEVEL_FIRST_VALID")
    if event_type in {"STALE_FOR_CONSUMER", "RETIRED_FOR_CONSUMER"}:
        _require(bool(consumer_id), "CONSUMER_ID_REQUIRED")
    if event_type == "SUPERSEDED":
        _require(bool(superseding_level_id), "SUPERSEDING_LEVEL_REQUIRED")
    body = {
        "level_id": level["level_id"], "event_type": event_type,
        "event_time": iso(parse_time(event_time)), "reason": reason,
        "consumer_id": consumer_id, "superseding_level_id": superseding_level_id,
        "definition_content_sha256": level["content_sha256"],
        "authority": "APPEND_ONLY_LIFECYCLE",
    }
    return {"lifecycle_event_id": digest("C2.LEVEL.LIFECYCLE", body), **body}


def project_lifecycle(levels: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]], *, as_of_time: str, consumer_id: str | None = None) -> list[dict[str, Any]]:
    as_of = parse_time(as_of_time)
    by_level: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        if parse_time(str(event["event_time"])) <= as_of:
            by_level.setdefault(str(event["level_id"]), []).append(event)
    output: list[dict[str, Any]] = []
    for raw in levels:
        level = copy.deepcopy(dict(raw))
        if parse_time(str(level["first_valid_time"])) > as_of:
            continue
        state = "AVAILABLE"
        stale = False
        superseded_by = None
        for event in sorted(by_level.get(str(level["level_id"]), []), key=lambda item: (item["event_time"], item["lifecycle_event_id"])):
            if event["event_type"] == "INVALIDATED_SOURCE":
                state = "INVALIDATED_SOURCE"
            elif event["event_type"] == "SUPERSEDED":
                state = "SUPERSEDED"
                superseded_by = event.get("superseding_level_id")
            elif event["event_type"] == "RETIRED_FOR_CONSUMER" and event.get("consumer_id") == consumer_id:
                state = "RETIRED_FOR_CONSUMER"
            elif event["event_type"] == "STALE_FOR_CONSUMER" and event.get("consumer_id") == consumer_id:
                stale = True
        output.append({
            "level_id": level["level_id"], "definition": level,
            "state": state, "stale_for_consumer": stale,
            "superseded_by": superseded_by, "as_of_time": iso(as_of),
            "consumer_id": consumer_id,
        })
    output.sort(key=lambda item: (item["definition"]["first_valid_time"], item["level_id"]))
    return output


def build_swing_graph(levels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pivots = [copy.deepcopy(dict(level)) for level in levels if level.get("family") == "CONFIRMED_PIVOT"]
    pivots.sort(key=lambda item: (item["anchor_time"], item["first_valid_time"], item["level_id"]))
    nodes: list[dict[str, Any]] = []
    for level in pivots:
        node_identity = {"level_id": level["level_id"], "depth": level["structural_depth"], "clock_id": level["clock_id"]}
        nodes.append({
            "swing_node_id": digest("C2.SWING.NODE", node_identity),
            "level_id": level["level_id"], "polarity": "HIGH" if level["level_type"].endswith("HIGH") else "LOW",
            "value": level["value"], "anchor_time": level["anchor_time"],
            "first_valid_time": level["first_valid_time"], "clock_id": level["clock_id"],
            "structural_depth": level["structural_depth"], "generation_method": "RAW_OBSERVATION_PIVOT",
            "raw_metrics": {"prominence": None, "duration_observations": None, "efficiency": None, "age_observations": None, "interaction_count": 0},
            "authority": "SHADOW_ONLY",
        })
    legs: list[dict[str, Any]] = []
    for left, right in zip(nodes, nodes[1:]):
        body = {
            "from_node_id": left["swing_node_id"], "to_node_id": right["swing_node_id"],
            "price_change": float(right["value"]) - float(left["value"]),
            "start_anchor_time": left["anchor_time"], "end_anchor_time": right["anchor_time"],
            "clock_id": left["clock_id"], "structural_depth": left["structural_depth"],
        }
        legs.append({"swing_leg_id": digest("C2.SWING.LEG", body), **body})
    graph_body = {"node_ids": [node["swing_node_id"] for node in nodes], "leg_ids": [leg["swing_leg_id"] for leg in legs]}
    return {
        "swing_graph_id": digest("C2.SWING.GRAPH", graph_body),
        "nodes": nodes, "legs": legs, "hierarchy_edges": [],
        "complete_history": True, "current_pointer_is_derived": True,
        "authority": "SHADOW_ONLY",
    }


def build_pivot_of_pivots(child_graph: Mapping[str, Any], *, policy: PivotPolicy, polarity: str) -> dict[str, Any]:
    _require(policy.generation_method == "PIVOT_OF_PIVOTS", "PIVOT_OF_PIVOTS_POLICY_REQUIRED")
    synthetic: list[dict[str, Any]] = []
    for node in child_graph.get("nodes", []):
        synthetic.append({
            "observation_id": node["swing_node_id"], "first_valid_time": node["first_valid_time"],
            "interval_end": node["anchor_time"], "instrument": "GBPUSD", "side": "BID",
            "high": node["value"], "low": node["value"],
            "projection_eligibility": {"eligible": True},
            "continuity": {"segment_id": f"GRAPH:{child_graph['swing_graph_id']}"},
            "lineage": {"opt_a_release_id": None},
        })
    candidates = detect_pivot_candidates(synthetic, policy=policy, polarity=polarity)
    confirmed = [candidate for candidate in candidates if candidate["status"] == "UNIQUE_CONFIRMED"]
    parent_nodes: list[dict[str, Any]] = []
    hierarchy_edges: list[dict[str, Any]] = []
    for candidate in confirmed:
        parent_id = digest("C2.SWING.NODE", {"candidate_id": candidate["candidate_id"], "depth": policy.structural_depth, "clock_id": policy.clock_id})
        parent_nodes.append({
            "swing_node_id": parent_id, "candidate_id": candidate["candidate_id"],
            "polarity": polarity, "value": candidate["anchor_price"],
            "anchor_time": candidate["anchor_time"], "first_valid_time": candidate["first_valid_time"],
            "clock_id": policy.clock_id, "structural_depth": policy.structural_depth,
            "generation_method": "PIVOT_OF_PIVOTS", "authority": "SHADOW_ONLY",
        })
        child_ids = [item for item in candidate["member_observation_ids"]]
        for child_id in child_ids:
            body = {"parent_node_id": parent_id, "child_node_id": child_id, "edge_type": "PIVOT_OF_PIVOTS_MEMBER"}
            hierarchy_edges.append({"hierarchy_edge_id": digest("C2.SWING.HIERARCHY", body), **body})
    return {
        "parent_nodes": parent_nodes, "hierarchy_edges": hierarchy_edges,
        "candidates": candidates, "authority": "SHADOW_ONLY",
    }


def evaluate_selector(
    levels: Sequence[Mapping[str, Any]], *, selector_id: str, as_of_time: str,
    allowed_families: Sequence[str] | None = None,
    allowed_types: Sequence[str] | None = None,
    lifecycle_projection: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    _require(selector_id.startswith("SELECTOR.C2.LEVEL."), "SELECTOR_ID")
    allowed_family_set = set(allowed_families or LEVEL_FAMILIES)
    allowed_type_set = set(allowed_types or LEVEL_TYPES)
    lifecycle_by_id = {item["level_id"]: item for item in (lifecycle_projection or [])}
    candidate_ids: list[str] = []
    exclusions: list[dict[str, Any]] = []
    eligible: list[Mapping[str, Any]] = []
    as_of = parse_time(as_of_time)
    for level in levels:
        level_id = str(level["level_id"])
        candidate_ids.append(level_id)
        reason = None
        if level.get("family") not in allowed_family_set:
            reason = "EXCLUDED_FAMILY"
        elif level.get("level_type") not in allowed_type_set:
            reason = "EXCLUDED_TYPE"
        elif parse_time(str(level["first_valid_time"])) > as_of:
            reason = "NOT_FIRST_VALID_AS_OF"
        else:
            lifecycle = lifecycle_by_id.get(level_id)
            if lifecycle and lifecycle.get("state") not in {"AVAILABLE", "SUPERSEDED"}:
                reason = "LIFECYCLE_UNAVAILABLE"
            elif lifecycle and lifecycle.get("stale_for_consumer"):
                reason = "CONSUMER_STALE"
        if reason:
            exclusions.append({"level_id": level_id, "reason": reason})
        else:
            eligible.append(level)
    selected_id = None
    ties: list[str] = []
    if eligible:
        latest = max(parse_time(str(level["first_valid_time"])) for level in eligible)
        ties = sorted(str(level["level_id"]) for level in eligible if parse_time(str(level["first_valid_time"])) == latest)
        if len(ties) == 1:
            selected_id = ties[0]
            reason = "SELECTED_UNIQUE"
        else:
            reason = "TIED_CANDIDATES"
    else:
        reason = "NO_ELIGIBLE_CANDIDATE"
    body = {
        "selector_id": selector_id, "selector_version": "r1", "active": False,
        "canonical": False, "as_of_time": iso(as_of), "candidate_ids": sorted(candidate_ids),
        "eligible_ids": sorted(str(level["level_id"]) for level in eligible),
        "exclusions": sorted(exclusions, key=lambda item: (item["reason"], item["level_id"])),
        "tie_ids": ties, "selected_level_id": selected_id, "reason": reason,
        "fallback_level_id": None, "authority": "SHADOW_SELECTOR_EVIDENCE_ONLY",
    }
    return {"selector_result_id": digest("C2.LEVEL.SELECTOR.RESULT", body), **body}


def build_legacy_level_crosswalk(legacy_records: Sequence[Mapping[str, Any]], levels: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    type_map = {
        "RANGE_HIGH": "TRAILING_RANGE_HIGH", "RANGE_LOW": "TRAILING_RANGE_LOW",
        "MIDPOINT": "TRAILING_RANGE_MIDPOINT", "SWING_HIGH": "CONFIRMED_SWING_HIGH",
        "SWING_LOW": "CONFIRMED_SWING_LOW",
    }
    index: dict[tuple[str, str, float], list[str]] = {}
    for level in levels:
        key = (str(level["side"]), str(level["level_type"]), float(level["value"]))
        index.setdefault(key, []).append(str(level["level_id"]))
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in legacy_records:
        legacy_id = str(raw["legacy_level_id"])
        _require(legacy_id not in seen, "DUPLICATE_LEGACY_LEVEL")
        seen.add(legacy_id)
        mapped_type = type_map.get(str(raw["legacy_type"]))
        matches = sorted(index.get((str(raw["side"]), str(mapped_type), float(raw["value"])), [])) if mapped_type else []
        body = {
            "legacy_level_id": legacy_id, "legacy_type": raw["legacy_type"],
            "mapped_level_type": mapped_type, "matched_level_ids": matches,
            "match_status": "MATCHED_UNIQUE" if len(matches) == 1 else "MATCHED_MULTIPLE" if len(matches) > 1 else "UNMATCHED",
            "legacy_mutated": False, "historical_name_preserved": True,
            "authority": "AUDIT_ONLY",
        }
        output.append({"crosswalk_id": digest("C2.LEVEL.LEGACY.XWALK", body), **body})
    output.sort(key=lambda item: item["legacy_level_id"])
    return output


def assert_relation_cannot_mutate_level(level_before: Mapping[str, Any], level_after: Mapping[str, Any]) -> None:
    _require(canonical_bytes(level_before) == canonical_bytes(level_after), "RELATION_MUTATED_LEVEL_DEFINITION")
