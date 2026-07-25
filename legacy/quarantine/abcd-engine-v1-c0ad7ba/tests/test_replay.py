from __future__ import annotations

from datetime import timedelta
import unittest

from test_contracts import baseline, bar
from ovc_opt_b import contiguous_segments, replay_unlevelled_terms


class ReplayTests(unittest.TestCase):
    def test_gap_creates_separate_segments(self) -> None:
        bars = baseline(30)
        shifted = []
        for item in bars[25:]:
            shifted.append(type(item)(
                bar_id="shifted-" + item.bar_id,
                instrument_id=item.instrument_id,
                timeframe=item.timeframe,
                open_time=item.open_time + timedelta(minutes=15),
                close_time=item.close_time + timedelta(minutes=15),
                open=item.open, high=item.high, low=item.low, close=item.close,
                price_increment=item.price_increment,
            ))
        segments = contiguous_segments(bars[:25] + shifted)
        self.assertEqual(tuple(map(len, segments)), (25, 5))

    def test_replay_does_not_bridge_short_segment(self) -> None:
        bars = baseline(30)
        replay = replay_unlevelled_terms(bars)
        self.assertEqual(replay.segment_lengths, (30,))
        self.assertEqual(len(replay.records), 11)  # 9 displacement + 2 compression candidates


if __name__ == "__main__":
    unittest.main()
