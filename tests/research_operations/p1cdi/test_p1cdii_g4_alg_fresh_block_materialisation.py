from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
BLOCKERS = [
    "P1CDII_G4_ALG_FRESH_BLOCK_001_UNPROVEN_MULTIPLANE_AUTO_ADMISSION",
    "P1CDII_G4_ALG_FRESH_BLOCK_002_NONCANONICAL_PROJECTION_AUTO_ADMISSION",
    "P1CDII_G4_ALG_FRESH_BLOCK_003_DUPLICATE_SOURCE_RECORD_ID_CONFLICT_NOT_FAIL_CLOSED",
    "P1CDII_G4_ALG_FRESH_BLOCK_004_IDENTITY_RECORD_CONFLICT_ORDER_DEPENDENT",
]


def test_fresh_independent_block_packet_is_exact_and_routes_only_remediation_2() -> None:
    packet_bytes = PACKET.read_bytes()
    packet = json.loads(packet_bytes)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert hashlib.sha256(packet_bytes).hexdigest() == "2d6651e4fddf567292df59ed53c539de558b7afeea9b789a290ac4cc7daf2e19"
    assert packet["reviewed_frontier"]["latest_lawful_main"] == "bb313b004a3a4fa2be9f8141ddc5f56fd4b3ba86"
    assert packet["reviewed_frontier"]["latest_lawful_main_tree"] == "f414f69a14ffd8613c1c2cbcb2cb740f8395c744"
    assert packet["gate_decision"] == "BLOCK"
    assert packet["authority_delta"] == "NONE"
    assert packet["successor_beyond_wp4_authorised"] is False
    assert [item["id"] for item in packet["discrepancies"]] == BLOCKERS
    fresh = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW"]
    assert state["status"] == "GATE_READY"
    assert fresh["status"] == "BLOCKED"
    assert fresh["authority_delta"] == "NONE"
    assert fresh["blockers"] == BLOCKERS
    assert fresh["next_packet"] == "P1CDII-WP4-REMEDIATION-2"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-1"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-2"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-2"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-3"]["status"] == "COMPLETED"
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
