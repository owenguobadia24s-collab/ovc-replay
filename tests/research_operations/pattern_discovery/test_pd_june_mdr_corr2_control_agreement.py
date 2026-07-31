from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.control_agreement_assurance import canonical_sha256, cohen_kappa, score_blinded_review

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2"
CONTROL = BASE / "PD_JUNE_MDR_CORR2_CONTROL_LEDGER.json"
INDEX = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_INDEX.json"
ANSWER = BASE / "PD_JUNE_MDR_CORR2_SEALED_ANSWER_KEY.json"
TEMPLATE = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_RESPONSE.template.json"
DECISION = BASE / "PD_JUNE_MDR_G1_CORR2_OPERATOR_DECISION.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


def load_batched_review() -> dict:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cards: list[dict] = []
    for item in index["batches"]:
        path = BASE / item["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["file_sha256"]:
            raise AssertionError(path)
        batch = json.loads(raw)
        if canonical_sha256(batch["cards"]) != item["cards_canonical_sha256"]:
            raise AssertionError(path)
        cards.extend(batch["cards"])
    review = dict(index)
    review["cards"] = cards
    return review


class PDJuneMDRCorr2ControlAgreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.control = json.loads(CONTROL.read_text(encoding="utf-8"))
        cls.review = load_batched_review()
        cls.answer = json.loads(ANSWER.read_text(encoding="utf-8"))
        cls.template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_control_population_is_exact_and_non_mutating(self) -> None:
        self.assertEqual(self.control["population"]["immutable_candidate_count"], 208)
        self.assertEqual(len(self.control["controls"]), 10)
        self.assertTrue(self.control["verification"]["all_controls_candidate_disjoint"])
        self.assertTrue(self.control["verification"]["all_control_state_ids_unique"])
        self.assertEqual(self.control["verification"]["matched_quality_exact_count"], 6)
        self.assertFalse(self.control["authority"]["candidate_population_mutated"])
        self.assertFalse(self.control["authority"]["machine_replay_performed"])

    def test_blind_packet_is_exact(self) -> None:
        self.assertEqual(self.review["card_count"], 16)
        self.assertEqual(self.answer["composition"], {"matched_controls": 6, "population_controls": 4, "promoted_candidates": 6})
        self.assertEqual({item["blind_id"] for item in self.review["cards"]}, {item["blind_id"] for item in self.answer["mapping"]})

    def test_scoring_remains_fail_closed(self) -> None:
        perfect = json.loads(json.dumps(self.template))
        mapping = {item["blind_id"]: item for item in self.answer["mapping"]}
        for response in perfect["responses"]:
            expected = mapping[response["blind_id"]]
            response["trigger_classification"] = expected["expected_trigger_classification"]
            response["structural_description_verdict"] = "SUPPORTED"
            response["review_disposition"] = expected["prior_operator_disposition"] or "REJECT_PILOT_OBJECT"
            response["confidence"] = 5
        self.assertEqual(score_blinded_review(self.review, self.answer, perfect)["bounded_result"], "PASS_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW")
        control_id = next(item["blind_id"] for item in self.answer["mapping"] if item["object_class"] == "NEGATIVE_CONTROL")
        next(item for item in perfect["responses"] if item["blind_id"] == control_id)["trigger_classification"] = "BREACH_ACTIVE"
        self.assertEqual(score_blinded_review(self.review, self.answer, perfect)["bounded_result"], "DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW")

    def test_final_operator_defer_preserves_authority(self) -> None:
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertIsNone(self.state["next_packet"])
        self.assertIn("MACHINE_REPLAY", self.state["retained_prohibitions"])
        self.assertIn("R2_PUBLICATION", self.state["retained_prohibitions"])

    def test_kappa_helper(self) -> None:
        self.assertEqual(cohen_kappa(["A", "B"], ["A", "B"]), 1.0)
        self.assertIsNone(cohen_kappa([], []))


if __name__ == "__main__":
    unittest.main()
