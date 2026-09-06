from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP2 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp2"
STATE_ROOT = ROOT / "records/research_operations/lsiac"
BLOCKED_STATE = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_25.json"
WP2_COMPLETED_STATE = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_26.json"
POINTER = STATE_ROOT / "CURRENT_STATE_POINTER.json"
WP0 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor/RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json"
ARTIFACT_POLICY = ROOT / "artifacts/README.md"

EXPECTED_D9 = "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
EXPECTED_IMPL = "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_historical_wp2_blocker_remains_exactly_a_source_availability_blocker():
    wp0 = load(WP0)
    blocker = load(WP2 / "RRSCG_CORE_WP2_PREFLIGHT_AND_BLOCKER_v0_1.json")
    d9 = next(row for row in wp0["bindings"] if row["object"] == "RRSCG_D9_DYNAMICS_AND_GEOMETRY_KINEMATICS")
    implementation = next(row for row in wp0["bindings"] if row["object"] == "RRSCG_D9_IMPLEMENTATION_0001_SOURCE_PACKAGE")
    assert d9["status"] == "BOUND_EXACT"
    assert d9["nested_algorithm_actual_sha256"] == EXPECTED_D9
    assert implementation["status"] == "BOUND_EXACT"
    assert implementation["actual_sha256"] == EXPECTED_IMPL
    assert blocker["court_record_source_binding"]["implementation_source_sha256"] == EXPECTED_IMPL
    assert blocker["execution_availability"]["state"] == "D9_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert blocker["preflight_disposition"] == "BLOCKED"


def test_blocker_and_wp2_completion_are_preserved_after_forward_progression():
    blocked = load(BLOCKED_STATE)
    completed = load(WP2_COMPLETED_STATE)
    pointer = load(POINTER)
    current_path = STATE_ROOT / pointer["current_state"]
    current = load(current_path)

    assert blocked["status"] == "BLOCKED"
    assert blocked["implementation_allowed"] is True
    assert blocked["implementation_exercisable_now"] is False
    assert blocked["d9_algorithm_implementation_written"] is False
    assert blocked["blockers"][0]["required_sha256"] == EXPECTED_IMPL

    assert completed["status"] == "APPROVED"
    assert completed["exact_d9_source_package_sha256"] == EXPECTED_IMPL
    assert pointer["prior_wp2_blocker_retained"] == BLOCKED_STATE.name
    assert pointer["prior_wp2_completed_retained"] == WP2_COMPLETED_STATE.name

    assert current_path.exists()
    assert pointer["current_state"] != BLOCKED_STATE.name
    assert current["programme_id"] == pointer["programme_id"]


def test_source_rematerialisation_receipt_closes_only_execution_availability():
    receipt = load(WP2 / "RRSCG_CORE_WP2_SOURCE_REMATERIALISATION_RECEIPT_v0_1.json")
    assert receipt["expected_sha256"] == EXPECTED_IMPL
    assert receipt["actual_sha256"] == EXPECTED_IMPL
    assert receipt["internal_sha256sum_entries_verified"] == 29
    assert receipt["internal_sha256sum_entries_total"] == 29
    assert receipt["disposition"] == "SOURCE_BYTES_EXECUTION_ACCESS_RESTORED_AND_EXACTLY_VERIFIED"
    assert receipt["authority_delta"] == "NONE_SOURCE_AVAILABILITY_ONLY"


def test_external_artifact_policy_still_excludes_duplicate_engine_zips():
    policy = ARTIFACT_POLICY.read_text(encoding="utf-8")
    assert "duplicate engine ZIPs" in policy
    assert "ovc-replay-external-artifacts" in policy
