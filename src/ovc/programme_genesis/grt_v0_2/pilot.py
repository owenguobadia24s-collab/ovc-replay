"""GRT2-G2.5 limited-enforcement pilot evaluation and evidence helpers.

This module implements only the operator-approved G2.5 admission surface. It
must not be confused with GRT2-G3: full Repository Constitution enforcement,
DebtFloor generation 0 and required GRT-EXACT remain separately reserved.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from .reference import _artifact_type_from_path


class PilotEvidenceError(ValueError):
    pass


_ALLOWED_CANDIDATE_CLASSES = {"REAL_ORDINARY", "QUALIFICATION_INJECTION"}


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise PilotEvidenceError("GRT2_G2_5_TIME_INVALID")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PilotEvidenceError("GRT2_G2_5_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise PilotEvidenceError("GRT2_G2_5_TIME_MUST_BE_OFFSET_AWARE")
    return parsed


def validate_active_pilot_authority(authority: Mapping[str, Any]) -> None:
    if authority.get("gate_id") != "GRT2-G2.5":
        raise PilotEvidenceError("GRT2_G2_5_AUTHORITY_GATE_MISMATCH")
    if authority.get("authority_status") != "ACTIVE":
        raise PilotEvidenceError("GRT2_G2_5_AUTHORITY_NOT_ACTIVE")
    if authority.get("enforcement_mode") != "LIMITED_NEW_ARTIFACT_ENFORCEMENT":
        raise PilotEvidenceError("GRT2_G2_5_AUTHORITY_MODE_MISMATCH")
    if authority.get("g3_status") != "NOT_AUTHORISED":
        raise PilotEvidenceError("GRT2_G2_5_G3_BOUNDARY_NOT_PRESERVED")


def _root_map(root_registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = root_registry.get("roots")
    if not isinstance(rows, list) or not rows:
        raise PilotEvidenceError("GRT2_G2_5_ROOT_REGISTRY_UNAVAILABLE")
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise PilotEvidenceError("GRT2_G2_5_ROOT_REGISTRY_INVALID")
        path = row.get("path")
        if not isinstance(path, str) or not path or "/" in path:
            raise PilotEvidenceError("GRT2_G2_5_ROOT_REGISTRY_INVALID")
        if path in out:
            raise PilotEvidenceError("GRT2_G2_5_ROOT_REGISTRY_DUPLICATE")
        out[path] = row
    return out


def _normalize_change(change: Mapping[str, Any]) -> dict[str, Any]:
    status = change.get("status")
    path = change.get("path")
    old_path = change.get("old_path")
    if status not in {"A", "M", "D", "R", "C", "T"}:
        raise PilotEvidenceError("GRT2_G2_5_CHANGE_STATUS_INVALID")
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        raise PilotEvidenceError("GRT2_G2_5_CHANGE_PATH_INVALID")
    if status in {"R", "C"} and (not isinstance(old_path, str) or not old_path):
        raise PilotEvidenceError("GRT2_G2_5_CHANGE_OLD_PATH_REQUIRED")
    return {"status": status, "path": path, "old_path": old_path}


def evaluate_limited_candidate(
    *,
    changes: Sequence[Mapping[str, Any]],
    root_registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate the exact G2.5 limited scope over an already-materialized diff.

    G2.5 blocks only new governed additions/new roots/new workflows when they
    violate applicable law, plus writes to forbidden/deprecated roots. Changes
    caused solely by modifying pre-existing artifacts remain shadow-only.
    """
    roots = _root_map(root_registry)
    normalized = [_normalize_change(change) for change in changes]
    rows: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    not_evaluable: list[dict[str, Any]] = []
    scopes: set[str] = set()

    for change in normalized:
        status = change["status"]
        path = change["path"]
        root = path.split("/", 1)[0]
        root_record = roots.get(root)
        is_new_write = status in {"A", "R", "C"}
        is_new_root = is_new_write and root_record is None
        is_workflow = path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))
        artifact_type = _artifact_type_from_path(path)
        row: dict[str, Any] = {
            "status": status,
            "path": path,
            "old_path": change.get("old_path"),
            "root": root,
            "artifact_type": artifact_type,
            "pilot_scopes": [],
            "findings": [],
            "disposition": "PASS",
        }

        if not is_new_write:
            row["pilot_scopes"].append("PREEXISTING_ARTIFACT_CHANGE_SHADOW_ONLY")
            scopes.add("PREEXISTING_ARTIFACT_CHANGE_SHADOW_ONLY")
            rows.append(row)
            continue

        if is_new_root:
            row["pilot_scopes"].append("NEW_PERMANENT_ROOT")
            scopes.add("NEW_PERMANENT_ROOT")
            finding = {
                "reason_code": "GRT2_G2_5_NEW_PERMANENT_ROOT_UNREGISTERED",
                "path": path,
                "admission": "FAIL",
            }
            row["findings"].append(finding)
            row["disposition"] = "FAIL"
            blocking.append(finding)
            rows.append(row)
            continue

        if root_record.get("governed") is True:
            row["pilot_scopes"].append("ADDED_GOVERNED_ARTIFACT")
            scopes.add("ADDED_GOVERNED_ARTIFACT")
        if is_workflow:
            row["pilot_scopes"].append("NEW_WORKFLOW")
            scopes.add("NEW_WORKFLOW")

        new_write_policy = root_record.get("new_write_policy")
        if new_write_policy in {"DEPRECATED_NO_NEW_WRITES", "FORBIDDEN_NO_NEW_WRITES"}:
            row["pilot_scopes"].append("FORBIDDEN_OR_DEPRECATED_ROOT_WRITE")
            scopes.add("FORBIDDEN_OR_DEPRECATED_ROOT_WRITE")
            finding = {
                "reason_code": "GRT2_G2_5_FORBIDDEN_ROOT_NEW_WRITE",
                "path": path,
                "admission": "FAIL",
            }
            row["findings"].append(finding)
            row["disposition"] = "FAIL"
            blocking.append(finding)

        if root_record.get("governed") is True and artifact_type is None:
            finding = {
                "reason_code": "GRT2_G2_5_ADDED_GOVERNED_ARTIFACT_CLASS_NOT_EVALUABLE",
                "path": path,
                "admission": "NOT_EVALUABLE",
            }
            row["findings"].append(finding)
            if row["disposition"] != "FAIL":
                row["disposition"] = "NOT_EVALUABLE"
            not_evaluable.append(finding)

        rows.append(row)

    if blocking:
        decision = "FAIL"
    elif not_evaluable:
        decision = "NOT_EVALUABLE"
    else:
        decision = "PASS"

    full_g3_unresolved = sorted(
        {
            family
            for row in rows
            if row["status"] != "D"
            for family in (
                "CURRENT_STATE_AND_LIFECYCLE",
                "OWNERSHIP",
                "GENESIS_BINDINGS",
                "DEPENDENCIES",
                "COMPANIONS_AND_ORPHANS",
                "SUPERSESSION",
            )
        }
    )
    full_g3_status = "PASS" if not full_g3_unresolved else "NOT_EVALUABLE"

    return {
        "schema": "ovc-grt2-g2-5-candidate-evaluation/v1",
        "pilot_scope_classification": sorted(scopes) or ["NO_G2_5_BLOCKING_SCOPE_CHANGE"],
        "pilot_decision": decision,
        "pilot_findings": blocking + not_evaluable,
        "change_evaluations": rows,
        "full_g3_shadow_status": full_g3_status,
        "full_g3_shadow_findings": [
            {"reason_code": "FULL_G3_RULE_FAMILY_NOT_MATERIALIZED_FOR_REPLAY", "rule_family": family}
            for family in full_g3_unresolved
        ],
        "escape_review": {"unresolved_escape_count": 1 if decision == "FAIL" else 0},
        "false_positive_review": {"unresolved_blocking_false_positive_count": 0},
        "false_negative_probes": {"unresolved_false_negative_count": 0},
        "scope_leakage_review": {"preexisting_modification_only_block_count": 0},
        "authority_effect": "NONE_G2_5_EVIDENCE_ONLY",
        "g3_authority_effect": "NONE",
    }


