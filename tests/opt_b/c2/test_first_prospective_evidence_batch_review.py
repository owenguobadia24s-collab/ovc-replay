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

    def valid_record(self, record_id: str = "C2EV-0123456789ABCDEF") -> dict:
        return {
            "schema": "ovc-c2-prospective-evidence-record/v0.1",
            "record_id": record_id,
            "research_line_id": MODULE.RESEARCH_LINE,
            "record_class": "STATE_FIDELITY_REVIEW",
            "evidence_status": "OBSERVED_UNREVIEWED",
            "instrument": "GBPUSD",
            "canonical_clock": "15M",
            "price_side": "BID",
            "observation_start_utc": "2026-07-27T08:00:00Z",
            "observation_end_utc": "2026-07-27T08:15:00Z",
            "created_at_utc": "2026-07-27T08:16:00Z",
            "author": "operator",
            "active_release_id": MODULE.ACTIVE_RELEASE,
            "active_manifest_id": MODULE.ACTIVE_MANIFEST,
            "active_manifest_sha256": MODULE.ACTIVE_MANIFEST_SHA256,
            "source_object_ids": ["C2STATE-EXAMPLE-001"],
            "summary": "Prospective review of whether the C2 state matched the observable bar context.",
            "prospective": True,
            "sequence_boundary_friction": False,
            "c2e_authority": "NONE",
            "probability_authority": "NONE",
            "exposure_authority": "NONE",
            "trading_authority": "NONE",
            "execution_authority": "NONE",
        }

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

    def test_one_valid_real_record_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_records(root, [self.valid_record()])
            result, exit_code = MODULE.review(root)
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS_FIRST_BATCH_ACCEPTED", result["decision"])
        self.assertEqual(1, result["record_count"])
        self.assertEqual([], result["errors"])

    def test_duplicate_ids_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.valid_record()
            self.write_records(root, [record, record])
            result, exit_code = MODULE.review(root)
        self.assertEqual(1, exit_code)
        self.assertEqual("BLOCK_BATCH_INTEGRITY_FAILURE", result["decision"])
        self.assertTrue(any("duplicate active record IDs" in error for error in result["errors"]))

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
