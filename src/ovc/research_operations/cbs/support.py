from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .enums import EstimateState
from .identity import CBSContractError, seal_object


def build_support_manifest(
    *, comparator_id: str, projection_id: str, warmup: int, lookback: int,
    lookahead: int, edge_censor: int, gap_policy: str, abstention_reasons: Sequence[str],
) -> dict[str, Any]:
    values = (warmup, lookback, lookahead, edge_censor)
    if any(not isinstance(value, int) or value < 0 for value in values):
        raise CBSContractError("CBS_SUPPORT_MANIFEST_INVALID")
    return seal_object(
        {"schema":"ovc-cbs-comparator-support-manifest/v0.1", "comparator_id":comparator_id,
         "projection_id":projection_id, "warmup":warmup, "lookback":lookback, "lookahead":lookahead,
         "edge_censor":edge_censor, "gap_policy":gap_policy, "abstention_reasons":sorted(set(abstention_reasons)),
         "required_analyses":["MATCHED_SUPPORT","FULL_POPULATION"]}, id_field="support_manifest_id"
    )


def classify_support(*, index: int, total: int, manifest: Mapping[str, Any], source_gap: bool = False,
                     source_censored: bool = False, evaluable: bool = True) -> EstimateState:
    if source_gap or source_censored:
        return EstimateState.CENSORED
    if not evaluable:
        return EstimateState.NOT_EVALUABLE
    left = max(int(manifest["warmup"]), int(manifest["lookback"]), int(manifest["edge_censor"]))
    right = max(int(manifest["lookahead"]), int(manifest["edge_censor"]))
    if index < left or index >= total - right:
        return EstimateState.CENSORED
    return EstimateState.NO_ESTIMATE


def support_analysis_populations(states_by_method: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    if not states_by_method:
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE")
    lengths = {len(states) for states in states_by_method.values()}
    if len(lengths) != 1:
        raise CBSContractError("SUPPORT_MISMATCH:UNALIGNED_POPULATIONS")
    total = lengths.pop()
    evaluable = {method: {i for i, state in enumerate(states) if state not in {EstimateState.NOT_EVALUABLE.value, EstimateState.CENSORED.value}} for method, states in states_by_method.items()}
    matched = sorted(set.intersection(*evaluable.values())) if evaluable else []
    return {"full_population_indices":list(range(total)), "matched_support_indices":matched,
            "per_method_evaluable_counts":{method:len(indices) for method, indices in sorted(evaluable.items())},
            "support_differs":len({tuple(states) for states in states_by_method.values()}) > 1}
