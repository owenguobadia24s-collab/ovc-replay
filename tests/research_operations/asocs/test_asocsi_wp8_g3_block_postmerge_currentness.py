from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BLOCK_STATE = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_21_WP8_G3_REPRODUCTION_BLOCKED.json"
EFFECTIVE_STATE = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_22_WP8_G3_REPRODUCTION_BLOCK_REPOSITORY_EFFECTIVE.json"
BLOCK_PACKET = "ASOCSI-WP8-G3-REPRODUCTION-INTEGRITY-PREFLIGHT"
FROZEN_G3 = "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def generation(path: str) -> int:
    match = re.search(r"ASOCSI_PROGRAMME_STATE_v0_(\d+)_", path)
    assert match is not None, path
    return int(match.group(1))

def test_wp8_g3_block_is_repository_effective_without_scientific_rewrite():
    historical = load(BLOCK_STATE)
    effective = load(EFFECTIVE_STATE)
    pointer = load("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current = load(pointer["current_state"])
    receipt = load("records/research_operations/asocs/wp8/ASOCSI_WP8_G3_REPRODUCTION_BLOCK_POST_MERGE_COMPLETION_RECEIPT_v0_1.json")
    decision = load("docs/programmes/asocs-v0-1/implementation/wp8/ASOCSI_G6_G3_REPRODUCTION_BLOCK_DECISION_v0_1.json")

    assert historical["status"] == "BLOCKED"
    assert historical["blockers"] == ["G3_FROZEN_CONTENT_IDENTITIES_NOT_REPRODUCIBLE_FROM_EXACT_SOURCE_AND_EXACT_G1"]
    assert historical["human_adjudication_started"] is False

    assert decision["decision"] == "BLOCK"
    assert decision["stage1_reveal_authorized"] is False
    assert decision["authority_delta"] == "NONE"

    assert effective["packet_id"] == BLOCK_PACKET
    assert effective["status"] == "BLOCKED"
    assert effective["candidate_commit"] == "2bcd440fe7861e1c177eb7afd98af3f8194ff1ae"
    assert effective["merge_commit"] == "d6675594a2de881e6d96fee3024b3639ae828da9"
    assert effective["repository_effective"]["repository_effective"] is True
    assert effective["repository_effective"]["pr_number"] == 1299
    assert effective["frozen_g3_identity"]["observation_traces_sha256"] == FROZEN_G3
    assert effective["human_adjudication_started"] is False
    assert effective["stop_boundary"] == "ASOCSI-WP8-STAGED-REVEAL_NOT_AUTHORIZED_UNTIL_G3_REPRODUCIBLE"

    assert receipt["status"] == "BLOCKED"
    assert receipt["repository_effective"] is True
    assert receipt["merge"]["commit_sha"] == effective["merge_commit"]
    assert receipt["merge"]["candidate_head_sha"] == effective["candidate_commit"]
    assert receipt["block"]["frozen_g3_observation_traces_sha256"] == FROZEN_G3
    assert receipt["block"]["stage1_reveal_started"] is False
    assert receipt["block"]["human_adjudication_started"] is False
    assert receipt["authority_delta"] == "NONE"

    assert pointer["programme_id"] == current["programme_id"] == effective["programme_id"]
    assert pointer["packet_id"] == current["packet_id"]
    assert pointer["status"] == current["status"]
    assert pointer["next_packet"] == current["next_packet"]
    assert generation(pointer["current_state"]) >= generation(EFFECTIVE_STATE)
    if pointer["current_state"] != EFFECTIVE_STATE:
        prerequisites = set(current.get("prerequisites", []))
        preserved = current.get("preserved", {})
        assert BLOCK_PACKET in prerequisites or preserved.get("wp8_g3_reproduction_block") is True
