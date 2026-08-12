from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "records/development/skills/DSAI_G9A_OPERATOR_TRUSTED_PROMOTION_PASS_20260812T193029+0100.json"
PREDECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_G9A_GIT_MERGE_TRUSTED_PROMOTION_DECISION_PACKET.json"
TRUST = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
CANDIDATE = ROOT / "registries/development/skills/wp9_git_merge_candidate_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_24.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"
RELEASE = "OVC-SKILL-014@0.2.0+sha256:e000ce135ff4e9a17d4f29ddfb61ba5bd3474fdd9f89e7e9814bf43eee5deff5"
ENV = "windows-local-python311"


class DSAIG9AOperatorTrustedPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.predecision = json.loads(PREDECISION.read_text(encoding="utf-8"))
        cls.trust = json.loads(TRUST.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))["entries"][0]
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    def test_operator_command_materialises_exact_one_tuple_promotion(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE DSAI-G9A PASS TRUSTED")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_kind"], "TRUSTED_PROMOTION")
        self.assertEqual(self.decision["authority_effect"], "SKILL_MATURITY_SELECTION_ELIGIBILITY_ONLY")
        self.assertEqual(self.decision["promotion_count"], 1)
        row = self.decision["promotions"][0]
        self.assertEqual(row["release_id"], RELEASE)
        self.assertEqual(row["capability_id"], "GIT_PACKET_MANAGEMENT")
        self.assertEqual(row["environment_id"], ENV)
        self.assertEqual(row["maturity"], "TRUSTED")
        self.assertTrue(row["selection_eligible"])
        self.assertEqual(row["permission_delta"], "NONE")
        self.assertEqual(row["write_authority"], "NONE")
        self.assertEqual(row["merge_authority"], "NONE")

    def test_predecision_packet_remains_immutable_and_matches_promoted_tuple(self):
        candidate = self.predecision["promotion_candidate"]
        row = self.decision["promotions"][0]
        self.assertEqual(self.predecision["decision"], "PENDING_OPERATOR")
        self.assertEqual(candidate["release_id"], row["release_id"])
        self.assertEqual(candidate["capability_id"], row["capability_id"])
        self.assertEqual(candidate["environment_id"], row["environment_id"])
        self.assertEqual(candidate["environment_hash"], row["environment_hash"])
        self.assertEqual(candidate["knowledge_pack_hash"], row["knowledge_pack_hash"])

    def test_trusted_registry_contains_exact_git_merge_tuple_without_permissions(self):
        rows = [row for row in self.trust["entries"] if row["release_id"] == RELEASE]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(self.trust["entry_count"], 10)
        self.assertEqual(row["capability_id"], "GIT_PACKET_MANAGEMENT")
        self.assertEqual(row["environment_id"], ENV)
        self.assertEqual(row["maturity"], "TRUSTED")
        self.assertTrue(row["selection_eligible"])
        self.assertEqual(row["permission_delta"], "NONE")
        self.assertEqual(row["write_authority"], "NONE")
        self.assertEqual(row["merge_authority"], "NONE")

    def test_candidate_registry_remains_historical_predecision_projection(self):
        self.assertEqual(self.candidate["release_id"], RELEASE)
        self.assertEqual(self.candidate["maturity"], "QUALIFICATION_CANDIDATE")
        self.assertFalse(self.candidate["trusted"])
        self.assertFalse(self.candidate["selection_eligible"])
        self.assertEqual(self.candidate["merge_authority"], "NONE")
        self.assertEqual(self.candidate["promotion_gate"], "DSAI-G9A")
        self.assertEqual(self.candidate["activation_gate"], "DSAI-G9B")

    def test_post_g9a_state_preserves_g9b_and_merge_authority_boundaries(self):
        capability = self.state["git_merge_capability"]
        self.assertTrue(capability["trusted"])
        self.assertTrue(capability["selection_eligible"])
        self.assertEqual(capability["maturity"], "TRUSTED")
        self.assertEqual(capability["merge_authority"], "NONE")
        self.assertFalse(capability["automatic_merge"])
        authority = self.state["authority"]
        self.assertEqual(authority["total_trusted_tuple_count"], 10)
        self.assertEqual(authority["orch_2"], "INACTIVE_PENDING_DSAI_G9B")
        self.assertEqual(authority["merge_authority"], "NONE")
        self.assertFalse(authority["automatic_merge"])
        self.assertFalse(authority["direct_main_mutation"])
        self.assertEqual(authority["validation"], "DENIED")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP9"]["g9b_decision"], "NOT_READY")

    def test_v024_preserves_post_g9a_state_while_live_pointer_may_advance_lawfully(self):
        self.assertEqual(self.state["programme_status"], "G9A_PASS_READY_G9B_PREPARATION")
        self.assertEqual(self.pointer["programme_id"], "OVC-DSAI-v0.1")
        self.assertEqual(self.pointer["schema"], "ovc-programme-current-state-pointer/v1")
        self.assertTrue(str(self.pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_"))
        self.assertTrue(str(self.pointer["status"]).strip())
        self.assertIn(self.pointer["next_packet"], {"DSAI-WP9", "DSAI-WP10", "DSAI-WP11"})


if __name__ == "__main__":
    unittest.main()
