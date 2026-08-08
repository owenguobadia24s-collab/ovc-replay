from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-remaining-sequence-delegation/SRFDI_REMAINING_SEQUENCE_OPERATOR_DELEGATION_v0_1.json"
REGISTRY = ROOT / "registries/implementation/srfd/SRFDI_REMAINING_SEQUENCE_DELEGATION_v0_1.json"


class SRFDIRemainingSequenceDelegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.registry = json.loads(REGISTRY.read_text())

    def test_operator_delegates_remaining_sequence_without_routine_stops(self) -> None:
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("DELEGATE_REMAINING_SEQUENCE_AUTO_CONTINUE", self.decision["decision"])
        self.assertFalse(self.decision["effective_scope"]["operator_stop_required"])
        self.assertEqual([], self.registry["remaining_operator_stops"])
        self.assertIn("SRFDI-G-JUNE-AUTH", self.registry["auto_continue_sequence"])
        self.assertIn("SRFDI-G11", self.registry["auto_continue_sequence"])

    def test_june_is_only_conditionally_preauthorized_and_old_token_is_not_reusable(self) -> None:
        policy = self.decision["automatic_decision_policy"]["SRFDI-G-JUNE-AUTH"]
        self.assertEqual("AUTHORIZE_JUNE", policy["decision_if_all_exact_prerequisites_pass"])
        self.assertIn("NEW_FRESH_NONREUSABLE_AUTHORITY_TOKEN_CREATED_AND_VERIFIED", policy["requirements"])
        self.assertEqual("MUST_REMAIN_CONSUMED_NOT_REUSABLE", self.decision["preserved_history"]["consumed_v0_4_authority_token"])

    def test_g11_is_scientific_disposition_only(self) -> None:
        g11 = self.decision["automatic_decision_policy"]["SRFDI-G11"]
        self.assertEqual("AUTO_RECORD_DECOMPOSED_SCIENTIFIC_DISPOSITIONS_FROM_FROZEN_PREREGISTERED_RULES_AND_EVIDENCE", g11["decision"])
        self.assertIn("NO_METHOD_PROMOTION", g11["prohibitions"])
        self.assertIn("NO_2021_2023_DISCOVERY_AUTO_START", g11["prohibitions"])
        self.assertIn("NO_VALIDATION_CONSUMPTION", g11["prohibitions"])

    def test_reserved_authority_remains_denied(self) -> None:
        effect = self.decision["authority_effect"]
        self.assertEqual("DENIED", effect["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", effect["validation_2025"])
        self.assertEqual("NONE", effect["production_activation"])
        self.assertEqual("NONE", effect["selector_change"])
        self.assertEqual("NONE", effect["family_or_semantic_promotion"])
        self.assertEqual("NONE", effect["canonical_or_r2_publication"])
        self.assertEqual("NONE", effect["probability_risk_exposure_execution"])
        self.assertTrue(self.registry["hard_blockers_remain_fail_closed"])


if __name__ == "__main__":
    unittest.main()
