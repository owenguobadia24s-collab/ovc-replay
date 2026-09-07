from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, canonical_id, seal_object


def semantic_configuration_key(configuration: Mapping[str, Any]) -> str:
    required=("method_family_id","projection_id","parameters","representation_id","context_id")
    if any(key not in configuration for key in required):
        raise CBSContractError("CBS_CONFIGURATION_IDENTITY_INCOMPLETE")
    return canonical_id({key:configuration[key] for key in required})


def build_specification_opportunity_ledger(configurations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not configurations:
        raise CBSContractError("CBS_SPECIFICATION_LEDGER_EMPTY")
    ids=[str(row.get("configuration_id","")) for row in configurations]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise CBSContractError("CBS_SPECIFICATION_CONFIGURATION_ID_INVALID")
    rows=[]
    for configuration in configurations:
        state=str(configuration.get("state",""))
        if state not in {"DECLARED","ATTEMPTED","FAILED","NOT_EVALUABLE","POST_HOC"}:
            raise CBSContractError("CBS_SPECIFICATION_STATE_INVALID")
        rows.append({**dict(configuration),"semantic_configuration_key":semantic_configuration_key(configuration)})
    groups: dict[str,list[str]]={}
    for row in rows:
        groups.setdefault(row["semantic_configuration_key"],[]).append(str(row["configuration_id"]))
    return seal_object({"schema":"ovc-cbs-boundary-specification-opportunity-ledger/v0.1",
        "configurations":sorted(rows,key=lambda row:str(row["configuration_id"])),
        "semantic_groups":[{"semantic_configuration_key":key,"configuration_ids":sorted(values),"family_weight":1}
                           for key,values in sorted(groups.items())],
        "declared_configuration_count":len(rows),"semantic_configuration_count":len(groups),
        "complete_accounting":True,"post_hoc_visible":True,"best_configuration_selection":"FORBIDDEN"},
        id_field="specification_ledger_id")


def family_factorised_support(*, region_id: str, evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str,str],dict[str,set[str]]]={}
    for row in evidence:
        family=str(row.get("method_family_id","")); cluster=str(row.get("dependence_cluster",""))
        if not family or not cluster:
            raise CBSContractError("PARAMETER_MULTIPLICITY_FAIL:MISSING_FAMILY_OR_CLUSTER")
        bucket=groups.setdefault((family,cluster),{"estimates":set(),"configurations":set(),"semantic":set()})
        bucket["estimates"].add(str(row.get("estimate_id","")))
        bucket["configurations"].add(str(row.get("configuration_id","")))
        bucket["semantic"].add(str(row.get("semantic_configuration_key","")))
    rows=[]
    for (family,cluster),values in sorted(groups.items()):
        rows.append({"method_family_id":family,"dependence_cluster":cluster,"supports_region":bool(values["estimates"]),
            "estimate_ids":sorted(values["estimates"]),"configuration_ids":sorted(values["configurations"]),
            "semantic_configuration_keys":sorted(values["semantic"]),"family_weight":1})
    return seal_object({"schema":"ovc-cbs-family-factorised-support/v0.1","region_id":region_id,
        "families":rows,"supporting_family_count":sum(row["supports_region"] for row in rows),
        "supporting_dependence_cluster_count":len({row["dependence_cluster"] for row in rows if row["supports_region"]}),
        "independent_vote_count":None,"aggregation":"NO_VOTE_NO_AVERAGE"},id_field="family_support_id")
