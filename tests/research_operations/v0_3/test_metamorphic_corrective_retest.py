from __future__ import annotations

import json
import unittest
from dataclasses import replace
from decimal import getcontext
from pathlib import Path

from ovc.opt_b.c1 import build, dumps
from ovc.research_operations.v0_3 import (
    load_invariant_registry,
    parse_formula_registry,
    run_metamorphic_assurance,
)


ROOT = Path(__file__).resolve().parents[3]
INVARIANT_TEXT = (
    ROOT / "registries/research_operations/v0_3/C1_METAMORPHIC_INVARIANT_REGISTRY_v0_1.yaml"
).read_text(encoding="utf-8")
FORMULA_TEXT = (
    ROOT / "registries/opt_b/c1/C1_FORMULA_REGISTRY_v0_1.yaml"
).read_text(encoding="utf-8")
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/v0_3/wp3_metamorphic_cases.json").read_text(encoding="utf-8")
)


class CorrectiveMetamorphicRetest(unittest.TestCase):
    def setUp(self) -> None:
        getcontext().prec = 34
        self.invariants = load_invariant_registry(INVARIANT_TEXT)
        self.formulas = parse_formula_registry(FORMULA_TEXT)

    def run_actual(self):
        return run_metamorphic_assurance(
            self.invariants,
            self.formulas,
            build,
            FIXTURE["current"],
            FIXTURE["prior"],
            dumps,
        )

    def test_corrected_implementation_passes_all_independent_assertions(self) -> None:
        result = self.run_actual()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed_assertion_count"], 0)
        self.assertEqual(result["failed_assertions"], [])
        self.assertEqual(result["metamorphic_assertion_count"], 79)
        self.assertEqual(result["golden_assertion_count"], 18)

    def test_corrected_wick_balance_matches_frozen_upper_minus_lower_formula(self) -> None:
        result = self.run_actual()
        assertion = next(
            item for item in result["golden_assertions"]
            if item["primitive_id"] == "C1-WICK-BALANCE.v0.1"
        )
        self.assertEqual(assertion["status"], "PASS")
        self.assertEqual(
            assertion["actual"],
            "-0.1428571428571428571428571428571429",
        )
        self.assertEqual(assertion["actual"], assertion["expected"])

    def test_determinism_and_canonical_reorder_still_pass(self) -> None:
        receipt = self.run_actual()["determinism_receipt"]
        self.assertTrue(receipt["same_input_same_output_bytes"])
        self.assertTrue(receipt["canonical_reorder_identical"])
        self.assertEqual(receipt["base_sha256"], receipt["rerun_sha256"])

    def test_negative_control_remains_detectable(self) -> None:
        def corrupted(current: dict, prior: dict | None):
            result = build(current, prior)
            measurements = dict(result.measurements)
            measurements["body_abs"] = "999"
            return replace(result, measurements=measurements)

        result = run_metamorphic_assurance(
            self.invariants,
            self.formulas,
            corrupted,
            FIXTURE["current"],
            FIXTURE["prior"],
            dumps,
        )
        failed_ids = {item.get("primitive_id") for item in result["failed_assertions"]}
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("C1-BODY-ABS.v0.1", failed_ids)


if __name__ == "__main__":
    unittest.main()
