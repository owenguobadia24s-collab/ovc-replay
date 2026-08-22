from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/development-acceleration-v0-1/da-wp4b"
GATE = BASE / "DA_G4B_GATE_PACKET.json"
REQUEST = BASE / "DA_G4B_OPERATOR_DECISION_REQUEST.json"
DECISION = BASE / "DA_G4B_OPERATOR_DECISION.json"
EVALUATION = BASE / "DA_G4B_ACTIVATION_EVALUATION.json"
RULESET = BASE / "main-ruleset.json"
STATE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
ACTIVE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_ACTIVE_PROFILE_v0_1.json"
RUNNER = ROOT / "scripts/development/run_da_receipt_bot.ps1"
EXPECTED_RULESET_SHA = "ed6fe8eb2c030fc185adbf70ae4571fca3fee2f3fbab8002267c8da2b221c0c4"
EXPECTED_EVALUATION_ID = "4815173d1ec559164072013f20d008f2d3a5b120841e8e6cb0350ee1f1164238"


class DevelopmentAccelerationG4BTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = json.loads(GATE.read_text())
        self.request = json.loads(REQUEST.read_text())
        self.decision = json.loads(DECISION.read_text())
        self.evaluation = json.loads(EVALUATION.read_text())
        self.state = json.loads(STATE.read_text())
        self.active = json.loads(ACTIVE.read_text())
        self.runner = RUNNER.read_text()

    def test_operator_pass_is_recorded_once_and_active(self) -> None:
        self.assertEqual(self.gate["gate_id"], "DA-G4B")
        self.assertEqual(self.gate["status"], "COMPLETED_READY_FOR_SQUASH_MERGE")
        self.assertEqual(self.request["status"], "DECIDED_PASS")
        self.assertEqual(self.request["recorded_decision"], "PASS")
        self.assertEqual(self.decision["decision_id"], "DA-G4B.OPERATOR.PASS.20260802T163600Z")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertTrue(self.decision["authority_active"])
        self.assertFalse(self.decision["merge_authority_granted_to_bot"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertTrue(self.state["activation_gate"]["authority_active"])

    def test_active_profile_binds_all_external_evidence(self) -> None:
        self.assertTrue(self.active["active"])
        self.assertEqual(self.active["status"], "ACTIVE")
        self.assertEqual(self.active["profile_id"], "OVC.DEVELOPMENT.ACCELERATION.RECEIPT-BOT.v0.1")
        self.assertEqual(self.active["branch_protection_evidence_hash"], EXPECTED_RULESET_SHA)
        self.assertEqual(self.active["proposal_shadow_evidence_hash"], "3d21a03d1772491da6cd1722712a816abd200b1f7f69fa76548ffa3b6a6476ea")
        self.assertEqual(self.active["activation_evaluation_id"], EXPECTED_EVALUATION_ID)
        self.assertEqual(self.evaluation["evaluation_id"], EXPECTED_EVALUATION_ID)
        self.assertEqual(self.evaluation["status"], "PASS")
        self.assertTrue(self.evaluation["authority_active"])

    def test_ruleset_and_shadow_evidence_remain_exact(self) -> None:
        self.assertEqual(hashlib.sha256(RULESET.read_bytes()).hexdigest(), EXPECTED_RULESET_SHA)
        ruleset = json.loads(RULESET.read_bytes())
        self.assertEqual(ruleset["enforcement"], "active")
        self.assertIn("refs/heads/main", ruleset["conditions"]["ref_name"]["include"])
        self.assertEqual(ruleset["bypass_actors"], [])
        self.assertEqual(ruleset["current_user_can_bypass"], "never")
        self.assertEqual(self.state["activation_gate"]["shadow_pull_request"], 211)
        self.assertEqual(self.state["activation_gate"]["shadow_status"], "PASS_OPEN_UNMERGED")

    def test_delta_is_narrow_and_denials_are_permanent(self) -> None:
        delta = self.gate["approved_authority_delta"]
        self.assertEqual(delta["allowed_actions"], ["CREATE_BOT_BRANCH", "CREATE_OR_UPDATE_ALLOWLISTED_FILES", "OPEN_OR_UPDATE_PULL_REQUEST"])
        self.assertEqual(delta["allowed_branches"], ["bot/ovc-dev-accel-receipts/*"])
        denied = set(delta["permanent_denials"])
        for token in (
            "WRITE_MAIN", "MERGE_PULL_REQUEST", "APPROVE_PULL_REQUEST", "FORCE_PUSH",
            "REWRITE_HISTORY", "MODIFY_AUTHORITY_PROFILE", "PROVIDER_ACCESS", "R2_WRITE",
            "VALIDATION_ACCESS", "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
        ):
            self.assertIn(token, denied)
        self.assertEqual(self.state["authority"]["direct_main_write"], "PROHIBITED")
        self.assertEqual(self.state["authority"]["merge_pull_request"], "PROHIBITED_TO_BOT")

    def test_transport_is_fail_closed_and_has_no_merge_surface(self) -> None:
        for token in (
            "IDEMPOTENCY_COLLISION", "STALE_MAIN_SHA", "PATH_NOT_ALLOWED",
            "bot/ovc-dev-accel-receipts/*", "DA-G4B.OPERATOR.PASS.20260802T163600Z",
            "merge_performed = $false", "approval_performed = $false",
            "force_push_performed = $false", "history_rewrite_performed = $false",
        ):
            self.assertIn(token, self.runner)
        self.assertIsNone(re.search(r"/merges(?:\?|\"|'|$)|/reviews(?:\?|\"|'|$)|git\s+(?:push|merge|reset)", self.runner, re.I))
        self.assertNotIn("DELETE", self.runner)
        self.assertNotIn("force = $true", self.runner)

    def test_active_transport_publishes_detached_exact_head_qualification_before_pr_creation(self) -> None:
        for token in (
            "build_vit_planned_lineage.py",
            "build_vit_pr_lineage.py",
            "VIT_LINEAGE_BUILD_FAILED",
            "VIT_RESULT_TREE_MISMATCH",
            "--publish-detached",
            "VIT-Qualification-ID:",
            "vit_route = \"VIT_MANDATORY\"",
            "vit_qualification_source = \"DETACHED_QUALIFICATION_LEDGER\"",
            "vit_physical_placement_binding = \"LATE_BOUND\"",
            "vit_lineage_attached_to_pr = $false",
        ):
            self.assertIn(token, self.runner)
        self.assertNotIn("VIT-Lineage-B64:", self.runner)
        self.assertLess(self.runner.index("--publish-detached"), self.runner.index("/pulls?state=open"))
        self.assertLess(self.runner.index("VIT_RESULT_TREE_MISMATCH"), self.runner.index("--publish-detached"))
        self.assertLess(self.runner.index("--publish-detached"), self.runner.index("$prBody ="))

    def test_no_credentials_are_committed(self) -> None:
        bodies = "\n".join(path.read_text() for path in (GATE, REQUEST, DECISION, EVALUATION, STATE, ACTIVE))
        for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
            self.assertNotIn(token, bodies)


if __name__ == "__main__":
    unittest.main()