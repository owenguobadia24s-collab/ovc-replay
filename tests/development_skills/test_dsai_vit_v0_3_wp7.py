from __future__ import annotations

import unittest

from ovc.development.skills.vit_historical_replay import HistoricalReplayEvent, replay_historical_events, require_q2_source_completeness


class DsaiVitV03Wp7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = (
            HistoricalReplayEvent("e1","esli-wp7-requeue","ESLI","WP7","STALE_MAIN_REQUEUE",discarded_assurance_cycles=2,reconciliation_attempts=2,operator_interventions=1,placement_only_recomputable=True),
            HistoricalReplayEvent("e2","dsai3-wp0-baseline","DSAI3","WP0","STACKED_PR_RECONCILIATION",discarded_assurance_cycles=1,reconciliation_attempts=1,operator_interventions=1,placement_only_recomputable=True),
            HistoricalReplayEvent("e3","dmrpi-wp0-recon","DMRPI","WP0","CLOSEOUT_FRONTIER_MOVEMENT",discarded_assurance_cycles=1,reconciliation_attempts=1,operator_interventions=1,placement_only_recomputable=True),
            HistoricalReplayEvent("e4","dsai-throughput-plan","DSAI","PORTFOLIO","MULTI_LANE_PERIOD",discarded_assurance_cycles=0,reconciliation_attempts=0,operator_interventions=0,payload_rebuild_required=False),
            HistoricalReplayEvent("e5","siq-g1","SIQ","G1","OPERATOR_AUTHORITY_BOUNDARY",operator_interventions=1),
        )

    def test_q2_replay_is_deterministic_and_authority_source_bound(self) -> None:
        first = replay_historical_events(self.events)
        second = replay_historical_events(reversed(self.events))
        self.assertEqual(first.report_id,second.report_id)
        self.assertEqual(first.authority_inference_count,0)
        self.assertEqual(first.discarded_assurance_cycles,4)
        self.assertEqual(first.projected_placement_only_recomputations,3)
        self.assertEqual(first.projected_operator_interventions,1)

    def test_required_historical_classes_are_complete(self) -> None:
        report = replay_historical_events(self.events)
        self.assertTrue(require_q2_source_completeness(report,("STALE_MAIN_REQUEUE","STACKED_PR_RECONCILIATION","CLOSEOUT_FRONTIER_MOVEMENT","MULTI_LANE_PERIOD")))

    def test_authority_inference_blocks_q2_completeness(self) -> None:
        bad = self.events + (HistoricalReplayEvent("e6","unknown","X","Y","STALE_MAIN_REQUEUE",authority_source_explicit=False),)
        report = replay_historical_events(bad)
        self.assertFalse(require_q2_source_completeness(report,("STALE_MAIN_REQUEUE",)))


if __name__ == "__main__":
    unittest.main()
