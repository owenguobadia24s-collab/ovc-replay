from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Mapping, Sequence

from ovc.context.occurrence_context.consumers import project_context
from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.downstream import build_sri_handoff
from ovc.opt_b.c2e_v2.handoff import build_input_frame
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine
from ovc.opt_b.sfc.c2e_adapter import adapt_c2e_handoff
from ovc.opt_b.sfc.comparison import ComparabilityDomain, ComparisonSpec, comparability_metadata, compare
from ovc.opt_b.sfc.evidence import family_evidence_stream, residual_rate
from ovc.opt_b.sfc.fdi import FamilyMethodSpec, deterministic_star_assign
from ovc.opt_b.sfc.representation import RepresentationPack, compile_population, compile_representation
from ovc.research_orchestration.evidence import project_research_read_model
from ovc.research_orchestration.golden2_weekly import END, PROGRAMME_ID, START, run_weekly_upstream
from ovc.research_orchestration.models import (
    IntegratedRunReceipt,
    PipelineProfile,
    StageDependency,
    StageExecutionReceipt,
    StageSpec,
)
from ovc.research_orchestration.planner import CanonicalPlan, build_plan
from ovc.research_orchestration.registry import build_registry_snapshot
from ovc.research_orchestration.serialization import logical_sha256

STAGE_IDS = (
    "POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED", "C2E_V0_2", "OCCURRENCE_CONTEXT",
    "SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY",
    "FAMILY_EVIDENCE_STREAM", "RESEARCH_OPERATIONS",
)
C2AR_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2AR_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"


def _hash(value: Any) -> str:
    return logical_sha256(value)


def _boundary_pack(side: str) -> dict[str, Any]:
    return freeze_pack({
        "version": f"IROF.GOLDEN2.{side}.v0_1",
        "supersedes": None,
        "population_scope": {
            "instrument_id": "GBPUSD", "side": side, "clock_id": "UTC_15M", "scale_id": "15M",
            "scope_id": "LOCAL_15M", "source_population_id": "IROF.GOLDEN2.SYNTHETIC_ONLY",
        },
        "rules": [
            {
                "boundary_rule_id": "RULE.CONTINUE", "candidate_type": "CONTINUATION_CANDIDATE",
                "lifecycle_action": "CONTINUATION", "priority_class": 7,
                "dependencies": {"REQUIRED": ["DEP.LOCAL"], "OPTIONAL": [], "WARNING": [], "ONE_OF": [], "PROHIBITED": ["FDI_C2G"]},
                "parameters": {"threshold": "0.250000", "confirmation_delay_seconds": "0"},
                "parameter_precisions": {"threshold": 6, "confirmation_delay_seconds": 0},
                "time_semantics": {"confirmation": "IMMEDIATE"},
            },
            {
                "boundary_rule_id": "RULE.BIRTH", "candidate_type": "BIRTH_CANDIDATE",
                "lifecycle_action": "BIRTH", "priority_class": 8,
                "dependencies": {"REQUIRED": ["DEP.LOCAL"], "OPTIONAL": [], "WARNING": [], "ONE_OF": [], "PROHIBITED": ["FDI_C2G"]},
                "parameters": {"threshold": "0.500000"}, "parameter_precisions": {"threshold": 6},
                "time_semantics": {"confirmation": "IMMEDIATE"},
            },
        ],
        "compatibility_matrix": [{"candidate_type_a": "BIRTH_CANDIDATE", "candidate_type_b": "CONTINUATION_CANDIDATE", "disposition": "ORDERED_BY_PRIORITY"}],
        "ownership": {"peer_mode": "SINGLE_OWNER"},
        "topology": {"cycle_policy": "DENY", "nest": "TYPED_ONLY", "split": True, "merge": True, "re_parent": True},
        "discontinuity": {"source_gap": "CENSOR_GAP", "release_end": "CENSOR_RELEASE_END", "scheduled_closure": "PACK_DECLARED", "required_context_loss": "RULE_SPECIFIC"},
        "conflict_policy": {"equal_priority_incompatible": "INCOMPATIBLE_CONFLICT", "lexical_winner": False},
        "implementation_hashes": {"boundary_pack.py": "IROF-GOLDEN2-CURRENT-MAIN"},
        "registry_hashes": {"priority": "IROF-GOLDEN2", "compatibility": "IROF-GOLDEN2"},
        "authority": "SHADOW",
        "metadata": {"description": "Golden2 fixture-only inactive pack"},
    })


