"""GRT2-G3 pre-activation readiness evidence helpers.

This module is intentionally non-enforcing. It materialises source-backed
comparisons needed to decide whether a GRT2-G3 gate packet may be presented.
It cannot activate the Repository Constitution, create DebtFloor generation 0,
or convert unresolved evidence into a zero claim.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from .debt import (
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    B0_SOURCE_COMMIT,
    baseline_membership_sha256,
    validate_baseline_members,
)
from .serialization import canonical_sha256


class G3ReadinessError(ValueError):
    pass


def _logical_record_valid(record: Mapping[str, Any]) -> bool:
    expected = record.get("logical_sha256")
    if not isinstance(expected, str):
        return False
    payload = dict(record)
    payload.pop("logical_sha256", None)
    return expected == canonical_sha256(payload)


def readiness_stage_blockers(
    pointer: Mapping[str, Any],
    *,
    gate_state: Mapping[str, Any] | None = None,
    gate_packet: Mapping[str, Any] | None = None,
    gate_qa: Mapping[str, Any] | None = None,
    readiness_completion: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Accept pre-materialisation readiness or the exact authority-inert gate stage.

    Advancing the pointer to the reserved operator decision must not make an
    otherwise identical full readiness replay fail.  The post-materialisation
    route is accepted only when the content-addressed gate records prove that no
    Constitution, DebtFloor, full-enforcement, or G3 authority was activated.
    """
    if pointer.get("next_packet") == "GRT2-G3-READINESS-EVIDENCE":
        return ()
    if pointer.get("next_packet") != "GRT2-G3-OPERATOR-DECISION":
        return ("GRT2_NEXT_PACKET_NOT_G3_READINESS_OR_OPERATOR_DECISION",)
    records = (gate_state, gate_packet, gate_qa, readiness_completion)
    if any(not isinstance(record, Mapping) or not _logical_record_valid(record) for record in records):
        return ("GRT2_GATE_READY_RECORD_IDENTITY_INVALID",)
    assert gate_state is not None and gate_packet is not None and gate_qa is not None and readiness_completion is not None
    valid = (
        pointer.get("current_state") == "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_15.json"
        and pointer.get("packet_id") == "GRT2-G3-GATE-READY"
        and pointer.get("gate_id") == "GRT2-G3"
        and pointer.get("status") == "GATE_READY_OPERATOR_REQUIRED"
        and pointer.get("operator_decision_required") is True
        and pointer.get("next_action") == "STOP_FOR_OPERATOR_GRT2_G3_DECISION"
        and gate_state.get("status") == "GATE_READY_OPERATOR_REQUIRED"
        and gate_state.get("authority_effect") == "NONE_GATE_PREPARATION_ONLY"
        and gate_state.get("constitution_status") == "PROPOSED_UNADMITTED"
        and gate_state.get("active_enforcement") == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
        and gate_state.get("debt_floor_generation") is None
        and gate_state.get("operator_decision_required") is True
        and gate_packet.get("status") == "GATE_READY_OPERATOR_REQUIRED"
        and gate_packet.get("operator_decision") is None
        and gate_packet.get("operator_decision_required") is True
        and gate_packet.get("authority_consumed") == "NONE"
        and gate_packet.get("stop_condition") == "STOP_FOR_OPERATOR_GRT2_G3_DECISION"
        and gate_qa.get("qa_recommendation") == "PASS"
        and gate_qa.get("unresolved_issues") == []
        and readiness_completion.get("status") == "COMPLETED_PASS_MERGED"
        and readiness_completion.get("authority_effect") == "NONE_READINESS_COMPLETION_ONLY"
        and readiness_completion.get("constitution_status") == "PROPOSED_UNADMITTED"
        and readiness_completion.get("debt_floor_generation") is None
        and readiness_completion.get("g3_authority") == "NOT_CONSUMED"
    )
    return () if valid else ("GRT2_GATE_READY_PREACTIVATION_BOUNDARY_INVALID",)


_ZERO_TOLERANCE_FIELDS = (
    "unresolved_escape_count",
    "blocking_false_positive_count",
    "unresolved_false_negative_count",
    "scope_leakage_count",
)

