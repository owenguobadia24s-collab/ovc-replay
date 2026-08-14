from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/development/OVC_DSAI_V0_3_VIT_CONFORMANCE_IMPLEMENTATION_PLAN_v0_1_R1_RATIFIED.json"
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp0"
STATE_ROOT = ROOT / "registries/implementation/dsai_vit_v0_3"
LEGACY_ROOT = ROOT / "registries/implementation/dsai_v0_3"

class DsaiVitV03Wp0MaterialisationTests(unittest.TestCase):
    def test_plan_hashes_and_reserved_gates_are_exact(self) -> None:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(plan["plan_sha256"], "6ea429c0150f837ccf0619085896b3b7b7156b4e3c194619dd89b0254355f15f")
        self.assertEqual(plan["design_sha256"], "1755d8e0eac857ff2b741b00e014250913ed919402555d08abe79616748fcc4e")
        self.assertEqual(plan["evaluation_sha256"], "1185d6d5353c079bc33bdfd21bf4a3c22994c19493241ac51ded2d318b21f325")
        self.assertEqual(plan["reserved_gates"], ["DSAI3V-G-VIT-PILOT", "DSAI3V-G-VIT-GENERAL"])

    def test_g0_materialisation_does_not_activate_physical_vit(self) -> None:
        decision = json.loads((RELEASE / "DSAI3V_G0_OPERATOR_PASS.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["authority_after_materialisation"]["live_physical_vit_control"], "DENIED_UNTIL_DSAI3V_G_VIT_PILOT")
        self.assertFalse(decision["authority_after_materialisation"]["parallel_physical_merge"])

    def test_new_programme_is_running_and_legacy_route_is_superseded(self) -> None:
        pointer = json.loads((STATE_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        state = json.loads((STATE_ROOT / pointer["current_state"]).read_text(encoding="utf-8"))
        self.assertEqual(state["programme_id"], "OVC-DSAI-VIT-v0.3")
        self.assertEqual(state["next_packet"], "DSAI3V-WP1")
        self.assertEqual(state["current_authority"]["vit_live_physical_main_control"], "DENIED")
        legacy_pointer = json.loads((LEGACY_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        legacy_state = json.loads((LEGACY_ROOT / legacy_pointer["current_state"]).read_text(encoding="utf-8"))
        self.assertEqual(legacy_state["status"], "SUPERSEDED")
        self.assertEqual(legacy_state["superseded_by_programme"], "OVC-DSAI-VIT-v0.3")

    def test_baseline_preserves_parent_authority_and_siq(self) -> None:
        recon = json.loads((RELEASE / "DSAI3V_WP0_BASELINE_RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["baseline_main"], "c4aff0fa34aa1123031244d9e003bd32b2115706")
        self.assertEqual(recon["parent_authority"]["ORCH-4"], "ACTIVE_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION")
        self.assertFalse(recon["parent_authority"]["parallel_merge"])
        self.assertEqual(recon["parent_authority"]["siq_runtime"], "ACTIVE_SERIALIZED_MINIMAL_CRITICAL_SECTION")

if __name__ == "__main__":
    unittest.main()
