from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .enums import OpportunityState
from .identity import CBSContractError, seal_object


def build_evaluation_universe(*, population_id: str, opportunity_keys: Sequence[str], evaluation_cutoff: str) -> dict[str, Any]:
    keys = list(opportunity_keys)
    if len(keys) != len(set(keys)):
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE:DUPLICATE_OPPORTUNITY")
    opportunities = [{"opportunity_id":key, "ordinal":index, "evaluation_cutoff":evaluation_cutoff,
                      "state":OpportunityState.NO_ESTIMATE.value} for index, key in enumerate(keys)]
    return seal_object(
        {"schema":"ovc-cbs-boundary-evaluation-universe/v0.1", "population_id":population_id,
         "formed_before_detection":True, "opportunities":opportunities, "opportunity_count":len(opportunities),
         "allowed_states":[state.value for state in OpportunityState]}, id_field="universe_id"
    )


def reconcile_opportunities(universe: Mapping[str, Any], updates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    keys = [item["opportunity_id"] for item in universe.get("opportunities", [])]
    if len(keys) != universe.get("opportunity_count") or len(keys) != len(set(keys)):
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE:COUNT_CONSERVATION")
    by_id = {str(update.get("opportunity_id")): str(update.get("state")) for update in updates}
    if len(by_id) != len(updates) or set(by_id) - set(keys):
        raise CBSContractError("ASCERTAINMENT_FAIL:UNKNOWN_OR_DUPLICATE_OPPORTUNITY")
    allowed = set(universe.get("allowed_states", []))
    states = [by_id.get(key, OpportunityState.NO_ESTIMATE.value) for key in keys]
    if set(states) - allowed:
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE:INVALID_STATE")
    counts = dict(sorted(Counter(states).items()))
    if sum(counts.values()) != len(keys):
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE:COUNT_CONSERVATION")
    return seal_object(
        {"schema":"ovc-cbs-evaluation-universe-reconciliation/v0.1", "universe_id":universe["universe_id"],
         "opportunity_count":len(keys), "state_counts":counts, "count_conserved":True,
         "positive_only_denominator":False}, id_field="reconciliation_id"
    )
