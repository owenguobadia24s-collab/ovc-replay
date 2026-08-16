from __future__ import annotations

import unittest

from ovc.development.authority_gates import (
    GateAssessmentInput,
    GateFunction,
    classify_gate,
    migrate_gate,
)


class OperatorReservedGateDoctrineTests(unittest.TestCase):
    def _input(self, **overrides):
        values = {
            "gate_id": "TEST-G1",
            "gate_instance_id": "TEST-G1@candidate",
            "programme_id": "OVC-TEST-v0.1",
            "plan_id": "OVC-TEST-PLAN-v0.1",
            "plan_version": "0.1",
            "packet_id": "TEST-WP1",
            "baseline_commit": "a" * 40,
            "candidate_commit": "b" * 40,
            "current_authority_envelope_id": "AUTH-ENV-1",
            "current_authority_hash": "1" * 64,
            "proposed_pass_effect_hash": "2" * 64,
            "proposed_authority_hash": "3" * 64,
            "acceptance_conditions_passed": True,
            "qa_status": "PASS",
            "blocking_issue_count": 0,
            "rollback_defined": True,
        }
        values.update(overrides)
        return GateAssessmentInput(**values)

    def test_zero_authority_delta_is_auto_ratifiable(self):
        assessment = classify_gate(self._input())
        self.assertEqual(assessment.gate_function, "ASSURANCE")
        self.assertEqual(assessment.execution_class, "AUTO_RATIFIABLE")
        self.assertEqual(assessment.reason_codes, ("AUTO.NO_AUTHORITY_DELTA",))

    def test_review_without_authority_delta_is_review_prerequisite(self):
        assessment = classify_gate(
            self._input(required_reviews=("REVIEW.INDEPENDENT_ASSURANCE",))
        )
        self.assertEqual(assessment.gate_function, "REVIEW")
        self.assertEqual(assessment.execution_class, "REVIEW_PREREQUISITE")
        self.assertEqual(assessment.reason_codes, ("REVIEW.INDEPENDENT_ASSURANCE",))

    def test_net_new_reserved_delta_is_operator_required(self):
        assessment = classify_gate(
            self._input(
                authority_delta=("OPR.ACTIVATION",),
                net_new_delta=("OPR.ACTIVATION",),
            )
        )
        self.assertEqual(assessment.gate_function, "AUTHORITY_DECISION")
        self.assertEqual(assessment.execution_class, "OPERATOR_REQUIRED")
        self.assertEqual(assessment.reserved_predicate_hits, ("OPR.ACTIVATION",))

    def test_already_delegated_reserved_action_does_not_retrigger_operator(self):
        assessment = classify_gate(
            self._input(
                authority_delta=("OPR.REAL_SOURCE_TRANSITION",),
                already_delegated_delta=("OPR.REAL_SOURCE_TRANSITION",),
                net_new_delta=(),
            )
        )
        self.assertEqual(assessment.execution_class, "AUTO_RATIFIABLE")
        self.assertEqual(assessment.reason_codes, ("AUTO.ALREADY_DELEGATED",))

    def test_hard_deny_precedes_every_other_class(self):
        assessment = classify_gate(
            self._input(
                hard_denies=("DENY.FORCE_PUSH",),
                net_new_delta=("OPR.ACTIVATION",),
                required_reviews=("REVIEW.INDEPENDENT_ASSURANCE",),
            )
        )
        self.assertEqual(assessment.execution_class, "HARD_DENY")
        self.assertEqual(assessment.reason_codes, ("DENY.FORCE_PUSH",))

    def test_missing_authority_blocks_instead_of_becoming_operator_fallback(self):
        assessment = classify_gate(
            self._input(blockers=("BLOCK.MISSING_AUTHORITY",))
        )
        self.assertEqual(assessment.execution_class, "BLOCKED")
        self.assertEqual(assessment.reason_codes, ("BLOCK.MISSING_AUTHORITY",))

    def test_mixed_gate_stops_only_for_net_new_authority(self):
        assessment = classify_gate(
            self._input(
                required_reviews=("REVIEW.SEMANTIC_CONFORMANCE",),
                net_new_delta=("OPR.SCIENTIFIC_PROMOTION",),
            )
        )
        self.assertEqual(assessment.gate_function, GateFunction.MIXED.value)
        self.assertEqual(assessment.execution_class, "OPERATOR_REQUIRED")

    def test_legacy_operator_review_migrates_forward_without_history_rewrite(self):
        assessment = classify_gate(
            self._input(required_reviews=("REVIEW.INDEPENDENT_ASSURANCE",))
        )
        migration = migrate_gate(
            legacy_classification="OPERATOR_REQUIRED",
            legacy_source_ref="docs/releases/test/legacy_gate.json",
            assessment=assessment,
            effective_from="2026-08-16T00:58:00+01:00",
        )
        self.assertEqual(migration.legacy_classification, "OPERATOR_REQUIRED")
        self.assertEqual(migration.new_classification, "REVIEW_PREREQUISITE")
        self.assertEqual(migration.migration_reason, ("REVIEW.INDEPENDENT_ASSURANCE",))
        self.assertTrue(migration.migration_id)


if __name__ == "__main__":
    unittest.main()
