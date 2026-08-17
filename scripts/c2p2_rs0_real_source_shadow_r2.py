#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any, Iterable

from ovc.opt_b.c2p_v0_2.rs0_execution import iter_verified_rows, validate_locator
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_streaming import (
    ADAPTER_ID,
    merge_canonical_source_streams,
    run_spooled_empirical_runtime,
)

PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-REAL-SOURCE-SHADOW-RUN-R2"
AUTHORITY_ID = "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.3"
GENERATION_ID = "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
GENERATION_SHA = "c7f0160f7bb8d75b92d4aa95116895c25c44c987e2e78a8352c0e491244bbf1a"
RUNTIME_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1"
RUNTIME_BINDING_SHA = "cc25a6fbe2e9bff7ad58d992bb9e267d0afd4b92bd3c8c32c97fcd5c5a8fd84c"
RUNTIME_IMPLEMENTATION_SHA = "5e096f8693fae0f36f76d344388628dab7a450745a40dad08c71cc24cf656121"
ADAPTER_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_1"
ADAPTER_BINDING_SHA = "43d29861b3a05c5c84676493f94aceb942b7bb530c51dcf6c2687ee11ddbef01"
ADAPTER_IMPLEMENTATION_SHA = "8d3de43abb1b6c80817ca24b6ef301a2bd39dbc3024cc31e92f382b4dfd6b648"
DEPENDENCY_REGISTRY_SHA = "5f77f1f520eedb8a472db6ddf7ae5494fe032e6a155c205aaf9ef5d06f125183"
SOURCE_MATERIALISATION_ID = "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"
SOURCE_MATERIALISATION_SHA = "f7e772ca550fe9b1fb69c45ceca6e55f48da3b9cc02d88bb7b8dd1b74dd6766b"
SOURCE_LOCATOR_LOGICAL_SHA = "c56c756f706da9554878232487bb8887f7b52bcf1d57890fb09d51acf9486977"
SOURCE_LOCATOR_FILE_SHA = "af1f0e180b23543fb27cc3ed9c8cd9a8f201717f020f003468f1a9456dcb4d34"
SOURCE_ARTIFACT_DIGEST = "sha256:482781f5b7921d64219650ff4711027337dbfe677b22415df37708848471976e"
SOURCE_ACTION_RUN_ID = 32010902424
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

