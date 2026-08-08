from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-4"
BLOCKER = BASE / "SRFDI_WP10_V04_CAPACITY_BLOCKER.json"
QA = BASE / "SRFDI_WP10_V04_QA_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_13_BLOCKED_CANDIDATE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIWP10V04CapacityBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_token_is_consumed_once_and_never_reset_by_block(self) -> None:
        authority = self.blocker["authority"]
        self.assertTrue(authority["token_consumed"])
        self.assertTrue(authority["consumed_once"])
        self.assertEqual("NONE", authority["retry_authority"])
        self.assertEqual("SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686", authority["token_id"])
        self.assertTrue(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.state["authority"]["authority_token_v0_4"])

    def test_exact_source_population_and_firewalls_remain_unchanged(self) -> None:
        preflight = self.blocker["exact_preflight"]
        self.assertEqual("PASS", preflight["result"])
        self.assertEqual(8598, preflight["eligible_record_count"])
        self.assertEqual("fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e", preflight["eligible_record_ids_sha256"])
        self.assertEqual(0, preflight["exclusion_count"])
        self.assertEqual({"EVALUABLE": 4996, "NOT_EVALUATED": 3602}, preflight["computability"])
        self.assertEqual("DENIED", self.blocker["firewalls"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.blocker["firewalls"]["validation_2025"])
        self.assertEqual("NONE", self.blocker["firewalls"]["scientific_promotion"])
        self.assertEqual("NONE", self.blocker["firewalls"]["probability_risk_exposure_execution"])

    def test_representation_stage_is_complete_and_wrapper_corrections_are_explicit(self) -> None:
        rep = self.blocker["representation_execution"]
        self.assertEqual("PRESERVED_OPERATIONAL_WRAPPER_ERROR", rep["attempt0"]["status"])
        self.assertEqual("NONE", rep["attempt0"]["scientific_delta"])
        self.assertEqual("PASS_SAME_CONSUMED_RUN", rep["correction"]["status"])
        self.assertEqual(36, rep["comparability_domain_count"])
        self.assertEqual(35380668, rep["exact_pair_opportunity_count"])
        self.assertEqual(1944, rep["required_family_configuration_instances"])
        self.assertEqual(4996, rep["representation_counts"]["SRFDI-R1"])
        self.assertEqual(4996, rep["representation_counts"]["SRFDI-R6-EACH_OF_FIVE_VARIANTS"])
        self.assertEqual(8598, rep["representation_counts"]["SRFDI-R8"])
        self.assertEqual(8598, rep["representation_counts"]["SRFDI-R9"])
        self.assertEqual("NONE", self.blocker["run_start_bookkeeping"]["authority_or_scientific_effect"])

    def test_capacity_failure_is_unresolved_not_hidden_partial_success(self) -> None:
        capacity = self.blocker["capacity_measurement"]
        self.assertEqual("CAPACITY_UNRESOLVED", capacity["status"])
        self.assertEqual("STOP_NODE_PRESERVE_EVIDENCE_DO_NOT_DROP_METHOD", capacity["action"])
        self.assertFalse(capacity["average_linkage_required_anchor_completed_within_process_window"])
        self.assertEqual(240, capacity["process_window_seconds"])
        self.assertEqual("REAL_DATA_FULL_GRID_CAPACITY_COVERAGE_INVALIDATED_NOT_A_CLAIM_THAT_14400_SECONDS_WAS_ALREADY_EXCEEDED", capacity["interpretation"])
        self.assertEqual("NOT_COMPLETED", self.blocker["scientific_execution"]["distance_family_full_grid"])
        self.assertEqual("NOT_EVALUABLE", self.blocker["scientific_execution"]["g10_scientific_disposition"])
        self.assertFalse(self.blocker["scientific_execution"]["scientific_family_outcomes_promoted_or_selected"])

    def test_qa_blocks_and_prohibits_partial_escape(self) -> None:
        self.assertEqual("BLOCK", self.qa["qa_result"])
        self.assertEqual("CAPACITY_UNRESOLVED_REAL_DATA_FULL_GRID", self.qa["reason_code"])
        self.assertEqual("FAIL_CAPACITY_UNRESOLVED", self.qa["acceptance"]["full_distance_family_grid_completed"])
        self.assertEqual("PROHIBITED_AND_NOT_USED", self.qa["acceptance"]["partial_benchmark_escape_hatch"])
        self.assertEqual("NO", self.qa["acceptance"]["g10_scientific_disposition_evaluable"])
        self.assertEqual("BLOCK", self.qa["recommended_disposition"])

    def test_block_state_does_not_mutate_main_pointer_or_fabricate_retry_authority(self) -> None:
        self.assertEqual("BLOCK_EVIDENCE_CURRENT_ON_PR", self.state["state_role"])
        self.assertEqual("BLOCKED_POST_START_CAPACITY_UNRESOLVED", self.state["status"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("NOT_PERFORMED_ON_BLOCK_EVIDENCE_PR", self.state["current_pointer_mutation"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_12.json", self.pointer["authoritative_state"])
        self.assertEqual("AUTHORIZED_READY_UNCONSUMED", self.pointer["status"])
        self.assertFalse(self.pointer["authority_token_consumed"])
        self.assertIn("NEW_OPERATOR_DEFINED_BOUNDED_CAPACITY_REMEDIATION_AUTHORITY", self.state["next_action"])


if __name__ == "__main__":
    unittest.main()
