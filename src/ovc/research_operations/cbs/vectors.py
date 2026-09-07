from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from .identity import CBSContractError, seal_object


SUPPORT_PLANES = (
    "method", "location", "temporal", "parameter", "representation", "chronology", "context",
    "transport", "topology", "null", "dependence", "missingness_conflict", "support", "estimand",
)
FORBIDDEN_SCALAR_FIELDS = frozenset({"score", "probability", "weighted_score", "mean_support", "majority_vote"})


def build_boundary_support_vector(
    *, region_id: str, estimand: str, planes: Mapping[str, Any],
    projection_ids: Sequence[str], universe_id: str, materiality_ref: str | None = None,
) -> dict[str, Any]:
    missing = [name for name in SUPPORT_PLANES if name not in planes]
    forbidden = sorted(FORBIDDEN_SCALAR_FIELDS & set(planes))
    if missing:
        raise CBSContractError(f"BOUNDARY_SUPPORT_UNRESOLVED:MISSING_PLANES:{','.join(missing)}")
    if forbidden:
        raise CBSContractError(f"NO_VOTE_NO_AVERAGE:{','.join(forbidden)}")
    if estimand not in {"REFERENCE_BOUNDARY_AUDIT", "CONSENSUS_BOUNDARY_DISCOVERY"}:
        raise CBSContractError("ESTIMAND_CROSSING")
    if not region_id or not universe_id or not projection_ids:
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE")
    return seal_object(
        {
            "schema": "ovc-cbs-boundary-support-vector/v0.1",
            "region_id": region_id,
            "estimand": estimand,
            "planes": {name: planes[name] for name in SUPPORT_PLANES},
            "projection_ids": sorted(set(projection_ids)),
            "evaluation_universe_id": universe_id,
            "materiality_ref": materiality_ref,
            "scalar_score": None,
            "calibrated_probability": None,
            "aggregation": "FAMILY_AND_DEPENDENCE_FACTORISED_NO_VOTE_NO_AVERAGE",
        },
        id_field="support_vector_id",
    )


def _instant(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise CBSContractError("CBS_ESTIMATE_TIME_INVALID") from exc


def build_causal_admissibility_vector(*, region_id: str, estimates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not estimates:
        raise CBSContractError("CAUSAL_ADMISSION_FAIL:NO_ESTIMATES")
    rows: list[dict[str, Any]] = []
    for estimate in estimates:
        temporal_class = str(estimate.get("temporal_class", ""))
        causal = bool(estimate.get("causal_admissibility", False))
        if temporal_class == "RETROSPECTIVE" and causal:
            raise CBSContractError("RETROSPECTIVE_CAUSAL_JOIN_FORBIDDEN")
        effective = estimate.get("effective_time")
        first_valid = estimate.get("first_valid_time")
        confirmation = estimate.get("confirmation_time")
        if causal:
            if not effective or not first_valid or _instant(str(first_valid)) < _instant(str(effective)):
                raise CBSContractError("FVT_BACKDATE_ATTEMPT")
            if temporal_class not in {"ONLINE_CAUSAL", "CONFIRMATION_DELAYED", "OWNER_DEFINED_ONLINE_CAUSAL"}:
                raise CBSContractError("CAUSAL_ADMISSION_FAIL:INADMISSIBLE_TEMPORAL_CLASS")
        latency = None
        if effective and first_valid:
            latency = (_instant(str(first_valid)) - _instant(str(effective))).total_seconds()
            if latency < 0:
                raise CBSContractError("FVT_BACKDATE_ATTEMPT")
        rows.append(
            {
                "estimate_id": str(estimate.get("estimate_id", "")),
                "method_id": str(estimate.get("method_id", "")),
                "temporal_class": temporal_class,
                "candidate_onset_time": estimate.get("candidate_onset_time"),
                "effective_time": effective,
                "confirmation_time": confirmation,
                "first_valid_time": first_valid,
                "evaluation_cutoff": estimate.get("evaluation_cutoff"),
                "causal_admissible": causal,
                "latency_seconds": latency,
                "evidence_role": "SUPPORT_ONLY" if temporal_class == "RETROSPECTIVE" else "CAUSAL_OR_CONFIRMATION_CANDIDATE",
            }
        )
    return seal_object(
        {
            "schema": "ovc-cbs-causal-boundary-admissibility-vector/v0.1",
            "region_id": region_id,
            "entries": sorted(rows, key=lambda row: (row["method_id"], row["estimate_id"])),
            "causal_admissible_count": sum(row["causal_admissible"] for row in rows),
            "retrospective_causal_count": 0,
            "location_stability_grants_causality": False,
        },
        id_field="causal_admissibility_vector_id",
    )
