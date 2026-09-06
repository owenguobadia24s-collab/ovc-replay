import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP0S = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_20.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_successor_binding_matrix_passes_exactly_three_core_objects():
    matrix = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_EXACT_BINDING_MATRIX_v0_2.json")
    assert matrix["all_required_bindings_pass"] is True
    assert matrix["disposition"] == "PASS"
    assert len(matrix["rows"]) == 3
    assert all(row["binding_status"].startswith("BOUND_EXACT") for row in matrix["rows"])


def test_r2_and_d9_preserved_identities_are_exactly_reverified():
    matrix = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_EXACT_BINDING_MATRIX_v0_2.json")
    by_object = {row["object"]: row for row in matrix["rows"]}
    r2 = by_object["RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL"]
    assert r2["actual_sha256"] == r2["expected_sha256"] == (
        "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"
    )
    d9 = by_object["RRSCG_D9_DYNAMICS_AND_GEOMETRY_KINEMATICS"]
    assert d9["actual_package_sha256"] == d9["expected_package_sha256"] == (
        "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
    )
    assert d9["actual_implementation_source_sha256"] == d9["expected_implementation_source_sha256"] == (
        "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"
    )


def test_d10_full_identity_is_recovered_from_preserved_prefix_and_redundantly_bound():
    matrix = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_EXACT_BINDING_MATRIX_v0_2.json")
    d10 = {row["object"]: row for row in matrix["rows"]}["RRSCG_D10_REDUCER_SUBCOMPONENT"]
    full = "6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f"
    assert full.startswith(d10["historical_known_hash_prefix"])
    assert d10["recovered_full_package_sha256"] == full
    assert d10["direct_package_sha256"] == full
    assert d10["release_bundle_embedded_package_sha256"] == full
    assert d10["release_state"] == "SEALED_SUCCESSOR_NOT_ACTIVE"


def test_source_binding_pass_stops_at_operator_reserved_accession_gate():
    decision = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_CLOSEOUT_DECISION_v0_1.json")
    state = load(STATE)
    expected_gate = "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING"
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "NONE_SOURCE_RECOVERY_AND_EXACT_BINDING_ONLY"
    assert decision["operator_decision_required_now"] is True
    assert decision["operator_gate"] == expected_gate
    assert state["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert state["current_gate"] == expected_gate
    assert state["implementation_allowed"] is False
    assert state["rrscg_persistent_accession_allowed"] is False


def test_d10_binding_does_not_activate_or_replace_d9():
    receipt = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_SOURCE_MATERIALISATION_RECEIPT_v0_1.json")
    d10 = [row for row in receipt["artifacts"] if row["role"] == "RRSCG_D10_EXACT_RELEASE_BUNDLE"][0]
    qa = load(WP0S / "RRSCG_CORE_WP0_SUCCESSOR_QA_v0_1.json")
    assert d10["release_state"] == "SEALED_SUCCESSOR_NOT_ACTIVE"
    assert qa["authority_delta"] == "NONE_SOURCE_RECOVERY_AND_EXACT_BINDING_ONLY"
