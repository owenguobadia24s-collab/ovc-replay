from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from ovc.console_vnext.adapters import (
    ConsoleC1SourceAdapter, ConsoleC2ESourceAdapter, ConsoleC2SourceAdapter,
    GovernanceSourceAdapter, OccurrenceContextSourceAdapter, SFCSourceAdapter,
)
from ovc.console_vnext.application.errors import AuthorityDenied, ContractError, SourceConflict
from ovc.console_vnext.application.models import Availability

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "research_console_vnext" / "wp1" / "characterization.json"
SOURCE = ROOT / "src" / "ovc" / "console_vnext"


def _cases():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


class RCNWP1ApplicationBoundaryTests(unittest.TestCase):
    def test_c1_round_trip_preserves_payload_and_identity(self):
        case = _cases()["c1_available"]
        result = ConsoleC1SourceAdapter().project(case["payload"], case["context"])
        self.assertEqual(result.availability, Availability.AVAILABLE)
        self.assertEqual(result.source_identity.commit, case["context"]["source_commit"])
        self.assertEqual(result.payload, case["payload"])
        self.assertTrue(result.authorised)
        self.assertTrue(result.active)

    def test_validation_is_denied_before_object_resolution(self):
        case = _cases()["c1_validation"]
        with self.assertRaises(AuthorityDenied):
            ConsoleC1SourceAdapter().project(case["payload"], case["context"])

    def test_stale_source_identity_fails_closed(self):
        case = _cases()["c1_available"]
        context = dict(case["context"])
        context["represented_commit"] = "fedcba0987654321"
        with self.assertRaises(SourceConflict):
            ConsoleC1SourceAdapter().project(case["payload"], context)

    def test_c2_axes_and_computability_are_not_collapsed(self):
        case = _cases()["c2_axes"]
        result = ConsoleC2SourceAdapter().project(case["payload"], case["context"])
        self.assertEqual(result.payload["axes"], case["payload"]["axes"])
        self.assertEqual(result.payload["computability"], case["payload"]["computability"])
        bad = dict(case["payload"]); bad["confidence_score"] = 0.9
        with self.assertRaises(ContractError):
            ConsoleC2SourceAdapter().project(bad, case["context"])

    def test_c2e_absence_is_explicit_not_historical_fallback(self):
        case = _cases()["c2e_missing"]
        result = ConsoleC2ESourceAdapter().project_optional(None, case["context"])
        self.assertEqual(result.availability, Availability.NOT_MATERIALIZED)
        self.assertIsNone(result.payload)
        self.assertEqual(result.blockers[0].reason_code, "C2E_CURRENT_GENERATION_NOT_MATERIALIZED")

    def test_occurrence_context_cannot_rewrite_structural_identity(self):
        case = _cases()["occurrence"]
        result = OccurrenceContextSourceAdapter().project(case["payload"], case["context"])
        self.assertEqual(result.payload["metadata_role"], "STRATIFICATION")
        bad = dict(case["payload"]); bad["rewrite_structural_identity"] = True
        with self.assertRaises(AuthorityDenied):
            OccurrenceContextSourceAdapter().project(bad, case["context"])

    def test_sfc_residual_and_null_family_survive_unchanged(self):
        case = _cases()["sfc_residual"]
        result = SFCSourceAdapter().project(case["payload"], case["context"])
        self.assertEqual(result.payload["assignment_status"], "RESIDUAL")
        self.assertIsNone(result.payload["family_id"])
        self.assertEqual(result.payload["reason_code"], "NO_STABLE_FAMILY")

    def test_governance_sources_are_read_only_and_non_commanding(self):
        cases = _cases()
        grt = GovernanceSourceAdapter().project(cases["grt"]["payload"], cases["grt"]["context"])
        self.assertEqual(grt.payload["programme_count"], 8)
        context = dict(cases["irof"]["context"]); context["orchestration_commands_enabled"] = True
        with self.assertRaises(AuthorityDenied):
            GovernanceSourceAdapter().project(cases["irof"]["payload"], context)

    def test_application_boundary_has_no_presentation_framework_imports(self):
        forbidden = {"streamlit", "fastapi"}
        for path in SOURCE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8")); imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module.split(".")[0])
            self.assertFalse(forbidden.intersection(imports), f"{path}: {imports}")


if __name__ == "__main__":
    unittest.main()
