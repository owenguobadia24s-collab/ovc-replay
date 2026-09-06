from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import CBSContractError, seal_object
from .common import build_estimate


def run_b1_run_change(*, points: Sequence[Mapping[str, Any]], config_id: str, min_run_length: int,
                      evaluation_cutoff: str) -> dict[str, Any]:
    if min_run_length < 1:
        raise CBSContractError("CBS_B1_MIN_RUN_INVALID")
    ordered = sorted(points, key=lambda item: (str(item["effective_time"]), str(item.get("observation_id", ""))))
    estimates=[]
    if ordered:
        prior=ordered[0]["signature"]; run_length=1
        for point in ordered[1:]:
            current=point["signature"]
            if current != prior:
                if run_length >= min_run_length:
                    estimates.append(build_estimate(method_id="B1",family_id="CBS_B1_FAMILY",config_id=config_id,
                        temporal_class="ONLINE_CAUSAL",state="ESTIMATED",candidate_onset_time=str(point["effective_time"]),
                        effective_time=str(point["effective_time"]),confirmation_time=str(point["first_valid_time"]),
                        first_valid_time=str(point["first_valid_time"]),evaluation_cutoff=evaluation_cutoff,
                        causal_admissibility=True,reason_codes=["TYPED_SIGNATURE_CHANGE"]))
                prior=current; run_length=1
            else:
                run_length += 1
    return seal_object({"schema":"ovc-cbs-comparator-output/v0.1","method_id":"B1","config_id":config_id,
        "min_run_length":min_run_length,"estimates":estimates,"input_count":len(ordered)},id_field="output_id")
