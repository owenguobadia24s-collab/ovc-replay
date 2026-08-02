from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.mta.source_c1_audit import (
    SourceC1AuditError,
    audit_files,
    audit_stream,
    validate_reference,
)

ROOT = Path(__file__).resolve().parents[3]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class MTAWP2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load("fixtures/research_operations/mta/MTA_WP2_SOURCE_C1_FIXTURE_v0_1.json")
        cls.reference = load("docs/releases/market-translation-audit-v0-2/mta-g2/MTA_WP2_EXTERNAL_AUDIT_REFERENCE.json")

    def test_validator_script_passes(self) -> None:
        path = ROOT / "scripts/research_operations/validate_mta_wp2.py"
        spec = importlib.util.spec_from_file_location("validate_mta_wp2", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

    def test_reference_accounts_for_every_record(self) -> None:
        result = validate_reference(self.reference)
        accounting = self.reference["record_accounting"]
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(accounting["derived_bars_total"], 5220)
        self.assertEqual(accounting["derived_bars_complete"], 4958)
        self.assertEqual(accounting["derived_bars_incomplete"], 262)
        self.assertEqual(accounting["c1_records_total"], 4958)
        self.assertEqual(accounting["audited_derived_records_total"], 10178)
        self.assertEqual(accounting["unaccounted_derived_records"], 0)

    def test_fixture_passes_formula_identity_and_lineage(self) -> None:
        result = audit_stream(self.fixture["bars"], self.fixture["c1"], clock="15M", side="BID")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["mismatches"], {})
        self.assertEqual(result["counts"]["bars_complete"], 1)
        self.assertEqual(result["counts"]["bars_incomplete"], 1)
        self.assertEqual(result["counts"]["c1_total"], 1)

    def test_incomplete_bar_cannot_enter_c1(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        copied = copy.deepcopy(fixture["c1"][0])
        copied["source_path"] = "bars/15M/BID/RPS.BAR.FIXTURE.0002"
        fixture["c1"].append(copied)
        result = audit_stream(fixture["bars"], fixture["c1"], clock="15M", side="BID")
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["mismatches"]["c1_from_incomplete"], 1)

    def test_formula_tampering_is_detected(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["c1"][0]["measurements"]["range_abs"] = "9"
        result = audit_stream(fixture["bars"], fixture["c1"], clock="15M", side="BID")
        self.assertEqual(result["mismatches"]["formula_values"], 1)
        self.assertEqual(result["mismatches"]["c1_record_identity"], 1)

    def test_source_bar_identity_tampering_is_detected(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["c1"][0]["source_bar_id"] = "rps-price:wrong"
        result = audit_stream(fixture["bars"], fixture["c1"], clock="15M", side="BID")
        self.assertEqual(result["mismatches"]["source_bar_identity"], 1)
        self.assertEqual(result["mismatches"]["c1_record_identity"], 1)

    def test_file_hash_mismatch_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bars_path = root / "bars.jsonl"
            c1_path = root / "c1.jsonl"
            bars_path.write_text("\n".join(json.dumps(item, sort_keys=True) for item in self.fixture["bars"]) + "\n", encoding="utf-8")
            c1_path.write_text("\n".join(json.dumps(item, sort_keys=True) for item in self.fixture["c1"]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceC1AuditError, "BAR_SHA256_MISMATCH"):
                audit_files(
                    bars_path,
                    c1_path,
                    clock="15M",
                    side="BID",
                    expected_bar_sha256="0" * 64,
                )

    def test_reference_rejects_authority_escape(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["r2_publication"] = "ALLOWED"
        with self.assertRaisesRegex(SourceC1AuditError, "REFERENCE_AUTHORITY_ESCAPE"):
            validate_reference(reference)

    def test_reference_rejects_nonzero_mismatch(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["mismatch_counts"]["formula"] = 1
        with self.assertRaisesRegex(SourceC1AuditError, "REFERENCE_MISMATCHES_NONZERO"):
            validate_reference(reference)

    def test_all_input_hashes_match_frozen_output_manifest(self) -> None:
        manifest = load("docs/releases/pattern-discovery-v0-3/pd-june-full-month-mdr/wp2-replay/output-manifest.json")
        by_path = {item["path"]: item for item in manifest["files"]}
        for item in self.reference["input_files"]:
            observed = by_path[item["name"]]
            self.assertEqual(observed["sha256"], item["sha256"])
            self.assertEqual(observed["size_bytes"], item["size_bytes"])
            self.assertEqual(observed["record_count"], item["records"])

    def test_paired_provider_absence_remains_explicit(self) -> None:
        source = self.reference["source_qa"]
        self.assertEqual(source["m1_absent_timestamps_per_side"], 138)
        self.assertEqual(source["m1_gap_runs_per_side"], 95)
        self.assertEqual(source["bid_ask_pairing"], "PASS_EXACT")
        self.assertEqual(source["classification"], "PAIRED_PROVIDER_ABSENCE_NOT_TRANSPORT_CORRUPTION")
        self.assertFalse(source["repair_performed"])


if __name__ == "__main__":
    unittest.main()
