from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.research_operations.v0_3.computability import (
    ComputabilityAccessDenied,
    ComputabilityContractError,
    build_computability_profile,
    build_null_reason_profile,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/v0_3/wp2_computability_and_diff_cases.json").read_text(encoding="utf-8")
)


def source(**overrides):
    value = copy.deepcopy(FIXTURE["source"])
    value.update(overrides)
    return value


def prior(**overrides):
    value = copy.deepcopy(FIXTURE["prior"])
    value.update(overrides)
    return value


def record(**overrides):
    value = copy.deepcopy(FIXTURE["record"])
    value.update(overrides)
    return value


class C1ComputabilityTests(unittest.TestCase):
    def test_lawful_record_profile_is_deterministic(self) -> None:
        first = build_computability_profile(record(), source(), prior())
        second = build_computability_profile(record(), source(), prior())
        self.assertEqual(first, second)
        self.assertEqual(first["prior_close_computability"], "COMPUTABLE")
        self.assertEqual(first["field_null_consistency"], "PASS")
        self.assertEqual(first["writes"], "NONE")

    def test_zero_range_preserves_absolute_geometry_and_nulls_only_registered_ratios(self) -> None:
        values = record()["measurements"]
        for field in [
            "range_abs", "range_ticks", "body_signed", "body_abs",
            "upper_wick_abs", "lower_wick_abs", "true_range_abs",
            "true_range_ticks", "close_change", "open_gap",
        ]:
            values[field] = "0"
        null_fields = [
            "body_utilisation", "upper_wick_share", "lower_wick_share",
            "wick_balance", "open_location", "close_location", "signed_efficiency",
        ]
        for field in null_fields:
            values[field] = None
        result = build_computability_profile(
            record(
                measurements=values,
                categorical={"direction": "FLAT"},
                null_reasons={field: "ZERO_RANGE" for field in null_fields},
            ),
            source(open="1.25", high="1.25", low="1.25", close="1.25"),
            prior(close="1.25"),
        )
        self.assertEqual(result["range_computability"], "ZERO_RANGE")
        self.assertEqual(result["null_reason_counts"], {"ZERO_RANGE": 7})

    def test_prior_close_never_bridges_gap(self) -> None:
        values = record()["measurements"]
        prior_fields = ["true_range_abs", "true_range_ticks", "close_change", "open_gap"]
        for field in prior_fields:
            values[field] = None
        result = build_computability_profile(
            record(
                measurements=values,
                null_reasons={field: "NO_CONTIGUOUS_PRIOR_BAR" for field in prior_fields},
            ),
            source(),
            prior(close_time="2023-01-03T00:00:00Z"),
        )
        self.assertEqual(result["prior_close_reason"], "NO_CONTIGUOUS_PRIOR_BAR")

    def test_prior_identity_mismatch_never_supplies_values(self) -> None:
        values = record()["measurements"]
        prior_fields = ["true_range_abs", "true_range_ticks", "close_change", "open_gap"]
        for field in prior_fields:
            values[field] = None
        result = build_computability_profile(
            record(
                measurements=values,
                null_reasons={field: "PRIOR_IDENTITY_MISMATCH" for field in prior_fields},
            ),
            source(),
            prior(price_side="ASK"),
        )
        self.assertEqual(result["prior_close_reason"], "PRIOR_IDENTITY_MISMATCH")

    def test_unknown_null_reason_non_finite_and_missing_reason_fail_closed(self) -> None:
        values = record()["measurements"]
        values["body_abs"] = None
        with self.assertRaises(ComputabilityContractError):
            build_computability_profile(
                record(measurements=values, null_reasons={"body_abs": "MYSTERY"}),
                source(),
                prior(),
            )
        values = record()["measurements"]
        values["body_abs"] = "NaN"
        with self.assertRaises(ComputabilityContractError):
            build_computability_profile(record(measurements=values), source(), prior())
        values = record()["measurements"]
        values["body_abs"] = None
        with self.assertRaises(ComputabilityContractError):
            build_computability_profile(record(measurements=values), source(), prior())

    def test_source_inadmissible_emits_no_record_and_validation_denies_before_resolution(self) -> None:
        profile = build_computability_profile(None, source(admissibility="QUARANTINED"))
        self.assertEqual(profile["record_emission"], "NO_RECORD")
        self.assertEqual(profile["record_emission_reason"], "SOURCE_BAR_INADMISSIBLE")
        with self.assertRaises(ComputabilityContractError):
            build_computability_profile(record(), source(admissibility="QUARANTINED"))
        with self.assertRaises(ComputabilityAccessDenied):
            build_computability_profile(None, source(research_role="VALIDATION", path="forbidden"))

    def test_null_reason_profile_is_role_scoped_and_input_order_independent(self) -> None:
        emitted = build_computability_profile(record(), source(), prior())
        rejected = build_computability_profile(
            None,
            source(source_bar_id="bad-bar", admissibility="QUARANTINED"),
        )
        first = build_null_reason_profile([emitted, rejected])
        second = build_null_reason_profile([rejected, emitted])
        self.assertEqual(first, second)
        self.assertEqual(first["record_emission_counts"], {"EMITTED": 1, "SOURCE_BAR_INADMISSIBLE": 1})


if __name__ == "__main__":
    unittest.main()
