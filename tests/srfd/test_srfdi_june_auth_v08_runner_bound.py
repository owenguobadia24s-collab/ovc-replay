from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd import june_authority_v08
from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_execution_resilience import ExecutionResilienceError, RunAuthorityStore

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-8"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_DELEGATED_DECISION_v0_8.json"
ENVELOPE = BASE / "SRFD_JUNE_AUTHORITY_ENVELOPE_v0_8.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_8.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_QA_v0_8.json"
SUPERSESSION = BASE / "SRFDI_V07_UNUSED_TOKEN_SUPERSESSION_v0_8.json"
SOURCE_REVERIFY = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-6/SRFD_SOURCE_ARTIFACT_REVERIFICATION_v0_6.json"
OLD_V07_TOKEN = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-7/SRFD_JUNE_AUTHORITY_TOKEN_v0_7.json"
IMPL_BINDING = ROOT / "registries/research/srfd/wp10_v07_runner_implementation_binding_v0_1.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_26_JUNE_AUTH_V0_8_RUNNER_BOUND_AUTHORIZED.json"


class SRFDIJuneAuthV08RunnerBoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.supersession = json.loads(SUPERSESSION.read_text())
        cls.source_reverify = json.loads(SOURCE_REVERIFY.read_text())
        cls.old_v07_token = json.loads(OLD_V07_TOKEN.read_text())
        cls.impl_binding = json.loads(IMPL_BINDING.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_authority_artifacts_reconstruct_exactly(self):
        self.assertEqual(june_authority_v08.DECISION_SHA256, logical_sha256(self.decision))
        self.assertEqual(june_authority_v08.ENVELOPE_SHA256, logical_sha256(self.envelope))
        self.assertEqual(june_authority_v08.V07_SUPERSESSION_SHA256, logical_sha256(self.supersession))
        reconstructed = june_authority_v08.verify_runner_bound_june_authority(
            self.decision,
            self.envelope,
            self.token,
            self.source_reverify,
            self.supersession,
        )
        self.assertEqual(self.token, reconstructed)
        self.assertEqual(june_authority_v08.EXPECTED_TOKEN, self.token["token_id"])

    def test_runner_implementation_binding_matches_merged_files(self):
        self.assertEqual(june_authority_v08.RUNNER_IMPLEMENTATION_BINDING_SHA256, logical_sha256(self.impl_binding))
        self.assertEqual(self.impl_binding, june_authority_v08.implementation_binding())
        for name, path in self.impl_binding["runtime_paths"].items():
            data = (ROOT / path).read_bytes()
            git_blob = sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            self.assertEqual(self.impl_binding["runtime_blobs"][name], git_blob, name)
        self.assertEqual(june_authority_v08.RUN_BINDING_SHA256, june_authority_v08.build_run_binding().logical_hash)

    def test_v07_history_is_preserved_but_cannot_start_new_runner(self):
        self.assertEqual(june_authority_v08.V07_TOKEN, self.old_v07_token["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.old_v07_token["state"])
        self.assertFalse(self.supersession["superseded_token_consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.supersession["superseded_token_new_state"])
        self.assertEqual(june_authority_v08.V07_TOKEN, self.pointer["prior_v0_7_authority_token_id"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.pointer["prior_v0_7_authority_token_state"])

    def test_fresh_v08_token_consumes_once_for_exact_runner_binding(self):
        binding = june_authority_v08.build_run_binding()
        with TemporaryDirectory() as td:
            store = RunAuthorityStore(Path(td))
            start = store.consume(self.token, binding)
            self.assertEqual("CONSUMED_FOR_RUN", start.state)
            self.assertEqual(self.token["token_id"], start.token_id)
            self.assertEqual(june_authority_v08.RUN_BINDING_SHA256, start.run_binding_sha256)
            with self.assertRaises(ExecutionResilienceError) as ctx:
                store.consume(self.token, binding)
            self.assertEqual("TOKEN_ALREADY_CONSUMED", ctx.exception.reason_code)

    def test_state_pointer_opens_only_wp10_v07_with_v08_token(self):
        self.assertEqual("READY", self.pointer["status"])
        self.assertEqual("SRFDI-WP10-v0.7", self.pointer["next_packet"])
        self.assertEqual(self.token["token_id"], self.pointer["authority_token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["authority_token_state"])
        self.assertFalse(self.pointer["authority_token_consumed"])
        self.assertEqual(june_authority_v08.RUN_BINDING_SHA256, self.pointer["run_binding_sha256"])
        self.assertEqual(june_authority_v08.RUNNER_IMPLEMENTATION_BINDING_SHA256, self.pointer["runner_implementation_binding_sha256"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual(self.token["token_id"], self.state["authority"]["authority_token_id"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED", self.state["authority"]["market_benchmark"])

    def test_qa_is_fail_closed_pending_exact_authority_pr_head(self):
        self.assertEqual("PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE", self.qa["qa_result"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertIn("FULL_REPOSITORY_SUITE", self.qa["exact_head_requirement"])
        self.assertIn("TOKEN_BECOMES_EFFECTIVE", self.qa["on_exact_head_pass"])


if __name__ == "__main__":
    unittest.main()
