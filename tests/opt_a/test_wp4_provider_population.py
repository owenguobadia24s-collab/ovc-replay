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


ROOT = Path(__file__).resolve().parents[2]
INTAKE_ROOT = ROOT / "docs" / "releases" / "opt-a-v2" / "intake"


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

    def test_committed_population_summary_is_exact_and_non_authoritative(self) -> None:
        summary = json.loads(
            (INTAKE_ROOT / "WP4_POPULATION_INTAKE_SUMMARY.json").read_text(encoding="utf-8")
        )
        self.assertEqual("DUKASCOPY", summary["provider"])
        self.assertEqual("GBPUSD", summary["instrument_id"])
        self.assertEqual("2021-01-01T00:00:00Z", summary["interval_start"])
        self.assertEqual("2026-01-01T00:00:00Z", summary["interval_end"])
        self.assertEqual(60, summary["month_count"])
        self.assertEqual(240, summary["source_object_count"])
        self.assertEqual(3_781_810, summary["row_count"])
        self.assertEqual(216_656_289, summary["size_bytes"])
        self.assertEqual("PASS", summary["qa_state"])
        self.assertEqual("NONE", summary["market_authority"])
        self.assertEqual("NONE", summary["r2_mutation"])
        self.assertEqual("NONE", summary["selector_activation"])
        self.assertEqual("DENIED_UNTIL_FREEZE", summary["release_parent"])
        self.assertEqual("LOCKED_UNCONSUMED", summary["validation_consumption"])
        months = [item["year_month"] for item in summary["monthly_summaries"]]
        self.assertEqual(list(iter_population_months()), months)
        self.assertTrue(all(item["qa_state"] == "PASS" for item in summary["monthly_summaries"]))
        self.assertTrue(
            all(item["source_object_count"] == 4 for item in summary["monthly_summaries"])
        )
        self.assertTrue(
            all(
                item["validation_consumption"] == "LOCKED_UNCONSUMED"
                for item in summary["monthly_summaries"]
                if item["research_role"] == "VALIDATION"
            )
        )

    def test_execution_receipt_and_artifact_inventory_are_bounded(self) -> None:
        receipt = json.loads(
            (INTAKE_ROOT / "WP4_EXECUTION_RECEIPT.json").read_text(encoding="utf-8")
        )
        inventory = json.loads(
            (INTAKE_ROOT / "WP4_ACTIONS_ARTIFACT_INVENTORY.json").read_text(encoding="utf-8")
        )
        self.assertEqual(30175183492, receipt["workflow_run_id"])
        self.assertEqual("OVC_DIRECT_BI5_CANDLE_ADAPTER", receipt["adapter"])
        self.assertEqual("1.0.1", receipt["adapter_version"])
        self.assertEqual(60, receipt["month_count"])
        self.assertEqual(240, receipt["source_object_count"])
        self.assertEqual("NONE", receipt["r2_mutation"])
        self.assertEqual("NONE", receipt["selector_activation"])
        self.assertEqual("NONE", receipt["market_authority"])
        self.assertEqual("LOCKED_UNCONSUMED", receipt["validation_consumption"])
        self.assertIs(inventory["market_payloads_in_git"], False)
        self.assertEqual("NONE", inventory["canonical_authority"])
        self.assertEqual("NONE", inventory["r2_mutation"])
        self.assertEqual(85_076_759, inventory["yearly_compressed_size_bytes"])
        self.assertEqual(12, len(inventory["artifacts"]))
        yearly = [
            item
            for item in inventory["artifacts"]
            if item["role"].startswith("TEMPORARY_YEARLY_PROVIDER_EVIDENCE")
        ]
        self.assertEqual(5, len(yearly))
        self.assertEqual(
            inventory["yearly_compressed_size_bytes"],
            sum(item["size_in_bytes"] for item in yearly),
        )


if __name__ == "__main__":
    unittest.main()
