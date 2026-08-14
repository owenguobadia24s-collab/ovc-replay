from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import validate_instance
from ovc.programme_genesis.grt_v0_2.dependencies import assess_companion, assess_orphan, resolve_dependency, validate_workflow_governance
from ovc.programme_genesis.grt_v0_2.rules import evaluate_rule, findings_from_evaluations, reconcile_finding

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/wp3c/dependency_rule_fixture.json"
SCHEMA = ROOT / "schemas/governance/grt_v0_2/dependency_resolution.schema.json"
RULES = ROOT / "registries/governance/grt_v0_2/GRT_RULE_BUNDLE_v0_2.json"


class GRT2WP3CResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.rules = {rule["rule_id"]: rule for rule in json.loads(RULES.read_text(encoding="utf-8"))["rules"]}

    def test_required_dependency_resolves_and_missing_fails_closed(self) -> None:
        result = resolve_dependency(self.fixture["required_contract"], [self.fixture["provider"]])
        self.assertEqual(result["status"], "RESOLVED")
        validate_instance(result, json.loads(SCHEMA.read_text(encoding="utf-8")))
        missing = resolve_dependency(self.fixture["required_contract"], [])
        self.assertEqual(missing["status"], "UNRESOLVED")
        self.assertIn("CARDINALITY_UNSATISFIED", missing["reason_codes"])

    def test_optional_absence_is_typed_not_fabricated(self) -> None:
        contract = dict(self.fixture["required_contract"])
        contract["requiredness"] = "OPTIONAL"
        contract["cardinality"] = "ZERO_OR_ONE"
        result = resolve_dependency(contract, [])
        self.assertEqual(result["status"], "OPTIONAL_ABSENT")
        self.assertEqual(result["provider_ids"], [])

    def test_placeholder_companion_cannot_satisfy_obligation(self) -> None:
        valid = assess_companion(self.fixture["companion_obligation"], [self.fixture["valid_companion"]])
        self.assertEqual(valid["status"], "RESOLVED")
        placeholder = dict(self.fixture["valid_companion"])
        placeholder["placeholder"] = True
        invalid = assess_companion(self.fixture["companion_obligation"], [placeholder])
        self.assertEqual(invalid["status"], "FAIL")

    def test_orphan_is_role_and_lifecycle_aware(self) -> None:
        current = {"artifact_id":"OVC.SCHEMA.v1","lifecycle_class":"CURRENT_SUPPORTING"}
        self.assertTrue(assess_orphan(current, [])["actionable"])
        historical = dict(current); historical["lifecycle_class"] = "HISTORICAL_IMMUTABLE"
        self.assertFalse(assess_orphan(historical, [])["actionable"])
        related = assess_orphan(current, [{"relationship_type":"GOVERNED_BY","status":"RESOLVED"}])
        self.assertFalse(related["actionable"])

    def test_workflow_governance_is_explicit(self) -> None:
        self.assertEqual(validate_workflow_governance(self.fixture["workflow"])["status"], "PASS")
        incomplete = dict(self.fixture["workflow"]); incomplete.pop("owner")
        self.assertEqual(validate_workflow_governance(incomplete)["status"], "FAIL")

    def test_registered_rule_missing_fact_is_not_evaluable_and_violation_yields_finding(self) -> None:
        rule = self.rules["GRT-R500"]
        subject = {"artifact_id":"OVC.CONSUMER.v1"}
        missing = evaluate_rule(rule, subject, {})
        self.assertEqual(missing["admission_result"], "NOT_EVALUABLE")
        facts = {rule["applicability_predicate"]: True, rule["violation_predicate"]: True}
        violation = evaluate_rule(rule, subject, facts)
        self.assertEqual(violation["evaluation_status"], "VIOLATION")
        findings = findings_from_evaluations(evaluations=[violation], rule_by_id=self.rules, first_seen_tree="1"*40)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "GRT-R500")

    def test_debt_reconciliation_reuses_wp2_ratchet_semantics(self) -> None:
        unchanged = reconcile_finding(predecessor_state="GRANDFATHERED", candidate_state="ACTIONABLE", predecessor_extent={"violations":1}, candidate_extent={"violations":1})
        expanded = reconcile_finding(predecessor_state="GRANDFATHERED", candidate_state="ACTIONABLE", predecessor_extent={"violations":1}, candidate_extent={"violations":2})
        self.assertEqual(unchanged["classification"], "BASELINE_UNCHANGED")
        self.assertEqual(unchanged["admission"], "PASS")
        self.assertEqual(expanded["classification"], "BASELINE_EXPANDED")
        self.assertEqual(expanded["admission"], "FAIL")


if __name__ == "__main__":
    unittest.main()