# This is an observer-to-Constitution crosswalk, not a rule amendment.  Codes
# omitted from the map have no debt-producing rule in the immutable v0.2 bundle
# and are recorded explicitly as lawful observer-only conditions.
_OBSERVER_RULE_CROSSWALK: dict[str, tuple[str, ...]] = {
    "CONFLICTING_PROGRAMME_OWNERSHIP": ("GRT-R200",),
    "DUPLICATE_COMPONENT_OWNERSHIP": ("GRT-R200",),
    "GENESIS_TOPOLOGY_CONFLICT": ("GRT-R300",),
    "IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK": ("GRT-R300",),
    "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER": ("GRT-R200",),
    "MISSING_AUTHORITY_RECORD": ("GRT-R300",),
    "ORPHAN_SCHEMA": ("GRT-R421",),
    "ORPHAN_WORKFLOW": ("GRT-R805",),
    "SHADOW_ACTIVE_MISMATCH": ("GRT-R700",),
    "STALE_DOCUMENTATION": ("GRT-R700",),
    "STALE_PROGRAMME_STATE": ("GRT-R700",),
    "SUPERSEDED_COMPONENT_STILL_REFERENCED": ("GRT-R600",),
    "UNRESOLVED_DEPENDENCY": ("GRT-R500",),
}

_RULE_FAMILY = {
    "GRT-R200": "OWNERSHIP",
    "GRT-R300": "GENESIS_BINDINGS",
    "GRT-R421": "COMPANIONS_AND_ORPHANS",
    "GRT-R500": "DEPENDENCIES",
    "GRT-R600": "SUPERSESSION",
    "GRT-R700": "CURRENT_STATE_AND_DOCUMENTATION",
    "GRT-R805": "WORKFLOWS_AND_TOOLING",
}


def _component_path_map(topology: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["component_id"]): str(row["path"])
        for row in topology.get("components", [])
        if row.get("component_id") and row.get("path")
    }


def _stable_source_ref(value: Any) -> str:
    """Project source evidence onto a content-independent source locator.

    GRT v0.1 commonly records component evidence as ``git:path@blob``. The
    blob is exact provenance but not stable subject identity: ordinary lawful
    edits must not manufacture a novel repository subject. Plain repository
    paths and non-Git evidence references are retained exactly.
    """
    text = str(value)
    if text.startswith("git:"):
        body = text[4:]
        if "@" in body:
            body = body.rsplit("@", 1)[0]
        return f"git:{body}"
    return text


def anomaly_subject_projection(anomaly: Mapping[str, Any], topology: Mapping[str, Any]) -> dict[str, Any]:
    """Project an observer anomaly onto a stable source subject.

    The observer anomaly ID and content blob are intentionally excluded: both may
    change under ordinary lawful repository evolution. Source evidence is the
    preferred subject locator because the frozen B0 members retain it exactly;
    component paths are used only when no source evidence is available.
    """
    paths = _component_path_map(topology)
    component_paths = sorted(
        paths[str(component_id)]
        for component_id in anomaly.get("affected_component_ids", [])
        if str(component_id) in paths
    )
    source_refs = sorted({_stable_source_ref(x) for x in anomaly.get("source_evidence", [])})
    stable_subjects = source_refs if source_refs else component_paths
    return {
        "anomaly_code": str(anomaly.get("anomaly_code", "")),
        "source_subjects": stable_subjects,
        "programme_ids": sorted(str(x) for x in anomaly.get("affected_programme_ids", [])),
    }


def anomaly_subject_key(anomaly: Mapping[str, Any], topology: Mapping[str, Any]) -> str:
    return canonical_sha256(anomaly_subject_projection(anomaly, topology))


def _repository_path(value: Any) -> str | None:
    text = _stable_source_ref(value)
    if text.startswith("git-tree:"):
        return None
    if text.startswith("git:"):
        text = text[4:]
    prefixes = (
        ".github/", "apps/", "contracts/", "docs/", "fixtures/", "legacy/",
        "plans/", "records/", "registries/", "schemas/", "scripts/", "src/",
        "tests/", "tools/",
    )
    return text if text.startswith(prefixes) else None


