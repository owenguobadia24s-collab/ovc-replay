from __future__ import annotations

import unittest
from pathlib import Path

from apps.research_console.pattern_discovery_corr2 import CORR3_BANNER


ROOT = Path(__file__).resolve().parents[3]
PANEL = ROOT / "apps/research_console/pattern_discovery_corr2.py"
RUNNER = ROOT / "src/ovc/research_operations/pattern_discovery/pilot_corr3_review_closure.py"
ENTRY = ROOT / "src/ovc/research_operations/pattern_discovery/pilot_corr3_review_closure_entry.py"
WRAPPER = ROOT / "scripts/run_c1c_g5_corr3_review.ps1"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/C1C_G5_CORR3_STRUCTURAL_COMPARISON_REVIEW_CONTRACT_v0_1.md"
AUTHORITY = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/C1C_G5_CORR3_AUTHORITY_BINDING.json"


class C1cG5Corr3ConsoleBoundaryTests(unittest.TestCase):
    def test_console_projects_exact_medoid_components_overlap_and_persistence(self) -> None:
        panel = PANEL.read_text(encoding="utf-8")
        self.assertIn("corr3_structural_comparison", panel)
        self.assertIn("Exact assigned-medoid comparison", panel)
        self.assertIn("Duplicate-window and overlap status", panel)
        self.assertIn("LONG_PERSISTENCE derivation", panel)
        self.assertIn("Target and assigned-medoid fingerprints", panel)
        self.assertIn("READ ONLY", CORR3_BANNER)

    def test_runner_contains_no_replay_provider_or_rule_mutation(self) -> None:
        runner = RUNNER.read_text(encoding="utf-8")
        for forbidden in (
            "run_pilot_from_states(",
            "load_exact_c2_states(",
            "verify_compute_run(",
            "build_cluster_versions(",
            "build_partition_cluster_version(",
            "requests.",
            "urllib",
            "rclone",
            "boto3",
        ):
            self.assertNotIn(forbidden, runner)
        self.assertIn("CORR3_OPERATOR_REVIEW_PREPARATION_PROHIBITED_IN_CI", runner)
        self.assertIn("CORR3_OPERATOR_REVIEW_FINALIZATION_PROHIBITED_IN_CI", runner)
        self.assertIn('"second_machine_replay_performed": False', runner)
        self.assertIn('"canonical_append": "DENIED"', runner)

    def test_wrapper_entry_contract_and_authority_preserve_exact_boundary(self) -> None:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        entry = ENTRY.read_text(encoding="utf-8")
        contract = CONTRACT.read_text(encoding="utf-8")
        authority = AUTHORITY.read_text(encoding="utf-8")
        self.assertIn("preflight", wrapper)
        self.assertIn("prepare", wrapper)
        self.assertIn("finalize", wrapper)
        self.assertIn("-ReviewFile", wrapper)
        self.assertIn("pilot_corr2_review_closure_entry", entry)
        self.assertIn("No second machine replay is required or authorised", contract)
        self.assertIn("PDPILOT-CANDIDATE-bab63b935155e4d9033aed81", contract)
        self.assertIn("different scopes and are not required to equal", contract)
        self.assertIn('"machine_replay": "DENIED_NOT_REQUIRED"', authority)
        self.assertIn('"distance_pack_change": "NONE"', authority)
        self.assertIn('"canonical_append": "DENIED"', authority)


if __name__ == "__main__":
    unittest.main()
