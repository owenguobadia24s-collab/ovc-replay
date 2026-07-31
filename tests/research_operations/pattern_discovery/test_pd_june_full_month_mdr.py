from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ovc.research_operations.pattern_discovery.full_month_mdr import (
    EXPECTED_SOURCE_END,
    EXPECTED_SOURCE_START,
    PLAN_AMENDMENT_ID,
    SOURCE_SLICE_ID,
    TARGET_END,
    TARGET_START,
    build_source_profile,
    classify_timestamp,
    derive_context_buffer,
    derive_source_window,
    iter_h1_transport_months,
    iter_m1_partition_days,
    iter_native_h1_transport_months,
)


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr"
AUTHORITY = BASE / "PD_JUNE_FULL_MONTH_MDR_OPERATOR_AUTHORITY.json"
AMENDMENT = BASE / "PD_JUNE_FULL_MONTH_MDR_A1_OPERATOR_DECISION.json"
INCIDENT = BASE / "PD_JUNE_FULL_MONTH_MDR_A1_JULY_H1_PROVIDER_INCIDENT.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"
PLAN = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_v0_1.md"
PLAN_A1 = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_A1_JULY_NATIVE_H1_WAIVER.md"
CONTRACT = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_v0_1.md"
CONTRACT_A1 = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_A1.md"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_full_month_mdr_v0_1.schema.json"
SCHEMA_A1 = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_full_month_mdr_a1_v0_1.schema.json"


class PDJuneFullMonthMDRTests(unittest.TestCase):
    def test_context_buffer_and_source_window_are_exact(self) -> None:
        self.assertEqual(derive_context_buffer(), timedelta(hours=48))
        self.assertEqual(derive_source_window(), (EXPECTED_SOURCE_START, EXPECTED_SOURCE_END))
        self.assertEqual(EXPECTED_SOURCE_START, datetime(2026, 5, 30, tzinfo=timezone.utc))
        self.assertEqual(EXPECTED_SOURCE_END, datetime(2026, 7, 3, tzinfo=timezone.utc))

    def test_whole_june_is_the_only_target_interval(self) -> None:
        self.assertEqual(TARGET_START, datetime(2026, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(TARGET_END, datetime(2026, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(classify_timestamp(datetime(2026, 5, 31, 23, 45, tzinfo=timezone.utc)), "CONTEXT_PRE_TARGET")
        self.assertEqual(classify_timestamp(datetime(2026, 6, 1, tzinfo=timezone.utc)), "TARGET_JUNE")
        self.assertEqual(classify_timestamp(datetime(2026, 6, 30, 23, 45, tzinfo=timezone.utc)), "TARGET_JUNE")
        self.assertEqual(classify_timestamp(datetime(2026, 7, 1, tzinfo=timezone.utc)), "CONTEXT_POST_TARGET")
        self.assertEqual(classify_timestamp(datetime(2026, 7, 3, tzinfo=timezone.utc)), "OUTSIDE_SOURCE")

    def test_transport_plan_keeps_july_m1_but_waives_native_july_h1(self) -> None:
        days = iter_m1_partition_days(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        all_months = iter_h1_transport_months(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        native_months = iter_native_h1_transport_months(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        self.assertEqual(len(days), 34)
        self.assertEqual(days[0].strftime("%Y-%m-%d"), "2026-05-30")
        self.assertEqual(days[-1].strftime("%Y-%m-%d"), "2026-07-02")
        self.assertEqual([item.strftime("%Y-%m") for item in all_months], ["2026-05", "2026-06", "2026-07"])
        self.assertEqual([item.strftime("%Y-%m") for item in native_months], ["2026-05", "2026-06"])

    def test_source_profile_retains_context_and_records_a1(self) -> None:
        profile = build_source_profile()
        self.assertEqual(profile["source_slice_id"], SOURCE_SLICE_ID)
        self.assertEqual(profile["plan_amendment"], PLAN_AMENDMENT_ID)
        self.assertEqual(profile["target_eligibility"], "TARGET_JUNE_ONLY")
        self.assertEqual(profile["m1_daily_partition_count_per_side"], 34)
        self.assertEqual(profile["h1_monthly_transport_count_per_side"], 2)
        self.assertEqual(profile["h1_monthly_transport_months_utc"], ["2026-05", "2026-06"])
        self.assertEqual(profile["native_july_h1_transport"], "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE")
        self.assertEqual(profile["post_target_h1_context"], "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS")
        self.assertEqual(profile["provider_execution_location"], "OPERATOR_LOCAL_ONLY")
        self.assertEqual(profile["provider_execution_in_ci"], "DENIED")
        self.assertEqual(profile["release_status"], "NOT_A_RELEASE")
        self.assertEqual(profile["selector_eligibility"], "NONE")
        self.assertEqual(profile["r2_publication"], "DENIED")
        self.assertEqual(profile["validation_consumption"], "DENIED")

    def test_operator_authority_amendment_and_programme_state_are_bound(self) -> None:
        for path in (AUTHORITY, AMENDMENT, INCIDENT, STATE, PLAN, PLAN_A1, CONTRACT, CONTRACT_A1, SCHEMA, SCHEMA_A1):
            self.assertTrue(path.is_file(), path)
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
        state = json.loads(STATE.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(authority["decision"], "PASS")
        self.assertEqual(authority["decision_authority"], "OPERATOR")
        self.assertEqual(amendment["decision"], "PASS")
        self.assertEqual(amendment["decision_authority"], "OPERATOR")
        self.assertEqual(amendment["authority_delta"], "WAIVE_NATIVE_JULY_H1_IMPORT_DERIVE_POST_TARGET_H1_FROM_M1")
        self.assertEqual(amendment["next_packet"], "PD-JUNE-FM-WP1")
        self.assertEqual(state["status"], "GATE_READY")
        self.assertEqual(state["packet_id"], "PD-JUNE-FM-WP1")
        self.assertEqual(state["plan_amendment"], PLAN_AMENDMENT_ID)
        self.assertEqual(state["source_request_plan"], "GENERATED_72_PROVIDER_OBJECTS_68_M1_DAILY_4_H1_MONTHLY")
        self.assertEqual(state["native_july_h1_transport"], "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE")
        self.assertEqual(state["post_target_h1_context"], "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS")
        self.assertEqual(state["next_packet"], "PD-JUNE-FM-WP2")
        self.assertEqual(state["next_packet_status"], "BLOCKED_PENDING_FROZEN_LOCAL_SOURCE_SLICE_AND_COMPACT_RECEIPTS")
        self.assertEqual(state["provider_execution_location"], "OPERATOR_LOCAL_ONLY")
        self.assertEqual(state["provider_execution_in_ci"], "DENIED")
        self.assertEqual(state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(schema["properties"]["source_slice_id"]["const"], SOURCE_SLICE_ID)

    def test_base_and_amended_contracts_preserve_context(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        amendment = PLAN_A1.read_text(encoding="utf-8")
        contract = CONTRACT.read_text(encoding="utf-8")
        contract_a1 = CONTRACT_A1.read_text(encoding="utf-8")
        self.assertIn("whole of June 2026", plan)
        self.assertIn("May 30–31 and July 1–2 are context-only", plan)
        self.assertIn("Implementation Plan Amendment A1", amendment)
        self.assertIn("native-H1", amendment)
        self.assertIn("SOURCE_BOUNDARY_INCOMPLETE", contract)
        self.assertIn("M1-derived H1", contract_a1)
        self.assertIn("Provider execution is operator-local only", contract)
        self.assertIn("grants no formula, threshold, semantic", contract)


if __name__ == "__main__":
    unittest.main()