def _subject_id(path: str) -> str:
    return "GRT.ARTIFACT.PATH." + canonical_sha256({"path": path})[:24]


def _condition_source_paths(anomaly: Mapping[str, Any], topology: Mapping[str, Any]) -> list[str]:
    component_paths = _component_path_map(topology)
    paths = {
        path
        for value in anomaly.get("source_evidence", [])
        if (path := _repository_path(value)) is not None
    }
    paths.update(
        component_paths[str(component_id)]
        for component_id in anomaly.get("affected_component_ids", [])
        if str(component_id) in component_paths
    )
    return sorted(paths)


def _classify_current_condition(
    anomaly: Mapping[str, Any],
    topology: Mapping[str, Any],
    full_snapshot: Mapping[str, Any],
    *,
    b0_mapped: bool,
    constitution_status: str,
) -> dict[str, Any]:
    key = anomaly_subject_key(anomaly, topology)
    code = str(anomaly.get("anomaly_code", ""))
    paths = _condition_source_paths(anomaly, topology)
    subject_ids = {_subject_id(path) for path in paths}
    stable_paths = {"git:" + path for path in paths} | set(paths)
    rule_ids = _OBSERVER_RULE_CROSSWALK.get(code, ())
    base = {
        "subject_key": key,
        "observer_anomaly_id": anomaly.get("anomaly_id"),
        "observer_code": code,
        "source_paths": paths,
        "b0_lineage": "B0_MAPPED" if b0_mapped else "NON_B0",
        "extent": anomaly_extent(anomaly),
    }
    if not rule_ids:
        return {
            **base,
            "classification": "B0_MAPPED_LAWFUL_NON_DEBT" if b0_mapped else "LAWFUL_NON_B0_OBSERVER_ONLY",
            "constitutional_basis": "NO_DEBT_PRODUCING_V0_2_RULE_FOR_OBSERVER_CODE",
            "evaluated_rule_ids": [],
            "mapped_finding_ids": [],
        }

    evaluations = []
    for row in full_snapshot.get("evaluations", []):
        if str(row.get("rule_id", "")) not in rule_ids:
            continue
        evidence = {_stable_source_ref(value) for value in row.get("evidence_refs", [])}
        if str(row.get("subject_artifact_id", "")) in subject_ids or evidence & stable_paths:
            evaluations.append(row)
    findings = []
    for row in full_snapshot.get("findings", []):
        if str(row.get("rule_id", "")) not in rule_ids:
            continue
        evidence = {_stable_source_ref(value) for value in row.get("evidence_refs", [])}
        if str(row.get("subject_artifact_id", "")) in subject_ids or evidence & stable_paths:
            findings.append(str(row["finding_id"]))

    evaluated_rule_ids = sorted({str(row["rule_id"]) for row in evaluations})
    if any(row.get("evaluation_status") == "NOT_EVALUABLE" for row in evaluations):
        return {
            **base,
            "classification": "UNRESOLVED_V0_2_EVALUATION",
            "constitutional_basis": "SOURCE_BOUND_RULE_FACT_NOT_EVALUABLE",
            "evaluated_rule_ids": evaluated_rule_ids,
            "mapped_finding_ids": sorted(set(findings)),
        }
    if any(row.get("evaluation_status") == "VIOLATION" for row in evaluations):
        if not findings:
            return {
                **base,
                "classification": "UNRESOLVED_V0_2_FINDING_IDENTITY",
                "constitutional_basis": "VIOLATION_WITHOUT_SOURCE_BOUND_FINDING",
                "evaluated_rule_ids": evaluated_rule_ids,
                "mapped_finding_ids": [],
            }
        if b0_mapped:
            classification = "B0_MAPPED_CURRENT_ACTIONABLE"
        elif constitution_status == "PROPOSED_UNADMITTED":
            classification = "LATE_DISCOVERED_PREEXISTING_CURRENT_ACTIONABLE"
        else:
            classification = "TRANSITION_NEW_ACTIONABLE_DEBT"
        return {
            **base,
            "classification": classification,
            "constitutional_basis": "SOURCE_BOUND_V0_2_VIOLATION",
            "evaluated_rule_ids": evaluated_rule_ids,
            "mapped_finding_ids": sorted(set(findings)),
        }
    if evaluations:
        return {
            **base,
            "classification": "B0_MAPPED_LAWFUL_NON_DEBT" if b0_mapped else "LAWFUL_NON_B0_UNDER_V0_2",
            "constitutional_basis": "SOURCE_BOUND_V0_2_PASS_OR_NOT_APPLICABLE",
            "evaluated_rule_ids": evaluated_rule_ids,
            "mapped_finding_ids": [],
        }

    # The full adapter's classification pass proves the subject class.  If the
    # relevant constitutional family is complete but emits no rule evaluation
    # for that classified subject, the rule selector is lawfully not applicable.
    classified_subjects = {
        str(row.get("subject_artifact_id", ""))
        for row in full_snapshot.get("evaluations", [])
        if row.get("rule_id") == "GRT-R100"
        and row.get("evaluation_status") == "PASS"
        and str(row.get("subject_artifact_id", "")) in subject_ids
    }
    families = full_snapshot.get("family_coverage", {})
    family_complete = all(families.get(_RULE_FAMILY[rule_id]) == "EVALUATED" for rule_id in rule_ids)
    if paths and classified_subjects and family_complete:
        return {
            **base,
            "classification": "B0_MAPPED_LAWFUL_NON_DEBT" if b0_mapped else "LAWFUL_NON_B0_RULE_NOT_APPLICABLE",
            "constitutional_basis": "CLASSIFIED_SUBJECT_OUTSIDE_V0_2_RULE_SELECTOR",
            "evaluated_rule_ids": [],
            "mapped_finding_ids": [],
        }
    return {
        **base,
        "classification": "UNRESOLVED_V0_2_RULE_MAPPING",
        "constitutional_basis": "NO_SOURCE_BOUND_V0_2_RULE_EVIDENCE",
        "evaluated_rule_ids": [],
        "mapped_finding_ids": [],
    }


