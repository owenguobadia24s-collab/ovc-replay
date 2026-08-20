from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_2_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
BLOCKERS = [
    "P1CDII_G4_ALG_FRESH_REVIEW_2_BLOCK_001_PARTIAL_ADMISSION_BYPASSES_GENERATION_BINDING",
    "P1CDII_G4_ALG_FRESH_REVIEW_2_BLOCK_002_CROSS_GROUP_SOURCE_IDENTITY_CONFLICT_NOT_RECONCILED",
    "P1CDII_G4_ALG_FRESH_REVIEW_2_BLOCK_003_RETROGRADE_SEMANTIC_SUCCESSOR_ACCEPTED",
]


def test_fresh_review_2_block_is_exact_and_routes_only_remediation_3() -> None:
    packet_bytes = PACKET.read_bytes()
    packet = json.loads(packet_bytes)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert hashlib.sha256(packet_bytes).hexdigest() == "894d31b1dd1c7408f3fd3f7d65f917fe744c72b23bef33a15560992fdb6b7580"
    assert packet["reviewed_frontier"]["latest_lawful_main_commit"] == "cc24d44d427c73e874043b2eccf82d754de5ca39"
    assert packet["reviewed_frontier"]["latest_lawful_main_tree"] == "77e780009f44c757638f11649913629439a97257"
    assert packet["gate_decision"] == "BLOCK"
    assert packet["authority_delta"] == "NONE"
    assert packet["successor_beyond_wp4_authorised"] is False
    assert [item["id"] for item in packet["discrepancies"]] == BLOCKERS
    review = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-2"]
    assert state["status"] == "GATE_READY"
    assert review["status"] == "BLOCKED"
    assert review["authority_delta"] == "NONE"
    assert review["blockers"] == BLOCKERS
    assert review["next_packet"] == "P1CDII-WP4-REMEDIATION-3"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-2"]["status"] == "COMPLETED"
    remediation = state["packets"]["P1CDII-WP4-REMEDIATION-3"]
    assert remediation["status"] == "COMPLETED"
    assert remediation["authority_delta"] == "NONE"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-3"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-4"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-5"]["status"] == "READY"
    assert state["next_packet"] == "P1CDII-WP4-REMEDIATION-5"
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"
    validate_contract(
        json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()),
        state,
    )
