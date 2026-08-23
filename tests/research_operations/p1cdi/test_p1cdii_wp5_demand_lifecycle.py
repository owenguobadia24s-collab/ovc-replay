from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.research_operations.p1cdi.demand import (
    assess_demand_eligibility,
    assert_non_actuating,
    build_discovery_demand,
    build_discovery_work_recommendation,
    build_gap_demand,
    build_non_actuation_proof,
    build_rccr_referral,
    build_stack_sufficiency_binding,
    validate_one_way_rccr_return,
)
from ovc.research_operations.p1cdi.lifecycle import (
    build_lifecycle_event,
    project_inventory_activity,
    validate_lifecycle_event,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP5_SYNTHETIC_DEMAND_FIXTURE_v0_1.json"
DEMAND_SCHEMA = ROOT / "schemas/research_operations/p1cdi/p1cdi_demand_rccr_v0_1.schema.json"
LIFECYCLE_SCHEMA = ROOT / "schemas/research_operations/p1cdi/p1cdi_lifecycle_currentness_v0_1.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_closed_shape(test: unittest.TestCase, record: dict, schema: dict, branch: str) -> None:
    definition = schema["$defs"][branch]
    test.assertFalse(definition.get("additionalProperties", True))
    test.assertEqual(set(record), set(definition["required"]))
    for field, field_schema in definition["properties"].items():
        if "const" in field_schema:
            test.assertEqual(record[field], field_schema["const"])
        if "enum" in field_schema:
            test.assertIn(record[field], field_schema["enum"])


class P1CDIIWP5DemandLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = _load(FIXTURE)
        cls.demand_schema = _load(DEMAND_SCHEMA)
        cls.lifecycle_schema = _load(LIFECYCLE_SCHEMA)

    def test_fixture_gap_conditions_map_exactly_without_forbidden_inference(self) -> None:
        self.assertEqual(self.fixture["schema"], "p1cdii-wp5-synthetic-demand-fixture/v0.1")
        for case in self.fixture["cases"]:
            demand = build_gap_demand(
                condition=case["condition"],
                generation_refs=["p1:generation:fixture"],
                required_information=[f"info:{case['condition']}"],
                source_evidence_refs=["evidence:fixture"],
            )
            self.assertEqual(demand["demand_type"], case["expected_demand_type"])
            self.assertNotIn("score", demand)
            self.assertNotIn("priority", demand)
            self.assertNotIn("scientific_disposition", demand)
            self.assertEqual(demand["authority_effect"], "NONE")
            _assert_closed_shape(self, demand, self.demand_schema, "Demand")

    def test_demand_identity_is_order_invariant_but_state_is_not_identity(self) -> None:
        left = build_discovery_demand(
            generation_refs=["g:2", "g:1"],
            demand_type="REPRODUCTION",
            required_information=["info:b", "info:a"],
            source_evidence_refs=["ev:2", "ev:1"],
            blockers=["block:b", "block:a"],
        )
        right = build_discovery_demand(
            generation_refs=["g:1", "g:2"],
            demand_type="REPRODUCTION",
            required_information=["info:a", "info:b"],
            source_evidence_refs=["ev:1", "ev:2"],
            blockers=["block:a", "block:b"],
            state="DEFERRED",
        )
        self.assertEqual(left["demand_id"], right["demand_id"])
        self.assertEqual(left["generation_refs"], right["generation_refs"])
        self.assertEqual(left["required_information"], right["required_information"])
        self.assertNotEqual(left["state"], right["state"])

    def test_lifecycle_activity_is_separate_from_source_scientific_disposition(self) -> None:
        first = build_lifecycle_event(
            generation_id="p1:generation:fixture",
            activity_state="ACTIVE_RESEARCH",
            effective_time="2026-08-23T10:00:00Z",
            source_scientific_disposition_ref=None,
        )
        later = build_lifecycle_event(
            generation_id="p1:generation:fixture",
            activity_state="DORMANT",
            effective_time="2026-08-23T11:00:00Z",
            source_scientific_disposition_ref="owner:scientific-disposition:external",
        )
        self.assertEqual(validate_lifecycle_event(first), first)
        _assert_closed_shape(self, first, self.lifecycle_schema, "LifecycleEvent")
        projection = project_inventory_activity(
            generation_id="p1:generation:fixture", lifecycle_events=[later, first]
        )
        self.assertEqual(projection["activity_state"], "DORMANT")
        self.assertEqual(
            projection["source_scientific_disposition_ref"],
            "owner:scientific-disposition:external",
        )
        self.assertEqual(projection["scientific_strength_inference"], "DENIED")
        self.assertFalse(projection["decision_bearing"])
        self.assertEqual(projection["authority_effect"], "NONE")

    def test_rccr_referral_is_one_way_and_cannot_activate_capability(self) -> None:
        demand = build_gap_demand(
            condition="CURRENT_STACK_CANNOT_ANSWER",
            generation_refs=["p1:generation:fixture"],
            required_information=["persistent-object-identity"],
            source_evidence_refs=["evidence:stack-insufficiency"],
        )
        eligibility = assess_demand_eligibility(
            demand=demand,
            current_stack_result="NOT_RESEARCHABLE",
            reason_codes=["CURRENT_STACK_MISSING_INFORMATION"],
        )
        _assert_closed_shape(self, eligibility, self.demand_schema, "Eligibility")
        referral = build_rccr_referral(
            demand=demand,
            question="Can the current lawful stack supply persistent object identity?",
            source_frontier_ref="p1:frontier:fixture",
            rccr_owner_ref="RCCR:CURRENT",
        )
        _assert_closed_shape(self, referral, self.demand_schema, "Referral")
        self.assertIsNone(referral["rccr_result_ref"])
        binding = build_stack_sufficiency_binding(
            demand_id=demand["demand_id"],
            rccr_result_ref="rccr:assessment:fixture",
        )
        _assert_closed_shape(self, binding, self.demand_schema, "StackBinding")
        projection = validate_one_way_rccr_return(referral=referral, binding=binding)
        self.assertEqual(projection["direction"], self.fixture["rccr_cycle"]["direction"])
        self.assertEqual(projection["source_scientific_mutation"], "DENIED")
        self.assertEqual(projection["capability_activation"], "DENIED")
        self.assertFalse(projection["decision_bearing"])

    def test_next_discovery_work_is_advisory_and_negative_reachability_is_explicit(self) -> None:
        demand = build_gap_demand(
            condition="DEPENDENCE_INCOMPLETE",
            generation_refs=["p1:generation:fixture"],
            required_information=["dependence-aware-assessment"],
        )
        recommendation = build_discovery_work_recommendation(
            demand_refs=[demand["demand_id"]],
            reason_trace=["OPEN_DEMAND", "ELIGIBLE_RESEARCH_ROUTE"],
        )
        _assert_closed_shape(self, recommendation, self.demand_schema, "Recommendation")
        assert_non_actuating(recommendation)
        proof = build_non_actuation_proof(recommendation=recommendation)
        self.assertEqual(proof["result"], "PASS_NEGATIVE_REACHABILITY")
        self.assertEqual(proof["denied_targets"], self.fixture["next_discovery_work"]["negative_reachability"])
        self.assertEqual(proof["authority_effect"], "NONE")

    def test_actuation_and_registry_escape_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_discovery_demand(
                generation_refs=["g:1"],
                demand_type="BEST_NEXT_WORK",
                required_information=["info:1"],
            )
        with self.assertRaises(ValueError):
            build_gap_demand(
                condition="CAPABILITY_AVAILABLE",
                generation_refs=["g:1"],
                required_information=["info:1"],
            )
        recommendation = build_discovery_work_recommendation(
            demand_refs=["p1:demand:fixture"], reason_trace=["reason:fixture"]
        )
        escaped = copy.deepcopy(recommendation)
        escaped["actuation"] = "ALLOWED"
        with self.assertRaises(PermissionError):
            assert_non_actuating(escaped)
        escaped = copy.deepcopy(recommendation)
        escaped["command"] = "OVC RUN"
        with self.assertRaises(PermissionError):
            assert_non_actuating(escaped)

    def test_rccr_cycle_rejects_cross_demand_or_missing_result(self) -> None:
        demand = build_gap_demand(
            condition="STACK_SUFFICIENCY_UNRESOLVED",
            generation_refs=["g:1"],
            required_information=["info:stack"],
        )
        referral = build_rccr_referral(
            demand=demand,
            question="Is the stack sufficient?",
            source_frontier_ref="frontier:1",
            rccr_owner_ref="RCCR:CURRENT",
        )
        wrong = build_stack_sufficiency_binding(
            demand_id="p1:demand:other", rccr_result_ref="rccr:assessment:1"
        )
        with self.assertRaises(ValueError):
            validate_one_way_rccr_return(referral=referral, binding=wrong)
        with self.assertRaises(ValueError):
            build_stack_sufficiency_binding(demand_id=demand["demand_id"], rccr_result_ref="")


if __name__ == "__main__":
    unittest.main()
