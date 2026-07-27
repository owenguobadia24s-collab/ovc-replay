from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "opt_b" / "review_first_prospective_evidence_batch.py"
SPEC = importlib.util.spec_from_file_location("c2_first_batch_review", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FirstProspectiveEvidenceBatchReviewTests(unittest.TestCase):
    def target(self, root: Path) -> Path:
        return root / MODULE.APPEND_TARGET

    def valid_record(self, operation_mode: str = "LIVE_PROSPECTIVE") -> dict:
        record = {
            "schema": "ovc-c2-prospective-evidence-record/v0.2",
            "record_id": "",
            "research_line_id": MODULE.RESEARCH_LINE,
            "record_class": "STATE_FIDELITY_REVIEW",
            "evidence_status": "OBSERVED_UNREVIEWED",
            "instrument": "GBPUSD",
            "canonical_clock": "15M",
            "price_side": "BID",
            "market_window_start_utc": "2026-07-27T08:00:00Z",
            "market_window_end_utc": "2026-07-27T08:15:00Z",
            "trigger_first_valid_at": "2026-07-27T08:15:00Z",
            "review_created_at_utc": "2026-07-27T08:16:00Z",
            "operation_mode": operation_mode,
            "author": "operator",
            "active_release_id": MODULE.ACTIVE_RELEASE,
            "active_manifest_id": MODULE.ACTIVE_MANIFEST,
            "active_manifest_sha256": MODULE.ACTIVE_MANIFEST_SHA256,
            "source_object_ids": ["C2STATE-EXAMPLE-001"],
            "summary": "Review of whether the C2 state matched the observable bar context.",
            "sequence_boundary_friction": False,
            "c2e_authority": "NONE",
            "probability_authority": "NONE",
            "exposure_authority": "NONE",
            "trading_authority": "NONE",
            "execution_authority": "NONE",
        }
        record["record_id"] = MODULE.deterministic_record_id(record)
        return record

    def write_records(self, root: Path, records: list[dict]) -> None:
        target = self.target(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def test_absent_target_defers_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, exit_code = MODULE.review(Path(directory))
        self.assertEqual(0, exit_code)
        self.assertEqual("DEFER_NO_REAL_PROSPECTIVE_BATCH", result["decision"])
        self.assertEqual("ABSENT", result["append_target_state"])
        self.assertEqual(0, result["record_count"])
        self.assertEqual(0, result["live_prospective_count"])

    def test_empty_target_defers_without_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self.target(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            result, exit_code = MODULE.review(root)
        self.assertEqual(0, exit_code)
        self.assertEqual("DEFER_NO_REAL_PROSPECTIVE_BATCH", result["decision"])
        self.assertEqual("EMPTY", result["append_target_state"])

    def test_one_valid_live_record_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_records(root, [self.valid_record()])
            result, exit_code = MODULE.review(root)
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS_FIRST_BATCH_ACCEPTED", result["decision"])
        self.assertEqual(1, result["record_count"])
        self.assertEqual(1, result["live_prospective_count"])
        self.assertEqual([], result["errors"])
        self.assertEqual("2026-07-27T08:15:00Z", result["market_time_range"]["first_trigger_first_valid_at"])

    def test_time_gated_only_ledger_defers(self) -> None:
        record = self.valid_record("TIME_GATED_REPLAY")
        record["market_window_start_utc"] = "2024-01-01T08:00:00Z"
        record["market_window_end_utc"] = "2024-01-01T08:15:00Z"
        record["trigger_first_valid_at"] = "2024-01-01T08:15:00Z"
        record["record_id"] = MODULE.deterministic_record_id(record)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_records(root, [record])
            result, exit_code = MODULE.review(root)
        self.assertEqual(0, exit_code)
        self.assertEqual("DEFER_NO_REAL_PROSPECTIVE_BATCH", result["decision"])
        self.assertEqual(0, result["live_prospective_count"])
        self.assertEqual(1, result["operation_mode_counts"]["TIME_GATED_REPLAY"])

    def test_duplicate_ids_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.valid_record()
            self.write_records(root, [record, record])
            result, exit_code = MODULE.review(root)
        self.assertEqual(1, exit_code)
        self.assertEqual("BLOCK_BATCH_INTEGRITY_FAILURE", result["decision"])
        self.assertTrue(any("duplicate active record IDs" in error for error in result["errors"]))

    def test_non_evidentiary_boundary_friction_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.valid_record("NON_EVIDENTIARY_REPLAY")
            record["sequence_boundary_friction"] = True
            self.write_records(root, [record])
            result, exit_code = MODULE.review(root)
        self.assertEqual(1, exit_code)
        self.assertEqual("BLOCK_BATCH_INTEGRITY_FAILURE", result["decision"])
        self.assertTrue(
            any("cannot carry sequence-boundary-friction weight" in error for error in result["errors"])
        )

    def test_prohibited_authority_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.valid_record()
            record["probability_authority"] = "ACTIVE"
            self.write_records(root, [record])
            result, exit_code = MODULE.review(root)
        self.assertEqual(1, exit_code)
        self.assertEqual("BLOCK_BATCH_INTEGRITY_FAILURE", result["decision"])
        self.assertTrue(any("probability_authority must remain NONE" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
