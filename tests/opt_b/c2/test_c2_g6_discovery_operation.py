from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LINE = ROOT / "registries/research/OPT_B_C2_DISCOVERY_LINE_REGISTRY.yaml"
OPERATION = ROOT / "registries/research/C2_DISCOVERY_OPERATION_REGISTRY.yaml"
AUTHORITY = ROOT / "registries/authority/C2_DISCOVERY_OPERATION_AUTHORITY.yaml"
GATE = ROOT / "docs/releases/opt-b-c2-v2/c2-g6/C2_G6_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c2-v2/c2-g6/C2_G6_OPERATOR_DECISION.md"


class C2G6DiscoveryOperationTests(unittest.TestCase):
    def test_gate_opens_only_prospective_research(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_DISCOVERY_OPERATION_OPEN_PROSPECTIVE_ONLY")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertEqual(gate["operation"]["status"], "OPEN_PROSPECTIVE_RESEARCH")
        self.assertFalse(gate["operation"]["pre_cutoff_rows_admissible"])
        self.assertEqual(gate["operation"]["effective_commit"], "2a3f262fc0539786b67ae6c3e20604eb4d4adc2b")

    def test_exact_active_selector_is_bound(self) -> None:
        text = LINE.read_text(encoding="utf-8")
        self.assertIn("selector_state: ACTIVE", text)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", text)
        self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1", text)
        self.assertIn("c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33", text)

    def test_legacy_and_historical_seed_material_are_denied(self) -> None:
        text = LINE.read_text(encoding="utf-8")
        for term in (
            "old 202-story programme",
            "old 58-candidate programme",
            "B-STATE-0.3b cases or labels",
            "OPT-C outcomes",
            "OPT-D validations",
        ):
            self.assertIn(term, text)
        self.assertIn("historical_material_use: CONTEXT_ONLY_NOT_EVIDENCE", text)

    def test_operation_starts_empty_and_append_only(self) -> None:
        text = OPERATION.read_text(encoding="utf-8")
        self.assertIn("accepted_record_count: 0", text)
        self.assertIn("rejected_record_count: 0", text)
        self.assertIn("append_authority: RESEARCH_OPERATIONS_APPEND_ONLY", text)
        self.assertIn("amend_existing_records: DENIED", text)
        self.assertIn("delete_records: DENIED", text)

    def test_non_trading_and_validation_boundaries_remain(self) -> None:
        text = AUTHORITY.read_text(encoding="utf-8")
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertIn("c2e_authority: NONE", text)
        for field in ("probability_authority", "exposure_authority", "trading_authority", "execution_authority"):
            self.assertIn(f"{field}: NONE", text)
        self.assertIn("direct_git_write: DENIED", text)
        self.assertIn("direct_r2_write: DENIED", text)

    def test_operator_decision_names_next_boundary(self) -> None:
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("PASS", text)
        self.assertIn("C2_WP7_PROSPECTIVE_EVIDENCE_ACCUMULATION", text)


if __name__ == "__main__":
    unittest.main()
