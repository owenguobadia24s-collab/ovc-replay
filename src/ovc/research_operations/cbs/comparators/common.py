from __future__ import annotations

from datetime import datetime
from typing import Any

from ..identity import CBSContractError, seal_object


def _instant(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise CBSContractError("CBS_ESTIMATE_TIME_INVALID") from exc


def build_estimate(
    *, method_id: str, family_id: str, config_id: str, temporal_class: str, state: str,
    candidate_onset_time: str | None, effective_time: str | None, confirmation_time: str | None,
    first_valid_time: str | None, evaluation_cutoff: str, causal_admissibility: bool,
    direction: str | None = None, reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    if state == "ESTIMATED":
        times = [candidate_onset_time, effective_time, confirmation_time, first_valid_time]
        if any(value is None for value in times):
            raise CBSContractError("CBS_ESTIMATE_TIME_INCOMPLETE")
        if _instant(first_valid_time) > _instant(evaluation_cutoff):
            raise CBSContractError("CBS_FIRST_VALID_AFTER_EVALUATION_CUTOFF")
        if causal_admissibility and _instant(first_valid_time) < _instant(effective_time):
            raise CBSContractError("CBS_FIRST_VALID_BACKDATING")
    if temporal_class == "RETROSPECTIVE" and causal_admissibility:
        raise CBSContractError("CBS_RETROSPECTIVE_CAUSAL_JOIN_FORBIDDEN")
    return seal_object(
        {"schema":"ovc-cbs-boundary-estimate/v0.1", "method_id":method_id, "family_id":family_id,
         "config_id":config_id, "temporal_class":temporal_class, "state":state,
         "candidate_onset_time":candidate_onset_time, "effective_time":effective_time,
         "confirmation_time":confirmation_time, "first_valid_time":first_valid_time,
         "evaluation_cutoff":evaluation_cutoff, "causal_admissibility":causal_admissibility,
         "direction":direction, "reason_codes":sorted(set(reason_codes or [])),
         "c2e_boundary_identity":None, "episode_identity_effect":"NONE"}, id_field="estimate_id"
    )
