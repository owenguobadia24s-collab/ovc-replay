from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.opt_b.srfd.serialization import logical_sha256
from tests.historical_court_record import json_at

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "docs/releases/external-artifact-capacity-ownership-v0-1"
REG = ROOT / "registries/implementation/eacr"
SRFD = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-0"


def j(path: Path):
    return json.loads(path.read_text())


def assert_logical(path: Path):
    data = j(path)
    expected = data.pop("logical_sha256")
    assert logical_sha256(data) == expected


def test_eacr_g1_is_operator_required_and_recommends_pass():
    gate = j(REL / "EACR_G1_GATE_PACKET.json")
    pointer = json_at("88c7392465404bd2caf0e688acba96e5174159e2", REG / "CURRENT_STATE_POINTER.json")
    assert gate["status"] == "GATE_READY"
    assert gate["gate_classification"] == "OPERATOR_REQUIRED"
    assert gate["operator_decision_required"] is True
    assert gate["recommended_decision"] == "PASS"
    assert pointer["current_gate"] == "EACR-G1"
    assert pointer["operator_decision_required"] is True
    assert pointer["next_action"] == "STOP_FOR_OPERATOR_EACR_G1"
    assert_logical(REL / "EACR_G1_GATE_PACKET.json")


def test_all_five_work_packets_are_complete_before_g1():
    state = j(REG / "OVC_EACR_STATE_v0_3.json")
    assert state["work_packets"] == {
        "EACR-WP1": "COMPLETED",
        "EACR-WP2": "COMPLETED_MERGED_5231baebdfced4e889fc9ea64979be345d5e4102",
        "EACR-WP3": "COMPLETED_MERGED_0515d515b261cada7daef9a9cc5ae03db9e462ad",
        "EACR-WP4": "COMPLETED_PASS",
        "EACR-WP5": "COMPLETED_GATE_PREP",
    }
    assert state["status"] == "GATE_READY"
    assert_logical(REG / "OVC_EACR_STATE_v0_3.json")


def test_closeout_qa_preserves_authority_firewalls():
    qa = j(REL / "EACR_WP4_WP5_CONFORMANCE_QA.json")
    gate = j(REL / "EACR_G1_GATE_PACKET.json")
    assert qa["status"] == "PASS_READY_FOR_EACR_G1"
    assert not qa["blockers"]
    assert all(value == "PASS" for value in qa["checks"].values())
    delta = gate["authority_delta_if_pass"]
    assert delta["srfd_benchmark_execution"] == "NOT_STARTED"
    assert delta["market_science"] == "UNCHANGED"
    assert delta["selector_family_semantic_publication"] == "NONE"
    assert delta["validation"] == "LOCKED_UNCONSUMED"
    assert delta["probability_risk_exposure_execution"] == "NONE"


def test_closeout_qa_logical_identity_is_append_only_superseded():
    original_path = REL / "EACR_WP4_WP5_CONFORMANCE_QA.json"
    successor_path = REL / "EACR_WP4_WP5_CONFORMANCE_QA_IDENTITY_SUCCESSOR.json"
    adjudication_path = REL / "EACR_QA_LOGICAL_HASH_INTEGRITY_ADJUDICATION.json"

    original_bytes = original_path.read_bytes()
    original = json.loads(original_bytes)
    successor = j(successor_path)
    adjudication = j(adjudication_path)

    recorded_bad_hash = original.pop("logical_sha256")
    corrected_hash = successor.pop("logical_sha256")
    assert recorded_bad_hash == "76368f31dc8e446377d552536956595d7ea76ab340feb739fc98534f50705c82"
    assert corrected_hash == "827ff0afb6e9344ead9b57eda4c6a4db7b9e29710ac2b311127779541282a024"
    assert logical_sha256(original) == corrected_hash
    assert original == successor

    stale_pre_final = json.loads(json.dumps(original))
    assert stale_pre_final["checks"].pop("old_checkpoint_relabel_forbidden") == "PASS"
    assert logical_sha256(stale_pre_final) == recorded_bad_hash

    git_blob = b"blob " + str(len(original_bytes)).encode("ascii") + b"\0" + original_bytes
    assert hashlib.sha1(git_blob).hexdigest() == "fa4a86937ec989c441a166c3b61b055c2fd36133"
    assert hashlib.sha256(original_bytes).hexdigest() == "fa4d58558ad54166a9c2c582b158ae94ccd14d4c2f5f835f632505c49add6db4"

    assert adjudication["discrepancy_id"] == "PYT-WP2-EACR-QA-LOGICAL-HASH-001"
    assert adjudication["classification"] == "EVIDENCE_INTEGRITY_ONLY"
    assert adjudication["authority_effect"] == "NONE"
    assert adjudication["deterministic_cause"]["category"] == "STALE_PRE_FINAL_PAYLOAD"
    assert adjudication["semantic_adjudication"]["qa_payload_correct"] is True
    assert adjudication["semantic_adjudication"]["operator_decision"] == "UNCHANGED"
    assert adjudication["resolution"]["status"] == "RESOLVED"
    assert adjudication["resolution"]["historical_artifact_modified"] is False
    assert adjudication["successor_artifact"]["corrected_logical_sha256"] == corrected_hash
    assert_logical(successor_path)
    assert_logical(adjudication_path)


def test_identity_correction_leaves_terminal_eacr_chain_unchanged():
    qa_path = "docs/releases/external-artifact-capacity-ownership-v0-1/EACR_WP4_WP5_CONFORMANCE_QA.json"
    bad_hash = "76368f31dc8e446377d552536956595d7ea76ab340feb739fc98534f50705c82"
    gate_path = REL / "EACR_G1_GATE_PACKET.json"
    decision_path = REL / "EACR_G1_OPERATOR_DECISION_PASS.json"
    receipt_path = REL / "EACR_COMPLETION_RECEIPT.json"
    state_path = REG / "OVC_EACR_STATE_v0_4.json"

    gate = j(gate_path)
    decision = j(decision_path)
    receipt = j(receipt_path)
    state = j(state_path)
    assert gate["qa_packet"] == qa_path
    assert decision["reviewed_qa_packet"] == qa_path
    assert decision["reviewed_gate_packet_logical_sha256"] == gate["logical_sha256"]
    assert receipt["operator_decision"].endswith("EACR_G1_OPERATOR_DECISION_PASS.json")
    assert state["completion_receipt"].endswith("EACR_COMPLETION_RECEIPT.json")
    assert state["status"] == "COMPLETED"
    assert decision["decision"] == receipt["terminal_decision"] == "PASS"
    assert decision["authority_effect"]["probability_risk_exposure_execution"] == "NONE"
    assert decision["authority_effect"]["selector_family_semantic_publication"] == "NONE"
    for path in (gate_path, decision_path, receipt_path, state_path):
        assert bad_hash not in path.read_text()
        assert_logical(path)


def test_srfd_rebound_token_is_still_unconsumed_at_gate():
    pointer = j(REG / "CURRENT_STATE_POINTER.json")
    token = j(SRFD / "SRFD_JUNE_AUTHORITY_TOKEN_v1_0_EACR.json")
    assert pointer["srfd_v10_token_id"] == token["token_id"]
    assert pointer["srfd_v10_token_state"] == "AUTHORIZED_UNCONSUMED"
    assert pointer["srfd_v10_execution_started"] is False
    assert token["state"] == "AUTHORIZED_UNCONSUMED"
