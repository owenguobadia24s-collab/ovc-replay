import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"
RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2_MERGE_RECEIPT.json"
QA = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_QA_PACKET.json"
GATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_OPERATOR_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_OPERATOR_DECISION.json"
STATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2a/PGN_G2A_PROGRAMME_STATE_UPDATE.json"


EXPECTED_CLASSIFICATIONS = [
    "NATIVE_PROGRAMME",
    "LEGACY_PROGRAMME_REQUIRING_CONVERSION",
    "SUPERSEDED_PROGRAMME",
    "ABSORBED_INTO_SUCCESSOR",
    "BOUNDED_PACKET_NOT_A_PROGRAMME",
    "PROPOSAL_NOT_ADMITTED",
    "UNRESOLVED",
]


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class NativeGenesisPortfolioG2ATests(unittest.TestCase):
    def test_g2_merge_receipt_binds_exact_partial_census_and_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(283, receipt["pull_request"])
        self.assertEqual("35d5cdd92c5860ceef40120392d17b9a362de35b", receipt["final_head"])
        self.assertEqual("3eb774894676ad620fe1aa826a8e48445f75ec4d", receipt["merge_commit"])
        self.assertEqual("7f26a513c7696bf065f4b30b5337d44677adc1f2fb48e7864593f6f708f704ad", receipt["census"]["builder_sha256"])
        self.assertEqual(7, receipt["census"]["legacy_target_count"])
        self.assertFalse(receipt["census"]["candidate_construction"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", receipt["exact_head_assurance"][key]["conclusion"])

    def test_operator_adjust_scope_decision_is_exact_and_immutable(self) -> None:
        decision = load(DECISION)
        self.assertEqual("PGN-G2A.OPERATOR.ADJUST_SCOPE.20260804T113500+0100", decision["decision_id"])
        self.assertEqual("ADJUST_SCOPE", decision["decision"])
        self.assertEqual("PGN-WP2E", decision["scope_delta"]["new_packet_id"])
        self.assertEqual(EXPECTED_CLASSIFICATIONS, decision["scope_delta"]["required_classifications"])
        self.assertEqual("DENIED_PENDING_EXPANDED_CENSUS_ACKNOWLEDGEMENT", decision["authority_after_decision"]["candidate_construction"])
        self.assertEqual("PGN-G2B", decision["mandatory_stop"]["gate_id"])
        self.assertEqual("DO_NOT_BEGIN_PGN_WP3_CANDIDATE_CONSTRUCTION", decision["mandatory_stop"]["prohibition"])

    def test_gate_completes_adjust_scope_without_candidate_authority(self) -> None:
        gate = load(GATE)
        self.assertEqual("COMPLETED_ADJUST_SCOPE", gate["status"])
        self.assertFalse(gate["operator_decision_required"])
        self.assertEqual("ADJUST_SCOPE", gate["decision"])
        self.assertEqual("PGN-WP2E", gate["approved_scope_adjustment"]["packet_id"])
        self.assertEqual(EXPECTED_CLASSIFICATIONS, gate["approved_scope_adjustment"]["classification_enum"])
        self.assertEqual("VALID_PARTIAL_CENSUS_NOT_SUFFICIENT_FOR_PGN_WP3", gate["prior_census_disposition"]["status"])
        self.assertEqual(0, gate["prior_census_disposition"]["candidates_constructed"])
        self.assertEqual("DENIED_PENDING_PGN_G2B", gate["authority_after_decision"]["candidate_construction"])
        self.assertEqual("PGN-G2B", gate["next_gate"])

    def test_state_routes_to_expanded_census_and_blocks_wp3(self) -> None:
        state = load(STATE)
        self.assertEqual("COMPLETED", state["status"])
        self.assertEqual("ADJUST_SCOPE", state["decision"])
        self.assertEqual("PGN-WP2E", state["next_packet"])
        self.assertEqual(EXPECTED_CLASSIFICATIONS, state["expanded_census"]["required_classifications"])
        self.assertEqual("PGN-G2B", state["expanded_census"]["acknowledgement_gate"])
        self.assertEqual("DENIED_PENDING_PGN_G2B", state["authority"]["candidate_construction"])
        self.assertNotEqual("PGN-WP3", state["next_packet"])
        self.assertEqual([], state["blockers"])

    def test_qa_recommends_adjusted_scope_and_preserves_uncertainty(self) -> None:
        qa = load(QA)
        self.assertEqual("PASS_ADJUST_SCOPE", qa["status"])
        self.assertEqual("PASS_ADJUST_SCOPE_AND_PROCEED_TO_PGN_WP2E", qa["qa_recommendation"])
        self.assertFalse(qa["assessment"]["repository_history_complete"])
        self.assertFalse(qa["assessment"]["candidate_construction_authorised"])
        self.assertEqual("PGN-G2B", qa["assessment"]["expanded_acknowledgement_gate"])
        self.assertEqual("PASS_RUN_30901795049", qa["checks"]["repository_tests"])
        self.assertEqual("PASS_RUN_30901794677", qa["checks"]["ovc_final_head"])
        self.assertEqual("PASS_JOB_91967638390", qa["checks"]["ovc_merge_readiness"])
        self.assertGreaterEqual(len(qa["warnings"]), 5)
        self.assertEqual([], qa["blockers"])

    def test_prior_census_is_preserved_not_silently_reclassified(self) -> None:
        census = load(CENSUS)
        self.assertEqual(7, census["adoption_target_count"])
        self.assertEqual([], census["blockers"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", census["candidate_construction_authority"])
        self.assertTrue(all(not item["candidate_constructed"] for item in census["adoption_targets"]))


if __name__ == "__main__":
    unittest.main()
