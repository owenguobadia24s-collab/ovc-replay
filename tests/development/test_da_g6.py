from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_PROPOSAL_v0_1.json"
SCHEMA = ROOT / "schemas/development/default_workflow_adoption_profile_v0_1.schema.json"
GATE = ROOT / "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_GATE_PACKET.json"
QA = ROOT / "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_QA_PACKET.json"
REQUEST = ROOT / "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_OPERATOR_DECISION_REQUEST.json"
STATE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
CONTRACT = ROOT / "contracts/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_ADOPTION_PROPOSAL_v0_1.md"
WORKFLOW = ROOT / ".github/workflows/development-acceleration-da-g6.yml"


class DevelopmentAccelerationG6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads(PROFILE.read_text())
        self.schema = json.loads(SCHEMA.read_text())
        self.gate = json.loads(GATE.read_text())
        self.qa = json.loads(QA.read_text())
        self.request = json.loads(REQUEST.read_text())
        self.state = json.loads(STATE.read_text())
        self.contract = CONTRACT.read_text()
        self.workflow = WORKFLOW.read_text()
        self.controls = self.profile["mandatory_acceleration_conditions"]

    def test_profile_is_closed_inactive_and_operator_reserved(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["type"], "object")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.profile["status"], "PENDING_OPERATOR_DA_G6")
        self.assertFalse(self.profile["active"])
        self.assertTrue(self.request["operator_decision_required"])
        self.assertFalse(self.request["default_workflow_active"])
        self.assertFalse(self.request["retirement_active"])
        self.assertEqual(self.schema["properties"]["mandatory_acceleration_conditions"]["const"], self.controls)

    def test_sealed_candidate_two_phase_gate(self) -> None:
        control = self.controls["sealed_candidate_two_phase_gate"]
        self.assertEqual(control["state_sequence"], [
            "IMPLEMENTED", "QA_REVIEW", "CANDIDATE_SEALED",
            "OPERATOR_DECISION_PENDING", "MERGED", "RECEIPT_RECORDED",
        ])
        self.assertTrue(control["candidate_sha_binding_required"])
        self.assertEqual(control["post_seal_candidate_mutation"], "PROHIBITED")
        self.assertIn("exact candidate SHA", self.contract)
        self.assertEqual(
            self.request["candidate_binding"],
            "PASS_DECISION_MUST_REFERENCE_EXACT_CANDIDATE_SHA_AND_FAIL_IF_PR_HEAD_MOVES",
        )

    def test_atomic_transaction_and_head_budget(self) -> None:
        control = self.controls["atomic_git_transaction_and_head_budget"]
        self.assertEqual(control["transaction"], "ONE_BLOB_TREE_COMMIT_FAST_FORWARD_UPDATE")
        self.assertEqual(control["maximum_preseal_candidate_head_mutations"], 2)
        self.assertEqual(control["maximum_postseal_candidate_head_mutations"], 0)
        self.assertEqual(control["repair_after_budget"], "NEW_BOUNDED_SUPERSEDING_BRANCH")

    def test_one_active_pr_programme_lease(self) -> None:
        control = self.controls["one_active_pr_programme_lease"]
        self.assertEqual(control["maximum_active_continuation_prs"], 1)
        lease = self.gate["proposed_authority_delta"]["programme_lease"]
        self.assertEqual(lease["predecessor_pr"], 217)
        self.assertEqual(lease["predecessor_resolution"], "MERGED")
        self.assertEqual(lease["predecessor_merge_commit"], "fed2a3c260c24ffcb5d073ccdf51987800d26f22")

    def test_required_check_provenance_is_fail_closed(self) -> None:
        control = self.controls["required_check_provenance_and_ruleset_health"]
        self.assertEqual(control["source_identity_mismatch_result"], "BLOCK")
        for field in (
            "ruleset_id", "ruleset_logical_hash", "required_context",
            "workflow_path", "workflow_name", "job_name",
            "expected_check_source_identity", "event_type", "branch_pattern", "verified_at",
        ):
            self.assertIn(field, control["required_fields"])
        self.assertEqual(control["required_times"], [
            "BEFORE_BRANCH_CREATION", "AFTER_WORKFLOW_OR_RULESET_CHANGE", "BEFORE_MERGE",
        ])

    def test_canonical_required_pr_runtime(self) -> None:
        control = self.controls["canonical_required_pr_runtime"]
        self.assertEqual(control["runner"], "ubuntu-latest")
        self.assertEqual(control["python"], "3.11")
        self.assertIn("python-version: '3.11'", self.workflow)
        self.assertNotIn("Complete repository suite", self.workflow)

    def test_default_scope_and_retirement_boundaries(self) -> None:
        self.assertEqual(
            self.profile["default_scope"],
            "FUTURE_ELIGIBLE_OVC_IMPLEMENTATION_PACKETS_WITH_APPROVED_REGISTERED_PROFILE",
        )
        self.assertEqual(self.profile["retirement_mode"], "NON_DESTRUCTIVE_RETIRED_NON_AUTHORITATIVE")
        self.assertEqual(len(self.profile["retired_mechanics"]), 5)
        self.assertIn("GOVERNING_PLAN_EXPLICITLY_REQUIRES_PROGRAMME_SPECIFIC_MECHANIC", self.profile["exceptions"])
        self.assertIn("No file deletion", self.contract)
        self.assertIn("Historical files, decisions, releases, tests and evidence remain preserved", self.contract)

    def test_permanent_denials_are_retained(self) -> None:
        denied = set(self.profile["permanent_denials"])
        required = {
            "WRITE_MAIN", "BOT_MERGE_PULL_REQUEST", "BOT_APPROVE_PULL_REQUEST",
            "FORCE_PUSH", "REWRITE_HISTORY", "DELETE_ACCEPTED_RECORD",
            "PROVIDER_ACCESS", "R2_WRITE", "RELEASE_PUBLICATION",
            "SELECTOR_OR_SEMANTIC_MUTATION", "ACTIVE_DISCOVERY_DEVELOPMENT_OR_VALIDATION",
            "NEW_MARKET_INSTRUMENT_CLOCK_SIDE_OR_DEPENDENCY",
            "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_AUTHORITY",
            "UNAPPROVED_AGENT_WRITE_AUTHORITY",
        }
        self.assertTrue(required.issubset(denied))
        authority = self.state["authority"]
        self.assertEqual(authority["direct_main_write"], "PROHIBITED")
        self.assertEqual(authority["merge_pull_request"], "PROHIBITED_TO_BOT")
        self.assertEqual(authority["force_push"], "PROHIBITED")
        self.assertEqual(authority["history_rewrite"], "PROHIBITED")
        self.assertEqual(authority["market"], "NONE")
        self.assertEqual(authority["validation"], "DENIED")
        self.assertEqual(authority["exposure"], "NONE")
        self.assertEqual(authority["execution"], "NONE")

    def test_gate_is_one_inactive_operator_decision(self) -> None:
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"])
        self.assertEqual(self.gate["operator_command"], "OVC APPROVE DA-G6 PASS")
        self.assertEqual(self.request["allowed_decisions"], self.gate["allowed_decisions"])
        self.assertEqual(self.request["operator_command"], self.gate["operator_command"])
        self.assertEqual(len(self.gate["proposed_authority_delta"]["mandatory_acceleration_conditions"]), 5)
        self.assertEqual(len(self.gate["exact_work_after_approval"]), 8)
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertFalse(self.gate["default_workflow_active"])
        self.assertFalse(self.gate["retirement_active"])

    def test_no_active_profile_is_materialized(self) -> None:
        bodies = "\n".join(path.read_text() for path in (PROFILE, GATE, QA, REQUEST, STATE))
        self.assertNotIn('"default_workflow_active": true', bodies)
        self.assertNotIn('"retirement_active": true', bodies)
        self.assertNotIn('"active": true', PROFILE.read_text())
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj_", "Bearer "):
            self.assertNotIn(token, bodies)


if __name__ == "__main__":
    unittest.main()
