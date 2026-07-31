from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ovc.research_operations.pattern_discovery.full_month_mdr import (
    EXPECTED_SOURCE_END,
    EXPECTED_SOURCE_START,
    SOURCE_SLICE_ID,
    TARGET_END,
    TARGET_START,
    build_source_profile,
    classify_timestamp,
    derive_context_buffer,
    derive_source_window,
    iter_h1_transport_months,
    iter_m1_partition_days,
)


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr" / "PD_JUNE_FULL_MONTH_MDR_OPERATOR_AUTHORITY.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"
PLAN = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_v0_1.md"
CONTRACT = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_v0_1.md"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_full_month_mdr_v0_1.schema.json"


class PDJuneFullMonthMDRTests(unittest.TestCase):
    def test_context_buffer_and_source_window_are_exact(self) -> None:
        self.assertEqual(derive_context_buffer(), timedelta(hours=48))
        self.assertEqual(
            derive_source_window(),
            (EXPECTED_SOURCE_START, EXPECTED_SOURCE_END),
        )
        self.assertEqual(EXPECTED_SOURCE_START, datetime(2026, 5, 30, tzinfo=timezone.utc))
        self.assertEqual(EXPECTED_SOURCE_END, datetime(2026, 7, 3, tzinfo=timezone.utc))

    def test_whole_june_is_the_only_target_interval(self) -> None:
        self.assertEqual(TARGET_START, datetime(2026, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(TARGET_END, datetime(2026, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(
            classify_timestamp(datetime(2026, 5, 31, 23, 45, tzinfo=timezone.utc)),
            "CONTEXT_PRE_TARGET",
        )
        self.assertEqual(
            classify_timestamp(datetime(2026, 6, 1, tzinfo=timezone.utc)),
            "TARGET_JUNE",
        )
        self.assertEqual(
            classify_timestamp(datetime(2026, 6, 30, 23, 45, tzinfo=timezone.utc)),
            "TARGET_JUNE",
        )
        self.assertEqual(
            classify_timestamp(datetime(2026, 7, 1, tzinfo=timezone.utc)),
            "CONTEXT_POST_TARGET",
        )
        self.assertEqual(
            classify_timestamp(datetime(2026, 7, 3, tzinfo=timezone.utc)),
            "OUTSIDE_SOURCE",
        )

    def test_transport_partition_plan_spans_may_june_and_july(self) -> None:
        days = iter_m1_partition_days(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        months = iter_h1_transport_months(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        self.assertEqual(len(days), 34)
        self.assertEqual(days[0].strftime("%Y-%m-%d"), "2026-05-30")
        self.assertEqual(days[-1].strftime("%Y-%m-%d"), "2026-07-02")
        self.assertEqual([item.strftime("%Y-%m") for item in months], ["2026-05", "2026-06", "2026-07"])

    def test_source_profile_retains_non_release_and_ci_boundary(self) -> None:
        profile = build_source_profile()
        self.assertEqual(profile["source_slice_id"], SOURCE_SLICE_ID)
        self.assertEqual(profile["target_eligibility"], "TARGET_JUNE_ONLY")
        self.assertEqual(profile["m1_daily_partition_count_per_side"], 34)
        self.assertEqual(profile["h1_monthly_transport_count_per_side"], 3)
        self.assertEqual(profile["provider_execution_location"], "OPERATOR_LOCAL_ONLY")
        self.assertEqual(profile["provider_execution_in_ci"], "DENIED")
        self.assertEqual(profile["release_status"], "NOT_A_RELEASE")
        self.assertEqual(profile["selector_eligibility"], "NONE")
        self.assertEqual(profile["r2_publication"], "DENIED")
        self.assertEqual(profile["validation_consumption"], "DENIED")

    def test_operator_authority_and_programme_state_are_bound(self) -> None:
        for path in (AUTHORITY, STATE, PLAN, CONTRACT, SCHEMA):
            self.assertTrue(path.is_file(), path)
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        state = json.loads(STATE.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(authority["decision"], "PASS")
        self.assertEqual(authority["decision_authority"], "OPERATOR")
        self.assertEqual(
            authority["authority_delta"],
            "READ_ONLY_PROVIDER_INTAKE_REPLAY_AND_REVIEW_CONSTRUCTION_ONLY",
        )
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["packet_id"], "PD-JUNE-FM-00")
        self.assertEqual(state["next_packet"], "PD-JUNE-FM-WP1")
        self.assertEqual(state["next_packet_status"], "READY_AFTER_FM00_SQUASH_MERGE")
        self.assertEqual(state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(schema["properties"]["source_slice_id"]["const"], SOURCE_SLICE_ID)

    def test_plan_and_contract_prevent_calendar_boundary_censoring(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("whole of June 2026", plan)
        self.assertIn("May 30–31 and July 1–2 are context-only", plan)
        self.assertIn("Source-boundary insufficiency must be zero", plan)
        self.assertIn("SOURCE_BOUNDARY_INCOMPLETE", contract)
        self.assertIn("Provider execution is operator-local only", contract)
        self.assertIn("grants no formula, threshold, semantic", contract)


if __name__ == "__main__":
    unittest.main()
