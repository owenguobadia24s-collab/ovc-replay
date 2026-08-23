from __future__ import annotations

import json
from pathlib import Path

from tests.research_operations.p1cdi._court_state import assert_post_review5_current_state
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
PACKET = BASE / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_5_PACKET_v0_1.json"
MATERIALISATION = BASE / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_5_MATERIALISATION_RECORD_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
EXPECTED_PACKET_BLOB = "0c950abfeca8a962f9a87f0063b2241ad6bebd5d"


def test_review5_pass_is_review_only_closes_g4_and_releases_only_wp5() -> None:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    materialisation = json.loads(MATERIALISATION.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))

    assert packet["packet_id"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"
    assert packet["gate_id"] == "P1CDII-G4-ALG"
    assert packet["gate_class"] == "INDEPENDENT_BLOCKING"
    assert packet["status"] == "REVIEW_COMPLETE_PASS"
    assert packet["disposition"] == "PASS"
    assert packet["authority"]["authority_delta"] == "NONE"
    independence = packet["reviewer_independence"]
    assert independence["status"] == "PASS"
    assert independence["implementation_mutation"] == "NONE"
    assert independence["committed_test_or_fixture_mutation"] == "NONE"
    assert independence["programme_state_mutation_before_disposition"] == "NONE"
    assert independence["integration_or_successor_mutation_before_disposition"] == "NONE"
    assert independence["remediation_author_conclusion_substituted_for_review"] is False
    assert independence["independence_defects"] == []

    challenge = packet["independent_challenge"]
    assert len(packet["prior_immutable_g4_blockers"]) == 13
    assert set(challenge["blocker_dispositions"]) == set(packet["prior_immutable_g4_blockers"])
    assert set(challenge["blocker_dispositions"].values()) == {"REMEDIATED_CONFIRMED_CURRENT"}
    assert challenge["new_blockers_found"] == []
    assert packet["exact_current_assurance"]["blocking_assurance_failures"] == []
    assert packet["decision"]["gate_disposition"] == "PASS"
    assert packet["decision"]["g4_alg_result"] == "PASS"
    assert packet["decision"]["authority_delta"] == "NONE"
    assert packet["decision"]["successor"] == "P1CDII-WP5"
    assert packet["operator_decision_required_now"] is False

    source = materialisation["source_review_packet"]
    assert source["path"] == PACKET.relative_to(ROOT).as_posix()
    assert source["git_blob"] == EXPECTED_PACKET_BLOB
    assert source["disposition"] == "PASS"
    assert source["status"] == "REVIEW_COMPLETE_PASS"
    assert materialisation["authority_delta"] == "NONE"
    assert materialisation["gate_transition"] == {
        "P1CDII-G4-ALG": "PASS",
        "P1CDII-WP4": "COMPLETED",
        "next_packet": "P1CDII-WP5",
        "next_packet_state": "READY",
    }
    assert materialisation["operator_decision_required"] is False

    assert_post_review5_current_state(state)
    validate_contract(
        json.loads(
            (ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()
        ),
        state,
    )
