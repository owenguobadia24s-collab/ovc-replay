from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r2"
R1_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R1_ACKNOWLEDGEMENT_RECEIPT.json"
)
R2_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R2_ACKNOWLEDGEMENT_RECEIPT.json"
)
BUNDLE = BASE / "PGN_G3_R2_CANDIDATE_REVIEW_BUNDLE.json"
QA = BASE / "PGN_G3_R2_QA_PACKET.json"
GATE = BASE / "PGN_G3_R2_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R2_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R2_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R2_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R2_IDS = [
    "OVC-CLOCK-CONTINUITY-REVIEW-v0.1",
    "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2",
    "OVC-MTA-v0.2",
]
R2_SHA = "b3585068a9bc0ce7568b5b9058014677d48afc212c35d3fefc6f599a8a202dff"
DECISION_ID = "PGN-G3-R2.OPERATOR.ACKNOWLEDGE_CONTINUE.20260804T150800+0100"


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


class NativeGenesisPortfolioG3R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.r1_receipt = load(R1_RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
        cls.builder = load_builder()

    def test_r1_receipt_is_exact_prerequisite(self) -> None:
        self.assertEqual(288, self.r1_receipt["pull_request"])
        self.assertEqual(
            "0b6078e47b6f03c7fe122c4f8577dfc3b9893808",
            self.r1_receipt["merge_commit"],
        )
        self.assertEqual(
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R2_ONLY",
            self.r1_receipt["authority_effect"],
        )
        self.assertEqual("NONE", self.r1_receipt["native_adoption"])

    def test_r2_bundle_matches_deterministic_builder(self) -> None:
        generated = self.builder.build_group("PGN-G3-R2", ROOT)
        self.assertEqual(self.bundle, generated)
        self.assertEqual(R2_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R2_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(3, self.bundle["candidate_count"])

    def test_all_r2_candidates_are_unapproved_and_source_preserving(self) -> None:
        classes = {
            "OVC-CLOCK-CONTINUITY-REVIEW-v0.1": "MARKET_CONSTRUCTION",
            "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2": "MARKET_CONSTRUCTION",
            "OVC-MTA-v0.2": "RESEARCH_EVIDENCE",
        }
        for item in self.bundle["candidates"]:
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual(classes[candidate["programme_id"]], candidate["candidate_class"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
            self.assertEqual("NONE", candidate["authority_envelope"]["authority_delta"])
            self.assertEqual(
                "DENIED_PENDING_PGN_G3",
                candidate["authority_envelope"]["native_adoption"],
            )
            self.assertFalse(candidate["migration_crosswalk"]["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3-R2 ACKNOWLEDGE_CONTINUE",
            self.decision["exact_operator_command"],
        )
        self.assertEqual(
            0, self.decision["acknowledged_review_group"]["native_adoption_count"]
        )
        self.assertEqual(
            "NONE", self.decision["authority_granted"]["native_genesis_adoption"]
        )
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])
        self.assertEqual("DENIED", self.ack_record["r3_materialisation_before_merge"])

    def test_gate_qa_and_state_are_approved_pending_merge(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual(
            "APPROVED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE",
            self.gate["status"],
        )
        self.assertEqual(
            "CANDIDATE_UNAPPROVED",
            self.gate["review_group"]["candidate_status_after_decision"],
        )
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual(
            "PASS_OPERATOR_ACKNOWLEDGED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE",
            self.qa["status"],
        )
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("PGN-G3-R3", self.state["next_packet"])
        self.assertEqual("PGN-G3-R3", self.state["next_gate"])
        self.assertEqual([], self.state["blockers"])

    def test_r3_remains_locked_until_post_merge_receipt(self) -> None:
        self.assertFalse(R2_RECEIPT.exists())
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R3", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
