from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd import june_authority_v07
from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_execution_resilience import ExecutionResilienceError, RunAuthorityStore

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-7"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_DELEGATED_DECISION_v0_7.json"
ENVELOPE = BASE / "SRFD_JUNE_AUTHORITY_ENVELOPE_v0_7.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_7.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_QA_v0_7.json"
SOURCE_REVERIFY = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-6/SRFD_SOURCE_ARTIFACT_REVERIFICATION_v0_6.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_24_JUNE_AUTH_V0_7_RUN_SCOPED_AUTHORIZED.json"
RESILIENCE_MODULE = ROOT / "src/ovc/opt_b/srfd/wp10_execution_resilience.py"


class SRFDIJuneAuthV07RunScopedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.source_reverify = json.loads(SOURCE_REVERIFY.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_authority_artifact_hashes_and_token_reconstruct_exactly(self):
        self.assertEqual("729faf0d9e8128a24f4b1696d15d28aa252af8f5c7c5a82d5d1105f4ca75c244", logical_sha256(self.decision))
        self.assertEqual("7e3f41fbb0f62c5ca6644b5efcaee976799ee86bc5a5066d926d48b07935b716", logical_sha256(self.envelope))
        reconstructed = june_authority_v07.verify_fresh_june_run_scoped_authority(self.decision, self.envelope, self.token, self.source_reverify)
        self.assertEqual(self.token, reconstructed)
        self.assertEqual(june_authority_v07.EXPECTED_TOKEN, self.token["token_id"])
        self.assertEqual(june_authority_v07.RUN_BINDING_SHA256, self.token["run_binding_sha256"])

    def test_resilience_code_and_post_merge_binding_are_exact(self):
        data = RESILIENCE_MODULE.read_bytes()
        git_blob = sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        self.assertEqual(june_authority_v07.RESILIENCE_MODULE_BLOB, git_blob)
        self.assertEqual(june_authority_v07.RESILIENCE_BINDING_SHA256, logical_sha256(june_authority_v07.implementation_binding()))
        self.assertEqual(june_authority_v07.RUN_BINDING_SHA256, june_authority_v07.build_run_binding().logical_hash)
        self.assertEqual(june_authority_v07.BASELINE_MAIN, self.decision["resilience_precondition"]["execution_resilience_merge"])
        self.assertEqual(489, self.decision["resilience_precondition"]["exact_head_assurance"]["pr_number"])

    def test_frozen_source_verification_is_reused_without_provider_fetch(self):
        self.assertEqual(june_authority_v07.SOURCE_REVERIFY_HASH, logical_sha256(self.source_reverify))
        self.assertTrue(self.source_reverify["all_exact"])
        self.assertEqual(6, len(self.source_reverify["artifacts"]))
        self.assertEqual("REUSE_IMMUTABLE_ACCEPTED_VERIFICATION_NO_PROVIDER_FETCH", self.decision["prerequisites"]["source_artifact_reverification_mode"])
        self.assertEqual("DENIED", self.decision["prerequisites"]["provider_fetch"])
        self.assertEqual("FORBIDDEN", self.envelope["source_population_binding"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.envelope["firewalls"]["validation_2025"])

    def test_fresh_token_starts_only_the_exact_bound_run(self):
        binding = june_authority_v07.build_run_binding()
        with TemporaryDirectory() as td:
            store = RunAuthorityStore(Path(td))
            start = store.consume(self.token, binding)
            self.assertEqual("CONSUMED_FOR_RUN", start.state)
            self.assertEqual(self.token["token_id"], start.token_id)
            self.assertEqual(june_authority_v07.RUN_BINDING_SHA256, start.run_binding_sha256)
            self.assertEqual(start, store.load(self.token["token_id"]))
            with self.assertRaises(ExecutionResilienceError) as ctx:
                store.consume(self.token, binding)
            self.assertEqual("TOKEN_ALREADY_CONSUMED", ctx.exception.reason_code)

    def test_historical_v07_state_is_immutable_while_pointer_may_advance(self):
        self.assertEqual("SRFDI-WP10-v0.7", self.state["active_packet"])
        self.assertEqual(self.token["token_id"], self.state["authority"]["authority_token_id"])
        self.assertFalse(self.state["authority"]["authority_token_consumed"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.state["authority"]["authority_token_state"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertEqual(june_authority_v07.RUN_BINDING_SHA256, self.state["exact_bindings"]["run_binding_sha256"])

        self.assertIn(self.pointer["status"], {"READY", "BLOCKED", "AUTHORIZED_REMEDIATION_ONLY", "GATE_READY"})
        if self.pointer["authority_token_id"] != self.token["token_id"]:
            self.assertEqual(self.token["token_id"], self.pointer["prior_v0_7_authority_token_id"])
            self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.pointer["prior_v0_7_authority_token_state"])
            self.assertFalse(self.pointer["prior_v0_7_authority_token_consumed"])
        else:
            self.assertFalse(self.pointer["authority_token_consumed"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["authority_token_state"])
            self.assertEqual(june_authority_v07.RUN_BINDING_SHA256, self.pointer["run_binding_sha256"])
        if self.pointer["status"] == "READY":
            self.assertEqual("SRFDI-WP10-v0.7", self.pointer["next_packet"])
        elif self.pointer["status"] == "BLOCKED":
            self.assertIsNone(self.pointer["next_packet"])
            self.assertEqual("HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH", self.pointer["stop_at"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["blocker_evidence"].endswith("SRFDI_WP10_V07_EXECUTION_BLOCKER.json"))
        elif self.pointer["status"] == "AUTHORIZED_REMEDIATION_ONLY":
            self.assertEqual("SRFDI-G10B", self.pointer["current_gate"])
            self.assertEqual("SRFDI-WP10B", self.pointer["next_packet"])
            self.assertEqual("SRFDI-G10B-FREEZE", self.pointer["stop_at"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
            self.assertTrue(self.pointer["blocker_evidence"].endswith("SRFDI_WP10_V07_EXECUTION_BLOCKER.json"))
        else:
            self.assertEqual("GATE_READY", self.pointer["status"])
            self.assertIn(self.pointer["current_gate"], {"SRFDI-G10B-FREEZE", "SRFDI-G-JUNE-AUTH"})
            self.assertIsNone(self.pointer["next_packet"])
            self.assertTrue(self.pointer["operator_decision_required"])
            if self.pointer["current_gate"] == "SRFDI-G10B-FREEZE":
                self.assertEqual("COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE", self.pointer["wp10b_execution"])
            else:
                self.assertTrue(self.pointer["wp10b_execution"].startswith("COMPLETED_FROZEN_ON_MAIN@"))
                self.assertIsNone(self.pointer["fresh_authority_token_id"])
                self.assertEqual("NOT_MINTED_PENDING_OPERATOR", self.pointer["fresh_authority_token_state"])
                self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
            self.assertTrue(self.pointer["blocker_evidence"].endswith("SRFDI_WP10_V07_EXECUTION_BLOCKER.json"))
        self.assertEqual(june_authority_v07.PRIOR_V06_TOKEN, self.pointer["prior_v0_6_authority_token_id"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.pointer["prior_v0_6_authority_token_state"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])

    def test_qa_requires_final_v07_exact_head_before_effect(self):
        self.assertEqual("PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE", self.qa["qa_result"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertIn("FULL_REPOSITORY_SUITE", self.qa["exact_head_requirement"])
        self.assertIn("TOKEN_BECOMES_EFFECTIVE", self.qa["on_exact_head_pass"])


if __name__ == "__main__":
    unittest.main()
