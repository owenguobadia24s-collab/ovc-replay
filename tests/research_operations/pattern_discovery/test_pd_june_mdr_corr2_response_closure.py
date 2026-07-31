from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.control_agreement_assurance import canonical_sha256, score_blinded_review

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2"
INDEX = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_INDEX.json"
ANSWER = BASE / "PD_JUNE_MDR_CORR2_SEALED_ANSWER_KEY.json"
RESPONSE = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_RESPONSE.completed.json"
SCORE = BASE / "PD_JUNE_MDR_CORR2_SCORED_REVIEW.json"
VALIDATION = BASE / "PD_JUNE_MDR_CORR2_RESPONSE_VALIDATION_RECEIPT.json"
COMPARISON = BASE / "PD_JUNE_MDR_CORR2_POST_UNBLINDING_COMPARISON.json"
COMPARISON_MD = BASE / "PD_JUNE_MDR_CORR2_POST_UNBLINDING_COMPARISON.md"
QA = BASE / "PD_JUNE_MDR_CORR2_CLOSURE_QA_PACKET.json"
RETURN_GATE = BASE / "PD_JUNE_MDR_G1_CORR2_RETURN_GATE_PACKET.json"
DECISION = BASE / "PD_JUNE_MDR_G1_CORR2_OPERATOR_DECISION.json"
MERGE_RECEIPT = BASE / "PD_JUNE_MDR_G1_CORR2_MERGE_RECEIPT.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_corr2_response_closure_v0_1.schema.json"
DECISION_SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_g1_corr2_operator_decision_v0_1.schema.json"
MERGE_SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_g1_corr2_merge_receipt_v0_1.schema.json"


def load_review() -> dict:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cards: list[dict] = []
    for item in index["batches"]:
        path = BASE / item["path"]
        raw = path.read_bytes()
        if len(raw) != item["size_bytes"]:
            raise AssertionError(f"batch size mismatch: {path}")
        if hashlib.sha256(raw).hexdigest() != item["file_sha256"]:
            raise AssertionError(f"batch hash mismatch: {path}")
        batch = json.loads(raw)
        if canonical_sha256(batch["cards"]) != item["cards_canonical_sha256"]:
            raise AssertionError(f"batch canonical hash mismatch: {path}")
        cards.extend(batch["cards"])
    review = dict(index)
    review["cards"] = cards
    return review


class PDJuneMDRCorr2ResponseClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.review = load_review()
        cls.answer = json.loads(ANSWER.read_text(encoding="utf-8"))
        cls.response = json.loads(RESPONSE.read_text(encoding="utf-8"))
        cls.score = json.loads(SCORE.read_text(encoding="utf-8"))
        cls.validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
        cls.comparison = json.loads(COMPARISON.read_text(encoding="utf-8"))
        cls.qa = json.loads(QA.read_text(encoding="utf-8"))
        cls.return_gate = json.loads(RETURN_GATE.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.merge_receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_closure_decision_and_merge_files_exist(self) -> None:
        for path in (INDEX, ANSWER, RESPONSE, SCORE, VALIDATION, COMPARISON, COMPARISON_MD, QA, RETURN_GATE, DECISION, MERGE_RECEIPT, STATE, SCHEMA, DECISION_SCHEMA, MERGE_SCHEMA):
            self.assertTrue(path.is_file(), path)

    def test_completed_response_is_exactly_bound_and_frozen(self) -> None:
        self.assertEqual(self.response["review_status"], "COMPLETED")
        self.assertEqual(len(self.response["responses"]), 16)
        self.assertEqual(hashlib.sha256(RESPONSE.read_bytes()).hexdigest(), "1fb60b05b0a85cc95074bb2867b67f1debbdd2310ca5e98a3af2ba0b934e9a8d")
        self.assertEqual(self.validation["card_payload_binding"], "PASS_16_OF_16")
        self.assertTrue(self.validation["response_frozen_before_unblinding"])

    def test_repository_scorer_reproduces_stored_result(self) -> None:
        self.assertEqual(score_blinded_review(self.review, self.answer, self.response), self.score)
        self.assertEqual(self.score["bounded_result"], "DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW")
        metrics = self.score["metrics"]
        self.assertEqual(metrics["control_determinate_count"], 4)
        self.assertEqual(metrics["control_false_positive_count"], 0)
        self.assertEqual(metrics["promoted_trigger_detected_count"], 4)
        self.assertEqual(metrics["promoted_exact_reason_agreement_count"], 3)
        self.assertEqual(metrics["promoted_structural_contradiction_count"], 0)
        self.assertEqual(metrics["prior_repeat_disposition_agreement_count"], 0)
        self.assertEqual(metrics["prior_repeat_disposition_kappa"], -0.125)

    def test_operator_defer_and_squash_merge_are_recorded(self) -> None:
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertIsNone(self.decision["next_packet"])
        self.assertEqual(self.return_gate["gate_status"], "APPROVED_DEFER_CORR2_CLOSED_MERGE_READY")
        self.assertEqual(self.merge_receipt["merge_result"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(self.merge_receipt["packet_merge_commit"], "306e449acdaddbb0131fd01aca6098dd8ab0b7ef")
        self.assertIsNone(self.merge_receipt["next_packet"])

    def test_programme_state_is_completed_and_stopped(self) -> None:
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["decision"], "DEFER")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertEqual(self.state["merge_status"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(self.state["merge_commit"], "306e449acdaddbb0131fd01aca6098dd8ab0b7ef")
        self.assertIsNone(self.state["next_gate"])
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
