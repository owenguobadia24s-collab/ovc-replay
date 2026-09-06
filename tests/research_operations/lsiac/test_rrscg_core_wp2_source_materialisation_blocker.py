from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP2 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp2"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_25.json"
POINTER = ROOT / "records/research_operations/lsiac/CURRENT_STATE_POINTER.json"
WP0 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor/RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json"
ARTIFACT_POLICY = ROOT / "artifacts/README.md"

EXPECTED_D9 = "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
EXPECTED_IMPL = "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp2_distinguishes_exact_binding_from_execution_availability():
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


def test_wp2_fails_closed_without_d9_reconstruction():
    blocker = load(WP2 / "RRSCG_CORE_WP2_PREFLIGHT_AND_BLOCKER_v0_1.json")
    qa = load(WP2 / "RRSCG_CORE_WP2_QA_v0_1.json")
    authority = load(WP2 / "RRSCG_CORE_WP2_AUTHORITY_MANIFEST_v0_1.json")
    assert blocker["no_reconstruction_rule"]["effect"] == "NO_D9_IMPLEMENTATION_WRITTEN"
    assert blocker["d9_implementation_written"] is False
    assert qa["qa_recommendation"] == "BLOCK"
    assert "RECONSTRUCT_D9_FROM_SUMMARIES_OUTPUTS_OR_BEHAVIOUR" in authority["denied"]


def test_wp2_programme_state_is_blocked_not_deauthorised():
    state = load(STATE)
    pointer = load(POINTER)
    assert state["status"] == "BLOCKED"
    assert state["implementation_allowed"] is True
    assert state["implementation_exercisable_now"] is False
    assert state["rrscg_persistent_accession_construction_allowed"] is True
    assert state["operator_decision_required_now"] is False
    assert state["d9_algorithm_implementation_written"] is False
    assert state["claim_cap"] == "DESCRIPTIVE_DEVELOPMENT_ONLY"
    assert state["blockers"][0]["required_sha256"] == EXPECTED_IMPL
    assert state["next_packet"] == "RRSCG-CORE-WP2-D9-OBSERVER-STATE-FACULTY"
    assert pointer["current_state"] == "LSIAC_PROGRAMME_STATE_v0_25.json"
    assert pointer["status"] == "BLOCKED"


def test_external_artifact_policy_explains_execution_gap():
    policy = ARTIFACT_POLICY.read_text(encoding="utf-8")
    assert "duplicate engine ZIPs" in policy
    assert "ovc-replay-external-artifacts" in policy


def test_dependency_frontier_has_one_artifact_availability_blocker():
    frontier = load(WP2 / "RRSCG_CORE_WP2_DEPENDENCY_FRONTIER_v0_1.json")
    assert frontier["status"] == "BLOCKED"
    assert len(frontier["blocked"]) == 1
    assert frontier["blocked"][0]["id"] == "D9_EXACT_SOURCE_BYTES_EXECUTION_AVAILABILITY"
    assert frontier["blocked"][0]["required_sha256"] == EXPECTED_IMPL
