import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP0S = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_20.json"
ARTIFACT_POLICY = ROOT / "artifacts/README.md"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_load_bearing_sources_are_bound_exact():
    manifest = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json")
    assert manifest["all_load_bearing_algorithm_sources_bound_exact"] is True
    assert manifest["d10_full_identity_recovered"] is True
    assert manifest["disposition"] == "PASS_EXACT_SOURCE_BINDING"
    by_object = {row["object"]: row for row in manifest["bindings"]}
    assert by_object["RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL"]["actual_sha256"] == (
        "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"
    )
    assert by_object["RRSCG_D9_DYNAMICS_AND_GEOMETRY_KINEMATICS"]["nested_algorithm_actual_sha256"] == (
        "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
    )
    assert by_object["RRSCG_D9_IMPLEMENTATION_0001_SOURCE_PACKAGE"]["actual_sha256"] == (
        "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"
    )
    assert by_object["RRSCG_D10_REDUCER_SUBCOMPONENT"]["recovered_full_expected_package_sha256"] == (
        "6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f"
    )


def test_d10_identity_is_independently_cross_bound():
    manifest = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json")
    d10 = next(row for row in manifest["bindings"] if row["object"] == "RRSCG_D10_REDUCER_SUBCOMPONENT")
    expected = d10["recovered_full_expected_package_sha256"]
    assert expected.startswith(d10["prior_known_hash_prefix"])
    assert d10["actual_uploaded_package_sha256"] == expected
    assert d10["nested_release_bundle_package_sha256"] == expected
    assert d10["fresh_exact_byte_review_declared_package_sha256"] == expected
    assert d10["final_qualification_declared_package_sha256"] == expected
    assert d10["standalone_equals_nested_release_bytes"] is True


def test_source_binding_pass_grants_no_implementation_authority():
    decision = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_GATE_DECISION_v0_1.json")
    state = load(STATE)
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "NONE_SOURCE_BINDING_ONLY"
    assert decision["implementation_effect"] == "STILL_PROHIBITED_PENDING_OPERATOR_RESERVED_ACCESSION_AUTHORITY"
    assert decision["operator_decision_required_now"] is True
    assert state["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert state["implementation_allowed"] is False
    assert state["rrscg_persistent_accession_allowed"] is False
    assert state["operator_decision_required_now"] is True
    assert state["current_gate"] == "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING"


def test_external_archive_policy_is_respected():
    text = ARTIFACT_POLICY.read_text(encoding="utf-8")
    assert "duplicate engine ZIPs" in text
    manifest = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json")
    assert manifest["artifact_storage_policy"] == "EXTERNAL_ARTIFACTS_NOT_COMMITTED_TO_ORDINARY_GIT_PER_ARTIFACTS_README"


def test_operator_gate_is_narrow_and_default_hold():
    gate = load(WP0S / "LSIAC_G_RRSCG_CORE_ACCESSION_AUTHORITY_AFTER_WP0_SOURCE_BINDING_GATE_PACKET_v0_1.json")
    assert gate["authority_class"] == "OPERATOR_RESERVED"
    assert gate["default_without_operator_action"] == "HOLD_NO_IMPLEMENTATION"
    denied = set(gate["explicitly_not_granted"])
    assert "CAPABILITY_ACTIVATION" in denied
    assert "ACTIVE_VALIDATION" in denied
    assert "PROBABILITY_RISK_EXPOSURE_EH_TRADING_OR_EXECUTION_AUTHORITY" in denied
