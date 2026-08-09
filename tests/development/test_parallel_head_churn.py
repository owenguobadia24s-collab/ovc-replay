from __future__ import annotations

import copy
import unittest

from ovc.development.head_churn import classify_main_head_movement


BASE = "1" * 40
CURRENT = "2" * 40


class ParallelHeadChurnTests(unittest.TestCase):
    def footprint(self):
        return {
            "schema": "ovc-parallel-development-dependency-footprint/v1",
            "programme_id": "TEST-PROGRAMME",
            "packet_id": "TEST-WP1",
            "plan_id": "TEST-PLAN",
            "baseline_main_sha": BASE,
            "dependency_paths": ["contracts/opt_b/c2e/**"],
            "semantic_authority_paths": ["registries/authority/C2_ACTIVE_DISCOVERY_AUTHORITY.yaml"],
            "shared_integration_paths": ["src/ovc/shared/**"],
            "candidate_owned_paths": ["src/ovc/example/**"],
            "identity_bindings": [
                {"path": "schemas/opt_b/example.schema.json", "identity": "sha256:abc"}
            ],
            "external_identity_bindings": [
                {"logical_name": "frozen-population", "identity": "sha256:def"}
            ],
        }

    def policy(self):
        return {
            "global_integration_patterns": [
                ".github/workflows/**",
                "scripts/development/**",
                "src/ovc/development/**",
                "tests/development/**",
            ]
        }

    def classify(self, paths, footprint=True):
        return classify_main_head_movement(
            baseline_main_sha=BASE,
            current_main_sha=CURRENT,
            changed_main_paths=paths,
            footprint=self.footprint() if footprint else None,
            policy=self.policy(),
        )

    def test_no_main_movement_is_irrelevant(self):
        result = classify_main_head_movement(
            baseline_main_sha=BASE,
            current_main_sha=BASE,
            changed_main_paths=[],
            footprint=None,
            policy=self.policy(),
        )
        self.assertEqual(result["classification"], "IRRELEVANT")
        self.assertFalse(result["main_moved"])

    def test_movement_without_footprint_fails_closed(self):
        result = self.classify(["docs/releases/unrelated/receipt.json"], footprint=False)
        self.assertEqual(result["classification"], "UNRESOLVED_REQUIRES_FOOTPRINT")
        self.assertEqual(result["scientific_evidence_reuse"], "PROHIBITED_PENDING_FOOTPRINT")

    def test_unrelated_change_is_irrelevant_with_footprint(self):
        result = self.classify(["docs/releases/another-programme/receipt.json"])
        self.assertEqual(result["classification"], "IRRELEVANT")
        self.assertEqual(result["scientific_evidence_reuse"], "PERMITTED_IF_BOUND_IDENTITIES_UNCHANGED")

    def test_global_development_workflow_change_is_integration_relevant(self):
        result = self.classify([".github/workflows/tests.yml"])
        self.assertEqual(result["classification"], "INTEGRATION_RELEVANT")
        self.assertTrue(any(row["classification"] == "INTEGRATION_RELEVANT" for row in result["matches"]))

    def test_candidate_owned_change_is_integration_relevant(self):
        result = self.classify(["src/ovc/example/adapter.py"])
        self.assertEqual(result["classification"], "INTEGRATION_RELEVANT")

    def test_consumed_dependency_change_is_semantic(self):
        result = self.classify(["contracts/opt_b/c2e/episode_contract.md"])
        self.assertEqual(result["classification"], "SEMANTIC_AUTHORITY_RELEVANT")
        self.assertEqual(result["scientific_evidence_reuse"], "PROHIBITED_PENDING_SEMANTIC_REPREFLIGHT")

    def test_identity_binding_change_is_semantic(self):
        result = self.classify(["schemas/opt_b/example.schema.json"])
        self.assertEqual(result["classification"], "SEMANTIC_AUTHORITY_RELEVANT")

    def test_semantic_match_wins_over_integration_match(self):
        footprint = self.footprint()
        footprint["semantic_authority_paths"].append(".github/workflows/ovc-tiered-tests.yml")
        result = classify_main_head_movement(
            baseline_main_sha=BASE,
            current_main_sha=CURRENT,
            changed_main_paths=[".github/workflows/ovc-tiered-tests.yml"],
            footprint=footprint,
            policy=self.policy(),
        )
        self.assertEqual(result["classification"], "SEMANTIC_AUTHORITY_RELEVANT")
        self.assertTrue(any(row["classification"] == "INTEGRATION_RELEVANT" for row in result["matches"]))
        self.assertTrue(any(row["classification"] == "SEMANTIC_AUTHORITY_RELEVANT" for row in result["matches"]))

    def test_receipt_is_deterministic_across_path_and_pattern_order(self):
        footprint_a = self.footprint()
        footprint_b = copy.deepcopy(footprint_a)
        footprint_b["dependency_paths"].reverse()
        result_a = classify_main_head_movement(
            baseline_main_sha=BASE,
            current_main_sha=CURRENT,
            changed_main_paths=["src/ovc/example/a.py", ".github/workflows/tests.yml"],
            footprint=footprint_a,
            policy=self.policy(),
        )
        result_b = classify_main_head_movement(
            baseline_main_sha=BASE,
            current_main_sha=CURRENT,
            changed_main_paths=[".github/workflows/tests.yml", "src/ovc/example/a.py"],
            footprint=footprint_b,
            policy=self.policy(),
        )
        self.assertEqual(result_a, result_b)

    def test_changed_paths_with_identical_main_sha_is_invalid(self):
        with self.assertRaises(ValueError):
            classify_main_head_movement(
                baseline_main_sha=BASE,
                current_main_sha=BASE,
                changed_main_paths=["README.md"],
                footprint=self.footprint(),
                policy=self.policy(),
            )


if __name__ == "__main__":
    unittest.main()
