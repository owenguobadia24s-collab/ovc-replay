from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_PROPOSAL_v0_1.json"
APPROVED_PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_APPROVED_PROFILE_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/development/repository_bot_authority_profile_v0_1.schema.json"
GATE_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_GATE_PACKET.json"
QA_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_QA_PACKET.json"
REQUEST_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION_REQUEST.json"
DECISION_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION.json"
CONTRACT_PATH = ROOT / "contracts/development/OVC_REPOSITORY_RECEIPT_BOT_AUTHORITY_PROPOSAL_v0_1.md"
STATE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"


class RepositoryBotGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        self.approved = json.loads(APPROVED_PROFILE_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
        self.request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
        self.decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
        self.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def test_profile_is_closed_inactive_and_operator_reserved(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["type"], "object")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.schema["properties"]["status"]["const"], "PENDING_OPERATOR_DA_G4")
        self.assertFalse(self.schema["properties"]["active"]["const"])
        self.assertEqual(self.profile["status"], "PENDING_OPERATOR_DA_G4")
        self.assertFalse(self.profile["active"])
        self.assertEqual(self.approved["status"], "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE")
        self.assertFalse(self.approved["active"])
        self.assertTrue(self.approved["implementation_authorized"])
        self.assertEqual(self.approved["gate_id"], "DA-G4")
        self.assertEqual(
            self.state["authority"]["repository_bot_write"],
            "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        )
        self.assertFalse(self.state["operator_gate"]["authority_active"])

    def test_allowlist_is_exact_and_minimal(self) -> None:
        expected_paths = [
            "docs/releases/development-acceleration-v0-1/**",
            "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
            "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
        ]
        expected_actions = ["CREATE_BOT_BRANCH", "CREATE_OR_UPDATE_ALLOWLISTED_FILES", "OPEN_OR_UPDATE_PULL_REQUEST"]
        self.assertEqual(self.profile["base_branch"], "main")
        self.assertEqual(self.profile["branch_patterns"], ["bot/ovc-dev-accel-receipts/*"])
        self.assertEqual(self.profile["allowed_paths"], expected_paths)
        self.assertEqual(self.profile["allowed_actions"], expected_actions)
        self.assertEqual(self.profile["allowed_paths"], self.schema["properties"]["allowed_paths"]["const"])
        self.assertEqual(self.profile["allowed_actions"], self.schema["properties"]["allowed_actions"]["const"])
        self.assertEqual(self.approved["allowed_paths"], expected_paths)
        self.assertEqual(self.approved["allowed_actions_after_activation_only"], expected_actions)

    def test_merge_main_self_modification_and_market_authority_are_denied(self) -> None:
        denied = set(self.profile["denied_actions"])
        approved_denied = set(self.approved["permanent_denials"])
        required = {
            "WRITE_MAIN",
            "WRITE_NON_BOT_BRANCH",
            "MERGE_PULL_REQUEST",
            "APPROVE_PULL_REQUEST",
            "DISMISS_REVIEW",
            "FORCE_PUSH",
            "REWRITE_HISTORY",
            "MODIFY_WORKFLOW",
            "MODIFY_SOURCE_CODE",
            "MODIFY_AUTHORITY_PROFILE",
            "SELF_APPROVE",
            "PROVIDER_ACCESS",
            "R2_WRITE",
            "RELEASE_PUBLICATION",
            "SELECTOR_MUTATION",
            "VALIDATION_ACCESS",
            "MARKET_OR_SEMANTIC_MUTATION",
            "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
        }
        self.assertTrue(required.issubset(denied))
        self.assertTrue(required.issubset(approved_denied))
        self.assertEqual(self.profile["self_modification"], "DENIED")
        current = self.gate["current_authority"]
        self.assertEqual(current["repository_bot_write"], "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE")
        self.assertEqual(current["direct_main_write"], "PROHIBITED")
        self.assertEqual(current["market_authority"], "NONE")
        self.assertEqual(current["probability_risk_exposure_execution_authority"], "NONE")

    def test_activation_requires_branch_protection_shadow_and_final_assurance(self) -> None:
        conditions = set(self.profile["activation_conditions"])
        approved_conditions = set(self.approved["activation_conditions"])
        for token in (
            "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
            "REAL_PROPOSAL_BRANCH_SHADOW_PASS",
            "FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS",
            "DENIED_ACTION_TESTS_PASS",
            "TOKEN_REDACTION_TESTS_PASS",
            "REVOCATION_TESTS_PASS",
        ):
            self.assertIn(token, conditions)
            self.assertIn(token, approved_conditions)
        self.assertEqual(
            self.gate["approved_authority_delta"]["current_status"],
            "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        )
        self.assertEqual(
            self.qa["current_repository_bot_write"],
            "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        )
        self.assertEqual(
            self.request["effect_of_pass"],
            "Approve the exact profile for bounded implementation but keep active=false until every implementation and activation condition passes.",
        )
        self.assertFalse(self.decision["authority_active"])

    def test_revocation_is_independent_and_non_destructive(self) -> None:
        for revocation in (self.profile["revocation"], self.approved["revocation"]):
            self.assertEqual(revocation["profile_disable"], "REQUIRED")
            self.assertEqual(revocation["credential_revoke"], "REQUIRED")
            self.assertEqual(revocation["history_rewrite"], "PROHIBITED")
            self.assertEqual(revocation["accepted_record_deletion"], "PROHIBITED")
        rollback = self.gate["rollback"]
        self.assertIn("revoke the dedicated identity", rollback["after_approved_implementation"])
        self.assertIn("no deletion or history rewrite", rollback["preservation"])

    def test_no_credentials_or_active_authority_are_materialized(self) -> None:
        bodies = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                PROFILE_PATH,
                APPROVED_PROFILE_PATH,
                SCHEMA_PATH,
                GATE_PATH,
                QA_PATH,
                REQUEST_PATH,
                DECISION_PATH,
                CONTRACT_PATH,
                STATE_PATH,
            )
        )
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
            self.assertNotIn(token, bodies)
        self.assertNotIn('"active": true', bodies)
        self.assertEqual(self.profile["credential_storage"], "PROHIBITED_IN_REPOSITORY_RECORDS_FIXTURES_AND_LOGS")
        self.assertEqual(self.approved["credential_state"], "NOT_PROVISIONED")
        self.assertEqual(self.approved["writer_adapter_state"], "NOT_IMPLEMENTED")

    def test_decision_request_is_single_consolidated_operator_gate(self) -> None:
        self.assertEqual(self.request["status"], "DECIDED_PASS")
        self.assertEqual(
            self.request["current_authority"],
            "REPOSITORY_BOT_WRITE_APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        )
        self.assertEqual(self.request["requested_decision"], "PASS")
        self.assertEqual(self.request["allowed_decisions"], ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"])
        self.assertEqual(self.request["operator_command"], "OVC APPROVE DA-G4 PASS")
        self.assertEqual(
            self.request["decision_record"],
            "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION.json",
        )
        self.assertFalse(self.request["authority_active"])
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertTrue(self.decision["implementation_authorized"])
        self.assertFalse(self.decision["authority_active"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["current_gate"], "DA-G4")
        self.assertEqual(self.state["next_action"], "SQUASH_MERGE_PR_208_THEN_BEGIN_DA_WP4B")


if __name__ == "__main__":
    unittest.main()
