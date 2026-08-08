"""Boundary-pack identity and fail-closed compatibility helpers for C2E v0.2."""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .serialization import canonical_decimal, digest, sha256_hex


class BoundaryPackError(ValueError):
    pass


COMPATIBILITY_DISPOSITIONS = {
    "COMPATIBLE_COMPOUND",
    "ORDERED_BY_PRIORITY",
    "MUTUALLY_EXCLUSIVE_BY_RULE",
    "INCOMPATIBLE_CONFLICT",
}


IDENTITY_PARAMETER_PRECISIONS = {
    "threshold": 6,
    "confirmation_delay_seconds": 0,
    "maximum_open_duration_seconds": 0,
}


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise BoundaryPackError(marker)


def _normalize_parameters(parameters: Mapping[str, Any], precision_registry: Mapping[str, int] | None = None) -> dict[str, Any]:
    precision_registry = dict(precision_registry or {})
    normalized: dict[str, Any] = {}
    for key in sorted(parameters):
        value = parameters[key]
        precision = precision_registry.get(key)
        if precision is None:
            _require(not isinstance(value, float), f"PACK_FLOAT_WITHOUT_PRECISION:{key}")
            normalized[key] = copy.deepcopy(value)
        else:
            normalized[key] = canonical_decimal(value, precision)
    return normalized


def _normalize_rule(rule: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(rule))
    for key in ("boundary_rule_id", "lifecycle_action", "candidate_type"):
        _require(bool(result.get(key)), f"BOUNDARY_RULE_REQUIRED:{key}")
    priority = result.get("priority_class")
    _require(isinstance(priority, int) and 1 <= priority <= 8, "BOUNDARY_PRIORITY_INVALID")
    dependencies = result.get("dependencies", {})
    _require(isinstance(dependencies, Mapping), "BOUNDARY_DEPENDENCIES_INVALID")
    normalized_deps = {}
    for role in ("REQUIRED", "OPTIONAL", "WARNING", "ONE_OF", "PROHIBITED"):
        values = dependencies.get(role, [])
        _require(isinstance(values, list), f"BOUNDARY_DEPENDENCY_ROLE_INVALID:{role}")
        normalized_deps[role] = sorted({str(item) for item in values})
    result["dependencies"] = normalized_deps
    result["parameters"] = _normalize_parameters(result.get("parameters", {}), result.get("parameter_precisions", {}))
    result["parameter_precisions"] = {str(k): int(v) for k, v in sorted(result.get("parameter_precisions", {}).items())}
    return result


def _compatibility_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((str(a), str(b))))


def normalize_compatibility(entries: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for raw in entries:
        row = copy.deepcopy(dict(raw))
        a, b = _compatibility_key(row.get("candidate_type_a", ""), row.get("candidate_type_b", ""))
        _require(bool(a) and bool(b), "COMPATIBILITY_TYPES_REQUIRED")
        _require(a != b, "COMPATIBILITY_SELF_PAIR_DENIED")
        _require((a, b) not in seen, "DUPLICATE_COMPATIBILITY_PAIR")
        disposition = str(row.get("disposition", ""))
        _require(disposition in COMPATIBILITY_DISPOSITIONS, "COMPATIBILITY_DISPOSITION_INVALID")
        seen.add((a, b))
        normalized.append({"candidate_type_a": a, "candidate_type_b": b, "disposition": disposition})
    return sorted(normalized, key=lambda row: (row["candidate_type_a"], row["candidate_type_b"]))


def logical_pack_payload(pack: Mapping[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(dict(pack))
    rules = [_normalize_rule(item) for item in raw.get("rules", [])]
    rules.sort(key=lambda item: item["boundary_rule_id"])
    _require(bool(rules), "BOUNDARY_PACK_RULES_REQUIRED")
    scope = copy.deepcopy(raw.get("population_scope", {}))
    _require(bool(scope), "BOUNDARY_PACK_SCOPE_REQUIRED")
    ownership = copy.deepcopy(raw.get("ownership", {}))
    _require(ownership.get("peer_mode") == "SINGLE_OWNER", "OWNERSHIP_DEFAULT_MUST_BE_SINGLE_OWNER")
    semantic = {
        "version": str(raw.get("version", "")),
        "supersedes": raw.get("supersedes"),
        "population_scope": scope,
        "rules": rules,
        "compatibility_matrix": normalize_compatibility(raw.get("compatibility_matrix", [])),
        "ownership": ownership,
        "topology": copy.deepcopy(raw.get("topology", {})),
        "discontinuity": copy.deepcopy(raw.get("discontinuity", {})),
        "conflict_policy": copy.deepcopy(raw.get("conflict_policy", {})),
        "implementation_hashes": {str(k): str(v) for k, v in sorted(raw.get("implementation_hashes", {}).items())},
        "registry_hashes": {str(k): str(v) for k, v in sorted(raw.get("registry_hashes", {}).items())},
        "authority": str(raw.get("authority", "")),
    }
    _require(semantic["version"] != "", "BOUNDARY_PACK_VERSION_REQUIRED")
    _require(semantic["authority"] in {"CANDIDATE", "SHADOW"}, "BOUNDARY_PACK_ACTIVE_AUTHORITY_DENIED")
    return semantic


def boundary_pack_id(pack: Mapping[str, Any]) -> str:
    return digest("C2E.BOUNDARY.PACK", logical_pack_payload(pack), length=32)


def freeze_pack(pack: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(pack))
    logical = logical_pack_payload(result)
    result["boundary_pack_id"] = boundary_pack_id(result)
    result["logical_sha256"] = sha256_hex(logical)
    result["active"] = False
    result["canonical"] = False
    return result


def compatibility_disposition(pack: Mapping[str, Any], candidate_type_a: str, candidate_type_b: str) -> str:
    key = _compatibility_key(candidate_type_a, candidate_type_b)
    for row in normalize_compatibility(pack.get("compatibility_matrix", [])):
        if (row["candidate_type_a"], row["candidate_type_b"]) == key:
            return row["disposition"]
    return "UNDECLARED_FAIL_CLOSED"
