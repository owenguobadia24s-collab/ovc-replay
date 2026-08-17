from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .contracts import PRSCContractError, semantic_id


def bind_prsc_refs_to_candidate_review_card(card: Mapping[str, Any], *, prsc_refs: Sequence[str]) -> dict[str, Any]:
    """Additive review adapter: never changes proposal eligibility or owner-defined candidate semantics."""
    result = deepcopy(dict(card))
    original_status = result.get("proposal_review_status")
    existing = list(result.get("prsc_refs", []))
    for ref in prsc_refs:
        ref = str(ref).strip()
        if ref and ref not in existing:
            existing.append(ref)
    result["prsc_refs"] = existing
    if result.get("proposal_review_status") != original_status:
        raise PRSCContractError("PRSC_ADAPTER_PROPOSAL_ELIGIBILITY_MUTATION")
    return result


def bind_prsc_refs_to_question_decision(record: Mapping[str, Any], *, prsc_refs: Sequence[str]) -> dict[str, Any]:
    """Bind PRSC evidence only to DT-Q08/DT-Q10 while preserving the existing EC1 tree result."""
    result = deepcopy(dict(record))
    if result.get("decision_tree_id") not in {"DT-Q08", "DT-Q10"}:
        raise PRSCContractError("PRSC_ADAPTER_QUESTION_NOT_Q08_Q10")
    frozen = {
        key: deepcopy(result.get(key))
        for key in ("decision_tree_id", "terminal_node", "recommended_disposition", "reserved_action_requested")
    }
    existing = list(result.get("prsc_refs", []))
    for ref in prsc_refs:
        ref = str(ref).strip()
        if ref and ref not in existing:
            existing.append(ref)
    result["prsc_refs"] = existing
    for key, value in frozen.items():
        if result.get(key) != value:
            raise PRSCContractError(f"PRSC_ADAPTER_EC1_DECISION_MUTATION:{key}")
    return result


def build_ec1_prsc_adapter_binding(*, object_type: str, object_id: str, prsc_refs: Sequence[str]) -> dict[str, Any]:
    if object_type not in {"P1CandidateReviewCard", "QuestionDecisionRecord"}:
        raise PRSCContractError("PRSC_ADAPTER_OBJECT_TYPE_INVALID")
    body = {
        "schema": "ovc-prsc-ec1-adapter-binding/v0.1",
        "object_type": object_type,
        "object_id": object_id,
        "prsc_refs": list(dict.fromkeys(str(v) for v in prsc_refs if str(v).strip())),
        "owner_semantics_mutated": False,
        "authority_effect": "NONE",
    }
    body["binding_id"] = semantic_id(body)
    return body
