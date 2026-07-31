from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.prospective_source import full_month_mdr_replay as subject
from ovc.research_operations.prospective_source.models import ProspectiveBar


ROOT = Path(__file__).resolve().parents[3]


def bar(
    start: str,
    end: str,
    *,
    quality: str = "COMPLETE",
    clock: str = "15M",
) -> ProspectiveBar:
    complete = quality == "COMPLETE"
    return ProspectiveBar(
        bar_id=f"test:{start}",
        clock=clock,
        side="BID",
        start_utc=start,
        end_utc=end,
        open="1.25000" if complete else None,
        high="1.25100" if complete else None,
        low="1.24900" if complete else None,
        close="1.25050" if complete else None,
        volume="1" if complete else None,
        parent_source_object_ids=(f"parent:{start}",),
        quality_state=quality,
    )


class PDJuneFullMonthMDRWP2Tests(unittest.TestCase):
    def test_source_acceptance_index_is_exactly_bound(self) -> None:
        value = subject.load_source_acceptance_index(ROOT)
        self.assertEqual(value["source_slice_id"], subject.SLICE_ID)
        self.assertEqual(
            value["manifest"]["logical_sha256"],
            subject.SOURCE_MANIFEST_LOGICAL_SHA256,
        )
        self.assertEqual(value["acceptance"]["decision"], "PASS")

    def test_accepted_a2_manifest_separates_embedded_and_content_hashes(self) -> None:
        path = (
            ROOT
            / "fixtures"
            / "research_operations"
            / "prospective_source"
            / "pd_june_full_month_mdr_source_manifest_a2.json"
        )
        manifest = json.loads(path.read_text(encoding="utf-8"))
        embedded, content = subject.validate_source_manifest_hashes(manifest)
        self.assertEqual(
            embedded,
            subject.ACCEPTED_SOURCE_MANIFEST_EMBEDDED_LOGICAL_SHA256,
        )
        self.assertEqual(
            content,
            subject.ACCEPTED_SOURCE_MANIFEST_CONTENT_LOGICAL_SHA256,
        )
        self.assertNotEqual(embedded, content)

    def test_target_classification_is_exact(self) -> None:
        self.assertEqual(
            subject.classify_timestamp("2026-05-31T23:45:00Z"),
            "CONTEXT_PRE_TARGET",
        )
        self.assertEqual(
            subject.classify_timestamp("2026-06-01T00:00:00Z"),
            "TARGET_JUNE",
        )
        self.assertEqual(
            subject.classify_timestamp("2026-06-30T23:45:00Z"),
            "TARGET_JUNE",
        )
        self.assertEqual(
            subject.classify_timestamp("2026-07-01T00:00:00Z"),
            "CONTEXT_POST_TARGET",
        )
        self.assertEqual(
            subject.classify_timestamp("2026-07-03T00:00:00Z"),
            "OUTSIDE_SOURCE",
        )

    def test_expected_full_month_counts_are_frozen(self) -> None:
        self.assertEqual(
            subject.EXPECTED_COUNTS["15M"],
            {
                "total": 2316,
                "complete": 2231,
                "incomplete": 85,
                "target_total": 2112,
                "target_complete": 2036,
                "target_incomplete": 76,
            },
        )
        self.assertEqual(
            subject.EXPECTED_COUNTS["2H_A_L"],
            {
                "total": 294,
                "complete": 248,
                "incomplete": 46,
                "target_total": 268,
                "target_complete": 227,
                "target_incomplete": 41,
            },
        )
        self.assertEqual(subject.EXPECTED_C1_RECORDS, 4958)
        self.assertEqual(subject.EXPECTED_TARGET_C1_RECORDS, 4526)
        self.assertEqual(subject.EXPECTED_C2_STATES, 9420)
        self.assertEqual(subject.EXPECTED_TARGET_C2_STATES, 8598)

    def test_complete_segments_split_on_incomplete_and_time_gap(self) -> None:
        values = [
            bar("2026-06-01T00:00:00Z", "2026-06-01T00:15:00Z"),
            bar("2026-06-01T00:15:00Z", "2026-06-01T00:30:00Z"),
            bar(
                "2026-06-01T00:30:00Z",
                "2026-06-01T00:45:00Z",
                quality="QUARANTINED_INCOMPLETE_PARENT_SET",
            ),
            bar("2026-06-01T00:45:00Z", "2026-06-01T01:00:00Z"),
            bar("2026-06-01T01:15:00Z", "2026-06-01T01:30:00Z"),
        ]
        segments = subject.complete_segments(values)
        self.assertEqual([[item.start_utc for item in part] for part in segments], [
            ["2026-06-01T00:00:00Z", "2026-06-01T00:15:00Z"],
            ["2026-06-01T00:45:00Z"],
            ["2026-06-01T01:15:00Z"],
        ])

    def test_parent_event_resolver_invalidates_then_recovers(self) -> None:
        levels_a = ({"level_id": "A"},)
        levels_b = ({"level_id": "B"},)
        resolver = subject.ParentEventResolver(
            [
                ("2026-06-01T02:00:00Z", levels_a),
                ("2026-06-01T04:00:00Z", ()),
                ("2026-06-01T06:00:00Z", levels_b),
            ]
        )
        self.assertEqual(
            resolver({"close_time": "2026-06-01T02:15:00Z"}),
            levels_a,
        )
        self.assertEqual(
            resolver({"close_time": "2026-06-01T04:15:00Z"}),
            (),
        )
        self.assertEqual(
            resolver({"close_time": "2026-06-01T06:15:00Z"}),
            levels_b,
        )
        self.assertEqual(resolver.empty_resolutions, 1)

    def test_execute_denies_wrong_gate_and_ci_before_source_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as repository:
            with self.assertRaisesRegex(subject.ComputeError, "exact delegated authority"):
                subject.execute(
                    Path(repository),
                    authority_gate="WRONG",
                    environ={},
                )
            with self.assertRaisesRegex(subject.ComputeError, "prohibited in CI"):
                subject.execute(
                    Path(repository),
                    authority_gate=subject.AUTHORITY_GATE,
                    environ={"CI": "true"},
                )

    def test_retained_authority_is_non_activating(self) -> None:
        self.assertEqual(subject.OPERATION_MODE, "TIME_GATED_REPLAY")
        self.assertEqual(subject.DERIVED_AUTHORITY, "TIME_GATED_REPLAY_DERIVED")
        self.assertEqual(subject.AUTHORITY_GATE, "PD-JUNE-FM-G1")
        self.assertEqual(subject.EXPANDED_OUTPUT_LIMIT, 512 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
