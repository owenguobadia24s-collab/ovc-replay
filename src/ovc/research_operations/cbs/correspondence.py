from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object
from .regions import parse_instant


def _seconds(a: object, b: object) -> float:
    return (parse_instant(a)-parse_instant(b)).total_seconds()


def _rows(rows: Sequence[Mapping[str, Any]], *, id_key: str, time_key: str) -> list[Mapping[str, Any]]:
    estimated=[row for row in rows if row.get("state","ESTIMATED") == "ESTIMATED"]
    ids=[str(row.get(id_key,"")) for row in estimated]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise CBSContractError("CBS_CORRESPONDENCE_ID_INVALID")
    return sorted(estimated,key=lambda row:(parse_instant(row[time_key]),str(row[id_key])))


def directional_correspondence(*, references: Sequence[Mapping[str, Any]], challengers: Sequence[Mapping[str, Any]],
                               tolerance_seconds: float, estimand: str,
                               source_events: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    if tolerance_seconds < 0 or estimand not in {"REFERENCE_BOUNDARY_AUDIT","CONSENSUS_BOUNDARY_DISCOVERY"}:
        raise CBSContractError("CBS_CORRESPONDENCE_INPUT_INVALID")
    refs=_rows(references,id_key="region_id",time_key="anchor_time")
    chall=_rows(challengers,id_key="estimate_id",time_key="effective_time")
    relations: dict[str,list[tuple[str,float]]] = {str(ref["region_id"]):[] for ref in refs}
    reverse: dict[str,list[tuple[str,float]]] = {str(item["estimate_id"]):[] for item in chall}
    for ref in refs:
        for item in chall:
            delta=_seconds(item["effective_time"],ref["anchor_time"])
            if abs(delta) <= tolerance_seconds:
                relations[str(ref["region_id"])].append((str(item["estimate_id"]),delta))
                reverse[str(item["estimate_id"])].append((str(ref["region_id"]),delta))

    # Ordered dynamic programming maximises one-to-one match cardinality, then
    # minimises displacement, then uses stable pair identities as a tie-break.
    empty: tuple[int,float,tuple[tuple[str,str,float],...]]=(0,0.0,())
    dp=[[empty for _ in range(len(chall)+1)] for _ in range(len(refs)+1)]
    def better(left: tuple[int,float,tuple], right: tuple[int,float,tuple]) -> tuple[int,float,tuple]:
        return left if (-left[0],left[1],left[2]) <= (-right[0],right[1],right[2]) else right
    for i in range(len(refs)+1):
        for j in range(len(chall)+1):
            if i==0 and j==0:
                continue
            candidates=[]
            if i: candidates.append(dp[i-1][j])
            if j: candidates.append(dp[i][j-1])
            if i and j:
                ref_id=str(refs[i-1]["region_id"]); estimate_id=str(chall[j-1]["estimate_id"])
                delta=_seconds(chall[j-1]["effective_time"],refs[i-1]["anchor_time"])
                if abs(delta) <= tolerance_seconds:
                    prior=dp[i-1][j-1]
                    candidates.append((prior[0]+1,prior[1]+abs(delta),prior[2]+((ref_id,estimate_id,delta),)))
            best=candidates[0]
            for candidate in candidates[1:]: best=better(best,candidate)
            dp[i][j]=best
    pairs=dp[-1][-1][2]
    used_refs={pair[0] for pair in pairs}; used_estimates={pair[1] for pair in pairs}
    matches=[{"region_id":ref_id,"estimate_id":estimate_id,"signed_displacement_seconds":format(delta,".12g"),
              "direction":"EARLY" if delta<0 else "LATE" if delta>0 else "EXACT"}
             for ref_id,estimate_id,delta in pairs]

    ambiguity=[]
    for ref_id,values in sorted(relations.items()):
        if values:
            minimum=min(abs(delta) for _,delta in values)
            tied=sorted(estimate_id for estimate_id,delta in values if abs(abs(delta)-minimum) <= 1e-12)
            if len(tied)>1:
                ambiguity.append({"kind":"REFERENCE_EQUIDISTANT","region_id":ref_id,"estimate_ids":tied})
    for estimate_id,values in sorted(reverse.items()):
        if values:
            minimum=min(abs(delta) for _,delta in values)
            tied=sorted(ref_id for ref_id,delta in values if abs(abs(delta)-minimum) <= 1e-12)
            if len(tied)>1:
                ambiguity.append({"kind":"ESTIMATE_EQUIDISTANT","estimate_id":estimate_id,"region_ids":tied})

    splits=[{"region_id":ref_id,"estimate_ids":sorted(estimate_id for estimate_id,_ in values)}
            for ref_id,values in sorted(relations.items()) if len(values)>1]
    merges=[{"estimate_id":estimate_id,"region_ids":sorted(ref_id for ref_id,_ in values)}
            for estimate_id,values in sorted(reverse.items()) if len(values)>1]
    typed_events=[]
    for event in source_events:
        classification=str(event.get("classification",""))
        if classification not in {"CENSOR","SOURCE_GAP"}:
            raise CBSContractError("CBS_CORRESPONDENCE_SOURCE_EVENT_INVALID")
        typed_events.append(dict(event))
    payload={"schema":"ovc-cbs-boundary-correspondence-ledger/v0.1","estimand":estimand,
        "tolerance_seconds":format(tolerance_seconds,".12g"),"matches":sorted(matches,key=lambda row:(row["region_id"],row["estimate_id"])),
        "splits":splits,"merges":merges,"ambiguities":ambiguity,
        "unmatched_region_ids":sorted(str(ref["region_id"]) for ref in refs if str(ref["region_id"]) not in used_refs),
        "unmatched_estimate_ids":sorted(str(item["estimate_id"]) for item in chall if str(item["estimate_id"]) not in used_estimates),
        "typed_source_events":typed_events,"reference_count":len(refs),"challenger_count":len(chall),
        "one_to_one_first":True,"complete_accounting":len(used_refs)+sum(str(ref["region_id"]) not in used_refs for ref in refs)==len(refs),
        "comparator_identity_rewrite":"NONE","ground_truth":False}
    return seal_object(payload,id_field="correspondence_ledger_id")


def correspondence_tolerance_surface(*, references: Sequence[Mapping[str, Any]], challengers: Sequence[Mapping[str, Any]],
                                     tolerance_grid: Mapping[str, Any], estimand: str) -> dict[str, Any]:
    ledgers=[directional_correspondence(references=references,challengers=challengers,
        tolerance_seconds=float(entry["tolerance_seconds"]),estimand=estimand) for entry in tolerance_grid["entries"]]
    return seal_object({"schema":"ovc-cbs-correspondence-tolerance-surface/v0.1","estimand":estimand,
        "tolerance_grid_id":tolerance_grid["tolerance_grid_id"],"ledgers":ledgers,"selected_best_tolerance":None,
        "complete_grid":True},id_field="correspondence_surface_id")
