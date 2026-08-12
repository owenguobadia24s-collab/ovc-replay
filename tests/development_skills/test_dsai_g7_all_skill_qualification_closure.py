from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills.assurance import audit_evidence, evaluate_qa, plan_tests
from ovc.development.skills.engineering import default_freshness_policy, git_packet_dry_run
from ovc.development.skills.qualification_closure import (
    FULL_ADVERSARIAL_CATALOGUE,
    evaluate_all_skill_coverage,
    evaluate_cache_reuse,
    evaluate_dependency_freeze,
    evaluate_evidence_completeness,
    evaluate_governing_state,
    evaluate_population_freeze,
    evaluate_scientific_non_coercion,
    evaluate_skill_resolution_freeze,
    evaluate_test_preservation,
)
from ovc.development.skills.security import (
    build_tool_request,
    decide_tool_request,
    issue_credential_handle,
    redact_sensitive,
    resolve_security_envelope,
)


ROOT = Path(__file__).resolve().parents[2]


class DSAIG7AllSkillQualificationClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extension = json.loads(
            (ROOT / "fixtures/development_skills/g7_adversarial_extension_v0_2.json").read_text(encoding="utf-8")
        )
        self.coverage = json.loads(
            (ROOT / "fixtures/development_skills/g7_all_skill_adversarial_coverage_v0_1.json").read_text(encoding="utf-8")
        )
        self.base = json.loads(
            (ROOT / "fixtures/development_skills/g7_adversarial_suite_v0_1.json").read_text(encoding="utf-8")
        )

    def _run_case(self, case):
        driver = case["driver"]
        value = case["input"]
        try:
            if driver == "test_preservation":
                out = evaluate_test_preservation(**value)
                actual = out["status"]
            elif driver == "qa":
                out = evaluate_qa(value["assertions"])
                actual = out["acceptance_result"]
            elif driver == "test_planner":
                out = plan_tests(**value)
                actual = "PASS"
                self.assertIn(case["expect_contains_test"], out["selected_tests"])
            elif driver == "evidence_completeness":
                out = evaluate_evidence_completeness(**value)
                actual = out["status"]
            elif driver == "evidence_audit":
                out = audit_evidence(value["records"])
                actual = out["status"]
            elif driver == "security_request":
                env = resolve_security_envelope(**value["envelope"])
                request = build_tool_request(**value["request"])
                out = decide_tool_request(env, request)
                actual = "PASS" if out["decision"] == "ALLOW" else "BLOCK"
            elif driver == "raw_tool_request":
                with self.assertRaises(ValueError):
                    build_tool_request(**value)
                return
            elif driver == "raw_credential_handle":
                with self.assertRaises(ValueError):
                    issue_credential_handle(**value)
                return
            elif driver == "redaction":
                out = redact_sensitive(value["value"])
                for dotted in case["expected_redacted"]:
                    cursor = out
                    for part in dotted.split("."):
                        cursor = cursor[part]
                    self.assertEqual(cursor, "[REDACTED]")
                actual = "PASS"
            elif driver == "git_dry_run":
                freshness = default_freshness_policy().assess(
                    baseline_main_sha="a" * 40,
                    current_main_sha="a" * 40,
                    commit_distance=0,
                    elapsed_minutes=0,
                    dependency_or_write_overlap=False,
                    mutating=False,
                    merge_candidate=False,
                )
                out = git_packet_dry_run(actions=value["actions"], paths=value["paths"], freshness=freshness)
                actual = out["status"]
            elif driver == "population_freeze":
                out = evaluate_population_freeze(**value)
                actual = out["status"]
            elif driver == "dependency_freeze":
                out = evaluate_dependency_freeze(**value)
                actual = out["status"]
            elif driver == "freshness":
                out = default_freshness_policy().assess(**value)
                actual = "PASS" if out["status"] == "FRESH" else "BLOCK"
            elif driver == "cache_reuse":
                out = evaluate_cache_reuse(**value)
                actual = out["status"]
            elif driver == "skill_resolution":
                out = evaluate_skill_resolution_freeze(**value)
                actual = out["status"]
            elif driver == "governing_state":
                out = evaluate_governing_state(value["records"])
                actual = out["status"]
            elif driver == "non_coercion":
                out = evaluate_scientific_non_coercion(**value)
                actual = out["status"]
            else:
                self.fail(f"unsupported driver {driver}")
        except (ValueError, OSError):
            if case["expected"] == "ERROR_FAIL_CLOSED":
                return
            raise
        self.assertEqual(actual, case["expected"], case["case_id"])
        expected_reason = case.get("expected_reason")
        if expected_reason:
            reasons = out.get("reason_codes", [])
            self.assertIn(expected_reason, reasons, case["case_id"])

    def test_extension_adds_six_cases_for_each_remaining_global_family(self):
        new_families = set(FULL_ADVERSARIAL_CATALOGUE) - set(self.base["families"])
        self.assertEqual(set(self.extension["families"]), new_families)
        self.assertEqual(self.extension["new_case_count"], 66)
        for family in new_families:
            cases = [row for row in self.extension["cases"] if row["family"] == family]
            self.assertEqual(len(cases), 6, family)

    def test_effective_global_corpus_is_18_families_108_cases(self):
        self.assertEqual(self.base["case_count"], 42)
        self.assertEqual(self.extension["new_case_count"], 66)
        self.assertEqual(self.extension["effective_case_count"], 108)
        self.assertEqual(set(self.base["families"]) | set(self.extension["families"]), set(FULL_ADVERSARIAL_CATALOGUE))

    def test_all_new_adversarial_cases_execute_with_zero_false_allow_or_false_block(self):
        for case in self.extension["cases"]:
            with self.subTest(case_id=case["case_id"], family=case["family"]):
                self._run_case(case)

    def test_all_skill_coverage_matrix_has_no_silent_gap(self):
        result = evaluate_all_skill_coverage(self.coverage)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["catalogue_family_count"], 18)
        self.assertEqual(result["catalogue_skill_count"], 15)
        self.assertEqual(result["implemented_release_count"], 14)
        self.assertEqual(result["g7_promotion_eligible_count"], 8)

        catalogue = json.loads((ROOT / self.coverage["catalogue_skill_registry"]).read_text(encoding="utf-8"))
        self.assertEqual(len(catalogue["entries"]), self.coverage["catalogue_skill_count"])
        implemented = {}
        for path in self.coverage["implemented_release_registries"]:
            registry = json.loads((ROOT / path).read_text(encoding="utf-8"))
            for row in registry["entries"]:
                implemented[row["skill_id"]] = row
        self.assertEqual(len(implemented), self.coverage["implemented_release_count"])
        for skill_id, row in implemented.items():
            self.assertTrue(row["release_id"])
            self.assertEqual(row["authority_effect"], "NONE")
            self.assertEqual(row["availability"], "SHADOW_ONLY")

    def test_every_implemented_release_is_bound_to_all_general_families(self):
        general = set(self.coverage["generic_mandatory_families"])
        self.assertEqual(general, set(FULL_ADVERSARIAL_CATALOGUE) - set(self.coverage["research_domain_conditional_families"]))
        self.assertEqual(len(general), 16)
        self.assertEqual(
            self.coverage["policy"]["every_implemented_generic_skill_release"],
            "ALL_16_GENERAL_FAMILIES_MANDATORY",
        )
        self.assertTrue(self.coverage["policy"]["shared_runtime_fixture_requires_exact_skill_tuple_binding"])

    def test_research_only_families_are_explicit_not_silently_omitted(self):
        conditional = set(self.coverage["research_domain_conditional_families"])
        self.assertEqual(conditional, {"AMBIGUOUS_GOVERNING_STATE", "SCIENTIFIC_NON_COERCION"})
        self.assertEqual(
            self.coverage["policy"]["every_research_domain_skill_release"],
            "ALL_16_GENERAL_PLUS_2_RESEARCH_FAMILIES_MANDATORY",
        )

    def test_g7_promotion_scope_does_not_steal_later_reserved_gates(self):
        self.assertEqual(set(self.coverage["g7_promotion_eligible_skill_ids"]), {
            "OVC-SKILL-001", "OVC-SKILL-002", "OVC-SKILL-003", "OVC-SKILL-004",
            "OVC-SKILL-020", "OVC-SKILL-022", "OVC-SKILL-023", "OVC-SKILL-024",
        })
        later = self.coverage["later_reserved_promotion_gates"]
        self.assertEqual(later["OVC-SKILL-014"]["gate"], "DSAI-G9A")
        self.assertEqual(later["OVC-SKILL-030"]["gate"], "DSAI-G8B")
        self.assertTrue(self.coverage["policy"]["qualification_closure_does_not_supersede_named_promotion_gate"])


if __name__ == "__main__":
    unittest.main()
