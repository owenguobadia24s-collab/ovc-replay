from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import unittest

from ovc.development.diagnostic_observability import DevelopmentTrace, ingest_github_workflow_jobs, observe_subprocess, summarize_trace


class FakeClock:
    def __init__(self, start: str = "2026-08-13T17:00:00Z") -> None:
        self.now = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(timezone.utc)
        self.ns = 0

    def utc_now(self) -> str:
        return self.now.isoformat(timespec="microseconds").replace("+00:00", "Z")

    def clock_ns(self) -> int:
        return self.ns

    def advance_ms(self, milliseconds: int) -> None:
        self.ns += milliseconds * 1_000_000
        self.now += timedelta(milliseconds=milliseconds)


class DevelopmentObservabilityTests(unittest.TestCase):
    def test_measured_span_and_unobserved_wall(self) -> None:
        clock = FakeClock()
        trace = DevelopmentTrace(run_id="RUN-1", programme_id="P", packet_id="WP", clock_ns=clock.clock_ns, utc_now=clock.utc_now)
        token = trace.start_span(category="REPOSITORY_INSPECTION", operation="preflight", source="DSAI")
        clock.advance_ms(250)
        trace.finish_span(token)
        clock.advance_ms(750)
        summary = trace.finish_run()
        self.assertEqual(summary["total_wall_ms"], 1000)
        self.assertEqual(summary["observed_union_ms"], 250)
        self.assertEqual(summary["unobserved_wall_ms"], 750)
        self.assertEqual(summary["latency_decomposition"]["MODEL_REASONING"]["evidence_class"], "UNAVAILABLE")

    def test_overlap_is_union_not_sum(self) -> None:
        events = [
            {"category": "REMOTE_CI_EXECUTION", "activity_class": "WAIT", "started_at_utc": "2026-08-13T17:00:00Z", "completed_at_utc": "2026-08-13T17:00:10Z"},
            {"category": "EVIDENCE_COLLECTION", "activity_class": "ACTIVE", "started_at_utc": "2026-08-13T17:00:03Z", "completed_at_utc": "2026-08-13T17:00:07Z"}
        ]
        summary = summarize_trace(run_id="RUN-2", programme_id=None, packet_id=None, started_at_utc="2026-08-13T17:00:00Z", completed_at_utc="2026-08-13T17:00:10Z", total_wall_ms=10_000, events=events)
        self.assertEqual(summary["observed_union_ms"], 10_000)
        self.assertEqual(summary["unobserved_wall_ms"], 0)
        self.assertEqual(summary["throughput"]["active_execution_ms"], 4000)
        self.assertEqual(summary["throughput"]["external_wait_ms"], 10_000)

    def test_model_reasoning_cannot_be_inferred(self) -> None:
        clock = FakeClock()
        trace = DevelopmentTrace(run_id="RUN-3", clock_ns=clock.clock_ns, utc_now=clock.utc_now)
        with self.assertRaisesRegex(ValueError, "MODEL_REASONING"):
            trace.start_span(category="MODEL_REASONING", operation="guess", source="CHAT")

    def test_subprocess_wrapper_measures_without_authorizing(self) -> None:
        clock = FakeClock()
        trace = DevelopmentTrace(run_id="RUN-4", clock_ns=clock.clock_ns, utc_now=clock.utc_now)
        def fake_runner(command, **kwargs):
            clock.advance_ms(125)
            return subprocess.CompletedProcess(command, 0)
        result = observe_subprocess(trace, ["python", "-m", "unittest"], category="LOCAL_TEST_ASSURANCE", runner=fake_runner)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(trace.events[0]["duration_ms"], 125)
        self.assertEqual(trace.events[0]["authority_effect"], "NONE")

    def test_github_jobs_queue_and_execution_are_ingested(self) -> None:
        trace = DevelopmentTrace(run_id="RUN-5", started_at_utc="2026-08-13T17:00:00Z")
        events = ingest_github_workflow_jobs(trace, workflow_run={"id": 10, "name": "tests"}, jobs=[{
            "id": 11, "name": "repository-suite", "created_at": "2026-08-13T17:00:01Z",
            "started_at": "2026-08-13T17:00:03Z", "completed_at": "2026-08-13T17:00:08Z", "conclusion": "success"
        }])
        self.assertEqual([event["category"] for event in events], ["REMOTE_CI_QUEUE", "REMOTE_CI_EXECUTION"])
        self.assertEqual(events[0]["duration_ms"], 2000)
        self.assertEqual(events[1]["duration_ms"], 5000)

    def test_policy_is_diagnostic_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / "registries/development/skills/development_latency_diagnostic_observability_v0_1.json").read_text())
        self.assertEqual(policy["receipt_class"], "TEMPORARY_DIAGNOSTIC_OBSERVABILITY")
        self.assertEqual(policy["authority_effect"], "NONE")
        self.assertTrue(policy["observability_only"])
        self.assertFalse(policy["governance_expansion"])
        self.assertFalse(policy["new_operator_gate"])
        self.assertEqual(policy["merge_authority"], "NONE")
        self.assertEqual(policy["measurement_contract"]["model_reasoning"], "UNAVAILABLE_UNLESS_EXPLICIT_MEASURED_PLATFORM_TELEMETRY")


if __name__ == "__main__":
    unittest.main()
