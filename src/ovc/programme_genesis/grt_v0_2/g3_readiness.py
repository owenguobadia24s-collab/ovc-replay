"""GRT2-G3 pre-activation readiness evidence helpers.

This module is intentionally non-enforcing.  It materialises source-backed
comparisons needed to decide whether a GRT2-G3 gate packet may be presented.
It cannot activate the Repository Constitution, create DebtFloor generation 0,
or convert unresolved evidence into a zero claim.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .serialization import canonical_sha256


class G3ReadinessError(ValueError):
    pass


_ZERO_TOLERANCE_FIELDS = (
    "unresolved_escape_count",
    "blocking_false_positive_count",
    "unresolved_false_negative_count",
    "scope_leakage_count",
)


def _component_path_map(topology: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["component_id"]): str(row["path"])
        for row in topology.get("components", [])
        if row.get("component_id") and row.get("path")
    }


def anomaly_subject_projection(anomaly: Mapping[str, Any], topology: Mapping[str, Any]) -> dict[str, Any]:
    """Project a v0.1 observer anomaly onto stable source subjects.

    The observer anomaly ID is intentionally *not* used as lineage identity: it
    includes descriptive payload that may change as repository denominators move.
    Paths and source-explicit programme IDs are retained so a later v0.2 rule
    mapping can adjudicate legality without manufacturing authority.
    """
    paths = _component_path_map(topology)
    component_paths = sorted(
        paths.get(str(component_id), f"UNRESOLVED_COMPONENT:{component_id}")
        for component_id in anomaly.get("affected_component_ids", [])
    )
    return {
        "anomaly_code": str(anomaly.get("anomaly_code", "")),
        "component_paths": component_paths,
        "programme_ids": sorted(str(x) for x in anomaly.get("affected_programme_ids", [])),
    }


def anomaly_subject_key(anomaly: Mapping[str, Any], topology: Mapping[str, Any]) -> str:
    return canonical_sha256(anomaly_subject_projection(anomaly, topology))


def anomaly_extent(anomaly: Mapping[str, Any]) -> dict[str, int]:
    """Return conservative measurable extent from v0.1 observer evidence.

    This is measurement evidence, not constitutional debt authority.  Binary
    findings receive extent 1.  Where the observer explicitly reports a count in
    its detail, that count is retained so expansion cannot be hidden by a stable
    subject key.
    """
    code = str(anomaly.get("anomaly_code", ""))
    if code == "UNRESOLVED_DEPENDENCY":
        match = re.match(r"^(\d+) repository-like path reference", str(anomaly.get("detail", "")))
        if match:
            return {"unresolved_reference_count": int(match.group(1))}
    if code in {"DUPLICATE_COMPONENT_OWNERSHIP", "CONFLICTING_PROGRAMME_OWNERSHIP"}:
        return {"owner_count": max(1, len(anomaly.get("affected_programme_ids", [])))}
    return {"observer_condition_count": 1}


def _extent_relation(previous: Mapping[str, int], current: Mapping[str, int]) -> str:
    if set(previous) != set(current):
        return "MATERIAL_CHANGED"
    delta = [current[key] - previous[key] for key in sorted(previous)]
    if all(value == 0 for value in delta):
        return "UNCHANGED"
    if all(value <= 0 for value in delta):
        return "REDUCED"
    if all(value >= 0 for value in delta):
        return "EXPANDED"
    return "MATERIAL_CHANGED"


def reconcile_observer_transition_candidates(
    *, baseline_topology: Mapping[str, Any], current_topology: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconcile observer conditions without pretending they are v0.2 findings.

    Exact stable-subject matches prove observer continuity/reduction/expansion.
    Novel conditions are transition-debt *candidates* and still require a
    source-backed v0.2 constitutional rule mapping before they can be declared
    actionable debt or lawful non-debt.  This fail-closed distinction is what
    prevents an empty ledger from becoming a fabricated zero-debt claim.
    """
    baseline_rows = list(baseline_topology.get("anomalies", []))
    current_rows = list(current_topology.get("anomalies", []))
    baseline_by_key = {anomaly_subject_key(row, baseline_topology): row for row in baseline_rows}
    current_by_key = {anomaly_subject_key(row, current_topology): row for row in current_rows}

    unchanged: list[str] = []
    reduced: list[str] = []
    expanded: list[str] = []
    material_changed: list[str] = []
    for key in sorted(set(baseline_by_key) & set(current_by_key)):
        relation = _extent_relation(anomaly_extent(baseline_by_key[key]), anomaly_extent(current_by_key[key]))
        {"UNCHANGED": unchanged, "REDUCED": reduced, "EXPANDED": expanded, "MATERIAL_CHANGED": material_changed}[relation].append(key)

    resolved = sorted(set(baseline_by_key) - set(current_by_key))
    novel_keys = sorted(set(current_by_key) - set(baseline_by_key))
    novel = [
        {
            "subject_key": key,
            "projection": anomaly_subject_projection(current_by_key[key], current_topology),
            "observer_anomaly_id": current_by_key[key].get("anomaly_id"),
            "severity": current_by_key[key].get("severity"),
            "extent": anomaly_extent(current_by_key[key]),
            "constitutional_status": "UNMAPPED_REQUIRES_V0_2_RULE_EVIDENCE",
        }
        for key in novel_keys
    ]
    return {
        "schema": "ovc-grt2-g3-observer-transition-reconciliation/v1",
        "baseline_commit": baseline_topology.get("portfolio", {}).get("source_commit"),
        "current_commit": current_topology.get("portfolio", {}).get("source_commit"),
        "baseline_observer_condition_count": len(baseline_rows),
        "current_observer_condition_count": len(current_rows),
        "stable_unchanged_count": len(unchanged),
        "stable_reduced_count": len(reduced),
        "stable_expanded_count": len(expanded),
        "stable_material_changed_count": len(material_changed),
        "resolved_observer_condition_count": len(resolved),
        "novel_observer_condition_count": len(novel),
        "novel_observer_conditions": novel,
        "transition_debt_zero_proven": len(novel) == 0 and not expanded and not material_changed,
        "baseline_expansion_zero_proven": not expanded and not material_changed,
        "authority_effect": "NONE_OBSERVER_RECONCILIATION_ONLY",
    }


