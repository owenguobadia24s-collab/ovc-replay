from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.computability import (
    AUTHORITY,
    ComputabilityError,
    apply_consumer_policy,
    build_denominator_record,
    build_overlap_report,
    compare_population_records,
    evaluate_component,
    project_legacy_quality,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2/vnext/C2_COMPUTABILITY_FIXTURE_PACK_v0_1.json"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_COMPUTABILITY_POLICY_REGISTRY_v0_1.jsonc"
SCHEMA = ROOT / "schemas/opt_b/c2/vnext/C2_COMPUTABILITY_SCHEMA_BUNDLE_vNext_r1.json"
CROSSWALK = ROOT / "registries/opt_b/c2/vnext/C2_LEGACY_QUALITY_CROSSWALK_v0_1.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def component(
    unit_id: str,
    *,
    requested: bool = True,
    applicable: bool = True,
    censored: bool = False,
    edges: list[dict] | None = None,
    results: dict | None = None,
    assurance: str = "ASSURED",
    age: dict | None = None,
) -> dict:
    return evaluate_component(
        component_id="MOTION.RAW",
        profile_id="MOTION.RAW.v1",
        unit_id=unit_id,
        as_of_time="2026-06-01T02:00:00Z",
        dependency_edges=edges or [],
        dependency_results=results or {},
        requested=requested,
        applicable=applicable,
        censored=censored,
        assurance_status=assurance,
        age_evidence=age or {},
        source_ids=[f"SOURCE-{unit_id}"],
    )


