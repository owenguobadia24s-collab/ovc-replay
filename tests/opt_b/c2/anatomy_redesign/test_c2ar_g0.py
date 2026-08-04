from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-g0"
SOURCE = json.loads((BASE / "C2AR_G0_SOURCE_PLAN_HASH.json").read_text(encoding="utf-8"))
BASELINE = json.loads((BASE / "C2AR_G0_BASELINE_MANIFEST.json").read_text(encoding="utf-8"))
AUTHORITY = json.loads((BASE / "C2AR_G0_AUTHORITY_AND_CAPACITY_ENVELOPE.json").read_text(encoding="utf-8"))
QA = json.loads((BASE / "C2AR_G0_QA_PACKET.json").read_text(encoding="utf-8"))
GATE = json.loads((BASE / "C2AR_G0_OPERATOR_GATE_PACKET.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_PROGRAMME_PREPARATION_STATE_v0_2.json").read_text(encoding="utf-8"))

EXPECTED_PROGRAMME = "OVC-C2-ANATOMY-REDESIGN-v0.2"
EXPECTED_PLAN = "OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION"
EXPECTED_VERSION = "0.2-REVISED"
EXPECTED_GATE = "C2AR-G0"


class C2ARG0Error(ValueError):
    pass


def require(value: bool, marker: str) -> None:
    if not value:
        raise C2ARG0Error(marker)


def validate_identity(value: dict) -> None:
    require(value.get("programme_id") == EXPECTED_PROGRAMME, "PROGRAMME_ID")
    require(value.get("plan_id") == EXPECTED_PLAN, "PLAN_ID")
    require(value.get("plan_version") == EXPECTED_VERSION, "PLAN_VERSION")
    require(value.get("gate_id") == EXPECTED_GATE, "GATE_ID")


def validate_source(value: dict) -> None:
    validate_identity(value)
    source = value.get("source", {})
    require(source.get("sha256") == "b76fb70533ccba161eb9d043f393ff875a3bcf8170009dc0a380c234a04f628d", "SOURCE_HASH")
    require(source.get("size_bytes") == 78065, "SOURCE_SIZE")
    require(value.get("governing_design", {}).get("sha256") == "d51ab109481c4a4f84c5fd955c56521e1d27c853bb568168dc689bf5f5bbf1c9", "SCAFFOLD_HASH")
    require(value.get("verified_reads") == 2, "HASH_READS")


def validate_baseline(value: dict) -> None:
    validate_identity(value)
    require(value.get("lawful_main_tip") == "4d3ce5ecaf92897d69b1c7bf4945ca4f6935e606", "MAIN_TIP")
    active = value.get("active_c2_authority", {})
    require(active.get("state") == "ACTIVE_DISCOVERY", "ACTIVE_STATE")
    require(active.get("discovery_release_id") == "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", "ACTIVE_RELEASE")
    require(active.get("validation_consumption") == "LOCKED_UNCONSUMED", "VALIDATION_LOCK")
    require(active.get("mutation_under_c2ar_g0") == "DENIED", "ACTIVE_MUTATION")
    pccr = value.get("overlap_and_concurrency", {}).get("pccr", {})
    require(pccr.get("status") == "NOT_ADMITTED_GATE_READY", "PCCR_STATUS")
    require(pccr.get("execution_authority") == "DENIED", "PCCR_EXECUTION")
    require(value.get("raw_market_data_added") is False, "RAW_DATA")


def validate_authority(value: dict) -> None:
    validate_identity(value)
    current = value.get("current_authority", {})
    require(current.get("wp0_execution") == "DENIED_PENDING_C2AR_G0", "WP0_ESCAPE")
    require(current.get("active_c2_selector") == "UNCHANGED_ACTIVE_DISCOVERY", "SELECTOR")
    require(current.get("probability_risk_exposure_trading_execution") == "NONE", "EXPOSURE")
    delta = value.get("proposed_delta_on_pass", {})
    require(delta.get("release_packet") == "C2AR-WP0_ONLY", "DELTA_SCOPE")
    require(delta.get("market_or_selector_authority") == "NONE", "MARKET_AUTHORITY")
    maturity = value.get("contract_maturity", {})
    require(maturity.get("SHADOW_EXPERIMENT") == "MUTABLE_VERSIONED_THROUGH_WP5_5", "SHADOW_MATURITY")
    require(maturity.get("SHADOW_FROZEN") == "ONLY_AFTER_OPERATOR_REQUIRED_CEAR_G6", "FREEZE_GATE")
    require(value.get("capacity_policy", {}).get("capacity_exceeded") == "FAIL_CLOSED_PRESERVE_PARTIAL_DIAGNOSTIC_MANIFEST_NO_SILENT_SAMPLING", "CAPACITY")