def _parent_record(record_id: str, kind: str, fvt: str, content_sha256: str | None = None) -> dict[str, Any]:
    return {"record_id": record_id, "kind": kind, "first_valid_time": fvt, "content_sha256": content_sha256}


def _frame(snapshot: Mapping[str, Any], predecessor: str | None) -> dict[str, Any]:
    axes = {row["axis"]: row for row in snapshot["formula_outputs"]}
    structural_axes = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
    axis_ids = {axis: str(axes[axis]["profile_output_id"]) for axis in structural_axes}
    parents: list[dict[str, Any]] = [
        _parent_record(axis_ids[axis], axis, str(axes[axis]["as_of_time"]), str(axes[axis].get("content_sha256")))
        for axis in structural_axes
    ]
    for level in snapshot["levels"]:
        parents.append(_parent_record(str(level["level_id"]), "LEVEL", str(level["first_valid_time"])))
    parents.append(_parent_record(str(snapshot["container"]["container_id"]), "CONTAINER", str(snapshot["container"]["first_valid_time"])))
    parents.append(_parent_record(str(snapshot["level_relation_set"]["relation_set_id"]), "RELATION_SET", str(snapshot["level_relation_set"]["as_of_time"])))
    for row in snapshot["transition_records"]:
        parents.append(_parent_record(str(row["transition_id"]), "TRANSITION", str(row["current_time"])))
    parents.append(_parent_record(str(snapshot["formula_bundle"]["bundle_id"]), "RUN", str(snapshot["formula_bundle"]["as_of_time"]), str(snapshot["formula_bundle"].get("content_sha256"))))
    ids = [row["record_id"] for row in parents]
    if len(ids) != len(set(ids)):
        raise ValueError("GOLDEN2_DUPLICATE_C2_PARENT_ID")
    fvt = str(snapshot["first_valid_time"])
    payload = {
        "source_binding": {
            "c2ar_package_id": C2AR_PACKAGE_ID, "c2ar_package_sha256": C2AR_PACKAGE_SHA256,
            "research_consumer_permission": "READ_ONLY_SHADOW_RESEARCH_ONLY", "active": False, "canonical": False,
            "source_release_id": "IROF.GOLDEN2.SYNTHETIC.SOURCE.v0_1", "source_manifest_id": "IROF.GOLDEN2.SYNTHETIC.MANIFEST.v0_1",
            "c2_release_id": "IROF.GOLDEN2.C2.SYNTHETIC.v0_1", "c2_contract_id": "C2AR.INTEGRATED.SHADOW.PACKAGE.v1",
            "source_build_commit": "IROF-GOLDEN2-SYNTHETIC",
        },
        "identity": {
            "instrument_id": "GBPUSD", "side": snapshot["side"], "scope_id": "LOCAL_15M", "scale_id": "15M",
            "clock_id": "UTC_15M", "lattice_id": "LATTICE.15M.UTC_0000.v1",
            "observation_id": snapshot["observation_id"], "c2_record_id": snapshot["observation_id"],
            "parameter_pack_id": "C2AR.INTEGRATED.SHADOW.FREEZE.v1", "contract_id": "C2E.HANDOFF.v0_2", "schema_id": "c2e_input_frame/v0_2",
        },
        "chronology": {
            "source_time": snapshot["interval_start"], "candidate_onset_time": snapshot["interval_start"],
            "first_valid_time": fvt, "evaluation_cutoff": fvt,
            "continuity_segment_id": snapshot["continuity_segment_id"], "predecessor_observation_id": predecessor,
        },
        "structural": {
            "location_record_ids": [axis_ids["LOCATION"]], "motion_record_ids": [axis_ids["MOTION"]],
            "organisation_record_ids": [axis_ids["ORGANISATION"]], "interaction_record_ids": [axis_ids["INTERACTION"]],
            "level_record_ids": [str(row["level_id"]) for row in snapshot["levels"]],
            "container_record_ids": [str(snapshot["container"]["container_id"])],
            "relation_set_id": str(snapshot["level_relation_set"]["relation_set_id"]),
            "transition_record_ids": [str(row["transition_id"]) for row in snapshot["transition_records"]],
            "run_record_ids": [str(snapshot["formula_bundle"]["bundle_id"])],
        },
        "context": {"context_resolution_bundle_id": None, "fixed_parent_links": [], "structural_object_links": [], "parent_axis_links": []},
        "evidence": {
            "dependency_results": [{
                "dependency_id": "DEP.LOCAL", "role": "REQUIRED", "status": "COMPUTABLE",
                "source_record_ids": [axis_ids[axis] for axis in structural_axes], "reason_codes": [],
            }],
            "availability_status": "AVAILABLE", "technical_status": "COMPUTABLE",
            "assurance": [{"assertion_id": "IROF.GOLDEN2.C2.FRAME", "status": "ASSURED"}],
            "consumer_eligibility": "INELIGIBLE_INACTIVE_SHADOW", "authority_state": "UNAUTHORIZED_ACTIVE_C2E", "reason_codes": [],
        },
        "lineage": {
            "parent_record_ids": sorted(ids), "artifact_hashes": {"c2_snapshot": snapshot["logical_hash"]},
            "source_build_commit": "IROF-GOLDEN2-SYNTHETIC",
        },
        "parent_records": parents,
    }
    return build_input_frame(payload)


