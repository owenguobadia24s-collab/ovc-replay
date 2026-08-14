from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.development_latency_context import (
    build_contextual_companion_receipt,
    normalize_development_context,
    validate_contextual_companion_receipt,
)
from ovc.development.diagnostic_observability import (
    attach_companion_receipt,
    summarize_trace,
)


def summary() -> dict:
    return summarize_trace(
        run_id="RUN-CONTEXT-1",
        programme_id="OVC-EXAMPLE-v0.1",
        packet_id="EX-WP2",
        started_at_utc="2026-08-13T18:00:00Z",
        completed_at_utc="2026-08-13T18:00:01Z",
        total_wall_ms=1000,
        events=[],
    )


class DevelopmentLatencyContextTests(unittest.TestCase):
    def test_d2_exact_packet_receipt_carries_comparison_context(self) -> None:
        source = {"schema": "existing-execution/v1", "record_id": "EXECUTION-ID", "status": "PASS"}
        receipt = build_contextual_companion_receipt(
            source_execution_record=source,
            trace_summary=summary(),
            implementation_difficulty="D2",
            work_phase="IMPLEMENTATION",
            specification_maturity="WORK_PACKET_EXACT",
            classification_basis="Ratified bounded packet with exact acceptance criteria.",
            assistant_model="GPT-5.6 Sol",
            reasoning_profile="MEDIUM",
            subscription_plan="Pro",
            assistant_configuration_evidence="DECLARED",
            scope_metrics={
                "changed_files_count": 3,
                "tests_run_count": 12,
                "remediation_attempt_count": 0,
            },
            observed_at_utc="2026-08-13T18:00:02Z",
        )
        self.assertEqual(receipt["schema"], "ovc-development-latency-diagnostic-companion/v2")
        self.assertEqual(receipt["receipt_version"], "DEVOBS-v0.2")
        self.assertEqual(receipt["task_profile"]["implementation_difficulty"], "D2")
        self.assertEqual(receipt["task_profile"]["difficulty_label"], "BOUNDED_IMPLEMENTATION")
        self.assertEqual(receipt["task_profile"]["work_phase"], "IMPLEMENTATION")
        self.assertEqual(receipt["task_profile"]["specification_maturity"], "WORK_PACKET_EXACT")
        self.assertEqual(receipt["assistant_configuration"]["reasoning_profile"], "MEDIUM")
        self.assertEqual(receipt["assistant_configuration"]["evidence_class"], "DECLARED")
        self.assertTrue(receipt["comparison_context_only"])
        self.assertEqual(validate_contextual_companion_receipt(receipt), receipt)

    def test_context_attachment_preserves_existing_execution_identity(self) -> None:
        source = {
            "schema": "existing-orch-record/v1",
            "record_id": "ORIGINAL-ID",
            "execution_intent_id": "INTENT-ID",
            "status": "PASS",
        }
        receipt = build_contextual_companion_receipt(
            source_execution_record=source,
            trace_summary=summary(),
            implementation_difficulty="D3",
            work_phase="RECONCILIATION",
            specification_maturity="IMPLEMENTATION_PLAN",
            reasoning_profile="HIGH",
            assistant_configuration_evidence="DECLARED",
            observed_at_utc="2026-08-13T18:00:02Z",
        )
        attached = attach_companion_receipt(source, receipt)
        self.assertEqual(attached["record_id"], "ORIGINAL-ID")
        self.assertEqual(attached["execution_intent_id"], "INTENT-ID")
        self.assertTrue(attached["development_latency_diagnostic"]["source_execution_identity_unchanged"])
        self.assertEqual(attached["development_latency_diagnostic"]["authority_effect"], "NONE")

    def test_unknown_reasoning_profile_remains_explicitly_unavailable(self) -> None:
        context = normalize_development_context(
            implementation_difficulty="D1",
            work_phase="TEST_QA",
        )
        self.assertEqual(context["assistant_configuration"]["reasoning_profile"], "UNKNOWN")
        self.assertEqual(context["assistant_configuration"]["evidence_class"], "UNAVAILABLE")

    def test_known_reasoning_profile_cannot_be_unattributed(self) -> None:
        with self.assertRaisesRegex(ValueError, "known reasoning_profile"):
            normalize_development_context(
                implementation_difficulty="D2",
                work_phase="IMPLEMENTATION",
                reasoning_profile="PRO",
            )

    def test_invalid_difficulty_and_scope_metrics_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "implementation_difficulty"):
            normalize_development_context(
                implementation_difficulty="D6",
                work_phase="IMPLEMENTATION",
            )
        with self.assertRaisesRegex(ValueError, "scope metric"):
            normalize_development_context(
                implementation_difficulty="D2",
                work_phase="IMPLEMENTATION",
                scope_metrics={"changed_files_count": -1},
            )

    def test_v2_policy_preserves_v1_and_freezes_matching_rule(self) -> None:
        root = Path(__file__).resolve().parents[1]
        policy = json.loads(
            (root / "registries/development/skills/development_latency_diagnostic_observability_v0_2.json").read_text()
        )
        self.assertEqual(policy["supersedes_policy_id"], "OVC.DEVOBS.LATENCY.20260813.v1")
        self.assertEqual(
            policy["legacy_v1_policy"],
            "PRESERVE_AS_VALID_HISTORICAL_DIAGNOSTIC_EVIDENCE_NO_REWRITE",
        )
        self.assertEqual(policy["difficulty_taxonomy"]["D5"], "NOVEL_BLOCKING")
        self.assertEqual(
            policy["comparison_doctrine"]["rule"],
            "COMPARE_ASSISTANT_CONFIGURATIONS_WITHIN_MATCHED_PRIMARY_STRATA_AND_REPORT_MIXED_STRATA_SEPARATELY",
        )
        self.assertEqual(
            policy["comparison_doctrine"]["model_reasoning_duration_policy_unchanged"],
            "UNAVAILABLE_UNLESS_EXPLICIT_MEASURED_PLATFORM_TELEMETRY",
        )
        self.assertEqual(policy["authority_effect"], "NONE")
        self.assertFalse(policy["new_operator_gate"])


if __name__ == "__main__":
    unittest.main()
