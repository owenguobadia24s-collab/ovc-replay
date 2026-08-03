import json
import unittest
from pathlib import Path

from ovc.programme_genesis import build_snapshot_from_registry, load_migration_source_registry


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"


class ProgrammeGenesisWP4CensusOutputTests(unittest.TestCase):
    def test_repository_census_emits_compact_reproducible_evidence(self) -> None:
        snapshot = build_snapshot_from_registry(ROOT, load_migration_source_registry(REGISTRY))
        summary = {
            "evidence": "PG_WP4_REPOSITORY_CENSUS",
            "status": snapshot["status"],
            "record_count": snapshot["record_count"],
            "unique_programme_count": snapshot["unique_programme_count"],
            "warning_count": sum(item["severity"] == "WARN" for item in snapshot["conflict_ledger"]),
            "blocking_conflict_count": snapshot["blocking_conflict_count"],
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "programme_ids": sorted(record["programme_id"] for record in snapshot["records"]),
        }
        print(json.dumps(summary, sort_keys=True))
        self.assertEqual("PASS", snapshot["status"])
        self.assertEqual(0, snapshot["blocking_conflict_count"])


if __name__ == "__main__":
    unittest.main()
