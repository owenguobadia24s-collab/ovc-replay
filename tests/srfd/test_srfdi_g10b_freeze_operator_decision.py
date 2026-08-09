from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_OPERATOR_DECISION.json"
GATE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b-freeze/SRFDI_G10B_FREEZE_OPERATOR_PACKET.json"
FREEZE = ROOT / "registries/research/srfd/wp10b_segmentation_execution_binding_freeze_v0_1.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_31_G10B_FREEZE_APPROVED_PENDING_MERGE.json"


class SRFDIG10BFreezeOperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.gate = json.loads(GATE.read_text())
        cls.freeze = json.loads(FREEZE.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_operator_pass_is_exact(self):
        self.assertEqual("OVC APPROVE SRFDI-G10B-FREEZE PASS", self.decision["operator_command"])
        self.assertEqual("PASS", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("SRFDI-G10B-FREEZE", self.decision["gate_id"])
        self.assertEqual("GATE_READY", self.gate["status"])

    def test_execution_binding_only_is_frozen(self):
        self.assertEqual("FROZEN_BY_OPERATOR_PENDING_MAIN_MERGE", self.freeze["status"])
        self.assertEqual("EXECUTION_BINDING_FREEZE_ONLY_NONSCIENTIFIC", self.freeze["authority_state"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1", self.freeze["candidate_logical_sha256"])
        self.assertEqual("EXACT_WHOLE_OBJECT_EQUALITY", self.freeze["validation_contract"]["production_reference_output_equality"])
        self.assertEqual("FORBIDDEN", self.freeze["validation_contract"]["posthoc_empirical_count_targets"])

    def test_science_and_reserved_authority_remain_frozen_or_denied(self):
        bindings = self.freeze["frozen_scientific_bindings"]
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", bindings["preregistration_v0_4_logical_sha256"])
        self.assertEqual("6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0", bindings["segmentation_registry_logical_sha256"])
        self.assertEqual(8598, bindings["eligible_record_count"])
        self.assertEqual(1944, bindings["family_configuration_count"])
        delta = self.decision["authority_delta"]
        self.assertTrue(delta["fresh_june_scientific_run"].startswith("DENIED_REQUIRES_SEPARATE_NEW_EXACT"))
        self.assertEqual("DENIED", delta["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", delta["validation_2025"])
        for key in ("scientific_parameter_or_method_change", "family_representation_semantic_promotion", "selector_activation_or_replacement", "canonical_or_r2_publication", "probability_risk_exposure_execution"):
            self.assertEqual("NONE", delta[key])

    def test_consumed_run_is_preserved_and_state_is_approved_pending_merge(self):
        blocked = self.freeze["blocked_run"]
        self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", blocked["token_state"])
        self.assertEqual("FORBIDDEN", blocked["resume"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("FROZEN_BY_OPERATOR_PENDING_MAIN_MERGE", self.state["authority"]["segmentation_execution_binding"])
        self.assertEqual("SRFDI-G10B-FREEZE-MERGE-CLOSEOUT", self.state["next_packet"])


if __name__ == "__main__":
    unittest.main()
