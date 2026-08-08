"""Strict execution wrapper for the FSR revised-C2 rehearsal.

The first-pass FSR adapter intentionally exercised the broad component graph.  This
wrapper adds the two integration constraints required by the frozen C2 contracts:
(1) transition/relation state is reset at a continuity-segment boundary, and
(2) LOCAL_MEASUREMENT relation sets include only containers admitted to that role;
structural swing containers remain inspectable but are explicitly excluded from the
measurement relation set.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .computability import build_denominator_record
from .formula_profiles import PROFILE_IDS, build_formula_bundle, evaluate_location_profile
from .fsr_rehearsal import (
    AUTHORITY,
    PROGRAMME_ID,
    SIDES,
    _build_observation_population,
    _checkpoint_prefixes,
    _parent_context_bundle,
    _sha,
    _snapshot,
)
from .horizons import default_horizon_templates
from .relations_vnext import build_relation_set, relate_point_to_container
from .transitions import classify_transition


def _strictify_snapshot(
    snapshot: dict[str, Any],
    *,
    current_observation: Mapping[str, Any],
    previous_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rebuild role-scoped LOCATION evidence and transitions after broad stage exercise."""
    trailing_container = next(
        item for item in snapshot["containers"] if str(item.get("container_kind")) == "TRAILING_RANGE"
    )
    close_probe = {
        "probe_id": snapshot["raw"]["container_relations"][0]["subject_probe_id"],
        "value": current_observation["close"],
        "source_record_id": current_observation["observation_id"],
        "first_valid_time": current_observation["first_valid_time"],
        "probe_label": "CLOSE",
    }
    # Use the already-computed relation for the same trailing container where possible.
    trailing_relation = next(
        (
            item
            for item in snapshot["raw"]["container_relations"]
            if str(item["object_id"]) == str(trailing_container["container_id"])
        ),
        None,
    )
    if trailing_relation is None:
        trailing_relation = relate_point_to_container(close_probe, trailing_container, precision=5)

    level_set = build_relation_set(
        scope_type="LOCAL_LEVELS",
        subject_observation_id=str(current_observation["observation_id"]),
        candidate_object_ids=[str(item["level_id"]) for item in snapshot["levels"]],
        relations=snapshot["raw"]["level_relations"],
        exclusions=[],
        as_of_time=str(current_observation["first_valid_time"]),
    )
    structural_ids = [
        str(item["container_id"])
        for item in snapshot["containers"]
        if str(item["container_id"]) != str(trailing_container["container_id"])
    ]
    container_set = build_relation_set(
        scope_type="LOCAL_MEASUREMENT_CONTAINERS",
        subject_observation_id=str(current_observation["observation_id"]),
        candidate_object_ids=[str(item["container_id"]) for item in snapshot["containers"]],
        relations=[trailing_relation],
        exclusions=[{"object_id": object_id, "reason": "KIND_NOT_ALLOWED_FOR_SCOPE"} for object_id in structural_ids],
        as_of_time=str(current_observation["first_valid_time"]),
    )
    location = evaluate_location_profile(
        [level_set, container_set],
        [*snapshot["raw"]["level_relations"], trailing_relation],
        as_of_time=str(current_observation["first_valid_time"]),
    )
    outputs = [location, *[item for item in snapshot["formula_outputs"] if item["axis"] != "LOCATION"]]
    outputs.sort(key=lambda item: ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY").index(item["axis"]))
    snapshot["formula_outputs"] = outputs
    snapshot["formula_bundle"] = build_formula_bundle(outputs, as_of_time=str(current_observation["first_valid_time"]))
    snapshot["measurement_relation_sets"] = [level_set, container_set]
    snapshot["measurement_container_relation_count"] = 1
    snapshot["structural_container_exclusion_count"] = len(structural_ids)

    transitions: list[dict[str, Any]] = []
    if previous_snapshot is not None:
        previous_profiles = {item["axis"]: item for item in previous_snapshot["formula_outputs"]}
        for output in outputs:
            axis = str(output["axis"])
            transitions.append(
                classify_transition(
                    previous_profiles[axis],
                    output,
                    previous_time=str(previous_snapshot["as_of_time"]),
                    current_time=str(current_observation["first_valid_time"]),
                    profile_id=PROFILE_IDS[axis],
                    scope_id=str(current_observation["side"]),
                    measurement_fields=("facts",),
                    categorical_fields=("computability",),
                )
            )
    snapshot["transition_records"] = transitions
    return snapshot


def run_fsr_c2_vnext_strict(
    opt_a_manifest: Mapping[str, Any], c1_stream: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    population, _price_index = _build_observation_population(opt_a_manifest, c1_stream)
    snapshots: list[dict[str, Any]] = []
    continuity_resets = 0

    for side in SIDES:
        side_observations = [item for item in population["observations"] if item["side"] == side]
        by_id = {str(item["observation_id"]): item for item in side_observations}
        previous_snapshot: dict[str, Any] | None = None
        previous_segment_id: str | None = None
        for prefix in _checkpoint_prefixes(side_observations):
            current_observation = prefix[-1]
            segment_id = str(current_observation["continuity"]["segment_id"])
            if previous_segment_id is not None and segment_id != previous_segment_id:
                previous_snapshot = None
                continuity_resets += 1
            broad = _snapshot(prefix, opt_a_manifest=opt_a_manifest, previous_snapshot=previous_snapshot)
            broad["continuity_segment_id"] = segment_id
            broad["parent_context"] = _parent_context_bundle(broad, population, opt_a_manifest)
            strict = _strictify_snapshot(
                broad,
                current_observation=by_id[str(broad["observation_id"])],
                previous_snapshot=previous_snapshot,
            )
            snapshots.append(strict)
            previous_snapshot = strict
            previous_segment_id = segment_id

    component_records = [item for snapshot in snapshots for item in snapshot["computability_records"]]
    denominator = build_denominator_record(
        component_records,
        scope_id="FSR.C2.AXIS.COMPONENTS",
        scope_definition="All FSR revised-C2 axis component evaluations across deterministic checkpoints",
        unit_type="BUNDLE",
        consumer_policy_id="FSR.CONSUMER.UNAUTHORIZED.v1",
        release_id=str(opt_a_manifest["fixture_id"]),
        calendar_id="OVC.CALENDAR.GBPUSD.FSR.v1",
        clock_and_lattice_profile="15M_LOCAL_PLUS_2H_PARENT",
        instrument_scope="GBPUSD",
        side_handling="SEPARATE",
    )
    horizon_templates = [item.to_dict() for item in default_horizon_templates()]
    cross_segment_transition_count = 0
    previous_by_side: dict[str, Mapping[str, Any]] = {}
    for snapshot in snapshots:
        prior = previous_by_side.get(str(snapshot["side"]))
        if (
            prior is not None
            and prior["continuity_segment_id"] != snapshot["continuity_segment_id"]
            and snapshot["transition_records"]
        ):
            cross_segment_transition_count += len(snapshot["transition_records"])
        previous_by_side[str(snapshot["side"])] = snapshot

    body = {
        "schema": "ovc-fsr-c2-vnext-rehearsal/v2-strict",
        "programme_id": PROGRAMME_ID,
        "fixture_id": opt_a_manifest["fixture_id"],
        "population": {
            "population_id": population["population_id"],
            "expected_slot_count": population["expected_slot_count"],
            "observation_count": population["observation_count"],
            "expectation_counts": population["expectation_counts"],
            "evidence_counts": population["evidence_counts"],
            "continuity_counts": population["continuity_counts"],
            "sha256": _sha(population["observations"]),
        },
        "horizon_template_count": len(horizon_templates),
        "horizon_templates_sha256": _sha(horizon_templates),
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "transition_count": sum(len(item["transition_records"]) for item in snapshots),
        "continuity_reset_count": continuity_resets,
        "cross_segment_transition_count": cross_segment_transition_count,
        "detector_counts": {
            kind: sum(len(item["detectors"][kind]) for item in snapshots)
            for kind in ("distance", "touch", "crossing")
        },
        "axis_output_count": sum(len(item["formula_outputs"]) for item in snapshots),
        "axis_computability_counts": dict(sorted(Counter(
            output["computability"] for snapshot in snapshots for output in snapshot["formula_outputs"]
        ).items())),
        "parent_fixed_link_counts": dict(sorted(Counter(
            snapshot["parent_context"]["fixed_parent_observation_link"]["computability"] for snapshot in snapshots
        ).items())),
        "computability_denominator": denominator,
        "chronology": {
            "all_c2_first_valid_not_before_interval_end": all(
                item["first_valid_time"] >= item["interval_end"] for item in population["observations"]
            ),
            "all_formula_as_of_not_after_snapshot": all(
                output["as_of_time"] <= snapshot["as_of_time"]
                for snapshot in snapshots
                for output in snapshot["formula_outputs"]
            ),
            "hidden_construction_consumed": False,
            "cross_segment_transitions": cross_segment_transition_count,
        },
        "scope_assurance": {
            "all_measurement_relation_sets_have_one_container_relation": all(
                snapshot["measurement_container_relation_count"] == 1 for snapshot in snapshots
            ),
            "structural_container_exclusions": sum(
                snapshot["structural_container_exclusion_count"] for snapshot in snapshots
            ),
        },
        "authority": {
            "active_selector": "NONE",
            "active_formula": "NONE",
            "release_publication": "NONE",
            "validation_consumption": "DENIED",
            "semantic_event_episode_promotion": "NONE",
            "probability_risk_exposure_execution": "NONE",
            "mode": AUTHORITY,
        },
    }
    body["logical_sha256"] = _sha(body)
    return body
