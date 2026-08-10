import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
RA = BASE / "run_authority"
REL = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag1-gap-001"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
POP_HASH = "46f02ed89c9c4a3d4b3ef2046b7aa32489c5b63a526dbb8151896331d0ae896d"
OLD_TOKEN = "C2E2.G6.TOKEN.da591198b34d96ef5fcccb9a"


def _j(path):
    return json.loads(path.read_text())


def test_read_only_feasibility_is_pass_but_does_not_claim_gap_closed():
    r = _j(REL / "C2E_AG1_GAP_001_READ_ONLY_FEASIBILITY_RECEIPT.json")
    assert r["full_ag1_requirement_status"] == "NOT_YET_MET"
    assert r["fresh_run_required"] is True
    assert [x["status"] for x in r["checks"][:2]] == ["PASS", "PASS"]
    assert r["checks"][0]["prefix_record_count"] == 8229
    assert r["checks"][0]["restored_episode_count"] == 46
    assert r["checks"][0]["semantic_prefix_hash"] == "4dc0af22d802272ced022cb4e8d7769b4a5e06cf268bb872cb90dbf1276f4f5e"
    assert r["authority_effect"] == "NONE"


def test_restart_manifest_is_exact_and_does_not_expand_science_or_resources():
    m = _j(RA / "C2E_AG1_RESTART_RUN_MANIFEST_v0_1.json")
    assert m["run_manifest_id"] == "C2E.AG1.RESTART.EQUIVALENCE.JUNE.EXACT.v1"
    assert m["boundary_pack"]["boundary_pack_id"] == PACK_ID
    assert m["boundary_pack"]["logical_sha256"] == PACK_HASH
    assert m["source_population"]["logical_population_sha256"] == POP_HASH
    assert m["source_population"]["target_frame_count"] == 4072
    assert m["restart_protocol"]["restart_cut"] == "PARTITION_END:ASK"
    assert m["execution_requirements"]["authorized_run_count_if_pass"] == 1
    assert m["execution_requirements"]["provider_intake"] == "NONE"
    assert m["resource_envelope"]["expansion_from_wp6"] == "NONE"
    assert m["authority"]["execution"] == "DENIED_UNTIL_EXACT_SINGLE_USE_OPERATOR_TOKEN"


def test_token_is_only_proposed_and_old_consumed_token_remains_unusable():
    p = _j(RA / "C2E2_G6_RUN_AUTH_R2_TOKEN_PROPOSAL.json")
    hist = _j(RA / "C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_3.json")
    assert p["status"] == "PROPOSED_PENDING_OPERATOR"
    assert p["single_use"] is True
    assert p["reuse_prohibited"] is True
    assert p["consumed"] is False
    assert p["invalidated"] is False
    assert hist["active_runtime_authority"] == "NONE_TOKEN_CONSUMED"
    assert hist["unconsumed_tokens"] == []
    old = [x for x in hist["historical_tokens"] if x["token_id"] == OLD_TOKEN][0]
    assert old["consumed"] is True
    assert old["reuse_prohibited"] is True


def test_run_authority_subgate_is_operator_required_and_no_downstream_authority():
    g = _j(REL / "C2E2_G6_RUN_AUTH_R2_GATE_PACKET.json")
    assert g["gate_id"] == "C2E2-G6-RUN-AUTH-R2"
    assert g["gate_classification"] == "OPERATOR_REQUIRED"
    assert g["decision_status"] == "PENDING_OPERATOR"
    assert g["recommended_decision"] == "PASS"
    assert g["allowed_decisions"] == ["PASS", "DEFER", "BLOCK"]
    assert g["proposed_authority_delta_if_pass"]["fresh_run_authority"].startswith("ONE_EXACT_SINGLE_USE")
    assert g["proposed_authority_delta_if_pass"]["provider_intake"] == "NONE_EXISTING_FROZEN_MATERIALISATION_ONLY"
    assert g["proposed_authority_delta_if_pass"]["active_c2e"] == "NONE"
    assert g["proposed_authority_delta_if_pass"]["active_boundary_pack"] == "NONE"
    assert g["proposed_authority_delta_if_pass"]["post_run_authority"] == "NONE_AUTOMATIC_C2E_AG1_REMAINS_OPERATOR_RESERVED"


def test_historical_r2_subgate_is_exact_while_current_pointer_may_progress():
    p = _j(BASE / "CURRENT_STATE_POINTER.json")
    assert p["active_c2e"] == "NONE"
    assert p["active_boundary_pack"] == "NONE"
    auth = p["authoritative_state"]
    if auth.endswith("OVC_C2E2_STATE_v0_34.json"):
        assert p["current_gate"] == "C2E-AG1"
        assert p["status"] == "GATE_READY"
        assert p["recommended_operator_decision"] == "DEFER"
        assert p["next_action"] == "STOP_FOR_OPERATOR_C2E_AG1"
        assert p["blocking_operator_subgate"] == "C2E2-G6-RUN-AUTH-R2"
        assert p["blocking_operator_subgate_decision_required"] is True
        assert p["blocking_operator_subgate_recommended_decision"] == "PASS"
        assert p["ag1_gap001_execution_evidence"] == "NOT_YET_AUTHORIZED"
    elif auth.endswith("OVC_C2E2_STATE_v0_38.json"):
        assert p["current_gate"] == "C2E-AG1"
        assert p["status"] == "APPROVED"
        assert p["operator_decision"] == "PASS"
        assert p["ag1_replay_adequacy"] == "PASS"
        assert p["restart_token_status"] == "CONSUMED_SUCCESS_REUSE_PROHIBITED"
        assert p["next_gate"] == "C2E-AG2"
    else:
        assert auth == "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_39.json"
        assert p["current_gate"] == "C2E-AG2"
        assert p["current_packet"] == "C2E-AG2-PREP"
        assert p["status"] == "GATE_READY"
        assert p["operator_decision_required"] is True
        assert p["recommended_operator_decision"] == "DEFER"
        assert p["ag1_replay_adequacy"] == "PASS"
        assert p["ag2_required_evidence_gap"] == "C2E-AG2-GAP-001_SRFD_COMPARATOR_DISAGREEMENT"
