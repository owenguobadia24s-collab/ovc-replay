from __future__ import annotations

from typing import Any, Mapping, Sequence


class PRSCRVAdapterError(ValueError):
    pass


LIMITATION_ROUTES = {"METHOD_LIMITATION", "INFORMATION_LIMITATION", "DATA_GAP", "AUTHORITY_LIMITATION"}


def bind_candidate_review_card(*, card_ref: str, candidate_ref: str, challenge_vector_ref: str, disposition_ref: str | None, review_refs: Sequence[str]) -> dict[str, Any]:
    return {
        "adapter_schema": "ovc-prsc-p1-candidate-review-card-ref-adapter/v0.1",
        "owner_record_ref": card_ref,
        "candidate_ref": candidate_ref,
        "prsc_refs": {
            "scientific_challenge_vector_ref": challenge_vector_ref,
            "scientific_disposition_ref": disposition_ref,
            "independent_scientific_review_refs": list(review_refs),
        },
        "candidate_semantics_changed": False,
        "authority_effect": "NONE",
    }


def bind_evidence_cycle_review_packet(*, packet_ref: str, candidate_adapter_refs: Sequence[str], q08_bundle_refs: Sequence[str], limitation_routes: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    for item in limitation_routes:
        if item.get("limitation_type") not in LIMITATION_ROUTES:
            raise PRSCRVAdapterError("unsupported limitation route")
        if item.get("authority_effect", "NONE") != "NONE":
            raise PRSCRVAdapterError("limitation routing cannot activate authority")
    return {
        "adapter_schema": "ovc-prsc-evidence-cycle-review-packet-ref-adapter/v0.1",
        "owner_record_ref": packet_ref,
        "candidate_adapter_refs": list(candidate_adapter_refs),
        "ec1_q08_scientific_challenge_bundle_refs": list(q08_bundle_refs),
        "limitation_routes": [dict(x) for x in limitation_routes],
        "authority_effect": "NONE",
    }


def preserve_review_disagreement(*, candidate_ref: str, review_refs: Sequence[str], dispositions: Sequence[str]) -> dict[str, Any] | None:
    if len(review_refs) != len(dispositions):
        raise PRSCRVAdapterError("review/disposition cardinality mismatch")
    unique = sorted(set(dispositions))
    if len(unique) <= 1:
        return None
    return {
        "schema": "ovc-prsc-review-disagreement-record/v0.1",
        "candidate_ref": candidate_ref,
        "review_refs": list(review_refs),
        "dispositions": list(dispositions),
        "resolution": "PRESERVE_DISAGREEMENT_NO_MAJORITY",
        "authority_effect": "NONE",
    }


def build_q08_bundle(*, candidate_ref: str, challenge_vector_ref: str, review_refs: Sequence[str], disagreement_ref: str | None, disposition_ref: str, freeze_recommendation_ref: str | None = None) -> dict[str, Any]:
    return {
        "schema": "ovc-prsc-ec1-q08-scientific-challenge-bundle/v0.1",
        "candidate_ref": candidate_ref,
        "challenge_vector_ref": challenge_vector_ref,
        "independent_review_refs": list(review_refs),
        "review_disagreement_ref": disagreement_ref,
        "scientific_disposition_ref": disposition_ref,
        "candidate_freeze_recommendation_ref": freeze_recommendation_ref,
        "candidate_freeze_effect": "NONE",
        "candidate_freeze_gate": "EC1-GSCI" if freeze_recommendation_ref else None,
        "authority_effect": "NONE",
    }
