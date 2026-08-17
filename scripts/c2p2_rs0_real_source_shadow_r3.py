#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any, Iterable

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    SOURCE_ORDER_ADAPTER_ID,
    merge_source_factories_with_kind_segmentation,
)

BASE_RUNNER_PATH = Path(__file__).with_name("c2p2_rs0_real_source_shadow_r2.py")
SPEC = importlib.util.spec_from_file_location("c2p2_rs0_real_source_shadow_r2_base", BASE_RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("RS0_R3_BASE_RUNNER_IMPORT_FAILED")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)

PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-REAL-SOURCE-SHADOW-RUN-R3"
AUTHORITY_ID = "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4"
ADAPTER_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2"
ADAPTER_BINDING_SHA = "01c3e85d5c4b47fbb2a102a1d4dff3774e49fcd15110157aaac3ea538a51201c"
ADAPTER_IMPLEMENTATION_SHA = "eaf19ce7cb3ffa9f1839d5a63586a6ead8ab73fc3dde57cf0011290022eee5ed"
BASE_SPOOLED_ADAPTER_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_v0_1"
BASE_SPOOLED_IMPLEMENTATION_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime_streaming.py")
BASE_SPOOLED_IMPLEMENTATION_SHA = "8d3de43abb1b6c80817ca24b6ef301a2bd39dbc3024cc31e92f382b4dfd6b648"
AUTHORITY_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_4.json")
PRIOR_CONSUMPTION_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_2.json")
ADAPTER_BINDING_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2.json")
ADAPTER_IMPLEMENTATION_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime_source_order.py")
DECISION_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_R3_OPERATOR_DECISION_v0_1.json")

base.PACKET_ID = PACKET_ID
base.AUTHORITY_ID = AUTHORITY_ID
base.AUTHORITY_PATH = AUTHORITY_PATH
base.PRIOR_CONSUMPTION_PATH = PRIOR_CONSUMPTION_PATH
base.ADAPTER_BINDING_ID = ADAPTER_BINDING_ID
base.ADAPTER_BINDING_SHA = ADAPTER_BINDING_SHA
base.ADAPTER_BINDING_PATH = ADAPTER_BINDING_PATH
base.ADAPTER_IMPLEMENTATION_PATH = ADAPTER_IMPLEMENTATION_PATH
base.ADAPTER_IMPLEMENTATION_SHA = ADAPTER_IMPLEMENTATION_SHA
base.ADAPTER_ID = SOURCE_ORDER_ADAPTER_ID
base.DECISION_PATH = DECISION_PATH
base.__file__ = str(Path(__file__).resolve())

ORIGINAL_CANDIDATE_CHILD = base.candidate_child


