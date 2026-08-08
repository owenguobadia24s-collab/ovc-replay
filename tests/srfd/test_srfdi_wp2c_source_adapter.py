from __future__ import annotations

from copy import deepcopy
import unittest

from ovc.opt_b.srfd.source_adapter import (
    C2SourceBinding,
    SourceAdapterError,
    adapt_c2_state,
    adapt_c2_to_c2e_input,
    bind_source_population,
    build_c1_parent_index,
)


SOURCE_MANIFEST = "1" * 64
OUTPUT_MANIFEST = "2" * 64


def binding() -> C2SourceBinding:
    return C2SourceBinding(
        source_release_id="PD-JUNE-FM.RUN.fixture",
        source_commit="abc123",
        source_slice_id="RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1",
        source_manifest_sha256=SOURCE_MANIFEST,
        output_manifest_sha256=OUTPUT_MANIFEST,
        active_c2_model_release_id="OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        benchmark_start_inclusive_utc="2026-06-01T00:00:00Z",
        benchmark_end_exclusive_utc="2026-07-01T00:00:00Z",
        context_start_utc="2026-05-30T00:00:00Z",
        context_end_exclusive_utc="2026-07-03T00:00:00Z",
    )


def c1(record_id: str, open_time: str, close_time: str, *, clock: str = "15M", side: str = "BID") -> dict[str, object]:
    target = "2026-06-01T00:00:00Z" <= open_time < "2026-07-01T00:00:00Z"
    classification = "TARGET_JUNE" if target else "CONTEXT_PRE_TARGET" if open_time < "2026-06-01T00:00:00Z" else "CONTEXT_POST_TARGET"
    return {
        "c1_record_id": record_id,
        "first_valid_time": close_time,
        "open_time": open_time,
        "close_time": close_time,
        "clock": clock,
        "side": side,
        "source_slice_id": binding().source_slice_id,
        "source_manifest_sha256": SOURCE_MANIFEST,
        "eligibility_class": classification,
        "target_eligible": target,
        "operation_mode": "TIME_GATED_REPLAY",
        "role": "DISCOVERY",
        "measurements": {},
        "categorical": {},
    }


def axes() -> dict[str, dict[str, object]]:
    return {
        "LOCATION": {"status": "EVALUATED", "value": "MID_REGION", "measurement": "0.5"},
        "MOTION": {"status": "EVALUATED", "value": "UP_STALL", "measurement": "0.2"},
        "ORGANISATION": {"status": "EVALUATED", "value": "FORMING", "measurement": "0.4"},
        "INTERACTION": {"status": "EVALUATED", "value": "APPROACHING", "measurement": "0.01"},
        "QUALITY": {"status": "EVALUATED", "value": "COMPLETE"},
    }


def c2(record_id: str, parent: dict[str, object], *, scope: str = "GBPUSD-15M-LOCAL-v0.1") -> dict[str, object]:
    return {
        "active_c2_model_release_id": binding().active_c2_model_release_id,
        "axes": axes(),
        "c1_manifest_id": "C1.MANIFEST",
        "c1_release_id": "C1.RELEASE",
        "c2_state_id": record_id,
        "clock": parent["clock"],
        "container_ids": ["container.b", "container.a"],
        "continuity": "CONTIGUOUS",
        "eligibility_class": parent["eligibility_class"],
        "evaluation_scope_id": scope,
        "first_valid_time": parent["first_valid_time"],
        "level_ids": ["level.b", "level.a"],
        "live_prospective_append": "DENIED",
        "operation_mode": "TIME_GATED_REPLAY",
        "opt_a_manifest_id": "A.MANIFEST",
        "opt_a_release_id": "A.RELEASE",
        "parameter_pack_id": "C2.PACK",
        "parent_c1_record_id": parent["c1_record_id"],
        "parent_opt_a_bar_id": "BAR.1",
        "persistence": {"LOCATION": 1},
        "relation_set_id": "REL.1",
        "release_membership": False,
        "role": "DISCOVERY",
        "side": parent["side"],
        "source_slice_id": binding().source_slice_id,
        "target_eligible": parent["target_eligible"],
    }


