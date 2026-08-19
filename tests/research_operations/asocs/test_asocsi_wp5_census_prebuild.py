from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.asocs.census import (
    build_census,
    checkpoint_prefix,
    prove_two_run_equality,
    verify_restart,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _fixture() -> list[dict]:
    return [
        {"bar_id": "A", "clock": "15M", "interval_start": "2026-01-02T00:00:00", "interval_end": "2026-01-02T00:15:00",
         "effective_time": "2026-01-02T00:15:00", "first_valid_time": "2026-01-02T00:15:00",
         "region": "TARGET", "status": "COMPLETE", "parent_source_row_ids": ["m1:a"], "missing_parent_slots": [],
         "open": "1.1", "high": "1.2", "low": "1.0", "close": "1.15"},
        {"bar_id": "B", "clock": "15M", "interval_start": "2026-01-02T00:15:00", "interval_end": "2026-01-02T00:30:00",
         "effective_time": "2026-01-02T00:30:00", "first_valid_time": "2026-01-02T00:30:00",
         "region": "TARGET", "status": "COMPLETE", "parent_source_row_ids": ["m1:b"], "missing_parent_slots": [],
         "open": "1.15", "high": "1.25", "low": "1.1", "close": "1.2"},
        {"bar_id": "C", "clock": "15M", "interval_start": "2026-01-02T00:30:00", "interval_end": "2026-01-02T00:45:00",
         "effective_time": "2026-01-02T00:45:00", "first_valid_time": "2026-01-02T00:45:00",
         "region": "TARGET", "status": "INCOMPLETE", "parent_source_row_ids": ["m1:c"], "missing_parent_slots": ["2026-01-02T00:31:00"]},
        {"bar_id": "D", "clock": "15M", "interval_start": "2026-01-02T00:45:00", "interval_end": "2026-01-02T01:00:00",
         "effective_time": "2026-01-02T01:00:00", "first_valid_time": "2026-01-02T01:00:00",
         "region": "TARGET", "status": "ABSENT", "parent_source_row_ids": [], "missing_parent_slots": ["2026-01-02T00:45:00"]},
    ]


def test_census_accepts_real_wp2_bar_id_and_preserves_lineage_missingness() -> None:
    census = build_census(_fixture())
    assert census["record_count"] == 4
    assert census["source_status_counts"] == {"ABSENT": 1, "COMPLETE": 2, "INCOMPLETE": 1}
    assert census["traces"][0]["object_id"] == "A"
    assert census["traces"][0]["source_lineage"]["parent_source_row_ids"] == ["m1:a"]
    assert census["traces"][2]["c1"]["disposition"] == "NOT_EVALUABLE_SOURCE"
    assert all(v["disposition"] == "NOT_EVALUABLE" for v in census["traces"][0]["upper_stack"].values())


def test_c1_prior_is_used_only_across_complete_contiguous_15m_records() -> None:
    census = build_census(_fixture())
    first = census["traces"][0]["c1"]
    second = census["traces"][1]["c1"]
    assert first["null_reasons"]["true_range_abs"] == "SOURCE_CONTINUITY_UNRESOLVED_OR_GAP"
    assert second["measurements"]["true_range_abs"] is not None
    assert "true_range_abs" not in second["null_reasons"]


def test_checkpoint_restart_and_two_run_logical_equality() -> None:
    census = build_census(_fixture())
    checkpoint = checkpoint_prefix(census, 2)
    assert verify_restart(checkpoint, census)
    proof = prove_two_run_equality(_fixture())
    assert proof["result"] == "PASS"
    assert proof["logical_equal"] is True
    assert proof["ordered_trace_ids_equal"] is True


def test_g3_candidate_is_bound_to_recovered_exact_source_but_not_frozen_before_ci() -> None:
    candidate = _json("docs/programmes/asocs-v0-1/implementation/wp5/ASOCSI_G3_CENSUS_CANDIDATE_v0_1.json")
    assert candidate["source"]["sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert candidate["census"]["census_sha256"] == "c49f34e7af19f0110d24377a54ab8f0bd3fb183e83e924de07bf39cd586de2c7"
    assert candidate["census"]["record_count"] == 17568
    assert candidate["census"]["target_record_count"] == 17376
    assert candidate["two_clean_logical_executions_equal"] is True
    assert candidate["review_sampling_started"] is False
    qa = _json("docs/programmes/asocs-v0-1/implementation/wp5/ASOCSI_WP5_QA_PACKET_v0_2.json")
    assert qa["qa_recommendation"] == "QA_REVIEW"
    assert qa["gate_decision"] == "NOT_YET_RATIFIED"
    assert qa["repository_ci"] == "PENDING"


def test_wp5_qa_state_does_not_admit_wp6_before_g3_pass() -> None:
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_8_WP5_QA_REVIEW.json")
    assert state["status"] == "QA_REVIEW"
    assert state["gate_status"] == "QA_REVIEW"
    assert state["review_sampling_started"] is False
    assert state["next_packet"] == "ASOCSI-WP6_AFTER_G3_PASS"


def test_g3_delegated_freeze_and_pointer_admit_only_wp6_after_pass() -> None:
    exact_source = "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    census_id = "c49f34e7af19f0110d24377a54ab8f0bd3fb183e83e924de07bf39cd586de2c7"
    freeze = _json("docs/programmes/asocs-v0-1/implementation/wp5/ASOCSI_G3_CENSUS_FREEZE_v0_1.json")
    decision = _json("docs/programmes/asocs-v0-1/implementation/wp5/ASOCSI_G3_DELEGATED_DECISION_v0_1.json")
    qa = _json("docs/programmes/asocs-v0-1/implementation/wp5/ASOCSI_WP5_QA_PACKET_v0_3.json")
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_9_WP5.json")
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current_state = _json(pointer["current_state"])
    assert freeze["status"] == "FROZEN_G3"
    assert freeze["source"]["sha256"] == exact_source
    assert freeze["census_sha256"] == census_id
    assert freeze["integrity"]["review_sampling_before_freeze"] is False
    assert freeze["active"] is False and freeze["canonical"] is False and freeze["publication"] is False
    assert decision["decision"] == "PASS_DELEGATED"
    assert decision["authority_delta"] == "NONE"
    assert qa["qa_recommendation"] == "PASS"
    assert state["status"] == "COMPLETED"
    assert state["gate_status"] == "APPROVED"
    assert state["review_sampling_started"] is False
    assert state["next_packet"] == "ASOCSI-WP6"
    assert pointer["programme_id"] == "OVC-ASOCS-6M-v0.1"
    assert pointer["packet_id"] == current_state["packet_id"]
    assert pointer["status"] == current_state["status"]
    assert pointer["next_packet"] == current_state["next_packet"]