def validate_state(value: dict) -> None:
    require(value.get("schema") == "ovc-c2ar-programme-preparation-state/v1", "STATE_SCHEMA")
    require(value.get("programme_id") == EXPECTED_PROGRAMME, "STATE_PROGRAMME")
    require(value.get("admission_status") == "NOT_RATIFIED", "STATE_ADMISSION")
    require(value.get("status") == "GATE_READY", "STATE_STATUS")
    require(value.get("current_gate") == EXPECTED_GATE, "STATE_GATE")
    require(value.get("operator_decision_required") is True, "STATE_OPERATOR")
    require(value.get("next_action") == "OPERATOR_DECIDE_C2AR_G0", "STATE_NEXT")
    packets = value.get("packets", [])
    require([item["packet_id"] for item in packets][:7] == ["C2AR-WP0", "C2AR-WP1", "C2AR-WP2", "C2AR-WP3", "C2AR-WP4", "C2AR-WP5", "C2AR-WP5.5"], "WP5_5_SEQUENCE")
    require(any(item["packet_id"] == "C2AR-WP6" and "OPERATOR_REQUIRED_CEAR_G6" in item["authority_required"] for item in packets), "G6_OPERATOR")


def validate_gate(value: dict) -> None:
    validate_identity(value)
    require(value.get("status") == "GATE_READY_PENDING_EXACT_HEAD_CI", "GATE_STATUS")
    require(value.get("operator_decision_required") is True, "GATE_OPERATOR")
    require(value.get("proposed_delta") == "RATIFY_REVISED_IMPLEMENTATION_PLAN_AND_RELEASE_C2AR_WP0_BASELINE_CONTROLS_ONLY", "GATE_DELTA")
    terms = set(value.get("ratified_terms_on_pass", []))
    require("MANDATORY_SYNTHETIC_END_TO_END_SMOKE_AT_C2AR_G5_5_BEFORE_CEAR_G6" in terms, "SMOKE_TERM")
    require("PCCR_REMAINS_NOT_ADMITTED_AND_OVERLAPPING_EXECUTION_HELD" in terms, "PCCR_TERM")
    require(value.get("exact_operator_command") == "OVC APPROVE C2AR-G0 PASS", "COMMAND")
    require(value.get("allowed_decisions") == ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"], "DECISIONS")


def validate_qa(value: dict) -> None:
    validate_identity(value)
    require(value.get("qa_recommendation") == "PASS_IF_EXACT_HEAD_REQUIRED_CHECKS_PASS", "QA_RECOMMENDATION")
    statuses = {item["id"]: item["status"] for item in value.get("checks", [])}
    require(statuses.get("C2AR-G0-QA-01") == "PASS", "QA_SOURCE")
    require(statuses.get("C2AR-G0-QA-06") == "PENDING_EXACT_HEAD_CI", "QA_FOCUSED")
    require(statuses.get("C2AR-G0-QA-07") == "PENDING_EXACT_HEAD_CI", "QA_FULL")


class C2ARG0Tests(unittest.TestCase):
    def test_gate_packet_set_passes(self):
        validate_source(SOURCE)
        validate_baseline(BASELINE)
        validate_authority(AUTHORITY)
        validate_state(STATE)
        validate_gate(GATE)
        validate_qa(QA)

    def test_selector_activation_escape_blocks(self):
        value = copy.deepcopy(AUTHORITY)
        value["proposed_delta_on_pass"]["market_or_selector_authority"] = "ACTIVE"
        with self.assertRaises(C2ARG0Error):
            validate_authority(value)

    def test_pccr_parallel_execution_blocks(self):
        value = copy.deepcopy(BASELINE)
        value["overlap_and_concurrency"]["pccr"]["execution_authority"] = "APPROVED"
        with self.assertRaises(C2ARG0Error):
            validate_baseline(value)

    def test_shadow_freeze_before_g6_blocks(self):
        value = copy.deepcopy(AUTHORITY)
        value["contract_maturity"]["SHADOW_FROZEN"] = "AT_G1"
        with self.assertRaises(C2ARG0Error):
            validate_authority(value)

    def test_wp0_execution_before_g0_blocks(self):
        value = copy.deepcopy(AUTHORITY)
        value["current_authority"]["wp0_execution"] = "APPROVED"
        with self.assertRaises(C2ARG0Error):
            validate_authority(value)

    def test_active_release_mutation_blocks(self):
        value = copy.deepcopy(BASELINE)
        value["active_c2_authority"]["mutation_under_c2ar_g0"] = "APPROVED"
        with self.assertRaises(C2ARG0Error):
            validate_baseline(value)


if __name__ == "__main__":
    unittest.main()
