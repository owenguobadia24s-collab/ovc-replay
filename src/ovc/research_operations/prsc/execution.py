from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


class PRSCExecutionError(ValueError):
    pass


TERMINAL_STATES = {"COMPLETE", "NOT_EVALUABLE", "QUARANTINED", "CAPACITY_INCOMPLETE", "REVIEW_DEFERRED"}


@dataclass(frozen=True)
class ExecutionPrerequisites:
    prereg_pass: bool
    e1_complete: bool
    r1_reproduced: bool
    challenge_authority_pass: bool
    source_current: bool
    protocol_state: str


def assert_real_execution_authorized(p: ExecutionPrerequisites) -> None:
    if not (p.prereg_pass and p.e1_complete and p.r1_reproduced and p.challenge_authority_pass and p.source_current):
        raise PRSCExecutionError("real PRSC execution prerequisites incomplete")
    if p.protocol_state != "FROZEN":
        raise PRSCExecutionError("real PRSC execution requires exact FROZEN protocol generation")


def build_review_population_manifest(proposals: Sequence[Mapping[str, Any]], terminal_by_candidate: Mapping[str, str]) -> dict[str, Any]:
    ids = [str(p["candidate_ref"]) for p in proposals]
    if len(ids) != len(set(ids)):
        raise PRSCExecutionError("duplicate mechanically eligible candidate_ref")
    known = set(ids)
    missing = [cid for cid in ids if cid not in terminal_by_candidate]
    extra = [cid for cid in terminal_by_candidate if cid not in known]
    invalid = {cid: state for cid, state in terminal_by_candidate.items() if state not in TERMINAL_STATES}
    if missing or extra or invalid:
        raise PRSCExecutionError(f"population reconciliation failed missing={missing} extra={extra} invalid={invalid}")
    counts = {state: 0 for state in sorted(TERMINAL_STATES)}
    for cid in ids:
        counts[terminal_by_candidate[cid]] += 1
    return {"schema": "ovc-prsc-review-population-manifest/v0.1", "candidate_refs": ids, "counts": counts, "n_admitted": len(ids), "reconciled": True, "authority_effect": "NONE"}


def execute_candidate_synthetic(*, candidate_ref: str, protocol_generation_ref: str, dimensions: Sequence[str], handlers: Mapping[str, Callable[[str], Mapping[str, Any]]]) -> dict[str, Any]:
    results = []
    for dimension in dimensions:
        handler = handlers.get(dimension)
        if handler is None:
            results.append({"dimension": dimension, "status": "NOT_EVALUABLE", "reason_codes": ["NO_SYNTHETIC_HANDLER"]})
        else:
            result = dict(handler(candidate_ref))
            result["dimension"] = dimension
            results.append(result)
    return {"schema": "ovc-prsc-candidate-execution-record/v0.1", "candidate_ref": candidate_ref, "protocol_generation_ref": protocol_generation_ref, "execution_mode": "SYNTHETIC_BUILD_AHEAD", "dimension_results": results, "partial_review_permitted": False, "authority_effect": "NONE"}


def build_completion_receipt(*, manifest_ref: str, execution_refs: Sequence[str], population_reconciled: bool, qa_pass: bool) -> dict[str, Any]:
    status = "PASS_CANDIDATE" if population_reconciled and qa_pass else "BLOCKED"
    return {"schema": "ovc-prsc-completion-receipt/v0.1", "execution_manifest_ref": manifest_ref, "execution_refs": list(execution_refs), "population_reconciled": population_reconciled, "qa_pass": qa_pass, "status": status, "authority_effect": "NONE"}
