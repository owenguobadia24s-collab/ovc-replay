from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSITIONS = ROOT / "registries/opt_b/c2/vnext/C2_TRANSITION_CLASSIFICATION_CANDIDATE_v0_1.jsonc"
DETECTORS = ROOT / "registries/opt_b/c2/vnext/C2_DETECTOR_POLICY_CANDIDATES_v0_1.jsonc"
PACKET = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp7/CEAR_G7_OPERATOR_DECISION_PACKET.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G7_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG7GateTests(unittest.TestCase):
    def test_transition_candidate_is_complete_non_effective_and_semantically_neutral(self) -> None:
        candidate = load(TRANSITIONS)
        self.assertFalse(candidate["effective"])
        self.assertFalse(candidate["active"])
        self.assertFalse(candidate["canonical"])
        self.assertEqual(
            {"NO_CHANGE", "MEASUREMENT_CHANGE", "CATEGORICAL_CHANGE", "STRUCTURAL_CHANGE", "REFERENCE_IDENTITY_CHANGE", "COMPUTABILITY_CHANGE"},
            {item["class_id"] for item in candidate["transition_classes"]},
        )
        self.assertTrue(all(item["semantic_authority"] == "NONE" for item in candidate["transition_classes"]))
        self.assertFalse(candidate["comparison_contract"]["object_identity_change_is_crossing"])
        self.assertIn("REVERSAL", candidate["prohibited_classes"])
        self.assertIn("OUTCOME", candidate["prohibited_classes"])

    def test_detector_candidates_are_raw_inactive_noncanonical_and_threshold_free(self) -> None:
        registry = load(DETECTORS)
        self.assertFalse(registry["effective"])
        self.assertIsNone(registry["active_detector_id"])
        self.assertIsNone(registry["canonical_detector_id"])
        self.assertEqual(6, len(registry["policies"]))
        for policy in registry["policies"]:
            self.assertFalse(policy["active"])
            self.assertFalse(policy["canonical"])
            self.assertEqual([], policy["numeric_thresholds"])
            self.assertEqual("NONE", policy["semantic_authority"])
        crossing = next(item for item in registry["policies"] if item["detector_id"] == "C2.DETECTOR.FIXED_OBJECT_CROSSING.v1")
        self.assertFalse(crossing["ohlc_directional_authority"])
        distance = next(item for item in registry["policies"] if item["detector_id"] == "C2.DETECTOR.RAW_DISTANCE_CHANGE.v1")
        self.assertFalse(distance["approaching_label_authority"])
        reference = next(item for item in registry["policies"] if item["detector_id"] == "C2.DETECTOR.REFERENCE_IDENTITY_CHANGE.v1")
        self.assertFalse(reference["crossing_authority"])

    def test_semantic_event_episode_and_reserved_authorities_remain_denied(self) -> None:
        registry = load(DETECTORS)
        prohibited = set(registry["prohibited_outputs"])
        self.assertTrue({"APPROACHING", "TESTING", "REJECTING", "ACCEPTING", "EVENT_ID", "EPISODE_ID", "PROBABILITY", "OUTCOME"}.issubset(prohibited))
        denied = set(registry["explicit_non_effects"])
        self.assertIn("NO_DETECTOR_ACTIVATION", denied)
        self.assertIn("NO_NUMERIC_THRESHOLD_PARAMETER_OR_SCALE_SELECTION", denied)
        self.assertIn("NO_PARENT_RESOLVER_OR_DENOMINATOR_POLICY", denied)
        self.assertIn("NO_RELEASE_PUBLICATION_VALIDATION", denied)

    def test_operator_packet_is_one_complete_reserved_decision(self) -> None:
        packet = load(PACKET)
        self.assertEqual("CEAR-G7", packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", packet["gate_class"])
        self.assertTrue(packet["operator_decision_required"])
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE CEAR-G7 PASS", packet["exact_operator_decision_text"])
        self.assertEqual({"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}, set(packet["allowed_decisions"]))
        self.assertEqual([], packet["tests_and_qa"]["blocking_warnings"])
        self.assertEqual([], packet["tests_and_qa"]["unresolved_issues"])
        self.assertIn("DETECTOR_ACTIVATION_OR_CANONICAL_SELECTION", packet["proposed_authority_delta"]["explicitly_not_granted"])
        self.assertIn("PARENT_CONTEXT_RESOLVER_POLICY", packet["proposed_authority_delta"]["explicitly_not_granted"])
        self.assertTrue(packet["exact_work_after_approval"])

    def test_gate_state_denies_execution_and_preserves_active_c2(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("GATE_READY_NO_EXECUTION_AUTHORITY", state["authority"]["wp7"])
        self.assertEqual("NOT_GRANTED", state["authority"]["transition_classifier"])
        self.assertFalse(state["candidate_artifacts"]["effective"])
        self.assertEqual([], state["blockers"])
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
