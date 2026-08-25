from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7/DSAI3V_RAC_DELTA_ASSURANCE_PILOT_OPERATOR_DECISION_v0_1.json"
APPROVED_STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_3_PILOT_APPROVED_IMPLEMENTATION_READY.json"
IMPLEMENTED_STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_4_PILOT_SUBSTRATE_IMPLEMENTED_INACTIVE.json"
ACTIVE_STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_5_PILOT_BASELINE_ACTIVE.json"
CORRECTED_STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_6_PILOT_CORRECTED_REBASELINE_REQUIRED.json"
POINTER = ROOT / "registries/implementation/dsai3v_cipr_rac/CURRENT_STATE_POINTER.json"
BASELINE = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7/DSAI3V_RAC_PILOT_BASELINE_CERTIFICATE_v0_1.json"


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
        state = json.loads(APPROVED_STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertFalse(state["blocking_path_substitution_active"])
        self.assertFalse(state["required_check_substitution_active"])
        self.assertFalse(state["runner_cutover_active"])
        self.assertEqual(
            state["next_packet"],
            "DSAI3V-RAC-WP7-BOUNDED-DELTA-ASSURANCE-PILOT",
        )

    def test_wp7_inactive_state_is_preserved_and_pointer_advances_only_to_bounded_wp7b(self) -> None:
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        state = json.loads(IMPLEMENTED_STATE.read_text(encoding="utf-8"))
        active = json.loads(ACTIVE_STATE.read_text(encoding="utf-8"))
        self.assertEqual(
            pointer["current_state"],
            "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_6_PILOT_CORRECTED_REBASELINE_REQUIRED.json",
        )
        self.assertEqual(pointer["status"], "PILOT_COMPATIBILITY_CORRECTED_REBASELINE_REQUIRED")
        self.assertEqual(pointer["next_packet"], "DSAI3V-RAC-WP7D-PILOT-REBASELINE-AFTER-CORRECTION")
        self.assertEqual(pointer["operator_stop_gate"], "DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL")
        self.assertEqual(state["phase"], "PILOT_SUBSTRATE_IMPLEMENTED_INACTIVE_BASELINE_REQUIRED")
        self.assertEqual(state["status"], "IMPLEMENTED_QA_REVIEW")
        self.assertFalse(state["blocking_path_substitution_active"])
        self.assertFalse(state["required_check_substitution_active"])
        self.assertFalse(state["runner_cutover_active"])
        self.assertEqual(state["next_packet"], "DSAI3V-RAC-WP7B-PILOT-BASELINE-ACTIVATION")
        self.assertEqual(state["next_boundary_class"], "OPERATOR_REQUIRED")
        self.assertEqual(active["pilot_class"], "DSAI_VIT_RECEIPT_ONLY_V0_1")
        self.assertFalse(active["general_delta_assurance_active"])
        self.assertFalse(active["required_check_substitution_active"])
        self.assertFalse(active["runner_cutover_active"])
        self.assertEqual(active["next_boundary_class"], "OPERATOR_REQUIRED")
        corrected = json.loads(CORRECTED_STATE.read_text(encoding="utf-8"))
        self.assertEqual(corrected["pilot_eligibility"], "FAIL_CLOSED_ASSURANCE_SURFACE_DRIFT_UNTIL_REBASELINE")
        self.assertEqual(corrected["unsafe_omission_count"], 0)


if __name__ == "__main__":
    unittest.main()
