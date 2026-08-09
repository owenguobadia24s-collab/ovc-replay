from __future__ import annotations

import time
from typing import Any

from ovc.research_orchestration.cache import SemanticArtifactCache
from ovc.research_orchestration.checkpoint import StageCompletion, assert_fresh_resume_equivalent, build_resume_plan
from ovc.research_orchestration.golden2_downstream import build_golden2_plan, execute_c2e, execute_sfc, project_research_operations, run_weekly_full_chain
from ovc.research_orchestration.golden2_metrics import RUN_ID, telemetry
from ovc.research_orchestration.golden2_weekly import PROGRAMME_ID, build_c1_week, build_c2_week, build_opt_a_week
from ovc.research_orchestration.models import ArtifactRef, SemanticCacheKey
from ovc.research_orchestration.serialization import logical_sha256


def _hash(value: Any) -> str:
    return logical_sha256(value)


def _timed(fn: Any, *args: Any) -> tuple[Any, float, float]:
    w0 = time.perf_counter(); c0 = time.process_time()
    out = fn(*args)
    return out, time.perf_counter() - w0, time.process_time() - c0


def _fresh() -> tuple[dict[str, Any], dict[str, Any], dict[str, str], float, float]:
    w0 = time.perf_counter(); c0 = time.process_time()
    opt_a, wa, ca = _timed(build_opt_a_week)
    c1, w1, c1cpu = _timed(build_c1_week, opt_a)
    c2, w2, c2cpu = _timed(build_c2_week, opt_a, c1)
    upstream_summary = {
        "programme_id": PROGRAMME_ID, "population_id": opt_a["summary"]["population_id"],
        "opt_a": opt_a["summary"], "c1": c1["summary"], "c2": c2["summary"],
        "hidden_generator_truth_consumed": False, "real_market_data": False, "validation_consumed": False, "authority_effect": "NONE",
    }
    upstream_summary["logical_hash"] = _hash(upstream_summary)
    upstream = {"opt_a": opt_a, "c1": c1, "c2": c2, "summary": upstream_summary}
    c2e, we, cecpu = _timed(execute_c2e, upstream)
    sfc, ws, cscpu = _timed(execute_sfc, c2e)
    research, wr, crcpu = _timed(project_research_operations, upstream, c2e, sfc)
    summary = {
        "programme_id": PROGRAMME_ID, "upstream_logical_hash": upstream_summary["logical_hash"],
        "c2e_logical_hash": c2e["logical_hash"], "sfc_logical_hash": sfc["logical_hash"],
        "research_operations_logical_hash": research["logical_hash"], "family_evidence_status": sfc["family_evidence_stream"]["status"],
        "real_market_data": False, "validation_consumed": False, "authority_effect": "NONE",
    }
    summary["logical_hash"] = _hash(summary)
    stage_telemetry = {
        "POPULATION_SOURCE_OPT_A": telemetry("POPULATION_SOURCE_OPT_A", wall=wa, cpu=ca, objects=sum(opt_a["summary"]["m1_counts"].values())),
        "C1": telemetry("C1", wall=w1, cpu=c1cpu, objects=c1["summary"]["record_count"]),
        "C2_REVISED": telemetry("C2_REVISED", wall=w2, cpu=c2cpu, objects=c2["summary"]["structural_snapshot_count"]),
        "C2E_V0_2": telemetry("C2E_V0_2", wall=we, cpu=cecpu, objects=c2e["frame_count"]),
        "SFC_COMBINED": telemetry("SFC_COMBINED", wall=ws, cpu=cscpu, objects=len(sfc["representations"]), pairs=len(sfc["pairs"])),
        "RESEARCH_OPERATIONS": telemetry("RESEARCH_OPERATIONS", wall=wr, cpu=crcpu, objects=len(research["read_model"].nodes)),
    }
    for stage, count in (
        ("OCCURRENCE_CONTEXT", 1), ("SRI_REPRESENTATION", len(sfc["representations"])),
        ("COMPARABILITY_COMPARISON_DISTANCE", len(sfc["pairs"])), ("FDI_C2G_FAMILY", len(sfc["catalog"]["families"])),
        ("FAMILY_EVIDENCE_STREAM", 1),
    ):
        stage_telemetry[stage] = telemetry(stage, wall=None, cpu=None, objects=count, pairs=len(sfc["pairs"]) if stage == "COMPARABILITY_COMPARISON_DISTANCE" else 0)
    outputs = {
        "POPULATION_SOURCE_OPT_A": opt_a["summary"]["logical_hash"], "C1": _hash(c1["summary"]),
        "C2_REVISED": c2["summary"]["logical_hash"], "C2E_V0_2": c2e["logical_hash"],
        "OCCURRENCE_CONTEXT": _hash(sfc["occurrence_context_projection"]), "SRI_REPRESENTATION": _hash(sfc["representations"]),
        "COMPARABILITY_COMPARISON_DISTANCE": _hash(sfc["pairs"]), "FDI_C2G_FAMILY": sfc["catalog"]["logical_hash"],
        "FAMILY_EVIDENCE_STREAM": sfc["family_evidence_stream"]["logical_hash"], "RESEARCH_OPERATIONS": research["logical_hash"],
    }
    return {"upstream": upstream, "c2e": c2e, "sfc": sfc, "research": research, "summary": summary}, stage_telemetry, outputs, time.perf_counter()-w0, time.process_time()-c0


