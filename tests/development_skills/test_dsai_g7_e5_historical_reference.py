from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills.assurance import (
    audit_evidence, evaluate_gate, evaluate_qa, plan_tests, test_execution_plan,
)
from ovc.development.skills.engineering import (
    build_contract_proposal, build_fixture_proposal, build_implementation_proposal,
    build_schema_proposal, git_packet_dry_run,
)
from ovc.development.skills.governance import (
    shadow_authority_resolver, shadow_preflight, shadow_prerequisite_resolver, shadow_scope_guard,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "fixtures/development_skills/g7_e5_historical_reference_corpus_v0_1.json"
E4_PASS = ROOT / "records/development/skills/DSAI_G7_E4_OPERATOR_PASS_20260812T115600+0100.json"
ENV = ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json"

def run_case(case):
    d = case["driver"]
    v = case["input"]
    if d == "preflight": return shadow_preflight(v)
    if d == "authority": return shadow_authority_resolver(**v)
    if d == "scope": return shadow_scope_guard(**v)
    if d == "prereq": return shadow_prerequisite_resolver(**v)
    if d == "contract_builder": return build_contract_proposal(**v)
    if d == "schema_builder": return build_schema_proposal(**v)
    if d == "fixture_builder": return build_fixture_proposal(**v)
    if d == "implementation_builder": return build_implementation_proposal(**v)
    if d == "git": return git_packet_dry_run(**v)
    if d == "test_plan": return plan_tests(**v)
    if d == "test_execution": return test_execution_plan(**v)
    if d == "qa": return evaluate_qa(v["assertions"])
    if d == "evidence": return audit_evidence(v["records"])
    if d == "gate": return evaluate_gate(**v)
    raise AssertionError(f"unsupported E5 driver {d}")

def assert_reference(testcase, case, out):
    for key, expected in case["reference"].items():
        if key == "reason_contains": testcase.assertIn(expected, out.get("reason_codes", []), case["case_id"])
        elif key == "selected_contains": testcase.assertIn(expected, out.get("selected_tests", []), case["case_id"])
        else: testcase.assertEqual(out.get(key), expected, f"{case['case_id']}:{key}")

class DSAIG7E5HistoricalReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.e4 = json.loads(E4_PASS.read_text(encoding="utf-8"))
        cls.env = json.loads(ENV.read_text(encoding="utf-8"))
        cls.releases = {}
        for path in (
            ROOT / "registries/development/skills/governance_candidates_v0_1.json",
            ROOT / "registries/development/skills/first_generation_candidates_v0_1.json",
        ):
            for row in json.loads(path.read_text(encoding="utf-8"))["entries"]:
                cls.releases[row["skill_id"]] = row

    def test_e4_operator_pass_is_materialised_without_trusted_effect(self):
        self.assertEqual(self.e4["evaluation_layer"], "E4")
        self.assertEqual(self.e4["decision"], "PASS")
        self.assertEqual(self.e4["decision_authority"], "HUMAN_OPERATOR")
        self.assertEqual(self.e4["known_false_allows_remaining"], 0)
        self.assertEqual(self.e4["authority_effect"], "QUALIFICATION_EVIDENCE_ONLY_NO_TRUSTED_PROMOTION")
        self.assertEqual(self.e4["next_evaluation_layer"], "E5")

    def test_e5_corpus_is_all_skill_exact_tuple_scoped_and_independent_review_pending(self):
        self.assertEqual(self.corpus["case_count"], 42)
        self.assertEqual(len(self.corpus["cases"]), 42)
        self.assertEqual(self.corpus["implemented_exact_skill_count"], 14)
        self.assertEqual(self.corpus["cases_per_skill"], 3)
        self.assertEqual(self.corpus["independent_reference_review_state"], "PENDING")
        self.assertEqual(self.corpus["authority_effect"], "NONE")
        self.assertFalse(self.corpus["scoring_policy"]["operator_outcome_used_for_scoring"])
        counts = {}
        for case in self.corpus["cases"]:
            counts[case["skill_id"]] = counts.get(case["skill_id"], 0) + 1
            release = self.releases[case["skill_id"]]
            self.assertEqual(case["release_id"], release["release_id"])
            self.assertIn(case["capability_id"], release["capability_ids"])
            self.assertEqual(case["environment_id"], self.env["base_environment_id"])
            self.assertFalse(case["operator_outcome_used_for_scoring"])
        self.assertEqual(set(counts), set(self.releases))
        self.assertEqual(set(counts.values()), {3})

    def test_every_historical_source_reference_exists_in_repository(self):
        for case in self.corpus["cases"]:
            for source in case["historical_source_refs"]:
                with self.subTest(case_id=case["case_id"], source=source):
                    self.assertTrue((ROOT / source).exists(), f"missing historical source {source}")

    def test_all_42_historical_replays_match_frozen_reference(self):
        for case in self.corpus["cases"]:
            with self.subTest(case_id=case["case_id"], skill_id=case["skill_id"]):
                out = run_case(case)
                assert_reference(self, case, out)
                self.assertEqual(out.get("authority_effect"), "NONE", case["case_id"])
                if "writes_performed" in out:
                    self.assertEqual(out["writes_performed"], [], case["case_id"])

    def test_reference_scoring_does_not_use_operator_outcomes(self):
        for case in self.corpus["cases"]:
            self.assertFalse(case["operator_outcome_used_for_scoring"])
            self.assertNotIn("operator_outcome", case["reference"])
            self.assertTrue(case["reference_basis"].strip())

if __name__ == "__main__":
    unittest.main()
