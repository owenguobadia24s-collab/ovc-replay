from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import load_json, validate_schema
from ovc.programme_genesis.grt_v0_2.debt import (
    B0_MEMBERSHIP_SHA256,
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    baseline_membership_sha256,
    validate_baseline_member_record,
    validate_baseline_members,
    validate_debt_baseline,
)

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "registries/governance/grt_v0_2/baseline"
SCHEMAS = ROOT / "schemas/governance/grt_v0_2"


def rows() -> list[dict]:
    return [
        json.loads(line)
        for line in (BASE / "GRT_B0_BASELINE_MEMBERS_v0_1.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]


class GRT2WP2BaselineTests(unittest.TestCase):
    def test_wp2_schemas_are_bootstrap_valid(self) -> None:
        for name in (
            "baseline_member_record.schema.json",
            "grt_debt_baseline.schema.json",
            "grt_finding_record.schema.json",
            "lineage.schema.json",
            "debt_floor.schema.json",
        ):
            validate_schema(load_json(SCHEMAS / name))

    def test_exact_b0_population(self) -> None:
        data = rows()
        schema = load_json(SCHEMAS / "baseline_member_record.schema.json")
        self.assertEqual(len(data), 569)
        for row in data:
            validate_baseline_member_record(row, schema)
        validate_baseline_members(data)
        self.assertEqual(baseline_membership_sha256(data), B0_MEMBERSHIP_SHA256)
        self.assertEqual(len({row["original_GRT_anomaly"] for row in data}), 569)
        self.assertEqual(len({row["payload_hash"] for row in data}), 569)
        self.assertEqual([row["ordinal"] for row in data], list(range(1, 570)))

    def test_baseline_is_source_bound_and_unmapped_until_wp3a(self) -> None:
        data = rows()
        baseline = load_json(BASE / "GRT_DEBT_BASELINE_B0.json")
        validate_debt_baseline(
            baseline,
            data,
            load_json(SCHEMAS / "grt_debt_baseline.schema.json"),
        )
        self.assertEqual(baseline["source_commit"], B0_SOURCE_COMMIT)
        self.assertEqual(baseline["source_tree_hash"], B0_SOURCE_TREE)
        self.assertEqual(baseline["source_topology_sha256"], B0_TOPOLOGY_SHA256)
        self.assertEqual(
            baseline["constitution_mapping_status"],
            "PENDING_WP3_ARTIFACT_GRAPH",
        )
        self.assertTrue(
            all(row["mapping_status"] == "PENDING_WP3_ARTIFACT_GRAPH" for row in data)
        )
        self.assertTrue(all(row["mapped_finding_id"] is None for row in data))
        self.assertTrue(all(row["disposition"] is None for row in data))
        self.assertTrue(all(row["lineage_refs"] == [] for row in data))
        self.assertTrue(
            all(any(json.loads(row["original_subject_locator"]).values()) for row in data)
        )


if __name__ == "__main__":
    unittest.main()
