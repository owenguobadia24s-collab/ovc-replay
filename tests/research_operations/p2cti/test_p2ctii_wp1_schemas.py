from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "schemas/research_operations/p2cti"
REGISTRY_ROOT = ROOT / "registries/research_operations/p2cti"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp1_schema_files_are_draft_2020_12_and_closed_at_top_level():
    names = [
        "p2cti_inventory_v0_1.schema.json",
        "p2cti_source_frontier_v0_1.schema.json",
        "p2cti_control_records_v0_1.schema.json",
        "p2cti_current_pointer_v0_1.schema.json",
    ]
    for name in names:
        schema = load(SCHEMA_ROOT / name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("https://ovc.local/schemas/research_operations/p2cti/")

    control = load(SCHEMA_ROOT / "p2cti_control_records_v0_1.schema.json")
    assert control["additionalProperties"] is False
    assert "authority_effect" in control["required"]
    assert control["properties"]["authority_effect"]["const"] == "NONE"


def test_inventory_schema_enforces_reference_only_entry_shape():
    schema = load(SCHEMA_ROOT / "p2cti_inventory_v0_1.schema.json")
    entry = schema["$defs"]["Entry"]
    owner_ref = schema["$defs"]["OwnerRef"]
    assert "source_object_ref" in entry["required"]
    assert "scientific_payload" not in entry["properties"]
    assert owner_ref["properties"]["scientific_payload_copied"]["const"] is False
    assert entry["additionalProperties"] is False


def test_bootstrap_manifest_freezes_7_19_4_and_30():
    schema = load(SCHEMA_ROOT / "p2cti_source_frontier_v0_1.schema.json")
    bootstrap = schema["$defs"]["BootstrapMigrationManifest"]["properties"]
    assert bootstrap["expected_total"]["const"] == 30
    counts = bootstrap["expected_class_counts"]["properties"]
    assert counts["EXTERNAL_THEORY_RECORD"]["const"] == 7
    assert counts["IN_HOUSE_THEORY_RECORD"]["const"] == 19
    assert counts["ARCHITECTURE_NEED_SEED"]["const"] == 4
    assert bootstrap["entry_ids"]["minItems"] == 30
    assert bootstrap["entry_ids"]["maxItems"] == 30
    assert bootstrap["no_scientific_payload_rewrite"]["const"] is True


def test_owner_and_operational_registries_preserve_owner_semantics():
    owner = load(REGISTRY_ROOT / "P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json")
    operational = load(REGISTRY_ROOT / "P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json")
    assert owner["resolution_rule"] == "DECLARED_OWNER_ONLY"
    assert owner["fallback_by_recency_path_title"] == "FORBIDDEN"
    assert owner["missing_owner_evidence"] == "UNRESOLVED"
    assert operational["next_theory_work_authority"] == "ADVISORY_ONLY"
    assert operational["architecture_need_owner"] == "RCCR"
    assert operational["method_gap_precedes_architecture_pressure"] is True
    assert operational["silent_truncation"] == "FORBIDDEN"
