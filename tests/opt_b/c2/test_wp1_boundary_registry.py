from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "registries" / "opt_b" / "c2"
GATE = ROOT / "docs" / "releases" / "opt-b-c2-v2" / "wp1" / "WP1_GATE_PACKET.json"


class C2WP1BoundaryRegistryTests(unittest.TestCase):
    def test_gate_passes_with_no_blockers(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_C2_BOUNDARY_RETIREMENT_AND_RESEARCH_LINE_FROZEN")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertEqual(len(gate["checks"]), 7)
        self.assertTrue(all(item["status"] == "PASS" for item in gate["checks"]))

    def test_namespaces_are_reserved_without_semantic_or_episode_fields(self) -> None:
        text = (BASE / "C2_NAMESPACE_MAP.yaml").read_text(encoding="utf-8")
        for namespace in ("C2.L", "C2.K", "C2.R", "C2.S", "C2.T", "C2.Q"):
            self.assertIn(namespace, text)
        for field in ("overall_state", "winning_state", "episode_id", "future_outcome", "trade_label"):
            self.assertIn(field, text)

    def test_dependency_and_retirement_boundaries_are_fail_closed(self) -> None:
        dependency = (BASE / "C2_DEPENDENCY_POLICY.yaml").read_text(encoding="utf-8")
        retirement = (BASE / "C2_LEGACY_RETIREMENT_PLAN.yaml").read_text(encoding="utf-8")
        self.assertIn("B-STATE-0.3b runtime imports or parentage", dependency)
        self.assertIn("reverse_write_to_c1: PROHIBITED", dependency)
        self.assertIn("reactivate_b_state: PROHIBITED", retirement)
        self.assertIn("target: C1_ACTIVE_C2_NONE", retirement)

    def test_wp1_does_not_grant_engine_replay_or_selector_authority(self) -> None:
        registry = (BASE / "C2_IMPLEMENTATION_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("status: WP1_PASS_BOUNDARY_FROZEN_WP2_AUTHORISED", registry)
        self.assertIn("engine_implementation: DENIED_PENDING_WP2", registry)
        self.assertIn("market_replay: DENIED_PENDING_C2_G2_AND_OPERATOR_APPROVAL", registry)
        self.assertIn("selector: NONE", registry)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", registry)


if __name__ == "__main__":
    unittest.main()
