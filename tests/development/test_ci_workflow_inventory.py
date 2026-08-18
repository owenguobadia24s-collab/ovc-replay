from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/development/ci_workflow_inventory.py"
POLICY_DIR = ROOT / "registries/development"
CURRENT_VERSION = "0_9"
HISTORICAL_VERSIONS = ("0_8", "0_7", "0_6", "0_5", "0_4", "0_3", "0_2", "0_1")
EXPECTED_SNAPSHOTS = {
    "0_9": (191, 139, 52),
    "0_8": (191, 138, 53),
    "0_7": (191, 137, 54),
    "0_6": (191, 136, 55),
    "0_5": (191, 135, 56),
    "0_4": (191, 134, 57),
    "0_3": (191, 133, 58),
    "0_2": (177, 131, 46),
    "0_1": (175, 129, 46),
}
EXPECTED_SUPERSESSION_CHAIN = {
    "0_9": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.8",
    "0_8": "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.7",
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
    return json.loads((POLICY_DIR / f"OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v{version}.json").read_text())


class CiWorkflowInventoryGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(CURRENT_VERSION)
        self.historical = {v: load_policy(v) for v in HISTORICAL_VERSIONS}
        self.inventory = inventory_module.build_inventory(ROOT, self.policy)
        self.records = {row["path"]: row for row in self.inventory["records"]}

    def test_current_inventory_is_exhaustive_and_exact(self):
        inventory_module.validate_inventory(self.inventory, self.policy)
        expected = self.policy["snapshot"]["expected_repository_workflow_definition_count"]
        self.assertEqual(expected, 139)
        self.assertEqual(self.inventory["total_workflow_definitions"], expected)
        self.assertEqual(sum(self.inventory["category_counts"].values()), expected)

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
        self.assertEqual(self.policy["historical_policy_preserved"], "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_8.json")

    def test_exactly_two_approved_pull_request_listeners_remain(self):
        pr_paths = sorted(record["path"] for record in self.inventory["records"] if "pull_request" in record["triggers"])
        self.assertEqual(pr_paths, sorted(self.policy["approved_pull_request_workflows"]))
        self.assertEqual(self.inventory["category_counts"]["CURRENT_PR_CI"], 2)

    def test_sd_wp3_workflow_is_bounded_non_pr_synthetic_only(self):
        admission = self.policy["admitted_new_workflow"]
        path = ".github/workflows/c2p2-sd-wp3-qualification.yml"
        self.assertEqual(admission["path"], path)
        record = self.records[path]
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["push"])
        self.assertNotIn("pull_request", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        mode = admission["authority_mode"]
        for marker in (
            "SYNTHETIC_ONLY", "NO_REAL_SOURCE_READ", "NO_REAL_SOURCE_EXECUTION",
            "NO_SELECTION", "NO_ACTIVATION", "NO_VALIDATION", "NO_PUBLICATION",
            "NO_REQUIRED_CHECK_SUBSTITUTION",
        ):
            self.assertIn(marker, mode)

    def test_r5_and_preserved_diagnostic_workflows_remain_non_pr(self):
        admissions = {item["path"]: item for item in self.policy["additional_non_pr_diagnostic_workflows"]}
        required = {
            ".github/workflows/c2p2-rs0-real-source-shadow-run-r5.yml",
            ".github/workflows/c2p2-rs0-r4-capacity-recovery.yml",
            ".github/workflows/c2p2-rs0-current-source-materialisation.yml",
            ".github/workflows/vit-post-merge-completion.yml",
            ".github/workflows/ci-unittest-shard-shadow.yml",
            ".github/workflows/pyt-wp2-step5-unified.yml",
            ".github/workflows/grt2-g2-qualification.yml",
            ".github/workflows/grt2-g2-performance.yml",
            ".github/workflows/dsai3v-async-assurance-shadow.yml",
        }
        self.assertTrue(required.issubset(admissions))
        for path in required:
            self.assertIn(path, self.records)
            self.assertNotIn("pull_request", self.records[path]["triggers"])
        self.assertIn("PRESERVED_CONSUMED_R5_SINGLE_USE_REAL_SOURCE", admissions[".github/workflows/c2p2-rs0-real-source-shadow-run-r5.yml"]["authority_mode"])

    def test_classification_is_deterministic(self):
        self.assertEqual(self.inventory, inventory_module.build_inventory(ROOT, self.policy))

    def test_policy_prohibits_destructive_cleanup_and_required_check_mutation(self):
        governance = self.policy["governance"]
        self.assertTrue(governance["classification_only"])
        self.assertEqual(governance["workflow_deletion"], "PROHIBITED")
        self.assertEqual(governance["required_check_mutation"], "PROHIBITED_BY_THIS_PACKET")
        self.assertEqual(governance["historical_evidence_preservation"], "REQUIRED")


if __name__ == "__main__":
    unittest.main()
