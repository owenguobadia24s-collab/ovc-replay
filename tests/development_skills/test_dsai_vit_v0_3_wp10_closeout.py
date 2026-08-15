from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp10"
STATE_ROOT = ROOT / "registries/implementation/dsai_vit_v0_3"


class DsaiVitV03Wp10CloseoutTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_q6_receipts_are_serial_complete_and_exact(self) -> None:
        pack = self._load(RELEASE / "DSAI3V_WP10_Q6_LIVE_PILOT_RECEIPTS.json")
        receipts = pack["receipts"]
        self.assertEqual(len(receipts), 2)
        self.assertTrue(pack["chain_complete"])
        self.assertEqual(receipts[1]["predecessor_commit"], receipts[0]["observed_main_commit"])
        for receipt in receipts:
            self.assertTrue(receipt["exact_tree_equal"])
            self.assertEqual(receipt["predicted_tree"], receipt["observed_tree"])
            self.assertFalse(receipt["parallel_merge"])
            self.assertTrue(receipt["authority_allow"])

    def test_q6_zero_tolerance_metrics_pass(self) -> None:
        metrics = self._load(RELEASE / "DSAI3V_WP10_Q6_METRICS_AND_INCIDENTS.json")
        self.assertEqual(metrics["false_authority_allows"], 0)
        self.assertEqual(metrics["parallel_merges"], 0)
        self.assertEqual(metrics["tree_mismatches"], 0)
        self.assertEqual(metrics["unexplained_main_divergence"], 0)
        self.assertTrue(metrics["complete_end_to_end_receipts"])
        self.assertEqual(metrics["operator_interventions"], 0)
        self.assertEqual(metrics["unresolved_high_severity_incidents"], 0)
        self.assertTrue(metrics["q6_pass"])

    def test_g10_is_delegated_pass_with_no_authority_delta(self) -> None:
        decision = self._load(RELEASE / "DSAI3V_G10_DELEGATED_PASS.json")
        self.assertEqual(decision["gate_id"], "DSAI3V-G10")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["next_gate"], "DSAI3V-G-VIT-GENERAL")

    def test_general_gate_is_ready_but_not_self_approved(self) -> None:
        gate = self._load(RELEASE / "DSAI3V_G_VIT_GENERAL_GATE_READY.json")
        self.assertEqual(gate["status"], "GATE_READY")
        self.assertTrue(gate["operator_required"])
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertFalse(gate["proposed_delta"]["parallel_physical_merge"])
        self.assertFalse(gate["proposed_delta"]["programme_specific_authority_change"])

    def test_programme_state_preserves_pilot_authority_until_operator_decision(self) -> None:
        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        state = self._load(STATE_ROOT / pointer["current_state"])
        self.assertEqual(pointer["status"], "GATE_READY")
        self.assertEqual(pointer["current_gate"], "DSAI3V-G-VIT-GENERAL")
        self.assertEqual(state["status"], "GATE_READY")
        self.assertEqual(state["current_authority"]["vit_live_physical_main_control"], "ACTIVE_PILOT_LOW_RISK_IMPLEMENTATION_ONLY")
        self.assertFalse(state["current_authority"]["parallel_physical_merge"])
        self.assertEqual(state["reserved_gates"]["DSAI3V-G-VIT-GENERAL"], "OPERATOR_REQUIRED")


if __name__ == "__main__":
    unittest.main()
