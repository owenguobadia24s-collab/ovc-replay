from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.control_agreement_assurance import (
    canonical_sha256,
    score_blinded_review,
)

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
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_corr2_response_closure_v0_1.schema.json"


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
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_closure_files_exist(self) -> None:
        for path in (
            INDEX, ANSWER, RESPONSE, SCORE, VALIDATION, COMPARISON, COMPARISON_MD,
            QA, RETURN_GATE, STATE, SCHEMA,
        ):
            self.assertTrue(path.is_file(), path)

    def test_completed_response_is_exactly_bound_and_frozen(self) -> None:
        self.assertEqual(self.response["review_status"], "COMPLETED")
        self.assertEqual(len(self.response["responses"]), 16)
        self.assertEqual(
            hashlib.sha256(RESPONSE.read_bytes()).hexdigest(),
            "1fb60b05b0a85cc95074bb2867b67f1debbdd2310ca5e98a3af2ba0b934e9a8d",
        )
        self.assertEqual(self.validation["response_file_sha256"], hashlib.sha256(RESPONSE.read_bytes()).hexdigest())
        self.assertEqual(self.validation["card_payload_binding"], "PASS_16_OF_16")
        self.assertEqual(self.validation["unique_blind_ids"], "PASS_16_OF_16")
        self.assertEqual(self.validation["required_fields"], "PASS_16_OF_16")
        self.assertEqual(self.validation["allowed_value_validation"], "PASS_16_OF_16")
        self.assertEqual(self.validation["confidence_validation"], "PASS_16_OF_16")
        self.assertTrue(self.validation["response_frozen_before_unblinding"])

    def test_repository_scorer_reproduces_stored_result(self) -> None:
        reproduced = score_blinded_review(self.review, self.answer, self.response)
        self.assertEqual(reproduced, self.score)
        self.assertEqual(self.score["bounded_result"], "DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW")
        self.assertEqual(self.score["general_market_description_reliability"], "NOT_ESTABLISHED_SINGLE_GAPPED_JUNE_SLICE")
        metrics = self.score["metrics"]
        self.assertEqual(metrics["control_determinate_count"], 4)
        self.assertEqual(metrics["control_false_positive_count"], 0)
        self.assertEqual(metrics["promoted_trigger_detected_count"], 4)
        self.assertEqual(metrics["promoted_exact_reason_agreement_count"], 3)
        self.assertEqual(metrics["promoted_structural_contradiction_count"], 0)
        self.assertEqual(metrics["prior_repeat_disposition_agreement_count"], 0)
        self.assertEqual(metrics["prior_repeat_disposition_kappa"], -0.125)

    def test_comparison_and_qa_preserve_bounded_interpretation(self) -> None:
        self.assertTrue(self.comparison["review_frozen_before_unblinding"])
        self.assertEqual(self.comparison["review_response_sha256"], self.validation["response_file_sha256"])
        self.assertEqual(self.comparison["metrics"], self.score["metrics"])
        self.assertEqual(self.comparison["acceptance"], self.score["acceptance"])
        self.assertEqual(self.qa["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(
            self.qa["qa_result"],
            "PASS_RESPONSE_VALIDATION_AND_REPRODUCIBLE_SCORING_BOUNDED_ACCEPTANCE_NOT_MET",
        )
        self.assertEqual(self.qa["recommendation"], "RETURN_TO_PD-JUNE-MDR-G1_WITH_DEFER_RECOMMENDATION")
        self.assertEqual(self.qa["gate_acceptance_result"], "FAIL_PREDECLARED_BOUNDED_PASS_CONDITIONS")

    def test_return_gate_requires_operator_and_grants_no_authority(self) -> None:
        self.assertEqual(self.return_gate["gate_id"], "PD-JUNE-MDR-G1")
        self.assertEqual(self.return_gate["gate_status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertTrue(self.return_gate["operator_approval_required"])
        self.assertEqual(self.return_gate["recommended_decision"], "DEFER")
        self.assertEqual(self.return_gate["proposed_authority_delta"], "NONE_DEFER_AND_PRESERVE_CURRENT_AUTHORITY")
        authority = self.return_gate["current_authority"]
        self.assertEqual(authority["provider_intake"], "DENIED")
        self.assertEqual(authority["machine_replay"], "DENIED")
        self.assertEqual(authority["canonical_discovery_processing_or_append"], "DENIED")
        self.assertEqual(authority["r2_publication"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_programme_state_is_at_operator_return_gate(self) -> None:
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["packet_id"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.state["operator_response_status"], "COMPLETED_VALIDATED_SCORED")
        self.assertEqual(self.state["operator_input_stage"], "PD-JUNE-MDR-G1_DECISION")
        self.assertEqual(self.state["review_status"], "OPERATOR_INPUT_REQUIRED")
        self.assertEqual(self.state["decision"], "PENDING_OPERATOR_DECISION")
        self.assertEqual(self.state["recommended_decision"], "DEFER")
        self.assertEqual(self.state["next_gate"], "PD-JUNE-MDR-G1")
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(self.state["next_packet_status"], "WAITING_OPERATOR_REVIEW_ARTIFACT")
        self.assertEqual(self.state["overall_verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
