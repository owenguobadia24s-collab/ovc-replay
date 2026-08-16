from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP1 = ROOT / "docs/programmes/system-atlas-v0-1/wp1"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_atlas_g1_is_auto_pass_with_no_authority_delta() -> None:
    gate = load(WP1 / "ATLAS_G1_GATE_PACKET.json")
    assert gate["gate_class"] == "AUTO"
    assert gate["proposed_delta"] == "NONE"
    assert gate["blockers"] == []
    assert gate["recommended_decision"] == "AUTO_PASS"
    assert gate["next_packet"] == "ATLAS-WP1V"


def test_wp1_vit_authority_and_frontier_are_canonical() -> None:
    authority = load(WP1 / "ATLAS_WP1_VIT_AUTHORITY_MANIFEST.json")
    frontier = load(WP1 / "ATLAS_WP1_VIT_DEPENDENCY_FRONTIER.json")
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert authority["payload"]["authority_class"] == "AUTO_EXECUTABLE"
    assert authority["payload"]["authority_delta"].startswith("NONE_")
    assert frontier["payload"]["predecessor_requirement"] == "QUALIFIED_VIT_GENERATION_REQUIRED"


def test_programme_state_advances_to_wp1v_without_activation() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    packet_order = ["ATLAS-WP1", "ATLAS-WP1V", *[f"ATLAS-WP{index}" for index in range(2, 12)]]
    assert packet_order.index(state["current_packet"]) >= packet_order.index("ATLAS-WP1")
    if state["current_packet"] == "ATLAS-WP1":
        assert state["current_gate"] == "ATLAS-G1"
        assert state["next_packet"] == "ATLAS-WP1V"
    if state["current_gate"] == "ATLAS-G4-ALG":
        assert state["blockers"] == ["ATLAS_G4_ALG_ELIGIBLE_INDEPENDENT_REVIEWER_UNBOUND"]
    else:
        assert state["blockers"] == []
    assert state["stop_boundary"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
    assert pointer["next_operator_gate"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
