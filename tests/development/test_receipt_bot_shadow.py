from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.receipt_bot import ReceiptBotError, evaluate_work_packet, load_policy, load_work_packet
from ovc.development.receipt_bot_shadow import (
    RecordingShadowProposalAdapter,
    ReceiptBotShadowIdentity,
    evaluate_shadow_readiness,
    execute_pre_activation_shadow,
    parse_shadow_identity,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json"
WORK_PACKET = ROOT / "fixtures/development/receipt_bot/work_packet_shadow_v0_1.json"
PAYLOAD = ROOT / "fixtures/development/receipt_bot/shadow_receipt_payload_v0_1.json"
TARGET_PATH = "docs/releases/development-acceleration-v0-1/da-wp4b-shadow/DA_G4B_SHADOW_RECEIPT.json"


class ReceiptBotShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(POLICY)
        self.packet = load_work_packet(WORK_PACKET)
        self.plan = evaluate_work_packet(self.packet, self.policy)
        self.identity = ReceiptBotShadowIdentity(
            app_id=12345,
            installation_id=67890,
            app_slug="ovc-dev-accel-receipt-bot",
            repository="owenguobadia24s-collab/ovc-replay",
            credential_kind="GITHUB_APP_INSTALLATION_TOKEN",
            revocable=True,
            operator_connector=False,
            permissions={
                "contents": "write",
                "pull_requests": "write",
                "metadata": "read",
            },
        )
        self.pre_shadow_evidence = {
            condition: "PASS"
            for condition in self.policy.required_activation_conditions
            if condition not in {"REAL_PROPOSAL_BRANCH_SHADOW_PASS", "QA_PASS"}
        }

    def test_shadow_readiness_breaks_activation_cycle_without_activating_authority(self) -> None:
        readiness = evaluate_shadow_readiness(self.pre_shadow_evidence, self.policy)
        self.assertEqual(readiness["status"], "PASS")
        self.assertTrue(readiness["shadow_execution_authorized"])
        self.assertFalse(readiness["authority_active"])
        self.assertEqual(
            readiness["post_shadow_conditions"],
            ["QA_PASS", "REAL_PROPOSAL_BRANCH_SHADOW_PASS"],
        )

    def test_shadow_readiness_requires_branch_protection(self) -> None:
        evidence = dict(self.pre_shadow_evidence)
        evidence["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] = "BLOCKED"
        readiness = evaluate_shadow_readiness(evidence, self.policy)
        self.assertEqual(readiness["status"], "BLOCK")
        self.assertFalse(readiness["shadow_execution_authorized"])
        self.assertIn(
            "NOT_PASS:MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
            readiness["blockers"],
        )

    def test_shadow_identity_is_exact_minimum_and_operator_connector_is_denied(self) -> None:
        parsed = parse_shadow_identity(self.identity.to_dict())
        self.assertTrue(parsed.revocable)
        self.assertFalse(parsed.operator_connector)
        self.assertEqual(parsed.permissions["contents"], "write")

        raw = self.identity.to_dict()
        raw["operator_connector"] = True
        with self.assertRaises(ReceiptBotError):
            parse_shadow_identity(raw)

        raw = self.identity.to_dict()
        raw["permissions"] = {**raw["permissions"], "administration": "write"}
        with self.assertRaises(ReceiptBotError):
            parse_shadow_identity(raw)

    def test_pre_activation_shadow_executes_only_three_actions_and_stays_inactive(self) -> None:
        self.assertEqual(self.plan["status"], "PASS")
        readiness = evaluate_shadow_readiness(self.pre_shadow_evidence, self.policy)
        adapter = RecordingShadowProposalAdapter()
        audit = execute_pre_activation_shadow(
            self.plan,
            adapter,
            shadow_readiness=readiness,
            identity=self.identity,
            content_by_path={TARGET_PATH: PAYLOAD.read_bytes()},
        )
        self.assertEqual(
            [row["action"] for row in adapter.calls],
            [
                "CREATE_BOT_BRANCH",
                "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
                "OPEN_OR_UPDATE_PULL_REQUEST",
            ],
        )
        self.assertEqual(audit["mode"], "PRE_ACTIVATION_SHADOW")
        self.assertEqual(audit["shadow_result"], "PASS")
        self.assertFalse(audit["authority_active"])
        self.assertFalse(audit["production_transport_active"])
        self.assertFalse(audit["merge_performed"])
        self.assertFalse(audit["approval_performed"])
        self.assertFalse(audit["force_push_performed"])
        audit_text = json.dumps(audit, sort_keys=True)
        self.assertNotIn("ovc-da-g4b-shadow-receipt", audit_text)
        self.assertNotIn("APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE", audit_text)

    def test_shadow_rejects_content_hash_mismatch_and_non_shadow_path(self) -> None:
        readiness = evaluate_shadow_readiness(self.pre_shadow_evidence, self.policy)
        with self.assertRaises(ReceiptBotError):
            execute_pre_activation_shadow(
                self.plan,
                RecordingShadowProposalAdapter(),
                shadow_readiness=readiness,
                identity=self.identity,
                content_by_path={TARGET_PATH: b"wrong"},
            )

        raw = json.loads(WORK_PACKET.read_text(encoding="utf-8"))
        raw["target_files"][0]["path"] = "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
        from ovc.development.receipt_bot import parse_work_packet

        plan = evaluate_work_packet(parse_work_packet(raw), self.policy)
        with self.assertRaises(ReceiptBotError):
            execute_pre_activation_shadow(
                plan,
                RecordingShadowProposalAdapter(),
                shadow_readiness=readiness,
                identity=self.identity,
                content_by_path={raw["target_files"][0]["path"]: PAYLOAD.read_bytes()},
            )

    def test_shadow_adapter_exposes_no_reserved_methods(self) -> None:
        adapter = RecordingShadowProposalAdapter()
        self.assertFalse(hasattr(adapter, "merge_pull_request"))
        self.assertFalse(hasattr(adapter, "approve_pull_request"))
        self.assertFalse(hasattr(adapter, "force_push"))
        self.assertFalse(hasattr(adapter, "delete_branch"))


if __name__ == "__main__":
    unittest.main()
