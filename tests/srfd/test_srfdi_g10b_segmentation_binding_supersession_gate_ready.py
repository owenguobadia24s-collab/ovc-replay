from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10b"
OPERATOR = BASE / "SRFDI_G10B_OPERATOR_PACKET.json"
QA = BASE / "SRFDI_G10B_QA_PACKET.json"
PREP = BASE / "SRFDI_WP10B_PREPARATION_RECORD.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_28_G10B_SUPERSESSION_GATE_READY_CANDIDATE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
SEGMENTATION = ROOT / "registries/research/srfd/segmentation_boundary_packs_v0_3.json"


class SRFDIG10BSegmentationBindingSupersessionGateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.operator = json.loads(OPERATOR.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.prep = json.loads(PREP.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.segmentation = json.loads(SEGMENTATION.read_text())

    def test_gate_is_preparation_only_and_operator_required(self) -> None:
        self.assertEqual("SRFDI-G10B", self.operator["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", self.operator["gate_class"])
        self.assertEqual("SUPERSEDE", self.operator["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G10B SUPERSEDE", self.operator["exact_operator_command"])
        self.assertEqual("NONE", self.prep["authority_effect"])

    def test_current_pointer_preserves_blocker_and_only_adds_bounded_remediation(self) -> None:
        self.assertIn(self.pointer["status"], {"BLOCKED", "AUTHORIZED_REMEDIATION_ONLY"})
        self.assertTrue(self.pointer["authority_token_consumed"])
        self.assertEqual(
            "CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",
            self.pointer["authority_token_state"],
        )
        self.assertTrue(self.pointer["blocker_evidence"].endswith("SRFDI_WP10_V07_EXECUTION_BLOCKER.json"))
        if self.pointer["status"] == "BLOCKED":
            self.assertEqual("HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH", self.pointer["stop_at"])
            self.assertIsNone(self.pointer["next_packet"])
        else:
            self.assertEqual("SRFDI-G10B", self.pointer["current_gate"])
            self.assertEqual("SRFDI-WP10B", self.pointer["next_packet"])
            self.assertEqual("SRFDI-G10B-FREEZE", self.pointer["stop_at"])
            self.assertEqual("AUTHORIZED_SEGMENTATION_EXECUTION_BINDING_REMEDIATION_ONLY", self.pointer["wp10b_execution"])
            self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY", self.pointer["june_execution"])

    def test_candidate_state_is_not_the_current_pointer(self) -> None:
        self.assertEqual(
            "CANDIDATE_PROPOSAL_ONLY_NOT_CURRENT_POINTER",
            self.state["state_role"],
        )
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(
            "DENIED_PENDING_SRFDI_G10B_OPERATOR_SUPERSESSION",
            self.state["authority"]["wp10b_execution"],
        )

    def test_frozen_science_and_segmentation_registry_are_unchanged(self) -> None:
        frozen = self.operator["frozen_scientific_bindings"]
        self.assertEqual(8598, frozen["eligible_record_count"])
        self.assertEqual(36, frozen["comparability_domain_count"])
        self.assertEqual(35380668, frozen["exact_pair_opportunity_count"])
        self.assertEqual(1944, frozen["family_configuration_count"])
        self.assertEqual(
            frozen["segmentation_registry_logical_sha256"],
            self.prereg["inherited_frozen_surfaces"]["segmentation_registry_logical_sha256"],
        )
        self.assertEqual(
            "RUN_CHANGE_SEGMENTATION",
            next(
                item["method_id"]
                for item in self.segmentation["packs"]
                if item["method_id"] == "RUN_CHANGE_SEGMENTATION"
            ),
        )

    def test_posthoc_observed_counts_cannot_become_targets(self) -> None:
        classification = self.operator["court_record_classification"]
        self.assertFalse(classification["scientific_registry_contains_expected_output_counts"])
        self.assertFalse(classification["preregistration_contains_expected_output_counts"])
        self.assertTrue(classification["runner_contract_contains_expected_output_counts"])
        self.assertIn("MUST_NOT_BECOME_REPLACEMENT_ACCEPTANCE_TARGETS", classification["posthoc_rebinding_guard"])
        prohibited = " ".join(self.operator["proposed_authority_delta_if_SUPERSEDE"]["prohibited_work"])
        self.assertIn("232 / 7013 / 6781", prohibited)

    def test_proposed_fix_requires_reference_equivalence_and_invariants(self) -> None:
        allowed = " ".join(self.operator["proposed_authority_delta_if_SUPERSEDE"]["allowed_work"])
        self.assertIn("independent reference execution", allowed)
        self.assertIn("segment_count = stream_count + boundary_count", allowed)
        self.assertEqual("SRFDI-G10B-FREEZE", self.operator["proposed_authority_delta_if_SUPERSEDE"]["next_operator_gate"])

    def test_all_reserved_firewalls_remain_closed(self) -> None:
        current = self.operator["current_authority"]
        self.assertEqual("NONE", current["new_run_authority"])
        self.assertEqual("DENIED", current["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", current["validation_2025"])
        self.assertEqual("NONE", current["scientific_promotion"])
        self.assertEqual("NONE", current["selector_family_semantic_publication"])
        self.assertEqual("NONE", current["probability_risk_exposure_execution"])
        self.assertEqual("PASS_FOR_OPERATOR_REVIEW_WITH_POSTHOC_REBINDING_GUARD", self.qa["qa_result"])
        self.assertEqual("DENIED", self.pointer.get("provider_fetch", "DENIED"))
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer.get("validation_2025", "LOCKED_UNCONSUMED"))
        self.assertEqual("NONE", self.pointer.get("scientific_promotion", "NONE"))
        self.assertEqual("NONE", self.pointer.get("selector_family_semantic_publication", "NONE"))
        self.assertEqual("NONE", self.pointer.get("probability_risk_exposure_execution", "NONE"))


if __name__ == "__main__":
    unittest.main()
