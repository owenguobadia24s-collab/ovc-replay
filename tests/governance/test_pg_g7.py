import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
REGISTRY = ROOT / "registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"
RECEIPT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_WP6_MERGE_RECEIPT.json"
REVERIFY = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/DA2_G1_RULESET_REVERIFICATION_20260803.json"
PACKET = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION_PACKET.json"
QA = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_QA_PACKET.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ProgrammeGenesisG7GateTests(unittest.TestCase):
    def test_pg_wp6_merge_receipt_resolves_strict_refresh_blocker(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(277, receipt["pull_request"])
        self.assertEqual("dd818f157aee2814b60091e9562e598de6012c38", receipt["refreshed_final_head"])
        self.assertEqual("ac5a86931fb9426c55e2cf1e00656ce69908828b", receipt["merge_commit"])
        resolution = receipt["blocker_resolution"]
        self.assertEqual("STRICT_RULESET_REQUIRED_BRANCH_UP_TO_DATE_WITH_MAIN", resolution["root_cause"])
        self.assertEqual(1, resolution["before_refresh"]["behind_by"])
        self.assertEqual(0, resolution["after_refresh"]["behind_by"])
        self.assertFalse(resolution["force_push"])
        self.assertFalse(resolution["history_rewrite"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["tests"]["conclusion"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["merge_readiness"]["conclusion"])

    def test_ruleset_reverification_matches_accepted_da2_evidence(self) -> None:
        evidence = load(REVERIFY)
        expected = "e346492b2e8f3df93f2801e4f69d9b7be04798652d00edee0ec18c5c184f306d"
        self.assertEqual(expected, evidence["source_sha256"])
        self.assertTrue(evidence["accepted_repository_verification"]["exact_hash_match"])
        self.assertEqual("active", evidence["observed"]["enforcement"])
        self.assertTrue(evidence["observed"]["strict_required_status_checks_policy"])
        self.assertEqual(
            [{"context": "OVC merge readiness", "integration_id": 15368}],
            evidence["observed"]["required_status_checks"],
        )
        self.assertEqual([], evidence["observed"]["bypass_actors"])
        self.assertEqual("PASS_AND_MERGED", evidence["corrective_result"])

    def test_programme_state_is_gate_ready_and_upkeep_remains_disabled(self) -> None:
        state = load(STATE)
        registry = load(REGISTRY)
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("GATE_READY", state["status"])
        self.assertEqual("PG-G7", state["current_packet"])
        self.assertEqual("PG-G7", state["current_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertIsNone(state["operator_decision_id"])
        self.assertEqual([], state["blockers"])
        self.assertEqual("COMPLETED", packets["PG-WP6"]["status"])
        self.assertEqual("ac5a86931fb9426c55e2cf1e00656ce69908828b", packets["PG-WP6"]["merge_commit"])
        self.assertEqual("GATE_READY", packets["PG-G7"]["status"])
        self.assertEqual([], packets["PG-G7"]["blockers"])
        self.assertEqual("FROZEN_DISABLED_PENDING_PG_G7", registry["status"])
        self.assertFalse(registry["enabled"])
        self.assertFalse(registry["capabilities"]["candidate_persistence"])
        self.assertEqual("DENIED_PENDING_PG_G7", state["authority"]["candidate_persistence"])
        self.assertEqual("DENIED_PENDING_PG_G7", state["authority"]["automatic_upkeep"])

    def test_gate_packet_is_consolidated_and_bounded(self) -> None:
        packet = load(PACKET)
        self.assertEqual("PG-G7", packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", packet["authority_required"])
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE PG-G7 PASS", packet["exact_operator_command"])
        self.assertEqual(
            ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            packet["allowed_decisions"],
        )
        delta = packet["proposed_authority_delta"]
        self.assertEqual("ACTIVATE_BOUNDED_APPEND_ONLY", delta["candidate_persistence"])
        self.assertEqual("CANDIDATE_UNAPPROVED", delta["candidate_status"])
        self.assertEqual("NONE", delta["authority_effect"])
        self.assertEqual("REMAINS_DENIED", delta["programme_creation"])
        self.assertEqual("REMAINS_DENIED", delta["approval_merge_main_write_publication"])
        self.assertEqual([], packet["unresolved_issues"])
        self.assertEqual(8, len(packet["acceptance_conditions"]))
        self.assertTrue(all(item["result"] == "PASS" for item in packet["acceptance_conditions"]))

    def test_qa_recommends_pass_without_self_activation(self) -> None:
        qa = load(QA)
        registry = load(REGISTRY)
        self.assertIn(qa["status"], {"QA_REVIEW_PENDING_EXACT_HEAD_CI", "PASS"})
        self.assertEqual([], qa["blockers"])
        self.assertEqual("PASS_IF_EXACT_HEAD_TESTS_PASS", qa["qa_recommendation"])
        self.assertTrue(qa["operator_decision_required"])
        self.assertFalse(registry["enabled"])
        self.assertIsNone(registry["activation_decision_id"])


if __name__ == "__main__":
    unittest.main()
