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
UNLOCK_RECEIPT = ROOT / (
    "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews/"
    "PGN_G3_R1_ACKNOWLEDGEMENT_RECEIPT.json"
)
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
        self.assertEqual(3, self.bundle["candidate_count"])
        for item in self.bundle["candidates"]:
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
            self.assertEqual("NONE", candidate["authority_envelope"]["authority_delta"])

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3-R1 ACKNOWLEDGE_CONTINUE",
            self.decision["exact_operator_command"],
        )
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.decision["authority_granted"]["market_model_selector_release_validation_publication_agent_probability_risk_exposure_execution"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])
        self.assertEqual("DENIED", self.ack_record["r2_materialisation_before_merge"])

    def test_gate_qa_and_state_are_approved_pending_merge(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual("APPROVED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.gate["status"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status_after_decision"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual("PASS_OPERATOR_ACKNOWLEDGED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", self.qa["status"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("PGN-G3-R2", self.state["next_packet"])
        self.assertEqual("PGN-G3-R2", self.state["next_gate"])
        self.assertEqual([], self.state["blockers"])

    def test_r2_remains_locked_until_post_merge_unlock_receipt(self) -> None:
        self.assertFalse(UNLOCK_RECEIPT.exists())
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R2", ROOT)
        for group in self.queue["groups"][1:]:
            self.assertEqual([], group["candidate_ids"])
            self.assertEqual("LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT", group["disclosure_status"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
