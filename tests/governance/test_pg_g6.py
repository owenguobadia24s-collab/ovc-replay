import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
PACKET_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_OPERATOR_DECISION_PACKET.json"
DECISION_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_OPERATOR_DECISION.json"
QA_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_QA_PACKET.json"
MERGE_RECEIPT_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g5/PG_G5_MERGE_RECEIPT.json"
ADAPTER_PATH = ROOT / "registries/governance/programme_genesis/CONTROL_PLANE_ADAPTER_REGISTRY_v0_1.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ProgrammeGenesisG6Tests(unittest.TestCase):
    def test_operator_four_part_decision_is_recorded(self) -> None:
        state = load_json(STATE_PATH)
        decision = load_json(DECISION_PATH)
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("PG-G6", state["current_packet"])
        self.assertEqual("PG-G6", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(
            "PG-G6.OPERATOR.CANON_PASS.MIGRATION_PASS.ENFORCEMENT_DEFER.READ_ONLY_ROUTE_DEFER.20260803T204000+0100",
            state["operator_decision_id"],
        )
        self.assertEqual(
            "OVC APPROVE PG-G6 CANON=PASS MIGRATION=PASS ENFORCEMENT=DEFER READ_ONLY_ROUTE=DEFER",
            decision["operator_command"],
        )
        self.assertEqual("PASS", decision["decisions"]["CANON"]["decision"])
        self.assertEqual("PASS", decision["decisions"]["MIGRATION"]["decision"])
        self.assertEqual("DEFER", decision["decisions"]["ENFORCEMENT"]["decision"])
        self.assertEqual("DEFER", decision["decisions"]["READ_ONLY_ROUTE"]["decision"])

    def test_authority_delta_is_orthogonal_and_bounded(self) -> None:
        authority = load_json(STATE_PATH)["authority"]
        self.assertEqual("ADOPTED_PROGRAMME_GENESIS_V0_2", authority["portfolio_canon"])
        self.assertEqual("ACCEPTED_SEVEN_PROVISIONAL_RECORDS", authority["migration_adoption"])
        self.assertEqual("PROVISIONAL_NON_CANONICAL_ONLY", authority["canonical_migration_adoption"])
        self.assertEqual("DEFERRED_DISABLED", authority["admission_enforcement"])
        self.assertEqual("DEFERRED_DISABLED_UNREGISTERED", authority["control_plane_route"])
        self.assertEqual("DENIED_PENDING_PG_G7", authority["automatic_upkeep"])
        self.assertEqual("NONE", authority["market_model_selector_release_validation"])
        self.assertEqual("NONE", authority["agent_probability_risk_exposure_execution"])

    def test_predecision_packet_contains_exactly_four_independent_parts(self) -> None:
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

    def test_decision_preserves_provisional_migration_uncertainty(self) -> None:
        decision = load_json(DECISION_PATH)
        migration = decision["decisions"]["MIGRATION"]
        self.assertEqual("PROVISIONAL_NON_CANONICAL", migration["record_status"])
        self.assertEqual("NONE_BEYOND_PROGRAMME_OWNED_SOURCE", migration["authority_effect_on_imported_values"])
        self.assertEqual(14, migration["migration_warning_count_retained"])
        self.assertEqual(7, migration["health_warning_count_retained"])
        self.assertEqual("ONLY_DISCOVERED_PROGRAMME_OWNED_STATE_RECORDS", migration["coverage_claim"])

    def test_pg_g5_merge_receipt_binds_final_head_and_evidence(self) -> None:
        receipt = load_json(MERGE_RECEIPT_PATH)
        self.assertEqual(270, receipt["pull_request"])
        self.assertEqual("6e9844c933a380bfb336193862ee7d50105484f4", receipt["final_candidate_commit"])
        self.assertEqual("a639002606cf3842e510f3c9420738d0718d8590", receipt["merge_commit"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["tests"]["conclusion"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["merge_readiness"]["conclusion"])
        self.assertEqual(128, receipt["exact_head_assurance"]["tests"]["test_count"])
        self.assertEqual("DISABLED_PENDING_PG_G6", receipt["repository_evidence"]["adapter_status"])

    def test_adapter_remains_disabled_after_route_defer(self) -> None:
        adapter = load_json(ADAPTER_PATH)
        self.assertEqual("FROZEN_DISABLED_PENDING_PG_G6", adapter["status"])
        self.assertFalse(adapter["enabled"])
        self.assertFalse(adapter["route_registered"])
        self.assertTrue(adapter["read_only"])
        self.assertFalse(adapter["write_enabled"])
        self.assertFalse(adapter["enforcement_enabled"])
        self.assertFalse(adapter["network_listener"])
        self.assertEqual([], adapter["mutation_methods"])

    def test_qa_recommendation_matches_operator_decision(self) -> None:
        qa = load_json(QA_PATH)
        decision = load_json(DECISION_PATH)
        self.assertIn(qa["status"], {"QA_REVIEW_PENDING_EXACT_HEAD_CI", "PASS"})
        self.assertEqual([], qa["blockers"])
        for part in ("CANON", "MIGRATION", "ENFORCEMENT", "READ_ONLY_ROUTE"):
            self.assertEqual(qa["qa_recommendation"][part], decision["decisions"][part]["decision"])

    def test_pg_wp6_is_ready_only_for_disabled_build(self) -> None:
        state = load_json(STATE_PATH)
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("APPROVED", packets["PG-G6"]["status"])
        self.assertEqual("READY", packets["PG-WP6"]["status"])
        self.assertEqual(
            ["PG-G6_CANON_PASS_MIGRATION_PASS_MERGED", "PG-G6_ENFORCEMENT_DEFERRED", "PG-G6_READ_ONLY_ROUTE_DEFERRED"],
            packets["PG-WP6"]["prerequisites"],
        )
        self.assertIsNone(packets["PG-WP6"]["baseline_commit"])
        self.assertEqual("AUTO_EXECUTABLE_BUILD_OPERATOR_REQUIRED_AT_PG_G7", packets["PG-WP6"]["authority_required"])
        self.assertEqual("DENIED_PENDING_PG_G7", state["authority"]["automatic_upkeep"])


if __name__ == "__main__":
    unittest.main()
