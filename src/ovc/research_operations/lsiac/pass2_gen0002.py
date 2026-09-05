from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .pass1_gen0002 import (
    EXPECTED_FRONTIER_RECEIPT_ID,
    EXPECTED_POST_DELTA_SHA256,
    EXPECTED_SOURCE_PASSPORT_SET_SHA256,
    EXPECTED_SOURCE_UNIVERSE_ID,
    GENERATION_ID,
    PROTOCOL_ID,
    build_pass1_classification_view,
)

PACKET_ID = "LSIAC-GEN0002-PASS2-SURVIVAL-ROLE-DESTINATION-EFFECT"
OPERATOR_AUTHORITY_DECISION_ID = "7130e987c4ba3900eff0abfc43d4989d9899393ef151e2a975dd5b5d04377c84"
EXPECTED_PASS1_VIRTUAL_VIEW_ID = "e9b10aebcae1136c1b5df34fb569392e10bcec0a2bc30e93675588ad4e288c6a"
EXPECTED_PROTOCOL_BINDING_ID = "15e449ffe15ded1d6419533257515ab9686122a1b5c73f7c82c49cea6e273d4f"
PROJECTION = "GEN0002_PASS2_FAIL_CLOSED_SURVIVAL_ROLE_DESTINATION_EFFECT_V1"
AUTHORITY_EFFECT = "SCIENTIFIC_INHERITANCE_ONLY_NO_OWNER_RUNTIME_SEMANTIC_OR_EXPOSURE_AUTHORITY"

HIGH_IMPACT_ROLES = {"CANONICAL_PRINCIPLE", "CANONICAL_CAPABILITY"}
HIGH_IMPACT_EFFECTS = {"CROSS_ARCHITECTURE_AMENDMENT_REQUIRED"}


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _identity(prefix: str, subject_id: str) -> str:
    digest = hashlib.sha256(f"{GENERATION_ID}|{prefix}|{subject_id}".encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:24]}"


def _source_debt(classification: Mapping[str, Any]) -> list[str]:
    blockers = [str(value) for value in classification.get("source_blockers", [])]
    if classification.get("source_standing") == "PENDING_SOURCE_BINDING":
        blockers.append("PENDING_SOURCE_BINDING")
    return sorted(set(blockers))


def _claim_strength(classification: Mapping[str, Any]) -> str:
    """Apply the frozen total cap conservatively without manufacturing positive evidence."""
    if classification.get("source_standing") in {"PENDING_SOURCE_BINDING", "SOURCE_CONFLICT"}:
        return "NOT_EVALUABLE"
    if classification.get("scientific_disposition") == "NOT_EVALUABLE":
        return "NOT_EVALUABLE"
    return "HISTORICAL_CONTEXT_ONLY"


def _lifecycle(classification: Mapping[str, Any]) -> str:
    if classification.get("source_standing") in {"PENDING_SOURCE_BINDING", "SOURCE_CONFLICT"}:
        return "QUARANTINED"
    return "DEFERRED_UNRESOLVED"


def build_counterevidence_manifest(classification: Mapping[str, Any]) -> dict[str, Any]:
    subject_id = str(classification["subject_id"])
    debt = _source_debt(classification)
    disposition = str(classification.get("scientific_disposition", "UNRESOLVED"))
    warnings = [
        "GEN0002_PASS1_DOES_NOT_SUPPLY_ROLE_SPECIFIC_ADMISSIBILITY_EVIDENCE",
        "NO_INITIAL_DOCKET_ROLE_RECURRENCE_VISUAL_APPEAL_OR_DOWNSTREAM_SUCCESS_USED_AS_PRIOR_WEIGHT",
    ]
    warnings.extend(debt)
    payload = {
        "schema": "ovc-lsiac-gen0002-counterevidence-completeness/v0.1",
        "generation_id": GENERATION_ID,
        "inheritance_candidate_id": _identity("LSIAC-GEN0002-INH", subject_id),
        "supporting_load_bearing_subjects": [],
        "negative_subjects": [subject_id] if disposition == "NEGATIVE_SUPPORTED" else [],
        "null_or_control_results": [],
        "contradictions": [],
        "warnings": sorted(set(warnings)),
        "protocol_exceptions": [],
        "source_binding_debt": debt,
        "not_evaluable_relevant_subjects": (
            [subject_id] if _claim_strength(classification) == "NOT_EVALUABLE" or debt else []
        ),
        "complete": True,
    }
    return {**payload, "manifest_sha256": _canonical_sha256(payload)}


