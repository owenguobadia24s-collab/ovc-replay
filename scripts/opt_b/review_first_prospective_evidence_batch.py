#!/usr/bin/env python3
"""Review the first real C2 prospective evidence batch without fabricating records."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.opt_b.validate_c2_wp7_prospective_evidence import (  # noqa: E402
    deterministic_record_id,
    validate_record as validate_contract_record,
)

APPEND_TARGET = Path("evidence/research/opt-b-c2-v2/prospective/c2_evidence_records.jsonl")
RESEARCH_LINE = "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1"
ACTIVE_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
ACTIVE_MANIFEST = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1"
ACTIVE_MANIFEST_SHA256 = "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33"
PROHIBITED_CONTEXT_MARKERS = {
    "OLD_202_STORY_PROGRAMME",
    "OLD_58_CANDIDATE_PROGRAMME",
    "B_STATE_0_3B",
    "C2E_EPISODE",
    "C2_5_EVENT",
    "C3_MEANING",
    "HISTORICAL_OPT_C",
    "HISTORICAL_OPT_D",
}


def validate_record(record: dict[str, Any], line_number: int) -> list[str]:
    errors = [f"line {line_number}: {error}" for error in validate_contract_record(record)]

    context = record.get("context_references", [])
    if isinstance(context, list):
        joined = "\n".join(str(value) for value in context)
        for marker in PROHIBITED_CONTEXT_MARKERS:
            if marker in joined:
                errors.append(f"line {line_number}: prohibited seed marker {marker}")

    return errors


def _empty_result(state: str, sha256: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "decision": "DEFER_NO_REAL_PROSPECTIVE_BATCH",
        "append_target": str(APPEND_TARGET),
        "append_target_state": state,
        "record_count": 0,
        "live_prospective_count": 0,
        "operation_mode_counts": {},
        "errors": [],
    }
    if sha256 is not None:
        result["sha256"] = sha256
    return result


def review(root: Path) -> tuple[dict[str, Any], int]:
    target = root / APPEND_TARGET
    if not target.exists():
        return _empty_result("ABSENT"), 0

    payload = target.read_bytes()
    payload_sha = hashlib.sha256(payload).hexdigest()
    if not payload.strip():
        return _empty_result("EMPTY", payload_sha), 0

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(payload.decode("utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: malformed JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number}: row must be a JSON object")
            continue
        records.append(value)
        errors.extend(validate_record(value, line_number))

    ids = [record.get("record_id") for record in records if isinstance(record.get("record_id"), str)]
    duplicate_ids = sorted(record_id for record_id, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate active record IDs: {duplicate_ids}")

    mode_counts = Counter(record.get("operation_mode") for record in records)
    live_records = [record for record in records if record.get("operation_mode") == "LIVE_PROSPECTIVE"]

    if errors:
        decision = "BLOCK_BATCH_INTEGRITY_FAILURE"
    elif not live_records:
        decision = "DEFER_NO_REAL_PROSPECTIVE_BATCH"
    else:
        decision = "PASS_FIRST_BATCH_ACCEPTED"

    result: dict[str, Any] = {
        "decision": decision,
        "append_target": str(APPEND_TARGET),
        "append_target_state": "PRESENT",
        "record_count": len(records),
        "live_prospective_count": len(live_records),
        "sha256": payload_sha,
        "record_ids": ids,
        "live_prospective_record_ids": [record["record_id"] for record in live_records],
        "class_counts": dict(Counter(record.get("record_class") for record in records)),
        "operation_mode_counts": {str(key): value for key, value in mode_counts.items()},
        "sequence_boundary_friction_count": sum(
            1
            for record in live_records
            if record.get("sequence_boundary_friction") is True
        ),
        "errors": errors,
    }

    if live_records:
        result["market_time_range"] = {
            "first_market_window_start_utc": min(
                str(record["market_window_start_utc"]) for record in live_records
            ),
            "last_market_window_end_utc": max(
                str(record["market_window_end_utc"]) for record in live_records
            ),
            "first_trigger_first_valid_at": min(
                str(record["trigger_first_valid_at"]) for record in live_records
            ),
            "last_trigger_first_valid_at": max(
                str(record["trigger_first_valid_at"]) for record in live_records
            ),
            "first_review_created_at_utc": min(
                str(record["review_created_at_utc"]) for record in live_records
            ),
            "last_review_created_at_utc": max(
                str(record["review_created_at_utc"]) for record in live_records
            ),
        }

    return result, 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result, exit_code = review(args.root.resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
