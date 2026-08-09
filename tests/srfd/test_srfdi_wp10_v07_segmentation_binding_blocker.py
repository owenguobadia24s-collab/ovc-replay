from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-7"
BLOCKER = BASE / "SRFDI_WP10_V07_EXECUTION_BLOCKER.json"
START = BASE / "SRFDI_WP10_V07_RUN_START_RECEIPT.json"
PREFLIGHT = BASE / "SRFDI_WP10_V07_PREFLIGHT_RECEIPT.json"
CHECKPOINT = BASE / "SRFDI_WP10_V07_CHECKPOINT_00000001.json"
POPULATION = BASE / "SRFDI_WP10_V07_POPULATION_ARTIFACT.json"
CAPACITY = BASE / "SRFDI_WP10_V07_CAPACITY_TELEMETRY_AT_BLOCKER.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_27_WP10_V07_SEGMENTATION_BINDING_BLOCKED.json"

RUN_ID = "SRFD.RUN.be74524955a4168484d21d91aee067e084e64be0178ed976bc4824369f7d8513"
TOKEN_ID = "SRFD.JUNE.AUTH.7b9799d46cb6b3953fa9e96fb8309fbdeb0afe6dd53bfdcd16dec9cb85728ad0"
RUN_BINDING = "25f1c18d39898b5f2b5e9511245ecfd2615eb420205e68f9f1e8c7fe7f929fb9"


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class SRFDIWP10V07SegmentationBindingBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.start = json.loads(START.read_text())
        cls.preflight = json.loads(PREFLIGHT.read_text())
        cls.checkpoint = json.loads(CHECKPOINT.read_text())
        cls.population = json.loads(POPULATION.read_text())
        cls.capacity = json.loads(CAPACITY.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_external_receipt_copies_preserve_exact_bytes(self):
        self.assertEqual("c70cbf50f2f7ec10a41eb65f94510bee66ab52f31ba56713ad21b7296b77b991", file_sha(START))
        self.assertEqual("f38dd025b7903c3b4cdb3adc7324b6b97409bcac8c4cbdd4759882b75115b932", file_sha(PREFLIGHT))
        self.assertEqual("a0e474a2dddc9ed64efb25e27f2abb1384efa2c9b6cdccbb90d6690b5b9ca855", file_sha(CHECKPOINT))
        self.assertEqual("e3de8629f6e3f592b8000b373d4cb2d5787a1a861623c4a063bfdaeedd8047db", file_sha(POPULATION))
        self.assertEqual("3bd9dab79671cb63fc7209c4c0940ca0347c1d1f898d543edb7b8fce785114e2", file_sha(CAPACITY))

    def test_token_is_consumed_exactly_for_preserved_run(self):
        self.assertEqual(TOKEN_ID, self.start["token_id"])
        self.assertEqual(RUN_ID, self.start["run_id"])
        self.assertEqual(RUN_BINDING, self.start["run_binding_sha256"])
        self.assertEqual("CONSUMED_FOR_RUN", self.start["state"])
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertEqual(TOKEN_ID, self.pointer["authority_token_id"])
        self.assertIn("CONSUMED_FOR_RUN", self.pointer["authority_token_state"])

    def test_population_only_committed_before_segmentation_block(self):
        self.assertEqual(["population"], self.checkpoint["completed_units"])
        self.assertEqual(1, self.checkpoint["sequence"])
        self.assertEqual("COMMITTED", self.checkpoint["state"])
        self.assertEqual("population", self.population["unit_id"])
        self.assertEqual(8598, self.population["output"]["eligible_record_count"])
        self.assertEqual(36, self.population["output"]["comparability_domain_count"])
        self.assertEqual(1944, self.population["output"]["family_configuration_count"])
        self.assertEqual("WITHIN_T0", self.capacity["capacity_status"])
        self.assertEqual(1, self.capacity["accounted_unit_count"])

    def test_segmentation_mismatch_is_exact_and_fail_closed(self):
        failure = self.blocker["failure"]
        self.assertEqual("SEGMENTATION_BINDING_MISMATCH", failure["reason_code"])
        self.assertEqual("segmentation/RUN_CHANGE_SEGMENTATION", failure["stage"])
        self.assertEqual({"stream_count": 264, "segment_count": 7609, "boundary_count": 7345}, failure["expected"])
        self.assertEqual({"stream_count": 232, "segment_count": 7013, "boundary_count": 6781}, failure["actual"])
        self.assertFalse(failure["segmentation_artifact_committed"])
        self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED", self.blocker["status"])
        self.assertEqual("BLOCKED_FAIL_CLOSED", self.blocker["authority"]["resume_under_current_runner"])
        self.assertEqual("NONE", self.blocker["authority"]["new_run_authority"])

    def test_current_programme_state_records_hard_stop_without_authority_widening(self):
        self.assertEqual("BLOCKED", self.pointer["status"])
        self.assertEqual("HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH", self.pointer["stop_at"])
        self.assertIsNone(self.pointer["next_packet"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(RUN_ID, self.pointer["run_id"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])
        self.assertEqual("BLOCKED", self.state["status"])
        self.assertEqual("NONE_UNDER_CURRENT_STANDING_DELEGATION_AFTER_HARD_STOP", self.state["remediation_authority"])
        self.assertEqual("PRESERVE_EVIDENCE_AND_STOP_FAIL_CLOSED_NO_ROUTINE_OPERATOR_APPROVAL_REQUEST", self.state["next_action"])


if __name__ == "__main__":
    unittest.main()
