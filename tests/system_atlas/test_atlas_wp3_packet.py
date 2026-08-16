from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP3 = ROOT / "docs/programmes/system-atlas-v0-1/wp3"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp3_gate_is_auto_pass_without_resolver_authority() -> None:
    gate = load(WP3 / "ATLAS_G3_GATE_PACKET.json")
    assert gate["gate_class"] == "AUTO"
    assert gate["recommended_decision"] == "AUTO_PASS"
    assert gate["proposed_delta"] == "NONE"
    assert "ATLAS-G4-ALG" in gate["warnings"][1]
    assert gate["blockers"] == []


def test_wp3_vit_bindings_are_canonical() -> None:
    for name in ("ATLAS_WP3_VIT_AUTHORITY_MANIFEST.json", "ATLAS_WP3_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP3 / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])


def test_wp3_manifest_currentness_record_is_content_addressed() -> None:
    record = load(WP3 / "ATLAS_WP3_MANIFEST_CURRENTNESS_RECORD.json")
    body = dict(record)
    observed_hash = body.pop("record_hash")
    assert canonical_sha256(body) == observed_hash
    assert record["status"] == "CURRENT"
    assert record["current_declarative_eligibility"] is True
    assert {row["status"] for row in record["source_comparisons"]} == {"MATCH"}
    assert record["canonical_promotion"] == "DENIED_PENDING_WP4_RESOLUTION"


def test_wp3_packet_preserves_read_only_boundaries() -> None:
    packet = load(WP3 / "ATLAS_WP3_IMPLEMENTATION_PACKET.json")
    assert packet["second_scanner_created"] is False
    assert packet["canonical_assertions_emitted"] == 0
    assert packet["owner_or_authority_state_resolved"] is False
    assert packet["research_console_source_admitted"] is False
    assert packet["grt_authority_activated"] is False
    assert packet["shared_systems_authority_activated"] is False
    assert packet["write_authority_created"] is False


def test_wp3_programme_pointer_is_consistent() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    for field in ("status", "current_packet", "current_gate", "next_packet"):
        assert pointer[field] == state[field]
    assert pointer["next_operator_gate"] == state["stop_boundary"]
