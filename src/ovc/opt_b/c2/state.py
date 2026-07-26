from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from .adapter import accept_c1_record
from .containers import build_containers
from .identity import stable_id
from .levels import PARAMETER_PACK_ID, build_levels
from .relations import build_relation_set

AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
_MOTION_BOUNDARIES = (Decimal("-0.75"), Decimal("-0.15"), Decimal("0.15"), Decimal("0.75"))
_MOTION_VALUES = ("DOWN_PROGRESS", "DOWN_STALL", "BALANCED", "UP_STALL", "UP_PROGRESS")
_ORGANISATION_BOUNDARIES = (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))
_ORGANISATION_VALUES = ("DISORDERED", "FORMING", "ORDERED", "DEGRADING")


def _axis(
    value: str | None,
    *,
    status: str = "EVALUATED",
    reason: str | None = None,
    measurement: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status, "value": value}
    if reason:
        out["reason_code"] = reason
    if measurement is not None:
        out["measurement"] = measurement
    return out


def _bucket(value: Decimal, boundaries: Sequence[Decimal], labels: Sequence[str]) -> str:
    for boundary, label in zip(boundaries, labels):
        if value < boundary:
            return label
    return labels[-1]


def build_structure(
    record: Mapping[str, Any],
    *,
    history: Sequence[Mapping[str, Any]] | None = None,
    previous_record: Mapping[str, Any] | None = None,
    parent_levels: Iterable[Mapping[str, Any]] | None = None,
    evaluation_scope_id: str | None = None,
) -> dict[str, Any]:
    parent = accept_c1_record(record)
    accepted_history = [accept_c1_record(item) for item in (history or [parent])]
    levels = build_levels(parent, accepted_history)
    parent_level_items = list(parent_levels or ())
    containers = build_containers(parent, levels, parent_level_items)
    relation_levels = levels + parent_level_items
    relation_set = build_relation_set(
        parent,
        relation_levels,
        containers,
        previous_record,
        evaluation_scope_id=evaluation_scope_id,
    )
    return {
        "levels": levels,
        "containers": containers,
        "relation_set": relation_set,
    }