def adjudicate_subject(classification: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create one bounded GEN0002 scientific accession decision.

    The frozen Pass-1 view contains no role-specific admissibility evidence. Therefore the
    only lawful final role on the current record is NONE. This is a no-forward disposition
    for this accession generation, not a falsification of the underlying historical science.
    """
    subject_id = str(classification["subject_id"])
    counterevidence = build_counterevidence_manifest(classification)
    debt = _source_debt(classification)
    lifecycle = _lifecycle(classification)
    decision_core = {
        "schema": "ovc-lsiac-gen0002-accession-decision/v0.1",
        "generation_id": GENERATION_ID,
        "inheritance_id": _identity("LSIAC-GEN0002-INH", subject_id),
        "source_subject_ids": [subject_id],
        "source_standing": str(classification["source_standing"]),
        "scientific_disposition": str(classification["scientific_disposition"]),
        "exposure_state": str(classification["exposure_state"]),
        "claim_strength": _claim_strength(classification),
        "inheritance_roles": ["NONE"],
        "lifecycle_state": lifecycle,
        "authority_state": "NONE",
        "authority_ref": None,
        "source_relation_state": str(classification["source_relation_state"]),
        "scope_envelope": {
            "population": "SOURCE_DEFINED_OR_UNRESOLVED_BY_GEN0002_PASS1",
            "representation": "SOURCE_DEFINED_OR_UNRESOLVED_BY_GEN0002_PASS1",
            "method": "SOURCE_DEFINED_OR_UNRESOLVED_BY_GEN0002_PASS1",
            "clock": "SOURCE_DEFINED_OR_UNRESOLVED_BY_GEN0002_PASS1",
            "exposure": str(classification["exposure_state"]),
            "authority_scope": "LSIAC_SCIENTIFIC_INHERITANCE_ONLY_NO_DOWNSTREAM_AUTHORITY",
            "exclusions": [
                "NO_SCOPE_EXPANSION_BEYOND_FROZEN_SOURCE_RECORD",
                "NO_OWNER_RUNTIME_SEMANTIC_SELECTOR_VALIDATION_PUBLICATION_OR_EXECUTION_EFFECT",
            ],
        },
        "surviving_statement": (
            "No distinct forward inheritance role is admissible for this subject in GEN0002 "
            "on the frozen Pass-1 evidence; preserve the source record without downstream activation."
        ),
        "role_justifications": {
            "NONE": (
                "The frozen GEN0002 Pass-1 projection contains no complete role-specific "
                "admissibility bundle; the protocol therefore fails closed rather than inferring a role."
            )
        },
        "counterevidence_manifest_sha256": counterevidence["manifest_sha256"],
        "dependence_graph_refs": sorted(str(value) for value in classification.get("dependence_refs", [])),
        "destination_binding_set": {
            "controlling_destination": None,
            "consumer_destinations": [],
        },
        "architecture_effect_set": {
            "primary_effect": "NO_FORWARD_IMPLEMENTATION",
            "secondary_effects": [],
        },
        "supersession_edges": [],
        "review_declarations": [],
        "rollback_reentry": (
            "Forward-only. Re-enter through a successor source-binding/adjudication packet after "
            "new exact load-bearing evidence or a separately authorised protocol/generation change; "
            "do not mutate this GEN0002 decision in place."
        ),
        "docket_status": "SOURCE_BINDING_REQUIRED" if debt else "CLOSED",
        "authority_effect": AUTHORITY_EFFECT,
    }
    decision_id = "LSIAC-GEN0002-DEC-" + _canonical_sha256(decision_core)[:24]
    return {**decision_core, "decision_id": decision_id}, counterevidence


def _high_impact_trigger(decision: Mapping[str, Any]) -> bool:
    roles = set(str(value) for value in decision.get("inheritance_roles", []))
    effect = str(decision.get("architecture_effect_set", {}).get("primary_effect", ""))
    return bool(roles & HIGH_IMPACT_ROLES or effect in HIGH_IMPACT_EFFECTS)


def build_pass2_adjudication_view(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    pass1 = build_pass1_classification_view(root)
    if pass1.get("subject_count") != 431 or pass1.get("passport_count") != 434:
        raise ValueError("LSIAC_GEN0002_PASS2_PASS1_CARDINALITY_MISMATCH")
    if pass1.get("source_universe_id") != EXPECTED_SOURCE_UNIVERSE_ID:
        raise ValueError("LSIAC_GEN0002_PASS2_SOURCE_UNIVERSE_MISMATCH")
    if pass1.get("frontier_receipt_id") != EXPECTED_FRONTIER_RECEIPT_ID:
        raise ValueError("LSIAC_GEN0002_PASS2_FRONTIER_MISMATCH")
    if pass1.get("protocol_binding_id") != EXPECTED_PROTOCOL_BINDING_ID:
        raise ValueError("LSIAC_GEN0002_PASS2_PROTOCOL_BINDING_MISMATCH")

    decisions: list[dict[str, Any]] = []
    counterevidence: list[dict[str, Any]] = []
    for classification in pass1["classifications"]:
        decision, manifest = adjudicate_subject(classification)
        decisions.append(decision)
        counterevidence.append(manifest)

    decisions.sort(key=lambda value: value["source_subject_ids"][0])
    counterevidence.sort(key=lambda value: value["inheritance_candidate_id"])

    counts: dict[str, dict[str, int]] = {}
    for field in ("claim_strength", "lifecycle_state", "docket_status"):
        bucket: dict[str, int] = {}
        for decision in decisions:
            value = str(decision[field])
            bucket[value] = bucket.get(value, 0) + 1
        counts[field] = dict(sorted(bucket.items()))

    non_none_role_count = sum(
        1 for decision in decisions if set(decision["inheritance_roles"]) != {"NONE"}
    )
    retain_forward_count = sum(
        1 for decision in decisions if decision["lifecycle_state"] == "RETAIN_FORWARD"
    )
    high_impact_count = sum(1 for decision in decisions if _high_impact_trigger(decision))
    destination_count = sum(
        1
        for decision in decisions
        if decision["destination_binding_set"]["controlling_destination"]
        or decision["destination_binding_set"]["consumer_destinations"]
    )

    return {
        "schema": "ovc-lsiac-gen0002-pass2-adjudication-view/v0.1",
        "programme_id": "OVC-LSIAC-v0.1",
        "packet_id": PACKET_ID,
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "operator_authority_decision_id": OPERATOR_AUTHORITY_DECISION_ID,
        "pass1_virtual_view_id": EXPECTED_PASS1_VIRTUAL_VIEW_ID,
        "source_universe_id": EXPECTED_SOURCE_UNIVERSE_ID,
        "frontier_receipt_id": EXPECTED_FRONTIER_RECEIPT_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "subject_count": len(decisions),
        "passport_count": int(pass1["passport_count"]),
        "decisions": decisions,
        "counterevidence_manifests": counterevidence,
        "decision_records_canonical_sha256": _canonical_sha256(decisions),
        "counterevidence_records_canonical_sha256": _canonical_sha256(counterevidence),
        "counts": counts,
        "non_none_role_count": non_none_role_count,
        "retain_forward_count": retain_forward_count,
        "high_impact_review_trigger_count": high_impact_count,
        "destination_binding_count": destination_count,
        "architecture_execution_count": 0,
        "projection": PROJECTION,
        "anti_selection_rule": (
            "NO_INITIAL_DOCKET_ROLE_RECURRENCE_VISUAL_APPEAL_OR_DOWNSTREAM_SUCCESS_USED_AS_DECISION_BEARING_PRIOR_WEIGHT"
        ),
        "authority_effect": AUTHORITY_EFFECT,
    }


def build_virtual_view_identity(*, algorithm_git_blob_sha: str) -> str:
    payload = {
        "schema": "ovc-lsiac-gen0002-pass2-virtual-view-identity/v0.1",
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "operator_authority_decision_id": OPERATOR_AUTHORITY_DECISION_ID,
        "pass1_virtual_view_id": EXPECTED_PASS1_VIRTUAL_VIEW_ID,
        "source_universe_id": EXPECTED_SOURCE_UNIVERSE_ID,
        "frontier_receipt_id": EXPECTED_FRONTIER_RECEIPT_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "algorithm_git_blob_sha": algorithm_git_blob_sha,
        "projection": PROJECTION,
        "scope": "ALL_431_GEN0002_FROZEN_ACCESSION_SUBJECTS",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _canonical_sha256(payload)
