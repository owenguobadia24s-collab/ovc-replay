from __future__ import annotations
import importlib.util,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
VALIDATOR=ROOT/"scripts/development/v0_2/validate_da2_g1.py"
spec=importlib.util.spec_from_file_location("validate_da2_g1",VALIDATOR); assert spec and spec.loader
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
class DA2G1OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((ROOT/"registries/development/v0_2/OVC_DA2_WORKFLOW_ADMISSION_MODES_v0_1.json").read_text()); self.cases=json.loads((ROOT/"fixtures/development/v0_2/da2_g1_path_admission_cases.json").read_text()); self.tests=(ROOT/".github/workflows/tests.yml").read_text(); self.tiered=(ROOT/".github/workflows/ovc-tiered-tests.yml").read_text()
    def test_validator_passes(self): self.assertEqual(module.main(),0)
    def test_exactly_two_pr_admitted_workflows(self): self.assertEqual(set(self.registry["modes"]["CANONICAL_PULL_REQUEST"]),{".github/workflows/tests.yml",".github/workflows/ovc-tiered-tests.yml"})
    def test_exactly_one_complete_suite_in_pr_workflows(self):
        command="python3 -m unittest discover -s tests -v"; self.assertEqual(self.tests.count(command),1); self.assertNotIn(command,self.tiered)
    def test_profiles_and_evaluator_are_present(self):
        for profile in ("FAST","PACKET","FINAL_HEAD"): self.assertIn(profile,self.tiered)
        self.assertIn("OVC merge readiness",self.tiered); self.assertIn("run.name === 'tests'",self.tiered)
    def test_runtime_and_concurrency_are_canonical(self):
        for text in (self.tests,self.tiered): self.assertIn('python-version: "3.11"',text); self.assertIn("cancel-in-progress: true",text)
    def test_path_cases_are_closed(self):
        ids={c["case_id"] for c in self.cases["cases"]}; self.assertEqual(ids,{"DEVELOPMENT_FAST","DEVELOPMENT_PACKET","WORKFLOW_FINAL","MTA_FINAL","UNKNOWN_FINAL"}); self.assertTrue(all(c["expected_profile"] in {"FAST","PACKET","FINAL_HEAD"} for c in self.cases["cases"]))
    def test_no_candidate_run_ids_in_decision_packet(self): self.assertNotIn('"run_id"',(ROOT/"docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_IMPLEMENTATION_PACKET.json").read_text())
    def test_ruleset_migration_is_fail_closed(self):
        packet=json.loads((ROOT/"docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_RULESET_MIGRATION_PACKET.json").read_text()); self.assertEqual(packet["target_required_contexts"],["OVC merge readiness"]); self.assertEqual(packet["accepted_source"],{"app_id":15368,"app_slug":"github-actions"}); self.assertEqual(packet["failure_result"],"BLOCK_PRESERVE_MIGRATION_AND_OLD_REQUIRED_CONTEXTS")
if __name__=="__main__": unittest.main()
