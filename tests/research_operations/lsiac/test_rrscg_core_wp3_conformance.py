from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP3 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp3"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_28.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp3_source_recovery_is_exact_and_does_not_mutate_drive_artifacts():
    receipt = _load(WP3 / "RRSCG_CORE_WP3_SOURCE_REMATERIALISATION_RECEIPT_v0_1.json")
    package = receipt["algorithm_package"]
    release = receipt["corroborating_release_bundle"]
    assert package["expected_sha256"] == package["actual_sha256"]
    assert package["internal_sha256sum_entries_verified"] == 64
    assert package["internal_sha256sum_failures"] == []
    assert release["standalone_equals_nested_release_bytes"] is True
    assert receipt["source_verification"]["exhaustive_reducer_cases"] == "1024_OF_1024_PASS"
    assert receipt["source_verification"]["parent_r2_equivalence"] == "1027_OF_1027_PASS"
    assert receipt["artifact_mutation"].startswith("NONE")


def test_g3_is_auto_ratified_without_authority_delta():
    frontier = _load(WP3 / "RRSCG_CORE_WP3_DEPENDENCY_FRONTIER_v0_2.json")
    qa = _load(WP3 / "RRSCG_CORE_WP3_QA_v0_2.json")
    review = _load(WP3 / "RRSCG_CORE_G3_INDEPENDENT_ALGORITHMIC_REVIEW_v0_1.json")
    decision = _load(WP3 / "RRSCG_CORE_G3_GATE_DECISION_v0_1.json")
    authority = _load(WP3 / "RRSCG_CORE_WP3_AUTHORITY_MANIFEST_v0_2.json")
    state = _load(STATE)

    assert frontier["status"] == "SATISFIED"
    assert frontier["blocked"] == []
    assert qa["qa_recommendation"] == "PASS_PENDING_EXACT_FINAL_REPOSITORY_ASSURANCE"
    assert review["verdict"] == "PASS_WITH_SCOPE_RESTRICTIONS"
    assert decision["decision"] == "PASS"
    assert decision["decision_class"] == "DELEGATED_AUTO_RATIFICATION_NON_RESERVED_CONFORMANCE"
    assert decision["authority_delta"] == "NONE"
    assert state["status"] == "APPROVED"
    assert state["capability_activation_allowed"] is False
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["next_packet"] == "RRSCG-CORE-WP4-C2-OWNER-ADAPTER-IROF-TRANSPORT"
    assert {"CAPABILITY_ACTIVATION", "ACTIVE_VALIDATION", "CANONICAL_OR_R2_PUBLICATION"} <= set(authority["denied"])


def test_d10_supersession_is_reducer_layer_only():
    authority = _load(WP3 / "RRSCG_CORE_WP3_AUTHORITY_MANIFEST_v0_2.json")
    assert "TRANSPORT_EXACT_BOUND_D10_C_LAST_REDUCER_ONLY" in authority["granted"]
    assert "D9_FULL_DYNAMICS_REPLACEMENT_OUTSIDE_REDUCER_INTERFACE" in authority["denied"]
    assert authority["claim_cap"] == "DESCRIPTIVE_DEVELOPMENT_ONLY"
    assert authority["capability_state"] == "INACTIVE"
