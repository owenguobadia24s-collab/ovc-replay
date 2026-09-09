import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "records/research_operations/sff/SFFI_PROGRAMME_STATE_v0_5.json"
RECEIPT = ROOT / "docs/programmes/sff-v0-1/wp9/org1/ORG1_R4_R6_INTEGRATION_CLOSEOUT_v0_1.json"

MERGE = "d794eefbb2ec40436d9ff6845596402be4fdb92f"
CANDIDATE = "a871ef952c7e13d88e6e81589b0cab1a7b3a9586"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_org1_r4_r6_integration_closeout_binds_terminal_main_state() -> None:
    state = read(STATE)
    receipt = read(RECEIPT)
    assert receipt["decision"] == "PASS"
    assert receipt["pr"] == 1466
    assert receipt["candidate_commit"] == CANDIDATE
    assert receipt["merge_commit"] == MERGE
    assert receipt["scientific_disposition"] == "C1_INDETERMINATE_SUPPORT_POPULATION_OR_INTEGRITY_UNAVAILABLE"
    assert receipt["same_generation_rescue"] == "PROHIBITED"
    assert receipt["authority_delta"] == "NONE"
    assert receipt["next_packet"] is None

    assert state["status"] == "ORG1_FRESH_STUDY_COMPLETE_PRIMARY_INDETERMINATE_BLOCK_SUPPORT_INTEGRATED_ON_MAIN"
    assert state["candidate_commit"] == CANDIDATE
    assert state["merge_commit"] == MERGE
    assert state["integration_merge_commit"] == MERGE
    assert state["scientific_claim_status"] == "C1_INDETERMINATE_SUPPORT_POPULATION_OR_INTEGRITY_UNAVAILABLE"
    assert state["primary_confirmatory_ci_evaluable"] is False
    assert state["same_generation_rescue"] == "PROHIBITED"
    assert state["validation_state"] == "LOCKED_UNCONSUMED"
    assert state["model_promotion"] is False
    assert state["next_packet"] is None
