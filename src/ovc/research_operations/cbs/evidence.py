from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object


EVIDENCE_CLASSES = ("supporting", "contradicting", "null", "missing", "transport")


def build_method_disagreement_record(*, region_id: str, clusters: Sequence[Mapping[str, Any]], typed_source_events: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    if any(event.get("classification") == "SOURCE_GAP" and event.get("counted_as_disagreement") for event in typed_source_events):
        raise CBSContractError("SOURCE_GAP_NOT_METHOD_DISAGREEMENT")
    return seal_object(
        {"schema": "ovc-cbs-method-disagreement-record/v0.1", "region_id": region_id,
         "clusters": sorted((dict(row) for row in clusters), key=lambda row: str(row.get("cluster_id", ""))),
         "typed_source_events": list(typed_source_events), "coerced_consensus": False},
        id_field="method_disagreement_record_id",
    )


def build_uncertainty_record(*, region_id: str, topology: Mapping[str, Any], displacement_surface_ids: Sequence[str], disagreement_record_id: str) -> dict[str, Any]:
    return seal_object(
        {"schema": "ovc-cbs-boundary-uncertainty-record/v0.1", "region_id": region_id, "topology": dict(topology),
         "displacement_surface_ids": sorted(set(displacement_surface_ids)),
         "method_disagreement_record_id": disagreement_record_id, "canonical_timestamp": None,
         "mean_timestamp_forbidden": True}, id_field="boundary_uncertainty_record_id"
    )


def build_evidence_dossier(*, region_id: str, evidence_refs: Mapping[str, Sequence[str]], support_vector_id: str, causal_vector_id: str) -> dict[str, Any]:
    missing = [name for name in EVIDENCE_CLASSES if name not in evidence_refs]
    if missing:
        raise CBSContractError(f"BOUNDARY_SUPPORT_UNRESOLVED:MISSING_DOSSIER:{','.join(missing)}")
    return seal_object(
        {"schema": "ovc-cbs-boundary-evidence-dossier/v0.1", "region_id": region_id,
         "evidence_refs": {name: sorted(set(evidence_refs[name])) for name in EVIDENCE_CLASSES},
         "support_vector_id": support_vector_id, "causal_admissibility_vector_id": causal_vector_id,
         "content_addressed_references_only": True}, id_field="boundary_evidence_dossier_id"
    )


def build_concordance_surface(*, estimand: str, rows: Sequence[Mapping[str, Any]], universe_id: str, matched_support_id: str, full_population_id: str) -> dict[str, Any]:
    if not matched_support_id or not full_population_id:
        raise CBSContractError("SUPPORT_MISMATCH")
    forbidden = {"probability", "score", "weighted_score", "majority_vote"}
    if any(forbidden & set(row) for row in rows):
        raise CBSContractError("NO_VOTE_NO_AVERAGE")
    return seal_object(
        {"schema": "ovc-cbs-boundary-concordance-surface/v0.1", "estimand": estimand,
         "rows": list(rows), "evaluation_universe_id": universe_id, "matched_support_id": matched_support_id,
         "full_population_id": full_population_id, "non_probabilistic": True,
         "aggregation": "FAMILY_AND_DEPENDENCE_FACTORISED", "causal_claim_effect": "NONE"},
        id_field="concordance_surface_id",
    )
