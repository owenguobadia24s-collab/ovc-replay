from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/plan-v0-3-ratification"
BINDING = BASE / "C2AR_PLAN_V0_3_SOURCE_BINDING.json"
DECISION = BASE / "C2AR_PLAN_V0_3_OPERATOR_RATIFICATION.json"
QA = BASE / "C2AR_PLAN_V0_3_RATIFICATION_QA.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_PLAN_V0_3_RATIFIED_STATE.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARPlanV03RatificationTests(unittest.TestCase):
    def test_plan_source_is_exactly_hash_bound(self) -> None:
        binding = load(BINDING)
        self.assertEqual("OVC-C2-ANATOMY-OBSERVATION-REDESIGN-IMPLEMENTATION-PLAN-0.3-REVISED", binding["plan_document_id"])
        self.assertEqual("0.3-REVISED", binding["plan_version"])
        self.assertEqual("3b016136b3ee69827bb27d9252dd827235665afa57a2f33b3469539942bee009", binding["source_file_sha256"])
        self.assertEqual(82394, binding["source_file_size_bytes"])
        self.assertEqual("d51ab109481c4a4f84c5fd955c56521e1d27c853bb568168dc689bf5f5bbf1c9", binding["governing_design_source"]["sha256"])
        self.assertEqual("b76fb70533ccba161eb9d043f393ff875a3bcf8170009dc0a380c234a04f628d", binding["superseded_plan"]["sha256"])
        self.assertEqual("MATCH", binding["hash_verification"]["result"])
        self.assertEqual(2, binding["hash_verification"]["reads"])
        self.assertEqual("C2AR_PROGRAMME_RELEASE_ROOT_POST_PGN_WP2E_GENERATED_EVIDENCE", binding["repository_evidence_location"])

    def test_operator_ratification_preserves_parts_one_through_nine(self) -> None:
        decision = load(DECISION)
        self.assertEqual("C2AR-PLAN-V0.3.OPERATOR.RATIFY.20260805T081600+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertTrue(decision["approved_effect"]["preserve_parts_1_through_9"])
        self.assertEqual("CEAR-G9", decision["approved_effect"]["preserve_accepted_gates_through"])
        self.assertEqual("BOTTOM_UP_FUNCTIONAL_DISCOVERY", decision["approved_effect"]["replace_part_10_route"])
        self.assertEqual("BENCHMARK_COMPARATORS_AND_CROSSWALK_OBJECTS_ONLY", decision["approved_effect"]["legacy_rules"])
        self.assertEqual("IMPLEMENTED_SHADOW_COMPLETE_ACTIVE_C2_UNCHANGED", decision["approved_effect"]["completion_boundary"])
        self.assertEqual(
            "docs/releases/c2-anatomy-observation-redesign-v0-2/plan-v0-3-ratification/C2AR_PLAN_V0_3_SOURCE_BINDING.json",
            decision["source_binding"],
        )

    def test_part_ten_is_bottom_up_neutral_and_legacy_seed_free(self) -> None:
        method = load(DECISION)["part_10_methodology"]
        self.assertEqual("COMPLETE_LAWFUL_NEUTRAL_OPPORTUNITY_POPULATIONS", method["discovery_population"])
        self.assertIn("NOT_EVALUABLE", method["opportunity_outcomes"])
        self.assertIn("AUTHORITY_BLOCKED", method["opportunity_outcomes"])
        self.assertIn("FUNCTIONAL_CORE", method["discovery_objects"])
        self.assertEqual(["INVARIANT", "COMMON", "OPTIONAL", "RARE", "CONTRADICTORY"], method["functional_core_components"])
        self.assertIn("SAME_OBJECT", method["restricted_rule_ast"])
        self.assertIn("RELATION_TRANSITION", method["restricted_rule_ast"])
        self.assertTrue(method["matched_controls_required"])
        self.assertTrue(method["complete_negative_results_required"])
        self.assertEqual("PROHIBITED", method["legacy_seed_filter_score_stop_promote"])
        self.assertEqual("PROHIBITED", method["outcome_validation_profitability_exposure_dependencies"])

    def test_cear_g9_is_carried_forward_and_remaining_sequence_is_bounded(self) -> None:
        state = load(STATE)
        self.assertEqual("0.3-REVISED", state["plan_version"])
        self.assertEqual("APPROVED", state["status"])
        self.assertEqual("C2AR-WP9-IMPLEMENTATION", state["current_packet"])
        self.assertEqual("C2AR-G9A", state["current_gate"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("CEAR-G9.OPERATOR.PASS.20260805T081600+0100", state["cear_g9"]["decision_id"])
        self.assertEqual("4f7527524c4cde404fa240531b23743e1f1df5ea", state["cear_g9"]["decision_merge"])
        self.assertEqual("INACTIVE_NONCANONICAL_SHADOW_ONLY", state["cear_g9"]["implementation_authority"])
        packets = {item["packet_id"]: item for item in state["remaining_packets"]}
        self.assertEqual("AUTO_RATIFIABLE_C2AR_G9A", packets["C2AR-WP9-IMPLEMENTATION"]["authority_required"])
        self.assertEqual("OPERATOR_REQUIRED_CEAR_G10", packets["C2AR-WP10"]["authority_required"])
        self.assertEqual("AUTO_IF_NO_RESERVED_DELTA_C2AR_G11", packets["C2AR-WP11"]["authority_required"])

    def test_reserved_authority_and_qa_remain_explicit(self) -> None:
        decision = load(DECISION)
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("ACTIVE_C2_SELECTOR_FORMULA_PARAMETER_CLOCK_LATTICE_RESOLVER_OR_RELEASE_CHANGE", denied)
        self.assertIn("CANONICAL_OR_R2_PUBLICATION", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)
        self.assertIn("OUTCOME_BASED_DISCOVERY_SELECTION_OR_CONFIRMATION", denied)
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION", denied)
        qa = load(QA)
        self.assertEqual("PASS", qa["recommendation"])
        self.assertTrue(all(item["result"] == "PASS" for item in qa["findings"]))
        self.assertEqual([], qa["blocking_warnings"])
        self.assertEqual([], qa["unresolved_issues"])
        self.assertEqual("NONE", qa["active_authority_effect"])


if __name__ == "__main__":
    unittest.main()
