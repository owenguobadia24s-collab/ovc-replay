from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9-implementation"
EVIDENCE = BASE / "C2AR_WP9_IMPLEMENTATION_EVIDENCE.json"
QA = BASE / "C2AR_G9A_QA_PACKET.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP9_IMPLEMENTED_STATE_v0_3.jsonc"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_COMPUTABILITY_POLICY_REGISTRY_v0_1.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARWP9ImplementationTests(unittest.TestCase):
    def test_implementation_evidence_is_complete_and_reconciled(self) -> None:
        evidence = load(EVIDENCE)
        self.assertEqual("C2AR-WP9-IMPLEMENTATION", evidence["packet"])
        self.assertEqual("C2AR-G9A", evidence["gate"])
        self.assertEqual("CEAR-G9.OPERATOR.PASS.20260805T081600+0100", evidence["operator_authority"])
        self.assertEqual("IMPLEMENTED_PENDING_FINAL_ASSURANCE", evidence["status"])
        self.assertEqual(8, evidence["synthetic_fixture_evidence"]["case_count"])
        denominator = evidence["synthetic_fixture_evidence"]["denominator_population"]
        self.assertEqual("TRANSITION_PAIR", denominator["unit_type"])
        self.assertEqual(6, denominator["population_count"])
        self.assertEqual(5, denominator["requested_count"])
        self.assertEqual(1, denominator["not_requested_count"])
        self.assertEqual(4, denominator["applicable_count"])
        self.assertEqual(2, denominator["computable_count"])
        self.assertEqual(1, denominator["not_computable_count"])
        self.assertEqual(1, denominator["censored_count"])
        self.assertEqual(2, denominator["denominator_count"])
        self.assertEqual(1, denominator["numerator_count"])
        self.assertEqual("PASS", denominator["all_partition_checks"])
        overlap = evidence["synthetic_fixture_evidence"]["overlap_population"]
        self.assertEqual(4, overlap["raw_unit_count"])
        self.assertTrue(overlap["raw_population_preserved"])
        self.assertFalse(overlap["canonical_adjustment_selected"])
        self.assertTrue(all(item["result"] == "PASS" for item in evidence["acceptance_results"]))
        self.assertEqual([], evidence["external_artifacts"])
        self.assertFalse(evidence["market_data"])
        self.assertFalse(evidence["r2_writes"])

    def test_qa_recommends_delegated_pass_without_reserved_delta(self) -> None:
        qa = load(QA)
        self.assertEqual("AUTO_RATIFIABLE_WITHIN_CEAR_G9_PASS", qa["gate_class"])
        self.assertEqual("PASS", qa["qa_recommendation"])
        self.assertEqual("PASS", qa["delegated_decision_recommendation"])
        self.assertTrue(all(item["result"] == "PASS" for item in qa["findings"]))
        self.assertEqual([], qa["blocking_warnings"])
        self.assertEqual([], qa["unresolved_issues"])
        self.assertEqual("NONE", qa["active_authority_delta"])
        self.assertFalse(qa["capacity"]["market_replay"])
        self.assertFalse(qa["capacity"]["capacity_exceeded"])

    def test_state_is_qa_review_and_preserves_every_reserved_boundary(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("QA_REVIEW", state["status"])
        self.assertEqual("C2AR-WP9-IMPLEMENTATION", state["current_packet"])
        self.assertEqual("C2AR-G9A", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("AUTO_RATIFIABLE_WITHIN_CEAR_G9_PASS", state["authority_required"])
        authority = state["authority"]
        self.assertEqual("NONE", authority["active_consumer"])
        self.assertEqual("NONE", authority["numeric_staleness_threshold"])
        self.assertEqual("NONE", authority["canonical_overlap_adjustment"])
        self.assertEqual("NONE", authority["global_quality_gating"])
        self.assertEqual("UNCHANGED_READ_ONLY", authority["active_c2"])
        self.assertEqual("NONE", authority["semantic_event_episode_rule"])
        self.assertEqual("NONE", authority["publication_validation"])
        self.assertEqual("NONE", authority["probability_risk_exposure_execution"])
        self.assertEqual([], state["blockers"])

    def test_registry_denies_active_consumers_thresholds_adjustment_and_quality_gating(self) -> None:
        registry = load(REGISTRY)
        consumers = {item["consumer_policy_id"]: item for item in registry["consumer_policies"]}
        self.assertEqual("REGISTERED_INACTIVE", consumers["C2.CONSUMER.DISCOVERY_INPUT.v1"]["status"])
        self.assertIn("UNAUTHORIZED", consumers["C2.CONSUMER.DISCOVERY_INPUT.v1"]["authority"])
        self.assertEqual("AUTHORIZED_BOUNDED_SYNTHETIC_QA_ONLY", consumers["C2.CONSUMER.READ_ONLY_QA.v1"]["authority"])
        self.assertIsNone(registry["overlap_policy"]["canonical_weighting"])
        self.assertIsNone(registry["overlap_policy"]["canonical_deduplication"])
        self.assertIsNone(registry["overlap_policy"]["numeric_adjustment"])
        self.assertFalse(registry["legacy_quality_projection"]["governing"])
        denied = set(registry["explicitly_not_granted"])
        self.assertIn("ACTIVE_OR_CANONICAL_CONSUMER_POLICY", denied)
        self.assertIn("NUMERIC_STALENESS_OR_FRESHNESS_THRESHOLD", denied)
        self.assertIn("CANONICAL_OVERLAP_WEIGHTING_DEDUPLICATION_OR_ADJUSTMENT", denied)
        self.assertIn("GLOBAL_QUALITY_GATING", denied)
        self.assertIn("SEMANTIC_EVENT_EPISODE_OR_RULE_AUTHORITY", denied)


if __name__ == "__main__":
    unittest.main()
