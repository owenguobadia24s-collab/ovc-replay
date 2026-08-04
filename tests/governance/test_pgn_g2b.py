import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2b"
RECEIPT = BASE / "PGN_WP2E_MERGE_RECEIPT.json"
QA = BASE / "PGN_G2B_QA_PACKET.json"
GATE = BASE / "PGN_G2B_OPERATOR_GATE_PACKET.json"
DECISION = BASE / "PGN_G2B_OPERATOR_DECISION.json"
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


def complete_counts(value: dict) -> dict:
    return {key: value.get(key, 0) for key in EXPECTED_COUNTS}


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

    def test_operator_decision_is_exact_and_immutable(self) -> None:
        decision = load(DECISION)
        self.assertEqual("PGN-G2B.OPERATOR.ACKNOWLEDGE_CONTINUE.20260804T132000+0100", decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", decision["decision"])
        self.assertEqual("OVC APPROVE PGN-G2B ACKNOWLEDGE_CONTINUE", decision["exact_operator_command"])
        self.assertEqual("EXPLICIT_OPERATOR_APPROVAL", decision["operator_authority"])
        self.assertEqual(108, decision["acknowledged_evidence"]["object_count"])
        self.assertEqual(EXPECTED_COUNTS, decision["acknowledged_evidence"]["classification_counts"])
        self.assertEqual(16, decision["candidate_construction_scope"]["count"])
        self.assertEqual(16, len(set(decision["candidate_construction_scope"]["programme_ids"])))

    def test_gate_presents_exact_census_candidate_scope_and_exclusions(self) -> None:
        gate = load(GATE)
        manifest = load(MANIFEST)
        self.assertEqual("APPROVED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", gate["status"])
        self.assertFalse(gate["operator_decision_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", gate["decision"])
        self.assertEqual(108, gate["census"]["object_count"])
        self.assertEqual(EXPECTED_COUNTS, gate["census"]["classification_counts"])
        self.assertEqual(EXPECTED_COUNTS, complete_counts(manifest["classification_counts"]))
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

    def test_acknowledgement_releases_candidate_only_authority(self) -> None:
        gate = load(GATE)
        decision = load(DECISION)
        self.assertIn("CANDIDATE_CONSTRUCTION", gate["approved_delta"])
        self.assertNotIn("NATIVE_ADOPTION", gate["approved_delta"])
        self.assertEqual("AUTHORISED_PGN_WP3_EXACT_SIXTEEN_ONLY", gate["authority_after_decision"]["candidate_construction"])
        self.assertEqual("DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3", gate["authority_after_decision"]["native_genesis_adoption"])
        self.assertEqual("NONE", gate["authority_after_decision"]["market_model_selector_release_validation_publication_agent_probability_risk_exposure_execution"])
        self.assertEqual("CONSTRUCT_NATIVE_GENESIS_CANDIDATES_ONLY", decision["candidate_construction_scope"]["authority_granted"])

    def test_state_is_approved_and_routes_to_exact_pgn_wp3_scope(self) -> None:
        state = load(STATE)
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("PGN-G2B", state["gate_id"])
        self.assertEqual("AUTHORISED_PGN_WP3_EXACT_SIXTEEN_ONLY", state["authority"]["candidate_construction"])
        self.assertEqual("DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3", state["authority"]["native_genesis_adoption"])
        self.assertEqual("PGN-WP3", state["next_packet"])
        self.assertEqual("PGN-G3-R1", state["next_gate"])
        self.assertEqual([], state["blockers"])
        forbidden = list(ROOT.glob("**/PGN_WP3*")) + list(ROOT.glob("**/pgn-wp3*"))
        self.assertEqual([], forbidden)

    def test_qa_passes_operator_decision_and_preserves_warnings(self) -> None:
        qa = load(QA)
        self.assertEqual("PASS_OPERATOR_ACKNOWLEDGED_PENDING_FINAL_HEAD_ASSURANCE_AND_MERGE", qa["status"])
        self.assertEqual([], qa["blockers"])
        self.assertGreaterEqual(len(qa["warnings"]), 6)
        self.assertEqual("PASS_MERGE_OPERATOR_DECISION_AND_CONTINUE_TO_PGN_WP3_AFTER_FINAL_HEAD_ASSURANCE", qa["qa_recommendation"])
        self.assertEqual(0, qa["assessment"]["candidates_constructed"])
        self.assertEqual("PASS", qa["checks"]["operator_decision_exact"])


if __name__ == "__main__":
    unittest.main()
