from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .index_common import AXES, RO4IndexError, canonical_bytes, logical_hash, sha256_file
from .sequence_common import (
    BANNER,
    CANDIDATE_AUTHORITY,
    COUNT_BANNER,
    DENIED_PD_FIELDS,
    DISTANCE_REGISTRY_ID,
    DIVERSITY_POLICY_ID,
    FORBIDDEN_VOCABULARY,
    OPERATION_MODE,
    SEQUENCE_AUTHORITY,
    SEQUENCE_POLICY_ID,
    SequenceBuildResult,
    declared_distance,
    diversity_audit,
    iter_gzip_jsonl,
    machine_identity,
    peak_rss_bytes,
    signature_core,
    signature_id,
    write_gzip_jsonl,
    write_json,
)
from .sequence_materialize import (
    _candidate_and_control_records,
    _prepare_counts,
    _sig,
    reconstruct_sequence,
)
from .sequence_workspace import connect_workspace, workspace_inventory


from .sequence_finalize_support import (
    _batch_and_answer_key,
    _machine_ablation_assurance,
    _operation_mode_assurance,
    _pd_isolation_assurance,
    _signature_for_sequence,
    _source_partitions,
    _vocabulary_assurance,
)

def finalize_sequence_evidence(
    *,
    index_dir: Path,
    workspace_path: Path,
    output_dir: Path,
    benchmark_path: Path | None = None,
) -> SequenceBuildResult:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_partitions = _source_partitions(index_dir)
    inventory = workspace_inventory(workspace_path)
    built_partitions = {item["partition_id"]: item for item in inventory["partitions"]}
    if set(built_partitions) != set(source_partitions):
        missing = sorted(set(source_partitions) - set(built_partitions))
        extra = sorted(set(built_partitions) - set(source_partitions))
        raise RO4IndexError(f"SEQUENCE_WORKSPACE_PARTITION_SET_MISMATCH:missing={missing}:extra={extra}")
    if inventory["validation_consumption"] != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    if max((item["max_calendar_partition_count"] for item in inventory["partitions"]), default=0) > 100_000:
        raise RO4IndexError("SEQUENCE_WINDOW_CAP_EXCEEDED_WITHOUT_DECLARED_SAMPLE")

    connection = connect_workspace(workspace_path)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    partitions = {
        int(row[0]): {
            "pid": int(row[0]), "partition_id": row[1], "role": row[2], "clock": row[3], "side": row[4],
            "evaluation_scope_id": row[5], "release_id": row[6], "manifest_sha256": row[7],
            "index_file": row[8], "index_file_sha256": row[9],
        }
        for row in connection.execute(
            "SELECT pid,partition_id,role,clock,side,evaluation_scope_id,release_id,manifest_sha256,index_file,index_file_sha256 FROM partitions ORDER BY partition_id"
        )
    }
    _prepare_counts(connection)
    candidate_iter, control_iter, review_pool, diversity_counts, exclusions = _candidate_and_control_records(connection, partitions)
    candidates_path = output_dir / "neutral-recurrence-candidates.jsonl.gz"
    controls_path = output_dir / "real-control-ledger.jsonl.gz"
    candidate_artifact = write_gzip_jsonl(candidates_path, candidate_iter)
    control_artifact = write_gzip_jsonl(controls_path, control_iter)
    if candidate_artifact["record_count"] != control_artifact["record_count"]:
        raise RO4IndexError("CANDIDATE_CONTROL_CARDINALITY_MISMATCH")
    if candidate_artifact["record_count"] == 0:
        raise RO4IndexError("NO_RECURRENCE_CANDIDATES")

    full_diversity = diversity_audit("RO4.G3.FULL.RECURRENCE.POPULATION.v0.1", diversity_counts)
    batch, answer_key, batch_diversity, review_signatures = _batch_and_answer_key(
        index_dir=index_dir, connection=connection, review_pool=review_pool
    )
    answer_path = output_dir / "sealed-answer-key.json"
    answer_artifact = write_json(answer_path, answer_key)
    batch["answer_key_sha256"] = answer_artifact["sha256"]
    batch["logical_hash"] = logical_hash({key: value for key, value in batch.items() if key != "logical_hash"})
    batch_path = output_dir / "blinded-review-batch.json"
    batch_artifact = write_json(batch_path, batch)
    diversity_wrapper = {
        "schema": "ovc-ro4-g3-diversity-audit-set/v1",
        "policy_id": DIVERSITY_POLICY_ID,
        "full_population": full_diversity,
        "operator_batch": batch_diversity,
        "ro4_g4_acknowledgement_required": full_diversity["status"] == "SIGNATURE_CONCENTRATION_WARNING",
    }
    diversity_wrapper["logical_hash"] = logical_hash(diversity_wrapper)
    diversity_path = output_dir / "signature-diversity-audit.json"
    diversity_artifact = write_json(diversity_path, diversity_wrapper)
    signatures_wrapper = {
        "schema": "ovc-ro4-g3-review-signature-set/v1",
        "authority": SEQUENCE_AUTHORITY,
        "records": sorted(review_signatures, key=lambda item: (item["signature_id"], item["sequence_id"])),
    }
    signatures_wrapper["logical_hash"] = logical_hash(signatures_wrapper)
    signature_path = output_dir / "review-sequence-signatures.json"
    signature_artifact = write_json(signature_path, signatures_wrapper)
    machine_assurance = _machine_ablation_assurance(review_signatures)
    machine_path = output_dir / "machine-only-ablation-assurance.json"
    machine_artifact = write_json(machine_path, machine_assurance)
    pd_assurance = _pd_isolation_assurance(batch, candidates_path)
    pd_path = output_dir / "pd-isolation-assurance.json"
    pd_artifact = write_json(pd_path, pd_assurance)
    vocabulary = _vocabulary_assurance([candidates_path, controls_path, batch_path, signature_path])
    vocabulary_path = output_dir / "vocabulary-assurance.json"
    vocabulary_artifact = write_json(vocabulary_path, vocabulary)
    mode_assurance = _operation_mode_assurance()
    mode_path = output_dir / "operation-mode-assurance.json"
    mode_artifact = write_json(mode_path, mode_assurance)
    inventory_path = output_dir / "sequence-population-inventory.json"
    inventory_artifact = write_json(inventory_path, inventory)

    lookup_times: list[float] = []
    lookup_rows = list(connection.execute("SELECT sequence_hash FROM windows ORDER BY sample_hash LIMIT 100"))
    for row in lookup_rows:
        lookup_started = time.perf_counter()
        connection.execute("SELECT pid,start_index,length FROM windows WHERE sequence_hash=?", (row[0],)).fetchone()
        lookup_times.append(time.perf_counter() - lookup_started)
    connection.close()
    checkpoint = sqlite3.connect(workspace_path)
    try:
        checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        checkpoint.close()
    sorted_lookup = sorted(lookup_times)
    lookup_p95 = sorted_lookup[max(0, math.ceil(len(sorted_lookup) * 0.95) - 1)] if sorted_lookup else 0.0

    workspace_artifact = {
        "artifact_type": "sequence_population_workspace",
        "file": workspace_path.name,
        "byte_identity": "LOGICAL_ONLY_REPLACEABLE_SQLITE",
        "size_bytes": workspace_path.stat().st_size,
        "record_count": inventory["window_count"],
        "logical_hash": inventory["logical_hash"],
        "external": True,
    }
    artifacts = [
        {"artifact_type": "candidates", **candidate_artifact, "external": True},
        {"artifact_type": "real_controls", **control_artifact, "external": True},
        {"artifact_type": "blinded_batch", **batch_artifact, "external": True},
        {"artifact_type": "sealed_answer_key", **answer_artifact, "external": True},
        {"artifact_type": "diversity_audit", **diversity_artifact, "external": True},
        {"artifact_type": "review_signatures", **signature_artifact, "external": True},
        {"artifact_type": "machine_ablation_assurance", **machine_artifact, "external": True},
        {"artifact_type": "pd_isolation_assurance", **pd_artifact, "external": True},
        {"artifact_type": "vocabulary_assurance", **vocabulary_artifact, "external": True},
        {"artifact_type": "operation_mode_assurance", **mode_artifact, "external": True},
        {"artifact_type": "population_inventory", **inventory_artifact, "external": True},
        workspace_artifact,
    ]
    manifest_core = {
        "schema": "ovc-ro4-g3-evidence-manifest/v1",
        "authority": CANDIDATE_AUTHORITY,
        "source_g1_logical_hash": inventory["source_g1_logical_hash"],
        "source_g2_logical_hash": "eb5435443be26e956334c4aedd12c2a5280fc815f014f24bd74b064bf4e6eaeb",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "sequence_policy_id": SEQUENCE_POLICY_ID,
        "distance_registry_id": DISTANCE_REGISTRY_ID,
        "sample_state": "FULL_POPULATION_NO_SAMPLING",
        "window_count": inventory["window_count"],
        "recurrence_candidate_count": candidate_artifact["record_count"],
        "recurrence_member_count": sum(diversity_counts),
        "excluded_candidate_groups": exclusions,
        "real_control_count": control_artifact["record_count"],
        "operator_batch_count": len(batch["cards"]),
        "synthetic_controls_operator_facing": 0,
        "pd_population_merge": "DENIED",
        "semantic_authority": "NONE",
        "promotion_path": "DENIED",
        "full_population_diversity_status": full_diversity["status"],
        "ro4_g4_acknowledgement_required": diversity_wrapper["ro4_g4_acknowledgement_required"],
        "non_canonical_banner": BANNER,
        "count_banner": COUNT_BANNER,
        "artifacts": sorted(artifacts, key=lambda item: item["artifact_type"]),
    }
    manifest_core["logical_hash"] = logical_hash(manifest_core)
    manifest_path = output_dir / "g3-manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest_core))

    runtime = time.perf_counter() - started
    benchmark = {
        "benchmark_id": "RO4-G3-FULL-SEQUENCE-EVIDENCE",
        **machine_identity(),
        "runtime_seconds": round(runtime, 6),
        "finalize_runtime_seconds": round(time.perf_counter() - started, 6),
        "peak_rss_bytes": peak_rss_bytes(),
        "workspace_size_bytes": workspace_path.stat().st_size,
        "output_size_bytes": sum(item["size_bytes"] for item in artifacts),
        "window_count": inventory["window_count"],
        "max_calendar_partition_count": max(item["max_calendar_partition_count"] for item in inventory["partitions"]),
        "recurrence_candidate_count": candidate_artifact["record_count"],
        "existing_sequence_lookup_p95_seconds": round(lookup_p95, 9),
        "sample_state": "FULL_POPULATION_NO_SAMPLING",
        "logical_hash": manifest_core["logical_hash"],
        "status": "PASS" if runtime <= 900 and peak_rss_bytes() <= 8 * 1024**3 and lookup_p95 <= 2 else "BLOCK",
    }
    if benchmark["status"] != "PASS":
        raise RO4IndexError("RO4_G3_PERFORMANCE_BOUND_FAILURE")
    if benchmark_path:
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_bytes(canonical_bytes(benchmark))
    return SequenceBuildResult(manifest=manifest_core, benchmark=benchmark)
