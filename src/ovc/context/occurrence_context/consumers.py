from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .builder import OccurrenceContextError
from .serialization import canonical_json, sha256_payload

ALLOWED_CONSUMER_ROLES = {"IDENTITY_BINDING", "STRATIFIER", "FILTER", "DISPLAY_ONLY"}
ALLOWED_DEPENDENCY_DISPOSITIONS = {"REQUIRED", "OPTIONAL", "FORBIDDEN"}
FORBIDDEN_WHOLE_ENVELOPE_PATHS = {"", "*", ".", "occurrence_context", "OccurrenceContext"}


def _resolve_path(value: Mapping[str, Any], path: str) -> Any:
    if path in FORBIDDEN_WHOLE_ENVELOPE_PATHS or path.endswith(".*"):
        raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "whole-envelope consumption is forbidden")
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def validate_consumption_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "consumer_kind",
        "consumer_version",
        "accepted_context_schema_versions",
        "accepted_context_pack_versions",
        "field_dependencies",
        "admissible_cutoff_rule",
        "missingness_behavior",
        "authority_effect",
    }
    missing = sorted(field for field in required if field not in manifest)
    if missing:
        raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", ",".join(missing))
    if manifest["authority_effect"] != "NONE":
        raise OccurrenceContextError("OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED", "consumer authority must remain NONE")
    if "0.1" not in set(manifest["accepted_context_schema_versions"]):
        raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "schema v0.1 not accepted")
    dependencies: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in manifest["field_dependencies"]:
        path = str(item.get("field_path", ""))
        if path in FORBIDDEN_WHOLE_ENVELOPE_PATHS or path.endswith(".*"):
            raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "whole-envelope dependency forbidden")
        if path in seen:
            raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "duplicate field dependency")
        seen.add(path)
        dependency = str(item.get("dependency", ""))
        role = str(item.get("role", ""))
        if dependency not in ALLOWED_DEPENDENCY_DISPOSITIONS:
            raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "unknown dependency disposition")
        if role == "REPRESENTATION_INPUT" or role not in ALLOWED_CONSUMER_ROLES:
            raise OccurrenceContextError("OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED")
        dependencies.append({"field_path": path, "dependency": dependency, "role": role})
    payload = {
        "consumer_kind": str(manifest["consumer_kind"]),
        "consumer_version": str(manifest["consumer_version"]),
        "accepted_context_schema_versions": sorted(set(str(item) for item in manifest["accepted_context_schema_versions"])),
        "accepted_context_pack_versions": sorted(set(str(item) for item in manifest["accepted_context_pack_versions"])),
        "field_dependencies": sorted(dependencies, key=lambda item: item["field_path"]),
        "admissible_cutoff_rule": str(manifest["admissible_cutoff_rule"]),
        "missingness_behavior": str(manifest["missingness_behavior"]),
        "authority_effect": "NONE",
    }
    payload["manifest_hash"] = sha256_payload("OVC.OCCURRENCE_CONTEXT.CONSUMER_MANIFEST", payload)
    return payload


def project_context(context: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_consumption_manifest(manifest)
    if str(context.get("schema_version")) not in validated["accepted_context_schema_versions"]:
        raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "context schema not accepted")
    if str(context.get("context_pack_version")) not in validated["accepted_context_pack_versions"]:
        raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", "context pack not accepted")
    projected: dict[str, Any] = {}
    for dep in validated["field_dependencies"]:
        path = dep["field_path"]
        if dep["dependency"] == "FORBIDDEN":
            try:
                value = _resolve_path(context, path)
            except KeyError:
                continue
            if value not in (None, [], {}, ""):
                raise OccurrenceContextError("OC_ROLE_UNDECLARED_FIELD", f"forbidden consumer field populated: {path}")
            continue
        try:
            value = _resolve_path(context, path)
        except KeyError:
            if dep["dependency"] == "REQUIRED":
                raise OccurrenceContextError("OC_AVAIL_REQUIRED_DEPENDENCY_MISSING", path)
            continue
        projected[path] = deepcopy(value)
    result = {
        "consumer_kind": validated["consumer_kind"],
        "consumer_version": validated["consumer_version"],
        "occurrence_context_id": str(context["occurrence_context_id"]),
        "context_first_valid_time": str(context["first_valid_time"]),
        "fields": projected,
        "manifest_hash": validated["manifest_hash"],
        "authority_effect": "NONE",
    }
    canonical_json(result)
    return result


def assert_c2p_identity_payload_context_free(payload: Mapping[str, Any]) -> None:
    forbidden_tokens = {
        "occurrence_context_id",
        "session",
        "session_id",
        "a_l_block_id",
        "calendar_year",
        "calendar_month",
        "era",
        "market_condition",
        "mcarb",
        "auxiliary_refs",
        "family_id",
    }
    overlap = {str(key).lower() for key in payload}.intersection(forbidden_tokens)
    if overlap:
        raise OccurrenceContextError("OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED", ",".join(sorted(overlap)))
