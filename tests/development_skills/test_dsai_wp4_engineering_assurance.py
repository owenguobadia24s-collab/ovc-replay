from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.head_churn import classify_main_head_movement
from ovc.development.skills import BaseFreshnessPolicy, audit_evidence, build_contract_proposal, build_skill_release_bundle, evaluate_gate, evaluate_qa, git_packet_dry_run, plan_tests, test_execution_plan as execute_test_plan
from ovc.development.skills.engineering import classify_head_churn

ROOT = Path(__file__).resolve().parents[2]
A = "a" * 40
B = "b" * 40


class DSAIWP4EngineeringAssuranceTests(unittest.TestCase):
    def test_e1_e3_candidates_non_trusted_contract_bound_and_releases_rebuild(self) -> None:
        registry = json.loads((ROOT / "registries/development/skills/first_generation_candidates_v0_1.json").read_text())
        self.assertEqual(len(registry["entries"]), 10)
        for row in registry["entries"]:
            self.assertEqual(row["maturity"], "EXPERIMENTAL")
            self.assertEqual(row["write_permission"], "DENY")
            self.assertEqual(row["authority_effect"], "NONE")
            self.assertTrue(row["input_contract_id"])
            self.assertTrue(row["output_contract_id"])
            fields = {key: row[key] for key in ("capability_ids","execution_mode","implementation_entrypoint","input_contract_id","output_contract_id","tool_profile_id","write_permission","authority_effect")}
            fields["failure_policy"] = "FAIL_CLOSED"
            rebuilt=build_skill_release_bundle(skill_id=row["skill_id"],logical_name=row["logical_name"],semantic_version=row["semantic_version"],fields=fields,field_classification={key:"NORMATIVE" for key in fields},source_refs=["OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED","OVC-DSAI-IMPLEMENTATION-PLAN-0.2"])
            self.assertEqual(rebuilt["release_id"], row["release_id"])
            self.assertNotEqual(row["maturity"], "TRUSTED")

    def test_constructive_output_cannot_embed_authority_decision(self) -> None:
        proposal = build_contract_proposal(logical_path="contracts/example.md", payload={"contract":"ok"})
        self.assertEqual(proposal["authority_effect"], "NONE")
        self.assertEqual(proposal["writes_performed"], [])
        with self.assertRaisesRegex(ValueError, "forbidden authority fields"):
            build_contract_proposal(logical_path="contracts/example.md", payload={"nested":{"authority_decision":"PASS"}})

    def test_golden_git_dry_run_blocks_merge_force_push_and_history_rewrite(self) -> None:
        fresh = BaseFreshnessPolicy().assess(baseline_main_sha=A,current_main_sha=A,commit_distance=0,elapsed_minutes=1,dependency_or_write_overlap=False,mutating=True,merge_candidate=False)
        good = git_packet_dry_run(actions=["CREATE_BRANCH","COMMIT","PUSH","OPEN_PR"],paths=["src/ovc/x.py"],freshness=fresh)
        self.assertEqual(good["status"], "PASS")
        self.assertEqual(good["writes_performed"], [])
        for action in ("MERGE","FORCE_PUSH","REWRITE_HISTORY"):
            blocked = git_packet_dry_run(actions=[action],paths=["src/ovc/x.py"],freshness=fresh)
            self.assertEqual(blocked["status"], "BLOCK")
            self.assertEqual(blocked["merge_capability"], "DISABLED_UNTRUSTED")

    def test_base_freshness_policy_head_churn_boundaries(self) -> None:
        policy = BaseFreshnessPolicy()
        within = policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=5,elapsed_minutes=29,dependency_or_write_overlap=False,mutating=False,merge_candidate=False)
        self.assertEqual(within["status"], "FRESH")
        cases = [
            policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=6,elapsed_minutes=1,dependency_or_write_overlap=False,mutating=False,merge_candidate=False),
            policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=1,elapsed_minutes=30,dependency_or_write_overlap=False,mutating=False,merge_candidate=False),
            policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=1,elapsed_minutes=1,dependency_or_write_overlap=True,mutating=False,merge_candidate=False),
            policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=1,elapsed_minutes=1,dependency_or_write_overlap=False,mutating=True,merge_candidate=False),
            policy.assess(baseline_main_sha=A,current_main_sha=B,commit_distance=1,elapsed_minutes=1,dependency_or_write_overlap=False,mutating=False,merge_candidate=True),
        ]
        self.assertTrue(all(row["status"] == "RE_PREFLIGHT_REQUIRED" for row in cases))
        with self.assertRaises(ValueError): BaseFreshnessPolicy(max_readonly_commit_distance=6)
        with self.assertRaises(ValueError): BaseFreshnessPolicy(max_readonly_elapsed_minutes=31)

    def test_shared_head_churn_wrapper_is_exact_equivalent(self) -> None:
        kwargs=dict(baseline_main_sha=A,current_main_sha=A,changed_main_paths=[],footprint=None)
        self.assertEqual(classify_head_churn(**kwargs), classify_main_head_movement(**kwargs))

    def test_test_planner_widens_uncertain_impact_and_executor_remains_local(self) -> None:
        plan = plan_tests(changed_paths=["src/ovc/x.py"],direct_tests=["test_x"],impact_known=False)
        self.assertTrue(plan["widened"])
        self.assertIn("REPOSITORY_WIDE_SUITE", plan["selected_tests"])
        execution = execute_test_plan(test_plan=plan)
        self.assertEqual(execution["execution_mode"], "LOCAL_TEST_ONLY")
        self.assertEqual(execution["writes_performed"], [])

    def test_qa_false_pass_and_false_block_are_fail_closed(self) -> None:
        self.assertEqual(evaluate_qa([{"status":"PASS"},{"status":"BLOCK"}])["acceptance_result"], "BLOCK")
        self.assertEqual(evaluate_qa([{"status":"PASS"}])["acceptance_result"], "PASS")
        self.assertEqual(evaluate_qa([])["acceptance_result"], "NOT_EVALUABLE")
        self.assertEqual(evaluate_qa([{"status":"PASS"}])["authority_result"], "NO_AUTHORITY_DECISION")

    def test_gate_title_does_not_override_authority_delta(self) -> None:
        reserved = evaluate_gate(gate_title="harmless documentation",acceptance_conditions=[True],qa_status="PASS",authority_delta="TRUSTED_PROMOTION")
        self.assertEqual(reserved["acceptance_result"], "PASS")
        self.assertEqual(reserved["authority_result"], "OPERATOR_REQUIRED")
        self.assertFalse(reserved["auto_ratifiable"])
        auto = evaluate_gate(gate_title="critical activation wording",acceptance_conditions=[True],qa_status="PASS",authority_delta="NONE")
        self.assertEqual(auto["authority_result"], "AUTO_EXECUTABLE")
        self.assertTrue(auto["auto_ratifiable"])
        self.assertFalse(auto["authority_granted"])

    def test_evidence_audit_blocks_stale_and_invalid_hash(self) -> None:
        self.assertEqual(audit_evidence([{"sha256":"a"*64,"stale":False}])["status"], "PASS")
        self.assertEqual(audit_evidence([{"sha256":"bad","stale":False}])["status"], "BLOCK")
        self.assertEqual(audit_evidence([{"sha256":"a"*64,"stale":True}])["status"], "BLOCK")

    def test_new_schemas_keep_closed_top_level_contract(self) -> None:
        for name in ("first_generation_candidate_registry_v0_1.schema.json","base_freshness_receipt_v0_1.schema.json","wp4_tool_profile_registry_v0_1.schema.json"):
            schema=json.loads((ROOT/"schemas/development/skills"/name).read_text())
            self.assertEqual(schema["$schema"],"https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["type"],"object")
            self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__": unittest.main()
