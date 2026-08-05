from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r1"
REVIEW_RECEIPT_DIR = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews"
BUNDLE = BASE / "PGN_G3_R1_CANDIDATE_REVIEW_BUNDLE.json"
QA = BASE / "PGN_G3_R1_QA_PACKET.json"
GATE = BASE / "PGN_G3_R1_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R1_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R1_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R1_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
WP3_RECEIPT = BASE / "PGN_WP3_MERGE_RECEIPT.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R1_IDS = [
    "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1",
    "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1",
    "OVC-C2E-NEUTRAL-EPISODE-v0.1",
]
DECISION_ID = "PGN-G3-R1.OPERATOR.ACKNOWLEDGE_CONTINUE.20260804T142700+0100"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


def load_builder():
    spec = importlib.util.spec_from_file_location("pgn_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeGenesisPortfolioG3R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load(BUNDLE)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack = load(ACK_RECORD)
        cls.wp3_receipt = load(WP3_RECEIPT)
        cls.receipts = {
            index: load(REVIEW_RECEIPT_DIR / f"PGN_G3_R{index}_ACKNOWLEDGEMENT_RECEIPT.json")
            for index in range(1, 5)
        }
        cls.builder = load_builder()

    def test_wp3_and_r1_records_remain_exact(self) -> None:
        self.assertEqual(287, self.wp3_receipt["pull_request"])
        self.assertEqual("48f30a628e977f34ef068c7e7d67fba95654b5a9", self.wp3_receipt["merge_commit"])
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R1", ROOT))
        self.assertEqual(R1_IDS, self.bundle["candidate_ids"])
        for item in self.bundle["candidates"]:
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])

    def test_operator_acknowledgement_is_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual(DECISION_ID, self.ack["decision_id"])
        self.assertEqual("NONE", self.ack["native_adoption"])
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])

    def test_receipts_advance_progressively_through_r4_only(self) -> None:
        expected_effects = {
            1: "DISCLOSE_AND_MATERIALISE_PGN_G3_R2_ONLY",
            2: "DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY",
            3: "DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY",
            4: "DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY",
        }
        for index, effect in expected_effects.items():
            self.assertEqual("NONE", self.receipts[index]["native_adoption"])
            self.assertEqual(effect, self.receipts[index]["authority_effect"])
        for index in range(1, 6):
            group = self.builder.build_group(f"PGN-G3-R{index}", ROOT)
            self.assertEqual(f"PGN-G3-R{index}", group["review_group_id"])
            self.assertEqual("NONE", group["authority_effect"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
