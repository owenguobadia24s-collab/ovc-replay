from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
PACKET = BASE / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_4_PACKET_v0_1.json"
MATERIALISATION = BASE / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_4_MATERIALISATION_RECORD_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
EXPECTED_SHA256 = "c93d4c78e5c4623736846151504ff0f67dcf9a37b530efde81251f5a753557ce"
BLOCKERS = [
    "P1CDII_G4_ALG_FRESH_REVIEW_4_BLOCK_001_DIRECT_ROOT_FAST_PATH_DOES_NOT_PROVE_FIRST_GENERATION_BINDING",
    "P1CDII_G4_ALG_FRESH_REVIEW_4_BLOCK_002_WRAPS_EXPOSES_UNGUARDED_CORRESPONDENCE_ENTRYPOINT",
]


def test_fresh_review_4_block_is_exact_immutable_and_routes_only_remediation_5() -> None:
    packet_bytes = PACKET.read_bytes()
    actual_sha256 = hashlib.sha256(packet_bytes).hexdigest()
    packet = json.loads(packet_bytes)
    materialisation = json.loads(MATERIALISATION.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))

    assert actual_sha256 == EXPECTED_SHA256, actual_sha256
    assert packet["packet_id"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"
    assert packet["gate_id"] == "P1CDII-G4-ALG"
    assert packet["gate_decision"] == "BLOCK"
    assert packet["authority_delta"] == "NONE"
    assert packet["successor_beyond_wp4_authorised"] is False
    assert packet["wp5_authorised"] is False
    assert [item["id"] for item in packet["discrepancies"]] == BLOCKERS

    source = materialisation["source_review"]
    assert materialisation["disposition"] == "BLOCK"
    assert materialisation["authority_delta"] == "NONE"
    assert materialisation["blockers"] == BLOCKERS
    assert source["commit"] == "48879e6dc39a00887d565352c86f1be15be8ed27"
    assert source["parent"] == "0360f22f3d59b3a2e1e7e5e98b0bcae58726ff69"
    assert source["packet_blob"] == "517fb55e0a0a52e26e6c1e8283a60325c6d9f7a4"
    assert source["packet_sha256"] == EXPECTED_SHA256
    assert source["reviewer_only_diff"] == {
        "files_changed": 1,
        "additions": 481,
        "deletions": 0,
        "only_path": "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_4_PACKET_v0_1.json",
        "verified": True,
    }
    assert source["immutable"] is True
    assert source["altered_or_reinterpreted"] is False
    assert materialisation["operator_decision_required_now"] is False

    review = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"]
    remediation = state["packets"]["P1CDII-WP4-REMEDIATION-5"]
    assert state["status"] == "GATE_READY"
    assert review["status"] == "BLOCKED"
    assert review["authority_delta"] == "NONE"
    assert review["blockers"] == BLOCKERS
    assert review["next_packet"] == "P1CDII-WP4-REMEDIATION-5"
    assert remediation["status"] == "COMPLETED"
    assert remediation["authority_required"] == "AUTO_EXECUTABLE"
    assert remediation["authority_delta"] == "NONE"
    assert remediation["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"
    assert state["blockers"] == []
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"]["status"] == "READY"
    assert state["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"
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
