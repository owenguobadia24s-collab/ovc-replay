from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/development/v0_2/build_ci_admission_baseline.py"
spec = importlib.util.spec_from_file_location("da2_builder", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DA2AdmissionBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_root = ROOT / "fixtures/development/v0_2"
        self.complete = json.loads((fixture_root / "ci_admission_complete.json").read_text())
        self.missing = json.loads((fixture_root / "ci_admission_missing_timing.json").read_text())
        self.classes = json.loads((fixture_root / "ci_admission_classifications.json").read_text())

    def test_complete_evidence_is_deterministic(self) -> None:
        first = module.build(self.complete["subjects"], self.classes)
        second = module.build(self.complete["subjects"], self.classes)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertFalse(first["reproducibility"]["estimated_values_used"])

    def test_missing_timing_blocks(self) -> None:
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "missing exact fields"):
            module.build(self.missing["subjects"], self.classes)

    def test_missing_required_source_identity_blocks(self) -> None:
        bad = json.loads(json.dumps(self.complete))
        bad["subjects"][0]["workflow_runs"][0]["check_source"] = None
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "missing accepted app identity"):
            module.build(bad["subjects"], self.classes)

    def test_ambiguous_classification_blocks(self) -> None:
        bad_classes = json.loads(json.dumps(self.classes))
        bad_classes["classifications"]["UNRELATED"].append("tests")
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "2 classifications"):
            module.build(self.complete["subjects"], bad_classes)

    def test_negative_duration_blocks(self) -> None:
        bad = json.loads(json.dumps(self.complete))
        run = bad["subjects"][0]["workflow_runs"][0]
        run["run_started_at"] = "2026-08-02T20:00:00Z"
        run["created_at"] = "2026-08-02T20:01:00Z"
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "negative duration"):
            module.build(bad["subjects"], self.classes)


if __name__ == "__main__":
    unittest.main()
