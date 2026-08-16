from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP4 = ROOT / "docs/programmes/system-atlas-v0-1/wp4"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp4_gate_is_independent_non_operator_and_not_passed() -> None:
    gate = load(WP4 / "ATLAS_G4_ALG_GATE_PACKET.json")
    request = load(WP4 / "ATLAS_G4_ALG_REVIEW_REQUEST.json")
    assert gate["gate_class"] == "INDEPENDENT_REVIEW_BLOCKING_NON_OPERATOR"
    assert gate["recommended_decision"] == "PARK_PENDING_INDEPENDENT_REVIEW"
    assert gate["independent_review_status"] == "UNBOUND_NOT_PERFORMED"
    assert gate["blockers"] == ["ATLAS_G4_ALG_ELIGIBLE_INDEPENDENT_REVIEWER_UNBOUND"]
    assert request["operator_substitution_permitted"] is False
    assert request["self_attestation_permitted"] is False
    assert request["required_verdict"] == "ELIGIBLE_INDEPENDENT_PASS"


def test_wp4_vit_bindings_are_canonical() -> None:
    for name in ("ATLAS_WP4_VIT_AUTHORITY_MANIFEST.json", "ATLAS_WP4_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP4 / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])


def test_wp4_packet_preserves_read_only_boundaries() -> None:
    packet = load(WP4 / "ATLAS_WP4_IMPLEMENTATION_PACKET.json")
    assert packet["canonical_assertions_emitted"] == 0
    assert packet["owner_or_authority_state_published"] is False
    assert packet["optimized_resolver_accepted"] is False
    assert packet["research_console_source_admitted"] is False
    assert packet["grt_authority_activated"] is False
    assert packet["shared_systems_authority_activated"] is False
    assert packet["changed_scientific_semantics"] is False
    assert packet["write_authority_created"] is False
    assert packet["validation_consumed"] is False
    assert packet["canonical_publication"] is False


def test_wp4_review_evidence_identity_is_bound() -> None:
    qa = load(WP4 / "ATLAS_WP4_QA_PACKET.json")
    request = load(WP4 / "ATLAS_G4_ALG_REVIEW_REQUEST.json")
    expected = "2cf3879276cb8676890b631880222ad2c704760e3455b80ab482cd4647b0a1e6"
    assert qa["external_algorithm_review_evidence"]["sha256"] == expected
    assert request["review_evidence"]["sha256"] == expected
    assert qa["checks"]["canonical_assertions"] == "PASS_ZERO_PENDING_ATLAS_G4_ALG"


def test_wp4_programme_state_is_parked_and_wp5_is_ineligible() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    for field in ("status", "current_packet", "current_gate", "next_packet"):
        assert pointer[field] == state[field]
    assert state["current_gate"] == "ATLAS-G4-ALG"
    assert state["next_packet"] == "ATLAS-WP5"
    assert state["next_packet_eligibility"] == "DENIED_UNTIL_ATLAS_G4_ALG_PASS"
    assert pointer["next_operator_gate"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
