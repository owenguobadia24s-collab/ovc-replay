from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WP4_BRANCH = "build/c2p2-wp4-event-ledger-projections"


class C2P2WP4FullPytestAssuranceTests(unittest.TestCase):
    """Run the pytest-native repository surface once on the exact WP4 PR head.

    The canonical unittest job does not install pytest. The existing
    pytest-unittest-parity job does, and executes every unittest-discovered
    file. On this bounded WP4 branch only, this bridge removes the legacy-only
    selector and launches one child `python -m pytest` process. The child flag
    prevents recursion when the full surface collects this file. After merge
    the branch predicate is false, so this assurance bridge is inert and grants
    no persistent CI or runtime authority.
    """

    def test_full_pytest_native_surface_on_exact_wp4_pr_head(self) -> None:
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
        self.assertTrue(expected_head, "OVC_LEASE_HEAD_SHA is required")
        actual_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(expected_head, actual_head)

        child_env = dict(os.environ)
        child_env.pop("OVC_PYTEST_LEGACY_ONLY", None)
        child_env["OVC_C2P2_FULL_PYTEST_CHILD"] = "1"
        child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        command = [sys.executable, "-m", "pytest", "-q", "-ra"]
        started_ns = time.monotonic_ns()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=child_env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        duration_ms = (time.monotonic_ns() - started_ns) // 1_000_000
        print(completed.stdout, end="")
        print(
            "OVC_C2P2_FULL_PYTEST_RECEIPT "
            + json.dumps(
                {
                    "schema": "ovc-c2p2-full-pytest-receipt/v1",
                    "packet_id": "C2P2-WP4",
                    "gate_id": "C2P2-G4",
                    "head_sha": actual_head,
                    "command": command,
                    "duration_ms": duration_ms,
                    "exit_code": completed.returncode,
                    "legacy_only_selector_removed": True,
                    "plugin_autoload_disabled": True,
                },
                sort_keys=True,
            )
        )
        self.assertEqual(completed.returncode, 0, completed.stdout[-12000:])


if __name__ == "__main__":
    unittest.main()
