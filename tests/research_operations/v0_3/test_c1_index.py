from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.research_operations.v0_3.c1_index import (
    AccessDenied,
    IndexContractError,
    build_c1_indexes,
    build_incremental_index_receipt,
    parse_formula_registry,
    validation_metadata_only,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "fixtures" / "research_operations" / "v0_3" / "wp1_c1_index_cases.json"
REGISTRY_PATH = ROOT / "registries" / "opt_b" / "c1" / "C1_FORMULA_REGISTRY_v0_1.yaml"

FAMILY_COUNTS = [
    ("DISCOVERY", "15M", "BID", 71982),
    ("DISCOVERY", "15M", "ASK", 71982),
    ("DISCOVERY", "2H_A_L", "BID", 7964),
    ("DISCOVERY", "2H_A_L", "ASK", 7964),
    ("DEVELOPMENT", "15M", "BID", 23853),
    ("DEVELOPMENT", "15M", "ASK", 23853),
    ("DEVELOPMENT", "2H_A_L", "BID", 2583),
    ("DEVELOPMENT", "2H_A_L", "ASK", 2583),
]


def load_inputs():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8")
    registry_sha256 = hashlib.sha256(registry_text.encode("utf-8")).hexdigest()
    releases = deepcopy(fixture["releases"])
    for release in releases:
        release["formula_registry_sha256"] = registry_sha256
    return fixture, registry_text, releases


def record_headers(*, reverse_families: bool = False, duplicate_first: bool = False):
    _, _, releases = load_inputs()
    release_by_role = {release["role"]: release for release in releases}
    families = list(reversed(FAMILY_COUNTS)) if reverse_families else FAMILY_COUNTS
    first_record_id = None
    emitted = 0
    for role, clock, side, count in families:
        release = release_by_role[role]
        for offset in range(count):
            token = f"{role}|{clock}|{side}|{offset}"
            record_id = "c1:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
            if first_record_id is None:
                first_record_id = record_id
            elif duplicate_first and emitted == 1:
                record_id = first_record_id
            emitted += 1
            null_reasons = {}
            if offset == 0:
                null_reasons = {
                    "true_range_abs": "NO_PRIOR_BAR",
                    "true_range_ticks": "NO_PRIOR_BAR",
                    "close_change": "NO_PRIOR_BAR",
                    "open_gap": "NO_PRIOR_BAR",
                }
            yield {
                "record_id": record_id,
                "role": role,
                "release_id": release["release_id"],
                "manifest_sha256": release["manifest_sha256"],
                "clock": clock,
                "side": side,
                "schema_version": "0.1",
                "formula_registry_id": "C1.FORMULAS.v0.1",
                "null_reasons": null_reasons,
                "source_hash": hashlib.sha256((token + "|source").encode("utf-8")).hexdigest(),
            }


class C1IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture, cls.registry_text, cls.releases = load_inputs()

    def test_formula_registry_indexes_all_18_frozen_definitions_once(self) -> None:
        parsed = parse_formula_registry(self.registry_text)
        self.assertEqual(parsed["formula_count"], 18)
        self.assertEqual(len(parsed["formulas"]), 18)
        self.assertEqual(len({row["primitive_id"] for row in parsed["formulas"]}), 18)
        self.assertEqual(parsed["arithmetic"], "DECIMAL_EXACT")

    def test_full_corpus_indexes_are_exact_and_input_order_independent(self) -> None:
        first = build_c1_indexes(
            releases=self.releases,
            formula_registry_text=self.registry_text,
            record_headers=record_headers(),
            validation_metadata=self.fixture["validation_metadata"],
        )
        second = build_c1_indexes(
            releases=list(reversed(self.releases)),
            formula_registry_text=self.registry_text,
            record_headers=record_headers(reverse_families=True),
            validation_metadata=dict(reversed(list(self.fixture["validation_metadata"].items()))),
        )
        self.assertEqual(first["logical_index_sha256"], second["logical_index_sha256"])
        self.assertEqual(len(first["release_index"]), 2)
        self.assertEqual(len(first["primitive_index"]), 18)
        self.assertEqual(len(first["family_index"]), 8)
        coverage = first["coverage_profile"]
        self.assertEqual(coverage["total_c1_record_count"], 212764)
        self.assertEqual(coverage["total_record_file_count"], 192)
        self.assertEqual(coverage["roles"]["DISCOVERY"]["c1_record_count"], 159892)
        self.assertEqual(coverage["roles"]["DEVELOPMENT"]["c1_record_count"], 52872)
        actual_counts = {
            (row["role"], row["clock"], row["side"]): row["record_count"]
            for row in first["family_index"]
        }
        expected_counts = {(role, clock, side): count for role, clock, side, count in FAMILY_COUNTS}
        self.assertEqual(actual_counts, expected_counts)
        self.assertEqual(first["validation"]["availability"], "METADATA_ONLY")
        self.assertEqual(first["validation"]["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(first["writes"], "NONE")

    def test_validation_is_denied_before_path_or_record_resolution(self) -> None:
        with self.assertRaisesRegex(AccessDenied, "VALIDATION_DENY_BEFORE_RESOLUTION"):
            validation_metadata_only({
                "role": "VALIDATION",
                "release_id": "OPT-B.C1.GBPUSD.VALIDATION.NOT_BUILT",
                "manifest_sha256": "a" * 64,
                "path": "/forbidden/validation.jsonl",
            })
        with self.assertRaisesRegex(AccessDenied, "VALIDATION_DENY_BEFORE_RECORD_RESOLUTION"):
            build_c1_indexes(
                releases=self.releases,
                formula_registry_text=self.registry_text,
                record_headers=[{
                    "record_id": "c1:" + "0" * 64,
                    "role": "VALIDATION",
                    "release_id": "OPT-B.C1.GBPUSD.VALIDATION.NOT_BUILT",
                    "manifest_sha256": "a" * 64,
                    "clock": "15M",
                    "side": "BID",
                    "schema_version": "0.1",
                    "formula_registry_id": "C1.FORMULAS.v0.1",
                }],
            )

    def test_unknown_role_release_clock_side_and_duplicate_ids_fail_closed(self) -> None:
        bad_release = deepcopy(self.releases[0])
        bad_release["role"] = "VALIDATION"
        with self.assertRaises(AccessDenied):
            build_c1_indexes(
                releases=[bad_release, self.releases[1]],
                formula_registry_text=self.registry_text,
                record_headers=[],
            )

        two = []
        for row in record_headers(duplicate_first=True):
            two.append(row)
            if len(two) == 2:
                break
        with self.assertRaisesRegex(IndexContractError, "duplicate record_id"):
            build_c1_indexes(
                releases=self.releases,
                formula_registry_text=self.registry_text,
                record_headers=two,
            )

        bad = deepcopy(self.releases[0])
        bad["clocks"] = ["15M", "H1_PROVIDER_NATIVE"]
        with self.assertRaisesRegex(IndexContractError, "clocks"):
            build_c1_indexes(
                releases=[bad, self.releases[1]],
                formula_registry_text=self.registry_text,
                record_headers=[],
            )

    def test_incremental_receipt_is_sorted_source_bound_and_non_writing(self) -> None:
        full = build_c1_indexes(
            releases=self.releases,
            formula_registry_text=self.registry_text,
            record_headers=record_headers(),
        )
        receipt = build_incremental_index_receipt(
            prior_logical_index_sha256="1" * 64,
            added_source_identities=["src-b", "src-a", "src-a"],
            final_index=full,
        )
        self.assertEqual(receipt["added_source_identities"], ["src-a", "src-b"])
        self.assertEqual(receipt["final_logical_index_sha256"], full["logical_index_sha256"])
        self.assertEqual(receipt["writes"], "NONE")


if __name__ == "__main__":
    unittest.main()
