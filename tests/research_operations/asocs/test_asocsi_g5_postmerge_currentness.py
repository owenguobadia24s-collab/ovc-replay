from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
G5_STATE_PATH = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_20_WP7_G5_REPOSITORY_EFFECTIVE.json"
G5_PACKET_ID = "ASOCSI-WP7-G5-BLIND-EVIDENCE-FREEZE"
G5_GATE_ID = "ASOCSI-G5"


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _state_generation(path: str) -> int:
    match = re.search(r"ASOCSI_PROGRAMME_STATE_v0_(\d+)_", path)
    assert match is not None, path
    return int(match.group(1))


def _assert_current_descends_from_g5(pointer: dict, current: dict, g5: dict) -> None:
    assert pointer["programme_id"] == current["programme_id"] == g5["programme_id"]
    assert pointer["packet_id"] == current["packet_id"]
    assert pointer["status"] == current["status"]
    assert pointer["next_packet"] == current["next_packet"]
    assert _state_generation(pointer["current_state"]) >= _state_generation(G5_STATE_PATH)

    if pointer["current_state"] == G5_STATE_PATH:
        assert current["packet_id"] == G5_PACKET_ID
        return

    prerequisites = set(current.get("prerequisites", []))
    preserved = current.get("preserved", {})
    assert (
        G5_GATE_ID in prerequisites
        or G5_PACKET_ID in prerequisites
        or preserved.get("g5_blind_evidence") is True
    )
    assert current.get("human_review_started") is True


def test_g5_postmerge_currentness_is_repository_effective_and_generation_safe():
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current = _json(pointer["current_state"])
    g5 = _json(G5_STATE_PATH)
    receipt = _json("records/research_operations/asocs/wp7/ASOCSI_G5_POST_MERGE_COMPLETION_RECEIPT_v0_1.json")

    assert g5["packet_id"] == G5_PACKET_ID
    assert g5["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert g5["next_packet"] == "ASOCSI-WP8-STAGED-REVEAL-AND-ADJUDICATION"
    assert g5["candidate_commit"] == "5ae79ce0e17f9b32c18405a66d801219564f20b6"
    assert g5["merge_commit"] == "213e4921449b061ed32d97caef36dc6adb54c883"
    assert g5["human_review"]["completed_sessions"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert g5["human_review_started"] is True
    assert g5["authority_delta"] == "NONE"
    assert g5["stop_boundary"] == "ASOCSI-WP8-STAGED-REVEAL-HUMAN_ADJUDICATION_REQUIRED"

    assert receipt["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert receipt["merge"]["pr_number"] == 1292
    assert receipt["merge"]["candidate_head_sha"] == g5["candidate_commit"]
    assert receipt["merge"]["commit_sha"] == g5["merge_commit"]
    assert receipt["authority_delta"] == "NONE"

    _assert_current_descends_from_g5(pointer, current, g5)
