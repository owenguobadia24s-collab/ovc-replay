import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PG_ROOT = ROOT / "registries/governance/programme_genesis"
SCHEMA_ROOT = ROOT / "schemas/governance/programme_genesis"
FIXTURE_ROOT = ROOT / "fixtures/governance/programme_genesis"
CONTRACT = ROOT / "contracts/governance/programme_genesis/PROGRAMME_GENESIS_AUTHORITY_CONTRACT_v0_1.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_scope_audit(record: dict) -> list[str]:
    errors: list[str] = []
    if record.get("record_type") != "SCOPE_AUDIT":
        errors.append("record_type")
    if record.get("schema_version") != "0.1":
        errors.append("schema_version")
    comparisons = record.get("comparisons", [])
    if len(comparisons) != 3:
        errors.append("exactly_three_comparisons")
    if len({item.get("existing_programme_id") for item in comparisons}) != len(comparisons):
        errors.append("unique_comparisons")
    if record.get("result") == "ADMISSIBLE_FOR_GENESIS_REVIEW":
        for comparison in comparisons:
            for field in ("packet_fit", "correction_fit", "incident_fit", "maintenance_fit"):
                if comparison.get(field) != "NO":
                    errors.append(f"negative_fit:{field}")
            if len(comparison.get("negative_fit_evidence", "")) < 20:
                errors.append("negative_fit_evidence")
        checks = record.get("fit_checks", {})
        for field in (
            "all_three_compared",
            "no_existing_fit",
            "maintenance_registry_checked",
            "reserved_authority_fail_closed",
        ):
            if checks.get(field) is not True:
                errors.append(f"fit_check:{field}")
    return errors


class ProgrammeGenesisWP1Tests(unittest.TestCase):
    def test_contract_freezes_fail_closed_authority_and_operator_boundaries(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Missing authority is `NONE`, never inherited", text)
        self.assertIn("PG-G3A", text)
        self.assertIn("PG-G6", text)
        self.assertIn("PG-G7", text)
        self.assertIn("may not rewrite", text)
        self.assertIn("Reverse authority is prohibited", text)
        self.assertIn("does not create or activate a programme", text)

    def test_schema_bundle_defines_all_core_wp1_objects(self) -> None:
        schema = load_json(SCHEMA_ROOT / "programme_genesis_bundle_v0_1.schema.json")
        definitions = schema["$defs"]
        self.assertTrue({"programme_genesis", "programme_event", "dependency_edge", "authority_envelope"}.issubset(definitions))
        genesis_required = set(definitions["programme_genesis"]["required"])
        self.assertTrue({"scope_audit_ref", "authority_envelope_ref", "governing_sources", "rollback"}.issubset(genesis_required))
        self.assertEqual("NONE", definitions["dependency_edge"]["properties"]["authority_effect"]["const"])
        self.assertEqual("NONE", definitions["programme_event"]["properties"]["authority_effect"]["enum"][0])

    def test_scope_audit_schema_requires_three_comparisons_and_fail_closed_checks(self) -> None:
        schema = load_json(SCHEMA_ROOT / "scope_audit_v0_1.schema.json")
        comparison_rule = schema["properties"]["comparisons"]
        self.assertEqual(3, comparison_rule["minItems"])
        self.assertEqual(3, comparison_rule["maxItems"])
        checks = schema["properties"]["fit_checks"]["properties"]
        self.assertTrue(all(rule["const"] is True for rule in checks.values()))
        valid = load_json(FIXTURE_ROOT / "valid_scope_audit_v0_1.json")
        invalid = load_json(FIXTURE_ROOT / "invalid_scope_audit_scope_gaming_v0_1.json")
        self.assertEqual([], validate_scope_audit(valid))
        errors = validate_scope_audit(invalid)
        self.assertIn("exactly_three_comparisons", errors)
        self.assertTrue(any(error.startswith("fit_check:") for error in errors))

    def test_valid_genesis_fixture_is_source_linked_and_non_exposure(self) -> None:
        record = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
        self.assertEqual("PROGRAMME_GENESIS", record["record_type"])
        self.assertEqual("CONSTITUTIONAL_GOVERNANCE", record["programme_class"])
        self.assertTrue(record["scope_audit_ref"].startswith("PGSCOPE."))
        self.assertTrue(record["authority_envelope_ref"].startswith("PGAUTH."))
        self.assertGreaterEqual(len(record["governing_sources"]), 2)
        self.assertTrue(any(source["source_type"] == "OPERATOR_DECISION" for source in record["governing_sources"]))
        excluded = " ".join(record["scope"]["excluded"]).lower()
        self.assertIn("exposure", excluded)
        self.assertIn("execution", excluded)

    def test_programme_class_registry_is_partition_only_and_non_authoritative(self) -> None:
        registry = load_json(PG_ROOT / "PROGRAMME_CLASS_REGISTRY_v0_1.json")
        classes = registry["classes"]
        ids = [item["class_id"] for item in classes]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual("NONE_CLASSIFICATION_AND_PARTITIONING_ONLY", registry["authority_effect"])
        self.assertTrue(all(item["may_self_grant_authority"] is False for item in classes))
        self.assertEqual("PG-G6", registry["activation_gate"])

    def test_edge_registry_blocks_reverse_and_inferred_hard_authority(self) -> None:
        registry = load_json(PG_ROOT / "EDGE_TYPE_REGISTRY_v0_1.json")
        types = {item["edge_type"]: item for item in registry["edge_types"]}
        self.assertTrue(types["REQUIRES"]["hard_requires_source_explicit"])
        self.assertTrue(types["GOVERNED_BY"]["hard_requires_source_explicit"])
        self.assertTrue(all(item["may_grant_authority"] is False for item in types.values()))
        prohibited = set(registry["prohibited_edge_effects"])
        self.assertIn("ADAPTER_INFERENCE_SATISFIES_HARD_PREREQUISITE", prohibited)
        self.assertIn("TEST_RESULT_TO_AUTHORITY_GRANT", prohibited)

    def test_event_registry_orders_deterministically_and_requires_decisions_for_authority(self) -> None:
        registry = load_json(PG_ROOT / "EVENT_TYPE_REGISTRY_v0_1.json")
        self.assertEqual(["first_valid_at", "precedence", "event_id"], registry["ordering"])
        events = registry["event_types"]
        names = [item["event_type"] for item in events]
        self.assertEqual(len(names), len(set(names)))
        precedence = [item["precedence"] for item in events]
        self.assertEqual(len(precedence), len(set(precedence)))
        by_name = {item["event_type"]: item for item in events}
        self.assertTrue(by_name["GENESIS_ACCEPTED"]["accepted_decision_required"])
        self.assertEqual(["NONE"], by_name["PR_MERGED"]["authority_effects"])
        self.assertEqual(["NONE"], by_name["QA_REVIEWED"]["authority_effects"])

    def test_wp1_files_do_not_activate_reserved_capabilities(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                CONTRACT,
                PG_ROOT / "PROGRAMME_CLASS_REGISTRY_v0_1.json",
                PG_ROOT / "EDGE_TYPE_REGISTRY_v0_1.json",
                PG_ROOT / "EVENT_TYPE_REGISTRY_v0_1.json",
            ]
        )
        self.assertIn("FROZEN_CANDIDATE", combined)
        self.assertIn("PG-G6", combined)
        self.assertIn("PG-G7", combined)
        self.assertNotIn('may_self_grant_authority": true', combined)


if __name__ == "__main__":
    unittest.main()
