import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RS0 = ROOT / "docs" / "releases" / "c2p-persistent-structural-objects-v0-2" / "c2p2-rs0"
STATE = ROOT / "registries" / "implementation" / "c2p_v0_2" / "C2P2_RS0_STATE_v0_1.json"
EXECUTION_STATE = ROOT / "registries" / "implementation" / "c2p_v0_2" / "C2P2_RS0_EXECUTION_STATE_v0_1.json"
PS0_CANDIDATES_V1 = ROOT / "docs" / "releases" / "c2p-persistent-structural-objects-v0-2" / "c2p2-ps0" / "C2P2_PS0_OBJECTPACK_CANDIDATES_v0_1.json"
PS0_CANDIDATES_V2 = ROOT / "docs" / "releases" / "c2p-persistent-structural-objects-v0-2" / "c2p2-ps0" / "C2P2_PS0_OBJECTPACK_CANDIDATES_v0_2.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_rs0_preparation_preserves_historical_v1_comparative_set_and_current_successor_v2_no_winner():
    binding = load(RS0 / "C2P2_RS0_SOURCE_POPULATION_BINDING_v0_1.json")
    state = load(STATE)
    ps0_v1 = load(PS0_CANDIDATES_V1)
    ps0_v2 = load(PS0_CANDIDATES_V2)

    historical = {
        "C2P2-PS0-OP-A-STRICT-CONTINUITY-v1",
        "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v1",
        "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v1",
    }
    successor = {
        "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2",
        "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2",
    }
    assert set(binding["candidate_set"]) == historical
    v1_rows = ps0_v1.get("candidates", ps0_v1.get("candidate_object_packs", []))
    v1_ids = {row.get("object_pack_id", row.get("candidate_id")) for row in v1_rows if isinstance(row, dict)}
    assert historical <= v1_ids

    assert set(state["candidate_set"]) == successor
    assert {row["candidate_id"] for row in ps0_v2["candidates"]} == successor
    assert set(ps0_v2["supersedes_generation"]["candidate_ids"]) == historical
    assert ps0_v2["selection_state"] == "NONE_SELECTED"
    assert ps0_v2["active_object_pack_id"] is None
    assert state["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert binding["common_comparison_requirements"]["scalar_winner_forbidden"] is True


def test_rs0_is_sidecar_only_and_cannot_change_ec1_science():
    binding = load(RS0 / "C2P2_RS0_SOURCE_POPULATION_BINDING_v0_1.json")
    state = load(STATE)
    firewall = binding["ec1_firewall"]

    assert binding["scientific_effect"] == "NONE"
    assert binding["operating_role"] == "C2P_SHADOW_SIDECAR_ONLY"
    assert binding["ec1_scientific_authority"] == "UNCHANGED"
    assert state["authority"]["ec1_scientific_authority"] == "UNCHANGED"
    assert state["authority"]["ec1_candidate_defining_use"] == "FORBIDDEN"
    assert firewall["may_change_q01_q10"] is False
    assert firewall["may_change_population_or_denominator"] is False
    assert firewall["may_seed_or_filter_path1_search"] is False
    assert firewall["may_rank_or_freeze_ec1_candidates"] is False
    assert firewall["may_become_active_ec1_candidate_defining_source"] is False


def test_historical_preparation_and_grun_are_preserved_but_not_retargeted_to_successor_generation():
    binding = load(RS0 / "C2P2_RS0_SOURCE_POPULATION_BINDING_v0_1.json")
    state = load(STATE)
    execution = load(EXECUTION_STATE)
    historical_gate = load(RS0 / "C2P2_RS0_RUN_AUTHORITY_PACKET_v0_1.json")
    approved_gate = load(RS0 / "C2P2_RS0_RUN_AUTHORITY_PACKET_v0_3.json")
    authority = load(ROOT / "registries" / "authority" / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_1.json")

    assert binding["real_source_run_authority"] == "DENIED_UNTIL_C2P2_RS0_GRUN_OPERATOR_PASS"
    assert binding["c2p_activation_authority"] == "NONE"
    assert binding["active_object_pack"] is None
    assert historical_gate["decision"] == "PENDING_OPERATOR"
    assert historical_gate["decision_authority"] == "OPERATOR_REQUIRED"

    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert approved_gate["decision"] == "PASS"
    assert approved_gate["approved_authority"]["real_source_run"] == "ONE_BOUNDED_PREREGISTERED_RS0_SHADOW_RUN"
    assert approved_gate["approved_authority"]["objectpack_selection"] == "NONE"
    assert approved_gate["approved_authority"]["ec1_scientific_authority_effect"] == "NONE"

    assert state["authority"]["prior_grun_v1"] == "PASS_TOKEN_UNCONSUMED_NOT_APPLICABLE_TO_SUCCESSOR_V2"
    assert state["authority"]["successor_candidate_real_source_launch"] == "DENIED_UNTIL_RUNTIME_CLOSEOUT_FINAL_GENERATION_AND_FRESH_GRUN_PASS"
    assert state["authority"]["active_object_pack"] is None
    assert state["authority"]["objectpack_selection"] == "NONE"
    assert execution["prior_grun"]["run_authority_consumed"] is False
    assert execution["prior_grun"]["run_count_remaining"] == 1
    assert execution["fresh_grun_required_before_real_source_launch"] is True


def test_rs0_dependency_and_capacity_firewalls_fail_closed():
    binding = load(RS0 / "C2P2_RS0_SOURCE_POPULATION_BINDING_v0_1.json")
    deps = binding["dependency_rules"]
    resource = binding["resource_envelope"]

    assert deps["c2"] == "REQUIRED"
    assert deps["c2e_candidate_c"] == "OPTIONAL_DECLARED_ENRICHMENT_ONLY"
    assert deps["c2e_episode_identity_sufficient_for_c2p_identity"] is False
    assert deps["family_or_c3_semantics_identity_authority"] == "FORBIDDEN"
    assert deps["future_information"] == "FORBIDDEN"
    assert deps["opt_c_opt_d_outcomes"] == "FORBIDDEN"
    assert deps["validation"] == "LOCKED_UNCONSUMED"
    assert resource["identity_precision"] == "EXACT_ONLY"
    assert resource["sampling"] == "FORBIDDEN"
    assert resource["reduced_precision"] == "FORBIDDEN"
    assert resource["capacity_exhaustion"] == "FAIL_CLOSED_CAPACITY_EXCEEDED"
