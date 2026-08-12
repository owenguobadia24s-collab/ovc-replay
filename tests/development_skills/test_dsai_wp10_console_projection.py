from __future__ import annotations

import ast
import json
from pathlib import Path

from ovc.development.skills import SECTION_ORDER, build_skill_control_read_model

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/dsai_control_sources.json"
MANIFEST = ROOT / "fixtures/research_console_vnext/console_pack_v0_1/manifest.json"
SCHEMA = ROOT / "schemas/development/skills/skill_control_read_model_v0_1.schema.json"
CONTRACT = ROOT / "contracts/development/skills/console_readonly_projection_v0_1.json"
ROUTER = ROOT / "apps/research_api/routers/system.py"
APP = ROOT / "apps/research_api/app.py"
PRODUCTION = ROOT / "apps/research_console_vnext/src/production/ProductionConsole.tsx"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build():
    return build_skill_control_read_model(_load(FIXTURE))


def test_read_model_rebuild_is_deterministic_and_complete():
    first = _build()
    second = _build()
    assert first == second
    assert first["schema_id"] == "ovc-dsai-skill-control-read-model/v1"
    assert first["mode"] == "READ_ONLY_PROJECTION"
    assert first["authority_effect"] == "NONE"
    assert list(first["sections"]) == list(SECTION_ORDER)
    assert first["missing_sections"] == []
    assert first["forbidden_controls"] == ["APPROVE", "ENABLE", "MERGE", "REVOKE", "RUN", "TRUST"]


def test_every_projected_section_retains_source_identity_and_missingness():
    model = _build()
    for name in SECTION_ORDER:
        projected = model["sections"][name]
        assert projected["source_identity"] == model["source_identity"]
        assert isinstance(projected["missing"], bool)
        assert projected["authority_effect"] == "NONE"

    source = _load(FIXTURE)
    source["sections"]["incidents"] = None
    missing = build_skill_control_read_model(source)
    assert missing["sections"]["incidents"]["value"] is None
    assert missing["sections"]["incidents"]["missing"] is True
    assert "incidents" in missing["missing_sections"]


def test_inferred_edges_cannot_become_hard_prerequisite_or_authority():
    model = _build()
    edges = model["sections"]["dependencies"]["value"]
    inferred = [row for row in edges if row.get("inferred") is True]
    assert inferred
    assert all(row["hard_prerequisite"] is False for row in inferred)
    assert all(row["authority_effect"] == "NONE" for row in inferred)


def test_contract_and_closed_schema_freeze_get_only_none_delta_surface():
    contract = _load(CONTRACT)
    schema = _load(SCHEMA)
    assert contract["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert contract["authority_delta"] == "NONE"
    assert contract["research_console_authority"] == "FIXTURE_ONLY_LOCAL_READ_ONLY"
    assert contract["api_path"] == "/api/v1/control/skills"
    assert contract["allowed_methods"] == ["GET"]
    assert contract["forbidden_methods"] == ["POST", "PUT", "PATCH", "DELETE"]
    assert contract["projection_rules"]["real_source_resolution"] is False
    assert schema["additionalProperties"] is False
    assert schema["properties"]["authority_effect"]["const"] == "NONE"
    assert schema["properties"]["mode"]["const"] == "READ_ONLY_PROJECTION"


def test_fixture_pack_registers_dsai_projection_without_changing_rcn_authority():
    manifest = _load(MANIFEST)
    assert manifest["mode"] == "FIXTURE_ONLY"
    assert manifest["data_classification"] == "SYNTHETIC_FIXTURE"
    assert manifest["evidence_status"] == "NON_EVIDENTIARY"
    assert manifest["authority_effect"] == "NONE"
    assert manifest["resources"]["dsai_control_sources"] == "dsai_control_sources.json"
    assert "ovc-dsai-skill-control-read-model/v1" in manifest["source_identity"]["schema_ids"]


def test_control_api_binding_is_get_only_and_global_mutation_barrier_remains():
    tree = ast.parse(ROUTER.read_text(encoding="utf-8"))
    methods = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            if decorator.args[0].value == "/control/skills":
                methods.append(decorator.func.attr.lower())
    assert methods == ["get"]
    router_text = ROUTER.read_text(encoding="utf-8")
    assert "build_skill_control_read_model" in router_text
    app_text = APP.read_text(encoding="utf-8")
    assert '_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}' in app_text
    assert 'status_code=405' in app_text


def test_existing_control_visual_surface_remains_explicitly_no_write():
    text = PRODUCTION.read_text(encoding="utf-8")
    assert "NO WRITE SURFACE" in text
    assert "approval, activation, merge and execution controls are intentionally absent" in text
    assert 'data-testid="production-primary-canvas"' in text
