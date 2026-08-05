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
DECISION = BASE / "PGN_G3_R5_OPERATOR_DECISION.json"
ACK_RECORD = BASE / "PGN_G3_R5_OPERATOR_ACKNOWLEDGEMENT_RECORD.json"
BUILDER = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"

R5_IDS = [
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
    "PD-JUNE-FULL-MONTH-MDR",
]
R6_IDS = ["OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1"]
R5_SHA = "36945653326c1bf23c7da0b00516351a2cb31e14f047f3d6b0fb395a6b12b6e1"
R6_SHA = "bfe34292f0815eeae2ec1da9438ee9d20e4436a9444c1d3627d233b26ea245c5"
DECISION_ID = "PGN-G3-R5.OPERATOR.ACKNOWLEDGE_CONTINUE.20260805T190200+0100"


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
        cls.r5_receipt = load(R5_RECEIPT)
        cls.bundle = load(BUNDLE)
        cls.crosswalk = load(CROSSWALK)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
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

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("OVC APPROVE PGN-G3-R5 ACKNOWLEDGE_CONTINUE", self.decision["exact_operator_command"])
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.decision["authority_granted"]["native_genesis_adoption"])
        self.assertEqual("NONE", self.decision["authority_granted"]["cross_programme_edge_acceptance"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])
        self.assertEqual("DENIED", self.ack_record["r6_materialisation_before_merge"])

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
        self.assertEqual("PGN-G3-R6", self.state["next_packet"])
        self.assertEqual("PGN-G3-R6", self.state["next_gate"])
        self.assertEqual([], self.state["blockers"])

    def test_post_merge_receipt_is_exact_and_unlocks_only_r6(self) -> None:
        self.assertEqual(332, self.r5_receipt["pull_request"])
        self.assertEqual("0c33793a05738018f1560456ab2468babee4407d", self.r5_receipt["final_head"])
        self.assertEqual("04e1c0bfe8b8888f201b217990104be002262fc7", self.r5_receipt["merge_commit"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness", "compatibility"):
            self.assertEqual("SUCCESS", self.r5_receipt["exact_head_assurance"][key]["conclusion"])
        self.assertEqual(0, self.r5_receipt["exact_head_assurance"]["unresolved_review_threads"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R6_ONLY", self.r5_receipt["authority_effect"])
        self.assertEqual("NONE", self.r5_receipt["native_adoption"])
        self.assertEqual("NONE", self.r5_receipt["cross_programme_edge_acceptance"])
        r6 = self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual(R6_IDS, r6["candidate_ids"])
        self.assertEqual(R6_SHA, r6["candidate_group_sha256"])
        self.assertEqual(1, r6["candidate_count"])
        self.assertEqual("NONE", r6["authority_effect"])
        self.assertEqual("DENIED_PENDING_PGN_G3", r6["native_adoption"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
