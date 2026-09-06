from __future__ import annotations

import json
from pathlib import Path

from ovc.development.programme_state_preflight import check_pointer

ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = ROOT / "records/research_operations/lsiac"
POINTER = STATE_ROOT / "CURRENT_STATE_POINTER.json"
HISTORICAL_BLOCKER = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_22.json"
PRIOR_COMPLETED = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_24.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_lsiac_current_state_pointer_selects_forward_state_without_rewriting_history():
    pointer = _load(POINTER)
    current_path = STATE_ROOT / pointer["current_state"]
    rows = check_pointer(POINTER, repository_root=ROOT)
    assert len(rows) == 1
    assert rows[0]["status"] == "PASS"
    assert rows[0]["reason"] == "POINTER_STATE_CONSISTENT"
    assert rows[0]["current_state"] == pointer["current_state"]
    current = _load(current_path)
    blocker = _load(HISTORICAL_BLOCKER)
    prior = _load(PRIOR_COMPLETED)
    assert pointer["historical_blocker_retained"] == HISTORICAL_BLOCKER.name
    assert pointer["prior_completed_state"] == PRIOR_COMPLETED.name
    assert current["programme_id"] == "OVC-LSIAC-v0.1"
    assert current["packet_id"] == pointer["current_packet"]
    assert current["status"] == pointer["status"]
    assert current["next_packet"] == pointer["next_packet"]
    assert prior["status"] == "APPROVED"
    assert prior["next_packet"] == "RRSCG-CORE-WP2-D9-OBSERVER-STATE-FACULTY"
    assert blocker["status"] == "BLOCKED"
    assert blocker["blockers"][0]["blocker_id"] == "RRSCG_CORE_WP1_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