class SRFDIWP2CSourceAdapterTests(unittest.TestCase):
    def test_target_membership_is_reproduced_from_parent_observation_open_time(self) -> None:
        parent = c1("C1.END", "2026-06-30T23:45:00Z", "2026-07-01T00:00:00Z")
        index = build_c1_parent_index([parent], binding())
        adapted = adapt_c2_state(c2("C2.END", parent), binding(), c1_parent_index=index)
        self.assertTrue(adapted["target_eligible"])
        self.assertEqual("2026-07-01T00:00:00Z", adapted["first_valid_time"])
        tampered = c2("C2.BAD", parent)
        tampered["target_eligible"] = False
        tampered["eligibility_class"] = "CONTEXT_POST_TARGET"
        with self.assertRaisesRegex(SourceAdapterError, "QA_NON_REPRODUCIBLE"):
            adapt_c2_state(tampered, binding(), c1_parent_index=index)

    def test_adapter_preserves_native_axes_without_selecting_representation_fields(self) -> None:
        parent = c1("C1.1", "2026-06-10T00:00:00Z", "2026-06-10T00:15:00Z")
        adapted = adapt_c2_state(c2("C2.1", parent), binding(), c1_parent_index=build_c1_parent_index([parent], binding()))
        native_axes = adapted["native_c2"]["axes"]
        expected_axes = axes()
        self.assertEqual(set(expected_axes), set(native_axes))
        for axis, expected in expected_axes.items():
            for key, value in expected.items():
                self.assertEqual(value, native_axes[axis][key])
        self.assertEqual("SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION", adapted["adapter_semantics"])
        self.assertNotIn("structural", adapted)
        self.assertNotIn("structural_raw", adapted)
        self.assertNotIn("structural_normalized", adapted)
        self.assertEqual("MIXED_TYPED_C2", adapted["units"])
        self.assertTrue(adapted["representation_schema"].endswith("GBPUSD-15M-LOCAL-v0.1"))

    def test_missingness_is_retained_in_population_not_globally_zero_imputed_or_excluded(self) -> None:
        parent = c1("C1.2", "2026-06-10T00:15:00Z", "2026-06-10T00:30:00Z")
        row = c2("C2.2", parent)
        row["axes"] = axes()
        row["axes"]["MOTION"] = {"status": "NOT_EVALUATED", "value": None, "reason_code": "NO_CONTIGUOUS_PRIOR_STATE"}
        population = bind_source_population([row], [parent], binding())
        self.assertEqual(1, population["eligible_record_count"])
        self.assertEqual(0, population["exclusion_count"])
        self.assertEqual({"NOT_EVALUATED": 1}, population["computability_counts_within_eligible_population"])
        self.assertEqual("RETAIN_IN_POPULATION_DEFER_TO_FROZEN_REPRESENTATION_COMPUTABILITY", population["missingness_policy"])

    def test_structurally_missing_axis_is_explicit_target_exclusion(self) -> None:
        parent = c1("C1.3", "2026-06-10T00:30:00Z", "2026-06-10T00:45:00Z")
        row = c2("C2.3", parent)
        row["axes"] = axes()
        row["axes"].pop("INTERACTION")
        population = bind_source_population([row], [parent], binding())
        self.assertEqual(0, population["eligible_record_count"])
        self.assertEqual(1, population["exclusion_count"])
        self.assertEqual("REP_REQUIRED_DIMENSION_MISSING", population["exclusions"][0]["reason_code"])

    def test_population_identity_is_order_independent_and_context_is_not_target_exclusion(self) -> None:
        target_parent = c1("C1.T", "2026-06-02T00:00:00Z", "2026-06-02T00:15:00Z")
        context_parent = c1("C1.C", "2026-05-31T23:45:00Z", "2026-06-01T00:00:00Z")
        rows = [c2("C2.T", target_parent), c2("C2.C", context_parent)]
        first = bind_source_population(rows, [target_parent, context_parent], binding())
        second = bind_source_population(reversed(rows), reversed([target_parent, context_parent]), binding())
        self.assertEqual(first["population_id"], second["population_id"])
        self.assertEqual(first["eligible_record_ids_sha256"], second["eligible_record_ids_sha256"])
        self.assertEqual(1, first["eligible_record_count"])
        self.assertEqual(1, first["context_record_count"])
        self.assertEqual(0, first["exclusion_count"])

    def test_lineage_authority_and_forbidden_outcome_tampering_fail_closed(self) -> None:
        parent = c1("C1.4", "2026-06-10T00:45:00Z", "2026-06-10T01:00:00Z")
        index = build_c1_parent_index([parent], binding())
        bad_slice = c2("C2.S", parent)
        bad_slice["source_slice_id"] = "OTHER"
        with self.assertRaisesRegex(SourceAdapterError, "AVAIL_SOURCE_UNAVAILABLE"):
            adapt_c2_state(bad_slice, binding(), c1_parent_index=index)
        bad_release = c2("C2.R", parent)
        bad_release["release_membership"] = True
        with self.assertRaisesRegex(SourceAdapterError, "AUTH_SCOPE_EXPANSION"):
            adapt_c2_state(bad_release, binding(), c1_parent_index=index)
        forbidden = c2("C2.O", parent)
        forbidden["outcome"] = "UP"
        with self.assertRaisesRegex(SourceAdapterError, "AUTH_SCOPE_EXPANSION"):
            adapt_c2_state(forbidden, binding(), c1_parent_index=index)

    def test_neutral_c2e_input_is_deterministic_and_does_not_infer_parent(self) -> None:
        parent = c1("C1.5", "2026-06-10T01:00:00Z", "2026-06-10T01:15:00Z")
        row = c2("C2.5", parent)
        row["continuity"] = "RESET"
        adapted = adapt_c2_state(row, binding(), c1_parent_index=build_c1_parent_index([parent], binding()))
        first = adapt_c2_to_c2e_input(adapted)
        second = adapt_c2_to_c2e_input(deepcopy(adapted))
        self.assertEqual(first, second)
        self.assertIsNone(first.parent_record_id)
        self.assertEqual("C2_SCOPE_RESET", first.reset_reason)
        self.assertEqual("NONE", first.transition_kind)
        self.assertTrue(first.state_key.startswith("C2.STATE."))


if __name__ == "__main__":
    unittest.main()
