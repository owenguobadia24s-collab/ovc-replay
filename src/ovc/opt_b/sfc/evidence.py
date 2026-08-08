from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from typing import Any, Mapping, Sequence

from .serialization import logical_hash


def _families(catalog: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    return {str(row["family_id"]):frozenset(str(x) for x in row.get("member_ids",[])) for row in catalog.get("families",[])}


def correspondence(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    lf,rf=_families(left),_families(right); edges=[]
    for lid,lm in sorted(lf.items()):
        for rid,rm in sorted(rf.items()):
            inter=lm&rm
            if not inter: continue
            union=lm|rm
            edge={"left_family_id":lid,"right_family_id":rid,"shared_member_ids":sorted(inter),"shared_count":len(inter),"union_count":len(union),"jaccard":f"{len(inter)}/{len(union)}","left_containment":f"{len(inter)}/{len(lm)}","right_containment":f"{len(inter)}/{len(rm)}"}
            edge["logical_hash"]=logical_hash(edge); edges.append(edge)
    by_l=defaultdict(list); by_r=defaultdict(list)
    for edge in edges:
        by_l[edge["left_family_id"]].append(edge["right_family_id"]); by_r[edge["right_family_id"]].append(edge["left_family_id"])
    payload={"left_catalog_id":left.get("family_catalog_id"),"right_catalog_id":right.get("family_catalog_id"),"edges":edges,"split_events":[{"left_family_id":k,"right_family_ids":sorted(v)} for k,v in sorted(by_l.items()) if len(v)>1],"merge_events":[{"left_family_ids":sorted(v),"right_family_id":k} for k,v in sorted(by_r.items()) if len(v)>1],"left_family_denominator":len(lf),"right_family_denominator":len(rf),"authority_state":"INACTIVE_CONFORMANCE_ONLY"}
    return {**payload,"correspondence_id":"SFC.CORR."+logical_hash(payload)[:24],"logical_hash":logical_hash(payload)}


def rate_record(metric_type: str, numerator: int, denominator: int, *, left_scope: str, right_scope: str|None=None, zero_reason: str="ZERO_DENOMINATOR", rule_pack_ids: Sequence[str]=()) -> dict[str, Any]:
    if numerator<0 or denominator<0 or numerator>denominator:
        raise ValueError("SFC_METRIC_DENOMINATOR_INVALID")
    status="EVALUATED" if denominator else "NOT_EVALUABLE"
    rate=f"{numerator}/{denominator}" if denominator else None
    payload={"metric_id":"","metric_type":metric_type,"left_scope":left_scope,"right_scope":right_scope,"numerator":numerator,"denominator":denominator,"rate":rate,"status":status,"reason_code":None if denominator else zero_reason,"rule_pack_ids":list(rule_pack_ids),"lineage":{"exact_counts":True},"authority_state":"INACTIVE_CONFORMANCE_ONLY"}
    payload["metric_id"]="SFC.METRIC."+logical_hash(payload)[:24]; payload["logical_hash"]=logical_hash(payload)
    return payload


def residual_rate(catalog: Mapping[str, Any]) -> dict[str, Any]:
    eligible=int(catalog.get("denominator_eligible",0)); residual=int(catalog.get("denominator_residual_noise",0))
    return rate_record("RESIDUAL_RATE_WITH_DENOMINATOR",residual,eligible,left_scope=str(catalog.get("family_catalog_id")),zero_reason="EMPTY_ASSIGNMENT_DOMAIN",rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"])


def ambiguity_rate(corr: Mapping[str, Any], *, direction: str="LEFT_TO_RIGHT") -> dict[str, Any]:
    anchors=defaultdict(list)
    for edge in corr.get("edges",[]):
        key=edge["left_family_id"] if direction=="LEFT_TO_RIGHT" else edge["right_family_id"]
        anchors[key].append(edge)
    denominator=numerator=0
    for edges in anchors.values():
        if not edges: continue
        denominator+=1
        ratios=[]
        for e in edges:
            n,d=(int(x) for x in e["jaccard"].split("/")); ratios.append((Fraction(n,d),e))
        maximum=max(v for v,_ in ratios)
        if maximum>0 and sum(1 for v,_ in ratios if v==maximum)>1: numerator+=1
    return rate_record("AMBIGUITY_RATE_WITH_DENOMINATOR",numerator,denominator,left_scope=str(corr.get("left_catalog_id")),right_scope=str(corr.get("right_catalog_id")),zero_reason="NO_POSITIVE_CORRESPONDENCE_DOMAIN",rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"])


def directional_survival(corr: Mapping[str, Any], *, direction: str="LEFT_TO_RIGHT", metric_type: str="CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR") -> dict[str, Any]:
    anchor_key="left_family_id" if direction=="LEFT_TO_RIGHT" else "right_family_id"
    containment_key="left_containment" if direction=="LEFT_TO_RIGHT" else "right_containment"
    anchors=set(); survived=set()
    for edge in corr.get("edges",[]):
        anchor=edge[anchor_key]; anchors.add(anchor)
        n,d=(int(x) for x in edge[containment_key].split("/"))
        if n==d and d>0: survived.add(anchor)
    return rate_record(metric_type,len(survived),len(anchors),left_scope=str(corr.get("left_catalog_id" if direction=="LEFT_TO_RIGHT" else "right_catalog_id")),right_scope=str(corr.get("right_catalog_id" if direction=="LEFT_TO_RIGHT" else "left_catalog_id")),zero_reason="NO_ANCHOR_FAMILY_OPPORTUNITY",rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"])


def exact_cross_method(corr: Mapping[str, Any], *, direction: str="LEFT_TO_RIGHT") -> dict[str, Any]:
    anchor_key="left_family_id" if direction=="LEFT_TO_RIGHT" else "right_family_id"
    anchors=set(); exact=set()
    for edge in corr.get("edges",[]):
        anchor=edge[anchor_key]; anchors.add(anchor)
        n,d=(int(x) for x in edge["jaccard"].split("/"))
        if n==d and d>0: exact.add(anchor)
    return rate_record("CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR",len(exact),len(anchors),left_scope=str(corr.get("left_catalog_id")),right_scope=str(corr.get("right_catalog_id")),zero_reason="NO_ANCHOR_FAMILY_OPPORTUNITY",rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"])


def chronological_stability(catalog: Mapping[str, Any], occurrence_time: Mapping[str,str], *, split_time: str="2026-06-16T00:00:00Z") -> dict[str, Any]:
    families=_families(catalog); denominator=len(families); numerator=0
    for members in families.values():
        has_h1=any(occurrence_time.get(m,"") < split_time for m in members)
        has_h2=any(occurrence_time.get(m,"") >= split_time for m in members)
        if has_h1 and has_h2: numerator+=1
    return rate_record("CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR",numerator,denominator,left_scope=str(catalog.get("family_catalog_id")),zero_reason="NO_DISCOVERED_FAMILY_IN_BENCHMARK_WINDOW",rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"])


def invariant_cores(catalogs: Sequence[Mapping[str, Any]], *, minimum_catalog_support: int=2) -> dict[str, Any]:
    maps=[]
    for catalog in catalogs:
        m={}
        for fid,members in _families(catalog).items():
            for member in members: m[member]=fid
        maps.append(m)
    members=sorted(set().union(*(set(m) for m in maps))) if maps else []
    adjacency={m:set() for m in members}
    for a,b in combinations(members,2):
        support=sum(1 for mapping in maps if mapping.get(a) is not None and mapping.get(a)==mapping.get(b))
        if support>=minimum_catalog_support: adjacency[a].add(b); adjacency[b].add(a)
    visited=set(); cores=[]
    for member in members:
        if member in visited: continue
        stack=[member]; component=set()
        while stack:
            cur=stack.pop()
            if cur in visited: continue
            visited.add(cur); component.add(cur); stack.extend(sorted(adjacency[cur]-visited))
        if len(component)>=2:
            row={"member_ids":sorted(component),"minimum_catalog_support":minimum_catalog_support,"catalog_denominator":len(maps)}; row["invariant_core_id"]="SFC.CORE."+logical_hash(row)[:24]; cores.append(row)
    payload={"cores":cores,"catalog_denominator":len(maps),"authority_state":"INACTIVE_CONFORMANCE_ONLY"}; payload["logical_hash"]=logical_hash(payload); return payload


def family_evidence_stream(*, source_population_id: str, source_c2e_stream_id: str, catalogs: Sequence[Mapping[str,Any]], evidence_objects: Sequence[Mapping[str,Any]], evaluation_cutoff: str) -> dict[str,Any]:
    statuses={str(c.get("evidence_status")) for c in catalogs}
    if "FAMILY_EVIDENCE_PRESENT" in statuses: status="FAMILY_EVIDENCE_PRESENT"
    elif statuses and statuses <= {"NO_STABLE_FAMILY"}: status="NO_STABLE_FAMILY"
    elif "QUARANTINED" in statuses: status="QUARANTINED"
    else: status="NOT_EVALUABLE" if catalogs else "UNRESOLVED"
    payload={"source_population_id":source_population_id,"source_c2e_stream_id":source_c2e_stream_id,"evidence_object_ids":sorted(str(o.get("logical_hash") or o.get("metric_id") or o.get("correspondence_id")) for o in evidence_objects),"status":status,"missingness":[],"rule_pack_ids":["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"],"first_valid_time":evaluation_cutoff,"evaluation_cutoff":evaluation_cutoff,"authority_state":"INACTIVE_CONFORMANCE_ONLY"}
    payload["stream_id"]="SFC.FAMILY.EVIDENCE."+logical_hash(payload)[:24]; payload["logical_hash"]=logical_hash(payload); return payload
