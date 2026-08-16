from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"


class SIQLiveBaseGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_same_pr_concurrency_is_scoped_to_exact_head_generation(self) -> None:
        self.assertIn(
            "group: ovc-pr-${{ github.event.pull_request.number || github.ref }}-${{ github.event.pull_request.head.sha || github.sha }}",
            self.text,
        )

    def test_event_base_is_provenance_not_final_readiness_authority(self) -> None:
        self.assertIn("event base ${eventPr.base.sha} is provenance only", self.text)
        self.assertNotIn("currentMain !== pr.base.sha", self.text)
        self.assertNotIn("mainSnapshot !== pr.base.sha", self.text)
        self.assertNotIn("mainSnapshot !== readyBase ||", self.text)
        self.assertIn("github.rest.repos.compareCommits", self.text)
        self.assertIn("OVC_RECONCILE_REQUIRED", self.text)
        self.assertIn("OVC_READY_BASE_REFRESHED_BEFORE_FINAL_LEASE", self.text)

    def test_live_pr_head_is_rechecked_before_ready_and_final_pass(self) -> None:
        self.assertGreaterEqual(self.text.count("github.rest.pulls.get"), 5)
        self.assertGreaterEqual(self.text.count("OVC_SIQ_SUPERSEDED_EVENT_HEAD"), 4)

    def test_superseded_predecessor_generation_releases_lease(self) -> None:
        self.assertIn("terminal.data.head.sha !== leaseOwner.headSha", self.text)
        self.assertIn("OVC_FINAL_INTEGRATION_PREDECESSOR_SUPERSEDED", self.text)
        self.assertIn("emitPredecessorMetric('SUPERSEDED', leaseOwner)", self.text)

    def test_stable_main_fail_closed_guard_remains(self) -> None:
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.text)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_PASS", self.text)
        self.assertIn("cancel-in-progress: false", self.text)


if __name__ == "__main__":
    unittest.main()
