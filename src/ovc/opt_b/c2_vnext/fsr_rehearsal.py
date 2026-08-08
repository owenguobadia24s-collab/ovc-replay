"""FSR v0.1 adapter for fresh-source C1 -> complete revised C2 shadow topology.

This is an integration rehearsal surface only. It binds *actual* C1 records
built from the FSR synthetic OPT-A fixture into C2 vNext observation identity,
then exercises the implemented horizon, level, container, relation, five-axis
formula, transition, parent-context and computability machinery without
activating any selector, release, semantic, event, episode or exposure path.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .computability import build_denominator_record, evaluate_component
from .containers import (
    build_container_graph,
    build_swing_envelope,
    build_trailing_range_container,
    evaluate_role_projection,
    shadow_pairing_policies,
)
from .formula_profiles import (
    PROFILE_IDS,
    build_formula_bundle,
    evaluate_interaction_profile,
    evaluate_location_profile,
    evaluate_motion_profile,
    evaluate_organisation_profile,
    evaluate_quality_profile,
)
from .horizons import HorizonDefinition, default_horizon_templates, evaluate_horizon
from .levels import (
    baseline_pivot_policies,
    build_confirmed_pivot_level,
    build_swing_graph,
    build_trailing_range_snapshot,
    detect_pivot_candidates,
    evaluate_selector,
)
from .observation import build_population, default_gbpusd_calendar, enumerate_slots
from .parent_context import resolve_parent_context
from .relations_vnext import (
    build_relation_set,
    fixed_object_crossing,
    point_probe,
    relate_point_to_container,
    relate_point_to_level,
    temporal_relation_delta,
)
from .transitions import classify_transition, detect_raw_distance_change, detect_precision_touch

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
START = "2023-06-05T00:00:00Z"
END = "2023-06-06T00:00:00Z"
SIDES = ("BID", "ASK")
AUTHORITY = "SYNTHETIC_SHADOW_NON_PROMOTABLE"


class FSRC2Error(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _float(value: Any) -> float:
    return float(str(value))


def _iso(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _c1_index(c1_stream: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for record in c1_stream:
        source_bar_id = str(record["source_bar_id"])
        if source_bar_id in index:
            raise FSRC2Error("DUPLICATE_C1_SOURCE_BAR_ID")
        index[source_bar_id] = record
    return index


def _build_observation_population(
    opt_a_manifest: Mapping[str, Any], c1_stream: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[tuple[str, str, str], Mapping[str, Any]]]:
    c1_by_source = _c1_index(c1_stream)
    evidence_rows: list[dict[str, Any]] = []
    price_index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for bar in opt_a_manifest["observations"]:
        if bar["clock_id"] != "15M":
            continue
        c1 = c1_by_source.get(str(bar["source_bar_id"]))
        if c1 is None:
            raise FSRC2Error(f"C1_PARENT_MISSING:{bar['source_bar_id']}")
        key = (str(bar["price_side"]), str(bar["open_time"]), str(bar["close_time"]))
        price_index[key] = bar
        evidence_rows.append(
            {
                "interval_start": bar["open_time"],
                "interval_end": bar["close_time"],
                "side": bar["price_side"],
                "source_record_id": bar["source_bar_id"],
                "opt_a_release_id": opt_a_manifest["fixture_id"],
                "opt_a_record_id": bar["source_bar_id"],
                "c1_release_id": f"FSR.C1.{opt_a_manifest['fixture_id']}",
                "c1_record_id": c1["record_id"],
                "complete": True,
            }
        )

    slots = enumerate_slots(
        START,
        END,
        instrument="GBPUSD",
        calendar=default_gbpusd_calendar(),
        sides=SIDES,
        partition_id="FSR.FRESH.20230605",
    )
    evidence_slot_keys = {
        (str(row["side"]), str(row["interval_start"]), str(row["interval_end"])) for row in evidence_rows
    }
    absence_classes = {
        str(slot["slot_id"]): "SOURCE_GAP"
        for slot in slots
        if (str(slot["side"]), str(slot["interval_start"]), str(slot["interval_end"])) not in evidence_slot_keys
    }
    population = build_population(
        START,
        END,
        instrument="GBPUSD",
        calendar=default_gbpusd_calendar(),
        evidence_rows=evidence_rows,
        sides=SIDES,
        absence_classes=absence_classes,
        partition_id="FSR.FRESH.20230605",
    )
    observations = copy.deepcopy(population["observations"])
    for observation in observations:
        key = (str(observation["side"]), str(observation["interval_start"]), str(observation["interval_end"]))
        bar = price_index.get(key)
        if bar is not None:
            observation.update(
                {
                    "open": _float(bar["open"]),
                    "high": _float(bar["high"]),
                    "low": _float(bar["low"]),
                    "close": _float(bar["close"]),
                }
            )
            observation["content_sha256"] = _sha({k: v for k, v in observation.items() if k != "content_sha256"})
    population = {**population, "observations": observations}
    return population, price_index


def _trailing_definition(side: str) -> HorizonDefinition:
    return HorizonDefinition(
        horizon_id=f"HORIZON.FSR.TRAILING.4.{side}.v1",
        kind="TRAILING_COUNT",
        semantic_type="OBSERVATION_COUNT",
        unit="OBSERVATION",
        grain="15M_C2_OBSERVATION",
        source_basis="FSR.FRESH.C1_TO_C2.v1",
        applicability_scope=("GBPUSD", side, "FSR_SYNTHETIC"),
        consumer_classes=("C2_MEASUREMENT",),
        causal_class="CAUSAL_BACKWARD",
        continuity_policy="SAME_CONTINUITY_SEGMENT",
        first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID",
        version="v1",
        maturity="SHADOW_EXPERIMENT",
        clock_id="LATTICE.15M.UTC_0000.v1",
        count=4,
        template=False,
        benchmark_only=False,
        canonical=False,
    )


def _available_levels(observations: Sequence[Mapping[str, Any]], as_of_time: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    policy = baseline_pivot_policies()[0]
    high_candidates = detect_pivot_candidates(observations, policy=policy, polarity="HIGH")
    low_candidates = detect_pivot_candidates(observations, policy=policy, polarity="LOW")
    confirmed = [
        build_confirmed_pivot_level(item)
        for item in [*high_candidates, *low_candidates]
        if item["status"] == "UNIQUE_CONFIRMED" and item.get("first_valid_time") is not None and str(item["first_valid_time"]) <= as_of_time
    ]
    confirmed.sort(key=lambda item: (str(item["first_valid_time"]), str(item["level_id"])))
    statuses = Counter(str(item["status"]) for item in [*high_candidates, *low_candidates])
    return confirmed, dict(sorted(statuses.items()))


def _swing_containers(confirmed: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    policies = shadow_pairing_policies()
    pairings: list[dict[str, Any]] = []
    containers: list[dict[str, Any]] = []
    for left, right in zip(confirmed, confirmed[1:]):
        left_type = str(left.get("level_type", ""))
        right_type = str(right.get("level_type", ""))
        if left_type == right_type:
            continue
        low = left if left_type == "CONFIRMED_SWING_LOW" else right
        high = left if left_type == "CONFIRMED_SWING_HIGH" else right
        pairing, container = build_swing_envelope(low, high, policy=policies[0])
        pairings.append(pairing)
        if container is not None:
            containers.append(container)
    unique = {str(item["container_id"]): item for item in containers}
    return pairings, [unique[key] for key in sorted(unique)]


def _m1_path(
    opt_a_manifest: Mapping[str, Any], *, side: str, previous_time: str, current_time: str
) -> list[float]:
    points = [
        item
        for item in opt_a_manifest["observations"]
        if item["clock_id"] == "M1"
        and item["price_side"] == side
        and str(item["close_time"]) > previous_time
        and str(item["close_time"]) <= current_time
    ]
    points.sort(key=lambda item: str(item["close_time"]))
    return [_float(item["close"]) for item in points]


def _snapshot(
    observations: Sequence[Mapping[str, Any]],
    *,
    opt_a_manifest: Mapping[str, Any],
    previous_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    current = observations[-1]
    side = str(current["side"])
    horizon_definition = _trailing_definition(side)
    horizon = evaluate_horizon(
        horizon_definition,
        observations,
        as_of_observation_id=str(current["observation_id"]),
        consumer_class="C2_MEASUREMENT",
    )
    if horizon["status"] != "COMPUTABLE":
        raise FSRC2Error(f"TRAILING_HORIZON_NOT_COMPUTABLE:{side}:{current['interval_end']}:{horizon['reason_codes']}")
    member_ids = set(horizon["member_observation_ids"])
    trailing = [item for item in observations if item["observation_id"] in member_ids]

    confirmed, candidate_counts = _available_levels(observations, str(current["first_valid_time"]))
    range_levels = build_trailing_range_snapshot(
        trailing,
        horizon_id=horizon_definition.horizon_id,
        clock_id="LATTICE.15M.UTC_0000.v1",
    )
    levels = [*confirmed, *range_levels]
    level_projection = evaluate_selector(
        levels,
        selector_id="SELECTOR.C2.LEVEL.LATEST_FIRST_VALID.r1",
        as_of_time=str(current["first_valid_time"]),
    )
    swing_graph = build_swing_graph(confirmed) if confirmed else None

    trailing_container = build_trailing_range_container(range_levels)
    pairing_records, swing_containers = _swing_containers(confirmed)
    containers = [trailing_container, *swing_containers]
    container_graph = build_container_graph(containers)
    measurement_projection = evaluate_role_projection(
        containers,
        projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1",
        role="LOCAL_MEASUREMENT",
        scope_kind="LOCAL",
        as_of_time=str(current["first_valid_time"]),
    )
    structural_projection = evaluate_role_projection(
        containers,
        projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1",
        role="LOCAL_STRUCTURAL",
        scope_kind="LOCAL",
        as_of_time=str(current["first_valid_time"]),
    )

    close_probe = point_probe(
        value=_float(current["close"]),
        source_record_id=str(current["observation_id"]),
        first_valid_time=str(current["first_valid_time"]),
        probe_label="CLOSE",
    )
    level_relations = [relate_point_to_level(close_probe, item, precision=5) for item in levels]
    container_relations = [relate_point_to_container(close_probe, item, precision=5) for item in containers]
    level_set = build_relation_set(
        scope_type="LOCAL_LEVELS",
        subject_observation_id=str(current["observation_id"]),
        candidate_object_ids=[str(item["level_id"]) for item in levels],
        relations=level_relations,
        exclusions=[],
        as_of_time=str(current["first_valid_time"]),
    )
    container_set = build_relation_set(
        scope_type="LOCAL_MEASUREMENT_CONTAINERS",
        subject_observation_id=str(current["observation_id"]),
        candidate_object_ids=[str(item["container_id"]) for item in containers],
        relations=container_relations,
        exclusions=[],
        as_of_time=str(current["first_valid_time"]),
    )

    previous_relations = {} if previous_snapshot is None else {
        str(item["object_id"]): item for item in previous_snapshot["raw"]["level_relations"]
    }
    relation_deltas: list[dict[str, Any]] = []
    crossings: list[dict[str, Any]] = []
    distance_detectors: list[dict[str, Any]] = []
    touch_detectors: list[dict[str, Any]] = []
    for relation in level_relations:
        object_id = str(relation["object_id"])
        previous = previous_relations.get(object_id)
        if previous is not None:
            delta = temporal_relation_delta(previous, relation)
            relation_deltas.append(delta)
            distance_detectors.append(
                detect_raw_distance_change(
                    object_id=object_id,
                    previous_object_id=object_id,
                    absolute_distance_delta=delta["absolute_distance_delta"],
                    relation_delta_id=delta["relation_delta_id"],
                    as_of_time=str(current["first_valid_time"]),
                )
            )
            object_level = next(item for item in levels if str(item["level_id"]) == object_id)
            previous_time = str(previous_snapshot["as_of_time"])
            path = _m1_path(
                opt_a_manifest,
                side=side,
                previous_time=previous_time,
                current_time=str(current["first_valid_time"]),
            )
            if len(path) >= 2:
                crossings.append(
                    fixed_object_crossing(
                        object_id=object_id,
                        object_value=_float(object_level["value"]),
                        previous_value=path[0],
                        current_value=path[-1],
                        previous_time=previous_time,
                        current_time=str(current["first_valid_time"]),
                        precision=5,
                        evidence_mode="M1_PATH",
                        ordered_path=path,
                    )
                )
        touch_detectors.append(
            detect_precision_touch(
                object_id=object_id,
                probe_id=str(relation["subject_probe_id"]),
                raw_topology=str(relation["topology"]),
                source_precision=5,
                as_of_time=str(current["first_valid_time"]),
            )
        )

    location = evaluate_location_profile(
        [level_set, container_set],
        [*level_relations, *container_relations],
        as_of_time=str(current["first_valid_time"]),
    )
    member_by_id = {str(item["observation_id"]): item for item in observations}
    horizon_members = [member_by_id[item] for item in horizon["member_observation_ids"]]
    price_delta = _float(horizon_members[-1]["close"]) - _float(horizon_members[0]["close"])
    motion = evaluate_motion_profile(
        {**horizon, "status": "COMPLETE"},
        price_delta=price_delta,
        relation_deltas=relation_deltas,
        as_of_time=str(current["first_valid_time"]),
    )
    organisation = evaluate_organisation_profile(
        container_graph,
        swing_graph=swing_graph,
        as_of_time=str(current["first_valid_time"]),
    )
    interaction = evaluate_interaction_profile(
        relation_deltas=relation_deltas,
        crossing_evidence=crossings,
        reference_changes=[],
        as_of_time=str(current["first_valid_time"]),
    )
    quality = evaluate_quality_profile(
        [
            {
                "component_id": f"OBSERVATION:{current['observation_id']}",
                "status": "COMPUTABLE",
                "reason_codes": [],
                "source_ids": [str(current["evidence"].get("source_record_id"))],
                "censored": False,
                "ambiguous": False,
                "conflict": False,
                "first_valid_time": str(current["first_valid_time"]),
            },
            {
                "component_id": str(horizon["membership_id"]),
                "status": "COMPUTABLE",
                "reason_codes": list(horizon.get("reason_codes", [])),
                "source_ids": list(horizon["member_observation_ids"]),
                "censored": False,
                "ambiguous": False,
                "conflict": False,
                "first_valid_time": str(current["first_valid_time"]),
            },
        ],
        as_of_time=str(current["first_valid_time"]),
    )
    formula_outputs = [location, motion, organisation, interaction, quality]
    bundle = build_formula_bundle(formula_outputs, as_of_time=str(current["first_valid_time"]))

    transition_records: list[dict[str, Any]] = []
    if previous_snapshot is not None:
        previous_profiles = {item["axis"]: item for item in previous_snapshot["formula_outputs"]}
        for output in formula_outputs:
            axis = str(output["axis"])
            previous_output = previous_profiles[axis]
            transition_records.append(
                classify_transition(
                    previous_output,
                    output,
                    previous_time=str(previous_snapshot["as_of_time"]),
                    current_time=str(current["first_valid_time"]),
                    profile_id=PROFILE_IDS[axis],
                    scope_id=side,
                    measurement_fields=("facts",),
                    categorical_fields=("computability",),
                )
            )

    components: list[dict[str, Any]] = []
    for output in formula_outputs:
        dependency_id = str(output["profile_output_id"])
        components.append(
            evaluate_component(
                component_id=f"FSR.AXIS.{side}.{output['axis']}",
                profile_id=str(output["profile_id"]),
                unit_id=str(current["observation_id"]),
                as_of_time=str(current["first_valid_time"]),
                dependency_edges=[{"dependency_id": dependency_id, "edge_type": "REQUIRED"}],
                dependency_results={dependency_id: {"status": output["computability"], "reason_codes": output["reason_codes"]}},
                assurance_status="ASSURED",
                source_ids=list(output.get("source_ids", [])),
            )
        )

    return {
        "snapshot_id": f"FSR.C2.SNAPSHOT.{_sha({'side': side, 'time': current['first_valid_time'], 'bundle': bundle['bundle_id']})[:24]}",
        "side": side,
        "as_of_time": str(current["first_valid_time"]),
        "observation_id": str(current["observation_id"]),
        "horizon": horizon,
        "candidate_status_counts": candidate_counts,
        "levels": levels,
        "level_projection": level_projection,
        "swing_graph": swing_graph,
        "pairing_records": pairing_records,
        "containers": containers,
        "container_graph": container_graph,
        "measurement_projection": measurement_projection,
        "structural_projection": structural_projection,
        "formula_outputs": formula_outputs,
        "formula_bundle": bundle,
        "transition_records": transition_records,
        "computability_records": components,
        "detectors": {"distance": distance_detectors, "touch": touch_detectors, "crossing": crossings},
        "raw": {"level_relations": level_relations, "container_relations": container_relations, "relation_deltas": relation_deltas},
        "authority": AUTHORITY,
    }


def _checkpoint_prefixes(observations: Sequence[Mapping[str, Any]]) -> list[list[Mapping[str, Any]]]:
    by_segment: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in observations:
        if item.get("projection_eligibility", {}).get("eligible") and item.get("continuity", {}).get("segment_id"):
            by_segment[str(item["continuity"]["segment_id"])].append(item)
    prefixes: list[list[Mapping[str, Any]]] = []
    for segment_id in sorted(by_segment, key=lambda key: str(by_segment[key][0]["interval_start"])):
        segment = sorted(by_segment[segment_id], key=lambda item: str(item["interval_start"]))
        for length in range(8, len(segment) + 1, 8):
            prefixes.append(segment[:length])
        if len(segment) >= 8 and (not prefixes or prefixes[-1][-1]["observation_id"] != segment[-1]["observation_id"]):
            prefixes.append(segment)
    return prefixes


def _parent_context_bundle(
    snapshot: Mapping[str, Any], population: Mapping[str, Any], opt_a_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    local_observation = next(
        item for item in population["observations"] if item["observation_id"] == snapshot["observation_id"]
    )
    release_id = str(opt_a_manifest["fixture_id"])
    calendar_id = "OVC.CALENDAR.GBPUSD.FSR.v1"
    parent_lattice_id = "LATTICE.2H.UTC_0000.v1"
    local = {
        "observation_id": local_observation["observation_id"],
        "first_valid_time": local_observation["first_valid_time"],
        "instrument_id": "GBPUSD",
        "side": local_observation["side"],
        "release_id": release_id,
        "calendar_id": calendar_id,
        "parent_lattice_id": parent_lattice_id,
        "parent_scope_id": f"FSR.PARENT.{local_observation['side']}",
    }
    parent_slots = []
    for item in opt_a_manifest["observations"]:
        if item["clock_id"] != "2H_A_L" or item["price_side"] != local_observation["side"]:
            continue
        parent_slots.append(
            {
                "observation_id": item["source_bar_id"],
                "interval_start": item["open_time"],
                "interval_end": item["close_time"],
                "first_valid_time": item["first_valid_time"],
                "instrument_id": "GBPUSD",
                "side": item["price_side"],
                "release_id": release_id,
                "calendar_id": calendar_id,
                "parent_lattice_id": parent_lattice_id,
                "status": "COMPLETE",
                "source_id": item["source_bar_id"],
            }
        )
    return resolve_parent_context(
        local_observation=local,
        parent_slots=parent_slots,
        eligible_local_observation_count=sum(
            1 for item in population["observations"] if item["side"] == local_observation["side"] and item["projection_eligibility"]["eligible"] and item["first_valid_time"] <= local_observation["first_valid_time"]
        ),
        registered_closure_count=0,
        episode_authority=False,
    )


def run_fsr_c2_vnext(
    opt_a_manifest: Mapping[str, Any], c1_stream: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    population, _price_index = _build_observation_population(opt_a_manifest, c1_stream)
    snapshots: list[dict[str, Any]] = []
    for side in SIDES:
        side_observations = [item for item in population["observations"] if item["side"] == side]
        previous_snapshot = None
        for prefix in _checkpoint_prefixes(side_observations):
            snapshot = _snapshot(prefix, opt_a_manifest=opt_a_manifest, previous_snapshot=previous_snapshot)
            snapshot["parent_context"] = _parent_context_bundle(snapshot, population, opt_a_manifest)
            snapshots.append(snapshot)
            previous_snapshot = snapshot

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
    manifest_body = {
        "schema": "ovc-fsr-c2-vnext-rehearsal/v1",
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
                output["as_of_time"] <= snapshot["as_of_time"] for snapshot in snapshots for output in snapshot["formula_outputs"]
            ),
            "hidden_construction_consumed": False,
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
    manifest_body["logical_sha256"] = _sha(manifest_body)
    return manifest_body
