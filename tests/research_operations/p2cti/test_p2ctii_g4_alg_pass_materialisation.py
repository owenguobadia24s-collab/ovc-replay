from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/programmes/p2cti-v0-1/wp4/P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_AFTER_REMEDIATION_2_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json"

EXPECTED_PACKET_SHA256 = "43d39278c947f9fdd73b8be539bd086026161ed82e9cc56e6ed9a5f7ff3534b3"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fresh_g4_pass_packet_is_immutable_and_complete() -> None:
    payload = PACKET.read_bytes()
    packet = json.loads(payload)
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_PACKET_SHA256
    assert packet["gate_id"] == "P2CTII-G4-ALG"
    assert packet["status"] == "REVIEW_COMPLETE_PASS"
    assert packet["gate_evaluation"]["decision"] == "PASS"
    assert packet["gate_evaluation"]["authority_delta"] == "NONE"
    assert packet["review_execution"]["review_matrix"] == {
        "total": 138,
        "pass": 138,
        "block": 0,
        "sections": packet["review_execution"]["review_matrix"]["sections"],
    }
    assert len(packet["review_execution"]["review_matrix"]["sections"]) == 11
    assert all(value.startswith("PASS_") for value in packet["review_execution"]["review_matrix"]["sections"].values())
    assert packet["review_execution"]["remediation_2_adversarial_reexecution"]["prior_fresh_blockers"] == "PASS_11_OF_11"
    assert packet["next_packet"] == "P2CTII-WP5"


def test_programme_state_preserves_g4_pass_without_reserved_authority() -> None:
    state = _load(STATE)
    completed = {packet["packet_id"]: packet for packet in state["completed_packets"]}
    assert state["p2ctii_g4_alg_status"] == "PASS"
    assert state["wp5_authorised"] is True
    assert "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2" in completed
    assert completed["P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2"]["decision"] == "PASS"
    assert completed["P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2"]["packet_sha256"] == EXPECTED_PACKET_SHA256
    assert state["blockers"] == []
    assert state["fresh_review_packet_sha256"] == EXPECTED_PACKET_SHA256

    # G4 itself never granted observability. A later explicit operator PASS may
    # lawfully consume only that reserved non-grant while preserving all later
    # authority boundaries.
    if state.get("p2ctii_observability_gate_status") == "PASS_ACTIVE":
        observability = completed["P2CTII-G-OBSERVABILITY-ACTIVATE"]
        assert observability["decision"] == "PASS"
        assert observability["authority_delta"] == "OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION"
        assert state["operational_current_pointer_publication"] == "ALLOWED_P2CTI_OPERATIONAL_READ_ONLY_ONLY"
        assert state["operational_reliance"] is True
        assert "P2CTI_OBSERVABILITY" not in state["explicit_non_grants"]
        assert "P2CTI_CONTINUOUS_INTAKE_WRITES" in state["explicit_non_grants"]
        assert state["reserved_later_gates"] == ["P2CTII-G-CONTINUOUS-INTAKE"]
    else:
        assert state["operational_current_pointer_publication"] == "DENIED_SEPARATELY_GOVERNED"
        assert "P2CTI_OBSERVABILITY" in state["explicit_non_grants"]
        assert "P2CTI_CONTINUOUS_INTAKE_WRITES" in state["explicit_non_grants"]
        assert state["reserved_later_gates"] == [
            "P2CTII-G-OBSERVABILITY-ACTIVATE",
            "P2CTII-G-CONTINUOUS-INTAKE",
        ]

    if state["packet_id"] == "P2CTII-G4-ALG":
        assert state["status"] == "APPROVED"
        assert state["next_packet"] == "P2CTII-WP5"
    else:
        assert state["packet_id"] in {
            "P2CTII-WP5",
            "P2CTII-WP6",
            "P2CTII-WP7",
            "P2CTII-WP8",
            "P2CTII-WP9",
            "P2CTII-G-OBSERVABILITY-ACTIVATE",
            "P2CTII-WP10",
        }
