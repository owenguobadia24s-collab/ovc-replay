from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1" / "market.json"

ORIGINAL_WP2_BARS = [
    {"t": "2026-01-01T08:00:00Z", "o": 1.2700, "h": 1.2712, "l": 1.2694, "c": 1.2708},
    {"t": "2026-01-01T08:15:00Z", "o": 1.2708, "h": 1.2721, "l": 1.2702, "c": 1.2717},
    {"t": "2026-01-01T08:30:00Z", "o": 1.2717, "h": 1.2724, "l": 1.2709, "c": 1.2711},
    {"t": "2026-01-01T08:45:00Z", "o": 1.2711, "h": 1.2730, "l": 1.2708, "c": 1.2727},
]


class WP3DVisualFixtureTests(unittest.TestCase):
    def test_density_enrichment_is_additive_and_non_evidentiary(self) -> None:
        payload = json.loads(MARKET.read_text(encoding="utf-8"))
        self.assertEqual("SYNTHETIC_FIXTURE", payload["source"])
        self.assertTrue(payload["not_market_evidence"])
        self.assertGreaterEqual(len(payload["bars"]), 32)
        self.assertEqual(ORIGINAL_WP2_BARS, payload["bars"][:4])

    def test_density_bars_are_strictly_chronological_ohlc(self) -> None:
        payload = json.loads(MARKET.read_text(encoding="utf-8"))
        timestamps = [bar["t"] for bar in payload["bars"]]
        self.assertEqual(sorted(timestamps), timestamps)
        self.assertEqual(len(timestamps), len(set(timestamps)))
        for bar in payload["bars"]:
            self.assertGreaterEqual(bar["h"], max(bar["o"], bar["c"]))
            self.assertLessEqual(bar["l"], min(bar["o"], bar["c"]))


if __name__ == "__main__":
    unittest.main()
