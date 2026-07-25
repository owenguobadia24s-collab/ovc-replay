from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.population_integrity import PopulationIntegrityError, verify_year_workspace


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class A2G1PopulationIntegrityTests(unittest.TestCase):
    def build_year(self, root: Path, year: int = 2024) -> None:
        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            objects = []
            source_ids = []
            for timeframe, side in (("M1", "BID"), ("M1", "ASK"), ("H1", "BID"), ("H1", "ASK")):
                source_id = f"SRC.DUKASCOPY.GBPUSD.{timeframe}.{side}.{ym}.v1"
                source_ids.append(source_id)
                rel = f"source/development/{timeframe.lower()}/{side.lower()}/GBPUSD_{timeframe}_{side}_{ym}_UTC.csv"
                csv_path = root / rel
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                csv_path.write_text("timestamp,open,high,low,close,volume\n1704067200000,1.2,1.3,1.1,1.25,10\n", encoding="utf-8")
                raw_rel = f"transport_cache/{source_id}.bi5"
                raw_path = root / raw_rel
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(source_id.encode("utf-8"))
                digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
                raw_digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
                objects.append({
                    "source_object_id": source_id,
                    "output_path": rel,
                    "output_sha256": digest,
                    "output_size_bytes": csv_path.stat().st_size,
                    "row_count": 1,
                    "transport_chunks": [{
                        "status": "DOWNLOADED",
                        "cached_path": raw_rel,
                        "relative_provider_path": raw_rel,
                        "sha256": raw_digest,
                        "size_bytes": raw_path.stat().st_size,
                        "url": "https://datafeed.dukascopy.com/example",
                    }],
                })
                intake = {
                    "source_object_id": source_id,
                    "qa_state": "PASS",
                    "request": {
                        "interval_start": f"{ym}-01T00:00:00Z",
                        "interval_end": f"{year + (month == 12)}-{1 if month == 12 else month + 1:02d}-01T00:00:00Z",
                        "provider_instrument": "GBPUSD",
                        "timeframe": timeframe,
                        "price_side": side,
                        "parameters_sha256": "a" * 64,
                    },
                    "response": {"sha256": digest, "size_bytes": csv_path.stat().st_size},
                }
                identity = {
                    "source_object_id": source_id,
                    "quality_state": "PASS",
                    "response_sha256": digest,
                    "size_bytes": csv_path.stat().st_size,
                }
                write_json(root / "records/intake" / f"{source_id}.json", intake)
                write_json(root / "records/source_identity" / f"{source_id}.json", identity)
            write_json(root / "records/downloader" / f"{ym}.json", {
                "year_month": ym,
                "market_authority": "NONE",
                "objects": objects,
            })
            write_json(root / "summaries" / f"{ym}.json", {
                "year_month": ym,
                "source_objects": source_ids,
                "qa_state": "PASS",
            })

    def test_complete_year_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_year(root)
            result = verify_year_workspace(root, 2024)
            self.assertEqual("PASS", result["result"])
            self.assertEqual(12, result["month_count"])
            self.assertEqual(48, result["source_object_count"])
            self.assertEqual("AUTHORISED", result["authority"]["workspace_entry"])
            self.assertEqual("DENIED", result["authority"]["release_freeze"])

    def test_byte_identity_failure_blocks_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_year(root)
            csv_path = next((root / "source").rglob("*.csv"))
            csv_path.write_text(csv_path.read_text(encoding="utf-8") + "corrupt\n", encoding="utf-8")
            with self.assertRaises(PopulationIntegrityError):
                verify_year_workspace(root, 2024)

    def test_missing_request_lineage_blocks_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_year(root)
            record_path = next((root / "records/intake").glob("*.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            del record["request"]["parameters_sha256"]
            write_json(record_path, record)
            with self.assertRaises(PopulationIntegrityError):
                verify_year_workspace(root, 2024)


if __name__ == "__main__":
    unittest.main()
