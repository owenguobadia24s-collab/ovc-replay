from __future__ import annotations

import unittest

from ovc.development.dsai3v_live_trace import (
    TRACE_SCOPE,
    build_observed_completion_trace,
)


class Dsai3vLiveTraceTests(unittest.TestCase):
    def test_observed_github_jobs_build_scoped_trace_without_inference(self) -> None:
        runs = (
            {"id": 1001, "name": "tests"},
            {"id": 1002, "name": "tiered"},
        )
        jobs = {
            1001: (
                {
                    "id": 2001,
                    "name": "repository suite",
                    "created_at": "2026-08-18T07:00:00Z",
                    "started_at": "2026-08-18T07:00:01Z",
                    "completed_at": "2026-08-18T07:00:05Z",
                    "conclusion": "success",
                },
            ),
            1002: (
                {
                    "id": 2002,
                    "name": "FINAL_HEAD profile",
                    "created_at": "2026-08-18T07:00:00.500000Z",
                    "started_at": "2026-08-18T07:00:02Z",
                    "completed_at": "2026-08-18T07:00:06Z",
                    "conclusion": "success",
                },
            ),
        }

        bundle = build_observed_completion_trace(
            programme_id="OVC-TEST",
            packet_id="TEST-PACKET",
            pr_number=42,
            head_sha="a" * 40,
            merged_at_utc="2026-08-18T07:00:08Z",
            workflow_runs=runs,
            jobs_by_run=jobs,
        )

        self.assertIsNotNone(bundle)
        assert bundle is not None
        summary = bundle["trace_summary"]
        self.assertEqual(summary["total_wall_ms"], 8000)
        self.assertEqual(summary["latency_decomposition"]["REMOTE_CI_QUEUE"]["evidence_class"], "MEASURED")
        self.assertEqual(summary["latency_decomposition"]["REMOTE_CI_EXECUTION"]["evidence_class"], "MEASURED")
        self.assertEqual(summary["latency_decomposition"]["LOCAL_TEST_ASSURANCE"]["evidence_class"], "UNAVAILABLE")
        self.assertEqual(summary["latency_decomposition"]["REMEDIATION_RETRY"]["evidence_class"], "UNAVAILABLE")
        self.assertEqual(summary["latency_decomposition"]["MODEL_REASONING"]["evidence_class"], "UNAVAILABLE")
        self.assertEqual(
            summary["latency_decomposition"]["MODEL_REASONING"]["reason"],
            "NO_EXPLICIT_PLATFORM_MODEL_TELEMETRY",
        )
        self.assertEqual(bundle["async_assurance_metrics"]["workflow_green_to_materialisation_ms"], 2000)
        self.assertGreater(len(bundle["trace_events"]), 0)
        self.assertTrue(summary["run_id"].startswith(f"DSAI3V:{TRACE_SCOPE}:PR42:"))
        self.assertEqual(bundle["authority_effect"], "NONE")
        self.assertEqual(
            bundle["evidence_rule"],
            "OBSERVED_GITHUB_TIMESTAMPS_ONLY_NO_CAUSAL_INFERENCE",
        )

    def test_no_observed_jobs_returns_none(self) -> None:
        self.assertIsNone(
            build_observed_completion_trace(
                programme_id="OVC-TEST",
                packet_id="TEST-PACKET",
                pr_number=42,
                head_sha="a" * 40,
                merged_at_utc="2026-08-18T07:00:08Z",
                workflow_runs=(),
                jobs_by_run={},
            )
        )

    def test_merge_before_assurance_start_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "physical merge precedes observed assurance start"):
            build_observed_completion_trace(
                programme_id="OVC-TEST",
                packet_id="TEST-PACKET",
                pr_number=42,
                head_sha="a" * 40,
                merged_at_utc="2026-08-18T06:59:59Z",
                workflow_runs=({"id": 1001, "name": "tests"},),
                jobs_by_run={
                    1001: (
                        {
                            "id": 2001,
                            "name": "repository suite",
                            "created_at": "2026-08-18T07:00:00Z",
                            "started_at": "2026-08-18T07:00:01Z",
                            "completed_at": "2026-08-18T07:00:05Z",
                            "conclusion": "success",
                        },
                    )
                },
            )


if __name__ == "__main__":
    unittest.main()