class ComputabilityTests(unittest.TestCase):
    def test_fixture_cases_are_deterministic_and_match_expected_dispositions(self) -> None:
        fixture = load(FIXTURE)
        for case in fixture["cases"]:
            value = evaluate_component(
                **case["component"],
                dependency_edges=case["edges"],
                dependency_results=case["results"],
                requested=case.get("requested", True),
                applicable=case.get("applicable", True),
                censored=case.get("censored", False),
                assurance_status="NOT_ASSESSED",
            )
            again = evaluate_component(
                **case["component"],
                dependency_edges=copy.deepcopy(case["edges"]),
                dependency_results=copy.deepcopy(case["results"]),
                requested=case.get("requested", True),
                applicable=case.get("applicable", True),
                censored=case.get("censored", False),
                assurance_status="NOT_ASSESSED",
            )
            self.assertEqual(value, again, case["case_id"])
            expected = case["expected"]
            for field in ("availability_status", "computability_status", "missing_dependency_ids"):
                if field in expected:
                    self.assertEqual(expected[field], value[field], case["case_id"])
            if "warning_contains" in expected:
                self.assertIn(expected["warning_contains"], value["warnings"])
            if "reason_contains" in expected:
                self.assertIn(expected["reason_contains"], value["reason_codes"])
            if "satisfied_group" in expected:
                self.assertIn(expected["satisfied_group"], value["satisfied_alternative_groups"])
            self.assertFalse(value["active"])
            self.assertFalse(value["canonical"])
            self.assertEqual(AUTHORITY, value["authority"])

    def test_optional_and_warning_dependencies_do_not_block_raw_component(self) -> None:
        value = component(
            "OPT-WARN",
            edges=[
                {"dependency_id": "OPT", "edge_type": "OPTIONAL"},
                {"dependency_id": "WARN", "edge_type": "WARNING_ONLY"},
            ],
            results={"OPT": {"status": "MISSING"}, "WARN": {"status": "UNAVAILABLE"}},
        )
        self.assertEqual("COMPUTABLE", value["computability_status"])
        self.assertEqual(2, len(value["warnings"]))
        self.assertEqual([], value["missing_dependency_ids"])

    def test_required_failure_propagates_only_to_exact_component(self) -> None:
        failed = component(
            "REQ-FAIL",
            edges=[{"dependency_id": "PARENT", "edge_type": "REQUIRED"}],
            results={"PARENT": {"status": "NOT_COMPUTABLE"}},
        )
        independent = component("INDEPENDENT")
        self.assertEqual("NOT_COMPUTABLE", failed["computability_status"])
        self.assertEqual(["PARENT"], failed["missing_dependency_ids"])
        self.assertEqual("COMPUTABLE", independent["computability_status"])

    def test_ambiguity_can_block_unique_selection_without_removing_inventory(self) -> None:
        value = evaluate_component(
            component_id="LOCATION.SELECTED_PARENT",
            profile_id="LOCATION.PARENT.v1",
            unit_id="AMB-001",
            as_of_time="2026-06-01T02:00:00Z",
            dependency_edges=[{"dependency_id": "UNIQUE-PARENT", "edge_type": "REQUIRED"}],
            dependency_results={
                "UNIQUE-PARENT": {
                    "status": "NOT_COMPUTABLE",
                    "reason_codes": ["MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION"],
                }
            },
            source_ids=["PARENT-A", "PARENT-B"],
        )
        self.assertEqual("NOT_COMPUTABLE", value["computability_status"])
        self.assertEqual(["PARENT-A", "PARENT-B"], value["source_ids"])
        self.assertEqual(["UNIQUE-PARENT"], value["missing_dependency_ids"])

    def test_prohibited_future_or_outcome_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(ComputabilityError, "PROHIBITED_FIELD"):
            evaluate_component(
                component_id="BAD",
                profile_id="BAD.v1",
                unit_id="BAD-1",
                as_of_time="2026-06-01T02:00:00Z",
                dependency_edges=[],
                dependency_results={"X": {"status": "COMPUTABLE", "outcome": 1}},
            )

    def test_consumer_policy_is_exact_inactive_and_authority_sensitive(self) -> None:
        base = component("ELIGIBLE", age={"observation_age_seconds": 0})
        policy = {
            "consumer_policy_id": "C2.CONSUMER.READ_ONLY_QA.v1",
            "version": "1",
            "active": False,
            "canonical": False,
            "assurance_required": True,
            "required_age_dimensions": ["observation_age_seconds"],
            "staleness_policy_id": "RAW_AGE_ONLY",
        }
        denied = apply_consumer_policy(base, policy, consumer_authorized=False)
        allowed = apply_consumer_policy(base, policy, consumer_authorized=True)
        self.assertEqual("INELIGIBLE", denied["consumer_eligibility_status"])
        self.assertEqual("UNAUTHORIZED", denied["authority_status"])
        self.assertIn("CONSUMER_UNAUTHORIZED", denied["reason_codes"])
        self.assertEqual("ELIGIBLE", allowed["consumer_eligibility_status"])
        self.assertEqual("AUTHORIZED", allowed["authority_status"])
        self.assertFalse(allowed["active"])
        self.assertFalse(allowed["canonical"])

    def test_numeric_staleness_threshold_is_prohibited(self) -> None:
        with self.assertRaisesRegex(ComputabilityError, "NUMERIC_STALENESS_THRESHOLD_PROHIBITED"):
            apply_consumer_policy(
                component("STALE"),
                {
                    "consumer_policy_id": "POLICY",
                    "version": "1",
                    "active": False,
                    "canonical": False,
                    "numeric_staleness_threshold": 3600,
                },
                consumer_authorized=True,
            )

    def test_missing_age_dimension_causes_ineligibility_not_noncomputability(self) -> None:
        base = component("AGE-MISSING")
        value = apply_consumer_policy(
            base,
            {
                "consumer_policy_id": "PARENT-CONSUMER",
                "version": "1",
                "active": False,
                "canonical": False,
                "assurance_required": False,
                "required_age_dimensions": ["definition_age_seconds"],
                "staleness_policy_id": "RAW_AGE_ONLY",
            },
            consumer_authorized=True,
        )
        self.assertEqual("COMPUTABLE", value["computability_status"])
        self.assertEqual("INELIGIBLE", value["consumer_eligibility_status"])
        self.assertIn("AGE_EVIDENCE_UNAVAILABLE:definition_age_seconds", value["reason_codes"])

    def test_denominator_reconciles_every_terminal_disposition(self) -> None:
        policy = {
            "consumer_policy_id": "C2.CONSUMER.READ_ONLY_QA.v1",
            "version": "1",
            "active": False,
            "canonical": False,
            "assurance_required": False,
        }
        records = [
            apply_consumer_policy(component("U1"), policy, consumer_authorized=True),
            apply_consumer_policy(component("U2"), policy, consumer_authorized=True),
            apply_consumer_policy(
                component("U3", edges=[{"dependency_id": "D", "edge_type": "REQUIRED"}], results={"D": {"status": "MISSING"}}),
                policy,
                consumer_authorized=True,
            ),
            apply_consumer_policy(component("U4", censored=True), policy, consumer_authorized=True),
            apply_consumer_policy(component("U5", applicable=False), policy, consumer_authorized=True),
            apply_consumer_policy(component("U6", requested=False), policy, consumer_authorized=True),
        ]
        records[0]["numerator_member"] = True
        value = build_denominator_record(
            records,
            scope_id="FIXTURE.TRANSITION.PAIRS.v1",
            scope_definition="ALL_SYNTHETIC_COMPARABLE_TRANSITION_PAIRS",
            unit_type="TRANSITION_PAIR",
            consumer_policy_id=policy["consumer_policy_id"],
        )
        counts = value["counts"]
        self.assertEqual(6, counts["population_count"])
        self.assertEqual(5, counts["requested_count"])
        self.assertEqual(1, counts["not_requested_count"])
        self.assertEqual(4, counts["applicable_count"])
        self.assertEqual(1, counts["not_applicable_count"])
        self.assertEqual(2, counts["computable_count"])
        self.assertEqual(1, counts["not_computable_count"])
        self.assertEqual(1, counts["censored_count"])
        self.assertEqual(2, counts["eligible_count"])
        self.assertEqual(2, counts["denominator_count"])
        self.assertEqual(1, counts["numerator_count"])
        self.assertEqual(0.5, value["rate"])
        self.assertTrue(all(value["partition_checks"].values()))

    def test_censored_record_never_becomes_zero_or_neutral(self) -> None:
        value = component("CENSORED", censored=True)
        self.assertEqual("CENSORED", value["computability_status"])
        self.assertNotIn(0, value.values())
        self.assertNotIn("NEUTRAL", value.values())

    def test_mixed_or_duplicate_population_units_fail_closed(self) -> None:
        row = component("DUP")
        with self.assertRaisesRegex(ComputabilityError, "DUPLICATE_POPULATION_UNIT"):
            build_denominator_record(
                [row, copy.deepcopy(row)],
                scope_id="S",
                scope_definition="SCOPE",
                unit_type="OBSERVATION",
                consumer_policy_id="P",
            )
        with self.assertRaisesRegex(ComputabilityError, "UNSUPPORTED_UNIT_TYPE"):
            build_denominator_record(
                [row],
                scope_id="S",
                scope_definition="SCOPE",
                unit_type="MIXED",
                consumer_policy_id="P",
            )

    def test_overlap_preserves_raw_units_and_reports_multi_cluster_membership(self) -> None:
        case = load(FIXTURE)["overlap_case"]
        value = build_overlap_report(
            case["raw_unit_ids"],
            case["clusters"],
            claim_id=case["claim_id"],
            unit_type=case["unit_type"],
            cluster_policy_id=case["cluster_policy_id"],
        )
        for key, expected in case["expected"].items():
            self.assertEqual(expected, value[key])
        self.assertFalse(value["canonical_weighting_selected"])
        self.assertFalse(value["canonical_deduplication_selected"])
        self.assertFalse(value["numeric_adjustment_selected"])
        self.assertFalse(value["raw_population_mutated"])

    def test_overlap_rejects_out_of_population_and_unauthorized_episode_membership(self) -> None:
        with self.assertRaisesRegex(ComputabilityError, "CLUSTER_MEMBER_OUTSIDE_RAW_POPULATION"):
            build_overlap_report(
                ["A"],
                [{"cluster_id": "C", "cluster_type": "SHARED_WINDOW", "member_unit_ids": ["B"]}],
                claim_id="CLAIM",
                unit_type="WINDOW",
                cluster_policy_id="POLICY",
            )
        with self.assertRaisesRegex(ComputabilityError, "SHARED_EPISODE_AUTHORITY_REQUIRED"):
            build_overlap_report(
                ["A"],
                [{"cluster_id": "C", "cluster_type": "SHARED_EPISODE", "member_unit_ids": ["A"]}],
                claim_id="CLAIM",
                unit_type="WINDOW",
                cluster_policy_id="POLICY",
            )

    def test_comparability_fails_closed_on_policy_or_unit_mismatch(self) -> None:
        policy = {
            "consumer_policy_id": "P",
            "version": "1",
            "active": False,
            "canonical": False,
            "assurance_required": False,
        }
        row = apply_consumer_policy(component("CMP"), policy, consumer_authorized=True)
        left = build_denominator_record(
            [row],
            scope_id="S",
            scope_definition="SCOPE",
            unit_type="OBSERVATION",
            consumer_policy_id="P",
        )
        right = copy.deepcopy(left)
        right["overlap_policy_id"] = "OTHER"
        result = compare_population_records(left, right)
        self.assertEqual("NOT_COMPARABLE", result["status"])
        self.assertEqual(["overlap_policy_id"], result["mismatch_fields"])
        same = compare_population_records(left, left)
        self.assertEqual("COMPARABLE", same["status"])
        self.assertEqual([], same["mismatch_fields"])

    def test_legacy_quality_projection_is_transparent_and_non_governing(self) -> None:
        records = [component("Q1"), component("Q2", censored=True)]
        value = project_legacy_quality(records)
        self.assertIsNone(value["global_quality_status"])
        self.assertFalse(value["governing"])
        self.assertFalse(value["may_drive_eligibility"])
        self.assertFalse(value["may_drive_denominator_inclusion"])
        self.assertFalse(value["may_hide_component_status"])
        self.assertEqual({"CENSORED": 1, "COMPUTABLE": 1}, value["component_status_counts"])
        self.assertIn("SOURCE_CENSORED", value["source_reason_codes"])

    def test_registry_schema_and_crosswalk_preserve_cear_g9_boundary(self) -> None:
        registry = load(REGISTRY)
        schema = load(SCHEMA)
        crosswalk = load(CROSSWALK)
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", registry["status"])
        self.assertFalse(registry["active"])
        self.assertFalse(registry["canonical"])
        self.assertIsNone(registry["overlap_policy"]["canonical_weighting"])
        self.assertIsNone(registry["overlap_policy"]["numeric_adjustment"])
        self.assertFalse(registry["legacy_quality_projection"]["governing"])
        self.assertFalse(schema["active"])
        self.assertFalse(schema["canonical"])
        self.assertFalse(crosswalk["compatibility_projection"]["governing"])
        self.assertEqual("MAINTAINED_SHADOW", crosswalk["status"])
        self.assertIn("VALIDATION_PUBLICATION_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", registry["explicitly_not_granted"])


if __name__ == "__main__":
    unittest.main()
