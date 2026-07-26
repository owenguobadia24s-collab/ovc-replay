from __future__ import annotations

import json
import unittest
from copy import deepcopy

from ovc.opt_b.c1 import AUTHORITY_STATE, InputRejected, build, dumps, validate


def bar(**overrides):
    payload = {
        "release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "manifest_id": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "research_role": "DISCOVERY",
        "instrument_id": "GBPUSD",
        "clock_id": "15M",
        "price_side": "BID",
        "source_bar_id": "bar-001",
        "open_time": "2023-01-03T00:15:00Z",
        "close_time": "2023-01-03T00:30:00Z",
        "first_valid_time": "2023-01-03T00:30:00Z",
        "open": "1.2500", "high": "1.2550", "low": "1.2480", "close": "1.2540",
        "price_increment": "0.0001",
        "admissibility": "HANDOFF_ELIGIBLE", "quality_state": "COMPLETE",
        "synthetic": True, "selector_state": "NONE", "authority_state": "NONE",
        "validation_consumption_state": "NOT_APPLICABLE",
        "parent_source_object_ids": ["src-1"], "parent_m1_bar_ids": [f"m1-{i}" for i in range(15)],
    }
    payload.update(overrides)
    return payload


class C1WP3ReferenceEngineTests(unittest.TestCase):
    def test_reference_engine_remains_trusted_after_later_gates(self) -> None:
        self.assertIn(AUTHORITY_STATE, {
            "WP3_REFERENCE_ENGINE_FIXTURE_TRUST_PASS",
            "WP4_REPLAY_QA_PASS_LOCAL_CANDIDATE",
            "B1_G1_CANDIDATE_INVENTORY_ACCEPTED_FREEZE_AUTHORISED",
            "B1_G2_PUBLICATION_READY_WP5_AUTHORISED",
            "B1_G5_SHADOW_SELECTED_C2_DENIED",
        })

    def test_exact_decimal_geometry_and_determinism(self) -> None:
        result = build(bar())
        validate(result)
        self.assertEqual(result.measurements["range_abs"], "0.007")
        self.assertEqual(result.measurements["range_ticks"], "70")
        self.assertEqual(result.measurements["body_signed"], "0.004")
        self.assertEqual(result.categorical["direction"], "UP")
        self.assertEqual(dumps(result), dumps(build(bar())))
        self.assertEqual(result.record_id, build(deepcopy(bar())).record_id)

    def test_contiguous_prior_close_fields(self) -> None:
        current = bar()
        prior = bar(source_bar_id="bar-000", open_time="2023-01-03T00:00:00Z", close_time="2023-01-03T00:15:00Z", first_valid_time="2023-01-03T00:15:00Z", close="1.2500")
        result = build(current, prior)
        validate(result)
        self.assertEqual(result.measurements["close_change"], "0.004")
        self.assertEqual(result.measurements["open_gap"], "0")
        self.assertEqual(result.measurements["true_range_abs"], "0.007")

    def test_gap_does_not_search_or_bridge(self) -> None:
        prior = bar(source_bar_id="bar-old", open_time="2023-01-02T23:45:00Z", close_time="2023-01-03T00:00:00Z", first_valid_time="2023-01-03T00:00:00Z")
        result = build(bar(), prior)
        self.assertEqual(result.null_reasons["close_change"], "NO_CONTIGUOUS_PRIOR_BAR")
        self.assertEqual(result.null_reasons["true_range_abs"], "NO_CONTIGUOUS_PRIOR_BAR")

    def test_zero_range_has_explicit_nulls(self) -> None:
        result = build(bar(open="1.25", high="1.25", low="1.25", close="1.25"))
        validate(result)
        self.assertEqual(result.categorical["direction"], "FLAT")
        self.assertEqual(result.measurements["range_abs"], "0")
        self.assertIsNone(result.measurements["body_utilisation"])
        self.assertEqual(result.null_reasons["body_utilisation"], "ZERO_RANGE")

    def test_control_clock_validation_and_legacy_parent_rejected(self) -> None:
        with self.assertRaisesRegex(InputRejected, "CONTROL_CLOCK_NOT_AUTHORISED"):
            build(bar(clock_id="H1_PROVIDER_NATIVE"))
        with self.assertRaisesRegex(InputRejected, "PROHIBITED_PARENT_RELEASE"):
            build(bar(release_id="OPT-A.GBPUSD.2026H1.v1"))
        with self.assertRaisesRegex(InputRejected, "VALIDATION_LOCKED"):
            build(bar(release_id="OPT-A.GBPUSD.VALIDATION.2025.v2", research_role="VALIDATION", validation_consumption_state="LOCKED_UNCONSUMED"))

    def test_side_mismatch_cannot_supply_prior_close(self) -> None:
        prior = bar(source_bar_id="bar-000", open_time="2023-01-03T00:00:00Z", close_time="2023-01-03T00:15:00Z", first_valid_time="2023-01-03T00:15:00Z", price_side="ASK")
        result = build(bar(), prior)
        self.assertEqual(result.null_reasons["open_gap"], "PRIOR_IDENTITY_MISMATCH")

    def test_serialization_has_no_runtime_or_machine_identity(self) -> None:
        payload = json.loads(dumps(build(bar())))
        self.assertNotIn("created_at", payload)
        self.assertNotIn("local_path", payload)
        self.assertEqual(payload["authority_state"], "NONE")
        self.assertTrue(payload["synthetic"])


if __name__ == "__main__":
    unittest.main()
