from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.development.receipt_bot import (
    ReceiptBotError,
    RecordingProposalAdapter,
    evaluate_activation,
    evaluate_work_packet,
    execute_plan,
    load_policy,
    load_work_packet,
    parse_work_packet,
    redact_secrets,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json"
PASS_PACKET = ROOT / "fixtures/development/receipt_bot/work_packet_pass_v0_1.json"
BLOCK_PACKET = ROOT / "fixtures/development/receipt_bot/work_packet_block_v0_1.json"


class ReceiptBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(POLICY)
        self.packet = load_work_packet(PASS_PACKET)

    def test_policy_is_exact_and_inactive(self) -> None:
        self.assertFalse(self.policy.active)
        self.assertEqual(self.policy.base_branch, "main")
        self.assertEqual(self.policy.branch_patterns, ("bot/ovc-dev-accel-receipts/*",))
        self.assertEqual(
            self.policy.allowed_actions,
            (
                "CREATE_BOT_BRANCH",
                "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
                "OPEN_OR_UPDATE_PULL_REQUEST",
            ),
        )
        self.assertIn("MERGE_PULL_REQUEST", self.policy.denied_actions)
        self.assertIn("WRITE_MAIN", self.policy.denied_actions)
        self.assertIn("MODIFY_AUTHORITY_PROFILE", self.policy.denied_actions)
        self.assertIn("MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED", self.policy.required_activation_conditions)
        self.assertIn("REAL_PROPOSAL_BRANCH_SHADOW_PASS", self.policy.required_activation_conditions)

    def test_pass_plan_is_deterministic_and_no_write(self) -> None:
        first = evaluate_work_packet(self.packet, self.policy)
        second = evaluate_work_packet(self.packet, self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["blockers"], [])
        self.assertFalse(first["authority"]["active"])
        self.assertFalse(first["authority"]["writes_performed"])
        self.assertFalse(first["authority"]["merge_api_available"])
        actions = [row["action"] for row in first["actions"]]
        self.assertEqual(actions[0], "CREATE_BOT_BRANCH")
        self.assertEqual(actions[-1], "OPEN_OR_UPDATE_PULL_REQUEST")
        self.assertNotIn("MERGE_PULL_REQUEST", actions)
        self.assertNotIn("APPROVE_PULL_REQUEST", actions)

    def test_block_fixture_surfaces_all_material_failures(self) -> None:
        blocked = evaluate_work_packet(load_work_packet(BLOCK_PACKET), self.policy)
        self.assertEqual(blocked["status"], "BLOCK")
        expected = {
            "STALE_MAIN_SHA",
            "BRANCH_NOT_ALLOWED",
            "PATH_NOT_ALLOWED:src/ovc/development/receipt_bot.py",
            "CLOSURE_NOT_PASS",
            "QA_NOT_PASS",
            "DECISION_NOT_PASS",
            "RESERVED_AUTHORITY_DELTA",
            "BLOCKERS_PRESENT",
            "WARNINGS_PRESENT",
            "UNRESOLVED_REVIEWS_PRESENT",
            "DESTRUCTIVE_ROLLBACK",
        }
        self.assertTrue(expected.issubset(set(blocked["blockers"])))

    def test_wrong_profile_and_main_branch_block(self) -> None:
        raw = json.loads(PASS_PACKET.read_text(encoding="utf-8"))
        raw["profile_hash"] = "f" * 64
        raw["branch"] = "main"
        result = evaluate_work_packet(parse_work_packet(raw), self.policy)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("APPROVED_PROFILE_IDENTITY_MISMATCH", result["blockers"])
        self.assertIn("BRANCH_NOT_ALLOWED", result["blockers"])

    def test_path_traversal_and_duplicate_paths_fail_parsing(self) -> None:
        raw = json.loads(PASS_PACKET.read_text(encoding="utf-8"))
        raw["target_files"][0]["path"] = "../escape.json"
        with self.assertRaises(ReceiptBotError):
            parse_work_packet(raw)

        raw = json.loads(PASS_PACKET.read_text(encoding="utf-8"))
        raw["target_files"].append(copy.deepcopy(raw["target_files"][0]))
        with self.assertRaises(ReceiptBotError):
            parse_work_packet(raw)

    def test_idempotent_retry_and_collision(self) -> None:
        first = evaluate_work_packet(self.packet, self.policy)
        retry = evaluate_work_packet(
            self.packet,
            self.policy,
            idempotency_ledger={self.packet.idempotency_key: first["plan_id"]},
        )
        self.assertEqual(retry["status"], "PASS")
        self.assertEqual(retry["idempotency_status"], "IDEMPOTENT_RETRY")

        collision = evaluate_work_packet(
            self.packet,
            self.policy,
            idempotency_ledger={self.packet.idempotency_key: "0" * 64},
        )
        self.assertEqual(collision["status"], "BLOCK")
        self.assertEqual(collision["idempotency_status"], "COLLISION")
        self.assertIn("IDEMPOTENCY_COLLISION", collision["blockers"])

    def test_secret_redaction_is_recursive(self) -> None:
        token_a = "gh" + "p_" + "A" * 20
        token_b = "github" + "_pat_" + "B" * 20
        token_c = "sk" + "-proj-" + "C" * 20
        value = {
            "a": token_a,
            "nested": [f"Bearer {token_b}", {"key": token_c}],
        }
        redacted = redact_secrets(value)
        text = json.dumps(redacted, sort_keys=True)
        self.assertNotIn(token_a, text)
        self.assertNotIn(token_b, text)
        self.assertNotIn(token_c, text)
        self.assertIn("[REDACTED]", text)

    def test_activation_blocks_missing_external_evidence(self) -> None:
        evidence = {condition: "PASS" for condition in self.policy.required_activation_conditions}
        evidence["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] = "PENDING"
        evidence["REAL_PROPOSAL_BRANCH_SHADOW_PASS"] = "PENDING"
        evaluation = evaluate_activation(evidence, self.policy)
        self.assertEqual(evaluation["status"], "BLOCK")
        self.assertFalse(evaluation["authority_active"])
        self.assertIn(
            "NOT_PASS:MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
            evaluation["blockers"],
        )
        self.assertIn("NOT_PASS:REAL_PROPOSAL_BRANCH_SHADOW_PASS", evaluation["blockers"])

    def test_inactive_activation_cannot_drive_adapter(self) -> None:
        plan = evaluate_work_packet(self.packet, self.policy)
        evidence = {condition: "PASS" for condition in self.policy.required_activation_conditions}
        evidence["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] = "PENDING"
        activation = evaluate_activation(evidence, self.policy)
        adapter = RecordingProposalAdapter()
        with self.assertRaises(ReceiptBotError):
            execute_plan(plan, adapter, activation_evaluation=activation)
        self.assertEqual(adapter.calls, [])

    def test_recording_adapter_exposes_no_merge_or_approval_method(self) -> None:
        adapter = RecordingProposalAdapter()
        self.assertFalse(hasattr(adapter, "merge_pull_request"))
        self.assertFalse(hasattr(adapter, "approve_pull_request"))
        self.assertFalse(hasattr(adapter, "force_push"))
        self.assertFalse(hasattr(adapter, "delete_branch"))


if __name__ == "__main__":
    unittest.main()
