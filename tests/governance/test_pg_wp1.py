import json
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


def test_contract_freezes_fail_closed_authority_and_operator_boundaries() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Missing authority is `NONE`, never inherited" in text
    assert "PG-G3A" in text
    assert "PG-G6" in text
    assert "PG-G7" in text
    assert "may not rewrite" in text
    assert "Reverse authority is prohibited" in text
    assert "does not create or activate a programme" in text


def test_schema_bundle_defines_all_core_wp1_objects() -> None:
    schema = load_json(SCHEMA_ROOT / "programme_genesis_bundle_v0_1.schema.json")
    definitions = schema["$defs"]
    assert {"programme_genesis", "programme_event", "dependency_edge", "authority_envelope"}.issubset(definitions)

    genesis_required = set(definitions["programme_genesis"]["required"])
    assert {"scope_audit_ref", "authority_envelope_ref", "governing_sources", "rollback"}.issubset(genesis_required)
    assert definitions["dependency_edge"]["properties"]["authority_effect"]["const"] == "NONE"
    assert definitions["programme_event"]["properties"]["authority_effect"]["enum"][0] == "NONE"


def test_scope_audit_schema_requires_three_comparisons_and_fail_closed_checks() -> None:
    schema = load_json(SCHEMA_ROOT / "scope_audit_v0_1.schema.json")
    comparison_rule = schema["properties"]["comparisons"]
    assert comparison_rule["minItems"] == 3
    assert comparison_rule["maxItems"] == 3
    checks = schema["properties"]["fit_checks"]["properties"]
    assert all(rule["const"] is True for rule in checks.values())

    valid = load_json(FIXTURE_ROOT / "valid_scope_audit_v0_1.json")
    invalid = load_json(FIXTURE_ROOT / "invalid_scope_audit_scope_gaming_v0_1.json")
    assert validate_scope_audit(valid) == []
    errors = validate_scope_audit(invalid)
    assert "exactly_three_comparisons" in errors
    assert any(error.startswith("fit_check:") for error in errors)


def test_valid_genesis_fixture_is_source_linked_and_non_exposure() -> None:
    record = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
    assert record["record_type"] == "PROGRAMME_GENESIS"
    assert record["programme_class"] == "CONSTITUTIONAL_GOVERNANCE"
    assert record["scope_audit_ref"].startswith("PGSCOPE.")
    assert record["authority_envelope_ref"].startswith("PGAUTH.")
    assert len(record["governing_sources"]) >= 2
    assert any(source["source_type"] == "OPERATOR_DECISION" for source in record["governing_sources"])
    excluded = " ".join(record["scope"]["excluded"]).lower()
    assert "exposure" in excluded
    assert "execution" in excluded


def test_programme_class_registry_is_partition_only_and_non_authoritative() -> None:
    registry = load_json(PG_ROOT / "PROGRAMME_CLASS_REGISTRY_v0_1.json")
    classes = registry["classes"]
    ids = [item["class_id"] for item in classes]
    assert len(ids) == len(set(ids))
    assert registry["authority_effect"] == "NONE_CLASSIFICATION_AND_PARTITIONING_ONLY"
    assert all(item["may_self_grant_authority"] is False for item in classes)
    assert registry["activation_gate"] == "PG-G6"


def test_edge_registry_blocks_reverse_and_inferred_hard_authority() -> None:
    registry = load_json(PG_ROOT / "EDGE_TYPE_REGISTRY_v0_1.json")
    types = {item["edge_type"]: item for item in registry["edge_types"]}
    assert types["REQUIRES"]["hard_requires_source_explicit"] is True
    assert types["GOVERNED_BY"]["hard_requires_source_explicit"] is True
    assert all(item["may_grant_authority"] is False for item in types.values())
    prohibited = set(registry["prohibited_edge_effects"])
    assert "ADAPTER_INFERENCE_SATISFIES_HARD_PREREQUISITE" in prohibited
    assert "TEST_RESULT_TO_AUTHORITY_GRANT" in prohibited


def test_event_registry_orders_deterministically_and_requires_decisions_for_authority() -> None:
    registry = load_json(PG_ROOT / "EVENT_TYPE_REGISTRY_v0_1.json")
    assert registry["ordering"] == ["first_valid_at", "precedence", "event_id"]
    events = registry["event_types"]
    names = [item["event_type"] for item in events]
    assert len(names) == len(set(names))
    precedence = [item["precedence"] for item in events]
    assert len(precedence) == len(set(precedence))
    by_name = {item["event_type"]: item for item in events}
    assert by_name["GENESIS_ACCEPTED"]["accepted_decision_required"] is True
    assert by_name["PR_MERGED"]["authority_effects"] == ["NONE"]
    assert by_name["QA_REVIEWED"]["authority_effects"] == ["NONE"]


def test_wp1_files_do_not_activate_reserved_capabilities() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            CONTRACT,
            PG_ROOT / "PROGRAMME_CLASS_REGISTRY_v0_1.json",
            PG_ROOT / "EDGE_TYPE_REGISTRY_v0_1.json",
            PG_ROOT / "EVENT_TYPE_REGISTRY_v0_1.json",
        ]
    )
    assert "FROZEN_CANDIDATE" in combined
    assert "PG-G6" in combined
    assert "PG-G7" in combined
    assert "may_self_grant_authority\": true" not in combined