def _stream_record_id(row: Mapping[str, Any]) -> str | None:
    schema = str(row.get("schema", ""))
    return {
        "c2e_membership_delta/v0_2": "membership_delta_id",
        "c2e_phase_segment/v0_2": "phase_segment_id",
        "c2e_boundary_event/v0_2": "boundary_event_id",
        "c2e_lineage_edge/v0_2": "lineage_edge_id",
    }.get(schema) and str(row[{
        "c2e_membership_delta/v0_2": "membership_delta_id",
        "c2e_phase_segment/v0_2": "phase_segment_id",
        "c2e_boundary_event/v0_2": "boundary_event_id",
        "c2e_lineage_edge/v0_2": "lineage_edge_id",
    }[schema]])


def _sfc_record(handoff: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    source_objects: dict[str, dict[str, Any]] = {}
    for row in records:
        rid = _stream_record_id(row)
        if rid is not None:
            source_objects[rid] = dict(row)
    record = {
        "producer_contract_id": "C2E_TO_SRI_STREAM_HANDOFF_CONTRACT_v0_1",
        "producer_contract_blob": "31ba923f68bfd18dd2e3091b0fe7cb21de5b772d",
        "episode_id": handoff["episode_id"], "boundary_pack_id": handoff["boundary_pack_id"],
        "source_release_id": handoff["source_release_id"], "instrument_id": "GBPUSD", "side": handoff["side"],
        "scope_id": handoff["scope_id"], "scale_id": handoff["scale_id"], "lifecycle_status": handoff["status"],
        "genesis_reference": handoff["genesis_ref"], "snapshot_reference": handoff["snapshot_ref"],
        "phase_segment_references": list(handoff["phase_refs"]), "boundary_event_references": list(handoff["boundary_refs"]),
        "lineage_edge_references": list(handoff["lineage_refs"]), "membership_references": list(handoff["membership_refs"]),
        "availability_missingness": "AVAILABLE", "first_valid_time": handoff["first_valid_time"],
        "record_hashes": {},
        "source_lineage": {"source_build_commit": "IROF-GOLDEN2-SYNTHETIC", "artifact_hashes": {"c2e_stream": _hash(list(records))}},
    }
    return record, source_objects


def execute_c2e(upstream: Mapping[str, Any]) -> dict[str, Any]:
    eligible = [
        item for item in upstream["c2"]["snapshots"]
        if all(row["computability"] == "COMPUTABLE" for row in item["formula_outputs"][:4])
    ]
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
                frame = _frame(row, predecessor)
                frames.append(frame)
                predecessor = frame["identity"]["observation_id"]
            if not frames:
                continue
            frame_count += len(frames)
            first_fvt = frames[0]["chronology"]["first_valid_time"]
            genesis = engine.birth(frame=frames[0], boundary_rule_id="RULE.BIRTH", candidate_id=f"G2.BIRTH.{side}.{group_index}", effective_time=first_fvt, first_valid_time=first_fvt)
            episode_count += 1
            for index, frame in enumerate(frames[1:], start=1):
                fvt = frame["chronology"]["first_valid_time"]
                engine.continue_episode(episode_id=genesis["episode_id"], frame=frame, candidate_id=f"G2.CONT.{side}.{group_index}.{index}", effective_time=fvt, first_valid_time=fvt)
                if index == max(1, len(frames) // 2):
                    engine.phase_mutation(
                        episode_id=genesis["episode_id"], candidate_id=f"G2.PHASE.{side}.{group_index}", phase_type="SYNTHETIC_MIDPOINT",
                        start_time=first_fvt, end_time=None, source_record_ids=[frame["frame_id"]], effective_time=fvt, first_valid_time=fvt,
                    )
            last_fvt = frames[-1]["chronology"]["first_valid_time"]
            if group_index == len(side_groups) - 1:
                engine.censor(episode_id=genesis["episode_id"], candidate_id=f"G2.END.{side}", reason="CENSOR_RELEASE_END", effective_time=last_fvt, first_valid_time=last_fvt)
            else:
                engine.terminate(episode_id=genesis["episode_id"], candidate_id=f"G2.TERM.{side}.{group_index}", conflict=False, effective_time=last_fvt, first_valid_time=last_fvt)
            snapshot = engine.snapshot(genesis["episode_id"], as_of_time=last_fvt, first_valid_time=last_fvt)
            handoff = build_sri_handoff(genesis=genesis, snapshot=snapshot, records=engine.stream.records, first_valid_time=last_fvt)
            handoffs.append(handoff)
            adapted_inputs.append(_sfc_record(handoff, engine.stream.records))
            status_counts[str(snapshot["status"])] += 1
        event_count += sum(1 for row in engine.stream.records if row.get("schema") == "c2e_boundary_event/v0_2")
    result = {
        "frame_count": frame_count, "episode_count": episode_count, "handoff_count": len(handoffs),
        "event_count": event_count, "status_counts": dict(sorted(status_counts.items())),
        "handoffs": handoffs, "sfc_inputs": adapted_inputs,
        "real_source_replay": False, "active_c2e": "NONE", "active_boundary_pack": "NONE", "authority_effect": "NONE",
    }
    result["logical_hash"] = _hash({key: value for key, value in result.items() if key != "sfc_inputs"})
    return result


def execute_sfc(c2e: Mapping[str, Any]) -> dict[str, Any]:
    if not c2e["sfc_inputs"]:
        raise ValueError("GOLDEN2_C2E_HANDOFF_EMPTY")
    cutoff = max(str(record["first_valid_time"]) for record, _objects in c2e["sfc_inputs"])
    adapted = [adapt_c2e_handoff(record, source_objects=objects, evaluation_cutoff=cutoff) for record, objects in c2e["sfc_inputs"]]
    population = compile_population(adapted, population_rule_pack_id="IROF.GOLDEN2.SFC.POPULATION.v0_1", population_cutoff=cutoff)
    eligible_ids = set(population["eligible_source_ids"])
    eligible = [row for row in adapted if row["episode_id"] in eligible_ids]
    pack = RepresentationPack(
        "IROF.GOLDEN2.SRI.NULL_CONTROL.v0_1", "SRI-R9", (),
        comparability_domain_id="IROF.GOLDEN2.COMPARABILITY.v0_1", context_roles=("STRATIFICATION_ONLY",),
    )
    reps = [compile_representation(row, pack, source_population_id=population["population_id"], normalization_pack=None) for row in eligible]
    reps.sort(key=lambda row: row["representation_id"])
    source_by_episode = {row["episode_id"]: row for row in eligible}
    rep_source = {row["representation_id"]: source_by_episode[row["source_ids"][0]] for row in reps}
    spec = ComparisonSpec(
        spec_id="IROF.GOLDEN2.NULL_DISTANCE.v0_1", kind="DISTANCE", formula="EUCLIDEAN", dimensions=(),
        equivalence_kind="EXACT",
    )
    domain = ComparabilityDomain("IROF.GOLDEN2.COMPARABILITY.v0_1")
    pairs: list[dict[str, Any]] = []
    for left, right in combinations(reps, 2):
        lm = comparability_metadata(left); rm = comparability_metadata(right)
        lm["side"] = rep_source[left["representation_id"]]["side"]
        rm["side"] = rep_source[right["representation_id"]]["side"]
        pairs.append(compare(left, right, left_meta=lm, right_meta=rm, domain=domain, spec=spec, evaluation_cutoff=cutoff))
    method = FamilyMethodSpec(
        family_method_id="IROF.GOLDEN2.FDI.NULL_STAR.v0_1", method_version="0.1", configuration_id="IROF.GOLDEN2.FDI.NULL_STAR.CONFIG.v0_1",
        input_representation_pack_id=pack.representation_pack_id, comparison_spec_id=spec.spec_id, minimum_support=2,
    )
    catalog = deterministic_star_assign(
        pairs, occurrence_ids=[row["representation_id"] for row in reps], threshold="0",
        population_id=population["population_id"], representation_pack_id=pack.representation_pack_id,
        comparison_spec_id=spec.spec_id, method=method, evaluation_cutoff=cutoff,
    )
    stream = family_evidence_stream(
        source_population_id=population["population_id"], source_c2e_stream_id="IROF.GOLDEN2.C2E." + c2e["logical_hash"][:24],
        catalogs=(catalog,), evidence_objects=(residual_rate(catalog),), evaluation_cutoff=cutoff,
    )
    context = {
        "schema_version": "0.1", "context_pack_version": "0.1", "occurrence_context_id": "OC.IROF.GOLDEN2.WEEK.001",
        "first_valid_time": cutoff, "instrument_id": "GBPUSD", "session": {"id": "SYNTHETIC_WEEK"}, "scale": {"id": "15M"},
    }
    manifest = {
        "consumer_kind": "IROF_GOLDEN2_RESEARCH_STRATIFIER", "consumer_version": "0.1",
        "accepted_context_schema_versions": ["0.1"], "accepted_context_pack_versions": ["0.1"],
        "field_dependencies": [
            {"field_path": "instrument_id", "dependency": "REQUIRED", "role": "STRATIFIER"},
            {"field_path": "session.id", "dependency": "OPTIONAL", "role": "STRATIFIER"},
            {"field_path": "scale.id", "dependency": "OPTIONAL", "role": "DISPLAY_ONLY"},
        ],
        "admissible_cutoff_rule": "CONTEXT_FVT_LE_EVALUATION_CUTOFF", "missingness_behavior": "EXPLICIT", "authority_effect": "NONE",
    }
    context_projection = project_context(context, manifest)
    result = {
        "population": population, "representations": reps, "pairs": pairs, "catalog": catalog,
        "family_evidence_stream": stream, "occurrence_context_projection": context_projection,
        "representation_interpretation": "NULL_CONTROL_EXECUTION_ASSURANCE_ONLY",
        "representation_or_family_promotion": False, "authority_effect": "NONE",
    }
    result["logical_hash"] = _hash(result)
    return result


def build_golden2_plan() -> CanonicalPlan:
    deps = {
        "POPULATION_SOURCE_OPT_A": (), "C1": ("POPULATION_SOURCE_OPT_A",), "C2_REVISED": ("C1",),
        "C2E_V0_2": ("C2_REVISED",), "OCCURRENCE_CONTEXT": ("C2E_V0_2",), "SRI_REPRESENTATION": ("C2E_V0_2",),
        "COMPARABILITY_COMPARISON_DISTANCE": ("SRI_REPRESENTATION",), "FDI_C2G_FAMILY": ("COMPARABILITY_COMPARISON_DISTANCE",),
        "FAMILY_EVIDENCE_STREAM": ("FDI_C2G_FAMILY",), "RESEARCH_OPERATIONS": ("FAMILY_EVIDENCE_STREAM", "OCCURRENCE_CONTEXT"),
    }
    specs = tuple(StageSpec(
        stage_id=stage, stage_version="0.1", stage_kind="GOLDEN2_WEEKLY_SYNTHETIC_E2E",
        implementation_identity=f"irof-golden2:{stage}", contract_identity=f"irof-golden2-contract:{stage}",
        schema_identity=f"irof-golden2-schema:{stage}", input_types=(), output_types=(f"{stage}_OUT",),
        dependencies=tuple(StageDependency(parent, "REQUIRED") for parent in deps[stage]),
        checkpoint_capability="STAGE", cache_capability="SEMANTIC", adapter_identity=f"IROF.CURRENT.{stage}",
    ) for stage in STAGE_IDS)
    profile = PipelineProfile("IROF_GOLDEN2_WEEKLY_FULL_DESCRIPTIVE_WITH_CONTEXT", "0.1", STAGE_IDS, required_terminal_outputs=("RESEARCH_OPERATIONS_OUT",))
    return build_plan(snapshot=build_registry_snapshot(stage_specs=specs, profiles=(profile,)), profile_id=profile.profile_id)


def project_research_operations(upstream: Mapping[str, Any], c2e: Mapping[str, Any], sfc: Mapping[str, Any]) -> dict[str, Any]:
    plan = build_golden2_plan()
    metrics = {
        "POPULATION_SOURCE_OPT_A": upstream["opt_a"]["summary"]["m1_counts"]["BID"] + upstream["opt_a"]["summary"]["m1_counts"]["ASK"],
        "C1": upstream["c1"]["summary"]["record_count"], "C2_REVISED": upstream["c2"]["summary"]["structural_snapshot_count"],
        "C2E_V0_2": c2e["frame_count"], "OCCURRENCE_CONTEXT": 1, "SRI_REPRESENTATION": len(sfc["representations"]),
        "COMPARABILITY_COMPARISON_DISTANCE": len(sfc["pairs"]), "FDI_C2G_FAMILY": len(sfc["catalog"]["families"]),
        "FAMILY_EVIDENCE_STREAM": 1, "RESEARCH_OPERATIONS": 1,
    }
    receipts = tuple(StageExecutionReceipt(
        run_id="IROF.RUN.GOLDEN2.WEEK.v0_1", attempt_id="GOLDEN2.ATTEMPT.1", stage_id=stage, stage_version="0.1",
        status="COMPLETE", input_hashes=(), output_artifact_ids=(f"IROF.GOLDEN2.ARTIFACT.{stage}",), metrics={"work_units": metrics[stage]},
    ) for stage in STAGE_IDS)
    receipt = IntegratedRunReceipt(
        run_id="IROF.RUN.GOLDEN2.WEEK.v0_1", attempt_id="GOLDEN2.ATTEMPT.1", status="COMPLETE", stage_receipts=receipts,
        artifact_ids=tuple(row.output_artifact_ids[0] for row in receipts), qa_manifest_id="GOLDEN2-G2-QA",
        aggregate_metrics={"stage_count": len(receipts), "source_m1_rows": metrics["POPULATION_SOURCE_OPT_A"], "c2e_frames": c2e["frame_count"]},
    )
    model = project_research_read_model(source_commit="IROF-GOLDEN2-SYNTHETIC", catalogue=None, run_receipt=receipt, plan=plan)
    return {"run_receipt": receipt, "read_model": model, "plan": plan, "logical_hash": model.logical_sha256}


def run_weekly_full_chain() -> dict[str, Any]:
    upstream = run_weekly_upstream()
    c2e = execute_c2e(upstream)
    sfc = execute_sfc(c2e)
    research = project_research_operations(upstream, c2e, sfc)
    result = {
        "programme_id": PROGRAMME_ID, "upstream_logical_hash": upstream["summary"]["logical_hash"],
        "c2e_logical_hash": c2e["logical_hash"], "sfc_logical_hash": sfc["logical_hash"],
        "research_operations_logical_hash": research["logical_hash"],
        "family_evidence_status": sfc["family_evidence_stream"]["status"],
        "real_market_data": False, "validation_consumed": False, "authority_effect": "NONE",
    }
    result["logical_hash"] = _hash(result)
    return {"upstream": upstream, "c2e": c2e, "sfc": sfc, "research": research, "summary": result}
