from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a-freeze/SRFDI_G10A_FREEZE_OPERATOR_DECISION.json"
GATE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a-freeze/SRFDI_G10A_FREEZE_OPERATOR_PACKET.json"
FREEZE = ROOT / "registries/research/srfd/g10a_family_capacity_backend_freeze_v0_1.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_18_G10A_FREEZE_APPROVED_PENDING_MERGE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIG10AFreezeOperatorDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text())
        self.gate = json.loads(GATE.read_text())
        self.freeze = json.loads(FREEZE.read_text())
        self.state = json.loads(STATE.read_text())
        self.pointer = json.loads(POINTER.read_text())

    def test_operator_pass_is_exact_and_gate_candidate_is_preserved(self) -> None:
        self.assertEqual("OVC APPROVE SRFDI-G10A-FREEZE PASS", self.decision["operator_command"])
        self.assertEqual("PASS", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.decision["gate_id"])
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertEqual("OVC APPROVE SRFDI-G10A-FREEZE PASS", self.gate["exact_operator_command"])

    def test_freeze_is_capacity_only_and_science_population_are_unchanged(self) -> None:
        bindings = self.freeze["frozen_scientific_bindings"]
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", bindings["preregistration_v0_4_logical_sha256"])
        self.assertEqual("SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd", bindings["population_id"])
        self.assertEqual(8598, bindings["eligible_record_count"])
        self.assertEqual(36, self.freeze["comparability_domain_count"])
        self.assertEqual(35380668, self.freeze["exact_pair_opportunity_count"])
        self.assertEqual(1944, self.freeze["family_configuration_count"])
        self.assertEqual("68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866", self.freeze["catalog_grid_hash"])
        self.assertEqual("CAPACITY_IMPLEMENTATION_FREEZE_ONLY_NONSCIENTIFIC", self.freeze["authority_state"])

    def test_reserved_authority_remains_denied(self) -> None:
        delta = self.decision["authority_delta"]
        self.assertEqual("DENIED_REQUIRES_SEPARATE_NEW_SRFDI_G_JUNE_AUTH", delta["fresh_june_scientific_run"])
        self.assertEqual("DENIED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", delta["validation_2025"])
        for key in ("scientific_parameter_or_method_change", "family_representation_semantic_promotion", "selector_activation_or_replacement", "canonical_or_r2_publication", "probability_risk_exposure_execution"):
            self.assertEqual("NONE", delta[key])
        self.assertTrue(self.freeze["prohibitions"]["fresh_scientific_june_run"])
        self.assertTrue(self.freeze["prohibitions"]["validation_read"])

    def test_historical_state_is_exact_while_pointer_may_advance_after_closeout(self) -> None:
        self.assertEqual("APPROVED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("FROZEN_BY_OPERATOR_PENDING_MAIN_MERGE", self.state["authority"]["capacity_backend"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.state["authority"]["authority_token_v0_4"])
        self.assertEqual("SRFDI-G10A-FREEZE-MERGE-CLOSEOUT", self.state["next_packet"])
        self.assertIn(self.pointer["authoritative_state"], {"registries/implementation/srfd/OVC_SRFDI_STATE_v0_18_G10A_FREEZE_APPROVED_PENDING_MERGE.json", "registries/implementation/srfd/OVC_SRFDI_STATE_v0_19_G10A_FREEZE_COMPLETED.json"})
        self.assertIn(self.pointer["status"], {"APPROVED_PENDING_MERGE", "COMPLETED"})
        self.assertIn("FRESH_SCIENTIFIC_RUN_DENIED", self.pointer["june_execution"])
        if self.pointer["status"] == "APPROVED_PENDING_MERGE":
            self.assertEqual("SRFDI-G10A-FREEZE", self.pointer["current_gate"])
            self.assertEqual("SRFDI-G10A-FREEZE-MERGE-CLOSEOUT", self.pointer["next_packet"])
        else:
            self.assertEqual("SRFDI-G-JUNE-AUTH", self.pointer["current_gate"])
            self.assertEqual("SRFDI-G-JUNE-AUTH-PREP", self.pointer["next_packet"])

    def test_predecision_assurance_and_blocker_evidence_are_exact(self) -> None:
        assurance = self.decision["predecision_assurance"]
        self.assertEqual({"run_id": 31275740239, "result": "SUCCESS"}, assurance["repository_suite"])
        self.assertEqual({"run_id": 31275740231, "result": "SUCCESS"}, assurance["tiered_profile_compatibility_merge_readiness"])
        self.assertEqual(0, assurance["review_threads"]["unresolved"])
        self.assertEqual("PRESERVE_UNMERGED", self.decision["preserved_blocker_evidence"]["status"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.decision["preserved_blocker_evidence"]["v0_4_authority_token"])


if __name__ == "__main__":
    unittest.main()
