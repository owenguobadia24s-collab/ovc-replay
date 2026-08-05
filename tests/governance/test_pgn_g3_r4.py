from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r4"
R3_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json"
BUNDLE = BASE / "PGN_G3_R4_CANDIDATE_REVIEW_BUNDLE.json"
CROSSWALK = BASE / "PGN_G3_R4_ARTIFACT_GOVERNANCE_CROSSWALK.json"
QA = BASE / "PGN_G3_R4_QA_PACKET.json"
GATE = BASE / "PGN_G3_R4_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R4_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R4_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R4_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R4_IDS = ["OVC-RESEARCH-CONSOLE.v0.2", "OVC-RESEARCH-CONSOLE.v0.3", "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1"]
R4_SHA = "70526ebfa5fe9ffd484720c43d892546efb88d5f69bb6eca16890819dae9ffc9"
DECISION_ID = "PGN-G3-R4.OPERATOR.ACKNOWLEDGE_CONTINUE.20260805T175400+0100"


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


class NativeGenesisPortfolioG3R4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.r3_receipt = load(R3_RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.crosswalk = load(CROSSWALK)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
        cls.builder = load_builder()

    def test_r3_receipt_is_exact_prerequisite(self) -> None:
        self.assertEqual(326, self.r3_receipt["pull_request"])
        self.assertEqual("129e1437e48d26d6ef2c8d2013a95a2b35e0e43f", self.r3_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY", self.r3_receipt["authority_effect"])

    def test_r4_bundle_matches_deterministic_builder(self) -> None:
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R4", ROOT))
        self.assertEqual(R4_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R4_SHA, self.bundle["candidate_group_sha256"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R5", ROOT)

    def test_candidates_and_crosswalk_remain_authority_neutral(self) -> None:
        for item in self.bundle["candidates"]:
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        self.assertEqual(3, self.crosswalk["candidate_count"])
        relations = [r for c in self.crosswalk["candidates"] for r in c["relationships"]]
        self.assertEqual(1, len([r for r in relations if r["evidence_status"] == "CANDIDATE_RELATION"]))
        self.assertTrue(all(r["authority_effect"] == "NONE" for r in relations))

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual("OVC APPROVE PGN-G3-R4 ACKNOWLEDGE_CONTINUE", self.decision["exact_operator_command"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.decision["authority_granted"]["native_genesis_adoption"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])

    def test_gate_qa_and_state_are_approved_pending_merge(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual("APPROVED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.gate["status"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status_after_decision"])
        self.assertEqual("PASS_OPERATOR_ACKNOWLEDGED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.qa["status"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED_SATISFIED", self.state["authority_required"])
        self.assertEqual("PGN-G3-R5", self.state["next_packet"])
        self.assertIsNone(self.state["merge_commit"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
