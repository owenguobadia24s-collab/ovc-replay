import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6"
QA = BASE / "C2E2_WP6_POSTRUN_QA_PACKET.json"
DECISION = BASE / "C2E2_WP6_DELEGATED_COMPLETION_DECISION.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_30.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


def load(path): return json.loads(path.read_text())

def test_postrun_qa_passes_without_hiding_warnings():
    qa = load(QA)
    assert qa["qa_recommendation"] == "PASS"
    assert qa["qa_disposition"] == "PASS_WITH_NONBLOCKING_WARNINGS"
    assert qa["blocking_warnings"] == []
    assert qa["unresolved_issues"] == []
    assert len(qa["nonblocking_warnings"]) == 2
    assert any(a["id"] == "WP6-QA-08" and a["status"] == "WARN" for a in qa["assertions"])
    assert any(a["id"] == "WP6-QA-13" and a["status"] == "PASS" for a in qa["assertions"])
    assert qa["frozen_inputs"]["run_authority_token_effective_status"] == "CONSUMED_FOR_RUN"

def test_delegated_closeout_has_no_reserved_authority_delta():
    decision = load(DECISION)
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DELEGATED_OPERATOR_PLAN_AUTHORITY"
    assert decision["authority_delta"] == "NONE_BEYOND_COMPLETED_BOUNDED_WP6_EVIDENCE"
    assert decision["blockers"] == []
    assert decision["next_packet"] == "C2E2-WP7"
    assert "activates no C2E machinery" in decision["non_reserved_rationale"]

def test_completed_state_is_immutable_while_current_pointer_advances_lawfully():
    state = load(STATE)
    pointer = load(POINTER)
    assert state["status"] == "COMPLETED"
    assert state["packet_record"]["status"] == "COMPLETED"
    assert state["packet_record"]["merge_commit"] is None
    assert state["next_packet"] == "C2E2-WP7"
    assert state["authority"]["active_c2e"] == "NONE"
    assert state["authority"]["active_boundary_pack"] == "NONE"
    assert state["authority"]["c2e_activation"] == "DENIED_OPERATOR_RESERVED"
    assert state["authority"]["validation_consumption"] == "DENIED"
    assert state["run_evidence"]["resolver_conflicts"] == 0
    assert state["run_evidence"]["srfd_comparator_status"] == "UNAVAILABLE_CURRENT_LAWFUL_ROUTE"
    assert pointer["active_c2e"] == "NONE"
    assert pointer["active_boundary_pack"] == "NONE"
    assert pointer["replacement_run_token_status"] == "CONSUMED_FOR_RUN"
    auth = pointer["authoritative_state"]
    if auth.endswith("OVC_C2E2_STATE_v0_30.json"):
        assert pointer["current_packet"] == "C2E2-WP7"
        assert pointer["current_gate"] == "C2E2-G7"
        assert pointer["status"] == "READY"
    elif auth.endswith("OVC_C2E2_STATE_v0_38.json"):
        assert pointer["current_packet"] == "C2E-AG1-DECISION"
        assert pointer["current_gate"] == "C2E-AG1"
        assert pointer["status"] == "APPROVED"
        assert pointer["ag1_replay_adequacy"] == "PASS"
    else:
        assert auth == "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_39.json"
        assert pointer["current_packet"] == "C2E-AG2-PREP"
        assert pointer["current_gate"] == "C2E-AG2"
        assert pointer["status"] == "GATE_READY"
        assert pointer["operator_decision_required"] is True
        assert pointer["recommended_operator_decision"] == "DEFER"
        assert pointer["ag3_progression"] == "DENIED_PENDING_AG2"
