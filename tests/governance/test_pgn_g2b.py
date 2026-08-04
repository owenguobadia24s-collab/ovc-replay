import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2b"
RECEIPT = BASE / "PGN_WP2E_MERGE_RECEIPT.json"
QA = BASE / "PGN_G2B_QA_PACKET.json"
GATE = BASE / "PGN_G2B_OPERATOR_GATE_PACKET.json"
STATE = BASE / "PGN_G2B_PROGRAMME_STATE_UPDATE.json"
MANIFEST = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"

EXPECTED_COUNTS = {
    "NATIVE_PROGRAMME": 2,
    "LEGACY_PROGRAMME_REQUIRING_CONVERSION": 16,
    "SUPERSEDED_PROGRAMME": 1,
    "ABSORBED_INTO_SUCCESSOR": 0,
    "BOUNDED_PACKET_NOT_A_PROGRAMME": 70,
    "PROPOSAL_NOT_ADMITTED": 1,
    "UNRESOLVED": 18,
}


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class NativeGenesisPortfolioG2BTests(unittest.TestCase):
    def test_wp2e_merge_receipt_binds_exact_head_merge_and_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(285, receipt["pull_request"])
        self.assertEqual("eaa855aad5a81041bf6f401ad8c3c834f9bc35bc", receipt["final_head"])
        self.assertEqual("dcdc968ea936dd1e66f7fa1a6cf9c0a4528a52c1", receipt["merge_commit"])
        self.assertEqual(EXPECTED_COUNTS, receipt["census"]["classification_counts"])
        self.assertEqual(108, receipt["census"]["object_count"])
        for key in ("repository_tests", "ovc_final_head", "merge_readiness"):
            self.assertEqual("SUCCESS", receipt["exact_head_assurance"][key]["conclusion"])

    def test_gate_presents_exact_census_candidate_scope_and_exclusions(self) -> None:
        gate = load(GATE)
        manifest = load(MANIFEST)
        self.assertEqual(108, gate["census"]["object_count"])
        self.assertEqual(EXPECTED_COUNTS, gate["census"]["classification_counts"])
        self.assertEqual(EXPECTED_COUNTS, manifest["classification_counts"])
        self.assertEqual(16, gate["candidate_construction_scope"]["count"])
        self.assertEqual(16, len(gate["candidate_construction_scope"]["programme_ids"]))
        self.assertEqual(16, len(set(gate["candidate_construction_scope"]["programme_ids"])))
        self.assertEqual(70, gate["excluded_from_candidate_construction"]["bounded_packets_and_release_objects"])
        self.assertEqual(18, gate["excluded_from_candidate_construction"]["unresolved_objects"])
        self.assertEqual(["OVC-PCCR-v0.1"], gate["excluded_from_candidate_construction"]["proposals_not_admitted"])

    def test_lineage_and_coverage_uncertainty_are_explicit(self) -> None:
        gate = load(GATE)
        self.assertEqual(1, len(gate["lineage_consolidations"]))
        lineage = gate["lineage_consolidations"][0]
        self.assertEqual("OPT-A.GBPUSD.2026H1.v1", lineage["object_id"])
        self.assertEqual("SUPERSEDED_PROGRAMME", lineage["classification"])
        self.assertEqual(3, len(lineage["successors"]))
        self.assertFalse(gate["coverage_boundary"]["initial_commit_resolved"])
        self.assertEqual("UNRESOLVED", gate["coverage_boundary"]["pre_snapshot_history_classification"])
        self.assertEqual(0, gate["census"]["classification_counts"]["ABSORBED_INTO_SUCCESSOR"])

    def test_operator_decision_options_and_recommendation_are_bounded(self) -> None:
        gate = load(GATE)
        self.assertEqual(
            ["ACKNOWLEDGE_CONTINUE", "ADJUST_SCOPE", "DEFER", "BLOCK", "QUARANTINE"],
            gate["allowed_decisions"],
        )
        self.assertEqual("ACKNOWLEDGE_CONTINUE", gate["recommended_decision"])
        self.assertEqual("OVC APPROVE PGN-G2B ACKNOWLEDGE_CONTINUE", gate["exact_operator_command"])
        self.assertIn("PGN_G3_REMAINS_REQUIRED_FOR_EVERY_NATIVE_ADOPTION", gate["acceptance_conditions"])
        self.assertEqual("DENIED_PENDING_PGN_G2B", gate["current_authority"]["candidate_construction"])
        self.assertEqual("DENIED_PENDING_PGN_G3", gate["current_authority"]["native_genesis_adoption"])

    def test_state_stops_before_pgn_wp3_and_candidate_construction(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertEqual("PGN-G2B", state["gate_id"])
        self.assertEqual("DENIED_PENDING_PGN_G2B", state["authority"]["candidate_construction"])
        self.assertEqual("DENIED_PENDING_PGN_G3", state["authority"]["native_genesis_adoption"])
        self.assertEqual("AWAIT_OPERATOR_PGN_G2B_ACKNOWLEDGE_CONTINUE_OR_ADJUST_SCOPE_DO_NOT_BEGIN_PGN_WP3", state["next_action"])
        self.assertEqual([], state["blockers"])
        forbidden = list(ROOT.glob("**/PGN_WP3*")) + list(ROOT.glob("**/pgn-wp3*"))
        self.assertEqual([], forbidden)

    def test_qa_has_no_blocker_and_preserves_warnings(self) -> None:
        qa = load(QA)
        self.assertEqual("ACKNOWLEDGE_CONTINUE", qa["qa_recommendation"])
        self.assertEqual([], qa["blockers"])
        self.assertGreaterEqual(len(qa["warnings"]), 6)
        self.assertEqual("NONE_UNTIL_OPERATOR_PGN_G2B_DECISION", qa["authority_delta"])
        self.assertEqual(0, qa["assessment"]["candidates_constructed"])

    def test_acknowledgement_is_not_native_adoption_or_reserved_authority(self) -> None:
        gate = load(GATE)
        proposed = gate["proposed_delta"]
        self.assertIn("CANDIDATE_CONSTRUCTION", proposed)
        self.assertNotIn("NATIVE_ADOPTION", proposed)
        self.assertEqual("NONE", gate["current_authority"]["market_model_selector_release_validation_publication_agent_probability_risk_exposure_execution"])
        self.assertEqual("STILL_DENIED_PENDING_PGN_G3", gate["candidate_construction_scope"]["native_adoption"])


if __name__ == "__main__":
    unittest.main()
