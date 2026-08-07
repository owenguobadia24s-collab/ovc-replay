from __future__ import annotations

import unittest

from ovc.opt_b.srfd.segmentation import (
    SegmentationError, TemporalMode, assert_temporal_join_allowed, censor_segment,
    directional_change, lineage_event, order_boundary_events, pelt_reference, segment_runs,
)


class SRFDIWP3SegmentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.states = [
            {"record_id":"S1","first_valid_time":"2026-06-01T00:00:00Z","state":"A"},
            {"record_id":"S2","first_valid_time":"2026-06-01T02:00:00Z","state":"A"},
            {"record_id":"S3","first_valid_time":"2026-06-01T04:00:00Z","state":"B"},
            {"record_id":"S4","first_valid_time":"2026-06-01T06:00:00Z","state":"B"},
            {"record_id":"S5","first_valid_time":"2026-06-01T08:00:00Z","state":"A"},
        ]

    def test_run_change_is_causal_and_input_order_independent(self) -> None:
        first = segment_runs(self.states,state_field="state")
        second = segment_runs(reversed(self.states),state_field="state")
        self.assertEqual(first,second)
        self.assertEqual(TemporalMode.ONLINE_CAUSAL.value,first["temporal_mode"])
        self.assertEqual([2,2,1],[len(item["member_record_ids"]) for item in first["segments"]])
        self.assertEqual("2026-06-01T04:00:00Z",first["boundary_events"][0]["first_valid_time"])

    def test_directional_change_does_not_backdate_first_valid(self) -> None:
        prices = [
            {"record_id":"P1","first_valid_time":"2026-06-01T00:00:00Z","price":"100"},
            {"record_id":"P2","first_valid_time":"2026-06-01T01:00:00Z","price":"103"},
            {"record_id":"P3","first_valid_time":"2026-06-01T02:00:00Z","price":"99"},
        ]
        result = directional_change(prices,value_field="price",threshold="2")
        self.assertEqual(TemporalMode.CONFIRMATION_DELAYED.value,result["temporal_mode"])
        self.assertTrue(result["boundary_events"])
        first = result["boundary_events"][0]
        self.assertLessEqual(first["onset_time"],first["first_valid_time"])
        self.assertNotEqual(first["onset_record_id"],first["confirmation_record_id"])

    def test_pelt_reference_is_retrospective_only(self) -> None:
        result = pelt_reference([0,0,0,10,10,10],penalty="1")
        self.assertEqual(TemporalMode.RETROSPECTIVE.value,result["temporal_mode"])
        self.assertIn(3,result["changepoints"])
        with self.assertRaisesRegex(SegmentationError,"QA_RETROSPECTIVE_ISOLATION_FAILURE"):
            assert_temporal_join_allowed(result["temporal_mode"],TemporalMode.ONLINE_CAUSAL)
        assert_temporal_join_allowed(result["temporal_mode"],TemporalMode.RETROSPECTIVE)

    def test_split_merge_and_nesting_lineage_is_append_only_and_stable(self) -> None:
        split = lineage_event("split",parent_ids=["P"],child_ids=["C2","C1"])
        split2 = lineage_event("split",parent_ids=["P"],child_ids=["C1","C2"])
        self.assertEqual(split,split2); self.assertTrue(split["append_only"])
        merge = lineage_event("merge",parent_ids=["P2","P1"],child_ids=["C"])
        nest = lineage_event("nest",parent_ids=["OUTER"],child_ids=["INNER"])
        self.assertEqual("MERGE",merge["relation"]); self.assertEqual("NEST",nest["relation"])

    def test_release_and_gap_censor_preserve_reason(self) -> None:
        segment = segment_runs(self.states[:2],state_field="state")["segments"][0]
        release = censor_segment(segment,reason="C2E_RELEASE_END_CENSOR")
        gap = censor_segment(segment,reason="SOURCE_GAP")
        self.assertTrue(release["censored"]); self.assertEqual("C2E_RELEASE_END_CENSOR",release["censor_reason"])
        self.assertEqual("SOURCE_GAP",gap["censor_reason"])

    def test_simultaneous_boundary_order_is_deterministic(self) -> None:
        events = [
            {"boundary_id":"B2","event_type":"Z","first_valid_time":"2026-06-01T02:00:00Z"},
            {"boundary_id":"B1","event_type":"A","first_valid_time":"2026-06-01T02:00:00Z"},
        ]
        self.assertEqual(["B1","B2"],[item["boundary_id"] for item in order_boundary_events(reversed(events))])


if __name__ == "__main__":
    unittest.main()
