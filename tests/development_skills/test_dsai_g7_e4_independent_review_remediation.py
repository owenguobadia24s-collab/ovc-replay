from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import unittest

from ovc.development.skills import (
    BaseFreshnessPolicy,
    audit_evidence,
    build_tool_request,
    decide_tool_request,
    resolve_security_envelope,
    sandbox_leakage_probe,
    shadow_authority_resolver,
    shadow_preflight,
    shadow_prerequisite_resolver,
    shadow_scope_guard,
)
from ovc.development.skills.assurance import evaluate_qa, plan_tests
from ovc.development.skills.engineering import default_freshness_policy, git_packet_dry_run
from ovc.development.skills.qualification_closure import (
    evaluate_cache_reuse,
    evaluate_dependency_freeze,
    evaluate_evidence_completeness,
    evaluate_governing_state,
    evaluate_population_freeze,
    evaluate_scientific_non_coercion,
    evaluate_skill_resolution_freeze,
    evaluate_test_preservation,
)
from ovc.development.skills.e4_remediation import (
    evaluate_branch_update_guard,
    evaluate_dependency_freeze_refined,
    evaluate_e4_applicability_matrix,
    evaluate_skill_resolution_set,
)


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "fixtures/development_skills/g7_adversarial_suite_v0_1.json"
EXTENSION = ROOT / "fixtures/development_skills/g7_adversarial_extension_v0_2.json"
REMEDIATION = ROOT / "fixtures/development_skills/g7_e4_independent_review_remediation_v0_1.json"
APPLICABILITY = ROOT / "fixtures/development_skills/g7_e4_skill_family_applicability_v0_1.json"


def _run_case(case: dict) -> tuple[str, list[str]]:
    driver = case["driver"]
    value = case["input"]

    if driver == "authority_resolver":
        row = shadow_authority_resolver(**value)
        return row["disposition"], row["reason_codes"]

    if driver == "scope_guard":
        try:
            row = shadow_scope_guard(**value)
        except (ValueError, OSError):
            return "ERROR_FAIL_CLOSED", []
        return row["disposition"], row["reason_codes"]

    if driver == "prerequisite_resolver":
        row = shadow_prerequisite_resolver(**value)
        return row["disposition"], row["reason_codes"]

    if driver == "preflight":
        row = shadow_preflight(value)
        return row["disposition"], row["reason_codes"]

    if driver == "freshness":
        row = BaseFreshnessPolicy().assess(**value)
        return ("PASS" if row["status"] == "FRESH" else "BLOCK"), row["reason_codes"]

    if driver == "evidence_audit":
        row = audit_evidence(value["records"])
        return row["status"], row["reason_codes"]

    if driver == "security":
        env_args = {
            "skill_id": "OVC-SKILL-G7-E4-REMEDIATION",
            "capability_ids": ["G7_E4_REMEDIATION"],
            "allowed_semantic_actions": value["envelope"].get("allowed_semantic_actions", []),
            "read_prefixes": value["envelope"].get("read_prefixes", []),
            "write_prefixes": value["envelope"].get("write_prefixes", []),
            "semantic_owners": value["envelope"].get("semantic_owners", []),
            "logical_credential_ids": value["envelope"].get("logical_credential_ids", []),
            "network_allowlist": value["envelope"].get("network_allowlist", []),
            "write_authority_active": value["envelope"].get("write_authority_active", False),
            "validation_authority_active": value["envelope"].get("validation_authority_active", False),
        }
        envelope = resolve_security_envelope(**env_args)
        request = build_tool_request(**value["request"])
        row = decide_tool_request(envelope, request)
        return ("PASS" if row["decision"] == "ALLOW" else "BLOCK"), row["reason_codes"]

    if driver == "sandbox":
        row = sandbox_leakage_probe(**value)
        return row["status"], []

    if driver == "test_preservation":
        row = evaluate_test_preservation(**value)
        return row["status"], row["reason_codes"]

    if driver == "qa":
        row = evaluate_qa(value["assertions"])
        return row["acceptance_result"], row.get("reason_codes", [])

    if driver == "test_planner":
        row = plan_tests(**value)
        if case.get("expect_contains_test"):
            assert case["expect_contains_test"] in row["selected_tests"]
        return "PASS", []

    if driver == "evidence_completeness":
        row = evaluate_evidence_completeness(**value)
        return row["status"], row["reason_codes"]

    if driver == "security_request":
        envelope = resolve_security_envelope(**value["envelope"])
        request = build_tool_request(**value["request"])
        row = decide_tool_request(envelope, request)
        return ("PASS" if row["decision"] == "ALLOW" else "BLOCK"), row["reason_codes"]

    if driver == "raw_tool_request":
        try:
            build_tool_request(**value)
        except ValueError:
            return "ERROR_FAIL_CLOSED", []
        return "PASS", []

    if driver == "raw_credential_handle":
        from ovc.development.skills.security import issue_credential_handle
        try:
            issue_credential_handle(**value)
        except ValueError:
            return "ERROR_FAIL_CLOSED", []
        return "PASS", []

    if driver == "redaction":
        from ovc.development.skills.security import redact_sensitive
        row = redact_sensitive(value["value"])
        for dotted in case["expected_redacted"]:
            cursor = row
            for part in dotted.split("."):
                cursor = cursor[part]
            assert cursor == "[REDACTED]"
        return "PASS", []

    if driver == "git_dry_run":
        freshness = default_freshness_policy().assess(
            baseline_main_sha="a" * 40,
            current_main_sha="a" * 40,
            commit_distance=0,
            elapsed_minutes=0,
            dependency_or_write_overlap=False,
            mutating=False,
            merge_candidate=False,
        )
        row = git_packet_dry_run(actions=value["actions"], paths=value["paths"], freshness=freshness)
        return row["status"], row.get("reason_codes", [])

    if driver == "population_freeze":
        row = evaluate_population_freeze(**value)
        return row["status"], row["reason_codes"]

    if driver == "dependency_freeze":
        row = evaluate_dependency_freeze(**value)
        return row["status"], row["reason_codes"]

    if driver == "dependency_freeze_refined":
        row = evaluate_dependency_freeze_refined(**value)
        return row["status"], row["reason_codes"]

    if driver == "cache_reuse":
        row = evaluate_cache_reuse(**value)
        return row["status"], row["reason_codes"]

    if driver == "skill_resolution":
        row = evaluate_skill_resolution_freeze(**value)
        return row["status"], row["reason_codes"]

    if driver == "skill_resolution_set":
        row = evaluate_skill_resolution_set(**value)
        return row["status"], row["reason_codes"]

    if driver == "governing_state":
        row = evaluate_governing_state(value["records"])
        return row["status"], row["reason_codes"]

    if driver == "non_coercion":
        row = evaluate_scientific_non_coercion(**value)
        return row["status"], row["reason_codes"]

    if driver == "branch_update_guard":
        row = evaluate_branch_update_guard(**value)
        return row["status"], row["reason_codes"]

    raise AssertionError(f"unsupported driver {driver}")


