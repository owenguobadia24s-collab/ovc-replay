"""Corrected inactive June empirical boundary evaluator using stable signatures.

Rule meanings and rule IDs are unchanged from the preregistered baseline. Only
change comparison is repaired: PHASE_MUTATION and RE_PARENT consume the
versioned stable comparison signatures rather than wrapper record identities.
"""
from __future__ import annotations

from typing import Any, Mapping

from .empirical_boundary_rules import EmpiricalBoundaryRuleError, RULE_IDS, _scan
from .stable_signatures import StableSignatureError, verify_comparison_signatures

IMPLEMENTATION_ID = "C2E.EMPIRICAL.BOUNDARY.JUNE.STABLE_SIGNATURES.v2"


def _required(frame: Mapping[str, Any]) -> None:
    for key in ("identity", "chronology", "structural", "context", "evidence", "lineage", "comparison"):
        if key not in frame:
            raise EmpiricalBoundaryRuleError(f"FRAME_FIELD_REQUIRED:{key}")
    for key in ("continuity_segment_id", "first_valid_time", "evaluation_cutoff"):
        if not frame["chronology"].get(key):
            raise EmpiricalBoundaryRuleError(f"CHRONOLOGY_REQUIRED:{key}")
    for axis in ("location_record_ids", "motion_record_ids", "organisation_record_ids", "interaction_record_ids"):
        if axis not in frame["structural"]:
            raise EmpiricalBoundaryRuleError(f"STRUCTURAL_AXIS_REQUIRED:{axis}")
    try:
        verify_comparison_signatures(frame["comparison"])
    except StableSignatureError as exc:
        raise EmpiricalBoundaryRuleError(str(exc)) from exc


def evaluate_boundary_predicates_v2(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None = None,
    *,
    explicit_source_gap: bool = False,
    release_end: bool = False,
) -> dict[str, Any]:
    _scan(current)
    _required(current)
    if previous is not None:
        _scan(previous)
        _required(previous)
        for key in ("instrument_id", "side", "scope_id", "scale_id", "clock_id"):
            if current["identity"].get(key) != previous["identity"].get(key):
                raise EmpiricalBoundaryRuleError(f"PEER_SCOPE_MISMATCH:{key}")

    current_segment = str(current["chronology"]["continuity_segment_id"])
    previous_segment = None if previous is None else str(previous["chronology"]["continuity_segment_id"])
    segment_changed = previous is not None and current_segment != previous_segment
    gap = bool(explicit_source_gap or segment_changed)

    current_structural = str(current["comparison"]["structural_signature_sha256"])
    current_parent = str(current["comparison"]["parent_signature_sha256"])
    prior_structural = None if previous is None else str(previous["comparison"]["structural_signature_sha256"])
    prior_parent = None if previous is None else str(previous["comparison"]["parent_signature_sha256"])

    parent_changed = previous is not None and not gap and not release_end and current_parent != prior_parent
    structural_changed = previous is not None and not gap and not release_end and current_structural != prior_structural
    birth = (previous is None or gap) and not release_end
    continuation = previous is not None and not gap and not release_end

    matched = {
        "C2E.RULE.JUNE.BASELINE.CENSOR_GAP.v1": gap and not release_end,
        "C2E.RULE.JUNE.BASELINE.CENSOR_RELEASE_END.v1": bool(release_end),
        "C2E.RULE.JUNE.BASELINE.RE_PARENT.v1": parent_changed,
        "C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1": structural_changed,
        "C2E.RULE.JUNE.BASELINE.CONTINUATION.v1": continuation,
        "C2E.RULE.JUNE.BASELINE.BIRTH.v1": birth,
    }
    return {
        "schema": "ovc-c2e-empirical-boundary-evaluation/v2",
        "implementation_id": IMPLEMENTATION_ID,
        "signature_contract_id": "C2E.STABLE.COMPARISON.SIGNATURES.v1",
        "pack_semantics": "JUNE_BASELINE_CONTINUITY_EPISODE_WITH_TYPED_PHASE_AND_PARENT_MUTATION",
        "matched_rules": [rule for rule in RULE_IDS if matched[rule]],
        "matched": matched,
        "current_structural_signature_sha256": current_structural,
        "previous_structural_signature_sha256": prior_structural,
        "current_parent_signature_sha256": current_parent,
        "previous_parent_signature_sha256": prior_parent,
        "segment_changed": segment_changed,
        "explicit_source_gap": bool(explicit_source_gap),
        "release_end": bool(release_end),
        "thresholds_used": [],
        "outcome_inputs_used": False,
        "family_inputs_used": False,
        "validation_inputs_used": False,
        "authority": "CANDIDATE_INACTIVE_NONCANONICAL",
    }


def evaluate_boundary_predicates(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None = None,
    *,
    explicit_source_gap: bool = False,
    release_end: bool = False,
) -> dict[str, bool]:
    """Compatibility view returning only the frozen rule-match map.

    New WP6 execution uses :func:`evaluate_boundary_predicates_v2` directly so
    the comparison-signature evidence remains visible.  This narrow alias keeps
    historical helper imports deterministic without creating a second semantic
    implementation.
    """
    return dict(
        evaluate_boundary_predicates_v2(
            current,
            previous,
            explicit_source_gap=explicit_source_gap,
            release_end=release_end,
        )["matched"]
    )
