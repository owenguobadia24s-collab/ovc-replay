from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from .identity import exact_semantic_equal, projection_bytes


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTAKE_CLASSES = frozenset({"DISCOVERY_RESULT","STRUCTURAL_CORE","CLOSURE_CLASS","EVIDENCE_DOSSIER","P1_DISPOSITION","PATH1_CANDIDATE_PROPOSAL","NULL_FINDING","RESIDUAL_FINDING","CONTRADICTION","FAILED_REPLICATION","REPLICATION_RESULT","ADVERSARIAL_REVIEW","STACK_SUFFICIENCY_FINDING","METHOD_GAP_FINDING","MISSING_INFORMATION_FINDING","POPULATION_INTEGRITY","DENOMINATOR","DEPENDENCE","CAPACITY","REPRODUCIBILITY","CORRECTION","QUARANTINE_RECORD","SUPERSESSION_RECORD"})
_VISIBILITY_CLASSES = frozenset({"PATH1_FULL","PATH1_SAFE","CROSS_MODE_POST_FREEZE","OPERATOR_RESTRICTED","PROTECTED"})


def build_intake_envelope(
    *,
    envelope_id: str,
    source_ref: str,
    source_sha256: str,
    source_owner: str,
    source_first_valid_time: str,
    received_time: str,
    inventory_first_valid_time: str,
    intake_class: str,
    visibility_class: str,
) -> dict[str, Any]:
    required = {
        "envelope_id": envelope_id,
        "source_ref": source_ref,
        "source_sha256": source_sha256,
        "source_owner": source_owner,
        "source_first_valid_time": source_first_valid_time,
        "received_time": received_time,
        "inventory_first_valid_time": inventory_first_valid_time,
        "intake_class": intake_class,
        "visibility_class": visibility_class,
    }
    if any(not value for value in required.values()):
        raise ValueError("all intake envelope fields must be non-empty")
    if not _SHA256.fullmatch(source_sha256):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    if intake_class not in _INTAKE_CLASSES:
        raise ValueError(f"unknown intake_class: {intake_class}")
    if visibility_class not in _VISIBILITY_CLASSES:
        raise ValueError(f"unknown visibility_class: {visibility_class}")
    return {
        "record_type": "P1DiscoveryIntakeEnvelope",
        "schema_version": "0.1",
        **required,
        "intake_state": "PENDING_RESOLUTION",
        "reason_codes": ["UNRESOLVED_CURRENTNESS"],
        "authority_effect": "NONE",
    }


def classify_exact_intake(
    *,
    envelope: Mapping[str, Any],
    projection: Mapping[str, Any],
    existing_envelopes: Sequence[Mapping[str, Any]],
    existing_projections: Sequence[Mapping[str, Any]],
    non_exact_candidate_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Classify an advisory intake without performing a canonical write."""

    result = dict(envelope)
    if result.get("record_type") != "P1DiscoveryIntakeEnvelope":
        raise ValueError("P1DiscoveryIntakeEnvelope is required")
    projection_bytes(projection)
    duplicate = any(
        item.get("source_ref") == result.get("source_ref")
        and item.get("source_sha256") == result.get("source_sha256")
        for item in existing_envelopes
    )
    exact_generation = any(exact_semantic_equal(projection, item) for item in existing_projections)
    if duplicate:
        state, reasons = "DUPLICATE_EXACT", ["DUPLICATE_EXACT"]
    elif exact_generation:
        state, reasons = "ADMITTED_EXISTING_DISTINCTION_EVIDENCE", []
    elif non_exact_candidate_refs:
        state, reasons = "CORRESPONDENCE_REVIEW_REQUIRED", ["CORRESPONDENCE_REVIEW_REQUIRED"]
    else:
        state, reasons = "ADMITTED_NEW_DISTINCTION", []
    result["intake_state"] = state
    result["reason_codes"] = reasons
    return {
        "envelope": result,
        "canonical_write": "DENIED",
        "decision_bearing": False,
        "non_exact_candidate_refs": sorted(set(non_exact_candidate_refs)),
        "authority_effect": "NONE",
    }