AUTHORITY_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_3.json")
PRIOR_CONSUMPTION_PATH = Path("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_1.json")
CANDIDATE_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0/C2P2_PS0_OBJECTPACK_CANDIDATES_v0_3.json")
RUNTIME_BINDING_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1.json")
RUNTIME_IMPLEMENTATION_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime.py")
ADAPTER_BINDING_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_1.json")
ADAPTER_IMPLEMENTATION_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime_streaming.py")
DEPENDENCY_REGISTRY_PATH = Path("registries/opt_b/c2p/v0_2/research/C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
SOURCE_CLOSEOUT_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CURRENT_SOURCE_MATERIALISATION_CLOSEOUT_v0_1.json")
EXTERNAL_ROOT_PATH = Path("registries/implementation/c2p_v0_2/C2P2_RS0_EXTERNAL_ARTIFACT_ROOT_BINDING_v0_1.json")
DECISION_PATH = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_R2_OPERATOR_DECISION_v0_1.json")


class PreflightError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def validate_repo_bindings(repo_root: Path) -> dict[str, Any]:
    authority = load_json(repo_root / AUTHORITY_PATH)
    decision = load_json(repo_root / DECISION_PATH)
    if decision.get("decision") != "PASS" or decision.get("gate_id") != "C2P2-RS0-FRESH-GRUN-R2":
        raise PreflightError("RS0_R2_OPERATOR_DECISION_NOT_PASS")
    if authority.get("authority_id") != AUTHORITY_ID or authority.get("state") != "AUTHORISED_NOT_STARTED":
        raise PreflightError("RS0_R2_AUTHORITY_NOT_LAUNCHABLE")
    if authority.get("execution_count_limit") != 1 or authority.get("execution_count_consumed") != 0 or authority.get("run_count_remaining") != 1:
        raise PreflightError("RS0_R2_SINGLE_USE_AUTHORITY_NOT_AVAILABLE")
    if authority.get("run_mode") != "PREREGISTERED_COMPARATIVE_A_B_C_SHADOW_ONLY":
        raise PreflightError("RS0_R2_RUN_MODE_DRIFT")

    prior = load_json(repo_root / PRIOR_CONSUMPTION_PATH)
    if prior.get("execution_count_consumed") != 1 or prior.get("run_count_remaining") != 0:
        raise PreflightError("RS0_PRIOR_AUTHORITY_CONSUMPTION_NOT_PRESERVED")

    generation = authority.get("candidate_generation", {})
    if generation.get("generation_id") != GENERATION_ID or generation.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_R2_CANDIDATE_GENERATION_DRIFT")
    if generation.get("candidate_logical_hashes") != CANDIDATE_HASHES:
        raise PreflightError("RS0_R2_CANDIDATE_HASH_DRIFT")
    if generation.get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER" or generation.get("active_object_pack_id") is not None:
        raise PreflightError("RS0_R2_SELECTION_STATE_DRIFT")

    runtime = authority.get("runtime_binding", {})
    if runtime.get("binding_id") != RUNTIME_BINDING_ID or runtime.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_R2_CORE_RUNTIME_BINDING_DRIFT")
    if runtime.get("implementation_sha256") != RUNTIME_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_R2_CORE_RUNTIME_AUTHORITY_DRIFT")
    if sha256_file(repo_root / RUNTIME_IMPLEMENTATION_PATH) != RUNTIME_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_R2_CORE_RUNTIME_BYTES_DRIFT")

    adapter = authority.get("execution_adapter", {})
    if adapter.get("binding_id") != ADAPTER_BINDING_ID or adapter.get("binding_logical_sha256") != ADAPTER_BINDING_SHA:
        raise PreflightError("RS0_R2_ADAPTER_BINDING_AUTHORITY_DRIFT")
    if adapter.get("adapter_id") != ADAPTER_ID or adapter.get("implementation_sha256") != ADAPTER_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_R2_ADAPTER_IMPLEMENTATION_AUTHORITY_DRIFT")
    if sha256_file(repo_root / ADAPTER_IMPLEMENTATION_PATH) != ADAPTER_IMPLEMENTATION_SHA:
        raise PreflightError("RS0_R2_ADAPTER_IMPLEMENTATION_BYTES_DRIFT")

    binding = load_json(repo_root / ADAPTER_BINDING_PATH)
    if binding.get("binding_id") != ADAPTER_BINDING_ID or binding.get("logical_sha256") != ADAPTER_BINDING_SHA:
        raise PreflightError("RS0_R2_ADAPTER_BINDING_FILE_DRIFT")
    qualification = binding.get("qualification", {})
    if qualification.get("reference_semantics") != "PASS_EXACT_FIXTURE_EQUIVALENCE_A_B_C" or qualification.get("full_cardinality_synthetic_capacity") != "PASS":
        raise PreflightError("RS0_R2_ADAPTER_NOT_QUALIFIED")

    core_binding = load_json(repo_root / RUNTIME_BINDING_PATH)
    if core_binding.get("binding_id") != RUNTIME_BINDING_ID or core_binding.get("logical_sha256") != RUNTIME_BINDING_SHA:
        raise PreflightError("RS0_R2_CORE_RUNTIME_BINDING_FILE_DRIFT")

    dependency = load_json(repo_root / DEPENDENCY_REGISTRY_PATH)
    if dependency.get("logical_sha256") != DEPENDENCY_REGISTRY_SHA or dependency.get("entries") != []:
        raise PreflightError("RS0_R2_DEPENDENCY_REGISTRY_DRIFT")

    candidates_doc = load_json(repo_root / CANDIDATE_PATH)
    if candidates_doc.get("generation_id") != GENERATION_ID or candidates_doc.get("generation_logical_sha256") != GENERATION_SHA:
        raise PreflightError("RS0_R2_CANDIDATE_DOCUMENT_DRIFT")
    specs = candidates_doc.get("candidates")
    if not isinstance(specs, list) or len(specs) != 3:
        raise PreflightError("RS0_R2_CANDIDATE_SET_CARDINALITY_INVALID")
    observed_hashes = {row.get("candidate_id"): row.get("candidate_logical_hash") for row in specs}
    if observed_hashes != CANDIDATE_HASHES or any(row.get("activation_eligible") is not False for row in specs):
        raise PreflightError("RS0_R2_CANDIDATE_DOCUMENT_HASH_OR_ACTIVATION_DRIFT")

    source = authority.get("source_materialisation", {})
    if source.get("materialisation_id") != SOURCE_MATERIALISATION_ID or source.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_R2_SOURCE_AUTHORITY_DRIFT")
    if source.get("locator_logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA or source.get("artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_R2_SOURCE_LOCATOR_OR_ARTIFACT_AUTHORITY_DRIFT")
    if source.get("github_actions_source_run_id") != SOURCE_ACTION_RUN_ID:
        raise PreflightError("RS0_R2_SOURCE_RUN_ID_DRIFT")

    closeout = load_json(repo_root / SOURCE_CLOSEOUT_PATH)
    materialisation = closeout.get("materialisation", {})
    if materialisation.get("materialisation_id") != SOURCE_MATERIALISATION_ID or materialisation.get("logical_sha256") != SOURCE_MATERIALISATION_SHA:
        raise PreflightError("RS0_R2_SOURCE_CLOSEOUT_DRIFT")
    rows = materialisation.get("rows", {})
    if rows.get("C2_VNEXT") != EXPECTED_C2_ROWS or rows.get("C2E_V0_2") != EXPECTED_C2E_ROWS:
        raise PreflightError("RS0_R2_SOURCE_ROW_COUNT_DRIFT")
    if closeout.get("artifact", {}).get("github_actions_artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise PreflightError("RS0_R2_SOURCE_ARTIFACT_DIGEST_DRIFT")

    capacity = authority.get("capacity", {})
    expected_capacity = {
        "peak_memory_limit_bytes": MEMORY_LIMIT,
        "external_storage_limit_bytes": STORAGE_LIMIT,
        "concurrency_limit": CONCURRENCY_LIMIT,
        "checkpoint_cadence_assertions": CHECKPOINT_CADENCE,
        "capacity_exceeded": "FAIL_CLOSED_RETURN_TO_OPERATOR",
        "reduced_precision": "FORBIDDEN",
        "population_change": "FORBIDDEN",
        "objectpack_change": "FORBIDDEN",
    }
    if capacity != expected_capacity:
        raise PreflightError("RS0_R2_CAPACITY_ENVELOPE_DRIFT")

    external = load_json(repo_root / EXTERNAL_ROOT_PATH)
    rs0_root = external.get("rs0_run_root", {})
    if rs0_root.get("folder_id") != authority.get("external_artifact_root", {}).get("folder_id") or rs0_root.get("binding_status") != "EXACT_BOUND":
        raise PreflightError("RS0_R2_EXTERNAL_ARTIFACT_ROOT_DRIFT")

    return {
        "authority_id": AUTHORITY_ID,
        "candidate_ids": [row["candidate_id"] for row in sorted(specs, key=lambda item: item["candidate_id"])],
        "capacity": capacity,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "adapter_binding_logical_sha256": ADAPTER_BINDING_SHA,
        "adapter_id": ADAPTER_ID,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "external_artifact_root": authority.get("external_artifact_root"),
    }


def validate_source_artifact(source_root: Path) -> dict[str, Any]:
    locator_path = source_root / "rs0-source-locator.json"
    if not locator_path.exists():
        matches = list(source_root.rglob("rs0-source-locator.json"))
        if len(matches) != 1:
            raise PreflightError(f"RS0_R2_SOURCE_LOCATOR_CARDINALITY:{len(matches)}")
        locator_path = matches[0]
        source_root = locator_path.parent
    actual_sha = sha256_file(locator_path)
    if actual_sha != SOURCE_LOCATOR_FILE_SHA:
        raise PreflightError(f"RS0_R2_SOURCE_LOCATOR_BYTES_DRIFT:{actual_sha}")
    locator = load_json(locator_path)
    if locator.get("logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA:
        raise PreflightError("RS0_R2_SOURCE_LOCATOR_LOGICAL_DRIFT")
    sources = validate_locator(locator, source_root)
    c2 = [source for source in sources if source.role == "C2_VNEXT"]
    c2e = [source for source in sources if source.role == "C2E_V0_2"]
    if len(c2) != 2 or len(c2e) != 2:
        raise PreflightError("RS0_R2_SOURCE_ROLE_CARDINALITY_DRIFT")
    if sum(source.row_count for source in c2) != EXPECTED_C2_ROWS or sum(source.row_count for source in c2e) != EXPECTED_C2E_ROWS:
        raise PreflightError("RS0_R2_LOCATOR_ROW_COUNT_DRIFT")
    return {
        "source_root": str(source_root),
        "locator_path": str(locator_path),
        "locator_file_sha256": actual_sha,
        "locator_logical_sha256": SOURCE_LOCATOR_LOGICAL_SHA,
        "c2_sources": [
            {"relative_path": row.relative_path, "role": row.role, "row_count": row.row_count, "sha256": row.sha256}
            for row in c2
        ],
        "c2e_sources": [
            {"relative_path": row.relative_path, "role": row.role, "row_count": row.row_count, "sha256": row.sha256}
            for row in c2e
        ],
    }


def merged_c2_rows(source_plan: dict[str, Any]) -> Iterable[dict[str, Any]]:
    root = Path(source_plan["source_root"])
    streams = [
        iter_verified_rows(root / source["relative_path"], expected_role="C2_VNEXT")
        for source in source_plan["c2_sources"]
    ]
    yield from merge_canonical_source_streams(streams)


def _stream_json_values(connection: sqlite3.Connection, table: str, column: str = "value_json") -> Iterable[dict[str, Any]]:
    for (value_json,) in connection.execute(f"SELECT {column} FROM {table}"):
        yield json.loads(value_json)


def compact_scientific_summary(database_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    connection = sqlite3.connect(database_path)
    try:
        decision_counts: Counter[str] = Counter()
        for value in _stream_json_values(connection, "decisions"):
            decision_counts[str(value.get("terminal_decision"))] += 1

        tracklet_states: Counter[str] = Counter()
        for value in _stream_json_values(connection, "tracklets"):
            tracklet_states[str(value.get("state"))] += 1

        assertion_observations: list[int] = []
        for value in _stream_json_values(connection, "assertions"):
            assertion_observations.append(int(value.get("observation_count", 0)))

        evidence_support: Counter[str] = Counter()
        c2e_disposition: Counter[str] = Counter()
        predicate_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
        for value in _stream_json_values(connection, "evidence_vectors"):
            evidence_support["SUPPORTED" if value.get("same_object_pair_supported") else "UNSUPPORTED"] += 1
            c2e_disposition[str(value.get("c2e_dependency_disposition"))] += 1
            predicates = value.get("predicate_results")
            if isinstance(predicates, dict):
                for key, outcome in predicates.items():
                    predicate_outcomes[str(key)][json.dumps(outcome, sort_keys=True)] += 1
            elif isinstance(predicates, list):
                for item in predicates:
                    if isinstance(item, dict):
                        key = item.get("predicate_id") or item.get("predicate") or item.get("name") or "UNNAMED"
                        outcome = item.get("result") if "result" in item else item
                        predicate_outcomes[str(key)][json.dumps(outcome, sort_keys=True)] += 1

        if assertion_observations:
            assertion_stats = {
                "count": len(assertion_observations),
                "observation_count_min": min(assertion_observations),
                "observation_count_max": max(assertion_observations),
                "observation_count_sum": sum(assertion_observations),
                "observation_count_mean": sum(assertion_observations) / len(assertion_observations),
            }
        else:
            assertion_stats = {
                "count": 0,
                "observation_count_min": None,
                "observation_count_max": None,
                "observation_count_sum": 0,
                "observation_count_mean": None,
            }

        return {
            "counts": manifest["counts"],
            "decision_terminal_counts": dict(sorted(decision_counts.items())),
            "tracklet_state_counts": dict(sorted(tracklet_states.items())),
            "assertion_observation_stats": assertion_stats,
            "evidence_same_object_support_counts": dict(sorted(evidence_support.items())),
            "c2e_dependency_disposition_counts": dict(sorted(c2e_disposition.items())),
            "predicate_outcome_counts": {
                key: dict(sorted(counter.items())) for key, counter in sorted(predicate_outcomes.items())
            },
            "stream_sha256": manifest["stream_sha256"],
            "indexes_sha256": manifest["indexes_sha256"],
            "adapter_result_sha256": manifest["adapter_result_sha256"],
        }
    finally:
        connection.close()


def candidate_child(repo_root: Path, source_plan_path: Path, candidate_id: str, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{candidate_id}.r2-summary.json"
    work_dir = output_dir / f"{candidate_id}.spool-work"
    started_at = utc_now()
    started_perf = time.perf_counter()
    try:
        bindings = validate_repo_bindings(repo_root)
        source_plan = load_json(source_plan_path)
        candidates_doc = load_json(repo_root / CANDIDATE_PATH)
        spec = next((row for row in candidates_doc["candidates"] if row["candidate_id"] == candidate_id), None)
        if spec is None:
            raise PreflightError(f"RS0_R2_CANDIDATE_NOT_FOUND:{candidate_id}")
        dependency = load_json(repo_root / DEPENDENCY_REGISTRY_PATH)
        if work_dir.exists():
            shutil.rmtree(work_dir)
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
        manifest = run_spooled_empirical_runtime(
            merged_c2_rows(source_plan),
            spec,
            dependency,
            work_dir=work_dir,
            checkpoint_cadence=CHECKPOINT_CADENCE,
            export_streams=False,
            storage_limit_bytes=STORAGE_LIMIT,
        )
        database_path = work_dir / manifest["database_file"]
        database_bytes = database_path.stat().st_size
        if database_bytes > STORAGE_LIMIT:
            raise RuntimeError(f"RS0_R2_STORAGE_LIMIT_EXCEEDED:{database_bytes}>{STORAGE_LIMIT}")
        compact = compact_scientific_summary(database_path, manifest)
        summary = {
            "schema": "ovc-c2p2-rs0-real-source-candidate-r2-summary/v1",
            "candidate_id": candidate_id,
            "candidate_logical_hash": CANDIDATE_HASHES[candidate_id],
            "semantic_candidate_id": spec["semantic_candidate_id"],
            "status": "COMPLETED_SHADOW_UNSELECTED",
            "started_at": started_at,
            "completed_at": utc_now(),
            "wall_seconds": time.perf_counter() - started_perf,
            "peak_rss_bytes": peak_rss_bytes(),
            "memory_limit_bytes": MEMORY_LIMIT,
            "spool_database_bytes": database_bytes,
            "storage_limit_bytes": STORAGE_LIMIT,
            "runtime_binding_id": RUNTIME_BINDING_ID,
            "adapter_binding_id": bindings["adapter_binding_id"],
            "adapter_id": bindings["adapter_id"],
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "activation_state": "NONE",
            "scientific_summary": compact,
            "ephemeral_spool_disposition": "DELETED_AFTER_WHOLE_POPULATION_HASH_AND_AGGREGATE_MATERIALISATION",
        }
        write_json(summary_path, summary)
        shutil.rmtree(work_dir)
        return 0
    except BaseException as exc:
        database_bytes = 0
        if work_dir.exists():
            db_path = work_dir / "runtime-spool.sqlite3"
            if db_path.exists():
                database_bytes = db_path.stat().st_size
        write_json(summary_path, {
            "schema": "ovc-c2p2-rs0-real-source-candidate-r2-summary/v1",
            "candidate_id": candidate_id,
            "candidate_logical_hash": CANDIDATE_HASHES.get(candidate_id),
            "status": "EXECUTION_FAILURE_FAIL_CLOSED",
            "started_at": started_at,
            "completed_at": utc_now(),
            "wall_seconds": time.perf_counter() - started_perf,
            "reason": type(exc).__name__,
            "detail": str(exc),
            "peak_rss_bytes": peak_rss_bytes(),
            "memory_limit_bytes": MEMORY_LIMIT,
            "partial_spool_database_bytes": database_bytes,
            "storage_limit_bytes": STORAGE_LIMIT,
            "selection_state": "NONE_SELECTED",
            "activation_state": "NONE",
            "partial_spool_disposition": "DELETED_AFTER_FAILURE_RECEIPT_TO_RESPECT_STORAGE_ENVELOPE",
        })
        if work_dir.exists():
            shutil.rmtree(work_dir)
        return 75 if isinstance(exc, (MemoryError, OSError)) or "STORAGE_LIMIT" in str(exc) else 70


def execute(repo_root: Path, source_plan_path: Path, output_dir: Path, github_run_id: str | None) -> int:
    bindings = validate_repo_bindings(repo_root)
    source_plan = load_json(source_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    write_json(output_dir / "run-r2-start-receipt.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r2-start/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "single_use_authority_consumed_on_semantic_launch": True,
        "started_at": started_at,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "adapter_id": ADAPTER_ID,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
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
            str(Path(__file__).resolve()),
            "candidate-child",
            "--repo-root", str(repo_root),
            "--source-plan", str(source_plan_path),
            "--candidate-id", candidate_id,
            "--output-dir", str(output_dir),
        ]
        completed = subprocess.run(command, check=False)
        summary = load_json(output_dir / f"{candidate_id}.r2-summary.json")
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
                "schema": "ovc-c2p2-rs0-real-source-candidate-r2-summary/v1",
                "candidate_id": candidate_id,
                "candidate_logical_hash": CANDIDATE_HASHES[candidate_id],
                "status": "NOT_RUN_FAIL_CLOSED_AFTER_PRIOR_CANDIDATE_FAILURE",
                "selection_state": "NONE_SELECTED",
                "activation_state": "NONE",
            })

    completed_all = all(row.get("status") == "COMPLETED_SHADOW_UNSELECTED" for row in summaries)
    status = "COMPLETED_COMPARATIVE_SET_NO_WINNER" if completed_all else (
        "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED" if failure_class == "CAPACITY_EXCEEDED" else "BLOCKED_EXECUTION_FAILURE_SINGLE_USE_CONSUMED"
    )
    gate_id = "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" if completed_all else "C2P2-RS0-RUN-RECOVERY-R2"
    result = {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r2-result/v1",
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
        "execution_adapter": {
            "binding_id": ADAPTER_BINDING_ID,
            "binding_logical_sha256": ADAPTER_BINDING_SHA,
            "adapter_id": ADAPTER_ID,
            "implementation_sha256": ADAPTER_IMPLEMENTATION_SHA,
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
        "next_operator_gate": gate_id,
        "rollback": "PRESERVE_ALL_R2_RUN_AND_PARTIAL_EVIDENCE_FORWARD_SUPERSESSION_ONLY",
    }
    result_path = output_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R2_RESULT_v0_1.json"
    write_json(result_path, result)
    result_sha = sha256_file(result_path)

    release_dir = repo_root / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    write_json(release_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R2_RESULT_v0_1.json", result)
    write_json(repo_root / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_2.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-consumption/v2",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "operator_decision_ref": str(DECISION_PATH),
        "execution_count_limit": 1,
        "execution_count_consumed": 1,
        "run_count_remaining": 0,
        "consumption_status": "CONSUMED_BY_LAUNCHED_REAL_SOURCE_EXECUTION_R2",
        "run_result_status": status,
        "run_result_sha256": result_sha,
        "github_run_id": github_run_id,
        "candidate_generation_id": GENERATION_ID,
        "adapter_binding_id": ADAPTER_BINDING_ID,
        "selection_state": result["selection_state"],
        "active_object_pack_id": None,
        "rollback": "CONSUMPTION_IS_APPEND_ONLY_NO_TOKEN_REINSTATEMENT_WITHOUT_NEW_OPERATOR_AUTHORITY",
    })
    write_json(repo_root / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_2.json", {
        "schema": "ovc-c2p2-rs0-execution-state/v2",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "status": "GATE_READY" if completed_all else "BLOCKED",
        "branch": "run/c2p2-rs0-real-source-shadow-r2-20260817",
        "authority_required": "OPERATOR_REQUIRED_AT_NEXT_GATE",
        "authority_id": AUTHORITY_ID,
        "run_authority_consumed": True,
        "run_count_remaining": 0,
        "run_result_ref": str(release_dir / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R2_RESULT_v0_1.json").replace(str(repo_root) + os.sep, ""),
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
        "rollback": "PRESERVE_PRIOR_FAILED_RUN_RECOVERY_AND_R2_EVIDENCE_FORWARD_SUPERSEDE_ONLY",
    })
    gate = {
        "schema": "ovc-c2p2-rs0-post-run-r2-gate-packet/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "gate_id": gate_id,
        "gate_classification": "OPERATOR_REQUIRED",
        "status": "GATE_READY",
        "current_authority": "R2_SINGLE_USE_CONSUMED_NO_SELECTION_NO_ACTIVATION",
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
            "Whole-population candidate streams were hashed and reduced to deterministic scientific-review aggregates; ephemeral SQLite spools were deleted after each completed candidate to remain inside the frozen external-storage envelope."
        ],
        "unresolved_issues": [] if completed_all else ["R2 comparative run did not complete; no scientific selection is permitted."],
        "rollback": "FORWARD_ONLY_PRESERVE_R2_AUTHORITY_CONSUMPTION_AND_ALL_COMPACT_RUN_EVIDENCE",
        "recommended_decision": "REVIEW_COMPARATIVE_EVIDENCE_NO_AUTOMATIC_SELECTION" if completed_all else "BLOCK",
        "exact_work_after_approval": "Operator scientific review may select, defer, block or quarantine an ObjectPack candidate only at this gate; no activation follows automatically." if completed_all else "Authorise a separately bounded recovery generation before any further real-source execution.",
    }
    write_json(release_dir / "C2P2_RS0_POST_RUN_R2_GATE_PACKET_v0_1.json", gate)
    return 0 if completed_all else 75


def preflight(repo_root: Path, source_root: Path, output_dir: Path) -> int:
    bindings = validate_repo_bindings(repo_root)
    source_plan = validate_source_artifact(source_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "source-plan-r2.json", source_plan)
    write_json(output_dir / "preflight-r2.json", {
        "schema": "ovc-c2p2-rs0-real-source-shadow-run-r2-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "bindings": bindings,
        "source_plan": source_plan,
        "semantic_execution_started": False,
        "authority_consumed": False,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "github_actions": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
        },
    })
    return 0


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
        print(f"C2P2_RS0_R2_PREFLIGHT_ERROR={exc}", file=sys.stderr)
        return 64
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
