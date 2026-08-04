from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.formula_profiles import (
    FormulaProfileError,
    build_formula_bundle,
    evaluate_interaction_profile,
    evaluate_location_profile,
    evaluate_motion_profile,
    evaluate_organisation_profile,
    evaluate_quality_profile,
)

ROOT = Path(__file__).resolve().parents[4]
AS_OF = "2026-01-05T03:00:00Z"


def relation_set() -> dict:
    return {
        "relation_set_id": "RELSET.1", "as_of_time": AS_OF,
        "candidate_object_ids": ["LEVEL.1", "CONTAINER.1", "LEVEL.EXCLUDED"],
        "relation_ids": ["REL.1", "REL.2"],
        "exclusions": [{"object_id": "LEVEL.EXCLUDED", "reason": "NOT_FIRST_VALID_AS_OF"}],
        "complete_scoped_inventory": True,
        "selected_object_id": None, "fallback_object_id": None,
    }


def raw_relations() -> list[dict]:
    return [
        {"relation_id": "REL.1", "subject_probe_id": "PROBE.1", "object_kind": "LEVEL", "object_id": "LEVEL.1", "topology": "ABOVE", "signed_distance": 0.1, "absolute_distance": 0.1, "equal_at_source_precision": False, "source_precision": 5, "mode": "CAUSAL_AS_OF", "first_valid_time": "2026-01-05T02:45:00Z"},
        {"relation_id": "REL.2", "subject_probe_id": "PROBE.1", "object_kind": "CONTAINER", "object_id": "CONTAINER.1", "topology": "INSIDE", "signed_distance_to_lower": 0.3, "signed_distance_to_upper": -0.7, "source_precision": 5, "mode": "CAUSAL_AS_OF", "first_valid_time": "2026-01-05T02:45:00Z"},
    ]


def relation_delta() -> dict:
    return {
        "relation_delta_id": "DELTA.1", "object_id": "LEVEL.1",
        "signed_distance_delta": -0.2, "absolute_distance_delta": -0.2,
        "absolute_distance_change": "DECREASED", "previous_topology": "ABOVE",
        "current_topology": "ABOVE", "first_valid_time": "2026-01-05T02:45:00Z",
        "approaching_label": None, "testing_label": None,
    }


def container_graph() -> dict:
    return {
        "container_graph_id": "GRAPH.CONTAINER.1", "complete_inventory": True,
        "width_derived_tree": False,
        "containers": [
            {"container_id": "CONTAINER.1", "family": "TRAILING_RANGE_SNAPSHOT", "kind": "MEASUREMENT", "lower_value": 1.0, "upper_value": 2.0, "width": 1.0, "centre": 1.5, "structural_depth": "NA", "first_valid_time": "2026-01-05T02:00:00Z"},
            {"container_id": "CONTAINER.2", "family": "SWING_ENVELOPE", "kind": "STRUCTURAL", "lower_value": 0.8, "upper_value": 2.2, "width": 1.4, "centre": 1.5, "structural_depth": "S0", "first_valid_time": "2026-01-05T02:15:00Z"},
        ],
        "edges": [{"container_edge_id": "EDGE.1", "left_container_id": "CONTAINER.2", "right_container_id": "CONTAINER.1", "relation": "CONTAINS", "basis": "RAW_INTERVAL_GEOMETRY"}],
    }


