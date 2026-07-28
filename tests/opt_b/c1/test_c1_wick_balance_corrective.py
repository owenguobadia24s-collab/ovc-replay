from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ovc.opt_b.c1.formulas import C1_IMPLEMENTATION_ID, calculate, calculate_wick_balance
from ovc.opt_b.c1.models import SourceBar


ROOT = Path(__file__).resolve().parents[3]


class WickBalanceCorrectiveTests(unittest.TestCase):
    def source_bar(self, *, high: str = "1.2550", low: str = "1.2480") -> SourceBar:
        return SourceBar(
            release_id="OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            manifest_id="MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
            research_role="DISCOVERY",
            instrument_id="GBPUSD",
            clock_id="15M",
            price_side="BID",
            source_bar_id="opt-a:test",
            open_time="2023-01-03T00:15:00Z",
            close_time="2023-01-03T00:30:00Z",
            first_valid_time="2023-01-03T00:30:00Z",
            open=Decimal("1.2500"),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal("1.2540"),
            price_increment=Decimal("0.0001"),
            admissibility="HANDOFF_ELIGIBLE",
            quality_state="COMPLETE",
            synthetic=True,
            selector_state="NONE",
            authority_state="NONE",
            validation_consumption_state="NOT_APPLICABLE",
            parent_source_object_ids=("src-1",),
            parent_m1_bar_ids=tuple(f"m1-{index}" for index in range(15)),
        )

    def test_frozen_registry_sign_is_upper_minus_lower(self) -> None:
        result = calculate(self.source_bar(), None, None)
        self.assertEqual(
            result[0]["wick_balance"],
            "-0.1428571428571428571428571428571429",
        )
        self.assertEqual(C1_IMPLEMENTATION_ID, "C1.IMPLEMENTATION.v0.2")

    def test_shared_callable_is_null_for_zero_range(self) -> None:
        self.assertIsNone(
            calculate_wick_balance(Decimal("0"), Decimal("0"), Decimal("0"))
        )

    def test_full_replay_uses_shared_callable_without_duplicate_sign(self) -> None:
        source = (ROOT / "scripts/opt_b/run_c1_wp4_replay.py").read_text(encoding="utf-8")
        self.assertIn("calculate_wick_balance(upper, lower, r)", source)
        self.assertNotIn("(lower - upper) / r", source)

    def test_registry_and_implementation_remain_aligned(self) -> None:
        registry = (ROOT / "registries/opt_b/c1/C1_FORMULA_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("formula: upper_wick_share - lower_wick_share", registry)
        implementation = (ROOT / "src/ovc/opt_b/c1/formulas.py").read_text(encoding="utf-8")
        self.assertIn("(upper_wick_abs - lower_wick_abs) / range_abs", implementation)
        self.assertNotIn("(lower_wick_abs - upper_wick_abs) / range_abs", implementation)

    def test_impact_auditor_accepts_registry_conformant_fixture(self) -> None:
        record = {
            "record_id": "c1:test",
            "clock": "15M",
            "price_side": "BID",
            "measurements": {
                "range_abs": "0.007",
                "upper_wick_abs": "0.001",
                "lower_wick_abs": "0.002",
                "wick_balance": "-0.1428571428571428571428571428571429",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            discovery = root / "discovery/records/15M/BID"
            development = root / "development/records/15M/BID"
            discovery.mkdir(parents=True)
            development.mkdir(parents=True)
            for target in (discovery / "a.jsonl.gz", development / "b.jsonl.gz"):
                with gzip.open(target, "wt", encoding="utf-8", mtime=0) as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
            output = root / "audit.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/opt_b/audit_c1_wick_balance.py"),
                    "--discovery-root",
                    str(root / "discovery"),
                    "--development-root",
                    str(root / "development"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["active_affected_record_count"], 0)
            self.assertEqual(report["counterfactual_wrong_library_divergence_record_count"], 2)
            self.assertEqual(
                report["status"],
                "PASS_ACTIVE_RELEASES_CORRECT_IMPLEMENTATION_DRIFT_CONFIRMED",
            )


if __name__ == "__main__":
    unittest.main()
