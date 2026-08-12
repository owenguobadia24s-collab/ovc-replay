from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills import (
    LocalToolBroker,
    build_tool_request,
    decide_tool_request,
    orch1_assisted_plan,
    resolve_security_envelope,
)

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "records/development/skills/DSAI_G8C_OPERATOR_ORCH1_ASSISTED_WRITE_PASS_20260812T164000+0100.json"
AUTHORITY = ROOT / "registries/development/skills/orch1_assisted_write_authority_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_20.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"
TRUSTED = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
G8C_ID = "DSAI-G8C.OPERATOR.PASS.ORCH1_ASSISTED_WRITE.20260812T164000+0100"
PACKET_EXECUTOR_RELEASE = "OVC-SKILL-030@0.1.0+sha256:62809d0f5f1d4298fa916766912d4bec7b5a8bf7712f7382d448137f6f12f130"


class DSAIG8COperatorAssistedWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        cls.trusted = json.loads(TRUSTED.read_text(encoding="utf-8"))

    def test_operator_pass_is_exact_one_authority_kind(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE DSAI-G8C")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_kind"], "ASSISTED_AGENT_WRITE")
        self.assertEqual(self.decision["authority_effect"], "BOUNDED_AGENT_SKILL_WRITE_AUTHORITY_NO_MERGE")
        activation = self.decision["activation"]
        self.assertEqual(activation["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertFalse(activation["direct_main_mutation"])
        self.assertFalse(activation["automatic_merge"])
        self.assertEqual(activation["merge_authority"], "NONE")

    def test_authority_registry_is_exact_allowlist_and_no_merge(self):
        self.assertTrue(self.authority["effective"])
        self.assertEqual(self.authority["source_decision_id"], G8C_ID)
        self.assertEqual(self.authority["packet_class_policy"], "EXACT_ALLOWLIST_ONLY")
        self.assertEqual(self.authority["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(self.authority["branch_scope"], "PACKET_BRANCH_ONLY")
        self.assertFalse(self.authority["direct_main_mutation"])
        self.assertFalse(self.authority["automatic_merge"])
        self.assertEqual(self.authority["merge_authority"], "NONE")
        self.assertEqual(self.authority["validation"], "DENIED")

    def test_orch1_only_enables_declared_low_risk_class(self):
        enabled = orch1_assisted_plan(packet_class="LOW_RISK_IMPLEMENTATION", enabled_packet_classes=self.authority["enabled_packet_classes"], g8c_authority_effective=True)
        self.assertEqual(enabled["status"], "ASSISTED_EXECUTION_ELIGIBLE")
        self.assertFalse(enabled["automatic_merge"])
        self.assertEqual(enabled["merge_authority"], "NONE")
        escaped = orch1_assisted_plan(packet_class="UNDECLARED_CLASS", enabled_packet_classes=self.authority["enabled_packet_classes"], g8c_authority_effective=True)
        self.assertEqual(escaped["status"], "BLOCKED")
        self.assertIn("PACKET_CLASS_NOT_ENABLED", escaped["reason_codes"])
        inactive = orch1_assisted_plan(packet_class="LOW_RISK_IMPLEMENTATION", enabled_packet_classes=self.authority["enabled_packet_classes"], g8c_authority_effective=False)
        self.assertEqual(inactive["status"], "BLOCKED")
        self.assertIn("DSAI_G8C_AUTHORITY_REQUIRED", inactive["reason_codes"])

    def test_assisted_write_requires_security_path_owner_and_g8c_binding(self):
        envelope = resolve_security_envelope(
            skill_id="ORCH-1-ASSISTED-AGENT",
            capability_ids=["PACKET_EXECUTION"],
            allowed_semantic_actions=["READ_FILE", "WRITE_FILE", "MERGE"],
            read_prefixes=["src/ovc/development/skills"],
            write_prefixes=["src/ovc/development/skills"],
            semantic_owners=["DSAI"],
            write_authority_active=True,
        )
        good_request = build_tool_request(action="WRITE_FILE", path="src/ovc/development/skills/pilot.py", semantic_owner="DSAI")
        good_security = decide_tool_request(envelope, good_request)
        self.assertEqual(good_security["decision"], "ALLOW")
        receipt = LocalToolBroker(active=True, assisted_write_active=True, assisted_write_authority_id=G8C_ID).dispatch(envelope=envelope, request=good_request)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["reason"], "ASSISTED_WRITE_AUTHORIZED")
        self.assertTrue(receipt["side_effect_authorized"])
        self.assertFalse(receipt["side_effect_performed"])
        self.assertEqual(receipt["merge_authority"], "NONE")

        bad_requests = [
            build_tool_request(action="WRITE_FILE", path=None, semantic_owner="DSAI"),
            build_tool_request(action="WRITE_FILE", path="src/ovc/development/skills/pilot.py", semantic_owner=None),
            build_tool_request(action="WRITE_FILE", path="registries/authority/pilot.json", semantic_owner="DSAI"),
            build_tool_request(action="MERGE", path="src/ovc/development/skills/pilot.py", semantic_owner="DSAI"),
        ]
        for request in bad_requests:
            with self.subTest(request=request):
                self.assertEqual(decide_tool_request(envelope, request)["decision"], "DENY")

    def test_g8c_preserves_packet_executor_trust_without_self_granting_new_trust(self):
        self.assertEqual(self.trusted["entry_count"], len(self.trusted["entries"]))
        self.assertGreaterEqual(self.trusted["entry_count"], 9)
        self.assertNotEqual(self.decision["authority_kind"], "TRUSTED_PROMOTION")
        packet_executor = [row for row in self.trusted["entries"] if row["skill_id"] == "OVC-SKILL-030"]
        self.assertEqual(len(packet_executor), 1)
        self.assertEqual(packet_executor[0]["release_id"], PACKET_EXECUTOR_RELEASE)
        self.assertEqual(packet_executor[0]["capability_id"], "PACKET_EXECUTION")
        self.assertEqual(packet_executor[0]["write_authority"], "NONE")
        self.assertEqual(packet_executor[0]["merge_authority"], "NONE")

    def test_programme_advances_to_orch1_pilot_but_wp9_remains_blocked(self):
        self.assertEqual(self.state["programme_status"], "G8C_PASS_ORCH1_ASSISTED_WRITE_ACTIVE_PILOT_PENDING")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP8"]["g8c_decision"], "PASS_OPERATOR_ASSISTED_WRITE")
        authority = self.state["authority"]
        self.assertEqual(authority["orch_1"], "ACTIVE_ASSISTED_WRITE_EXACT_LOW_RISK_CLASSES")
        self.assertEqual(authority["orch_1_enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(authority["merge_authority"], "NONE")
        self.assertEqual(authority["orch_2"], "INACTIVE_PENDING_DSAI_G9B")
        blockers = set(self.state["wp9_readiness"]["blockers"])
        self.assertIn("ORCH1_PILOT_EVIDENCE_REQUIRED", blockers)
        self.assertIn("GIT_MERGE_CAPABILITY_G9A_NOT_YET_TRUSTED", blockers)
        self.assertIn("DSAI_G9B_NOT_REACHED", blockers)

        self.assertEqual(self.pointer["programme_id"], "OVC-DSAI-v0.1")
        self.assertEqual(self.pointer["schema"], "ovc-programme-current-state-pointer/v1")
        self.assertTrue(str(self.pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_"))
        self.assertTrue(str(self.pointer["status"]).strip())
        self.assertTrue(str(self.pointer["next_packet"]).startswith("DSAI-WP"))


if __name__ == "__main__":
    unittest.main()
