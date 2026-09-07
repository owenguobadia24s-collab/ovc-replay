from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from .identity import CBSContractError, seal_object


def parse_instant(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise CBSContractError("CBS_REGION_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise CBSContractError("CBS_REGION_TIME_UNZONED")
    return parsed.astimezone(timezone.utc)


def format_instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _estimated(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    output = [row for row in rows if row.get("state") == "ESTIMATED"]
    return sorted(output, key=lambda row: (parse_instant(row["effective_time"]), str(row["estimate_id"])))


def build_tolerance_grid(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not entries:
        raise CBSContractError("CBS_TOLERANCE_GRID_EMPTY")
    groups: dict[str, list[str]] = {}
    for entry in entries:
        provenance_id = str(entry.get("configuration_id", "")).strip()
        try:
            seconds = float(entry.get("seconds"))
        except (TypeError, ValueError) as exc:
            raise CBSContractError("CBS_TOLERANCE_INVALID") from exc
        if not provenance_id or seconds < 0 or seconds != seconds or seconds == float("inf"):
            raise CBSContractError("CBS_TOLERANCE_INVALID")
        semantic = format(seconds, ".12g")
        groups.setdefault(semantic, []).append(provenance_id)
    rows = [
        {"tolerance_seconds": key, "provenance_configuration_ids": sorted(ids), "family_weight": 1}
        for key, ids in sorted(groups.items(), key=lambda item: float(item[0]))
    ]
    return seal_object(
        {"schema": "ovc-cbs-tolerance-grid/v0.1", "entries": rows,
         "declared_configuration_count": sum(len(ids) for ids in groups.values()),
         "semantic_tolerance_count": len(rows), "best_tolerance_selection": "FORBIDDEN"},
        id_field="tolerance_grid_id",
    )


def build_reference_regions(*, reference_estimates: Sequence[Mapping[str, Any]], tolerance_seconds: float,
                            estimand_denominator_id: str) -> dict[str, Any]:
    if tolerance_seconds < 0 or not estimand_denominator_id:
        raise CBSContractError("CBS_REFERENCE_REGION_INPUT_INVALID")
    regions=[]
    for estimate in _estimated(reference_estimates):
        if estimate.get("method_id") != "B0":
            raise CBSContractError("CBS_REFERENCE_REGION_NON_B0_INPUT")
        center=parse_instant(estimate["effective_time"]); delta=timedelta(seconds=tolerance_seconds)
        regions.append(seal_object(
            {"schema":"ovc-cbs-boundary-candidate-region/v0.1","estimand":"REFERENCE_BOUNDARY_AUDIT",
             "estimand_denominator_id":estimand_denominator_id,"reference_estimate_id":estimate["estimate_id"],
             "member_estimate_ids":[estimate["estimate_id"]],"window_start":format_instant(center-delta),
             "window_end":format_instant(center+delta),"anchor_time":format_instant(center),
             "tolerance_seconds":format(tolerance_seconds,".12g"),"ground_truth":False},id_field="region_id"))
    return seal_object({"schema":"ovc-cbs-boundary-candidate-region-set/v0.1","estimand":"REFERENCE_BOUNDARY_AUDIT",
        "estimand_denominator_id":estimand_denominator_id,"regions":regions,"region_count":len(regions),
        "privileged_reference":"B0_FROZEN_PROJECTION_ONLY"},id_field="region_set_id")


def build_consensus_regions(*, estimates: Sequence[Mapping[str, Any]], tolerance_seconds: float,
                            estimand_denominator_id: str) -> dict[str, Any]:
    if tolerance_seconds < 0 or not estimand_denominator_id:
        raise CBSContractError("CBS_CONSENSUS_REGION_INPUT_INVALID")
    ordered=_estimated(estimates); clusters: list[list[Mapping[str, Any]]] = []
    for estimate in ordered:
        instant=parse_instant(estimate["effective_time"])
        if not clusters or (instant-parse_instant(clusters[-1][-1]["effective_time"])).total_seconds() > tolerance_seconds:
            clusters.append([estimate])
        else:
            clusters[-1].append(estimate)
    regions=[]
    for cluster in clusters:
        member_ids=sorted(str(item["estimate_id"]) for item in cluster)
        start=parse_instant(cluster[0]["effective_time"]); end=parse_instant(cluster[-1]["effective_time"])
        anchor=min(cluster,key=lambda item:(parse_instant(item["effective_time"]),str(item["estimate_id"])))
        regions.append(seal_object(
            {"schema":"ovc-cbs-boundary-candidate-region/v0.1","estimand":"CONSENSUS_BOUNDARY_DISCOVERY",
             "estimand_denominator_id":estimand_denominator_id,"reference_estimate_id":None,
             "member_estimate_ids":member_ids,"window_start":format_instant(start),"window_end":format_instant(end),
             "anchor_time":str(anchor["effective_time"]),"tolerance_seconds":format(tolerance_seconds,".12g"),
             "ground_truth":False,"representative_rule":"EARLIEST_MEMBER_NOT_AVERAGE"},id_field="region_id"))
    return seal_object({"schema":"ovc-cbs-boundary-candidate-region-set/v0.1","estimand":"CONSENSUS_BOUNDARY_DISCOVERY",
        "estimand_denominator_id":estimand_denominator_id,"regions":regions,"region_count":len(regions),
        "privileged_reference":None,"symmetric":True},id_field="region_set_id")
