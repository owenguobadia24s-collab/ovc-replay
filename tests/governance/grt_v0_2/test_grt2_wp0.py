from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2 import reconcile as public_reconcile
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
        self.assertEqual(
            (B0_WARNING_COUNT, B0_ANOMALY_COUNT, B0_PROGRAMME_COUNT, B0_COMPONENT_COUNT, B0_COMPONENT_EDGE_COUNT),
            (569, 1364, 53, 4615, 11861),
        )

    def test_public_wp0_reconcile_uses_non_inferential_evidence_adapter(self) -> None:
        self.assertEqual(public_reconcile.__module__, "ovc.programme_genesis.grt_v0_2.wp0_evidence")

    def test_materialised_source_identity_is_exact_and_non_enforcing(self) -> None:
        identity = json.loads((WP0_ROOT / "GRT2_SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["plan"]["plan_id"], "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED")
        self.assertEqual(identity["plan"]["sha256"], "c81e1368f4e25c77906d378772379b04910b5c8f93fc9b21f988749602a9bedb")
        self.assertEqual(identity["design"]["sha256"], "bee3b1d9095a5f45f141abae550af35acb1a2aceca1bee555e59ddd2a19de9d7")
        self.assertEqual(identity["authority_effect"], "MATERIALISE_ALREADY_RATIFIED_G0_ONLY")

    def test_pgn_defer_all_is_preserved_as_future_critical_path(self) -> None:
        critical = json.loads((WP0_ROOT / "GRT2_PGN_CRITICAL_PATH.json").read_text(encoding="utf-8"))
        self.assertEqual(critical["source"]["candidate_count"], 16)
        self.assertEqual(critical["source"]["decision_counts"], {"PASS": 0, "DEFER": 16, "BLOCK": 0, "QUARANTINE": 0})
        self.assertEqual(critical["source"]["native_records_created"], 0)
        self.assertIn("PGN_AUTHORITY_REQUIRED_CURRENT", critical["future_gate_status"])

    def test_github_ruleset_visibility_is_direct_and_squash_only(self) -> None:
        census = json.loads((WP0_ROOT / "GRT2_GITHUB_ASSURANCE_CENSUS.json").read_text(encoding="utf-8"))
        self.assertFalse(census["visibility_gap"])
        self.assertEqual(census["repository_ruleset_visibility"], "DIRECT")
        self.assertEqual(census["ruleset"]["required_status_checks"], [{"context": "OVC merge readiness", "integration_id": 15368}])
        self.assertEqual(census["ruleset"]["allowed_merge_methods"], ["squash"])
        self.assertTrue(census["ruleset"]["non_fast_forward_prohibited"])
        self.assertEqual(census["ruleset"]["current_user_can_bypass"], "never")

    def test_wp0_reproduction_plan_never_redefines_or_maps_b0_by_raw_id(self) -> None:
        plan = json.loads((WP0_ROOT / "GRT2_B0_RECONCILIATION_PLAN.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["immutable_b0"]["expected_raw_warning_count"], 569)
        method = " ".join(plan["fresh_census_method"])
        self.assertIn("never redefine B0", method)
        self.assertIn("diagnostic only", method)
        self.assertIn("WP2", method)
        self.assertIn("B0_SOURCE_NOT_REPRODUCIBLE", plan["gate_rule"])

    def test_exact_ci_evidence_when_supplied_or_gate_contract_when_not(self) -> None:
        evidence_dir_text = os.environ.get("GRT2_WP0_EVIDENCE_DIR")
        if not evidence_dir_text:
            plan = json.loads((WP0_ROOT / "GRT2_B0_RECONCILIATION_PLAN.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["immutable_b0"]["source_commit"], B0_SOURCE_COMMIT)
            self.assertEqual(plan["immutable_b0"]["expected_topology_sha256"], B0_TOPOLOGY_SHA256)
            return

        evidence_dir = Path(evidence_dir_text)
        b0 = json.loads((evidence_dir / "GRT2_B0_REPRODUCTION.json").read_text(encoding="utf-8"))
        current = json.loads((evidence_dir / "GRT2_CURRENT_DEBT_CENSUS.json").read_text(encoding="utf-8"))
        identity = json.loads((WP0_ROOT / "GRT2_SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(b0["source_commit"], B0_SOURCE_COMMIT)
        self.assertEqual(b0["source_tree"], B0_SOURCE_TREE)
        self.assertEqual(b0["topology_sha256"], B0_TOPOLOGY_SHA256)
        self.assertEqual(b0["raw_warning_count"], 569)
        self.assertEqual(b0["anomaly_count"], 1364)
        self.assertEqual(b0["determinism"]["result"], "PASS")
        self.assertEqual(len(b0["members"]), 569)
        self.assertEqual(len({row["anomaly_id"] for row in b0["members"]}), 569)
        self.assertEqual(sum(b0["warning_category_counts"].values()), 569)
        self.assertEqual(current["baseline"]["commit"], identity["materialisation_baseline"]["commit"])
        self.assertEqual(current["baseline"]["tree"], identity["materialisation_baseline"]["tree"])
        self.assertNotIn("classification", current)
        lineage = current["lineage_classification"]
        self.assertEqual(lineage["status"], "DEFERRED_TO_GRT2_WP2")
        self.assertEqual(lineage["authority_effect"], "NONE_DIAGNOSTIC_ONLY")
        self.assertEqual(current["transition_debt_status"], "NOT_EVALUATED_AT_WP0")


if __name__ == "__main__":
    unittest.main()
