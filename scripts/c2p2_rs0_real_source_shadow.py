#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

from ovc.opt_b.c2p_v0_2.rs0_execution import iter_verified_rows, validate_locator
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import run_empirical_runtime

PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-REAL-SOURCE-SHADOW-RUN"
AUTHORITY_ID = "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.2"
GENERATION_ID = "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
GENERATION_SHA = "c7f0160f7bb8d75b92d4aa95116895c25c44c987e2e78a8352c0e491244bbf1a"
RUNTIME_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1"
RUNTIME_BINDING_SHA = "cc25a6fbe2e9bff7ad58d992bb9e267d0afd4b92bd3c8c32c97fcd5c5a8fd84c"
RUNTIME_IMPLEMENTATION_SHA = "5e096f8693fae0f36f76d344388628dab7a450745a40dad08c71cc24cf656121"
DEPENDENCY_REGISTRY_SHA = "5f77f1f520eedb8a472db6ddf7ae5494fe032e6a155c205aaf9ef5d06f125183"
SOURCE_MATERIALISATION_ID = "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"
SOURCE_MATERIALISATION_SHA = "f7e772ca550fe9b1fb69c45ceca6e55f48da3b9cc02d88bb7b8dd1b74dd6766b"
SOURCE_LOCATOR_LOGICAL_SHA = "c56c756f706da9554878232487bb8887f7b52bcf1d57890fb09d51acf9486977"
SOURCE_LOCATOR_FILE_SHA = "af1f0e180b23543fb27cc3ed9c8cd9a8f201717f020f003468f1a9456dcb4d34"
SOURCE_ARTIFACT_DIGEST = "sha256:482781f5b7921d64219650ff4711027337dbfe677b22415df37708848471976e"
MEMORY_LIMIT = 1_160_593_408
STORAGE_LIMIT = 6_411_935_744
CONCURRENCY_LIMIT = 1
CHECKPOINT_CADENCE = 256
EXPECTED_C2_ROWS = 1_505_072
EXPECTED_C2E_ROWS = 584_520
CANDIDATE_HASHES = {
    "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3": "a8cb003521c62129044a4d62cb9a4d5a967cd3ef9d933fb1090ac4dad0843102",
    "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3": "a91f50c12438c4d5263d36b48e40acc0a5e146b474307721a4108ac2398a752e",
    "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3": "29f8ac9a5844b425901fda90299f911a48a85422a390771753ffd5b894b1c52c",
}

AUTHORITY_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_2.json")
CANDIDATE_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0/C2P2_PS0_OBJECTPACK_CANDIDATES_v0_3.json")
RUNTIME_BINDING_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1.json")
RUNTIME_IMPLEMENTATION_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime.py")
DEPENDENCY_REGISTRY_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
SOURCE_CLOSEOUT_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CURRENT_SOURCE_MATERIALISATION_CLOSEOUT_v0_1.json")
EXTERNAL_ROOT_PATH = Path("registries/implementation/c2p_v0_2/C2P2_RS0_EXTERNAL_ARTIFACT_ROOT_BINDING_v0_1.json")


class PreflightError(RuntimeError):
    pass


