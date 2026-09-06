from __future__ import annotations

import json
from pathlib import Path

from ovc.development.programme_state_preflight import check_pointer

ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = ROOT / "records/research_operations/lsiac"
POINTER = STATE_ROOT / "CURRENT_STATE_POINTER.json"
HISTORICAL_WP1_BLOCKER = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_22.json"
PRIOR_WP1_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_24.json"
HISTORICAL_WP2_BLOCKER = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_25.json"
PRIOR_WP2_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_26.json"
HISTORICAL_WP3_BLOCKER = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_27.json"
PRIOR_WP3_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_28.json"
PRIOR_WP4_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_29.json"
PRIOR_WP5_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_30.json"
RRSCG_TERMINAL_STATE = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_31.json"
CURRENT_STATE = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_32.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_lsiac_current_state_pointer_preserves_rrscg_and_advances_mcac_without_rewriting_history():
    rows = check_pointer(POINTER, repository_root=ROOT)
    assert len(rows) == 1
    assert rows[0]["status"] == "PASS"
    assert rows[0]["reason"] == "POINTER_STATE_CONSISTENT"
    assert rows[0]["current_state"] == "LSIAC_PROGRAMME_STATE_v0_32.json"
    pointer = _load(POINTER)
    current = _load(CURRENT_STATE)
    rrscg_terminal = _load(RRSCG_TERMINAL_STATE)
    wp1_blocker = _load(HISTORICAL_WP1_BLOCKER)
    wp1_completed = _load(PRIOR_WP1_COMPLETED)
    wp2_blocker = _load(HISTORICAL_WP2_BLOCKER)
    wp2_completed = _load(PRIOR_WP2_COMPLETED)
    wp3_blocker = _load(HISTORICAL_WP3_BLOCKER)
    wp3_completed = _load(PRIOR_WP3_COMPLETED)
    wp4_completed = _load(PRIOR_WP4_COMPLETED)
    wp5_completed = _load(PRIOR_WP5_COMPLETED)
    assert pointer["historical_blocker_retained"] == HISTORICAL_WP1_BLOCKER.name
    assert pointer["prior_wp2_blocker_retained"] == HISTORICAL_WP2_BLOCKER.name
    assert pointer["prior_wp2_completed_retained"] == PRIOR_WP2_COMPLETED.name
    assert pointer["prior_wp3_blocker_retained"] == HISTORICAL_WP3_BLOCKER.name
    assert pointer["prior_wp3_completed_retained"] == PRIOR_WP3_COMPLETED.name
    assert pointer["prior_wp4_completed_retained"] == PRIOR_WP4_COMPLETED.name
    assert pointer["prior_wp5_completed_retained"] == PRIOR_WP5_COMPLETED.name
    assert pointer["prior_rrscg_terminal_retained"] == RRSCG_TERMINAL_STATE.name
    assert pointer["status"] == "COMPLETED"
    assert current["status"] == "COMPLETED"
    assert current["packet_id"] == "MCAC-ACC-v0.1"
    assert current["next_packet"] == "NONE_MCAC_V0_1_COMPLETE"
    assert current["blockers"] == []
    assert rrscg_terminal["packet_id"] == "RRSCG-CORE-WP5-PARITY-REPLAY-SCALE-QUALIFICATION"
    assert rrscg_terminal["next_packet"] == "NONE_RRSCG_CORE_COMPLETE"
    assert wp1_blocker["status"] == "BLOCKED"
    assert wp1_completed["status"] == "APPROVED"
    assert wp2_blocker["status"] == "BLOCKED"
    assert wp2_blocker["blockers"][0]["blocker_id"] == "RRSCG_CORE_WP2_D9_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert wp2_completed["status"] == "APPROVED"
    assert wp3_blocker["status"] == "BLOCKED"
    assert wp3_blocker["blockers"][0]["blocker_id"] == "RRSCG_CORE_WP3_D10_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert wp3_completed["status"] == "APPROVED"
    assert wp4_completed["status"] == "APPROVED"
    assert wp5_completed["status"] == "COMPLETED"
