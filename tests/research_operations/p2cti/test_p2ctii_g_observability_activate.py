from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json"
DECISION_PATH = (
    ROOT / "docs/programmes/p2cti-v0-1/wp9/"
    "P2CTII_G_OBSERVABILITY_ACTIVATE_OPERATOR_DECISION_v0_1.json"
)
RECEIPT_PATH = (
    ROOT / "docs/programmes/p2cti-v0-1/wp9/"
    "P2CTII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT_v0_1.json"
)

NON_GRANTS = [
    "RESEARCH_CONSOLE_SOURCE_PRESENTATION_AUTHORITY",
    "P2CTI_CONTINUOUS_INTAKE_WRITES",
    "THEORY_SEMANTIC_FREEZE",
    "P2_6_CANDIDATE_FORMATION",
    "RESEARCH_CANDIDATE_GENERATION_FREEZE",
    "OPT_C_ADMISSION",
    "CAPABILITY_ACTIVATION",
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
    assert decision["gate_id"] == "P2CTII-G-OBSERVABILITY-ACTIVATE"
    assert decision["decision"] == "PASS"
    assert decision["authority"] == "OPERATOR"
    assert decision["operator_instruction"] == "OVC APPROVE P2CTII-G-OBSERVABILITY-ACTIVATE PASS"
    assert decision["decision_baseline_main"] == "39cf15a21a98192cae7883bcb99a9af93fa2d27c"
    assert decision["decision_baseline_tree"] == "3b31c9171fcc7a3a9bbdeb303484cb9b5e8a8b38"
    assert decision["approved_authority_delta"] == "OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION"
    assert decision["operational_reliance"] is True
    assert decision["research_console_consumer_admission"] == "NOT_GRANTED"
    assert decision["continuous_intake_writes"] == "NOT_GRANTED"
    assert decision["explicit_non_grants"] == NON_GRANTS
    assert decision["next_packet"] == "P2CTII-WP10"
    assert decision["next_reserved_gate"] == "P2CTII-G-CONTINUOUS-INTAKE"


def test_activation_receipt_does_not_grant_write_or_consumer_authority() -> None:
    receipt = _load(RECEIPT_PATH)
    assert receipt["activation"] == "ACTIVE_OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION"
    assert receipt["operational_reliance"] is True
    assert receipt["read_only"] is True
    assert receipt["operational_current_pointer_publication"] == "ALLOWED_P2CTI_OPERATIONAL_READ_ONLY_ONLY"
    assert receipt["research_console_consumer_admission"] is False
    assert receipt["durable_continuous_intake_writes"] is False
    assert receipt["theory_semantic_freeze"] is False
    assert receipt["candidate_formation"] is False
    assert receipt["validation"] is False
    assert receipt["publication"] is False
    assert receipt["probability_risk_exposure_trading_execution"] is False
    assert receipt["agent_write"] is False
    assert receipt["authority_effect"] == "OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION"


def test_programme_advances_only_to_auto_wp10() -> None:
    state = _load(STATE_PATH)
    assert state["packet_id"] == "P2CTII-WP10"
    assert state["status"] == "READY"
    assert state["authority_required"] == "AUTO_EXECUTABLE"
    assert state["authority_delta"] == "NONE"
    assert state["decision_bearing_currentness_eligibility"] == "OPERATIONAL_READ_ONLY_CURRENT_PROJECTION_ACTIVE"
    assert state["operational_current_pointer_publication"] == "ALLOWED_P2CTI_OPERATIONAL_READ_ONLY_ONLY"
    assert state["p2ctii_observability_gate_status"] == "PASS_ACTIVE"
    assert state["operational_reliance"] is True
    assert state["research_console_source_admission_packet"] == "PRODUCER_READY_CONSUMER_ADMISSION_NOT_GRANTED"
    assert state["reserved_later_gates"] == ["P2CTII-G-CONTINUOUS-INTAKE"]
    assert state["explicit_non_grants"] == NON_GRANTS
    assert state["required_return_gate"] == "P2CTII-G-CONTINUOUS-INTAKE"
