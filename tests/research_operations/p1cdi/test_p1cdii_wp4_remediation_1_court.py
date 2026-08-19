from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_remediation_court_record_grants_no_g4_pass_or_successor_authority() -> None:
    base = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
    implementation = json.loads((base / "P1CDII_WP4_REMEDIATION_1_IMPLEMENTATION_PACKET_v0_1.json").read_text())
    qa = json.loads((base / "P1CDII_WP4_REMEDIATION_1_QA_PACKET_v0_1.json").read_text())
    decision = json.loads((base / "P1CDII_WP4_REMEDIATION_1_DECISION_v0_1.json").read_text())
    state = json.loads((ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json").read_text())
    assert implementation["immutable_block"]["packet_sha256"] == "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35"
    assert implementation["oracle_successor"]["old_sha256"] == "1538a3406bcea04c047bdddf9e66f22a96b1ed78fde5b3e88427590c2104ffb8"
    assert implementation["oracle_successor"]["new_sha256"] == "81ee71dd614606dc9fece46f5b5b0822de7b2812f1d4d641cdedc23355935c21"
    assert implementation["authority_delta"] == "NONE"
    assert implementation["remediation_author_may_issue_g4_alg_pass"] is False
    assert qa["g4_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_CONFLICT_FREE_REVIEW"
    assert decision["decision"] == "PASS_REMEDIATION"
    assert decision["p1cdii_g4_alg"]["current_status"] == "UNRESOLVED"
    assert decision["successor_beyond_wp4_authorised"] is False
    assert state["status"] == "GATE_READY"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-1"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-2"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-2"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-3"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-3"]["status"] == "BLOCKED"
    assert state["packets"]["P1CDII-WP4-REMEDIATION-4"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"]["status"] == "READY"
    assert state["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-4"
