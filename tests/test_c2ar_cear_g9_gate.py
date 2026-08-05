from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "registries/opt_b/c2/vnext/C2_COMPUTABILITY_CONSUMER_POLICY_CANDIDATE_v0_1.jsonc"
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp9"
PACKET = RELEASE / "CEAR_G9_GATE_PACKET.json"
QA = RELEASE / "CEAR_G9_PREDECISION_QA.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G9_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG9GateTests(unittest.TestCase):
    def test_candidate_is_non_effective_and_separates_five_dimensions(self) -> None:
        candidate = load(CANDIDATE)
        self.assertEqual("PROPOSED_OPERATOR_GATE", candidate["status"])
        self.assertFalse(candidate["effective"])
        self.assertFalse(candidate["active"])
        self.assertFalse(candidate["canonical"])
        self.assertEqual("DENIED_PENDING_CEAR_G9", candidate["implementation_authority"])
        self.assertEqual(
            ["AVAILABILITY", "COMPUTABILITY", "ASSURANCE", "CONSUMER_ELIGIBILITY", "AUTHORITY"],
            [item["dimension"] for item in candidate["separate_dimensions"]],
        )
        self.assertEqual(
            "USABILITY_IS_PER_COMPONENT_AND_PER_CONSUMER_WITH_EXPLICIT_DEPENDENCIES_DENOMINATORS_AND_OVERLAP_EVIDENCE_NOT_ONE_GLOBAL_DEGRADED_OR_QUALITY_STATE",
            candidate["central_decision"],
        )

    def test_dependency_graph_is_selective_versioned_and_has_no_hidden_fallback(self) -> None:
        graph = load(CANDIDATE)["dependency_graph"]
        self.assertTrue(graph["versioned"])
        self.assertTrue(graph["profile_specific"])
        self.assertEqual(
            ["REQUIRED", "OPTIONAL", "WARNING_ONLY", "ALTERNATIVE", "PROHIBITED"],
            graph["edge_types"],
        )
        self.assertFalse(graph["hidden_fallback"])
        self.assertFalse(graph["global_failure_propagation"])
        self.assertTrue(graph["dependency_ids_required"])
        self.assertTrue(graph["reason_propagation_required"])
        self.assertEqual(
            "PROPAGATE_ONLY_TO_THE_DECLARED_DEPENDENT_COMPONENT",
            graph["required_edge_failure"],
        )

    def test_missingness_censorship_ambiguity_staleness_and_conflict_remain_distinct(self) -> None:
        candidate = load(CANDIDATE)
        self.assertEqual(
            ["NOT_REQUESTED", "NOT_APPLICABLE", "COMPUTABLE", "NOT_COMPUTABLE", "CENSORED", "CONFLICTED"],
            candidate["terminal_dispositions"],
        )
        families = candidate["reason_code_families"]
        self.assertIn("WARMUP_INSUFFICIENT", families["warmup_and_population"])
        self.assertIn("SOURCE_MISSING", families["source_and_continuity"])
        self.assertIn("BOUNDARY_CENSORED", families["censorship"])
        self.assertIn("MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION", families["ambiguity"])
        self.assertIn("STALE_FOR_CONSUMER", families["staleness"])
        self.assertIn("MODEL_UNAVAILABLE", families["model_and_dependency"])
        self.assertIn("POLICY_CONFLICT", families["conflict"])

    def test_axis_profiles_and_parent_dependencies_are_independent(self) -> None:
        rules = {item["axis"]: item["rule"] for item in load(CANDIDATE)["axis_and_profile_rules"]}
        self.assertIn("SEPARATE_DEPENDENCY_GRAPHS", rules["LOCATION"])
        self.assertIn("RAW_MOTION", rules["MOTION"])
        self.assertIn("EACH_METRIC_IS_INDEPENDENTLY_COMPUTABLE", rules["ORGANISATION"])
        self.assertIn("PER_EXACT_OBJECT_ID_AND_TRACK", rules["INTERACTION"])
        self.assertIn("NON_GOVERNING_COMPATIBILITY_PROJECTION", rules["QUALITY_COMPATIBILITY_PROJECTION"])
        self.assertIn("REQUIRED_PARENT_DEPENDENCY", rules["PARENT_DEPENDENT_PROFILES"])

    def test_consumer_policy_selects_no_active_policy_or_numeric_threshold(self) -> None:
        policy = load(CANDIDATE)["consumer_policy"]
        self.assertTrue(policy["consumer_policy_id_required"])
        self.assertTrue(policy["eligibility_result_per_component"])
        self.assertTrue(policy["eligibility_requires_computable"])
        self.assertTrue(policy["eligibility_requires_authorized"])
        self.assertFalse(policy["universal_staleness_policy"])
        self.assertFalse(policy["numeric_staleness_threshold_selected"])
        self.assertEqual("NOT_GRANTED_AT_CEAR_G9", policy["consumer_specific_numeric_parameters"])
        self.assertFalse(policy["silent_exclusion"])
        self.assertFalse(policy["hidden_fallback"])

    def test_denominator_contract_has_exact_partitions_and_pair_units(self) -> None:
        denominator = load(CANDIDATE)["denominator_contract"]
        required_counts = set(denominator["required_counts"])
        self.assertTrue({
            "population_count",
            "requested_count",
            "not_requested_count",
            "applicable_count",
            "not_applicable_count",
            "computable_count",
            "not_computable_count",
            "censored_count",
            "conflicted_count",
            "eligible_count",
            "included_count",
            "numerator_count",
            "denominator_count",
        }.issubset(required_counts))
        identities = set(denominator["partition_identities"])
        self.assertIn("POPULATION_COUNT_EQUALS_REQUESTED_COUNT_PLUS_NOT_REQUESTED_COUNT", identities)
        self.assertIn("REQUESTED_COUNT_EQUALS_APPLICABLE_COUNT_PLUS_NOT_APPLICABLE_COUNT", identities)
        self.assertIn(
            "APPLICABLE_COUNT_EQUALS_COMPUTABLE_COUNT_PLUS_NOT_COMPUTABLE_COUNT_PLUS_CENSORED_COUNT_PLUS_CONFLICTED_COUNT",
            identities,
        )
        self.assertEqual("COMPARABLE_TRANSITION_PAIRS_NOT_SINGLE_OBSERVATIONS", denominator["transition_rate_unit"])
        self.assertTrue(denominator["raw_counts_separate_from_rates"])
        self.assertFalse(denominator["silent_missingness_exclusion"])
        self.assertFalse(denominator["mixed_unit_rate"])

    def test_overlap_is_claim_specific_without_canonical_adjustment(self) -> None:
        overlap = load(CANDIDATE)["overlap_contract"]
        self.assertTrue(overlap["overlap_is_claim_specific"])
        self.assertTrue(overlap["raw_unit_counts_always_preserved"])
        self.assertIn("SHARED_OBSERVATION", overlap["cluster_types"])
        self.assertIn("SHARED_OBJECT_TRACK", overlap["cluster_types"])
        self.assertIn("BID_ASK_PAIR", overlap["cluster_types"])
        self.assertFalse(overlap["canonical_weighting_or_deduplication_selected"])
        self.assertFalse(overlap["numeric_overlap_adjustment_selected"])
        self.assertFalse(overlap["raw_and_adjusted_rate_mixing"])
        self.assertFalse(overlap["generic_overlap_correction"])
        self.assertIn("SAME_CLUSTER_POLICY_ID", overlap["comparison_rule"])

    def test_comparability_and_quality_fail_closed(self) -> None:
        candidate = load(CANDIDATE)
        comparison = candidate["comparability_contract"]
        self.assertIn("unit_type", comparison["required_equal_fields"])
        self.assertIn("consumer_policy_id", comparison["required_equal_fields"])
        self.assertIn("overlap_policy_id", comparison["required_equal_fields"])
        self.assertTrue(comparison["transition_pairs_require_same_pair_construction_policy"])
        self.assertFalse(comparison["silent_pooling"])
        self.assertIn("NOT_COMPARABLE", comparison["incomparable_result"])
        quality = candidate["quality_compatibility_projection"]
        self.assertFalse(quality["governing"])
        self.assertFalse(quality["may_hide_component_status"])
        self.assertFalse(quality["may_drive_eligibility"])
        self.assertFalse(quality["may_drive_denominator_inclusion"])
        self.assertIsNone(quality["global_degraded_state"])

    def test_gate_packet_and_qa_are_complete_operator_decision(self) -> None:
        packet = load(PACKET)
        qa = load(QA)
        self.assertEqual("CEAR-G9", packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", packet["decision_authority"])
        self.assertEqual(["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"], packet["allowed_decisions"])
        self.assertEqual("8ef7efb131a87ee9304c8e41494d64980dbc875d", packet["lawful_baseline_commit"])
        self.assertTrue(all(item["required"] for item in packet["acceptance_conditions"]))
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE CEAR-G9 PASS", packet["exact_approval_command"])
        self.assertEqual([], packet["external_artifacts"])
        self.assertEqual([], packet["external_artifact_hashes"])
        self.assertIn("DO_NOT_MERGE_THIS_GATE_PR", packet["stop_boundary"])
        self.assertEqual("PASS", qa["recommended_decision"])
        self.assertTrue(all(item["result"] == "PASS" for item in qa["findings"]))
        self.assertEqual([], qa["blocking_warnings"])
        self.assertEqual([], qa["unresolved_issues"])
        self.assertEqual("NONE_BEFORE_OPERATOR_PASS", qa["active_authority_delta"])

    def test_gate_state_denies_implementation_and_reserved_authority(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("OVC APPROVE CEAR-G9 PASS", state["exact_approval_command"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["consumer_eligibility_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["denominator_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["overlap_adjustment_policy"])
        self.assertEqual("NOT_GRANTED", state["current_authority"]["global_quality_gating"])
        self.assertEqual("NONE", state["current_authority"]["rule_theory"])
        self.assertEqual("NONE", state["current_authority"]["release_publication_validation"])
        self.assertEqual("NONE", state["current_authority"]["probability_risk_exposure_execution"])
        self.assertEqual("DENIED_PENDING_OPERATOR_PASS_AND_DECISION_PR_MERGE", state["implementation_status"])
        self.assertEqual([], state["blockers"])

    def test_active_and_downstream_authorities_are_explicitly_not_granted(self) -> None:
        denied = set(load(PACKET)["explicitly_not_granted"])
        required = {
            "ACTIVE_OR_CANONICAL_CONSUMER_ELIGIBILITY_POLICY",
            "NUMERIC_STALENESS_FRESHNESS_THRESHOLD",
            "CANONICAL_OVERLAP_WEIGHTING_DEDUPLICATION_OR_ADJUSTMENT",
            "ACTIVE_RATE_OR_DENOMINATOR_PUBLICATION",
            "GLOBAL_QUALITY_GATING",
            "HIDDEN_FALLBACK_OR_SILENT_EXCLUSION",
            "SEMANTIC_EVENT_OR_EPISODE_PROMOTION",
            "C2E_OR_C2_5_ACTIVATION",
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
