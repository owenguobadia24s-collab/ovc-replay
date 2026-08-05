from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r4"
R4_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R4_ACKNOWLEDGEMENT_RECEIPT.json"
BUNDLE = BASE / "PGN_G3_R4_CANDIDATE_REVIEW_BUNDLE.json"
CROSSWALK = BASE / "PGN_G3_R4_ARTIFACT_GOVERNANCE_CROSSWALK.json"
QA = BASE / "PGN_G3_R4_QA_PACKET.json"
GATE = BASE / "PGN_G3_R4_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R4_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R4_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R4_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R4_IDS = [
    "OVC-RESEARCH-CONSOLE.v0.2",
    "OVC-RESEARCH-CONSOLE.v0.3",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1",
]
R5_IDS = [
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
    "PD-JUNE-FULL-MONTH-MDR",
]
R4_SHA = "70526ebfa5fe9ffd484720c43d892546efb88d5f69bb6eca16890819dae9ffc9"
DECISION_ID = "PGN-G3-R4.OPERATOR.ACKNOWLEDGE_CONTINUE.20260805T163200+0100"


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


class NativeGenesisPortfolioG3R4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load(BUNDLE)
        cls.crosswalk = load(CROSSWALK)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack = load(ACK_RECORD)
        cls.receipt = load(R4_RECEIPT)
        cls.builder = load_builder()

    def test_r4_bundle_crosswalk_and_decision_are_exact(self) -> None:
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R4", ROOT))
        self.assertEqual(R4_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R4_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        candidate_relations = [
            relation
            for candidate in self.crosswalk["candidates"]
            for relation in candidate["relationships"]
            if relation["evidence_status"] == "CANDIDATE_RELATION"
        ]
        lineage_relations = [
            relation
            for candidate in self.crosswalk["candidates"]
            for relation in candidate["relationships"]
            if relation["evidence_status"] == "LINEAGE_EXPLICIT"
        ]
        self.assertEqual(1, len(candidate_relations))
        self.assertEqual(2, len(lineage_relations))
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.ack["native_adoption"])
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])

    def test_receipt_binds_exact_head_checks_merge_and_unlocks_only_r5(self) -> None:
        self.assertEqual(330, self.receipt["pull_request"])
        self.assertEqual(328, self.receipt["superseded_pull_request"])
        self.assertEqual("9b76695b434383a2de7ea654c3a2af52756702ad", self.receipt["final_head"])
        self.assertEqual("19b00bb8f489bc07bf84db87eff41ba5dd21b308", self.receipt["merge_commit"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", self.receipt["exact_head_assurance"][key]["conclusion"])
        self.assertEqual(0, self.receipt["exact_head_assurance"]["unresolved_review_threads"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY", self.receipt["authority_effect"])
        self.assertEqual("NONE", self.receipt["native_adoption"])
        self.assertEqual("NONE", self.receipt["cross_programme_edge_acceptance"])
        r5 = self.builder.build_group("PGN-G3-R5", ROOT)
        self.assertEqual(R5_IDS, r5["candidate_ids"])
        self.assertEqual("NONE", r5["authority_effect"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
