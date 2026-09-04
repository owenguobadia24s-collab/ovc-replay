from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.ci import vit_post_merge_completion_remote as remote


class VitRemoteHistoricalRecoveryScopeTests(unittest.TestCase):
    def test_primary_merge_never_receives_legacy_lineage_opt_in(self) -> None:
        events: list[tuple[str, str | None]] = []

        def capture(*, repo_root, merge_sha, receipt_store):
            events.append((merge_sha, os.environ.get(remote.LEGACY_LINEAGE_ENV)))

        previous = os.environ.pop(remote.LEGACY_LINEAGE_ENV, None)
        try:
            with tempfile.TemporaryDirectory() as raw:
                argv = [
                    "vit_post_merge_completion_remote.py",
                    "--repo-root",
                    raw,
                    "--merge-sha",
                    "1" * 40,
                    "--receipt-store-root",
                    str(Path(raw) / "receipts"),
                    "--recovery-manifest",
                    str(Path(raw) / "recovery.json"),
                ]
                with (
                    patch.object(sys, "argv", argv),
                    patch.object(remote.late, "_manifest_requests", return_value=["2" * 40]),
                    patch.object(remote.late, "_recover_one", side_effect=capture),
                ):
                    self.assertEqual(remote.main(), 0)
        finally:
            if previous is not None:
                os.environ[remote.LEGACY_LINEAGE_ENV] = previous
            else:
                os.environ.pop(remote.LEGACY_LINEAGE_ENV, None)

        self.assertEqual(events[0], ("1" * 40, None))
        self.assertEqual(events[1], ("2" * 40, "true"))
        self.assertNotIn(remote.LEGACY_LINEAGE_ENV, os.environ)

    def test_historical_opt_in_restores_existing_environment_value(self) -> None:
        observed: list[str | None] = []

        def capture(*, repo_root, merge_sha, receipt_store):
            observed.append(os.environ.get(remote.LEGACY_LINEAGE_ENV))

        with patch.dict(os.environ, {remote.LEGACY_LINEAGE_ENV: "false"}, clear=False):
            with patch.object(remote.late, "_recover_one", side_effect=capture):
                remote._recover_explicit_historical_request(
                    repo_root=Path("."),
                    merge_sha="3" * 40,
                    receipt_store=object(),
                )
            self.assertEqual(os.environ.get(remote.LEGACY_LINEAGE_ENV), "false")

        self.assertEqual(observed, ["true"])

    def test_manifest_duplicate_of_primary_is_not_recovered_twice(self) -> None:
        calls: list[str] = []

        def capture(*, repo_root, merge_sha, receipt_store):
            calls.append(merge_sha)

        with tempfile.TemporaryDirectory() as raw:
            primary = "4" * 40
            argv = [
                "vit_post_merge_completion_remote.py",
                "--repo-root",
                raw,
                "--merge-sha",
                primary,
                "--receipt-store-root",
                str(Path(raw) / "receipts"),
                "--recovery-manifest",
                str(Path(raw) / "recovery.json"),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(remote.late, "_manifest_requests", return_value=[primary, "5" * 40, "5" * 40]),
                patch.object(remote.late, "_recover_one", side_effect=capture),
            ):
                self.assertEqual(remote.main(), 0)

        self.assertEqual(calls, [primary, "5" * 40])


if __name__ == "__main__":
    unittest.main()
