from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_hash


class SFCFDIError(ValueError):
    pass


ASSIGNMENT_STATUSES = {"MEMBER","RESIDUAL","NOISE","SINGLETON","AMBIGUOUS","NOT_COMPARABLE","NOT_EVALUABLE","QUARANTINED"}


@dataclass(frozen=True)
class FamilyMethodSpec:
    family_method_id: str
    method_version: str
    configuration_id: str
    input_representation_pack_id: str
    comparison_spec_id: str
    minimum_support: int = 2
    assignment_policy: str = "NEAREST_SUPPORTED_PROTOTYPE"
    residual_policy: str = "EXPLICIT_RESIDUAL"
    prototype_policy: str = "LEXICOGRAPHIC_MEDOID"
    tie_policy: str = "AMBIGUOUS"
    deterministic_ordering: str = "LEXICOGRAPHIC_ID"
    authority_state: str = "INACTIVE_CONFORMANCE_ONLY"


def family_id(*, population_id: str, representation_pack_id: str, comparison_spec_id: str, method: FamilyMethodSpec, member_ids: Sequence[str]) -> str:
    identity={"population":population_id,"pack":representation_pack_id,"comparison":comparison_spec_id,"method":method.family_method_id,"version":method.method_version,"configuration":method.configuration_id,"members":sorted(member_ids)}
    return "SFC.FAMILY."+logical_hash(identity)[:24]


def catalog_id(*, population_id: str, representation_pack_id: str, comparison_spec_id: str, method: FamilyMethodSpec) -> str:
    return "SFC.CATALOG."+logical_hash({"population":population_id,"pack":representation_pack_id,"comparison":comparison_spec_id,"method":method.family_method_id,"version":method.method_version,"configuration":method.configuration_id})[:24]


def assignment(occurrence_id: str, catalog: str, status: str, family_ids: Sequence[str] = (), *, reason_codes: Sequence[str] = (), first_valid_time: str = "SYNTHETIC", evaluation_cutoff: str = "SYNTHETIC") -> dict[str, Any]:
    if status not in ASSIGNMENT_STATUSES:
        raise SFCFDIError("SFC_ASSIGNMENT_STATUS_INVALID")
    families=sorted(set(str(x) for x in family_ids))
    if status=="MEMBER" and len(families)!=1:
        raise SFCFDIError("SFC_MEMBER_REQUIRES_ONE_FAMILY")
    if status=="AMBIGUOUS" and len(families)<2:
        raise SFCFDIError("SFC_AMBIGUOUS_REQUIRES_MULTIPLE_FAMILIES")
    payload={"occurrence_id":occurrence_id,"catalog_id":catalog,"status":status,"family_ids":families,"reason_codes":sorted(set(reason_codes)),"first_valid_time":first_valid_time,"evaluation_cutoff":evaluation_cutoff}
    return {**payload,"logical_hash":logical_hash(payload)}


