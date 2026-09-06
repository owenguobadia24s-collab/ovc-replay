from __future__ import annotations

import json
from pathlib import Path

from ovc.development.programme_state_preflight import check_pointer

ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = ROOT / "records/research_operations/lsiac"
POINTER = STATE_ROOT / "CURRENT_STATE_POINTER.json"
HISTORICAL_BLOCKER = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_22.json"
CURRENT_STATE = STATE_ROOT / "LSIAC_PROGRAMME_STATE_v0_24.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_lsiac_current_state_pointer_selects_forward_state_without_rewriting_blocker():
    rows = check_pointer(POINTER, repository_root=ROOT)
    assert rows == [
        {
            "pointer": "records/research_operations/lsiac/CURRENT_STATE_POINTER.json",
            "status": "PASS",
            "reason": "POINTER_STATE_CONSISTENT",
            "current_state": "LSIAC_PROGRAMME_STATE_v0_24.json",
            "programme_id": "OVC-LSIAC-v0.1",
            "packet_id": "RRSCG-CORE-WP1-R2-KERNEL-CONFORMANCE-IMPLEMENTATION",
            "next_packet": "RRSCG-CORE-WP2-D9-OBSERVER-STATE-FACULTY",
        }
    ]
    pointer = _load(POINTER)
    current = _load(CURRENT_STATE)
    blocker = _load(HISTORICAL_BLOCKER)
    assert pointer["historical_blocker_retained"] == HISTORICAL_BLOCKER.name
    assert current["status"] == "APPROVED"
    assert current["blockers"] == []
    assert blocker["status"] == "BLOCKED"
    assert blocker["blockers"][0]["blocker_id"] == "RRSCG_CORE_WP1_SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
