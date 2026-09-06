from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import CBSContractError, seal_object
from .common import build_estimate


def run_b2_directional_change(*, points: Sequence[Mapping[str, Any]], config_id: str, threshold: float,
                              evaluation_cutoff: str) -> dict[str, Any]:
    if threshold <= 0:
        raise CBSContractError("CBS_B2_THRESHOLD_INVALID")
    ordered=sorted(points,key=lambda item:(str(item["effective_time"]),str(item.get("observation_id",""))))
    estimates=[]
    if ordered:
        low=high=float(ordered[0]["value"]); low_point=high_point=ordered[0]; mode="SEEK_EITHER"
        for point in ordered[1:]:
            value=float(point["value"])
            if value < low: low=value; low_point=point
            if value > high: high=value; high_point=point
            if mode in {"SEEK_EITHER","SEEK_UP"} and value-low >= threshold:
                estimates.append(build_estimate(method_id="B2",family_id="CBS_B2_FAMILY",config_id=config_id,
                    temporal_class="CONFIRMATION_DELAYED",state="ESTIMATED",candidate_onset_time=str(low_point["effective_time"]),
                    effective_time=str(point["effective_time"]),confirmation_time=str(point["effective_time"]),
                    first_valid_time=str(point["first_valid_time"]),evaluation_cutoff=evaluation_cutoff,
                    causal_admissibility=True,direction="UP",reason_codes=["DIRECTIONAL_THRESHOLD_CONFIRMED"]))
                mode="SEEK_DOWN"; high=value; high_point=point; low=value; low_point=point
            elif mode in {"SEEK_EITHER","SEEK_DOWN"} and high-value >= threshold:
                estimates.append(build_estimate(method_id="B2",family_id="CBS_B2_FAMILY",config_id=config_id,
                    temporal_class="CONFIRMATION_DELAYED",state="ESTIMATED",candidate_onset_time=str(high_point["effective_time"]),
                    effective_time=str(point["effective_time"]),confirmation_time=str(point["effective_time"]),
                    first_valid_time=str(point["first_valid_time"]),evaluation_cutoff=evaluation_cutoff,
                    causal_admissibility=True,direction="DOWN",reason_codes=["DIRECTIONAL_THRESHOLD_CONFIRMED"]))
                mode="SEEK_UP"; low=value; low_point=point; high=value; high_point=point
    return seal_object({"schema":"ovc-cbs-comparator-output/v0.1","method_id":"B2","config_id":config_id,
        "threshold":threshold,"estimates":estimates,"input_count":len(ordered)},id_field="output_id")
