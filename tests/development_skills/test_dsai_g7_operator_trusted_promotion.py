from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "records/development/skills/DSAI_G7_OPERATOR_TRUSTED_PROMOTION_PASS_20260812T131200+0100.json"
PREDECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_CONSOLIDATED_TRUSTED_PROMOTION_DECISION_PACKET.json"
QPACK = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_FINAL_QUALIFICATION_READINESS_CANDIDATE.json"
TRUST = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_17.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


class DSAIG7OperatorTrustedPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.predecision = json.loads(PREDECISION.read_text(encoding="utf-8"))
        cls.qpack = json.loads(QPACK.read_text(encoding="utf-8"))
        cls.trust = json.loads(TRUST.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    @staticmethod
    def tuple_key(row):
        return row["release_id"], row["capability_id"], row["environment_id"]

    def test_operator_pass_is_exact_and_changes_only_trusted_maturity_selection_eligibility(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE DSAI-G7 PASS TRUSTED")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_kind"], "TRUSTED_PROMOTION")
        self.assertEqual(self.decision["authority_effect"], "SKILL_MATURITY_SELECTION_ELIGIBILITY_ONLY")
        self.assertEqual(self.decision["promotion_count"], 8)
        self.assertEqual(self.decision["baseline_main"], "fa23baf4d57364aacef0b28635c54b43fd7dc9a9")
        self.assertEqual(self.decision["reserved_non_effects"], {
            "force_push_history_rewrite": "HARD_DENY",
            "merge_authority": "NONE",
            "orch_1": "INACTIVE",
            "orch_2": "INACTIVE",
            "scientific_selector_publication_probability_risk_exposure_trading_execution": "NONE",
            "tool_broker_production": "INACTIVE",
            "validation": "DENIED",
            "write_authority": "NONE",
        })

    def test_promoted_exact_tuples_equal_the_consolidated_operator_packet_and_qualified_candidate(self):
        expected = {self.tuple_key(row) for row in self.predecision["promotion_candidates"]}
        qualified = {self.tuple_key(row) for row in self.qpack["exact_tuples"]}
        promoted = {self.tuple_key(row) for row in self.decision["promotions"]}
        registered = {self.tuple_key(row) for row in self.trust["entries"]}
        self.assertEqual(len(expected), 8)
        self.assertEqual(expected, qualified)
        self.assertEqual(expected, promoted)
        self.assertEqual(expected, registered)
        self.assertEqual(self.qpack["stale_qualifications"], 0)
        self.assertEqual(self.qpack["known_false_allows"], 0)
        for row in self.qpack["exact_tuples"]:
            self.assertEqual(set(row["evaluation_layers"].values()), {"PASS"})

    def test_trusted_registry_is_exact_match_only_and_never_infers_extra_capability_or_permission(self):
        self.assertTrue(self.trust["effective"])
        self.assertEqual(self.trust["authority_kind"], "TRUSTED_PROMOTION")
        self.assertEqual(self.trust["authority_effect"], "SKILL_MATURITY_SELECTION_ELIGIBILITY_ONLY")
        self.assertEqual(self.trust["entry_count"], 8)
        for row in self.trust["entries"]:
            self.assertEqual(row["maturity"], "TRUSTED")
            self.assertTrue(row["selection_eligible"])
            self.assertEqual(row["permission_delta"], "NONE")
            self.assertEqual(row["write_authority"], "NONE")
            self.assertEqual(row["merge_authority"], "NONE")
        preflight_caps = {row["capability_id"] for row in self.trust["entries"] if row["skill_id"] == "OVC-SKILL-001"}
        self.assertEqual(preflight_caps, {"PACKET_PREFLIGHT"})
        self.assertNotIn("REPOSITORY_RECONCILIATION", preflight_caps)

    def test_candidate_release_registries_remain_immutable_shadow_evidence_not_hidden_authority(self):
        for relpath in (
            "registries/development/skills/governance_candidates_v0_1.json",
            "registries/development/skills/first_generation_candidates_v0_1.json",
        ):
            registry = json.loads((ROOT / relpath).read_text(encoding="utf-8"))
            self.assertTrue(registry["projection_only"])
            self.assertEqual(registry["authority_effect"], "NONE")
            for row in registry["entries"]:
                self.assertNotEqual(row.get("maturity"), "TRUSTED")
        promoted_skill_ids = {row["skill_id"] for row in self.trust["entries"]}
        self.assertEqual(promoted_skill_ids, {
            "OVC-SKILL-001", "OVC-SKILL-002", "OVC-SKILL-003", "OVC-SKILL-004",
            "OVC-SKILL-020", "OVC-SKILL-022", "OVC-SKILL-023", "OVC-SKILL-024",
        })

    def test_state_advances_only_to_wp8_and_preserves_later_reserved_gates(self):
        self.assertEqual(self.state["programme_status"], "APPROVED_G7_READY_WP8")
        self.assertEqual(self.state["supersedes_state"], "OVC_DSAI_STATE_v0_16.json")
        self.assertEqual(self.state["trusted_promotion"]["status"], "EFFECTIVE")
        self.assertEqual(self.state["trusted_promotion"]["exact_tuple_count"], 8)
        self.assertEqual(self.state["authority"]["tool_broker_production"], "INACTIVE")
        self.assertEqual(self.state["authority"]["packet_executor_trusted_gate"], "DSAI-G8B")
        self.assertEqual(self.state["authority"]["git_merge_trusted_gate"], "DSAI-G9A")
        self.assertEqual(self.state["authority"]["orch_1"], "INACTIVE")
        self.assertEqual(self.state["authority"]["orch_2"], "INACTIVE")
        self.assertEqual(self.state["authority"]["validation"], "DENIED")
        self.assertEqual(self.pointer, {
            "current_state": "OVC_DSAI_STATE_v0_17.json",
            "next_packet": "DSAI-WP8",
            "programme_id": "OVC-DSAI-v0.1",
            "schema": "ovc-programme-current-state-pointer/v1",
            "status": "READY_WP8",
        })


if __name__ == "__main__":
    unittest.main()
