from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.topology import build_repository_topology, build_topology_from_inventory
from ovc.programme_genesis.topology_conformance import TopologyConformanceError, build_repository_conformance_snapshot


ROOT = Path(__file__).resolve().parents[2]
RULE_PACK = json.loads((ROOT / "registries/governance/genesis_repository_topology/GRT_TOPOLOGY_RULE_PACK_v0_1.json").read_text(encoding="utf-8"))


class GRTWP9ConformanceTests(unittest.TestCase):
    def test_conformance_projection_is_authority_neutral_and_preserves_unknowns(self) -> None:
        model = build_topology_from_inventory(
            repository="example/ovc",
            source_commit="a" * 40,
            entries=[
                {"path": "src/ovc/unowned/core.py", "blob_hash": "1" * 40},
                {"path": "docs/releases/example/state.md", "blob_hash": "2" * 40},
            ],
            content_by_path={
                "src/ovc/unowned/core.py": "VALUE = 1\n",
                "docs/releases/example/state.md": "programme_id: OVC-EXAMPLE-v0.1\nstatus: ACTIVE\n",
            },
            rule_pack={"rule_pack_id": "GRT.TEST.WP9", "scan_roots": ["src/", "docs/releases/"]},
        )
        snapshot = build_repository_conformance_snapshot(model)
        self.assertEqual(snapshot["authority_effect"], "NONE_DERIVED_CONFORMANCE_AUDIT_ONLY")
        self.assertFalse(snapshot["repair_performed"])
        self.assertFalse(snapshot["programme_or_dependency_authority_changed"])
        self.assertFalse(snapshot["validation_consumed"])
        self.assertGreaterEqual(snapshot["component_population"]["without_programme_owner_count"], 1)

    def test_authority_bearing_input_fails_closed(self) -> None:
        with self.assertRaises(TopologyConformanceError):
            build_repository_conformance_snapshot({
                "schema": "ovc-genesis-repository-topology-read-model/v1",
                "authority_effect": "MUTATION_ALLOWED",
            })

    def test_repository_wide_conformance_snapshot_is_complete_and_printable(self) -> None:
        model = build_repository_topology(ROOT, rule_pack=RULE_PACK)
        snapshot = build_repository_conformance_snapshot(model)
        counts = snapshot["programme_coverage"]["counts"]
        self.assertEqual(sum(counts.values()), model["portfolio"]["programme_count"])
        self.assertEqual(snapshot["component_population"]["count"], model["portfolio"]["component_count"])
        self.assertEqual(snapshot["findings"]["blocker_count"], model["health_summary"]["severity_counts"].get("BLOCKER", 0))
        self.assertEqual(snapshot["source_commit"], model["portfolio"]["source_commit"])
        self.assertEqual(snapshot["topology_sha256"], model["topology_sha256"])
        print("GRT_WP9_CONFORMANCE_SUMMARY=" + json.dumps({
            "source_commit": snapshot["source_commit"],
            "topology_sha256": snapshot["topology_sha256"],
            "programme_coverage_counts": snapshot["programme_coverage"]["counts"],
            "component_count": snapshot["component_population"]["count"],
            "component_type_counts": snapshot["component_population"]["type_counts"],
            "components_without_programme_owner": snapshot["component_population"]["without_programme_owner_count"],
            "shared_components": snapshot["component_population"]["shared_component_count"],
            "historical_or_legacy_components": snapshot["component_population"]["historical_or_legacy_count"],
            "stale_documentation": snapshot["findings"]["stale_documentation_count"],
            "authority_mismatches_or_conflicts": snapshot["findings"]["authority_mismatch_or_conflict_count"],
            "unresolved_relationships": snapshot["findings"]["unresolved_relationship_count"],
            "warnings": snapshot["findings"]["warning_count"],
            "blockers": snapshot["findings"]["blocker_count"],
            "authority_effect": snapshot["authority_effect"],
        }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
