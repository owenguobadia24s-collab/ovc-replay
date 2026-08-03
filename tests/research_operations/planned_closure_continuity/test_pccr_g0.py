from __future__ import annotations
import copy
import json
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "fixtures/research_operations/planned_closure_continuity/valid_scheduled_closure_fixture_v0_1.json").read_text(encoding="utf-8"))
GATE = json.loads((ROOT / "docs/releases/planned-closure-continuity-remediation-v0-1/pccr-g0/PCCR_G0_OPERATOR_GATE_PACKET.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "registries/research_operations/planned_closure_continuity/PCCR_G0_PREPARATION_STATE_v0_1.json").read_text(encoding="utf-8"))

class PCCRPlanError(ValueError):
    pass

def require(value: bool, marker: str) -> None:
    if not value:
        raise PCCRPlanError(marker)

def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def validate_fixture(value: dict) -> None:
    require(value.get("schema") == "ovc-pccr-scheduled-closure-fixture/v1", "FIXTURE_SCHEMA")
    require(value.get("fixture_only") is True, "FIXTURE_ONLY")
    require(value.get("instrument") == "GBPUSD", "INSTRUMENT_SCOPE")
    closures = value.get("closures")
    require(isinstance(closures, list) and closures, "CLOSURES")
    for item in closures:
        require(item.get("classification") == "SCHEDULED_MARKET_CLOSURE", "CLASSIFICATION")
        require(parse_time(item["scheduled_close"]) < parse_time(item["scheduled_open"]), "INTERVAL")
        require(item.get("bars_created") == 0 and item.get("prices_created") == 0, "SYNTHETIC_DATA")
        require(item.get("first_valid_rule") == "FIRST_COMPLETED_POST_OPEN_OBSERVATION", "FIRST_VALID")
    require(value.get("authority") == {"status":"FIXTURE_ONLY_NON_EVIDENTIARY","activation":"DENIED"}, "FIXTURE_AUTHORITY")

def validate_gate(value: dict) -> None:
    require(value.get("schema") == "ovc-pccr-g0-operator-gate-packet/v1", "GATE_SCHEMA")
    require((value.get("programme_id"), value.get("plan_id"), value.get("gate_id")) == ("OVC-PCCR-v0.1", "OVC-PLANNED-CLOSURE-CONTINUITY-REMEDIATION-IMPLEMENTATION-PLAN-0.1", "PCCR-G0"), "GATE_IDENTITY")
    require(value.get("source_decision") == "CCR-G5.OPERATOR.PASS.20260803T194600+0100", "SOURCE_DECISION")
    require(value.get("status") == "GATE_READY" and value.get("operator_decision_required") is True, "OPERATOR_GATE")
    require(value.get("proposed_delta") == "AUTHORISE_FORMAL_PCCR_ADMISSION_AND_OVC_OWNED_GBPUSD_CLOSURE_CALENDAR_AND_NON_CANONICAL_CLOSURE_AWARE_CONTINUITY_SHADOW_ONLY", "DELTA")
    boundary = value.get("authority_boundary", {})
    expected = {"formal_programme_admission":"DENIED_PENDING_PCCR_G0","current_clock":"2H_A_L_UTC_AUTHORITATIVE_UNCHANGED","provider_gap_handling":"STRICT_FAIL_CLOSED_UNCHANGED","continuity_activation":"DENIED","synthetic_bars_or_interpolation":"DENIED","c2e_c25_resumption":"DENIED","validation_publication_probability_risk_exposure_execution":"NONE"}
    for key, expected_value in expected.items():
        require(boundary.get(key) == expected_value, f"AUTHORITY:{key}")
    baseline = value.get("binding_baseline", {})
    require((baseline.get("scheduled_closures_per_side"), baseline.get("potentially_affected_state_scope_rows"), baseline.get("scheduled_closure_location_recovery_median_bars")) == (4, 496, 31), "BASELINE")

def validate_state(value: dict) -> None:
    require(value.get("schema") == "ovc-pccr-g0-preparation-state/v1", "STATE_SCHEMA")
    require(value.get("admission_status") == "NOT_ADMITTED", "ADMISSION_ESCAPE")
    require(value.get("status") == "GATE_READY" and value.get("current_gate") == "PCCR-G0", "STATE_GATE")
    require(value.get("operator_decision_required") is True, "STATE_OPERATOR")
    require(value.get("authority", {}).get("current") == "PLAN_PREPARATION_ONLY", "STATE_AUTHORITY")
    require(value.get("authority", {}).get("formal_programme_admission") == "DENIED_PENDING_PCCR_G0", "STATE_ADMISSION")
    require(value.get("authority", {}).get("continuity_activation") == "DENIED", "STATE_ACTIVATION")
    require(value.get("next_action") == "OPERATOR_DECIDE_PCCR_G0", "STATE_NEXT")

class PCCRPlanTests(unittest.TestCase):
    def test_fixture_gate_and_preparation_state_pass(self):
        validate_fixture(FIXTURE)
        validate_gate(GATE)
        validate_state(STATE)

    def test_synthetic_bar_blocks(self):
        value = copy.deepcopy(FIXTURE)
        value["closures"][0]["bars_created"] = 1
        with self.assertRaises(PCCRPlanError):
            validate_fixture(value)

    def test_provider_gap_relaxation_blocks(self):
        value = copy.deepcopy(GATE)
        value["authority_boundary"]["provider_gap_handling"] = "RELAXED"
        with self.assertRaises(PCCRPlanError):
            validate_gate(value)

    def test_new_instrument_blocks(self):
        value = copy.deepcopy(FIXTURE)
        value["instrument"] = "XAUUSD"
        with self.assertRaises(PCCRPlanError):
            validate_fixture(value)

    def test_activation_blocks(self):
        value = copy.deepcopy(GATE)
        value["authority_boundary"]["continuity_activation"] = "APPROVED"
        with self.assertRaises(PCCRPlanError):
            validate_gate(value)

    def test_formal_admission_blocks_before_operator_pass(self):
        value = copy.deepcopy(STATE)
        value["admission_status"] = "ADMITTED"
        with self.assertRaises(PCCRPlanError):
            validate_state(value)

if __name__ == "__main__":
    unittest.main()
