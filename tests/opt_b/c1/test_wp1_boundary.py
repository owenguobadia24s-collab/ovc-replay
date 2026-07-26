from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class C1WP1BoundaryTests(unittest.TestCase):
    def test_required_wp1_artifacts_exist(self) -> None:
        required = (
            "contracts/opt_b/c1/OVC_OPT_B_C1_AUTHORITY_BOUNDARY_v0_1.md",
            "registries/opt_b/c1/C1_IMPLEMENTATION_REGISTRY.yaml",
            "registries/opt_b/c1/C1_NAMESPACE_MAP.yaml",
            "registries/opt_b/c1/C1_DEFERRED_CAPABILITIES.yaml",
            "docs/releases/opt-b-c1-v2/wp1/WP1_OPERATOR_DECISION.md",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_only_active_opt_a_v2_is_admissible_upstream(self) -> None:
        boundary = (ROOT / "contracts/opt_b/c1/OVC_OPT_B_C1_AUTHORITY_BOUNDARY_v0_1.md").read_text(encoding="utf-8")
        registry = (ROOT / "registries/opt_b/c1/C1_IMPLEMENTATION_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("active OPT-A v2 role-selector set", boundary)
        self.assertIn("OPT-A.GBPUSD.2026H1.v1", registry)
        self.assertIn("legacy/quarantine/**", registry)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", registry)

    def test_atomic_fact_boundary_excludes_downstream_semantics(self) -> None:
        boundary = (ROOT / "contracts/opt_b/c1/OVC_OPT_B_C1_AUTHORITY_BOUNDARY_v0_1.md").read_text(encoding="utf-8")
        for phrase in (
            "rolling windows, ATR or volatility regimes",
            "reference levels, containers or sessions",
            "C2.5 events or semantic candle names",
            "future paths, outcomes, cohorts, claims or trade labels",
        ):
            self.assertIn(phrase, boundary)

    def test_wp1_boundary_survives_later_shadow_activation(self) -> None:
        authority = (ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        self.assertIn("  opt_a: ACTIVE", authority)
        self.assertIn("  opt_b_c1: SHADOW", authority)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
        self.assertIn("market_replay: COMPLETE_WP4_PASS", authority)
        self.assertIn("r2_publication: COMPLETE_WP5_REMOTE_VERIFIED", authority)
        self.assertIn("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW", authority)
        self.assertIn("probability_authority: NONE", authority)
        self.assertIn("execution_authority: NONE", authority)

    def test_namespace_and_deferred_registers_block_scope_creep(self) -> None:
        namespace = (ROOT / "registries/opt_b/c1/C1_NAMESPACE_MAP.yaml").read_text(encoding="utf-8")
        deferred = (ROOT / "registries/opt_b/c1/C1_DEFERRED_CAPABILITIES.yaml").read_text(encoding="utf-8")
        self.assertIn("rename_legacy_implementation_as_c1: DENIED", namespace)
        self.assertIn("one_identifier_one_meaning: true", namespace)
        self.assertIn("ROLLING_WINDOWS_AND_ATR", deferred)
        self.assertIn("PROBABILITY_EXPOSURE_TRADING_AND_EXECUTION", deferred)
        self.assertIn("state: PROHIBITED", deferred)


if __name__ == "__main__":
    unittest.main()
