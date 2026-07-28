from __future__ import annotations

import unittest
from pathlib import Path

from apps.research_console.pattern_discovery import (
    CORRECTION_BANNER,
    review_fields_for_disposition,
)
from apps.research_console.pattern_discovery_corr2 import CORR2_BANNER


ROOT = Path(__file__).resolve().parents[3]
CONSOLE = ROOT / "apps/research_console/pattern_discovery.py"
PANEL = ROOT / "apps/research_console/pattern_discovery_corr2.py"
RUNNER = ROOT / "src/ovc/research_operations/pattern_discovery/pilot_corr2_review_closure.py"
WRAPPER = ROOT / "scripts/run_c1c_g5_corr2_deferred_review.ps1"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/C1C_G5_CORR2_DEFERRED_OBJECT_REVIEW_CONTRACT_v0_1.md"


class C1cG5Corr2ConsoleTests(unittest.TestCase):
    def test_disposition_specific_fields_include_exact_evidence_references(self) -> None:
        for disposition in (
            "WORKFLOW_ACCEPTED",
            "FLAG_WORKFLOW_DEFECT",
            "FLAG_UI_FRICTION",
            "DEFER_PILOT_OBJECT",
            "REJECT_PILOT_OBJECT",
        ):
            fields = review_fields_for_disposition(disposition)
            self.assertIn("evidence_references", fields)
        self.assertIn("resolution_criteria", review_fields_for_disposition("DEFER_PILOT_OBJECT"))
        self.assertIn("next_review_condition", review_fields_for_disposition("DEFER_PILOT_OBJECT"))
        self.assertIn("affected_console_surface", review_fields_for_disposition("FLAG_UI_FRICTION"))

    def test_console_is_read_only_and_exact_context_is_visible(self) -> None:
        console = CONSOLE.read_text(encoding="utf-8")
        panel = PANEL.read_text(encoding="utf-8")
        self.assertIn("render_exact_review_context", console)
        self.assertIn("exact_evidence_references", panel)
        self.assertIn("Resolved queue context", panel)
        self.assertIn("Resolved fingerprint context", panel)
        self.assertIn("Resolved immutable source lineage", panel)
        self.assertIn("disabled=not enabled", console)
        self.assertIn("Canonical append remains disabled", console)
        self.assertIn("NO REPLAY OR CANONICAL AUTHORITY", CORR2_BANNER)
        self.assertIn("C2 AND CANONICAL AUTHORITY UNCHANGED", CORRECTION_BANNER)

    def test_runner_contains_no_machine_replay_or_provider_operation(self) -> None:
        runner = RUNNER.read_text(encoding="utf-8")
        for forbidden in (
            "run_pilot_from_states(",
            "load_exact_c2_states(",
            "verify_compute_run(",
            "requests.",
            "urllib",
            "rclone",
            "boto3",
        ):
            self.assertNotIn(forbidden, runner)
        self.assertIn("CORR2_OPERATOR_REVIEW_PREPARATION_PROHIBITED_IN_CI", runner)
        self.assertIn("CORR2_OPERATOR_REVIEW_FINALIZATION_PROHIBITED_IN_CI", runner)
        self.assertIn('"second_machine_replay_performed": False', runner)
        self.assertIn('"canonical_append": "DENIED"', runner)

    def test_wrapper_and_contract_preserve_operator_local_boundary(self) -> None:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("preflight", wrapper)
        self.assertIn("prepare", wrapper)
        self.assertIn("finalize", wrapper)
        self.assertIn("-ReviewFile", wrapper)
        self.assertIn("does not execute another market replay", contract)
        self.assertIn("exactly the two deferred pilot objects", contract)
        self.assertIn("canonical Discovery processing or append", contract)
        self.assertIn("PILOT_ONLY", contract)
        self.assertIn("NON_PROMOTABLE", contract)


if __name__ == "__main__":
    unittest.main()
