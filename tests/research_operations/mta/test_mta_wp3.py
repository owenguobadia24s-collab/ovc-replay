from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.research_operations.mta.c2_translation_audit import (
    MTAWP3AuditError,
    validate_reference,
    validate_sequence_fixture,
)

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "docs/releases/market-translation-audit-v0-2/mta-g3/MTA_WP3_C2_TRANSLATION_AUDIT_REFERENCE.json"
FIXTURE = ROOT / "fixtures/research_operations/mta/MTA_WP3_C2_TRANSLATION_FIXTURE_v0_1.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


class MTAWP3Tests(unittest.TestCase):
    def test_reference_passes(self) -> None:
        result = validate_reference(load(REFERENCE))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["accepted_c2_ids_reconstructed"], 16765)

    def test_reference_blocks_unaccounted_records(self) -> None:
        value = load(REFERENCE)
        value["record_accounting"]["unaccounted_c2_records"] = 1
        with self.assertRaisesRegex(MTAWP3AuditError, "REFERENCE_ACCOUNTING_MISMATCH"):
            validate_reference(value)

    def test_reference_blocks_authority_escape(self) -> None:
        value = load(REFERENCE)
        value["c2e_c2_5_c3"] = "ALLOWED"
        with self.assertRaisesRegex(MTAWP3AuditError, "REFERENCE_AUTHORITY_ESCAPE"):
            validate_reference(value)

    def test_fixture_passes(self) -> None:
        self.assertEqual(validate_sequence_fixture(load(FIXTURE)), {"status": "PASS", "states": 2, "transitions": 1})

    def test_fixture_blocks_wrong_changed_axes(self) -> None:
        value = copy.deepcopy(load(FIXTURE))
        value["transitions"][0]["changed_axes"] = ["LOCATION"]
        with self.assertRaisesRegex(MTAWP3AuditError, "FIXTURE_CHANGED_AXES_MISMATCH"):
            validate_sequence_fixture(value)


if __name__ == "__main__":
    unittest.main()
