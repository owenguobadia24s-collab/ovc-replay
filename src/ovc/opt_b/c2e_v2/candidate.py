"""Synthetic/shadow boundary-candidate construction for C2E2-WP3.

This module does not define empirical boundary predicates.  It converts an
already-evaluated synthetic rule result into a deterministic candidate object
under an exact frozen boundary pack.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .dependency import evaluate_rule_dependencies
from .serialization import digest


class CandidateError(ValueError):
    pass


def build_candidate(rule: Mapping[str, Any], frame: Mapping[str, Any], *, matched: bool, effective_time: str, confirmation_time: str | None = None, invalidated_by_actions: list[str] | None = None) -> dict[str, Any] | None:
    if not matched:
        return None
    dependencies = rule.get("dependencies", {})
    declared = list(dependencies.get("REQUIRED", [])) + list(dependencies.get("OPTIONAL", [])) + list(dependencies.get("WARNING", [])) + list(dependencies.get("PROHIBITED", []))
    dep_result = evaluate_rule_dependencies(declared, frame["evidence"].get("dependency_results", []))
    if not dep_result["evaluable"]:
        return {
            "candidate_id": digest("C2E.CANDIDATE.BLOCKED", {"rule":rule["boundary_rule_id"],"frame":frame["frame_id"],"effective_time":effective_time}),
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
            "invalidated_by_actions": sorted(set(invalidated_by_actions or [])),
        }
    identity = {
        "rule": rule["boundary_rule_id"], "candidate_type": rule["candidate_type"],
        "frame": frame["frame_id"], "effective_time": effective_time,
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
        "invalidated_by_actions": sorted(set(invalidated_by_actions or [])),
        "source": copy.deepcopy(identity),
    }