def _checkpoint(outputs: dict[str, str]) -> dict[str, Any]:
    plan = build_golden2_plan(); hashes = dict(plan.stage_spec_hashes)
    rows = tuple(StageCompletion(stage, hashes[stage], outputs[stage], outputs[stage], "GOLDEN2.ATTEMPT.1") for stage in plan.ordered_stage_ids)
    observed = {row.stage_id: row.content_hash for row in rows}
    resume = build_resume_plan(plan=plan, semantic_run_id=RUN_ID, completions=rows, expected_stage_spec_hashes=hashes, observed_content_hashes=observed, new_attempt_id="GOLDEN2.ATTEMPT.2")
    bad = dict(observed); bad["SRI_REPRESENTATION"] = "CORRUPTED"
    corrupt = build_resume_plan(plan=plan, semantic_run_id=RUN_ID, completions=rows, expected_stage_spec_hashes=hashes, observed_content_hashes=bad, new_attempt_id="GOLDEN2.ATTEMPT.BAD")
    return {"restart_count": resume.restart_count, "reused_all_stages": resume.reusable_completed_stage_ids == plan.ordered_stage_ids, "rerun_stage_ids": list(resume.rerun_stage_ids), "corrupt_quarantined_stage_ids": list(corrupt.quarantined_stage_ids), "corrupt_rerun_stage_ids": list(corrupt.rerun_stage_ids), "corrupt_reason_codes": list(corrupt.reason_codes)}


def _cache(fresh: dict[str, Any]) -> dict[str, Any]:
    sfc = fresh["sfc"]
    key = SemanticCacheKey(stage_id="FDI_C2G_FAMILY", stage_version="0.1", parent_semantic_hashes=tuple(sorted(row["logical_hash"] for row in sfc["representations"])), contract_identity="IROF.GOLDEN2.FDI.CONTRACT", schema_identity="IROF.GOLDEN2.FDI.SCHEMA", implementation_identity="IROF.GOLDEN2.FDI.IMPLEMENTATION", pack_bindings={"family_method":"IROF.GOLDEN2.FDI.NULL_STAR.v0_1"}, population_hash=sfc["population"]["logical_hash"], comparability_identity="IROF.GOLDEN2.COMPARABILITY.v0_1")
    artifact = ArtifactRef(artifact_id="IROF.GOLDEN2.FAMILY.CATALOG", logical_hash=sfc["catalog"]["logical_hash"], artifact_type="FAMILY_CATALOG", owner_stage_id="FDI_C2G_FAMILY", owner_run_id=RUN_ID, lifecycle_state="COMPLETE", content_sha256=sfc["catalog"]["logical_hash"], semantic_cache_key=key.key, schema_identity="IROF.GOLDEN2.FDI.SCHEMA")
    cache = SemanticArtifactCache(); cache.register(key, artifact)
    hit = cache.lookup(key, observed_content_sha256=artifact.content_sha256, bytes_avoided=4096, work_units_avoided=max(1, len(sfc["pairs"])))
    corrupt = cache.lookup(key, observed_content_sha256="CORRUPTED"); after = cache.lookup(key)
    return {"initial_status": hit.status, "bytes_avoided": hit.bytes_avoided, "work_units_avoided": hit.work_units_avoided, "corrupt_status": corrupt.status, "corrupt_reason_codes": list(corrupt.reason_codes), "post_quarantine_status": after.status, "post_quarantine_reason_codes": list(after.reason_codes)}


def run_assurance() -> dict[str, Any]:
    fresh, stage_telemetry, outputs, total_wall, total_cpu = _fresh()
    repeated = run_weekly_full_chain()
    assert_fresh_resume_equivalent(fresh["summary"]["logical_hash"], repeated["summary"]["logical_hash"], fresh["summary"]["logical_hash"])
    alternate = dict(fresh["c2e"]); alternate["sfc_inputs"] = list(reversed(list(fresh["c2e"]["sfc_inputs"])))
    alternate_sfc = execute_sfc(alternate)
    if alternate_sfc["logical_hash"] != fresh["sfc"]["logical_hash"]:
        raise AssertionError("GOLDEN2_ALTERNATE_ORDER_CHANGED_OUTPUT")
    result = {
        "schema": "ovc-irof-golden2-assurance-result/v0.1", "programme_id": PROGRAMME_ID,
        "scientific_logical_hash": fresh["summary"]["logical_hash"], "repeated_logical_hash": repeated["summary"]["logical_hash"],
        "fresh_repeated_equivalent": True, "alternate_order_equivalent": True,
        "checkpoint": _checkpoint(outputs), "cache": _cache(fresh), "telemetry": stage_telemetry,
        "whole_run": {"wall_seconds": total_wall, "cpu_seconds": total_cpu, "worker_count": 1},
        "counts": {"m1_bid": fresh["upstream"]["opt_a"]["summary"]["m1_counts"]["BID"], "m1_ask": fresh["upstream"]["opt_a"]["summary"]["m1_counts"]["ASK"], "c1": fresh["upstream"]["c1"]["summary"]["record_count"], "c2_observations": fresh["upstream"]["c2"]["summary"]["observation_count"], "c2_structural_snapshots": fresh["upstream"]["c2"]["summary"]["structural_snapshot_count"], "c2_transitions": fresh["upstream"]["c2"]["summary"]["transition_count"], "c2e_frames": fresh["c2e"]["frame_count"], "c2e_episodes": fresh["c2e"]["episode_count"], "sri_representations": len(fresh["sfc"]["representations"]), "comparison_pairs": len(fresh["sfc"]["pairs"]), "families": len(fresh["sfc"]["catalog"]["families"])},
        "family_evidence_status": fresh["sfc"]["family_evidence_stream"]["status"], "representation_interpretation": fresh["sfc"]["representation_interpretation"],
        "real_source_replay": False, "validation_consumed": False, "authority_effect": "NONE",
    }
    result["receipt_hash"] = _hash({k:v for k,v in result.items() if k not in {"telemetry","whole_run"}})
    return result
