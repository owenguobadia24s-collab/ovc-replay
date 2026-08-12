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
PILOT = ROOT / "records/development/skills/DSAI_WP8_ORCH1_PILOT_RUN_20260812T172700+0100.json"
PAYLOAD = ROOT / "fixtures/development/skills/orch1_low_risk_pilot_v0_1.json"
AUTHORITY = ROOT / "registries/development/skills/orch1_assisted_write_authority_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_20.json"
G8C_ID = "DSAI-G8C.OPERATOR.PASS.ORCH1_ASSISTED_WRITE.20260812T164000+0100"
BRANCH = "pilot/dsai-wp8-orch1-low-risk-implementation"
BASELINE = "3057d42e8a228a862dc37bddfa0e462d64bfe72f"


class DSAIWP8ORCH1PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = json.loads(PILOT.read_text(encoding="utf-8"))
        cls.payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
        cls.authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def _envelope(self):
        return resolve_security_envelope(
            skill_id="ORCH-1-ASSISTED-AGENT",
            capability_ids=["PACKET_EXECUTION"],
            allowed_semantic_actions=self.pilot["required_semantic_actions"],
            read_prefixes=[],
            write_prefixes=self.pilot["write_domain"]["exact_prefixes"],
            semantic_owners=self.pilot["write_domain"]["semantic_owners"],
            write_authority_active=True,
        )

    def test_pilot_is_exact_low_risk_class_on_packet_branch(self):
        self.assertEqual(self.pilot["packet_class"], "LOW_RISK_IMPLEMENTATION")
        self.assertEqual(self.pilot["packet_branch"], BRANCH)
        self.assertNotEqual(self.pilot["packet_branch"], "main")
        self.assertEqual(self.pilot["baseline_main"], BASELINE)
        self.assertFalse(self.pilot["direct_main_mutation"])
        self.assertFalse(self.pilot["automatic_merge"])
        self.assertEqual(self.pilot["merge_authority"], "NONE")
        self.assertTrue(self.pilot["stop_before_merge"])
        self.assertEqual(self.pilot["authority_effect"], "NONE")

    def test_g8c_authority_makes_exact_class_eligible_only(self):
        enabled = orch1_assisted_plan(
            packet_class=self.pilot["packet_class"],
            enabled_packet_classes=self.authority["enabled_packet_classes"],
            g8c_authority_effective=self.authority["effective"],
        )
        self.assertEqual(enabled["status"], "ASSISTED_EXECUTION_ELIGIBLE")
        self.assertFalse(enabled["automatic_merge"])
        self.assertEqual(enabled["merge_authority"], "NONE")
        escaped = orch1_assisted_plan(
            packet_class="UNDECLARED_CLASS",
            enabled_packet_classes=self.authority["enabled_packet_classes"],
            g8c_authority_effective=self.authority["effective"],
        )
        self.assertEqual(escaped["status"], "BLOCKED")
        self.assertIn("PACKET_CLASS_NOT_ENABLED", escaped["reason_codes"])

    def test_every_declared_write_commit_and_push_is_security_and_broker_authorized(self):
        envelope = self._envelope()
        broker = LocalToolBroker(
            active=True,
            assisted_write_active=True,
            assisted_write_authority_id=G8C_ID,
        )
        for path in self.pilot["write_domain"]["exact_write_paths"]:
            for action in self.pilot["required_semantic_actions"]:
                with self.subTest(path=path, action=action):
                    request = build_tool_request(action=action, path=path, semantic_owner="DSAI")
                    security = decide_tool_request(envelope, request)
                    self.assertEqual(security["decision"], "ALLOW")
                    receipt = broker.dispatch(envelope=envelope, request=request)
                    self.assertEqual(receipt["status"], "PASS")
                    self.assertEqual(receipt["reason"], "ASSISTED_WRITE_AUTHORIZED")
                    self.assertTrue(receipt["side_effect_authorized"])
                    self.assertFalse(receipt["side_effect_performed"])
                    self.assertEqual(receipt["merge_authority"], "NONE")

    def test_missing_owner_out_of_scope_and_merge_remain_denied(self):
        envelope = self._envelope()
        denied = [
            build_tool_request(
                action="WRITE_FILE",
                path="tests/development_skills/test_dsai_wp8_orch1_pilot.py",
                semantic_owner=None,
            ),
            build_tool_request(
                action="WRITE_FILE",
                path="src/ovc/development/skills/orch1_escape.py",
                semantic_owner="DSAI",
            ),
            build_tool_request(
                action="MERGE",
                path="tests/development_skills/test_dsai_wp8_orch1_pilot.py",
                semantic_owner="DSAI",
            ),
        ]
        for request in denied:
            with self.subTest(request=request):
                self.assertEqual(decide_tool_request(envelope, request)["decision"], "DENY")

    def test_payload_is_non_semantic_and_has_no_scientific_authority(self):
        self.assertEqual(self.payload["pilot_id"], self.pilot["pilot_id"])
        self.assertEqual(self.payload["packet_class"], "LOW_RISK_IMPLEMENTATION")
        self.assertEqual(self.payload["semantic_owner"], "DSAI")
        self.assertEqual(self.payload["probe_value"], "BOUNDED_WRITE_CONFIRMED")
        self.assertEqual(self.payload["authority_effect"], "NONE")
        self.assertEqual(self.payload["scientific_authority_effect"], "NONE")
        self.assertEqual(self.payload["validation"], "DENIED")
        self.assertFalse(self.payload["merge_requested"])

    def test_conflict_reconciliation_is_no_overlap_and_wp9_stays_blocked(self):
        self.assertEqual(self.pilot["conflict_reconciliation"]["status"], "PASS_NO_WRITE_SET_OVERLAP")
        for row in self.pilot["conflict_reconciliation"]["open_prs_checked"]:
            self.assertFalse(row["write_set_overlap"])
        blockers = set(self.state["wp9_readiness"]["blockers"])
        self.assertIn("ORCH1_PILOT_EVIDENCE_REQUIRED", blockers)
        self.assertIn("GIT_MERGE_CAPABILITY_G9A_NOT_YET_TRUSTED", blockers)
        self.assertIn("DSAI_G9B_NOT_REACHED", blockers)


if __name__ == "__main__":
    unittest.main()
