import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "records/research_operations/sff/SFFI_PROGRAMME_STATE_v0_3.json"
DECISION = ROOT / "docs/programmes/sff-v0-1/wp9/org1/SFFI_GREAL_ORG1_INTEGRATION_DECISION_v0_1.json"
POINTER = ROOT / "registries/research_operations/sff/SFFI_GREAL_CURRENT_CANDIDATE_v0_1.json"

CANDIDATE = "sff-greal-candidate:c24c95d09438c09548881a9f4cecc35bb5ca8a15b51a0061c035a3c976bf8d61"
MERGE = "ea17e3cdff20b6ff2c2479d7f5b8dd7f627f0d7b"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_integration_closeout_binds_exact_main_merge_and_next_packet() -> None:
    state = read(STATE)
    decision = read(DECISION)
    pointer = read(POINTER)

    assert decision["decision"] == "PASS"
    assert decision["integration_pr"] == 1464
    assert decision["merge_commit"] == MERGE
    assert decision["candidate_id"] == CANDIDATE
    assert decision["protected_outcomes_accessed"] is False
    assert decision["validation_state"] == "LOCKED_UNCONSUMED"
    assert decision["next_packet"] == "ORG1-R4-EVAL-A-PROSPECTIVE-REPLAY"

    assert state["status"] == "ORG1_REAL_STUDY_CANDIDATE_SUPERSESSION_EFFECTIVE_ON_MAIN_FRESH_SCORING_AUTHORIZED"
    assert state["merge_commit"] == MERGE
    assert state["integration_merge_commit"] == MERGE
    assert state["greal_candidate_id"] == CANDIDATE
    assert state["protected_outcomes_accessed"] is False
    assert state["validation_state"] == "LOCKED_UNCONSUMED"
    assert state["fresh_scoring_state"] == "AUTHORIZED_EXACT_ORG1_R4_R5_ONLY_BY_COMPOSITE_OPERATOR_CHAIN"
    assert state["next_packet"] == "ORG1-R4-EVAL-A-PROSPECTIVE-REPLAY"
    assert pointer["current_candidate_id"] == CANDIDATE
