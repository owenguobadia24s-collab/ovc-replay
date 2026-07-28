from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.research_operations.v0_3.formula_diff import (
    AcknowledgementRequired,
    build_non_activating_evidence_header,
    compare_formula_versions,
    comparison_preflight,
    create_comparison_acknowledgement,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/v0_3/wp2_computability_and_diff_cases.json").read_text(encoding="utf-8")
)
BASE = FIXTURE["base_formula"]
CONTEXT = {"comparison_mode": "FORMULA_DEFINITION", "role": "DISCOVERY"}


class C1ComparisonAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preflight = comparison_preflight(BASE, BASE, CONTEXT)
        self.acknowledgement = create_comparison_acknowledgement(
            self.preflight["comparison_id"],
            "operator-1",
            "2026-07-28T10:00:00Z",
            "2026-07-28T12:00:00Z",
        )

    def test_header_states_non_activation_and_acknowledgement_requirement(self) -> None:
        header = build_non_activating_evidence_header(self.preflight)
        self.assertEqual(header["evidence_class"], "NON_ACTIVATING_EVIDENCE")
        self.assertEqual(header["authority_effect"], "NONE")
        self.assertEqual(header["detailed_diff_access"], "ACKNOWLEDGEMENT_REQUIRED")
        self.assertIn("FORMULA_MUTATION", header["prohibited_effects"])
        self.assertIn("VALIDATION_CONSUMPTION", header["prohibited_effects"])

    def test_missing_acknowledgement_denies_detailed_diff(self) -> None:
        with self.assertRaisesRegex(AcknowledgementRequired, "ACKNOWLEDGEMENT_REQUIRED"):
            compare_formula_versions(
                BASE, BASE, CONTEXT, None,
                "operator-1", "2026-07-28T10:30:00Z",
            )

    def test_mismatch_operator_and_expiry_fail_closed(self) -> None:
        with self.assertRaises(AcknowledgementRequired):
            compare_formula_versions(
                BASE, BASE, CONTEXT,
                {**self.acknowledgement, "comparison_id": "ro3-c1-comparison:" + "0" * 64},
                "operator-1", "2026-07-28T10:30:00Z",
            )
        with self.assertRaises(AcknowledgementRequired):
            compare_formula_versions(
                BASE, BASE, CONTEXT, self.acknowledgement,
                "operator-2", "2026-07-28T10:30:00Z",
            )
        with self.assertRaises(AcknowledgementRequired):
            compare_formula_versions(
                BASE, BASE, CONTEXT, self.acknowledgement,
                "operator-1", "2026-07-28T12:00:00Z",
            )

    def test_acknowledgement_is_append_only_non_approval_evidence(self) -> None:
        self.assertEqual(self.acknowledgement["record_state"], "FROZEN_APPEND_ONLY")
        self.assertEqual(self.acknowledgement["authority_effect"], "NONE")
        self.assertIsNone(self.acknowledgement["supersedes"])
        statement = self.acknowledgement["acknowledged_statement"].lower()
        self.assertIn("non-activating evidence", statement)
        self.assertIn("not approval", statement)

    def test_detailed_output_has_no_winner_or_activation_effect(self) -> None:
        result = compare_formula_versions(
            BASE, BASE, CONTEXT, self.acknowledgement,
            "operator-1", "2026-07-28T10:30:00Z",
        )
        self.assertIsNone(result["winner"])
        self.assertEqual(result["authority_effect"], "NONE")
        self.assertEqual(result["writes"], "NONE")
        payload = json.dumps(result, sort_keys=True)
        self.assertNotIn('"selector_write"', payload)
        self.assertNotIn('"threshold_write"', payload)
        self.assertNotIn('"r2_write"', payload)


if __name__ == "__main__":
    unittest.main()
