from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import validate_instance
from ovc.programme_genesis.grt_v0_2.qualification import (
    ASSURANCE_AXES, PERFORMANCE_SURFACES, PerformanceBudgetError,
    build_qualification_record, build_qualification_target, evaluate_g2_readiness, freeze_performance_budget,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas/governance/grt_v0_2/performance_budget.schema.json"


class GRT2WP3EQualificationTests(unittest.TestCase):
    def target(self):
        return build_qualification_target(
            constitution_hash="a"*64, runtime_hash="b"*64, scanner_hash="c"*64,
            platform_classes=["ubuntu-python"], mutation_catalogue_hash="d"*64,
        )

    def passing_qualification(self):
        return build_qualification_record(
            target=self.target(), axis_results={axis:"PASS" for axis in ASSURANCE_AXES},
            mutation_survivors=0, reference_incremental_differences=0,
            unresolved_false_negatives=0, blocking_false_positives=0,
            capacity_status="PASS", restart_status="PASS", platform_status="PASS", shadow_status="PASS",
            evidence_refs=["fixture:qualification"],
        )

    def synthetic_measurements(self):
        rows = []
        for surface_index, surface in enumerate(PERFORMANCE_SURFACES):
            for index in range(20):
                rows.append({
                    "surface": surface,
                    "duration_ms": 10 + surface_index * 5 + index,
                    "peak_memory_bytes": 1000 + surface_index * 100 + index,
                    "evidence_ref": f"synthetic:{surface}:{index}",
                })
        return rows

    def test_qualification_requires_all_axes_and_zero_tolerance_counts(self) -> None:
        passed = self.passing_qualification()
        self.assertEqual(passed["decision"], "PASS")
        failed = build_qualification_record(
            target=self.target(), axis_results={axis:"PASS" for axis in ASSURANCE_AXES},
            mutation_survivors=1, reference_incremental_differences=0,
            unresolved_false_negatives=0, blocking_false_positives=0,
            capacity_status="PASS", restart_status="PASS", platform_status="PASS", shadow_status="PASS",
            evidence_refs=["fixture:mutation-survivor"],
        )
        self.assertEqual(failed["decision"], "FAIL")

    def test_performance_budget_refuses_insufficient_measurement(self) -> None:
        with self.assertRaises(PerformanceBudgetError):
            freeze_performance_budget(samples=[], environment_hash="e"*64, repository_scale=100,
                                      cache_storage_ceiling_bytes=1000, proof_evidence_size_ceiling_bytes=1000,
                                      capacity_failure_threshold=100)

    def test_synthetic_budget_algorithm_is_deterministic_but_not_g2_evidence(self) -> None:
        kwargs = dict(
            samples=self.synthetic_measurements(), environment_hash="e"*64, repository_scale=100,
            cache_storage_ceiling_bytes=2000, proof_evidence_size_ceiling_bytes=3000,
            capacity_failure_threshold=100,
        )
        a = freeze_performance_budget(**kwargs)
        b = freeze_performance_budget(**kwargs)
        self.assertEqual(a, b)
        self.assertEqual(a["runtime_budgets"]["GRT_FAST"]["sample_count"], 20)
        validate_instance(a, json.loads(SCHEMA.read_text(encoding="utf-8")))
        self.assertTrue(all(ref.startswith("synthetic:") for ref in a["measurement_evidence_refs"]))

    def test_g2_readiness_requires_measured_budget_and_zero_transition_debt(self) -> None:
        qualification = self.passing_qualification()
        blocked = evaluate_g2_readiness(qualification=qualification, performance_budget=None, transition_debt_count=0)
        self.assertEqual(blocked["status"], "BLOCKED")
        budget = freeze_performance_budget(
            samples=self.synthetic_measurements(), environment_hash="e"*64, repository_scale=100,
            cache_storage_ceiling_bytes=2000, proof_evidence_size_ceiling_bytes=3000,
            capacity_failure_threshold=100,
        )
        passed = evaluate_g2_readiness(qualification=qualification, performance_budget=budget, transition_debt_count=0)
        self.assertEqual(passed["status"], "PASS")
        debt = evaluate_g2_readiness(qualification=qualification, performance_budget=budget, transition_debt_count=1)
        self.assertEqual(debt["status"], "BLOCKED")
        self.assertIn("PRE_ENFORCEMENT_TRANSITION_DEBT_NONZERO", debt["reason_codes"])


if __name__ == "__main__":
    unittest.main()
