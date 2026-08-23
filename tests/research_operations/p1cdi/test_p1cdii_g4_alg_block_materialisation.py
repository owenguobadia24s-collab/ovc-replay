from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi._court_state import assert_post_review5_current_state
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"


def test_independent_block_packet_is_exact_and_history_survives_review5_pass() -> None:
    packet_bytes = PACKET.read_bytes()
    packet = json.loads(packet_bytes)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert hashlib.sha256(packet_bytes).hexdigest() == "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35"
    assert packet["gate_decision"] == "BLOCK"
    assert packet["authority_delta"] == "NONE"
    assert packet["reviewed_frontier"]["latest_lawful_main"] == "81faa31be2e59e47bc9784174f971c93a5a3a41c"
    assert_post_review5_current_state(state)
    validate_contract(
        json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()),
        state,
    )
