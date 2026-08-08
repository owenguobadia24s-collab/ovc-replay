from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-4"
RECEIPT = BASE / "SRFDI_G_JUNE_AUTH_MERGE_RECEIPT_v0_4.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_4.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_12.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthMergeReceiptV04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_receipt_binds_exact_decision_head_assurance_and_merge(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.receipt["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.receipt["decision"])
        self.assertEqual(431, self.receipt["pr_number"])
        self.assertEqual("cd1f9e71a9dc50a2588c0156885c178da5b8695e", self.receipt["tested_decision_head"])
        self.assertEqual("73e20265adc5aeb4d6947a0dc4ab32d97253cbf0", self.receipt["merge_commit"])
        self.assertEqual("PASS", self.receipt["assurance"]["result"])
        self.assertEqual(565, self.receipt["assurance"]["repository_test_count"])
        self.assertEqual(31266647985, self.receipt["assurance"]["repository_suite_run"])
        self.assertEqual(31266647997, self.receipt["assurance"]["tiered_workflow_run"])

    def test_authoritative_state_is_ready_but_token_unconsumed(self) -> None:
        self.assertEqual("AUTHORISED_CURRENT_UNCONSUMED", self.state["state_role"])
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10-v0.4", self.state["active_packet"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual(self.token["token_id"], self.state["exact_bindings"]["authority_token_id"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

    def test_historical_v04_merge_state_routes_exact_wp10_without_widening_authority(self) -> None:
        self.assertEqual("SRFDI-WP10-v0.4", self.state["active_packet"])
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual(self.token["token_id"], self.state["exact_bindings"]["authority_token_id"])

        self.assertTrue(self.pointer["authoritative_state"].startswith("registries/implementation/srfd/OVC_SRFDI_STATE_v0_"))
        self.assertEqual(self.token["token_id"], self.pointer["authority_token_id"])
        self.assertFalse(self.pointer["superseded_authority_token_consumed"])

    def test_exact_run_bindings_are_preserved_post_merge(self) -> None:
        bindings = self.state["exact_bindings"]
        self.assertEqual("2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29", bindings["manifest_binding_sha256"])
        self.assertEqual("576608343486e6fe5e0992b2e165491f7fea1c6401c202e0056a10447992ae99", bindings["source_population_binding_logical_sha256"])
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", bindings["preregistration_v0_4_logical_sha256"])
        self.assertEqual("371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b", bindings["stability_metric_registry_v0_4_logical_sha256"])
        self.assertEqual("6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0", bindings["segmentation_registry_v0_3_logical_sha256"])
        self.assertEqual(8598, bindings["eligible_record_count"])


if __name__ == "__main__":
    unittest.main()
