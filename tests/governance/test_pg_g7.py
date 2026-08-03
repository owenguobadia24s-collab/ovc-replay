import json
import tempfile
import unittest
from pathlib import Path

from ovc.programme_genesis import build_candidate_event, persist_candidate_event


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
REGISTRY = ROOT / "registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"
WP6_RECEIPT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_WP6_MERGE_RECEIPT.json"
G7_RECEIPT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_MERGE_RECEIPT.json"
REVERIFY = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/DA2_G1_RULESET_REVERIFICATION_20260803.json"
PACKET = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION_PACKET.json"
QA = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_QA_PACKET.json"
DECISION = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION.json"
DECISION_ID = "PG-G7.OPERATOR.PASS.20260803T222900+0100"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ProgrammeGenesisG7GateTests(unittest.TestCase):
    def test_pg_wp6_merge_receipt_resolves_strict_refresh_blocker(self) -> None:
        receipt = load(WP6_RECEIPT)
        self.assertEqual(277, receipt["pull_request"])
        self.assertEqual("dd818f157aee2814b60091e9562e598de6012c38", receipt["refreshed_final_head"])
        self.assertEqual("ac5a86931fb9426c55e2cf1e00656ce69908828b", receipt["merge_commit"])
        self.assertEqual("RESOLVED", receipt["blocker_resolution"]["result"])

    def test_ruleset_reverification_matches_accepted_da2_evidence(self) -> None:
        evidence = load(REVERIFY)
        expected = "e346492b2e8f3df93f2801e4f69d9b7be04798652d00edee0ec18c5c184f306d"
        self.assertEqual(expected, evidence["source_sha256"])
        self.assertTrue(evidence["accepted_repository_verification"]["exact_hash_match"])
        self.assertEqual("active", evidence["observed"]["enforcement"])
        self.assertTrue(evidence["observed"]["strict_required_status_checks_policy"])
        self.assertEqual([{"context": "OVC merge readiness", "integration_id": 15368}], evidence["observed"]["required_status_checks"])
        self.assertEqual([], evidence["observed"]["bypass_actors"])
        self.assertEqual("PASS_AND_MERGED", evidence["corrective_result"])

    def test_operator_decision_is_exact_and_bounded(self) -> None:
        decision = load(DECISION)
        self.assertEqual(DECISION_ID, decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE PG-G7 PASS", decision["operator_command"])
        delta = decision["authority_delta"]
        self.assertEqual("ACTIVE_BOUNDED_APPEND_ONLY", delta["candidate_persistence"])
        self.assertEqual("CANDIDATE_UNAPPROVED", delta["candidate_status"])
        self.assertEqual("NONE", delta["authority_effect"])
        for key in ("programme_creation", "programme_event_acceptance", "approval", "merge", "main_write", "publication"):
            self.assertEqual("DENIED", delta[key])

    def test_programme_state_and_gate_are_completed(self) -> None:
        state = load(STATE)
        registry = load(REGISTRY)
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(DECISION_ID, state["operator_decision_id"])
        self.assertEqual("PROGRAMME_COMPLETED_NO_NEXT_PACKET", state["next_action"])
        self.assertEqual([], state["blockers"])
        self.assertEqual("COMPLETED", packets["PG-G7"]["status"])
        self.assertEqual("54127ead1099c7030c210691689b621bd3728d91", packets["PG-G7"]["candidate_commit"])
        self.assertEqual("b86f63a757621d52ff3ba4937c5706835bf34180", packets["PG-G7"]["merge_commit"])
        self.assertIsNone(packets["PG-G7"]["next_packet"])
        self.assertEqual("ACTIVE_BOUNDED_APPEND_ONLY", registry["status"])
        self.assertTrue(registry["enabled"])
        self.assertTrue(registry["capabilities"]["candidate_persistence"])
        self.assertEqual(DECISION_ID, registry["activation_decision_id"])

    def test_pg_g7_merge_receipt_binds_terminal_state(self) -> None:
        receipt = load(G7_RECEIPT)
        self.assertEqual(278, receipt["pull_request"])
        self.assertEqual("54127ead1099c7030c210691689b621bd3728d91", receipt["final_decision_head"])
        self.assertEqual("b86f63a757621d52ff3ba4937c5706835bf34180", receipt["merge_commit"])
        self.assertEqual("SQUASH", receipt["merge_method"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["repository_tests"]["conclusion"])
        self.assertEqual(156, receipt["exact_head_assurance"]["repository_tests"]["test_count"])
        self.assertEqual("SUCCESS", receipt["exact_head_assurance"]["merge_readiness"]["conclusion"])
        self.assertEqual("COMPLETED", receipt["programme_result"])
        self.assertIsNone(receipt["next_packet"])

    def test_gate_packet_and_predecision_qa_remain_immutable_evidence(self) -> None:
        packet = load(PACKET)
        qa = load(QA)
        self.assertEqual("PG-G7", packet["gate_id"])
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE PG-G7 PASS", packet["exact_operator_command"])
        self.assertEqual([], packet["unresolved_issues"])
        self.assertEqual(8, len(packet["acceptance_conditions"]))
        self.assertTrue(all(item["result"] == "PASS" for item in packet["acceptance_conditions"]))
        self.assertEqual([], qa["blockers"])
        self.assertEqual("PASS_IF_EXACT_HEAD_TESTS_PASS", qa["qa_recommendation"])

    def test_active_persistence_still_has_no_authority_effect(self) -> None:
        registry = load(REGISTRY)
        event = build_candidate_event(
            programme_id="OVC-PG-v0.2",
            event_type="HEALTH_FINDING_CANDIDATE",
            source_kind="PROGRAMME_HEALTH_FINDING",
            source_finding_id="pg-g7-test",
            source_path="docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION.json",
            source_sha256="c" * 64,
            observed_at="2026-08-03T21:29:00+00:00",
            first_valid_at="2026-08-03T21:29:00+00:00",
            proposed_payload={"finding_type": "POST_ACTIVATION_CHECK", "severity": "INFO"},
            target_branch="upkeep/pg-candidate-events/g7-test",
            registry=registry,
            existing_programme_ids={"OVC-PG-v0.2"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = persist_candidate_event(
                temp_dir,
                event,
                registry=registry,
                branch_name="upkeep/pg-candidate-events/g7-test",
                existing_programme_ids={"OVC-PG-v0.2"},
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("CANDIDATE_UNAPPROVED", stored["status"])
            self.assertEqual("NONE", stored["authority_effect"])


if __name__ == "__main__":
    unittest.main()
