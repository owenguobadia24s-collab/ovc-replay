from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp12"
STATE_ROOT = ROOT / "registries/implementation/dsai_vit_v0_3"
SLO = STATE_ROOT / "VIT_SERVICE_SLO_v0_1.json"


class DsaiVitV03Wp12Tests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_stabilization_sample_has_zero_safety_regression(self) -> None:
        evidence = self._load(RELEASE / "DSAI3V_WP12_STABILIZATION_EVIDENCE.json")
        sample = evidence["live_materialisation_sample"]
        self.assertEqual(sample["count"], 4)
        self.assertEqual(sample["exact_tree_equal_count"], 4)
        self.assertEqual(sample["receipt_complete_count"], 4)
        self.assertEqual(sample["parallel_merge_count"], 0)
        self.assertEqual(sample["tree_mismatch_count"], 0)
        self.assertEqual(sample["false_authority_allow_count"], 0)
        self.assertEqual(sample["duplicate_effective_write_count"], 0)
        self.assertEqual(sample["lost_mandatory_receipt_count"], 0)
        self.assertEqual(sample["safety_class_incident_count"], 0)
        self.assertEqual(evidence["receipt_audit"]["aggregate"], "PASS_4_OF_4")
        self.assertEqual(evidence["incident_review"]["unresolved_safety_class_incidents"], 0)

    def test_permanent_slo_preserves_hard_correctness_and_authority(self) -> None:
        slo = self._load(SLO)
        hard = slo["hard_correctness_slos"]
        self.assertEqual(hard["exact_physical_vit_tree_equality_rate"], 1.0)
        self.assertEqual(hard["mandatory_receipt_completeness_rate"], 1.0)
        for key in ("false_authority_allows", "parallel_physical_merges", "unexplained_main_divergences", "duplicate_effective_writes", "lost_mandatory_receipts", "accepted_tree_mismatches", "safety_class_incidents"):
            self.assertEqual(hard[key], 0)
        currentness = slo["currentness_policy"]
        self.assertEqual(currentness["grt_g3"], "NOT_AUTHORISED")
        self.assertFalse(currentness["parallel_physical_merge"])
        self.assertEqual(slo["authority_effect"], "NONE_OPERATIONAL_POLICY_ONLY")
        self.assertEqual(slo["latency_policy"]["breach_effect"], "OPERATIONAL_REVIEW_ONLY_NO_AUTHORITY_EFFECT")
        self.assertFalse(slo["latency_policy"]["correctness_checks_may_be_skipped_for_latency"])

    def test_reference_assurance_and_state_are_terminal_ready(self) -> None:
        assurance = self._load(RELEASE / "DSAI3V_WP12_REFERENCE_ASSURANCE.json")
        self.assertEqual(assurance["physical_reference_sample"]["status"], "PASS")
        self.assertEqual(assurance["receipt_completeness"]["status"], "PASS")
        self.assertEqual(assurance["safety"]["status"], "PASS")

        historical = self._load(STATE_ROOT / "OVC_DSAI_VIT_V0_3_STATE_v0_19.json")
        self.assertEqual(historical["status"], "COMPLETED")
        self.assertEqual(historical["packet_id"], "DSAI3V-WP12")
        self.assertEqual(historical["gate_id"], "DSAI3V-G12")
        self.assertIsNone(historical["next_packet"])

        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        state = self._load(STATE_ROOT / pointer["current_state"])
        self.assertIn(pointer["status"], {"QA_REVIEW", "COMPLETED"})
        self.assertIn("DSAI3V-WP12", state["completed_packets"])


if __name__ == "__main__":
    unittest.main()
