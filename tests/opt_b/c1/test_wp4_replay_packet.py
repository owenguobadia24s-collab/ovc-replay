from __future__ import annotations

import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/opt_b/run_c1_wp4_replay.py"
WORKFLOW = ROOT / ".github/workflows/opt-b-c1-wp4-market-replay.yml"

spec = importlib.util.spec_from_file_location("c1_wp4_replay", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class C1WP4ReplayPacketTests(unittest.TestCase):
    def test_packet_binds_exact_approved_scope(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("run-id: 30179286521", text)
        self.assertIn("a2-g3-opt-a-gbpusd-discovery-2021-2023-v2", text)
        self.assertIn("a2-g3-opt-a-gbpusd-development-2024-v2", text)
        self.assertNotIn("a2-g3-opt-a-gbpusd-validation-2025", text)
        self.assertIn("LOCKED_UNCONSUMED", text)

    def test_current_bar_geometry_and_no_prior_are_explicit(self) -> None:
        meta = module.ROLES["discovery"]
        row = {"timestamp":"1609459200000","open":"1.20000","high":"1.20100","low":"1.19900","close":"1.20050","volume":"1"}
        record, rejection = module.build_record(meta=meta, clock="15M", side="BID", source_path="canonical/x.csv", row=row, prior=None)
        self.assertIsNone(rejection)
        self.assertEqual(record["measurements"]["range_abs"], "0.002")
        self.assertEqual(record["categorical"]["direction"], "UP")
        for field in module.PRIOR_FIELDS:
            self.assertEqual(record["null_reasons"][field], "NO_PRIOR_BAR")
        self.assertTrue(record["record_id"].startswith("c1:"))

    def test_gap_is_not_bridged(self) -> None:
        meta = module.ROLES["development"]
        prior = {"release_id":meta["release_id"],"manifest_id":meta["manifest_id"],"clock":"15M","side":"ASK","timestamp":0,"close":Decimal("1.1")}
        row = {"timestamp":1800000,"open":"1.10000","high":"1.10100","low":"1.09900","close":"1.10050","volume":"1"}
        record, _ = module.build_record(meta=meta, clock="15M", side="ASK", source_path="canonical/x.csv", row=row, prior=prior)
        self.assertEqual(record["null_reasons"]["true_range_abs"], "NO_CONTIGUOUS_PRIOR_BAR")

    def test_candidate_has_no_selector_or_downstream_authority(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"market_authority": "NONE"', text)
        self.assertIn('"release_parent_eligibility": "DENIED_PENDING_FREEZE"', text)
        self.assertIn('"selector_activation": "NONE"', text)
        self.assertIn('"c2_consumption": "DENIED"', text)


if __name__ == "__main__":
    unittest.main()
