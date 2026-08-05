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
DECISION = BASE / "PGN_G3_R1_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R1_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
REVIEW_RECEIPT_DIR = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews"
)
R1_RECEIPT = REVIEW_RECEIPT_DIR / "PGN_G3_R1_ACKNOWLEDGEMENT_RECEIPT.json"
R2_RECEIPT = REVIEW_RECEIPT_DIR / "PGN_G3_R2_ACKNOWLEDGEMENT_RECEIPT.json"
QUEUE = ROOT / "registries/governance/programme_genesis/pgn_candidates/PGN_WP3_PROGRESSIVE_REVIEW_QUEUE_v0_1.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R1_IDS = [
    "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1",
    "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1",
    "OVC-C2E-NEUTRAL-EPISODE-v0.1",
]
R1_SHA = "6938fbcb52ae6d52d13e56a40cd76d6446f1376e3340309a5dde8d861684bfb1"
DECISION_ID = "PGN-G3-R1.OPERATOR.ACKNOWLEDGE_CONTINUE.20260804T142700+0100"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pgn_wp3_native_candidates", BUILDER)
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
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
        cls.r1_receipt = load(R1_RECEIPT)
        cls.r2_receipt = load(R2_RECEIPT)
        cls.queue = load(QUEUE)
        cls.builder = load_builder()

    def test_wp3_merge_receipt_is_exact(self) -> None:
        self.assertEqual(287, self.receipt["pull_request"])
        self.assertEqual("46e6bbfca831d47fc6d559ff18205ce66ab3e0bb", self.receipt["final_head"])
        self.assertEqual("48f30a628e977f34ef068c7e7d67fba95654b5a9", self.receipt["merge_commit"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", self.receipt["exact_head_assurance"][key]["conclusion"])

    def test_r1_bundle_matches_sealed_commitment(self) -> None:
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R1", ROOT))
        self.assertEqual(R1_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R1_SHA, self.bundle["candidate_group_sha256"])
        for item in self.bundle["candidates"]:
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual("OVC APPROVE PGN-G3-R1 ACKNOWLEDGE_CONTINUE", self.decision["exact_operator_command"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])

    def test_r1_receipt_remains_exact_while_later_receipts_advance_progressively(self) -> None:
        self.assertEqual(288, self.r1_receipt["pull_request"])
        self.assertEqual("af2170d862e1464e1a1b8e8b65b77a07e5cc8101", self.r1_receipt["final_head"])
        self.assertEqual("0b6078e47b6f03c7fe122c4f8577dfc3b9893808", self.r1_receipt["merge_commit"])
        self.assertEqual(DECISION_ID, self.r1_receipt["decision_id"])
        self.assertEqual("NONE", self.r1_receipt["native_adoption"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R2_ONLY", self.r1_receipt["authority_effect"])

        self.assertEqual(289, self.r2_receipt["pull_request"])
        self.assertEqual("NONE", self.r2_receipt["native_adoption"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY", self.r2_receipt["authority_effect"])

        self.assertEqual("PGN-G3-R2", self.builder.build_group("PGN-G3-R2", ROOT)["review_group_id"])
        self.assertEqual("PGN-G3-R3", self.builder.build_group("PGN-G3-R3", ROOT)["review_group_id"])
        self.assertEqual("PGN-G3-R4", self.builder.build_group("PGN-G3-R4", ROOT)["review_group_id"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R5", ROOT)

        for group in self.queue["groups"][1:]:
            self.assertEqual([], group["candidate_ids"])
            self.assertEqual("LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT", group["disclosure_status"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))

    def test_gate_qa_and_state_preserve_no_adoption(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status_after_decision"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("PGN-G3-R2", self.state["next_packet"])


if __name__ == "__main__":
    unittest.main()
