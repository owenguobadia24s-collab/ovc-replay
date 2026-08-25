from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.programme_genesis.grt_v0_2.debt import (
    DebtValidationError,
    G4_CANDIDATE_FINDING_ID,
    G4_GRANDFATHERED_FINDING_ID,
    validate_debt_floor,
    validate_g4_current_projection_substitution,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
G4 = ROOT / "docs/programmes/grt-v0-2/g4"
IMPL = ROOT / "registries/implementation/grt_v0_2"
GOV = ROOT / "registries/governance/grt_v0_2"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_logical(record):
    payload = dict(record)
    logical_sha256 = payload.pop("logical_sha256")
    assert logical_sha256 == canonical_sha256(payload)


def finding(finding_id: str):
    return {
        "finding_id": finding_id,
        "rule_id": "GRT-R300",
        "debt_extent": {"accepted_native_genesis_binding_count": 0},
    }


def test_exact_operator_pass_and_gate_binding():
    decision = load(G4 / "GRT2_G4_OPERATOR_DECISION.json")
    check_logical(decision)
    assert decision["operator_instruction"] == "OVC APPROVE GRT2-G4 PASS"
    assert decision["decision"] == "PASS"
    assert decision["approved_gate_packet"]["logical_sha256"] == "028257fd9e7c19e5e03031fc09e932ec71411a08bdabc8b203ebfc25d6e62354"
    assert decision["next_packet"] == "GRT2-WP5"


def test_substitution_validator_is_exact_and_fail_closed():
    decision = load(G4 / "GRT2_G4_OPERATOR_DECISION.json")
    before = {G4_GRANDFATHERED_FINDING_ID: finding(G4_GRANDFATHERED_FINDING_ID)}
    after = {G4_CANDIDATE_FINDING_ID: finding(G4_CANDIDATE_FINDING_ID)}
    assert validate_g4_current_projection_substitution(decision, before, after) == {
        G4_GRANDFATHERED_FINDING_ID: G4_CANDIDATE_FINDING_ID
    }
    tampered = copy.deepcopy(decision)
    tampered["approved_authority_delta"]["exact_current_projection_substitution"]["scope"] = "ANY"
    payload = dict(tampered)
    payload.pop("logical_sha256")
    tampered["logical_sha256"] = canonical_sha256(payload)
    with pytest.raises(DebtValidationError, match="SUBSTITUTION_NOT_EXACT"):
        validate_g4_current_projection_substitution(tampered, before, after)


def test_current_projection_and_wp5_boundary():
    pointer = load(IMPL / "CURRENT_STATE_POINTER.json")
    state = load(ROOT / pointer["current_state"])
    check_logical(state)
    assert pointer["gate_id"] == state["gate_id"] == "GRT2-G4"
    assert pointer["next_packet"] == state["next_packet"] == "GRT2-WP5"
    assert state["operator_decision"] == "PASS"
    assert state["wp5_status"] == "NOT_STARTED"
    assert state["proposed_current_projection_substitution"]["status"] == "APPROVED_PENDING_MAIN_MATERIALISATION"


def test_generation_two_floor_contains_exact_substituted_census():
    pointer = load(GOV / "GRT_DEBT_FLOOR_CURRENT.json")
    floor = load(ROOT / pointer["definition"])
    check_logical(pointer)
    validate_debt_floor(floor)
    ids = set(floor["open_grandfathered_findings"])
    assert pointer["generation"] == floor["generation"] == 2
    assert len(ids) == 1648
    assert G4_GRANDFATHERED_FINDING_ID not in ids
    assert G4_CANDIDATE_FINDING_ID in ids
    assert floor["predecessor_commit"] == "fb0f7a2f7cafca7ee8073d65e071b7c2c922b77e"


def test_authority_manifest_and_frontier_are_hash_bound():
    manifest = load(G4 / "GRT2_G4_AUTHORITY_MANIFEST.json")
    frontier = load(G4 / "GRT2_G4_DEPENDENCY_FRONTIER.json")
    assert manifest["authority_manifest_id"] == canonical_sha256(manifest["authority_manifest"])
    assert frontier["dependency_frontier_id"] == canonical_sha256(frontier["dependency_frontier"])
