from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2_vnext.fsr_rehearsal_strict import run_fsr_c2_vnext_strict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _c1_stream(handoff: list[dict]) -> list[dict]:
    output: list[dict] = []
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            group = sorted(
                (item for item in handoff if item["clock_id"] == clock and item["price_side"] == side),
                key=lambda item: item["open_time"],
            )
            prior = None
            for current in group:
                output.append(dataclasses.asdict(build_c1(current, prior)))
                prior = current
    return output


class FSRWP4Tests(unittest.TestCase):
    def test_actual_c1_lineage_reaches_complete_revised_c2_shadow_topology(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            opt_a = build_opt_a_fixture(Path(root) / "fixture", repo_root=REPO_ROOT)
            c1 = _c1_stream(c1_handoff_records(opt_a))
            first = run_fsr_c2_vnext_strict(opt_a, c1)
            second = run_fsr_c2_vnext_strict(opt_a, c1)

            self.assertEqual(first["logical_sha256"], second["logical_sha256"])
            self.assertEqual(first["population"]["expected_slot_count"], 192)
            self.assertEqual(first["population"]["observation_count"], 192)
            self.assertEqual(first["population"]["evidence_counts"].get("PRESENT_COMPLETE"), 190)
            self.assertEqual(first["population"]["evidence_counts"].get("ABSENT"), 2)
            self.assertGreaterEqual(first["population"]["continuity_counts"].get("GAP_RESET", 0), 2)
            self.assertGreaterEqual(first["continuity_reset_count"], 2)
            self.assertEqual(first["cross_segment_transition_count"], 0)
            self.assertEqual(first["chronology"]["cross_segment_transitions"], 0)
            self.assertGreater(first["snapshot_count"], 8)
            self.assertEqual(first["axis_output_count"], first["snapshot_count"] * 5)
            self.assertGreater(first["transition_count"], 0)
            self.assertGreater(first["detector_counts"]["touch"], 0)
            self.assertGreater(first["horizon_template_count"], 0)
            self.assertTrue(first["chronology"]["all_c2_first_valid_not_before_interval_end"])
            self.assertTrue(first["chronology"]["all_formula_as_of_not_after_snapshot"])
            self.assertFalse(first["chronology"]["hidden_construction_consumed"])
            self.assertTrue(first["scope_assurance"]["all_measurement_relation_sets_have_one_container_relation"])
            self.assertGreaterEqual(first["scope_assurance"]["structural_container_exclusions"], 0)
            self.assertEqual(first["authority"]["active_selector"], "NONE")
            self.assertEqual(first["authority"]["validation_consumption"], "DENIED")
            self.assertEqual(first["authority"]["semantic_event_episode_promotion"], "NONE")
            self.assertEqual(first["authority"]["release_publication"], "NONE")
            self.assertEqual(first["computability_denominator"]["authority"], "SHADOW_FROZEN_READ_ONLY")
            self.assertTrue(all(snapshot["authority"] == "SYNTHETIC_SHADOW_NON_PROMOTABLE" for snapshot in first["snapshots"]))
            self.assertTrue(all(snapshot["formula_bundle"]["active"] is False for snapshot in first["snapshots"]))
            self.assertTrue(all(snapshot["formula_bundle"]["canonical"] is False for snapshot in first["snapshots"]))


if __name__ == "__main__":
    unittest.main()