def all_outputs() -> list[dict]:
    location = evaluate_location_profile([relation_set()], raw_relations(), as_of_time=AS_OF)
    motion = evaluate_motion_profile(
        {"membership_id": "MEM.1", "horizon_id": "HORIZON.4", "status": "COMPLETE", "member_observation_ids": ["OBS.1", "OBS.2"], "first_valid_time": "2026-01-05T02:45:00Z"},
        price_delta=0.2, relation_deltas=[relation_delta()], as_of_time=AS_OF,
    )
    organisation = evaluate_organisation_profile(
        container_graph(),
        swing_graph={"swing_graph_id": "GRAPH.SWING.1", "level_ids": ["LEVEL.1", "LEVEL.2"], "edges": [], "first_valid_time": "2026-01-05T02:30:00Z"},
        as_of_time=AS_OF,
    )
    interaction = evaluate_interaction_profile(
        relation_deltas=[relation_delta()],
        crossing_evidence=[{"crossing_evidence_id": "CROSS.1", "object_id": "LEVEL.1", "crossing_status": "CROSS_UP", "evidence_mode": "M1_PATH", "path_order_known": True, "previous_side": -1, "current_side": 1, "same_fixed_object_required": True}],
        reference_changes=[{"reference_change_id": "REFCHANGE.1", "previous_object_id": "LEVEL.OLD", "current_object_id": "LEVEL.1", "first_valid_time": "2026-01-05T02:30:00Z", "reason": "PROJECTION_CHANGED", "is_crossing": False}],
        as_of_time=AS_OF,
    )
    quality = evaluate_quality_profile([
        {"component_id": "OBSERVATION", "status": "COMPUTABLE", "reason_codes": [], "source_ids": ["OBS.1"]},
        {"component_id": "HORIZON", "status": "CENSORED", "reason_codes": ["RIGHT_BOUNDARY"], "source_ids": ["MEM.1"], "censored": True},
        {"component_id": "CONTAINER", "status": "AMBIGUOUS", "reason_codes": ["PAIRING_TIE"], "source_ids": ["CONTAINER.1", "CONTAINER.2"], "ambiguous": True},
    ], as_of_time=AS_OF)
    return [location, motion, organisation, interaction, quality]