def candidate_is_eligible(record: Mapping[str, Any], *, pilot_start: str) -> bool:
    if record.get("candidate_class") not in _ALLOWED_CANDIDATE_CLASSES:
        return False
    merged_at = record.get("merged_at")
    if not isinstance(merged_at, str):
        return False
    if _parse_time(merged_at) < _parse_time(pilot_start):
        return False
    if record.get("exact_tree_replay") is not True:
        return False
    return record.get("pilot_decision") in {"PASS", "FAIL"}


def summarize_pilot(
    *,
    candidate_records: Sequence[Mapping[str, Any]],
    pilot_start: str,
    evaluated_at: str,
    minimum_elapsed_hours: int = 24,
    minimum_eligible_candidate_count: int = 8,
) -> dict[str, Any]:
    start = _parse_time(pilot_start)
    end = _parse_time(evaluated_at)
    elapsed_hours = (end - start).total_seconds() / 3600.0
    if elapsed_hours < 0:
        raise PilotEvidenceError("GRT2_G2_5_ELAPSED_NEGATIVE")

    eligible = [record for record in candidate_records if candidate_is_eligible(record, pilot_start=pilot_start)]
    real_count = sum(record.get("candidate_class") == "REAL_ORDINARY" for record in eligible)
    injection_count = sum(record.get("candidate_class") == "QUALIFICATION_INJECTION" for record in eligible)
    pilot_escapes = sum(int(record.get("escape_review", {}).get("unresolved_escape_count", 0)) for record in eligible)
    false_positives = sum(
        int(record.get("false_positive_review", {}).get("unresolved_blocking_false_positive_count", 0)) for record in eligible
    )
    false_negatives = sum(
        int(record.get("false_negative_probes", {}).get("unresolved_false_negative_count", 0)) for record in eligible
    )
    scope_leakage = sum(
        int(record.get("scope_leakage_review", {}).get("preexisting_modification_only_block_count", 0)) for record in eligible
    )
    full_g3_complete = bool(eligible) and all(record.get("full_g3_shadow_status") == "PASS" for record in eligible)
    elapsed_met = elapsed_hours >= minimum_elapsed_hours
    candidate_threshold_met = len(eligible) >= minimum_eligible_candidate_count
    threshold_met = elapsed_met and candidate_threshold_met
    g3_ready = (
        threshold_met
        and full_g3_complete
        and pilot_escapes == 0
        and false_positives == 0
        and false_negatives == 0
        and scope_leakage == 0
        and all(record.get("performance_status") == "PASS" for record in eligible)
        and all(record.get("qa_disposition") == "PASS" for record in eligible)
    )
    return {
        "schema": "ovc-grt2-g2-5-pilot-summary/v1",
        "pilot_start": pilot_start,
        "evaluated_at": evaluated_at,
        "elapsed_hours": round(elapsed_hours, 6),
        "minimum_elapsed_hours": minimum_elapsed_hours,
        "elapsed_threshold_met": elapsed_met,
        "eligible_candidate_count": len(eligible),
        "minimum_eligible_candidate_count": minimum_eligible_candidate_count,
        "candidate_threshold_met": candidate_threshold_met,
        "threshold_met": threshold_met,
        "real_candidate_count": real_count,
        "qualification_injection_count": injection_count,
        "pilot_escape_count": pilot_escapes,
        "blocking_false_positive_count": false_positives,
        "unresolved_false_negative_count": false_negatives,
        "scope_leakage_count": scope_leakage,
        "full_g3_shadow_complete": full_g3_complete,
        "g3_ready": g3_ready,
        "status": "THRESHOLD_MET_G3_EVIDENCE_INCOMPLETE" if threshold_met and not g3_ready else ("G3_READY" if g3_ready else "COLLECTING"),
        "authority_effect": "NONE_EVIDENCE_SUMMARY_ONLY",
    }
