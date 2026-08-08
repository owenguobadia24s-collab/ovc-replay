from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9d"
RECEIPT = BASE / "SRFDI_G9D_FREEZE_MERGE_RECEIPT.json"
DECISION = BASE / "SRFDI_G9D_FREEZE_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_10.json"


class SRFDIWP9DMergeReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_receipt_binds_exact_operator_decision_head_assurance_and_merge(self) -> None:
        self.assertEqual("SRFDI-G9D-FREEZE", self.receipt["gate_id"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.receipt["decision"])
        self.assertEqual(self.decision["operator_command"], self.receipt["operator_command"])
        self.assertEqual("bf2550a88dc154476d2ab83e8b5e47e511836eaa", self.receipt["approved_predecision_head"])
        self.assertEqual("40c9be2809ea645909af568ca5232b9526e2ac91", self.receipt["final_head"])
        self.assertEqual("0e94bf4d61272b685a8e972e695e88b6ca4cb3c7", self.receipt["merge_commit"])
        self.assertEqual(547, self.receipt["tests"]["repository_test_count"])
        self.assertEqual("PASS", self.receipt["tests"]["result"])

    def test_authoritative_state_freezes_v04_and_denies_june(self) -> None:
        authority = self.state["authority"]
        self.assertEqual("V0_4_PREREGISTRATION_AND_STABILITY_METRIC_FREEZE_ACTIVE", authority["implementation"])
        self.assertEqual("FROZEN_EXACT_VERSION", authority["preregistration_v0_4"])
        self.assertEqual("FROZEN_EXACT_VERSION", authority["stability_metric_registry_v0_4"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", authority["prior_june_authority_token_v0_3"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", authority["june"])
        self.assertEqual("DENIED", authority["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", authority["validation_2025"])
        self.assertEqual("NONE", authority["probability_risk_exposure_execution"])

    def test_exact_scientific_and_population_bindings_are_preserved(self) -> None:
        bindings = self.state["exact_bindings"]
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", bindings["preregistration_v0_4_logical_sha256"])
        self.assertEqual("371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b", bindings["stability_metric_registry_v0_4_logical_sha256"])
        self.assertEqual("6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0", bindings["segmentation_registry_v0_3_logical_sha256"])
        self.assertEqual("SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd", bindings["population_id"])
        self.assertEqual(8598, bindings["eligible_record_count"])
        self.assertFalse(bindings["prior_v0_3_authority_token_consumed"])

    def test_historical_v10_routes_only_to_fresh_june_authority_preparation(self) -> None:
        self.assertEqual("FROZEN_AWAITING_NEW_JUNE_AUTH_PREPARATION", self.state["status"])
        self.assertEqual("SRFDI-G-JUNE-AUTH-PREPARATION-v0.4", self.state["current_gate"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", self.state["authority"]["june"])
        self.assertFalse(self.state["exact_bindings"]["prior_v0_3_authority_token_consumed"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["stop_at"])


if __name__ == "__main__":
    unittest.main()
