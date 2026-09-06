import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP0 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_19.json"
C2_POINTER = ROOT / "registries/opt_b/c2/vnext/CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ_SURFACE.json"
IROF_POINTER = ROOT / "registries/implementation/irof/CURRENT_STATE_POINTER.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_upstream_execution_surfaces_remain_satisfied():
    c2 = load(C2_POINTER)
    irof = load(IROF_POINTER)
    assert c2["status"] == "ACTIVE_ON_LAWFUL_MAIN_MATERIALISATION"
    assert c2["source_expansion"] == "NONE"
    assert irof["programme_disposition"] == "INACTIVE_INFRASTRUCTURE_AVAILABLE"


def test_wp0_binding_matrix_is_fail_closed():
    matrix = load(WP0 / "RRSCG_CORE_WP0_EXACT_BINDING_MATRIX_v0_1.json")
    assert matrix["all_required_bindings_pass"] is False
    assert matrix["disposition"] == "BLOCK"
    assert len(matrix["rows"]) == 3
    assert all(row["implementation_eligible"] is False for row in matrix["rows"])
    assert all(row["current_exact_byte_locator"] is None for row in matrix["rows"])


def test_preserved_exact_identities_are_not_silently_changed():
    matrix = load(WP0 / "RRSCG_CORE_WP0_EXACT_BINDING_MATRIX_v0_1.json")
    by_object = {row["object"]: row for row in matrix["rows"]}
    assert by_object["RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL"]["expected_sha256"] == (
        "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"
    )
    d9 = by_object["RRSCG_D9_DYNAMICS_AND_GEOMETRY_KINEMATICS"]
    assert d9["expected_package_sha256"] == (
        "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
    )
    assert d9["expected_implementation_source_sha256"] == (
        "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"
    )
    d10 = by_object["RRSCG_D10_REDUCER_SUBCOMPONENT"]
    assert d10["expected_full_package_sha256"] is None
    assert d10["known_hash_prefix"] == "6b58e"


def test_historical_exactness_is_distinguished_from_current_materialisation():
    census = load(WP0 / "RRSCG_CORE_WP0_SOURCE_RECOVERY_CENSUS_v0_1.json")
    by_object = {row["object"]: row for row in census["historical_exactness_evidence"]}
    assert by_object["RRSCG_D9_IMPLEMENTATION_0001_SOURCE_PACKAGE"]["current_byte_state"] == (
        "HISTORICALLY_MATERIALISED_AND_VERIFIED_BUT_CURRENTLY_UNRETRIEVABLE"
    )
    assert by_object["RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL"]["current_byte_state"] == "UNMATERIALISED"
    assert by_object["RRSCG_D10_REDUCER_SUBCOMPONENT"]["current_byte_state"] == (
        "UNMATERIALISED_AND_FULL_HASH_NOT_RECOVERED"
    )


def test_block_does_not_revoke_history_or_grant_authority():
    receipt = load(WP0 / "RRSCG_CORE_WP0_BLOCKER_RECEIPT_v0_1.json")
    qa = load(WP0 / "RRSCG_CORE_WP0_QA_v0_1.json")
    state = load(STATE)
    assert receipt["decision"] == "BLOCK"
    assert receipt["authority_delta"] == "NONE_SOURCE_RECOVERY_AND_BINDING_ONLY"
    assert "NO_HISTORICAL_SCIENTIFIC_RESULT_IS_INVALIDATED" in receipt["non_findings"]
    assert qa["disposition"] == "PASS_FAIL_CLOSED_BLOCK_IS_CORRECT_WP0_OUTCOME"
    assert state["status"] == "BLOCKED"
    assert state["implementation_allowed"] is False
    assert state["algorithm_reconstruction_allowed"] is False
    assert state["rrscg_persistent_accession_allowed"] is False
    assert state["operator_decision_required_now"] is False


def test_future_reserved_gate_remains_parked_after_successful_binding_only():
    state = load(STATE)
    receipt = load(WP0 / "RRSCG_CORE_WP0_BLOCKER_RECEIPT_v0_1.json")
    expected = "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING"
    assert state["future_operator_gate_after_successful_binding"] == expected
    assert receipt["future_reserved_gate_if_unblocked"] == expected
