from __future__ import annotations

from typing import Any, Mapping

LETTERS = tuple("ABCDEFGHIJKL")
EXPECTED_AGGREGATE = {
    "fifteen_minute_resolutions_total": 4462,
    "fifteen_minute_resolutions_target": 4072,
    "parent_available_total": 629,
    "parent_available_target": 615,
    "empty_or_cleared_target": 3457,
    "unknown_reset_count": 0,
}

class MTAWP4AuditError(ValueError):
    pass

def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise MTAWP4AuditError(marker)

def validate_reference(reference: Mapping[str, Any]) -> dict[str, Any]:
    _require(reference.get("schema") == "ovc-mta-wp4-clock-parent-audit-reference/v1", "REFERENCE_SCHEMA_MISMATCH")
    _require((reference.get("programme_id"), reference.get("packet_id"), reference.get("gate_id")) == ("OVC-MTA-v0.2", "MTA-WP4", "MTA-G4"), "REFERENCE_IDENTITY_MISMATCH")
    _require(reference.get("plan_version") == "0.2", "REFERENCE_PLAN_VERSION_MISMATCH")
    mapping = reference.get("a_l_mapping")
    _require(isinstance(mapping, list) and len(mapping) == 12, "A_L_MAPPING_COUNT_MISMATCH")
    _require(tuple(item.get("block") for item in mapping) == LETTERS, "A_L_MAPPING_ORDER_MISMATCH")
    for index, item in enumerate(mapping):
        _require(item.get("start_hour_utc") == index * 2, f"A_L_START_HOUR_MISMATCH:{LETTERS[index]}")
        _require(item.get("end_hour_utc") == ((index * 2 + 2) % 24), f"A_L_END_HOUR_MISMATCH:{LETTERS[index]}")
    artifact = reference.get("external_artifact")
    _require(isinstance(artifact, dict) and artifact.get("provider") == "GOOGLE_DRIVE", "EXTERNAL_ARTIFACT_MISSING")
    _require(artifact.get("file_id") == "1O4AmSc1grGX3sfFFa0i4f-Oh1Ro44ghk", "EXTERNAL_ARTIFACT_ID_MISMATCH")
    _require(artifact.get("size_bytes") == 3712999, "EXTERNAL_ARTIFACT_SIZE_MISMATCH")
    _require(artifact.get("sha256") == "e63228a1244790263059efbb949e2917d8e1889aac26503ea9e05955cf1c6000", "EXTERNAL_ARTIFACT_SHA_MISMATCH")
    aggregate = reference.get("aggregate")
    _require(isinstance(aggregate, dict), "AGGREGATE_MISSING")
    for key, expected in EXPECTED_AGGREGATE.items():
        _require(aggregate.get(key) == expected, f"AGGREGATE_MISMATCH:{key}")
    _require(aggregate.get("target_availability_rate_percent") == "15.103143", "TARGET_AVAILABILITY_RATE_MISMATCH")
    sides = reference.get("sides")
    _require(isinstance(sides, dict) and set(sides) == {"BID", "ASK"}, "SIDE_MATRIX_MISMATCH")
    expected_available = {"BID": 311, "ASK": 304}
    for side in ("BID", "ASK"):
        item = sides[side]
        _require(item["two_hour_bars"]["total"] == 294 and item["two_hour_bars"]["target"] == 268, f"2H_ACCOUNTING_MISMATCH:{side}")
        _require(item["parent_events"]["actions"]["CLEAR_INCOMPLETE"] == 46, f"PARENT_CLEAR_COUNT_MISMATCH:{side}")
        _require(item["fifteen_minute_resolutions"]["total"] == 2231 and item["fifteen_minute_resolutions"]["target"] == 2036, f"15M_ACCOUNTING_MISMATCH:{side}")
        _require(item["fifteen_minute_resolutions"]["target_status"]["AVAILABLE"] == expected_available[side], f"PARENT_AVAILABLE_MISMATCH:{side}")
        _require(item["fifteen_minute_resolutions"]["future_parent_usage"] == 0, f"FUTURE_PARENT_USAGE:{side}")
        _require(item["reset_census"]["causes"] == {"PROVIDER_GAP": 48, "SCHEDULED_WEEKEND_CLOSURE": 4, "SOURCE_PARTITION_START": 1}, f"RESET_CENSUS_MISMATCH:{side}")
        _require(item["reset_census"]["unknown_count"] == 0, f"UNKNOWN_RESET:{side}")
    mismatches = reference.get("mismatch_counts")
    _require(isinstance(mismatches, dict) and all(value == 0 for value in mismatches.values()), "MISMATCH_COUNTS_NONZERO")
    paired = reference.get("paired_consistency")
    _require(isinstance(paired, dict) and all(value == 0 for value in paired.values()), "PAIRED_CONSISTENCY_FAILURE")
    finding_ids = {item.get("finding_id") for item in reference.get("findings", []) if isinstance(item, dict)}
    _require({"MTA-WP4-F1","MTA-WP4-F2","MTA-WP4-F3","MTA-WP4-F4","MTA-WP4-F5"}.issubset(finding_ids), "FINDING_SET_MISMATCH")
    _require(reference.get("qa_recommendation") == "PASS_WITH_MATERIAL_FINDINGS", "QA_NOT_PASS")
    denied = {"clock_change":"DENIED","continuity_rule_change":"DENIED","formula_threshold_change":"DENIED","selector_change":"DENIED","c2e_c2_5_c3":"DENIED","validation_consumption":"DENIED","r2_publication":"DENIED","probability_risk_exposure_execution":"NONE"}
    for key, expected in denied.items():
        _require(reference.get(key) == expected, f"AUTHORITY_ESCAPE:{key}")
    return {"status":"PASS","target_resolutions":4072,"target_parent_available":615,"target_availability_rate_percent":"15.103143","material_findings":sorted(finding_ids)}

def validate_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    _require(fixture.get("schema") == "ovc-mta-wp4-parent-event-fixture/v1", "FIXTURE_SCHEMA_MISMATCH")
    events = fixture.get("events"); locals_ = fixture.get("local_closes")
    _require(isinstance(events, list) and isinstance(locals_, list), "FIXTURE_SHAPE_MISMATCH")
    times = [item["event_time"] for item in events]
    _require(times == sorted(times) and len(times) == len(set(times)), "FIXTURE_EVENT_ORDER_INVALID")
    active = []
    index = 0
    observed = []
    for item in locals_:
        while index < len(events) and events[index]["event_time"] <= item["close_time"]:
            active = events[index]["levels"] if events[index]["quality"] == "COMPLETE" else []
            index += 1
        observed.append(bool(active))
    _require(observed == [item["expected_parent_available"] for item in locals_], "FIXTURE_RESOLUTION_MISMATCH")
    return {"status":"PASS","events":len(events),"local_closes":len(locals_)}
