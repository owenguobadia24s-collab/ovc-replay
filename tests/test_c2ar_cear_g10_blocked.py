from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10"
AUDIT = BASE / "C2AR_WP10_INPUT_AVAILABILITY_AUDIT.json"
SYNTHETIC = BASE / "C2AR_WP10_SYNTHETIC_PREPARATION_EVIDENCE.json"
QA = BASE / "CEAR_G10_BLOCKED_QA_PACKET.json"
PACKET = BASE / "CEAR_G10_BLOCKED_PACKET.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G10_BLOCKED_STATE_v0_3.jsonc"
LEGACY_MANIFEST = ROOT / "docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/output-manifest.json"
METHOD = ROOT / "registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG10BlockedTests(unittest.TestCase):
    def test_input_audit_proves_legacy_manifest_is_not_vnext_substitute(self) -> None:
        audit = load(AUDIT)
        manifest = load(LEGACY_MANIFEST)
        legacy = audit["legacy_full_month_manifest"]
        self.assertEqual("BLOCKED_REQUIRED_INPUT_UNAVAILABLE_OR_NON_REPRODUCIBLE", audit["audit_status"])
        self.assertEqual("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1", legacy["active_c2_model_release_id"])
        self.assertEqual(manifest["active_c2_model_release_id"], legacy["active_c2_model_release_id"])
        self.assertEqual(manifest["code_commit"], legacy["code_commit"])
        self.assertEqual(manifest["file_count"], legacy["file_count"])
        self.assertEqual(manifest["deterministic_payload_hash"], legacy["deterministic_payload_hash"])
        self.assertEqual(manifest["output_manifest_sha256"], legacy["output_manifest_sha256"])
        self.assertEqual("MANIFEST_ONLY_PAYLOAD_BYTES_NOT_PRESENT", legacy["payload_availability_in_repository_connector"])
        self.assertEqual("NOT_ACCEPTABLE_SUBSTITUTE", legacy["sufficiency_for_wp10"])
        self.assertTrue(all(item["blocking"] for item in audit["non_substitution_findings"]))
        self.assertIn("C2_VNEXT_FULL_POPULATION_REPLAY_MANIFEST", audit["missing_required_artifacts"])
        self.assertIn("FIRST_CLEAN_RUN_LOGICAL_HASH", audit["missing_required_artifacts"])
        self.assertIn("SECOND_CLEAN_RUN_LOGICAL_HASH", audit["missing_required_artifacts"])
        self.assertIn("DETERMINISM_COMPARISON_RECEIPT", audit["missing_required_artifacts"])
        self.assertEqual("BLOCKED", audit["acceptance_condition_effect"]["condition_70_complete_population_method_and_denominator_reconciliation"])
        self.assertEqual("PASS", audit["acceptance_condition_effect"]["condition_73_authority_and_era_separation"])
        self.assertEqual("NONE", audit["active_authority_effect"])

    def test_synthetic_preparation_passes_but_is_not_disposition_eligible(self) -> None:
        evidence = load(SYNTHETIC)
        self.assertEqual("PREPARATION_IMPLEMENTED_SYNTHETIC_ONLY_NOT_DISPOSITION_ELIGIBLE", evidence["status"])
        fixture = evidence["synthetic_fixture_results"]
        self.assertEqual(14, fixture["requested_opportunities"])
        self.assertEqual(8, fixture["outcomes"]["COMPUTABLE"])
        self.assertEqual(8, fixture["fingerprints"])
        self.assertEqual(2, fixture["retained_motifs"])
        self.assertEqual(4, fixture["insufficient_support_negative_candidates"])
        self.assertEqual(2, fixture["provisional_families"])
        self.assertEqual(2, fixture["functional_cores"])
        self.assertEqual(2, fixture["declarative_rule_candidates"])
        self.assertEqual(4, fixture["matched_controls"])
        self.assertEqual(0, fixture["legacy_seed_count"])
        self.assertEqual(0, fixture["outcome_dependency_count"])
        self.assertFalse(fixture["market_population"])
        self.assertFalse(fixture["cear_g10_disposition_eligible"])
        self.assertEqual("PASS", evidence["acceptance_scope"]["contract_and_code_preparation"])
        self.assertEqual("BLOCKED", evidence["acceptance_scope"]["complete_real_vnext_opportunity_population"])
        self.assertEqual("NOT_READY", evidence["acceptance_scope"]["cear_g10_operator_dispositions"])
        self.assertEqual("NONE", evidence["authority"]["functional_candidate_pass"])
        self.assertEqual("NONE", evidence["authority"]["rule_candidate_pass"])
        self.assertEqual("UNCHANGED_READ_ONLY", evidence["authority"]["active_c2"])

    def test_qa_recommends_block_with_exact_acceptance_results(self) -> None:
        qa = load(QA)
        self.assertEqual("BLOCK", qa["qa_recommendation"])
        findings = {item["id"]: item["result"] for item in qa["findings"]}
        self.assertEqual("PASS", findings["G10-QA-01"])
        self.assertEqual("PASS", findings["G10-QA-06"])
        self.assertEqual("BLOCK", findings["G10-QA-07"])
        self.assertEqual("BLOCK", findings["G10-QA-10"])
        conditions = {item["condition_id"]: item["result"] for item in qa["acceptance_conditions"]}
        self.assertEqual("BLOCKED_REQUIRED_VNEXT_POPULATION_UNAVAILABLE", conditions["CEAR-G10-A70"])
        self.assertEqual("NOT_EVALUABLE", conditions["CEAR-G10-A71"])
        self.assertEqual("NOT_EVALUABLE", conditions["CEAR-G10-A72"])
        self.assertEqual("PASS", conditions["CEAR-G10-A73"])
        self.assertGreater(len(qa["blocking_warnings"]), 0)
        self.assertEqual(1, len(qa["unresolved_issues"]))
        self.assertTrue(qa["unresolved_issues"][0]["blocking"])
        self.assertEqual("NONE", qa["active_authority_delta"])
        self.assertEqual("NOT_EVALUABLE_FOR_REAL_POPULATION", qa["capacity"]["capacity_status"])

    def test_gate_packet_is_complete_blocked_and_prohibits_merge_and_wp11(self) -> None:
        packet = load(PACKET)
        self.assertEqual("CEAR-G10", packet["gate_id"])
        self.assertEqual("BLOCKED_BEFORE_DISPOSITION", packet["gate_status"])
        self.assertEqual(["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"], packet["allowed_decisions"])
        self.assertEqual("BLOCK", packet["recommended_decision"])
        self.assertEqual("NOT_EVALUABLE_UNTIL_COMPLETE_REVISED_VNEXT_POPULATION_EXISTS", packet["proposed_authority_delta"])
        self.assertEqual("CEAR-G10-BLOCKER-001", packet["blocker"]["blocker_id"])
        self.assertFalse(packet["blocker"]["correctable_inside_current_repository_branch"])
        self.assertIn("SUPPLY_OR_PRODUCE_ONE_CONTENT_ADDRESSED_COMPLETE_C2_VNEXT_SHADOW_FROZEN_REPLAY", packet["blocker"]["smallest_lawful_resolution"])
        acceptance = {item["condition_id"]: item["result"] for item in packet["acceptance_conditions"]}
        self.assertEqual("BLOCKED", acceptance["CEAR-G10-A70"])
        self.assertEqual("NOT_EVALUABLE", acceptance["CEAR-G10-A71"])
        self.assertEqual("NOT_EVALUABLE", acceptance["CEAR-G10-A72"])
        self.assertEqual("PASS", acceptance["CEAR-G10-A73"])
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", packet["current_authority"]["c2_vnext"])
        self.assertEqual("CANDIDATE_NOT_ADMITTED", packet["current_authority"]["discovery_method"])
        self.assertEqual("NONE", packet["current_authority"]["research_consumer_permission"])
        self.assertEqual("UNCHANGED_READ_ONLY", packet["current_authority"]["active_c2"])
        self.assertEqual("OVC CONTINUE", packet["exact_resume_command_after_resolution"])
        self.assertIn("DO_NOT_MERGE_PR_319", packet["stop_boundary"])
        self.assertIn("DO_NOT_BEGIN_WP11", packet["stop_boundary"])

    def test_state_is_blocked_without_operator_disposition_surface(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("BLOCKED", state["status"])
        self.assertEqual("C2AR-WP10", state["current_packet"])
        self.assertEqual("CEAR-G10", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("NOT_READY_REQUIRED_ARTIFACT_BLOCKER", state["decision_readiness"])
        self.assertEqual("BLOCK", state["recommended_disposition"])
        self.assertEqual("CEAR-G10-BLOCKER-001", state["blocker_id"])
        self.assertEqual("BLOCKED", state["completed_preparation"]["real_vnext_population_execution"])
        self.assertIn("C2_VNEXT_FULL_POPULATION_REPLAY_MANIFEST", state["missing_required_artifacts"])
        self.assertEqual("PROHIBITED", state["available_but_insufficient_evidence"]["substitution"])
        authority = state["authority"]
        self.assertEqual("CANDIDATE_NOT_ADMITTED", authority["discovery_method"])
        self.assertEqual("NONE", authority["real_functional_candidates"])
        self.assertEqual("NONE", authority["real_rule_candidates"])
        self.assertEqual("NONE", authority["research_consumer_permission"])
        self.assertEqual("NONE", authority["selector_event_episode_semantic_outcome"])
        self.assertEqual("UNCHANGED_READ_ONLY", authority["active_c2"])
        self.assertEqual("PROHIBITED_WHILE_BLOCKED", state["merge_status"])
        self.assertEqual("LOCKED", state["wp11_status"])
        self.assertEqual("OVC CONTINUE", state["exact_resume_command"])
        self.assertEqual(["CEAR-G10-BLOCKER-001"], state["blockers"])

    def test_method_candidate_remains_non_effective_and_operator_reserved(self) -> None:
        method = load(METHOD)
        self.assertEqual("CANDIDATE_METHOD_NOT_ADMITTED_PENDING_CEAR_G10", method["status"])
        self.assertFalse(method["effective"])
        self.assertFalse(method["active"])
        self.assertFalse(method["canonical"])
        self.assertTrue(method["real_population_requirement"]["required_for_cear_g10"])
        self.assertFalse(method["real_population_requirement"]["legacy_active_c2_substitution"])
        self.assertFalse(method["real_population_requirement"]["manifest_without_payload_substitution"])
        self.assertFalse(method["real_population_requirement"]["synthetic_substitution"])
        self.assertFalse(method["real_population_requirement"]["sampled_substitution"])
        self.assertEqual("PROHIBITED", method["legacy_isolation"]["seed"])
        self.assertEqual("PROHIBITED", method["outcome_isolation"]["validation_dependencies"])
        denied = set(method["explicitly_not_granted"])
        self.assertIn("DISCOVERY_METHOD_FREEZE", denied)
        self.assertIn("FUNCTIONAL_CANDIDATE_PASS", denied)
        self.assertIn("RULE_CANDIDATE_PASS", denied)
        self.assertIn("RESEARCH_CONSUMER_PERMISSION", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", denied)


if __name__ == "__main__":
    unittest.main()
