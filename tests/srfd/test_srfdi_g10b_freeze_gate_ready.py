from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "registries/research/srfd/wp10b_segmentation_execution_binding_candidate_v0_1.json"
GATE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10b/SRFDI_WP10B_QA_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_30_G10B_FREEZE_GATE_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
OLD_BINDING = ROOT / "registries/research/srfd/wp10_v07_runner_implementation_binding_v0_1.json"
RUNNER = ROOT / "src/ovc/opt_b/srfd/wp10_v07_runner.py"
REFERENCE = ROOT / "src/ovc/opt_b/srfd/wp10b_segmentation_reference.py"

class SRFDIG10BFreezeGateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = json.loads(BINDING.read_text())
        cls.gate = json.loads(GATE.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.old_binding = json.loads(OLD_BINDING.read_text())

    def test_candidate_binding_hash_and_runtime_blobs_are_exact(self):
        expected = "2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1"
        self.assertEqual(expected, logical_sha256(self.binding))
        self.assertEqual(expected, self.gate["candidate_execution_binding"]["logical_sha256"])
        for name, path in self.binding["runtime_paths"].items():
            data = (ROOT / path).read_bytes()
            blob = sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            self.assertEqual(self.binding["runtime_blobs"][name], blob, name)

    def test_historical_v08_runner_binding_is_preserved(self):
        self.assertEqual("47fbf10aeb7ba41ee91cd8638650522401fad82a", self.old_binding["runtime_blobs"]["production_runner"])
        self.assertNotEqual(self.old_binding["runtime_blobs"]["production_runner"], self.binding["runtime_blobs"]["production_runner"])

    def test_reference_is_independent_and_runner_has_no_empirical_count_target(self):
        reference = REFERENCE.read_text()
        self.assertNotIn("from .segmentation_prereg", reference)
        self.assertNotIn("from .segmentation import", reference)
        runner = RUNNER.read_text()
        self.assertNotIn("EXPECTED_SEGMENTATION_COUNTS", runner)
        for value in ("7609", "7345", "7013", "6781"):
            self.assertNotIn(value, runner)

    def test_equivalence_qa_and_gate_are_pass_ready(self):
        self.assertEqual("PASS_GATE_READY", self.qa["qa_result"])
        self.assertEqual("PASS", self.qa["qa_recommendation"])
        self.assertEqual("PASS_EXACT", self.gate["equivalence_evidence"]["production_reference_output_equality"])
        self.assertEqual([], self.gate["blocking_warnings"])
        self.assertEqual([], self.gate["unresolved_issues"])
        self.assertEqual("PASS", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G10B-FREEZE PASS", self.gate["exact_operator_command"])

    def test_gate_ready_history_and_lawful_pointer_progression_preserve_firewalls(self):
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertIn(self.pointer["status"], {"GATE_READY", "APPROVED", "READY", "RUNNING", "QA_REVIEW", "BLOCKED"})
        self.assertIn(self.pointer["current_gate"], {"SRFDI-G10B-FREEZE", "SRFDI-G-JUNE-AUTH", "SRFDI-G10", "SRFDI-G11"})
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
        if self.pointer["current_gate"] == "SRFDI-G10B-FREEZE":
            self.assertEqual("GATE_READY", self.pointer["status"])
            self.assertIsNone(self.pointer["next_packet"])
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY", self.pointer["june_execution"])
        elif self.pointer["current_gate"] == "SRFDI-G-JUNE-AUTH" and self.pointer["status"] == "GATE_READY":
            self.assertIsNone(self.pointer["next_packet"])
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
            self.assertIsNone(self.pointer["fresh_authority_token_id"])
        elif self.pointer["current_gate"] == "SRFDI-G-JUNE-AUTH":
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertIsNotNone(self.pointer["fresh_authority_token_id"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1", self.pointer["candidate_runner_implementation_binding_sha256"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])

    def test_pass_would_freeze_only_execution_binding(self):
        delta = self.gate["proposed_authority_delta_if_PASS"]
        self.assertEqual("UNCHANGED_V0_4", delta["scientific_preregistration"])
        self.assertEqual("UNCHANGED_V0_3", delta["segmentation_registry"])
        self.assertTrue(delta["fresh_june_scientific_run"].startswith("STILL_DENIED"))
        self.assertEqual("DENIED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", delta["validation_2025"])
        self.assertEqual("NONE", delta["scientific_promotion"])
        self.assertEqual("NONE", delta["probability_risk_exposure_execution"])

if __name__ == "__main__":
    unittest.main()
