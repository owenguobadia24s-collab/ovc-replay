from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r5"
R4_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R4_ACKNOWLEDGEMENT_RECEIPT.json"
R5_RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/PGN_G3_R5_ACKNOWLEDGEMENT_RECEIPT.json"
BUNDLE = BASE / "PGN_G3_R5_CANDIDATE_REVIEW_BUNDLE.json"
CROSSWALK = BASE / "PGN_G3_R5_ARTIFACT_GOVERNANCE_CROSSWALK.json"
QA = BASE / "PGN_G3_R5_QA_PACKET.json"
GATE = BASE / "PGN_G3_R5_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R5_PROGRAMME_STATE_UPDATE.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R5_IDS = ["OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2", "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4", "PD-JUNE-FULL-MONTH-MDR"]
R5_SHA = "36945653326c1bf23c7da0b00516351a2cb31e14f047f3d6b0fb395a6b12b6e1"


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


class NativeGenesisPortfolioG3R5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.r4_receipt = load(R4_RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.crosswalk = load(CROSSWALK)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.builder = load_builder()

    def test_r4_receipt_is_exact_prerequisite(self) -> None:
        self.assertEqual(330, self.r4_receipt["pull_request"])
        self.assertEqual("9b76695b434383a2de7ea654c3a2af52756702ad", self.r4_receipt["final_head"])
        self.assertEqual("19b00bb8f489bc07bf84db87eff41ba5dd21b308", self.r4_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY", self.r4_receipt["authority_effect"])
        self.assertEqual("NONE", self.r4_receipt["native_adoption"])
        self.assertEqual("NONE", self.r4_receipt["cross_programme_edge_acceptance"])

    def test_r5_bundle_matches_deterministic_builder(self) -> None:
        generated = self.builder.build_group("PGN-G3-R5", ROOT)
        self.assertEqual(self.bundle, generated)
        self.assertEqual(R5_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R5_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(3, self.bundle["candidate_count"])

    def test_all_candidates_remain_unapproved_and_source_preserving(self) -> None:
        classes = {
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2": "RESEARCH_INFRASTRUCTURE",
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4": "RESEARCH_EVIDENCE",
            "PD-JUNE-FULL-MONTH-MDR": "RESEARCH_EVIDENCE",
        }
        for item in self.bundle["candidates"]:
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual(classes[candidate["programme_id"]], candidate["candidate_class"])
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
            self.assertEqual("NONE", candidate["authority_envelope"]["authority_delta"])
            self.assertEqual("DENIED_PENDING_PGN_G3", candidate["authority_envelope"]["native_adoption"])
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertFalse(candidate["migration_crosswalk"]["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_crosswalk_preserves_lifecycle_and_incident_truth(self) -> None:
        self.assertEqual("PGN-G3-R5", self.crosswalk["review_group_id"])
        self.assertEqual("MATERIALISED_UNAPPROVED", self.crosswalk["status"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        self.assertEqual(3, self.crosswalk["candidate_count"])
        relations = [relation for candidate in self.crosswalk["candidates"] for relation in candidate["relationships"]]
        self.assertEqual(0, sum(item["evidence_status"] in {"CANDIDATE_RELATION", "UNRESOLVED"} for item in relations))
        self.assertTrue(all(item["authority_effect"] == "NONE" for item in relations))
        ro4 = next(candidate for candidate in self.crosswalk["candidates"] if candidate["programme_id"] == "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4")
        self.assertIn("BLOCKED_AT_RO4_G6", ro4["coverage"]["lineage_records"])
        pd = next(candidate for candidate in self.crosswalk["candidates"] if candidate["programme_id"] == "PD-JUNE-FULL-MONTH-MDR")
        self.assertEqual("NONE_INCIDENT_EXPLICITLY_NOT_A_RELEASE", pd["coverage"]["immutable_release_identities"])
        self.assertTrue(any("NOT_A_RELEASE" in (relation["ambiguity_or_competing_owner"] or "") for relation in pd["relationships"]))

    def test_gate_qa_and_state_are_operator_ready_without_adoption(self) -> None:
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE PGN-G3-R5 ACKNOWLEDGE_CONTINUE", self.gate["exact_operator_command"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.qa["qa_recommendation"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED", self.state["authority_required"])
        self.assertIsNone(self.state["decision_record"])
        self.assertEqual([], self.state["blockers"])

    def test_r6_remains_locked_and_no_adoption_decision_exists(self) -> None:
        self.assertFalse(R5_RECEIPT.exists())
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
