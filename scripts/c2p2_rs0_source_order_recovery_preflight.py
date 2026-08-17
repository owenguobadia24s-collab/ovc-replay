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
    C2_SOURCE_KIND_ORDER,
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return {
        "relative_path": source.relative_path,
        "source_sha256": source.sha256,
        "expected_rows": source.row_count,
        **inspection,
    }


def global_merge_receipt(
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

    expected_counts: Counter[tuple[str, str]] = Counter()
    for inspection in source_inspections:
        side = next(iter(inspection["rows_by_side"]))
        for source_kind, count in inspection["rows_by_kind"].items():
            expected_counts[(side, source_kind)] += int(count)

    factories = [stream_factory(source_root, source) for source in sources]
    merged = merge_source_factories_with_kind_segmentation(factories)
    previous_key: tuple[str, str] | None = None
    order_sha = hashlib.sha256()
    observed_counts: Counter[tuple[str, str]] = Counter()
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
            side = str(row.get("side") or "")
            observed_counts[(side, source_kind)] += 1
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
    if rows != EXPECTED_C2_ROWS:
        raise RuntimeError(f"RS0_SOURCE_ORDER_GLOBAL_ROW_COUNT_DRIFT:{rows}")
    if observed_counts != expected_counts:
        raise RuntimeError(
            "RS0_SOURCE_ORDER_ROW_PARTITION_PRESERVATION_FAIL:"
            f"expected={dict(expected_counts)}:observed={dict(observed_counts)}"
        )

    return {
        "rows": rows,
        "unique_source_record_ids": rows,
        "strict_global_order": True,
        "global_order_sha256": order_sha.hexdigest(),
        "identity_index_bytes": database_bytes,
        "expected_side_kind_counts": {
            f"{side}|{kind}": count
            for (side, kind), count in sorted(expected_counts.items())
        },
        "observed_side_kind_counts": {
            f"{side}|{kind}": count
            for (side, kind), count in sorted(observed_counts.items())
        },
        "row_partition_preserved": True,
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
    global_receipt = global_merge_receipt(
        source_root,
        c2_sources,
        source_inspections,
        args.work_dir,
    )

    peak = peak_rss_bytes()
    if peak > MEMORY_LIMIT:
        raise SystemExit("RS0_SOURCE_ORDER_PREFLIGHT_MEMORY_LIMIT_EXCEEDED")

    receipt = {
        "schema": "ovc-c2p2-rs0-source-order-recovery-current-source-preflight/v2",
        "programme_id": "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1",
        "packet_id": "C2P2-RS0-SOURCE-ORDER-RECOVERY",
        "status": "PASS",
        "source_order_adapter_id": SOURCE_ORDER_ADAPTER_ID,
        "source_materialisation_id": SOURCE_MATERIALISATION_ID,
        "source_materialisation_logical_sha256": SOURCE_MATERIALISATION_SHA,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_locator_path": str(locator_path),
        "source_locator_file_sha256": SOURCE_LOCATOR_FILE_SHA,
        "source_locator_logical_sha256": SOURCE_LOCATOR_LOGICAL_SHA,
        "source_envelope": {
            "producer_ref": "src/ovc/opt_b/c2p_v0_2/rs0_source_materialisation.py::_write_streaming_c2_source",
            "documented_physical_layout": [
                "C2_LEVEL segment",
                "C2_CONTAINER segment",
                "C2_PARENT_OBSERVATION segment",
            ],
            "interpretation": "PHYSICAL_FILE_ENVELOPE_CONTAINS_THREE_LOGICAL_MONOTONE_SOURCE_KIND_STREAMS",
            "source_inspections": source_inspections,
            "boundary_time_decreases_are_segment_resets_only": True,
            "within_logical_stream_time_decreases": 0,
        },
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
        "scientific_effect": "NONE_SOURCE_ENVELOPE_SEQUENCING_ONLY",
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