def validate_repo_bindings(repo_root: Path) -> dict[str, Any]:
    authority = base.load_json(repo_root / AUTHORITY_PATH)
    decision = base.load_json(repo_root / DECISION_PATH)
    if decision.get("decision") != "PASS" or decision.get("gate_id") != "C2P2-RS0-FRESH-GRUN-R3":
        raise base.PreflightError("RS0_R3_OPERATOR_DECISION_NOT_PASS")
    if authority.get("authority_id") != AUTHORITY_ID or authority.get("state") != "AUTHORISED_NOT_STARTED":
        raise base.PreflightError("RS0_R3_AUTHORITY_NOT_LAUNCHABLE")
    if authority.get("execution_count_limit") != 1 or authority.get("execution_count_consumed") != 0 or authority.get("run_count_remaining") != 1:
        raise base.PreflightError("RS0_R3_SINGLE_USE_AUTHORITY_NOT_AVAILABLE")
    if authority.get("run_mode") != "PREREGISTERED_COMPARATIVE_A_B_C_SHADOW_ONLY":
        raise base.PreflightError("RS0_R3_RUN_MODE_DRIFT")

    prior = base.load_json(repo_root / PRIOR_CONSUMPTION_PATH)
    if prior.get("authority_id") != "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.3":
        raise base.PreflightError("RS0_R3_PRIOR_AUTHORITY_ID_DRIFT")
    if prior.get("execution_count_consumed") != 1 or prior.get("run_count_remaining") != 0:
        raise base.PreflightError("RS0_R3_PRIOR_AUTHORITY_CONSUMPTION_NOT_PRESERVED")

    generation = authority.get("candidate_generation", {})
    if generation.get("generation_id") != base.GENERATION_ID or generation.get("generation_logical_sha256") != base.GENERATION_SHA:
        raise base.PreflightError("RS0_R3_CANDIDATE_GENERATION_DRIFT")
    if generation.get("candidate_logical_hashes") != base.CANDIDATE_HASHES:
        raise base.PreflightError("RS0_R3_CANDIDATE_HASH_DRIFT")
    if generation.get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER" or generation.get("active_object_pack_id") is not None:
        raise base.PreflightError("RS0_R3_SELECTION_STATE_DRIFT")

    runtime = authority.get("runtime_binding", {})
    if runtime.get("binding_id") != base.RUNTIME_BINDING_ID or runtime.get("logical_sha256") != base.RUNTIME_BINDING_SHA:
        raise base.PreflightError("RS0_R3_CORE_RUNTIME_BINDING_DRIFT")
    if runtime.get("implementation_sha256") != base.RUNTIME_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_CORE_RUNTIME_AUTHORITY_DRIFT")
    if base.sha256_file(repo_root / base.RUNTIME_IMPLEMENTATION_PATH) != base.RUNTIME_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_CORE_RUNTIME_BYTES_DRIFT")

    adapter = authority.get("execution_adapter", {})
    if adapter.get("binding_id") != ADAPTER_BINDING_ID or adapter.get("binding_logical_sha256") != ADAPTER_BINDING_SHA:
        raise base.PreflightError("RS0_R3_ADAPTER_BINDING_AUTHORITY_DRIFT")
    if adapter.get("adapter_id") != SOURCE_ORDER_ADAPTER_ID or adapter.get("implementation_sha256") != ADAPTER_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_ADAPTER_IMPLEMENTATION_AUTHORITY_DRIFT")
    if adapter.get("base_spooled_adapter_id") != BASE_SPOOLED_ADAPTER_ID or adapter.get("base_spooled_adapter_implementation_sha256") != BASE_SPOOLED_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_BASE_SPOOLED_ADAPTER_AUTHORITY_DRIFT")
    if base.sha256_file(repo_root / ADAPTER_IMPLEMENTATION_PATH) != ADAPTER_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_SOURCE_ORDER_ADAPTER_BYTES_DRIFT")
    if base.sha256_file(repo_root / BASE_SPOOLED_IMPLEMENTATION_PATH) != BASE_SPOOLED_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_BASE_SPOOLED_ADAPTER_BYTES_DRIFT")

    binding = base.load_json(repo_root / ADAPTER_BINDING_PATH)
    if binding.get("binding_id") != ADAPTER_BINDING_ID or binding.get("logical_sha256") != ADAPTER_BINDING_SHA:
        raise base.PreflightError("RS0_R3_ADAPTER_BINDING_FILE_DRIFT")
    if binding.get("status") != "QUALIFIED_INACTIVE_PENDING_FRESH_GRUN_R3":
        raise base.PreflightError("RS0_R3_ADAPTER_BINDING_NOT_QUALIFIED_INACTIVE")
    qualification = binding.get("qualification", {})
    if qualification.get("adversarial_equal_time_a_b_c_reference_equivalence") != "PASS_EXACT":
        raise base.PreflightError("RS0_R3_ADAPTER_REFERENCE_EQUIVALENCE_NOT_PASS")
    if qualification.get("full_cardinality_synthetic_capacity") != "PASS" or qualification.get("exact_current_source_ordering_only_preflight") != "PASS":
        raise base.PreflightError("RS0_R3_ADAPTER_CAPACITY_OR_SOURCE_PREFLIGHT_NOT_PASS")
    if qualification.get("real_source_semantic_execution") != "NONE" or qualification.get("run_token_consumed") is not False:
        raise base.PreflightError("RS0_R3_RECOVERY_QUALIFICATION_AUTHORITY_DRIFT")
    source_order = binding.get("source_order_recovery", {})
    if source_order.get("adapter_id") != SOURCE_ORDER_ADAPTER_ID or source_order.get("implementation_sha256") != ADAPTER_IMPLEMENTATION_SHA:
        raise base.PreflightError("RS0_R3_SOURCE_ORDER_BINDING_IMPLEMENTATION_DRIFT")
    if source_order.get("runtime_contract_source_rows") != "C2_VNEXT_LEVEL_OR_CONTAINER_ONLY":
        raise base.PreflightError("RS0_R3_SOURCE_ORDER_RUNTIME_CONTRACT_DRIFT")

    core_binding = base.load_json(repo_root / base.RUNTIME_BINDING_PATH)
    if core_binding.get("binding_id") != base.RUNTIME_BINDING_ID or core_binding.get("logical_sha256") != base.RUNTIME_BINDING_SHA:
        raise base.PreflightError("RS0_R3_CORE_RUNTIME_BINDING_FILE_DRIFT")

    dependency = base.load_json(repo_root / base.DEPENDENCY_REGISTRY_PATH)
    if dependency.get("logical_sha256") != base.DEPENDENCY_REGISTRY_SHA or dependency.get("entries") != []:
        raise base.PreflightError("RS0_R3_DEPENDENCY_REGISTRY_DRIFT")

    candidates_doc = base.load_json(repo_root / base.CANDIDATE_PATH)
    if candidates_doc.get("generation_id") != base.GENERATION_ID or candidates_doc.get("generation_logical_sha256") != base.GENERATION_SHA:
        raise base.PreflightError("RS0_R3_CANDIDATE_DOCUMENT_DRIFT")
    specs = candidates_doc.get("candidates")
    if not isinstance(specs, list) or len(specs) != 3:
        raise base.PreflightError("RS0_R3_CANDIDATE_SET_CARDINALITY_INVALID")
    observed_hashes = {row.get("candidate_id"): row.get("candidate_logical_hash") for row in specs}
    if observed_hashes != base.CANDIDATE_HASHES or any(row.get("activation_eligible") is not False for row in specs):
        raise base.PreflightError("RS0_R3_CANDIDATE_DOCUMENT_HASH_OR_ACTIVATION_DRIFT")

    source = authority.get("source_materialisation", {})
    if source.get("materialisation_id") != base.SOURCE_MATERIALISATION_ID or source.get("logical_sha256") != base.SOURCE_MATERIALISATION_SHA:
        raise base.PreflightError("RS0_R3_SOURCE_AUTHORITY_DRIFT")
    if source.get("locator_logical_sha256") != base.SOURCE_LOCATOR_LOGICAL_SHA or source.get("artifact_digest") != base.SOURCE_ARTIFACT_DIGEST:
        raise base.PreflightError("RS0_R3_SOURCE_LOCATOR_OR_ARTIFACT_AUTHORITY_DRIFT")
    if source.get("github_actions_source_run_id") != base.SOURCE_ACTION_RUN_ID or source.get("github_actions_source_artifact_id") != 9283576949:
        raise base.PreflightError("RS0_R3_SOURCE_ACTION_IDENTITY_DRIFT")

    closeout = base.load_json(repo_root / base.SOURCE_CLOSEOUT_PATH)
    materialisation = closeout.get("materialisation", {})
    if materialisation.get("materialisation_id") != base.SOURCE_MATERIALISATION_ID or materialisation.get("logical_sha256") != base.SOURCE_MATERIALISATION_SHA:
        raise base.PreflightError("RS0_R3_SOURCE_CLOSEOUT_DRIFT")
    rows = materialisation.get("rows", {})
    if rows.get("C2_VNEXT") != base.EXPECTED_C2_ROWS or rows.get("C2E_V0_2") != base.EXPECTED_C2E_ROWS:
        raise base.PreflightError("RS0_R3_SOURCE_ROW_COUNT_DRIFT")
    artifact = closeout.get("artifact", {})
    if artifact.get("github_actions_artifact_id") != 9283576949 or artifact.get("github_actions_artifact_digest") != base.SOURCE_ARTIFACT_DIGEST:
        raise base.PreflightError("RS0_R3_SOURCE_ARTIFACT_DRIFT")

    capacity = authority.get("capacity", {})
    expected_capacity = {
        "peak_memory_limit_bytes": base.MEMORY_LIMIT,
        "external_storage_limit_bytes": base.STORAGE_LIMIT,
        "concurrency_limit": base.CONCURRENCY_LIMIT,
        "checkpoint_cadence_assertions": base.CHECKPOINT_CADENCE,
        "capacity_exceeded": "FAIL_CLOSED_RETURN_TO_OPERATOR",
        "reduced_precision": "FORBIDDEN",
        "population_change": "FORBIDDEN",
        "objectpack_change": "FORBIDDEN",
    }
    if capacity != expected_capacity:
        raise base.PreflightError("RS0_R3_CAPACITY_ENVELOPE_DRIFT")

    external = base.load_json(repo_root / base.EXTERNAL_ROOT_PATH)
    rs0_root = external.get("rs0_run_root", {})
    if rs0_root.get("folder_id") != authority.get("external_artifact_root", {}).get("folder_id") or rs0_root.get("binding_status") != "EXACT_BOUND":
        raise base.PreflightError("RS0_R3_EXTERNAL_ARTIFACT_ROOT_DRIFT")

    return {
        "authority_id": AUTHORITY_ID,
        "candidate_ids": [row["candidate_id"] for row in sorted(specs, key=lambda item: item["candidate_id"])],
        "capacity": capacity,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "adapter_binding_logical_sha256": ADAPTER_BINDING_SHA,
        "adapter_id": SOURCE_ORDER_ADAPTER_ID,
        "source_materialisation_id": base.SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": base.SOURCE_MATERIALISATION_SHA,
        "external_artifact_root": authority.get("external_artifact_root"),
    }


