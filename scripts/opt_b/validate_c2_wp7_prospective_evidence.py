from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/opt_b/c2/c2_prospective_evidence_record_v0_2.schema.json"
BASELINE_PATH = ROOT / "fixtures/opt_b/c2/wp7/C2_PROSPECTIVE_EVIDENCE_ZERO_BASELINE.json"

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
OPERATION_MODES = {
    "LIVE_PROSPECTIVE",
    "TIME_GATED_REPLAY",
    "NON_EVIDENTIARY_REPLAY",
}
EXPECTED_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
EXPECTED_MANIFEST = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1"
EXPECTED_MANIFEST_SHA = "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33"
RESEARCH_LINE = "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1"
C2_G6_OPENED_AT = datetime(2026, 7, 26, 19, 29, 21, tzinfo=timezone.utc)
C2_G7_ACCEPTED_AT = datetime(2026, 7, 26, 19, 49, 46, tzinfo=timezone.utc)

REQUIRED_FIELDS = {
    "schema",
    "record_id",
    "research_line_id",
    "record_class",
    "evidence_status",
    "instrument",
    "canonical_clock",
    "price_side",
    "market_window_start_utc",
    "market_window_end_utc",
    "trigger_first_valid_at",
    "review_created_at_utc",
    "operation_mode",
    "author",
    "active_release_id",
    "active_manifest_id",
    "active_manifest_sha256",
    "source_object_ids",
    "summary",
}
OPTIONAL_FIELDS = {
    "context_references",
    "sequence_boundary_friction",
    "c2e_authority",
    "probability_authority",
    "exposure_authority",
    "trading_authority",
    "execution_authority",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def deterministic_record_id(record: dict[str, Any]) -> str:
    material = "|".join(
        [
            str(record["research_line_id"]),
            str(record["record_class"]),
            str(record["canonical_clock"]),
            str(record["price_side"]),
            str(record["operation_mode"]),
            str(record["market_window_start_utc"]),
            str(record["market_window_end_utc"]),
            str(record["trigger_first_valid_at"]),
            ",".join(sorted(record["source_object_ids"])),
        ]
    )
    return "C2EV-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        return [f"missing required fields: {', '.join(missing)}"]

    unexpected = sorted(record.keys() - ALLOWED_FIELDS)
    if unexpected:
        errors.append(f"unexpected fields: {', '.join(unexpected)}")

    if record["schema"] != "ovc-c2-prospective-evidence-record/v0.2":
        errors.append("unexpected schema")
    if record["research_line_id"] != RESEARCH_LINE:
        errors.append("unexpected research line")
    if record["record_class"] not in ALLOWED_CLASSES:
        errors.append("record class is not admissible")
    if record["evidence_status"] not in ALLOWED_STATUSES:
        errors.append("evidence status is not admissible")
    if record["operation_mode"] not in OPERATION_MODES:
        errors.append("operation mode is not admissible")
    if record["instrument"] != "GBPUSD":
        errors.append("instrument must be GBPUSD")
    if record["canonical_clock"] not in {"15M", "2H_A_L"}:
        errors.append("canonical clock is not admissible")
    if record["price_side"] not in {"BID", "ASK"}:
        errors.append("price side is not admissible")
    if record["active_release_id"] != EXPECTED_RELEASE:
        errors.append("record is not bound to the active C2 Discovery release")
    if record["active_manifest_id"] != EXPECTED_MANIFEST:
        errors.append("record is not bound to the active manifest")
    if record["active_manifest_sha256"] != EXPECTED_MANIFEST_SHA:
        errors.append("active manifest hash mismatch")

    source_ids = record["source_object_ids"]
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or len(source_ids) != len(set(source_ids))
        or any(not isinstance(value, str) or not value.strip() for value in source_ids)
    ):
        errors.append("source_object_ids must be a non-empty unique list of strings")

    if not isinstance(record["author"], str) or not record["author"].strip():
        errors.append("author must be non-empty")
    if not isinstance(record["summary"], str) or not record["summary"].strip():
        errors.append("summary must be non-empty")

    if record["record_id"] != deterministic_record_id(record):
        errors.append("record_id is not deterministic")

    try:
        start = _parse_utc(record["market_window_start_utc"])
        end = _parse_utc(record["market_window_end_utc"])
        trigger = _parse_utc(record["trigger_first_valid_at"])
        review_created = _parse_utc(record["review_created_at_utc"])

        if end <= start:
            errors.append("market window is not increasing")
        if trigger < start or trigger > end:
            errors.append("trigger_first_valid_at is outside the market window")
        if review_created < end:
            errors.append("review creation precedes market-window completion")
        if review_created <= C2_G7_ACCEPTED_AT:
            errors.append("review creation is not after C2-G7 acceptance")

        if record["operation_mode"] == "LIVE_PROSPECTIVE":
            if start <= C2_G6_OPENED_AT or end <= C2_G6_OPENED_AT or trigger <= C2_G6_OPENED_AT:
                errors.append("LIVE_PROSPECTIVE timestamps are not strictly after C2-G6 opening")
        elif record["operation_mode"] == "NON_EVIDENTIARY_REPLAY":
            if record.get("sequence_boundary_friction") is True:
                errors.append("NON_EVIDENTIARY_REPLAY cannot carry sequence-boundary-friction weight")
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid timestamp: {exc}")

    context = record.get("context_references", [])
    if not isinstance(context, list):
        errors.append("context_references must be a list")

    for field in (
        "c2e_authority",
        "probability_authority",
        "exposure_authority",
        "trading_authority",
        "execution_authority",
    ):
        if record.get(field, "NONE") != "NONE":
            errors.append(f"{field} must remain NONE")

    return errors


def validate_jsonl(path: Path) -> dict[str, int]:
    seen: set[str] = set()
    counts = {name: 0 for name in sorted(ALLOWED_CLASSES)}
    counts.update(
        {
            "total": 0,
            "live_prospective": 0,
            "time_gated_replay": 0,
            "non_evidentiary_replay": 0,
            "prospective_evidence": 0,
        }
    )
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            record = json.loads(raw)
            errors = validate_record(record)
            if errors:
                raise ValueError(f"line {line_number}: {'; '.join(errors)}")
            if record["record_id"] in seen:
                raise ValueError(f"line {line_number}: duplicate active record_id")
            seen.add(record["record_id"])
            counts[record["record_class"]] += 1
            counts["total"] += 1
            mode_key = record["operation_mode"].lower()
            counts[mode_key] += 1
            if record["operation_mode"] == "LIVE_PROSPECTIVE":
                counts["prospective_evidence"] += 1
    return counts


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["operation_mode"]["enum"] == [
        "LIVE_PROSPECTIVE",
        "TIME_GATED_REPLAY",
        "NON_EVIDENTIARY_REPLAY",
    ]
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert baseline["state"] == "ZERO_COUNT_PROSPECTIVE_BASELINE"
    assert baseline["counts"]["total"] == 0
    assert baseline["historical_backfill"] == 0
    assert baseline["validation_consumed"] is False
    print("PASS_C2_WP7_PROSPECTIVE_EVIDENCE_CONTRACT_V0_2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
