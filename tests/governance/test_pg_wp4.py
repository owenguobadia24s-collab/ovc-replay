import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.programme_genesis import (
    MigrationError,
    build_conflict_ledger,
    build_migration_record,
    build_migration_snapshot,
    build_snapshot_from_registry,
    discover_programme_state_paths,
    load_migration_source_registry,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/governance/programme_genesis/programme_migration_snapshot_v0_1.schema.json"
CONTRACT_PATH = ROOT / "contracts/governance/programme_genesis/EXISTING_PROGRAMME_MIGRATION_CONTRACT_v0_1.md"
PG_STATE_PATH = "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_state(programme_id: str, status: str = "RUNNING") -> dict:
    return {
        "schema": "example-programme-state/v1",
        "programme_id": programme_id,
        "plan_id": f"{programme_id}.PLAN",
        "plan_version": "1.0",
        "programme_status": status,
        "current_packet": "WP1" if status != "COMPLETED" else None,
        "current_gate": "G1" if status != "COMPLETED" else None,
        "operator_decision_required": False,
        "operator_decision_id": "EXAMPLE.DECISION.PASS",
        "baseline_commit": "a" * 40,
        "branch": "build/example",
        "candidate_commit": "b" * 40,
        "merge_commit": None,
        "authority": {"read": "ACTIVE", "write": "DENIED"},
        "blockers": [],
        "next_action": "CONTINUE" if status != "COMPLETED" else None,
    }


class ProgrammeGenesisWP4Tests(unittest.TestCase):
    def test_discovery_selects_only_programme_state_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            programme = root / "registries/example/EXAMPLE_PROGRAMME_STATE_v1.json"
            packet = root / "registries/example/EXAMPLE_WP1_STATE_v1.json"
            generic = root / "registries/example/STATE_v1.json"
            write_json(programme, source_state("OVC-EXAMPLE-v1"))
            write_json(packet, source_state("OVC-EXAMPLE-v1"))
            write_json(generic, source_state("OVC-EXAMPLE-v1"))
            discovered = discover_programme_state_paths(root)
            self.assertEqual([programme], discovered)

    def test_migration_record_preserves_source_values_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "registries/example/EXAMPLE_PROGRAMME_STATE_v1.json"
            source = source_state("OVC-EXAMPLE-v1")
            source["authority"] = {"nested": {"value": [1, "two", None]}}
            write_json(path, source)
            record = build_migration_record(root, path)
            self.assertEqual(source["programme_id"], record["preserved_values"]["programme_id"])
            self.assertEqual(source["programme_status"], record["preserved_values"]["status"])
            self.assertEqual(source["authority"], record["preserved_values"]["authority"])
            self.assertEqual("programme_status", record["source_coverage"]["source_field_map"]["status"])
            self.assertEqual([], record["inferred_fields"])
            self.assertEqual([], record["conflicting_fields"])
            self.assertEqual("PROVISIONAL_NON_CANONICAL", record["import_status"])
            self.assertEqual("NONE", record["authority_effect"])
            self.assertTrue(record["migration_uncertainty"]["required"])
            self.assertEqual("MIGRATION_UNCERTAINTY", record["migration_uncertainty"]["banner"])

    def test_migration_record_binds_exact_path_and_source_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "registries/example/EXAMPLE_PROGRAMME_STATE_v1.json"
            write_json(path, source_state("OVC-EXAMPLE-v1"))
            record = build_migration_record(root, path)
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual("registries/example/EXAMPLE_PROGRAMME_STATE_v1.json", record["source"]["path"])
            self.assertEqual(expected, record["source"]["sha256"])
            self.assertIn(expected[:16], record["migration_id"])

    def test_native_governance_deadline_distinguishes_active_and_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            active = root / "registries/a/A_PROGRAMME_STATE_v1.json"
            terminal = root / "registries/b/B_PROGRAMME_STATE_v1.json"
            write_json(active, source_state("OVC-A-v1", "RUNNING"))
            write_json(terminal, source_state("OVC-B-v1", "COMPLETED"))
            self.assertEqual(
                "BEFORE_NEXT_AUTHORITY_CHANGING_GATE_OR_PROGRAMME_BOUNDARY",
                build_migration_record(root, active)["native_governance_deadline"],
            )
            self.assertEqual(
                "BEFORE_REACTIVATION_OR_SUPERSESSION",
                build_migration_record(root, terminal)["native_governance_deadline"],
            )

    def test_duplicate_programme_sources_expose_conflict_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_path = root / "registries/a/A_PROGRAMME_STATE_v1.json"
            second_path = root / "registries/b/A_PROGRAMME_STATE_v2.json"
            first = source_state("OVC-A-v1", "RUNNING")
            second = source_state("OVC-A-v1", "COMPLETED")
            write_json(first_path, first)
            write_json(second_path, second)
            first_record = build_migration_record(root, first_path)
            second_record = build_migration_record(root, second_path)
            findings = build_conflict_ledger([first_record, second_record])
            conflicts = [item for item in findings if item["finding_type"] == "MIGRATION_SOURCE_CONFLICT"]
            self.assertTrue(conflicts)
            self.assertTrue(all(item["severity"] == "BLOCK" for item in conflicts))
            self.assertTrue(all(item["authority_effect"] == "NONE" for item in conflicts))
            self.assertEqual("RUNNING", first_record["preserved_values"]["status"])
            self.assertEqual("COMPLETED", second_record["preserved_values"]["status"])

    def test_snapshot_is_deterministic_and_authority_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "registries/b/B_PROGRAMME_STATE_v1.json", source_state("OVC-B-v1"))
            write_json(root / "registries/a/A_PROGRAMME_STATE_v1.json", source_state("OVC-A-v1", "COMPLETED"))
            first = build_migration_snapshot(root, minimum_records=2)
            second = build_migration_snapshot(root, minimum_records=2)
            self.assertEqual(first, second)
            self.assertEqual("PASS", first["status"])
            self.assertEqual("NONE", first["authority_effect"])
            self.assertEqual("DENIED_PENDING_PG_G6", first["canonical_adoption"])
            self.assertEqual("DENIED_PENDING_PG_G6", first["admission_enforcement"])
            self.assertEqual("DENIED_PENDING_PG_G6", first["control_plane_route"])
            self.assertEqual("DENIED_PENDING_PG_G7", first["automatic_upkeep"])
            self.assertEqual(["OVC-A-v1", "OVC-B-v1"], [item["programme_id"] for item in first["records"]])

    def test_missing_or_invalid_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(MigrationError, "does not exist"):
                build_migration_record(root, "registries/missing/PROGRAMME_STATE.json")
            invalid = root / "registries/x/X_PROGRAMME_STATE.json"
            write_json(invalid, {"schema": "invalid"})
            with self.assertRaisesRegex(MigrationError, "no programme_id"):
                build_migration_record(root, invalid)
            with self.assertRaisesRegex(MigrationError, "minimum"):
                build_migration_snapshot(root, minimum_records=1)

    def test_repository_snapshot_is_reproducible_and_preserves_uncertainty(self) -> None:
        registry = load_migration_source_registry(REGISTRY_PATH)
        first = build_snapshot_from_registry(ROOT, registry)
        second = build_snapshot_from_registry(ROOT, registry)
        minimum = registry["discovery"]["minimum_records"]
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["record_count"], minimum)
        self.assertEqual(first["record_count"], first["unique_programme_count"])
        self.assertEqual("PASS", first["status"])
        self.assertEqual(0, first["blocking_conflict_count"])
        self.assertNotIn("OVC-PG-v0.2", {record["programme_id"] for record in first["records"]})
        self.assertIn(PG_STATE_PATH, first["excluded_paths"])
        for record in first["records"]:
            source_path = ROOT / record["source"]["path"]
            self.assertTrue(source_path.is_file(), record["source"]["path"])
            self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(), record["source"]["sha256"])
            self.assertEqual("PROVISIONAL_NON_CANONICAL", record["import_status"])
            self.assertEqual("NONE", record["authority_effect"])
            self.assertEqual([], record["inferred_fields"])
            self.assertTrue(record["migration_uncertainty"]["required"])
            self.assertTrue(record["unresolved_fields"])

    def test_schema_and_contract_freeze_non_canonical_boundary(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual("PROVISIONAL_NON_CANONICAL", schema["properties"]["import_status"]["const"])
        self.assertEqual("NONE", schema["properties"]["authority_effect"]["const"])
        self.assertEqual(0, schema["$defs"]["migration_record"]["properties"]["inferred_fields"]["maxItems"])
        self.assertEqual("DENIED_PENDING_PG_G6", schema["properties"]["canonical_adoption"]["const"])
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("does not accept any imported programme fact or edge as canon", contract)
        self.assertIn("Programme-owned machine-readable state is the authoritative source", contract)
        self.assertIn("inferred_fields` is empty by default", contract)
        self.assertIn("PG-G4=PASS` accepts only the migration mechanism", contract)
        self.assertIn("Automatic upkeep remains denied until `PG-G7`", contract)


if __name__ == "__main__":
    unittest.main()
