from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "registries/opt_b/c2/vnext/C2_PARENT_CONTEXT_RESOLVER_CANDIDATE_v0_1.jsonc"
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp8"
PACKET = RELEASE / "CEAR_G8_GATE_PACKET.json"
QA = RELEASE / "CEAR_G8_PREDECISION_QA.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G8_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG8GateTests(unittest.TestCase):
    def test_candidate_is_non_effective_and_parent_is_a_typed_bundle(self) -> None:
        candidate = load(CANDIDATE)
        self.assertEqual("PROPOSED_OPERATOR_GATE", candidate["status"])
        self.assertFalse(candidate["effective"])
        self.assertFalse(candidate["active"])
        self.assertFalse(candidate["canonical"])
        self.assertEqual("DENIED_PENDING_CEAR_G8", candidate["implementation_authority"])
        families = [item["family"] for item in candidate["context_families"]]
        self.assertEqual(
            [
                "FIXED_PARENT_OBSERVATION_LINK",
                "PARENT_CLOCK_STRUCTURAL_PROJECTION",
                "HIGHER_ORDER_LOCAL_CLOCK_PROJECTION",
                "EPISODE_CONTEXT",
            ],
            families,
        )
        self.assertEqual(
            "PARENT_CONTEXT_IS_A_TYPED_BUNDLE_OF_SEPARATE_LINKED_OBJECTS_NOT_ONE_BLENDED_PARENT_FIELD",
            candidate["central_decision"],
        )

    def test_fixed_parent_is_latest_expected_completed_slot_without_fallback(self) -> None:
        resolver = load(CANDIDATE)["fixed_parent_resolver"]
        self.assertEqual("2H_A_L", resolver["parent_clock"])
        self.assertEqual("UTC_0000", resolver["parent_anchor"])
        self.assertEqual(
            "PARENT_INTERVAL_END_LESS_THAN_OR_EQUAL_TO_LOCAL_FIRST_VALID_TIME",
            resolver["chronology_rule"],
        )
        self.assertTrue(resolver["equal_timestamp_allowed"])
        self.assertIn(
            "RESOLVE_THAT_EXACT_SLOT_BEFORE_COMPLETENESS_FILTERING",
            resolver["resolution_order"],
        )
        self.assertFalse(resolver["older_parent_fallback"])
        self.assertFalse(resolver["latest_observed_instead_of_latest_expected"])
        self.assertEqual(
            "CLEAR_DEPENDENTS_NO_SILENT_CARRY_FORWARD",
            resolver["expected_slot_failure_policy"],
        )
        self.assertIn("GAPPED", resolver["non_computable_slot_statuses"])
        self.assertIn("CONFLICTED", resolver["non_computable_slot_statuses"])

    def test_parent_objects_are_linked_separately_without_hidden_selection(self) -> None:
        candidate = load(CANDIDATE)
        resolver = candidate["parent_object_resolver"]
        self.assertTrue(resolver["inventory_required"])
        self.assertTrue(resolver["authoritative_objects_referenced_not_recreated"])
        self.assertFalse(resolver["parent_range_recreation"])
        self.assertTrue(resolver["measurement_and_structural_links_separate"])
        self.assertTrue(resolver["structural_depths_separate"])
        self.assertEqual("NULL_WITH_NO_ELIGIBLE_PARENT_OBJECT", resolver["zero_eligible_result"])
        self.assertEqual(
            "NULL_WITH_MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION",
            resolver["multiple_eligible_result"],
        )
        self.assertIsNone(resolver["fallback_selected_id"])
        self.assertEqual(
            {
                "LATEST_OBJECT",
                "NEAREST_OBJECT",
                "WIDEST_OBJECT",
                "SMALLEST_OBJECT",
                "BEST_OBJECT",
                "BEST_LATTICE",
                "BEST_PARENT",
                "FALLBACK_OBJECT",
            },
            set(resolver["hidden_selection_prohibited"]),
        )

    def test_refresh_age_episode_and_computability_boundaries_are_explicit(self) -> None:
        candidate = load(CANDIDATE)
        refresh = candidate["context_refresh"]
        self.assertTrue(refresh["link_recomputed_for_each_local_observation"])
        self.assertFalse(refresh["parent_object_recreated_by_local_observation"])
        self.assertEqual(
            "CONTEXT_REFRESH_LIFECYCLE_NOT_LOCAL_MARKET_TRANSITION",
            refresh["parent_identity_change_classification"],
        )
        age = candidate["age_evidence"]
        self.assertFalse(age["universal_staleness_threshold"])
        self.assertEqual("DEFERRED_TO_CONSUMER_POLICY_AND_CEAR_G9", age["staleness_authority"])
        self.assertEqual(7, len(age["required_dimensions"]))
        episode = candidate["episode_boundary"]
        self.assertFalse(episode["fixed_parent_is_episode"])
        self.assertFalse(episode["episode_link_available"])
        self.assertTrue(episode["episode_absence_does_not_block_fixed_parent"])
        computability = candidate["computability"]
        self.assertTrue(computability["independent_components"])
        self.assertTrue(computability["parent_absence_affects_only_dependent_products"])
        self.assertFalse(computability["global_degraded_collapse"])
        self.assertTrue(computability["no_fallback"])

    def test_gate_packet_is_one_complete_operator_decision(self) -> None:
        packet = load(PACKET)
        self.assertEqual("CEAR-G8", packet["gate_id"])
        self.assertEqual("Parent-Context Resolver Policy Freeze", packet["gate_title"])
        self.assertEqual("OPERATOR_REQUIRED", packet["decision_authority"])
        self.assertEqual(["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"], packet["allowed_decisions"])
        self.assertEqual("841e91a4dd9f89372aa64fb87721a9eb71f9eb56", packet["lawful_baseline_commit"])
        self.assertTrue(all(item["required"] for item in packet["acceptance_conditions"]))
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE CEAR-G8 PASS", packet["exact_approval_command"])
        self.assertEqual([], packet["external_artifacts"])
        self.assertEqual([], packet["external_artifact_hashes"])
        self.assertIn("DO_NOT_MERGE_THIS_GATE_PR", packet["stop_boundary"])

    def test_qa_recommends_pass_without_hiding_warnings_or_unresolved_issues(self) -> None:
        qa = load(QA)
        self.assertEqual("PASS", qa["recommended_decision"])
        self.assertTrue(all(item["result"] == "PASS" for item in qa["findings"]))
        self.assertEqual([], qa["blocking_warnings"])
        self.assertEqual([], qa["unresolved_issues"])
        self.assertGreaterEqual(len(qa["warnings"]), 4)
        self.assertFalse(qa["market_data_required"])
        self.assertFalse(qa["r2_write_required"])
        self.assertEqual("NONE_BEFORE_OPERATOR_PASS", qa["active_authority_delta"])

    def test_gate_state_denies_implementation_and_preserves_reserved_authority(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("CEAR-G8", state["current_gate"])
        self.assertEqual("OVC APPROVE CEAR-G8 PASS", state["exact_approval_command"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["parent_context_resolver"])
        self.assertEqual("NONE", state["current_authority"]["semantic_event_episode"])
        self.assertEqual("NONE", state["current_authority"]["consumer_denominator_overlap"])
        self.assertEqual("NONE", state["current_authority"]["release_publication_validation"])
        self.assertEqual("NONE", state["current_authority"]["probability_risk_exposure_execution"])
        self.assertEqual("DENIED_PENDING_OPERATOR_PASS_AND_DECISION_PR_MERGE", state["implementation_status"])
        self.assertEqual([], state["blockers"])

    def test_active_and_downstream_authorities_are_explicitly_not_granted(self) -> None:
        denied = set(load(PACKET)["explicitly_not_granted"])
        required = {
            "ACTIVE_OR_CANONICAL_PARENT_SELECTION",
            "NUMERIC_STALENESS_FRESHNESS_THRESHOLD",
            "SEMANTIC_EVENT_OR_EPISODE_PROMOTION",
            "C2E_OR_C2_5_ACTIVATION",
            "CONSUMER_DENOMINATOR_OR_OVERLAP_POLICY",
            "RULE_OR_THEORY_PROMOTION",
            "CANONICAL_OR_R2_PUBLICATION",
            "VALIDATION_CONSUMPTION",
            "ACTIVE_C2_SELECTOR_OR_RELEASE_CHANGE",
            "PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION",
            "AGENT_WRITE_AUTHORITY",
        }
        self.assertTrue(required.issubset(denied))


if __name__ == "__main__":
    unittest.main()
