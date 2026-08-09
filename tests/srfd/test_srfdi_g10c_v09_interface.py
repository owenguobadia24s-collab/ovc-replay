from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_execution_resilience import ExecutionResilienceError, RunAuthorityStore
from ovc.opt_b.srfd.wp10_v09_interface import (
    EXECUTION_BINDING_SHA256,
    FRESH_TOKEN_ID,
    RUN_BINDING_SHA256,
    WP10V09InterfaceError,
    binding_from_manifest,
    effective_token_view,
    interface_preflight,
    start_after_exact_preflight,
)

ROOT = Path(__file__).resolve().parents[2]
V09 = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9"
MANIFEST = V09 / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json"
TOKEN = V09 / "SRFD_JUNE_AUTHORITY_TOKEN_v0_9.json"
EFFECT = V09 / "SRFD_JUNE_AUTHORITY_EFFECT_v0_9.json"
FREEZE = ROOT / "registries/research/srfd/wp10b_segmentation_execution_binding_freeze_v0_1.json"
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10c/SRFDI_G10C_OPERATOR_DECISION.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10c/SRFDI_G10C_IMPLEMENTATION_QA.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json"


class SRFDIG10CV09InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.effect = json.loads(EFFECT.read_text())
        cls.freeze = json.loads(FREEZE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())

    def test_operator_supercede_decision_is_exact_and_bounded(self) -> None:
        self.assertEqual("SRFDI-G10C", self.decision["gate_id"])
        self.assertEqual("OVC APPROVE SRFDI-G10C SUPERSEDE", self.decision["operator_command"])
        self.assertEqual("SUPERSEDE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("NONE", self.decision["authority_delta"]["scientific_delta"])
        self.assertEqual("DENIED", self.decision["authority_delta"]["new_token"])
        self.assertEqual("DENIED", self.decision["authority_delta"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.decision["authority_delta"]["validation_2025"])

    def test_exact_v09_binding_reconstructs_without_hidden_v07_fields(self) -> None:
        binding = binding_from_manifest(self.manifest)
        self.assertEqual(RUN_BINDING_SHA256, binding.logical_hash)
        self.assertNotIn("implementation_commit", binding.to_dict())
        self.assertEqual(EXECUTION_BINDING_SHA256, binding.execution_binding_sha256)
        self.assertEqual("SRFDI-WP10-v0.9", binding.packet_id)

    def test_frozen_execution_runtime_and_authority_overlay_pass_source_independently(self) -> None:
        receipt = interface_preflight(
            repo_root=ROOT,
            manifest=self.manifest,
            raw_token=self.token,
            authority_effect=self.effect,
            execution_freeze=self.freeze,
        )
        self.assertEqual("PASS", receipt["status"])
        self.assertFalse(receipt["market_records_read"])
        self.assertFalse(receipt["token_consumed"])
        self.assertEqual("DENIED", receipt["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", receipt["validation_2025"])
        self.assertEqual("NONE", receipt["scientific_delta"])

    def test_effective_view_never_mutates_raw_token_artifact(self) -> None:
        before = deepcopy(self.token)
        before_hash = logical_sha256(before)
        binding = binding_from_manifest(self.manifest)
        view = effective_token_view(self.token, self.effect, binding)
        self.assertEqual("AUTHORIZED_UNCONSUMED", view["state"])
        self.assertEqual(FRESH_TOKEN_ID, view["token_id"])
        self.assertEqual(before, self.token)
        self.assertEqual(before_hash, logical_sha256(self.token))
        self.assertEqual(before_hash, view.raw_payload_logical_sha256)

    def test_authority_effect_drift_fails_closed(self) -> None:
        bad = deepcopy(self.effect)
        bad["fresh_token"]["token_id"] = "SRFD.JUNE.AUTH." + "0" * 64
        binding = binding_from_manifest(self.manifest)
        with self.assertRaises(WP10V09InterfaceError) as ctx:
            effective_token_view(self.token, bad, binding)
        self.assertEqual("V09_AUTHORITY_EFFECT_TOKEN_MISMATCH", ctx.exception.reason_code)

    def test_token_is_not_consumed_when_full_preflight_fails(self) -> None:
        def failing_preflight(_binding):
            raise WP10V09InterfaceError("TEST_PREFLIGHT_FAILURE", "deliberate")

        with TemporaryDirectory() as td:
            store = RunAuthorityStore(Path(td))
            with self.assertRaises(WP10V09InterfaceError):
                start_after_exact_preflight(
                    store=store,
                    repo_root=ROOT,
                    manifest=self.manifest,
                    raw_token=self.token,
                    authority_effect=self.effect,
                    execution_freeze=self.freeze,
                    full_preflight=failing_preflight,
                )
            self.assertFalse((Path(td) / "consumption").exists())

    def test_exact_pass_consumes_existing_token_once_only_after_preflight(self) -> None:
        def passing_preflight(binding):
            return {
                "status": "PASS",
                "run_binding_sha256": binding.logical_hash,
                "frozen_science_status": "PASS",
                "source_binding_status": "PASS",
                "capacity_contract_status": "PASS",
                "execution_binding_status": "PASS",
                "provider_fetch": "DENIED",
                "validation_2025": "LOCKED_UNCONSUMED",
                "token_consumed": False,
            }

        with TemporaryDirectory() as td:
            store = RunAuthorityStore(Path(td))
            start, interface_receipt, full_receipt, binding = start_after_exact_preflight(
                store=store,
                repo_root=ROOT,
                manifest=self.manifest,
                raw_token=self.token,
                authority_effect=self.effect,
                execution_freeze=self.freeze,
                full_preflight=passing_preflight,
            )
            self.assertEqual(FRESH_TOKEN_ID, start.token_id)
            self.assertEqual(RUN_BINDING_SHA256, start.run_binding_sha256)
            self.assertEqual("PASS", interface_receipt["status"])
            self.assertEqual("PASS", full_receipt["status"])
            self.assertEqual(RUN_BINDING_SHA256, binding.logical_hash)
            with self.assertRaises(ExecutionResilienceError) as ctx:
                start_after_exact_preflight(
                    store=store,
                    repo_root=ROOT,
                    manifest=self.manifest,
                    raw_token=self.token,
                    authority_effect=self.effect,
                    execution_freeze=self.freeze,
                    full_preflight=passing_preflight,
                )
            self.assertEqual("TOKEN_ALREADY_CONSUMED", ctx.exception.reason_code)

    def test_qa_remains_non_scientific_and_requires_exact_head_assurance(self) -> None:
        self.assertIn(self.qa["qa_result"], {"QA_REVIEW_PENDING_EXACT_HEAD", "PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE", "PASS_EXACT_HEAD"})
        self.assertEqual("NONE_IMPLEMENTATION_OF_OPERATOR_AUTHORIZED_REMEDIATION", self.qa["authority_delta"])
        self.assertTrue(self.qa["auto_ratifiable_after_exact_head_pass"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertFalse(self.blocker["exact_authority"]["fresh_token_consumed"])


if __name__ == "__main__":
    unittest.main()
