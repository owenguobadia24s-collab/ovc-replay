from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Mapping

from ovc.opt_b.c2_vnext.observation import (
    build_population, default_gbpusd_calendar, bind_evidence,
    assign_continuity, baseline_lattices, digest, parse_time, iso,
)
from ovc.opt_b.c2_vnext.horizons import HorizonDefinition
from ovc.opt_b.c2_vnext.levels import build_trailing_range_snapshot
from ovc.opt_b.c2_vnext.containers import build_trailing_range_container, build_container_graph
from ovc.opt_b.c2_vnext.relations_vnext import (
    point_probe, relate_point_to_level, relate_point_to_container,
    build_relation_set, temporal_relation_delta, reference_change_record,
)
from ovc.opt_b.c2_vnext.formula_profiles import (
    evaluate_location_profile, evaluate_motion_profile,
    evaluate_organisation_profile, evaluate_interaction_profile,
)
from ovc.opt_b.c2_vnext.parent_context import resolve_parent_context, expected_parent_slot

SCHEMA = "ovc-c2-vnext-real-source-observation-materialisation/v1"
PACKET_ID = "C2VNEXT-REAL-OBS-MATERIALISATION-20260809"
MATERIALISATION_ID = "C2VNEXT.JUNE.REAL.OBSERVATION.MATERIALISATION.v1"
CONTEXT_START = "2026-05-30T00:00:00Z"
CONTEXT_END = "2026-07-03T00:00:00Z"
TARGET_START = "2026-06-01T00:00:00Z"
TARGET_END = "2026-07-01T00:00:00Z"
INSTRUMENT = "GBPUSD"
PARTITION_ID = MATERIALISATION_ID
PARENT_LATTICE_ID = "LATTICE.2H.UTC_0000.v1"
LOCAL_LATTICE_ID = "LATTICE.15M.UTC_0000.v1"
SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
SOURCE_MANIFEST_SHA256 = "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
C1_RELEASE_ID = "RPS.C1SET.GBPUSD.PD-JUNE-FM.20260530_20260703.v1"
C1_MANIFEST_ID = "RPS.C1MANIFEST.PD-JUNE-FM.9cad7d7274091b27fb153c99"
C2AR_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2AR_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
HORIZON_COUNTS = (4, 8, 16)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(value: Any) -> str:
    return sha256_bytes(canonical(value))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def c1_to_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "interval_start": row["open_time"], "interval_end": row["close_time"],
        "side": row["side"], "source_record_id": row["c1_record_id"],
        "opt_a_release_id": row["opt_a_release_id"], "opt_a_record_id": row["source_bar_id"],
        "c1_release_id": row["c1_release_id"], "c1_record_id": row["c1_record_id"],
        "complete": row.get("quality_state") == "COMPLETE",
    }


