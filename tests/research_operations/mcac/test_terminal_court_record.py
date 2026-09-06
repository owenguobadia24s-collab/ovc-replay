from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load(path: str):
    return json.loads((ROOT / path).read_text())


def test_terminal_receipt_binds_exact_primary_integration_and_assurance():
    receipt = load("docs/programmes/lsiac-v0-1/mcac-v0-1/wp5/MCAC_TERMINAL_RECEIPT_v0_1.json")
    assert receipt["status"] == "MCAC_V0_1_COMPLETE_REPOSITORY_EFFECTIVE"
    assert receipt["primary_pr"] == 1444
    assert receipt["candidate_commit"] == "93efe1f2d5fc1bff95c762d594df961792c4cb60"
    assert receipt["merge_commit"] == "3ba03bd9383b46edebfba28ebca1bff1e6c2ef8f"
    assert receipt["assurance"]["canonical_population_count"] == 5600
    assert receipt["vit"]["status"] == "PASS" and receipt["grt"]["status"] == "PASS_EXACT_TREE"


def test_programme_state_and_pointer_are_terminal_and_bounded():
    state = load("records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_32.json")
    pointer = load("records/research_operations/lsiac/CURRENT_STATE_POINTER.json")
    assert state["terminal_state"] == "MCAC_V0_1_COMPLETE_REPOSITORY_EFFECTIVE"
    assert [item["workstream_id"] for item in state["workstreams"]] == [f"MCAC-WS{i}" for i in range(6)]
    assert all(not item["blockers"] for item in state["workstreams"])
    assert state["capability_state"] == "INACTIVE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["new_clock_authority"] == "NONE"
    assert pointer["current_state"] == "LSIAC_PROGRAMME_STATE_v0_32.json"
    assert pointer["prior_rrscg_terminal_retained"] == "LSIAC_PROGRAMME_STATE_v0_31.json"
