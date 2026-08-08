"""Priority/compatibility resolution with post-effect closure for C2E v0.2."""
from __future__ import annotations

import copy
from itertools import combinations
from typing import Any, Mapping, Sequence

from .boundary_pack import compatibility_disposition


class ResolverError(ValueError):
    pass


def _semantic_conflict(pack: Mapping[str, Any], group: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for left, right in combinations(group, 2):
        disposition = compatibility_disposition(pack, left["candidate_type"], right["candidate_type"])
        if disposition in {"UNDECLARED_FAIL_CLOSED", "INCOMPATIBLE_CONFLICT", "MUTUALLY_EXCLUSIVE_BY_RULE"}:
            reasons.append(f"{left['candidate_type']}::{right['candidate_type']}::{disposition}")
        elif left["priority_class"] == right["priority_class"] and disposition == "ORDERED_BY_PRIORITY":
            reasons.append(f"{left['candidate_type']}::{right['candidate_type']}::EQUAL_PRIORITY_NOT_ORDERABLE")
    return bool(reasons), sorted(reasons)


def resolve_candidates(pack: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [copy.deepcopy(dict(item)) for item in candidates if item is not None and item.get("evaluable", True)]
    normalized.sort(key=lambda row: (int(row["priority_class"]), str(row["candidate_id"])))
    # Equal-priority incompatibility is resolved semantically before lexical ordering can matter.
    for priority in sorted({int(row["priority_class"]) for row in normalized}):
        same = [row for row in normalized if int(row["priority_class"]) == priority]
        conflict, reasons = _semantic_conflict(pack, same)
        if conflict:
            return {"status":"CONFLICT","reason_codes":["C2E_EQUAL_PRIORITY_INCOMPATIBLE", *reasons],"resolved":[],"suppressed":[],"candidates":sorted(normalized,key=lambda r:r["candidate_id"])}

    resolved: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    applied_actions: set[str] = set()
    for candidate in normalized:
        if applied_actions.intersection(candidate.get("invalidated_by_actions", [])):
            suppressed.append({**candidate, "suppression_reason":"HIGHER_PRIORITY_EFFECT_INVALIDATED"})
            continue
        # Revalidate this candidate against every surviving higher-priority effect.
        conflict = False
        for earlier in resolved:
            disposition = compatibility_disposition(pack, earlier["candidate_type"], candidate["candidate_type"])
            if disposition in {"UNDECLARED_FAIL_CLOSED","INCOMPATIBLE_CONFLICT","MUTUALLY_EXCLUSIVE_BY_RULE"}:
                conflict = True
                break
        if conflict:
            return {"status":"CONFLICT","reason_codes":["C2E_COMPATIBILITY_CLOSURE_FAILED"],"resolved":resolved,"suppressed":suppressed,"candidates":normalized}
        resolved.append(candidate)
        applied_actions.add(candidate["lifecycle_action"])

    # Final compound closure: every pair must still be jointly lawful. Different-priority
    # ORDERED_BY_PRIORITY is lawful; equal priority required COMPATIBLE_COMPOUND above.
    conflict, reasons = _semantic_conflict(pack, resolved)
    if conflict:
        return {"status":"CONFLICT","reason_codes":["C2E_COMPATIBILITY_CLOSURE_FAILED", *reasons],"resolved":[],"suppressed":suppressed,"candidates":normalized}
    return {"status":"RESOLVED","reason_codes":[],"resolved":resolved,"suppressed":suppressed,"candidates":normalized}
