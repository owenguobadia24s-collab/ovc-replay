from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/development/ci_workflow_inventory.py"
POLICY_DIR = ROOT / "registries/development"
CURRENT_VERSION = "0_12"
HISTORICAL_VERSIONS = ("0_11", "0_10", "0_9", "0_8", "0_7", "0_6", "0_5", "0_4", "0_3", "0_2", "0_1")
EXPECTED_SNAPSHOTS = {
    "0_12": (191, 142, 49), "0_11": (191, 141, 50), "0_10": (191, 140, 51),
    "0_9": (191, 139, 52), "0_8": (191, 138, 53), "0_7": (191, 137, 54),
    "0_6": (191, 136, 55), "0_5": (191, 135, 56), "0_4": (191, 134, 57),
    "0_3": (191, 133, 58), "0_2": (177, 131, 46), "0_1": (175, 129, 46),
}
EXPECTED_SUPERSESSION_CHAIN = {
    "0_12":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.11", "0_11":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.10",
    "0_10":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.9", "0_9":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.8",
    "0_8":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.7", "0_7":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.6",
    "0_6":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.5", "0_5":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.4",
    "0_4":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.3", "0_3":"OVC.CIPR.WORKFLOW_GOVERNANCE.v0.2",
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
        self.assertEqual(self.inventory["total_workflow_definitions"], 142)
        self.assertEqual(sum(self.inventory["category_counts"].values()), 142)

    def test_current_and_historical_snapshot_chain_is_preserved(self):
        policies = {CURRENT_VERSION:self.policy, **self.historical}
        for version, expected in EXPECTED_SNAPSHOTS.items():
            snapshot = policies[version]["snapshot"]
            observed = (snapshot["github_actions_registered_total_count"], snapshot["expected_repository_workflow_definition_count"], snapshot["registration_count_excess"])
            self.assertEqual(observed, expected, version)
        for version, predecessor in EXPECTED_SUPERSESSION_CHAIN.items():
            self.assertEqual(policies[version]["supersedes_for_current_inventory"], predecessor)

    def test_exactly_two_approved_pull_request_listeners_remain(self):
        pr_paths = sorted(record["path"] for record in self.inventory["records"] if "pull_request" in record["triggers"])
        self.assertEqual(pr_paths, sorted(self.policy["approved_pull_request_workflows"]))
        self.assertEqual(self.inventory["category_counts"]["CURRENT_PR_CI"], 2)

    def test_wp6_after_gadj_is_push_only_post_freeze_and_fail_closed(self):
        admission = self.policy["admitted_new_workflow"]
        path = ".github/workflows/c2p2-sd-wp6-after-gadj.yml"
        self.assertEqual(admission["path"], path)
        record = self.records[path]
        self.assertEqual(record["triggers"], ["push"])
        self.assertNotIn("pull_request", record["triggers"])
        for marker in ("FROZEN_HUMAN_LABELS_ONLY", "POST_FREEZE_UNBLIND", "NO_SELECTION", "NO_ACTIVATION", "NO_VALIDATION", "NO_PUBLICATION", "NO_EC1_CANDIDATE_USE"):
            self.assertIn(marker, admission["authority_mode"])

    def test_prior_greal_sd_and_r5_workflows_are_preserved_non_pr(self):
        admissions = {row["path"]:row for row in self.policy["additional_non_pr_diagnostic_workflows"]}
        for path in (
            ".github/workflows/c2p2-sd-greal.yml",
            ".github/workflows/c2p2-sd-wp3-qualification-r2.yml",
            ".github/workflows/c2p2-sd-wp3-qualification.yml",
            ".github/workflows/c2p2-rs0-real-source-shadow-run-r5.yml",
        ):
            self.assertIn(path, admissions)
            self.assertIn(path, self.records)
            self.assertNotIn("pull_request", self.records[path]["triggers"])

    def test_classification_is_deterministic(self):
        self.assertEqual(self.inventory, inventory_module.build_inventory(ROOT, self.policy))

if __name__ == "__main__":
    unittest.main()
