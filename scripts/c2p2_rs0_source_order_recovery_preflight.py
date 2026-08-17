#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
from typing import Any

from ovc.opt_b.c2p_v0_2.rs0_execution import iter_verified_rows, validate_locator
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    BASE_CANDIDATE_SOURCE_KINDS,
    C2_SOURCE_KIND_ORDER,
    CONTEXT_ONLY_SOURCE_KINDS,
    SOURCE_ORDER_ADAPTER_ID,
    inspect_source_kind_segments,
    merge_source_factories_with_kind_segmentation,
)
from ovc.opt_b.c2p_v0_2.rs0_empirical_semantics import normalize_candidate_source_row


SOURCE_MATERIALISATION_ID = "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"
SOURCE_MATERIALISATION_SHA = "f7e772ca550fe9b1fb69c45ceca6e55f48da3b9cc02d88bb7b8dd1b74dd6766b"
SOURCE_LOCATOR_LOGICAL_SHA = "c56c756f706da9554878232487bb8887f7b52bcf1d57890fb09d51acf9486977"
SOURCE_LOCATOR_FILE_SHA = "af1f0e180b23543fb27cc3ed9c8cd9a8f201717f020f003468f1a9456dcb4d34"
SOURCE_ARTIFACT_DIGEST = "sha256:482781f5b7921d64219650ff4711027337dbfe677b22415df37708848471976e"
EXPECTED_C2_ROWS = 1_505_072
MEMORY_LIMIT = 1_160_593_408
STORAGE_LIMIT = 6_411_935_744
BINDING_PATH = Path(
    "registries/opt_b/c2p/v0_2/research/"
    "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2.json"
)
MODULE_PATH = Path("src/ovc/opt_b/c2p_v0_2/rs0_empirical_runtime_source_order.py")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def bind_current_adapter_bytes(repo_root: Path) -> dict[str, str]:
    """Bind the pending recovery record to exact head bytes before qualification.

    This is repository bookkeeping only. The qualified logical identity is still
    created later by the workflow after tests/capacity/current-source preflight.
    """

    binding_path = repo_root / BINDING_PATH
    module_path = repo_root / MODULE_PATH
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if binding.get("status") != "IMPLEMENTED_PENDING_QUALIFICATION":
        raise RuntimeError("RS0_SOURCE_ORDER_BINDING_NOT_PENDING_QUALIFICATION")
    recovery = binding.get("source_order_recovery")
    if not isinstance(recovery, dict):
        raise RuntimeError("RS0_SOURCE_ORDER_RECOVERY_BINDING_MISSING")
    if recovery.get("implementation_path") != str(MODULE_PATH):
        raise RuntimeError("RS0_SOURCE_ORDER_IMPLEMENTATION_PATH_DRIFT")
    implementation_sha = sha256_file(module_path)
    recovery["implementation_sha256"] = implementation_sha
    binding["source_order_recovery"] = recovery
    binding.pop("logical_sha256", None)
    prequalification_logical = canonical_hash(binding)
    binding["logical_sha256"] = prequalification_logical
    binding_path.write_text(
        json.dumps(binding, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "implementation_sha256": implementation_sha,
        "prequalification_binding_logical_sha256": prequalification_logical,
    }


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def locate_source_root(source_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    locator_path = source_root / "rs0-source-locator.json"
    if not locator_path.exists():
        matches = list(source_root.rglob("rs0-source-locator.json"))
        if len(matches) != 1:
            raise RuntimeError(f"RS0_SOURCE_ORDER_LOCATOR_CARDINALITY:{len(matches)}")
        locator_path = matches[0]
        source_root = locator_path.parent
    if sha256_file(locator_path) != SOURCE_LOCATOR_FILE_SHA:
        raise RuntimeError("RS0_SOURCE_ORDER_LOCATOR_BYTES_DRIFT")
    locator = json.loads(locator_path.read_text(encoding="utf-8"))
    if locator.get("logical_sha256") != SOURCE_LOCATOR_LOGICAL_SHA:
        raise RuntimeError("RS0_SOURCE_ORDER_LOCATOR_LOGICAL_DRIFT")
    return source_root, locator_path, locator


def stream_factory(source_root: Path, source):
    path = source_root / source.relative_path

    def factory():
        return iter_verified_rows(path, expected_role="C2_VNEXT")

    return factory


def inspect_exact_source_envelope(source_root: Path, source) -> dict[str, Any]:
    inspection = inspect_source_kind_segments(
        iter_verified_rows(
            source_root / source.relative_path,
            expected_role="C2_VNEXT",
        )
    )
    if inspection["raw_rows"] != source.row_count:
        raise RuntimeError("RS0_SOURCE_ORDER_STREAM_ROW_COUNT_DRIFT")
    if inspection["observed_kinds"] != list(C2_SOURCE_KIND_ORDER):
        raise RuntimeError(
            "RS0_SOURCE_ORDER_EXACT_SOURCE_KIND_ENVELOPE_DRIFT:"
            + ",".join(inspection["observed_kinds"])
        )
    expected_transitions = [
        {"from": "C2_LEVEL", "to": "C2_CONTAINER"},
        {"from": "C2_CONTAINER", "to": "C2_PARENT_OBSERVATION"},
    ]
    if inspection["segment_transitions"] != expected_transitions:
        raise RuntimeError("RS0_SOURCE_ORDER_EXACT_SOURCE_SEGMENT_TRANSITION_DRIFT")
    if inspection["within_kind_time_decreases"] != 0:
        raise RuntimeError("RS0_SOURCE_ORDER_WITHIN_KIND_TIME_DECREASE")
    if len(inspection["rows_by_side"]) != 1:
        raise RuntimeError("RS0_SOURCE_ORDER_SOURCE_FILE_SIDE_CARDINALITY_DRIFT")
    if inspection["boundary_time_decreases"] <= 0:
        raise RuntimeError("RS0_SOURCE_ORDER_EXPECTED_SEGMENT_BOUNDARY_RESET_NOT_OBSERVED")
    if inspection["base_candidate_rows"] <= 0 or inspection["context_only_rows"] <= 0:
        raise RuntimeError("RS0_SOURCE_ORDER_EXPECTED_BASE_AND_CONTEXT_PARTITIONS_MISSING")
    return {
        "relative_path": source.relative_path,
        "source_sha256": source.sha256,
        "expected_rows": source.row_count,
        **inspection,
    }


def global_base_candidate_merge_receipt(
    source_root: Path,
    sources: list[Any],
    source_inspections: list[dict[str, Any]],
    work_dir: Path,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "source-order-preflight.sqlite3"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("CREATE TABLE source_ids(source_record_id TEXT PRIMARY KEY)")

    expected_base_counts: Counter[tuple[str, str]] = Counter()
    total_raw_rows = 0
    total_context_rows = 0
    for inspection in source_inspections:
        side = next(iter(inspection["rows_by_side"]))
        total_raw_rows += int(inspection["raw_rows"])
        total_context_rows += int(inspection["context_only_rows"])
        for source_kind in BASE_CANDIDATE_SOURCE_KINDS:
            expected_base_counts[(side, source_kind)] += int(
                inspection["rows_by_kind"][source_kind]
            )

    expected_base_rows = sum(expected_base_counts.values())
    if total_raw_rows != EXPECTED_C2_ROWS:
        raise RuntimeError(f"RS0_SOURCE_ORDER_RAW_POPULATION_DRIFT:{total_raw_rows}")
    if expected_base_rows + total_context_rows != total_raw_rows:
        raise RuntimeError("RS0_SOURCE_ORDER_BASE_CONTEXT_PARTITION_NOT_EXHAUSTIVE")

    factories = [stream_factory(source_root, source) for source in sources]
    merged = merge_source_factories_with_kind_segmentation(factories)
    previous_key: tuple[str, str] | None = None
    order_sha = hashlib.sha256()
    observed_base_counts: Counter[tuple[str, str]] = Counter()
    rows = 0
    try:
        for row in merged:
            material = normalize_candidate_source_row(row)
            source_id = str(material["source_record_id"])
            key = (str(material["first_valid_time"]), source_id)
            if previous_key is not None and key <= previous_key:
                raise RuntimeError("RS0_SOURCE_ORDER_GLOBAL_MERGE_NOT_STRICTLY_CANONICAL")
            try:
                connection.execute(
                    "INSERT INTO source_ids(source_record_id) VALUES (?)",
                    (source_id,),
                )
            except sqlite3.IntegrityError as exc:
                raise RuntimeError(
                    f"RS0_SOURCE_ORDER_DUPLICATE_SOURCE_RECORD:{source_id}"
                ) from exc
            source_kind = str(row.get("source_record_kind") or "")
            if source_kind not in BASE_CANDIDATE_SOURCE_KINDS:
                raise RuntimeError(
                    f"RS0_SOURCE_ORDER_CONTEXT_PROMOTED_TO_BASE_CANDIDATE:{source_kind}"
                )
            side = str(row.get("side") or "")
            observed_base_counts[(side, source_kind)] += 1
            previous_key = key
            order_sha.update(f"{key[0]}\x1f{key[1]}\n".encode("utf-8"))
            rows += 1
            if rows % 4096 == 0:
                connection.commit()
        connection.commit()
    finally:
        connection.close()

    database_bytes = db_path.stat().st_size
    if database_bytes > STORAGE_LIMIT:
        raise RuntimeError("RS0_SOURCE_ORDER_PREFLIGHT_STORAGE_LIMIT_EXCEEDED")
    if rows != expected_base_rows:
        raise RuntimeError(
            f"RS0_SOURCE_ORDER_BASE_CANDIDATE_ROW_COUNT_DRIFT:{rows}!={expected_base_rows}"
        )
    if observed_base_counts != expected_base_counts:
        raise RuntimeError(
            "RS0_SOURCE_ORDER_BASE_PARTITION_PRESERVATION_FAIL:"
            f"expected={dict(expected_base_counts)}:observed={dict(observed_base_counts)}"
        )

    return {
        "rows": rows,
        "raw_source_rows": total_raw_rows,
        "base_candidate_rows": rows,
        "context_only_rows_preserved_outside_base_runtime": total_context_rows,
        "base_plus_context_equals_raw_source_rows": rows + total_context_rows == total_raw_rows,
        "unique_base_source_record_ids": rows,
        "strict_global_base_candidate_order": True,
        "global_base_candidate_order_sha256": order_sha.hexdigest(),
        "identity_index_bytes": database_bytes,
        "expected_side_kind_counts": {
            f"{side}|{kind}": count
            for (side, kind), count in sorted(expected_base_counts.items())
        },
        "observed_side_kind_counts": {
            f"{side}|{kind}": count
            for (side, kind), count in sorted(observed_base_counts.items())
        },
        "base_candidate_partition_preserved": True,
        "context_promotion_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    repo_root = args.repo_root.resolve()
    byte_binding = bind_current_adapter_bytes(repo_root)
    source_root, locator_path, locator = locate_source_root(args.source_root.resolve())
    sources = validate_locator(locator, source_root)
    c2_sources = [source for source in sources if source.role == "C2_VNEXT"]
    if len(c2_sources) != 2:
        raise SystemExit("RS0_SOURCE_ORDER_C2_SOURCE_CARDINALITY_DRIFT")
    if sum(source.row_count for source in c2_sources) != EXPECTED_C2_ROWS:
        raise SystemExit("RS0_SOURCE_ORDER_C2_ROW_COUNT_DRIFT")

    closeout = json.loads(
        (
            repo_root
            / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CURRENT_SOURCE_MATERIALISATION_CLOSEOUT_v0_1.json"
        ).read_text(encoding="utf-8")
    )
    materialisation = closeout["materialisation"]
    if materialisation["materialisation_id"] != SOURCE_MATERIALISATION_ID:
        raise SystemExit("RS0_SOURCE_ORDER_MATERIALISATION_ID_DRIFT")
    if materialisation["logical_sha256"] != SOURCE_MATERIALISATION_SHA:
        raise SystemExit("RS0_SOURCE_ORDER_MATERIALISATION_LOGICAL_DRIFT")
    if closeout["artifact"]["github_actions_artifact_digest"] != SOURCE_ARTIFACT_DIGEST:
        raise SystemExit("RS0_SOURCE_ORDER_ARTIFACT_DIGEST_DRIFT")

    runtime_binding = json.loads(
        (
            repo_root
            / "registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1.json"
        ).read_text(encoding="utf-8")
    )
    if runtime_binding["runtime_contract"]["source_rows"] != "C2_VNEXT_LEVEL_OR_CONTAINER_ONLY":
        raise SystemExit("RS0_SOURCE_ORDER_RUNTIME_BASE_SOURCE_CONTRACT_DRIFT")
    if runtime_binding["runtime_contract"]["stream_order"] != [
        "first_valid_time",
        "source_record_id",
    ]:
        raise SystemExit("RS0_SOURCE_ORDER_RUNTIME_STREAM_ORDER_CONTRACT_DRIFT")

    consumption = json.loads(
        (
            repo_root
            / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_2.json"
        ).read_text(encoding="utf-8")
    )
    if consumption["execution_count_consumed"] != 1 or consumption["run_count_remaining"] != 0:
        raise SystemExit("RS0_SOURCE_ORDER_R2_CONSUMPTION_NOT_PRESERVED")

    decision = json.loads(
        (
            repo_root
            / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_RUN_RECOVERY_R2_OPERATOR_DECISION_v0_1.json"
        ).read_text(encoding="utf-8")
    )
    if decision["decision"] != "PASS":
        raise SystemExit("RS0_SOURCE_ORDER_RECOVERY_NOT_OPERATOR_APPROVED")
    if decision["approved_authority_delta"]["real_source_execution"] != "FORBIDDEN":
        raise SystemExit("RS0_SOURCE_ORDER_REAL_SOURCE_EXECUTION_AUTHORITY_DRIFT")

    source_inspections = [
        inspect_exact_source_envelope(source_root, source)
        for source in sorted(c2_sources, key=lambda item: item.relative_path)
    ]
    global_receipt = global_base_candidate_merge_receipt(
        source_root,
        c2_sources,
        source_inspections,
        args.work_dir,
    )

    peak = peak_rss_bytes()
    if peak > MEMORY_LIMIT:
        raise SystemExit("RS0_SOURCE_ORDER_PREFLIGHT_MEMORY_LIMIT_EXCEEDED")

    stream_receipts = [
        {
            "relative_path": row["relative_path"],
            "expected_rows": row["expected_rows"],
            "base_candidate_rows": row["base_candidate_rows"],
            "context_only_rows": row["context_only_rows"],
            "tie_inversions_detected": sum(
                int(row["equal_time_source_id_inversions_by_kind"][kind])
                for kind in BASE_CANDIDATE_SOURCE_KINDS
            ),
            "source_kind_envelope_status": row["status"],
        }
        for row in source_inspections
    ]

    receipt = {
        "schema": "ovc-c2p2-rs0-source-order-recovery-current-source-preflight/v3",
        "programme_id": "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1",
        "packet_id": "C2P2-RS0-SOURCE-ORDER-RECOVERY",
        "status": "PASS",
        "source_order_adapter_id": SOURCE_ORDER_ADAPTER_ID,
        "source_order_adapter_implementation_sha256": byte_binding["implementation_sha256"],
        "source_order_binding_prequalification_logical_sha256": byte_binding["prequalification_binding_logical_sha256"],
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_locator_path": str(locator_path),
        "source_locator_file_sha256": SOURCE_LOCATOR_FILE_SHA,
        "source_locator_logical_sha256": SOURCE_LOCATOR_LOGICAL_SHA,
        "runtime_source_contract": "C2_VNEXT_LEVEL_OR_CONTAINER_ONLY",
        "base_candidate_kinds": list(BASE_CANDIDATE_SOURCE_KINDS),
        "context_only_kinds": list(CONTEXT_ONLY_SOURCE_KINDS),
        "source_envelope": {
            "producer_ref": "src/ovc/opt_b/c2p_v0_2/rs0_source_materialisation.py::_write_streaming_c2_source",
            "documented_physical_layout": [
                "C2_LEVEL segment",
                "C2_CONTAINER segment",
                "C2_PARENT_OBSERVATION segment",
            ],
            "interpretation": "PHYSICAL_FILE_ENVELOPE_CONTAINS_BASE_CANDIDATE_AND_CONTEXT_ONLY_LOGICAL_SEGMENTS",
            "source_inspections": source_inspections,
            "boundary_time_decreases_are_segment_resets_only": True,
            "within_logical_stream_time_decreases": 0,
        },
        "stream_receipts": stream_receipts,
        "global_merge": global_receipt,
        "memory": {
            "peak_rss_bytes": peak,
            "limit_bytes": MEMORY_LIMIT,
            "headroom_bytes": MEMORY_LIMIT - peak,
        },
        "storage_limit_bytes": STORAGE_LIMIT,
        "semantic_runtime_invoked": False,
        "real_source_semantic_execution": False,
        "run_token_consumed_by_preflight": False,
        "r2_run_count_remaining_preserved": 0,
        "selection_state": "NONE",
        "activation_state": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "f0_a": "HOLD",
        "scientific_effect": "NONE_EXECUTION_ADAPTER_CONFORMANCE_TO_FROZEN_BASE_SOURCE_CONTRACT",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
