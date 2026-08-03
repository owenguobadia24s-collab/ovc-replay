import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
PACKET_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_OPERATOR_DECISION_PACKET.json"
QA_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_QA_PACKET.json"
MERGE_RECEIPT_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g5/PG_G5_MERGE_RECEIPT.json"
ADAPTER_PATH = ROOT / "registries/governance/programme_genesis/CONTROL_PLANE_ADAPTER_REGISTRY_v0_1.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ProgrammeGenesisG6Tests(unittest.TestCase):
    def test_programme_stops_at_operator_four_part_gate(self) -> None:
        state = load_json(STATE_PATH)
        self.assertEqual("GATE_READY", state["status"])
        self.assertEqual("PG-G6", state["current_packet"])
        self.assertEqual("PG-G6", state["current_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertIsNone(state["operator_decision_id"])
        self.assertEqual("AWAIT_OPERATOR_PG_G6_FOUR_PART_DECISION", state["next_action"])
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("COMPLETED", packets["PG-WP5"]["status"])
        self.assertEqual("a639002606cf3842e510f3c9420738d0718d8590", packets["PG-WP5"]["merge_commit"])
        self.assertEqual("GATE_READY", packets["PG-G6"]["status"])
        self.assertEqual("OPERATOR_REQUIRED_FOUR_PART_DECISION", packets["PG-G6"]["authority_required"])

    def test_current_authority_retains_all_pg_g6_denials(self) -> None:
        state = load_json(STATE_PATH)
        authority = state["authority"]
        self.assertEqual("DENIED_PENDING_PG_G6", authority["portfolio_canon"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["migration_adoption"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["control_plane_route"])
        self.assertEqual("DENIED_PENDING_PG_G7", authority["automatic_upkeep"])
        self.assertEqual("NONE", authority["market_model_selector_release_validation"])
        self.assertEqual("NONE", authority["agent_probability_risk_exposure_execution"])

    def test_decision_packet_contains_exactly_four_independent_parts(self) -> None:
        packet = load_json(PACKET_PATH)
        self.assertIn(packet["status"], {"GATE_READY_PENDING_EXACT_HEAD_ASSURANCE", "GATE_READY"})
        self.assertEqual("OPERATOR_REQUIRED_FOUR_PART_DECISION", packet["authority_required"])
        self.assertEqual({"CANON", "MIGRATION", "ENFORCEMENT", "READ_ONLY_ROUTE"}, set(packet["decision_parts"]))
        for name, part in packet["decision_parts"].items():
            self.assertEqual("DENIED_PENDING_PG_G6", part["current_status"], name)
            self.assertIn(part["recommended_decision"], packet["allowed_decisions_per_part"])
            self.assertIn("rollback", part)
        independence = " ".join(packet["decision_independence"])
        self.assertIn("CANON PASS does not imply", independence)
        self.assertIn("MIGRATION PASS does not convert", independence)
        self.assertIn("ENFORCEMENT PASS does not register", independence)
        self.assertIn("READ_ONLY_ROUTE PASS does not activate", independence)

    def test_recommended_decision_is_evidence_bounded(self) -> None:
        packet = load_json(PACKET_PATH)
        recommendation = packet["recommended_combined_decision"]
        self.assertEqual("PASS", recommendation["CANON"])
        self.assertEqual("PASS", recommendation["MIGRATION"])
        self.assertEqual("DEFER", recommendation["ENFORCEMENT"])
        self.assertEqual("DEFER", recommendation["READ_ONLY_ROUTE"])
        self.assertEqual(
            "OVC APPROVE PG-G6 CANON=PASS MIGRATION=PASS ENFORCEMENT=DEFER READ_ONLY_ROUTE=DEFER",
            packet["exact_recommended_operator_command"],
        )
        self.assertIn("no separately validated active admission-enforcement consumer", " ".join(packet["decision_parts"]["ENFORCEMENT"]["defer_rationale"]))
        self.assertIn("no validated network or Control Plane route implementation", " ".join(packet["decision_parts"]["READ_ONLY_ROUTE"]["defer_rationale"]))

    def test_migration_pass_preserves_provisional_uncertainty_and_coverage_warning(self) -> None:
        packet = load_json(PACKET_PATH)
        migration = packet["decision_parts"]["MIGRATION"]
        pass_effect = " ".join(migration["pass_effect"])
        self.assertIn("PROVISIONAL_NON_CANONICAL", pass_effect)
        self.assertIn("Fourteen migration warnings", pass_effect)
        self.assertIn("does not claim that every historical OVC programme", " ".join(migration["warnings"]))
        evidence = packet["evidence_summary"]
        self.assertEqual(7, evidence["migrated_programme_rows"])
        self.assertEqual(14, evidence["migration_warning_count"])
        self.assertEqual(7, evidence["health_warning_count"])
        self.assertEqual(0, evidence["health_blocking_count"])
        self.assertEqual(0, evidence["migration_blocking_conflict_count"])

    def test_pg_g5_merge_receipt_binds_final_head_and_evidence(self) -> None:
        receipt = load_json(MERGE_RECEIPT_PATH)
        self.assertEqual(270, receipt["pull_request"])
        self.assertEqual("6e9844c933a380bfb336193862ee7d50105484f4", receipt["final_candidate_commit"])
        self.assertEqual("a639002606cf3842e510f3c9420738d0718d8590", receipt["merge_commit"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["tests"]["conclusion"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["merge_readiness"]["conclusion"])
        self.assertEqual(128, receipt["exact_head_assurance"]["test_count"])
        self.assertEqual("DISABLED_PENDING_PG_G6", receipt["repository_evidence"]["adapter_status"])

    def test_adapter_remains_disabled_and_unregistered_at_gate(self) -> None:
        adapter = load_json(ADAPTER_PATH)
        self.assertEqual("FROZEN_DISABLED_PENDING_PG_G6", adapter["status"])
        self.assertFalse(adapter["enabled"])
        self.assertFalse(adapter["route_registered"])
        self.assertTrue(adapter["read_only"])
        self.assertFalse(adapter["write_enabled"])
        self.assertFalse(adapter["enforcement_enabled"])
        self.assertFalse(adapter["network_listener"])
        self.assertEqual([], adapter["mutation_methods"])
        self.assertEqual("PG-G6", adapter["activation_gate"])

    def test_qa_recommendation_matches_consolidated_packet(self) -> None:
        qa = load_json(QA_PATH)
        packet = load_json(PACKET_PATH)
        self.assertIn(qa["status"], {"QA_REVIEW_PENDING_EXACT_HEAD_CI", "PASS"})
        self.assertEqual([], qa["blockers"])
        self.assertEqual(packet["recommended_combined_decision"]["CANON"], qa["qa_recommendation"]["CANON"])
        self.assertEqual(packet["recommended_combined_decision"]["MIGRATION"], qa["qa_recommendation"]["MIGRATION"])
        self.assertEqual(packet["recommended_combined_decision"]["ENFORCEMENT"], qa["qa_recommendation"]["ENFORCEMENT"])
        self.assertEqual(packet["recommended_combined_decision"]["READ_ONLY_ROUTE"], qa["qa_recommendation"]["READ_ONLY_ROUTE"])

    def test_pg_wp6_cannot_start_without_accepted_relevant_pg_g6_parts(self) -> None:
        state = load_json(STATE_PATH)
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual(["PG-G6_RELEVANT_PARTS_PASS_MERGED"], packets["PG-WP6"]["prerequisites"])
        self.assertEqual("PLANNED", packets["PG-WP6"]["status"])
        self.assertIsNone(packets["PG-WP6"]["baseline_commit"])
        self.assertEqual("OPERATOR_REQUIRED_AT_PG_G7", packets["PG-WP6"]["authority_required"])


if __name__ == "__main__":
    unittest.main()
