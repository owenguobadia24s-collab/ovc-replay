from __future__ import annotations

import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_3_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
BLOCKER = "P1CDII_G4_ALG_FRESH_REVIEW_3_BLOCK_001_ORPHAN_GENERATION_SERIES_ROOT_NOT_PROVEN"


def test_fresh_review_3_block_is_materialised_without_pass_or_authority_gain() -> None:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))

    assert packet["packet_id"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-3"
    assert packet["gate_decision"] == "BLOCK"
    assert packet["authority_delta"] == "NONE"
    assert packet["operator_decision_required_now"] is False
    assert packet["successor_beyond_wp4_authorised"] is False
    assert packet["wp5_authorised"] is False
    assert packet["discrepancies"] == [
        {
            **packet["discrepancies"][0],
            "id": BLOCKER,
            "severity": "BLOCKING",
        }
    ]

    review = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-3"]
    remediation = state["packets"]["P1CDII-WP4-REMEDIATION-4"]
    assert state["status"] == "GATE_READY"
    assert review["status"] == "BLOCKED"
    assert review["authority_delta"] == "NONE"
    assert review["blockers"] == [BLOCKER]
    assert review["next_packet"] == "P1CDII-WP4-REMEDIATION-4"
    assert remediation["status"] == "COMPLETED"
    assert remediation["authority_required"] == "AUTO_EXECUTABLE"
    assert remediation["authority_delta"] == "NONE"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-5"]["status"] == "READY"
    assert state["next_packet"] == "P1CDII-WP4-REMEDIATION-5"
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"

    validate_contract(
        json.loads(
            (
                ROOT
                / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json"
            ).read_text(encoding="utf-8")
        ),
        state,
    )
