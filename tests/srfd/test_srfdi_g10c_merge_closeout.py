from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10c"
RECEIPT = BASE / "SRFDI_G10C_MERGE_RECEIPT.json"
QA = BASE / "SRFDI_G10C_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_41_G10C_COMPLETED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIG10CMergeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_exact_primary_merge_and_final_assurance(self) -> None:
        self.assertEqual("SRFDI-G10C", self.receipt["gate_id"])
        self.assertEqual("SUPERSEDE", self.receipt["decision"])
        self.assertEqual("OPERATOR", self.receipt["decision_authority"])
        self.assertEqual(547, self.receipt["pr_number"])
        self.assertEqual("55880e3531060789c92646d2a192788475874f54", self.receipt["tested_final_head"])
        self.assertEqual("f25308678b184c2de75b7d6b2206f9d8663d6cc6", self.receipt["merge_commit"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["repository_suite"]["result"])
        self.assertEqual(31341528378, self.receipt["assurance"]["repository_suite"]["run_id"])
        self.assertEqual("SUCCESS", self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness"]["result"])
        self.assertEqual(31341528377, self.receipt["assurance"]["tiered_profile_compatibility_merge_readiness"]["run_id"])
        self.assertEqual(0, self.receipt["assurance"]["unresolved_review_threads"])

    def test_closeout_is_zero_delta_delegated_pass(self) -> None:
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertTrue(self.qa["auto_ratifiable"])
        self.assertEqual("NONE_CLOSEOUT_ONLY", self.qa["authority_delta"])
        self.assertEqual("PASS", self.qa["delegated_decision"])
        self.assertEqual("SRFDI-WP10-v0.9", self.qa["next_packet"])

    def test_g10c_effective_state_preserves_exact_authority(self) -> None:
        self.assertEqual("COMPLETED", self.state["status"])
        self.assertEqual("AUTHORITATIVE_CURRENT", self.state["state_role"])
        self.assertEqual("SRFDI-WP10-v0.9", self.state["active_packet"])
        self.assertEqual("SRFDI-G10", self.state["current_gate"])
        auth = self.state["authority"]
        self.assertEqual("SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3", auth["fresh_authority_token_id"])
        self.assertFalse(auth["fresh_authority_token_consumed"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", auth["fresh_authority_token_state"])
        self.assertEqual("DENIED", auth["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", auth["validation_2025"])
        self.assertEqual("NONE", auth["scientific_promotion"])
        self.assertEqual("NONE", auth["probability_risk_exposure_execution"])
        self.assertEqual("ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a", self.state["exact_bindings"]["run_binding_sha256"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1", self.state["exact_bindings"]["execution_binding_sha256"])

    def test_current_pointer_advances_lawfully_beyond_closeout(self) -> None:
        if self.pointer.get("failure_reason") == "CAPACITY_EXCEEDED_EXTERNAL_BYTES":
            self.assertEqual("BLOCKED", self.pointer["status"])
            self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
            self.assertEqual("SRFDI-WP10-v1.0-CAPACITY-REMEDIATION", self.pointer["next_packet"])
            self.assertEqual("BLOCKED_CAPACITY_V09_PRESERVED_NOT_COMPLETED", self.pointer["june_execution"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertTrue(self.pointer["failure_receipt"].endswith("SRFDI_WP10_V09_CAPACITY_EXCEEDED_EXTERNAL_BYTES.json"))
            return
        self.assertIn(self.pointer["authoritative_state"], {
            "registries/implementation/srfd/OVC_SRFDI_STATE_v0_41_G10C_COMPLETED.json",
            "registries/implementation/srfd/OVC_SRFDI_STATE_v0_42_WP10_V09_RUNNING.json",
        })
        self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual("SUPERSEDE", self.pointer["g10c_operator_decision"])
        self.assertEqual("IMPLEMENTED_ASSURED_ON_MAIN@f25308678b184c2de75b7d6b2206f9d8663d6cc6", self.pointer["wp10_v09_interface"])
        self.assertEqual("SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3", self.pointer["fresh_authority_token_id"])
        self.assertEqual("ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a", self.pointer["run_binding_sha256"])
        if self.pointer["status"] == "READY":
            self.assertEqual("SRFDI-WP10-v0.9", self.pointer["next_packet"])
            self.assertFalse(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["fresh_authority_token_state"])
        else:
            self.assertEqual("RUNNING", self.pointer["status"])
            self.assertEqual("SRFDI-WP10-v0.9-RESUME", self.pointer["next_packet"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
