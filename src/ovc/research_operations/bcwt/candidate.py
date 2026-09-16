from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable

from ovc.research_operations.canonical import canonical_sha256

from .mechanical import BCWTValidationError

CANDIDATE_GENERATION_ID = "BCWT-ORG-RECONFIGURATION:1"
EXPECTED_OPPORTUNITY_COUNT = 5238
MEMBERSHIP_STATES = frozenset({
    "MATCH", "NON_MATCH", "AMBIGUOUS", "NOT_EVALUABLE", "NOT_COMPARABLE",
    "CENSORED", "QUARANTINED", "OUT_OF_SCOPE", "PROCESS_INVALID",
})
_FORBIDDEN_KEY_TOKENS = (
    "future", "outcome", "consequence", "probability", "expected_return", "trade",
    "position", "sff", "c2e_episode", "c2p_persistent", "validation_result",
)
_REQUIRED = frozenset({
    "population_unit_id", "segment_id", "start_sequence_id", "end_sequence_id",
    "start_fvt_ms", "end_fvt_ms", "source_ref", "d10_local_frame_relocation",
    "d12_continuation_persistence", "d14_internal_reorganisation",
    "d15_same_uninterrupted_segment", "d16_relation_before", "d16_relation_after",
    "d16_evaluable", "d17_load_bearing_evaluable",
})


def _reject_outcome_fields(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            token = str(key).lower()
            if any(forbidden in token for forbidden in _FORBIDDEN_KEY_TOKENS):
                raise PermissionError(f"BCWT-R3-WP3 outcome-blind firewall: {path}{key}")
            _reject_outcome_fields(item, f"{path}{key}.")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_outcome_fields(item, f"{path}{index}.")


def _observed(value: Any) -> bool:
    return str(value).upper() == "OBSERVED"


def _validate_source_row(row: dict[str, Any]) -> None:
    missing = _REQUIRED - set(row)
    if missing:
        raise BCWTValidationError(f"BCWT-R3-WP3 source row missing fields: {','.join(sorted(missing))}")
    _reject_outcome_fields(row)
    if not str(row["population_unit_id"]):
        raise BCWTValidationError("empty population_unit_id")
    if int(row["end_sequence_id"]) != int(row["start_sequence_id"]) + 1:
        raise BCWTValidationError("non-adjacent OPGS-R3 transition account")
    if int(row["end_fvt_ms"]) <= int(row["start_fvt_ms"]):
        raise BCWTValidationError("non-increasing transition FVT")
    if row["d15_same_uninterrupted_segment"] is not True:
        raise BCWTValidationError("cross-segment/non-continuous account cannot enter frozen population")


def classify_membership(row: dict[str, Any]) -> dict[str, Any]:
    """Classify one frozen OPGS-R3 opportunity without reading any consequence payload."""
    _validate_source_row(row)
    reasons: list[str] = []
    if row["d17_load_bearing_evaluable"] is not True:
        state = "NOT_EVALUABLE"
        reasons.append("D17_LOAD_BEARING_FIELDS_NOT_EVALUABLE")
    else:
        d10 = _observed(row["d10_local_frame_relocation"])
        d12 = _observed(row["d12_continuation_persistence"])
        d14 = _observed(row["d14_internal_reorganisation"])
        d16_evaluable = row["d16_evaluable"] is True
        d16_changed = d16_evaluable and row["d16_relation_before"] != row["d16_relation_after"]
        d16_unchanged = d16_evaluable and row["d16_relation_before"] == row["d16_relation_after"]

        if d10 or d14 or d16_changed:
            state = "MATCH"
            if d10:
                reasons.append("D10_RELOCATION_OBSERVED")
            if d14:
                reasons.append("D14_REORGANISATION_OBSERVED")
            if d16_changed:
                reasons.append("D16_RELATION_CHANGED")
        elif d12 and not d10 and not d14 and d16_unchanged:
            state = "NON_MATCH"
            reasons.extend(("D12_CONTINUATION_OBSERVED", "D16_RELATION_UNCHANGED", "D15_CONTINUITY_CONFIRMED"))
        else:
            state = "AMBIGUOUS"
            if not d16_evaluable:
                reasons.append("D16_NOT_EVALUABLE")
            if not d12:
                reasons.append("D12_CONTINUATION_NOT_OBSERVED")
            if not reasons:
                reasons.append("FROZEN_RULES_NEITHER_MATCH_NOR_NON_MATCH")

    return {
        "population_unit_id": str(row["population_unit_id"]),
        "state": state,
        "first_valid_time": str(row["end_fvt_ms"]),
        "reason_codes": reasons,
        "source_ref": deepcopy(row["source_ref"]),
    }


def compile_membership_ledger(
    rows: Iterable[dict[str, Any]], *, expected_count: int = EXPECTED_OPPORTUNITY_COUNT
) -> dict[str, Any]:
    source_rows = [deepcopy(row) for row in rows]
    entries = [classify_membership(row) for row in source_rows]
    ids = [entry["population_unit_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise BCWTValidationError("duplicate population_unit_id in membership ledger")
    if len(entries) != expected_count:
        raise BCWTValidationError(f"complete denominator failure: expected {expected_count}, got {len(entries)}")
    counts = Counter(entry["state"] for entry in entries)
    ledger = {
        "schema": "ovc-bcwt-r3-membership-ledger/v0_1",
        "candidate_generation_id": CANDIDATE_GENERATION_ID,
        "expected_opportunities": expected_count,
        "actual_opportunities": len(entries),
        "membership_state_counts": {state: counts.get(state, 0) for state in sorted(MEMBERSHIP_STATES)},
        "entries": entries,
        "source_rows_sha256": canonical_sha256(source_rows),
        "authority_effect": "NONE",
        "scientific_effect": "NONE_OUTCOME_BLIND_MEMBERSHIP_ONLY",
    }
    ledger["ledger_sha256"] = canonical_sha256(ledger)
    return ledger


def compile_occurrences(ledger: dict[str, Any]) -> list[dict[str, str]]:
    if ledger.get("candidate_generation_id") != CANDIDATE_GENERATION_ID:
        raise BCWTValidationError("candidate generation mismatch")
    return [
        {
            "candidate_generation_id": CANDIDATE_GENERATION_ID,
            "population_unit_id": entry["population_unit_id"],
        }
        for entry in ledger.get("entries", [])
        if entry.get("state") == "MATCH"
    ]
