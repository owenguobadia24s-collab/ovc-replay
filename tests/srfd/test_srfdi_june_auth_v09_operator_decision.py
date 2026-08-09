from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_OPERATOR_DECISION_v0_9.json"
ENVELOPE = BASE / "SRFD_JUNE_AUTHORITY_ENVELOPE_v0_9.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_9.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_DECISION_QA_v0_9.json"
MANIFEST = BASE / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_34_G_JUNE_AUTH_V0_9_AUTHORIZED_PENDING_MERGE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


def logical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class SRFDIJuneAuthV09OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_approval_is_exact_and_bounded(self):
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.decision["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH", self.decision["operator_command_received"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE", self.decision["gate_exact_operator_command"])
        self.assertEqual("658b32b9cfc6321c26b8bde90626dc6b341446cf", self.decision["gate_preparation"]["merge_commit"])
        self.assertEqual("66fb96144c30524a120f032cc14bc4e0f92c1cfa", self.decision["gate_preparation"]["tested_head_sha"])
        self.assertEqual("SUCCESS", self.decision["gate_preparation"]["repository_suite"]["conclusion"])
        self.assertEqual("SUCCESS", self.decision["gate_preparation"]["ovc_profile_tiered_merge_readiness"]["conclusion"])
        self.assertEqual(0, self.decision["gate_preparation"]["unresolved_review_threads"])

    def test_decision_envelope_and_manifest_bind_exactly(self):
        self.assertEqual("393e22c14592909ce3a9f9ee519031d68dd6cd3c41d0a496fb6d24b3e8e343d3", logical_sha(self.decision))
        self.assertEqual("515c4fc8c79d6cf41a44198806a83ddad1d6ad63500446c80a521d5359cf4757", logical_sha(self.envelope))
        self.assertEqual("ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a", logical_sha(self.manifest["run_binding"]))
        self.assertEqual(self.manifest["run_binding_sha256"], self.envelope["run_binding_sha256"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1", self.envelope["execution_binding"]["logical_sha256"])
        self.assertEqual("eefd860af86aea38e80ec211dd5ea34160171b6f", self.envelope["execution_binding"]["effective_merge"])

    def test_fresh_token_is_unique_single_use_and_reconstructible(self):
        core = dict(self.token)
        token_id = core.pop("token_id")
        state = core.pop("state")
        self.assertEqual("AUTHORIZED_UNCONSUMED_PENDING_MAIN_MERGE", state)
        self.assertEqual("SRFD.JUNE.AUTH." + logical_sha(core), token_id)
        self.assertEqual("SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3", token_id)
        self.assertNotEqual(self.token["prior_v0_8_token_id"], token_id)
        self.assertTrue(self.token["single_use"])
        self.assertEqual("ONE_EXACT_BOUND_RUN", self.token["run_cardinality"])
        self.assertEqual(self.envelope["run_binding_sha256"], self.token["run_binding_sha256"])

    def test_reserved_authority_remains_closed(self):
        delta = self.decision["authority_delta"]
        self.assertEqual("DENIED_UNCHANGED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED_UNCHANGED", delta["validation_2025"])
        for key in ("scientific_parameter_or_method_change", "scientific_promotion", "selector_change", "family_promotion", "semantic_promotion", "canonical_or_r2_publication", "probability_risk_exposure_execution", "scope_expansion"):
            self.assertEqual("NONE", delta[key])
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.decision["historical_blocked_run"]["token_state"])
        self.assertEqual("FORBIDDEN", self.decision["historical_blocked_run"]["resume"])

    def test_state_and_pointer_are_approved_pending_merge_only(self):
        self.assertEqual("APPROVED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.token["token_id"], self.state["authority"]["fresh_authority_token_id"])
        self.assertEqual("APPROVED", self.pointer["status"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual(self.token["token_id"], self.pointer["fresh_authority_token_id"])
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
        self.assertEqual("SRFDI-G-JUNE-AUTH-v0.9-MERGE-CLOSEOUT", self.pointer["next_packet"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])

    def test_qa_requires_exact_head_before_effective_run_authority(self):
        self.assertEqual("PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE", self.qa["qa_result"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertIn("FULL_REPOSITORY_SUITE", self.qa["exact_head_requirement"])
        self.assertIn("AFTER_ELIGIBLE_SQUASH_MERGE_TO_MAIN", self.qa["on_exact_head_pass"])


if __name__ == "__main__":
    unittest.main()
