from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ovc.opt_b.c2_vnext.observation import (
    ClosureInterval,
    InstrumentCalendar,
    LatticeProfile,
    ObservationContractError,
    alternative_lattices,
    bind_evidence,
    build_legacy_crosswalk,
    build_population,
    default_gbpusd_calendar,
    enumerate_slots,
    project_lattice,
)

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[4]


def evidence(start: str, end: str, side: str, **extra):
    return {
        "interval_start": start,
        "interval_end": end,
        "side": side,
        "source_record_id": f"SRC:{side}:{start}",
        "opt_a_release_id": "OPT-A.SYNTHETIC.v1",
        "opt_a_record_id": f"A:{side}:{start}",
        "c1_release_id": "C1.SYNTHETIC.v1",
        "c1_record_id": f"C1:{side}:{start}",
        **extra,
    }


class ObservationFoundationTests(unittest.TestCase):
    def setUp(self):
        self.calendar = default_gbpusd_calendar()

    def test_every_expected_slot_is_accounted_once_for_bid_and_ask(self):
        rows = []
        for start, end in (
            ("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z"),
            ("2026-01-05T00:15:00Z", "2026-01-05T00:30:00Z"),
        ):
            rows.extend([evidence(start, end, "BID"), evidence(start, end, "ASK")])
        ledger = build_population(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:30:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=rows,
        )
        self.assertEqual(4, ledger["expected_slot_count"])
        self.assertEqual(4, ledger["observation_count"])
        self.assertEqual(4, ledger["unique_slot_count"])
        self.assertEqual({"PRESENT_COMPLETE": 4}, ledger["evidence_counts"])
        self.assertEqual({"CONTIGUOUS": 2, "SEGMENT_START": 2}, ledger["continuity_counts"])
        self.assertEqual({"ASK", "BID"}, {x["side"] for x in ledger["observations"]})
        for item in ledger["observations"]:
            self.assertEqual(item["interval_end"], item["first_valid_time"])
            self.assertTrue(item["projection_eligibility"]["eligible"])
            self.assertEqual("NONE", item["authority"]["active_selector"])

    def test_gap_incomplete_corruption_unknown_and_partition_are_distinct(self):
        slots = enumerate_slots(
            "2026-01-05T00:00:00Z",
            "2026-01-05T01:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            sides=("BID",),
        )
        rows = [
            evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "BID"),
            evidence("2026-01-05T00:30:00Z", "2026-01-05T00:45:00Z", "BID", complete=False),
            evidence("2026-01-05T00:45:00Z", "2026-01-05T01:00:00Z", "BID", corrupt=True),
            evidence("2026-01-05T01:00:00Z", "2026-01-05T01:15:00Z", "BID"),
        ]
        unknown_slot = next(x["slot_id"] for x in slots if x["interval_start"] == "2026-01-05T00:15:00Z")
        ledger = build_population(
            "2026-01-05T00:00:00Z",
            "2026-01-05T01:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=rows,
            sides=("BID",),
            absence_classes={unknown_slot: "UNKNOWN"},
            partition_boundary_starts=("2026-01-05T01:00:00Z",),
        )
        by_start = {x["interval_start"]: x for x in ledger["observations"]}
        self.assertEqual("SEGMENT_START", by_start["2026-01-05T00:00:00Z"]["continuity"]["status"])
        self.assertEqual("UNKNOWN_BREAK", by_start["2026-01-05T00:15:00Z"]["continuity"]["status"])
        self.assertEqual("GAP_RESET", by_start["2026-01-05T00:30:00Z"]["continuity"]["status"])
        self.assertEqual("GAP_RESET", by_start["2026-01-05T00:45:00Z"]["continuity"]["status"])
        self.assertEqual("PARTITION_BOUNDARY", by_start["2026-01-05T01:00:00Z"]["continuity"]["status"])
        self.assertEqual(
            {"CORRUPT": 1, "PRESENT_COMPLETE": 2, "PRESENT_INCOMPLETE": 1, "UNKNOWN_ABSENCE": 1},
            ledger["evidence_counts"],
        )

    def test_weekly_closure_is_calendar_classified_and_never_inferred_from_absence(self):
        winter_closed = self.calendar.classify(
            datetime(2026, 1, 2, 22, 0, tzinfo=UTC),
            datetime(2026, 1, 2, 22, 15, tzinfo=UTC),
        )
        winter_open = self.calendar.classify(
            datetime(2026, 1, 2, 21, 45, tzinfo=UTC),
            datetime(2026, 1, 2, 22, 0, tzinfo=UTC),
        )
        summer_closed = self.calendar.classify(
            datetime(2026, 3, 13, 21, 0, tzinfo=UTC),
            datetime(2026, 3, 13, 21, 15, tzinfo=UTC),
        )
        self.assertEqual("SCHEDULED_CLOSURE", winter_closed["status"])
        self.assertEqual("EXPECTED_EVIDENCE", winter_open["status"])
        self.assertEqual("SCHEDULED_CLOSURE", summer_closed["status"])
        open_missing = build_population(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=[],
            sides=("BID",),
        )["observations"][0]
        self.assertEqual("EXPECTED_EVIDENCE", open_missing["expectation"]["status"])
        self.assertEqual("ABSENT", open_missing["evidence"]["status"])
        self.assertEqual("GAP_RESET", open_missing["continuity"]["status"])

    def test_closure_observation_is_nullable_and_evidence_during_closure_is_corrupt(self):
        no_row = build_population(
            "2026-01-02T22:00:00Z",
            "2026-01-02T22:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=[],
            sides=("BID",),
        )["observations"][0]
        self.assertEqual("SCHEDULED_CLOSURE", no_row["expectation"]["status"])
        self.assertEqual("NOT_EXPECTED", no_row["evidence"]["status"])
        self.assertEqual("CLOSURE_BOUNDARY", no_row["continuity"]["status"])
        with_row = build_population(
            "2026-01-02T22:00:00Z",
            "2026-01-02T22:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=[evidence("2026-01-02T22:00:00Z", "2026-01-02T22:15:00Z", "BID")],
            sides=("BID",),
        )["observations"][0]
        self.assertEqual("CORRUPT", with_row["evidence"]["status"])
        self.assertFalse(with_row["projection_eligibility"]["eligible"])

    def test_exceptional_closure_is_source_referenced_not_provider_inferred(self):
        calendar = InstrumentCalendar(
            calendar_id="OVC.CALENDAR.GBPUSD.SYNTHETIC.v1",
            instrument="GBPUSD",
            timezone_name="America/New_York",
            effective_start=datetime(2026, 1, 1, tzinfo=UTC),
            effective_end=datetime(2027, 1, 1, tzinfo=UTC),
            exceptional_closures=(
                ClosureInterval(
                    datetime(2026, 1, 7, 12, 0, tzinfo=UTC),
                    datetime(2026, 1, 7, 13, 0, tzinfo=UTC),
                    "CLOSURE.SYNTHETIC.001",
                    source_ref="OVC_FIXTURE_CALENDAR",
                ),
            ),
            source_refs=("OVC_FIXTURE_POLICY",),
        )
        item = calendar.classify(
            datetime(2026, 1, 7, 12, 15, tzinfo=UTC),
            datetime(2026, 1, 7, 12, 30, tzinfo=UTC),
        )
        self.assertEqual("EXCEPTIONAL_CLOSURE", item["status"])
        self.assertEqual("CLOSURE.SYNTHETIC.001", item["closure_id"])
        self.assertIn("OVC_FIXTURE_CALENDAR", item["source_refs"])

    def test_alternative_lattice_references_same_observations_without_copy(self):
        rows = [
            evidence("2026-01-05T01:00:00Z", "2026-01-05T01:15:00Z", "BID"),
            evidence("2026-01-05T01:15:00Z", "2026-01-05T01:30:00Z", "BID"),
        ]
        ledger = build_population(
            "2026-01-05T01:00:00Z",
            "2026-01-05T01:30:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=rows,
            sides=("BID",),
        )
        alt = project_lattice(ledger["observations"], alternative_lattices()[0])
        self.assertEqual(
            {x["observation_id"] for x in ledger["observations"]},
            {x["observation_id"] for x in alt},
        )
        self.assertTrue(all(x["maturity"] == "SHADOW_EXPERIMENT" for x in alt))
        self.assertTrue(all("evidence" not in x for x in alt))

    def test_bid_and_ask_have_distinct_observation_identity_and_no_cross_side_merge(self):
        rows = [
            evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "BID"),
            evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "ASK"),
        ]
        ledger = build_population(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=rows,
        )
        self.assertEqual(2, len({x["observation_id"] for x in ledger["observations"]}))
        self.assertEqual(2, len({x["slot_id"] for x in ledger["observations"]}))

    def test_future_or_parent_fields_are_rejected(self):
        slots = enumerate_slots(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            sides=("BID",),
        )
        row = evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "BID", parent_id="PARENT")
        with self.assertRaisesRegex(ObservationContractError, "PROHIBITED_CAUSAL_KEY"):
            bind_evidence(slots, [row])

    def test_duplicate_and_unexpected_evidence_fail_closed(self):
        slots = enumerate_slots(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            sides=("BID",),
        )
        row = evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "BID")
        with self.assertRaisesRegex(ObservationContractError, "DUPLICATE_EVIDENCE"):
            bind_evidence(slots, [row, row])
        unexpected = evidence("2026-01-05T00:15:00Z", "2026-01-05T00:30:00Z", "BID")
        with self.assertRaisesRegex(ObservationContractError, "UNEXPECTED_EVIDENCE_INTERVAL"):
            bind_evidence(slots, [unexpected])

    def test_legacy_crosswalk_is_deterministic_non_mutating_and_exact(self):
        rows = [evidence("2026-01-05T00:00:00Z", "2026-01-05T00:15:00Z", "BID")]
        observations = build_population(
            "2026-01-05T00:00:00Z",
            "2026-01-05T00:15:00Z",
            instrument="GBPUSD",
            calendar=self.calendar,
            evidence_rows=rows,
            sides=("BID",),
        )["observations"]
        legacy = [
            {
                "legacy_interval_id": "LEGACY.1",
                "instrument": "GBPUSD",
                "side": "BID",
                "interval_start": "2026-01-05T00:00:00Z",
                "interval_end": "2026-01-05T00:15:00Z",
            },
            {
                "legacy_interval_id": "LEGACY.2",
                "instrument": "GBPUSD",
                "side": "ASK",
                "interval_start": "2026-01-05T00:00:00Z",
                "interval_end": "2026-01-05T00:15:00Z",
            },
        ]
        before = copy.deepcopy(legacy)
        first = build_legacy_crosswalk(legacy, observations)
        second = build_legacy_crosswalk(list(reversed(legacy)), observations)
        self.assertEqual(legacy, before)
        self.assertEqual(first, second)
        self.assertEqual("MATCHED_EXACT_INTERVAL_SIDE", first[0]["match_status"])
        self.assertEqual("UNMATCHED", first[1]["match_status"])
        self.assertTrue(all(not item["legacy_mutated"] for item in first))

    def test_repository_contract_schema_registry_and_fixture_are_complete(self):
        contract = (ROOT / "contracts/opt_b/c2/C2_OBSERVATION_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for decision in ("P1-D1", "P1-D2", "P1-D3", "P1-D4", "P1-D5", "P1-D6", "P1-D7", "P1-Q1", "P1-Q2"):
            self.assertIn(decision, contract)
        self.assertIn("Event-relative windows are downstream horizon memberships", contract)
        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_OBSERVATION_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertIn("c2_observation_vnext_r1", schema["schemas"])
        self.assertFalse(schema["schemas"]["c2_observation_vnext_r1"]["additionalProperties"])
        self.assertIn("parent_id", schema["prohibited_fields"])
        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_OBSERVATION_FOUNDATION_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual("INTERVAL_END", registry["identity"]["first_valid_rule"])
        self.assertFalse(registry["identity"]["event_relative_is_base_observation"])
        self.assertTrue(all(not item["active"] for item in registry["lattices"]))
        self.assertEqual("NONE", registry["authority"]["active_selector"])
        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/observation_foundation_cases_v0_1.json").read_text(encoding="utf-8"))
        self.assertTrue(fixture["fixture_only"])
        self.assertFalse(fixture["market_data"])
        expected = {"COMPLETE_BID_ASK", "PROVIDER_GAP", "INCOMPLETE", "CORRUPTION", "UNKNOWN_ABSENCE", "WEEKLY_CLOSURE_WINTER", "WEEKLY_CLOSURE_DST", "EXCEPTIONAL_CLOSURE", "PARTITION_BOUNDARY", "MULTI_LATTICE", "SLICE_BOUNDARY"}
        self.assertEqual(expected, {item["case_id"] for item in fixture["cases"]})

    def test_lattice_activation_is_denied(self):
        with self.assertRaisesRegex(ObservationContractError, "LATTICE_ACTIVATION_DENIED"):
            LatticeProfile("LATTICE.BAD", 120, 0, "SHADOW_EXPERIMENT", active=True)


if __name__ == "__main__":
    unittest.main()
