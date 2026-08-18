#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

R4_PATH = Path(__file__).with_name("c2p2_rs0_real_source_shadow_r4.py")
SPEC = importlib.util.spec_from_file_location("c2p2_rs0_real_source_shadow_r4_base_for_r5", R4_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("RS0_R5_R4_BASE_IMPORT_FAILED")
r4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r4
SPEC.loader.exec_module(r4)
base = r4.base

PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-REAL-SOURCE-SHADOW-RUN-R5"
AUTHORITY_ID = "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.6"
TOKEN_ID = "TOKEN.C2P2.RS0.R5.ONE_RUN.v0.6"
GENERATION_ID = r4.GENERATION_ID
GENERATION_SHA = r4.GENERATION_SHA
CANDIDATE_HASHES = r4.CANDIDATE_HASHES
RUNTIME_BINDING_ID = r4.RUNTIME_BINDING_ID
RUNTIME_BINDING_SHA = r4.RUNTIME_BINDING_SHA
RUNTIME_IMPLEMENTATION_BLOB_SHA = r4.RUNTIME_IMPLEMENTATION_BLOB_SHA
EVIDENCE_CONTRACT = r4.EVIDENCE_CONTRACT
SOURCE_ORDER_BINDING_ID = r4.SOURCE_ORDER_BINDING_ID
SOURCE_ORDER_BINDING_SHA = r4.SOURCE_ORDER_BINDING_SHA
SOURCE_ORDER_ADAPTER_ID = r4.SOURCE_ORDER_ADAPTER_ID
SOURCE_ORDER_IMPLEMENTATION_SHA = r4.SOURCE_ORDER_IMPLEMENTATION_SHA
SOURCE_MATERIALISATION_ID = r4.SOURCE_MATERIALISATION_ID
SOURCE_MATERIALISATION_SHA = r4.SOURCE_MATERIALISATION_SHA
SOURCE_LOCATOR_LOGICAL_SHA = r4.SOURCE_LOCATOR_LOGICAL_SHA
SOURCE_ARTIFACT_DIGEST = r4.SOURCE_ARTIFACT_DIGEST
SOURCE_ACTION_RUN_ID = r4.SOURCE_ACTION_RUN_ID
SOURCE_ACTION_ARTIFACT_ID = r4.SOURCE_ACTION_ARTIFACT_ID
EXPECTED_C2_ROWS = r4.EXPECTED_C2_ROWS
EXPECTED_C2E_ROWS = r4.EXPECTED_C2E_ROWS
MEMORY_LIMIT = 1_160_593_408
STORAGE_LIMIT = 11_811_160_064
CONCURRENCY_LIMIT = 1
CHECKPOINT_CADENCE = 4096
RECOVERY_QUALIFICATION_RUN_ID = 32137035782
RECOVERY_QUALIFICATION_ARTIFACT_ID = 9325333929
RECOVERY_QUALIFICATION_ARTIFACT_DIGEST = "sha256:7141d36d3f7c2849348f9c9f03866794c9d86c10f6d7a1dff48ef97eb80cbc20"
RECOVERY_MAX_DATABASE_BYTES = 8_992_563_200
RECOVERY_MAX_PEAK_RSS_BYTES = 429_891_584

AUTHORITY_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_6.json")
PRIOR_CONSUMPTION_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_4.json")
DECISION_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_R5_OPERATOR_DECISION_v0_1.json")
PRELAUNCH_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_R5_PRELAUNCH_CURRENTNESS_v0_1.json")
CANDIDATE_PATH = r4.CANDIDATE_PATH
RUNTIME_BINDING_PATH = r4.RUNTIME_BINDING_PATH
RUNTIME_IMPLEMENTATION_PATH = r4.RUNTIME_IMPLEMENTATION_PATH
SOURCE_ORDER_BINDING_PATH = r4.SOURCE_ORDER_BINDING_PATH
DEPENDENCY_REGISTRY_PATH = r4.DEPENDENCY_REGISTRY_PATH
SOURCE_CLOSEOUT_PATH = r4.SOURCE_CLOSEOUT_PATH
RECOVERY_QUALIFICATION_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_R4_CAPACITY_RECOVERY_QUALIFICATION_v0_1.json")
R4_GATE_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_R5_GATE_PACKET_v0_1.json")
EXTERNAL_ROOT_PATH = r4.EXTERNAL_ROOT_PATH
RUN_BRANCH = "run/c2p2-rs0-real-source-shadow-r5-20260818"


class PreflightError(RuntimeError):
    pass


def git_blob_sha(repo_root: Path, path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=repo_root, text=True).strip()


def validate_repo_bindings(repo_root: Path) -> dict[str, Any]:
    decision = base.load_json(repo_root / DECISION_PATH)
    if decision.get("decision") != "PASS" or decision.get("gate_id") != "C2P2-RS0-FRESH-GRUN-R5":
        raise PreflightError("RS0_R5_OPERATOR_DECISION_NOT_PASS")
    if decision.get("approved_execution_storage_limit_bytes") != STORAGE_LIMIT:
        raise PreflightError("RS0_R5_OPERATOR_CAPACITY_NOT_ACCEPTED")

    prelaunch = base.load_json(repo_root / PRELAUNCH_PATH)
    if prelaunch.get("status") != "PASS" or prelaunch.get("source_read") is not False or prelaunch.get("semantic_execution_started") is not False:
        raise PreflightError("RS0_R5_PRELAUNCH_CURRENTNESS_NOT_CLEAN")

    authority = base.load_json(repo_root / AUTHORITY_PATH)
    if authority.get("authority_id") != AUTHORITY_ID or authority.get("state") != "AUTHORISED_NOT_STARTED":
        raise PreflightError("RS0_R5_AUTHORITY_NOT_LAUNCHABLE")
    if authority.get("execution_count_limit") != 1 or authority.get("execution_count_consumed") != 0 or authority.get("run_count_remaining") != 1:
        raise PreflightError("RS0_R5_SINGLE_USE_AUTHORITY_NOT_AVAILABLE")
    if authority.get("fresh_run_token_id") != TOKEN_ID or authority.get("fresh_run_token_state") != "UNCONSUMED":
        raise PreflightError("RS0_R5_TOKEN_NOT_AVAILABLE")
    if authority.get("run_mode") != "PREREGISTERED_COMPARATIVE_A_B_C_SHADOW_ONLY" or authority.get("no_vit") is not True:
        raise PreflightError("RS0_R5_RUN_MODE_OR_NO_VIT_DRIFT")

    prior = base.load_json(repo_root / PRIOR_CONSUMPTION_PATH)
    if prior.get("authority_id") != "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.5":
        raise PreflightError("RS0_R5_R4_AUTHORITY_ID_DRIFT")
    if prior.get("execution_count_consumed") != 1 or prior.get("run_count_remaining") != 0:
        raise PreflightError("RS0_R5_R4_CONSUMPTION_NOT_PRESERVED")

    generation = authority.get("candidate_generation", {})
    if generation.get("generation_id") != GENERATION_ID or generation.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_R5_CANDIDATE_GENERATION_DRIFT")
    if generation.get("candidate_logical_hashes") != CANDIDATE_HASHES:
        raise PreflightError("RS0_R5_CANDIDATE_HASH_DRIFT")
    if generation.get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER" or generation.get("active_object_pack_id") is not None:
        raise PreflightError("RS0_R5_SELECTION_STATE_DRIFT")

    runtime = authority.get("runtime_binding", {})
    if runtime.get("binding_id") != RUNTIME_BINDING_ID or runtime.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_R5_RUNTIME_BINDING_AUTHORITY_DRIFT")
    if runtime.get("runtime_generation_id") != r4.RUNTIME_GENERATION_ID or runtime.get("evidence_contract_id") != EVIDENCE_CONTRACT:
        raise PreflightError("RS0_R5_RUNTIME_OR_EVIDENCE_GENERATION_DRIFT")
    if runtime.get("implementation_git_blob_sha") != RUNTIME_IMPLEMENTATION_BLOB_SHA:
        raise PreflightError("RS0_R5_RUNTIME_IMPLEMENTATION_AUTHORITY_DRIFT")
    if git_blob_sha(repo_root, RUNTIME_IMPLEMENTATION_PATH) != RUNTIME_IMPLEMENTATION_BLOB_SHA:
        raise PreflightError("RS0_R5_RUNTIME_IMPLEMENTATION_BYTES_DRIFT")

    binding = base.load_json(repo_root / RUNTIME_BINDING_PATH)
    if binding.get("binding_id") != RUNTIME_BINDING_ID or binding.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_R5_RUNTIME_BINDING_FILE_DRIFT")
    if binding.get("runtime_implementation_git_blob_sha") != RUNTIME_IMPLEMENTATION_BLOB_SHA:
        raise PreflightError("RS0_R5_RUNTIME_BINDING_IMPLEMENTATION_DRIFT")
    if binding.get("evidence_contract_id") != EVIDENCE_CONTRACT:
        raise PreflightError("RS0_R5_RUNTIME_BINDING_EVIDENCE_CONTRACT_DRIFT")

    source_order = authority.get("source_order_route", {})
    if source_order.get("binding_id") != SOURCE_ORDER_BINDING_ID or source_order.get("binding_logical_sha256") != SOURCE_ORDER_BINDING_SHA:
        raise PreflightError("RS0_R5_SOURCE_ORDER_AUTHORITY_DRIFT")
    if source_order.get("adapter_id") != SOURCE_ORDER_ADAPTER_ID or source_order.get("implementation_sha256") != SOURCE_ORDER_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_R5_SOURCE_ORDER_IMPLEMENTATION_AUTHORITY_DRIFT")
    order_binding = base.load_json(repo_root / SOURCE_ORDER_BINDING_PATH)
    if order_binding.get("binding_id") != SOURCE_ORDER_BINDING_ID or order_binding.get("logical_sha256") != SOURCE_ORDER_BINDING_SHA:
        raise PreflightError("RS0_R5_SOURCE_ORDER_BINDING_FILE_DRIFT")

    dependency = base.load_json(repo_root / DEPENDENCY_REGISTRY_PATH)
    if dependency.get("entries") != []:
        raise PreflightError("RS0_R5_DEPENDENCY_REGISTRY_DRIFT")

    candidates_doc = base.load_json(repo_root / CANDIDATE_PATH)
    if candidates_doc.get("generation_id") != GENERATION_ID or candidates_doc.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_R5_CANDIDATE_DOCUMENT_DRIFT")
    specs = candidates_doc.get("candidates")
    if not isinstance(specs, list) or len(specs) != 3:
        raise PreflightError("RS0_R5_CANDIDATE_SET_CARDINALITY_INVALID")
    observed_hashes = {row.get("candidate_id"): row.get("candidate_logical_hash") for row in specs}
    if observed_hashes != CANDIDATE_HASHES or any(row.get("activation_eligible") is not False for row in specs):
        raise PreflightError("RS0_R5_CANDIDATE_DOCUMENT_HASH_OR_ACTIVATION_DRIFT")

    source = authority.get("source_materialisation", {})
    if source.get("materialisation_id") != SOURCE_MATERIALISATION_ID or source.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_R5_SOURCE_AUTHORITY_DRIFT")
    if source.get("locator_logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA or source.get("artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_R5_SOURCE_LOCATOR_OR_ARTIFACT_AUTHORITY_DRIFT")
    if source.get("github_actions_source_run_id") != SOURCE_ACTION_RUN_ID or source.get("github_actions_source_artifact_id") != SOURCE_ACTION_ARTIFACT_ID:
        raise PreflightError("RS0_R5_SOURCE_ACTION_IDENTITY_DRIFT")

    closeout = base.load_json(repo_root / SOURCE_CLOSEOUT_PATH)
    material = closeout.get("materialisation", {})
    if material.get("materialisation_id") != SOURCE_MATERIALISATION_ID or material.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_R5_SOURCE_CLOSEOUT_DRIFT")
    rows = material.get("rows", {})
    if rows.get("C2_VNEXT") != EXPECTED_C2_ROWS or rows.get("C2E_V0_2") != EXPECTED_C2E_ROWS:
        raise PreflightError("RS0_R5_SOURCE_ROW_COUNT_DRIFT")
    artifact = closeout.get("artifact", {})
    if artifact.get("github_actions_artifact_id") != SOURCE_ACTION_ARTIFACT_ID or artifact.get("github_actions_artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_R5_SOURCE_ARTIFACT_DRIFT")

    qualification = base.load_json(repo_root / RECOVERY_QUALIFICATION_PATH)
    q = qualification.get("qualification", {})
    if qualification.get("status") != "PASS" or q.get("github_run_id") != RECOVERY_QUALIFICATION_RUN_ID or q.get("status") != "PASS":
        raise PreflightError("RS0_R5_RECOVERY_QUALIFICATION_DRIFT")
    if qualification.get("max_measured_database_bytes") != RECOVERY_MAX_DATABASE_BYTES:
        raise PreflightError("RS0_R5_RECOVERY_DATABASE_HIGH_WATER_DRIFT")
    if qualification.get("max_measured_peak_rss_bytes") != RECOVERY_MAX_PEAK_RSS_BYTES:
        raise PreflightError("RS0_R5_RECOVERY_MEMORY_HIGH_WATER_DRIFT")
    if qualification.get("proposed_execution_storage_limit_bytes") != STORAGE_LIMIT:
        raise PreflightError("RS0_R5_RECOVERY_PROPOSED_CEILING_DRIFT")
    if qualification.get("real_source_read") is not False or qualification.get("real_source_execution") is not False:
        raise PreflightError("RS0_R5_RECOVERY_AUTHORITY_CONTAMINATION")

    gate = base.load_json(repo_root / R4_GATE_PATH)
    if gate.get("gate_id") != "C2P2-RS0-FRESH-GRUN-R5" or gate.get("recommended_decision") != "PASS":
        raise PreflightError("RS0_R5_GATE_PACKET_DRIFT")
    if gate.get("external_artifact_hashes", {}).get("recovery_qualification_artifact_id") != RECOVERY_QUALIFICATION_ARTIFACT_ID:
        raise PreflightError("RS0_R5_RECOVERY_ARTIFACT_ID_DRIFT")
    if gate.get("external_artifact_hashes", {}).get("recovery_qualification_artifact_digest") != RECOVERY_QUALIFICATION_ARTIFACT_DIGEST:
        raise PreflightError("RS0_R5_RECOVERY_ARTIFACT_DIGEST_DRIFT")

    capacity = authority.get("capacity", {})
    expected_capacity = {
        "peak_memory_limit_bytes": MEMORY_LIMIT,
        "external_storage_limit_bytes": STORAGE_LIMIT,
        "concurrency_limit": CONCURRENCY_LIMIT,
        "checkpoint_cadence_source_records": CHECKPOINT_CADENCE,
        "capacity_exceeded": "FAIL_CLOSED_RETURN_TO_OPERATOR",
        "storage_ceiling_change": "OPERATOR_APPROVED_R5_ONLY",
        "reduced_precision": "FORBIDDEN",
        "population_change": "FORBIDDEN",
        "objectpack_change": "FORBIDDEN",
    }
    if capacity != expected_capacity:
        raise PreflightError("RS0_R5_CAPACITY_ENVELOPE_DRIFT")

    external = base.load_json(repo_root / EXTERNAL_ROOT_PATH)
    if external.get("rs0_run_root", {}).get("binding_status") != "EXACT_BOUND":
        raise PreflightError("RS0_R5_EXTERNAL_ARTIFACT_ROOT_DRIFT")

    return {
        "authority_id": AUTHORITY_ID,
        "candidate_ids": [row["candidate_id"] for row in sorted(specs, key=lambda item: item["candidate_id"])],
        "capacity": capacity,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "runtime_binding_logical_sha256": RUNTIME_BINDING_SHA,
        "runtime_generation_id": r4.RUNTIME_GENERATION_ID,
        "evidence_contract_id": EVIDENCE_CONTRACT,
        "source_order_binding_id": SOURCE_ORDER_BINDING_ID,
        "source_order_binding_logical_sha256": SOURCE_ORDER_BINDING_SHA,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
    }


r4.PACKET_ID = PACKET_ID
r4.AUTHORITY_ID = AUTHORITY_ID
r4.STORAGE_LIMIT = STORAGE_LIMIT
r4.MEMORY_LIMIT = MEMORY_LIMIT
r4.CONCURRENCY_LIMIT = CONCURRENCY_LIMIT
r4.CHECKPOINT_CADENCE = CHECKPOINT_CADENCE
r4.AUTHORITY_PATH = AUTHORITY_PATH
r4.PRIOR_CONSUMPTION_PATH = PRIOR_CONSUMPTION_PATH
r4.DECISION_PATH = DECISION_PATH
r4.PRELAUNCH_PATH = PRELAUNCH_PATH
r4.QUALIFICATION_PATH = RECOVERY_QUALIFICATION_PATH
r4.RUN_BRANCH = RUN_BRANCH
r4.validate_repo_bindings = validate_repo_bindings


def candidate_child(repo_root: Path, source_plan_path: Path, candidate_id: str, output_dir: Path) -> int:
    code = r4.candidate_child(repo_root, source_plan_path, candidate_id, output_dir)
    old = output_dir / f"{candidate_id}.r4-summary.json"
    new = output_dir / f"{candidate_id}.r5-summary.json"
    if old.exists():
        summary = base.load_json(old)
        summary["schema"] = "ovc-c2p2-rs0-real-source-candidate-r5-summary/v1"
        summary["r5_authority_id"] = AUTHORITY_ID
        summary["storage_limit_bytes"] = STORAGE_LIMIT
        base.write_json(new, summary)
        old.unlink()
    return code


def preflight(repo_root: Path, source_root: Path, output_dir: Path) -> int:
    bindings = validate_repo_bindings(repo_root)
    source_plan = base.validate_source_artifact(source_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    base.write_json(output_dir / "source-plan-r5.json", source_plan)
    base.write_json(output_dir / "preflight-r5.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r5-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "token_id": TOKEN_ID,
        "bindings": bindings,
        "source_plan": source_plan,
        "semantic_execution_started": False,
        "authority_consumed": False,
        "source_read_validated_only": True,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "github_actions": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
        },
    })
    return 0


def execute(repo_root: Path, source_plan_path: Path, output_dir: Path, github_run_id: str | None) -> int:
    bindings = validate_repo_bindings(repo_root)
    source_plan = base.load_json(source_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = base.utc_now()

    base.write_json(output_dir / "run-r5-start-receipt.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r5-start/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "fresh_run_token_id": TOKEN_ID,
        "single_use_authority_consumed_on_semantic_launch": True,
        "started_at": started_at,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "runtime_generation_id": r4.RUNTIME_GENERATION_ID,
        "evidence_contract_id": EVIDENCE_CONTRACT,
        "source_order_binding_id": SOURCE_ORDER_BINDING_ID,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_plan": source_plan,
        "capacity": bindings["capacity"],
        "selection_state": "NONE_SELECTED",
        "activation_state": "NONE",
        "no_vit": True,
    })

    summaries: list[dict[str, Any]] = []
    failure_class: str | None = None
    for candidate_id in bindings["candidate_ids"]:
        command = [
            sys.executable, str(Path(__file__).resolve()), "candidate-child",
            "--repo-root", str(repo_root),
            "--source-plan", str(source_plan_path),
            "--candidate-id", candidate_id,
            "--output-dir", str(output_dir),
        ]
        completed = subprocess.run(command, check=False)
        summary = base.load_json(output_dir / f"{candidate_id}.r5-summary.json")
        summaries.append(summary)
        if summary.get("status") != "COMPLETED_SHADOW_UNSELECTED" or completed.returncode != 0:
            detail = str(summary.get("detail", ""))
            failure_class = "CAPACITY_EXCEEDED" if (
                summary.get("reason") in {"MemoryError", "OSError"} or "STORAGE_LIMIT" in detail
            ) else "EXECUTION_FAILURE"
            break

    attempted = {row["candidate_id"] for row in summaries}
    for candidate_id in bindings["candidate_ids"]:
        if candidate_id not in attempted:
            summaries.append({
                "schema": "ovc-c2p2-rs0-real-source-candidate-r5-summary/v1",
                "candidate_id": candidate_id,
                "candidate_logical_hash": CANDIDATE_HASHES[candidate_id],
                "status": "NOT_RUN_FAIL_CLOSED_AFTER_PRIOR_CANDIDATE_FAILURE",
                "selection_state": "NONE_SELECTED",
                "activation_state": "NONE",
            })

    completed_all = all(row.get("status") == "COMPLETED_SHADOW_UNSELECTED" for row in summaries)
    status = "COMPLETED_COMPARATIVE_SET_NO_WINNER" if completed_all else (
        "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED" if failure_class == "CAPACITY_EXCEEDED"
        else "BLOCKED_EXECUTION_FAILURE_SINGLE_USE_CONSUMED"
    )
    gate_id = "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" if completed_all else "C2P2-RS0-RUN-RECOVERY-R5"
    result = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r5-result/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": status,
        "started_at": started_at,
        "completed_at": base.utc_now(),
        "github_run_id": github_run_id,
        "authority": {
            "authority_id": AUTHORITY_ID,
            "fresh_run_token_id": TOKEN_ID,
            "execution_count_limit": 1,
            "execution_count_consumed": 1,
            "run_count_remaining": 0,
            "single_use_consumed_even_on_post_launch_failure": True,
        },
        "candidate_generation": {
            "generation_id": GENERATION_ID,
            "generation_logical_sha256": GENERATION_SHA,
            "candidate_logical_hashes": CANDIDATE_HASHES,
        },
        "runtime_binding": {
            "binding_id": RUNTIME_BINDING_ID,
            "logical_sha256": RUNTIME_BINDING_SHA,
            "runtime_generation_id": r4.RUNTIME_GENERATION_ID,
            "implementation_git_blob_sha": RUNTIME_IMPLEMENTATION_BLOB_SHA,
        },
        "evidence_contract": {
            "contract_id": EVIDENCE_CONTRACT,
            "equivalence_target": "TERMINAL_AND_LIFECYCLE_EQUIVALENCE_WITH_VERSIONED_NEGATIVE_EVIDENCE_CONTRACT",
        },
        "source_order_route": {
            "binding_id": SOURCE_ORDER_BINDING_ID,
            "binding_logical_sha256": SOURCE_ORDER_BINDING_SHA,
            "adapter_id": SOURCE_ORDER_ADAPTER_ID,
            "implementation_sha256": SOURCE_ORDER_IMPLEMENTATION_SHA,
        },
        "source_materialisation": {
            "materialisation_id": SOURCE_MATERIALISATION_ID,
            "logical_sha256": SOURCE_MATERIALISATION_SHA,
            "locator_logical_sha256": SOURCE_LOCATOR_LOGICAL_SHA,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "c2_rows": EXPECTED_C2_ROWS,
            "c2e_rows": EXPECTED_C2E_ROWS,
        },
        "candidate_results": summaries,
        "capacity": bindings["capacity"],
        "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER" if completed_all else "NONE_SELECTED_INCOMPLETE_RUN",
        "preferred_candidate": None,
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "ec1_scientific_effect": "NONE",
        "f0_a": "HOLD_NO_JOINT_LAUNCH",
        "validation": "LOCKED_UNCONSUMED",
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "no_vit": True,
        "next_operator_gate": gate_id,
        "rollback": "PRESERVE_R4_CONSUMPTION_AND_ALL_R5_RUN_AND_PARTIAL_EVIDENCE_FORWARD_SUPERSESSION_ONLY",
    }

    result_path = output_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R5_RESULT_v0_1.json"
    base.write_json(result_path, result)
    release_dir = repo_root / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    release_result_path = release_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R5_RESULT_v0_1.json"
    base.write_json(release_result_path, result)
    result_sha = base.sha256_file(release_result_path)

    base.write_json(repo_root / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_5.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-consumption/v5",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "fresh_run_token_id": TOKEN_ID,
        "operator_decision_ref": str(DECISION_PATH),
        "execution_count_limit": 1,
        "execution_count_consumed": 1,
        "run_count_remaining": 0,
        "consumption_status": "CONSUMED_BY_LAUNCHED_REAL_SOURCE_EXECUTION_R5",
        "run_result_status": status,
        "run_result_sha256": result_sha,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "evidence_contract_id": EVIDENCE_CONTRACT,
        "source_order_binding_id": SOURCE_ORDER_BINDING_ID,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "rollback": "CONSUMPTION_IS_APPEND_ONLY_NO_TOKEN_REINSTATEMENT_WITHOUT_NEW_OPERATOR_AUTHORITY",
    })

    base.write_json(repo_root / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_6.json", {
        "schema": "ovc-c2p2-rs0-execution-state/v6",
        "plan_id": PROGRAMME_ID,
        "plan_version": "v0.1",
        "packet_id": PACKET_ID,
        "status": "GATE_READY" if completed_all else "BLOCKED",
        "branch": RUN_BRANCH,
        "authority_required": "OPERATOR_REQUIRED_AT_NEXT_GATE",
        "authority_id": AUTHORITY_ID,
        "run_authority_consumed": True,
        "run_count_remaining": 0,
        "run_result_ref": str(release_result_path).replace(str(repo_root) + os.sep, ""),
        "run_result_sha256": result_sha,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "runtime_binding_logical_sha256": RUNTIME_BINDING_SHA,
        "evidence_contract_id": EVIDENCE_CONTRACT,
        "source_order_binding_id": SOURCE_ORDER_BINDING_ID,
        "blockers": [] if completed_all else [status],
        "mandatory_stop": gate_id,
        "next_packet": gate_id,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "f0_a": "HOLD_UNCHANGED",
        "validation": "LOCKED_UNCONSUMED",
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "no_vit": True,
        "rollback": "PRESERVE_R4_CONSUMPTION_AND_R5_EVIDENCE_FORWARD_SUPERSEDE_ONLY",
    })

    gate = {
        "schema": "ovc-c2p2-rs0-post-run-r5-gate-packet/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": gate_id,
        "gate_classification": "OPERATOR_REQUIRED",
        "status": "GATE_READY",
        "current_authority": "R5_SINGLE_USE_CONSUMED_NO_SELECTION_NO_ACTIVATION",
        "run_status": status,
        "run_result_sha256": result_sha,
        "candidate_results": summaries,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "evidence_contract_id": EVIDENCE_CONTRACT,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "f0_a": "HOLD",
        "no_vit": True,
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "warnings": ["Whole-population streams use the qualified indexed necessary-key runtime and v0.2 negative-coverage evidence contract; ephemeral per-candidate SQLite databases are deleted after compact scientific-review aggregates are materialised."],
        "unresolved_issues": [] if completed_all else ["R5 comparative run did not complete; no scientific selection is permitted."],
        "rollback": "FORWARD_ONLY_PRESERVE_R4_AND_R5_AUTHORITY_CONSUMPTION_AND_ALL_COMPACT_RUN_EVIDENCE",
        "recommended_decision": "REVIEW_COMPARATIVE_EVIDENCE_NO_AUTOMATIC_SELECTION" if completed_all else "BLOCK",
        "exact_work_after_approval": ("Operator scientific review may select, defer, block or quarantine an ObjectPack candidate only at this gate; no activation follows automatically." if completed_all else "Authorise a separately bounded recovery generation before any further real-source execution."),
    }
    base.write_json(release_dir / "C2P2_RS0_POST_RUN_R5_GATE_PACKET_v0_1.json", gate)
    return 0 if completed_all else 75


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-repo-bindings")
    validate.add_argument("--repo-root", type=Path, default=Path("."))
    pf = sub.add_parser("preflight")
    pf.add_argument("--repo-root", type=Path, default=Path("."))
    pf.add_argument("--source-root", type=Path, required=True)
    pf.add_argument("--output-dir", type=Path, required=True)
    child = sub.add_parser("candidate-child")
    child.add_argument("--repo-root", type=Path, default=Path("."))
    child.add_argument("--source-plan", type=Path, required=True)
    child.add_argument("--candidate-id", required=True)
    child.add_argument("--output-dir", type=Path, required=True)
    run = sub.add_parser("execute")
    run.add_argument("--repo-root", type=Path, default=Path("."))
    run.add_argument("--source-plan", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--github-run-id")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "validate-repo-bindings":
            print(json.dumps(validate_repo_bindings(repo_root), sort_keys=True))
            return 0
        if args.command == "preflight":
            return preflight(repo_root, args.source_root.resolve(), args.output_dir.resolve())
        if args.command == "candidate-child":
            return candidate_child(repo_root, args.source_plan.resolve(), args.candidate_id, args.output_dir.resolve())
        if args.command == "execute":
            return execute(repo_root, args.source_plan.resolve(), args.output_dir.resolve(), args.github_run_id)
    except PreflightError as exc:
        print(f"C2P2_RS0_R5_PREFLIGHT_ERROR={exc}", file=sys.stderr)
        return 64
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
