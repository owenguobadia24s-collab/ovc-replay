import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.programme_genesis import (
    ReadModelError,
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
GRAPH_REPORT = ROOT / "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3_GRAPH_VALIDATION_REPORT.json"
ADAPTER_REGISTRY = ROOT / "registries/governance/programme_genesis/CONTROL_PLANE_ADAPTER_REGISTRY_v0_1.json"
SCHEMA = ROOT / "schemas/governance/programme_genesis/portfolio_read_model_bundle_v0_1.schema.json"
CONTRACT = ROOT / "contracts/governance/programme_genesis/PORTFOLIO_READ_MODEL_AND_DISABLED_ADAPTER_CONTRACT_v0_1.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def graph_summary() -> dict:
    report = load_json(GRAPH_REPORT)
    return {
        "graph_id": report["graph_id"],
        "scope": report["scope"],
        "status": report["status"],
        "census": report["census"],
        "validation_findings": report["validation_findings"],
        "authority_paths": report["authority_paths"],
        "migration_boundary": report["migration_boundary"],
    }


def repository_outputs() -> tuple[dict, dict, dict, dict, dict]:
    migration = build_snapshot_from_registry(ROOT, load_migration_source_registry(MIGRATION_REGISTRY))
    native = load_json(NATIVE_STATE)
    adapter = load_json(ADAPTER_REGISTRY)
    read_model = build_portfolio_read_model(
        migration,
        native,
        source_commit=SOURCE_COMMIT,
        graph_summary=graph_summary(),
    )
    health = build_portfolio_health_report(ROOT, read_model, adapter_config=adapter)
    compact = build_compact_portfolio_report(read_model, health)
    disabled = build_disabled_control_plane_projection(compact, adapter)
    return migration, read_model, health, compact, disabled


def synthetic_snapshot(source_path: str, source_sha256: str) -> dict:
    record = {
        "programme_id": "OVC-EXAMPLE-v1",
        "source": {"path": source_path, "sha256": source_sha256},
        "preserved_values": {
            "status": "RUNNING",
            "current_packet": "WP1",
            "current_gate": "G1",
            "authority": {"read": "ACTIVE", "write": "DENIED"},
            "blockers": [],
            "next_action": "CONTINUE",
        },
        "confidence": "MEDIUM",
        "migration_uncertainty": {
            "required": True,
            "banner": "MIGRATION_UNCERTAINTY",
            "reason": "NON_NATIVE_GENESIS_IMPORT",
            "removal_condition": "ACCEPTED_NATIVE_GENESIS_AT_A_LATER_AUTHORITY_CHANGING_GATE",
        },
        "unresolved_fields": ["scope_audit_ref"],
        "conflicting_fields": [],
        "native_governance_deadline": "BEFORE_NEXT_AUTHORITY_CHANGING_GATE_OR_PROGRAMME_BOUNDARY",
    }
    snapshot = {
        "schema": "ovc-programme-migration-snapshot/v1",
        "status": "PASS",
        "authority_effect": "NONE",
        "records": [record],
        "conflict_ledger": [
            {
                "finding_type": "MIGRATION_UNRESOLVED_FIELDS",
                "severity": "WARN",
                "programme_id": "OVC-EXAMPLE-v1",
                "fields": ["scope_audit_ref"],
                "authority_effect": "NONE",
            }
        ],
        "blocking_conflict_count": 0,
        "snapshot_sha256": "a" * 64,
    }
    return snapshot


def native_state() -> dict:
    return {
        "programme_id": "OVC-PG-v0.2",
        "status": "RUNNING",
        "current_packet": "PG-WP5",
        "current_gate": "PG-G5",
        "authority": {"control_plane_route": "DENIED_PENDING_PG_G6"},
        "blockers": [],
        "next_action": "BUILD_READ_MODEL",
    }


class ProgrammeGenesisWP5Tests(unittest.TestCase):
    def test_repository_read_model_is_deterministic_and_source_linked(self) -> None:
        first = repository_outputs()
        second = repository_outputs()
        self.assertEqual(first, second)
        migration, read_model, health, compact, disabled = first
        self.assertEqual(7, migration["record_count"])
        self.assertEqual(8, read_model["health_summary"]["programme_count"])
        self.assertEqual(7, read_model["health_summary"]["migrated_programme_count"])
        self.assertEqual(14, read_model["health_summary"]["migration_warning_count"])
        self.assertEqual("PASS_WITH_WARNINGS", read_model["status"])
        self.assertEqual(SOURCE_COMMIT, read_model["source_commit"])
        self.assertEqual("PASS_WITH_WARNINGS", health["status"])
        self.assertEqual(7, health["warning_count"])
        self.assertEqual(0, health["blocking_count"])
        self.assertEqual(8, compact["programme_count"])
        self.assertEqual("DISABLED", compact["control_plane_adapter_status"])
        self.assertEqual("DISABLED_PENDING_PG_G6", disabled["status"])

    def test_programme_rows_are_sorted_and_preserve_migration_uncertainty(self) -> None:
        migration, read_model, _, _, _ = repository_outputs()
        programme_ids = [row["programme_id"] for row in read_model["programmes"]]
        self.assertEqual(sorted(programme_ids), programme_ids)
        migrated = [row for row in read_model["programmes"] if row["source_kind"] == "MIGRATED_PROGRAMME_STATE"]
        native = [row for row in read_model["programmes"] if row["source_kind"] == "NATIVE_PROGRAMME_STATE"]
        self.assertEqual(7, len(migrated))
        self.assertEqual(1, len(native))
        self.assertEqual("OVC-PG-v0.2", native[0]["programme_id"])
        self.assertTrue(native[0]["canonical"])
        for row in migrated:
            self.assertFalse(row["canonical"])
            self.assertEqual("NONE", row["authority_effect"])
            self.assertEqual("MIGRATION_UNCERTAINTY", row["migration_uncertainty"]["banner"])
            self.assertTrue(row["unresolved_fields"])
            matching = next(record for record in migration["records"] if record["programme_id"] == row["programme_id"])
            self.assertEqual(matching["source"]["sha256"], row["source_sha256"])

    def test_record_order_does_not_change_read_model_identity(self) -> None:
        migration = build_snapshot_from_registry(ROOT, load_migration_source_registry(MIGRATION_REGISTRY))
        native = load_json(NATIVE_STATE)
        first = build_portfolio_read_model(migration, native, source_commit=SOURCE_COMMIT, graph_summary=graph_summary())
        reversed_snapshot = deepcopy(migration)
        reversed_snapshot["records"] = list(reversed(reversed_snapshot["records"]))
        second = build_portfolio_read_model(reversed_snapshot, native, source_commit=SOURCE_COMMIT, graph_summary=graph_summary())
        self.assertEqual(first, second)

    def test_health_detects_missing_and_tampered_sources_without_repair(self) -> None:
        adapter = load_json(ADAPTER_REGISTRY)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "registries/example/EXAMPLE_PROGRAMME_STATE_v1.json"
            source.parent.mkdir(parents=True)
            source.write_text('{"programme_id":"OVC-EXAMPLE-v1"}\n', encoding="utf-8")
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            read_model = build_portfolio_read_model(
                synthetic_snapshot("registries/example/EXAMPLE_PROGRAMME_STATE_v1.json", sha),
                native_state(),
                source_commit="b" * 40,
            )
            passing = build_portfolio_health_report(root, read_model, adapter_config=adapter)
            self.assertEqual("PASS_WITH_WARNINGS", passing["status"])
            self.assertEqual(0, passing["blocking_count"])
            source.write_text('{"programme_id":"OVC-EXAMPLE-v1","tampered":true}\n', encoding="utf-8")
            tampered = build_portfolio_health_report(root, read_model, adapter_config=adapter)
            self.assertEqual("FAIL", tampered["status"])
            self.assertTrue(any(item["finding_type"] == "MIGRATION_SOURCE_HASH_MISMATCH" for item in tampered["findings"]))
            source.unlink()
            missing = build_portfolio_health_report(root, read_model, adapter_config=adapter)
            self.assertEqual("FAIL", missing["status"])
            self.assertTrue(any(item["finding_type"] == "MIGRATION_SOURCE_MISSING" for item in missing["findings"]))

    def test_adapter_activation_attempt_quarantines_health_and_blocks_projection(self) -> None:
        _, read_model, _, compact, _ = repository_outputs()
        adapter = load_json(ADAPTER_REGISTRY)
        activated = deepcopy(adapter)
        activated["enabled"] = True
        activated["route_registered"] = True
        health = build_portfolio_health_report(ROOT, read_model, adapter_config=activated)
        self.assertEqual("FAIL", health["status"])
        self.assertTrue(any(item["finding_type"] == "CONTROL_PLANE_ADAPTER_PREMATURE_ACTIVATION" and item["severity"] == "QUARANTINE" for item in health["findings"]))
        with self.assertRaisesRegex(ReadModelError, "not authorised before PG-G6"):
            build_disabled_control_plane_projection(compact, activated)

    def test_read_model_fails_closed_on_invalid_sources_or_commit(self) -> None:
        migration = build_snapshot_from_registry(ROOT, load_migration_source_registry(MIGRATION_REGISTRY))
        native = load_json(NATIVE_STATE)
        blocked = deepcopy(migration)
        blocked["status"] = "BLOCK"
        with self.assertRaisesRegex(ReadModelError, "blocking migration snapshot"):
            build_portfolio_read_model(blocked, native, source_commit=SOURCE_COMMIT)
        non_neutral = deepcopy(migration)
        non_neutral["authority_effect"] = "GRANTED"
        with self.assertRaisesRegex(ReadModelError, "authority-neutral"):
            build_portfolio_read_model(non_neutral, native, source_commit=SOURCE_COMMIT)
        with self.assertRaisesRegex(ReadModelError, "source_commit"):
            build_portfolio_read_model(migration, native, source_commit="not-a-commit")

    def test_compact_report_and_disabled_adapter_retain_authority_denials(self) -> None:
        _, _, health, compact, disabled = repository_outputs()
        self.assertEqual(0, health["blocking_count"])
        self.assertEqual("DENIED_PENDING_PG_G6", compact["canonical_adoption"])
        self.assertEqual("DENIED_PENDING_PG_G6", compact["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G6", compact["control_plane_route"])
        self.assertEqual("DENIED_PENDING_PG_G7", compact["automatic_upkeep"])
        self.assertFalse(disabled["route_registered"])
        self.assertFalse(disabled["write_enabled"])
        self.assertFalse(disabled["enforcement_enabled"])
        self.assertTrue(disabled["read_only"])
        self.assertEqual("PG-G6", disabled["activation_gate"])
        self.assertEqual("NONE_DISABLED_ADAPTER_CANDIDATE", disabled["authority_effect"])

    def test_schema_contract_and_registry_freeze_disabled_boundary(self) -> None:
        schema = load_json(SCHEMA)
        definitions = schema["$defs"]
        self.assertEqual("NONE_READ_ONLY_DERIVED_VIEW", definitions["read_model"]["properties"]["authority_effect"]["const"])
        self.assertEqual("DISABLED_PENDING_PG_G6", definitions["disabled_adapter"]["properties"]["status"]["const"])
        self.assertFalse(definitions["disabled_adapter"]["properties"]["route_registered"]["const"])
        adapter = load_json(ADAPTER_REGISTRY)
        self.assertFalse(adapter["enabled"])
        self.assertFalse(adapter["route_registered"])
        self.assertFalse(adapter["write_enabled"])
        self.assertFalse(adapter["enforcement_enabled"])
        self.assertEqual("PG-G6", adapter["activation_gate"])
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Programme-owned machine-readable state remains authoritative", text)
        self.assertIn("Local payload availability is not route authority", text)
        self.assertIn("PG-G5=PASS` accepts only the disabled adapter candidate", text)
        self.assertIn("four orthogonal authority deltas independently", text)
        self.assertIn("Automatic upkeep remains separately denied until `PG-G7`", text)


if __name__ == "__main__":
    unittest.main()
