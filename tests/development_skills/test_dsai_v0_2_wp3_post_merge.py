from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import resolve_orch345_authority


ROOT = Path(__file__).resolve().parents[2]
TERMINAL_TARGET = "IMPLEMENTED_ORCH345_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION_PORTFOLIO_DISPATCH"


class DSAI2WP3PostMergeTests(unittest.TestCase):
    def _load(self, path: str) -> dict:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_g3_merge_receipt_and_programme_state_are_exact(self) -> None:
        receipt = self._load("docs/releases/development-skills-architecture-v0-2/dsai2-wp3/DSAI2_WP3_G3_SQUASH_MERGE_RECEIPT.json")
        self.assertEqual(receipt["pull_request"], 689)
        self.assertEqual(receipt["approved_head"], "f2578de987b1e27b866f61bbc564a185dcdac26d")
        self.assertEqual(receipt["result_main_sha"], "1db66a2ca48be27930395073e842638ad8f7f216")
        self.assertEqual(receipt["operator_decision"], "PASS")
        self.assertTrue(receipt["authority_effective_on_main"])
        self.assertFalse(receipt["authority_after_merge"]["parallel_merge"])

        state = self._load("registries/implementation/dsai_v0_2/OVC_DSAI_V0_2_STATE_v0_5.json")
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["packet_id"], "DSAI2-WP3")
        self.assertEqual(state["merge_commit"], "1db66a2ca48be27930395073e842638ad8f7f216")
        self.assertTrue(state["authority_effective_on_main"])
        self.assertEqual(state["authority_resolution"], "ACTIVE_AUTHORIZED")
        self.assertEqual(state["next_packet"], "DSAI2-WP4")

    def test_exact_authority_resolves_active_when_present_on_main(self) -> None:
        authority = self._load("registries/development/skills/orch345_bounded_authority_v0_1.json")
        resolution = resolve_orch345_authority(authority=authority, record_present_on_main=True)
        self.assertEqual(resolution["status"], "ACTIVE_AUTHORIZED")
        self.assertEqual(
            resolution["reason_codes"],
            ["EXACT_DSAI2_G3_BOUNDED_ORCH345_AUTHORITY_ACTIVE"],
        )
        self.assertFalse(authority["integration_policy"]["parallel_merge"])
        self.assertTrue(authority["integration_policy"]["serialized_final_integration_window"])
        self.assertEqual(authority["integration_policy"]["target_branch"], "main")
        self.assertEqual(authority["integration_policy"]["merge_method"], "squash")
        self.assertFalse(authority["integration_policy"]["direct_main_mutation"])
        self.assertFalse(authority["integration_policy"]["force_push"])
        self.assertFalse(authority["integration_policy"]["history_rewrite"])

    def test_historical_wp3_state_remains_immutable_while_live_pointer_may_advance(self) -> None:
        historical = self._load("registries/implementation/dsai_v0_2/OVC_DSAI_V0_2_STATE_v0_5.json")
        self.assertEqual(historical["status"], "COMPLETED")
        self.assertEqual(historical["packet_id"], "DSAI2-WP3")
        self.assertEqual(historical["merge_commit"], "1db66a2ca48be27930395073e842638ad8f7f216")
        self.assertEqual(historical["reserved_boundaries"]["operator_required_gate_behavior"], "STOP")
        self.assertEqual(historical["reserved_boundaries"]["validation"], "DENIED")
        self.assertEqual(
            historical["reserved_boundaries"]["scientific_selector_model_family_candidate_theory_semantic_publication_probability_risk_exposure_trading_execution"],
            "NONE",
        )

        pointer = self._load("registries/implementation/dsai_v0_2/CURRENT_STATE_POINTER.json")
        self.assertIn(
            pointer["current_state"],
            {
                "OVC_DSAI_V0_2_STATE_v0_5.json",
                "OVC_DSAI_V0_2_STATE_v0_6.json",
                "OVC_DSAI_V0_2_STATE_v0_7.json",
            },
        )
        if pointer["current_state"] == "OVC_DSAI_V0_2_STATE_v0_5.json":
            self.assertEqual(pointer["status"], "COMPLETED")
            self.assertEqual(pointer["next_packet"], "DSAI2-WP4")
        elif pointer["current_state"] == "OVC_DSAI_V0_2_STATE_v0_6.json":
            self.assertEqual(pointer["status"], "APPROVED")
            self.assertIsNone(pointer["next_packet"])
            current = self._load("registries/implementation/dsai_v0_2/OVC_DSAI_V0_2_STATE_v0_6.json")
            self.assertEqual(current["packet_id"], "DSAI2-WP4")
            self.assertEqual(current["gate_id"], "DSAI2-G4")
            self.assertEqual(current["decision"], "PASS_DELEGATED_AUTO_RATIFIED")
            self.assertIsNone(current["merge_commit"])
        else:
            self.assertEqual(pointer["status"], "COMPLETED")
            self.assertIsNone(pointer["next_packet"])
            current = self._load("registries/implementation/dsai_v0_2/OVC_DSAI_V0_2_STATE_v0_7.json")
            self.assertEqual(current["status"], "COMPLETED")
            self.assertEqual(current["terminal"]["target_terminal_state"], TERMINAL_TARGET)
            self.assertEqual(current["packet_id"], "DSAI2-WP4")
            self.assertTrue(current["terminal"]["programme_complete"])


if __name__ == "__main__":
    unittest.main()
