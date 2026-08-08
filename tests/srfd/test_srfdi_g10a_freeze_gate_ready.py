from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a-freeze/SRFDI_G10A_FREEZE_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10a/SRFDI_WP10A_QA_PACKET.json"
CAPACITY = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10a/SRFDI_WP10A_REAL_DATA_CAPACITY_RECEIPT.json"
EQUIV = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10a/SRFDI_WP10A_EQUIVALENCE_RECEIPT.json"
BACKEND = ROOT / "registries/research/srfd/g10a_family_capacity_backend_candidate_v0_1.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_17_G10A_FREEZE_GATE_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIG10AFreezeGateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.capacity = json.loads(CAPACITY.read_text())
        cls.equiv = json.loads(EQUIV.read_text())
        cls.backend = json.loads(BACKEND.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_gate_is_operator_required_pass_recommended(self) -> None:
        self.assertEqual("SRFDI-G10A-FREEZE", self.packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", self.packet["gate_class"])
        self.assertEqual("GATE_READY", self.packet["status"])
        self.assertEqual("PASS", self.packet["recommended_decision"])
        self.assertEqual(["PASS", "DEFER", "BLOCK", "QUARANTINE"], self.packet["allowed_decisions"])
        self.assertEqual("OVC APPROVE SRFDI-G10A-FREEZE PASS", self.packet["exact_operator_command"])

    def test_full_frozen_grid_and_repeatable_capacity_are_exact(self) -> None:
        frozen = self.packet["frozen_scientific_bindings"]
        self.assertEqual(8598, frozen["eligible_record_count"])
        self.assertEqual(36, frozen["comparability_domain_count"])
        self.assertEqual(35380668, frozen["exact_pair_opportunity_count"])
        self.assertEqual(1944, frozen["family_configuration_count"])
        self.assertEqual("FORBIDDEN", frozen["mutation"])
        self.assertEqual("PASS_FULL_GRID_T0", self.capacity["run_1"]["status"])
        self.assertEqual("PASS_FULL_GRID_T0", self.capacity["run_2"]["status"])
        self.assertTrue(self.capacity["repeatability"]["catalog_grid_hash_equal"])
        self.assertEqual("68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866", self.capacity["repeatability"]["catalog_grid_hash"])

    def test_backend_candidate_is_capacity_only_and_unfrozen(self) -> None:
        self.assertEqual("CANDIDATE_PENDING_OPERATOR_FREEZE", self.backend["status"])
        self.assertEqual("CAPACITY_REMEDIATION_ONLY_NONSCIENTIFIC", self.backend["authority_state"])
        self.assertEqual(1944, self.backend["family_configuration_count"])
        self.assertTrue(self.backend["prohibitions"]["sampling"])
        self.assertTrue(self.backend["prohibitions"]["scientific_parameter_change"])
        self.assertTrue(self.backend["prohibitions"]["fresh_scientific_june_run"])

    def test_equivalence_and_qa_recommend_pass_without_scientific_delta(self) -> None:
        self.assertEqual("PASS_SUBJECT_TO_FINAL_EXACT_HEAD_REPOSITORY_CI", self.equiv["result"])
        self.assertEqual("NONE_CAPACITY_ONLY", self.equiv["scientific_effect"])
        self.assertEqual("PASS_GATE_READY", self.qa["qa_result"])
        self.assertEqual("PASS", self.qa["qa_recommendation"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])

    def test_gate_ready_state_preserves_consumed_token_and_all_firewalls(self) -> None:
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("SRFDI-WP10A", self.state["active_packet"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])
        authority = self.state["authority"]
        self.assertEqual("CONSUMED_NOT_REUSABLE", authority["authority_token_v0_4"])
        self.assertTrue(authority["fresh_june_scientific_run"].startswith("DENIED"))
        self.assertEqual("DENIED", authority["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", authority["validation_2025"])
        self.assertEqual("NONE", authority["scientific_promotion"])
        self.assertEqual("NONE", authority["probability_risk_exposure_execution"])

    def test_current_pointer_may_advance_after_operator_pass_without_granting_fresh_run(self) -> None:
        self.assertIn(self.pointer["current_gate"], {"SRFDI-G10A-FREEZE", "SRFDI-G-JUNE-AUTH"})
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertIn("FRESH_SCIENTIFIC_RUN_DENIED", self.pointer["june_execution"])
        self.assertIn(self.pointer["status"], {"READY", "APPROVED_PENDING_MERGE", "COMPLETED"})
        if self.pointer["status"] == "READY":
            self.assertEqual("SRFDI-WP10A", self.pointer["next_packet"])
            self.assertEqual("AUTHORIZED_BOUNDED_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY", self.pointer["wp10a_execution"])
        elif self.pointer["status"] == "APPROVED_PENDING_MERGE":
            self.assertEqual("SRFDI-G10A-FREEZE", self.pointer["current_gate"])
            self.assertEqual("SRFDI-G10A-FREEZE-MERGE-CLOSEOUT", self.pointer["next_packet"])
            self.assertNotEqual("AUTHORIZED_BOUNDED_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY", self.pointer["wp10a_execution"])
        else:
            self.assertEqual("SRFDI-G-JUNE-AUTH", self.pointer["current_gate"])
            self.assertEqual("SRFDI-G-JUNE-AUTH-PREP", self.pointer["next_packet"])
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual("COMPLETED_CAPACITY_BACKEND_FROZEN", self.pointer["wp10a_execution"])

    def test_pass_would_freeze_only_backend_and_still_require_new_june_authority(self) -> None:
        delta = self.packet["proposed_authority_delta_if_PASS"]
        self.assertIn("EXACT VERSIONED CAPACITY IMPLEMENTATION", delta["freeze_backend_candidate"])
        self.assertTrue(delta["fresh_june_scientific_run"].startswith("STILL_DENIED"))
        self.assertEqual("UNCHANGED_V0_4", delta["scientific_preregistration"])
        self.assertEqual("DENIED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", delta["validation_2025"])
        self.assertEqual("NONE", delta["scientific_promotion"])
        self.assertEqual("NONE", delta["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
