from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs" / "releases" / "discovery-operating-hub-v0-1" / "programme-disposition" / "DO_PROGRAMME_OPERATOR_DEFER_DECISION.json"
REGISTRY = ROOT / "registries" / "research_operations" / "DISCOVERY_OPERATING_HUB_PROGRAMME_DISPOSITION_v0_1.yaml"


class DiscoveryOperatingHubProgrammeDispositionTests(unittest.TestCase):
    def test_operator_defer_decision_is_exact_and_non_activating(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["programme_id"], "OVC-DISCOVERY-OPERATING-HUB.v0.1")
        self.assertEqual(decision["decision"], "DEFER")
        self.assertEqual(decision["decision_authority"], "OPERATOR")
        self.assertFalse(decision["execution_enabled"])
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertIsNone(decision["continuation_point"])
        self.assertEqual(decision["source_pull_request"], 56)
        self.assertEqual(decision["source_pull_request_state"], "CLOSED_UNMERGED")
        self.assertFalse(decision["future_disposition"]["replacement_defined"])
        self.assertFalse(decision["future_disposition"]["automatic_reactivation"])

    def test_registry_preserves_all_reserved_boundaries(self) -> None:
        registry = REGISTRY.read_text(encoding="utf-8")
        for token in (
            "decision: DEFER",
            "execution_enabled: false",
            "authority_delta: NONE",
            "continuation_point: null",
            "source_pull_request_state: CLOSED_UNMERGED",
            "branch_disposition: PRESERVED_NO_DELETE_NO_HISTORY_REWRITE",
            "runtime_activation: DENIED",
            "r2_publication: DENIED",
            "validation_consumption: LOCKED_UNCONSUMED",
            "agent_write_authority: NONE",
            "remote_deployment: DENIED",
        ):
            self.assertIn(token, registry)


if __name__ == "__main__":
    unittest.main()