def build_catalog(*, population_id: str, representation_pack_id: str, comparison_spec_id: str, method: FamilyMethodSpec, family_members: Mapping[str, Sequence[str]], assignments: Sequence[Mapping[str, Any]], eligible_ids: Sequence[str], evaluation_cutoff: str) -> dict[str, Any]:
    cid=catalog_id(population_id=population_id,representation_pack_id=representation_pack_id,comparison_spec_id=comparison_spec_id,method=method)
    records=[]
    supported: dict[str,list[str]]={}
    for key,members in sorted(family_members.items()):
        uniq=sorted(set(str(x) for x in members))
        if len(uniq) < method.minimum_support:
            continue
        fid=family_id(population_id=population_id,representation_pack_id=representation_pack_id,comparison_spec_id=comparison_spec_id,method=method,member_ids=uniq)
        supported[key]=uniq
        proto=min(uniq)
        record={"family_id":fid,"family_catalog_id":cid,"member_ids":uniq,"support_count":len(uniq),"prototype_descriptor":{"policy":method.prototype_policy,"prototype_id":proto},"within_family_evidence":{"status":"PRESENT"},"dispersion_evidence":{"status":"UNSPECIFIED_CONFORMANCE_ONLY"},"exemplar_ids":[proto],"counterexample_ids":[],"first_valid_time":evaluation_cutoff,"evaluation_cutoff":evaluation_cutoff,"authority_state":"INACTIVE_CONFORMANCE_ONLY"}
        record["logical_hash"]=logical_hash(record)
        records.append(record)
    normalized=[]
    valid_family_ids={r["family_id"] for r in records}
    for row in sorted((dict(r) for r in assignments),key=lambda r:r["occurrence_id"]):
        if row["catalog_id"] != cid:
            raise SFCFDIError("SFC_ASSIGNMENT_CATALOG_MISMATCH")
        if any(fid not in valid_family_ids for fid in row.get("family_ids",[])):
            raise SFCFDIError("SFC_ASSIGNMENT_UNKNOWN_FAMILY")
        normalized.append(row)
    status_by={row["occurrence_id"]:row["status"] for row in normalized}
    eligible=sorted(set(str(x) for x in eligible_ids))
    residual=[oid for oid in eligible if status_by.get(oid) in {"RESIDUAL","NOISE","SINGLETON"}]
    assigned=[oid for oid in eligible if status_by.get(oid)=="MEMBER"]
    evidence_status="FAMILY_EVIDENCE_PRESENT" if records else "NO_STABLE_FAMILY"
    payload={"family_catalog_id":cid,"source_population_id":population_id,"representation_pack_id":representation_pack_id,"comparison_spec_id":comparison_spec_id,"family_method_id":method.family_method_id,"configuration_id":method.configuration_id,"families":records,"assignment_records":normalized,"residual_ids":residual,"noise_ids":[oid for oid in eligible if status_by.get(oid)=="NOISE"],"singleton_ids":[oid for oid in eligible if status_by.get(oid)=="SINGLETON"],"denominator_eligible":len(eligible),"denominator_assigned":len(assigned),"denominator_residual_noise":len(residual),"evidence_status":evidence_status,"first_valid_time":evaluation_cutoff,"evaluation_cutoff":evaluation_cutoff,"authority_state":"INACTIVE_CONFORMANCE_ONLY"}
    payload["logical_hash"]=logical_hash(payload)
    return payload


def deterministic_star_assign(distance_rows: Iterable[Mapping[str, Any]], *, occurrence_ids: Sequence[str], threshold: str, population_id: str, representation_pack_id: str, comparison_spec_id: str, method: FamilyMethodSpec, evaluation_cutoff: str) -> dict[str, Any]:
    """Fixture-safe deterministic star-family wrapper, not a promoted scientific method."""
    ids=sorted(set(str(x) for x in occurrence_ids))
    adjacency={oid:set() for oid in ids}
    limit=Decimal(threshold)
    for row in distance_rows:
        if row.get("status")!="EVALUATED" or row.get("value") is None:
            continue
        if Decimal(str(row["value"])) <= limit:
            a,b=str(row["left_representation_id"]),str(row["right_representation_id"])
            if a in adjacency and b in adjacency and a!=b:
                adjacency[a].add(b); adjacency[b].add(a)
    remaining=set(ids); groups={}
    while remaining:
        center=min(remaining,key=lambda oid:(-len(adjacency[oid]&remaining),oid))
        members=sorted({center}|(adjacency[center]&remaining))
        groups[center]=members
        remaining.difference_update(members)
    cid=catalog_id(population_id=population_id,representation_pack_id=representation_pack_id,comparison_spec_id=comparison_spec_id,method=method)
    supported={k:v for k,v in groups.items() if len(v)>=method.minimum_support}
    family_ids_by_member={}
    for key,members in supported.items():
        fid=family_id(population_id=population_id,representation_pack_id=representation_pack_id,comparison_spec_id=comparison_spec_id,method=method,member_ids=members)
        for oid in members: family_ids_by_member.setdefault(oid,[]).append(fid)
    rows=[]
    for oid in ids:
        fids=sorted(family_ids_by_member.get(oid,[]))
        if len(fids)==1: rows.append(assignment(oid,cid,"MEMBER",fids,evaluation_cutoff=evaluation_cutoff,first_valid_time=evaluation_cutoff))
        elif len(fids)>1: rows.append(assignment(oid,cid,"AMBIGUOUS",fids,reason_codes=["EXACT_TIE"],evaluation_cutoff=evaluation_cutoff,first_valid_time=evaluation_cutoff))
        else: rows.append(assignment(oid,cid,"SINGLETON",reason_codes=["BELOW_MINIMUM_SUPPORT"],evaluation_cutoff=evaluation_cutoff,first_valid_time=evaluation_cutoff))
    return build_catalog(population_id=population_id,representation_pack_id=representation_pack_id,comparison_spec_id=comparison_spec_id,method=method,family_members=supported,assignments=rows,eligible_ids=ids,evaluation_cutoff=evaluation_cutoff)