def baseline_topology_from_member_records(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reconstruct the immutable B0 observer surface from its frozen members.

    This deliberately does *not* rerun the current topology scanner over the B0
    commit. Scanner semantics are allowed to evolve; B0 is the immutable 569-row
    source evidence frozen by WP2. Every row is validated against its original
    scanner identity and membership hash before it may participate in G3
    transition reconciliation.
    """
    validate_baseline_members(rows)
    membership = baseline_membership_sha256(rows)
    if membership != B0_MEMBERSHIP_SHA256:
        raise G3ReadinessError("GRT2_G3_B0_MEMBERSHIP_HASH_MISMATCH")
    if len(rows) != B0_MEMBER_COUNT:
        raise G3ReadinessError("GRT2_G3_B0_MEMBER_COUNT_MISMATCH")

    anomalies: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: int(item["ordinal"])):
        try:
            locator = json.loads(str(row["original_subject_locator"]))
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            raise G3ReadinessError("GRT2_G3_B0_SUBJECT_LOCATOR_INVALID") from exc
        anomalies.append(
            {
                "anomaly_id": row["original_GRT_anomaly"],
                "anomaly_code": row["original_anomaly_code"],
                "affected_component_ids": [],
                "affected_programme_ids": list(locator.get("affected_programme_ids", [])),
                "source_evidence": list(locator.get("source_evidence", [])),
                "baseline_member_id": row["baseline_member_id"],
                "payload_hash": row["payload_hash"],
            }
        )
    return {
        "portfolio": {"source_commit": B0_SOURCE_COMMIT},
        "components": [],
        "anomalies": anomalies,
        "baseline_member_count": B0_MEMBER_COUNT,
        "baseline_membership_sha256": membership,
        "authority_effect": "NONE_IMMUTABLE_B0_PROJECTION_ONLY",
    }


def anomaly_extent(anomaly: Mapping[str, Any]) -> dict[str, int]:
    """Return conservative measurable extent from observer evidence.

    Live observer evidence may expose a measurable within-condition extent. Frozen
    B0 member records preserve exact warning identity but not the old scanner's
    mutable detail payload, so they are binary conditions and are never assigned a
    fabricated historical count.
    """
    code = str(anomaly.get("anomaly_code", ""))
    if code == "UNRESOLVED_DEPENDENCY" and anomaly.get("detail") is not None:
        match = re.match(r"^(\d+) repository-like path reference", str(anomaly.get("detail", "")))
        if match:
            return {"unresolved_reference_count": int(match.group(1))}
    if code in {"DUPLICATE_COMPONENT_OWNERSHIP", "CONFLICTING_PROGRAMME_OWNERSHIP"}:
        owners = len(anomaly.get("affected_programme_ids", []))
        if owners > 1:
            return {"owner_count": owners}
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


def _condition_extent_relation(previous: Mapping[str, Any], current: Mapping[str, Any]) -> str:
    """Compare extent only where the historical source actually preserved it.

    A frozen B0 member proves one historical observer condition existed. It does
    not preserve enough information to reconstruct a numeric sub-extent under the
    evolved scanner. Stable B0/current subjects are therefore compared as binary
    condition continuity. Novel subjects remain fully fail-closed transition-debt
    candidates.
    """
    if previous.get("baseline_member_id") is not None:
        return "UNCHANGED"
    return _extent_relation(anomaly_extent(previous), anomaly_extent(current))


def reconcile_observer_transition_candidates(
    *,
    baseline_topology: Mapping[str, Any],
    current_topology: Mapping[str, Any],
    full_snapshot: Mapping[str, Any] | None = None,
    constitution_status: str = "",
) -> dict[str, Any]:
    """Reconcile observer conditions without pretending they are v0.2 findings.

    Exact stable-subject matches prove observer continuity. Novel conditions are
    transition-debt *candidates* and still require a source-backed v0.2
    constitutional rule mapping before they can be declared actionable debt or
    lawful non-debt. This fail-closed distinction prevents an empty ledger from
    becoming a fabricated zero-debt claim.
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
        relation = _condition_extent_relation(baseline_by_key[key], current_by_key[key])
        {"UNCHANGED": unchanged, "REDUCED": reduced, "EXPANDED": expanded, "MATERIAL_CHANGED": material_changed}[relation].append(key)

    resolved = sorted(set(baseline_by_key) - set(current_by_key))
    novel_keys = sorted(set(current_by_key) - set(baseline_by_key))
    if full_snapshot is None:
        classifications = [
            {
                "subject_key": key,
                "projection": anomaly_subject_projection(current_by_key[key], current_topology),
                "observer_anomaly_id": current_by_key[key].get("anomaly_id"),
                "severity": current_by_key[key].get("severity"),
                "extent": anomaly_extent(current_by_key[key]),
                "classification": "UNRESOLVED_V0_2_RULE_MAPPING",
                "constitutional_basis": "FULL_CURRENT_V0_2_SNAPSHOT_REQUIRED",
                "mapped_finding_ids": [],
            }
            for key in sorted(current_by_key)
        ]
    else:
        classifications = [
            _classify_current_condition(
                current_by_key[key],
                current_topology,
                full_snapshot,
                b0_mapped=key in baseline_by_key,
                constitution_status=constitution_status,
            )
            for key in sorted(current_by_key)
        ]
    unresolved = [row for row in classifications if str(row["classification"]).startswith("UNRESOLVED_")]
    transition_new = [row for row in classifications if row["classification"] == "TRANSITION_NEW_ACTIONABLE_DEBT"]
    novel = [row for row in classifications if row["subject_key"] in set(novel_keys)]
    classification_counts: dict[str, int] = {}
    for row in classifications:
        value = str(row["classification"])
        classification_counts[value] = classification_counts.get(value, 0) + 1
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
        "current_condition_classification_count": len(classifications),
        "current_condition_classification_counts": dict(sorted(classification_counts.items())),
        "current_condition_classifications": classifications,
        "unresolved_current_condition_count": len(unresolved),
        "transition_new_debt_count": len(transition_new),
        "transition_debt_zero_proven": not unresolved and not transition_new and not expanded and not material_changed,
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
