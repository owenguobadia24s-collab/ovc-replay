from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_ARCHIVE_SHA256 = "fb52ea4f84fa7c1d79c9c524470d6722ab82b09a5ed4d4f0278fda4d330eabfc"
EXPECTED_INVENTORY_SHA256 = "39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383"
EXPECTED_REPLAY_REPORT_SHA256 = "553d814a77f1efe831644ccdb4b8fa625d7f584527ec09f580048f6851862589"
EXPECTED_DETERMINISM_SHA256 = "e71f52fcc5dde73c54b456d09ecc59a804de77ea4ecad44de9a196f0a818fbc9"
EXPECTED_RECORDS = 212_764
EXPECTED_FILES = 192
EXPECTED_BYTES = 36_169_581
EXPECTED_COUNTS = {
    "DEVELOPMENT:15M:ASK": 23_853,
    "DEVELOPMENT:15M:BID": 23_853,
    "DEVELOPMENT:2H_A_L:ASK": 2_583,
    "DEVELOPMENT:2H_A_L:BID": 2_583,
    "DISCOVERY:15M:ASK": 71_982,
    "DISCOVERY:15M:BID": 71_982,
    "DISCOVERY:2H_A_L:ASK": 7_964,
    "DISCOVERY:2H_A_L:BID": 7_964,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256_file(args.archive) != EXPECTED_ARCHIVE_SHA256:
        raise SystemExit("candidate archive hash mismatch")

    inventory_path = args.artifact_root / "WP4_INVENTORY.json"
    report_path = args.artifact_root / "WP4_REPLAY_REPORT.json"
    determinism_path = args.artifact_root / "WP4_DETERMINISM_RECEIPT.json"
    if sha256_file(inventory_path) != EXPECTED_INVENTORY_SHA256:
        raise SystemExit("embedded inventory hash mismatch")
    if sha256_file(report_path) != EXPECTED_REPLAY_REPORT_SHA256:
        raise SystemExit("embedded replay report hash mismatch")
    if sha256_file(determinism_path) != EXPECTED_DETERMINISM_SHA256:
        raise SystemExit("embedded determinism receipt hash mismatch")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    files = inventory["files"]
    if len(files) != EXPECTED_FILES:
        raise SystemExit("candidate file count mismatch")

    seen_paths: set[str] = set()
    seen_record_ids: set[str] = set()
    counts: Counter[str] = Counter()
    verified_bytes = 0

    for item in files:
        relative = item["path"]
        prefix = "wp4-candidate-a/"
        if not relative.startswith(prefix):
            raise SystemExit(f"unexpected inventory prefix: {relative}")
        relative = relative[len(prefix):]
        if relative in seen_paths:
            raise SystemExit(f"duplicate inventory path: {relative}")
        seen_paths.add(relative)
        path = args.artifact_root / relative
        if not path.is_file():
            raise SystemExit(f"missing candidate file: {relative}")
        if path.stat().st_size != item["size_bytes"]:
            raise SystemExit(f"size mismatch: {relative}")
        if sha256_file(path) != item["sha256"]:
            raise SystemExit(f"sha256 mismatch: {relative}")
        verified_bytes += path.stat().st_size

        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                record_id = record["record_id"]
                if record_id in seen_record_ids:
                    raise SystemExit(f"duplicate record_id: {record_id}")
                seen_record_ids.add(record_id)
                key = f'{record["role"]}:{record["clock"]}:{record["price_side"]}'
                counts[key] += 1
                if record["authority_state"] != "CANDIDATE_LOCAL_ONLY":
                    raise SystemExit(f"unexpected record authority: {relative}")
                if record["market_authority"] != "NONE":
                    raise SystemExit(f"unexpected market authority: {relative}")
                if record["release_parent_eligibility"] != "DENIED_PENDING_FREEZE":
                    raise SystemExit(f"unexpected release-parent eligibility: {relative}")

    if verified_bytes != EXPECTED_BYTES:
        raise SystemExit("verified byte total mismatch")
    if len(seen_record_ids) != EXPECTED_RECORDS:
        raise SystemExit("record count mismatch")
    if dict(sorted(counts.items())) != EXPECTED_COUNTS:
        raise SystemExit(f"role/clock/side cardinality mismatch: {dict(counts)}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    determinism = json.loads(determinism_path.read_text(encoding="utf-8"))
    if report["status"] != "LOCAL_CANDIDATE_QA_PASS":
        raise SystemExit("WP4 report is not QA PASS")
    if report["validation_consumption"] != "LOCKED_UNCONSUMED_EXCLUDED":
        raise SystemExit("Validation exclusion not preserved")
    if determinism["status"] != "PASS" or determinism["inventory_match"] is not True:
        raise SystemExit("deterministic rerun receipt failed")

    receipt = {
        "schema": "ovc-opt-b-c1-b1-g1-verification-receipt/v1",
        "gate": "OPT-B.C1.v2.B1-G1",
        "decision_basis": "EXACT_WP4_CANDIDATE_ARCHIVE_AND_COMPLETE_INVENTORY",
        "status": "PASS",
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "inventory_sha256": EXPECTED_INVENTORY_SHA256,
        "verified_file_count": EXPECTED_FILES,
        "verified_payload_bytes": EXPECTED_BYTES,
        "verified_record_count": EXPECTED_RECORDS,
        "unique_record_ids": EXPECTED_RECORDS,
        "duplicate_record_ids": 0,
        "role_clock_side_counts": dict(sorted(counts.items())),
        "wp4_replay_report_sha256": EXPECTED_REPLAY_REPORT_SHA256,
        "wp4_determinism_receipt_sha256": EXPECTED_DETERMINISM_SHA256,
        "validation_consumption": "LOCKED_UNCONSUMED_EXCLUDED",
        "freeze_authority": "AUTHORISED_EXACT_CANDIDATE_ONLY",
        "r2_publication": "DENIED",
        "selector_activation": "NONE",
        "c2_consumption": "DENIED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(receipt))


if __name__ == "__main__":
    main()