class DSAIG7E4IndependentReviewRemediationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = json.loads(BASE.read_text(encoding="utf-8"))
        cls.extension = json.loads(EXTENSION.read_text(encoding="utf-8"))
        cls.remediation = json.loads(REMEDIATION.read_text(encoding="utf-8"))
        cls.applicability = json.loads(APPLICABILITY.read_text(encoding="utf-8"))
        superseded = set(cls.remediation["superseded_case_ids"])
        cls.effective_cases = [
            row for row in [*cls.base["cases"], *cls.extension["cases"]]
            if row["case_id"] not in superseded
        ] + cls.remediation["replacement_cases"] + cls.remediation["added_cases"]

    def test_effective_corpus_is_111_cases_across_18_families(self):
        self.assertEqual(len(self.effective_cases), 111)
        counts = Counter(row["family"] for row in self.effective_cases)
        self.assertEqual(len(counts), 18)
        self.assertEqual(counts["TEST_WEAKENING"], 7)
        self.assertEqual(counts["SCIENTIFIC_NON_COERCION"], 8)
        for family, count in counts.items():
            if family not in {"TEST_WEAKENING", "SCIENTIFIC_NON_COERCION"}:
                self.assertEqual(count, 6, family)

    def test_all_111_effective_cases_execute_with_zero_known_mismatch(self):
        for case in self.effective_cases:
            with self.subTest(case_id=case["case_id"], family=case["family"]):
                observed, reasons = _run_case(case)
                self.assertEqual(observed, case["expected"], case)
                if case.get("expected_reason"):
                    self.assertIn(case["expected_reason"], reasons, case)
                for reason in case.get("expected_additional_reasons", []):
                    self.assertIn(reason, reasons, case)

    def test_skill_resolution_ordering_is_explicitly_set_membership(self):
        replacement = next(row for row in self.remediation["replacement_cases"] if row["case_id"] == "G7X.SKI.003.R1")
        observed, reasons = _run_case(replacement)
        self.assertEqual(observed, "PASS")
        self.assertEqual(reasons, [])

    def test_dependency_version_drift_preserves_exact_identity_reasons(self):
        replacement = next(row for row in self.remediation["replacement_cases"] if row["case_id"] == "G7X.DEP.005.R1")
        observed, reasons = _run_case(replacement)
        self.assertEqual(observed, "BLOCK")
        self.assertIn("DEPENDENCY_VERSION_DRIFT", reasons)
        self.assertIn("UNDECLARED_DEPENDENCY_INJECTION", reasons)
        self.assertIn("DECLARED_DEPENDENCY_MISSING", reasons)

    def test_branch_churn_replacements_are_branch_specific_not_freshness_duplicates(self):
        replacements = {
            row["case_id"]: row for row in self.remediation["replacement_cases"]
            if row["family"] == "BRANCH_CHURN"
        }
        self.assertEqual(replacements["G7X.BRA.005.R1"]["driver"], "branch_update_guard")
        self.assertEqual(replacements["G7X.BRA.006.R1"]["driver"], "branch_update_guard")
        self.assertEqual(_run_case(replacements["G7X.BRA.005.R1"])[0], "PASS")
        self.assertEqual(_run_case(replacements["G7X.BRA.006.R1"])[0], "BLOCK")

    def test_applicability_matrix_has_explicit_14_by_18_traceability(self):
        row = evaluate_e4_applicability_matrix(self.applicability)
        self.assertEqual(row["status"], "PASS", row)
        self.assertEqual(row["family_count"], 18)
        self.assertEqual(row["exact_skill_count"], 14)
        self.assertEqual(row["binding_count"], 252)

    def test_review_record_corrections_and_authority_boundary_are_explicit(self):
        corrections = {row["review_item"]: row for row in self.remediation["review_corrections"]}
        self.assertIn("SCOPE_AMBIGUOUS_FAIL_CLOSED", corrections["G7.SE.004"]["corrected_statement"])
        self.assertIn("104 accepted + 4 amended", corrections["signoff_arithmetic"]["corrected_statement"])
        self.assertEqual(self.remediation["authority_effect"], "NONE")
        self.assertEqual(self.remediation["trusted_promotion_effect"], "NONE")
        self.assertEqual(
            self.remediation["qualification_effect"],
            "NONE_UNTIL_FINAL_INDEPENDENT_E4_REVIEW_ACCEPTED",
        )


if __name__ == "__main__":
    unittest.main()
