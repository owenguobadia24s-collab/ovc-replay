from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/opt_b/c2/c2_prospective_evidence_record_v0_1.schema.json"
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
EXPECTED_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
EXPECTED_MANIFEST = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1"
EXPECTED_MANIFEST_SHA = "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33"
RESEARCH_LINE = "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1"


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def deterministic_record_id(record: dict[str, Any]) -> str:
    material = "|".join(
        [
            str(record["research_line_id"]),
            str(record["record_class"]),
            str(record["canonical_clock"]),
            str(record["price_side"]),
            str(record["observation_start_utc"]),
            str(record["observation_end_utc"]),
            ",".join(sorted(record["source_object_ids"])),
        ]
    )
    return "C2EV-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
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
    missing = sorted(required - record.keys())
    if missing:
        return [f"missing required fields: {', '.join(missing)}"]

    if record["schema"] != "ovc-c2-prospective-evidence-record/v0.1":
        errors.append("unexpected schema")
    if record["research_line_id"] != RESEARCH_LINE:
        errors.append("unexpected research line")
    if record["record_class"] not in ALLOWED_CLASSES:
        errors.append("record class is not admissible")
    if record["evidence_status"] not in ALLOWED_STATUSES:
        errors.append("evidence status is not admissible")
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
    if record["prospective"] is not True:
        errors.append("record must be prospective")
    if not isinstance(record["source_object_ids"], list) or not record["source_object_ids"]:
        errors.append("source_object_ids must be a non-empty list")
    if record["record_id"] != deterministic_record_id(record):
        errors.append("record_id is not deterministic")

    try:
        start = _parse_utc(record["observation_start_utc"])
        end = _parse_utc(record["observation_end_utc"])
        created = _parse_utc(record["created_at_utc"])
        if end < start:
            errors.append("observation interval is reversed")
        if created < end:
            errors.append("record creation precedes observation completion")
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid timestamp: {exc}")

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
    counts["total"] = 0
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
    return counts


def main() -> int:
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert baseline["state"] == "ZERO_COUNT_PROSPECTIVE_BASELINE"
    assert baseline["counts"]["total"] == 0
    assert baseline["historical_backfill"] == 0
    assert baseline["validation_consumed"] is False
    print("PASS_C2_WP7_PROSPECTIVE_EVIDENCE_CONTRACT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
