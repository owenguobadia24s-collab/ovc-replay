from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_PROPOSAL_v0_1.json"
APPROVED_PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_APPROVED_PROFILE_v0_1.json"
ACTIVE_PROFILE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_ACTIVE_PROFILE_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/development/repository_bot_authority_profile_v0_1.schema.json"
GATE_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_GATE_PACKET.json"
QA_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_QA_PACKET.json"
REQUEST_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION_REQUEST.json"
DECISION_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION.json"
ACTIVATION_DECISION_PATH = ROOT / "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_OPERATOR_DECISION.json"
STATE_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"


class RepositoryBotGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads(PROFILE_PATH.read_text())
        self.approved = json.loads(APPROVED_PROFILE_PATH.read_text())
        self.active = json.loads(ACTIVE_PROFILE_PATH.read_text())
        self.schema = json.loads(SCHEMA_PATH.read_text())
        self.gate = json.loads(GATE_PATH.read_text())
        self.qa = json.loads(QA_PATH.read_text())
        self.request = json.loads(REQUEST_PATH.read_text())
        self.decision = json.loads(DECISION_PATH.read_text())
        self.activation_decision = json.loads(ACTIVATION_DECISION_PATH.read_text())
        self.state = json.loads(STATE_PATH.read_text())

    def test_da_g4_records_remain_historical_and_inactive(self) -> None:
        self.assertEqual(self.schema["properties"]["status"]["const"], "PENDING_OPERATOR_DA_G4")
        self.assertFalse(self.schema["properties"]["active"]["const"])
        self.assertEqual(self.profile["status"], "PENDING_OPERATOR_DA_G4")
        self.assertFalse(self.profile["active"])
        self.assertEqual(self.approved["status"], "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE")
        self.assertFalse(self.approved["active"])
        self.assertTrue(self.approved["implementation_authorized"])
        self.assertEqual(self.approved["gate_id"], "DA-G4")
        self.assertFalse(self.state["operator_gate"]["authority_active"])

    def test_allowlist_is_unchanged_by_activation(self) -> None:
        paths = [
            "docs/releases/development-acceleration-v0-1/**",
            "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
            "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
        ]
        actions = ["CREATE_BOT_BRANCH", "CREATE_OR_UPDATE_ALLOWLISTED_FILES", "OPEN_OR_UPDATE_PULL_REQUEST"]
        self.assertEqual(self.profile["allowed_paths"], paths)
        self.assertEqual(self.profile["allowed_actions"], actions)
        self.assertEqual(self.approved["allowed_paths"], paths)
        self.assertEqual(self.approved["allowed_actions_after_activation_only"], actions)
        self.assertEqual(self.activation_decision["allowed_paths"], paths)
        self.assertEqual(self.activation_decision["allowed_actions"], actions)

    def test_permanent_denials_survive_activation(self) -> None:
        required = {
            "WRITE_MAIN", "WRITE_NON_BOT_BRANCH", "MERGE_PULL_REQUEST", "APPROVE_PULL_REQUEST",
            "DISMISS_REVIEW", "FORCE_PUSH", "REWRITE_HISTORY", "MODIFY_WORKFLOW",
            "MODIFY_SOURCE_CODE", "MODIFY_AUTHORITY_PROFILE", "SELF_APPROVE", "PROVIDER_ACCESS",
            "R2_WRITE", "RELEASE_PUBLICATION", "SELECTOR_MUTATION", "VALIDATION_ACCESS",
            "MARKET_OR_SEMANTIC_MUTATION", "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
        }
        self.assertTrue(required.issubset(set(self.profile["denied_actions"])))
        self.assertTrue(required.issubset(set(self.approved["permanent_denials"])))
        self.assertTrue(required.issubset(set(self.activation_decision["permanent_denials"])))
        self.assertEqual(self.state["authority"]["direct_main_write"], "PROHIBITED")
        self.assertEqual(self.state["authority"]["merge_pull_request"], "PROHIBITED_TO_BOT")

    def test_da_g4b_is_separate_operator_activation(self) -> None:
        self.assertEqual(self.request["status"], "DECIDED_PASS")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertTrue(self.decision["implementation_authorized"])
        self.assertFalse(self.decision["authority_active"])
        self.assertEqual(self.activation_decision["decision"], "PASS")
        self.assertEqual(self.activation_decision["decision_authority"], "OPERATOR")
        self.assertTrue(self.activation_decision["authority_active"])
        self.assertFalse(self.activation_decision["merge_authority_granted_to_bot"])
        self.assertTrue(self.active["active"])
        self.assertEqual(self.active["status"], "ACTIVE")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["activation_gate"]["status"], "APPROVED")
        self.assertTrue(self.state["activation_gate"]["authority_active"])

    def test_no_repository_credentials_materialized(self) -> None:
        bodies = "\n".join(path.read_text() for path in (
            PROFILE_PATH, APPROVED_PROFILE_PATH, ACTIVE_PROFILE_PATH, SCHEMA_PATH,
            GATE_PATH, QA_PATH, REQUEST_PATH, DECISION_PATH, ACTIVATION_DECISION_PATH, STATE_PATH,
        ))
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
            self.assertNotIn(token, bodies)
        self.assertEqual(self.profile["credential_storage"], "PROHIBITED_IN_REPOSITORY_RECORDS_FIXTURES_AND_LOGS")


if __name__ == "__main__":
    unittest.main()