def build_parallel_state(
    record: Mapping[str, Any],
    *,
    history: Sequence[Mapping[str, Any]] | None = None,
    previous_record: Mapping[str, Any] | None = None,
    parent_levels: Iterable[Mapping[str, Any]] | None = None,
    evaluation_scope_id: str | None = None,
    structure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    parent = accept_c1_record(record)
    previous = accept_c1_record(previous_record) if previous_record is not None else None
    parent_level_items = list(parent_levels or ())
    structure = dict(structure) if structure is not None else build_structure(
        parent,
        history=history,
        previous_record=previous,
        parent_levels=parent_level_items,
        evaluation_scope_id=evaluation_scope_id,
    )
    levels = structure["levels"]
    containers = structure["containers"]
    relation_set = structure["relation_set"]
    close = Decimal(parent["prices"]["close"])
    local = next(
        (
            item
            for item in containers
            if item.get("container_type") == "LOCAL_RANGE" and item.get("status") == "ACTIVE"
        ),
        None,
    )
    if local is None:
        location = _axis(None, status="NOT_EVALUATED", reason="WINDOW_NOT_COMPLETE")
        motion = _axis(None, status="NOT_EVALUATED", reason="WINDOW_NOT_COMPLETE")
        organisation = _axis(None, status="NOT_EVALUATED", reason="WINDOW_NOT_COMPLETE")
        local_scale = None
    else:
        low = Decimal(str(local["low"]))
        high = Decimal(str(local["high"]))
        local_scale = high - low
        if local_scale == 0:
            location = _axis(None, status="NOT_EVALUABLE", reason="AMBIGUOUS_BOUNDARY")
            motion = _axis(None, status="NOT_EVALUABLE", reason="AMBIGUOUS_BOUNDARY")
            organisation = _axis(None, status="NOT_EVALUABLE", reason="AMBIGUOUS_BOUNDARY")
        else:
            normalized = (close - low) / local_scale
            if normalized < 0:
                location_value = "BELOW"
            elif normalized < Decimal("0.33"):
                location_value = "LOWER_REGION"
            elif normalized < Decimal("0.67"):
                location_value = "MID_REGION"
            elif normalized <= 1:
                location_value = "UPPER_REGION"
            else:
                location_value = "ABOVE"
            location = _axis(location_value, measurement=format(normalized, "f"))

            if previous is None:
                motion = _axis(None, status="NOT_EVALUATED", reason="NO_CONTIGUOUS_PRIOR_STATE")
            else:
                progress = (close - Decimal(previous["prices"]["close"])) / local_scale
                motion = _axis(
                    _bucket(progress, _MOTION_BOUNDARIES, _MOTION_VALUES),
                    measurement=format(progress, "f"),
                )
            dispersion = Decimal(parent["measurements"]["range_abs"]) / local_scale
            organisation = _axis(
                _bucket(dispersion, _ORGANISATION_BOUNDARIES, _ORGANISATION_VALUES),
                measurement=format(dispersion, "f"),
            )

    level_relations = [item for item in relation_set["relations"] if "level_id" in item]
    relation_types = {item["relation_type"] for item in level_relations}
    if {"CROSSED_UP", "CROSSED_DOWN"} & relation_types:
        interaction = _axis("CROSSING")
    elif "AT_LEVEL" in relation_types:
        interaction = _axis("TESTING")
    elif not level_relations:
        interaction = _axis(None, status="NOT_EVALUATED", reason="NO_FIRST_VALID_LEVEL")
    elif previous is None:
        interaction = _axis("BEYOND")
    else:
        current_distance = min(abs(Decimal(item["signed_distance"])) for item in level_relations)
        prior_close = Decimal(previous["prices"]["close"])
        prior_distance = min(
            abs(prior_close - Decimal(level["value"]))
            for level in levels + parent_level_items
            if level.get("status") == "ACTIVE"
        )
        interaction = _axis(
            "APPROACHING" if current_distance < prior_distance else "REJECTING",
            measurement=format(current_distance, "f"),
        )

    conflicts = any(item.get("status") == "CONFLICT" for item in containers)
    exclusions = relation_set["exclusions"]
    if conflicts:
        quality = _axis("CONFLICT", status="CONFLICT", reason="AMBIGUOUS_BOUNDARY")
    elif local_scale is None:
        quality = _axis("CENSORED", reason="WINDOW_NOT_COMPLETE")
    elif exclusions:
        quality = _axis("DEGRADED", reason="RELATION_EXCLUDED")
    else:
        quality = _axis("COMPLETE")

    axes = {
        "LOCATION": location,
        "MOTION": motion,
        "ORGANISATION": organisation,
        "INTERACTION": interaction,
        "QUALITY": quality,
    }
    scope_id = evaluation_scope_id or (
        "GBPUSD-15M-LOCAL-v0.1" if parent["clock"] == "15M" else "GBPUSD-2H-A-L-LOCAL-v0.1"
    )
    identity = {
        "c1_record_id": parent["c1_record_id"],
        "source_bar_id": parent["source_bar_id"],
        "c1_release_id": parent["c1_release_id"],
        "opt_a_release_id": parent["opt_a_release_id"],
        "first_valid_time": parent["first_valid_time"],
        "clock": parent["clock"],
        "side": parent["side"],
        "evaluation_scope_id": scope_id,
        "parameter_pack_id": PARAMETER_PACK_ID,
        "axes": axes,
    }
    return {
        "c2_state_id": stable_id("c2-state", identity),
        "parent_c1_record_id": parent["c1_record_id"],
        "parent_opt_a_bar_id": parent["source_bar_id"],
        "c1_release_id": parent["c1_release_id"],
        "c1_manifest_id": parent["c1_manifest_id"],
        "opt_a_release_id": parent["opt_a_release_id"],
        "opt_a_manifest_id": parent["opt_a_manifest_id"],
        "first_valid_time": parent["first_valid_time"],
        "clock": parent["clock"],
        "side": parent["side"],
        "evaluation_scope_id": scope_id,
        "parameter_pack_id": PARAMETER_PACK_ID,
        "axes": axes,
        "level_ids": [item["c2_level_id"] for item in levels if item.get("status") == "ACTIVE"],
        "container_ids": [item["c2_container_id"] for item in containers if item.get("status") == "ACTIVE"],
        "relation_set_id": relation_set["c2_relation_set_id"],
    }
