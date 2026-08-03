import json
import unittest
from pathlib import Path

from ovc.programme_genesis import (
    build_compact_portfolio_report,
    build_disabled_control_plane_projection,
    build_portfolio_health_report,
    build_portfolio_read_model,
    build_snapshot_from_registry,
    load_migration_source_registry,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "ff903e24898094e1ba9408563f76197a9808e583"
MIGRATION_REGISTRY = ROOT / "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"
NATIVE_STATE = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
ADAPTER_REGISTRY = ROOT / "registries/governance/programme_genesis/CONTROL_PLANE_ADAPTER_REGISTRY_v0_1.json"
GRAPH_REPORT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3_GRAPH_VALIDATION_REPORT.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ProgrammeGenesisWP5EvidenceOutputTests(unittest.TestCase):
    def test_repository_read_model_emits_compact_reproducible_evidence(self) -> None:
        migration = build_snapshot_from_registry(ROOT, load_migration_source_registry(MIGRATION_REGISTRY))
        native = load_json(NATIVE_STATE)
        adapter_config = load_json(ADAPTER_REGISTRY)
        graph = load_json(GRAPH_REPORT)
        read_model = build_portfolio_read_model(
            migration,
            native,
            source_commit=SOURCE_COMMIT,
            graph_summary={
                "graph_id": graph["graph_id"],
                "scope": graph["scope"],
                "status": graph["status"],
                "census": graph["census"],
                "validation_findings": graph["validation_findings"],
                "authority_paths": graph["authority_paths"],
                "migration_boundary": graph["migration_boundary"],
            },
        )
        health = build_portfolio_health_report(ROOT, read_model, adapter_config=adapter_config)
        compact = build_compact_portfolio_report(read_model, health)
        adapter = build_disabled_control_plane_projection(compact, adapter_config)
        evidence = {
            "evidence": "PG_WP5_REPOSITORY_READ_MODEL",
            "source_commit": SOURCE_COMMIT,
            "read_model_status": read_model["status"],
            "health_status": health["status"],
            "programme_count": compact["programme_count"],
            "migrated_programme_count": compact["migrated_programme_count"],
            "migration_warning_count": compact["migration_warning_count"],
            "health_warning_count": compact["health_warning_count"],
            "health_blocking_count": compact["health_blocking_count"],
            "adapter_status": adapter["status"],
            "read_model_sha256": read_model["read_model_sha256"],
            "health_sha256": health["health_sha256"],
            "report_sha256": compact["report_sha256"],
            "adapter_projection_sha256": adapter["adapter_projection_sha256"],
        }
        print(json.dumps(evidence, sort_keys=True))
        self.assertEqual("PASS_WITH_WARNINGS", health["status"])
        self.assertEqual(0, health["blocking_count"])
        self.assertEqual("DISABLED_PENDING_PG_G6", adapter["status"])


if __name__ == "__main__":
    unittest.main()
