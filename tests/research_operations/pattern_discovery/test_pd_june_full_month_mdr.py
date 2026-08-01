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
from ovc.research_operations.prospective_source import dukascopy_full_month_mdr_a2

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr"
AUTHORITY = BASE / "PD_JUNE_FULL_MONTH_MDR_OPERATOR_AUTHORITY.json"
A1 = BASE / "PD_JUNE_FULL_MONTH_MDR_A1_OPERATOR_DECISION.json"
A2 = BASE / "PD_JUNE_FULL_MONTH_MDR_A2_OPERATOR_DECISION.json"
DIAGNOSTIC_A2 = BASE / "PD_JUNE_FULL_MONTH_MDR_A2_SOURCE_DIAGNOSTIC_SUMMARY.json"
SOURCE_ACCEPTANCE = BASE / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_INDEX.json"
SOURCE_RECEIPT = BASE / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_MERGE_RECEIPT.json"
TOOLING_RECEIPT = BASE / "PD_JUNE_FULL_MONTH_MDR_WP2_TOOLING_MERGE_RECEIPT.json"
REPLAY_RECEIPT = BASE / "wp2-replay" / "PD_JUNE_FULL_MONTH_MDR_WP2_REPLAY_MERGE_RECEIPT.json"
WP3_INDEX = BASE / "wp3-review" / "PD_JUNE_FM_WP3_EXTERNAL_ARTIFACT_INDEX.json"
WP3_QA = BASE / "wp3-review" / "PD_JUNE_FM_WP3_SELECTION_AND_COMPLETENESS_QA.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"
PLAN = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_v0_1.md"
PLAN_A1 = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_A1_JULY_NATIVE_H1_WAIVER.md"
PLAN_A2 = ROOT / "plans" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_IMPLEMENTATION_PLAN_A2_PAIRED_SPARSE_M1_ACCEPTANCE.md"
CONTRACT = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_v0_1.md"
CONTRACT_A1 = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_A1.md"
CONTRACT_A2 = ROOT / "contracts" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_A2.md"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_full_month_mdr_v0_1.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PDJuneFullMonthMDRTests(unittest.TestCase):
    def test_context_target_and_source_window_are_exact(self) -> None:
        self.assertEqual(derive_context_buffer(), timedelta(hours=48))
        self.assertEqual(derive_source_window(), (EXPECTED_SOURCE_START, EXPECTED_SOURCE_END))
        self.assertEqual(EXPECTED_SOURCE_START, datetime(2026, 5, 30, tzinfo=timezone.utc))
        self.assertEqual(EXPECTED_SOURCE_END, datetime(2026, 7, 3, tzinfo=timezone.utc))
        self.assertEqual(TARGET_START, datetime(2026, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(TARGET_END, datetime(2026, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(classify_timestamp(datetime(2026, 5, 31, 23, 45, tzinfo=timezone.utc)), "CONTEXT_PRE_TARGET")
        self.assertEqual(classify_timestamp(datetime(2026, 6, 1, tzinfo=timezone.utc)), "TARGET_JUNE")
        self.assertEqual(classify_timestamp(datetime(2026, 6, 30, 23, 45, tzinfo=timezone.utc)), "TARGET_JUNE")
        self.assertEqual(classify_timestamp(datetime(2026, 7, 1, tzinfo=timezone.utc)), "CONTEXT_POST_TARGET")
        self.assertEqual(classify_timestamp(datetime(2026, 7, 3, tzinfo=timezone.utc)), "OUTSIDE_SOURCE")

    def test_transport_plan_keeps_july_m1_and_waives_native_july_h1(self) -> None:
        days = iter_m1_partition_days(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        all_months = iter_h1_transport_months(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        native_months = iter_native_h1_transport_months(EXPECTED_SOURCE_START, EXPECTED_SOURCE_END)
        self.assertEqual(len(days), 34)
        self.assertEqual(days[0].strftime("%Y-%m-%d"), "2026-05-30")
        self.assertEqual(days[-1].strftime("%Y-%m-%d"), "2026-07-02")
        self.assertEqual([item.strftime("%Y-%m") for item in all_months], ["2026-05", "2026-06", "2026-07"])
        self.assertEqual([item.strftime("%Y-%m") for item in native_months], ["2026-05", "2026-06"])
        profile = build_source_profile()
        self.assertEqual(profile["source_slice_id"], SOURCE_SLICE_ID)
        self.assertEqual(profile["plan_amendment"], PLAN_AMENDMENT_ID)
        self.assertEqual(profile["native_july_h1_transport"], "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE")
        self.assertEqual(profile["post_target_h1_context"], "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS")
        self.assertEqual(profile["provider_execution_in_ci"], "DENIED")
        self.assertEqual(profile["release_status"], "NOT_A_RELEASE")

    def test_operator_authority_and_prior_packet_receipts_remain_bound(self) -> None:
        for path in (AUTHORITY, A1, A2, DIAGNOSTIC_A2, SOURCE_ACCEPTANCE, SOURCE_RECEIPT, TOOLING_RECEIPT, REPLAY_RECEIPT):
            self.assertTrue(path.is_file(), path)
        authority = load(AUTHORITY)
        a1 = load(A1)
        a2 = load(A2)
        diagnostic = load(DIAGNOSTIC_A2)
        source = load(SOURCE_ACCEPTANCE)
        source_receipt = load(SOURCE_RECEIPT)
        tooling = load(TOOLING_RECEIPT)
        replay = load(REPLAY_RECEIPT)
        self.assertEqual(authority["decision"], "PASS")
        self.assertEqual(authority["decision_authority"], "OPERATOR")
        self.assertEqual(a1["decision"], "PASS")
        self.assertEqual(a1["authority_delta"], "WAIVE_NATIVE_JULY_H1_IMPORT_DERIVE_POST_TARGET_H1_FROM_M1")
        self.assertEqual(a2["decision"], "PASS")
        self.assertEqual(a2["authority_delta"], "ACCEPT_EXACTLY_PAIRED_PROVIDER_M1_ABSENCE_WITH_EXPLICIT_DOWNSTREAM_CENSORING")
        self.assertEqual(diagnostic["diagnostic_sha256"], "ddfc9672be23ac8a87101c2d34daa706b7f4793a6bc5c925e9c07713563fef99")
        self.assertEqual(source["manifest"]["logical_sha256"], "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3")
        self.assertEqual(source_receipt["merge_commit"], "39da5213ff3931cf9a22760a3ee3529d4fc43c30")
        self.assertEqual(tooling["merge_commit"], "b3ac2561aff225442465e6914a1e1e29adbfab62")
        self.assertEqual(replay["merge_commit"], "fedc20ab92f0465e5c84d7626f859866c9ad1f00")

    def test_wp3_programme_state_and_external_review_evidence_are_bound(self) -> None:
        state = load(STATE)
        index = load(WP3_INDEX)
        qa = load(WP3_QA)
        schema = load(SCHEMA)
        self.assertEqual(state["packet_id"], "PD-JUNE-FM-WP3")
        self.assertEqual(state["status"], "QA_REVIEW")
        self.assertEqual(state["plan_version"], "0.1+A1+A2")
        self.assertEqual(state["source_acceptance_merge_commit"], "39da5213ff3931cf9a22760a3ee3529d4fc43c30")
        self.assertEqual(state["tooling_merge_commit"], "b3ac2561aff225442465e6914a1e1e29adbfab62")
        self.assertEqual(state["acceptance_merge_commit"], "fedc20ab92f0465e5c84d7626f859866c9ad1f00")
        self.assertEqual(state["replay_status"], "PASS_ACCEPTED_FOR_WP3")
        self.assertEqual(state["source"]["source_run_id"], "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9")
        self.assertEqual(state["review"]["selected_card_count"], 40)
        self.assertEqual(state["review"]["review_card_presentation_omission_count"], 0)
        self.assertEqual(state["next_packet"], "PD-JUNE-FM-G2")
        self.assertEqual(state["next_packet_status"], "BLOCKED_PENDING_WP3_FINAL_HEAD_CI_AND_SQUASH_MERGE")
        self.assertEqual(state["next_packet_authority"], "OPERATOR_REQUIRED_BLINDED_REVIEW")
        self.assertEqual(index["reviewer_package"]["sha256"], "1b68c2c58e895c700152b697ceb1cdc1bf9cf5ef9807c9f69893512c0104bd46")
        self.assertEqual(index["sealed_evidence"]["answer_key_sha256"], "48ddb7ff6689c60ef4ce24703119f6557959828e886e02213ae1804c3001ed97")
        self.assertEqual(qa["selected_card_count"], 40)
        self.assertEqual(qa["source_completeness"]["source_boundary_insufficiency"], 0)
        self.assertEqual(qa["card_content"]["review_card_presentation_omission_count"], 0)
        self.assertEqual(state["release_status"], "NOT_A_RELEASE")
        self.assertEqual(state["selector_eligibility"], "NONE")
        self.assertEqual(state["r2_publication"], "DENIED")
        self.assertEqual(state["validation_consumption"], "DENIED")
        self.assertFalse(state["write_authority"])
        self.assertEqual(schema["properties"]["source_slice_id"]["const"], SOURCE_SLICE_ID)

    def test_contracts_preserve_context_and_authority(self) -> None:
        self.assertIn("whole of June 2026", PLAN.read_text(encoding="utf-8"))
        self.assertIn("Implementation Plan Amendment A1", PLAN_A1.read_text(encoding="utf-8"))
        self.assertIn("Paired Sparse M1 Acceptance", PLAN_A2.read_text(encoding="utf-8"))
        self.assertIn("SOURCE_BOUNDARY_INCOMPLETE", CONTRACT.read_text(encoding="utf-8"))
        self.assertIn("M1-derived H1", CONTRACT_A1.read_text(encoding="utf-8"))
        self.assertIn("Paired sparse M1 admissibility", CONTRACT_A2.read_text(encoding="utf-8"))
        profile = dukascopy_full_month_mdr_a2.source_profile()
        self.assertEqual(profile["plan_version"], "0.1+A1+A2")
        self.assertEqual(profile["downstream_incomplete_membership_policy"], "INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING")


if __name__ == "__main__":
    unittest.main()
