from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r3"
R3_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json"
R4_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R4_ACKNOWLEDGEMENT_RECEIPT.json"
BUNDLE = BASE / "PGN_G3_R3_CANDIDATE_REVIEW_BUNDLE.json"
CROSSWALK = BASE / "PGN_G3_R3_ARTIFACT_GOVERNANCE_CROSSWALK.json"
QA = BASE / "PGN_G3_R3_QA_PACKET.json"
GATE = BASE / "PGN_G3_R3_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R3_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R3_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R3_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R3_IDS = ["OVC-DEV-ACCEL-v0.1", "OVC-DEV-ACCEL-v0.2", "OVC-DISCOVERY-OPERATING-HUB.v0.1"]
R3_SHA = "95c6d187900a4c0ad94fff94cfeb63791f8cf7b6c537379df7a666143a02f296"
DECISION_ID = "PGN-G3-R3.OPERATOR.ACKNOWLEDGE_CONTINUE.20260805T154400+0100"


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


class NativeGenesisPortfolioG3R3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load(BUNDLE)
        cls.crosswalk = load(CROSSWALK)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack = load(ACK_RECORD)
        cls.r3_receipt = load(R3_RECEIPT)
        cls.r4_receipt = load(R4_RECEIPT)
        cls.builder = load_builder()

    def test_r3_bundle_crosswalk_and_decision_remain_exact(self) -> None:
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R3", ROOT))
        self.assertEqual(R3_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R3_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        self.assertEqual(2, sum(
            relation["evidence_status"] == "CANDIDATE_RELATION"
            for candidate in self.crosswalk["candidates"]
            for relation in candidate["relationships"]
        ))
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.ack["native_adoption"])
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])

    def test_r3_and_r4_receipts_advance_without_adoption(self) -> None:
        self.assertEqual(326, self.r3_receipt["pull_request"])
        self.assertEqual("129e1437e48d26d6ef2c8d2013a95a2b35e0e43f", self.r3_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY", self.r3_receipt["authority_effect"])
        self.assertEqual(330, self.r4_receipt["pull_request"])
        self.assertEqual("9b76695b434383a2de7ea654c3a2af52756702ad", self.r4_receipt["final_head"])
        self.assertEqual("19b00bb8f489bc07bf84db87eff41ba5dd21b308", self.r4_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY", self.r4_receipt["authority_effect"])
        self.assertEqual("NONE", self.r4_receipt["native_adoption"])
        r5 = self.builder.build_group("PGN-G3-R5", ROOT)
        self.assertEqual("PGN-G3-R5", r5["review_group_id"])
        self.assertEqual("NONE", r5["authority_effect"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
