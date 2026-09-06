from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP3 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp3"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_27.json"
POINTER = ROOT / "records/research_operations/lsiac/CURRENT_STATE_POINTER.json"
WP0 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor/RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json"
ARTIFACT_POLICY = ROOT / "artifacts/README.md"

EXPECTED_D10 = "6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f"
EXPECTED_BUNDLE = "092bf144b38f84a43946d36a15d0905c2bce7f51e7ca815e6814eae361d1ad67"
EXPECTED_RELEASE_BINDING = "cb2315d01379138c1f62d6b1cacc89d9b1314bf2532602e264b7d223a27bf099"
EXPECTED_D9 = "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
EXPECTED_R2 = "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp3_blocker_preserves_exact_d10_binding_and_forbids_reconstruction():
    source = _load(WP0)
    by_object = {item["object"]: item for item in source["bindings"]}
    d10 = by_object["RRSCG_D10_REDUCER_SUBCOMPONENT"]
    assert d10["status"] == "BOUND_EXACT_FULL_IDENTITY_RECOVERED"
    assert d10["actual_uploaded_package_sha256"] == EXPECTED_D10
    assert d10["recovered_full_expected_package_sha256"] == EXPECTED_D10
    assert d10["release_bundle_sha256"] == EXPECTED_BUNDLE
    assert d10["release_binding_sha256"] == EXPECTED_RELEASE_BINDING
    assert d10["exact_d9_parent_package_sha256"] == EXPECTED_D9
    assert d10["immutable_parent_r2_sha256"] == EXPECTED_R2
    assert d10["standalone_equals_nested_release_bytes"] is True

    blocker = _load(WP3 / "RRSCG_CORE_WP3_PREFLIGHT_AND_BLOCKER_v0_1.json")
    assert blocker["preflight_disposition"] == "BLOCKED"
    assert blocker["blocker_id"] == "RRSCG_CORE_WP3_D10_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert blocker["d10_implementation_written"] is False
    assert blocker["court_record_source_binding"]["d10_algorithm_package_sha256"] == EXPECTED_D10
    assert blocker["execution_availability"]["state"] == "D10_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert blocker["no_reconstruction_rule"]["effect"] == "NO_D10_IMPLEMENTATION_WRITTEN"
    assert blocker["smallest_lawful_resolution"]["required_sha256"] == EXPECTED_D10
    assert blocker["smallest_lawful_resolution"]["new_operator_scientific_authority_required"] is False
    assert "RECONSTRUCT_D10_FROM_SUMMARIES_OUTPUTS_OR_BEHAVIOUR" in blocker["retained_denials"]


def test_wp3_blocker_state_and_dependency_frontier_are_fail_closed():
    state = _load(STATE)
    pointer = _load(POINTER)
    authority = _load(WP3 / "RRSCG_CORE_WP3_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _load(WP3 / "RRSCG_CORE_WP3_DEPENDENCY_FRONTIER_v0_1.json")
    qa = _load(WP3 / "RRSCG_CORE_WP3_QA_v0_1.json")

    assert state["status"] == "BLOCKED"
    assert state["implementation_exercisable_now"] is False
    assert state["d10_algorithm_implementation_written"] is False
    assert state["capability_activation_allowed"] is False
    assert state["blockers"][0]["required_sha256"] == EXPECTED_D10
    assert pointer["status"] == "APPROVED"
    assert pointer["current_state"] == "LSIAC_PROGRAMME_STATE_v0_28.json"
    assert pointer["prior_wp3_blocker_retained"] == "LSIAC_PROGRAMME_STATE_v0_27.json"
    assert authority["authority_delta"] == "NONE_BLOCKER_RECORD_ONLY"
    assert authority["currently_blocked"][0] == "D10_REDUCER_IMPLEMENTATION"
    assert frontier["status"] == "BLOCKED"
    assert len(frontier["blocked"]) == 1
    assert frontier["blocked"][0]["id"] == "D10_EXACT_SOURCE_BYTES_EXECUTION_AVAILABILITY"
    assert frontier["blocked"][0]["required_sha256"] == EXPECTED_D10
    assert qa["qa_recommendation"] == "BLOCK"


def test_wp3_blocker_matches_external_artifact_policy():
    policy = ARTIFACT_POLICY.read_text(encoding="utf-8")
    assert "duplicate engine ZIPs" in policy
    assert "ovc-replay-external-artifacts" in policy
