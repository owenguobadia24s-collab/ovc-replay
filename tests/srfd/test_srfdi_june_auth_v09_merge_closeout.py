from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9"
RECEIPT = BASE / "SRFDI_G_JUNE_AUTH_V0_9_MERGE_RECEIPT.json"
EFFECT = BASE / "SRFD_JUNE_AUTHORITY_EFFECT_v0_9.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_9.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_V0_9_CLOSEOUT_QA.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_35_JUNE_AUTH_V0_9_EFFECTIVE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"

FRESH_TOKEN = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
OLD_TOKEN = "SRFD.JUNE.AUTH.7b9799d46cb6b3953fa9e96fb8309fbdeb0afe6dd53bfdcd16dec9cb85728ad0"
RUN_BINDING = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"


class SRFDIJuneAuthV09MergeCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.effect = json.loads(EFFECT.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_exact_operator_authority_merge_and_assurance(self):
        self.assertEqual(538, self.receipt["pr_number"])
        self.assertEqual("eefefdcf1d920e2b75c72460b3be93fed3cece7f", self.receipt["tested_final_head"])
        self.assertEqual("658b32b9cfc6321c26b8bde90626dc6b341446cf", self.receipt["tested_main"])
        self.assertEqual("63f084c04796121357db15259467b91e7065929d", self.receipt["merge_commit"])
        self.assertEqual({"result": "SUCCESS", "run_id": 31337855068}, self.receipt["repository_suite"])
        self.assertEqual({"result": "SUCCESS", "run_id": 31337855103}, self.receipt["tiered_profile_compatibility_merge_readiness"])
        self.assertEqual(0, self.receipt["unresolved_review_threads"])

    def test_fresh_token_effect_is_append_only_and_unconsumed(self):
        self.assertEqual("AUTHORIZED_UNCONSUMED_PENDING_MAIN_MERGE", self.token["state"])
        self.assertEqual(FRESH_TOKEN, self.token["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.effect["fresh_token"]["state"])
        self.assertFalse(self.effect["fresh_token"]["consumed"])
        self.assertEqual(FRESH_TOKEN, self.effect["fresh_token"]["token_id"])
        self.assertEqual("63f084c04796121357db15259467b91e7065929d", self.effect["effective_main_commit"])
        self.assertEqual(RUN_BINDING, self.effect["run_binding_sha256"])

    def test_historical_v08_run_and_token_remain_nonreusable(self):
        old = self.effect["historical_v0_8"]
        self.assertEqual(OLD_TOKEN, old["token_id"])
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", old["token_state"])
        self.assertEqual("FORBIDDEN", old["resume"])
        self.assertEqual(OLD_TOKEN, self.pointer["authority_token_id"])
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])

    def test_state_and_pointer_are_ready_for_exact_v09_run_only(self):
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10-v0.9", self.state["active_packet"])
        self.assertEqual("SRFDI-G10", self.state["current_gate"])
        self.assertEqual(FRESH_TOKEN, self.state["authority"]["authority_token_id"])
        self.assertFalse(self.state["authority"]["authority_token_consumed"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.state["authority"]["authority_token_state"])
        self.assertEqual(RUN_BINDING, self.state["exact_bindings"]["run_binding_sha256"])
        if self.pointer.get("failure_reason") == "CAPACITY_EXCEEDED_EXTERNAL_BYTES":
            self.assertEqual("BLOCKED", self.pointer["status"])
            self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
            self.assertEqual(FRESH_TOKEN, self.pointer["fresh_authority_token_id"])
            self.assertEqual(RUN_BINDING, self.pointer["run_binding_sha256"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
            self.assertEqual("SRFDI-WP10-v1.0-CAPACITY-REMEDIATION", self.pointer["next_packet"])
            self.assertEqual("BLOCKED_CAPACITY_V09_PRESERVED_NOT_COMPLETED", self.pointer["june_execution"])
            return
        self.assertIn(self.pointer["status"], {"READY", "RUNNING"})
        self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
        self.assertEqual(FRESH_TOKEN, self.pointer["fresh_authority_token_id"])
        self.assertEqual(RUN_BINDING, self.pointer["run_binding_sha256"])
        if self.pointer["status"] == "READY":
            self.assertEqual("SRFDI-WP10-v0.9", self.pointer["next_packet"])
            self.assertFalse(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["fresh_authority_token_state"])
        else:
            self.assertEqual("SRFDI-WP10-v0.9-RESUME", self.pointer["next_packet"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
            self.assertEqual("RUNNING_EXACT_BOUND_V09_FROM_COMMITTED_CHECKPOINT", self.pointer["june_execution"])

    def test_closeout_is_zero_delta_and_firewalls_remain_closed(self):
        self.assertEqual("PASS_PENDING_CLOSEOUT_EXACT_HEAD_ASSURANCE", self.qa["qa_result"])
        self.assertEqual("PASS", self.qa["delegated_decision"])
        self.assertEqual("NONE_CLOSEOUT_ONLY_APPROVED_AUTHORITY_EFFECT", self.qa["authority_delta"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
