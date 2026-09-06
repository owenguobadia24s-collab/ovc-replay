from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import CBSContractError, seal_object, verify_object
from .common import build_estimate


def run_b0_reference(*, projected_events: Sequence[Mapping[str, Any]], b0_projection: Mapping[str, Any],
                     config_id: str, evaluation_cutoff: str) -> dict[str, Any]:
    verify_object(b0_projection, id_field="b0_projection_id")
    if b0_projection.get("status") not in {"FROZEN_SYNTHETIC", "FROZEN_DEVELOPMENT"}:
        raise CBSContractError("INPUT_PROJECTION_UNFROZEN:B0")
    estimates, typed_non_estimates = [], []
    classes = b0_projection["action_classes"]
    for event in sorted(projected_events, key=lambda item: (str(item.get("effective_time")), str(item.get("event_id")))):
        action = str(event.get("action", ""))
        classification = classes.get(action)
        if classification is None:
            raise CBSContractError("C2E_REFERENCE_PACK_UNRESOLVED:UNKNOWN_ACTION")
        if classification == "REFERENCE_BOUNDARY":
            effective = str(event["effective_time"]); first_valid = str(event["first_valid_time"])
            estimates.append(build_estimate(method_id="B0",family_id="OWNER_C2E_REFERENCE",config_id=config_id,
                temporal_class="OWNER_DEFINED_ONLINE_CAUSAL",state="ESTIMATED",candidate_onset_time=effective,
                effective_time=effective,confirmation_time=first_valid,first_valid_time=first_valid,
                evaluation_cutoff=evaluation_cutoff,causal_admissibility=True,reason_codes=[action]))
        else:
            typed_non_estimates.append({"event_id":event.get("event_id"),"action":action,"classification":classification})
    return seal_object({"schema":"ovc-cbs-comparator-output/v0.1","method_id":"B0","config_id":config_id,
        "estimates":estimates,"typed_non_estimates":typed_non_estimates,"owner_pack_id":b0_projection["pack_id"],
        "owner_identity_mutation":"NONE"},id_field="output_id")
