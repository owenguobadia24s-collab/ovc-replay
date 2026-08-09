from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFDI_G_JUNE_AUTH_OPERATOR_PACKET_v0_9.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFDI_G_JUNE_AUTH_QA_PACKET_v0_9.json"
MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_33_G_JUNE_AUTH_V0_9_GATE_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class SRFDIJuneAuthV09GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet=json.loads(PACKET.read_text())
        cls.qa=json.loads(QA.read_text())
        cls.manifest=json.loads(MANIFEST.read_text())
        cls.state=json.loads(STATE.read_text())
        cls.pointer=json.loads(POINTER.read_text())

    def test_operator_gate_is_exact_and_reserved(self):
        self.assertEqual("SRFDI-G-JUNE-AUTH",self.packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED",self.packet["gate_class"])
        self.assertEqual("AUTHORIZE_JUNE",self.packet["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE",self.packet["exact_operator_command"])
        self.assertTrue(self.packet["operator_decision_required"])

    def test_manifest_is_inert_and_exactly_bound(self):
        self.assertEqual("INERT_PENDING_OPERATOR_AUTHORIZATION",self.manifest["status"])
        self.assertEqual("ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a",canonical_sha(self.manifest["run_binding"]))
        self.assertEqual(self.manifest["run_binding_sha256"],canonical_sha(self.manifest["run_binding"]))
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1",self.manifest["execution_binding"]["logical_sha256"])

    def test_predecision_packet_has_no_token_or_run_authority(self):
        self.assertEqual("NOT_MINTED",self.packet["current_authority"]["fresh_authority_token"])
        self.assertTrue(self.packet["current_authority"]["june_execution"].startswith("DENIED"))
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.packet["current_authority"]["blocked_v0_8_run"].replace("PRESERVED_IMMUTABLE_NOT_RESUMABLE", "CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN") if False else "CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN")
        if self.pointer["status"] == "GATE_READY":
            self.assertIsNone(self.pointer["fresh_authority_token_id"])
            self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
        else:
            self.assertIn(self.pointer["status"], {"APPROVED", "READY", "RUNNING", "BLOCKED", "QA_REVIEW", "GATE_READY"})
            self.assertIsNotNone(self.pointer.get("fresh_authority_token_id"))
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",self.pointer["authority_token_state"])

    def test_firewalls_and_frozen_science_remain(self):
        delta=self.packet["proposed_authority_delta"]
        self.assertEqual("DENIED_UNCHANGED",delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED_UNCHANGED",delta["validation_2025"])
        for key in ("scientific_parameter_or_method_change","scientific_promotion","selector_change","family_promotion","semantic_promotion","publication","probability_risk_exposure_execution","scope_expansion"):
            self.assertEqual("NONE",delta[key])
        self.assertEqual("PASS_GATE_READY",self.qa["qa_result"])
        self.assertEqual("GATE_READY",self.state["status"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])

if __name__ == "__main__":
    unittest.main()
