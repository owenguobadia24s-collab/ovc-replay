from __future__ import annotations

import unittest

from ovc.development.skills.vit_budget import LanePacketObservation, measure_q4
from ovc.development.skills.vit_core import VitContractError


class DsaiVitV03Wp8BTests(unittest.TestCase):
    def _obs(self):
        rows = []
        for lane in ("L1", "L2", "L3"):
            for i in (1, 2):
                rows.append(LanePacketObservation(lane, f"{lane}-P{i}", 1.0 + i, 0.2, 0.5 + i, 0.1, 1000 + i, 2000 + i, "PLACEMENT_RECOMPUTE_ONLY" if i == 1 else "ASSURANCE_RENEWAL_REQUIRED", safe_bypass_exercised=(lane == "L1" and i == 2), restart_exercised=(lane == "L2" and i == 2), external_reanchor_exercised=(lane == "L3" and i == 2)))
        return tuple(rows)

    def test_three_lane_two_packet_measured_report_passes(self) -> None:
        report = measure_q4(self._obs())
        self.assertTrue(report.passes)
        self.assertEqual(report.budget.lane_count, 3)
        self.assertEqual(report.budget.min_packets_per_lane, 2)
        self.assertEqual(report.budget.source, "MEASURED_Q4_OBSERVATIONS")

    def test_insufficient_lane_depth_fails_closed(self) -> None:
        with self.assertRaises(VitContractError):
            measure_q4(self._obs()[:4])

    def test_false_authority_or_reference_disagreement_blocks(self) -> None:
        rows = list(self._obs())
        first = rows[0]
        rows[0] = LanePacketObservation(**{**first.__dict__, "false_authority_allow": True})
        self.assertFalse(measure_q4(rows).passes)
        rows = list(self._obs())
        first = rows[0]
        rows[0] = LanePacketObservation(**{**first.__dict__, "reference_optimized_equal": False})
        self.assertFalse(measure_q4(rows).passes)


if __name__ == "__main__":
    unittest.main()
