from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REVIEW_PATH = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/operator-review/C1C_G5_CORR3_WORKFLOW_ACCEPTED_REVIEW_INPUT.json"
DECISION_PATH = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/operator-review/C1C_G5_CORR3_WORKFLOW_ACCEPTED_OPERATOR_DECISION.json"
STATE_PATH = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_PROGRAMME_STATE.json"
TARGET = "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81"
CONTEXT_SHA = "01d4b1d1a4c060a5b2fb6a16b484fc94de8d43ad07ae65e0cb5a7b17412e65ef"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class Corr3WorkflowAcceptedOperatorDecisionTests(unittest.TestCase):
    def test_review_input_is_exact_bounded_workflow_acceptance(self) -> None:
        review = load(REVIEW_PATH)
        decision = review["decision"]
        self.assertEqual(review["schema"], "ovc-c1c-g5-corr3-review-input/v1")
        self.assertEqual(decision["candidate_window_id"], TARGET)
        self.assertEqual(decision["prior_disposition"], "DEFER_PILOT_OBJECT")
        self.assertEqual(decision["final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertEqual(decision["evidence_context_sha256"], CONTEXT_SHA)
        self.assertGreaterEqual(len(decision["evidence_references"]), 7)
        self.assertGreaterEqual(len(decision["acceptance_criteria"]), 6)
        self.assertFalse(review["second_machine_replay_required"])
        self.assertTrue(review["pilot_only"])
        self.assertEqual(review["promotion_eligibility"], "NON_PROMOTABLE")
        self.assertEqual(review["canonical_append"], "DENIED")

    def test_operator_record_is_bound_to_committed_review_input(self) -> None:
        decision = load(DECISION_PATH)
        review_sha = hashlib.sha256(REVIEW_PATH.read_bytes()).hexdigest()
        self.assertEqual(decision["operator_command"], "@GitHub approve WORKFLOW_ACCEPTED")
        self.assertEqual(decision["candidate_window_id"], TARGET)
        self.assertEqual(decision["final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertEqual(decision["review_input_file_sha256"], review_sha)
        self.assertEqual(decision["evidence_context_logical_sha256"], CONTEXT_SHA)
        self.assertEqual(decision["final_gate"]["decision"], "NOT_TAKEN")
        self.assertTrue(decision["final_gate"]["operator_approval_required_after_signed_local_finalization"])
        self.assertTrue(decision["local_finalization"]["required"])
        self.assertTrue(decision["local_finalization"]["requires_operator_private_ed25519_key"])
        self.assertFalse(decision["local_finalization"]["second_machine_replay_required"])
        self.assertEqual(decision["authority"]["machine_replay"], "DENIED_NOT_REQUIRED")
        self.assertEqual(decision["authority"]["canonical_append"], "DENIED")
        self.assertEqual(decision["authority"]["selector_mutation"], "DENIED")
        self.assertEqual(decision["authority"]["release_mutation"], "DENIED")

    def test_programme_state_advances_only_to_local_signed_finalization(self) -> None:
        state = load(STATE_PATH)
        local = state["operator_local_review"]
        blocker = state["blockers"][0]
        self.assertEqual(local["status"], "OPERATOR_WORKFLOW_ACCEPTED_AWAITING_LOCAL_SIGNATURE_FINALIZATION")
        self.assertEqual(local["candidate_window_id"], TARGET)
        self.assertEqual(local["final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertEqual(local["final_gate_decision"], "NOT_TAKEN")
        self.assertEqual(local["review_input_file_sha256"], hashlib.sha256(REVIEW_PATH.read_bytes()).hexdigest())
        self.assertEqual(state["next_packet"], "C1C-G5-CORR3-LOCAL-FINALIZE")
        self.assertEqual(blocker["status"], "OPEN_OPERATOR_LOCAL_SIGNATURE_AND_FINALIZATION_REQUIRED")
        self.assertIn("Machine replay", state["prohibitions"])
        self.assertIn("Selector or release mutation", state["prohibitions"])
        self.assertIn("Validation consumption", state["prohibitions"])


if __name__ == "__main__":
    unittest.main()
