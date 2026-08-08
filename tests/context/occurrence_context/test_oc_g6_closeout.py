import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "registries" / "implementation" / "occurrence_context"
RELEASE_DIR = ROOT / "docs" / "releases" / "occurrence-context-v0-1" / "oc-g6"


def _load(path: Path):
    return json.loads(path.read_text())


def test_oc_g6_closeout_is_completed_and_bounded():
    pointer = _load(STATE_DIR / "CURRENT_IMPLEMENTATION_STATE_POINTER.json")
    state = _load(STATE_DIR / "OVC_OC_IMPLEMENTATION_STATE_v0_10.json")
    receipt = _load(RELEASE_DIR / "OC_G6_MERGE_RECEIPT.json")
    decision = _load(RELEASE_DIR / "OC_G6_OPERATOR_DECISION.json")

    assert pointer["status"] == "COMPLETED"
    assert pointer["operator_decision"] == "PASS"
    assert pointer["merge_commit"] == "633eed419ae5d19e0d5c78ebfd07ee822fa247e7"
    assert state["status"] == "COMPLETED"
    assert state["next_packet"] is None
    assert state["authority"]["c2p"] == "NOT_STARTED_NOT_AUTHORIZED"
    assert state["authority"]["representation_input"] == "DENIED_BY_DEFAULT"
    assert state["authority"]["validation"] == "LOCKED_UNCONSUMED"
    assert receipt["decision"] == "PASS"
    assert receipt["merge_commit"] == "633eed419ae5d19e0d5c78ebfd07ee822fa247e7"
    assert decision["operator_command"] == "OVC APPROVE OC-G6 PASS"
    assert receipt["next_packet"] is None
