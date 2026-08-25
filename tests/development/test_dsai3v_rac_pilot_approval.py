from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7/DSAI3V_RAC_DELTA_ASSURANCE_PILOT_OPERATOR_DECISION_v0_1.json"
STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_3_PILOT_APPROVED_IMPLEMENTATION_READY.json"
POINTER = ROOT / "registries/implementation/dsai3v_cipr_rac/CURRENT_STATE_POINTER.json"


class TestDsai3vRacPilotApproval(unittest.TestCase):
    def test_operator_pass_is_exact_and_bounded(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["gate_id"], "DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(
            decision["operator_command"],
            "OVC APPROVE DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT PASS",
        )
        self.assertEqual(
            decision["authority_effect"],
            "AUTHORISE_BOUNDED_DELTA_ASSURANCE_PILOT_IMPLEMENTATION_ONLY",
        )
        self.assertIn("general delta-assurance admission", decision["non_grants"])
        self.assertEqual(
            decision["next_reserved_gate"],
            "DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL",
        )

    def test_materialisation_does_not_pre_activate_pilot(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertFalse(state["blocking_path_substitution_active"])
        self.assertFalse(state["required_check_substitution_active"])
        self.assertFalse(state["runner_cutover_active"])
        self.assertEqual(
            state["next_packet"],
            "DSAI3V-RAC-WP7-BOUNDED-DELTA-ASSURANCE-PILOT",
        )

    def test_current_pointer_releases_only_wp7(self) -> None:
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(pointer["status"], "PILOT_APPROVED_IMPLEMENTATION_READY")
        self.assertEqual(
            pointer["next_packet"],
            "DSAI3V-RAC-WP7-BOUNDED-DELTA-ASSURANCE-PILOT",
        )
        self.assertIsNone(pointer["operator_stop_gate"])


if __name__ == "__main__":
    unittest.main()
