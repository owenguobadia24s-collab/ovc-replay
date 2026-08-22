from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]


def test_remediation_3_court_record_grants_no_g4_pass_or_successor_authority() -> None:
    base = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
    block_hashes = {
        "P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json": "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35",
        "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json": "2d6651e4fddf567292df59ed53c539de558b7afeea9b789a290ac4cc7daf2e19",
        "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_2_PACKET_v0_1.json": "894d31b1dd1c7408f3fd3f7d65f917fe744c72b23bef33a15560992fdb6b7580",
    }
    assert {
        name: hashlib.sha256((base / name).read_bytes()).hexdigest()
        for name in block_hashes
    } == block_hashes
    implementation = json.loads((base / "P1CDII_WP4_REMEDIATION_3_IMPLEMENTATION_PACKET_v0_1.json").read_text())
    qa = json.loads((base / "P1CDII_WP4_REMEDIATION_3_QA_PACKET_v0_1.json").read_text())
    decision = json.loads((base / "P1CDII_WP4_REMEDIATION_3_DECISION_v0_1.json").read_text())
    review_3 = json.loads((base / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_3_PACKET_v0_1.json").read_text())
    state = json.loads((ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json").read_text())
    assert implementation["reviewed_lawful_main"] == {
        "commit": "a1fa68a682b7400bb0702db488e9f109a9c739ed",
        "tree": "82fc2195648d898cba0375660ddf90eaa6b41a76",
    }
    assert implementation["implementation_commit"] == "e67f744de97e8b4f7e210afc588a08a772895711"
    assert implementation["implementation_tree"] == "a76907f452cf7ed6e3383593c57897717b73a0bc"
    assert implementation["oracle"]["sha256"] == "4ff86f58bfe5e5f64ebbc403cbcf579eb4a166cdc3c93d1ed01c169a1e410106"
    assert implementation["oracle"]["bytes"] == 15215
    assert implementation["authority_delta"] == "NONE"
    assert implementation["remediation_author_may_issue_g4_alg_pass"] is False
    assert qa["g4_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_CONFLICT_FREE_REVIEW_3"
    assert decision["decision"] == "PASS_REMEDIATION"
    assert decision["p1cdii_g4_alg"]["current_status"] == "UNRESOLVED"
    assert decision["successor_beyond_wp4_authorised"] is False
    assert review_3["gate_decision"] == "BLOCK"
    assert review_3["authority_delta"] == "NONE"
    assert review_3["successor_beyond_wp4_authorised"] is False
    assert state["status"] == "GATE_READY"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-2"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-3"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-3"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-4"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-5"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"]["status"] == "READY"
    assert state["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"
    validate_contract(
        json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()),
        state,
    )
