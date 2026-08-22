from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]


def test_remediation_2_court_record_grants_no_g4_pass_or_successor_authority() -> None:
    base = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
    prior_block = base / "P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json"
    fresh_block = base / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
    implementation = json.loads((base / "P1CDII_WP4_REMEDIATION_2_IMPLEMENTATION_PACKET_v0_1.json").read_text())
    qa = json.loads((base / "P1CDII_WP4_REMEDIATION_2_QA_PACKET_v0_1.json").read_text())
    decision = json.loads((base / "P1CDII_WP4_REMEDIATION_2_DECISION_v0_1.json").read_text())
    state = json.loads((ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json").read_text())
    assert hashlib.sha256(prior_block.read_bytes()).hexdigest() == "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35"
    assert hashlib.sha256(fresh_block.read_bytes()).hexdigest() == "2d6651e4fddf567292df59ed53c539de558b7afeea9b789a290ac4cc7daf2e19"
    assert implementation["implementation_commit"] == "8c7ed2251d23e4f5b9e431c380eba337c6f522dd"
    assert implementation["oracle_successor"]["original_wp4_sha256"] == "1538a3406bcea04c047bdddf9e66f22a96b1ed78fde5b3e88427590c2104ffb8"
    assert implementation["oracle_successor"]["remediation_1_sha256"] == "81ee71dd614606dc9fece46f5b5b0822de7b2812f1d4d641cdedc23355935c21"
    assert implementation["oracle_successor"]["remediation_2_sha256"] == "4ff86f58bfe5e5f64ebbc403cbcf579eb4a166cdc3c93d1ed01c169a1e410106"
    assert implementation["authority_delta"] == "NONE"
    assert implementation["remediation_author_may_issue_g4_alg_pass"] is False
    assert qa["g4_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_CONFLICT_FREE_REVIEW_2"
    assert decision["decision"] == "PASS_REMEDIATION"
    assert decision["p1cdii_g4_alg"]["current_status"] == "UNRESOLVED"
    assert decision["successor_beyond_wp4_authorised"] is False
    assert state["status"] == "GATE_READY"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-1"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-2"]["status"] == "COMPLETED"
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