def merged_c2_rows(source_plan: dict[str, Any]) -> Iterable[dict[str, Any]]:
    root = Path(source_plan["source_root"])
    factories = []
    for source in source_plan["c2_sources"]:
        path = root / source["relative_path"]
        factories.append(lambda path=path: base.iter_verified_rows(path, expected_role="C2_VNEXT"))
    yield from merge_source_factories_with_kind_segmentation(factories)


def candidate_child(repo_root: Path, source_plan_path: Path, candidate_id: str, output_dir: Path) -> int:
    code = ORIGINAL_CANDIDATE_CHILD(repo_root, source_plan_path, candidate_id, output_dir)
    old_path = output_dir / f"{candidate_id}.r2-summary.json"
    new_path = output_dir / f"{candidate_id}.r3-summary.json"
    if old_path.exists():
        summary = base.load_json(old_path)
        summary["schema"] = "ovc-c2p2-rs0-real-source-candidate-r3-summary/v1"
        summary["run_generation"] = "R3"
        base.write_json(new_path, summary)
        old_path.unlink()
    return code


def preflight(repo_root: Path, source_root: Path, output_dir: Path) -> int:
    bindings = validate_repo_bindings(repo_root)
    source_plan = base.validate_source_artifact(source_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    base.write_json(output_dir / "source-plan-r3.json", source_plan)
    base.write_json(output_dir / "preflight-r3.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r3-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "bindings": bindings,
        "source_plan": source_plan,
        "semantic_execution_started": False,
        "authority_consumed": False,
        "source_order_adapter_id": SOURCE_ORDER_ADAPTER_ID,
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
    base.write_json(output_dir / "run-r3-start-receipt.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r3-start/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "single_use_authority_consumed_on_semantic_launch": True,
        "started_at": started_at,
        "github_run_id": github_run_id,
        "candidate_generation_id": base.GENERATION_ID,
        "runtime_binding_id": base.RUNTIME_BINDING_ID,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "adapter_id": SOURCE_ORDER_ADAPTER_ID,
        "source_materialisation_id": base.SOURCE_MATERIALISATION_ID,
        "source_plan": source_plan,
        "capacity": bindings["capacity"],
        "selection_state": "NONE_SELECTED",
        "activation_state": "NONE",
    })

    summaries: list[dict[str, Any]] = []
    failure_class: str | None = None
    for candidate_id in bindings["candidate_ids"]:
        command = [
            sys.executable,
            str(Path(base.__file__).resolve()),
            "candidate-child",
            "--repo-root", str(repo_root),
            "--source-plan", str(source_plan_path),
            "--candidate-id", candidate_id,
            "--output-dir", str(output_dir),
        ]
        completed = subprocess.run(command, check=False)
        summary = base.load_json(output_dir / f"{candidate_id}.r3-summary.json")
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
                "schema": "ovc-c2p2-rs0-real-source-candidate-r3-summary/v1",
                "candidate_id": candidate_id,
                "candidate_logical_hash": base.CANDIDATE_HASHES[candidate_id],
                "status": "NOT_RUN_FAIL_CLOSED_AFTER_PRIOR_CANDIDATE_FAILURE",
                "selection_state": "NONE_SELECTED",
                "activation_state": "NONE",
            })

    completed_all = all(row.get("status") == "COMPLETED_SHADOW_UNSELECTED" for row in summaries)
    status = "COMPLETED_COMPARATIVE_SET_NO_WINNER" if completed_all else (
        "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED" if failure_class == "CAPACITY_EXCEEDED" else "BLOCKED_EXECUTION_FAILURE_SINGLE_USE_CONSUMED"
    )
    gate_id = "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" if completed_all else "C2P2-RS0-RUN-RECOVERY-R3"
    result = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r3-result/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": status,
        "started_at": started_at,
        "completed_at": base.utc_now(),
        "github_run_id": github_run_id,
        "authority": {
            "authority_id": AUTHORITY_ID,
            "execution_count_limit": 1,
            "execution_count_consumed": 1,
            "run_count_remaining": 0,
            "single_use_consumed_even_on_post_launch_failure": True,
        },
        "candidate_generation": {
            "generation_id": base.GENERATION_ID,
            "generation_logical_sha256": base.GENERATION_SHA,
            "candidate_logical_hashes": base.CANDIDATE_HASHES,
        },
        "runtime_binding": {
            "binding_id": base.RUNTIME_BINDING_ID,
            "logical_sha256": base.RUNTIME_BINDING_SHA,
            "implementation_sha256": base.RUNTIME_IMPLEMENTATION_SHA,
        },
        "execution_adapter": {
            "binding_id": ADAPTER_BINDING_ID,
            "binding_logical_sha256": ADAPTER_BINDING_SHA,
            "adapter_id": SOURCE_ORDER_ADAPTER_ID,
            "implementation_sha256": ADAPTER_IMPLEMENTATION_SHA,
            "base_spooled_adapter_id": BASE_SPOOLED_ADAPTER_ID,
            "base_spooled_adapter_implementation_sha256": BASE_SPOOLED_IMPLEMENTATION_SHA,
        },
        "source_materialisation": {
            "materialisation_id": base.SOURCE_MATERIALISATION_ID,
            "logical_sha256": base.SOURCE_MATERIALISATION_SHA,
            "locator_logical_sha256": base.SOURCE_LOCATOR_LOGICAL_SHA,
            "artifact_digest": base.SOURCE_ARTIFACT_DIGEST,
            "c2_rows": base.EXPECTED_C2_ROWS,
            "c2e_rows": base.EXPECTED_C2E_ROWS,
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
        "next_operator_gate": gate_id,
        "rollback": "PRESERVE_ALL_R3_RUN_AND_PARTIAL_EVIDENCE_FORWARD_SUPERSESSION_ONLY",
    }
    result_path = output_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R3_RESULT_v0_1.json"
    base.write_json(result_path, result)

    release_dir = repo_root / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    release_result_path = release_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R3_RESULT_v0_1.json"
    base.write_json(release_result_path, result)
    result_sha = base.sha256_file(release_result_path)

    base.write_json(repo_root / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_3.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-consumption/v3",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "operator_decision_ref": str(DECISION_PATH),
        "execution_count_limit": 1,
        "execution_count_consumed": 1,
        "run_count_remaining": 0,
        "consumption_status": "CONSUMED_BY_LAUNCHED_REAL_SOURCE_EXECUTION_R3",
        "run_result_status": status,
        "run_result_sha256": result_sha,
        "github_run_id": github_run_id,
        "candidate_generation_id": base.GENERATION_ID,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "rollback": "CONSUMPTION_IS_APPEND_ONLY_NO_TOKEN_REINSTATEMENT_WITHOUT_NEW_OPERATOR_AUTHORITY",
    })

    base.write_json(repo_root / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_2.json", {
        "schema": "ovc-c2p2-rs0-execution-state/v2",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": "GATE_READY" if completed_all else "BLOCKED",
        "branch": "run/c2p2-rs0-real-source-shadow-r3-20260817",
        "authority_required": "OPERATOR_REQUIRED_AT_NEXT_GATE",
        "authority_id": AUTHORITY_ID,
        "run_authority_consumed": True,
        "run_count_remaining": 0,
        "run_result_ref": str(release_result_path).replace(str(repo_root) + os.sep, ""),
        "run_result_sha256": result_sha,
        "adapter_binding_ref": str(ADAPTER_BINDING_PATH),
        "adapter_binding_logical_sha256": ADAPTER_BINDING_SHA,
        "blockers": [] if completed_all else [status],
        "mandatory_stop": gate_id,
        "next_packet": None,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "f0_a": "HOLD_UNCHANGED",
        "validation": "LOCKED_UNCONSUMED",
        "rollback": "PRESERVE_PRIOR_R2_RECOVERY_AND_R3_EVIDENCE_FORWARD_SUPERSEDE_ONLY",
    })

    gate = {
        "schema": "ovc-c2p2-rs0-post-run-r3-gate-packet/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": gate_id,
        "gate_classification": "OPERATOR_REQUIRED",
        "status": "GATE_READY",
        "current_authority": "R3_SINGLE_USE_CONSUMED_NO_SELECTION_NO_ACTIVATION",
        "run_status": status,
        "run_result_sha256": result_sha,
        "candidate_results": summaries,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "f0_a": "HOLD",
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "warnings": [
            "Whole-population candidate streams were source-order recovered under the qualified v0.2 adapter, hashed and reduced to deterministic scientific-review aggregates; ephemeral SQLite spools were deleted after each completed candidate to remain inside the frozen external-storage envelope."
        ],
        "unresolved_issues": [] if completed_all else ["R3 comparative run did not complete; no scientific selection is permitted."],
        "rollback": "FORWARD_ONLY_PRESERVE_R3_AUTHORITY_CONSUMPTION_AND_ALL_COMPACT_RUN_EVIDENCE",
        "recommended_decision": "REVIEW_COMPARATIVE_EVIDENCE_NO_AUTOMATIC_SELECTION" if completed_all else "BLOCK",
        "exact_work_after_approval": "Operator scientific review may select, defer, block or quarantine an ObjectPack candidate only at this gate; no activation follows automatically." if completed_all else "Authorise a separately bounded recovery generation before any further real-source execution.",
    }
    base.write_json(release_dir / "C2P2_RS0_POST_RUN_R3_GATE_PACKET_v0_1.json", gate)
    return 0 if completed_all else 75


base.validate_repo_bindings = validate_repo_bindings
base.merged_c2_rows = merged_c2_rows
base.candidate_child = candidate_child
base.preflight = preflight
base.execute = execute


if __name__ == "__main__":
    raise SystemExit(base.main())
