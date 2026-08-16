from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP2 = ROOT / "docs/programmes/system-atlas-v0-1/wp2"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp2_gate_is_auto_pass_without_authority_delta() -> None:
    gate = load(WP2 / "ATLAS_G2_GATE_PACKET.json")
    assert gate["gate_class"] == "AUTO"
    assert gate["recommended_decision"] == "AUTO_PASS"
    assert gate["proposed_delta"] == "NONE"
    assert gate["blockers"] == []


def test_wp2_vit_bindings_are_canonical() -> None:
    for name in ("ATLAS_WP2_VIT_AUTHORITY_MANIFEST.json", "ATLAS_WP2_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP2 / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])


def test_wp2_packet_preserves_all_reserved_boundaries() -> None:
    packet = load(WP2 / "ATLAS_WP2_IMPLEMENTATION_PACKET.json")
    assert packet["canonical_assertions_emitted"] == 0
    assert packet["owner_or_authority_state_inferred"] is False
    assert packet["grt_authority_activated"] is False
    assert packet["shared_systems_authority_activated"] is False
    assert packet["write_authority_created"] is False
    assert packet["canonical_publication"] is False


def test_wp2_programme_pointer_is_consistent() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    for field in ("status", "current_packet", "current_gate", "next_packet"):
        assert pointer[field] == state[field]
    assert pointer["next_operator_gate"] == state["stop_boundary"]
