import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
PACKET_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3A_OPERATOR_ACKNOWLEDGEMENT_PACKET.json"
DECISION_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3A_OPERATOR_DECISION.json"
RECEIPT_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3_MERGE_RECEIPT.json"
REPORT_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3_GRAPH_VALIDATION_REPORT.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ProgrammeGenesisG3ATests(unittest.TestCase):
    def test_operator_acknowledgement_is_immutable_and_bounded(self) -> None:
        decision = load_json(DECISION_PATH)
        self.assertEqual("PG-G3A.OPERATOR.ACKNOWLEDGE_CONTINUE.20260803T194700+0100", decision["decision_id"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", decision["decision"])
        self.assertEqual("OVC APPROVE PG-G3A ACKNOWLEDGE_CONTINUE", decision["operator_command"])
        delta = decision["authority_delta"]
        self.assertEqual("APPROVED", delta["pg_wp4_source_faithful_provisional_migration"])
        self.assertEqual("NOT_PRE_ACCEPTED", delta["future_migrated_programme_facts"])
        self.assertEqual("NOT_PRE_ACCEPTED", delta["future_migrated_edges"])
        self.assertEqual("DENIED_PENDING_PG_G6", delta["canonical_migration_adoption"])
        self.assertEqual("DENIED_PENDING_PG_G6", delta["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G7", delta["automatic_upkeep"])

    def test_pg_wp3_receipt_binds_exact_merge_and_assurance(self) -> None:
        receipt = load_json(RECEIPT_PATH)
        self.assertEqual(266, receipt["pull_request"])
        self.assertEqual("dae630a8dba8d46bd82bf7f22cac45a00b177781", receipt["final_candidate_commit"])
        self.assertEqual("e3e6c12a293e0c1802cc2686678690d01318161b", receipt["merge_commit"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["tests"]["conclusion"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["merge_readiness"]["conclusion"])
        self.assertEqual("DENIED_PENDING_OPERATOR_ACKNOWLEDGEMENT", receipt["migration_status"])

    def test_acknowledgement_packet_is_approved_but_non_canonical(self) -> None:
        packet = load_json(PACKET_PATH)
        self.assertEqual("APPROVED", packet["status"])
        self.assertEqual("OPERATOR_REQUIRED_COMPLETED", packet["authority_required"])
        self.assertEqual("ACKNOWLEDGE_CONTINUE", packet["decision"])
        self.assertEqual("OVC APPROVE PG-G3A ACKNOWLEDGE_CONTINUE", packet["operator_command"])
        self.assertEqual([], packet["unresolved_issues"])
        self.assertEqual(0, packet["qa"]["blocking_findings"])
        self.assertIn("CANONICAL_MIGRATION_ADOPTION", packet["reserved_authority_denials"])
        self.assertIn("ADMISSION_ENFORCEMENT", packet["reserved_authority_denials"])
        self.assertIn("AGENT_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", packet["reserved_authority_denials"])

    def test_graph_claim_is_limited_to_pre_migration_self_graph(self) -> None:
        report = load_json(REPORT_PATH)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(10, report["census"]["nodes"])
        self.assertEqual(8, report["census"]["edges"])
        self.assertEqual(0, report["validation_findings"]["hard_dependency_cycles"])
        self.assertEqual(0, report["validation_findings"]["graph_authority_grants"])
        self.assertFalse(report["migration_boundary"]["migration_enabled"])
        self.assertEqual(0, report["migration_boundary"]["imported_existing_programmes"])
        self.assertTrue(any("pre-migration constitutional self-graph" in item for item in report["limitations"]))

    def test_acknowledgement_merge_is_preserved_as_pg_wp4_prerequisite(self) -> None:
        state = load_json(STATE_PATH)
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("COMPLETED", packets["PG-WP3"]["status"])
        self.assertIn(packets["PG-G3A"]["status"], {"APPROVED", "COMPLETED"})
        self.assertEqual("4919a3ce7bb9682f43c8bf41ed3b0a0bd4b4168a", packets["PG-G3A"]["merge_commit"])
        self.assertEqual(["PG-G3A_ACKNOWLEDGE_CONTINUE_MERGED"], packets["PG-WP4"]["prerequisites"])
        self.assertIn(packets["PG-WP4"]["status"], {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "APPROVED", "COMPLETED"})

    def test_current_state_retains_post_acknowledgement_denials(self) -> None:
        state = load_json(STATE_PATH)
        authority = state["authority"]
        self.assertTrue(str(authority["portfolio_migration"]).startswith("APPROVED"))
        self.assertEqual("DENIED_PENDING_PG_G6", authority["canonical_migration_adoption"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["control_plane_route"])
        self.assertEqual("DENIED_PENDING_PG_G7", authority["automatic_upkeep"])
        self.assertEqual("NONE", authority["market_model_selector_release_validation"])
        self.assertEqual("NONE", authority["agent_probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
