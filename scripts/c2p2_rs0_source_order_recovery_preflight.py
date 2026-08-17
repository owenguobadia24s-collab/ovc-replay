#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
from typing import Any, Iterable, Mapping

from ovc.opt_b.c2p_v0_2.rs0_execution import iter_verified_rows, validate_locator
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    SOURCE_ORDER_ADAPTER_ID,
    canonicalize_equal_time_groups,
    merge_source_streams_with_tie_canonicalization,
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
MODULUS = 1 << 256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_row_bytes(row: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(row),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class MultisetSignature:
    def __init__(self) -> None:
        self.count = 0
        self.xor = 0
        self.sum = 0

    def update(self, row: Mapping[str, Any]) -> None:
        value = int.from_bytes(hashlib.sha256(canonical_row_bytes(row)).digest(), "big")
        self.count += 1
        self.xor ^= value
        self.sum = (self.sum + value) % MODULUS

    def value(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "xor_sha256_int": f"{self.xor:064x}",
            "sum_sha256_int_mod_2_256": f"{self.sum:064x}",
        }


class InputObserver:
    def __init__(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self.rows = rows
        self.signature = MultisetSignature()
        self.tie_inversions = 0
        self.max_equal_time_group = 0
        self._current_time: str | None = None
        self._current_group = 0
        self._previous_time: str | None = None
        self._previous_source_id: str | None = None

    def __iter__(self):
        for row in self.rows:
            material = normalize_candidate_source_row(row)
            first_valid_time = str(material["first_valid_time"])
            source_record_id = str(material["source_record_id"])
            if self._previous_time is not None and first_valid_time < self._previous_time:
                raise RuntimeError("RS0_SOURCE_ORDER_PREFLIGHT_DECREASING_FIRST_VALID_TIME")
            if first_valid_time != self._current_time:
                self._current_time = first_valid_time
                self._current_group = 0
            self._current_group += 1
            self.max_equal_time_group = max(self.max_equal_time_group, self._current_group)
            if (
                self._previous_time == first_valid_time
                and self._previous_source_id is not None
                and source_record_id <= self._previous_source_id
            ):
                self.tie_inversions += 1
            self._previous_time = first_valid_time
            self._previous_source_id = source_record_id
            self.signature.update(row)
            yield row


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


def verify_stream(
    source_root: Path,
    source: Any,
) -> dict[str, Any]:
    observer = InputObserver(
        iter_verified_rows(
            source_root / source.relative_path,
            expected_role="C2_VNEXT",
        )
    )
    output_signature = MultisetSignature()
    output_count = 0
    previous_key: tuple[str, str] | None = None
    order_sha = hashlib.sha256()

    for row in canonicalize_equal_time_groups(observer):
        material = normalize_candidate_source_row(row)
        key = (str(material["first_valid_time"]), str(material["source_record_id"]))
        if previous_key is not None and key <= previous_key:
            raise RuntimeError("RS0_SOURCE_ORDER_RECOVERED_STREAM_NOT_STRICTLY_CANONICAL")
        previous_key = key
        output_signature.update(row)
        output_count += 1
        order_sha.update(f"{key[0]}\x1f{key[1]}\n".encode("utf-8"))

    if observer.signature.value() != output_signature.value():
        raise RuntimeError("RS0_SOURCE_ORDER_ROW_IDENTITY_MUTATION_OR_LOSS")
    if output_count != source.row_count:
        raise RuntimeError("RS0_SOURCE_ORDER_STREAM_ROW_COUNT_DRIFT")

    return {
        "relative_path": source.relative_path,
        "expected_rows": source.row_count,
        "input_rows": observer.signature.count,
        "output_rows": output_count,
        "tie_inversions_detected": observer.tie_inversions,
        "max_equal_time_group_rows": observer.max_equal_time_group,
        "row_multiset_signature": observer.signature.value(),
        "recovered_order_sha256": order_sha.hexdigest(),
        "row_identity_preserved": True,
        "strict_canonical_output": True,
    }


def global_merge_receipt(source_root: Path, sources: list[Any], work_dir: Path) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "source-order-preflight.sqlite3"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("CREATE TABLE source_ids(source_record_id TEXT PRIMARY KEY)")

    streams = [
        iter_verified_rows(
            source_root / source.relative_path,
            expected_role="C2_VNEXT",
        )
        for source in sources
    ]
    merged = merge_source_streams_with_tie_canonicalization(streams)
    previous_key: tuple[str, str] | None = None
    order_sha = hashlib.sha256()
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

    return {
        "rows": rows,
        "unique_source_record_ids": rows,
        "strict_global_order": True,
        "global_order_sha256": order_sha.hexdigest(),
        "identity_index_bytes": database_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

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

    stream_receipts = [
        verify_stream(source_root, source)
        for source in sorted(c2_sources, key=lambda item: item.relative_path)
    ]
    if sum(item["tie_inversions_detected"] for item in stream_receipts) <= 0:
        raise SystemExit("RS0_SOURCE_ORDER_EXPECTED_EQUAL_TIME_INVERSION_NOT_OBSERVED")

    global_receipt = global_merge_receipt(source_root, c2_sources, args.work_dir)
    peak = peak_rss_bytes()
    if peak > MEMORY_LIMIT:
        raise SystemExit("RS0_SOURCE_ORDER_PREFLIGHT_MEMORY_LIMIT_EXCEEDED")

    receipt = {
        "schema": "ovc-c2p2-rs0-source-order-recovery-current-source-preflight/v1",
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
        "scientific_effect": "NONE_ORDERING_ONLY",
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
