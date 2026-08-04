from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.relations_vnext import (
    NormalizationScale,
    RelationContractError,
    assert_causal_relation,
    bar_probes,
    build_legacy_relation_crosswalk,
    build_relation_set,
    fixed_object_crossing,
    point_probe,
    reference_change_record,
    relate_point_to_container,
    relate_point_to_level,
    relate_span_to_container,
    relate_span_to_level,
    span_probe,
    temporal_relation_delta,
)

ROOT = Path(__file__).resolve().parents[4]


def level(*, level_id: str = "LEVEL.1", value: float = 1.2, first_valid_time: str = "2026-01-05T01:00:00Z") -> dict:
    return {
        "level_id": level_id,
        "value": value,
        "first_valid_time": first_valid_time,
        "family": "CONFIRMED_PIVOT",
        "level_type": "CONFIRMED_SWING_HIGH",
    }


def container(*, container_id: str = "CONTAINER.1", lower: float = 1.0, upper: float = 2.0, first_valid_time: str = "2026-01-05T01:00:00Z") -> dict:
    return {
        "container_id": container_id,
        "lower_value": lower,
        "upper_value": upper,
        "first_valid_time": first_valid_time,
        "family": "TRAILING_RANGE_SNAPSHOT",
        "kind": "MEASUREMENT",
    }


