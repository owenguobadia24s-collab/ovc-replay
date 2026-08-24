from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import tools.ci.vit_lineage_source as lineage_source


class PesVitQualificationLivenessTests(unittest.TestCase):
    def test_actions_default_enables_bounded_reconciliation(self) -> None:
        with patch.dict(lineage_source.os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            self.assertEqual(lineage_source._qualification_reconcile_window_seconds(), 180.0)

    def test_local_default_remains_fail_fast(self) -> None:
        with patch.dict(lineage_source.os.environ, {}, clear=True):
            self.assertEqual(lineage_source._qualification_reconcile_window_seconds(), 0.0)

    def test_explicit_wait_window_is_bounded(self) -> None:
        with patch.dict(
            lineage_source.os.environ,
            {"OVC_PES_VIT_QUALIFICATION_WAIT_SECONDS": "601"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "PES_VIT_QUALIFICATION_WAIT_OUT_OF_RANGE"):
                lineage_source._qualification_reconcile_window_seconds()

    def test_real_ledger_read_reconciles_until_exact_head_qualification_appears(self) -> None:
        resolved = SimpleNamespace(
            record={"schema_version": "test-lineage"},
            qualification_id="a" * 64,
        )
        resolver = Mock(side_effect=[None, None, resolved])
        with (
            patch.object(lineage_source, "resolve_qualification_envelope", resolver),
            patch.object(lineage_source, "_qualification_reconcile_window_seconds", return_value=180.0),
            patch.object(lineage_source.time, "monotonic", side_effect=[100.0, 100.0, 105.0]),
            patch.object(lineage_source.time, "sleep") as sleep,
        ):
            source = lineage_source.resolve_candidate_lineage(
                root=Path("."),
                head_sha="1" * 40,
            )
        assert source is not None
        self.assertEqual(source.source, "DETACHED_QUALIFICATION_LEDGER")
        self.assertEqual(source.immutable_ref, "a" * 64)
        self.assertEqual(resolver.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_reconciliation_expires_fail_closed_without_manufacturing_authority(self) -> None:
        resolver = Mock(return_value=None)
        with (
            patch.object(lineage_source, "resolve_qualification_envelope", resolver),
            patch.object(lineage_source, "_qualification_reconcile_window_seconds", return_value=5.0),
            patch.object(lineage_source.time, "monotonic", side_effect=[100.0, 100.0, 105.0]),
            patch.object(lineage_source.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_REQUIRED"):
                lineage_source.resolve_candidate_lineage(
                    root=Path("."),
                    head_sha="1" * 40,
                )
        self.assertEqual(resolver.call_count, 2)
        sleep.assert_called_once_with(5.0)

    def test_injected_qualification_source_keeps_deterministic_fail_fast_semantics(self) -> None:
        resolver = Mock(return_value=None)
        with (
            patch.object(lineage_source, "resolve_qualification_envelope", resolver),
            patch.object(lineage_source, "_qualification_reconcile_window_seconds") as window,
            patch.object(lineage_source.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_REQUIRED"):
                lineage_source.resolve_candidate_lineage(
                    root=Path("."),
                    head_sha="1" * 40,
                    fetch_qualification_file=lambda _: None,
                )
        window.assert_not_called()
        sleep.assert_not_called()
        self.assertEqual(resolver.call_count, 1)


if __name__ == "__main__":
    unittest.main()