def evaluate_candidate_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if record.get("full_g3_shadow_status") != "PASS":
        reasons.append("FULL_G3_SHADOW_NOT_PASS")
    for field in _ZERO_TOLERANCE_FIELDS:
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value != 0:
            reasons.append(field.upper() + "_NONZERO_OR_MISSING")
    if record.get("performance_status") != "PASS":
        reasons.append("PERFORMANCE_NOT_PASS")
    if record.get("qa_disposition") != "PASS":
        reasons.append("QA_NOT_PASS")
    return {
        "candidate_id": record.get("candidate_id"),
        "status": "PASS" if not reasons else "INCOMPLETE",
        "reason_codes": reasons,
        "authority_effect": "NONE_G3_READINESS_EVIDENCE_ONLY",
    }


def summarize_g3_readiness(
    *,
    pilot_records: Sequence[Mapping[str, Any]],
    historical_records: Sequence[Mapping[str, Any]],
    transition_reconciliation: Mapping[str, Any],
    candidate_floor_ready: bool,
    required_historical_count: int = 10,
) -> dict[str, Any]:
    pilot = [evaluate_candidate_evidence(row) for row in pilot_records]
    historical = [evaluate_candidate_evidence(row) for row in historical_records]
    reasons: list[str] = []
    if not pilot or any(row["status"] != "PASS" for row in pilot):
        reasons.append("PILOT_FULL_G3_EVIDENCE_INCOMPLETE")
    if len(historical) < required_historical_count:
        reasons.append("HISTORICAL_INTEGRATION_REPLAY_GAP")
    if any(row["status"] != "PASS" for row in historical):
        reasons.append("HISTORICAL_DRY_RUN_INCOMPLETE")
    if transition_reconciliation.get("transition_debt_zero_proven") is not True:
        reasons.append("PRE_G3_TRANSITION_DEBT_ZERO_NOT_PROVEN")
    if transition_reconciliation.get("baseline_expansion_zero_proven") is not True:
        reasons.append("BASELINE_EXPANSION_ZERO_NOT_PROVEN")
    if not candidate_floor_ready:
        reasons.append("CANDIDATE_DEBT_FLOOR_GEN0_NOT_READY")
    return {
        "schema": "ovc-grt2-g3-readiness-summary/v1",
        "pilot_candidate_count": len(pilot),
        "historical_candidate_count": len(historical),
        "required_historical_candidate_count": required_historical_count,
        "pilot_results": pilot,
        "historical_results": historical,
        "transition_reconciliation": dict(transition_reconciliation),
        "candidate_floor_ready": candidate_floor_ready,
        "status": "GATE_READY" if not reasons else "EVIDENCE_INCOMPLETE",
        "reason_codes": reasons,
        "authority_effect": "NONE_G3_GATE_PREPARATION_ONLY",
    }
