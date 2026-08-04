from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp7"
DECISION = RELEASE / "CEAR_G7_OPERATOR_DECISION.json"
RECEIPT = RELEASE / "CEAR_G7_AUTHORITY_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G7_APPROVED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG7DecisionRecordTests(unittest.TestCase):
    def test_operator_pass_is_exact_immutable_and_bounded(self) -> None:
        decision = load(DECISION)
        self.assertEqual("CEAR-G7.OPERATOR.PASS.20260804T234400+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE CEAR-G7 PASS", decision["decision_text"])
        self.assertEqual("OPERATOR", decision["decision_authority"])
        self.assertEqual("d4c209163287436c604f13164f4418b978f9203e", decision["assured_predecision_head"])
        self.assertEqual(6, len(decision["approved_authority_delta"]["detectors"]))
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("DETECTOR_ACTIVATION_OR_CANONICAL_SELECTION", denied)
        self.assertIn("PARENT_CONTEXT_RESOLVER_POLICY", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)

    def test_evidence_constraints_fail_closed_without_semantic_authority(self) -> None:
        constraints = load(DECISION)["evidence_constraints"]
        self.assertEqual("SAME_IMMUTABLE_OBJECT_AND_ORDERED_M1_OR_TICK_PATH_REQUIRED", constraints["directional_crossing"])
        self.assertEqual("NO_DIRECTIONAL_PATH_ORDER_AUTHORITY", constraints["ohlc"])
        self.assertEqual("NEVER_CROSSING", constraints["reference_identity_change"])
        self.assertEqual("FAIL_CLOSED_NO_FALLBACK", constraints["missing_ambiguous_or_censored"])

    def test_receipt_and_programme_state_release_only_bounded_implementation(self) -> None:
        receipt = load(RECEIPT)
        state = load(STATE)
        self.assertEqual("APPROVED_PENDING_DECISION_PR_MERGE", receipt["authority_state"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["detector_activation"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["semantic_event_episode"])
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("C2AR-WP7-IMPLEMENTATION", state["active_packet"])
        self.assertEqual("NOT_GRANTED", state["authority"]["parent_context_resolver"])
        self.assertEqual("NONE", state["authority"]["release_publication_validation"])


if __name__ == "__main__":
    unittest.main()
