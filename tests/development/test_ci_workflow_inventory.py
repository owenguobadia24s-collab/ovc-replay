from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/development/ci_workflow_inventory.py"
POLICY_DIR = ROOT / "registries/development"
CURRENT_VERSION = "0_7"
HISTORICAL_VERSIONS = ("0_6", "0_5", "0_4", "0_3", "0_2", "0_1")
EXPECTED_SNAPSHOTS = {
    "0_7": (191, 137, 54),
    "0_6": (191, 136, 55),
    "0_5": (191, 135, 56),
    "0_4": (191, 134, 57),
    "0_3": (191, 133, 58),
    "0_2": (177, 131, 46),
    "0_1": (175, 129, 46),
}
EXPECTED_SUPERSESSION_CHAIN = {
    "0_7": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.6",
    "0_6": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.5",
    "0_5": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.4",
    "0_4": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.3",
    "0_3": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.2",
}

spec = importlib.util.spec_from_file_location("ci_workflow_inventory", SCRIPT_PATH)
assert spec and spec.loader
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)


def load_policy(version: str) -> dict:
    return json.loads(
        (POLICY_DIR / f"OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v{version}.json").read_text(encoding="utf-8")
    )


class CiWorkflowInventoryGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(CURRENT_VERSION)
        self.historical = {version: load_policy(version) for version in HISTORICAL_VERSIONS}
        self.inventory = inventory_module.build_inventory(ROOT, self.policy)
        self.records = {row["path"]: row for row in self.inventory["records"]}

    def test_current_inventory_is_exhaustive_and_exact(self):
        inventory_module.validate_inventory(self.inventory, self.policy)
        expected = self.policy["snapshot"]["expected_repository_workflow_definition_count"]
        self.assertEqual(expected, 137)
        self.assertEqual(self.inventory["total_workflow_definitions"], expected)
        self.assertEqual(sum(self.inventory["category_counts"].values()), expected)
        self.assertTrue(set(self.inventory["category_counts"]).issubset(set(self.policy["categories"])))
        print(
            "OVC_CI_WORKFLOW_CENSUS "
            + json.dumps(
                {
                    "total_workflow_definitions": self.inventory["total_workflow_definitions"],
                    "category_counts": self.inventory["category_counts"],
                    "trigger_counts": self.inventory["trigger_counts"],
                },
                sort_keys=True,
            )
        )

    def test_current_and_historical_snapshot_chain_is_preserved(self):
        policies = {CURRENT_VERSION: self.policy, **self.historical}
        for version, expected in EXPECTED_SNAPSHOTS.items():
            snapshot = policies[version]["snapshot"]
            observed = (
                snapshot["github_actions_registered_total_count"],
                snapshot["expected_repository_workflow_definition_count"],
                snapshot["registration_count_excess"],
            )
            self.assertEqual(observed, expected, version)
        for version, predecessor_id in EXPECTED_SUPERSESSION_CHAIN.items():
            self.assertEqual(policies[version]["supersedes_for_current_inventory"], predecessor_id, version)
        self.assertEqual(
            self.policy["historical_policy_preserved"],
            "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_6.json",
        )
        self.assertIn("NOT_REMEASURED", self.policy["snapshot"]["github_actions_source"])

    def test_exactly_two_approved_pull_request_listeners_remain(self):
        pr_paths = sorted(
            record["path"] for record in self.inventory["records"] if "pull_request" in record["triggers"]
        )
        self.assertEqual(pr_paths, sorted(self.policy["approved_pull_request_workflows"]))
        self.assertEqual(pr_paths, [
            ".github/workflows/ovc-tiered-tests.yml",
            ".github/workflows/tests.yml",
        ])
        self.assertEqual(self.inventory["category_counts"]["CURRENT_PR_CI"], 2)

    def test_r4_capacity_recovery_workflow_is_bounded_non_pr_and_non_promoting(self):
        admission = self.policy["admitted_new_workflow"]
        path = ".github/workflows/c2p2-rs0-r4-capacity-recovery.yml"
        self.assertEqual(admission["path"], path)
        record = self.records[path]
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["push"])
        self.assertNotIn("pull_request", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        mode = admission["authority_mode"]
        for marker in (
            "BOUNDED_R4_CAPACITY_RECOVERY",
            "SYNTHETIC_ONLY",
            "NO_REAL_SOURCE",
            "NO_FRESH_GRUN",
            "NO_SELECTION",
            "NO_ACTIVATION",
            "NO_VALIDATION",
            "NO_PUBLICATION",
            "NO_REQUIRED_CHECK_SUBSTITUTION",
        ):
            self.assertIn(marker, mode)

    def test_v06_current_source_workflow_admission_is_preserved(self):
        path = ".github/workflows/c2p2-rs0-current-source-materialisation.yml"
        admission = next(item for item in self.policy["additional_non_pr_diagnostic_workflows"] if item["path"] == path)
        historical = self.historical["0_6"]["admitted_new_workflow"]
        self.assertEqual(admission["authority_mode"], historical["authority_mode"])
        record = self.records[path]
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["push"])
        self.assertNotIn("pull_request", record["triggers"])
        self.assertIn("NO_GRUN_CONSUMPTION", admission["authority_mode"])

    def test_preserved_diagnostic_workflows_remain_non_pr(self):
        admissions = {item["path"]: item for item in self.policy["additional_non_pr_diagnostic_workflows"]}
        expected = {
            ".github/workflows/vit-post-merge-completion.yml": ("POST_WRITE_COMPLETION_OBSERVABILITY_ONLY", "NO_MERGE_AUTHORITY"),
            ".github/workflows/ci-unittest-shard-shadow.yml": ("SHADOW_ONLY", "NO_REQUIRED_CHECK_SUBSTITUTION"),
            ".github/workflows/pyt-wp2-step5-unified.yml": ("DIAGNOSTIC_ONLY", "NO_REQUIRED_CHECK_SUBSTITUTION"),
            ".github/workflows/grt2-g2-qualification.yml": ("QUALIFICATION_EVIDENCE_ONLY", "NO_REQUIRED_CHECK_SUBSTITUTION"),
            ".github/workflows/grt2-g2-performance.yml": ("MEASUREMENT_EVIDENCE_ONLY", "NO_REQUIRED_CHECK_SUBSTITUTION"),
            ".github/workflows/dsai3v-async-assurance-shadow.yml": ("SHADOW_ONLY", "NO_REQUIRED_CHECK_SUBSTITUTION", "NO_WRITE"),
        }
        for path, markers in expected.items():
            self.assertIn(path, admissions)
            self.assertIn(path, self.records)
            self.assertNotIn("pull_request", self.records[path]["triggers"])
            for marker in markers:
                self.assertIn(marker, admissions[path]["authority_mode"])

    def test_classification_is_deterministic(self):
        self.assertEqual(self.inventory, inventory_module.build_inventory(ROOT, self.policy))

    def test_non_pr_workflows_are_classified_without_mutation(self):
        non_pr = [record for record in self.inventory["records"] if "pull_request" not in record["triggers"]]
        expected = self.policy["snapshot"]["expected_repository_workflow_definition_count"] - len(
            self.policy["approved_pull_request_workflows"]
        )
        self.assertEqual(len(non_pr), expected)
        allowed = {"TEMPORARY", "HISTORICAL_MANUAL_VERIFICATION", "ACTIVE_MANUAL_OPERATION"}
        self.assertTrue(all(record["category"] in allowed for record in non_pr))
        self.assertFalse(self.inventory["destructive_actions_performed"])

    def test_policy_prohibits_destructive_cleanup_and_required_check_mutation(self):
        governance = self.policy["governance"]
        self.assertTrue(governance["classification_only"])
        self.assertEqual(governance["workflow_deletion"], "PROHIBITED")
        self.assertEqual(governance["workflow_disablement"], "PROHIBITED_BY_THIS_PACKET")
        self.assertIn("PROHIBITED_EXCEPT", governance["trigger_mutation"])
        self.assertEqual(governance["required_check_mutation"], "PROHIBITED_BY_THIS_PACKET")
        self.assertEqual(governance["historical_evidence_preservation"], "REQUIRED")
        self.assertEqual(governance["registry_repository_count_mismatch"], "OBSERVE_AND_RECORD_ONLY")

    def test_repository_categories_are_observable(self):
        categories = self.inventory["category_counts"]
        self.assertGreater(categories.get("HISTORICAL_MANUAL_VERIFICATION", 0), 0)
        self.assertGreater(categories.get("ACTIVE_MANUAL_OPERATION", 0), 0)
        self.assertGreaterEqual(categories.get("TEMPORARY", 0), 0)
        self.assertIn("TEMPORARY", self.policy["rules"])


if __name__ == "__main__":
    unittest.main()
