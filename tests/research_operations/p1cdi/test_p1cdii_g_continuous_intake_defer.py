from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DECISION_PATH = (
    ROOT
    / "docs/programmes/p1cdi-v0-1/wp11/P1CDII_G_CONTINUOUS_INTAKE_OPERATOR_DECISION_v0_1.json"
)
STATE_PATH = (
    ROOT
    / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_4_CONTINUOUS_INTAKE_DEFERRED.json"
)
POINTER_PATH = ROOT / "registries/research_operations/p1cdi/CURRENT_P1CDII_STATE_POINTER.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_defer_grants_no_authority() -> None:
    decision = _load(DECISION_PATH)

    assert decision["gate_id"] == "P1CDII-G-CONTINUOUS-INTAKE"
    assert decision["decision"] == "DEFER"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["operator_instruction"] == "DEFER"
    assert decision["authority_delta"] == "NONE"
    assert decision["authority_after"] == {
        "operational_read_only": "ACTIVE_EXACT_QUALIFIED_SOURCE_SCOPE_ONLY",
        "continuous_intake": "DENIED",
        "research_console_consumer_admission": "NOT_GRANTED",
    }
    assert decision["exact_source_scope"]["current_subject_count"] == 0
    assert "P1CDI_CONTINUOUS_INTAKE_WRITES" in decision["explicit_non_grants"]


def test_deferred_state_preserves_completed_wp11_and_gate_boundary() -> None:
    state = _load(STATE_PATH)
    pointer = _load(POINTER_PATH)

    assert state["status"] == "DEFERRED_AT_OPERATOR_GATE"
    assert state["wp11"]["status"] == "COMPLETED_LOGICALLY_AND_PHYSICALLY"
    assert state["wp11"]["durable_write_effect"] is False
    assert state["continuous_intake_gate"]["decision"] == "DEFER"
    assert state["continuous_intake_gate"]["activation"] == "NOT_AUTHORISED"
    assert state["authority"]["continuous_intake"] == "DENIED"
    assert state["required_return_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"
    assert state["next_action"] == "AWAIT_EXPLICIT_OPERATOR_RECONSIDERATION"
    assert pointer["continuous_intake"] == "DENIED"
    assert pointer["authority_effect"] == "NONE_OPERATOR_DEFER_CONTINUOUS_INTAKE_REMAINS_DENIED"
