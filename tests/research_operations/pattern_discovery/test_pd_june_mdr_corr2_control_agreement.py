from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.control_agreement_assurance import (
    canonical_sha256,
    cohen_kappa,
    score_blinded_review,
)

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2"
CONTROL = BASE / "PD_JUNE_MDR_CORR2_CONTROL_LEDGER.json"
INDEX = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_INDEX.json"
ANSWER = BASE / "PD_JUNE_MDR_CORR2_SEALED_ANSWER_KEY.json"
TEMPLATE = BASE / "PD_JUNE_MDR_CORR2_BLINDED_REVIEW_RESPONSE.template.json"
QA = BASE / "PD_JUNE_MDR_CORR2_QA_PACKET.json"
GUIDE = BASE / "PD_JUNE_MDR_CORR2_REVIEW_GUIDE.md"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
CONTRACT = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_MDR_CORR2_CONTROL_AND_AGREEMENT_ASSURANCE_CONTRACT_v0_1.md"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_corr2_control_agreement_v0_1.schema.json"


def load_batched_review() -> tuple[dict, list[Path]]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cards: list[dict] = []
    paths: list[Path] = []
    for item in index["batches"]:
        path = BASE / item["path"]
        raw = path.read_bytes()
        if len(raw) != item["size_bytes"]:
            raise AssertionError(f"batch size mismatch: {path}")
        if hashlib.sha256(raw).hexdigest() != item["file_sha256"]:
            raise AssertionError(f"batch hash mismatch: {path}")
        batch = json.loads(raw)
        if batch["card_count"] != item["card_count"]:
            raise AssertionError(f"batch card count mismatch: {path}")
        if canonical_sha256(batch["cards"]) != item["cards_canonical_sha256"]:
            raise AssertionError(f"batch card hash mismatch: {path}")
        cards.extend(batch["cards"])
        paths.append(path)
    review = dict(index)
    review["cards"] = cards
    return review, paths