class RelationFoundationTests(unittest.TestCase):
    def test_bar_probes_keep_point_body_and_bar_spans_separate(self) -> None:
        probes = bar_probes({
            "observation_id": "OBS.1",
            "first_valid_time": "2026-01-05T02:00:00Z",
            "open": 1.1,
            "high": 1.5,
            "low": 0.9,
            "close": 1.3,
        })
        self.assertEqual({"OPEN", "CLOSE", "BODY_SPAN", "BAR_SPAN"}, set(probes))
        self.assertEqual("POINT", probes["OPEN"]["probe_type"])
        self.assertEqual((1.1, 1.3), (probes["BODY_SPAN"]["low"], probes["BODY_SPAN"]["high"]))
        self.assertEqual((0.9, 1.5), (probes["BAR_SPAN"]["low"], probes["BAR_SPAN"]["high"]))
        self.assertNotEqual(probes["BODY_SPAN"]["probe_id"], probes["BAR_SPAN"]["probe_id"])

    def test_level_point_signed_absolute_equality_and_normalizations(self) -> None:
        probe = point_probe(value=1.25, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z")
        scales = [
            NormalizationScale("SCALE.LOCAL", 0.5, "PRICE", "POLICY.LOCAL", "CONTAINER.1", "2026-01-05T01:00:00Z"),
            NormalizationScale("SCALE.STRUCTURAL", 1.0, "PRICE", "POLICY.STRUCTURAL", "CONTAINER.2", "2026-01-05T01:30:00Z"),
        ]
        relation = relate_point_to_level(probe, level(value=1.2), precision=5, scales=scales)
        self.assertAlmostEqual(0.05, relation["signed_distance"])
        self.assertAlmostEqual(0.05, relation["absolute_distance"])
        self.assertEqual("SUBJECT_MINUS_OBJECT", relation["distance_sign_convention"])
        self.assertEqual("ABOVE", relation["topology"])
        self.assertFalse(relation["equal_at_source_precision"])
        self.assertEqual(2, len(relation["normalizations"]))
        self.assertAlmostEqual(0.1, relation["normalizations"][0]["normalized_signed_distance"])
        self.assertTrue(all(item["active"] is False and item["canonical"] is False for item in relation["normalizations"]))
        assert_causal_relation(relation)

        equal_probe = point_probe(value=1.200004, source_record_id="OBS.2", first_valid_time="2026-01-05T02:15:00Z")
        equal_relation = relate_point_to_level(equal_probe, level(value=1.2), precision=5)
        self.assertEqual("EQUAL", equal_relation["topology"])
        self.assertTrue(equal_relation["equal_at_source_precision"])
        self.assertEqual([], equal_relation["normalizations"])

    def test_normalization_has_no_fallback_and_must_be_first_valid(self) -> None:
        probe = point_probe(value=1.3, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z")
        future_scale = NormalizationScale("SCALE.FUTURE", 0.5, "PRICE", "POLICY", "SOURCE", "2026-01-05T03:00:00Z")
        with self.assertRaisesRegex(RelationContractError, "NORMALIZATION_SCALE_NOT_FIRST_VALID"):
            relate_point_to_level(probe, level(), precision=5, scales=[future_scale])
        with self.assertRaisesRegex(RelationContractError, "NORMALIZATION_SCALE_ACTIVATION_DENIED"):
            NormalizationScale("SCALE.ACTIVE", 1.0, "PRICE", "POLICY", "SOURCE", "2026-01-05T01:00:00Z", active=True)
        with self.assertRaisesRegex(RelationContractError, "CANONICAL_NORMALIZATION_SCALE_DENIED"):
            NormalizationScale("SCALE.CANONICAL", 1.0, "PRICE", "POLICY", "SOURCE", "2026-01-05T01:00:00Z", canonical=True)

    def test_level_span_topology_does_not_claim_path_crossing(self) -> None:
        target = level(value=1.2)
        below = span_probe(low=1.0, high=1.1, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z", probe_type="BODY_SPAN")
        touch = span_probe(low=1.0, high=1.2, source_record_id="OBS.2", first_valid_time="2026-01-05T02:15:00Z", probe_type="BODY_SPAN")
        straddle = span_probe(low=1.0, high=1.4, source_record_id="OBS.3", first_valid_time="2026-01-05T02:30:00Z", probe_type="BAR_SPAN")
        above = span_probe(low=1.3, high=1.4, source_record_id="OBS.4", first_valid_time="2026-01-05T02:45:00Z", probe_type="BAR_SPAN")
        self.assertEqual("ENTIRELY_BELOW", relate_span_to_level(below, target, precision=5)["topology"])
        self.assertEqual("TOUCHES", relate_span_to_level(touch, target, precision=5)["topology"])
        relation = relate_span_to_level(straddle, target, precision=5)
        self.assertEqual("STRADDLES", relation["topology"])
        self.assertIsNone(relation["path_crossing_claim"])
        self.assertEqual("ENTIRELY_ABOVE", relate_span_to_level(above, target, precision=5)["topology"])

    def test_container_point_and_span_topologies_are_explicit(self) -> None:
        target = container()
        values = {
            0.8: "BELOW",
            1.0: "ON_LOWER_BOUNDARY",
            1.5: "INSIDE",
            2.0: "ON_UPPER_BOUNDARY",
            2.2: "ABOVE",
        }
        for index, (value, expected) in enumerate(values.items()):
            probe = point_probe(value=value, source_record_id=f"OBS.{index}", first_valid_time="2026-01-05T02:00:00Z")
            relation = relate_point_to_container(probe, target, precision=5)
            self.assertEqual(expected, relation["topology"])
            self.assertAlmostEqual(value - 1.0, relation["signed_distance_to_lower"])
            self.assertAlmostEqual(value - 2.0, relation["signed_distance_to_upper"])

        cases = [
            ((0.5, 0.9), "ENTIRELY_BELOW"),
            ((0.5, 1.0), "TOUCHES_LOWER"),
            ((0.5, 1.5), "CROSSES_LOWER"),
            ((1.2, 1.8), "INSIDE"),
            ((1.5, 2.0), "TOUCHES_UPPER"),
            ((1.5, 2.5), "CROSSES_UPPER"),
            ((0.5, 2.5), "COVERS_CONTAINER"),
            ((2.1, 2.5), "ENTIRELY_ABOVE"),
        ]
        for index, ((low, high), expected) in enumerate(cases):
            probe = span_probe(low=low, high=high, source_record_id=f"SPAN.{index}", first_valid_time="2026-01-05T02:00:00Z", probe_type="BAR_SPAN")
            relation = relate_span_to_container(probe, target, precision=5)
            self.assertEqual(expected, relation["topology"], (low, high))
            self.assertIsNone(relation["path_crossing_claim"])

    def test_ohlc_cannot_assert_ordered_crossing_but_m1_and_tick_can(self) -> None:
        ohlc = fixed_object_crossing(
            object_id="LEVEL.1", object_value=1.2,
            previous_value=1.1, current_value=1.3,
            previous_time="2026-01-05T01:00:00Z", current_time="2026-01-05T01:15:00Z",
            precision=5, evidence_mode="OHLC_SPAN",
        )
        self.assertEqual("SPAN_STRADDLES_PATH_ORDER_UNKNOWN", ohlc["crossing_status"])
        self.assertFalse(ohlc["path_order_known"])

        cross_up = fixed_object_crossing(
            object_id="LEVEL.1", object_value=1.2,
            previous_value=1.1, current_value=1.3,
            previous_time="2026-01-05T01:00:00Z", current_time="2026-01-05T01:15:00Z",
            precision=5, evidence_mode="M1_PATH", ordered_path=[1.1, 1.15, 1.25, 1.3],
        )
        cross_down = fixed_object_crossing(
            object_id="LEVEL.1", object_value=1.2,
            previous_value=1.3, current_value=1.1,
            previous_time="2026-01-05T01:15:00Z", current_time="2026-01-05T01:30:00Z",
            precision=5, evidence_mode="TICK_PATH", ordered_path=[1.3, 1.25, 1.15, 1.1],
        )
        self.assertEqual("CROSS_UP", cross_up["crossing_status"])
        self.assertEqual("CROSS_DOWN", cross_down["crossing_status"])
        self.assertTrue(cross_up["same_fixed_object_required"])

    def test_reference_change_is_never_crossing(self) -> None:
        record = reference_change_record(
            previous_object_id="LEVEL.OLD",
            current_object_id="LEVEL.NEW",
            first_valid_time="2026-01-05T02:00:00Z",
            reason="PROJECTION_CHANGED",
        )
        self.assertFalse(record["is_crossing"])
        self.assertEqual("REFERENCE_IDENTITY_CHANGE_ONLY", record["authority"])
        with self.assertRaisesRegex(RelationContractError, "REFERENCE_CHANGE_REQUIRES_DIFFERENT_OBJECT"):
            reference_change_record(previous_object_id="LEVEL.1", current_object_id="LEVEL.1", first_valid_time="2026-01-05T02:00:00Z", reason="NO_CHANGE")

    def test_distance_delta_remains_raw_and_not_approaching(self) -> None:
        target = level()
        previous = relate_point_to_level(point_probe(value=1.5, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z"), target, precision=5)
        current = relate_point_to_level(point_probe(value=1.3, source_record_id="OBS.2", first_valid_time="2026-01-05T02:15:00Z"), target, precision=5)
        delta = temporal_relation_delta(previous, current)
        self.assertEqual("DECREASED", delta["absolute_distance_change"])
        self.assertIsNone(delta["approaching_label"])
        self.assertIsNone(delta["testing_label"])
        changed_object = copy.deepcopy(current)
        changed_object["object_id"] = "LEVEL.2"
        with self.assertRaisesRegex(RelationContractError, "RELATION_DELTA_REQUIRES_SAME_OBJECT"):
            temporal_relation_delta(previous, changed_object)

    def test_scoped_relation_set_requires_every_candidate_once_and_selects_nothing(self) -> None:
        probe = point_probe(value=1.3, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z")
        relation = relate_point_to_level(probe, level(level_id="LEVEL.1"), precision=5)
        relation_set = build_relation_set(
            scope_type="LOCAL_LEVELS",
            subject_observation_id="OBS.1",
            candidate_object_ids=["LEVEL.1", "LEVEL.2"],
            relations=[relation],
            exclusions=[{"object_id": "LEVEL.2", "reason": "NOT_FIRST_VALID_AS_OF"}],
            as_of_time="2026-01-05T02:00:00Z",
        )
        self.assertTrue(relation_set["complete_scoped_inventory"])
        self.assertIsNone(relation_set["selected_object_id"])
        self.assertIsNone(relation_set["fallback_object_id"])
        self.assertIsNone(relation_set["semantic_interaction_label"])
        with self.assertRaisesRegex(RelationContractError, "RELATION_SET_INCOMPLETE"):
            build_relation_set(
                scope_type="LOCAL_LEVELS",
                subject_observation_id="OBS.1",
                candidate_object_ids=["LEVEL.1", "LEVEL.2"],
                relations=[relation], exclusions=[],
                as_of_time="2026-01-05T02:00:00Z",
            )

    def test_causal_as_of_blocks_future_objects_and_retrospective_mode_is_separate(self) -> None:
        probe = point_probe(value=1.3, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z")
        future = level(first_valid_time="2026-01-05T03:00:00Z")
        with self.assertRaisesRegex(RelationContractError, "LEVEL_NOT_FIRST_VALID_AS_OF"):
            relate_point_to_level(probe, future, precision=5)
        retrospective = relate_point_to_level(probe, future, precision=5, mode="RETROSPECTIVE_AUDIT")
        self.assertEqual("RETROSPECTIVE_AUDIT", retrospective["mode"])
        with self.assertRaisesRegex(RelationContractError, "CAUSAL_RELATION_MODE_REQUIRED"):
            assert_causal_relation(retrospective)

    def test_legacy_crosswalk_preserves_interpretive_label_without_promotion(self) -> None:
        relation = relate_point_to_level(point_probe(value=1.3, source_record_id="OBS.1", first_valid_time="2026-01-05T02:00:00Z"), level(), precision=5)
        legacy = [
            {"legacy_relation_id": "LEGACY.1", "object_id": "LEVEL.1", "raw_topology": "ABOVE", "interpretive_label": "APPROACHING"},
            {"legacy_relation_id": "LEGACY.2", "object_id": "LEVEL.2", "raw_topology": "BELOW", "interpretive_label": "REJECTING"},
        ]
        before = copy.deepcopy(legacy)
        records = build_legacy_relation_crosswalk(legacy, [relation])
        self.assertEqual(before, legacy)
        self.assertEqual("MATCHED_UNIQUE", records[0]["match_status"])
        self.assertEqual("UNMATCHED", records[1]["match_status"])
        self.assertTrue(all(item["interpretive_label_promoted"] is False for item in records))
        self.assertTrue(all(item["legacy_mutated"] is False for item in records))

    def test_repository_contract_registry_schema_fixture_and_active_boundary(self) -> None:
        contract = (ROOT / "contracts/opt_b/c2/C2_RELATION_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for item in [f"P5-D{number}" for number in range(1, 21)] + [f"P5-Q{number}" for number in range(1, 9)]:
            self.assertIn(item, contract)
        self.assertIn("They do not label approach, test, rejection, acceptance", contract)

        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_RELATION_FOUNDATION_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual(6, len(registry["scopes"]))
        self.assertTrue(all(item["active"] is False and item["canonical"] is False for item in registry["normalization_scales"]))
        self.assertFalse(registry["relation_set"]["hidden_nearest_best_dominant"])
        self.assertEqual("NONE", registry["authority"]["interaction_semantic"])

        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_RELATION_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertEqual(9, len(schema["schemas"]))
        self.assertIn("APPROACHING", schema["prohibited_base_labels"])
        self.assertIn("nearest_object", schema["prohibited_fields"])

        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/relation_foundation_cases_v0_1.json").read_text(encoding="utf-8"))
        required = {"SIGNED_ABSOLUTE_SEPARATE", "BAR_SPAN_STRADDLES_LEVEL", "OHLC_PATH_ORDER_UNKNOWN", "M1_CROSS_UP", "REFERENCE_CHANGE_NOT_CROSSING", "RAW_DISTANCE_DECREASE", "SCOPED_RELATION_SET_INCOMPLETE_BLOCK", "LEGACY_APPROACH_LABEL_NOT_PROMOTED"}
        self.assertTrue(required.issubset({item["case_id"] for item in fixture["cases"]}))
        self.assertFalse(fixture["market_data"])

        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
