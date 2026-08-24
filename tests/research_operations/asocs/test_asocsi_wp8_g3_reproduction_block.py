from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_21_WP8_G3_REPRODUCTION_BLOCKED.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cid(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _state_generation(path: str) -> int:
    match = re.search(r"ASOCSI_PROGRAMME_STATE_v0_(\d+)_", path)
    assert match is not None, path
    return int(match.group(1))


def test_wp8_source_recovers_exact_g1_but_g3_identity_blocks_reveal():
    source = _json(WP8 / "ASOCSI_WP8_SOURCE_REPRODUCTION_RECEIPT_v0_1.json")
    repro = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_INTEGRITY_v0_1.json")
    authority = _json(WP8 / "ASOCSI_WP8_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _json(WP8 / "ASOCSI_WP8_DEPENDENCY_FRONTIER_v0_1.json")
    packet = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_PACKET_v0_1.json")
    qa = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_QA_v0_1.json")
    decision = _json(WP8 / "ASOCSI_G6_G3_REPRODUCTION_BLOCK_DECISION_v0_1.json")
    state = _json(STATE)
    pointer = _json(POINTER)
    current_path = Path(pointer["current_state"])
    current = _json(ROOT / current_path)

    assert source["source"]["sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert source["verification"]["g1_audit_15m"]["result"] == "PASS"
    assert source["verification"]["g1_audit_15m"]["observed_sha256"] == "df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9"

    assert repro["reproduction_basis"]["clean_attempt_count"] == 2
    assert repro["reproduction_basis"]["clean_attempts_identical"] is True
    assert repro["population_reconciliation"]["counts_match_frozen"] is True
    assert repro["expected_frozen"]["census_sha256"] != repro["observed_reproduction"]["census_sha256"]
    assert repro["expected_frozen"]["ordered_trace_ids_sha256"] != repro["observed_reproduction"]["ordered_trace_ids_sha256"]
    assert repro["expected_frozen"]["observation_traces"]["sha256"] != repro["observed_reproduction"]["observation_traces"]["sha256"]
    assert all(repro["expected_frozen"]["checkpoints"][k] != repro["observed_reproduction"]["checkpoints"][k] for k in ("4392", "8784", "13176", "17568"))
    assert repro["result"] == "FAIL_G3_CONTENT_IDENTITY_MISMATCH"
    assert repro["stage1_reveal_allowed"] is False

    assert packet["authority_manifest_id"] == _cid(authority)
    assert packet["dependency_frontier_id"] == _cid(frontier)
    assert qa["qa_recommendation"] == "BLOCK"
    assert decision["decision"] == "BLOCK"
    assert decision["authority_delta"] == "NONE"
    assert decision["stage1_reveal_authorized"] is False
    assert decision["human_adjudication_started"] is False

    assert state["status"] == "BLOCKED"
    assert state["authority_delta"] == "NONE"
    assert state["human_adjudication_started"] is False
    assert state["stop_boundary"] == "ASOCSI-WP8-STAGED-REVEAL_NOT_AUTHORIZED_UNTIL_G3_REPRODUCIBLE"

    assert pointer["programme_id"] == current["programme_id"] == state["programme_id"]
    assert pointer["packet_id"] == current["packet_id"] == state["packet_id"]
    assert pointer["status"] == current["status"] == "BLOCKED"
    assert pointer["next_packet"] == current["next_packet"] == state["next_packet"]
    assert _state_generation(pointer["current_state"]) >= _state_generation(str(STATE.relative_to(ROOT)).replace("\\", "/"))
    assert current["human_adjudication_started"] is False
    assert current["stop_boundary"] == state["stop_boundary"]
    assert current["blockers"] == state["blockers"]
    if current_path != STATE.relative_to(ROOT):
        assert current["repository_effective"]["repository_effective"] is True
        assert current["frozen_g3_identity"]["census_sha256"] == repro["expected_frozen"]["census_sha256"]
        assert current["frozen_g3_identity"]["ordered_trace_ids_sha256"] == repro["expected_frozen"]["ordered_trace_ids_sha256"]
        assert current["frozen_g3_identity"]["observation_traces_sha256"] == repro["expected_frozen"]["observation_traces"]["sha256"]


def test_wp8_block_does_not_grant_reserved_or_reveal_authority():
    authority = _json(WP8 / "ASOCSI_WP8_AUTHORITY_MANIFEST_v0_1.json")
    non_grants = set(authority["non_grants"])
    assert authority["authority_delta"] == "NONE"
    assert authority["scientific_effect"] == "NONE"
    assert {"START_STAGE1_REVEAL", "HUMAN_FIDELITY_ADJUDICATION", "REVEAL_C2_OR_C2E_OR_OCCURRENCE_CONTEXT", "ALTER_G3_G4_G5_FROZEN_EVIDENCE", "SEMANTIC_REMEDIATION", "VALIDATION_OR_EC1_AUTHORITY", "PUBLICATION", "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION", "AGENT_WRITE"}.issubset(non_grants)