def enrich_observation(observation: dict[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(observation)
    for key in ("open", "high", "low", "close"):
        result[key] = float(row["prices"][key])
    result["content_sha256"] = sha256_obj({k: v for k, v in result.items() if k != "content_sha256"})
    return result


def horizon_definition(count: int) -> HorizonDefinition:
    return HorizonDefinition(
        horizon_id=f"HORIZON.MOTION.15M.TRAILING.{count}.r1",
        kind="TRAILING_COUNT", semantic_type="OBSERVATION_COUNT",
        unit="OBSERVATION", grain="15M_C2_OBSERVATION",
        source_basis="P2-Q1_CANDIDATE_PROFILE" if count != 8 else "LEGACY_DECLARED_AND_P2_Q1_CANDIDATE",
        applicability_scope=("GBPUSD", "BID", "ASK", "MOTION"),
        consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_BACKWARD",
        continuity_policy="SAME_CONTINUITY_SEGMENT",
        first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", version="r1",
        maturity="SHADOW_EXPERIMENT", clock_id=LOCAL_LATTICE_ID,
        count=count, template=False, benchmark_only=False, canonical=False,
    )


def fast_horizon(definition: HorizonDefinition, full_items: list[dict[str, Any]], index: int) -> dict[str, Any]:
    """Exact optimized TRAILING_COUNT evaluator; CI proves equality with the frozen evaluator."""
    current = full_items[index]
    count = int(definition.count)
    selected = None
    if index + 1 < count:
        reason = "WARM_UP_INSUFFICIENT"
    else:
        selected = [copy.deepcopy(dict(item)) for item in full_items[index-count+1:index+1]]
        statuses = {str(item.get("continuity", {}).get("status")) for item in selected}
        segments = {item.get("continuity", {}).get("segment_id") for item in selected}
        if not all(bool(item.get("projection_eligibility", {}).get("eligible", False)) for item in selected) or len(segments) != 1 or None in segments:
            if "CLOSURE_BOUNDARY" in statuses:
                reason = "CLOSURE_BOUNDARY"
            elif "UNKNOWN_BREAK" in statuses:
                reason = "UNKNOWN_BREAK"
            elif statuses & {"GAP_RESET", "PARTITION_BOUNDARY"}:
                reason = "GAP_OR_RESET"
            else:
                reason = "DISCONTINUITY"
            selected = None
        elif any(str(left["interval_end"]) != str(right["interval_start"]) for left, right in zip(selected, selected[1:])):
            reason = "DISCONTINUITY"
            selected = None
        else:
            reason = "OK"
    if selected is None:
        body = {
            "horizon_id": definition.horizon_id, "definition_sha256": definition.definition_sha256,
            "kind": definition.kind, "as_of_observation_id": current["observation_id"],
            "as_of_first_valid_time": current["first_valid_time"], "status": "NOT_COMPUTABLE",
            "reason": reason, "member_observation_ids": [], "member_first_valid_times": [],
            "segment_id": current.get("continuity", {}).get("segment_id"), "causal_store_eligible": False,
            "benchmark_only": definition.benchmark_only, "metadata": {"requested_count": count}, "authority": "SHADOW_ONLY",
        }
    else:
        body = {
            "horizon_id": definition.horizon_id, "definition_sha256": definition.definition_sha256,
            "kind": definition.kind, "as_of_observation_id": current["observation_id"],
            "as_of_first_valid_time": current["first_valid_time"], "available_at": current["first_valid_time"],
            "status": "COMPUTABLE", "reason": "OK",
            "member_observation_ids": [str(item["observation_id"]) for item in selected],
            "member_first_valid_times": [str(item["first_valid_time"]) for item in selected],
            "segment_id": current.get("continuity", {}).get("segment_id"), "causal_store_eligible": True,
            "benchmark_only": definition.benchmark_only, "metadata": {"requested_count": count}, "authority": "SHADOW_ONLY",
        }
    return {"membership_id": digest("C2.HORIZON.MEMBERSHIP", body), **body}


def formula_membership(horizon: Mapping[str, Any], current_fvt: str) -> dict[str, Any]:
    status = "COMPLETE" if horizon["status"] == "COMPUTABLE" else str(horizon.get("reason") or horizon["status"])
    return {
        "membership_id": horizon["membership_id"], "horizon_id": horizon["horizon_id"],
        "status": status, "member_observation_ids": list(horizon.get("member_observation_ids", [])),
        "first_valid_time": current_fvt,
    }


def build_side(side: str, rows15: list[dict[str, Any]], rows2h: list[dict[str, Any]]) -> dict[str, Any]:
    calendar = default_gbpusd_calendar()
    pop15 = build_population(
        CONTEXT_START, CONTEXT_END, instrument=INSTRUMENT, calendar=calendar,
        evidence_rows=[c1_to_evidence(row) for row in rows15], sides=(side,),
        lattices=(baseline_lattices()[0],), partition_id=PARTITION_ID,
    )
    c1_by_interval15 = {(r["open_time"], r["close_time"], r["side"]): r for r in rows15}
    full15, complete15, target_ids = [], [], set()
    for raw in pop15["observations"]:
        row = c1_by_interval15.get((raw["interval_start"], raw["interval_end"], raw["side"]))
        obs = enrich_observation(raw, row) if row and raw["projection_eligibility"]["eligible"] else raw
        full15.append(obs)
        if row and raw["projection_eligibility"]["eligible"]:
            complete15.append(obs)
            if row.get("target_eligible") is True:
                target_ids.add(obs["observation_id"])

    evidence2h = [c1_to_evidence(row) for row in rows2h]
    slots2h = []
    for row in rows2h:
        start, end = parse_time(row["open_time"]), parse_time(row["close_time"])
        identity = {"instrument": INSTRUMENT, "side": side, "interval_start": iso(start), "interval_end": iso(end), "partition_id": PARTITION_ID}
        slots2h.append({"slot_id": digest("C2.SLOT", identity), **identity, "expectation": calendar.classify(start, end)})
    two_h_lattice = next(profile for profile in baseline_lattices() if profile.interval_minutes == 120)
    full2h = assign_continuity(bind_evidence(slots2h, evidence2h, lattices=(two_h_lattice,)))
    c1_by_interval2h = {(r["open_time"], r["close_time"], r["side"]): r for r in rows2h}
    complete2h = []
    for raw in full2h:
        row = c1_by_interval2h.get((raw["interval_start"], raw["interval_end"], raw["side"]))
        if row and raw["projection_eligibility"]["eligible"]:
            complete2h.append(enrich_observation(raw, row))

    parent_slots = [{
        "observation_id": obs["observation_id"], "interval_start": obs["interval_start"], "interval_end": obs["interval_end"],
        "first_valid_time": obs["first_valid_time"], "status": "COMPLETE", "source_id": obs["lineage"]["c1_record_id"],
        "instrument_id": INSTRUMENT, "side": side, "release_id": C1_RELEASE_ID,
        "calendar_id": calendar.calendar_id, "parent_lattice_id": PARENT_LATTICE_ID,
    } for obs in complete2h]
    parent_slot_index = {(item["interval_start"], item["interval_end"]): item for item in parent_slots}
    full_index = {obs["observation_id"]: index for index, obs in enumerate(full15)}
    complete_by_id = {obs["observation_id"]: obs for obs in complete15}
    horizon_defs = [horizon_definition(count) for count in HORIZON_COUNTS]

    memberships, levels, containers, relations, relation_sets, profiles, contexts, bundles = [], [], [], [], [], [], [], []
    previous_refs, previous_relations, previous_segment = {}, {}, None

    for current in complete15:
        current_id, current_fvt = current["observation_id"], current["first_valid_time"]
        segment = current["continuity"]["segment_id"]
        if segment != previous_segment:
            previous_refs, previous_relations = {}, {}
        previous_segment = segment
        current_levels, current_containers, motion_profiles, current_ref_map = [], [], [], {}
        for definition in horizon_defs:
            horizon = fast_horizon(definition, full15, full_index[current_id])
            memberships.append(horizon)
            price_delta = None
            if horizon["status"] == "COMPUTABLE":
                member_obs = [complete_by_id[member_id] for member_id in horizon["member_observation_ids"]]
                price_delta = float(current["close"]) - float(member_obs[0]["close"])
                range_levels = build_trailing_range_snapshot(member_obs, horizon_id=definition.horizon_id, clock_id=LOCAL_LATTICE_ID)
                current_levels.extend(range_levels)
                current_containers.append(build_trailing_range_container(range_levels))
                for level in range_levels:
                    current_ref_map[(definition.horizon_id, level["level_type"])] = level["level_id"]
            motion_profiles.append(evaluate_motion_profile(
                formula_membership(horizon, current_fvt), price_delta=price_delta, relation_deltas=[], as_of_time=current_fvt,
            ))

        graph = build_container_graph(current_containers)
        probe = point_probe(value=float(current["close"]), source_record_id=current_id, first_valid_time=current_fvt, probe_label="CLOSE")
        level_relations = [relate_point_to_level(probe, item, precision=5) for item in current_levels]
        container_relations = [relate_point_to_container(probe, item, precision=5) for item in current_containers]
        sets = []
        if current_levels:
            sets.append(build_relation_set(scope_type="LOCAL_LEVELS", subject_observation_id=current_id,
                candidate_object_ids=[item["level_id"] for item in current_levels], relations=level_relations, exclusions=[], as_of_time=current_fvt))
        if current_containers:
            sets.append(build_relation_set(scope_type="LOCAL_MEASUREMENT_CONTAINERS", subject_observation_id=current_id,
                candidate_object_ids=[item["container_id"] for item in current_containers], relations=container_relations, exclusions=[], as_of_time=current_fvt))
        location = evaluate_location_profile(sets, [*level_relations, *container_relations], as_of_time=current_fvt)
        organisation = evaluate_organisation_profile(graph, swing_graph=None, as_of_time=current_fvt)

        current_relation_map = {relation["object_id"]: relation for relation in level_relations}
        deltas = [temporal_relation_delta(previous_relations[object_id], relation)
                  for object_id, relation in current_relation_map.items() if object_id in previous_relations]
        ref_changes = []
        for key, current_level_id in sorted(current_ref_map.items()):
            prior_level_id = previous_refs.get(key)
            if prior_level_id is not None and prior_level_id != current_level_id:
                ref_changes.append(reference_change_record(previous_object_id=prior_level_id, current_object_id=current_level_id,
                    first_valid_time=current_fvt, reason="TRAILING_RANGE_SNAPSHOT_REFRESH"))
        interaction = evaluate_interaction_profile(relation_deltas=deltas, crossing_evidence=[], reference_changes=ref_changes, as_of_time=current_fvt)
        previous_refs, previous_relations = current_ref_map, current_relation_map

        local_parent = {"observation_id": current_id, "first_valid_time": current_fvt, "instrument_id": INSTRUMENT,
            "side": side, "release_id": C1_RELEASE_ID, "calendar_id": calendar.calendar_id,
            "parent_lattice_id": PARENT_LATTICE_ID, "parent_scope_id": "PARENT_2H_A_L"}
        expected_start, expected_end = expected_parent_slot(current_fvt)
        parent_candidate = parent_slot_index.get((expected_start, expected_end))
        context = resolve_parent_context(local_observation=local_parent,
            parent_slots=([parent_candidate] if parent_candidate is not None else []), parent_objects=(), structural_depths=(),
            higher_order_local_objects=(), episode_candidates=(), previous_bundle=None,
            eligible_local_observation_count=len(complete15), registered_closure_count=0, episode_authority=False)

        levels.extend(current_levels); containers.extend(current_containers)
        relations.extend(level_relations); relations.extend(container_relations); relations.extend(deltas); relations.extend(ref_changes)
        relation_sets.extend(sets); profiles.extend([location, *motion_profiles, organisation, interaction]); contexts.append(context)
        bundles.append({"schema": "ovc-c2-vnext-observation-materialisation-bundle/v1", "materialisation_id": MATERIALISATION_ID,
            "observation_id": current_id, "first_valid_time": current_fvt, "side": side, "target_eligible": current_id in target_ids,
            "horizon_membership_ids": [item["membership_id"] for item in memberships[-len(horizon_defs):]],
            "profile_output_ids": {"LOCATION": [location["profile_output_id"]], "MOTION": [item["profile_output_id"] for item in motion_profiles],
                "ORGANISATION": [organisation["profile_output_id"]], "INTERACTION": [interaction["profile_output_id"]]},
            "level_ids": [item["level_id"] for item in current_levels], "container_ids": [item["container_id"] for item in current_containers],
            "relation_set_ids": [item["relation_set_id"] for item in sets], "context_bundle_id": context["bundle_id"],
            "fixed_parent_observation_id": context["fixed_parent_observation_link"]["selected_id"],
            "authority": "SHADOW_FROZEN_READ_ONLY_MATERIALISATION_ONLY"})

    return {"side": side, "full15": full15, "complete15": complete15, "complete2h": complete2h, "target_ids": target_ids,
        "memberships": memberships, "levels": levels, "containers": containers, "relations": relations,
        "relation_sets": relation_sets, "profiles": profiles, "contexts": contexts, "bundles": bundles}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(canonical(row)); handle.write(b"\n")
    data = path.read_bytes()
    return {"file_name": path.name, "record_count": len(rows), "size_bytes": len(data), "sha256": sha256_bytes(data)}


def materialise(out_dir: Path, paths: Mapping[str, Path]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {key: load_jsonl(path) for key, path in paths.items()}
    for key, rows in inputs.items():
        expected_side = "BID" if "bid" in key else "ASK"
        expected_clock = "15M" if "15m" in key else "2H_A_L"
        if {row["side"] for row in rows} != {expected_side} or {row["clock"] for row in rows} != {expected_clock}:
            raise ValueError(f"INPUT_SCOPE_MISMATCH:{key}")
        if {row["c1_release_id"] for row in rows} != {C1_RELEASE_ID} or {row["source_slice_id"] for row in rows} != {SOURCE_SLICE_ID}:
            raise ValueError(f"INPUT_IDENTITY_MISMATCH:{key}")
        if {row["source_manifest_sha256"] for row in rows} != {SOURCE_MANIFEST_SHA256}:
            raise ValueError(f"INPUT_MANIFEST_MISMATCH:{key}")
    sides = [build_side("BID", inputs["15m_bid"], inputs["2h_bid"]), build_side("ASK", inputs["15m_ask"], inputs["2h_ask"])]
    files = {
        "observations_15m": write_jsonl(out_dir/"c2-observations-15m.jsonl", [x for side in sides for x in side["complete15"]]),
        "observations_2h": write_jsonl(out_dir/"c2-observations-2h-parent.jsonl", [x for side in sides for x in side["complete2h"]]),
    }
    for key, filename in (("memberships","c2-horizon-memberships.jsonl"),("levels","c2-levels.jsonl"),("containers","c2-containers.jsonl"),
                          ("relations","c2-relations.jsonl"),("relation_sets","c2-relation-sets.jsonl"),("profiles","c2-four-axis-profiles.jsonl"),
                          ("contexts","c2-parent-context-bundles.jsonl"),("bundles","c2-observation-bundles.jsonl")):
        rows = [x for side in sides for x in side[key]]
        if key == "profiles":
            unique = {}
            for row in rows:
                identity = row["profile_output_id"]
                if identity in unique and canonical(unique[identity]) != canonical(row):
                    raise ValueError(f"PROFILE_ID_CONTENT_COLLISION:{identity}")
                unique[identity] = row
            rows = [unique[identity] for identity in sorted(unique)]
        files[key] = write_jsonl(out_dir/filename, rows)
    target_ids = sorted(set().union(*(side["target_ids"] for side in sides)))
    bundle_by_id = {bundle["observation_id"]: bundle for side in sides for bundle in side["bundles"]}
    target_bundles = [bundle_by_id[identity] for identity in target_ids]
    files["target_bundles"] = write_jsonl(out_dir/"c2-target-june-observation-bundles.jsonl", target_bundles)
    parent_linked = sum(1 for bundle in target_bundles if bundle["fixed_parent_observation_id"] is not None)
    manifest = {"schema": SCHEMA, "packet_id": PACKET_ID, "materialisation_id": MATERIALISATION_ID,
        "source": {"source_slice_id": SOURCE_SLICE_ID, "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "c1_release_id": C1_RELEASE_ID, "c1_manifest_id": C1_MANIFEST_ID, "c2ar_package_id": C2AR_PACKAGE_ID, "c2ar_package_sha256": C2AR_PACKAGE_SHA256},
        "scope": {"instrument": INSTRUMENT, "sides": ["ASK","BID"], "local_clock": "15M", "parent_clock": "2H_A_L",
            "context_start": CONTEXT_START, "context_end_exclusive": CONTEXT_END, "target_start": TARGET_START, "target_end_exclusive": TARGET_END,
            "representation": "OBSERVATION_LEVEL", "target_unit": "C2EInputFrame_CANDIDATE_SOURCE"},
        "policy": {"motion_horizons": [f"HORIZON.MOTION.15M.TRAILING.{count}.r1" for count in HORIZON_COUNTS],
            "location_level_scope": "ALL_TRAILING_RANGE_HIGH_LOW_MIDPOINT_OBJECTS_FROM_ALL_FROZEN_4_8_16_HORIZON_CANDIDATES",
            "organisation_container_scope": "ALL_TRAILING_RANGE_MEASUREMENT_CONTAINERS_FROM_ALL_FROZEN_4_8_16_HORIZON_CANDIDATES",
            "interaction_scope": "SAME_OBJECT_RELATION_DELTAS_PLUS_TYPED_TRAILING_RANGE_REFERENCE_REFRESH",
            "parent_scope": "EXACT_LATEST_COMPLETED_2H_A_L_FIXED_PARENT_ONLY; NO_PARENT_OBJECT_SELECTION",
            "selector_use": "NONE", "threshold_selection": "NONE", "semantic_promotion": "NONE"},
        "counts": {"15m_complete_context": sum(len(side["complete15"]) for side in sides), "15m_target_eligible": len(target_ids),
            "2h_complete_context": sum(len(side["complete2h"]) for side in sides), "target_parent_linked": parent_linked,
            "target_parent_not_computable": len(target_ids)-parent_linked,
            "target_axis_profile_refs": {axis: sum(len(bundle["profile_output_ids"][axis]) for bundle in target_bundles)
                for axis in ("LOCATION","MOTION","ORGANISATION","INTERACTION")}},
        "files": files, "authority": {"active_c2": "UNCHANGED_READ_ONLY", "selector": "NONE", "semantic": "NONE", "outcome": "NONE",
            "validation": "DENIED", "publication": "DENIED", "probability_risk_exposure_execution": "NONE",
            "materialisation": "APPROVED_BOUNDED_REAL_SOURCE_READ_DERIVE_ONLY"},
        "provider_intake": "NONE_ALREADY_ACCEPTED_C1_SOURCE_ONLY", "determinism": "PENDING_SECOND_RUN_COMPARISON"}
    manifest["logical_sha256"] = sha256_obj(manifest)
    (out_dir/"materialisation-manifest.json").write_bytes(canonical(manifest)+b"\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--c1-15m-bid", required=True); parser.add_argument("--c1-15m-ask", required=True)
    parser.add_argument("--c1-2h-bid", required=True); parser.add_argument("--c1-2h-ask", required=True)
    args = parser.parse_args()
    manifest = materialise(Path(args.out), {"15m_bid": Path(args.c1_15m_bid), "15m_ask": Path(args.c1_15m_ask),
        "2h_bid": Path(args.c1_2h_bid), "2h_ask": Path(args.c1_2h_ask)})
    print(json.dumps({"logical_sha256": manifest["logical_sha256"], "counts": manifest["counts"], "files": manifest["files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
