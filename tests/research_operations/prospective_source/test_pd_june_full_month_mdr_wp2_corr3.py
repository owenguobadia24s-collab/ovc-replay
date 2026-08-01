from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ovc.research_operations.prospective_source import full_month_mdr_replay as subject


class PDJuneFullMonthMDRWP2Corr3Tests(unittest.TestCase):
    def test_transient_access_denial_retries_then_removes_pass_b(self) -> None:
        with tempfile.TemporaryDirectory() as root_value:
            root = Path(root_value)
            pass_b = root / "compute" / ".staging" / "pass-b"
            leaf = pass_b / "bars" / "15M" / "BID.jsonl"
            leaf.parent.mkdir(parents=True)
            leaf.write_text("{}\n", encoding="utf-8")

            calls = 0
            original_rmtree = subject._ORIGINAL_RMTREE

            def flaky_rmtree(path: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError(13, "Access is denied", str(path))
                original_rmtree(path)

            quarantined = subject.dispose_determinism_workspace(
                pass_b,
                rmtree=flaky_rmtree,
                sleeper=lambda _: None,
            )

            self.assertIsNone(quarantined)
            self.assertEqual(calls, 2)
            self.assertFalse(pass_b.exists())

    def test_persistent_access_denial_quarantines_duplicate_pass_b(self) -> None:
        with tempfile.TemporaryDirectory() as root_value:
            compute_root = Path(root_value) / "prospective-source" / "compute"
            pass_b = compute_root / ".PD-JUNE-FM-WP2.staging.test" / "pass-b"
            leaf = pass_b / "bars" / "15M" / "BID.jsonl"
            leaf.parent.mkdir(parents=True)
            leaf.write_text("{}\n", encoding="utf-8")

            def denied_rmtree(path: Path) -> None:
                raise PermissionError(13, "Access is denied", str(path))

            quarantined = subject.dispose_determinism_workspace(
                pass_b,
                rmtree=denied_rmtree,
                sleeper=lambda _: None,
            )

            self.assertIsNotNone(quarantined)
            assert quarantined is not None
            self.assertFalse(pass_b.exists())
            self.assertTrue(quarantined.is_dir())
            self.assertEqual(quarantined.parent, compute_root / "quarantine")
            receipt = quarantined / "cleanup-receipt.json"
            self.assertTrue(receipt.is_file())
            content = receipt.read_text(encoding="utf-8")
            self.assertIn(
                "QUARANTINED_AFTER_BOUNDED_WINDOWS_CLEANUP_DENIAL",
                content,
            )
            self.assertIn('"candidate_payload_mutated": false', content)

    def test_non_retryable_cleanup_error_remains_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as root_value:
            pass_b = Path(root_value) / "compute" / ".staging" / "pass-b"
            pass_b.mkdir(parents=True)

            def invalid_rmtree(path: Path) -> None:
                raise OSError(22, "Invalid argument", str(path))

            with self.assertRaises(OSError) as raised:
                subject.dispose_determinism_workspace(
                    pass_b,
                    rmtree=invalid_rmtree,
                    sleeper=lambda _: None,
                )
            self.assertEqual(raised.exception.errno, 22)
            self.assertTrue(pass_b.exists())

    def test_execute_scopes_cleanup_proxy_and_restores_shutil(self) -> None:
        original = subject.implementation.shutil
        observed: list[object] = []

        def fake_execute(*args: object, **kwargs: object) -> dict[str, str]:
            observed.append(subject.implementation.shutil)
            return {"status": "TEST"}

        with patch.object(subject, "_ORIGINAL_EXECUTE", side_effect=fake_execute):
            result = subject.execute(
                Path("."),
                authority_gate=subject.AUTHORITY_GATE,
                environ={},
            )

        self.assertEqual(result, {"status": "TEST"})
        self.assertEqual(observed, [subject._SHUTIL_PROXY])
        self.assertIs(subject.implementation.shutil, original)


if __name__ == "__main__":
    unittest.main()
