from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_7.json"
V06_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_6.json"
V05_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_5.json"
HISTORICAL_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_4.json"
V03_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_3.json"
OLDER_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_2.json"
WP3_POLICY_PATH = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_1.json"
SCRIPT_PATH = ROOT / "scripts/development/ci_workflow_inventory.py"

spec = importlib.util.spec_from_file_location("ci_workflow_inventory", SCRIPT_PATH)
assert spec and spec.loader
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)


class CiWorkflowInventoryGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.v06_policy = json.loads(V06_POLICY_PATH.read_text(encoding="utf-8"))
        self.v05_policy = json.loads(V05_POLICY_PATH.read_text(encoding="utf-8"))
        self.historical_policy = json.loads(HISTORICAL_POLICY_PATH.read_text(encoding="utf-8"))
        self.v03_policy = json.loads(V03_POLICY_PATH.read_text(encoding="utf-8"))
        self.older_policy = json.loads(OLDER_POLICY_PATH.read_text(encoding="utf-8"))
        self.wp3_policy = json.loads(WP3_POLICY_PATH.read_text(encoding="utf-8"))
        self.inventory = inventory_module.build_inventory(ROOT, self.policy)

    def test_inventory_matches_repository_count_and_is_exhaustive(self):
        inventory_module.validate_inventory(self.inventory, self.policy)
        expected = self.policy["snapshot"]["expected_repository_workflow_definition_count"]
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

    def test_actions_registry_and_repository_definition_layers_are_distinct(self):
        snapshot = self.policy["snapshot"]
        self.assertEqual(snapshot["github_actions_registered_total_count"], 191)
        self.assertEqual(snapshot["expected_repository_workflow_definition_count"], 137)
        self.assertEqual(snapshot["registration_count_excess"], 54)
        self.assertEqual(
            snapshot["registration_count_excess_interpretation"],
            "DRIFT_INDICATOR_REQUIRES_PATH_CROSSWALK_NOT_AUTHORITY",
        )
        self.assertIn("NOT_REMEASURED", snapshot["github_actions_source"])

    def test_v0_6_snapshot_remains_historical_and_unchanged(self):
        historical = self.v06_policy["snapshot"]
        self.assertEqual(self.v06_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.6")
        self.assertEqual(historical["github_actions_registered_total_count"], 191)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 136)
        self.assertEqual(historical["registration_count_excess"], 55)
        self.assertEqual(self.policy["supersedes_for_current_inventory"], self.v06_policy["policy_id"])

    def test_v0_5_snapshot_remains_historical_and_unchanged(self):
        historical = self.v05_policy["snapshot"]
        self.assertEqual(self.v05_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.5")
        self.assertEqual(historical["github_actions_registered_total_count"], 191)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 135)
        self.assertEqual(historical["registration_count_excess"], 56)
        self.assertEqual(self.v06_policy["supersedes_for_current_inventory"], self.v05_policy["policy_id"])

    def test_v0_4_snapshot_remains_historical_and_unchanged(self):
        historical = self.historical_policy["snapshot"]
        self.assertEqual(self.historical_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.4")
        self.assertEqual(historical["github_actions_registered_total_count"], 191)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 134)
        self.assertEqual(historical["registration_count_excess"], 57)
        self.assertEqual(self.v05_policy["supersedes_for_current_inventory"], self.historical_policy["policy_id"])

    def test_v0_3_snapshot_remains_historical_and_unchanged(self):
        historical = self.v03_policy["snapshot"]
        self.assertEqual(self.v03_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.3")
        self.assertEqual(historical["github_actions_registered_total_count"], 191)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 133)
        self.assertEqual(historical["registration_count_excess"], 58)
        self.assertEqual(self.historical_policy["supersedes_for_current_inventory"], self.v03_policy["policy_id"])

    def test_v0_2_snapshot_remains_historical_and_unchanged(self):
        historical = self.older_policy["snapshot"]
        self.assertEqual(self.older_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.2")
        self.assertEqual(historical["github_actions_registered_total_count"], 177)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 131)
        self.assertEqual(historical["registration_count_excess"], 46)
        self.assertEqual(
            self.v03_policy["supersedes_for_current_inventory"],
            self.older_policy["policy_id"],
        )

    def test_wp3_v0_1_snapshot_remains_historical_and_unchanged(self):
        historical = self.wp3_policy["snapshot"]
        self.assertEqual(self.wp3_policy["policy_id"], "OVC.CIPR.WORKFLOW_GOVERNANCE.v0.1")
        self.assertEqual(historical["github_actions_registered_total_count"], 175)
        self.assertEqual(historical["expected_repository_workflow_definition_count"], 129)
        self.assertEqual(historical["registration_count_excess"], 46)

    def test_exactly_two_approved_pull_request_listeners_remain(self):
        pr_paths = sorted(
            record["path"]
            for record in self.inventory["records"]
            if "pull_request" in record["triggers"]
        )
        self.assertEqual(pr_paths, sorted(self.policy["approved_pull_request_workflows"]))
        self.assertEqual(self.inventory["category_counts"]["CURRENT_PR_CI"], 2)

    def test_post_pyt_pytest_shard_shadow_is_new_non_pr_admission(self):
        admission = self.policy["admitted_new_workflow"]
        self.assertEqual(admission["path"], ".github/workflows/ci-pytest-shard-shadow.yml")
        record = next(
            record for record in self.inventory["records"] if record["path"] == admission["path"]
        )
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["push", "workflow_dispatch"])
        self.assertNotIn("pull_request", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        self.assertIn("SHADOW_ONLY", admission["authority_mode"])
        self.assertIn("NO_REQUIRED_CHECK_SUBSTITUTION", admission["authority_mode"])
        self.assertIn("NO_RUNNER_CUTOVER", admission["authority_mode"])

    def test_c2p2_rs0_source_materialisation_is_preserved_non_pr_and_authority_bounded(self):
        historical_admission = self.v06_policy["admitted_new_workflow"]
        admission = next(
            item for item in self.policy["additional_non_pr_diagnostic_workflows"]
            if item["path"] == historical_admission["path"]
        )
        self.assertEqual(admission["path"], ".github/workflows/c2p2-rs0-current-source-materialisation.yml")
        self.assertEqual(admission["authority_mode"], historical_admission["authority_mode"])
        record = next(
            record for record in self.inventory["records"] if record["path"] == admission["path"]
        )
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["push"])
        self.assertNotIn("pull_request", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        self.assertIn("BOUNDED_READ_ONLY_CURRENT_SOURCE_MATERIALISATION", admission["authority_mode"])
        self.assertIn("NO_REQUIRED_CHECK_SUBSTITUTION", admission["authority_mode"])
        self.assertIn("NO_GRUN_CONSUMPTION", admission["authority_mode"])

    def test_local_post_merge_completion_is_preserved_as_non_pr_and_authority_neutral(self):
        admission = next(
            item for item in self.policy["additional_non_pr_diagnostic_workflows"]
            if item["path"] == ".github/workflows/vit-post-merge-completion.yml"
        )
        historical_admission = next(
            item for item in self.v06_policy["additional_non_pr_diagnostic_workflows"]
            if item["path"] == admission["path"]
        )
        self.assertEqual(admission["authority_mode"], historical_admission["authority_mode"])
        record = next(
            record for record in self.inventory["records"] if record["path"] == admission["path"]
        )
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertNotIn("pull_request", record["triggers"])
        self.assertIn("push", record["triggers"])
        self.assertIn("workflow_dispatch", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        self.assertIn("POST_WRITE_COMPLETION_OBSERVABILITY_ONLY", admission["authority_mode"])
        self.assertIn("NO_MERGE_AUTHORITY", admission["authority_mode"])

    def test_prior_g4_shadow_workflow_remains_classified_non_pr(self):
        path = ".github/workflows/ci-unittest-shard-shadow.yml"
        admission = next(
            item for item in self.policy["additional_non_pr_diagnostic_workflows"] if item["path"] == path
        )
        record = next(record for record in self.inventory["records"] if record["path"] == path)
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertNotIn("pull_request", record["triggers"])
        self.assertFalse(admission["pull_request_listener"])
        self.assertEqual(admission["authority_mode"], "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION")

    def test_async_assurance_shadow_is_non_pr_read_only_and_non_substituting(self):
        path = ".github/workflows/dsai3v-async-assurance-shadow.yml"
        admission = next(
            item for item in self.policy["additional_non_pr_diagnostic_workflows"] if item["path"] == path
        )
        record = next(record for record in self.inventory["records"] if record["path"] == path)
        self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
        self.assertEqual(record["triggers"], ["workflow_dispatch"])
        self.assertFalse(admission["pull_request_listener"])
        self.assertIn("SHADOW_ONLY", admission["authority_mode"])
        self.assertIn("NO_REQUIRED_CHECK_SUBSTITUTION", admission["authority_mode"])
        self.assertIn("NO_WRITE", admission["authority_mode"])

    def test_grt_g2_evidence_workflows_are_non_pr_and_non_substituting(self):
        admissions = {
            item["path"]: item
            for item in self.policy["additional_non_pr_diagnostic_workflows"]
            if item["path"].startswith(".github/workflows/grt2-g2-")
        }
        self.assertEqual(
            set(admissions),
            {
                ".github/workflows/grt2-g2-qualification.yml",
                ".github/workflows/grt2-g2-performance.yml",
            },
        )
        for path, admission in admissions.items():
            record = next(record for record in self.inventory["records"] if record["path"] == path)
            self.assertEqual(record["category"], "ACTIVE_MANUAL_OPERATION")
            self.assertEqual(record["triggers"], ["workflow_dispatch"])
            self.assertFalse(admission["pull_request_listener"])
            self.assertIn("NO_REQUIRED_CHECK_SUBSTITUTION", admission["authority_mode"])

    def test_classification_is_deterministic(self):
        second = inventory_module.build_inventory(ROOT, self.policy)
        self.assertEqual(self.inventory, second)

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

    def test_repository_categories_are_observable_without_requiring_temp_presence(self):
        categories = self.inventory["category_counts"]
        self.assertGreater(categories.get("HISTORICAL_MANUAL_VERIFICATION", 0), 0)
        self.assertGreater(categories.get("ACTIVE_MANUAL_OPERATION", 0), 0)
        self.assertGreaterEqual(categories.get("TEMPORARY", 0), 0)
        self.assertIn("TEMPORARY", self.policy["rules"])


if __name__ == "__main__":
    unittest.main()
