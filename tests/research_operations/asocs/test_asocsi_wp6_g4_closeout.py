from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_g4_final_freeze_is_delegated_none_and_fail_closed() -> None:
    freeze = _json("docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_REVIEW_POPULATION_FREEZE_v0_1.json")
    decision = _json("docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_DELEGATED_DECISION_v0_1.json")
    qa = _json("docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_WP6_QA_PACKET_v0_2.json")
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_11_WP6.json")
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current_state = _json(pointer["current_state"])
    assert freeze["status"] == "FROZEN_G4"
    assert freeze["review_population_sha256"] == "ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe"
    assert freeze["sampling_manifest_id"] == "33fa9aa81059d0bde9b9cc84da73336d3a20c7236610ccf5b3d8a8a5979e3a31"
    assert freeze["upper_stack_review_scope"] == "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE"
    assert freeze["source_side_state"] == "UNRESOLVED_SINGLE_STREAM"
    assert freeze["source_clock_state"] == "SOURCE_TIMEZONE_UNRESOLVED"
    assert freeze["human_review_started"] is False
    assert freeze["active"] is freeze["canonical"] is freeze["publication"] is False
    assert decision["decision"] == "PASS_DELEGATED"
    assert decision["authority_delta"] == "NONE"
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_findings"] == []
    assert state["status"] == "COMPLETED"
    assert state["gate_status"] == "APPROVED"
    assert state["review_population_frozen"] is True
    assert state["human_review_started"] is False
    assert state["next_packet"] == "ASOCSI-WP7-INFRA_AFTER_G4_PASS"
    assert pointer["programme_id"] == "OVC-ASOCS-6M-v0.1"
    assert pointer["packet_id"] == current_state["packet_id"]
    assert pointer["status"] == current_state["status"]
    assert pointer["next_packet"] == current_state["next_packet"]


def test_g4_freeze_counts_are_consistent_with_candidate() -> None:
    freeze = _json("docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_REVIEW_POPULATION_FREEZE_v0_1.json")
    candidate = _json("docs/programmes/asocs-v0-1/implementation/wp6/ASOCSI_G4_SAMPLING_CANDIDATE_v0_1.json")
    i = freeze["integrity"]
    assert i["base_rate_selection_count"] == candidate["base_rate_selection_count"] == 120
    assert i["gap_centered_selection_count"] == candidate["gap_centered_selection_count"] == 40
    assert i["hidden_repeat_count"] == candidate["hidden_repeat_count"] == 18
    assert i["unique_review_unit_count"] == candidate["unique_review_unit_count"] == 352
    assert i["presentation_count"] == candidate["presentation_count"] == 370
    assert i["session_count"] == candidate["session_count"] == 15
