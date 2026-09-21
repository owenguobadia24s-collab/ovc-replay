import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "docs/programmes/pmm-dfa-v0-1/bootstrap/PMM_DFA_R1T_CHALLENGE_PACK_PROPOSAL_v0_1.json"
GATE = ROOT / "docs/programmes/pmm-dfa-v0-1/r1t/g0/PMM_DFA_R1T_G0_GATE_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/pmm_dfa/PMM_DFA_PROGRAMME_STATE_v0_3.json"
POINTER = ROOT / "records/research_operations/pmm_dfa/CURRENT_STATE_POINTER.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_pmm_dfa_r1t_g0_gate_ready_contract():
    proposal = load(PROPOSAL)
    gate = load(GATE)
    state = load(STATE)
    pointer = load(POINTER)

    assert proposal["status"] == "PROPOSAL_ONLY_NOT_FROZEN"
    assert [c["candidate_id"] for c in proposal["candidate_set"]] == [
        "R1T-N01", "R1T-C01", "R1T-C02", "R1T-C03", "R1T-C04", "R1T-C05"
    ]
    assert proposal["primary_topological_coordinate"] == [
        "depth", "anchor", "current_zone", "polarity"
    ]
    assert {"P1", "P2", "P3"}.issubset(
        {p["projection_id"] for p in proposal["representation_challenge_envelope"]}
    )
    assert "future_price_behaviour" in proposal["excluded_from_identity"]
    assert proposal["occurrence_contract"]["compiler_properties"] == [
        "PREFIX_SAFE", "DETERMINISTIC", "OUTCOME_BLIND"
    ]

    assert gate["gate_id"] == "PMM-DFA-R1T-G0"
    assert gate["recommendation"] == "PASS"
    assert gate["current_authority"]["r1t_candidate_generation"] == "PROPOSAL_ONLY_NOT_FROZEN"
    assert gate["current_authority"]["protected_development_source_access"] == "LOCKED_UNCONSUMED"
    assert "does NOT grant protected payload access, ACTIVE_DEVELOPMENT or Validation" in gate["proposed_delta"]
    assert gate["exact_post_approval_work"][-1].startswith("Prepare PMM-DFA-R1T-G1")

    assert state["status"] == "GATE_READY"
    assert state["authority_required"] == "OPERATOR_REQUIRED"
    assert state["decision_record"] is None
    assert "ACTIVE_DEVELOPMENT" in state["retained_denials"]

    assert pointer["current_packet"] == "PMM-DFA-R1T-G0"
    assert pointer["status"] == "GATE_READY"
    assert pointer["operator_decision_required"] is True
    assert pointer["next_packet"] is None
