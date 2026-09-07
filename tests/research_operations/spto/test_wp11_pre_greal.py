import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_mechanics import content_id
from ovc.research_operations.spto.pre_greal import BINDINGS, CUSTODY_BINDINGS, build_pre_greal_packet


ROOT = Path(__file__).resolve().parents[3]
PACKET = "docs/programmes/c2s-sptoi-v0-1/wp11/C2S_SPTOI_WP11_PRE_GREAL_OPERATOR_PACKET_v0_1.json"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def filed():
    return load(PACKET)


def test_filed_packet_rebuilds_exactly_validates_schema_and_identity():
    packet = filed()
    assert packet == build_pre_greal_packet(ROOT)
    body = copy.deepcopy(packet)
    identity = body.pop("operator_packet_id")
    assert identity == content_id("PreGrealOperatorPacket/v1", body)
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/PRE_GREAL_OPERATOR_PACKET_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(packet)


def test_all_24_bound_files_have_exact_live_hashes_and_sizes():
    bindings = filed()["qa_and_file_bindings"]
    assert bindings["bound_record_count"] == len(BINDINGS) + len(CUSTODY_BINDINGS) == 24
    for binding in bindings["file_bindings"]:
        raw = (ROOT / binding["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == binding["sha256"]
        assert len(raw) == binding["size_bytes"]


def test_governing_plan_protocol_and_er3_amendments_are_exact():
    authority = filed()["governing_authority"]
    assert authority["plan_id"].endswith("R3-TVX-R31-PRR1-RATIFIED")
    assert authority["plan_docx_sha256"] == "e1683cb537a3ca77cef1799fcb1079bcae61f449375340e597f6b4bb632977a1"
    assert authority["protocol_id"] == "OVC-EML-GRAMMAR-0002-RP-0.1-R1"
    assert authority["protocol_docx_sha256"] == "a4eaaa43d051628e6fc6da4151ed9500f68a832d85240188cdf0f656a1893fd5"
    assert authority["accepted_er3_amendments"] == [f"ER3-{i:02d}" for i in range(1, 13)]
    assert authority["protocol_operator_decision"] == "PASS"


def test_owner_primary_and_dense_secondary_boundary_is_fail_closed():
    source = filed()["source_and_read_surface"]
    assert source["owner_primary"]["type"] == "OWNER_STRUCTURAL_SNAPSHOT_STREAM"
    assert source["owner_primary"]["mode"] == "SYNTHETIC_QUALIFICATION_FIXTURE"
    assert source["dense_secondary"]["may_generate"] == [
        "MicroCarrierContextView", "MicroOperationView", "MicroFactorisedPath"
    ]
    assert source["dense_secondary"]["may_repair_owner_state_or_target"] is False
    assert source["dense_secondary"]["exact_binding"] is None
    assert source["dense_secondary"]["real_source_execution_eligible"] is False


def test_tvx_partial_source_and_c0c_non_equivalence_are_explicit():
    tvx = filed()["tvx_source_and_reproduction"]
    assert tvx["completeness_status"] == "PARTIAL_SOURCE_LIMITED"
    assert tvx["required_round_denominator"] == 13
    assert {"R9X", "R16", "R21"}.issubset(tvx["not_exactly_bound_rounds"])
    assert tvx["c0c_classification"] == "RECEIPT_CONCORDANT_NOT_BYTE_REPRODUCED"
    assert tvx["c0c_byte_equivalent"] is False
    assert tvx["c0c_join_eligibility"] is False


def test_population_denominators_training_frontier_and_no_survivor_promotion():
    population = filed()["population_and_training"]
    assert population["universal_owner_transition_denominator"] == 8
    assert population["grammar_evaluation_denominator"] == 6
    assert population["explicit_declared_view_row_denominator"] == 40
    assert population["computed_declared_view_rows"] == {
        "numerator": 29, "denominator": 40, "rendering": "29/40"
    }
    assert population["non_survivor_promotion"] == "FORBIDDEN"
    assert population["training_frontier"]["static_within_cohort"] is True


def test_factorised_mechanics_trace_and_coupled_nulls_are_complete():
    packet = filed()
    mechanics = packet["factorised_mechanics"]
    assert len(mechanics["declared_representation_set"]["members"]) == 5
    assert mechanics["relation_support_trace"]["trace_set_complete"] is True
    assert mechanics["comparison_target_pack"]
    nulls = packet["null_coupling"]
    assert len(nulls["null_spec_ids"]) == 6
    assert nulls["total_replica_count"] == 768
    assert nulls["all_representations_from_one_world_per_replica"] is True
    assert nulls["independent_representation_draws"] is False


def test_exposure_ledgers_derivation_capacity_and_retention_are_bound():
    packet = filed()
    exposure = packet["opportunity_exposure_and_freshness"]
    assert exposure["specification_opportunity_ledger"]["complete"] is True
    assert exposure["design_exposure_manifest"]["complete"] is True
    closure = packet["derivation_capacity_and_retention"]
    assert closure["dependency_change_assurance"]["changed"] is True
    assert closure["capacity_result"] == "PASS_MEASURED_WITHOUT_FEATURE_REMOVAL"
    assert closure["retention"]["expected"] == closure["retention"]["observed"]


def test_reviewer_independence_is_honest_and_operator_decision_is_not_claimed():
    review = filed()["reviewer_independence"]
    assert review["historical_g3_reviewer"]["reviewer_type"] == "INDEPENDENT_CODEX_SUBAGENT"
    assert review["historical_g3_decision"] == "ACCEPT_PARTIAL_SOURCE_LIMITED"
    assert review["wp11_independent_scientific_decision_claimed"] is False
    assert review["genuine_independent_authority"] == "OPERATOR_DECISION_REQUIRED_AT_GREAL"


def test_all_wp5_through_wp10_custody_is_exact_and_verified():
    custody = filed()["laboratory_custody"]
    assert [row["packet"] for row in custody] == ["WP10", "WP5", "WP6", "WP7", "WP8", "WP9"]
    assert all(row["status"] == "FILED_VERIFIED" for row in custody)
    assert all(row["drive_file_id"] and row["artifact_sha256"] and row["artifact_size_bytes"] for row in custody)


def test_proposed_delta_is_exactly_feasibility_only_and_suppresses_outputs():
    packet = filed()
    delta = packet["proposed_real_source_authority_delta"]
    proposed = delta["if_operator_passes"]
    assert delta["decision_token"] == "PASS_REAL_SOURCE_FEASIBILITY_ONLY"
    assert proposed["permitted_execution"] == "PHASE_A_REAL_SOURCE_FEASIBILITY_ONLY"
    assert proposed["required_output"] == "RealSourceFeasibilityExposureRecord"
    assert "CANDIDATE_OUTPUTS" in proposed["structurally_suppressed_outputs"]
    assert proposed["candidate_generating_factorised_search"].endswith("GREAL_FEAS_PASS")
    assert packet["current_authority"] == {
        "protected_source_access": "DENIED",
        "factorised_evidence_execution": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "candidate_generation": "DENIED",
        "candidate_freeze": "NONE",
        "semantic_authority": "NONE",
        "publication": "NONE",
        "probability_risk_exposure_trading_execution": "NONE",
    }


def test_terminal_pointer_is_greal_ready_and_stops_for_operator():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load(pointer["current_state"])
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp11/C2S_SPTOI_G11_PRE_GREAL_ASSEMBLY_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] == "C2S-SPTOI-WP11"
    assert pointer["next_packet"] is None
    assert pointer["status"] == "GREAL_PACKET_READY"
    assert pointer["next_operator_gate"] == "C2S-SPTOI-GREAL-SCI-PREREG"
    assert state["gate_status"] == "GREAL_PACKET_READY_OPERATOR_REQUIRED"
    assert gate["decision"] == "PASS_PRE_GREAL_PACKET_ASSEMBLY"
    assert gate["authority_effect"] == "NONE_PACKET_ASSEMBLY_ONLY"


def test_wp11_authority_and_dependency_frontier_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp11/C2S_SPTOI_WP11_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp11/C2S_SPTOI_WP11_DEPENDENCY_FRONTIER_v0_1.json")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
