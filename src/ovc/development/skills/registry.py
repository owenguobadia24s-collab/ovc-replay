from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ovc.development.identity import canonical_json_bytes, canonical_sha256


class RegistryValidationError(ValueError):
    """Fail-closed DSAI registry/schema validation error."""


CORE_SCHEMAS = {
    "CapabilityRecord": "capability_record_v0_1.schema.json",
    "SkillManifest": "skill_manifest_v0_1.schema.json",
    "SkillCapabilityBinding": "skill_capability_binding_v0_1.schema.json",
    "SkillDependencyManifest": "skill_dependency_manifest_v0_1.schema.json",
    "SkillInputContract": "skill_input_contract_v0_1.schema.json",
    "SkillOutputContract": "skill_output_contract_v0_1.schema.json",
    "ToolPermissionProfile": "tool_permission_profile_v0_1.schema.json",
}
REGISTRY_FILES = {
    "capabilities": ("capabilities_v0_1.json", "capability_registry_v0_1.schema.json"),
    "skills": ("skills_v0_1.json", "skill_registry_v0_1.schema.json"),
    "permissions": ("permissions_v0_1.json", "permission_registry_v0_1.schema.json"),
    "tools": ("tools_v0_1.json", "tool_registry_v0_1.schema.json"),
    "execution_profiles": ("execution_profiles_v0_1.json", "execution_profile_registry_v0_1.schema.json"),
}


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryValidationError(f"cannot load {path}: {exc}") from exc


def _types(value: Any) -> set[str]:
    if value is None:
        return {"null"}
    if isinstance(value, bool):
        return {"boolean"}
    if isinstance(value, int):
        return {"integer", "number"}
    if isinstance(value, float):
        return {"number"}
    if isinstance(value, str):
        return {"string"}
    if isinstance(value, list):
        return {"array"}
    if isinstance(value, dict):
        return {"object"}
    return set()


def validate_against_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if expected is not None:
        allowed = {expected} if isinstance(expected, str) else set(expected)
        if not (_types(value) & allowed):
            raise RegistryValidationError(f"{path}: expected {sorted(allowed)}, got {type(value).__name__}")
    if "const" in schema and value != schema["const"]:
        raise RegistryValidationError(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise RegistryValidationError(f"{path}: unsupported enum value {value!r}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise RegistryValidationError(f"{path}: string too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise RegistryValidationError(f"{path}: pattern mismatch")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise RegistryValidationError(f"{path}: too few items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_against_schema(item, item_schema, f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = sorted(set(required) - set(value))
        if missing:
            raise RegistryValidationError(f"{path}: missing required keys {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise RegistryValidationError(f"{path}: unknown keys {unknown}")
        for key, child_schema in properties.items():
            if key in value:
                validate_against_schema(value[key], child_schema, f"{path}.{key}")


def _schema_dir(root: Path) -> Path:
    return root / "schemas/development/skills"


def validate_core_object(root: Path, object_type: str, value: dict[str, Any]) -> str:
    try:
        schema_name = CORE_SCHEMAS[object_type]
    except KeyError as exc:
        raise RegistryValidationError(f"unknown core object type {object_type}") from exc
    validate_against_schema(value, _load(_schema_dir(root) / schema_name))
    return canonical_sha256(value, role=f"DSAI_{object_type.upper()}")


def _unique(entries: list[dict[str, Any]], field: str, registry: str) -> None:
    values = [row.get(field) for row in entries]
    if any(value is None for value in values):
        raise RegistryValidationError(f"{registry}: missing {field}")
    if len(values) != len(set(values)):
        raise RegistryValidationError(f"{registry}: duplicate {field}")


def validate_registry_bundle(root: Path, bundle: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for name, (_, schema_name) in REGISTRY_FILES.items():
        if name not in bundle:
            raise RegistryValidationError(f"missing registry {name}")
        validate_against_schema(bundle[name], _load(_schema_dir(root) / schema_name), f"$.{name}")
        if bundle[name].get("projection_only") is not True or bundle[name].get("authority_effect") != "NONE":
            raise RegistryValidationError(f"{name}: registry projections cannot grant authority")

    capabilities = bundle["capabilities"]["entries"]
    skills = bundle["skills"]["entries"]
    permissions = bundle["permissions"]["entries"]
    tools = bundle["tools"]["entries"]
    execution_profiles = bundle["execution_profiles"]["entries"]

    for row in capabilities:
        validate_core_object(root, "CapabilityRecord", row)
    for row in permissions:
        validate_core_object(root, "ToolPermissionProfile", row)

    _unique(capabilities, "capability_id", "capabilities")
    _unique(skills, "skill_id", "skills")
    _unique(skills, "logical_name", "skills")
    _unique(permissions, "permission_profile_id", "permissions")
    _unique(tools, "tool_id", "tools")
    _unique(execution_profiles, "execution_profile_id", "execution_profiles")

    capability_ids = {row["capability_id"] for row in capabilities}
    permission_ids = {row["permission_profile_id"] for row in permissions}
    tool_ids = {row["tool_id"] for row in tools}

    for row in skills:
        required = row.get("required_capability_ids")
        if not isinstance(required, list) or not required:
            raise RegistryValidationError(f"skills: {row.get('skill_id')} requires explicit capabilities")
        unknown = sorted(set(required) - capability_ids)
        if unknown:
            raise RegistryValidationError(f"skills: unknown mandatory capabilities {unknown}")
        if row.get("release_ids"):
            _unique([{"release_id": release_id} for release_id in row["release_ids"]], "release_id", row["skill_id"])

    for row in execution_profiles:
        if row.get("authority_effect") != "NONE":
            raise RegistryValidationError("execution profile cannot grant authority")
        if row.get("permission_profile_id") not in permission_ids:
            raise RegistryValidationError("execution profile references unknown permission profile")
        unknown_tools = sorted(set(row.get("tool_ids", [])) - tool_ids)
        if unknown_tools:
            raise RegistryValidationError(f"execution profile references unknown tools {unknown_tools}")

    boundary = _load(root / "registries/development/skills/operator_boundaries_v0_1.json")
    if boundary.get("projection_only") is not True or boundary.get("authority_effect") != "NONE":
        raise RegistryValidationError("operator boundary projection cannot grant authority")
    if any(row.get("active") is not False for row in boundary.get("boundaries", [])):
        raise RegistryValidationError("WP1 operator boundary projection cannot activate authority")

    logical = {name: canonical_sha256(bundle[name], role=f"DSAI_{name.upper()}_REGISTRY") for name in sorted(bundle)}
    return {"status":"PASS","registry_hashes":logical,"bundle_hash":canonical_sha256(logical, role="DSAI_REGISTRY_BUNDLE"),"canonical_bytes":len(canonical_json_bytes(bundle))}


def load_and_validate_registries(root: Path) -> dict[str, Any]:
    registry_root = root / "registries/development/skills"
    bundle = {name: _load(registry_root / file_name) for name, (file_name, _) in REGISTRY_FILES.items()}
    return validate_registry_bundle(root, bundle)
