"""Threshold-free preregistered June empirical boundary rules for C2E v0.2.

This module evaluates only first-valid C2EInputFrame facts already admitted by
the v0.2 handoff.  It does not read families, outcomes, Validation, C2.5/C3,
research queues, future path, probability, risk, exposure or execution state.
The rule pack is a CANDIDATE only: inactive, noncanonical and not an active C2E
selector.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

RULE_IDS = (
    "C2E.RULE.JUNE.BASELINE.CENSOR_GAP.v1",
    "C2E.RULE.JUNE.BASELINE.CENSOR_RELEASE_END.v1",
    "C2E.RULE.JUNE.BASELINE.RE_PARENT.v1",
    "C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1",
    "C2E.RULE.JUNE.BASELINE.CONTINUATION.v1",
    "C2E.RULE.JUNE.BASELINE.BIRTH.v1",
)

PROHIBITED_KEYS = {
    "family_id", "family", "medoid", "distance", "outcome", "future",
    "probability", "risk", "exposure", "trade", "trading", "execution",
    "c2_5", "c3", "semantic_label", "target", "stop",
}


class EmpiricalBoundaryRuleError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in PROHIBITED_KEYS:
                raise EmpiricalBoundaryRuleError(f"PROHIBITED_BOUNDARY_INPUT:{path}.{key}")
            _scan(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan(item, f"{path}[{index}]")


def _required(frame: Mapping[str, Any]) -> None:
    for key in ("identity", "chronology", "structural", "context", "evidence", "lineage"):
        if key not in frame:
            raise EmpiricalBoundaryRuleError(f"FRAME_FIELD_REQUIRED:{key}")
    for key in ("continuity_segment_id", "first_valid_time", "evaluation_cutoff"):
        if not frame["chronology"].get(key):
            raise EmpiricalBoundaryRuleError(f"CHRONOLOGY_REQUIRED:{key}")
    for axis in ("location_record_ids", "motion_record_ids", "organisation_record_ids", "interaction_record_ids"):
        if axis not in frame["structural"]:
            raise EmpiricalBoundaryRuleError(f"STRUCTURAL_AXIS_REQUIRED:{axis}")


def _structural_signature(frame: Mapping[str, Any]) -> str:
    structural = frame["structural"]
    payload = {
        "location_record_ids": sorted(structural.get("location_record_ids", [])),
        "motion_record_ids": sorted(structural.get("motion_record_ids", [])),
        "organisation_record_ids": sorted(structural.get("organisation_record_ids", [])),
        "interaction_record_ids": sorted(structural.get("interaction_record_ids", [])),
        "level_record_ids": sorted(structural.get("level_record_ids", [])),
        "container_record_ids": sorted(structural.get("container_record_ids", [])),
        "relation_set_id": structural.get("relation_set_id"),
        "transition_record_ids": sorted(structural.get("transition_record_ids", [])),
        "run_record_ids": sorted(structural.get("run_record_ids", [])),
    }
    return _digest(payload)


def _parent_signature(frame: Mapping[str, Any]) -> str:
    context = frame["context"]
    payload = {
        "context_resolution_bundle_id": context.get("context_resolution_bundle_id"),
        "fixed_parent_links": sorted(context.get("fixed_parent_links", [])),
        "structural_object_links": sorted(context.get("structural_object_links", [])),
        "parent_axis_links": sorted(context.get("parent_axis_links", [])),
    }
    return _digest(payload)


def evaluate_boundary_predicates(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None = None,
    *,
    explicit_source_gap: bool = False,
    release_end: bool = False,
) -> dict[str, Any]:
    """Evaluate the exact preregistered baseline predicates.

    The baseline is deliberately threshold-free.  Episode identity begins at a
    lawful continuity-segment start and persists across structural changes;
    structural changes become PHASE_MUTATION, while contextual-parent changes
    become RE_PARENT.  Explicit source gaps/release-end censor ordinary
    continuation.  No ordinary semantic TERMINATE/SPLIT/MERGE/NEST predicate is
    inferred.
    """
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

    current_structural = _structural_signature(current)
    current_parent = _parent_signature(current)
    prior_structural = None if previous is None else _structural_signature(previous)
    prior_parent = None if previous is None else _parent_signature(previous)

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
        "schema": "ovc-c2e-empirical-boundary-evaluation/v1",
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
