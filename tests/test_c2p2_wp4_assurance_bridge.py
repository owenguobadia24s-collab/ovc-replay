from __future__ import annotations

import io
import os
import time
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
C2P_TEST_ROOT = ROOT / "tests/opt_b/c2p/v0_2"
WP4_BRANCH = "build/c2p2-wp4-event-ledger-projections"


class _PytestReceipt:
    def __init__(self) -> None:
        self.collected = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def pytest_collection_finish(self, session) -> None:
        self.collected = len(session.items)

    def pytest_runtest_logreport(self, report) -> None:
        if report.when != "call":
            return
        if report.passed:
            self.passed += 1
        elif report.failed:
            self.failed += 1
        elif report.skipped:
            self.skipped += 1


def _run_unittest_pattern(pattern: str) -> tuple[int, unittest.TestResult, str, int]:
    loader = unittest.TestLoader()
    suite = loader.discover(str(C2P_TEST_ROOT), pattern=pattern)
    count = suite.countTestCases()
    stream = io.StringIO()
    started_ns = time.monotonic_ns()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration_ms = (time.monotonic_ns() - started_ns) // 1_000_000
    return count, result, stream.getvalue(), duration_ms


class C2P2WP4AssuranceBridgeTests(unittest.TestCase):
    """Bind explicit packet tests to the existing exact-head parity job."""

    def test_exact_head_targeted_prior_and_full_pytest_surfaces(self) -> None:
        if os.environ.get("OVC_C2P2_FULL_PYTEST_CHILD") == "1":
            return
        if os.environ.get("OVC_PYTEST_LEGACY_ONLY") != "1":
            return
        if os.environ.get("GITHUB_ACTIONS") != "true":
            return
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
            return
        if os.environ.get("GITHUB_HEAD_REF") != WP4_BRANCH:
            return

        expected_head = os.environ.get("OVC_LEASE_HEAD_SHA")
        self.assertTrue(expected_head)
        actual_head = (ROOT / ".git/HEAD").read_text(encoding="utf-8").strip()
        self.assertEqual(expected_head, actual_head)

        targeted_count, targeted_result, targeted_output, _ = _run_unittest_pattern(
            "test_c2p2_wp4_event_ledger_projection.py"
        )
        self.assertEqual(targeted_count, 11)
        self.assertTrue(targeted_result.wasSuccessful(), targeted_output[-12000:])

        prior_count, prior_result, prior_output, _ = _run_unittest_pattern(
            "test_c2p2_wp[0-3]*.py"
        )
        self.assertGreater(prior_count, 0)
        self.assertTrue(prior_result.wasSuccessful(), prior_output[-12000:])

        previous_legacy_only = os.environ.pop("OVC_PYTEST_LEGACY_ONLY", None)
        os.environ["OVC_C2P2_FULL_PYTEST_CHILD"] = "1"
        receipt = _PytestReceipt()
        started_ns = time.monotonic_ns()
        try:
            exit_code = pytest.main(["tests", "-q", "-ra"], plugins=[receipt])
        finally:
            os.environ.pop("OVC_C2P2_FULL_PYTEST_CHILD", None)
            if previous_legacy_only is not None:
                os.environ["OVC_PYTEST_LEGACY_ONLY"] = previous_legacy_only
        duration_ms = (time.monotonic_ns() - started_ns) // 1_000_000

        self.assertEqual(int(exit_code), 0)
        self.assertGreater(receipt.collected, 0)
        self.assertEqual(receipt.failed, 0)
        self.assertEqual(receipt.passed + receipt.skipped, receipt.collected)
        self.assertGreater(duration_ms, 0)


if __name__ == "__main__":
    unittest.main()
