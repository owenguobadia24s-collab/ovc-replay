from __future__ import annotations

import unittest

from ovc.research_operations.prsc import (
    PRSCContractError,
    build_hypothesis_family_registry,
    build_multiplicity_method_pack,
    build_shared_family_reference_draws,
    build_specification_opportunity_ledger,
    collapse_exact_semantic_duplicates,
    enforce_review_capacity,
    step_down_max_statistic_adjustment,
)


class PRSCMultiplicityTests(unittest.TestCase):
    def _family(self):
        return build_hypothesis_family_registry(
            family_id="FAM.1",
            hypotheses=[
                {"hypothesis_id": "H1", "semantic_key": "A"},
                {"hypothesis_id": "H2", "semantic_key": "B", "parent_hypothesis_id": "H1"},
                {"hypothesis_id": "H3", "semantic_key": "B"},
            ],
        )

    def test_family_identity_and_exact_duplicate_collapse_preserve_provenance(self):
        family = self._family()
        self.assertEqual(family["declared_hypothesis_count"], 3)
        self.assertIsNone(family["parent_family_id"])
        collapsed = collapse_exact_semantic_duplicates(family)
        self.assertEqual(collapsed["inference_count"], 2)
        b = next(row for row in collapsed["groups"] if row["semantic_key"] == "B")
        self.assertEqual(b["provenance_hypothesis_ids"], ["H2", "H3"])
        self.assertTrue(collapsed["provenance_preserved"])

    def test_unknown_parent_fails_closed(self):
        with self.assertRaises(PRSCContractError):
            build_hypothesis_family_registry(
                family_id="F",
                hypotheses=[{"hypothesis_id": "H", "semantic_key": "A", "parent_hypothesis_id": "MISSING"}],
            )

    def test_specification_opportunity_ledger_keeps_failed_and_post_hoc(self):
        ledger = build_specification_opportunity_ledger(
            family_id="FAM.1",
            configurations=[
                {"configuration_id": "C1", "state": "DECLARED", "hypothesis_id": "H1"},
                {"configuration_id": "C2", "state": "ATTEMPTED", "hypothesis_id": "H2"},
                {"configuration_id": "C3", "state": "FAILED", "reason": "NOT_EVALUABLE"},
                {"configuration_id": "C4", "state": "POST_HOC", "reason": "SEEN_AFTER_RESULTS"},
            ],
        )
        self.assertEqual(ledger["state_counts"]["FAILED"], 1)
        self.assertEqual(ledger["state_counts"]["POST_HOC"], 1)
        self.assertTrue(ledger["complete_accounting"])

    def test_shared_draws_require_complete_family_and_same_draw_count(self):
        family = self._family()
        with self.assertRaises(PRSCContractError):
            build_shared_family_reference_draws(family_registry=family, hypothesis_draws={"H1": [1], "H2": [2]})
        with self.assertRaises(PRSCContractError):
            build_shared_family_reference_draws(
                family_registry=family,
                hypothesis_draws={"H1": [1, 2], "H2": [2], "H3": [3, 4]},
            )

    def test_step_down_uses_shared_family_maxima_and_is_monotone(self):
        family = self._family()
        draws = build_shared_family_reference_draws(
            family_registry=family,
            hypothesis_draws={
                "H1": ["1.0", "2.0", "4.0", "0.5"],
                "H2": ["0.8", "1.5", "2.5", "0.4"],
                "H3": ["0.7", "1.2", "2.0", "0.3"],
            },
        )
        pack = build_multiplicity_method_pack(method_pack_id="M.1", familywise_alpha="0.05")
        result = step_down_max_statistic_adjustment(
            observed_statistics={"H1": "3.0", "H2": "2.0", "H3": "1.0"},
            shared_reference_draws=draws,
            method_pack=pack,
        )
        pvals = [float(row["adjusted_p"]) for row in result["rows"]]
        self.assertEqual(result["ordered_hypothesis_ids"], ["H1", "H2", "H3"])
        self.assertEqual(pvals, sorted(pvals))
        self.assertTrue(result["joint_dependence_preserved"])

    def test_review_capacity_never_allows_hidden_top_n(self):
        family = self._family()
        partial = enforce_review_capacity(family_registry=family, reviewed_hypothesis_ids=["H1"], capacity_limit=1)
        self.assertEqual(partial["status"], "REVIEW_CAPACITY_EXCEEDED")
        self.assertFalse(partial["hidden_top_n_allowed"])
        complete = enforce_review_capacity(family_registry=family, reviewed_hypothesis_ids=["H1", "H2", "H3"], capacity_limit=3)
        self.assertEqual(complete["status"], "PASS")

    def test_invalid_alpha_is_rejected(self):
        for value in ("0", "1", "nan"):
            with self.assertRaises(PRSCContractError):
                build_multiplicity_method_pack(method_pack_id="M", familywise_alpha=value)


if __name__ == "__main__":
    unittest.main()