class PDJuneMDRCorr2ControlAgreementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.control = json.loads(CONTROL.read_text(encoding="utf-8"))
        cls.review, cls.batch_paths = load_batched_review()
        cls.answer = json.loads(ANSWER.read_text(encoding="utf-8"))
        cls.template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        cls.qa = json.loads(QA.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_packet_files_exist(self) -> None:
        for path in (
            CONTROL, INDEX, *self.batch_paths, ANSWER, TEMPLATE, QA, GUIDE,
            STATE, CONTRACT, SCHEMA,
        ):
            self.assertTrue(path.is_file(), path)

    def test_control_population_is_exact_and_non_mutating(self) -> None:
        self.assertEqual(self.control["population"]["immutable_candidate_count"], 208)
        self.assertEqual(self.control["selection_rule"]["matched_control_count"], 6)
        self.assertEqual(self.control["selection_rule"]["population_control_count"], 4)
        self.assertEqual(self.control["selection_rule"]["total_control_count"], 10)
        self.assertEqual(len(self.control["controls"]), 10)
        self.assertTrue(self.control["verification"]["all_controls_candidate_disjoint"])
        self.assertTrue(self.control["verification"]["all_control_state_ids_unique"])
        self.assertEqual(self.control["verification"]["matched_quality_exact_count"], 6)
        self.assertFalse(self.control["authority"]["candidate_population_mutated"])
        self.assertFalse(self.control["authority"]["candidate_relabelled"])
        self.assertFalse(self.control["authority"]["machine_replay_performed"])

    def test_blind_packet_batches_and_answer_key_are_exact(self) -> None:
        self.assertEqual(self.review["review_status"], "OPERATOR_INPUT_REQUIRED")
        self.assertEqual(self.review["batch_count"], 4)
        self.assertEqual(self.review["card_count"], 16)
        self.assertEqual(len(self.review["cards"]), 16)
        self.assertEqual(
            self.answer["composition"],
            {"matched_controls": 6, "population_controls": 4, "promoted_candidates": 6},
        )
        self.assertEqual(self.answer["card_count"], 16)
        self.assertEqual(self.review["cards_canonical_sha256"], canonical_sha256(self.review["cards"]))
        self.assertEqual(self.answer["mapping_canonical_sha256"], canonical_sha256(self.answer["mapping"]))
        self.assertEqual(
            {item["blind_id"] for item in self.review["cards"]},
            {item["blind_id"] for item in self.answer["mapping"]},
        )
        self.assertTrue(all("source_object_id" not in card for card in self.review["cards"]))
        self.assertTrue(all("object_class" not in card for card in self.review["cards"]))

    def test_template_is_complete_but_unsubmitted(self) -> None:
        self.assertEqual(self.template["review_status"], "COMPLETED")
        self.assertEqual(len(self.template["responses"]), 16)
        self.assertTrue(all(item["confidence"] == 0 for item in self.template["responses"]))
        self.assertTrue(all(
            item["trigger_classification"] == "REPLACE_WITH_ALLOWED_VALUE"
            for item in self.template["responses"]
        ))

    def test_scoring_pass_and_fail_are_fail_closed(self) -> None:
        perfect = json.loads(json.dumps(self.template))
        mapping = {item["blind_id"]: item for item in self.answer["mapping"]}
        for response in perfect["responses"]:
            expected = mapping[response["blind_id"]]
            response["trigger_classification"] = expected["expected_trigger_classification"]
            response["structural_description_verdict"] = "SUPPORTED"
            response["review_disposition"] = (
                expected["prior_operator_disposition"]
                if expected["prior_operator_disposition"] is not None
                else "REJECT_PILOT_OBJECT"
            )
            response["confidence"] = 5
        scored = score_blinded_review(self.review, self.answer, perfect)
        self.assertEqual(scored["bounded_result"], "PASS_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW")
        self.assertEqual(scored["metrics"]["control_false_positive_count"], 0)
        self.assertEqual(scored["metrics"]["promoted_exact_reason_agreement_count"], 6)
        self.assertEqual(
            scored["general_market_description_reliability"],
            "NOT_ESTABLISHED_SINGLE_GAPPED_JUNE_SLICE",
        )

        failed = json.loads(json.dumps(perfect))
        control_id = next(
            item["blind_id"] for item in self.answer["mapping"]
            if item["object_class"] == "NEGATIVE_CONTROL"
        )
        next(item for item in failed["responses"] if item["blind_id"] == control_id)[
            "trigger_classification"
        ] = "BREACH_ACTIVE"
        failed_score = score_blinded_review(self.review, self.answer, failed)
        self.assertEqual(
            failed_score["bounded_result"],
            "DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW",
        )
        self.assertEqual(failed_score["metrics"]["control_false_positive_count"], 1)

    def test_kappa_helper(self) -> None:
        self.assertEqual(cohen_kappa(["A", "B"], ["A", "B"]), 1.0)
        self.assertIsNone(cohen_kappa([], []))

    def test_qa_state_and_authority_stop_at_operator_review(self) -> None:
        self.assertEqual(self.qa["status"], "GATE_READY_OPERATOR_REVIEW_INPUT_REQUIRED")
        self.assertEqual(
            self.qa["recommendation"],
            "COMPLETE_BLINDED_OPERATOR_REVIEW_THEN_SCORE_AND_RETURN_TO_PD-JUNE-MDR-G1",
        )
        self.assertEqual(
            self.state["packet_id"],
            "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE",
        )
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["review_status"], "OPERATOR_INPUT_REQUIRED")
        self.assertEqual(self.state["next_gate"], "PD-JUNE-MDR-G1")
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")
        self.assertIn("MACHINE_REPLAY", self.state["retained_prohibitions"])
        self.assertIn("R2_PUBLICATION", self.state["retained_prohibitions"])


if __name__ == "__main__":
    unittest.main()
