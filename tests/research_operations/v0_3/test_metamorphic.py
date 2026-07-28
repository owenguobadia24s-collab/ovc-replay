from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from ovc.opt_b.c1 import build, dumps
from ovc.research_operations.v0_3 import (
    contract_oracle,
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


class C1MetamorphicAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
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

    def test_frozen_registry_and_formula_registry_cover_same_18_primitives(self) -> None:
        invariant_ids = {item["primitive_id"] for item in self.invariants["invariants"]}
        formula_ids = {item["primitive_id"] for item in self.formulas["formulas"]}
        self.assertEqual(invariant_ids, formula_ids)
        self.assertEqual(len(invariant_ids), 18)
        self.assertEqual(self.invariants["status"], "FROZEN_AT_RO3_G0")

    def test_all_metamorphic_relations_and_determinism_pass(self) -> None:
        result = self.run_actual()
        metamorphic_failures = [
            item for item in result["metamorphic_assertions"] if item["status"] != "PASS"
        ]
        self.assertEqual(metamorphic_failures, [])
        self.assertTrue(result["determinism_receipt"]["same_input_same_output_bytes"])
        self.assertTrue(result["determinism_receipt"]["canonical_reorder_identical"])

    def test_independent_golden_oracle_detects_frozen_formula_implementation_mismatch(self) -> None:
        result = self.run_actual()
        failed = [item for item in result["golden_assertions"] if item["status"] == "FAIL"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["primitive_id"], "C1-WICK-BALANCE.v0.1")
        self.assertEqual(
            failed[0]["expected"],
            FIXTURE["hand_verified"]["wick_balance_formula_registry_expected"],
        )
        self.assertEqual(failed[0]["actual"], "0.1428571428571428571428571429")
        self.assertEqual(result["status"], "BLOCK")

    def test_contract_oracle_matches_hand_verified_geometry(self) -> None:
        oracle = contract_oracle(FIXTURE["current"], FIXTURE["prior"])
        expected = FIXTURE["hand_verified"]
        for field in (
            "range_abs", "range_ticks", "body_signed", "body_abs",
            "upper_wick_abs", "lower_wick_abs", "upper_wick_share",
            "lower_wick_share", "true_range_abs", "close_change", "open_gap",
        ):
            self.assertEqual(oracle["measurements"][field], expected[field])
        self.assertEqual(
            oracle["measurements"]["wick_balance"],
            expected["wick_balance_formula_registry_expected"],
        )
        self.assertEqual(oracle["categorical"]["direction"], expected["direction"])

    def test_deliberately_corrupted_implementation_is_detected(self) -> None:
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
