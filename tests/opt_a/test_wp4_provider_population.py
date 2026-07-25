from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.provider_population import (
    PopulationIntakeError,
    aggregate_month_summaries,
    audit_month_workspace,
    build_population_plan,
    iter_population_months,
    role_for_month,
    source_specs_for_month,
)


class WP4ProviderPopulationTests(unittest.TestCase):
    def test_exact_population_plan(self) -> None:
        plan = build_population_plan()
        self.assertEqual(60, plan["month_count"])
        self.assertEqual(240, plan["source_object_count"])
        self.assertEqual("2021-01", plan["months"][0])
        self.assertEqual("2025-12", plan["months"][-1])
        self.assertEqual(
            {"DISCOVERY": 144, "DEVELOPMENT": 48, "VALIDATION": 48},
            plan["role_counts"],
        )
        self.assertEqual("NONE", plan["authority"]["market"])
        self.assertEqual("LOCKED_UNCONSUMED", plan["authority"]["validation_consumption"])

    def test_role_and_release_boundaries(self) -> None:
        self.assertEqual("DISCOVERY", role_for_month("2021-01"))
        self.assertEqual("DISCOVERY", role_for_month("2023-12"))
        self.assertEqual("DEVELOPMENT", role_for_month("2024-01"))
        self.assertEqual("VALIDATION", role_for_month("2025-12"))
        specs = source_specs_for_month("2025-01")
        self.assertEqual(4, len(specs))
        self.assertEqual(
            {("M1", "BID"), ("M1", "ASK"), ("H1", "BID"), ("H1", "ASK")},
            {(item.native_timeframe, item.price_side) for item in specs},
        )
        self.assertTrue(all(item.research_role == "VALIDATION" for item in specs))
        self.assertTrue(
            all(item.target_release_id == "OPT-A.GBPUSD.VALIDATION.2025.v2" for item in specs)
        )

    def test_month_audit_writes_exact_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for spec in source_specs_for_month("2024-01"):
                path = root / spec.relative_csv_path
                path.parent.mkdir(parents=True, exist_ok=True)
                step = 60_000 if spec.native_timeframe == "M1" else 3_600_000
                start_ms = int(spec.interval_start.timestamp() * 1000)
                rows = [
                    "timestamp,open,high,low,close,volume",
                    f"{start_ms},1.2700,1.2710,1.2690,1.2705,10",
                    f"{start_ms + step},1.2705,1.2720,1.2700,1.2715,12",
                ]
                path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            summary = audit_month_workspace(root, "2024-01")
            self.assertEqual("PASS", summary["qa_state"])
            self.assertEqual(4, summary["source_object_count"])
            self.assertEqual(8, summary["row_count"])
            self.assertEqual("NONE", summary["market_authority"])
            self.assertEqual("DENIED_UNTIL_FREEZE", summary["release_parent"])
            for spec in source_specs_for_month("2024-01"):
                intake = json.loads((root / spec.relative_intake_record_path).read_text())
                identity = json.loads((root / spec.relative_identity_path).read_text())
                self.assertIs(intake["synthetic"], False)
                self.assertEqual("PASS", intake["qa_state"])
                self.assertEqual("LOCAL_ONLY", intake["availability_state"])
                self.assertEqual("NONE", intake["authority"]["market"])
                self.assertEqual("ELIGIBLE", identity["authority"]["workspace_input"])
                self.assertEqual("DENIED", identity["authority"]["selector_input"])

    def test_invalid_timestamp_alignment_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = source_specs_for_month("2024-01")[0]
            for item in source_specs_for_month("2024-01"):
                path = root / item.relative_csv_path
                path.parent.mkdir(parents=True, exist_ok=True)
                start_ms = int(item.interval_start.timestamp() * 1000)
                if item == spec:
                    start_ms += 1
                path.write_text(
                    "timestamp,open,high,low,close,volume\n"
                    f"{start_ms},1.27,1.28,1.26,1.27,1\n",
                    encoding="utf-8",
                )
            with self.assertRaises(PopulationIntakeError):
                audit_month_workspace(root, "2024-01")

    def test_aggregate_requires_every_month_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for month in iter_population_months():
                path = root / f"{month}.json"
                path.write_text(
                    json.dumps(
                        {
                            "year_month": month,
                            "qa_state": "PASS",
                            "source_object_count": 4,
                            "row_count": 10,
                            "size_bytes": 100,
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
            summary = aggregate_month_summaries(paths)
            self.assertEqual(60, summary["month_count"])
            self.assertEqual(240, summary["source_object_count"])
            self.assertEqual("PASS", summary["qa_state"])
            self.assertEqual("NONE", summary["r2_mutation"])
            with self.assertRaises(PopulationIntakeError):
                aggregate_month_summaries(paths[:-1])


if __name__ == "__main__":
    unittest.main()
