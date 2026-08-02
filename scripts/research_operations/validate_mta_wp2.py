from __future__ import annotations

import copy
import json
from pathlib import Path

from ovc.research_operations.mta.source_c1_audit import (
    SourceC1AuditError,
    audit_stream,
    validate_reference,
)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "docs/releases/market-translation-audit-v0-2/mta-g2/MTA_WP2_EXTERNAL_AUDIT_REFERENCE.json"
FIXTURE = "fixtures/research_operations/mta/MTA_WP2_SOURCE_C1_FIXTURE_v0_1.json"


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(relative)
    return value


def expect_error(action, marker: str) -> None:
    try:
        action()
    except SourceC1AuditError as exc:
        assert marker in str(exc), (marker, str(exc))
    else:
        raise AssertionError(f"expected SourceC1AuditError containing {marker}")


def main() -> int:
    required = [
        "contracts/research_operations/mta/OVC_MTA_OPT_A_C1_TRANSLATION_AUDIT_CONTRACT_v0_1.md",
        "schemas/research_operations/mta/mta_source_c1_audit_v0_1.schema.json",
        REFERENCE,
        FIXTURE,
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, missing

    reference = load(REFERENCE)
    result = validate_reference(reference)
    assert result["status"] == "PASS"
    assert result["audited_derived_records_total"] == 10178
    assert result["external_artifact_sha256"] == "3fe01f18feb95179a192232a64b7497adb53b0e9247f1473a8175fe6c83e2e44"

    fixture = load(FIXTURE)
    stream = audit_stream(fixture["bars"], fixture["c1"], clock="15M", side="BID")
    assert stream["result"] == "PASS", stream
    assert stream["counts"] == {
        "bars_total": 2,
        "target_total": 2,
        "bars_complete": 1,
        "target_complete": 1,
        "bars_incomplete": 1,
        "target_incomplete": 1,
        "c1_total": 1,
        "c1_target": 1,
    }
    assert stream["mismatches"] == {}

    bad_formula = copy.deepcopy(fixture)
    bad_formula["c1"][0]["measurements"]["range_abs"] = "0.999"
    failed = audit_stream(bad_formula["bars"], bad_formula["c1"], clock="15M", side="BID")
    assert failed["result"] == "FAIL"
    assert failed["mismatches"]["formula_values"] == 1
    assert failed["mismatches"]["c1_record_identity"] == 1

    bad_incomplete = copy.deepcopy(fixture)
    bad_incomplete["bars"][1]["open"] = "1.0"
    failed = audit_stream(bad_incomplete["bars"], bad_incomplete["c1"], clock="15M", side="BID")
    assert failed["mismatches"]["incomplete_nonnull_ohlcv"] == 1

    bad_reference = copy.deepcopy(reference)
    bad_reference["record_accounting"]["unaccounted_derived_records"] = 1
    expect_error(lambda: validate_reference(bad_reference), "REFERENCE_UNACCOUNTED_RECORDS")

    bad_authority = copy.deepcopy(reference)
    bad_authority["validation_consumption"] = "ALLOWED"
    expect_error(lambda: validate_reference(bad_authority), "REFERENCE_AUTHORITY_ESCAPE")

    output_manifest = load("docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/output-manifest.json")
    manifest_index = {item["path"]: item for item in output_manifest["files"]}
    for item in reference["input_files"]:
        observed = manifest_index[item["name"]]
        assert observed["sha256"] == item["sha256"]
        assert observed["size_bytes"] == item["size_bytes"]

    record_counts = {(item["role"], item["clock"], item["side"]): item["record_count"] for item in reference["input_files"]}
    assert sum(value for (role, _, _), value in record_counts.items() if role == "BARS") == 5220
    assert sum(value for (role, _, _), value in record_counts.items() if role == "C1") == 4958
    assert record_counts[("C1", "15M", "BID")] == 2231
    assert record_counts[("C1", "2H_A_L", "ASK")] == 248

    acceptance = load("docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/PD_JUNE_FULL_MONTH_MDR_WP2_REPLAY_ACCEPTANCE_INDEX.json")
    assert acceptance["run_id"] == reference["source_run_id"]
    assert acceptance["source_manifest_sha256"] == reference["source_manifest_sha256"]
    assert acceptance["deterministic_replay"]["result"] == "PASS_BYTE_IDENTICAL"
    assert acceptance["population"]["c1_target"] == 4526

    source_acceptance = load("docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_INDEX.json")
    assert source_acceptance["qa"]["m1"]["exact_bid_ask_timestamp_set"] is True
    assert source_acceptance["qa"]["m1"]["absent_timestamps_per_side"] == 138
    assert source_acceptance["qa"]["m1"]["gap_runs_per_side"] == 95
    assert source_acceptance["acceptance"]["repair_performed"] is False

    contract = (ROOT / required[0]).read_text(encoding="utf-8")
    for phrase in (
        "No absent interval may be fabricated or bridged",
        "every C1 record",
        "unaccounted_derived_records = 0",
        "MTA-G2 passes only when",
    ):
        assert phrase in contract

    print(json.dumps(result, sort_keys=True))
    print("MTA-WP2 source and C1 audit validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
