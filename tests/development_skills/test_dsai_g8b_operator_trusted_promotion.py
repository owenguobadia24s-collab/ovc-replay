from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "records/development/skills/DSAI_G8B_OPERATOR_TRUSTED_PROMOTION_PASS_20260812T160400+0100.json"
PREDECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp8/DSAI_G8B_PACKET_EXECUTOR_TRUSTED_PROMOTION_DECISION_PACKET.json"
TRUST = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
CANDIDATE = ROOT / "registries/development/skills/orchestration_candidates_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_19.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"
RELEASE = "OVC-SKILL-030@0.1.0+sha256:62809d0f5f1d4298fa916766912d4bec7b5a8bf7712f7382d448137f6f12f130"
ENV = "windows-local-python311"


class DSAIG8BOperatorTrustedPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.predecision = json.loads(PREDECISION.read_text(encoding="utf-8"))
        cls.trust = json.loads(TRUST.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))["entries"][0]
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    def test_operator_command_materialises_exact_one_tuple_promotion(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE DSAI-G8B PASS TRUSTED")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_kind"], "TRUSTED_PROMOTION")
        self.assertEqual(self.decision["authority_effect"], "SKILL_MATURITY_SELECTION_ELIGIBILITY_ONLY")
        self.assertEqual(self.decision["promotion_count"], 1)
        row = self.decision["promotions"][0]
        self.assertEqual(row["release_id"], RELEASE)
        self.assertEqual(row["capability_id"], "PACKET_EXECUTION")
        self.assertEqual(row["environment_id"], ENV)
        self.assertEqual(row["maturity"], "TRUSTED")
        self.assertTrue(row["selection_eligible"])
        self.assertEqual(row["write_authority"], "NONE")
        self.assertEqual(row["merge_authority"], "NONE")

    def test_exact_head_assurance_is_tree_identical_to_integrated_wp8(self):
        assurance = self.decision["assurance"]
        self.assertEqual(assurance["repository_tests"], {"run_number": 3602, "status": "PASS"})
        self.assertEqual(assurance["ovc_tiered_assurance"], {"run_number": 1977, "status": "PASS"})
        self.assertTrue(assurance["merge_tree_matches_tested_candidate_tree"])
        self.assertEqual(self.decision["decision_baseline_tree"], assurance["tested_candidate_tree"])

    def test_predecision_packet_remains_immutable_and_matches_promoted_tuple(self):
        candidate = self.predecision["promotion_candidate"]
        row = self.decision["promotions"][0]
        self.assertEqual(self.predecision["decision"], "PENDING_OPERATOR")
        self.assertEqual(candidate["release_id"], row["release_id"])
        self.assertEqual(candidate["capability_id"], row["capability_id"])
        self.assertEqual(candidate["environment_id"], row["environment_id"])
        self.assertEqual(candidate["environment_hash"], row["environment_hash"])
        self.assertEqual(candidate["knowledge_pack_hash"], row["knowledge_pack_hash"])

    def test_trusted_registry_contains_exact_packet_executor_tuple_without_permissions(self):
        rows = [row for row in self.trust["entries"] if row["release_id"] == RELEASE]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(self.trust["entry_count"], 9)
        self.assertEqual(row["capability_id"], "PACKET_EXECUTION")
        self.assertEqual(row["environment_id"], ENV)
        self.assertEqual(row["maturity"], "TRUSTED")
        self.assertTrue(row["selection_eligible"])
        self.assertEqual(row["permission_delta"], "NONE")
        self.assertEqual(row["write_authority"], "NONE")
        self.assertEqual(row["merge_authority"], "NONE")

    def test_candidate_registry_remains_projection_only_qualified_shadow_record(self):
        self.assertEqual(self.candidate["release_id"], RELEASE)
        self.assertEqual(self.candidate["maturity"], "QUALIFIED")
        self.assertEqual(self.candidate["availability"], "SHADOW_ONLY")
        self.assertEqual(self.candidate["write_permission"], "DENY")
        self.assertEqual(self.candidate["merge_permission"], "DENY")

    def test_v019_preserves_exact_post_g8b_state_while_pointer_may_advance_lawfully(self):
        self.assertEqual(self.state["programme_status"], "G8B_PASS_READY_G8C_PREPARATION")
        self.assertTrue(self.state["packet_executor"]["trusted"])
        self.assertEqual(self.state["packet_executor"]["maturity"], "TRUSTED")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP8"]["g8b_decision"], "PASS_OPERATOR_TRUSTED")
        self.assertEqual(self.state["packet_updates"]["DSAI-WP8"]["g8c_decision"], "NOT_READY")
        self.assertEqual(self.state["authority"]["orch_1"], "INACTIVE_PENDING_DSAI_G8C")
        self.assertEqual(self.state["authority"]["orch_2"], "INACTIVE")
        self.assertEqual(self.state["authority"]["write_authority"], "NONE")
        self.assertEqual(self.state["authority"]["merge_authority"], "NONE")
        self.assertEqual(self.state["authority"]["validation"], "DENIED")

        self.assertEqual(self.pointer["programme_id"], "OVC-DSAI-v0.1")
        self.assertEqual(self.pointer["schema"], "ovc-programme-current-state-pointer/v1")
        self.assertTrue(str(self.pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_"))
        self.assertTrue(str(self.pointer["status"]).strip())
        self.assertTrue(str(self.pointer["next_packet"]).startswith("DSAI-WP"))


if __name__ == "__main__":
    unittest.main()
