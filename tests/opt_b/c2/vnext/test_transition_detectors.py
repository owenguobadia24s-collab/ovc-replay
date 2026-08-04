from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.transitions import (
    TransitionDetectorError,
    classify_transition,
    detect_container_entry_exit,
    detect_fixed_object_crossing,
    detect_precision_touch,
    detect_raw_distance_change,
    detect_reference_identity_change,
    detect_structural_graph_change,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures/opt_b/c2/vnext/transition_detector_cases_v0_1.json"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_TRANSITION_DETECTOR_FREEZE_v1.jsonc"
SCHEMA = ROOT / "schemas/opt_b/c2/vnext/C2_TRANSITION_DETECTOR_SCHEMA_BUNDLE_vNext_r1.json"
CONTRACT = ROOT / "contracts/opt_b/c2/C2_TRANSITION_AND_RAW_DETECTOR_CONTRACT_vNext.md"
AS_OF = "2026-06-01T00:03:00Z"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def forbidden_values(value: object) -> list[str]:
    prohibited = {"APPROACHING", "TESTING", "REJECTING", "ACCEPTING", "BREAKOUT", "REVERSAL", "CONTINUATION", "SETUP", "SIGNAL"}
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(forbidden_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(forbidden_values(item))
    elif isinstance(value, str) and value in prohibited:
        found.append(value)
    return found


class TransitionDetectorTests(unittest.TestCase):
    def test_freeze_registry_is_effective_but_inactive_noncanonical_and_threshold_free(self) -> None:
        registry = load(REGISTRY)
        self.assertTrue(registry["effective"])
        self.assertFalse(registry["active"])
        self.assertFalse(registry["canonical"])
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", registry["authority"])
        self.assertEqual("CEAR-G7.OPERATOR.PASS.20260804T234400+0100", registry["operator_decision_id"])
        self.assertEqual(6, len(registry["detectors"]))
        for detector in registry["detectors"]:
            self.assertFalse(detector["active"])
            self.assertFalse(detector["canonical"])
            self.assertEqual([], detector["numeric_thresholds"])
            self.assertEqual("NONE", detector["semantic_authority"])
        self.assertFalse(registry["evidence_rules"]["ohlc_directional_authority"])
        self.assertFalse(registry["evidence_rules"]["reference_identity_change_is_crossing"])

    def test_contract_and_closed_schema_preserve_authority_boundary(self) -> None:
        contract = CONTRACT.read_text(encoding="utf-8")
        schema = load(SCHEMA)
        self.assertIn("SHADOW_FROZEN_READ_ONLY", contract)
        self.assertIn("A reference-identity change is never crossing", contract)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["$defs"]["transition_record"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["detector_output"]["additionalProperties"])
        self.assertEqual(False, schema["$defs"]["detector_output"]["properties"]["active"]["const"])
        self.assertEqual("NONE", schema["$defs"]["detector_output"]["properties"]["semantic_authority"]["const"])

    def test_transition_fixtures_classify_every_applicable_raw_change_deterministically(self) -> None:
        for case in load(FIXTURES)["transition_cases"]:
            kwargs = {key: case[key] for key in (
                "previous_time", "current_time", "measurement_fields", "categorical_fields",
                "reference_fields", "structural_fields", "computability_fields",
            )}
            first = classify_transition(case["previous"], case["current"], profile_id="PROFILE.RAW", scope_id="SCOPE.1", **kwargs)
            second = classify_transition(case["previous"], case["current"], profile_id="PROFILE.RAW", scope_id="SCOPE.1", **kwargs)
            self.assertEqual(first, second)
            self.assertEqual(case["expected_classes"], first["classes"])
            self.assertEqual(case["expected_primary"], first["primary_class"])
            self.assertFalse(first["active"])
            self.assertFalse(first["canonical"])
            self.assertEqual("NONE", first["semantic_authority"])
            self.assertEqual([], forbidden_values(first))

    def test_no_change_and_mixed_change_precedence_have_no_market_meaning(self) -> None:
        previous = {"record_id": "A", "profile_id": "P", "scope_id": "S", "facts": {"x": 1, "kind": "BELOW", "ref": "L1", "graph": "G1"}, "quality": "OK"}
        same = {**previous, "record_id": "B"}
        unchanged = classify_transition(previous, same, previous_time="2026-06-01T00:00:00Z", current_time="2026-06-01T00:01:00Z", profile_id="P", scope_id="S", measurement_fields=["facts.x"], categorical_fields=["facts.kind"], reference_fields=["facts.ref"], structural_fields=["facts.graph"], computability_fields=["quality"])
        self.assertEqual(["NO_CHANGE"], unchanged["classes"])
        current = {"record_id": "C", "profile_id": "P", "scope_id": "S", "facts": {"x": 2, "kind": "INSIDE", "ref": "L2", "graph": "G2"}, "quality": "CENSORED"}
        mixed = classify_transition(previous, current, previous_time="2026-06-01T00:00:00Z", current_time="2026-06-01T00:01:00Z", profile_id="P", scope_id="S", measurement_fields=["facts.x"], categorical_fields=["facts.kind"], reference_fields=["facts.ref"], structural_fields=["facts.graph"], computability_fields=["quality"])
        self.assertEqual("STRUCTURAL_CHANGE", mixed["primary_class"])
        self.assertEqual(["STRUCTURAL_CHANGE", "REFERENCE_IDENTITY_CHANGE", "COMPUTABILITY_CHANGE", "CATEGORICAL_CHANGE", "MEASUREMENT_CHANGE"], mixed["classes"])

    def test_transition_rejects_unordered_profile_scope_and_outcome_inputs(self) -> None:
        base = {"record_id": "A", "profile_id": "P", "scope_id": "S", "facts": {"x": 1}}
        with self.assertRaisesRegex(TransitionDetectorError, "TRANSITION_CHRONOLOGY_REQUIRED"):
            classify_transition(base, {**base, "record_id": "B"}, previous_time="2026-06-01T00:01:00Z", current_time="2026-06-01T00:00:00Z", profile_id="P", scope_id="S")
        with self.assertRaisesRegex(TransitionDetectorError, "CURRENT_PROFILE_MISMATCH"):
            classify_transition(base, {**base, "record_id": "B", "profile_id": "OTHER"}, previous_time="2026-06-01T00:00:00Z", current_time="2026-06-01T00:01:00Z", profile_id="P", scope_id="S")
        with self.assertRaisesRegex(TransitionDetectorError, "PROHIBITED_FIELD"):
            classify_transition(base, {**base, "record_id": "B", "outcome": "WIN"}, previous_time="2026-06-01T00:00:00Z", current_time="2026-06-01T00:01:00Z", profile_id="P", scope_id="S")

    def test_crossing_requires_same_fixed_object_ordered_m1_or_tick_path(self) -> None:
        fixture = next(item for item in load(FIXTURES)["detector_cases"] if item["case_id"] == "DETECTOR.CROSS_UP_ORDERED_M1")
        result = detect_fixed_object_crossing(object_id=fixture["object_id"], object_value=fixture["object_value"], ordered_path=fixture["ordered_path"], source_precision=fixture["source_precision"], as_of_time=AS_OF, evidence_mode=fixture["evidence_mode"])
        self.assertEqual(["CROSS_UP"], result["outputs"])
        self.assertEqual("COMPUTABLE", result["computability"])
        self.assertFalse(result["evidence"]["ohlc_directional_authority"])
        ohlc = detect_fixed_object_crossing(object_id="LEVEL.1", object_value="1.25000", ordered_path=fixture["ordered_path"], source_precision=5, as_of_time=AS_OF, evidence_mode="OHLC")
        self.assertEqual(["INSUFFICIENT_ORDERED_PATH"], ohlc["outputs"])
        self.assertEqual("NOT_COMPUTABLE", ohlc["computability"])
        unordered = detect_fixed_object_crossing(object_id="LEVEL.1", object_value="1.25000", ordered_path=[fixture["ordered_path"][1], fixture["ordered_path"][0]], source_precision=5, as_of_time=AS_OF, evidence_mode="M1")
        self.assertEqual("NOT_COMPUTABLE", unordered["computability"])
        self.assertIn("PATH_NOT_STRICTLY_ORDERED", unordered["reason_codes"])

    def test_touch_container_distance_and_reference_detectors_emit_raw_facts_only(self) -> None:
        touch = detect_precision_touch(object_id="LEVEL.1", probe_id="PROBE.1", raw_topology="EQUAL", source_precision=5, as_of_time=AS_OF)
        self.assertEqual(["TOUCH"], touch["outputs"])
        self.assertFalse(touch["evidence"]["proximity_substitution"])
        entry = detect_container_entry_exit(container_id="CONTAINER.1", previous_topology="BELOW", current_topology="INSIDE", positive_width=True, as_of_time=AS_OF)
        self.assertEqual(["ENTRY_FROM_BELOW"], entry["outputs"])
        self.assertFalse(entry["evidence"]["acceptance_or_rejection_authority"])
        ambiguous = detect_container_entry_exit(container_id="CONTAINER.1", previous_topology="BELOW", current_topology="ABOVE", positive_width=True, as_of_time=AS_OF)
        self.assertEqual(["NOT_COMPUTABLE"], ambiguous["outputs"])
        distance = detect_raw_distance_change(object_id="LEVEL.1", previous_object_id="LEVEL.1", absolute_distance_delta="-0.1", relation_delta_id="DELTA.1", as_of_time=AS_OF)
        self.assertEqual(["DISTANCE_DECREASED"], distance["outputs"])
        self.assertFalse(distance["evidence"]["approaching_label_authority"])
        changed = detect_reference_identity_change(previous_reference_id="LEVEL.1", current_reference_id="LEVEL.2", reference_kind="LEVEL", as_of_time=AS_OF)
        self.assertEqual(["REFERENCE_CHANGED"], changed["outputs"])
        self.assertFalse(changed["evidence"]["is_crossing"])
        for output in (touch, entry, ambiguous, distance, changed):
            self.assertEqual([], output["numeric_thresholds"])
            self.assertFalse(output["active"])
            self.assertFalse(output["canonical"])
            self.assertEqual("NONE", output["semantic_authority"])
            self.assertEqual([], forbidden_values(output))

    def test_structural_detector_requires_complete_inventory_and_explicit_supersession(self) -> None:
        fixture = next(item for item in load(FIXTURES)["detector_cases"] if item["case_id"] == "DETECTOR.STRUCTURAL_CHANGE")
        result = detect_structural_graph_change(previous_graph=fixture["previous_graph"], current_graph=fixture["current_graph"], supersessions=fixture["supersessions"], as_of_time=AS_OF)
        self.assertEqual(set(fixture["expected_outputs"]), set(result["outputs"]))
        self.assertEqual("COMPUTABLE", result["computability"])
        incomplete = detect_structural_graph_change(previous_graph={**fixture["previous_graph"], "complete_inventory": False}, current_graph=fixture["current_graph"], supersessions=fixture["supersessions"], as_of_time=AS_OF)
        self.assertEqual(["NOT_COMPUTABLE"], incomplete["outputs"])
        unexplained = detect_structural_graph_change(previous_graph=fixture["previous_graph"], current_graph=fixture["current_graph"], supersessions=[], as_of_time=AS_OF)
        self.assertEqual("NOT_COMPUTABLE", unexplained["computability"])
        self.assertIn("REMOVED_NODE_REQUIRES_EXPLICIT_SUPERSESSION", unexplained["reason_codes"])


if __name__ == "__main__":
    unittest.main()
