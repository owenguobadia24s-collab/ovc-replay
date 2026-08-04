from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-r2"
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
        cls.bundle = load(BUNDLE)
        cls.qa = load(QA)
        cls.gate = load(GATE)
        cls.state = load(STATE)
        cls.decision = load(DECISION)
        cls.ack_record = load(ACK_RECORD)
        cls.receipt = load(R2_RECEIPT)
        cls.builder = load_builder()

    def test_r2_bundle_remains_exact_and_unapproved(self) -> None:
        self.assertEqual(self.bundle, self.builder.build_group("PGN-G3-R2", ROOT))
        self.assertEqual(R2_IDS, self.bundle["candidate_ids"])
        self.assertEqual(R2_SHA, self.bundle["candidate_group_sha256"])
        self.assertEqual(3, self.bundle["candidate_count"])
        for item in self.bundle["candidates"]:
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertEqual(8, len(candidate["unresolved_fields"]))
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])

    def test_operator_acknowledgement_is_exact_and_not_adoption(self) -> None:
        self.assertEqual(DECISION_ID, self.decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.decision["decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3-R2 ACKNOWLEDGE_CONTINUE",
            self.decision["exact_operator_command"],
        )
        self.assertEqual(0, self.decision["acknowledged_review_group"]["native_adoption_count"])
        self.assertEqual("NONE", self.decision["authority_granted"]["native_genesis_adoption"])
        self.assertEqual(DECISION_ID, self.ack_record["decision_id"])
        self.assertEqual("NONE", self.ack_record["native_adoption"])

    def test_r2_unlock_receipt_binds_exact_merge_and_unlocks_only_r3(self) -> None:
        self.assertEqual(289, self.receipt["pull_request"])
        self.assertEqual("68420178ea9518a335d08e0672f83390970c5c56", self.receipt["final_head"])
        self.assertEqual("4d3ce5ecaf92897d69b1c7bf4945ca4f6935e606", self.receipt["merge_commit"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", self.receipt["exact_head_assurance"][key]["conclusion"])
        self.assertEqual(0, self.receipt["exact_head_assurance"]["unresolved_review_threads"])
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY", self.receipt["authority_effect"])
        self.assertEqual("NONE", self.receipt["native_adoption"])
        self.assertEqual("PGN-G3-R3", self.builder.build_group("PGN-G3-R3", ROOT)["review_group_id"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R4", ROOT)

    def test_gate_qa_and_state_preserve_no_adoption(self) -> None:
        self.assertFalse(self.gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", self.gate["decision"])
        self.assertEqual("CANDIDATE_UNAPPROVED", self.gate["review_group"]["candidate_status_after_decision"])
        self.assertEqual(0, self.gate["review_group"]["native_adoption_count"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual(0, self.qa["assessment"]["native_adoption_count"])
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("NONE", self.state["authority"]["reserved_authority"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))


if __name__ == "__main__":
    unittest.main()
