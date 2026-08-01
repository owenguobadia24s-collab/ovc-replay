from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_PROPOSAL_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/development/repository_bot_authority_profile_v0_1.schema.json"
GATE_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_GATE_PACKET.json"
QA_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_QA_PACKET.json"
DECISION_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION_REQUEST.json"
CONTRACT_PATH = ROOT / "contracts/development/OVC_REPOSITORY_RECEIPT_BOT_AUTHORITY_PROPOSAL_v0_1.md"
STATE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"


class RepositoryBotGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
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
        self.assertEqual(self.profile["gate_id"], "DA-G4")
        self.assertEqual(self.state["authority"]["repository_bot_write"], "DENIED_PENDING_DA_G4")
        self.assertFalse(self.state["operator_gate"]["authority_active"])

    def test_allowlist_is_exact_and_minimal(self) -> None:
        self.assertEqual(self.profile["base_branch"], "main")
        self.assertEqual(self.profile["branch_patterns"], ["bot/ovc-dev-accel-receipts/*"])
        self.assertEqual(
            self.profile["allowed_paths"],
            [
                "docs/releases/development-acceleration-v0-1/**",
                "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
                "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
            ],
        )
        self.assertEqual(
            self.profile["allowed_actions"],
            ["CREATE_BOT_BRANCH", "CREATE_OR_UPDATE_ALLOWLISTED_FILES", "OPEN_OR_UPDATE_PULL_REQUEST"],
        )
        self.assertEqual(self.profile["allowed_paths"], self.schema["properties"]["allowed_paths"]["const"])
        self.assertEqual(self.profile["allowed_actions"], self.schema["properties"]["allowed_actions"]["const"])

    def test_merge_main_self_modification_and_market_authority_are_denied(self) -> None:
        denied = set(self.profile["denied_actions"])
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
        self.assertEqual(self.profile["self_modification"], "DENIED")
        current = self.gate["current_authority"]
        self.assertEqual(current["repository_bot_write"], "DENIED")
        self.assertEqual(current["direct_main_write"], "PROHIBITED")
        self.assertEqual(current["market_authority"], "NONE")
        self.assertEqual(current["probability_risk_exposure_execution_authority"], "NONE")

    def test_activation_requires_branch_protection_shadow_and_final_assurance(self) -> None:
        conditions = set(self.profile["activation_conditions"])
        self.assertIn("MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED", conditions)
        self.assertIn("REAL_PROPOSAL_BRANCH_SHADOW_PASS", conditions)
        self.assertIn("FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS", conditions)
        self.assertIn("DENIED_ACTION_TESTS_PASS", conditions)
        self.assertIn("TOKEN_REDACTION_TESTS_PASS", conditions)
        self.assertIn("REVOCATION_TESTS_PASS", conditions)
        self.assertEqual(self.gate["proposed_authority_delta"]["current_status"], "PENDING_OPERATOR_NOT_ACTIVE")
        self.assertEqual(self.qa["activation_state_after_operator_pass"], "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE")
        self.assertEqual(self.decision["effect_of_pass"], "Approve the exact profile for bounded implementation but keep active=false until every implementation and activation condition passes.")

    def test_revocation_is_independent_and_non_destructive(self) -> None:
        revocation = self.profile["revocation"]
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
            for path in (PROFILE_PATH, SCHEMA_PATH, GATE_PATH, QA_PATH, DECISION_PATH, CONTRACT_PATH, STATE_PATH)
        )
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
            self.assertNotIn(token, bodies)
        self.assertNotIn('"active": true', bodies)
        self.assertEqual(self.profile["credential_storage"], "PROHIBITED_IN_REPOSITORY_RECORDS_FIXTURES_AND_LOGS")

    def test_decision_request_is_single_consolidated_operator_gate(self) -> None:
        self.assertEqual(self.decision["status"], "PENDING_OPERATOR")
        self.assertEqual(self.decision["current_authority"], "REPOSITORY_BOT_WRITE_DENIED")
        self.assertEqual(self.decision["requested_decision"], "PASS")
        self.assertEqual(
            self.decision["allowed_decisions"],
            ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
        )
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE DA-G4 PASS")
        self.assertIsNone(self.decision["decision_record"])
        self.assertFalse(self.decision["authority_active"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["current_gate"], "DA-G4")


if __name__ == "__main__":
    unittest.main()
