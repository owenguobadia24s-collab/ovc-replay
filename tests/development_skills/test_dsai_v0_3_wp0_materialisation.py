from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/development/OVC_DSAI_V0_3_CONTINUOUS_EXECUTION_LANDING_TRAIN_PLAN_v0_1.md"
ADMISSION = ROOT / "docs/releases/development-skills-architecture-v0-3/dsai3-wp0/DSAI3_G0_OPERATOR_ADMISSION.json"
RECON = ROOT / "docs/releases/development-skills-architecture-v0-3/dsai3-wp0/DSAI3_WP0_BASELINE_RECONCILIATION.json"
STATE = ROOT / "registries/implementation/dsai_v0_3/OVC_DSAI_V0_3_STATE_v0_1.json"
POINTER = ROOT / "registries/implementation/dsai_v0_3/CURRENT_STATE_POINTER.json"


class DsaiV03Wp0MaterialisationTests(unittest.TestCase):
    def test_operator_admission_is_bounded_and_does_not_activate_v03(self) -> None:
        admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
        self.assertEqual(admission["programme_id"], "OVC-DSAI-v0.3")
        self.assertEqual(
            admission["decision"],
            "PASS_ADMIT_BOUNDED_CONFORMANCE_IMPLEMENTATION_AND_ACTIVATION_GATE_PREPARATION",
        )
        denied = set(admission["not_authorised"])
        self.assertIn(
            "production activation of persistent continuous packet executor before DSAI3-G7",
            denied,
        )
        self.assertIn("parallel merge", denied)
        self.assertIn("force-push or history rewrite", denied)
        self.assertEqual(
            admission["authority_effect"],
            "BOUNDED_CONFORMANCE_IMPLEMENTATION_AND_GATE_PREPARATION_ONLY",
        )

    def test_baseline_reconciliation_preserves_parent_orch345_authority(self) -> None:
        recon = json.loads(RECON.read_text(encoding="utf-8"))
        self.assertEqual(
            recon["baseline_main"],
            "7e5db8b99464b7afebdbce703cf3377d9b65ff82",
        )
        self.assertEqual(
            recon["active_parent_authority"]["ORCH-4"],
            "ACTIVE_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION",
        )
        self.assertFalse(recon["active_parent_authority"]["parallel_merge"])
        self.assertEqual(recon["authority_delta"], "NONE")
        self.assertEqual(recon["next_packet"], "DSAI3-WP1")

    def test_programme_state_stops_before_activation_gate_and_reuses_active_siq(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "RUNNING")
        self.assertEqual(state["next_packet"], "DSAI3-WP1")
        self.assertEqual(
            state["gate_disposition"]["DSAI3-G7"],
            "FUTURE_OPERATOR_REQUIRED_NOT_EFFECTIVE",
        )
        self.assertEqual(
            state["current_authority"]["dsai3_continuous_executor"],
            "INACTIVE_SHADOW_SANDBOX_ONLY",
        )
        self.assertEqual(
            state["current_authority"]["siq_runtime"],
            "ACTIVE_EXISTING_SERIALIZED_MINIMAL_CRITICAL_SECTION",
        )
        self.assertEqual(pointer["current_state"], STATE.name)
        self.assertEqual(pointer["next_packet"], "DSAI3-WP1")

    def test_plan_contains_continuous_command_and_siq_reuse_invariants(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("parallel construction lanes -> persistent ordered landing train -> one serialized squash integration point", text)
        self.assertIn("OVC CONTINUE [packet]", text)
        self.assertIn("OVC CONTINUE ONLY <packet>", text)
        self.assertIn("The active `OVC.SIQ.RUNTIME.v0.1` constitution/runtime remains the sole landing-queue owner", text)
        self.assertIn("Only the SIQ queue-head candidate may perform base-sensitive final merge assurance", text)
        self.assertIn("DSAI3-G7 — activate continuous packet executor and SIQ actuation binding", text)
        self.assertIn("OPERATOR_REQUIRED", text)


if __name__ == "__main__":
    unittest.main()
