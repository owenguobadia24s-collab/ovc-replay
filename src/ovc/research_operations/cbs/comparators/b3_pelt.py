from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import inf
from typing import Any

from ..identity import CBSContractError, seal_object
from .common import build_estimate


def _prefix(values: Sequence[float]) -> tuple[list[float], list[float]]:
    total=[0.0]; squares=[0.0]
    for value in values:
        total.append(total[-1]+value); squares.append(squares[-1]+value*value)
    return total,squares


def _sse(total: Sequence[float], squares: Sequence[float], start: int, end: int) -> float:
    count=end-start
    value_sum=total[end]-total[start]
    return max(0.0,(squares[end]-squares[start])-(value_sum*value_sum/count))


def run_b3_penalised_segmentation(*, points: Sequence[Mapping[str, Any]], config_id: str,
                                  penalty: float, min_segment_length: int,
                                  evaluation_cutoff: str) -> dict[str, Any]:
    if penalty < 0 or min_segment_length < 1:
        raise CBSContractError("CBS_B3_METHOD_PACK_INVALID")
    ordered=sorted(points,key=lambda item:(str(item["effective_time"]),str(item.get("observation_id",""))))
    values=[float(point["value"]) for point in ordered]; n=len(values)
    total,squares=_prefix(values)
    best=[inf]*(n+1); previous=[-1]*(n+1); best[0]=-penalty
    for end in range(min_segment_length,n+1):
        for start in range(0,end-min_segment_length+1):
            if start and (start < min_segment_length or best[start] == inf):
                continue
            candidate=best[start]+_sse(total,squares,start,end)+penalty
            if candidate < best[end]-1e-12 or (abs(candidate-best[end]) <= 1e-12 and start < previous[end]):
                best[end]=candidate; previous[end]=start
    break_indices=[]
    if n and best[n] < inf:
        end=n
        while previous[end] > 0:
            break_indices.append(previous[end]); end=previous[end]
        break_indices.reverse()
    estimates=[]
    confirmation = str(ordered[-1]["first_valid_time"]) if ordered else evaluation_cutoff
    for index in break_indices:
        effective=str(ordered[index]["effective_time"])
        estimates.append(build_estimate(method_id="B3",family_id="CBS_B3_FAMILY",config_id=config_id,
            temporal_class="RETROSPECTIVE",state="ESTIMATED",candidate_onset_time=effective,
            effective_time=effective,confirmation_time=confirmation,first_valid_time=confirmation,
            evaluation_cutoff=evaluation_cutoff,causal_admissibility=False,
            reason_codes=["PENALISED_OFFLINE_CHANGEPOINT","COMPARISON_ONLY"]))
    return seal_object({"schema":"ovc-cbs-comparator-output/v0.1","method_id":"B3","config_id":config_id,
        "objective":"EXACT_PENALISED_SQUARED_ERROR","penalty":penalty,"min_segment_length":min_segment_length,
        "break_indices":break_indices,"estimates":estimates,"input_count":n,"comparison_only":True,
        "causal_join":"FORBIDDEN"},id_field="output_id")
