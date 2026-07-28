from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.research_operations.v0_3.formula_diff import (
    AcknowledgementRequired,
    ComparisonContractError,
    build_affected_surface_report,
    compare_formula_versions,
    compare_release_outputs,
    comparison_preflight,
    create_comparison_acknowledgement,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/v0_3/wp2_computability_and_diff_cases.json").read_text(encoding="utf-8")
)
BASE = FIXTURE["base_formula"]
CANDIDATE = FIXTURE["candidate_formula_change"]


class C1FormulaDiffTests(unittest.TestCase):
    @staticmethod
    def definition_context(**overrides):
        value = {"comparison_mode": "FORMULA_DEFINITION", "role": "DISCOVERY"}
        value.update(overrides)
        return value

    @staticmethod
    def acknowledgement(comparison_id: str):
        return create_comparison_acknowledgement(
            comparison_id,
            "operator-1",
            "2026-07-28T10:00:00Z",
            "2026-07-28T12:00:00Z",
        )

    def test_acknowledged_formula_diff_is_non_activating_deterministic_and_header_first(self) -> None:
        preflight = comparison_preflight(BASE, CANDIDATE, self.definition_context())
        acknowledgement = self.acknowledgement(preflight["comparison_id"])
        first = compare_formula_versions(
            BASE, CANDIDATE, self.definition_context(), acknowledgement,
            "operator-1", "2026-07-28T10:30:00Z",
        )
        second = compare_formula_versions(
            copy.deepcopy(BASE), copy.deepcopy(CANDIDATE), self.definition_context(),
            copy.deepcopy(acknowledgement), "operator-1", "2026-07-28T10:30:00Z",
        )
        self.assertEqual(first, second)
        self.assertEqual(next(iter(first)), "non_activating_evidence_header")
        self.assertIn("FORMULA_CHANGED", first["classification"])
        self.assertIsNone(first["winner"])
        self.assertEqual(first["authority_effect"], "NONE")
        self.assertEqual(first["writes"], "NONE")

    def test_same_inputs_have_identical_definition_class(self) -> None:
        preflight = comparison_preflight(BASE, BASE, self.definition_context())
        acknowledgement = self.acknowledgement(preflight["comparison_id"])
        result = compare_formula_versions(
            BASE, BASE, self.definition_context(), acknowledgement,
            "operator-1", "2026-07-28T10:30:00Z",
        )
        self.assertEqual(result["classification"], ["IDENTICAL_DEFINITION"])
        self.assertEqual(result["changes"], {})

    def test_one_byte_mutation_changes_comparison_identity_and_hash(self) -> None:
        changed = {**BASE, "formula": BASE["formula"] + " "}
        same_preflight = comparison_preflight(BASE, BASE, self.definition_context())
        changed_preflight = comparison_preflight(BASE, changed, self.definition_context())
        self.assertNotEqual(same_preflight["comparison_id"], changed_preflight["comparison_id"])
        self.assertNotEqual(same_preflight["candidate_sha256"], changed_preflight["candidate_sha256"])

    def test_release_output_comparison_is_order_independent(self) -> None:
        context = {
            "comparison_mode": "RELEASE_OUTPUT",
            "base_instrument": "GBPUSD", "candidate_instrument": "GBPUSD",
            "base_role": "DISCOVERY", "candidate_role": "DISCOVERY",
            "base_clock": "15M", "candidate_clock": "15M",
            "base_side": "BID", "candidate_side": "BID",
            "base_population_sha256": "a" * 64,
            "candidate_population_sha256": "a" * 64,
        }
        rows = [{"record_id": "b", "value": "2"}, {"record_id": "a", "value": "1"}]
        canonical = {"rows": sorted(rows, key=lambda row: row["record_id"])}
        preflight = comparison_preflight(canonical, canonical, context)
        acknowledgement = self.acknowledgement(preflight["comparison_id"])
        result = compare_release_outputs(
            rows, list(reversed(rows)), context, acknowledgement,
            "operator-1", "2026-07-28T10:30:00Z",
        )
        self.assertEqual(result["classification"], ["IDENTICAL_DEFINITION"])
        self.assertEqual(result["changed_record_ids"], [])

    def test_population_change_is_reported_separately_from_output_change(self) -> None:
        context = {
            "comparison_mode": "RELEASE_OUTPUT",
            "base_instrument": "GBPUSD", "candidate_instrument": "GBPUSD",
            "base_role": "DISCOVERY", "candidate_role": "DISCOVERY",
            "base_clock": "15M", "candidate_clock": "15M",
            "base_side": "BID", "candidate_side": "BID",
            "base_population_sha256": "a" * 64,
            "candidate_population_sha256": "b" * 64,
        }
        base_rows = [{"record_id": "a", "value": "1"}]
        candidate_rows = [{"record_id": "b", "value": "1"}]
        preflight = comparison_preflight({"rows": base_rows}, {"rows": candidate_rows}, context)
        acknowledgement = self.acknowledgement(preflight["comparison_id"])
        result = compare_release_outputs(
            base_rows, candidate_rows, context, acknowledgement,
            "operator-1", "2026-07-28T10:30:00Z",
        )
        self.assertIn("POPULATION_CHANGED", result["classification"])
        self.assertNotIn("OUTPUT_CHANGED", result["classification"])

    def test_role_contrast_is_distinct_and_validation_is_denied(self) -> None:
        contrast = {
            "comparison_mode": "ROLE_CONTRAST",
            "base_role": "DISCOVERY",
            "candidate_role": "DEVELOPMENT",
        }
        self.assertEqual(comparison_preflight(BASE, BASE, contrast)["status"], "COMPARABLE")
        with self.assertRaises(ComparisonContractError):
            comparison_preflight(
                BASE, BASE,
                {"comparison_mode": "FORMULA_DEFINITION", "role": "VALIDATION"},
            )

    def test_affected_surface_is_compact_separate_and_trace_only(self) -> None:
        result = build_affected_surface_report(
            "ro3-c1-comparison:" + "a" * 64,
            [
                {
                    "surface_type": "C2_CHILD",
                    "child_id": "c2-1",
                    "source_binding": "binding-1",
                    "consequence": "READ_ONLY_TRACE",
                    "availability": "AVAILABLE",
                },
                {
                    "surface_type": "PATTERN_DISCOVERY_TRACE",
                    "child_id": "pd-1",
                    "source_binding": "binding-1",
                    "consequence": "READ_ONLY_TRACE",
                    "availability": "AVAILABLE",
                    "operation_mode": "TIME_GATED_REPLAY",
                },
            ],
        )
        self.assertEqual(result["presentation"], "SEPARATE_BANNERED_TRACE_ONLY")
        self.assertFalse(result["co_render_with_c1_null_explanation"])
        self.assertEqual(result["authority_effect"], "NONE")
        with self.assertRaises(ComparisonContractError):
            build_affected_surface_report(
                "ro3-c1-comparison:" + "b" * 64,
                [{
                    "surface_type": "C2_CHILD", "child_id": "c2-1",
                    "source_binding": "binding-1", "consequence": "TRACE",
                    "availability": "AVAILABLE", "raw_payload": {"state": "forbidden"},
                }],
            )


if __name__ == "__main__":
    unittest.main()
