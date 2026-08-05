from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r4"
R3_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json"
)
BUNDLE = BASE / "PGN_G3_R4_CANDIDATE_REVIEW_BUNDLE.json"
CROSSWALK = BASE / "PGN_G3_R4_ARTIFACT_GOVERNANCE_CROSSWALK.json"
QA = BASE / "PGN_G3_R4_QA_PACKET.json"
GATE = BASE / "PGN_G3_R4_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R4_PROGRAMME_STATE_UPDATE.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R4_IDS = [
    "OVC-RESEARCH-CONSOLE.v0.2",
    "OVC-RESEARCH-CONSOLE.v0.3",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1",
]
R4_SHA = "70526ebfa5fe9ffd484720c43d892546efb88d5f69bb6eca16890819dae9ffc9"


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
        cls.builder = load_builder()

    def test_r3_receipt_is_exact_prerequisite(self) -> None:
        self.assertEqual(326, self.r3_receipt["pull_request"])
        self.assertEqual("fca07b4943790fe405e30ccc6aea7785155d7d81", self.r3_receipt["final_head"])
        self.assertEqual("129e1437e48d26d6ef2c8d2013a95a2b35e0e43f", self.r3_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY", self.r3_receipt["authority_effect"])
        self.assertEqual("NONE", self.r3_receipt["native_adoption"])

    def test_r4_bundle_matches_deterministic_builder(self) -> None:
        generated = self.builder.build_group("PGN-G3-R4", ROOT)
        self.assertEqual(self.bundle, generated)
        self.assertEqual(R4_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R4_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(3, self.bundle["candidate_count"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R5", ROOT)

    def test_all_candidates_remain_unapproved_and_source_preserving(self) -> None:
        for item in self.bundle["candidates"]:
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual("RESEARCH_INFRASTRUCTURE", candidate["candidate_class"])
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
            self.assertEqual("NONE", candidate["authority_envelope"]["authority_delta"])
            self.assertEqual("DENIED_PENDING_PGN_G3", candidate["authority_envelope"]["native_adoption"])
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertFalse(candidate["migration_crosswalk"]["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_crosswalk_preserves_missing_plan_and_supersession_boundaries(self) -> None:
        self.assertEqual("PGN-G3-R4", self.crosswalk["review_group_id"])
        self.assertEqual("MATERIALISED_UNAPPROVED", self.crosswalk["status"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        self.assertEqual(3, self.crosswalk["candidate_count"])
        relations = [
            relation
            for candidate in self.crosswalk["candidates"]
            for relation in candidate["relationships"]
        ]
        candidate_relations = [item for item in relations if item["evidence_status"] == "CANDIDATE_RELATION"]
        lineage_relations = [item for item in relations if item["evidence_status"] == "LINEAGE_EXPLICIT"]
        self.assertEqual(1, len(candidate_relations))
        self.assertEqual("OVC-RESEARCH-CONSOLE-V0.2-IMPLEMENTATION-PLAN-0.1", candidate_relations[0]["artifact_id"])
        self.assertEqual(2, len(lineage_relations))
        self.assertTrue(all(item["authority_effect"] == "NONE" for item in relations))
        self.assertTrue(all(candidate["candidate_status"] == "CANDIDATE_UNAPPROVED" for candidate in self.crosswalk["candidates"]))

    def test_gate_and_state_are_ready_without_authority_change(self) -> None:
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE PGN-G3-R4 ACKNOWLEDGE_CONTINUE", self.gate["exact_operator_command"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual("PASS_GATE_READY_OPERATOR_ACKNOWLEDGEMENT_REQUIRED", self.qa["status"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED", self.state["authority_required"])
        self.assertEqual("NONE", self.state["authority"]["reserved_authority"])
        self.assertIsNone(self.state["decision_record"])
        self.assertIsNone(self.state["merge_commit"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
