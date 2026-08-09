from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from ovc.opt_b.c2e_v2.downstream import build_sri_handoff
from ovc.opt_b.c2e_v2.handoff import build_input_frame
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine
from ovc.research_orchestration.golden2_downstream import (
    C2AR_PACKAGE_ID,
    C2AR_PACKAGE_SHA256,
    _boundary_pack,
    _hash,
    _parent_record,
    _sfc_record,
    execute_sfc,
    project_research_operations,
)
from ovc.research_orchestration.golden2_weekly import PROGRAMME_ID, run_weekly_upstream

REQUIRED_FIXTURE_BOUNDARY_AXES = ("LOCATION", "ORGANISATION")
ALL_STRUCTURAL_AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")


def _frame_loss_preserving(snapshot: Mapping[str, Any], predecessor: str | None) -> dict[str, Any]:
    axes = {str(row["axis"]): row for row in snapshot["formula_outputs"]}
    axis_ids = {axis: str(axes[axis]["profile_output_id"]) for axis in ALL_STRUCTURAL_AXES}
    computable_axes = tuple(axis for axis in ALL_STRUCTURAL_AXES if axes[axis]["computability"] == "COMPUTABLE")
    missing_required = sorted(set(REQUIRED_FIXTURE_BOUNDARY_AXES) - set(computable_axes))
    if missing_required:
        raise ValueError("GOLDEN2_FIXTURE_BOUNDARY_REQUIRED_AXIS_NOT_COMPUTABLE:" + ",".join(missing_required))

    parents: list[dict[str, Any]] = [
        _parent_record(axis_ids[axis], axis, str(axes[axis]["as_of_time"]), str(axes[axis].get("content_sha256")))
        for axis in ALL_STRUCTURAL_AXES
    ]
    for level in snapshot["levels"]:
        parents.append(_parent_record(str(level["level_id"]), "LEVEL", str(level["first_valid_time"])))
    parents.append(_parent_record(str(snapshot["container"]["container_id"]), "CONTAINER", str(snapshot["container"]["first_valid_time"])))
    parents.append(_parent_record(str(snapshot["level_relation_set"]["relation_set_id"]), "RELATION_SET", str(snapshot["level_relation_set"]["as_of_time"])))
    for row in snapshot["transition_records"]:
        parents.append(_parent_record(str(row["transition_id"]), "TRANSITION", str(row["current_time"])))
    parents.append(_parent_record(str(snapshot["formula_bundle"]["bundle_id"]), "RUN", str(snapshot["formula_bundle"]["as_of_time"]), str(snapshot["formula_bundle"].get("content_sha256"))))
    parent_ids = [row["record_id"] for row in parents]
    if len(parent_ids) != len(set(parent_ids)):
        raise ValueError("GOLDEN2_DUPLICATE_C2_PARENT_ID")

    fvt = str(snapshot["first_valid_time"])
    payload = {
        "source_binding": {
            "c2ar_package_id": C2AR_PACKAGE_ID,
            "c2ar_package_sha256": C2AR_PACKAGE_SHA256,
            "research_consumer_permission": "READ_ONLY_SHADOW_RESEARCH_ONLY",
            "active": False,
            "canonical": False,
            "source_release_id": "IROF.GOLDEN2.SYNTHETIC.SOURCE.v0_1",
            "source_manifest_id": "IROF.GOLDEN2.SYNTHETIC.MANIFEST.v0_1",
            "c2_release_id": "IROF.GOLDEN2.C2.SYNTHETIC.v0_1",
            "c2_contract_id": "C2AR.INTEGRATED.SHADOW.PACKAGE.v1",
            "source_build_commit": "IROF-GOLDEN2-SYNTHETIC",
        },
        "identity": {
            "instrument_id": "GBPUSD",
            "side": snapshot["side"],
            "scope_id": "LOCAL_15M",
            "scale_id": "15M",
            "clock_id": "UTC_15M",
            "lattice_id": "LATTICE.15M.UTC_0000.v1",
            "observation_id": snapshot["observation_id"],
            "c2_record_id": snapshot["observation_id"],
            "parameter_pack_id": "C2AR.INTEGRATED.SHADOW.FREEZE.v1",
            "contract_id": "C2E.HANDOFF.v0_2",
            "schema_id": "c2e_input_frame/v0_2",
        },
        "chronology": {
            "source_time": snapshot["interval_start"],
            "candidate_onset_time": snapshot["interval_start"],
            "first_valid_time": fvt,
            "evaluation_cutoff": fvt,
            "continuity_segment_id": snapshot["continuity_segment_id"],
            "predecessor_observation_id": predecessor,
        },
        "structural": {
            "location_record_ids": [axis_ids["LOCATION"]],
            "motion_record_ids": [axis_ids["MOTION"]],
            "organisation_record_ids": [axis_ids["ORGANISATION"]],
            "interaction_record_ids": [axis_ids["INTERACTION"]],
            "level_record_ids": [str(row["level_id"]) for row in snapshot["levels"]],
            "container_record_ids": [str(snapshot["container"]["container_id"])],
            "relation_set_id": str(snapshot["level_relation_set"]["relation_set_id"]),
            "transition_record_ids": [str(row["transition_id"]) for row in snapshot["transition_records"]],
            "run_record_ids": [str(snapshot["formula_bundle"]["bundle_id"])],
        },
        "context": {
            "context_resolution_bundle_id": None,
            "fixed_parent_links": [],
            "structural_object_links": [],
            "parent_axis_links": [],
        },
        "evidence": {
            "dependency_results": [{
                "dependency_id": "DEP.LOCAL",
                "role": "REQUIRED",
                "status": "COMPUTABLE",
                "source_record_ids": [axis_ids[axis] for axis in REQUIRED_FIXTURE_BOUNDARY_AXES],
                "reason_codes": [],
            }],
            "availability_status": "AVAILABLE",
            "technical_status": "COMPUTABLE",
            "assurance": [{"assertion_id": "IROF.GOLDEN2.C2.FRAME", "status": "ASSURED"}],
            "consumer_eligibility": "INELIGIBLE_INACTIVE_SHADOW",
            "authority_state": "UNAUTHORIZED_ACTIVE_C2E",
            "reason_codes": [],
        },
        "lineage": {
            "parent_record_ids": sorted(parent_ids),
            "artifact_hashes": {"c2_snapshot": snapshot["logical_hash"]},
            "source_build_commit": "IROF-GOLDEN2-SYNTHETIC",
        },
        "parent_records": parents,
    }
    return build_input_frame(payload)


