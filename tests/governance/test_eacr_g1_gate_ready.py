from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.srfd.serialization import logical_sha256

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
    pointer = j(REG / "CURRENT_STATE_POINTER.json")
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
    assert_logical(REL / "EACR_WP4_WP5_CONFORMANCE_QA.json")


def test_srfd_rebound_token_is_still_unconsumed_at_gate():
    pointer = j(REG / "CURRENT_STATE_POINTER.json")
    token = j(SRFD / "SRFD_JUNE_AUTHORITY_TOKEN_v1_0_EACR.json")
    assert pointer["srfd_v10_token_id"] == token["token_id"]
    assert pointer["srfd_v10_token_state"] == "AUTHORIZED_UNCONSUMED"
    assert pointer["srfd_v10_execution_started"] is False
    assert token["state"] == "AUTHORIZED_UNCONSUMED"
