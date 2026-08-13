from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.wp0 import (
    B0_ANOMALY_COUNT,
    B0_COMPONENT_COUNT,
    B0_COMPONENT_EDGE_COUNT,
    B0_PROGRAMME_COUNT,
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    B0_WARNING_COUNT,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WP0_ROOT = REPOSITORY_ROOT / "docs/programmes/grt-v0-2/wp0"

class GRT2WP0ContractTests(unittest.TestCase):
    def test_frozen_b0_source_constants_match_ratified_wp0_contract(self) -> None:
        self.assertEqual(B0_SOURCE_COMMIT, "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4")
        self.assertEqual(B0_SOURCE_TREE, "91374c54bde0e0b61ac51705f6434d4f2b0d8417")
        self.assertEqual(B0_TOPOLOGY_SHA256, "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2")
        self.assertEqual((B0_WARNING_COUNT, B0_ANOMALY_COUNT, B0_PROGRAMME_COUNT, B0_COMPONENT_COUNT, B0_COMPONENT_EDGE_COUNT), (569, 1364, 53, 4615, 11861))

    def test_materialised_source_identity_is_exact_and_non_enforcing(self) -> None:
        identity = json.loads((WP0_ROOT / "GRT2_SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["plan"]["plan_id"], "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED")
        self.assertEqual(identity["plan"]["sha256"], "c81e1368f4e25c77906d378772379b04910b5c8f93fc9b21f988749602a9bedb")
        self.assertEqual(identity["design"]["sha256"], "bee3b1d9095a5f45f141abae550af35acb1a2aceca1bee555e59ddd2a19de9d7")
        self.assertEqual(identity["materialisation_baseline"]["commit"], "32531afdacb7435aef2b45b71f503e0dfde502c8")
        self.assertEqual(identity["authority_effect"], "MATERIALISE_ALREADY_RATIFIED_G0_ONLY")

    def test_pgn_defer_all_is_preserved_as_future_critical_path(self) -> None:
        critical = json.loads((WP0_ROOT / "GRT2_PGN_CRITICAL_PATH.json").read_text(encoding="utf-8"))
        self.assertEqual(critical["source"]["candidate_count"], 16)
        self.assertEqual(critical["source"]["decision_counts"], {"PASS":0,"DEFER":16,"BLOCK":0,"QUARANTINE":0})
        self.assertEqual(critical["source"]["native_records_created"], 0)
        self.assertEqual(critical["programme_effect"]["PGN-WP4"], "DEFERRED_INDEFINITELY")
        self.assertIn("PGN_AUTHORITY_REQUIRED_CURRENT", critical["future_gate_status"])

    def test_github_ruleset_visibility_is_direct_and_squash_only(self) -> None:
        census = json.loads((WP0_ROOT / "GRT2_GITHUB_ASSURANCE_CENSUS.json").read_text(encoding="utf-8"))
        self.assertFalse(census["visibility_gap"])
        self.assertEqual(census["repository_ruleset_visibility"], "DIRECT")
        self.assertEqual(census["ruleset"]["required_status_checks"], [{"context":"OVC merge readiness","integration_id":15368}])
        self.assertEqual(census["ruleset"]["allowed_merge_methods"], ["squash"])
        self.assertTrue(census["ruleset"]["non_fast_forward_prohibited"])
        self.assertEqual(census["ruleset"]["current_user_can_bypass"], "never")

    def test_wp0_reproduction_plan_never_redefines_b0_from_current_census(self) -> None:
        plan = json.loads((WP0_ROOT / "GRT2_B0_RECONCILIATION_PLAN.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["immutable_b0"]["expected_raw_warning_count"], 569)
        self.assertIn("never redefine B0", " ".join(plan["fresh_census_method"]))
        self.assertIn("B0_SOURCE_NOT_REPRODUCIBLE", plan["gate_rule"])

if __name__ == "__main__":
    unittest.main()
