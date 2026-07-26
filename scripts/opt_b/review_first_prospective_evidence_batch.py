#!/usr/bin/env python3
"""Review the first real C2 prospective evidence batch without fabricating records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

APPEND_TARGET = Path("evidence/research/opt-b-c2-v2/prospective/c2_evidence_records.jsonl")
RESEARCH_LINE = "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1"
ACTIVE_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
ACTIVE_MANIFEST = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1"
ACTIVE_MANIFEST_SHA256 = "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33"
ALLOWED_CLASSES = {
    "STATE_FIDELITY_REVIEW",
    "BOUNDARY_CONFLICT_CASE",
    "ANOMALY",
    "INCIDENT",
    "BOUNDED_RESEARCH_QUESTION",
}
ALLOWED_STATUSES = {
    "OBSERVED_UNREVIEWED",
    "REVIEWED_ACCEPTED",
    "REVIEWED_REJECTED",
    "DUPLICATE_SUPERSEDED",
    "INCIDENT_BLOCKED",
}
REQUIRED = {
    "schema",
    "record_id",
    "research_line_id",
    "record_class",
    "evidence_status",
    "instrument",
    "canonical_clock",
    "price_side",
    "observation_start_utc",
    "observation_end_utc",
    "created_at_utc",
    "author",
    "active_release_id",
    "active_manifest_id",
    "active_manifest_sha256",
    "source_object_ids",
    "summary",
    "prospective",
}
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


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def validate_record(record: dict[str, Any], line_number: int) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED.difference(record))
    if missing:
        errors.append(f"line {line_number}: missing required fields {missing}")
        return errors

    exact = {
        "schema": "ovc-c2-prospective-evidence-record/v0.1",
        "research_line_id": RESEARCH_LINE,
        "instrument": "GBPUSD",
        "active_release_id": ACTIVE_RELEASE,
        "active_manifest_id": ACTIVE_MANIFEST,
        "active_manifest_sha256": ACTIVE_MANIFEST_SHA256,
        "prospective": True,
    }
    for key, expected in exact.items():
        if record.get(key) != expected:
            errors.append(f"line {line_number}: {key} does not match the frozen contract")

    record_id = record.get("record_id")
    if not isinstance(record_id, str) or len(record_id) != 21 or not record_id.startswith("C2EV-"):
        errors.append(f"line {line_number}: invalid record_id")
    elif any(ch not in "0123456789ABCDEF" for ch in record_id[5:]):
        errors.append(f"line {line_number}: record_id suffix must be uppercase hexadecimal")

    if record.get("record_class") not in ALLOWED_CLASSES:
        errors.append(f"line {line_number}: unknown record_class")
    if record.get("evidence_status") not in ALLOWED_STATUSES:
        errors.append(f"line {line_number}: unknown evidence_status")
    if record.get("canonical_clock") not in {"15M", "2H_A_L"}:
        errors.append(f"line {line_number}: invalid canonical_clock")
    if record.get("price_side") not in {"BID", "ASK"}:
        errors.append(f"line {line_number}: invalid price_side")

    source_ids = record.get("source_object_ids")
    if not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids)):
        errors.append(f"line {line_number}: source_object_ids must be a non-empty unique list")

    if not isinstance(record.get("author"), str) or not record["author"].strip():
        errors.append(f"line {line_number}: author must be non-empty")
    if not isinstance(record.get("summary"), str) or not record["summary"].strip():
        errors.append(f"line {line_number}: summary must be non-empty")

    try:
        start = parse_utc(record.get("observation_start_utc"))
        end = parse_utc(record.get("observation_end_utc"))
        created = parse_utc(record.get("created_at_utc"))
        if end <= start:
            errors.append(f"line {line_number}: observation interval is not increasing")
        if created < end:
            errors.append(f"line {line_number}: record was created before observation end")
    except ValueError as exc:
        errors.append(f"line {line_number}: invalid timestamp: {exc}")

    for field in (
        "c2e_authority",
        "probability_authority",
        "exposure_authority",
        "trading_authority",
        "execution_authority",
    ):
        if field in record and record[field] != "NONE":
            errors.append(f"line {line_number}: {field} must remain NONE")

    context = record.get("context_references", [])
    if not isinstance(context, list):
        errors.append(f"line {line_number}: context_references must be a list")
    else:
        joined = "\n".join(str(value) for value in context)
        for marker in PROHIBITED_CONTEXT_MARKERS:
            if marker in joined:
                errors.append(f"line {line_number}: prohibited seed marker {marker}")

    return errors


def review(root: Path) -> tuple[dict[str, Any], int]:
    target = root / APPEND_TARGET
    if not target.exists():
        return {
            "decision": "DEFER_NO_REAL_PROSPECTIVE_BATCH",
            "append_target": str(APPEND_TARGET),
            "append_target_state": "ABSENT",
            "record_count": 0,
            "errors": [],
        }, 0

    payload = target.read_bytes()
    if not payload.strip():
        return {
            "decision": "DEFER_NO_REAL_PROSPECTIVE_BATCH",
            "append_target": str(APPEND_TARGET),
            "append_target_state": "EMPTY",
            "record_count": 0,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "errors": [],
        }, 0

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

    decision = "BLOCK_BATCH_INTEGRITY_FAILURE" if errors else "PASS_FIRST_BATCH_ACCEPTED"
    result = {
        "decision": decision,
        "append_target": str(APPEND_TARGET),
        "append_target_state": "PRESENT",
        "record_count": len(records),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "record_ids": ids,
        "class_counts": dict(Counter(record.get("record_class") for record in records)),
        "sequence_boundary_friction_count": sum(
            1 for record in records if record.get("sequence_boundary_friction") is True
        ),
        "errors": errors,
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
