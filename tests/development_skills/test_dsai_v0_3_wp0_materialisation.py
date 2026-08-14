from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "registries/implementation/dsai_v0_3"
POINTER = STATE_ROOT / "CURRENT_STATE_POINTER.json"

class DsaiV03Wp0MaterialisationTests(unittest.TestCase):
    def test_legacy_dsai3_route_is_preserved_but_superseded_forward(self) -> None:
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        state = json.loads((STATE_ROOT / pointer["current_state"]).read_text(encoding="utf-8"))
        self.assertEqual(state["programme_id"], "OVC-DSAI-v0.3")
        self.assertEqual(state["status"], "SUPERSEDED")
        self.assertEqual(state["superseded_by_programme"], "OVC-DSAI-VIT-v0.3")
        self.assertTrue(state["historical_evidence_preserved"])
        self.assertIsNone(state["next_packet"])
        self.assertEqual(state["current_authority_effect"], "NONE; parent DSAI v0.2 ORCH-3/4/5 and SIQ remain unchanged")

if __name__ == "__main__":
    unittest.main()
