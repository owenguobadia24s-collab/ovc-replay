from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping

PROGRAMME_ID = "OVC-PCCR-v0.1"
PLAN_ID = "OVC-PLANNED-CLOSURE-CONTINUITY-REMEDIATION-IMPLEMENTATION-PLAN-0.1"
SOURCE_DECISION = "CCR-G5.OPERATOR.PASS.20260803T194600+0100"

class PCCRPlanError(ValueError):
    pass

def _require(value: bool, marker: str) -> None:
    if not value:
        raise PCCRPlanError(marker)

def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def validate_fixture(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("schema") == "ovc-pccr-scheduled-closure-fixture/v1", "FIXTURE_SCHEMA")
    _require(value.get("fixture_only") is True, "FIXTURE_MUST_BE_NON_EVIDENTIARY")
    _require(value.get("instrument") == "GBPUSD", "INSTRUMENT_SCOPE_ESCAPE")
    closures = value.get("closures")
    _require(isinstance(closures, list) and closures, "CLOSURES_REQUIRED")
    for item in closures:
        _require(item.get("classification") == "SCHEDULED_MARKET_CLOSURE", "PROVIDER_GAP_OR_UNKNOWN_NOT_ALLOWED")
        _require(_time(item["scheduled_close"]) < _time(item["scheduled_open"]), "INVALID_CLOSURE_INTERVAL")
        _require(item.get("bars_created") == 0 and item.get("prices_created") == 0, "SYNTHETIC_DATA_PROHIBITED")
        _require(item.get("first_valid_rule") == "FIRST_COMPLETED_POST_OPEN_OBSERVATION", "FIRST_VALID_RULE")
    authority = value.get("authority", {})
    _require(authority.get("status") == "FIXTURE_ONLY_NON_EVIDENTIARY", "FIXTURE_AUTHORITY")
    _require(authority.get("activation") == "DENIED", "ACTIVATION_ESCAPE")
    return {"status": "PASS", "closures": len(closures)}

def validate_gate(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("schema") == "ovc-pccr-g0-operator-gate-packet/v1", "GATE_SCHEMA")
    _require((value.get("programme_id"), value.get("plan_id"), value.get("gate_id")) == (PROGRAMME_ID, PLAN_ID, "PCCR-G0"), "GATE_IDENTITY")
    _require(value.get("source_decision") == SOURCE_DECISION, "SOURCE_DECISION")
    _require(value.get("status") == "GATE_READY" and value.get("operator_decision_required") is True, "GATE_NOT_OPERATOR_REQUIRED")
    _require(value.get("proposed_delta") == "AUTHORISE_OVC_OWNED_GBPUSD_CLOSURE_CALENDAR_AND_NON_CANONICAL_CLOSURE_AWARE_CONTINUITY_SHADOW_ONLY", "AUTHORITY_DELTA")
    boundary = value.get("authority_boundary", {})
    required = {
        "current_clock": "2H_A_L_UTC_AUTHORITATIVE_UNCHANGED",
        "provider_gap_handling": "STRICT_FAIL_CLOSED_UNCHANGED",
        "continuity_activation": "DENIED",
        "synthetic_bars_or_interpolation": "DENIED",
        "c2e_c25_resumption": "DENIED",
        "validation_publication_probability_risk_exposure_execution": "NONE",
    }
    for key, expected in required.items():
        _require(boundary.get(key) == expected, f"AUTHORITY_ESCAPE:{key}")
    baseline = value.get("binding_baseline", {})
    _require((baseline.get("scheduled_closures_per_side"), baseline.get("potentially_affected_state_scope_rows"), baseline.get("scheduled_closure_location_recovery_median_bars")) == (4, 496, 31), "BASELINE_EVIDENCE")
    return {"status": "PASS", "gate": "PCCR-G0"}

def validate_programme_state(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("schema") == "ovc-pccr-programme-state/v1", "STATE_SCHEMA")
    _require((value.get("programme_id"), value.get("plan_id")) == (PROGRAMME_ID, PLAN_ID), "STATE_IDENTITY")
    _require(value.get("status") == "GATE_READY" and value.get("current_gate") == "PCCR-G0", "STATE_NOT_GATE_READY")
    _require(value.get("operator_decision_required") is True, "STATE_OPERATOR_GATE")
    authority = value.get("authority", {})
    _require(authority.get("current") == "PLAN_PREPARATION_ONLY", "IMPLEMENTATION_AUTHORITY_ESCAPE")
    _require(authority.get("continuity_activation") == "DENIED", "STATE_ACTIVATION_ESCAPE")
    _require(value.get("next_action") == "OPERATOR_DECIDE_PCCR_G0", "STATE_NEXT_ACTION")
    return {"status": "PASS", "programme": PROGRAMME_ID}
