from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r1"
RECEIPT = BASE / "PGN_WP3_MERGE_RECEIPT.json"
BUNDLE = BASE / "PGN_G3_R1_CANDIDATE_REVIEW_BUNDLE.json"
QA = BASE / "PGN_G3_R1_QA_PACKET.json"
GATE = BASE / "PGN_G3_R1_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R1_PROGRAMME_STATE_UPDATE.json"
QUEUE = ROOT / "registries/governance/programme_genesis/pgn_candidates/PGN_WP3_PROGRESSIVE_REVIEW_QUEUE_v0_1.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R1_IDS = [
    "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1",
    "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1",
    "OVC-C2E-NEUTRAL-EPISODE-v0.1",
]
R1_SHA = "6938fbcb52ae6d52d13e56a40cd76d6446f1376e3340309a5dde8d861684bfb1"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_pgn_wp3_native_candidates", BUILDER
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeGenesisPortfolioG3R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = load(RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.queue = load(QUEUE)
        cls.builder = load_builder()

    def test_wp3_merge_receipt_binds_exact_merge_and_assurance(self) -> None:
        self.assertEqual(287, self.receipt["pull_request"])
        self.assertEqual(
            "46e6bbfca831d47fc6d559ff18205ce66ab3e0bb",
            self.receipt["final_head"],
        )
        self.assertEqual(
            "48f30a628e977f34ef068c7e7d67fba95654b5a9",
            self.receipt["merge_commit"],
        )
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual(
                "SUCCESS", self.receipt["exact_head_assurance"][key]["conclusion"]
            )
        self.assertEqual(0, self.receipt["exact_head_assurance"]["unresolved_review_threads"])

    def test_r1_bundle_matches_deterministic_builder_and_sealed_queue(self) -> None:
        generated = self.builder.build_group("PGN-G3-R1", ROOT)
        self.assertEqual(self.bundle, generated)
        first_group = self.queue["groups"][0]
        self.assertEqual("PGN-G3-R1", first_group["group_id"])
        self.assertEqual(R1_IDS, first_group["candidate_ids"])
        self.assertEqual(R1_SHA, first_group["sealed_candidate_bodies_sha256"])
        self.assertEqual(R1_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(R1_IDS, self.bundle["candidate_ids"])
        self.assertEqual(3, self.bundle["candidate_count"])

    def test_all_r1_candidates_are_unapproved_source_preserving_and_visible(self) -> None:
        for item in self.bundle["candidates"]:
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual("MARKET_TRANSLATION", candidate["candidate_class"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            envelope = candidate["authority_envelope"]
            self.assertTrue(envelope["source_authority_preserved"])
            self.assertEqual("NONE", envelope["authority_delta"])
            self.assertEqual("DENIED_PENDING_PGN_G3", envelope["native_adoption"])
            self.assertEqual("NONE", envelope["reserved_authority"])
            audit = candidate["scope_audit"]
            self.assertFalse(audit["fabricated_historical_intent"])
            self.assertEqual("UNRESOLVED_EXACT_SOURCE_TEXT", audit["purpose"])
            crosswalk = candidate["migration_crosswalk"]
            self.assertTrue(crosswalk["identity_preserved"])
            self.assertFalse(crosswalk["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_r2_and_later_groups_remain_locked_and_undisclosed(self) -> None:
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R2", ROOT)
        for group in self.queue["groups"][1:]:
            self.assertEqual([], group["candidate_ids"])
            self.assertEqual(
                "LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT",
                group["disclosure_status"],
            )
        receipts = list(
            ROOT.glob(
                "docs/releases/programme-genesis-native-portfolio-v0-2/"
                "pgn-g3/reviews/PGN_G3_R*_ACKNOWLEDGEMENT_RECEIPT.json"
            )
        )
        self.assertEqual([], receipts)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))

    def test_gate_acknowledgement_is_not_adoption(self) -> None:
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertEqual("PGN-G3-R1", self.gate["gate_id"])
        self.assertIn("WITHOUT_ADOPTING_ANY_CANDIDATE", self.gate["proposed_delta"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["recommended_decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3-R1 ACKNOWLEDGE_CONTINUE",
            self.gate["exact_operator_command"],
        )
        self.assertEqual(
            ["ACKNOWLEDGE_CONTINUE", "ADJUST_SCOPE", "DEFER", "BLOCK", "QUARANTINE"],
            self.gate["allowed_decisions"],
        )
        self.assertEqual(
            "DENIED_PENDING_COMPLETION_OF_PROGRESSIVE_REVIEW_AND_SEPARATE_PGN_G3_OPERATOR_DECISIONS",
            self.gate["current_authority"]["native_genesis_adoption"],
        )
        self.assertEqual(
            "LOCKED", self.gate["current_authority"]["later_review_groups"]
        )

    def test_qa_recommends_acknowledgement_without_hiding_warnings(self) -> None:
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.qa["qa_recommendation"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual(0, self.qa["assessment"]["native_adoption_count"])
        self.assertEqual(0, self.qa["assessment"]["later_group_ids_disclosed"])
        self.assertEqual(0, self.qa["assessment"]["later_group_bodies_materialized"])
        self.assertGreaterEqual(len(self.qa["warnings"]), 5)

    def test_programme_state_stops_at_operator_gate(self) -> None:
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED", self.state["authority_required"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.state["review"]["candidate_status"])
        self.assertTrue(self.state["review"]["later_groups_locked"])
        self.assertFalse(self.state["review"]["later_group_ids_disclosed"])
        self.assertEqual(
            "DENIED_PENDING_R1_ACKNOWLEDGEMENT_RECEIPT_MERGE",
            self.state["authority"]["next_group_disclosure"],
        )
        self.assertEqual([], self.state["blockers"])


if __name__ == "__main__":
    unittest.main()
