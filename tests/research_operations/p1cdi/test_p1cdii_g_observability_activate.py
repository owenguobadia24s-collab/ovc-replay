from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/p1cdi-v0-1/wp10"
DECISION_PATH = BASE / "P1CDII_G_OBSERVABILITY_ACTIVATE_OPERATOR_DECISION_v0_1.json"
RECEIPT_PATH = BASE / "P1CDII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT_v0_1.json"
STATE_PATH = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_2_OBSERVABILITY_ACTIVE.json"
POINTER_PATH = ROOT / "registries/research_operations/p1cdi/CURRENT_P1CDII_STATE_POINTER.json"
PREDECESSOR_STATE_PATH = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"

NON_GRANTS = [
    "RESEARCH_CONSOLE_SOURCE_PRESENTATION_AUTHORITY",
    "P1CDI_CONTINUOUS_INTAKE_WRITES",
    "NEW_PATH1_REAL_SOURCE_INTAKE",
    "CANDIDATE_OR_FREEZE_AUTHORITY",
    "SCIENTIFIC_DISPOSITION_WRITE",
    "VALIDATION",
    "PUBLICATION",
    "PROBABILITY",
    "RISK",
    "EXPOSURE",
    "TRADING",
    "EXECUTION",
    "AGENT_WRITE",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_pass_is_exact_and_scope_bounded() -> None:
    decision = _load(DECISION_PATH)
    assert decision["gate_id"] == "P1CDII-G-OBSERVABILITY-ACTIVATE"
    assert decision["decision"] == "PASS"
    assert decision["authority"] == "OPERATOR"
    assert decision["operator_instruction"] == "OVC APPROVE P1CDII-G-OBSERVABILITY-ACTIVATE"
    assert decision["decision_baseline_main"] == "f982af3834009c58ffa93c37bde62a95fecc39c7"
    assert decision["decision_baseline_tree"] == "8ed6ba1c811900b580289b035b81203665429ef5"
    assert decision["approved_authority_delta"] == "ACTIVATE_OPERATIONAL_READ_ONLY_P1CDI_CURRENT_PROJECTION_ONLY"
    assert decision["operational_reliance"] is True
    assert decision["exact_source_scope"]["expected_subject_count"] == 0
    assert decision["exact_source_scope"]["reconciled_subject_count"] == 0
    assert decision["research_console_consumer_admission"] == "NOT_GRANTED"
    assert decision["continuous_intake_writes"] == "NOT_GRANTED"
    assert decision["explicit_non_grants"] == NON_GRANTS
    assert decision["next_packet"] == "P1CDII-WP11"
    assert decision["next_reserved_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"


def test_activation_receipt_grants_read_only_reliance_and_nothing_more() -> None:
    receipt = _load(RECEIPT_PATH)
    assert receipt["activation"] == "ACTIVE_OPERATIONAL_READ_ONLY_P1CDI_CURRENT_PROJECTION_EXACT_SCOPE_ONLY"
    assert receipt["operational_reliance"] is True
    assert receipt["read_only"] is True
    assert receipt["exact_source_scope"]["current_subject_count"] == 0
    assert receipt["research_console_consumer_admission"] is False
    assert receipt["durable_continuous_intake_writes"] is False
    assert receipt["new_path1_real_source_intake"] is False
    assert receipt["candidate_or_freeze_authority"] is False
    assert receipt["scientific_disposition_write"] is False
    assert receipt["validation"] is False
    assert receipt["publication"] is False
    assert receipt["probability_risk_exposure_trading_execution"] is False
    assert receipt["agent_write"] is False
    assert receipt["automatic_source_scope_expansion"] is False
    assert receipt["authority_effect"] == "ACTIVATE_OPERATIONAL_READ_ONLY_P1CDI_CURRENT_PROJECTION_ONLY"


def test_current_state_pointer_supersedes_stale_gate_ready_projection() -> None:
    predecessor = _load(PREDECESSOR_STATE_PATH)
    assert predecessor["authority"]["operational_read_only"] == "DENIED"
    assert predecessor["packets"]["P1CDII-G-OBSERVABILITY-ACTIVATE"]["status"] == "GATE_READY"

    pointer = _load(POINTER_PATH)
    state = _load(STATE_PATH)
    assert pointer["current_state"].endswith("P1CDII_PROGRAMME_STATE_v0_2_OBSERVABILITY_ACTIVE.json")
    assert pointer["supersedes_state"].endswith("P1CDII_PROGRAMME_STATE_v0_1.json")
    assert state["supersedes"].endswith("P1CDII_PROGRAMME_STATE_v0_1.json@blob:44ec479ae2f905ab30a8db000408a6ff97f7cf39")
    assert state["current_packet"] == "P1CDII-WP11"
    assert state["status"] == "READY"
    assert state["authority_required"] == "AUTO_EXECUTABLE"
    assert state["authority_delta"] == "NONE"
    assert state["authority"]["operational_read_only"] == "ACTIVE_EXACT_QUALIFIED_SOURCE_SCOPE_ONLY"
    assert state["authority"]["continuous_intake"] == "DENIED"
    assert state["observability_activation"]["status"] == "COMPLETED"
    assert state["observability_activation"]["decision"] == "PASS"
    assert state["observability_activation"]["operational_reliance"] is True
    assert state["required_return_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"
    assert state["reserved_later_gates"] == ["P1CDII-G-CONTINUOUS-INTAKE"]
    assert state["explicit_non_grants"] == NON_GRANTS
    assert state["blockers"] == []


def test_continuous_intake_and_consumer_admission_remain_separate_reserved_boundaries() -> None:
    state = _load(STATE_PATH)
    assert state["research_console_source_admission"] == "PRODUCER_READY_CONSUMER_ADMISSION_NOT_GRANTED"
    assert state["operational_current_pointer_publication"] == "ALLOWED_P1CDI_OPERATIONAL_READ_ONLY_EXACT_SCOPE_ONLY"
    assert state["required_return_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"
    assert "P1CDI_CONTINUOUS_INTAKE_WRITES" in state["explicit_non_grants"]

