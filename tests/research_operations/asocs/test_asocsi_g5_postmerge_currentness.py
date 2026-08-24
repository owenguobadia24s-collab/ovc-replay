from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_g5_postmerge_currentness_is_repository_effective_and_generation_safe():
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    state = _json(pointer["current_state"])
    receipt = _json("records/research_operations/asocs/wp7/ASOCSI_G5_POST_MERGE_COMPLETION_RECEIPT_v0_1.json")

    assert pointer["current_state"].endswith("ASOCSI_PROGRAMME_STATE_v0_20_WP7_G5_REPOSITORY_EFFECTIVE.json")
    assert pointer["packet_id"] == state["packet_id"] == "ASOCSI-WP7-G5-BLIND-EVIDENCE-FREEZE"
    assert pointer["status"] == state["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert pointer["next_packet"] == state["next_packet"] == "ASOCSI-WP8-STAGED-REVEAL-AND-ADJUDICATION"
    assert state["candidate_commit"] == "5ae79ce0e17f9b32c18405a66d801219564f20b6"
    assert state["merge_commit"] == "213e4921449b061ed32d97caef36dc6adb54c883"
    assert state["human_review"]["completed_sessions"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert state["human_review_started"] is True
    assert state["authority_delta"] == "NONE"
    assert state["stop_boundary"] == "ASOCSI-WP8-STAGED-REVEAL-HUMAN_ADJUDICATION_REQUIRED"
    assert receipt["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert receipt["merge"]["pr_number"] == 1292
    assert receipt["merge"]["candidate_head_sha"] == state["candidate_commit"]
    assert receipt["merge"]["commit_sha"] == state["merge_commit"]
    assert receipt["authority_delta"] == "NONE"
