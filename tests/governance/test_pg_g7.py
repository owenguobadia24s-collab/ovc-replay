import json
import tempfile
import unittest
from pathlib import Path

from ovc.programme_genesis import build_candidate_event, persist_candidate_event


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
REGISTRY = ROOT / "registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"
RECEIPT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_WP6_MERGE_RECEIPT.json"
REVERIFY = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/DA2_G1_RULESET_REVERIFICATION_20260803.json"
PACKET = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION_PACKET.json"
QA = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_QA_PACKET.json"
DECISION = ROOT / "docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION.json"
DECISION_ID = "PG-G7.OPERATOR.PASS.20260803T222900+0100"


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

    def test_operator_decision_is_exact_and_bounded(self) -> None:
        decision = load(DECISION)
        self.assertEqual(DECISION_ID, decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE PG-G7 PASS", decision["operator_command"])
        self.assertEqual("6549f9534e1843294730e5a54c485cd40f81c92e", decision["accepted_gate_ready_head"])
        delta = decision["authority_delta"]
        self.assertEqual("ACTIVE_BOUNDED_APPEND_ONLY", delta["candidate_persistence"])
        self.assertEqual("ACTIVE_BOUNDED_CANDIDATE_EVENT_PERSISTENCE_ONLY", delta["automatic_upkeep"])
        self.assertEqual("CANDIDATE_UNAPPROVED", delta["candidate_status"])
        self.assertEqual("NONE", delta["authority_effect"])
        for key in ("programme_creation", "programme_event_acceptance", "approval", "merge", "main_write", "publication"):
            self.assertEqual("DENIED", delta[key])

    def test_programme_state_is_approved_and_registry_is_active_bounded(self) -> None:
        state = load(STATE)
        registry = load(REGISTRY)
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("PG-G7", state["current_packet"])
        self.assertEqual("PG-G7", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(DECISION_ID, state["operator_decision_id"])
        self.assertEqual([], state["blockers"])
        self.assertEqual("COMPLETED", packets["PG-WP6"]["status"])
        self.assertEqual("ac5a86931fb9426c55e2cf1e00656ce69908828b", packets["PG-WP6"]["merge_commit"])
        self.assertEqual("APPROVED", packets["PG-G7"]["status"])
        self.assertEqual("OPERATOR_REQUIRED_COMPLETED", packets["PG-G7"]["authority_required"])
        self.assertEqual("docs/releases/programme-genesis-v0-2/pg-g7/PG_G7_OPERATOR_DECISION.json", packets["PG-G7"]["decision_record"])
        self.assertEqual("ACTIVE_BOUNDED_APPEND_ONLY", registry["status"])
        self.assertTrue(registry["enabled"])
        self.assertTrue(registry["capabilities"]["candidate_persistence"])
        self.assertEqual(DECISION_ID, registry["activation_decision_id"])
        self.assertEqual("ACTIVE_BOUNDED_APPEND_ONLY", state["authority"]["candidate_persistence"])
        self.assertEqual("ACTIVE_BOUNDED_CANDIDATE_EVENT_PERSISTENCE_ONLY", state["authority"]["automatic_upkeep"])

    def test_gate_packet_and_predecision_qa_remain_immutable_evidence(self) -> None:
        packet = load(PACKET)
        qa = load(QA)
        self.assertEqual("PG-G7", packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", packet["authority_required"])
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE PG-G7 PASS", packet["exact_operator_command"])
        self.assertEqual([], packet["unresolved_issues"])
        self.assertEqual(8, len(packet["acceptance_conditions"]))
        self.assertTrue(all(item["result"] == "PASS" for item in packet["acceptance_conditions"]))
        self.assertIn(qa["status"], {"QA_REVIEW_PENDING_EXACT_HEAD_CI", "PASS"})
        self.assertEqual([], qa["blockers"])
        self.assertEqual("PASS_IF_EXACT_HEAD_TESTS_PASS", qa["qa_recommendation"])
        self.assertTrue(qa["operator_decision_required"])

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
