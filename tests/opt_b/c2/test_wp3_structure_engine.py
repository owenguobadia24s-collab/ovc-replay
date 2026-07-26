from __future__ import annotations

import copy
import unittest
from datetime import datetime, timedelta, timezone

from ovc.opt_b.c2.adapter import HandoffError, accept_c1_record
from ovc.opt_b.c2.containers import build_containers
from ovc.opt_b.c2.levels import build_levels
from ovc.opt_b.c2.relations import build_relation_set


def parent(index: int = 0, *, close: str = "1.1075") -> dict:
    start = datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index)
    end = start + timedelta(minutes=15)
    measurements = {
        "range_abs": "0.0100",
        "range_ticks": "1000",
        "body_signed": "0.0025",
        "body_abs": "0.0025",
        "body_utilisation": "0.25",
        "upper_wick_abs": "0.0025",
        "lower_wick_abs": "0.0050",
        "upper_wick_share": "0.25",
        "lower_wick_share": "0.50",
        "wick_balance": "-0.25",
        "open_location": "0.50",
        "close_location": "0.75",
        "signed_efficiency": "0.25",
        "true_range_abs": "0.0100",
        "true_range_ticks": "1000",
        "close_change": "0.0001",
        "open_gap": "0",
    }
    return {
        "c1_record_id": f"c1:{index:064x}",
        "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_manifest_id": "MANIFEST.C1.TEST",
        "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "opt_a_manifest_id": "MANIFEST.OPT-A.TEST",
        "opt_a_manifest_sha256": "0" * 64,
        "role": "DISCOVERY",
        "authority_state": "ACTIVE_DISCOVERY",
        "instrument": "GBPUSD",
        "clock": "15M",
        "side": "BID",
        "open_time": start.isoformat().replace("+00:00", "Z"),
        "close_time": end.isoformat().replace("+00:00", "Z"),
        "first_valid_time": end.isoformat().replace("+00:00", "Z"),
        "source_path": "canonical/15M/BID/2023-01.csv",
        "source_bar_id": f"opt-a:{index:064x}",
        "measurements": measurements,
        "categorical": {"direction": "UP"},
        "null_reasons": {},
        "quality_state": "EXACT_C1_AND_OPT_A_PARENT_VERIFIED",
        "prices": {"open": "1.1050", "high": "1.1100", "low": "1.1000", "close": close},
    }


class WP3StructureTrustTests(unittest.TestCase):
    def test_adapter_rejects_validation(self):
        value = parent()
        value["role"] = "VALIDATION"
        value["authority_state"] = "ACTIVE_VALIDATION"
        with self.assertRaises(HandoffError):
            accept_c1_record(value)

    def test_adapter_rejects_future_leakage(self):
        value = parent()
        value["future_outcome"] = "UP"
        with self.assertRaises(HandoffError):
            accept_c1_record(value)

    def test_levels_are_rolling_first_valid_and_deterministic(self):
        history = [parent(index) for index in range(32)]
        one = build_levels(history[-1], history)
        two = build_levels(copy.deepcopy(history[-1]), copy.deepcopy(history))
        self.assertEqual(one, two)
        self.assertEqual({item["level_type"] for item in one}, {"SWING_HIGH", "SWING_LOW", "RANGE_HIGH", "RANGE_LOW", "MIDPOINT"})
        active = [item for item in one if item["status"] == "ACTIVE"]
        self.assertEqual({item["level_type"] for item in active}, {"RANGE_HIGH", "RANGE_LOW", "MIDPOINT"})
        self.assertTrue(all(item["c2_level_id"].startswith("c2-level:") for item in active))

    def test_containers_preserve_eligible_and_excluded_boundaries(self):
        history = [parent(index) for index in range(32)]
        levels = build_levels(history[-1], history)
        built = build_containers(history[-1], levels)
        self.assertEqual({item["container_type"] for item in built}, {"LOCAL_RANGE", "PARENT_RANGE", "SWING_ENVELOPE"})
        local = next(item for item in built if item["container_type"] == "LOCAL_RANGE")
        self.assertEqual(local["status"], "ACTIVE")
        parent_range = next(item for item in built if item["container_type"] == "PARENT_RANGE")
        self.assertEqual(parent_range["status"], "EXCLUDED")

    def test_relation_set_is_complete_without_hidden_selection(self):
        history = [parent(index) for index in range(32)]
        value = history[-1]
        levels = build_levels(value, history)
        containers = build_containers(value, levels)
        result = build_relation_set(value, levels, containers, history[-2])
        self.assertTrue(result["complete_inventory"])
        self.assertEqual(len(result["relations"]) + len(result["exclusions"]), len(levels) + len(containers))
        self.assertNotIn("winning_level", result)

    def test_inverted_declared_boundaries_are_visible_conflict(self):
        value = parent()
        levels = [
            {"level_type": "RANGE_LOW", "status": "ACTIVE", "value": "1.2", "c2_level_id": "low", "first_valid_time": value["first_valid_time"]},
            {"level_type": "RANGE_HIGH", "status": "ACTIVE", "value": "1.1", "c2_level_id": "high", "first_valid_time": value["first_valid_time"]},
        ]
        built = build_containers(value, levels)
        local = next(item for item in built if item["container_type"] == "LOCAL_RANGE")
        self.assertEqual(local["status"], "CONFLICT")


if __name__ == "__main__":
    unittest.main()