class FormulaProfileTests(unittest.TestCase):
    def test_five_profiles_are_deterministic_inactive_and_threshold_free(self) -> None:
        first = all_outputs()
        second = all_outputs()
        self.assertEqual(first, second)
        self.assertEqual({"LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"}, {item["axis"] for item in first})
        for output in first:
            self.assertFalse(output["active"])
            self.assertFalse(output["canonical"])
            self.assertEqual([], output["numeric_thresholds"])
            self.assertIsNone(output["selected_object_id"])
            self.assertIsNone(output["fallback_object_id"])
            self.assertIsNone(output["semantic_label"])
            self.assertEqual("SHADOW_FROZEN_READ_ONLY", output["authority"])
            self.assertRegex(output["content_sha256"], r"^[0-9a-f]{64}$")

    def test_location_preserves_raw_geometry_exclusions_and_no_winner(self) -> None:
        output = evaluate_location_profile([relation_set()], raw_relations(), as_of_time=AS_OF)
        self.assertEqual("COMPUTABLE", output["computability"])
        self.assertEqual(2, len(output["facts"]["relations"]))
        self.assertEqual([{"object_id": "LEVEL.EXCLUDED", "reason": "NOT_FIRST_VALID_AS_OF"}], output["facts"]["exclusions"])
        self.assertTrue(output["facts"]["complete_scoped_inventory"])
        hidden = relation_set()
        hidden["selected_object_id"] = "LEVEL.1"
        with self.assertRaisesRegex(FormulaProfileError, "LOCATION_HIDDEN_SELECTION"):
            evaluate_location_profile([hidden], raw_relations(), as_of_time=AS_OF)
        missing = relation_set()
        missing["relation_ids"].append("REL.MISSING")
        with self.assertRaisesRegex(FormulaProfileError, "LOCATION_DECLARED_RELATION_MISSING"):
            evaluate_location_profile([missing], raw_relations(), as_of_time=AS_OF)

    def test_motion_is_typed_and_warmup_is_explicit_not_computable(self) -> None:
        complete = evaluate_motion_profile(
            {"membership_id": "MEM.1", "horizon_id": "HORIZON.4", "status": "COMPLETE", "member_observation_ids": ["OBS.1", "OBS.2"]},
            price_delta=0.2, relation_deltas=[relation_delta()], as_of_time=AS_OF,
        )
        self.assertEqual("COMPUTABLE", complete["computability"])
        self.assertEqual("HORIZON.4", complete["facts"]["horizon_id"])
        warmup = evaluate_motion_profile(
            {"membership_id": "MEM.2", "horizon_id": "HORIZON.8", "status": "WARMUP", "member_observation_ids": ["OBS.1"]},
            price_delta=None, relation_deltas=[], as_of_time=AS_OF,
        )
        self.assertEqual("NOT_COMPUTABLE", warmup["computability"])
        self.assertEqual({"HORIZON_WARMUP", "PRICE_DELTA_UNAVAILABLE"}, set(warmup["reason_codes"]))
        self.assertIsNone(warmup["fallback_object_id"])

    def test_organisation_preserves_graph_without_width_parentage(self) -> None:
        output = evaluate_organisation_profile(container_graph(), swing_graph=None, as_of_time=AS_OF)
        self.assertEqual("COMPUTABLE", output["computability"])
        self.assertEqual(2, len(output["facts"]["containers"]))
        self.assertEqual("CONTAINS", output["facts"]["container_edges"][0]["relation"])
        bad = container_graph()
        bad["width_derived_tree"] = True
        with self.assertRaisesRegex(FormulaProfileError, "WIDTH_DERIVED_HIERARCHY_PROHIBITED"):
            evaluate_organisation_profile(bad, swing_graph=None, as_of_time=AS_OF)

    def test_interaction_remains_raw_and_reference_change_is_not_crossing(self) -> None:
        output = all_outputs()[3]
        self.assertEqual("COMPUTABLE", output["computability"])
        self.assertEqual("CROSS_UP", output["facts"]["crossings"][0]["crossing_status"])
        self.assertFalse(output["facts"]["reference_changes"][0]["is_crossing"])
        bad = relation_delta()
        bad["approaching_label"] = "APPROACHING"
        with self.assertRaisesRegex(FormulaProfileError, "APPROACHING_LABEL_PROHIBITED"):
            evaluate_interaction_profile(relation_deltas=[bad], crossing_evidence=[], reference_changes=[], as_of_time=AS_OF)

    def test_quality_remains_per_component_without_global_collapse(self) -> None:
        output = all_outputs()[4]
        self.assertIsNone(output["facts"]["global_collapsed_status"])
        by_id = {item["component_id"]: item for item in output["facts"]["components"]}
        self.assertTrue(by_id["HORIZON"]["censored"])
        self.assertTrue(by_id["CONTAINER"]["ambiguous"])
        duplicate = [{"component_id": "A"}, {"component_id": "A"}]
        with self.assertRaisesRegex(FormulaProfileError, "DUPLICATE_QUALITY_COMPONENT"):
            evaluate_quality_profile(duplicate, as_of_time=AS_OF)

    def test_bundle_requires_exact_five_axes_and_never_selects_profile(self) -> None:
        outputs = all_outputs()
        bundle = build_formula_bundle(outputs, as_of_time=AS_OF)
        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual(["LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"], bundle["axis_order"])
        self.assertIsNone(bundle["selected_profile_id"])
        self.assertIsNone(bundle["fallback_profile_id"])
        self.assertFalse(bundle["active"])
        with self.assertRaisesRegex(FormulaProfileError, "BUNDLE_MISSING_AXES"):
            build_formula_bundle(outputs[:-1], as_of_time=AS_OF)
        active = copy.deepcopy(outputs)
        active[0]["active"] = True
        with self.assertRaisesRegex(FormulaProfileError, "BUNDLE_ACTIVE_OR_CANONICAL_PROFILE"):
            build_formula_bundle(active, as_of_time=AS_OF)
        probability = copy.deepcopy(outputs)
        probability[0]["facts"]["probability"] = 0.7
        with self.assertRaisesRegex(FormulaProfileError, "PROHIBITED_FIELD"):
            build_formula_bundle(probability, as_of_time=AS_OF)

    def test_future_input_is_blocked(self) -> None:
        future = relation_set()
        future["as_of_time"] = "2026-01-05T04:00:00Z"
        with self.assertRaisesRegex(FormulaProfileError, "INPUT_NOT_FIRST_VALID_AS_OF"):
            evaluate_location_profile([future], raw_relations(), as_of_time=AS_OF)

    def test_repository_contract_registry_schema_fixture_and_active_boundary(self) -> None:
        contract = (ROOT / "contracts/opt_b/c2/C2_FORMULA_PROFILE_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"):
            self.assertIn(axis, contract)
        self.assertIn("SHADOW_FROZEN", contract)
        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_FORMULA_PROFILE_REGISTRY_v1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual(5, len(registry["profiles"]))
        self.assertIsNone(registry["active_profile_id"])
        self.assertTrue(all(not item["active"] and not item["canonical"] and item["numeric_thresholds"] == [] for item in registry["profiles"]))
        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_FORMULA_PROFILE_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertEqual(2, len(schema["schemas"]))
        self.assertIn("probability", schema["prohibited_fields"])
        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/formula_profile_cases_v0_1.json").read_text(encoding="utf-8"))
        self.assertFalse(fixture["market_data"])
        self.assertGreaterEqual(len(fixture["cases"]), 15)
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
