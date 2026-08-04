import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"
RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2_MERGE_RECEIPT.json"
QA = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_QA_PACKET.json"
GATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_OPERATOR_GATE_PACKET.json"
STATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_PROGRAMME_STATE_UPDATE.json"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class NativeGenesisPortfolioG2ATests(unittest.TestCase):
    def test_g2_merge_receipt_binds_exact_census_and_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(283, receipt["pull_request"])
        self.assertEqual("35d5cdd92c5860ceef40120392d17b9a362de35b", receipt["final_head"])
        self.assertEqual("3eb774894676ad620fe1aa826a8e48445f75ec4d", receipt["merge_commit"])
        self.assertEqual("7f26a513c7696bf065f4b30b5337d44677adc1f2fb48e7864593f6f708f704ad", receipt["census"]["builder_sha256"])
        self.assertEqual(7, receipt["census"]["legacy_target_count"])
        self.assertFalse(receipt["census"]["candidate_construction"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", receipt["exact_head_assurance"][key]["conclusion"])

    def test_gate_presents_exact_population_and_progressive_groups(self) -> None:
        census = load(CENSUS)
        gate = load(GATE)
        target_ids = {item["programme_id"] for item in gate["census"]["targets"]}
        self.assertEqual(7, gate["census"]["legacy_adoption_target_count"])
        self.assertEqual({item["programme_id"] for item in census["adoption_targets"]}, target_ids)
        sizes = [item["candidate_count"] for item in gate["census"]["review_groups"]]
        self.assertEqual([3, 3, 1], sizes)
        self.assertTrue(all(size <= 3 for size in sizes))
        self.assertEqual(0, gate["census"]["candidates_constructed"])
        self.assertEqual(0, gate["census"]["blocking_conflicts"])

    def test_exclusions_and_surprises_are_explicit(self) -> None:
        gate = load(GATE)
        exclusions = {item["programme_id"]: item["reason"] for item in gate["census"]["exclusions"]}
        self.assertEqual("ALREADY_NATIVE", exclusions["OVC-PG-v0.2"])
        self.assertEqual("CURRENT_GOVERNANCE_PROGRAMME_NOT_A_LEGACY_TARGET", exclusions["OVC-PG-NATIVE-PORTFOLIO-v0.2"])
        self.assertEqual("PCCR-G0-PREPARATION", gate["census"]["non_admitted"][0]["object_id"])
        self.assertIn("PCCR_PREPARATION_EXISTS_BUT_IS_NOT_ADMITTED", gate["census"]["surprises"])

    def test_operator_decision_options_and_recommendation_are_bounded(self) -> None:
        gate = load(GATE)
        self.assertEqual(
            ["ACKNOWLEDGE_CONTINUE", "ADJUST_SCOPE", "DEFER", "BLOCK", "QUARANTINE"],
            gate["allowed_decisions"],
        )
        self.assertEqual("ACKNOWLEDGE_CONTINUE", gate["recommended_decision"])
        self.assertEqual("OVC APPROVE PGN-G2A ACKNOWLEDGE_CONTINUE", gate["exact_operator_command"])
        self.assertIn("PGN_G3_REMAINS_REQUIRED_FOR_EVERY_NATIVE_ADOPTION", gate["acceptance_conditions"])

    def test_state_stops_before_candidate_construction(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertEqual("PGN-G2A", state["gate_id"])
        self.assertEqual(0, state["census"]["candidates_constructed"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", state["authority"]["candidate_construction"])
        self.assertEqual("DENIED_PENDING_PGN_G3", state["authority"]["native_genesis_adoption"])
        self.assertEqual("AWAIT_OPERATOR_PGN_G2A_ACKNOWLEDGE_CONTINUE_OR_ADJUST_SCOPE", state["next_action"])
        self.assertEqual([], state["blockers"])

    def test_qa_has_no_blocker_and_preserves_warnings(self) -> None:
        qa = load(QA)
        self.assertEqual("ACKNOWLEDGE_CONTINUE", qa["qa_recommendation"])
        self.assertEqual([], qa["blockers"])
        self.assertGreaterEqual(len(qa["warnings"]), 4)
        self.assertEqual("NONE_UNTIL_OPERATOR_PGN_G2A_DECISION", qa["authority_delta"])


if __name__ == "__main__":
    unittest.main()
