from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import unittest

from test_contracts import baseline
from ovc_opt_b import build_level_registry, replay_complete_terms


class CompleteReplayTests(unittest.TestCase):
    def test_every_materialized_level_record_uses_an_eligible_level(self) -> None:
        bars = baseline(45)
        registry = build_level_registry(bars)
        replay = replay_complete_terms(bars, registry)
        by_id = {level.level_id: level for level in registry.levels}

        self.assertGreater(replay.coverage["eligible_directional_level_bar_evaluations"], 0)
        self.assertEqual(
            [record.term_record_id for record in replay.term_records],
            [record.term_record_id for record in replay_complete_terms(bars, registry).term_records],
        )
        for record in replay.term_records:
            if record.reference_level_id is None:
                continue
            self.assertLessEqual(by_id[record.reference_level_id].first_valid_time, record.anchor_time)

    def test_replay_never_bridges_a_source_gap(self) -> None:
        first = baseline(32)
        shift = timedelta(hours=12)
        second = [
            replace(
                candidate,
                bar_id=f"g{candidate.bar_id}",
                open_time=candidate.open_time + shift,
                close_time=candidate.close_time + shift,
            )
            for candidate in baseline(32)
        ]
        bars = first + second
        registry = build_level_registry(bars)
        replay = replay_complete_terms(bars, registry)
        first_ids = {bar.bar_id for bar in first}
        second_ids = {bar.bar_id for bar in second}

        for record in (*replay.term_records, *replay.transition_records):
            ids = set(record.input_bar_ids)
            self.assertTrue(ids <= first_ids or ids <= second_ids)


if __name__ == "__main__":
    unittest.main()
