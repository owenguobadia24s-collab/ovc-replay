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


class DevelopmentAccelerationG6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads(PROFILE.read_text())
        self.schema = json.loads(SCHEMA.read_text())
        self.gate = json.loads(GATE.read_text())
        self.qa = json.loads(QA.read_text())
        self.request = json.loads(REQUEST.read_text())
        self.state = json.loads(STATE.read_text())
        self.contract = CONTRACT.read_text()

    def test_profile_is_closed_inactive_and_operator_reserved(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["type"], "object")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.schema["properties"]["status"]["const"], "PENDING_OPERATOR_DA_G6")
        self.assertFalse(self.schema["properties"]["active"]["const"])
        self.assertEqual(self.profile["status"], "PENDING_OPERATOR_DA_G6")
        self.assertFalse(self.profile["active"])
        self.assertTrue(self.request["operator_decision_required"])
        self.assertFalse(self.request["default_workflow_active"])
        self.assertFalse(self.request["retirement_active"])

    def test_default_scope_requires_approved_registered_packets(self) -> None:
        self.assertEqual(
            self.profile["default_scope"],
            "FUTURE_ELIGIBLE_OVC_IMPLEMENTATION_PACKETS_WITH_APPROVED_REGISTERED_PROFILE",
        )
        stages = self.profile["required_stages"]
        for token in (
            "AUTHORITY_AND_PREREQUISITE_RESOLUTION",
            "UNIVERSAL_ARTIFACT_PREFLIGHT",
            "TIERED_TEST_SELECTION",
            "COMPLETE_FINAL_HEAD_ASSURANCE",
            "QA_AND_GATE_CLASSIFICATION",
            "DETERMINISTIC_CLOSURE_AND_RECEIPT",
            "ELIGIBLE_SQUASH_MERGE",
            "PROGRAMME_STATE_CONTINUATION",
        ):
            self.assertIn(token, stages)
        self.assertIn("OPERATOR_RESERVED_AUTHORITY_REQUIRES_GATE", self.profile["exceptions"])

    def test_retirement_is_explicit_non_destructive_and_exception_aware(self) -> None:
        self.assertEqual(self.profile["retirement_mode"], "NON_DESTRUCTIVE_RETIRED_NON_AUTHORITATIVE")
        self.assertEqual(len(self.profile["retired_mechanics"]), 5)
        self.assertIn("GOVERNING_PLAN_EXPLICITLY_REQUIRES_PROGRAMME_SPECIFIC_MECHANIC", self.profile["exceptions"])
        self.assertIn("No file deletion", self.contract)
        self.assertIn("Historical files, decisions, releases, tests and evidence remain preserved", self.contract)

    def test_permanent_denials_are_exactly_retained(self) -> None:
        denied = set(self.profile["permanent_denials"])
        required = {
            "WRITE_MAIN",
            "BOT_MERGE_PULL_REQUEST",
            "BOT_APPROVE_PULL_REQUEST",
            "FORCE_PUSH",
            "REWRITE_HISTORY",
            "DELETE_ACCEPTED_RECORD",
            "PROVIDER_ACCESS",
            "R2_WRITE",
            "RELEASE_PUBLICATION",
            "SELECTOR_OR_SEMANTIC_MUTATION",
            "ACTIVE_DISCOVERY_DEVELOPMENT_OR_VALIDATION",
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

    def test_gate_is_one_consolidated_operator_decision(self) -> None:
        self.assertEqual(self.gate["gate_id"], "DA-G6")
        self.assertEqual(self.gate["allowed_decisions"], ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"])
        self.assertEqual(self.gate["operator_command"], "OVC APPROVE DA-G6 PASS")
        self.assertEqual(self.request["allowed_decisions"], self.gate["allowed_decisions"])
        self.assertEqual(self.request["operator_command"], self.gate["operator_command"])
        self.assertEqual(len(self.gate["exact_work_after_approval"]), 8)
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertFalse(self.gate["default_workflow_active"])
        self.assertFalse(self.gate["retirement_active"])

    def test_qa_has_no_substantive_warning_or_unresolved_issue(self) -> None:
        self.assertEqual(self.gate["warnings"], [])
        self.assertEqual(self.gate["unresolved_issues"], [])
        self.assertEqual(self.qa["warnings"], [])
        self.assertEqual(self.qa["proposed_authority_delta"], "DEFAULT_WORKFLOW_ADOPTION_AND_NON_DESTRUCTIVE_DUPLICATED_MECHANICS_RETIREMENT")
        self.assertEqual(self.qa["reserved_authority_delta"], "OPERATOR_REQUIRED")
        self.assertFalse(self.qa["default_workflow_active"])
        self.assertFalse(self.qa["retirement_active"])

    def test_no_decision_or_active_profile_is_materialized(self) -> None:
        bodies = "\n".join(path.read_text() for path in (PROFILE, GATE, QA, REQUEST, STATE))
        self.assertNotIn('"default_workflow_active": true', bodies)
        self.assertNotIn('"retirement_active": true', bodies)
        self.assertNotIn('"active": true', PROFILE.read_text())
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
            self.assertNotIn(token, bodies)


if __name__ == "__main__":
    unittest.main()
