from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/development-acceleration-v0-1/da-wp4b"
GATE = BASE / "DA_G4B_GATE_PACKET.json"
REQUEST = BASE / "DA_G4B_OPERATOR_DECISION_REQUEST.json"
RULESET = BASE / "main-ruleset.json"
STATE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
QA = BASE / "DA_WP4B_QA_PACKET.json"
EXPECTED_RULESET_SHA = "ed6fe8eb2c030fc185adbf70ae4571fca3fee2f3fbab8002267c8da2b221c0c4"

class DevelopmentAccelerationG4BTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = json.loads(GATE.read_text())
        self.request = json.loads(REQUEST.read_text())
        self.state = json.loads(STATE.read_text())
        self.qa = json.loads(QA.read_text())

    def test_single_consolidated_operator_gate(self) -> None:
        self.assertEqual(self.gate["gate_id"], "DA-G4B")
        self.assertEqual(self.gate["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(self.gate["recommended_decision"], "PASS")
        self.assertEqual(self.gate["allowed_decisions"], ["PASS","DEFER","BLOCK","QUARANTINE","SUPERSEDE"])
        self.assertEqual(self.gate["operator_command"], "OVC APPROVE DA-G4B PASS")
        self.assertEqual(self.request["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(self.request["operator_command"], "OVC APPROVE DA-G4B PASS")
        self.assertFalse(self.gate["authority_active"])
        self.assertFalse(self.gate["production_transport_active"])
        self.assertFalse(self.request["authority_active"])

    def test_all_acceptance_conditions_pass_before_operator_boundary(self) -> None:
        results = {row["condition"]: row["result"] for row in self.gate["acceptance_conditions"]}
        required = {"CLOSED_ACTIVE_PROFILE_SCHEMA_MATCH","BRANCH_AND_PATH_ENFORCING_WRITER_ADAPTER",
                    "NO_MERGE_API_AVAILABLE_TO_BOT","DENIED_ACTION_TESTS_PASS","TOKEN_REDACTION_TESTS_PASS",
                    "IDEMPOTENCY_AND_COLLISION_TESTS_PASS","REVOCATION_TESTS_PASS",
                    "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED","REAL_PROPOSAL_BRANCH_SHADOW_PASS",
                    "FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS","QA_PASS"}
        self.assertTrue(required.issubset(results))
        self.assertTrue(all(results[key] == "PASS" for key in required))
        self.assertEqual(self.gate["unresolved_issues"], [])
        self.assertEqual(self.qa["status"], "PASS_GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(self.qa["qa_recommendation"], "PASS")

    def test_ruleset_and_shadow_evidence_are_exact(self) -> None:
        self.assertEqual(hashlib.sha256(RULESET.read_bytes()).hexdigest(), EXPECTED_RULESET_SHA)
        ruleset = json.loads(RULESET.read_bytes())
        self.assertEqual(ruleset["enforcement"], "active")
        self.assertIn("refs/heads/main", ruleset["conditions"]["ref_name"]["include"])
        self.assertEqual(ruleset["bypass_actors"], [])
        self.assertEqual(ruleset["current_user_can_bypass"], "never")
        self.assertEqual(self.gate["external_artifacts"][1]["sha256"], EXPECTED_RULESET_SHA)
        self.assertEqual(self.gate["current_authority"]["production_transport"], "ABSENT_FAIL_CLOSED")
        self.assertEqual(self.state["activation_gate"]["shadow_pull_request"], 211)
        self.assertEqual(self.state["activation_gate"]["shadow_status"], "PASS_OPEN_UNMERGED")

    def test_proposed_delta_remains_narrow_and_denials_permanent(self) -> None:
        delta = self.gate["proposed_authority_delta"]
        self.assertEqual(delta["allowed_actions"], ["CREATE_BOT_BRANCH","CREATE_OR_UPDATE_ALLOWLISTED_FILES","OPEN_OR_UPDATE_PULL_REQUEST"])
        self.assertEqual(delta["allowed_branches"], ["bot/ovc-dev-accel-receipts/*"])
        denied = set(delta["permanent_denials"])
        for token in ("WRITE_MAIN","MERGE_PULL_REQUEST","APPROVE_PULL_REQUEST","FORCE_PUSH",
                      "REWRITE_HISTORY","MODIFY_AUTHORITY_PROFILE","PROVIDER_ACCESS","R2_WRITE",
                      "VALIDATION_ACCESS","PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT"):
            self.assertIn(token, denied)
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["programme_status"], "GATE_READY")
        self.assertFalse(self.state["activation_gate"]["authority_active"])

if __name__ == "__main__":
    unittest.main()
