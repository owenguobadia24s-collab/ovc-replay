"""Boundary-candidate construction for C2E v0.2 shadow/replay execution.

Dependency-result rows describe observed upstream availability.  The frozen
boundary rule owns REQUIRED/OPTIONAL/WARNING meaning for each candidate.  A
rule's PROHIBITED dependencies are an absence constraint enforced first by the
C2E reverse-dependency firewall; they are therefore not required as handoff
rows (putting FDI/C2G/C2.5/C3 into the handoff would itself violate the
firewall).
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .dependency import SUCCESS, normalize_dependency_results
from .serialization import digest


class CandidateError(ValueError):
    pass


def _evaluate_rule_scoped_dependencies(
    dependencies: Mapping[str, Any], results: list[Mapping[str, Any]]
) -> dict[str, Any]:
    normalized = normalize_dependency_results(results)
    by_id = {row["dependency_id"]: row for row in normalized}
    groups = {
        "REQUIRED": [str(item) for item in dependencies.get("REQUIRED", [])],
        "OPTIONAL": [str(item) for item in dependencies.get("OPTIONAL", [])],
        "WARNING": [str(item) for item in dependencies.get("WARNING", [])],
        "PROHIBITED": [str(item) for item in dependencies.get("PROHIBITED", [])],
    }
    # Only upstream dependencies that may lawfully occur in a C2EInputFrame are
    # required as rows.  PROHIBITED dependencies are absence constraints.
    declared_upstream = groups["REQUIRED"] + groups["OPTIONAL"] + groups["WARNING"]
    missing = sorted(item for item in declared_upstream if item not in by_id)
    if missing:
        raise CandidateError(f"DEP_UNDECLARED_RESULT_MISSING:{','.join(missing)}")

    blocked: list[str] = []
    warnings: list[str] = []
    for dep_id in groups["REQUIRED"]:
        if by_id[dep_id]["status"] not in SUCCESS:
            blocked.append(f"DEP_REQUIRED_NOT_EVALUABLE:{dep_id}")
    for dep_id in groups["OPTIONAL"] + groups["WARNING"]:
        if by_id[dep_id]["status"] not in SUCCESS:
            warnings.append(f"DEPENDENCY_WARNING:{dep_id}")
    # Defence in depth for an already-normalized frame.  The handoff firewall
    # should make this branch unreachable for downstream OVC namespaces.
    for dep_id in groups["PROHIBITED"]:
        if dep_id in by_id:
            blocked.append(f"PROHIBITED_DEPENDENCY_PRESENT:{dep_id}")
    return {
        "evaluable": not blocked,
        "blocking_reason_codes": sorted(set(blocked)),
        "warning_reason_codes": sorted(set(warnings)),
        "dependency_results": normalized,
    }


def build_candidate(
    rule: Mapping[str, Any],
    frame: Mapping[str, Any],
    *,
    matched: bool,
    effective_time: str,
    confirmation_time: str | None = None,
    invalidated_by_actions: list[str] | None = None,
) -> dict[str, Any] | None:
    if not matched:
        return None
    dep_result = _evaluate_rule_scoped_dependencies(
        dict(rule.get("dependencies", {})), list(frame["evidence"].get("dependency_results", []))
    )
    if not dep_result["evaluable"]:
        return {
            "candidate_id": digest(
                "C2E.CANDIDATE.BLOCKED",
                {"rule": rule["boundary_rule_id"], "frame": frame["frame_id"], "effective_time": effective_time},
            ),
            "boundary_rule_id": rule["boundary_rule_id"],
            "candidate_type": rule["candidate_type"],
            "lifecycle_action": rule["lifecycle_action"],
            "priority_class": int(rule["priority_class"]),
            "frame_id": frame["frame_id"],
            "effective_time": effective_time,
            "confirmation_time": confirmation_time or effective_time,
            "first_valid_time": max(frame["chronology"]["first_valid_time"], confirmation_time or effective_time),
            "evaluable": False,
            "reason_codes": dep_result["blocking_reason_codes"],
            "warning_reason_codes": dep_result["warning_reason_codes"],
            "invalidated_by_actions": sorted(set(invalidated_by_actions or [])),
        }
    identity = {
        "rule": rule["boundary_rule_id"],
        "candidate_type": rule["candidate_type"],
        "frame": frame["frame_id"],
        "effective_time": effective_time,
        "confirmation_time": confirmation_time or effective_time,
    }
    return {
        "candidate_id": digest("C2E.CANDIDATE", identity, length=32),
        "boundary_rule_id": rule["boundary_rule_id"],
        "candidate_type": rule["candidate_type"],
        "lifecycle_action": rule["lifecycle_action"],
        "priority_class": int(rule["priority_class"]),
        "frame_id": frame["frame_id"],
        "effective_time": effective_time,
        "confirmation_time": confirmation_time or effective_time,
        "first_valid_time": max(frame["chronology"]["first_valid_time"], confirmation_time or effective_time),
        "evaluable": True,
        "reason_codes": [],
        "warning_reason_codes": dep_result["warning_reason_codes"],
        "invalidated_by_actions": sorted(set(invalidated_by_actions or [])),
        "source": copy.deepcopy(identity),
    }
