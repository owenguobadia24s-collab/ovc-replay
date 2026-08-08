"""Dependency-specific admissibility results for the C2E v0.2 handoff."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

SUCCESS = {"AVAILABLE", "COMPUTABLE", "ASSURED", "ELIGIBLE", "AUTHORIZED", "PRESENT"}
FAILURE = {"MISSING", "UNAVAILABLE", "NOT_COMPUTABLE", "CENSORED", "CONFLICTED", "INELIGIBLE", "UNAUTHORIZED"}
ROLES = {"REQUIRED", "OPTIONAL", "WARNING_ONLY", "PROHIBITED"}


class DependencyError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise DependencyError(marker)


def normalize_dependency_results(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in results:
        row = copy.deepcopy(dict(raw))
        dependency_id = str(row.get("dependency_id", ""))
        role = str(row.get("role", "")).upper()
        status = str(row.get("status", "")).upper()
        _require(bool(dependency_id), "DEPENDENCY_ID_REQUIRED")
        _require(dependency_id not in seen, "DUPLICATE_DEPENDENCY_ID")
        _require(role in ROLES, "DEPENDENCY_ROLE_INVALID")
        _require(status in SUCCESS | FAILURE | {"NOT_APPLICABLE", "NOT_EVALUATED"}, "DEPENDENCY_STATUS_INVALID")
        seen.add(dependency_id)
        normalized.append({
            "dependency_id": dependency_id,
            "role": role,
            "status": status,
            "source_record_ids": sorted({str(item) for item in row.get("source_record_ids", [])}),
            "reason_codes": sorted({str(item) for item in row.get("reason_codes", [])}),
        })
    normalized.sort(key=lambda item: item["dependency_id"])
    return normalized


def evaluate_rule_dependencies(
    declared_dependency_ids: Sequence[str],
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_dependency_results(results)
    by_id = {row["dependency_id"]: row for row in normalized}
    declared = [str(item) for item in declared_dependency_ids]
    missing = sorted(item for item in declared if item not in by_id)
    _require(not missing, f"DEP_UNDECLARED_RESULT_MISSING:{','.join(missing)}")
    blocked = []
    warnings = []
    for dep_id in declared:
        row = by_id[dep_id]
        if row["role"] == "PROHIBITED" and row["status"] in SUCCESS:
            blocked.append(f"PROHIBITED_DEPENDENCY_PRESENT:{dep_id}")
        elif row["role"] == "REQUIRED" and row["status"] not in SUCCESS:
            blocked.append(f"DEP_REQUIRED_NOT_EVALUABLE:{dep_id}")
        elif row["role"] in {"OPTIONAL", "WARNING_ONLY"} and row["status"] not in SUCCESS:
            warnings.append(f"DEPENDENCY_WARNING:{dep_id}")
    return {
        "evaluable": not blocked,
        "blocking_reason_codes": blocked,
        "warning_reason_codes": warnings,
        "dependency_results": normalized,
    }
