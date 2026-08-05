from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r3"
R2_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R2_ACKNOWLEDGEMENT_RECEIPT.json"
)
R3_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json"
)
BUNDLE = BASE / "PGN_G3_R3_CANDIDATE_REVIEW_BUNDLE.json"
QA = BASE / "PGN_G3_R3_QA_PACKET.json"
GATE = BASE / "PGN_G3_R3_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G3_R3_PROGRAMME_STATE_UPDATE.json"
DECISION = BASE / "PGN_G3_R3_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R3_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
CROSSWALK = BASE / "PGN_G3_R3_ARTIFACT_GOVERNANCE_CROSSWALK.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R3_IDS = [
    "OVC-DEV-ACCEL-v0.1",
    "OVC-DEV-ACCEL-v0.2",
    "OVC-DISCOVERY-OPERATING-HUB.v0.1",
]
R4_IDS = [
    "OVC-RESEARCH-CONSOLE.v0.2",
    "OVC-RESEARCH-CONSOLE.v0.3",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1",
]
R3_SHA = "95c6d187900a4c0ad94fff94cfeb63791f8cf7b6c537379df7a666143a02f296"
DECISION_ID = "PGN-G3-R3.OPERATOR.ACKNOWLEDGE_CONTINUE.20260805T154400+0100"


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


class NativeGenesisPortfolioG3R3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.r2_receipt = load(R2_RECEIPT)
        cls.r3_receipt = load(R3_RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
        cls.crosswalk = load(CROSSWALK)
        cls.builder = load_builder()

    def test_r2_receipt_is_exact_prerequisite(self) -> None:
        self.assertEqual(289, self.r2_receipt["pull_request"])
        self.assertEqual("68420178ea9518a335d08e0672f83390970c5c56", self.r2_receipt["final_head"])
        self.assertEqual("4d3ce5ecaf92897d69b1c7bf4945ca4f6935e606", self.r2_receipt["merge_commit"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY", self.r2_receipt["authority_effect"])
        self.assertEqual("NONE", self.r2_receipt["native_adoption"])

    def test_r3_bundle_matches_deterministic_builder(self) -> None:
        generated = self.builder.build_group("PGN-G3-R3", ROOT)
        self.assertEqual(self.bundle, generated)
        self.assertEqual(R3_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R3_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(3, self.bundle["candidate_count"])

    def test_all_r3_candidates_are_unapproved_and_source_preserving(self) -> None:
        classes = {
            "OVC-DEV-ACCEL-v0.1": "DEVELOPMENT_INFRASTRUCTURE",
            "OVC-DEV-ACCEL-v0.2": "DEVELOPMENT_INFRASTRUCTURE",
            "OVC-DISCOVERY-OPERATING-HUB.v0.1": "RESEARCH_INFRASTRUCTURE",
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
            self.assertEqual("DENIED_PENDING_PGN_G3", candidate["authority_envelope"]["native_adoption"])
            self.assertFalse(candidate["migration_crosswalk"]["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_crosswalk_is_materialised_and_authority_neutral(self) -> None:
        self.assertEqual("PGN-G3-R3", self.crosswalk["review_group_id"])
        self.assertEqual(3, self.crosswalk["candidate_count"])
        self.assertEqual("NONE", self.crosswalk["authority_effect"])
        candidate_relations = 0
        for candidate in self.crosswalk["candidates"]:
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["candidate_status"])
            for relation in candidate["relationships"]:
                self.assertEqual("NONE", relation["authority_effect"])
                if relation["evidence_status"] == "CANDIDATE_RELATION":
                    candidate_relations += 1
        self.assertEqual(2, candidate_relations)

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3-R3 ACKNOWLEDGE_CONTINUE",
            self.decision["exact_operator_command"],
        )
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.decision["authority_granted"]["native_genesis_adoption"])
        self.assertEqual("NONE", self.decision["authority_granted"]["cross_programme_edge_acceptance"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])
        self.assertEqual("DENIED", self.ack_record["r4_materialisation_before_merge"])

    def test_gate_qa_and_state_are_approved_pending_merge(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual("APPROVED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.gate["status"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status_after_decision"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual("PASS_OPERATOR_ACKNOWLEDGED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.qa["status"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED_SATISFIED", self.state["authority_required"])
        self.assertEqual("PGN-G3-R4", self.state["next_packet"])
        self.assertEqual("PGN-G3-R4", self.state["next_gate"])
        self.assertEqual([], self.state["blockers"])

    def test_post_merge_receipt_is_exact_and_unlocks_only_r4(self) -> None:
        self.assertEqual(326, self.r3_receipt["pull_request"])
        self.assertEqual("fca07b4943790fe405e30ccc6aea7785155d7d81", self.r3_receipt["final_head"])
        self.assertEqual("129e1437e48d26d6ef2c8d2013a95a2b35e0e43f", self.r3_receipt["merge_commit"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", self.r3_receipt["exact_head_assurance"][key]["conclusion"])
        self.assertEqual(0, self.r3_receipt["exact_head_assurance"]["unresolved_review_threads"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY", self.r3_receipt["authority_effect"])
        self.assertEqual("NONE", self.r3_receipt["native_adoption"])
        r4 = self.builder.build_group("PGN-G3-R4", ROOT)
        self.assertEqual(R4_IDS, r4["candidate_ids"])
        self.assertEqual("NONE", r4["authority_effect"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R5", ROOT)
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