class CapacityExceeded(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_repo_bindings(repo_root: Path) -> dict[str, Any]:
    authority = load_json(repo_root / AUTHORITY_PATH)
    if authority.get("authority_id") != AUTHORITY_ID:
        raise PreflightError("RS0_AUTHORITY_ID_DRIFT")
    if authority.get("state") != "AUTHORISED_NOT_STARTED":
        raise PreflightError(f"RS0_AUTHORITY_STATE_NOT_LAUNCHABLE:{authority.get('state')}")
    if authority.get("execution_count_limit") != 1 or authority.get("execution_count_consumed") != 0 or authority.get("run_count_remaining") != 1:
        raise PreflightError("RS0_SINGLE_USE_AUTHORITY_NOT_AVAILABLE")
    if authority.get("run_mode") != "PREREGISTERED_COMPARATIVE_A_B_C_SHADOW_ONLY":
        raise PreflightError("RS0_RUN_MODE_DRIFT")

    generation = authority.get("candidate_generation", {})
    if generation.get("generation_id") != GENERATION_ID or generation.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_CANDIDATE_GENERATION_DRIFT")
    if generation.get("candidate_logical_hashes") != CANDIDATE_HASHES:
        raise PreflightError("RS0_CANDIDATE_HASH_DRIFT")
    if generation.get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER" or generation.get("active_object_pack_id") is not None:
        raise PreflightError("RS0_SELECTION_STATE_DRIFT")

    runtime = authority.get("runtime_binding", {})
    if runtime.get("binding_id") != RUNTIME_BINDING_ID or runtime.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_RUNTIME_BINDING_DRIFT")
    if runtime.get("implementation_sha256") != RUNTIME_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_RUNTIME_IMPLEMENTATION_AUTHORITY_DRIFT")

    source = authority.get("source_materialisation", {})
    if source.get("materialisation_id") != SOURCE_MATERIALISATION_ID or source.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_SOURCE_MATERIALISATION_DRIFT")
    if source.get("locator_logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA or source.get("artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_SOURCE_LOCATOR_OR_ARTIFACT_DRIFT")

    capacity = authority.get("capacity", {})
    if capacity != {
        "peak_memory_limit_bytes": MEMORY_LIMIT,
        "external_storage_limit_bytes": STORAGE_LIMIT,
        "concurrency_limit": CONCURRENCY_LIMIT,
        "checkpoint_cadence_assertions": CHECKPOINT_CADENCE,
        "capacity_exceeded": "FAIL_CLOSED_RETURN_TO_OPERATOR",
        "reduced_precision": "FORBIDDEN",
        "population_change": "FORBIDDEN",
        "objectpack_change": "FORBIDDEN",
    }:
        raise PreflightError("RS0_CAPACITY_ENVELOPE_DRIFT")

    candidates_doc = load_json(repo_root / CANDIDATE_PATH)
    if candidates_doc.get("generation_id") != GENERATION_ID or candidates_doc.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_CANDIDATE_DOCUMENT_GENERATION_DRIFT")
    specs = candidates_doc.get("candidates")
    if not isinstance(specs, list) or len(specs) != 3:
        raise PreflightError("RS0_CANDIDATE_SET_CARDINALITY_INVALID")
    observed_hashes = {spec.get("candidate_id"): spec.get("candidate_logical_hash") for spec in specs}
    if observed_hashes != CANDIDATE_HASHES:
        raise PreflightError("RS0_CANDIDATE_DOCUMENT_HASH_DRIFT")
    if any(spec.get("activation_eligible") is not False for spec in specs):
        raise PreflightError("RS0_CANDIDATE_ACTIVATION_ELIGIBLE_FORBIDDEN")

    binding = load_json(repo_root / RUNTIME_BINDING_PATH)
    if binding.get("binding_id") != RUNTIME_BINDING_ID or binding.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_RUNTIME_BINDING_FILE_DRIFT")
    if binding.get("implementation", {}).get("sha256") != RUNTIME_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_RUNTIME_IMPLEMENTATION_BINDING_DRIFT")
    actual_runtime_sha = sha256_file(repo_root / RUNTIME_IMPLEMENTATION_PATH)
    if actual_runtime_sha != RUNTIME_IMPLEMENTATION_SHA:
        raise PreflightError(f"RS0_RUNTIME_IMPLEMENTATION_BYTES_DRIFT:{actual_runtime_sha}")

    dependency = load_json(repo_root / DEPENDENCY_REGISTRY_PATH)
    if dependency.get("logical_sha256") != DEPENDENCY_REGISTRY_SHA or dependency.get("entries") != []:
        raise PreflightError("RS0_C2E_DEPENDENCY_REGISTRY_DRIFT")

    closeout = load_json(repo_root / SOURCE_CLOSEOUT_PATH)
    materialisation = closeout.get("materialisation", {})
    if materialisation.get("materialisation_id") != SOURCE_MATERIALISATION_ID or materialisation.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_SOURCE_CLOSEOUT_DRIFT")
    rows = materialisation.get("rows", {})
    if rows.get("C2_VNEXT") != EXPECTED_C2_ROWS or rows.get("C2E_V0_2") != EXPECTED_C2E_ROWS:
        raise PreflightError("RS0_SOURCE_ROW_COUNT_DRIFT")
    artifact = closeout.get("artifact", {})
    if artifact.get("github_actions_artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_SOURCE_ARTIFACT_DIGEST_DRIFT")

    external_root = load_json(repo_root / EXTERNAL_ROOT_PATH)
    rs0_root = external_root.get("rs0_run_root", {})
    if rs0_root.get("folder_id") != authority.get("external_artifact_root", {}).get("folder_id") or rs0_root.get("binding_status") != "EXACT_BOUND":
        raise PreflightError("RS0_EXTERNAL_ARTIFACT_ROOT_DRIFT")

    return {
        "authority_id": AUTHORITY_ID,
        "candidate_generation_id": GENERATION_ID,
        "candidate_generation_logical_sha256": GENERATION_SHA,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "runtime_binding_logical_sha256": RUNTIME_BINDING_SHA,
        "runtime_implementation_sha256": actual_runtime_sha,
        "dependency_registry_logical_sha256": DEPENDENCY_REGISTRY_SHA,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "capacity": dict(capacity),
        "external_artifact_root": authority.get("external_artifact_root"),
        "candidate_ids": [spec["candidate_id"] for spec in specs],
    }


def validate_source_artifact(repo_root: Path, source_root: Path) -> dict[str, Any]:
    locator_path = source_root / "rs0-source-locator.json"
    if not locator_path.exists():
        matches = list(source_root.rglob("rs0-source-locator.json"))
        if len(matches) != 1:
            raise PreflightError(f"RS0_SOURCE_LOCATOR_CARDINALITY:{len(matches)}")
        locator_path = matches[0]
        source_root = locator_path.parent
    actual_locator_sha = sha256_file(locator_path)
    if actual_locator_sha != SOURCE_LOCATOR_FILE_SHA:
        raise PreflightError(f"RS0_SOURCE_LOCATOR_BYTES_DRIFT:{actual_locator_sha}")
    locator = load_json(locator_path)
    if locator.get("logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA:
        raise PreflightError("RS0_SOURCE_LOCATOR_LOGICAL_DRIFT")
    sources = validate_locator(locator, source_root)
    c2 = [source for source in sources if source.role == "C2_VNEXT"]
    c2e = [source for source in sources if source.role == "C2E_V0_2"]
    if len(c2) != 2 or len(c2e) != 2:
        raise PreflightError("RS0_SOURCE_ROLE_CARDINALITY_DRIFT")
    if sum(source.row_count for source in c2) != EXPECTED_C2_ROWS or sum(source.row_count for source in c2e) != EXPECTED_C2E_ROWS:
        raise PreflightError("RS0_LOCATOR_ROW_COUNT_DRIFT")
    return {
        "source_root": str(source_root),
        "locator_path": str(locator_path),
        "locator_file_sha256": actual_locator_sha,
        "locator_logical_sha256": locator.get("logical_sha256"),
        "c2_sources": [
            {"relative_path": source.relative_path, "role": source.role, "row_count": source.row_count, "sha256": source.sha256}
            for source in c2
        ],
        "c2e_sources": [
            {"relative_path": source.relative_path, "role": source.role, "row_count": source.row_count, "sha256": source.sha256}
            for source in c2e
        ],
    }


def _row_iter(source_plan: dict[str, Any]) -> Iterable[dict[str, Any]]:
    root = Path(source_plan["source_root"])
    for source in source_plan["c2_sources"]:
        yield from iter_verified_rows(root / source["relative_path"], expected_role="C2_VNEXT")


def _peak_rss_bytes() -> int:
    # Linux ru_maxrss is KiB.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def candidate_child(repo_root: Path, source_plan_path: Path, candidate_id: str, output_dir: Path) -> int:
    summary_path = output_dir / f"{candidate_id}.summary.json"
    result_path = output_dir / f"{candidate_id}.result.json.gz"
    started_at = utc_now()
    try:
        repo_bindings = validate_repo_bindings(repo_root)
        source_plan = load_json(source_plan_path)
        candidates_doc = load_json(repo_root / CANDIDATE_PATH)
        spec = next((row for row in candidates_doc["candidates"] if row["candidate_id"] == candidate_id), None)
        if spec is None:
            raise PreflightError(f"RS0_CANDIDATE_NOT_FOUND:{candidate_id}")
        dependency = load_json(repo_root / DEPENDENCY_REGISTRY_PATH)

        # Apply the frozen physical ceiling immediately before semantic materialisation.
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
        result = run_empirical_runtime(_row_iter(source_plan), spec, dependency)
        if result.get("selection_state") != "UNSELECTED_RESEARCH_CANDIDATE" or result.get("activation_state") != "NONE":
            raise RuntimeError("RS0_RUNTIME_NONAUTHORITY_INVARIANT_FAILED")
        output_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(result_path, "wt", encoding="utf-8", compresslevel=6) as handle:
            json.dump(result, handle, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
        output_bytes = result_path.stat().st_size
        if output_bytes > STORAGE_LIMIT:
            result_path.unlink(missing_ok=True)
            raise CapacityExceeded(f"RS0_EXTERNAL_STORAGE_LIMIT_EXCEEDED:{output_bytes}:{STORAGE_LIMIT}")
        summary = {
            "schema": "ovc-c2p2-rs0-real-source-candidate-run-summary/v1",
            "candidate_id": candidate_id,
            "candidate_logical_hash": CANDIDATE_HASHES[candidate_id],
            "semantic_candidate_id": spec["semantic_candidate_id"],
            "status": "COMPLETED_SHADOW_UNSELECTED",
            "started_at": started_at,
            "completed_at": utc_now(),
            "processed_source_records": len(result["processed_source_record_ids"]),
            "candidate_records": len(result["candidates"]),
            "tracklets": len(result["tracklets"]),
            "object_assertions": len(result["object_assertions"]),
            "match_decisions": len(result["match_decisions"]),
            "evidence_vectors": len(result["evidence_vectors"]),
            "checkpoint_sha256": result["checkpoint_sha256"],
            "result_file": result_path.name,
            "result_file_sha256": sha256_file(result_path),
            "result_file_bytes": output_bytes,
            "peak_rss_bytes": _peak_rss_bytes(),
            "memory_limit_bytes": MEMORY_LIMIT,
            "activation_state": "NONE",
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "runtime_binding_id": repo_bindings["runtime_binding_id"],
        }
        write_json(summary_path, summary)
        return 0
    except (MemoryError, CapacityExceeded) as exc:
        result_path.unlink(missing_ok=True)
        write_json(summary_path, {
            "schema": "ovc-c2p2-rs0-real-source-candidate-run-summary/v1",
            "candidate_id": candidate_id,
            "candidate_logical_hash": CANDIDATE_HASHES.get(candidate_id),
            "status": "CAPACITY_EXCEEDED_FAIL_CLOSED",
            "started_at": started_at,
            "completed_at": utc_now(),
            "reason": type(exc).__name__,
            "detail": str(exc),
            "peak_rss_bytes": _peak_rss_bytes(),
            "memory_limit_bytes": MEMORY_LIMIT,
            "activation_state": "NONE",
            "selection_state": "NONE_SELECTED",
        })
        return 75
    except OSError as exc:
        if exc.errno == 12:
            result_path.unlink(missing_ok=True)
            write_json(summary_path, {
                "schema": "ovc-c2p2-rs0-real-source-candidate-run-summary/v1",
                "candidate_id": candidate_id,
                "candidate_logical_hash": CANDIDATE_HASHES.get(candidate_id),
                "status": "CAPACITY_EXCEEDED_FAIL_CLOSED",
                "started_at": started_at,
                "completed_at": utc_now(),
                "reason": "OS_ENOMEM",
                "detail": str(exc),
                "peak_rss_bytes": _peak_rss_bytes(),
                "memory_limit_bytes": MEMORY_LIMIT,
                "activation_state": "NONE",
                "selection_state": "NONE_SELECTED",
            })
            return 75
        raise
    except BaseException as exc:  # preserve exact failure evidence; parent will fail closed.
        result_path.unlink(missing_ok=True)
        write_json(summary_path, {
            "schema": "ovc-c2p2-rs0-real-source-candidate-run-summary/v1",
            "candidate_id": candidate_id,
            "candidate_logical_hash": CANDIDATE_HASHES.get(candidate_id),
            "status": "EXECUTION_FAILURE_FAIL_CLOSED",
            "started_at": started_at,
            "completed_at": utc_now(),
            "reason": type(exc).__name__,
            "detail": str(exc),
            "peak_rss_bytes": _peak_rss_bytes(),
            "memory_limit_bytes": MEMORY_LIMIT,
            "activation_state": "NONE",
            "selection_state": "NONE_SELECTED",
        })
        return 70


def execute(repo_root: Path, source_plan_path: Path, output_dir: Path, github_run_id: str | None) -> int:
    repo_bindings = validate_repo_bindings(repo_root)
    source_plan = load_json(source_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    start_receipt = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-start/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "single_use_authority_consumed_on_semantic_launch": True,
        "started_at": started_at,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "candidate_generation_logical_sha256": GENERATION_SHA,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "runtime_binding_logical_sha256": RUNTIME_BINDING_SHA,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "source_plan": source_plan,
        "capacity": repo_bindings["capacity"],
        "selection_state": "NONE_SELECTED",
        "activation_state": "NONE",
    }
    write_json(output_dir / "run-start-receipt.json", start_receipt)

    summaries: list[dict[str, Any]] = []
    failure_class: str | None = None
    total_result_bytes = 0
    for candidate_id in repo_bindings["candidate_ids"]:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "candidate-child",
            "--repo-root", str(repo_root),
            "--source-plan", str(source_plan_path),
            "--candidate-id", candidate_id,
            "--output-dir", str(output_dir),
        ]
        completed = subprocess.run(command, check=False)
        summary = load_json(output_dir / f"{candidate_id}.summary.json")
        summaries.append(summary)
        if summary.get("status") == "COMPLETED_SHADOW_UNSELECTED":
            total_result_bytes += int(summary.get("result_file_bytes", 0))
            if total_result_bytes > STORAGE_LIMIT:
                summary["status"] = "CAPACITY_EXCEEDED_FAIL_CLOSED"
                summary["reason"] = "CUMULATIVE_EXTERNAL_STORAGE_LIMIT"
                summary["detail"] = f"{total_result_bytes}>{STORAGE_LIMIT}"
                write_json(output_dir / f"{candidate_id}.summary.json", summary)
                failure_class = "CAPACITY_EXCEEDED"
                break
        else:
            failure_class = "CAPACITY_EXCEEDED" if summary.get("status") == "CAPACITY_EXCEEDED_FAIL_CLOSED" else "EXECUTION_FAILURE"
            break
        if completed.returncode != 0:
            failure_class = "EXECUTION_FAILURE"
            break

    attempted = {row["candidate_id"] for row in summaries}
    for candidate_id in repo_bindings["candidate_ids"]:
        if candidate_id not in attempted:
            summaries.append({
                "schema": "ovc-c2p2-rs0-real-source-candidate-run-summary/v1",
                "candidate_id": candidate_id,
                "candidate_logical_hash": CANDIDATE_HASHES[candidate_id],
                "status": "NOT_RUN_FAIL_CLOSED_AFTER_PRIOR_CANDIDATE_FAILURE",
                "activation_state": "NONE",
                "selection_state": "NONE_SELECTED",
            })

    completed_all = all(row.get("status") == "COMPLETED_SHADOW_UNSELECTED" for row in summaries)
    status = "COMPLETED_COMPARATIVE_SET_NO_WINNER" if completed_all else (
        "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED" if failure_class == "CAPACITY_EXCEEDED" else "BLOCKED_EXECUTION_FAILURE_SINGLE_USE_CONSUMED"
    )
    gate_id = "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" if completed_all else "C2P2-RS0-RUN-RECOVERY"
    result = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-result/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": status,
        "started_at": started_at,
        "completed_at": utc_now(),
        "github_run_id": github_run_id,
        "authority": {
            "authority_id": AUTHORITY_ID,
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
            "implementation_sha256": RUNTIME_IMPLEMENTATION_SHA,
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
        "total_compressed_candidate_result_bytes": total_result_bytes,
        "capacity": repo_bindings["capacity"],
        "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER" if completed_all else "NONE_SELECTED_INCOMPLETE_RUN",
        "preferred_candidate": None,
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "ec1_scientific_effect": "NONE",
        "f0_a": "HOLD_NO_JOINT_LAUNCH",
        "validation": "LOCKED_UNCONSUMED",
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "next_operator_gate": gate_id,
        "rollback": "PRESERVE_ALL_RUN_AND_PARTIAL_EVIDENCE_FORWARD_SUPERSESSION_ONLY",
    }
    result_path = output_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_RESULT_v0_1.json"
    write_json(result_path, result)
    result_sha = sha256_file(result_path)

    release_dir = repo_root / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    write_json(release_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_RESULT_v0_1.json", result)
    write_json(repo_root / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_1.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-consumption/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "operator_decision_ref": "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_OPERATOR_DECISION_v0_1.json",
        "execution_count_limit": 1,
        "execution_count_consumed": 1,
        "run_count_remaining": 0,
        "consumption_status": "CONSUMED_BY_LAUNCHED_REAL_SOURCE_EXECUTION",
        "run_result_status": status,
        "run_result_sha256": result_sha,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "candidate_generation_logical_sha256": GENERATION_SHA,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "rollback": "CONSUMPTION_IS_APPEND_ONLY_NO_TOKEN_REINSTATEMENT_WITHOUT_NEW_OPERATOR_AUTHORITY",
    })
    write_json(repo_root / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_2.json", {
        "schema": "ovc-c2p2-rs0-execution-state/v2",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": "GATE_READY" if completed_all else "BLOCKED",
        "authority_required": "OPERATOR_REQUIRED",
        "authority_delta": "NONE_FROM_RUN; NEXT_GATE_RESERVED",
        "baseline_authority_id": AUTHORITY_ID,
        "run_result": str(Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_RESULT_v0_1.json")),
        "run_result_sha256": result_sha,
        "run_authority_consumed": True,
        "run_count_remaining": 0,
        "blockers": [] if completed_all else [status],
        "mandatory_stop": gate_id,
        "next_packet": None,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "f0_a": "HOLD_UNCHANGED",
        "validation": "LOCKED_UNCONSUMED",
        "rollback": "PRESERVE_RUN_EVIDENCE_FORWARD_SUPERSEDE_ONLY",
    })
    gate_packet = {
        "schema": "ovc-c2p2-rs0-post-run-gate-packet/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": gate_id,
        "gate_classification": "OPERATOR_REQUIRED",
        "status": "GATE_READY",
        "plan_id": "C2P2-RS0-PREPARATION-PLAN-v0.1",
        "baseline_commit": os.environ.get("C2P2_RS0_BASELINE_COMMIT"),
        "candidate_commit": os.environ.get("GITHUB_SHA"),
        "completed_packets": [
            "C2P2-RS0-CURRENT-SOURCE-MATERIALISATION",
            "C2P2-RS0-EMPIRICAL-RUNTIME-CLOSEOUT",
            "C2P2-RS0-FRESH-GRUN",
            PACKET_ID,
        ],
        "current_authority": "ONE_RUN_CONSUMED_NO_SELECTION_NO_ACTIVATION",
        "proposed_delta": (
            "OBJECTPACK_SELECTION_OR_SCIENTIFIC_DISPOSITION_REQUIRES_OPERATOR_DECISION"
            if completed_all else
            "NEW_RECOVERY_OR_RERUN_AUTHORITY_REQUIRED; CURRENT_SINGLE_USE_TOKEN_CONSUMED"
        ),
        "acceptance_conditions": [
            "Preserve immutable final candidate generation v3 and all run/partial evidence.",
            "Do not select or activate an ObjectPack from technical execution alone.",
            "Keep Validation locked and EC1/F0-A unchanged.",
        ],
        "tests": ["TARGETED_EXECUTION_HARNESS_TESTS_REQUIRED", "REPOSITORY_PR_ASSURANCE_REQUIRED"],
        "qa": {
            "recommendation": "PASS_TO_SCIENTIFIC_REVIEW_GATE" if completed_all else "BLOCK_AT_RUN_RECOVERY_GATE",
            "run_status": status,
            "single_use_consumed": True,
        },
        "warnings": [] if completed_all else [status],
        "unresolved_issues": [] if completed_all else [
            "The frozen runtime/capacity envelope did not complete the authorised comparative run.",
            "A rerun is forbidden until a new operator-approved authority generation exists.",
        ],
        "external_artifacts": {
            "bound_drive_folder_id": repo_bindings["external_artifact_root"]["folder_id"],
            "github_actions_run_id": github_run_id,
            "run_result_sha256": result_sha,
        },
        "rollback": "FORWARD_ONLY; preserve authority consumption and all run/partial evidence",
        "recommended_decision": "DEFER" if completed_all else "BLOCK",
        "exact_work_after_approval": (
            "If operator separately authorises scientific review/selection, evaluate A/B/C evidence without automatic activation."
            if completed_all else
            "Authorise a bounded capacity/runtime remediation generation, re-prove reference semantics and capacity, then require a fresh one-run GRUN before any rerun."
        ),
    }
    write_json(release_dir / "C2P2_RS0_POST_RUN_GATE_PACKET_v0_1.json", gate_packet)
    return 0 if completed_all else 2


def preflight(repo_root: Path, source_root: Path, output_dir: Path) -> int:
    repo_bindings = validate_repo_bindings(repo_root)
    source_plan = validate_source_artifact(repo_root, source_root)
    manifest = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-preflight/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": "PASS_READY_TO_CONSUME_SINGLE_USE_AUTHORITY",
        "checked_at": utc_now(),
        "repo_bindings": repo_bindings,
        "source_plan": source_plan,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "runner_os": os.environ.get("RUNNER_OS"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        },
        "authority_consumed": False,
        "selection_state": "NONE_SELECTED",
        "activation_state": "NONE",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "preflight.json", manifest)
    write_json(output_dir / "source-plan.json", source_plan)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate-repo-bindings")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p = sub.add_parser("preflight")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p = sub.add_parser("candidate-child")
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--source-plan", type=Path, required=True)
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p = sub.add_parser("execute")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--source-plan", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate-repo-bindings":
        print(json.dumps(validate_repo_bindings(args.repo_root.resolve()), sort_keys=True))
        return 0
    if args.command == "preflight":
        return preflight(args.repo_root.resolve(), args.source_root.resolve(), args.output_dir.resolve())
    if args.command == "candidate-child":
        return candidate_child(args.repo_root.resolve(), args.source_plan.resolve(), args.candidate_id, args.output_dir.resolve())
    if args.command == "execute":
        return execute(args.repo_root.resolve(), args.source_plan.resolve(), args.output_dir.resolve(), args.github_run_id)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