def execute_c2e_loss_preserving(upstream: Mapping[str, Any]) -> dict[str, Any]:
    axis_counts: Counter[str] = Counter()
    eligible: list[dict[str, Any]] = []
    for snapshot in upstream["c2"]["snapshots"]:
        by_axis = {str(row["axis"]): row for row in snapshot["formula_outputs"]}
        for axis in ALL_STRUCTURAL_AXES:
            axis_counts[f"{axis}:{by_axis[axis]['computability']}"] += 1
        if all(by_axis[axis]["computability"] == "COMPUTABLE" for axis in REQUIRED_FIXTURE_BOUNDARY_AXES):
            eligible.append(snapshot)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for snapshot in eligible:
        grouped[(str(snapshot["side"]), str(snapshot["continuity_segment_id"]))].append(snapshot)

    handoffs: list[dict[str, Any]] = []
    adapted_inputs: list[tuple[dict[str, Any], dict[str, dict[str, Any]]]] = []
    frame_count = 0
    event_count = 0
    episode_count = 0
    status_counts: Counter[str] = Counter()
    for side in ("BID", "ASK"):
        pack = _boundary_pack(side)
        engine = EpisodeEngine(pack["boundary_pack_id"])
        side_groups = [(key, rows) for key, rows in grouped.items() if key[0] == side]
        side_groups.sort(key=lambda item: min(row["first_valid_time"] for row in item[1]))
        for group_index, (_key, rows) in enumerate(side_groups):
            rows.sort(key=lambda item: item["first_valid_time"])
            frames: list[dict[str, Any]] = []
            predecessor: str | None = None
            for row in rows:
                frame = _frame_loss_preserving(row, predecessor)
                frames.append(frame)
                predecessor = frame["identity"]["observation_id"]
            if not frames:
                continue
            frame_count += len(frames)
            first_fvt = frames[0]["chronology"]["first_valid_time"]
            genesis = engine.birth(
                frame=frames[0],
                boundary_rule_id="RULE.BIRTH",
                candidate_id=f"G2.BIRTH.{side}.{group_index}",
                effective_time=first_fvt,
                first_valid_time=first_fvt,
            )
            episode_count += 1
            for index, frame in enumerate(frames[1:], start=1):
                fvt = frame["chronology"]["first_valid_time"]
                engine.continue_episode(
                    episode_id=genesis["episode_id"],
                    frame=frame,
                    candidate_id=f"G2.CONT.{side}.{group_index}.{index}",
                    effective_time=fvt,
                    first_valid_time=fvt,
                )
                if index == max(1, len(frames) // 2):
                    engine.phase_mutation(
                        episode_id=genesis["episode_id"],
                        candidate_id=f"G2.PHASE.{side}.{group_index}",
                        phase_type="SYNTHETIC_MIDPOINT",
                        start_time=first_fvt,
                        end_time=fvt,
                        source_record_ids=[frame["frame_id"]],
                        effective_time=fvt,
                        first_valid_time=fvt,
                    )
            last_fvt = frames[-1]["chronology"]["first_valid_time"]
            if group_index == len(side_groups) - 1:
                engine.censor(
                    episode_id=genesis["episode_id"],
                    candidate_id=f"G2.END.{side}",
                    reason="CENSOR_RELEASE_END",
                    effective_time=last_fvt,
                    first_valid_time=last_fvt,
                )
            else:
                engine.terminate(
                    episode_id=genesis["episode_id"],
                    candidate_id=f"G2.TERM.{side}.{group_index}",
                    conflict=False,
                    effective_time=last_fvt,
                    first_valid_time=last_fvt,
                )
            snapshot = engine.snapshot(genesis["episode_id"], as_of_time=last_fvt, first_valid_time=last_fvt)
            handoff = build_sri_handoff(genesis=genesis, snapshot=snapshot, records=engine.stream.records, first_valid_time=last_fvt)
            handoffs.append(handoff)
            adapted_inputs.append(_sfc_record(handoff, engine.stream.records))
            status_counts[str(snapshot["status"])] += 1
        event_count += sum(1 for row in engine.stream.records if row.get("schema") == "c2e_boundary_event/v0_2")

    result = {
        "input_c2_snapshot_count": len(upstream["c2"]["snapshots"]),
        "eligible_c2_snapshot_count": len(eligible),
        "frame_count": frame_count,
        "episode_count": episode_count,
        "handoff_count": len(handoffs),
        "event_count": event_count,
        "status_counts": dict(sorted(status_counts.items())),
        "axis_computability_counts": dict(sorted(axis_counts.items())),
        "fixture_boundary_required_axes": list(REQUIRED_FIXTURE_BOUNDARY_AXES),
        "conformance_warnings": [
            "C2_HORIZON_MEMBERSHIP_STATUS_COMPUTABLE_VS_MOTION_PROFILE_COMPLETE_VOCABULARY_MISMATCH"
        ],
        "handoffs": handoffs,
        "sfc_inputs": adapted_inputs,
        "real_source_replay": False,
        "active_c2e": "NONE",
        "active_boundary_pack": "NONE",
        "authority_effect": "NONE",
    }
    result["logical_hash"] = _hash({key: value for key, value in result.items() if key != "sfc_inputs"})
    return result


def run_weekly_full_chain_loss_preserving() -> dict[str, Any]:
    upstream = run_weekly_upstream()
    c2e = execute_c2e_loss_preserving(upstream)
    sfc = execute_sfc(c2e)
    research = project_research_operations(upstream, c2e, sfc)
    summary = {
        "programme_id": PROGRAMME_ID,
        "upstream_logical_hash": upstream["summary"]["logical_hash"],
        "c2e_logical_hash": c2e["logical_hash"],
        "sfc_logical_hash": sfc["logical_hash"],
        "research_operations_logical_hash": research["logical_hash"],
        "family_evidence_status": sfc["family_evidence_stream"]["status"],
        "real_market_data": False,
        "validation_consumed": False,
        "authority_effect": "NONE",
    }
    summary["logical_hash"] = _hash(summary)
    return {"upstream": upstream, "c2e": c2e, "sfc": sfc, "research": research, "summary": summary}
